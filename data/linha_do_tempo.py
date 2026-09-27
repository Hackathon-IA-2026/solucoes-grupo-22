"""Monta a linha do tempo de uma empresa (aba Timeline do chat) a partir de data/coppezip.duckdb e do índice dos
relatórios em uso, data/docs_titan.duckdb.

Biblioteca, não script: quem chama é o serviço da Busca (proper_mcps/docs/busca.py, rotas /timeline_empresas e
/timeline?cnpj=&de=&ate=), que monta a linha do tempo na hora em que a pessoa escolhe empresa e período na tela. Nada
fica pré-gerado em disco.

Nada é digitado: cada evento, indicador e passo de trajetória sai de uma tabela ou de um trecho de relatório, com a fonte.
- Empresa = o CNPJ e os agentes que ele controla hoje (participacoes_societarias), como em capacidade_por_grupo.
- Eventos por ano: usinas que entraram em operação e leilões de geração (SIGA e leilões da ANEEL, ligados pelo CEG),
  contratos e obras de transmissão (SIGET), financiamentos do BNDES, projetos de P&D (ANEEL) e trechos dos relatórios
  sobre os temas de TEMAS (busca por palavras e por sentido nos relatórios da empresa, veja paginas_por_tema).
- Indicadores por ano: demonstrações da CVM (kpis_financeiros), capacidade das usinas, BNDES, PDD e P&D.
- Trajetórias: passos ligados pelo mesmo ativo (CEG, contrato, nome do projeto) ou só pela ordem no tempo, e cada
  ligação diz qual é: os dados mostram a sequência, não a causa.
"""
import datetime
import os
import re
import unicodedata

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raiz do repositório


BANCO = os.path.join(RAIZ, "data", "coppezip.duckdb")
DOCS = os.path.join(RAIZ, "data", "docs_titan.duckdb")
ANOS_ANTES = 2  # o período sugerido começa dois anos antes da primeira DFP, para mostrar o que antecede os números
MAX_ANOS = 40  # teto do período pedido na tela
MAX_TRAJETORIAS = 8
ANOS_ANTES_TRAJETORIA = 5  # trajetórias podem começar até cinco anos antes da linha do tempo (leilão, contrato)
CANDIDATAS = 12  # páginas candidatas por relatório e tema em cada um dos dois métodos de busca
POR_RELATORIO = 6  # páginas lidas por relatório e tema depois da fusão
K_RRF = 60  # constante da fusão por posição (RRF), a mesma da Busca (proper_mcps/docs/server.py)

# tema: (rótulo, consulta BM25 nos relatórios, expressão que marca o tema num texto minúsculo e sem acento)
TEMAS = {
    "sustentabilidade": ("Sustentabilidade", "sustentabilidade gestão socioambiental ESG biodiversidade",
                         r"sustentab|socioambienta|\besg\b|\basg\b|biodiversidade"),
    "descarbonizacao": ("Descarbonização", "descarbonização redução de emissões de gases de efeito estufa carbono",
                        r"descarboniz|emissoes|carbono|efeito estufa|\bgee\b|net zero|neutralidade|tco2"),
    "transicao": ("Transição energética", "transição energética hidrogênio armazenamento baterias eletrificação",
                  r"transicao energetica|hidrogenio|\bh2\b|armazenamento|baterias?\b|mobilidade eletrica|eletrificac"),
    "renovavel": ("Energia renovável", "energia renovável eólica solar fotovoltaica biomassa",
                  r"renovave|eolic|solar|fotovolt|biomassa|biogas"),
    "investimento_ambiental": ("Investimento ambiental",
                               "investimentos ambientais títulos verdes debêntures verdes financiamento sustentável",
                               r"investimentos? (socio)?ambienta|titulos? verdes?|green ?bonds?|debentures? verdes?"
                               r"|financiamentos? sustentave|capex verde|rotulagem esg|sustainability.linked"),
    "inovacao": ("Inovação", "inovação pesquisa e desenvolvimento P&D digitalização startups",
                 r"inovac|p&d|pesquisa e desenvolvimento|startups?|digitaliza|redes? inteligentes?|smart grid"),
    "metas": ("Metas e compromissos", "metas compromissos climáticos 2030 2050 SBTi Pacto Global",
              r"\bmetas?\b|compromissos?|sbti|science based|pacto global|\bods\b"),
}
RENOVAVEL = r"eolic|solar|fotovolt|biomassa|hidr"  # origem da usina (SIGA) ou fonte do leilão, sem acento
GRI = re.compile(r"\b[23]\d{2}-\d{1,2}\b|\bGRI\b|\bSASB\b")  # índices GRI e SASB: listas de indicadores, não fatos
ACAO = (r"alcanc|aprov|conclu|realiz|reduz|investi|inaugur|lanc|emiti|capt|implant|assin|aderi|atingi|ampli|inici"
        r"|contrat|adquiri|anunci|obtev|obtiv|certific|entreg|aument|instal|desenvolv|conquist|vend|encerr|substitu")
FRASE = re.compile(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])|\s*•\s*")
# nome do empreendimento no projeto do BNDES ("IMPLANTACAO DO COMPLEXO EOLICO SERRA DO ASSURUA, COMPOSTO ...")
PROJETO_USINA = re.compile(r"\b(?:complexo|parque|usinas?|centra(?:l|is))(?: (?:eolic|solar|fotovoltaic|hidreletric"
                           r"|termeletric|geradora)\w*)*(?: (?:de energia|eolic\w*|solar))? (?:(?:do|da|de) )?"
                           r"([a-z][a-z0-9 ]{2,40}?)(?=,| com\b| composto| integrante| localizad| fase\b| no\b| na\b"
                           r"| em\b| e respectiv|\.|$)")
PROJETO_CONTRATO = re.compile(r"contrato de concessao.{0,80}?\bn[o°º]?\.? ?(\d{1,3}) ?/ ?(\d{4})")
RESSALVA = "Os passos estão em ordem no tempo; cada ligação diz o que os une nos dados. Isso não prova que um passo causou o outro."


def sem_acento(texto):
    return unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()


def temas_de(texto):
    t = sem_acento(texto)
    return [k for k, (_, _, rx) in TEMAS.items() if re.search(rx, t)]


def digitos(cnpj):
    return re.sub(r"\D", "", cnpj or "")


def num(v, casas):
    return f"{v:,.{casas}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def formatar(v, unidade):
    if unidade == "R$":
        return (f"R$ {num(v / 1e9, 2)} bi" if abs(v) >= 1e9 else f"R$ {num(v / 1e6, 1)} mi" if abs(v) >= 1e6
                else f"R$ {num(v, 0)}")
    return {"MW": f"{num(v, 1)} MW", "x": f"{num(v, 2)}x", "%": f"{num(v, 1)}%"}[unidade]


def limpo(texto):
    return re.sub(r"\s+", " ", re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", texto)).strip()


def curto(texto, limite=320):
    return texto if len(texto) <= limite else texto[:limite].rsplit(" ", 1)[0] + "…"


# ------------------------------------------------------------------------------------------------ relatórios
def melhor_frase(texto, rx, ano, empresa):
    """(pontos, frase) da frase que mais parece um fato do tema: termos do tema, verbo de ação, a própria empresa como
    sujeito, o ano e números. Descarta o que não é frase: título, legenda, glossário, tabela, texto cortado."""
    melhor = None
    sujeito = re.compile(rf"\b(companhia|empresa|grupo|{re.escape(empresa)})\b|\b({ACAO})\w*mos\b")
    for f in FRASE.split(limpo(texto)):
        f = re.sub(r"^\d{1,3} (?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ])", "", f)  # número de nota de rodapé colado no começo
        palavras = f.split()
        if (not 60 <= len(f) <= 450 or GRI.search(f) or "|" in f or not re.match(r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9“\"(]", f)
                or re.match(r"[^:.]{2,60}: [a-zà-ú]", f)  # glossário ou item de lista: "Programa X: iniciativa que..."
                or re.search(r"\b(acess[ae]|website|youtube|clique)", sem_acento(f))  # remete ao site, não é fato
                or not re.search(r"[.!?:;)”\"]$", f) or sum(c.isalpha() for c in f) < 0.6 * len(f)
                or sum(p[0].isupper() for p in palavras) > 0.4 * len(palavras)):
            continue
        s = sem_acento(f)
        acertos = len(re.findall(rx, s))
        if not acertos:
            continue
        pontos = (2 * min(acertos, 3) + 2 * bool(re.search(rf"\b({ACAO})", s)) + 1.5 * bool(sujeito.search(s))
                  + bool(re.search(rf"\b({ano}|{ano - 1})\b", f)) + 0.5 * bool(re.search(r"\d", f)))
        if melhor is None or pontos > melhor[0]:
            melhor = (pontos, f)
    return melhor


def paginas_por_tema(docs, arquivos):
    """{(arquivo, tema): [páginas candidatas, da mais provável para a menos]}.

    Duas buscas, fundidas por posição (RRF, o mesmo 1/(60 + posição) da Busca), porque as notas não são comparáveis:
    - palavras: BM25 na consulta do tema sobre os parágrafos do relatório (tabela blocos);
    - sentido: cosseno entre o vetor da consulta do tema (tabela temas, gravada pelo indexar_docs_titan.py) e os
      vetores dos trechos da página (tabela trechos, Amazon Titan) - acha a página que fala do tema com outras palavras.
    A comparação é sempre dentro do mesmo relatório, então o contexto que o indexador põe antes de cada trecho
    ("empresa ano, título.") é igual em todos os candidatos e não distorce a ordem.
    """
    if not arquivos:
        return {}
    if not docs.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = 'temas'").fetchone()[0]:
        raise RuntimeError(f"{DOCS} não tem a tabela temas: rode data/indexar_docs_titan.py --temas")
    pontos = {}
    for tema, arquivo, pagina, posicao in docs.execute(f"""
            SELECT tema, arquivo, pagina, row_number() OVER (PARTITION BY tema, arquivo ORDER BY s DESC) AS posicao
            FROM (SELECT m.tema AS tema, t.arquivo AS arquivo, t.pagina AS pagina,
                         max(array_cosine_similarity(t.embedding, m.embedding)) AS s
                  FROM trechos t, temas m WHERE t.arquivo IN (SELECT unnest(?)) GROUP BY ALL)
            QUALIFY posicao <= {CANDIDATAS}""", [arquivos]).fetchall():
        pontos.setdefault((arquivo, tema), {})[pagina] = 1 / (K_RRF + posicao)
    for tema, (_, consulta, _) in TEMAS.items():
        for arquivo, pagina, posicao in docs.execute(f"""
                SELECT arquivo, pagina, row_number() OVER (PARTITION BY arquivo ORDER BY s DESC) AS posicao
                FROM (SELECT arquivo, pagina, max(s) AS s FROM
                        (SELECT arquivo, pagina, fts_main_blocos.match_bm25(id, ?) AS s FROM blocos
                         WHERE arquivo IN (SELECT unnest(?)))
                      WHERE s IS NOT NULL GROUP BY ALL)
                QUALIFY posicao <= {CANDIDATAS}""", [consulta, arquivos]).fetchall():
            por_pagina = pontos.setdefault((arquivo, tema), {})
            por_pagina[pagina] = por_pagina.get(pagina, 0) + 1 / (K_RRF + posicao)
    return {chave: sorted(p, key=p.get, reverse=True)[:POR_RELATORIO] for chave, p in pontos.items()}


def trechos_dos_relatorios(docs, documentos):
    """{(arquivo, tema): (pontos, página, frase, parágrafo)}: para cada relatório e tema, a melhor frase entre os
    parágrafos das páginas candidatas (paginas_por_tema)."""
    # ano do relatório e primeira palavra do nome da empresa (Cemig, Engie, EDP...), para reconhecê-la como sujeito
    info = {d["arquivo"]: (d["ano"], sem_acento(d["empresa"]).split()[0]) for d in documentos}
    candidatas = paginas_por_tema(docs, sorted(info))
    if not candidatas:
        return {}
    paragrafos = {}
    for arquivo, pagina, texto in docs.execute(
            "SELECT arquivo, pagina, texto FROM blocos WHERE arquivo || '#' || pagina IN (SELECT unnest(?))",
            [[f"{a}#{p}" for (a, _), ps in candidatas.items() for p in ps]]).fetchall():
        paragrafos.setdefault((arquivo, pagina), []).append(texto)
    achados = {}
    for (arquivo, tema), paginas in candidatas.items():
        rx = TEMAS[tema][2]
        for posicao, pagina in enumerate(paginas, start=1):
            for texto in paragrafos.get((arquivo, pagina), []):
                if len(GRI.findall(texto)) >= 3:
                    continue
                frase = melhor_frase(texto, rx, *info[arquivo])
                if frase is None or frase[0] < 7:  # termos do tema e mais ação, sujeito ou o ano: não só uma definição
                    continue
                pontos = frase[0] + 1 / posicao
                if pontos > achados.get((arquivo, tema), (0,))[0]:
                    achados[(arquivo, tema)] = (pontos, pagina, frase[1], texto)
    return achados


def eventos_dos_relatorios(documentos, achados):
    """Um evento por ano e tema (o trecho mais bem pontuado entre os relatórios do ano); o mesmo trecho em vários
    temas vira um evento só."""
    melhor = {}
    for d in documentos:
        for tema in TEMAS:
            a = achados.get((d["arquivo"], tema))
            if a and a[0] > melhor.get((d["ano"], tema), (0,))[0]:
                melhor[(d["ano"], tema)] = (a[0], d, a)
    por_pagina = {}
    for (ano, tema), (pontos, d, (_, pagina, frase, texto)) in sorted(melhor.items(), key=lambda x: -x[1][0]):
        chave = (d["arquivo"], pagina, frase)
        if chave in por_pagina:
            por_pagina[chave]["temas"] = sorted(set(por_pagina[chave]["temas"]) | {tema})
            continue
        # sem link público (a maior parte dos PDFs do documentos.csv), a tela abre a cópia local pela rota da Busca
        url = d["url"] and d["url"] + (f"#page={pagina}" if d["url"].lower().endswith(".pdf") else "")
        por_pagina[chave] = {
            "ano": ano, "tipo": "relatorio", "titulo": TEMAS[tema][0], "descricao": curto(frase),
            "temas": sorted(set(temas_de(frase)) | {tema}), "pontos": pontos,
            "fonte": {"texto": f"{d['empresa']}, {d['titulo']}, p. {pagina}", "documento": d["titulo"],
                      "arquivo": d["arquivo"], "pagina": pagina, "url": url, "trecho": curto(limpo(texto), 1200)}}
    return list(por_pagina.values())


# ------------------------------------------------------------------------------------------------ tabelas
def dados_do_grupo(con, cnpj):
    """Linhas das tabelas para o CNPJ e os agentes que ele controla hoje."""
    grupo = [r[0] for r in con.execute("""SELECT cnpj_agente FROM participacoes_societarias
        WHERE cnpj_participante = ? AND na_cadeia_de_controle UNION SELECT ?""", [cnpj, cnpj]).fetchall()]

    def linhas(sql, params):
        cur = con.execute(sql, params)
        nomes = [c[0] for c in cur.description]
        return [dict(zip(nomes, r)) for r in cur.fetchall()]

    usinas = linhas("""
        SELECT u.ceg, u.nome, u.origem, u.fase, u.data_entrada_operacao AS entrada, any_value(u.data_base) AS data_base,
               sum(coalesce(u.potencia_fiscalizada_kw, u.potencia_outorgada_kw) * p.participacao_pct / 100) / 1000 AS mw
        FROM usinas u JOIN usinas_proprietarios p USING (ceg) WHERE p.cnpj IN (SELECT unnest(?))
        GROUP BY u.ceg, u.nome, u.origem, u.fase, u.data_entrada_operacao""", [grupo])
    for u in usinas:
        u["operando"] = u["fase"] == "Operação" and u["entrada"] is not None and u["entrada"] <= datetime.date.today()
        u["renovavel"] = bool(re.search(RENOVAVEL, sem_acento(u["origem"])))
    return {
        "usinas": usinas,
        "leiloes": linhas(r"""
            SELECT l.ano, coalesce(l.leilao_ccee, l.numero_leilao) AS leilao, l.tipo_leilao, l.fonte_energia,
                   l.potencia_mw, l.preco_leilao_brl_mwh, u.ceg
            FROM leiloes_geracao l JOIN usinas u ON regexp_replace(u.ceg, '\.\d+$', '') = l.ceg
            WHERE u.ceg IN (SELECT unnest(?))""", [[u["ceg"] for u in usinas]]),
        "contratos": linhas("""SELECT id_contrato, numero_contrato, concessionaria, data_assinatura
            FROM transmissao_contratos WHERE cnpj IN (SELECT unnest(?))""", [grupo]),
        "obras": linhas("""
            SELECT id_contrato, empreendimento, bool_or(situacao IN ('Em Operação', 'Concluído')
                   AND data_operacao_comercial <= current_date) AS operando, min(data_operacao_comercial) AS entrada
            FROM transmissao_empreendimentos WHERE cnpj IN (SELECT unnest(?)) GROUP BY ALL""", [grupo]),
        "bndes": linhas("""
            SELECT year(data_contratacao) AS ano, projeto, sum(valor_contratado_brl) AS valor,
                   bool_or(inovacao = 'SIM') AS inovacao, count(*) AS operacoes
            FROM bndes_operacoes WHERE cnpj IN (SELECT unnest(?)) AND valor_contratado_brl > 0
            GROUP BY ALL""", [grupo]),
        "ped": linhas("""SELECT ano_cadastro AS ano, titulo, custo_previsto_brl AS custo FROM ped_projetos
            WHERE cnpj IN (SELECT unnest(?)) AND ano_cadastro IS NOT NULL""", [grupo]),
        "pdd": linhas("""SELECT ano, sum(realizado_brl) AS realizado, string_agg(DISTINCT distribuidora, ', ') AS distribuidoras
            FROM pdd_investimentos WHERE cnpj IN (SELECT unnest(?)) AND realizado_brl > 0 GROUP BY ano""", [grupo]),
        "kpis": linhas("SELECT * FROM kpis_financeiros WHERE cnpj = ? ORDER BY ano", [cnpj]),
    }


def fonte_tabela(texto, tabela, catalogo, itens=None):
    f = {"texto": texto, "tabela": tabela, "origem": catalogo.get(tabela, "")}
    url = re.search(r"https?://\S+", f["origem"])
    if url:
        f["url"] = url.group(0).rstrip(",;)")
    if itens:
        f["itens"] = itens
    return f


def lista_nomes(nomes, n=3):
    nomes = list(dict.fromkeys(nomes))
    return ", ".join(nomes[:n]) + (f" e mais {len(nomes) - n}" if len(nomes) > n else "")


def eventos_das_tabelas(d, catalogo, primeiro, ultimo):
    eventos = []
    no_periodo = range(primeiro, ultimo + 1)

    # usinas que entraram em operação no ano
    por_ano = {}
    for u in d["usinas"]:
        if u["operando"] and u["entrada"].year in no_periodo:
            por_ano.setdefault(u["entrada"].year, []).append(u)
    for ano, us in por_ano.items():
        us.sort(key=lambda u: -u["mw"])
        por_origem = {}
        for u in us:
            por_origem[u["origem"]] = por_origem.get(u["origem"], 0) + u["mw"]
        partes = ", ".join(f"{o.lower()} {formatar(mw, 'MW')}" for o, mw in sorted(por_origem.items(), key=lambda x: -x[1]))
        renov = any(u["renovavel"] for u in us)
        eventos.append({
            "ano": ano, "tipo": "usina", "titulo": f"Usinas em operação: +{formatar(sum(por_origem.values()), 'MW')}",
            "descricao": f"{len(us)} usina(s) que a empresa controla hoje entraram em operação ({partes}): "
                         f"{lista_nomes(u['nome'] for u in us)}.",
            "temas": ["renovavel"] if renov else [],
            "fonte": fonte_tabela(f"ANEEL SIGA (usinas e usinas_proprietarios), data de entrada em operação; potência "
                                  f"fiscalizada × participação dos donos do grupo; base de {us[0]['data_base']:%d/%m/%Y}",
                                  "usinas", catalogo,
                                  [f"{u['ceg']}: {u['nome']} ({u['origem']}, {formatar(u['mw'], 'MW')})" for u in us[:12]])})

    # leilões de geração em que usinas do grupo venderam energia
    leiloes = {}
    for l in d["leiloes"]:
        if l["ano"] in no_periodo:
            leiloes.setdefault((l["ano"], l["leilao"]), []).append(l)
    usina = {u["ceg"]: u for u in d["usinas"]}
    for (ano, leilao), ls in leiloes.items():
        fontes = sorted({l["fonte_energia"] for l in ls if l["fonte_energia"]})
        precos = [l["preco_leilao_brl_mwh"] for l in ls if l["preco_leilao_brl_mwh"]]
        eventos.append({
            "ano": ano, "tipo": "leilao", "titulo": f"Leilão de geração: {leilao}",
            "descricao": f"{len(ls)} usina(s) que hoje são do grupo venderam energia no {leilao} ({ls[0]['tipo_leilao']}; "
                         f"{', '.join(fontes).lower()}; {formatar(sum(l['potencia_mw'] or 0 for l in ls), 'MW')}"
                         + (f"; preço médio R$ {num(sum(precos) / len(precos), 2)}/MWh" if precos else "") + ").",
            "temas": ["renovavel"] if any(re.search(RENOVAVEL, sem_acento(f)) for f in fontes) else [],
            "fonte": fonte_tabela("ANEEL, resultado dos leilões de geração (leiloes_geracao), ligado às usinas do grupo "
                                  "pelo CEG", "leiloes_geracao", catalogo,
                                  [f"{l['ceg']}: {usina[l['ceg']]['nome']}" for l in ls[:12]])})

    # transmissão: contratos assinados e empreendimentos que entraram em operação
    por_ano = {}
    for c in d["contratos"]:
        if c["data_assinatura"] and c["data_assinatura"].year in no_periodo:
            por_ano.setdefault(c["data_assinatura"].year, []).append(c)
    for ano, cs in por_ano.items():
        cs.sort(key=lambda c: c["data_assinatura"])
        eventos.append({
            "ano": ano, "tipo": "transmissao_contrato", "titulo": f"Transmissão: {len(cs)} concessão(ões) assinada(s)",
            "descricao": "Contrato(s) de concessão de transmissão assinado(s): " + "; ".join(
                f"{c['numero_contrato']} ({c['concessionaria']}, {c['data_assinatura']:%d/%m/%Y})" for c in cs) + ".",
            "temas": [],
            "fonte": fonte_tabela("ANEEL SIGET (transmissao_contratos), data de assinatura", "transmissao_contratos",
                                  catalogo)})
    por_ano = {}
    for o in d["obras"]:
        if o["operando"] and o["entrada"].year in no_periodo:
            por_ano.setdefault(o["entrada"].year, []).append(o)
    for ano, os_ in por_ano.items():
        eventos.append({
            "ano": ano, "tipo": "transmissao_operacao", "titulo": f"Transmissão: {len(os_)} empreendimento(s) em operação",
            "descricao": f"Entraram em operação comercial: {lista_nomes(o['empreendimento'] for o in os_)}.",
            "temas": [],
            "fonte": fonte_tabela("ANEEL SIGET (transmissao_empreendimentos), data de operação comercial",
                                  "transmissao_empreendimentos", catalogo,
                                  [f"{o['empreendimento']} ({o['entrada']:%d/%m/%Y})" for o in os_[:12]])})

    # financiamentos do BNDES: os três maiores projetos de cada ano
    por_ano = {}
    for b in d["bndes"]:
        if b["ano"] in no_periodo:
            por_ano.setdefault(b["ano"], []).append(b)
    for ano, bs in por_ano.items():
        for b in sorted(bs, key=lambda b: -b["valor"])[:3]:
            projeto = limpo(b["projeto"] or "projeto sem descrição")
            eventos.append({
                "ano": ano, "tipo": "bndes", "titulo": f"Financiamento BNDES: {formatar(b['valor'], 'R$')}",
                "descricao": f"{formatar(b['valor'], 'R$')} contratados ({b['operacoes']} operação(ões)) para: "
                             f"{curto(projeto.capitalize(), 260)}",
                "temas": sorted(set(temas_de(projeto)) | ({"inovacao"} if b["inovacao"] else set())),
                "fonte": fonte_tabela("BNDES, operações não automáticas (bndes_operacoes): valor contratado no ano pela "
                                      "empresa e pelas controladas", "bndes_operacoes", catalogo)})

    # P&D regulado: projetos cadastrados no ano
    por_ano = {}
    for p in d["ped"]:
        if p["ano"] in no_periodo:
            por_ano.setdefault(p["ano"], []).append(p)
    for ano, ps in por_ano.items():
        verdes = [p for p in ps if set(temas_de(p["titulo"] or "")) - {"inovacao"}]
        ps.sort(key=lambda p: (not (p in verdes), -(p["custo"] or 0)))
        custo = sum(p["custo"] or 0 for p in ps)
        eventos.append({
            "ano": ano, "tipo": "ped", "titulo": f"P&D: {len(ps)} projeto(s) cadastrado(s)",
            "descricao": f"{len(ps)} projeto(s) de P&D cadastrados na ANEEL" + (f" ({formatar(custo, 'R$')} previstos)"
                         if custo else "") + f": {lista_nomes(curto(limpo(p['titulo'] or ''), 90) for p in ps)}.",
            "temas": sorted({"inovacao"} | {t for p in verdes for t in temas_de(p["titulo"])}),
            "fonte": fonte_tabela("ANEEL, P&D regulado (ped_projetos), ano de cadastro e custo previsto", "ped_projetos",
                                  catalogo, [curto(limpo(p["titulo"] or ""), 140) for p in ps[:12]])})
    return eventos


# ------------------------------------------------------------------------------------------------ indicadores
CONTAS = {  # de onde vem cada coluna de kpis_financeiros (as mesmas contas de data/construir.py)
    "receita_liquida_brl": "conta 3.01 da DRE", "lucro_liquido_brl": "conta 3.11 da DRE",
    "ebitda_brl": "EBIT (3.05) + depreciação e amortização da DFC",
    "investimento_total_brl": "o maior entre o CAPEX de caixa (6.02) e o custo de construção das concessões",
    "divida_liquida_ebitda": "dívida bruta (2.01.04 + 2.02.01) menos caixa (1.01.01 + 1.01.02), sobre o EBITDA",
    "margem_ebitda_pct": "EBITDA sobre a receita (3.01)", "roe_pct": "lucro (3.11) sobre o patrimônio líquido (2.03)",
}


def graficos(d, primeiro, ultimo):
    """Gráficos de linha: [{id, titulo, unidade, nota, linhas: [{id, nome, pontos: [{ano, valor, fonte}]}]}]."""
    kpis = [k for k in d["kpis"] if primeiro <= k["ano"] <= ultimo]

    def cvm(coluna, nome):
        return {"id": coluna, "nome": nome, "pontos": [
            {"ano": k["ano"], "valor": k[coluna],
             "fonte": f"CVM DFP {k['ano']} ({k['escopo']}), {CONTAS[coluna]} (kpis_financeiros)"}
            for k in kpis if k[coluna] is not None]}

    capacidade = []
    for renov, nome in ((True, "Capacidade renovável"), (False, "Capacidade não renovável")):
        us = [u for u in d["usinas"] if u["operando"] and u["renovavel"] == renov]
        if us:
            base = f"{us[0]['data_base']:%d/%m/%Y}"
            capacidade.append({
                "id": "capacidade_renovavel_mw" if renov else "capacidade_nao_renovavel_mw", "nome": nome, "pontos": [
                    {"ano": a, "valor": round(sum(u["mw"] for u in us if u["entrada"].year <= a), 1),
                     "fonte": f"ANEEL SIGA: usinas em operação que o grupo controla hoje, somadas até o ano de entrada "
                              f"em operação (base de {base})"} for a in range(primeiro, ultimo + 1)]})
    investimento = [cvm("investimento_total_brl", "Investimento total (CVM)"),
                    {"id": "bndes_brl", "nome": "Financiamento BNDES contratado", "pontos": [
                        {"ano": a, "valor": sum(b["valor"] for b in d["bndes"] if b["ano"] == a),
                         "fonte": "BNDES, operações não automáticas: soma do valor contratado no ano pelo grupo"}
                        for a in range(primeiro, ultimo)]},
                    {"id": "pdd_realizado_brl", "nome": "Investimento realizado no PDD (ANEEL)", "pontos": [
                        {"ano": p["ano"], "valor": p["realizado"],
                         "fonte": f"ANEEL PDD (pdd_investimentos): realizado no ano por {p['distribuidoras']}"}
                        for p in sorted(d["pdd"], key=lambda p: p["ano"]) if primeiro <= p["ano"] < ultimo]}]
    ped = [{"id": "ped_brl", "nome": "Custo previsto dos projetos cadastrados", "pontos": [
        {"ano": a, "valor": sum(p["custo"] or 0 for p in d["ped"] if p["ano"] == a),
         "fonte": "ANEEL, P&D regulado (ped_projetos): custo previsto dos projetos cadastrados no ano pelo grupo"}
        for a in range(primeiro, ultimo)]}]
    todos = [
        ("resultado", "Receita, EBITDA e lucro", "R$", "CVM DFP, consolidado quando a empresa o publica; EBITDA = EBIT "
         "(3.05) + depreciação e amortização",
         [cvm("receita_liquida_brl", "Receita líquida"), cvm("ebitda_brl", "EBITDA"),
          cvm("lucro_liquido_brl", "Lucro líquido")]),
        ("investimento", "Investimento e financiamento", "R$", "Investimento total = o maior entre o CAPEX de caixa e o "
         "custo de construção das concessões (CVM); BNDES e PDD somam o grupo, anos fechados", investimento),
        ("capacidade", "Capacidade de geração em operação", "MW", "Usinas que o grupo controla hoje, acumuladas pelo ano "
         "de entrada em operação: não mostra compras nem vendas de usinas", capacidade),
        ("alavancagem", "Dívida líquida / EBITDA", "x", "CVM DFP; dívida bruta sem arrendamentos",
         [cvm("divida_liquida_ebitda", "Dívida líquida / EBITDA")]),
        ("margens", "Margem EBITDA e ROE", "%", "CVM DFP",
         [cvm("margem_ebitda_pct", "Margem EBITDA"), cvm("roe_pct", "ROE")]),
        ("ped", "P&D regulado (ANEEL)", "R$", "Por ano de cadastro do projeto, anos fechados", ped),
    ]
    saida = []
    for gid, titulo, unidade, nota, linhas in todos:
        linhas = [l for l in linhas if len(l["pontos"]) >= 2 and any(p["valor"] for p in l["pontos"])]
        if linhas:
            saida.append({"id": gid, "titulo": titulo, "unidade": unidade, "nota": nota, "linhas": linhas})
    return saida


# tipo de evento ou tema -> séries em que se olha a variação do ano (o "impacto" observado, sem atribuir causa)
IMPACTO = {
    "usina": ["capacidade_renovavel_mw", "capacidade_nao_renovavel_mw"], "leilao": ["investimento_total_brl"],
    "bndes": ["investimento_total_brl", "divida_liquida_ebitda"], "transmissao_contrato": ["investimento_total_brl"],
    "transmissao_operacao": ["receita_liquida_brl"], "ped": ["ped_brl"],
    "renovavel": ["capacidade_renovavel_mw"], "investimento_ambiental": ["investimento_total_brl", "bndes_brl"],
    "descarbonizacao": ["investimento_total_brl"], "transicao": ["investimento_total_brl"],
    "metas": ["investimento_total_brl"], "sustentabilidade": ["investimento_total_brl"], "inovacao": ["ped_brl"],
}


def variacoes(graficos_, ano):
    """{série: variação do ano contra o anterior}, com o texto e a fonte do ponto."""
    saida = {}
    for g in graficos_:
        for linha in g["linhas"]:
            pontos = {p["ano"]: p for p in linha["pontos"]}
            if ano not in pontos or pontos[ano]["valor"] is None:
                continue
            atual, antes = pontos[ano]["valor"], (pontos.get(ano - 1) or {}).get("valor")
            v = {"indicador": linha["nome"], "grafico": g["titulo"], "unidade": g["unidade"], "valor": atual,
                 "anterior": antes, "fonte": pontos[ano]["fonte"]}
            if antes is not None:
                v["variacao"] = atual - antes
                if antes:
                    v["variacao_pct"] = round(100 * (atual - antes) / abs(antes), 1)
                v["texto"] = (f"{linha['nome']}: {formatar(antes, g['unidade'])} em {ano - 1} → "
                              f"{formatar(atual, g['unidade'])} em {ano}"
                              + (f" ({'+' if atual >= antes else ''}{num(v['variacao_pct'], 1)}%)"
                                 if "variacao_pct" in v else ""))
            else:
                v["texto"] = f"{linha['nome']}: {formatar(atual, g['unidade'])} em {ano} (sem {ano - 1} na base)"
            saida[linha["id"]] = v
    return saida


# ------------------------------------------------------------------------------------------------ trajetórias
def passo_investimento(serie, inicio, fim):
    """O ano de maior alta do investimento total (CVM) entre inicio (exclusive) e fim, se houve alta."""
    altas = [(serie[a] - serie[a - 1], a) for a in range(inicio + 1, fim + 1)
             if serie.get(a) is not None and serie.get(a - 1) is not None and serie[a] > serie[a - 1]]
    if not altas:
        return None
    a = max(altas)[1]
    return {"ano": a, "papel": "Investimento", "vinculo": "ordem no tempo (investimento total da empresa)",
            "texto": f"Investimento total da empresa subiu de {formatar(serie[a - 1], 'R$')} em {a - 1} para "
                     f"{formatar(serie[a], 'R$')} em {a}.",
            "fonte": {"texto": f"CVM DFP {a - 1} e {a} (kpis_financeiros, investimento_total_brl)"}}


def passo_operacao(usinas_, vinculo):
    operando = [u for u in usinas_ if u["operando"]]
    passos = []
    if operando:
        anos = sorted({u["entrada"].year for u in operando})
        passos.append({
            "ano": anos[-1], "papel": "Resultado observado", "vinculo": vinculo,
            "texto": f"{len(operando)} usina(s) em operação em {anos[0]}" + (f"–{anos[-1]}" if len(anos) > 1 else "")
                     + f", {formatar(sum(u['mw'] for u in operando), 'MW')} atribuídos ao grupo: "
                     f"{lista_nomes(u['nome'] for u in operando)}.",
            "fonte": {"texto": "ANEEL SIGA (usinas), data de entrada em operação",
                      "itens": [f"{u['ceg']}: {u['nome']} ({u['entrada']:%d/%m/%Y})" for u in operando[:12]]}})
    faltam = [u for u in usinas_ if not u["operando"]]
    if faltam:
        passos.append({
            "ano": datetime.date.today().year, "papel": "Ainda não observado", "vinculo": vinculo,
            "texto": f"{len(faltam)} usina(s) ainda fora de operação ({lista_nomes(u['fase'] for u in faltam)}), "
                     f"{formatar(sum(u['mw'] for u in faltam), 'MW')}.",
            "fonte": {"texto": "ANEEL SIGA (usinas), fase atual", "itens": [f"{u['ceg']}: {u['nome']}" for u in faltam[:12]]}})
    return passos


def nome_do_conjunto(usinas_):
    return re.sub(r"\s+([0-9]+|[IVXLC]+|[A-Z])$", "", usinas_[0]["nome"]).strip()


def trajetorias(d, rel, primeiro, ultimo):
    serie = {k["ano"]: k["investimento_total_brl"] for k in d["kpis"]}
    usinas = d["usinas"]
    nomes = [(sem_acento(u["nome"]), u) for u in usinas]
    saida, cobertas = [], set()

    def leilao_de(cegs):
        ls = sorted((l for l in d["leiloes"] if l["ceg"] in cegs), key=lambda l: l["ano"])
        if not ls:
            return None
        l0 = [l for l in ls if l["leilao"] == ls[0]["leilao"]]
        return {"ano": ls[0]["ano"], "papel": "Contratação", "vinculo": None,
                "texto": f"{len(l0)} usina(s) do conjunto venderam energia no {ls[0]['leilao']} ({ls[0]['tipo_leilao']}).",
                "fonte": {"texto": "ANEEL, leilões de geração (leiloes_geracao), pelo CEG",
                          "itens": [f"{l['ceg']}: {l['fonte_energia']}, {formatar(l['potencia_mw'] or 0, 'MW')}" for l in l0[:12]]}}

    def fechar(titulo, temas, passos):
        passos = [p for p in passos if p]
        passos.sort(key=lambda p: p["ano"])
        for p in passos[1:]:
            p["vinculo"] = p["vinculo"] or "ordem no tempo"
        passos[0]["vinculo"] = None
        if len(passos) >= 2 and passos[0]["ano"] >= primeiro - ANOS_ANTES_TRAJETORIA and passos[-1]["ano"] >= primeiro:
            saida.append({"titulo": titulo, "temas": temas, "passos": passos, "ressalva": RESSALVA})

    # 1. geração: financiamento do BNDES cujo projeto nomeia usinas do grupo (e o leilão delas, pelo CEG) -> operação
    for b in sorted(d["bndes"], key=lambda b: (b["ano"], -b["valor"])):
        m = PROJETO_USINA.search(sem_acento(b["projeto"]))
        if not m or len(m.group(1).strip()) < 4:
            continue
        alvo = m.group(1).strip()
        us = [u for n, u in nomes if re.fullmatch(re.escape(alvo) + r"( [0-9]+| [ivxlc]+| [a-z])?", n)]
        us = [u for u in us if u["ceg"] not in cobertas and (not u["operando"] or u["entrada"].year >= b["ano"])]
        if not us:
            continue
        cobertas.update(u["ceg"] for u in us)
        fim = max([u["entrada"].year for u in us if u["operando"]] or [b["ano"]])
        fechar(f"{nome_do_conjunto(us)}: financiamento → operação",
               sorted({"renovavel"} if any(u["renovavel"] for u in us) else set()),
               [leilao_de({u["ceg"] for u in us}),
                {"ano": b["ano"], "papel": "Financiamento", "vinculo": "as mesmas usinas (CEG no leilão, nome no projeto do BNDES)",
                 "texto": f"BNDES contratou {formatar(b['valor'], 'R$')} para: {curto(limpo(b['projeto']).capitalize(), 200)}",
                 "fonte": {"texto": "BNDES, operações não automáticas (bndes_operacoes), descrição do projeto"}},
                passo_investimento(serie, b["ano"], fim)]
               + passo_operacao(us, "o nome do projeto no BNDES é o das usinas no SIGA"))

    # 2. geração: leilão -> operação (mesmo CEG), para as usinas que o BNDES não cobriu
    por_leilao = {}
    for l in d["leiloes"]:
        if l["ceg"] not in cobertas:
            por_leilao.setdefault((l["ano"], l["leilao"]), set()).add(l["ceg"])
    for (ano, leilao), cegs in sorted(por_leilao.items(), key=lambda x: -len(x[1])):
        us = [u for u in usinas if u["ceg"] in cegs and u["ceg"] not in cobertas]
        if not us:
            continue
        cobertas.update(cegs)
        fim = max([u["entrada"].year for u in us if u["operando"]] or [ano])
        passos = [leilao_de(cegs), passo_investimento(serie, ano, fim)] + passo_operacao(us, "mesmo CEG (leilão e SIGA)")
        fechar(f"{leilao}: leilão → operação", sorted({"renovavel"} if any(u["renovavel"] for u in us) else set()), passos)

    # 3. transmissão: contrato de concessão -> (financiamento do BNDES que cita o contrato) -> operação
    for c in d["contratos"]:
        m = re.match(r"(\d+)/(\d{4})", c["numero_contrato"] or "")
        if not c["data_assinatura"] or not m or int(m.group(2)) < primeiro - ANOS_ANTES_TRAJETORIA:
            continue
        obras = [o for o in d["obras"] if o["id_contrato"] == c["id_contrato"]
                 and not (o["operando"] and o["entrada"] < c["data_assinatura"])]
        if not obras:
            continue
        chave = (int(m.group(1)), m.group(2))
        financ = [b for b in d["bndes"] if (x := PROJETO_CONTRATO.search(sem_acento(b["projeto"])))
                  and (int(x.group(1)), x.group(2)) == chave]
        operando = [o for o in obras if o["operando"]]
        fim = max([o["entrada"].year for o in operando] or [c["data_assinatura"].year])
        passos = [{"ano": c["data_assinatura"].year, "papel": "Contratação", "vinculo": None,
                   "texto": f"Contrato de concessão de transmissão {c['numero_contrato']} assinado ({c['concessionaria']}).",
                   "fonte": {"texto": "ANEEL SIGET (transmissao_contratos)"}}]
        passos += [{"ano": b["ano"], "papel": "Financiamento", "vinculo": "o projeto do BNDES cita o número do contrato",
                    "texto": f"BNDES contratou {formatar(b['valor'], 'R$')} para: {curto(limpo(b['projeto']).capitalize(), 200)}",
                    "fonte": {"texto": "BNDES, operações não automáticas (bndes_operacoes), descrição do projeto"}}
                   for b in financ[:1]]
        passos.append(passo_investimento(serie, c["data_assinatura"].year, fim))
        if operando:
            anos = sorted({o["entrada"].year for o in operando})
            passos.append({"ano": anos[-1], "papel": "Resultado observado", "vinculo": "mesmo contrato (SIGET)",
                           "texto": f"{len(operando)} empreendimento(s) do contrato em operação comercial em {anos[0]}"
                                    + (f"–{anos[-1]}" if len(anos) > 1 else "") + f": "
                                    f"{lista_nomes([o['empreendimento'] for o in operando], 2)}.",
                           "fonte": {"texto": "ANEEL SIGET (transmissao_empreendimentos), data de operação comercial"}})
        if len(operando) < len(obras):
            passos.append({"ano": datetime.date.today().year, "papel": "Ainda não observado",
                           "vinculo": "mesmo contrato (SIGET)",
                           "texto": f"{len(obras) - len(operando)} empreendimento(s) do contrato ainda sem operação comercial.",
                           "fonte": {"texto": "ANEEL SIGET (transmissao_empreendimentos), situação"}})
        fechar(f"Transmissão {c['numero_contrato']} ({c['concessionaria']}): contrato → operação", [], passos)

    # 4. relatório: tema estratégico no ano A -> alta do investimento em A+1 -> o que se observa em A+2
    renovavel_por_ano = {}
    for u in usinas:
        if u["operando"] and u["renovavel"]:
            renovavel_por_ano[u["entrada"].year] = renovavel_por_ano.get(u["entrada"].year, 0) + u["mw"]
    ultimo_kpi = max(serie, default=0)
    for ano in sorted({e["ano"] for e in rel}):
        evs = [e for e in rel if e["ano"] == ano and set(e["temas"]) & {"metas", "transicao", "renovavel",
                                                                        "investimento_ambiental", "descarbonizacao"}]
        inv = passo_investimento(serie, ano, ano + 1)
        if not evs or not inv:
            continue
        e = max(evs, key=lambda e: e["pontos"])
        resultado = None
        if renovavel_por_ano.get(ano + 2):
            resultado = {"ano": ano + 2, "papel": "Resultado observado", "vinculo": "ordem no tempo",
                         "texto": f"{formatar(renovavel_por_ano[ano + 2], 'MW')} renováveis do grupo entraram em "
                                  f"operação em {ano + 2}.",
                         "fonte": {"texto": "ANEEL SIGA (usinas), data de entrada em operação"}}
        elif ano + 2 <= ultimo_kpi:
            k = {k["ano"]: k for k in d["kpis"]}
            if k.get(ano + 1) and k.get(ano + 2) and k[ano + 1]["ebitda_brl"] and k[ano + 2]["ebitda_brl"]:
                resultado = {"ano": ano + 2, "papel": "Resultado observado", "vinculo": "ordem no tempo",
                             "texto": f"EBITDA de {formatar(k[ano + 1]['ebitda_brl'], 'R$')} em {ano + 1} para "
                                      f"{formatar(k[ano + 2]['ebitda_brl'], 'R$')} em {ano + 2}.",
                             "fonte": {"texto": k[ano + 2]["fonte"]}}
        else:
            resultado = {"ano": ano + 2, "papel": "Ainda não observado", "vinculo": "ordem no tempo",
                         "texto": f"A base ainda não tem {ano + 2} para ver o resultado.",
                         "fonte": {"texto": f"CVM DFP até {ultimo_kpi}; ANEEL SIGA"}}
        fechar(f"{e['titulo']} no relatório de {ano} → investimento → resultado", e["temas"],
               [{"ano": ano, "papel": "Estratégia anunciada", "vinculo": None, "texto": e["descricao"], "fonte": e["fonte"]},
                inv, resultado])

    saida.sort(key=lambda t: (not t["temas"], all(p["papel"] != "Resultado observado" for p in t["passos"]),
                              -t["passos"][-1]["ano"], -len(t["passos"])))
    titulos = set()
    unicas = [t for t in saida if not (t["titulo"] in titulos or titulos.add(t["titulo"]))]
    return unicas[:MAX_TRAJETORIAS]


# ------------------------------------------------------------------------------------------------ montagem
ORDEM_TIPOS = ["relatorio", "usina", "leilao", "bndes", "transmissao_contrato", "transmissao_operacao", "ped"]


def selecao(con, docs):
    """O seletor da tela: uma linha por empresa com o que a base tem dela, sem montar linha do tempo nenhuma.
    'limites' é o período que se pode pedir e 'periodo' o sugerido para cada empresa."""
    hoje = datetime.date.today().year
    dfp = {c: (a, b) for c, a, b in con.execute(
        "SELECT cnpj, min(ano), max(ano) FROM kpis_financeiros GROUP BY 1").fetchall()}
    usinas = dict(con.execute("""
        SELECT g.cnpj_participante, count(DISTINCT p.ceg) FROM
            (SELECT cnpj_participante, cnpj_agente FROM participacoes_societarias WHERE na_cadeia_de_controle
             UNION SELECT cnpj, cnpj FROM empresas) g
        JOIN usinas_proprietarios p ON p.cnpj = g.cnpj_agente GROUP BY 1""").fetchall())
    relatorios = {digitos(c): (n, a, b) for c, n, a, b in docs.execute(
        "SELECT cnpj, count(*), min(ano), max(ano) FROM documentos WHERE cnpj IS NOT NULL GROUP BY 1").fetchall()}
    inicio = min([a for a, _ in dfp.values()] + [hoje]) - ANOS_ANTES
    primeiro = min([r[1] for r in relatorios.values()] + [inicio])
    saida = []
    for cnpj, nome, comercial, apelidos in con.execute("""
            SELECT e.cnpj, e.nome_social, e.nome_comercial, string_agg(DISTINCT a.apelido, ', ')
            FROM empresas e LEFT JOIN empresas_apelidos a USING (cnpj) GROUP BY ALL ORDER BY e.nome_social""").fetchall():
        rel = relatorios.get(digitos(cnpj))
        # o período sugerido cobre o que a empresa tem: os relatórios indexados e a primeira DFP, com os anos antes dela
        candidatos = ([rel[1]] if rel else []) + ([dfp[cnpj][0] - ANOS_ANTES] if cnpj in dfp else [])
        de = min(candidatos or [inicio])
        saida.append({"id": digitos(cnpj), "cnpj": cnpj, "nome": nome, "nome_comercial": comercial,
                      "apelidos": apelidos or "", "periodo": [max(de, primeiro), hoje],
                      "dfp": list(dfp[cnpj]) if cnpj in dfp else None, "usinas": usinas.get(cnpj, 0),
                      "relatorios": rel[0] if rel else 0})
    return {"gerado_em": datetime.date.today().isoformat(), "limites": [primeiro, hoje],
            "temas": {k: v[0] for k, v in TEMAS.items()}, "empresas": saida}


def empresa_de(con, cnpj):
    """{cnpj, nome, nome_comercial, apelidos} da empresa, ou None se o CNPJ não está na base."""
    linha = con.execute("""SELECT e.cnpj, e.nome_social, e.nome_comercial, string_agg(DISTINCT a.apelido, ', ')
                           FROM empresas e LEFT JOIN empresas_apelidos a USING (cnpj)
                           WHERE regexp_replace(e.cnpj, '\\D', '', 'g') = ? GROUP BY ALL""",
                        [digitos(cnpj)]).fetchone()
    if not linha:
        return None
    return {"cnpj": linha[0], "nome": linha[1], "nome_comercial": linha[2], "apelidos": linha[3] or ""}


def documentos_de(docs, cnpj, primeiro, ultimo):
    """Relatórios da empresa publicados no período (o ano do evento é o ano de publicação do relatório)."""
    cur = docs.execute("""SELECT arquivo, empresa, cnpj, ano, titulo, url FROM documentos
                          WHERE regexp_replace(cnpj, '\\D', '', 'g') = ? AND ano BETWEEN ? AND ?
                          ORDER BY ano, arquivo""", [digitos(cnpj), primeiro, ultimo])
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def linha_do_tempo(con, docs, empresa, primeiro, ultimo):
    catalogo = dict(con.execute("SELECT tabela, fonte FROM catalogo").fetchall())
    documentos = documentos_de(docs, empresa["cnpj"], primeiro, ultimo)
    achados = trechos_dos_relatorios(docs, documentos)
    d = dados_do_grupo(con, empresa["cnpj"])
    rel = eventos_dos_relatorios(documentos, achados)
    eventos = rel + eventos_das_tabelas(d, catalogo, primeiro, ultimo)
    graf = graficos(d, primeiro, ultimo)
    anos = []
    for ano in range(primeiro, ultimo + 1):
        evs = sorted((e for e in eventos if e["ano"] == ano),
                     key=lambda e: (not e["temas"], ORDEM_TIPOS.index(e["tipo"]), -e.get("pontos", 0)))
        var = variacoes(graf, ano)
        if not evs and not var:
            continue
        ligadas = list(dict.fromkeys(s for e in evs for chave in [e["tipo"], *e["temas"]] for s in IMPACTO.get(chave, [])))
        anos.append({"ano": ano, "destaque": any(e["temas"] for e in evs),
                     "temas": sorted({t for e in evs for t in e["temas"]}),
                     "eventos": [{k: v for k, v in e.items() if k not in ("ano", "pontos")} for e in evs],
                     "impacto": [{"texto": var[s]["texto"], "fonte": var[s]["fonte"]} for s in ligadas
                                 if s in var and var[s].get("variacao")],
                     "evolucao": list(var.values())})
    return {
        "empresa": empresa, "gerado_em": datetime.date.today().isoformat(), "periodo": [primeiro, ultimo],
        "temas": {k: v[0] for k, v in TEMAS.items()},
        "anos": anos, "trajetorias": trajetorias(d, rel, primeiro, ultimo), "graficos": graf,
        "notas": ["Empresa = o CNPJ e os agentes que ele controla hoje (composição societária declarada à ANEEL): usinas, "
                  "leilões, transmissão, BNDES e P&D somam o grupo; os indicadores financeiros são os do CNPJ na CVM "
                  "(consolidado quando publicado).",
                  "Usinas e leilões mostram os ativos que o grupo controla hoje: compras e vendas passadas não aparecem.",
                  "Os trechos de relatório vêm da busca por palavras (BM25) e por sentido (embedding) nos relatórios da "
                  "empresa publicados no período: confira a página.",
                  "Impacto e trajetórias mostram o que veio depois nos dados, não a causa."]}

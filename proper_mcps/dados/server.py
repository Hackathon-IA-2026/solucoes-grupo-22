"""Servidor MCP "energynexus-dados": a base do EnergyNexus (CVM, ANEEL, ONS, BNDES, ANBIMA) em DuckDB, só leitura.

Ferramentas: buscar_empresa, indicadores_financeiros, listar_tabelas, descrever_tabela, valores_distintos, consultar_sql.
O banco (data/energynexus.duckdb) é montado por data/construir.py; as descrições das tabelas vêm da tabela catalogo.
"""
import datetime
import decimal
import json
import math
import os
import re
import threading

import duckdb
from mcp.server.mcpserver import MCPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # raiz do repositório


DB = os.path.join(RAIZ, "data", "energynexus.duckdb")
LIMITE_LINHAS = 200
MAX_TRIMESTRES = 40  # 10 anos de ITR
TEMPO_MAXIMO_S = 30

INSTRUCOES = """Você responde sobre empresas do setor elétrico brasileiro com os dados desta base. Regras:
1. Empresa: chame buscar_empresa antes de tudo e use o cnpj devolvido. Se a confiança vier "aproximada", diga ao usuário
   qual empresa achou e não troque uma empresa por outra de nome parecido (Taesa não é AES; a Eletrobras hoje é a
   Axia Energia S.A.; holding e subsidiária têm CNPJs diferentes).
2. Números financeiros: use indicadores_financeiros. A conta 3.05 é EBIT, não EBITDA; o EBITDA da base é calculado
   (EBIT + depreciação e amortização) e deve ser apresentado assim. Os valores estão em reais (R$), não em milhares.
3. Todo número da resposta tem de vir de uma consulta a tabela desta base. Nunca escreva números no SQL para montar
   dados: consultar_sql recusa consultas sem tabela ou com valores digitados.
4. Antes de filtrar por texto, confira o valor exato com valores_distintos. Se uma consulta voltar vazia, revise o
   filtro antes de concluir que o dado não existe. Leia as ressalvas de descrever_tabela.
5. Cite a fonte (coluna fonte, ou tabela e conta) e o ano de cada número. Se a base não tiver o dado, diga isso com
   clareza e aponte de onde ele poderia vir.
6. Prefira poucas consultas agregadas a muitas pequenas.
7. Aviso é para ler: quando a resposta traz aviso, aviso_trimestres, aviso_holding, ressalvas_cvm ou como_usar, resolva
   o que ele diz (peça o resto, troque o CNPJ) ou conte ao usuário o que ficou de fora. Nenhuma resposta corta dado em
   silêncio: se veio cortada, ela diz quanto e como pedir o que falta.
8. Holding não é concessão: DEC, FEC, tarifa e mercado ficam no CNPJ da distribuidora; receita e dívida consolidadas
   ficam na holding. Diga sempre de qual das duas é o número.
9. ressalvas_cvm aponta período em que a própria empresa enviou a DRE com sinal trocado ou conta faltando. Nesse
   período não apresente EBIT, EBITDA nem margem sem repetir a ressalva ao usuário.
10. Grupo econômico: nunca monte o perímetro com LIKE no nome. '%neoenergia%' em distribuidora acha 2 das 5
   distribuidoras do grupo (Coelba, Cosern e Elektro não têm a marca no nome) e '%RGE %' acha FOTONS DE SAO GEORGE.
   Use grupos_economicos (cnpj, agente, holding_cvm, cnpj_holding_cvm), diga quantos CNPJs entraram e quais. Só as 151
   companhias da CVM estão em kpis_financeiros; as demais do grupo aparecem nas tabelas da ANEEL, do BNDES e do SND."""

mcp = MCPServer("energynexus-dados", instructions=INSTRUCOES)


def _con():
    return duckdb.connect(DB, read_only=True)


def _tabelas(con) -> list[str]:
    return [r[0] for r in con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' ORDER BY 1").fetchall()]


def _ident(nome: str, validos: list[str]) -> str:
    if nome not in validos:
        raise ValueError(f"'{nome}' não existe. Opções: {', '.join(validos)}")
    return '"' + nome.replace('"', '""') + '"'


DIGITOS = 6  # dígitos significativos: o arredondamento acompanha a ordem de grandeza do número
CASAS_MINIMAS = 2  # em reais os centavos ficam (R$ 111.004,76 não pode virar R$ 111.005)


def _arredondar(v: float) -> float:
    """Arredonda por dígitos significativos. Casas fixas (round(v, 4)) zeravam razões pequenas: capex/ativo de
    2,1e-6 virava 0.0 e o modelo lia "zero"."""
    if v == 0 or not math.isfinite(v):
        return v
    return round(v, max(CASAS_MINIMAS, DIGITOS - 1 - math.floor(math.log10(abs(v)))))


def _json(v):
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, float):
        return _arredondar(v)
    return v


def _linhas(cur, limite=None) -> list[dict]:
    nomes = [d[0] for d in cur.description]
    rows = cur.fetchmany(limite) if limite else cur.fetchall()
    return [{k: _json(v) for k, v in zip(nomes, r)} for r in rows]


# ------------------------------------------------------------------------------------------------ empresas
BUSCA = """
WITH a AS (SELECT cnpj, string_agg(apelido, ', ') AS apelidos,
                  string_agg(apelido, ', ') FILTER (tipo = 'ticker' AND regexp_matches(apelido, '\\d$')) AS tickers
           FROM empresas_apelidos GROUP BY cnpj),
f AS (SELECT cnpj, min(ano) AS primeiro, max(ano) AS ultimo FROM kpis_financeiros GROUP BY cnpj)
SELECT e.cnpj, e.nome_social, e.nome_comercial, e.situacao, a.tickers,
       CASE WHEN f.cnpj IS NULL THEN 'não' ELSE f.primeiro || '-' || f.ultimo END AS anos_com_demonstracoes,
       strip_accents(lower(concat_ws(' ', e.nome_social, e.nome_comercial, a.apelidos))) AS busca
FROM empresas e LEFT JOIN a USING (cnpj) LEFT JOIN f USING (cnpj)
"""
COLUNAS_EMPRESA = ["cnpj", "nome_social", "nome_comercial", "situacao", "tickers", "anos_com_demonstracoes"]

# universo completo de empresas do setor (4,2 mil em grupos_economicos, 10 mil no cadastro da ANEEL), fora das 151
# companhias da CVM que estão em empresas: é onde moram as concessões sem apelido de mercado (Energisa Tocantins)
FORA_DA_CVM = """
fora AS (SELECT cnpj, agente AS nome, NULL::BOOLEAN AS ativo, 1 AS prioridade,
                'em grupos_economicos, grupo ' || coalesce(holding_cvm, 'sem holding na CVM') AS origem
         FROM grupos_economicos WHERE cnpj IS NOT NULL
         UNION ALL
         SELECT cnpj, razao_social, ativo, CASE WHEN distribuicao THEN 0 ELSE 1 END,
                'no cadastro da ANEEL (' || coalesce(sigla, 'sem sigla') || ')'
         FROM agentes_aneel WHERE cnpj IS NOT NULL)
"""
# palavra inteira, não pedaço: '%rge %' em nome casava FOTONS DE SAO GEORGE e '%light%' casava LIGHTSOURCE
PALAVRA_INTEIRA = ("regexp_matches(' ' || strip_accents(lower(nome)) || ' ', '[^a-z0-9]' "
                   "|| regexp_escape(strip_accents(lower(?))) || '[^a-z0-9]')")


def _fora_da_cvm(con, onde: str, params: list, limite: int) -> list[tuple]:
    """Busca no universo fora da CVM, nas colunas de COLUNAS_EMPRESA mais a origem e se o CNPJ também está na CVM
    (nesse caso o cadastro da CVM manda). Quando o termo não diz o segmento, a distribuidora vem antes: é dela o
    CNPJ de DEC/FEC, tarifa e mercado."""
    return con.execute(f"""WITH b AS ({BUSCA}), {FORA_DA_CVM},
            m AS (SELECT cnpj, any_value(nome) AS nome, any_value(origem) AS origem, bool_or(ativo) AS ativo,
                         min(prioridade) AS prioridade, min(length(nome)) AS tamanho
                  FROM fora WHERE {onde} GROUP BY cnpj)
        SELECT m.cnpj, coalesce(b.nome_social, m.nome), b.nome_comercial,
               coalesce(b.situacao, CASE WHEN m.ativo THEN 'ATIVO na ANEEL' WHEN m.ativo IS NULL
                                         THEN 'sem registro na CVM' ELSE 'INATIVO na ANEEL' END),
               b.tickers, coalesce(b.anos_com_demonstracoes, 'não'), m.origem, b.nome_social IS NOT NULL
        FROM m LEFT JOIN b USING (cnpj) ORDER BY m.prioridade, m.tamanho LIMIT ?""", params + [limite]).fetchall()


def _como_fora(prefixo: str, r: tuple) -> str:
    return f"{prefixo} {r[6]}" + ("" if r[7] else "; agente sem registro na CVM, não tem demonstrações")


def _buscar(con, termo: str, limite: int) -> list[dict]:
    termo = termo.strip()
    achados, vistos = [], set()

    def juntar(rows, confianca, como):
        for r in rows:
            if r[0] not in vistos:
                vistos.add(r[0])
                achados.append({**dict(zip(COLUNAS_EMPRESA, r[:6])), "confianca": confianca, "como_encontrou": como(r)})

    cols = ", ".join(f"b.{c}" for c in COLUNAS_EMPRESA)
    # 1. apelido, marca, nome antigo ou ticker exatos
    juntar(con.execute(f"""WITH b AS ({BUSCA}) SELECT {cols}, ap.tipo, ap.apelido, ap.observacao
        FROM empresas_apelidos ap JOIN b USING (cnpj)
        WHERE strip_accents(lower(ap.apelido)) = strip_accents(lower(?))""", [termo]).fetchall(),
          "exata", lambda r: f"{r[6]} '{r[7]}'" + (f" ({r[8]})" if r[8] else ""))
    # 2. CNPJ ou código CVM
    digitos = re.sub(r"\D", "", termo)
    if len(digitos) >= 4:
        juntar(con.execute(f"""WITH b AS ({BUSCA}) SELECT {cols} FROM b JOIN empresas e USING (cnpj)
            WHERE regexp_replace(b.cnpj, '\\D', '', 'g') LIKE '%' || ? || '%' OR ltrim(e.cd_cvm, '0') = ltrim(?, '0')""",
                           [digitos, digitos]).fetchall(), "exata", lambda r: "CNPJ ou código CVM")
    # 2b. CNPJ inteiro de agente que não é companhia da CVM: é um CNPJ que este mesmo buscar_empresa devolve (passo 5),
    #     e sem isto ele voltava do passo 7 como "nome parecido" de outra empresa
    if not achados and len(digitos) == 14:
        juntar(_fora_da_cvm(con, "regexp_replace(cnpj, '\\D', '', 'g') = ?", [digitos], limite),
               "exata", lambda r: _como_fora("CNPJ", r))
    # 3. todas as palavras no nome social, comercial ou apelidos
    palavras = [p for p in re.split(r"[^\w]+", termo) if len(p) > 1]
    if palavras:
        conds = " AND ".join(["b.busca LIKE '%' || strip_accents(lower(?)) || '%'"] * len(palavras))
        juntar(con.execute(f"""WITH b AS ({BUSCA}) SELECT {cols} FROM b WHERE {conds}
            ORDER BY (b.anos_com_demonstracoes <> 'não') DESC, (b.situacao = 'ATIVO') DESC, length(b.nome_social)
            LIMIT ?""", palavras + [limite]).fetchall(), "nome", lambda r: "palavras do nome")
    # 4. sigla ou razão social do cadastro da ANEEL ("Light SESA", "Equatorial PA"): acha a concessão que não tem
    #    apelido de mercado, antes de o passo 5 cair na holding do grupo
    if not achados:
        juntar(con.execute(f"""WITH b AS ({BUSCA}) SELECT ag.cnpj, coalesce(b.nome_social, ag.razao_social),
                   b.nome_comercial, coalesce(b.situacao, CASE WHEN ag.ativo THEN 'ATIVO na ANEEL' ELSE 'INATIVO na ANEEL' END),
                   b.tickers, coalesce(b.anos_com_demonstracoes, 'não'), ag.sigla, b.nome_social IS NOT NULL
            FROM agentes_aneel ag LEFT JOIN b USING (cnpj)
            WHERE strip_accents(lower(coalesce(ag.sigla, ''))) = strip_accents(lower(?))
               OR strip_accents(lower(ag.razao_social)) = strip_accents(lower(?))
            ORDER BY b.nome_social IS NULL, ag.ativo DESC LIMIT ?""", [termo, termo, limite]).fetchall(),
               "exata", lambda r: f"sigla '{r[6]}' do cadastro da ANEEL"
                                  + ("" if r[7] else "; agente sem registro na CVM, não tem demonstrações"))
    # 5. palavras do termo no nome completo do universo fora da CVM: "Energisa Tocantins", "Energisa Acre" e
    #    "Energisa Borborema" são concessões sem apelido de mercado e sem registro na CVM, e caíam no passo 6
    #    devolvendo o CNPJ da holding do grupo (ENERGISA SA) como se fosse o da distribuidora
    if not achados and palavras:
        juntar(_fora_da_cvm(con, " AND ".join([PALAVRA_INTEIRA] * len(palavras)), palavras, limite),
               "nome", lambda r: _como_fora("palavras do nome", r))
    # 6. termo que contém um apelido inteiro ("Neoenergia Coelba" -> Coelba): subsidiária antes da holding, depois o mais longo
    if not achados:
        juntar(con.execute(f"""WITH b AS ({BUSCA}) SELECT {cols}, ap.tipo, ap.apelido, ap.observacao
            FROM empresas_apelidos ap JOIN b USING (cnpj)
            WHERE length(ap.apelido) >= 4 AND regexp_matches(' ' || strip_accents(lower(?)) || ' ',
                  '[^a-z0-9]' || regexp_escape(strip_accents(lower(ap.apelido))) || '[^a-z0-9]')
            ORDER BY coalesce(ap.observacao, '') LIKE 'holding%', length(ap.apelido) DESC LIMIT ?""", [termo, limite]).fetchall(),
               "nome", lambda r: f"o termo contém o {r[6]} '{r[7]}'" + (f" ({r[8]})" if r[8] else ""))
    # 7. nada encontrado: nomes parecidos, marcados como aproximados
    if not achados:
        juntar(con.execute(f"""WITH b AS ({BUSCA}) SELECT {cols} FROM b
            ORDER BY jaro_winkler_similarity(b.busca, strip_accents(lower(?))) DESC LIMIT 3""", [termo]).fetchall(),
               "aproximada", lambda r: "nome parecido; NÃO confirmado")
    return achados[:limite]


def _controladas(con, cnpj: str) -> list[str]:
    """Empresas do grupo cuja holding na CVM é esse CNPJ. Sem isso, um termo que só contém o apelido da holding
    ("Light SESA" -> apelido "Light") devolvia a holding calada, e os números da concessão ficavam em outro CNPJ."""
    return [f"{nome} ({c})" for c, nome in con.execute(
        """SELECT cnpj, any_value(agente) FROM grupos_economicos WHERE cnpj_holding_cvm = ? AND cnpj <> ?
           GROUP BY cnpj ORDER BY 2""", [cnpj, cnpj]).fetchall()]


@mcp.tool()
def buscar_empresa(termo: str, limite: int = 8) -> dict:
    """Encontra o CNPJ de empresas do setor elétrico por nome, apelido de mercado (Eletrobras, Taesa, Enel SP), nome
    antigo, ticker da B3 (TAEE11, CMIG4), CNPJ ou código CVM. Acha também a concessão que não é companhia da CVM
    (Energisa Tocantins, Sulgipe), pelo cadastro da ANEEL e por grupos_economicos: nesses casos anos_com_demonstracoes
    vem "não" e não há linha em kpis_financeiros. Devolve cnpj, nomes, tickers, anos com demonstrações financeiras e a
    confiança do resultado (exata, nome ou aproximada). Filtre as outras tabelas pelo cnpj."""
    con = _con()
    try:
        achados = _buscar(con, termo, limite)
        # o termo não bateu exato: se o que veio é a holding de um grupo, diga quais são as empresas dele
        do_grupo = _controladas(con, achados[0]["cnpj"]) if achados and achados[0]["confianca"] != "exata" else []
    finally:
        con.close()
    resposta = {"resultados": achados}
    if do_grupo:
        resposta["aviso_holding"] = (f"{achados[0]['nome_social']} é a holding do grupo na CVM; a concessão tem CNPJ "
                                     f"próprio. Empresas do grupo na base: {'; '.join(do_grupo[:10])}"
                                     + (f" (e outras {len(do_grupo) - 10})" if len(do_grupo) > 10 else ""))
    if achados and achados[0]["confianca"] == "aproximada":
        resposta["aviso"] = (f"Nenhuma empresa com '{termo}' no nome, apelido ou ticker. Os resultados são só nomes "
                             "parecidos: não use sem confirmar com o usuário.")
    elif len(achados) > 1 and achados[0]["confianca"] != "exata":
        resposta["aviso"] = "Mais de uma empresa combina com o termo: confira holding x subsidiária antes de escolher."
    return resposta


CONTAS_DRE = ("3.01", "3.02", "3.03", "3.04", "3.05")
TOLERANCIA_DRE = 0.005  # 0,5% da receita: abaixo disso a diferença é arredondamento da própria demonstração


def _incoerencias_dre(contas: dict[str, float]) -> list[str]:
    """Incoerências na DRE da CVM de um período (contas: {cd_conta: valor}). Duas famílias:
    - sinal: a convenção da CVM é custo negativo. Com 3.02 positivo o erro sobe para o resultado bruto e para o EBIT e
      as somas continuam fechando (Equatorial Pará 2025: 12.223.744 + 8.846.555 = 21.070.299), ou seja, checar a soma
      não pega o caso; o que pega é 3.02 > 0 e o resultado bruto acima da receita.
    - soma: 3.03 = 3.01 + 3.02 e 3.05 = 3.03 + 3.04, que quebram quando a empresa não envia uma das contas.
    EBIT acima da receita de propósito não entra: em holding é o normal (equivalência patrimonial em 3.04.06)."""
    receita, custo, bruto, oper, ebit = (contas.get(c) for c in CONTAS_DRE)
    folga = TOLERANCIA_DRE * max(abs(receita or 0), 1)
    problemas = []
    if custo is not None and custo > 0:
        problemas.append(f"a conta 3.02 (custo dos bens e serviços) veio positiva ({custo:.0f}); na CVM custo é negativo")
    if None not in (receita, bruto) and bruto > receita:
        problemas.append(f"o resultado bruto 3.03 ({bruto:.0f}) passa a receita 3.01 ({receita:.0f})")
    if None not in (receita, custo, bruto) and abs(bruto - (receita + custo)) > folga:
        problemas.append(f"3.03 ({bruto:.0f}) não fecha com 3.01 + 3.02 ({receita + custo:.0f})")
    if None not in (bruto, oper, ebit) and abs(ebit - (bruto + oper)) > folga:
        problemas.append(f"3.05 ({ebit:.0f}) não fecha com 3.03 + 3.04 ({bruto + oper:.0f})")
    if problemas:
        if custo is not None and custo > 0 and receita is not None:
            problemas.append(f"com 3.02 negativo o EBIT do período seria {receita - abs(custo) + (oper or 0):.0f}")
        problemas.append("não use o EBIT, o EBITDA nem as margens deste período sem conferir na demonstração original")
    return problemas


def _ressalvas_dre(con, cnpj: str, periodos: list[tuple[int, str]]) -> list[str]:
    """Roda a checagem de sinal nas contas da CVM dos períodos que alimentam os indicadores devolvidos."""
    contas: dict[tuple, dict] = {}
    for ano, escopo, conta, valor in con.execute(
            f"""SELECT ano, escopo, cd_conta, valor_brl FROM contas_cvm WHERE cnpj = ?
                AND cd_conta IN ({', '.join('?' * len(CONTAS_DRE))}) ORDER BY versao""",
            [cnpj, *CONTAS_DRE]).fetchall():
        contas.setdefault((ano, escopo), {})[conta] = valor
    return [f"{ano} ({escopo}): {p}" for ano, escopo in sorted(set(periodos))
            for p in _incoerencias_dre(contas.get((ano, escopo), {}))]


@mcp.tool()
def indicadores_financeiros(empresa: str, ano_inicial: int | None = None, ano_final: int | None = None,
                            trimestres: int = 4) -> dict:
    """Indicadores financeiros de uma empresa direto das demonstrações da CVM, em reais: os anuais (DFP, 2020 em
    diante: receita, EBIT, EBITDA calculado, lucro, dívida bruta e líquida, caixa, investimento, dividendos, margens,
    dívida líquida/EBITDA, cobertura de juros, ROE) e os trimestres mais recentes (ITR: trimestre, acumulado no ano e
    últimos 12 meses), com a fonte de cada período. empresa aceita nome, apelido, ticker ou CNPJ; trimestres é quantos
    ITR devolver, do mais recente para o mais antigo (4 por padrão, até 40)."""
    con = _con()
    try:
        achados = _buscar(con, empresa, 5)
        if not achados or achados[0]["confianca"] == "aproximada":
            return {"erro": f"não achei a empresa '{empresa}'", "parecidas": achados}
        if achados[0]["confianca"] != "exata" and len(achados) > 1:
            return {"erro": "mais de uma empresa combina; chame de novo com o cnpj", "candidatas": achados}
        alvo = achados[0]
        cur = con.execute("""SELECT * EXCLUDE (cnpj) FROM kpis_financeiros WHERE cnpj = ?
            AND ano BETWEEN coalesce(?, 0) AND coalesce(?, 9999) ORDER BY ano""", [alvo["cnpj"], ano_inicial, ano_final])
        anos = _linhas(cur)
        pedidos = max(1, min(int(trimestres), MAX_TRIMESTRES))
        itr = _linhas(con.execute("""SELECT ano, trimestre, data_referencia, receita_liquida_trimestre_brl,
            lucro_trimestre_brl, receita_liquida_12m_brl, ebitda_12m_brl, lucro_12m_brl, divida_bruta_brl, divida_liquida_brl,
            divida_liquida_ebitda_12m, investimento_acumulado_brl, fonte
            FROM kpis_trimestrais WHERE cnpj = ? ORDER BY data_referencia DESC LIMIT ?""", [alvo["cnpj"], pedidos]))
        na_base = con.execute("SELECT count(*) FROM kpis_trimestrais WHERE cnpj = ?", [alvo["cnpj"]]).fetchone()[0]
        ressalvas = _ressalvas_dre(con, alvo["cnpj"], [(a["ano"], a["escopo"]) for a in anos])
    finally:
        con.close()
    return {
        "empresa": {k: alvo[k] for k in ("cnpj", "nome_social", "tickers", "como_encontrou")},
        "unidade": "R$ (reais); *_pct em %; divida_liquida_ebitda e cobertura_juros_ebitda em vezes",
        "anos": anos or "sem demonstrações na base para esses anos",
        "trimestres_recentes": itr or "sem ITR na base para esta empresa",
        "trimestres_na_base": na_base,
        **({"ressalvas_cvm": ressalvas} if ressalvas else {}),
        **({"aviso_trimestres": f"mostrando os {len(itr)} ITR mais recentes de {na_base}; para os outros chame de novo "
                                f"com trimestres={min(na_base, MAX_TRIMESTRES)}"} if na_base > len(itr) else {}),
        "observacoes": ["EBITDA = EBIT (conta 3.05) + depreciação e amortização da DFC; pode diferir do EBITDA ajustado "
                        "divulgado pela empresa",
                        "Dívida bruta = empréstimos, financiamentos e debêntures (2.01.04 + 2.02.01), sem arrendamentos",
                        "Os trimestres (ITR) são o dado mais recente; o 4º trimestre de cada ano está só na DFP anual. "
                        "Nos trimestres, *_12m_brl somam os últimos 12 meses",
                        "Investimento: use investimento_total_brl. capex_brl é só o caixa de investimento (6.02); nas "
                        "concessões (IFRS 15 / ICPC 01) a obra aparece em custo_construcao_concessao_brl"],
    }


# ------------------------------------------------------------------------------------------------ catálogo
PRIMEIRA_FRASE = re.compile(r"(?s)^.{0,180}?[.;](?=\s|$)")


def _resumo(texto: str) -> str:
    """Primeira frase da descrição; o resto fica em descrever_tabela. Se a frase não couber, o corte é marcado."""
    t = " ".join((texto or "").split())
    m = PRIMEIRA_FRASE.match(t)
    if m:
        return m.group(0)
    return (t[:180].rsplit(" ", 1)[0] + " [...]") if len(t) > 180 else t


@mcp.tool()
def listar_tabelas(detalhe: bool = False) -> dict:
    """Índice das tabelas da base: nome, número de linhas e a primeira frase da descrição. Com detalhe=True devolve a
    descrição, a fonte e as ressalvas inteiras de todas as tabelas (resposta longa); descrever_tabela traz isso de uma
    tabela só, com as colunas."""
    con = _con()
    try:
        linhas = _linhas(con.execute("SELECT tabela, descricao, fonte, ressalvas, linhas FROM catalogo ORDER BY tabela"))
    finally:
        con.close()
    if detalhe:
        return {"tabelas": len(linhas), "catalogo": linhas}
    return {"tabelas": len(linhas),
            "catalogo": [{"tabela": t["tabela"], "linhas": t["linhas"], "resumo": _resumo(t["descricao"])}
                         for t in linhas],
            "como_usar": "resumo é só a primeira frase da descrição: a fonte, as ressalvas e as colunas de uma tabela "
                         "vêm de descrever_tabela('nome'), e as de todas de listar_tabelas(detalhe=True). Leia as "
                         "ressalvas antes de usar os números."}


@mcp.tool()
def descrever_tabela(tabela: str) -> dict:
    """Mostra as colunas (nome e tipo), a descrição, as ressalvas e 3 linhas de exemplo de uma tabela."""
    con = _con()
    try:
        ident = _ident(tabela, _tabelas(con))
        colunas = [{"coluna": r[0], "tipo": r[1]} for r in con.execute(f"DESCRIBE SELECT * FROM {ident}").fetchall()]
        info = con.execute("SELECT descricao, fonte, ressalvas FROM catalogo WHERE tabela = ?", [tabela]).fetchone()
        return {"tabela": tabela, "descricao": info[0] if info else "", "fonte": info[1] if info else "",
                "ressalvas": info[2] if info else "", "colunas": colunas,
                "exemplo": _linhas(con.execute(f"SELECT * FROM {ident} LIMIT 3"))}
    finally:
        con.close()


@mcp.tool()
def valores_distintos(tabela: str, coluna: str, contem: str | None = None, limite: int = 30) -> list[dict]:
    """Lista os valores distintos de uma coluna com a contagem, opcionalmente só os que contêm um texto (sem
    diferenciar acentos). Use para acertar o filtro antes de consultar (ex.: fase, origem, distribuidora, cd_conta)."""
    con = _con()
    try:
        t = _ident(tabela, _tabelas(con))
        c = _ident(coluna, [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM {t}").fetchall()])
        where, params = "", []
        if contem:
            where = f"WHERE strip_accents(lower(CAST({c} AS VARCHAR))) LIKE '%' || strip_accents(lower(?)) || '%'"
            params.append(contem)
        rows = con.execute(f"SELECT CAST({c} AS VARCHAR) AS valor, count(*) AS n FROM {t} {where} "
                           "GROUP BY 1 ORDER BY n DESC LIMIT ?", params + [limite]).fetchall()
        return [{"valor": v, "linhas": n} for v, n in rows]
    finally:
        con.close()


# ------------------------------------------------------------------------------------------------ SQL
RUIDO = re.compile(r"(?s)('(?:[^']|'')*')|(\$\$.*?\$\$)|(/\*.*?\*/)|(--[^\n]*)")


def _sem_ruido(sql: str) -> str:
    """SQL sem comentários, com os literais vazios. Uma varredura só, para um '--' dentro de aspas não comer a linha."""
    return RUIDO.sub(lambda m: "''" if m.group(1) or m.group(2) else " ", sql)


NUMERICOS = {"TINYINT","SMALLINT", "INTEGER", "BIGINT", "HUGEINT", "UTINYINT", "USMALLINT", "UINTEGER", "UBIGINT",
             "DECIMAL", "FLOAT", "DOUBLE"}


def _constante(item):
    """Valor de uma constante numérica (também sob CAST ou sinal de menos); None se o item não for isso."""
    if item.get("class") == "CAST" and item.get("child"):
        return _constante(item["child"])
    if item.get("class") == "FUNCTION" and item.get("function_name") == "-" and len(item.get("children", [])) == 1:
        v = _constante(item["children"][0])
        return -v if v is not None else None
    if item.get("class") != "CONSTANT":
        return None
    valor = item.get("value") or {}
    tipo = (valor.get("type") or {}).get("id")
    if tipo not in NUMERICOS or valor.get("is_null"):
        return None
    v = float(valor.get("value"))
    if tipo == "DECIMAL":
        v /= 10 ** (valor["type"].get("type_info") or {}).get("scale", 0)
    return v


def _analisar(no, ctes, tabelas, digitados):
    if isinstance(no, dict):
        if no.get("type") == "BASE_TABLE" and no.get("table_name"):
            tabelas.add(no["table_name"].lower())
        for item in (no.get("cte_map") or {}).get("map", []) if isinstance(no.get("cte_map"), dict) else []:
            ctes.add(str(item.get("key", "")).lower())
        itens = list(no.get("select_list") or [])
        if no.get("type") == "EXPRESSION_LIST":
            itens += [x for linha in no.get("values", []) for x in linha]
        for item in itens:
            v = _constante(item) if isinstance(item, dict) else None
            if v is not None and abs(v) >= 10000:
                digitados.append(v)
        for v in no.values():
            _analisar(v, ctes, tabelas, digitados)
    elif isinstance(no, list):
        for v in no:
            _analisar(v, ctes, tabelas, digitados)


@mcp.tool()
def consultar_sql(sql: str, limite: int = LIMITE_LINHAS) -> dict:
    """Executa uma consulta SQL (DuckDB, só SELECT ou WITH) na base e devolve as linhas (até 200). Filtre empresas
    pelo cnpj de buscar_empresa. Recusa consultas que não leem nenhuma tabela ou que digitam valores numéricos
    (os números precisam vir da base)."""
    texto = sql.strip().rstrip(";").strip()
    # a checagem olha o SQL sem comentários nem literais: senão um "-- nota" antes do SELECT ou um ';' dentro de
    # aspas derrubavam uma consulta válida
    limpo = _sem_ruido(texto).strip().rstrip(";").strip()
    if not re.match(r"(?is)^(select|with|from|\()", limpo) or ";" in limpo:
        return {"erro": "só uma consulta de leitura por vez (SELECT ou WITH; comentários -- e /* */ são aceitos)"}
    con = _con()
    try:
        arvore = json.loads(con.execute("SELECT json_serialize_sql(?)", [texto]).fetchone()[0])
        if arvore.get("error"):
            return {"erro": f"SQL inválido: {arvore.get('error_message')}"}
        ctes, tabelas, digitados = set(), set(), []
        _analisar(arvore, ctes, tabelas, digitados)
        reais = sorted((tabelas - ctes) & {t.lower() for t in _tabelas(con)})
        if not reais:
            return {"erro": "a consulta não lê nenhuma tabela da base. Os números da resposta precisam vir das tabelas; "
                            "use listar_tabelas para ver o que existe."}
        if digitados:
            return {"erro": f"a consulta digita valores numéricos ({', '.join(f'{v:g}' for v in digitados[:5])}) em vez de "
                            "lê-los da base. Refaça lendo as colunas das tabelas."}
        relogio = threading.Timer(TEMPO_MAXIMO_S, con.interrupt)
        relogio.start()
        try:
            cur = con.execute(texto)
            linhas = _linhas(cur, max(1, min(limite, LIMITE_LINHAS)) + 1)
        except duckdb.InterruptException:
            return {"erro": f"a consulta passou de {TEMPO_MAXIMO_S} s; filtre mais ou agregue"}
        except duckdb.Error as e:
            return {"erro": str(e).split("\n")[0][:500], "dica": "confira nomes de colunas com descrever_tabela"}
        finally:
            relogio.cancel()
        cortada = len(linhas) > limite
        return {"tabelas_usadas": reais, "linhas": linhas[:limite], "total_mostrado": min(len(linhas), limite),
                **({"aviso": f"resultado cortado em {limite} linhas; agregue ou filtre"} if cortada else {}),
                **({"aviso": "nenhuma linha: revise o filtro (valores_distintos) antes de concluir que o dado não existe"}
                   if not linhas else {})}
    finally:
        con.close()


if __name__ == "__main__":
    mcp.run()

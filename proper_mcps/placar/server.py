"""Servidor MCP "energynexus-placar": consulta o Placar da Transição (dados ESG extraídos dos relatórios para
data/placar.duckdb) e cruza com o banco estruturado (data/energynexus.duckdb) para métricas híbridas, radar de
consistência (anti-greenwashing) e exposição a preço de carbono. Também monta as telas (artefato HTML
autocontido em .runtime/relatorios, aberto em /relatorios/) do ranking, do radar e da exposição a carbono.

Todo valor de ESG traz arquivo, página e a confiança da extração; todo valor financeiro/operacional traz a tabela
de origem. As ferramentas só usam ESG com confianca > 0 (checado contra a página na extração).
"""
import json
import os
import secrets
from datetime import datetime
from html import escape

import duckdb
from mcp.server.mcpserver import MCPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLACAR = os.path.join(RAIZ, "data", "placar.duckdb")
ENERGYNEXUS = os.path.join(RAIZ, "data", "energynexus.duckdb")

# fontes de geração consideradas renováveis (SIGA/ANEEL): hídrica, eólica, solar, biomassa
RENOVAVEL = ("UHE", "PCH", "CGH", "EOL", "UFV", "BIO")

INSTRUCOES = """Use o energynexus-placar para o Placar da Transição (ESG estruturado dos relatórios, já com página e
confiança) e para três análises que cruzam relatório × dados oficiais:
- consultar_placar(empresa[, ano]): emissões por escopo, metas, % renovável, CAPEX, frameworks e o score de
  divulgação de uma empresa, com métricas híbridas (tCO2e/receita, CAPEX/receita) — cada número com sua fonte.
- placar_ranking(metrica[, ano]): ranking comparativo entre empresas (metrica: intensidade_receita,
  score_divulgacao, escopo1_2, pct_renovavel).
- radar_consistencia(empresa): alertas anti-greenwashing (afirmação do relatório × SIGA/DFP), com severidade e as
  duas evidências.
- exposicao_carbono(preco_por_t[, escopos]): emissões × preço de carbono contra lucro e EBITDA, com a fórmula.
Quando o usuário quiser VER, comparar visualmente ou compartilhar, monte a tela e mande o link: tela_ranking,
tela_radar e tela_carbono gravam um HTML autocontido (barras com o valor em cada barra, tabela com a fonte de cada
número; na de carbono o preço é uma barra deslizante que recalcula na hora). A tela não substitui a resposta: diga no
texto o essencial e cite as fontes.
Cite sempre a fonte que a ferramenta devolve (documento e página, ou tabela). Se uma empresa não estiver na base de
relatórios, diga; o placar cobre só as empresas com relatório indexado."""

mcp = MCPServer("energynexus-placar", instructions=INSTRUCOES)


def _con():
    con = duckdb.connect(PLACAR, read_only=True)
    # IF NOT EXISTS: o servidor atende chamadas concorrentes e o catálogo do banco é compartilhado no processo;
    # sem isso, um segundo ATTACH simultâneo falharia com "fin já existe".
    con.execute(f"ATTACH IF NOT EXISTS '{ENERGYNEXUS}' AS fin (READ_ONLY)")
    return con


def _filtro_empresa(alias: str, empresa: str | None):
    if not empresa:
        return "TRUE", []
    return (f"(strip_accents(lower({alias}.empresa)) LIKE '%' || strip_accents(lower(?)) || '%' "
            f"OR regexp_replace(coalesce({alias}.cnpj,''),'\\D','','g') = regexp_replace(?,'\\D','','g'))",
            [empresa.strip(), empresa.strip()])


def _fonte_paginas(linhas: list[dict]) -> str:
    """Fonte de um número agregado: os documentos e as páginas de onde saíram as parcelas."""
    por = {}
    for l in linhas:
        por.setdefault(l["arquivo"], set()).add(l["pagina"])
    return "; ".join(f"{a} p.{', '.join(str(p) for p in sorted(ps))}" for a, ps in sorted(por.items()))


def _fin_ano(con, cnpj: str, ano: int) -> dict | None:
    """Financeiro consolidado da entidade cujo CNPJ casa (por dígitos) com o do relatório, no ano (ou o último antes)."""
    r = con.execute("""
        SELECT empresa, ano, receita_liquida_brl, ebitda_brl, lucro_liquido_brl, investimento_total_brl
        FROM fin.kpis_financeiros
        WHERE escopo='consolidado' AND regexp_replace(cnpj,'\\D','','g')=regexp_replace(?,'\\D','','g') AND ano<=?
        ORDER BY ano DESC LIMIT 1""", [cnpj or "", int(ano)]).fetchone()
    if not r:
        return None
    return dict(zip(("empresa", "ano", "receita", "ebitda", "lucro", "investimento"), r))


def _emissoes(con, empresa, ano) -> list[dict]:
    cond, params = _filtro_empresa("e", empresa)
    ano_cond = "AND e.ano_relatorio = ?" if ano else ""
    if ano:
        params = params + [int(ano)]
    linhas = con.execute(f"""
        SELECT e.empresa, e.cnpj, e.ano_relatorio, e.escopo, e.tco2e, e.intensidade, e.unidade_intensidade,
               e.arquivo, e.pagina
        FROM esg_emissoes e WHERE {cond} {ano_cond} AND e.confianca > 0
        QUALIFY row_number() OVER (PARTITION BY e.cnpj, e.ano_relatorio, e.escopo
                                   ORDER BY e.tco2e DESC NULLS LAST) = 1
        ORDER BY e.empresa, e.ano_relatorio DESC, e.escopo""", params).fetchall()
    cols = ("empresa", "cnpj", "ano", "escopo", "tco2e", "intensidade", "unidade_intensidade", "arquivo", "pagina")
    return [dict(zip(cols, r)) for r in linhas]


def _ultima_edicao(itens: list[dict], campo_ano: str = "ano") -> list[dict]:
    """Uma edição por empresa: a mais recente. A base indexa o arquivo inteiro (de 2011 em diante), então um ranking
    por empresa-e-ano listaria a mesma empresa uma vez por relatório — a comparação entre empresas usa a divulgação
    vigente de cada uma. Quem pede um ano específico não passa por aqui."""
    maior: dict = {}
    for i in itens:
        chave = i.get("cnpj") or i["empresa"]
        maior[chave] = max(maior.get(chave, 0), i[campo_ano] or 0)
    return [i for i in itens if (i[campo_ano] or 0) == maior[i.get("cnpj") or i["empresa"]]]


def _por_escopo(linhas: list[dict]) -> dict:
    """Uma entrada por escopo (1, 2, 3) para somar sem contar duas vezes: quando o relatório traz o escopo 2 por
    localização e por mercado, fica o de mercado (o que as metas e o GHG Protocol usam para a meta)."""
    saida = {}
    for e in sorted(linhas, key=lambda x: x["escopo"]):   # "2" antes de "2_mercado": o de mercado prevalece
        saida[e["escopo"].replace("_mercado", "")] = e
    return saida


@mcp.tool()
def consultar_placar(empresa: str | None = None, ano: int | None = None) -> dict:
    """Placar da Transição de uma empresa (ou de todas, se empresa=None): emissões por escopo, metas climáticas,
    % renovável, CAPEX e frameworks reportados, com página e confiança, mais métricas híbridas com o financeiro da
    CVM. empresa é nome (Cemig, ISA, Auren...) ou CNPJ; ano é o ano do relatório."""
    con = _con()
    try:
        return _coletar(con, empresa, ano)
    finally:
        con.close()


def _coletar(con, empresa: str | None, ano: int | None) -> dict:
    """Monta o placar reutilizando UMA conexão (para radar/carbono não reabrirem/reanexarem o banco financeiro)."""
    if True:
        emissoes = _emissoes(con, empresa, ano)
        cond, params = _filtro_empresa("t", empresa)
        ano_cond = (" AND t.ano_relatorio = " + str(int(ano))) if ano else ""

        def busca(tabela, campos):
            return [dict(zip(["empresa", "cnpj", "ano_relatorio", *campos, "arquivo", "pagina"], r))
                    for r in con.execute(
                        f"SELECT t.empresa,t.cnpj,t.ano_relatorio,{','.join('t.'+c for c in campos)},t.arquivo,t.pagina "
                        f"FROM {tabela} t WHERE {cond}{ano_cond} AND t.confianca>0", params).fetchall()]

        metas = busca("esg_metas", ["tipo", "ano_alvo", "escopo_coberto", "valor_alvo"])
        renovavel = busca("esg_renovavel", ["pct_capacidade_renovavel", "pct_geracao_renovavel"])
        capex = busca("esg_capex", ["capex_total_brl", "capex_verde_brl", "definicao_verde"])
        frameworks = busca("esg_frameworks", ["framework", "asseguracao_externa", "assegurador"])

        # métricas híbridas por empresa (usa escopo 1+2 e o financeiro consolidado que casa por CNPJ)
        hibridas = []
        chaves = {(e["cnpj"], e["ano"], e["empresa"]) for e in emissoes}
        for cnpj, ano_rel, nome in sorted(chaves, key=lambda x: (x[2], x[1])):
            do_ano = _por_escopo([e for e in emissoes if e["cnpj"] == cnpj and e["ano"] == ano_rel])
            usadas = [do_ano[k] for k in ("1", "2") if k in do_ano]
            e12 = sum(e["tco2e"] or 0 for e in usadas)
            fin = _fin_ano(con, cnpj, ano_rel)
            item = {"empresa": nome, "ano": ano_rel, "escopo1_2_tco2e": round(e12, 1) if e12 else None,
                    "fonte_emissoes": _fonte_paginas(usadas)}
            if fin and fin["receita"]:
                item["tco2e_por_milhao_receita"] = round(e12 / (fin["receita"] / 1e6), 3) if e12 else None
                # investimento vem da CVM (comparável entre empresas); o relatório entra só no recorte "verde"
                item["capex_sobre_receita_pct"] = (round(100 * fin["investimento"] / fin["receita"], 1)
                                                   if fin["investimento"] else None)
                verde = next((c for c in capex if c["cnpj"] == cnpj and c["ano_relatorio"] == ano_rel
                              and c.get("capex_verde_brl")), None)
                if verde:
                    item["capex_verde_brl"] = verde["capex_verde_brl"]
                    item["capex_verde_definicao"] = verde.get("definicao_verde")
                    item["fonte_capex_verde"] = f"{verde['arquivo']} p.{verde['pagina']}"
                item["fonte_financeiro"] = f"kpis_financeiros {fin['empresa']} {fin['ano']} (consolidado)"
            else:
                item["aviso"] = "sem par financeiro na base (CNPJ do relatório não casa com kpis_financeiros)"
            hibridas.append(item)

        scores = _scores(emissoes, metas, renovavel, frameworks)
        return {"emissoes": emissoes, "metas": metas, "renovavel": renovavel, "capex": capex,
                "frameworks": frameworks, "metricas_hibridas": hibridas, "score_divulgacao": scores,
                "aviso": None if emissoes or metas else "empresa sem relatório indexado no placar"}


def _scores(emissoes, metas, renovavel, frameworks) -> list[dict]:
    """Score de maturidade de divulgação (0-100) por empresa/ano: cobertura de escopos + meta + framework + asseguração."""
    def vazio():
        return {"escopos": set(), "meta": False, "fw": set(), "asseg": False, "docs": []}

    por = {}
    for e in emissoes:
        d = por.setdefault((e["empresa"], e["ano"]), vazio())
        d["escopos"].add(e["escopo"].replace("_mercado", ""))
        d["docs"].append(e)
    for m in metas:
        d = por.setdefault((m["empresa"], m["ano_relatorio"]), vazio())
        d["meta"] = True
        d["docs"].append(m)
    for f in frameworks:
        d = por.setdefault((f["empresa"], f["ano_relatorio"]), vazio())
        d["fw"].add(f["framework"])
        d["asseg"] = d["asseg"] or bool(f["asseguracao_externa"])
        d["docs"].append(f)
    saida = []
    for (empresa, ano), d in por.items():
        s = 15 * len(d["escopos"] & {"1", "2", "3"}) + 20 * d["meta"] + min(len(d["fw"]), 3) * 5 + 20 * d["asseg"]
        saida.append({"empresa": empresa, "ano": ano, "score": min(s, 100),
                      "fonte": _fonte_paginas(d["docs"]),
                      "componentes": {"escopos": sorted(d["escopos"]), "tem_meta": d["meta"],
                                      "frameworks": sorted(d["fw"]), "asseguracao_externa": d["asseg"]}})
    return sorted(saida, key=lambda x: -x["score"])


@mcp.tool()
def placar_ranking(metrica: str = "score_divulgacao", ano: int | None = None, limite: int = 15) -> dict:
    """Ranking comparativo entre empresas. metrica: 'score_divulgacao', 'intensidade_receita' (tCO2e escopo 1+2 por
    R$ mi de receita), 'escopo1_2' (tCO2e), 'pct_renovavel'. Devolve as empresas ordenadas, com a fonte de cada número."""
    dados = consultar_placar(None, ano)
    if metrica == "score_divulgacao":
        itens = [{"empresa": s["empresa"], "ano": s["ano"], "valor": s["score"], "unidade": "0-100",
                  "fonte": s["fonte"], "detalhe": s["componentes"]} for s in dados["score_divulgacao"]]
        ordem = True
    elif metrica in ("intensidade_receita", "escopo1_2"):
        campo = "tco2e_por_milhao_receita" if metrica == "intensidade_receita" else "escopo1_2_tco2e"
        itens = [{"empresa": h["empresa"], "ano": h["ano"], "valor": h.get(campo),
                  "unidade": "tCO2e/R$ mi" if metrica == "intensidade_receita" else "tCO2e",
                  "fonte": h["fonte_emissoes"] + (f" ÷ {h['fonte_financeiro']}"
                                                  if metrica == "intensidade_receita" else "")}
                 for h in dados["metricas_hibridas"] if h.get(campo) is not None]
        ordem = True
    elif metrica == "pct_renovavel":
        itens = [{"empresa": r["empresa"], "ano": r["ano_relatorio"],
                  "valor": r.get("pct_geracao_renovavel") or r.get("pct_capacidade_renovavel"), "unidade": "%",
                  "fonte": f"{r['arquivo']} p.{r['pagina']}"} for r in dados["renovavel"]
                 if (r.get("pct_geracao_renovavel") or r.get("pct_capacidade_renovavel")) is not None]
        ordem = True
    else:
        return {"erro": f"métrica '{metrica}' desconhecida",
                "metricas": ["score_divulgacao", "intensidade_receita", "escopo1_2", "pct_renovavel"]}
    if ano is None:
        itens = _ultima_edicao(itens)        # sem ano pedido, a edição mais recente de cada empresa
    itens = sorted(itens, key=lambda x: (x["valor"] is None, -(x["valor"] or 0) if ordem else (x["valor"] or 0)))
    vistas, uma_por_empresa = set(), []      # o relatório repete o mesmo número em várias páginas: fica uma linha
    for i in itens:
        if i["empresa"] not in vistas:
            vistas.add(i["empresa"])
            uma_por_empresa.append(i)
    return {"metrica": metrica, "ranking": uma_por_empresa[:limite],
            "nota": "só empresas com relatório indexado e (para métricas híbridas) CNPJ que casa com a CVM; uma linha "
                    "por empresa" + (", da edição mais recente que traz a métrica" if ano is None else "")}


def _cap_por_fonte(con, cnpj: str) -> dict | None:
    """Capacidade em operação por origem (SIGA), somando MW proporcionais do grupo cujo CNPJ casa por dígitos."""
    linhas = con.execute("""
        SELECT strip_accents(lower(coalesce(origem, tipo_geracao))) AS fonte, sum(potencia_proporcional_mw) mw
        FROM fin.capacidade_por_grupo
        WHERE regexp_replace(cnpj_participante,'\\D','','g') = regexp_replace(?,'\\D','','g')
          AND (fase IS NULL OR strip_accents(lower(fase)) LIKE 'opera%')
        GROUP BY 1 HAVING sum(potencia_proporcional_mw) > 0""", [cnpj or ""]).fetchall()
    if not linhas:
        return None
    ren = {"hidrica", "eolica", "solar", "biomassa"}
    total = sum(mw for _, mw in linhas)
    renovavel = sum(mw for f, mw in linhas if any(r in f for r in ren))
    return {"total_mw": round(total, 1), "renovavel_mw": round(renovavel, 1),
            "pct_renovavel": round(100 * renovavel / total, 1) if total else None}


REGRAS = {"renovavel_vs_siga": "% renovável declarado × capacidade real (SIGA)",
          "meta_ignora_escopo3": "Meta climática e o escopo 3, que é o maior",
          "divulgacao_sem_asseguracao": "Divulgação sem asseguração externa independente"}


@mcp.tool()
def radar_consistencia(empresa: str | None = None) -> dict:
    """Radar anti-greenwashing: confronta afirmações dos relatórios com dados oficiais (SIGA/DFP). Cada alerta traz
    severidade, explicação e as duas evidências (documento/página e tabela). Regras: (1) % renovável declarado ×
    capacidade real no SIGA; (2) meta climática que não cobre o escopo 3 sendo ele o maior; (3) frameworks de
    divulgação sem asseguração externa."""
    con = _con()
    alertas = []
    try:
        placar = _coletar(con, empresa, None)
        emissoes = placar["emissoes"]
        # o radar fala da divulgação vigente: cada regra olha a edição mais recente da empresa (a base tem o arquivo
        # de 2011 em diante, e sem isso o mesmo alerta se repetia uma vez por relatório)
        metas = _ultima_edicao(placar["metas"], "ano_relatorio")
        renovavel = _ultima_edicao(placar["renovavel"], "ano_relatorio")
        frameworks = _ultima_edicao(placar["frameworks"], "ano_relatorio")
        # (1) % renovável × SIGA. Só compara base igual: o SIGA traz CAPACIDADE instalada, então um "% da geração"
        # declarado não entra no confronto (vira ressalva), para não comparar coisas diferentes.
        nao_comparaveis = []
        for r in renovavel:
            afirmado = r.get("pct_capacidade_renovavel")
            if afirmado is None:
                if r.get("pct_geracao_renovavel") is not None:
                    nao_comparaveis.append(
                        f"{r['empresa']} {r['ano_relatorio']}: declara {r['pct_geracao_renovavel']:.0f}% da GERAÇÃO "
                        f"({r['arquivo']} p.{r['pagina']}); o SIGA traz capacidade instalada — bases diferentes, "
                        f"não comparei")
                continue
            cap = _cap_por_fonte(con, r["cnpj"])
            if not cap or cap["pct_renovavel"] is None:
                nao_comparaveis.append(f"{r['empresa']} {r['ano_relatorio']}: sem capacidade em operação no SIGA "
                                       f"para o CNPJ do relatório")
                continue
            gap = afirmado - cap["pct_renovavel"]
            if abs(gap) >= 15:
                alertas.append({
                    "regra": "renovavel_vs_siga", "empresa": r["empresa"], "ano": r["ano_relatorio"],
                    "severidade": "alta" if abs(gap) >= 30 else "media",
                    "explicacao": f"Relatório declara {afirmado:.0f}% renovável, mas a capacidade em operação no SIGA "
                                  f"é {cap['pct_renovavel']:.0f}% renovável ({cap['renovavel_mw']:.0f} de "
                                  f"{cap['total_mw']:.0f} MW). Diferença de {gap:+.0f} pontos.",
                    "valor_afirmado": afirmado, "valor_oficial": cap["pct_renovavel"],
                    "evidencia_doc": f"{r['arquivo']} p.{r['pagina']}",
                    "evidencia_dado": "capacidade_por_grupo (SIGA/ANEEL)"})
        # (2) meta sem escopo 3, sendo ele o maior
        for m in metas:
            if m["tipo"] not in ("net_zero", "reducao_absoluta") or "3" in str(m.get("escopo_coberto") or ""):
                continue
            do_ano = _por_escopo([e for e in emissoes if e["empresa"] == m["empresa"]
                                  and e["ano"] == m["ano_relatorio"]])
            e3 = do_ano.get("3")
            e12 = sum(do_ano[k]["tco2e"] or 0 for k in ("1", "2") if k in do_ano)
            if e3 and (e3["tco2e"] or 0) > e12 > 0:
                # a meta diz quais escopos cobre e o 3 não está lá? é divergência. Se a meta extraída não diz nada
                # sobre escopo, a falha pode ser da leitura — vira alerta fraco, para conferir no relatório.
                declarou = bool(str(m.get("escopo_coberto") or "").strip())
                alertas.append({
                    "regra": "meta_ignora_escopo3", "empresa": m["empresa"], "ano": m["ano_relatorio"],
                    "severidade": "media" if declarou else "baixa",
                    "explicacao": f"Meta {m['tipo']} (alvo {m.get('ano_alvo')}) "
                                  + (f"cobre '{m['escopo_coberto']}' e deixa de fora o escopo 3" if declarou
                                     else "não diz, na página lida, quais escopos cobre — confira no relatório")
                                  + f", mas o escopo 3 ({e3['tco2e']:.0f} tCO2e) é maior que escopo 1+2 "
                                    f"({e12:.0f} tCO2e).",
                    "valor_afirmado": f"meta sem escopo 3", "valor_oficial": f"escopo 3 = {e3['tco2e']:.0f} tCO2e",
                    "evidencia_doc": f"meta: {m['arquivo']} p.{m['pagina']}; escopo 3: {e3['arquivo']} p.{e3['pagina']}",
                    "evidencia_dado": "esg_emissoes / esg_metas (relatório)"})
        # (3) frameworks sem asseguração
        por_emp = {}
        for f in frameworks:
            d = por_emp.setdefault((f["empresa"], f["ano_relatorio"]), {"fw": set(), "asseg": False, "f": f})
            d["fw"].add(f["framework"]); d["asseg"] = d["asseg"] or bool(f["asseguracao_externa"])
        for (emp, ano), d in por_emp.items():
            if d["fw"] and not d["asseg"]:
                alertas.append({
                    "regra": "divulgacao_sem_asseguracao", "empresa": emp, "ano": ano, "severidade": "baixa",
                    "explicacao": f"Divulga por {', '.join(sorted(d['fw']))} mas o relatório não indica asseguração "
                                  f"externa independente dos dados.",
                    "valor_afirmado": ", ".join(sorted(d["fw"])), "valor_oficial": "sem asseguração externa citada",
                    "evidencia_doc": f"{d['f']['arquivo']} p.{d['f']['pagina']}", "evidencia_dado": "esg_frameworks"})
        vistos, unicos = set(), []   # um alerta por (regra, empresa, ano)
        for a in alertas:
            chave = (a["regra"], a["empresa"], a["ano"])
            if chave not in vistos:
                vistos.add(chave)
                unicos.append(a)
        alertas = unicos
        ordem = {"alta": 0, "media": 1, "baixa": 2}
        alertas.sort(key=lambda a: ordem[a["severidade"]])
        for a in alertas:
            a["titulo"] = REGRAS[a["regra"]]
        return {"alertas": alertas, "total": len(alertas), "nao_comparaveis": nao_comparaveis,
                "nota": "alertas indicam divergência a investigar, não fraude; confira as duas evidências citadas. "
                        "O que está em nao_comparaveis não virou alerta porque a base do número declarado é outra "
                        "(geração × capacidade) ou falta o dado oficial."}
    finally:
        con.close()


@mcp.tool()
def exposicao_carbono(preco_por_t: float = 100.0, escopos: list[str] | None = None) -> dict:
    """Exposição a preço de carbono: emissões (escopos escolhidos) × preço em R$/t, contra lucro líquido e EBITDA.
    preco_por_t em R$/tCO2e (ajuste à vontade); escopos padrão ['1','2']. Ranking por % do EBITDA. Fórmula visível."""
    escopos = escopos or ["1", "2"]
    con = _con()
    try:
        emissoes = _emissoes(con, None, None)
        por_empresa: dict = {}
        for e in emissoes:
            # por nome, não por CNPJ: edições de anos diferentes da mesma empresa podem trazer CNPJ diferente, e o
            # ranking mostra o nome (o CNPJ sai da edição escolhida, para casar com o financeiro daquele ano)
            por_empresa.setdefault(e["empresa"], {}).setdefault(e["ano"], []).append(e)
        itens = []
        for nome, anos in por_empresa.items():
            # uma linha por empresa: a edição mais recente que traz os escopos pedidos e, se nenhuma traz todos, a
            # mais recente que traz algum (com o aviso de escopo faltando)
            escolhida = None
            for ano in sorted(anos, reverse=True):
                do_ano = _por_escopo(anos[ano])
                tem = [k for k in escopos if k in do_ano]
                if len(tem) == len(escopos):
                    escolhida = ano
                    break
                if tem and escolhida is None:
                    escolhida = ano
            if escolhida is None:
                continue
            ano, linhas = escolhida, anos[escolhida]
            cnpj = linhas[0]["cnpj"]
            do_ano = _por_escopo(linhas)
            usadas = [do_ano[k] for k in escopos if k in do_ano]
            tco2e = sum(e["tco2e"] or 0 for e in usadas)
            fin = _fin_ano(con, cnpj, ano)
            exposicao = tco2e * preco_por_t
            faltando = [k for k in escopos if k not in do_ano]
            item = {"empresa": nome, "cnpj": cnpj, "ano": ano, "escopos": escopos,
                    "escopos_sem_valor": faltando, "tco2e": round(tco2e, 1),
                    "exposicao_brl": round(exposicao, 0),
                    "formula": f"{tco2e:.0f} tCO2e × R$ {preco_por_t:.0f}/t = R$ {exposicao/1e6:.1f} mi",
                    "fonte_emissoes": _fonte_paginas(usadas)}
            if faltando:
                item["aviso_escopo"] = (f"o relatório indexado não traz escopo {', '.join(faltando)}: o valor cobre "
                                        f"só o escopo {', '.join(k for k in escopos if k not in faltando)}")
            if fin and fin["ebitda"]:
                item["pct_ebitda"] = round(100 * exposicao / fin["ebitda"], 1)
                item["pct_lucro"] = round(100 * exposicao / fin["lucro"], 1) if fin["lucro"] else None
                item["fonte_financeiro"] = f"kpis_financeiros {fin['empresa']} {fin['ano']}"
            else:
                item["aviso"] = "sem financeiro correspondente na base"
            itens.append(item)
        itens.sort(key=lambda x: (x.get("pct_ebitda") is None, -(x.get("pct_ebitda") or 0)))
        return {"preco_por_t": preco_por_t, "escopos": escopos, "ranking": itens,
                "nota": "exposição teórica se as emissões dos escopos escolhidos fossem precificadas; "
                        "compara com EBITDA e lucro do mesmo grupo na CVM"}
    finally:
        con.close()


# ------------------------------------------------------------------ telas: artefato HTML autocontido
# O iniciar.sh liga .runtime/relatorios em client/public/assets/relatorios: o navegador abre em /relatorios/<nome>.
PASTA = os.path.join(RAIZ, ".runtime", "relatorios")
URL_BASE = "/relatorios"

# Tokens do tema do chat (client/src/style.css): claro em branco, escuro no roxo do EnergyNexus. A série usa o violeta
# da marca (contraste acima de 3:1 nas duas superfícies); severidade traz ícone e rótulo, nunca só a cor.
CSS = """
:root{color-scheme:light;--fundo:#f7f7f8;--sup:#fff;--ink:#212121;--ink2:#424242;--mudo:#595959;
--linha:#e3e3e3;--serie:#7c3aed;--trilha:#ede9fe;--alta:#d03b3b;--media:#c2410c;--baixa:#595959}
@media (prefers-color-scheme:dark){:root:where(:not([data-tema="claro"])){color-scheme:dark;--fundo:#120a1f;
--sup:#1a1029;--ink:#ececec;--ink2:#cdcdcd;--mudo:#9d8bbd;--linha:#2e1d47;--serie:#ab68ff;--trilha:#2e1d47;
--alta:#f87171;--media:#ec835a;--baixa:#9d8bbd}}
:root[data-tema="escuro"]{color-scheme:dark;--fundo:#120a1f;--sup:#1a1029;--ink:#ececec;--ink2:#cdcdcd;
--mudo:#9d8bbd;--linha:#2e1d47;--serie:#ab68ff;--trilha:#2e1d47;--alta:#f87171;--media:#ec835a;--baixa:#9d8bbd}
*{box-sizing:border-box}
body{margin:0;padding:32px 16px 48px;background:var(--fundo);color:var(--ink);
font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:920px;margin:0 auto}
h1{font-size:23px;margin:0 0 4px;letter-spacing:-.01em}
.sub{color:var(--ink2);margin:0 0 24px;font-size:14px}
.cartao{background:var(--sup);border:1px solid var(--linha);border-radius:12px;padding:20px;margin-bottom:16px}
h2{font-size:15px;margin:0 0 16px;color:var(--ink)}
.barras{display:flex;flex-direction:column;gap:6px}
.item{display:grid;grid-template-columns:minmax(96px,22%) 1fr auto;gap:12px;align-items:center;position:relative}
.rot{color:var(--ink2);font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.trilha{background:var(--trilha);border-radius:4px;height:22px;overflow:hidden}
.barra{display:block;height:100%;background:var(--serie);border-radius:0 4px 4px 0;min-width:2px;
transition:width .18s ease}
.val{font-variant-numeric:tabular-nums;font-size:13px;color:var(--ink);white-space:nowrap}
.dica{position:absolute;left:0;bottom:calc(100% + 6px);z-index:2;background:var(--sup);color:var(--ink);
border:1px solid var(--linha);border-radius:8px;padding:6px 10px;font-size:12px;opacity:0;pointer-events:none;
transition:opacity .12s;box-shadow:0 4px 14px rgba(0,0,0,.14);max-width:min(560px,92%)}
.item:hover .dica,.item:focus-within .dica{opacity:1}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:7px 10px;border-bottom:1px solid var(--linha);vertical-align:top}
th{color:var(--mudo);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.f,.fonte{color:var(--ink2);font-size:12px}
.sev{display:inline-flex;gap:6px;align-items:center;font-weight:600;font-size:12px;text-transform:uppercase;
letter-spacing:.04em}
.sev.alta{color:var(--alta)}.sev.media{color:var(--media)}.sev.baixa{color:var(--baixa)}
.alerta{border:1px solid var(--linha);border-left:3px solid var(--linha);border-radius:8px;padding:14px 16px;
margin-bottom:10px;background:var(--sup)}
.alerta.alta{border-left-color:var(--alta)}.alerta.media{border-left-color:var(--media)}
.alerta.baixa{border-left-color:var(--baixa)}
.alerta p{margin:6px 0 0}
.ev{margin:8px 0 0;padding:0;list-style:none;color:var(--ink2);font-size:12px}
.ev li{margin:2px 0}
.ctrl{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:18px}
.ctrl input[type=range]{flex:1 1 220px;accent-color:var(--serie)}
.ctrl output{font-variant-numeric:tabular-nums;font-weight:600}
footer{max-width:920px;margin:0 auto;color:var(--mudo);font-size:12px;border-top:1px solid var(--linha);
padding-top:12px}
footer p{margin:4px 0}
@media (max-width:560px){.item{grid-template-columns:1fr auto}.trilha{grid-column:1/-1}}
"""


def _esc(v) -> str:
    return escape("" if v is None else str(v), quote=True)


def _num(v, dec: int = 1) -> str:
    """Número no formato do Brasil (1.234,5). Sem valor, travessão."""
    if v is None:
        return "—"
    return f"{float(v):,.{dec}f}".replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def _pagina(titulo: str, subtitulo: str, corpo: str, fontes: list[str], script: str = "") -> str:
    rodape = "".join(f"<p>{_esc(f)}</p>" for f in fontes)
    js = f"<script>{script}</script>" if script else ""
    return (f"<!doctype html>\n<html lang=\"pt-BR\"><head><meta charset=\"utf-8\">"
            f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            f"<title>{_esc(titulo)}</title><style>{CSS}</style></head><body>"
            f"<main><h1>{_esc(titulo)}</h1><p class=\"sub\">{_esc(subtitulo)}</p>{corpo}</main>"
            f"<footer><p><strong>Fontes</strong></p>{rodape}</footer>{js}</body></html>\n")


def _barras(itens: list[dict], unidade: str, dec: int = 1) -> str:
    """Barras horizontais: rótulo, barra proporcional ao maior valor, valor direto e a fonte no hover."""
    maior = max((abs(i["valor"]) for i in itens if i.get("valor") is not None), default=0) or 1
    fora = []
    for i in itens:
        largura = 100 * abs(i["valor"] or 0) / maior
        dica = f"{i['rotulo']} · {_num(i['valor'], dec)} {unidade} · {i['fonte']}"
        fora.append(f"<div class=\"item\" tabindex=\"0\"><span class=\"rot\" title=\"{_esc(i['rotulo'])}\">"
                    f"{_esc(i['rotulo'])}</span><span class=\"trilha\"><span class=\"barra\" "
                    f"style=\"width:{largura:.4g}%\"></span></span>"
                    f"<span class=\"val\">{_num(i['valor'], dec)}</span>"
                    f"<span class=\"dica\">{_esc(dica)}</span></div>")
    return f"<div class=\"barras\">{''.join(fora)}</div>"


def _tabela(colunas: list[str], linhas: list[list], classes: list[str] | None = None) -> str:
    """Tabela com as células JÁ escapadas (quem chama controla o que é número e o que é fonte)."""
    classes = classes or []
    cab = "".join(f"<th>{_esc(c)}</th>" for c in colunas)
    corpo = ""
    for lin in linhas:
        corpo += "<tr>" + "".join(
            f"<td class=\"{classes[k] if k < len(classes) else ''}\">{c}</td>" for k, c in enumerate(lin)) + "</tr>"
    return f"<table><thead><tr>{cab}</tr></thead><tbody>{corpo}</tbody></table>"


def _gravar(prefixo: str, html: str) -> str:
    os.makedirs(PASTA, exist_ok=True)
    nome = f"{datetime.now():%Y%m%d-%H%M%S}-{prefixo}-{secrets.token_hex(3)}.html"
    with open(os.path.join(PASTA, nome), "w", encoding="utf-8") as f:
        f.write(html)
    return f"{URL_BASE}/{nome}"


def _sem_fonte(itens: list[dict]) -> list[str]:
    """Nenhum número sem fonte: quem chega sem fonte não entra na tela."""
    return [f"{i.get('rotulo')}: {_num(i.get('valor'))}" for i in itens if not str(i.get("fonte") or "").strip()]


NOMES = {"score_divulgacao": ("Score de divulgação ESG", "0-100", 0),
         "intensidade_receita": ("Intensidade de emissões", "tCO2e por R$ mi de receita", 3),
         "escopo1_2": ("Emissões de escopo 1+2", "tCO2e", 1),
         "pct_renovavel": ("Percentual renovável declarado", "%", 1)}


@mcp.tool()
def tela_ranking(metrica: str = "score_divulgacao", ano: int | None = None, limite: int = 15) -> dict:
    """Monta a TELA do ranking do Placar (artefato HTML com gráfico de barras, valor em cada barra e a fonte de cada
    número) e devolve o link para abrir. Mesmas métricas de placar_ranking: 'score_divulgacao',
    'intensidade_receita', 'escopo1_2', 'pct_renovavel'. Use quando o usuário quiser ver, comparar ou compartilhar."""
    dados = placar_ranking(metrica, ano, limite)
    if dados.get("erro"):
        return dados
    titulo_m, unidade, dec = NOMES.get(metrica, (metrica, "", 1))
    itens = [{"rotulo": f"{i['empresa']} {i['ano']}", "valor": i["valor"], "fonte": i.get("fonte") or ""}
             for i in dados["ranking"]]
    faltando = _sem_fonte(itens)
    if faltando:
        return {"gravado": False, "erros": faltando,
                "como_corrigir": "a tela não mostra número sem fonte; use placar_ranking e cite os valores no texto"}
    if not itens:
        return {"gravado": False, "erros": ["o ranking veio vazio"],
                "como_corrigir": "confira a métrica e o ano; o placar cobre só as empresas com relatório indexado"}
    detalhe = [[_esc(i["rotulo"]), _num(i["valor"], dec), _esc(i["fonte"])] for i in itens]
    corpo = (f"<div class=\"cartao\"><h2>{_esc(titulo_m)} ({_esc(unidade)})</h2>"
             f"{_barras(itens, unidade, dec)}</div>"
             f"<div class=\"cartao\"><h2>Cada número e sua fonte</h2>"
             f"{_tabela(['Empresa e ano', unidade.capitalize(), 'Fonte'], detalhe, ['', 'n', 'f'])}</div>")
    html = _pagina(f"Placar da Transição — {titulo_m}",
                   f"{len(itens)} empresas com relatório indexado" + (f", ano {ano}" if ano else "") +
                   f". Gerado pelo EnergyNexus em {datetime.now():%d/%m/%Y %H:%M}.", corpo,
                   ["Emissões, metas, % renovável e frameworks: relatórios das empresas (arquivo e página na tabela), "
                    "extraídos com checagem de que o valor aparece na página citada.",
                    "Receita, EBITDA e lucro: kpis_financeiros (CVM, consolidado) — data/energynexus.duckdb.",
                    dados.get("nota") or ""])
    return {"gravado": True, "tela": _gravar(f"placar-{metrica}", html), "empresas": len(itens),
            "metrica": metrica, "proximo_passo": "mostre o link ao usuário e resuma o topo do ranking no texto"}


ICONE = {"alta": "▲", "media": "●", "baixa": "○"}


@mcp.tool()
def tela_radar(empresa: str | None = None) -> dict:
    """Monta a TELA do radar de consistência (anti-greenwashing): um cartão por alerta, com severidade (ícone e
    rótulo, não só cor), a explicação e as DUAS evidências (documento/página e tabela oficial). Devolve o link."""
    dados = radar_consistencia(empresa)
    alertas = dados["alertas"]
    if not alertas:
        corpo = ("<div class=\"cartao\"><h2>Nenhum alerta</h2><p>Nas regras de hoje (% renovável × SIGA, meta sem "
                 "escopo 3 e divulgação sem asseguração) não há divergência para investigar"
                 f"{' em ' + _esc(empresa) if empresa else ''}.</p></div>")
    else:
        cartoes = []
        for a in alertas:
            cartoes.append(
                f"<div class=\"alerta {_esc(a['severidade'])}\"><span class=\"sev {_esc(a['severidade'])}\">"
                f"{ICONE.get(a['severidade'], '•')} severidade {_esc(a['severidade'])}</span>"
                f"<p><strong>{_esc(a['empresa'])} {_esc(a['ano'])}</strong> — {_esc(a['titulo'])}</p>"
                f"<p>{_esc(a['explicacao'])}</p>"
                f"<ul class=\"ev\"><li>Evidência no relatório: {_esc(a['evidencia_doc'])}</li>"
                f"<li>Evidência na base: {_esc(a['evidencia_dado'])}</li></ul></div>")
        corpo = f"<div class=\"cartao\"><h2>{len(alertas)} alerta(s)</h2>{''.join(cartoes)}</div>"
    if dados.get("nao_comparaveis"):
        itens = "".join(f"<li>{_esc(x)}</li>" for x in dados["nao_comparaveis"])
        corpo += (f"<div class=\"cartao\"><h2>Declarações que não dá para confrontar</h2>"
                  f"<ul class=\"ev\">{itens}</ul></div>")
    html = _pagina("Radar de consistência" + (f" — {empresa}" if empresa else ""),
                   f"Afirmação do relatório × dado oficial. Gerado pelo EnergyNexus em {datetime.now():%d/%m/%Y %H:%M}.",
                   corpo,
                   ["Afirmações: relatórios das empresas (arquivo e página em cada alerta).",
                    "Capacidade em operação por fonte: capacidade_por_grupo (SIGA/ANEEL).",
                    dados["nota"]])
    return {"gravado": True, "tela": _gravar("radar", html), "alertas": len(alertas),
            "proximo_passo": "mostre o link e, no texto, os alertas de severidade alta com as duas evidências"}


JS_CARBONO = """
const D=__DADOS__;const fx=(v,d)=>v==null?'—':v.toLocaleString('pt-BR',{minimumFractionDigits:d,
maximumFractionDigits:d});
function desenhar(){const p=+document.getElementById('preco').value;document.getElementById('vp').value=
'R$ '+fx(p,0)+'/t';const l=D.map(d=>({...d,exp:d.tco2e*p})).map(d=>({...d,pct:d.ebitda?100*d.exp/d.ebitda:null}));
l.sort((a,b)=>(b.pct??-1)-(a.pct??-1));const m=Math.max(...l.map(d=>d.pct||0),0.0001);
document.getElementById('barras').innerHTML=l.map(d=>`<div class="item" tabindex="0"><span class="rot">${d.empresa}
 ${d.ano}</span><span class="trilha"><span class="barra" style="width:${100*(d.pct||0)/m}%"></span></span>
<span class="val">${d.pct==null?'sem EBITDA':fx(d.pct,1)+'%'}</span><span class="dica">${d.empresa} ${d.ano} · ${
fx(d.tco2e,0)} tCO2e × R$ ${fx(p,0)}/t = R$ ${fx(d.exp/1e6,1)} mi · ${d.fonte_emissoes}${d.fonte_financeiro?' · '+
d.fonte_financeiro:''}</span></div>`).join('');
document.getElementById('linhas').innerHTML=l.map(d=>`<tr><td>${d.empresa} ${d.ano}</td><td class="n">${
fx(d.tco2e,0)}</td><td class="n">${fx(d.exp/1e6,1)}</td><td class="n">${d.pct==null?'—':fx(d.pct,1)}</td>
<td class="n">${d.lucro?fx(100*d.exp/d.lucro,1):'—'}</td><td class="f">${
fx(d.tco2e,0)} tCO2e × R$ ${fx(p,0)}/t · ${d.fonte_emissoes}${d.fonte_financeiro?' · '+d.fonte_financeiro:
' · sem financeiro na base'}${d.aviso?' · ⚠ '+d.aviso:''}</td></tr>`).join('');}
document.getElementById('preco').addEventListener('input',desenhar);desenhar();
"""


@mcp.tool()
def tela_carbono(preco_por_t: float = 100.0, escopos: list[str] | None = None) -> dict:
    """Monta a TELA da exposição a preço de carbono, com barra deslizante de preço (R$/tCO2e) que recalcula na hora
    no navegador: emissões × preço contra EBITDA e lucro, com a fórmula e a fonte de cada número. Devolve o link."""
    dados = exposicao_carbono(preco_por_t, escopos)
    con = _con()
    try:
        linhas = []
        for i in dados["ranking"]:
            fin = _fin_ano(con, i["cnpj"], i["ano"])
            linhas.append({"empresa": i["empresa"], "ano": i["ano"], "tco2e": i["tco2e"],
                           "ebitda": (fin or {}).get("ebitda"), "lucro": (fin or {}).get("lucro"),
                           "fonte_emissoes": i["fonte_emissoes"], "aviso": i.get("aviso_escopo", ""),
                           "fonte_financeiro": i.get("fonte_financeiro", "")})
    finally:
        con.close()
    if not linhas:
        return {"gravado": False, "erros": ["nenhuma empresa com emissões confirmadas nos escopos pedidos"],
                "como_corrigir": "tente escopos=['1','2'] ou confira o placar com consultar_placar"}
    corpo = ("<div class=\"cartao\"><h2>Preço de carbono</h2><div class=\"ctrl\">"
             "<label for=\"preco\">R$ por tonelada de CO2e</label>"
             f"<input id=\"preco\" type=\"range\" min=\"0\" max=\"600\" step=\"10\" value=\"{int(preco_por_t)}\">"
             "<output id=\"vp\"></output></div>"
             f"<p class=\"fonte\">Exposição como % do EBITDA, escopos {', '.join(dados['escopos'])}. "
             "Arraste para ver outro preço; a conta é refeita na hora com os dados desta página.</p>"
             "<div class=\"barras\" id=\"barras\"></div></div>"
             "<div class=\"cartao\"><h2>Conta de cada empresa</h2><table><thead><tr><th>Empresa e ano</th>"
             "<th>tCO2e</th><th>Exposição (R$ mi)</th><th>% EBITDA</th><th>% lucro</th><th>Fórmula e fontes</th>"
             "</tr></thead><tbody id=\"linhas\"></tbody></table></div>")
    html = _pagina("Exposição a preço de carbono",
                   f"{len(linhas)} empresas com emissões confirmadas. "
                   f"Gerado pelo EnergyNexus em {datetime.now():%d/%m/%Y %H:%M}.", corpo,
                   ["Emissões por escopo: relatórios das empresas (arquivo e página em consultar_placar), só valores "
                    "com a fonte confirmada na página.",
                    "EBITDA e lucro líquido: kpis_financeiros (CVM, consolidado) — data/energynexus.duckdb.",
                    dados["nota"]],
                   JS_CARBONO.replace("__DADOS__", json.dumps(linhas, ensure_ascii=False).replace("</", "<\\/")))
    return {"gravado": True, "tela": _gravar("carbono", html), "empresas": len(linhas),
            "preco_inicial": preco_por_t, "escopos": dados["escopos"],
            "proximo_passo": "mostre o link, diga que o preço é ajustável na tela e cite as duas maiores exposições"}

if __name__ == "__main__":
    mcp.run()

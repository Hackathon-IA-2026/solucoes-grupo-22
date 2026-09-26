"""Servidor MCP "coppezip-placar": consulta o Placar da Transição (dados ESG extraídos dos relatórios para
data/placar.duckdb) e cruza com o banco estruturado (data/coppezip.duckdb) para métricas híbridas, radar de
consistência (anti-greenwashing) e exposição a preço de carbono.

Todo valor de ESG traz arquivo, página e a confiança da extração; todo valor financeiro/operacional traz a tabela
de origem. As ferramentas só usam ESG com confianca > 0 (checado contra a página na extração).
"""
import os

import duckdb
from mcp.server.mcpserver import MCPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLACAR = os.path.join(RAIZ, "data", "placar.duckdb")
COPPEZIP = os.path.join(RAIZ, "data", "coppezip.duckdb")

# fontes de geração consideradas renováveis (SIGA/ANEEL): hídrica, eólica, solar, biomassa
RENOVAVEL = ("UHE", "PCH", "CGH", "EOL", "UFV", "BIO")

INSTRUCOES = """Use o coppezip-placar para o Placar da Transição (ESG estruturado dos relatórios, já com página e
confiança) e para três análises que cruzam relatório × dados oficiais:
- consultar_placar(empresa[, ano]): emissões por escopo, metas, % renovável, CAPEX, frameworks e o score de
  divulgação de uma empresa, com métricas híbridas (tCO2e/receita, CAPEX/receita) — cada número com sua fonte.
- placar_ranking(metrica[, ano]): ranking comparativo entre empresas (metrica: intensidade_receita,
  score_divulgacao, escopo1_2, pct_renovavel).
- radar_consistencia(empresa): alertas anti-greenwashing (afirmação do relatório × SIGA/DFP), com severidade e as
  duas evidências.
- exposicao_carbono(preco_por_t[, escopos]): emissões × preço de carbono contra lucro e EBITDA, com a fórmula.
Cite sempre a fonte que a ferramenta devolve (documento e página, ou tabela). Se uma empresa não estiver na base de
relatórios, diga; o placar cobre só as empresas com relatório indexado."""

mcp = MCPServer("coppezip-placar", instructions=INSTRUCOES)


def _con():
    con = duckdb.connect(PLACAR, read_only=True)
    # IF NOT EXISTS: o servidor atende chamadas concorrentes e o catálogo do banco é compartilhado no processo;
    # sem isso, um segundo ATTACH simultâneo falharia com "fin já existe".
    con.execute(f"ATTACH IF NOT EXISTS '{COPPEZIP}' AS fin (READ_ONLY)")
    return con


def _filtro_empresa(alias: str, empresa: str | None):
    if not empresa:
        return "TRUE", []
    return (f"(strip_accents(lower({alias}.empresa)) LIKE '%' || strip_accents(lower(?)) || '%' "
            f"OR regexp_replace(coalesce({alias}.cnpj,''),'\\D','','g') = regexp_replace(?,'\\D','','g'))",
            [empresa.strip(), empresa.strip()])


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
        ORDER BY e.empresa, e.ano_relatorio, e.escopo""", params).fetchall()
    cols = ("empresa", "cnpj", "ano", "escopo", "tco2e", "intensidade", "unidade_intensidade", "arquivo", "pagina")
    return [dict(zip(cols, r)) for r in linhas]


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
            e12 = sum(e["tco2e"] or 0 for e in emissoes
                      if e["cnpj"] == cnpj and e["ano"] == ano_rel and e["escopo"] in ("1", "2", "2_mercado"))
            fin = _fin_ano(con, cnpj, ano_rel)
            item = {"empresa": nome, "ano": ano_rel, "escopo1_2_tco2e": round(e12, 1) if e12 else None,
                    "fonte_emissoes": "esg_emissoes (relatório, com página)"}
            if fin and fin["receita"]:
                item["tco2e_por_milhao_receita"] = round(e12 / (fin["receita"] / 1e6), 3) if e12 else None
                cx = next((c["capex_total_brl"] for c in capex if c["cnpj"] == cnpj), None) or fin["investimento"]
                item["capex_sobre_receita_pct"] = round(100 * cx / fin["receita"], 1) if cx else None
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
    por = {}
    for e in emissoes:
        d = por.setdefault((e["empresa"], e["ano"]), {"escopos": set(), "meta": False, "fw": set(), "asseg": False})
        d["escopos"].add(e["escopo"].replace("_mercado", ""))
    for m in metas:
        por.setdefault((m["empresa"], m["ano_relatorio"]), {"escopos": set(), "meta": False, "fw": set(), "asseg": False})["meta"] = True
    for f in frameworks:
        d = por.setdefault((f["empresa"], f["ano_relatorio"]), {"escopos": set(), "meta": False, "fw": set(), "asseg": False})
        d["fw"].add(f["framework"])
        d["asseg"] = d["asseg"] or bool(f["asseguracao_externa"])
    saida = []
    for (empresa, ano), d in por.items():
        s = 15 * len(d["escopos"] & {"1", "2", "3"}) + 20 * d["meta"] + min(len(d["fw"]), 3) * 5 + 20 * d["asseg"]
        saida.append({"empresa": empresa, "ano": ano, "score": min(s, 100),
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
                  "detalhe": s["componentes"]} for s in dados["score_divulgacao"]]
        ordem = True
    elif metrica in ("intensidade_receita", "escopo1_2"):
        campo = "tco2e_por_milhao_receita" if metrica == "intensidade_receita" else "escopo1_2_tco2e"
        itens = [{"empresa": h["empresa"], "ano": h["ano"], "valor": h.get(campo),
                  "unidade": "tCO2e/R$ mi" if metrica == "intensidade_receita" else "tCO2e",
                  "fonte": h.get("fonte_financeiro", h.get("fonte_emissoes"))}
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
    itens = sorted(itens, key=lambda x: (x["valor"] is None, -(x["valor"] or 0) if ordem else (x["valor"] or 0)))
    return {"metrica": metrica, "ranking": itens[:limite],
            "nota": "só empresas com relatório indexado e (para métricas híbridas) CNPJ que casa com a CVM"}


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
        emissoes, metas, renovavel, frameworks = (placar["emissoes"], placar["metas"], placar["renovavel"],
                                                   placar["frameworks"])
        # (1) % renovável × SIGA
        for r in renovavel:
            afirmado = r.get("pct_geracao_renovavel") or r.get("pct_capacidade_renovavel")
            if afirmado is None:
                continue
            cap = _cap_por_fonte(con, r["cnpj"])
            if not cap or cap["pct_renovavel"] is None:
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
            e3 = next((e for e in emissoes if e["empresa"] == m["empresa"] and e["escopo"] == "3"), None)
            e12 = sum(e["tco2e"] or 0 for e in emissoes if e["empresa"] == m["empresa"] and e["escopo"] in ("1", "2"))
            if e3 and (e3["tco2e"] or 0) > e12 > 0:
                alertas.append({
                    "regra": "meta_ignora_escopo3", "empresa": m["empresa"], "ano": m["ano_relatorio"],
                    "severidade": "media",
                    "explicacao": f"Meta {m['tipo']} (alvo {m.get('ano_alvo')}) cobre '{m.get('escopo_coberto')}', "
                                  f"mas o escopo 3 ({e3['tco2e']:.0f} tCO2e) é maior que escopo 1+2 ({e12:.0f} tCO2e).",
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
        return {"alertas": alertas, "total": len(alertas),
                "nota": "alertas indicam divergência a investigar, não fraude; confira as duas evidências citadas"}
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
        por = {}
        for e in emissoes:
            if e["escopo"].replace("_mercado", "") in escopos:
                por.setdefault((e["cnpj"], e["ano"], e["empresa"]), 0.0)
                por[(e["cnpj"], e["ano"], e["empresa"])] += e["tco2e"] or 0
        itens = []
        for (cnpj, ano, nome), tco2e in por.items():
            fin = _fin_ano(con, cnpj, ano)
            exposicao = tco2e * preco_por_t
            item = {"empresa": nome, "ano": ano, "escopos": escopos, "tco2e": round(tco2e, 1),
                    "exposicao_brl": round(exposicao, 0),
                    "formula": f"{tco2e:.0f} tCO2e × R$ {preco_por_t:.0f}/t = R$ {exposicao/1e6:.1f} mi",
                    "fonte_emissoes": "esg_emissoes (relatório)"}
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


if __name__ == "__main__":
    mcp.run()

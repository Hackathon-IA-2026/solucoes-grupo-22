"""Servidor MCP "energynexus-docs": busca nos relatórios das empresas (sustentabilidade, relato integrado, inventário de
emissões, TCFD, plano climático) e em documentos de referência (CVM, EPE, SEEG), com documento e página para citar.

Busca híbrida: palavras (BM25 do DuckDB, português) + significado (multilingual-e5-large), fundidas por posição (RRF).
O índice é montado por indexar.py a partir de documentos.csv.
"""
import os
import threading

import duckdb
from mcp.server.mcpserver import MCPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # raiz do repositório


DB = os.path.join(RAIZ, "data", "docs.duckdb")
MODELO = "intfloat/multilingual-e5-large"
# cópia simples do modelo (o onnxruntime recusa os links simbólicos do cache do Hugging Face)
PASTA_MODELO = os.path.join(RAIZ, "data", "modelos", "multilingual-e5-large")
CANDIDATOS = 60  # por método, antes da fusão

INSTRUCOES = """Use estas ferramentas para o que está nos relatórios das empresas e não nas tabelas: emissões de gases de
efeito estufa por escopo, intensidade de carbono, metas climáticas e SBTi, plano de transição, riscos climáticos, CAPEX
verde, P&D e inovação, estratégia, indicadores sociais e de governança; e para regulação e referências (Resoluções CVM
193 e 244 sobre IFRS S1/S2, Balanço Energético Nacional, SEEG).
1. Chame buscar_documentos com uma consulta objetiva em português (ex.: "emissões escopo 1 2025 tCO2e") e filtre por
   empresa e ano quando souber. Se o dado não aparecer, tente 2 ou 3 formulações diferentes antes de desistir.
2. Números de tabelas: leia a página inteira com ler_pagina antes de citar, porque os trechos cortam tabelas.
3. Cite documento, ano e página (ex.: Cemig, Relatório Anual de Sustentabilidade 2025, p. 87) e deixe claro que é um
   número reportado pela empresa.
4. Regulação e referências setoriais: filtre empresa="CVM" (Resoluções 193 e 244), "EPE" (BEN) ou "SEEG".
5. listar_documentos mostra o que existe; se a empresa ou o ano não estiver na base, diga isso."""

mcp = MCPServer("energynexus-docs", instructions=INSTRUCOES)
_modelo = None
_trava = threading.Lock()


def _embed(texto: str) -> list[float]:
    global _modelo
    with _trava:
        if _modelo is None:
            from fastembed import TextEmbedding
            _modelo = TextEmbedding(MODELO, specific_model_path=PASTA_MODELO, threads=4)
        return next(iter(_modelo.embed([f"query: {texto}"]))).tolist()


def _con():
    con = duckdb.connect(DB, read_only=True)
    con.execute("LOAD fts")
    return con


def _filtro(empresa: str | None, ano: int | None) -> tuple[str, list]:
    conds, params = [], []
    if empresa:
        conds.append("""(strip_accents(lower(d.empresa)) LIKE '%' || strip_accents(lower(?)) || '%'
                         OR regexp_replace(coalesce(d.cnpj, ''), '\\D', '', 'g') = regexp_replace(?, '\\D', '', 'g'))""")
        params += [empresa.strip(), empresa.strip()]
    if ano:
        conds.append("d.ano = ?")
        params.append(int(ano))
    return (" AND ".join(conds) or "TRUE"), params


@mcp.tool()
def buscar_documentos(consulta: str, empresa: str | None = None, ano: int | None = None, k: int = 8) -> dict:
    """Busca trechos nos relatórios das empresas e documentos de referência. Devolve texto, empresa, ano, título,
    arquivo e página de cada trecho. empresa filtra por nome (Cemig, Engie, Axia...) ou CNPJ; ano é o ano do relatório."""
    k = max(1, min(int(k), 20))
    onde, params = _filtro(empresa, ano)
    vetor = _embed(consulta)
    con = _con()
    try:
        palavras = con.execute(f"""
            SELECT t.id FROM (SELECT *, fts_main_trechos.match_bm25(id, ?) AS s FROM trechos) t
            JOIN documentos d USING (arquivo) WHERE t.s IS NOT NULL AND {onde} ORDER BY t.s DESC LIMIT {CANDIDATOS}""",
                               [consulta] + params).fetchall()
        sentido = con.execute(f"""
            SELECT t.id FROM trechos t JOIN documentos d USING (arquivo) WHERE {onde}
            ORDER BY array_cosine_similarity(t.embedding, ?::FLOAT[1024]) DESC LIMIT {CANDIDATOS}""",
                              params + [vetor]).fetchall()
        pontos = {}
        for lista in (palavras, sentido):
            for posicao, (i,) in enumerate(lista):
                pontos[i] = pontos.get(i, 0) + 1 / (60 + posicao)
        melhores = sorted(pontos, key=pontos.get, reverse=True)[:k]
        if not melhores:
            return {"resultados": [], "aviso": "nada encontrado; tente outras palavras ou confira listar_documentos"}
        linhas = con.execute("""
            SELECT t.id, d.empresa, d.ano, d.titulo, t.arquivo, t.pagina, t.texto
            FROM trechos t JOIN documentos d USING (arquivo) WHERE t.id IN (SELECT unnest(?))""", [melhores]).fetchall()
    finally:
        con.close()
    por_id = {r[0]: r for r in linhas}
    return {"resultados": [{"empresa": r[1], "ano": r[2], "documento": r[3], "arquivo": r[4], "pagina": r[5],
                            "trecho": r[6], "relevancia": round(pontos[i] * 1000, 1)}
                           for i in melhores if (r := por_id.get(i))]}


@mcp.tool()
def ler_pagina(arquivo: str, pagina: int) -> dict:
    """Devolve o texto completo de uma página de um documento (use o arquivo devolvido por buscar_documentos). Útil para
    ler tabelas inteiras antes de citar números."""
    con = _con()
    try:
        doc = con.execute("SELECT arquivo, empresa, ano, titulo, paginas, url FROM documentos WHERE arquivo = ?",
                          [arquivo]).fetchone()
        if not doc:
            return {"erro": f"arquivo '{arquivo}' não existe; use listar_documentos"}
        linha = con.execute("SELECT texto FROM paginas WHERE arquivo = ? AND pagina = ?", [arquivo, int(pagina)]).fetchone()
    finally:
        con.close()
    if not linha:
        return {"erro": f"o documento tem {doc[4]} páginas"}
    return {"arquivo": doc[0], "empresa": doc[1], "ano": doc[2], "documento": doc[3], "pagina": int(pagina),
            "total_paginas": doc[4], "url": doc[5], "texto": linha[0][:12000]}


@mcp.tool()
def listar_documentos(empresa: str | None = None) -> list[dict]:
    """Lista os documentos da base (empresa, ano, tipo, título, páginas, arquivo), opcionalmente de uma empresa."""
    onde, params = _filtro(empresa, None)
    con = _con()
    try:
        cur = con.execute(f"""SELECT d.empresa, d.ano, d.tipo, d.titulo, d.paginas, d.arquivo FROM documentos d
                              WHERE {onde} ORDER BY d.empresa, d.ano""", params)
        nomes = [c[0] for c in cur.description]
        return [dict(zip(nomes, r)) for r in cur.fetchall()]
    finally:
        con.close()


if __name__ == "__main__":
    mcp.run()

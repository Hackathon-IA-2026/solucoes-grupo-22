"""Servidor MCP "energynexus-docs": busca nos documentos das empresas, divididos em duas áreas (financeiro: releases,
demonstrações, apresentações, fatos relevantes, debêntures, rating; sustentabilidade: relatórios ESG, inventário de
emissões, TCFD, governança) e em documentos de referência (CVM, EPE, SEEG), com documento e página para citar.

Busca híbrida: palavras (BM25 do DuckDB, português) + significado (Amazon Titan Text Embeddings v2, pelo Bedrock),
fundidas por posição (RRF). O índice data/docs_titan.duckdb é montado por data/indexar_docs_titan.py a partir de
documentos.csv; credenciais da AWS em ~/.aws/credentials e região BEDROCK_AWS_DEFAULT_REGION do .env.
"""
import json
import os
import re
import threading

import boto3
import duckdb
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # raiz do repositório


DB = os.path.join(RAIZ, "data", "docs_titan.duckdb")
MODELO = "amazon.titan-embed-text-v2:0"
CANDIDATOS = 60  # por método, antes da fusão
MAX_LISTA = 100

INSTRUCOES = """Use estas ferramentas para o que está nos documentos das empresas e não nas tabelas. Os documentos têm
duas áreas; filtre por area sempre que a pergunta for de uma delas:
- area="financeiro": press releases de resultados, demonstrações financeiras completas e 20-F, apresentações a
  investidores, fatos relevantes, orçamento e proventos, debêntures (escrituras, prospectos, avisos, agente fiduciário) e
  relatórios de rating. Use para guidance, contexto de resultados, eventos corporativos, covenants e condições de dívida.
- area="sustentabilidade": relatórios de sustentabilidade e relato integrado, inventário de emissões, TCFD, plano
  climático, políticas e governança (estatuto, regimentos, código de conduta, partes relacionadas, remuneração) e as
  referências de regulação (CVM, EPE, SEEG). Use para emissões por escopo, metas climáticas, riscos, indicadores sociais.
1. Chame buscar_documentos com uma consulta objetiva em português (ex.: "emissões escopo 1 2025 tCO2e") e filtre por
   empresa, area e ano quando souber. Se o dado não aparecer, tente 2 ou 3 formulações diferentes antes de desistir.
2. Números de tabelas: leia a página inteira com ler_pagina antes de citar, porque os trechos cortam tabelas.
3. Cite documento, ano e página (ex.: Cemig, Relatório Anual de Sustentabilidade 2025, p. 87) e deixe claro que é um
   número reportado pela empresa. Número contábil oficial vem das tabelas da CVM; o documento dá o contexto.
4. Regulação e referências setoriais: filtre empresa="CVM" (Resoluções 193 e 244), "EPE" (BEN) ou "SEEG".
5. listar_documentos mostra o que existe (filtre por empresa, area e ano); se não estiver na base, diga isso."""

mcp = MCPServer("energynexus-docs", instructions=INSTRUCOES)
_bedrock = None
_trava = threading.Lock()


def _embed(texto: str) -> list[float]:
    global _bedrock
    with _trava:
        if _bedrock is None:
            # o LibreChat sobe os MCP sem as variáveis do .env: a região é lida do próprio arquivo
            with open(os.path.join(RAIZ, ".env")) as f:
                regiao = next((l.split("=", 1)[1].strip() for l in f if l.startswith("BEDROCK_AWS_DEFAULT_REGION=")), None)
            if not regiao:
                raise ToolError("base de documentos indisponível: falta BEDROCK_AWS_DEFAULT_REGION no .env")
            _bedrock = boto3.client("bedrock-runtime", region_name=regiao)
    try:
        r = _bedrock.invoke_model(modelId=MODELO, contentType="application/json", accept="application/json",
                                  body=json.dumps({"inputText": texto, "dimensions": 1024, "normalize": True}))
    except Exception as e:  # credencial vencida, sem acesso ou throttling
        # ToolError chega ao modelo com o motivo; outra exceção vira só "Error executing tool" e parece falha passageira
        raise ToolError(f"base de documentos indisponível: embeddings do Bedrock falharam ({e})")
    return json.loads(r["body"].read())["embedding"]


SEM_AREA = re.compile(r'column[^"]*"area"', re.I)  # BinderException de índice antigo, sem a coluna que _filtro usa


def _erro_consulta(e: Exception) -> ToolError:
    """Erro cru do DuckDB vira só "Error executing tool" para o modelo e parece falha passageira; ToolError diz o
    motivo (índice de outra versão, sem a coluna area, sem o índice fts) e o que fazer."""
    if SEM_AREA.search(str(e)):
        return ToolError(f"base de documentos indisponível: o índice {os.path.basename(DB)} não tem a coluna area, que "
                         "as três ferramentas devolvem; refaça com data/indexar_docs_titan.py (chamar sem o filtro "
                         "area não resolve)")
    return ToolError(f"base de documentos indisponível: a consulta falhou no índice {os.path.basename(DB)} ({e}); "
                     "se o índice for de uma versão antiga, refaça com data/indexar_docs_titan.py")


def _con():
    if not os.path.exists(DB):
        raise ToolError(f"base de documentos indisponível: o índice {DB} não existe (data/indexar_docs_titan.py)")
    try:
        con = duckdb.connect(DB, read_only=True)
    except duckdb.Error as e:  # arquivo de outra versão do DuckDB, ou interrompido no meio da indexação
        raise _erro_consulta(e)
    try:
        con.execute("LOAD fts")  # BM25 das palavras; o AgentCore instala a extensão na subida do runtime
    except duckdb.Error as e:
        con.close()
        raise ToolError(f"base de documentos indisponível: a extensão fts do DuckDB não carregou ({e}); instale com "
                        "INSTALL fts no mesmo Python que roda o servidor")
    return con


def _filtro(empresa: str | None, ano: int | None, area: str | None = None) -> tuple[str, list]:
    conds, params = [], []
    if area:
        conds.append("d.area = ?")
        params.append(area.strip().lower())
    if empresa:
        conds.append("""(strip_accents(lower(d.empresa)) LIKE '%' || strip_accents(lower(?)) || '%'
                         OR regexp_replace(coalesce(d.cnpj, ''), '\\D', '', 'g') = regexp_replace(?, '\\D', '', 'g'))""")
        params += [empresa.strip(), empresa.strip()]
    if ano:
        conds.append("d.ano = ?")
        params.append(int(ano))
    return (" AND ".join(conds) or "TRUE"), params


@mcp.tool()
def buscar_documentos(consulta: str, empresa: str | None = None, ano: int | None = None, area: str | None = None,
                      k: int = 8) -> dict:
    """Busca trechos nos documentos das empresas e de referência. Devolve texto, empresa, ano, área, título, arquivo e
    página de cada trecho. empresa filtra por nome (Cemig, Engie, Axia...) ou CNPJ; ano é o ano do documento; area é
    "financeiro" ou "sustentabilidade"."""
    k = max(1, min(int(k), 20))
    onde, params = _filtro(empresa, ano, area)
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
            SELECT t.id, d.empresa, d.ano, d.titulo, t.arquivo, t.pagina, t.texto, d.area
            FROM trechos t JOIN documentos d USING (arquivo) WHERE t.id IN (SELECT unnest(?))""", [melhores]).fetchall()
    except duckdb.Error as e:
        raise _erro_consulta(e)
    finally:
        con.close()
    por_id = {r[0]: r for r in linhas}
    return {"resultados": [{"empresa": r[1], "ano": r[2], "area": r[7], "documento": r[3], "arquivo": r[4],
                            "pagina": r[5], "trecho": r[6], "relevancia": round(pontos[i] * 1000, 1)}
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
    except duckdb.Error as e:
        raise _erro_consulta(e)
    finally:
        con.close()
    if not linha:
        return {"erro": f"o documento tem {doc[4]} páginas"}
    return {"arquivo": doc[0], "empresa": doc[1], "ano": doc[2], "documento": doc[3], "pagina": int(pagina),
            "total_paginas": doc[4], "url": doc[5], "texto": linha[0][:12000]}


@mcp.tool()
def listar_documentos(empresa: str | None = None, area: str | None = None, ano: int | None = None) -> dict:
    """Lista os documentos da base (empresa, área, ano, tipo, título, páginas, arquivo), os mais recentes primeiro, com
    a contagem por empresa, área e tipo. Filtre por empresa, area ("financeiro" ou "sustentabilidade") e ano."""
    onde, params = _filtro(empresa, ano, area)
    con = _con()
    try:
        contagem = con.execute(f"""SELECT d.empresa, d.area, d.tipo, count(*) AS documentos FROM documentos d
                                   WHERE {onde} GROUP BY ALL ORDER BY ALL""", params).fetchall()
        cur = con.execute(f"""SELECT d.empresa, d.area, d.ano, d.tipo, d.titulo, d.paginas, d.arquivo FROM documentos d
                              WHERE {onde} ORDER BY d.ano DESC, d.empresa, d.arquivo LIMIT {MAX_LISTA}""", params)
        nomes = [c[0] for c in cur.description]
        docs = [dict(zip(nomes, r)) for r in cur.fetchall()]
    except duckdb.Error as e:
        raise _erro_consulta(e)
    finally:
        con.close()
    total = sum(c[3] for c in contagem)
    resposta = {"total": total, "por_tipo": [dict(zip(("empresa", "area", "tipo", "documentos"), c)) for c in contagem],
                "documentos": docs}
    if total > MAX_LISTA:
        resposta["aviso"] = f"mostrando os {MAX_LISTA} mais recentes de {total}; filtre por empresa, area ou ano"
    return resposta


if __name__ == "__main__":
    mcp.run()

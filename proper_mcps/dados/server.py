"""Servidor MCP "energynexus-dados": a base do EnergyNexus (CVM, ANEEL, ONS, BNDES, ANBIMA) em DuckDB, só leitura.

Ferramentas: buscar_empresa, indicadores_financeiros, listar_tabelas, descrever_tabela, valores_distintos, consultar_sql.
O banco (data/coppezip.duckdb) é montado por data/construir.py; as descrições das tabelas vêm da tabela catalogo.
"""
import datetime
import decimal
import json
import os
import re
import threading

import duckdb
from mcp.server.mcpserver import MCPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # raiz do repositório


DB = os.path.join(RAIZ, "data", "coppezip.duckdb")
LIMITE_LINHAS = 200
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
6. Prefira poucas consultas agregadas a muitas pequenas."""

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


def _json(v):
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, float):
        return round(v, 4)
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
    # 3. todas as palavras no nome social, comercial ou apelidos
    palavras = [p for p in re.split(r"[^\w]+", termo) if len(p) > 1]
    if palavras:
        conds = " AND ".join(["b.busca LIKE '%' || strip_accents(lower(?)) || '%'"] * len(palavras))
        juntar(con.execute(f"""WITH b AS ({BUSCA}) SELECT {cols} FROM b WHERE {conds}
            ORDER BY (b.anos_com_demonstracoes <> 'não') DESC, (b.situacao = 'ATIVO') DESC, length(b.nome_social)
            LIMIT ?""", palavras + [limite]).fetchall(), "nome", lambda r: "palavras do nome")
    # 4. termo que contém um apelido inteiro ("Neoenergia Coelba" -> Coelba): subsidiária antes da holding, depois o mais longo
    if not achados:
        juntar(con.execute(f"""WITH b AS ({BUSCA}) SELECT {cols}, ap.tipo, ap.apelido, ap.observacao
            FROM empresas_apelidos ap JOIN b USING (cnpj)
            WHERE length(ap.apelido) >= 4 AND regexp_matches(' ' || strip_accents(lower(?)) || ' ',
                  '[^a-z0-9]' || regexp_escape(strip_accents(lower(ap.apelido))) || '[^a-z0-9]')
            ORDER BY coalesce(ap.observacao, '') LIKE 'holding%', length(ap.apelido) DESC LIMIT ?""", [termo, limite]).fetchall(),
               "nome", lambda r: f"o termo contém o {r[6]} '{r[7]}'" + (f" ({r[8]})" if r[8] else ""))
    # 5. nada encontrado: nomes parecidos, marcados como aproximados
    if not achados:
        juntar(con.execute(f"""WITH b AS ({BUSCA}) SELECT {cols} FROM b
            ORDER BY jaro_winkler_similarity(b.busca, strip_accents(lower(?))) DESC LIMIT 3""", [termo]).fetchall(),
               "aproximada", lambda r: "nome parecido; NÃO confirmado")
    return achados[:limite]


@mcp.tool()
def buscar_empresa(termo: str, limite: int = 8) -> dict:
    """Encontra o CNPJ de empresas do setor elétrico por nome, apelido de mercado (Eletrobras, Taesa, Enel SP), nome
    antigo, ticker da B3 (TAEE11, CMIG4), CNPJ ou código CVM. Devolve cnpj, nomes, tickers, anos com demonstrações
    financeiras e a confiança do resultado (exata, nome ou aproximada). Filtre as outras tabelas pelo cnpj."""
    con = _con()
    try:
        achados = _buscar(con, termo, limite)
    finally:
        con.close()
    resposta = {"resultados": achados}
    if achados and achados[0]["confianca"] == "aproximada":
        resposta["aviso"] = (f"Nenhuma empresa com '{termo}' no nome, apelido ou ticker. Os resultados são só nomes "
                             "parecidos: não use sem confirmar com o usuário.")
    elif len(achados) > 1 and achados[0]["confianca"] != "exata":
        resposta["aviso"] = "Mais de uma empresa combina com o termo: confira holding x subsidiária antes de escolher."
    return resposta


@mcp.tool()
def indicadores_financeiros(empresa: str, ano_inicial: int | None = None, ano_final: int | None = None) -> dict:
    """Indicadores financeiros de uma empresa direto das demonstrações da CVM, em reais: os anuais (DFP, 2020 em
    diante: receita, EBIT, EBITDA calculado, lucro, dívida bruta e líquida, caixa, investimento, dividendos, margens,
    dívida líquida/EBITDA, cobertura de juros, ROE) e os 4 trimestres mais recentes (ITR: trimestre, acumulado no ano e
    últimos 12 meses), com a fonte de cada período. empresa aceita nome, apelido, ticker ou CNPJ."""
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
        trimestres = _linhas(con.execute("""SELECT ano, trimestre, data_referencia, receita_liquida_trimestre_brl,
            lucro_trimestre_brl, receita_liquida_12m_brl, ebitda_12m_brl, lucro_12m_brl, divida_bruta_brl, divida_liquida_brl,
            divida_liquida_ebitda_12m, investimento_acumulado_brl, fonte
            FROM kpis_trimestrais WHERE cnpj = ? ORDER BY data_referencia DESC LIMIT 4""", [alvo["cnpj"]]))
    finally:
        con.close()
    return {
        "empresa": {k: alvo[k] for k in ("cnpj", "nome_social", "tickers", "como_encontrou")},
        "unidade": "R$ (reais); *_pct em %; divida_liquida_ebitda e cobertura_juros_ebitda em vezes",
        "anos": anos or "sem demonstrações na base para esses anos",
        "trimestres_recentes": trimestres or "sem ITR na base para esta empresa",
        "observacoes": ["EBITDA = EBIT (conta 3.05) + depreciação e amortização da DFC; pode diferir do EBITDA ajustado "
                        "divulgado pela empresa",
                        "Dívida bruta = empréstimos, financiamentos e debêntures (2.01.04 + 2.02.01), sem arrendamentos",
                        "Os trimestres (ITR) são o dado mais recente; o 4º trimestre de cada ano está só na DFP anual. "
                        "Nos trimestres, *_12m_brl somam os últimos 12 meses",
                        "Investimento: use investimento_total_brl. capex_brl é só o caixa de investimento (6.02); nas "
                        "concessões (IFRS 15 / ICPC 01) a obra aparece em custo_construcao_concessao_brl"],
    }


# ------------------------------------------------------------------------------------------------ catálogo
@mcp.tool()
def listar_tabelas() -> list[dict]:
    """Lista as tabelas da base com descrição, fonte, ressalvas e número de linhas."""
    con = _con()
    try:
        return _linhas(con.execute("SELECT tabela, descricao, fonte, ressalvas, linhas FROM catalogo ORDER BY tabela"))
    finally:
        con.close()


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
NUMERICOS = {"TINYINT", "SMALLINT", "INTEGER", "BIGINT", "HUGEINT", "UTINYINT", "USMALLINT", "UINTEGER", "UBIGINT",
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
    if not re.match(r"(?is)^\s*(select|with|from)\b", texto) or ";" in texto:
        return {"erro": "só uma consulta de leitura por vez (SELECT ou WITH)"}
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

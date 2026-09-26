"""Junta as demonstrações da CVM de data/dados_estruturados-20260926T162432Z-1-001 ao data/coppezip.duckdb.

Os CSVs trazem DFP (2010 em diante) e ITR (2011 em diante) dos 11 maiores grupos, no mesmo layout da CVM que o
construir.py lê (só que em UTF-8 e já filtrado). O banco tem DFP de 2020 e ITR de 2024 em diante; este script acrescenta
os períodos que faltam em contas_cvm e contas_cvm_trimestral (o que já existe no banco não é tocado) e cria a tabela
composicao_capital (quantidade de ações). Antes de gravar, compara os períodos em comum e imprime as diferenças.

Uso: python data/juntar_estruturados.py
Saída: data/coppezip.duckdb, trocado de forma atômica (trabalha numa cópia .tmp).
"""
import glob
import os
import shutil

import duckdb

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DADOS = os.path.join(RAIZ, "data")
ORIGEM = os.path.join(DADOS, "dados_estruturados-20260926T162432Z-1-001", "dados_estruturados")
destino = os.path.join(DADOS, "coppezip.duckdb")
tmp = destino + ".tmp"
DEMOS = ["BPA", "BPP", "DRE", "DFC_MI", "DFC_MD", "DVA"]  # os mesmos que o construir.py carrega

if os.path.exists(tmp):
    os.remove(tmp)
shutil.copyfile(destino, tmp)
con = duckdb.connect(tmp)


def ler(arquivo):
    return f"read_csv('{arquivo}', delim=';', header=true, all_varchar=true, quote='\"', escape='\"')"


def bruto(tipo):
    """Todas as demonstrações de dfp/ ou itr/, com as colunas demonstrativo e escopo do construir.py."""
    partes = []
    for d in DEMOS:
        for sufixo, escopo in (("con", "consolidado"), ("ind", "individual")):
            arquivo = os.path.join(ORIGEM, tipo, f"{d}_{sufixo}.csv")
            with open(arquivo, encoding="utf-8") as f:
                if sum(1 for _ in f) < 2:  # só o cabeçalho (DFC_MD do ITR)
                    continue
            partes.append(f"SELECT *, '{d}' AS demonstrativo, '{escopo}' AS escopo FROM {ler(arquivo)}")
    con.execute(f"CREATE TEMP TABLE {tipo}_novo_bruto AS " + " UNION ALL BY NAME ".join(partes))


def mostrar(titulo, sql):
    print(f"\n== {titulo}")
    print(con.sql(sql))


# ---------------------------------------------------------------- empresas dos CSVs
bruto("dfp")
bruto("itr")
mostrar("empresas nos CSVs (e se o CNPJ está na tabela empresas)", """
SELECT EMPRESA_ID, CNPJ_CIA, any_value(DENOM_CIA) AS nome, min(DT_REFER) AS de, max(DT_REFER) AS ate,
       CNPJ_CIA IN (SELECT cnpj FROM empresas) AS em_empresas
FROM (SELECT * FROM dfp_novo_bruto UNION ALL BY NAME SELECT * FROM itr_novo_bruto) GROUP BY ALL ORDER BY 1""")

# ---------------------------------------------------------------- mesmas transformações do construir.py
con.execute("""CREATE TEMP TABLE dfp_novo AS
WITH u AS (SELECT *, TRY_CAST(VERSAO AS INTEGER) AS v FROM dfp_novo_bruto WHERE ORDEM_EXERC = 'ÚLTIMO')
SELECT CNPJ_CIA AS cnpj, CD_CVM AS cd_cvm, DENOM_CIA AS empresa, year(TRY_CAST(DT_REFER AS DATE)) AS ano,
       TRY_CAST(DT_REFER AS DATE) AS data_referencia, demonstrativo, escopo, CD_CONTA AS cd_conta, DS_CONTA AS ds_conta,
       TRY_CAST(VL_CONTA AS DOUBLE) * CASE WHEN ESCALA_MOEDA = 'MIL' THEN 1000 ELSE 1 END AS valor_brl,
       v AS versao, 'CVM DFP ' || year(TRY_CAST(DT_REFER AS DATE)) || ', ' || demonstrativo || ' ' || escopo
         || ', conta ' || CD_CONTA AS fonte
FROM u
QUALIFY v = max(v) OVER (PARTITION BY CNPJ_CIA, DT_REFER, demonstrativo, escopo)""")
con.execute("""CREATE TEMP TABLE itr_novo AS
WITH u AS (SELECT *, TRY_CAST(VERSAO AS INTEGER) AS v, TRY_CAST(DT_REFER AS DATE) AS ref,
                  TRY_CAST(DT_INI_EXERC AS DATE) AS ini, TRY_CAST(DT_FIM_EXERC AS DATE) AS fim
           FROM itr_novo_bruto WHERE ORDEM_EXERC = 'ÚLTIMO')
SELECT CNPJ_CIA AS cnpj, CD_CVM AS cd_cvm, DENOM_CIA AS empresa, ref AS data_referencia, year(ref) AS ano,
       quarter(ref) AS trimestre, demonstrativo, escopo,
       CASE WHEN demonstrativo IN ('BPA', 'BPP') THEN 'saldo'
            WHEN ini = make_date(year(ref), 1, 1) THEN 'acumulado' ELSE 'trimestre' END AS periodo,
       ini AS inicio_periodo, coalesce(fim, ref) AS fim_periodo, CD_CONTA AS cd_conta, DS_CONTA AS ds_conta,
       TRY_CAST(VL_CONTA AS DOUBLE) * CASE WHEN ESCALA_MOEDA = 'MIL' THEN 1000 ELSE 1 END AS valor_brl, v AS versao,
       'CVM ITR ' || year(ref) || 'T' || quarter(ref) || ', ' || demonstrativo || ' ' || escopo || ', conta ' || CD_CONTA AS fonte
FROM u
QUALIFY v = max(v) OVER (PARTITION BY CNPJ_CIA, DT_REFER, demonstrativo, escopo)""")

# ---------------------------------------------------------------- conferência dos períodos em comum
for novo, atual, chave in (("dfp_novo", "contas_cvm", "cnpj, data_referencia, demonstrativo, escopo, cd_conta"),
                           ("itr_novo", "contas_cvm_trimestral",
                            "cnpj, data_referencia, demonstrativo, escopo, periodo, cd_conta")):
    mostrar(f"{atual}: contas em comum com os CSVs, por ano (valor igual = diferença < R$ 1)", f"""
SELECT n.ano, count(*) AS contas_em_comum, count(*) FILTER (abs(n.valor_brl - a.valor_brl) < 1) AS valor_igual,
       count(*) FILTER (n.versao <> a.versao) AS versao_diferente
FROM {novo} n JOIN {atual} a USING ({chave}) GROUP BY 1 ORDER BY 1""")
    mostrar(f"{atual}: exemplos de valores diferentes", f"""
SELECT n.cnpj, n.data_referencia, n.demonstrativo, n.escopo, n.cd_conta, a.valor_brl AS no_banco, n.valor_brl AS no_csv,
       a.versao AS versao_banco, n.versao AS versao_csv
FROM {novo} n JOIN {atual} a USING ({chave}) WHERE abs(n.valor_brl - a.valor_brl) >= 1 LIMIT 10""")

# ---------------------------------------------------------------- acrescenta só os períodos que o banco não tem
for novo, atual in (("dfp_novo", "contas_cvm"), ("itr_novo", "contas_cvm_trimestral")):
    antes = con.execute(f"SELECT count(*) FROM {atual}").fetchone()[0]
    con.execute(f"""INSERT INTO {atual} BY NAME
SELECT n.* FROM {novo} n ANTI JOIN (SELECT DISTINCT cnpj, data_referencia, demonstrativo, escopo FROM {atual}) a
  USING (cnpj, data_referencia, demonstrativo, escopo)""")
    depois = con.execute(f"SELECT count(*) FROM {atual}").fetchone()[0]
    print(f"\n{atual}: {antes} -> {depois} linhas (+{depois - antes})")
    mostrar(f"{atual}: linhas por ano depois da junção", f"""
SELECT ano, count(DISTINCT cnpj) AS empresas, count(*) AS linhas FROM {atual} GROUP BY 1 ORDER BY 1""")

con.execute("""UPDATE catalogo SET descricao = replace(descricao, 'de 2020 em diante', 'de 2020 em diante (2010 para '
  || 'Axia, Cemig, Copel, CPFL, Energisa, Eneva, Engie, Equatorial, ISA Energia, Neoenergia e Taesa)'),
  linhas = (SELECT count(*) FROM contas_cvm) WHERE tabela = 'contas_cvm' AND descricao NOT LIKE '%2010 para%'""")
con.execute("""UPDATE catalogo SET descricao = replace(descricao, 'de 2024 em diante', 'de 2024 em diante (2011 para '
  || 'Axia, Cemig, Copel, CPFL, Energisa, Eneva, Engie, Equatorial, ISA Energia, Neoenergia e Taesa)'),
  linhas = (SELECT count(*) FROM contas_cvm_trimestral) WHERE tabela = 'contas_cvm_trimestral'
  AND descricao NOT LIKE '%2011 para%'""")

# ---------------------------------------------------------------- quantidade de ações
partes = [f"SELECT *, '{t.upper()}' AS documento FROM {ler(os.path.join(ORIGEM, t, 'composicao_capital.csv'))}"
          for t in ("dfp", "itr")]
con.execute(f"""CREATE OR REPLACE TABLE composicao_capital AS
WITH u AS (SELECT *, TRY_CAST(VERSAO AS INTEGER) AS v, TRY_CAST(DT_REFER AS DATE) AS ref,
                  -- a CVM não informa a escala: parte das empresas preenche em milhares (Taesa: 1.033.497 = 1,03 bi)
                  CASE WHEN TRY_CAST(QT_ACAO_TOTAL_CAP_INTEGR AS BIGINT) < 100000000 THEN 1000 ELSE 1 END AS fator
           FROM ({" UNION ALL ".join(partes)}))
SELECT CNPJ_CIA AS cnpj, DENOM_CIA AS empresa, ref AS data_referencia, year(ref) AS ano, documento, v AS versao,
       TRY_CAST(QT_ACAO_ORDIN_CAP_INTEGR AS BIGINT) * fator AS acoes_ordinarias,
       TRY_CAST(QT_ACAO_PREF_CAP_INTEGR AS BIGINT) * fator AS acoes_preferenciais,
       TRY_CAST(QT_ACAO_TOTAL_CAP_INTEGR AS BIGINT) * fator AS acoes_total,
       TRY_CAST(QT_ACAO_ORDIN_TESOURO AS BIGINT) * fator AS tesouraria_ordinarias,
       TRY_CAST(QT_ACAO_PREF_TESOURO AS BIGINT) * fator AS tesouraria_preferenciais,
       TRY_CAST(QT_ACAO_TOTAL_TESOURO AS BIGINT) * fator AS tesouraria_total,
       'CVM ' || documento || ' ' || year(ref) || ', composição do capital' AS fonte
FROM u
WHERE TRY_CAST(QT_ACAO_TOTAL_CAP_INTEGR AS BIGINT) > 0  -- há entregas com o quadro zerado (CPFL)
QUALIFY v = max(v) OVER (PARTITION BY CNPJ_CIA, DT_REFER, documento)""")
n = con.execute("SELECT count(*) FROM composicao_capital").fetchone()[0]
con.execute("DELETE FROM catalogo WHERE tabela = 'composicao_capital'")
con.execute("INSERT INTO catalogo VALUES (?, ?, ?, ?, ?)", (
    "composicao_capital",
    "Quantidade de ações (ordinárias, preferenciais e total) do capital integralizado e em tesouraria, por data de "
    "referência da DFP (anual) e do ITR (trimestral), 2020 em diante, para Axia, Cemig, Copel, CPFL, Energisa, Eneva, "
    "Engie, Equatorial, ISA Energia, Neoenergia e Taesa. Use para valores por ação (lucro por ação, dividendo por ação).",
    "CVM, DFP e ITR (dados.cvm.gov.br), composição do capital",
    "ações em circulação = acoes_total - tesouraria_total. A CVM não informa a escala e parte das empresas preenche em "
    "milhares: registros com menos de 100 milhões de ações foram multiplicados por 1.000", n))
print(f"\ncomposicao_capital: {n} linhas")
mostrar("composicao_capital: ações por empresa ao longo do tempo (min e max devem ser da mesma ordem de grandeza)", """
SELECT cnpj, any_value(empresa) AS empresa, min(data_referencia) AS de, max(data_referencia) AS ate,
       min(acoes_total) AS min_acoes, max(acoes_total) AS max_acoes,
       arg_max(acoes_total, data_referencia) AS ultima, arg_max(tesouraria_total, data_referencia) AS ultima_tesouraria
FROM composicao_capital GROUP BY cnpj ORDER BY cnpj""")

con.close()
os.replace(tmp, destino)
print("\nok:", destino)

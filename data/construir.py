"""Monta o banco DuckDB da plataforma a partir dos arquivos brutos: tabelas tipadas, unidade no nome da coluna e fonte.

Uso: python data/construir.py
Entradas (data/raw, trazidas por data/baixar.py e pelo rclone do Drive):
  cvm/dfp/dfp_cia_aberta_AAAA.zip, cvm/fca/fca_cia_aberta_AAAA.zip, cvm/cad_cia_aberta.csv, cvm/anbima_deb.xlsx
  aneel_ons_epe_bndes/*.csv  e  data/parquet/reg_decfec.parquet (compensações de continuidade; o CSV tem 1 GB)
Saída: data/coppezip.duckdb, trocado de forma atômica (os servidores MCP abrem só para leitura).
"""
import csv
import glob
import os
import re
import shutil
import tempfile
import zipfile

import duckdb
import openpyxl

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raiz do repositório


DADOS = os.path.join(RAIZ, "data")
RAW = os.path.join(DADOS, "raw")
ANEEL = os.path.join(RAW, "aneel_ons_epe_bndes")
destino = os.path.join(DADOS, "coppezip.duckdb")
tmp = destino + ".tmp"
if os.path.exists(tmp):
    os.remove(tmp)
trabalho = tempfile.mkdtemp(prefix="build_", dir=DADOS)
con = duckdb.connect(tmp)
CATALOGO = []  # (tabela, descricao, fonte, ressalvas)


def tabela(nome, sql, descricao, fonte, ressalvas=""):
    con.execute(f"CREATE OR REPLACE TABLE {nome} AS {sql}")
    n = con.execute(f"SELECT count(*) FROM {nome}").fetchone()[0]
    CATALOGO.append((nome, descricao, fonte, ressalvas, n))
    print(f"{nome}: {n} linhas")


def csv_limpo(arquivo, codificacao):
    """Regrava um CSV do governo em UTF-8 limpo (sem NUL, aspas consistentes), que o DuckDB lê sem tropeçar."""
    saida = os.path.join(trabalho, os.path.basename(arquivo))
    with open(arquivo, encoding=codificacao, errors="replace", newline="") as f, open(saida, "w", newline="") as g:
        leitor = csv.reader((linha.replace("\0", "") for linha in f), delimiter=";")
        escritor = csv.writer(g, delimiter=";", quoting=csv.QUOTE_ALL)
        for linha in leitor:
            escritor.writerow(linha)
    return f"read_csv('{saida}', delim=';', header=true, all_varchar=true, quote='\"', escape='\"')"


# Números brasileiros ("1.234,56", ",72") e CNPJ sem máscara ("8635011000150") para o formato do cadastro da CVM
con.execute(r"""CREATE MACRO num_br(x) AS TRY_CAST(replace(replace(trim(x), '.', ''), ',', '.') AS DOUBLE)""")
con.execute(r"""CREATE MACRO digitos14(x) AS lpad(regexp_replace(x, '\D', '', 'g'), 14, '0')""")
con.execute(r"""CREATE MACRO fmt_cnpj(x) AS CASE WHEN length(regexp_replace(coalesce(x, ''), '\D', '', 'g')) BETWEEN 11 AND 14 THEN
  substr(digitos14(x), 1, 2) || '.' || substr(digitos14(x), 3, 3) || '.' || substr(digitos14(x), 6, 3) || '/'
  || substr(digitos14(x), 9, 4) || '-' || substr(digitos14(x), 13, 2) END""")
con.execute(r"""CREATE MACRO data_br(x) AS COALESCE(TRY_CAST(x AS DATE), TRY_CAST(try_strptime(trim(x), '%d/%m/%Y') AS DATE))""")

# ---------------------------------------------------------------- cadastro, tickers e apelidos
cad = os.path.join(RAW, "cvm", "cad_cia_aberta.csv")
tabela("empresas", f"""
SELECT CNPJ_CIA AS cnpj, DENOM_SOCIAL AS nome_social, DENOM_COMERC AS nome_comercial, CD_CVM AS cd_cvm,
       SIT AS situacao, SETOR_ATIV AS setor, CONTROLE_ACIONARIO AS controle_acionario, UF AS uf, MUN AS municipio,
       AUDITOR AS auditor
FROM read_csv('{cad}', delim=';', header=true, encoding='latin-1', all_varchar=true)
WHERE SETOR_ATIV ILIKE '%energia el%'
QUALIFY row_number() OVER (PARTITION BY CNPJ_CIA ORDER BY (SIT = 'ATIVO') DESC, TRY_CAST(DT_REG AS DATE) DESC NULLS LAST) = 1
""", "Companhias abertas do setor elétrico registradas na CVM (uma linha por CNPJ). Use buscar_empresa para achar o CNPJ.",
    "CVM, cadastro de companhias abertas (cad_cia_aberta.csv)")

fca = sorted(glob.glob(os.path.join(RAW, "cvm", "fca", "fca_cia_aberta_*.zip")))[-1]
with zipfile.ZipFile(fca) as z:
    nome = next(n for n in z.namelist() if "valor_mobiliario" in n)
    z.extract(nome, trabalho)
vm = os.path.join(trabalho, nome)
con.execute(f"""CREATE TEMP TABLE tickers AS
SELECT DISTINCT CNPJ_Companhia AS cnpj, upper(trim(Codigo_Negociacao)) AS ticker, Valor_Mobiliario AS tipo, Segmento AS segmento
FROM read_csv('{vm}', delim=';', header=true, encoding='latin-1', all_varchar=true)
WHERE coalesce(trim(Codigo_Negociacao), '') <> '' AND coalesce(Data_Fim_Negociacao, '') = ''
  AND CNPJ_Companhia IN (SELECT cnpj FROM empresas)""")

# Nomes pelos quais o mercado chama as empresas; o padrão é casado com o nome social do cadastro na montagem
APELIDOS = [
    ("Eletrobras", "^AXIA ENERGIA S\\.A\\.$", "Eletrobras passou a se chamar Axia Energia em 2025 (holding)"),
    ("Axia", "^AXIA ENERGIA S\\.A\\.$", "holding do grupo Axia, ex-Eletrobras"),
    ("Chesf", "^AXIA ENERGIA NORDESTE", "ex-Chesf, subsidiária da Axia"),
    ("Eletronorte", "^AXIA ENERGIA NORTE", "ex-Eletronorte, subsidiária da Axia"),
    ("Eletrosul", "^AXIA ENERGIA SUL", "ex-CGT Eletrosul, subsidiária da Axia"),
    ("Furnas", "^AXIA ENERGIA S\\.A\\.$", "Furnas não tem registro próprio na CVM: é do grupo Axia (ex-Eletrobras)"),
    ("Taesa", "^TRANSMISSORA ALIAN.A DE ENERGIA EL.TRICA", "holding de transmissão"),
    ("ISA CTEEP", "^ISA ENERGIA BRASIL", "ISA CTEEP passou a se chamar ISA Energia Brasil em 2024"),
    ("CTEEP", "^ISA ENERGIA BRASIL", "ex-CTEEP"),
    ("ISA Energia", "^ISA ENERGIA BRASIL", ""),
    ("Cemig", "MINAS GERAIS - CEMIG$", "holding do grupo Cemig"),
    ("Cemig D", "^CEMIG DISTRIBUI", "distribuidora do grupo Cemig"),
    ("Cemig GT", "^CEMIG GERA", "geração e transmissão do grupo Cemig"),
    ("Copel", "^(COMPANHIA|CIA) PARANAENSE DE ENERGIA", "holding do grupo Copel"),
    ("CPFL", "^CPFL ENERGIA S", "holding do grupo CPFL"),
    ("CPFL Paulista", "PAULISTA DE FOR.A (E )?LUZ", "distribuidora do grupo CPFL"),
    ("CPFL Piratininga", "PIRATININGA", "distribuidora do grupo CPFL"),
    ("RGE", "^RGE SUL", "distribuidora do grupo CPFL"),
    ("CPFL Renováveis", "^CPFL ENERGIAS RENOV", "geração renovável do grupo CPFL"),
    ("Engie", "^ENGIE BRASIL ENERGIA", "holding do grupo Engie no Brasil"),
    ("Tractebel", "^ENGIE BRASIL ENERGIA", "Tractebel Energia é o nome antigo (até 2016) da atual Engie Brasil Energia"),
    ("Equatorial", "^EQUATORIAL S\\.A\\.$", "holding do grupo Equatorial"),
    ("Neoenergia", "^NEOENERGIA S\\.A\\.?$", "holding do grupo Neoenergia"),
    ("Coelba", "ELETRICIDADE DO ESTADO DA BAHIA", "distribuidora do grupo Neoenergia"),
    ("Neoenergia Pernambuco", "ENERG.TICA DE PERNAMBUCO", "Neoenergia Pernambuco = Celpe"),
    ("Neoenergia Bahia", "ELETRICIDADE DO ESTADO DA BAHIA", "Neoenergia Coelba"),
    ("Enel Rio", "^AMPLA ENERGIA", "Enel Distribuição Rio = Ampla"),
    ("Enel Ceará", "COELCE", "Enel Distribuição Ceará = Coelce"),
    ("Enel São Paulo", "ELETROPAULO", "Enel Distribuição São Paulo = Eletropaulo"),
    ("Celpe", "ENERG.TICA DE PERNAMBUCO", "distribuidora do grupo Neoenergia"),
    ("Cosern", "ENERG.TICA DO RIO GRANDE DO NORTE", "distribuidora do grupo Neoenergia"),
    ("Elektro", "^ELEKTRO REDES", "distribuidora do grupo Neoenergia"),
    ("Energisa", "^ENERGISA S\\.?A\\.?$", "holding do grupo Energisa"),
    ("EDP Brasil", "^EDP .? ?ENERGIAS DO BRASIL", "holding do grupo EDP"),
    ("EDP São Paulo", "^EDP S.O PAULO", "distribuidora do grupo EDP"),
    ("EDP Espírito Santo", "^EDP ESP.RITO SANTO", "distribuidora do grupo EDP"),
    ("Enel SP", "ELETROPAULO", "Enel Distribuição São Paulo = Eletropaulo"),
    ("Eletropaulo", "ELETROPAULO", "hoje Enel Distribuição São Paulo"),
    ("Enel RJ", "^AMPLA ENERGIA", "Enel Distribuição Rio = Ampla"),
    ("Enel CE", "COELCE", "Enel Distribuição Ceará = Coelce"),
    ("Coelce", "COELCE", "hoje Enel Distribuição Ceará"),
    ("Light", "^LIGHT S\\.?A\\.?( -|$)", "holding do grupo Light (em recuperação judicial)"),
    ("Alupar", "^ALUPAR", "holding de transmissão e geração"),
    ("Auren", "^AUREN ENERGIA", "holding do grupo Auren (Votorantim/CPP), incorporou a AES Brasil"),
    ("AES Brasil", "^AUREN ENERGIA", "a AES Brasil foi incorporada pela Auren em 2024"),
    ("Cesp", "^CESP", "grupo Auren"),
    ("Eneva", "^ENEVA", ""),
    ("Celesc", "^CENTRAIS EL.TRICAS DE SANTA CATARINA", "holding do grupo Celesc"),
    ("CEEE", "CEEE", "distribuição (Equatorial) e transmissão (CPFL) no RS"),
    ("Omega", "^(OMEGA|SERENA) ENERGIA", "Omega Energia passou a se chamar Serena Energia"),
    ("Serena", "^SERENA ENERGIA", "ex-Omega Energia"),
    ("Celg", "^EQUATORIAL GOI", "Celg D, hoje Equatorial Goiás"),
    ("Celpa", "^EQUATORIAL PAR", "hoje Equatorial Pará"),
    ("Cemar", "^EQUATORIAL MARANH", "hoje Equatorial Maranhão"),
]
linhas = []
for apelido, padrao, obs in APELIDOS:
    achados = con.execute(
        "SELECT cnpj, nome_social FROM empresas WHERE regexp_matches(upper(nome_social), ?) ORDER BY (situacao = 'ATIVO') DESC",
        [padrao]).fetchall()
    if not achados:
        print(f"  aviso: apelido sem empresa no cadastro: {apelido} ({padrao})")
    for cnpj, _ in achados:
        linhas.append((apelido, cnpj, "apelido", obs))
con.execute("CREATE TEMP TABLE apelidos_manuais (apelido VARCHAR, cnpj VARCHAR, tipo VARCHAR, observacao VARCHAR)")
con.executemany("INSERT INTO apelidos_manuais VALUES (?, ?, ?, ?)", linhas)
tabela("empresas_apelidos", """
SELECT apelido, cnpj, tipo, observacao FROM apelidos_manuais
UNION ALL SELECT ticker, cnpj, 'ticker', tipo || coalesce(' · ' || segmento, '') FROM tickers
UNION ALL SELECT DISTINCT regexp_replace(ticker, '\\d+$', ''), cnpj, 'ticker', 'raiz do ticker' FROM tickers
""", "Apelidos, marcas, nomes antigos e tickers da B3 de cada empresa, ligados ao CNPJ (base da ferramenta buscar_empresa).",
    "CVM FCA (valores mobiliários negociados) e lista curada de apelidos")

# ---------------------------------------------------------------- CVM: demonstrações de 2020 em diante
DEMOS = ["BPA", "BPP", "DRE", "DFC_MI", "DFC_MD", "DVA"]
arquivos = []
for zp in sorted(glob.glob(os.path.join(RAW, "cvm", "dfp", "dfp_cia_aberta_*.zip"))):
    with zipfile.ZipFile(zp) as z:
        for n in z.namelist():
            m = re.match(r"dfp_cia_aberta_(\w+?)_(con|ind)_(\d{4})\.csv$", n)
            if m and m.group(1) in DEMOS:
                z.extract(n, trabalho)
                arquivos.append((os.path.join(trabalho, n), m.group(1), m.group(2)))
partes = [f"""SELECT *, '{d}' AS demonstrativo, '{'consolidado' if e == 'con' else 'individual'}' AS escopo
FROM read_csv('{a}', delim=';', header=true, encoding='latin-1', all_varchar=true)
WHERE CNPJ_CIA IN (SELECT cnpj FROM empresas)""" for a, d, e in arquivos]
con.execute("CREATE TEMP TABLE dfp_bruto AS " + " UNION ALL BY NAME ".join(partes))
tabela("contas_cvm", """
WITH u AS (
  SELECT *, TRY_CAST(VERSAO AS INTEGER) AS v FROM dfp_bruto
  WHERE ORDEM_EXERC = 'ÚLTIMO' AND CNPJ_CIA IN (SELECT cnpj FROM empresas))
SELECT CNPJ_CIA AS cnpj, CD_CVM AS cd_cvm, DENOM_CIA AS empresa, year(TRY_CAST(DT_REFER AS DATE)) AS ano,
       TRY_CAST(DT_REFER AS DATE) AS data_referencia, demonstrativo, escopo, CD_CONTA AS cd_conta, DS_CONTA AS ds_conta,
       TRY_CAST(VL_CONTA AS DOUBLE) * CASE WHEN ESCALA_MOEDA = 'MIL' THEN 1000 ELSE 1 END AS valor_brl,
       v AS versao, 'CVM DFP ' || year(TRY_CAST(DT_REFER AS DATE)) || ', ' || demonstrativo || ' ' || escopo
         || ', conta ' || CD_CONTA AS fonte
FROM u
QUALIFY v = max(v) OVER (PARTITION BY CNPJ_CIA, DT_REFER, demonstrativo, escopo)
""", "Todas as contas das demonstrações financeiras anuais (DFP) das empresas do setor, de 2020 em diante, já em R$ "
     "(escala MIL aplicada), última versão entregue. demonstrativo: BPA, BPP, DRE, DFC_MI, DFC_MD, DVA; escopo: "
     "consolidado ou individual. Prefira kpis_financeiros para indicadores prontos.",
    "CVM, DFP (dados.cvm.gov.br)", "valores em reais; despesas e saídas de caixa vêm negativas")

tabela("kpis_financeiros", r"""
WITH esc AS (
  SELECT cnpj, ano, CASE WHEN bool_or(escopo = 'consolidado') THEN 'consolidado' ELSE 'individual' END AS escopo
  FROM contas_cvm GROUP BY ALL),
c AS (SELECT c.* FROM contas_cvm c JOIN esc USING (cnpj, ano, escopo)),
capex_contas AS (
  SELECT * FROM c WHERE demonstrativo LIKE 'DFC%' AND regexp_matches(cd_conta, '^6\.02\.\d+$')
    AND regexp_matches(lower(ds_conta), 'imobilizad|intang|ativos? de contrato|ativos? contratua|infraestrutura|obras')
    AND NOT regexp_matches(lower(ds_conta), 'venda|aliena|baixa|receb|resgate')),
a AS (
  SELECT cnpj, ano, any_value(escopo) AS escopo, any_value(empresa) AS empresa,
    sum(valor_brl) FILTER (demonstrativo = 'DRE' AND cd_conta = '3.01') AS receita_liquida_brl,
    sum(valor_brl) FILTER (demonstrativo = 'DRE' AND cd_conta = '3.05') AS ebit_brl,
    sum(valor_brl) FILTER (demonstrativo = 'DRE' AND cd_conta = '3.06') AS resultado_financeiro_brl,
    sum(valor_brl) FILTER (demonstrativo = 'DRE' AND cd_conta = '3.06.02') AS despesas_financeiras_brl,
    sum(valor_brl) FILTER (demonstrativo = 'DRE' AND cd_conta = '3.11') AS lucro_liquido_brl,
    sum(valor_brl) FILTER (demonstrativo = 'BPA' AND cd_conta = '1') AS ativo_total_brl,
    sum(valor_brl) FILTER (demonstrativo = 'BPA' AND cd_conta IN ('1.01.01', '1.01.02')) AS caixa_aplicacoes_brl,
    sum(valor_brl) FILTER (demonstrativo = 'BPP' AND cd_conta IN ('2.01.04', '2.02.01')) AS divida_bruta_brl,
    sum(valor_brl) FILTER (demonstrativo = 'BPP' AND cd_conta = '2.03') AS patrimonio_liquido_brl,
    sum(abs(valor_brl)) FILTER (demonstrativo LIKE 'DFC%' AND regexp_matches(cd_conta, '^6\.01\.01\.\d+$')
        AND regexp_matches(lower(ds_conta), 'deprecia|amortiza')
        AND NOT regexp_matches(lower(ds_conta), 'capta|transa|juros|empr.stimo|deb.nture|financ')) AS depreciacao_amortizacao_brl,
    sum(valor_brl) FILTER (demonstrativo LIKE 'DFC%' AND cd_conta = '6.01') AS caixa_operacional_brl,
    sum(valor_brl) FILTER (demonstrativo LIKE 'DFC%' AND regexp_matches(cd_conta, '^6\.03\.\d+$')
        AND regexp_matches(lower(ds_conta), 'dividend|juros sobre (o )?capital')) AS dividendos_jcp_fluxo_brl
  FROM c GROUP BY cnpj, ano),
k AS (SELECT cnpj, ano, -sum(valor_brl) AS capex_brl, string_agg(cd_conta || ' ' || ds_conta, ' | ') AS contas_capex
      FROM capex_contas GROUP BY cnpj, ano),
obra AS (  -- concessões (IFRS 15 / ICPC 01): a obra aparece como custo de construção, não como CAPEX de caixa
  SELECT cnpj, ano, coalesce(
           sum(abs(valor_brl)) FILTER (demonstrativo LIKE 'DFC%' AND regexp_matches(cd_conta, '^6\.01\.01\.\d+$')
                                       AND regexp_matches(lower(ds_conta), 'custo.{0,20}(implementa|constru)')),
           sum(abs(valor_brl)) FILTER (demonstrativo = 'DRE' AND regexp_matches(cd_conta, '^3\.02\.\d+$')
                                       AND regexp_matches(lower(ds_conta), 'custo.{0,20}(infraestrutura|constru|implementa)')
                                       AND NOT regexp_matches(lower(ds_conta), 'opera|manuten'))) AS custo_construcao_brl
  FROM c GROUP BY cnpj, ano)
SELECT a.cnpj, a.empresa, a.ano, a.escopo, receita_liquida_brl, ebit_brl, depreciacao_amortizacao_brl,
       ebit_brl + depreciacao_amortizacao_brl AS ebitda_brl, resultado_financeiro_brl, despesas_financeiras_brl,
       lucro_liquido_brl, ativo_total_brl, patrimonio_liquido_brl, divida_bruta_brl, caixa_aplicacoes_brl,
       divida_bruta_brl - caixa_aplicacoes_brl AS divida_liquida_brl, caixa_operacional_brl, k.capex_brl,
       obra.custo_construcao_brl AS custo_construcao_concessao_brl,
       greatest(coalesce(k.capex_brl, 0), coalesce(obra.custo_construcao_brl, 0)) AS investimento_total_brl,
       -dividendos_jcp_fluxo_brl AS dividendos_jcp_pagos_brl,
       round(100 * ebit_brl / nullif(receita_liquida_brl, 0), 2) AS margem_ebit_pct,
       round(100 * (ebit_brl + depreciacao_amortizacao_brl) / nullif(receita_liquida_brl, 0), 2) AS margem_ebitda_pct,
       round(100 * lucro_liquido_brl / nullif(receita_liquida_brl, 0), 2) AS margem_liquida_pct,
       round((divida_bruta_brl - caixa_aplicacoes_brl) / nullif(ebit_brl + depreciacao_amortizacao_brl, 0), 2) AS divida_liquida_ebitda,
       round((ebit_brl + depreciacao_amortizacao_brl) / nullif(abs(despesas_financeiras_brl), 0), 2) AS cobertura_juros_ebitda,
       round(100 * lucro_liquido_brl / nullif(patrimonio_liquido_brl, 0), 2) AS roe_pct,
       k.contas_capex,
       'CVM DFP ' || a.ano || ' (' || a.escopo || '): receita 3.01, EBIT 3.05, lucro 3.11, desp. financeiras 3.06.02; '
         || 'dívida bruta 2.01.04+2.02.01; caixa 1.01.01+1.01.02; PL 2.03; D&A, caixa operacional (6.01), CAPEX (6.02) '
         || 'e dividendos (6.03) da DFC' AS fonte
FROM a LEFT JOIN k USING (cnpj, ano) LEFT JOIN obra USING (cnpj, ano)
""", "Indicadores financeiros anuais por empresa (2020 em diante), em R$, prontos para comparar: receita, EBIT, "
     "EBITDA calculado, lucro, dívida bruta e líquida, caixa, CAPEX, dividendos, margens, alavancagem, cobertura de juros e ROE. "
     "Usa o consolidado quando a empresa o publica.",
    "CVM DFP; cálculo desta plataforma a partir das contas indicadas na coluna fonte",
    "EBITDA = EBIT (3.05) + depreciação e amortização da DFC; pode diferir do EBITDA ajustado que a empresa divulga. "
    "3.05 é EBIT, nunca chame de EBITDA. Dívida bruta = empréstimos, financiamentos e debêntures (2.01.04 + 2.02.01), sem "
    "arrendamentos. capex_brl soma as saídas de caixa de imobilizado, intangível e ativo de contrato (6.02, contas em "
    "contas_capex). Concessões (IFRS 15 / ICPC 01) lançam a obra como custo de construção: custo_construcao_concessao_brl. "
    "Para 'quanto investiu', use investimento_total_brl (o maior dos dois, sem somar para não contar duas vezes).")

# ---------------------------------------------------------------- CVM: demonstrações trimestrais (ITR)
arquivos_itr = []
for zp in sorted(glob.glob(os.path.join(RAW, "cvm", "itr", "itr_cia_aberta_*.zip"))):
    with zipfile.ZipFile(zp) as z:
        for n in z.namelist():
            m = re.match(r"itr_cia_aberta_(\w+?)_(con|ind)_(\d{4})\.csv$", n)
            if m and m.group(1) in DEMOS:
                z.extract(n, trabalho)
                arquivos_itr.append((os.path.join(trabalho, n), m.group(1), m.group(2)))
if arquivos_itr:
    partes = [f"""SELECT *, '{d}' AS demonstrativo, '{'consolidado' if e == 'con' else 'individual'}' AS escopo
FROM read_csv('{a}', delim=';', header=true, encoding='latin-1', all_varchar=true)
WHERE CNPJ_CIA IN (SELECT cnpj FROM empresas)""" for a, d, e in arquivos_itr]
    con.execute("CREATE TEMP TABLE itr_bruto AS " + " UNION ALL BY NAME ".join(partes))
    tabela("contas_cvm_trimestral", """
WITH u AS (SELECT *, TRY_CAST(VERSAO AS INTEGER) AS v, TRY_CAST(DT_REFER AS DATE) AS ref,
                  TRY_CAST(DT_INI_EXERC AS DATE) AS ini, TRY_CAST(DT_FIM_EXERC AS DATE) AS fim
           FROM itr_bruto WHERE ORDEM_EXERC = 'ÚLTIMO')
SELECT CNPJ_CIA AS cnpj, CD_CVM AS cd_cvm, DENOM_CIA AS empresa, ref AS data_referencia, year(ref) AS ano,
       quarter(ref) AS trimestre, demonstrativo, escopo,
       CASE WHEN demonstrativo IN ('BPA', 'BPP') THEN 'saldo'
            WHEN ini = make_date(year(ref), 1, 1) THEN 'acumulado' ELSE 'trimestre' END AS periodo,
       ini AS inicio_periodo, coalesce(fim, ref) AS fim_periodo, CD_CONTA AS cd_conta, DS_CONTA AS ds_conta,
       TRY_CAST(VL_CONTA AS DOUBLE) * CASE WHEN ESCALA_MOEDA = 'MIL' THEN 1000 ELSE 1 END AS valor_brl, v AS versao,
       'CVM ITR ' || year(ref) || 'T' || quarter(ref) || ', ' || demonstrativo || ' ' || escopo || ', conta ' || CD_CONTA AS fonte
FROM u
QUALIFY v = max(v) OVER (PARTITION BY CNPJ_CIA, DT_REFER, demonstrativo, escopo)
""", "Contas das demonstrações trimestrais (ITR) de 2024 em diante, em R$: periodo = trimestre (só os 3 meses), "
     "acumulado (desde janeiro) ou saldo (balanço no fim do trimestre). O 4º trimestre não existe no ITR: está na DFP anual.",
        "CVM, ITR (dados.cvm.gov.br)", "valores em reais; despesas e saídas de caixa vêm negativas; a DFC do ITR é acumulada")
    tabela("kpis_trimestrais", r"""
WITH esc AS (SELECT cnpj, data_referencia,
                    CASE WHEN bool_or(escopo = 'consolidado') THEN 'consolidado' ELSE 'individual' END AS escopo
             FROM contas_cvm_trimestral GROUP BY ALL),
c AS (SELECT c.* FROM contas_cvm_trimestral c JOIN esc USING (cnpj, data_referencia, escopo)),
q AS (
  SELECT cnpj, data_referencia, any_value(ano) AS ano, any_value(trimestre) AS trimestre, any_value(escopo) AS escopo,
    any_value(empresa) AS empresa,
    sum(valor_brl) FILTER (demonstrativo = 'DRE' AND cd_conta = '3.01' AND (periodo = 'trimestre' OR (trimestre = 1 AND periodo = 'acumulado'))) AS receita_liquida_trimestre_brl,
    sum(valor_brl) FILTER (demonstrativo = 'DRE' AND cd_conta = '3.05' AND (periodo = 'trimestre' OR (trimestre = 1 AND periodo = 'acumulado'))) AS ebit_trimestre_brl,
    sum(valor_brl) FILTER (demonstrativo = 'DRE' AND cd_conta = '3.11' AND (periodo = 'trimestre' OR (trimestre = 1 AND periodo = 'acumulado'))) AS lucro_trimestre_brl,
    sum(valor_brl) FILTER (demonstrativo = 'DRE' AND cd_conta = '3.01' AND periodo = 'acumulado') AS receita_liquida_acumulada_brl,
    sum(valor_brl) FILTER (demonstrativo = 'DRE' AND cd_conta = '3.05' AND periodo = 'acumulado') AS ebit_acumulado_brl,
    sum(valor_brl) FILTER (demonstrativo = 'DRE' AND cd_conta = '3.11' AND periodo = 'acumulado') AS lucro_acumulado_brl,
    sum(valor_brl) FILTER (demonstrativo = 'DRE' AND cd_conta = '3.06.02' AND periodo = 'acumulado') AS despesas_financeiras_acumuladas_brl,
    sum(abs(valor_brl)) FILTER (demonstrativo LIKE 'DFC%' AND regexp_matches(cd_conta, '^6\.01\.01\.\d+$')
        AND regexp_matches(lower(ds_conta), 'deprecia|amortiza')
        AND NOT regexp_matches(lower(ds_conta), 'capta|transa|juros|empr.stimo|deb.nture|financ')) AS da_acumulada_brl,
    sum(valor_brl) FILTER (demonstrativo = 'BPP' AND cd_conta IN ('2.01.04', '2.02.01')) AS divida_bruta_brl,
    sum(valor_brl) FILTER (demonstrativo = 'BPA' AND cd_conta IN ('1.01.01', '1.01.02')) AS caixa_aplicacoes_brl,
    sum(valor_brl) FILTER (demonstrativo = 'BPP' AND cd_conta = '2.03') AS patrimonio_liquido_brl,
    -sum(valor_brl) FILTER (demonstrativo LIKE 'DFC%' AND regexp_matches(cd_conta, '^6\.02\.\d+$')
        AND regexp_matches(lower(ds_conta), 'imobilizad|intang|ativos? de contrato|ativos? contratua|infraestrutura|obras')
        AND NOT regexp_matches(lower(ds_conta), 'venda|aliena|baixa|receb|resgate')) AS capex_acumulado_brl,
    coalesce(
      sum(abs(valor_brl)) FILTER (demonstrativo LIKE 'DFC%' AND regexp_matches(cd_conta, '^6\.01\.01\.\d+$')
                                  AND regexp_matches(lower(ds_conta), 'custo.{0,20}(implementa|constru)')),
      sum(abs(valor_brl)) FILTER (demonstrativo = 'DRE' AND periodo = 'acumulado' AND regexp_matches(cd_conta, '^3\.02\.\d+$')
                                  AND regexp_matches(lower(ds_conta), 'custo.{0,20}(infraestrutura|constru|implementa)')
                                  AND NOT regexp_matches(lower(ds_conta), 'opera|manuten'))) AS custo_construcao_acumulado_brl
  FROM c GROUP BY cnpj, data_referencia)
SELECT q.cnpj, q.empresa, q.ano, q.trimestre, q.data_referencia, q.escopo,
       q.receita_liquida_trimestre_brl, q.ebit_trimestre_brl, q.lucro_trimestre_brl,
       q.receita_liquida_acumulada_brl, q.ebit_acumulado_brl, q.ebit_acumulado_brl + q.da_acumulada_brl AS ebitda_acumulado_brl,
       q.lucro_acumulado_brl,
       q.receita_liquida_acumulada_brl + a.receita_liquida_brl - p.receita_liquida_acumulada_brl AS receita_liquida_12m_brl,
       (q.ebit_acumulado_brl + q.da_acumulada_brl) + a.ebitda_brl - (p.ebit_acumulado_brl + p.da_acumulada_brl) AS ebitda_12m_brl,
       q.lucro_acumulado_brl + a.lucro_liquido_brl - p.lucro_acumulado_brl AS lucro_12m_brl,
       q.divida_bruta_brl, q.caixa_aplicacoes_brl, q.divida_bruta_brl - q.caixa_aplicacoes_brl AS divida_liquida_brl,
       round((q.divida_bruta_brl - q.caixa_aplicacoes_brl)
             / nullif((q.ebit_acumulado_brl + q.da_acumulada_brl) + a.ebitda_brl - (p.ebit_acumulado_brl + p.da_acumulada_brl), 0), 2)
         AS divida_liquida_ebitda_12m,
       q.patrimonio_liquido_brl, q.capex_acumulado_brl, q.custo_construcao_acumulado_brl,
       greatest(coalesce(q.capex_acumulado_brl, 0), coalesce(q.custo_construcao_acumulado_brl, 0)) AS investimento_acumulado_brl,
       'CVM ITR ' || q.ano || 'T' || q.trimestre || ' (' || q.escopo || '); últimos 12 meses = acumulado do ano + DFP '
         || (q.ano - 1) || ' - acumulado do mesmo trimestre de ' || (q.ano - 1) AS fonte
FROM q
LEFT JOIN kpis_financeiros a ON a.cnpj = q.cnpj AND a.ano = q.ano - 1
LEFT JOIN q p ON p.cnpj = q.cnpj AND p.ano = q.ano - 1 AND p.trimestre = q.trimestre
""", "Indicadores trimestrais (ITR) de 2024 em diante: receita, EBIT e lucro do trimestre e acumulados no ano, EBITDA, "
     "valores dos últimos 12 meses, dívida bruta e líquida no fim do trimestre, dívida líquida/EBITDA 12 meses e "
     "investimento acumulado. É o dado mais recente da base (a DFP anual vai até 2025).",
        "CVM ITR e DFP; cálculo desta plataforma", "12 meses só existem quando há o ITR do mesmo trimestre do ano anterior; "
        "EBITDA = EBIT + depreciação e amortização da DFC; investimento_acumulado_brl segue a regra de investimento_total_brl")

# ---------------------------------------------------------------- ANEEL: usinas (SIGA) e seus donos
siga = f"read_csv('{os.path.join(ANEEL, 'siga.csv')}', delim=';', header=true, all_varchar=true)"
tabela("usinas", f"""
SELECT CodCEG AS ceg, NomEmpreendimento AS nome, SigUFPrincipal AS uf, SigTipoGeracao AS tipo_geracao,
       DscFaseUsina AS fase, DscOrigemCombustivel AS origem, DscFonteCombustivel AS fonte_energia,
       DscTipoOutorga AS tipo_outorga, TRY_CAST(DatEntradaOperacao AS DATE) AS data_entrada_operacao,
       num_br(MdaPotenciaOutorgadaKw) AS potencia_outorgada_kw, num_br(MdaPotenciaFiscalizadaKw) AS potencia_fiscalizada_kw,
       num_br(MdaGarantiaFisicaKw) AS garantia_fisica_kw, num_br(NumCoordNEmpreendimento) AS latitude,
       num_br(NumCoordEEmpreendimento) AS longitude, trim(DscSubBacia) AS sub_bacia, DscMuninicpios AS municipios,
       DscPropriRegimePariticipacao AS proprietarios_texto, TRY_CAST(DatGeracaoConjuntoDados AS DATE) AS data_base
FROM {siga}
""", "Usinas de geração do Brasil (SIGA/ANEEL), uma linha por usina: tipo (UHE, PCH, CGH, EOL, UFV, UTE, UTN), fase "
     "(Operação, Construção, Construção não iniciada), origem (Hídrica, Eólica, Solar, Fóssil, Biomassa, Nuclear), potência em kW.",
    "ANEEL SIGA (dados abertos), data em data_base", "potência em kW (divida por 1000 para MW); donos em usinas_proprietarios")

PADRAO_DONO = r"([0-9]+(?:[.,][0-9]+)?)% para (.+?) - ([0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2}|[0-9]{3}\.[0-9]{3}\.[0-9]{3}-[0-9]{2}) \(([A-Z]+)\)"
tabela("usinas_proprietarios", f"""
WITH m AS (SELECT ceg, unnest(regexp_extract_all(proprietarios_texto, '{PADRAO_DONO}')) AS trecho FROM usinas)
SELECT ceg, regexp_extract(trecho, '{PADRAO_DONO}', 3) AS cnpj, trim(regexp_extract(trecho, '{PADRAO_DONO}', 2)) AS proprietario,
       TRY_CAST(replace(regexp_extract(trecho, '{PADRAO_DONO}', 1), ',', '.') AS DOUBLE) AS participacao_pct,
       regexp_extract(trecho, '{PADRAO_DONO}', 4) AS regime
FROM m
""", "Donos de cada usina do SIGA com CNPJ e percentual de participação (uma linha por usina e dono). regime: PIE "
     "(produtor independente), APE (autoprodutor), SP (serviço público), REG (registro).",
    "ANEEL SIGA, campo DscPropriRegimePariticipacao", "o dono é o titular direto, muitas vezes uma SPE: para um grupo, "
    "procure pelo nome (ILIKE) ou some as SPEs; o SIGA não traz o controlador final")

con.execute("""CREATE VIEW capacidade_por_proprietario AS
SELECT p.cnpj, any_value(p.proprietario) AS proprietario, u.origem, u.tipo_geracao, u.fase, count(*) AS usinas,
       round(sum(coalesce(u.potencia_fiscalizada_kw, u.potencia_outorgada_kw) * p.participacao_pct / 100) / 1000, 3) AS potencia_mw,
       any_value(u.data_base) AS data_base, 'ANEEL SIGA, potência fiscalizada × participação' AS fonte
FROM usinas_proprietarios p JOIN usinas u USING (ceg)
GROUP BY p.cnpj, u.origem, u.tipo_geracao, u.fase""")
CATALOGO.append(("capacidade_por_proprietario", "Capacidade instalada em MW por dono (CNPJ), origem, tipo e fase, já ponderada "
                 "pela participação de cada dono.", "ANEEL SIGA", "titular direto; grupos aparecem espalhados em SPEs", None))

# ---------------------------------------------------------------- ANEEL: leilões de geração
lei = csv_limpo(os.path.join(ANEEL, "leiloes.csv"), "cp1252")
tabela("leiloes_geracao", f"""
SELECT TRY_CAST(AnoLeilao AS INTEGER) AS ano, TRY_CAST(DatLeilao AS DATE) AS data_leilao, NumLeilao AS numero_leilao,
       DscNumeroLeilaoCCEE AS leilao_ccee, DscTipoLeilao AS tipo_leilao, NomEmpreendimento AS empreendimento, CodCEG AS ceg,
       SigTipoGeracao AS tipo_geracao, DscFonteEnergia AS fonte_energia, DscDetalhamentoFonteEnergia AS detalhe_fonte,
       num_br(MdaPotenciaInstaladaMW) AS potencia_mw, num_br(MdaGarantiaFisicaSEL) AS garantia_fisica_mwmed,
       num_br(VlrEnergiaVendida) AS energia_vendida_mwmed, num_br(VlrPrecoTeto) AS preco_teto_brl_mwh,
       num_br(VlrPrecoLeilao) AS preco_leilao_brl_mwh, num_br(VlrDesagio) AS desagio_pct,
       num_br(VlrInvestimentoPrevisto) AS investimento_previsto_brl, TRY_CAST(MdaDuracaoContrato AS INTEGER) AS duracao_contrato_anos,
       SigUFPrincipal AS uf, DscEmpresaVencedora AS vencedor, TRY_CAST(DatGeracaoConjuntoDados AS DATE) AS data_base
FROM {lei}
""", "Resultados dos leilões de GERAÇÃO de energia (2005 em diante): empreendimento, fonte, potência, preço, deságio, "
     "investimento previsto e vencedor.", "ANEEL, resultado de leilões de geração",
    "só geração; leilões de transmissão não estão nesta tabela. vencedor é texto (não tem CNPJ)")

# ---------------------------------------------------------------- ANEEL: transmissão (SIGET)
ag = csv_limpo(os.path.join(ANEEL, "siget_agente.csv"), "cp1252")
tabela("transmissao_contratos", f"""
SELECT IdeCcd AS id_contrato, IdcTipoCcd AS tipo_contrato, NumCnaCcd AS numero_contrato, data_br(DatAsnCcd) AS data_assinatura,
       data_br(DatFimCcd) AS data_fim, fmt_cnpj(NumCNPJ) AS cnpj, DscRazaoSocial AS concessionaria, SigUF AS uf,
       TRY_CAST(DatGeracaoConjuntoDados AS DATE) AS data_base
FROM {ag}
""", "Contratos de concessão de transmissão (SIGET/ANEEL) com a concessionária e o CNPJ.", "ANEEL SIGET")
emp = csv_limpo(os.path.join(ANEEL, "siget_empreendimento_obra_modulo.csv"), "utf-8")
tabela("transmissao_empreendimentos", f"""
SELECT e.IdeCcd AS id_contrato, c.cnpj, c.concessionaria, e.NomEpd AS empreendimento, e.DscEpd AS descricao,
       e.DscSituacaoEpd AS situacao, data_br(e.DatOprComEpd) AS data_operacao_comercial, e.DscObr AS obra,
       e.DscSitObr AS situacao_obra, e.NomMdl AS modulo, e.DscTipMdl AS tipo_modulo, e.DscClfMdl AS classificacao_modulo,
       num_br(e.VlrHisRct) AS valor_historico_receita_brl, data_br(e.DatFimCcd) AS fim_concessao
FROM {emp} e LEFT JOIN transmissao_contratos c ON c.id_contrato = e.IdeCcd
""", "Empreendimentos, obras e módulos de transmissão por contrato (linhas, subestações), com situação e datas.",
    "ANEEL SIGET", "valor_historico_receita_brl se repete em todos os módulos do mesmo empreendimento e NÃO é RAP "
    "confirmado: não some nem chame de RAP")

# ---------------------------------------------------------------- BNDES
bn = csv_limpo(os.path.join(ANEEL, "naoauto_full.csv"), "cp1252")
tabela("bndes_operacoes", f"""
SELECT trim(cliente) AS cliente, cnpj, trim(descricao_do_projeto) AS projeto, uf, municipio,
       TRY_CAST(data_da_contratacao AS DATE) AS data_contratacao, num_br(valor_contratado_reais) AS valor_contratado_brl,
       num_br(valor_desembolsado_reais) AS valor_desembolsado_brl, fonte_de_recurso_desembolsos AS fonte_recurso,
       custo_financeiro, num_br(juros) AS juros_pct_aa, TRY_CAST(prazo_carencia_meses AS INTEGER) AS carencia_meses,
       TRY_CAST(prazo_amortizacao_meses AS INTEGER) AS amortizacao_meses, modalidade_de_apoio AS modalidade,
       forma_de_apoio AS forma_apoio, produto, instrumento_financeiro AS instrumento, inovacao,
       trim(subsetor_cnae_nome) AS subsetor_cnae, trim(subsetor_bndes) AS subsetor_bndes, porte_do_cliente AS porte,
       situacao_do_contrato AS situacao,
       trim(subsetor_bndes) ILIKE 'ENERGIA EL%' AS setor_eletrico
FROM {bn}
""", "Operações de financiamento não automáticas do BNDES (contratos diretos e indiretos), com cliente, CNPJ, projeto, "
     "valores contratado e desembolsado em R$, custo e prazos. setor_eletrico marca geração, transmissão e distribuição.",
    "BNDES dados abertos, operações não automáticas", "CNPJ é do tomador (muitas vezes SPE do grupo)")

# ---------------------------------------------------------------- ANBIMA: debêntures incentivadas (Lei 12.431)
wb = openpyxl.load_workbook(os.path.join(RAW, "cvm", "anbima_deb.xlsx"), read_only=True, data_only=True)
emissoes = []
for aba in wb.worksheets:
    if "Deb" not in aba.title:
        continue
    artigo = "art. 1º" if "1º" in aba.title else "art. 2º"
    linhas = list(aba.iter_rows(values_only=True))
    i_cab = next(i for i, l in enumerate(linhas) if any(isinstance(v, str) and "Emissora" in v for v in l))
    cab = [str(v or "").lower() for v in linhas[i_cab]]
    col = {chave: next(j for j, h in enumerate(cab) if parte in h) for chave, parte in [
        ("emissao", "emissão das"), ("venc", "vencimento"), ("emissora", "emissora"), ("codigo", "cetip"),
        ("valor", "valor"), ("spread", "spread"), ("indexador", "indexador"), ("setor", "setor")]}

    def num(v):
        try:
            return float(str(v).replace(",", "."))
        except (TypeError, ValueError):
            return None
    for linha in linhas[i_cab + 1:]:
        emissora = linha[col["emissora"]]
        if not emissora or not str(emissora).strip():
            continue
        valor = num(linha[col["valor"]])
        data_emissao = str(linha[col["emissao"]] or "")[:10]
        # O cabeçalho diz R$ mil, mas na aba do art. 2º as emissões até 2017 estão em R$ milhões (Santo Antônio
        # SAES12 = 420); de 2018 em diante os valores vêm em R$ mil (Taesa TAEE17 = 508960)
        mult = 1e6 if artigo == "art. 2º" and data_emissao[:4] <= "2017" and valor is not None and valor < 10000 else 1e3
        emissoes.append((artigo, None, None, data_emissao, str(linha[col["venc"]] or "")[:10],
                         str(emissora).strip(), linha[col["codigo"]], valor * mult if valor is not None else None,
                         num(linha[col["spread"]]), linha[col["indexador"]], linha[col["setor"]]))
con.execute("""CREATE TEMP TABLE deb (artigo VARCHAR, inicio VARCHAR, encerramento VARCHAR, emissao VARCHAR, vencimento VARCHAR,
  emissora VARCHAR, codigo VARCHAR, valor_brl DOUBLE, spread DOUBLE, indexador VARCHAR, setor VARCHAR)""")
con.executemany("INSERT INTO deb VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", emissoes)
tabela("debentures_incentivadas", """
SELECT artigo, TRY_CAST(emissao AS DATE) AS data_emissao, TRY_CAST(vencimento AS DATE) AS data_vencimento, emissora,
       codigo AS codigo_cetip, valor_brl, round(spread * 100, 4) AS taxa_ou_spread_pct, indexador, setor
FROM deb
""", "Emissões de debêntures incentivadas de infraestrutura (Lei 12.431), com emissora, código, valor em R$, taxa e "
     "indexador. setor = 'Energia Elétrica' para o setor.", "ANBIMA, planilha de debêntures incentivadas (até 04/2024)",
    "emissora é texto (sem CNPJ); dados até abril de 2024; na planilha original o art. 2º mistura R$ milhões (até 2017) "
    "e R$ mil (2018 em diante), já convertidos para R$ aqui")

# ---------------------------------------------------------------- ANEEL: distribuição (tarifas, PDD, P&D, eficiência, compensações)
PQ = os.path.join(DADOS, "parquet")
tabela("tarifas_distribuicao", f"""
SELECT DscREH AS resolucao, SigAgente AS distribuidora, fmt_cnpj(NumCNPJDistribuidora) AS cnpj,
       TRY_CAST(DatInicioVigencia AS DATE) AS inicio_vigencia, TRY_CAST(DatFimVigencia AS DATE) AS fim_vigencia,
       DscBaseTarifaria AS base_tarifaria, DscSubGrupo AS subgrupo, DscModalidadeTarifaria AS modalidade,
       DscClasse AS classe, DscSubClasse AS subclasse, DscDetalhe AS detalhe, NomPostoTarifario AS posto,
       DscUnidadeTerciaria AS unidade, num_br(VlrTUSD) AS tusd, num_br(VlrTE) AS te
FROM read_csv('{os.path.join(ANEEL, 'tarifas.csv')}', delim=';', header=true, all_varchar=true)
""", "Tarifas homologadas das distribuidoras (TUSD e TE) por resolução, vigência, subgrupo (B1 residencial, A4...), "
     "modalidade, classe e posto. Para a tarifa atual filtre fim_vigencia >= current_date.",
    "ANEEL, tarifas homologadas", "tusd e te na unidade da coluna unidade (R$/MWh ou R$/kW); a sigla da distribuidora "
    "pode ser antiga (ELETROPAULO = Enel SP): prefira filtrar por cnpj")
tabela("pdd_investimentos", f"""
SELECT SigAgente AS distribuidora, fmt_cnpj(NumCPFCNPJ) AS cnpj, SigUF AS uf, DscRegiao AS regiao,
       TRY_CAST(AnoReferencia AS INTEGER) AS ano, DscTipoObra AS tipo_obra, DscTipoObraClasse AS classe_obra,
       num_br(VlrTotalPlanejado) AS planejado_brl, num_br(VlrTotalRealizado) AS realizado_brl
FROM read_csv('{os.path.join(ANEEL, 'pdd.csv')}', delim=';', header=true, all_varchar=true)
""", "Plano de Desenvolvimento da Distribuição: investimento planejado e realizado por distribuidora, ano e tipo de obra.",
    "ANEEL PDD")
tabela("ped_projetos", f"""
SELECT DscCodProjeto AS codigo, IdcSituacaoProjeto AS situacao, NomAgente AS empresa, SigAgente AS sigla,
       fmt_cnpj(NumCPFCNPJ) AS cnpj, DscTituloProjeto AS titulo, DscChamPEDEstrategico AS chamada_estrategica,
       SigSegmentoSetorEletrico AS segmento, SigTemaProjeto AS tema, SigFasInovacaoProjeto AS fase_inovacao,
       SigTipoProdutoProjeto AS tipo_produto, TRY_CAST(QtdMesesDuracaoPrevista AS INTEGER) AS duracao_meses,
       num_br(VlrCustoTotalPrevisto) AS custo_previsto_brl, num_br(VlrCustoTotalAuditado) AS custo_auditado_brl,
       TRY_CAST(AnoCadastroPropostaProjeto AS INTEGER) AS ano_cadastro, TRY_CAST(DatConclusaoProjeto AS DATE) AS data_conclusao
FROM read_csv('{os.path.join(ANEEL, 'ped.csv')}', delim=';', header=true, all_varchar=true)
""", "Projetos do programa de P&D regulado da ANEEL por empresa: tema, segmento, situação e custo.", "ANEEL P&D",
    "muitos projetos antigos têm título e custo vazios")
pee = csv_limpo(os.path.join(ANEEL, "pee.csv"), "utf-8")
tabela("pee_projetos", f"""
SELECT DscCodProjeto AS codigo, NomAgente AS empresa, DscTituloProjeto AS titulo, DscTipologia AS tipologia,
       num_br(VlrCustoTotal) AS custo_total_brl, num_br(VlrRcbGlobal) AS rcb, num_br(VlrEnergiaEconomizadaTotal) AS energia_economizada_mwh,
       num_br(VlrRetiradaDemandaPontaTotal) AS demanda_retirada_ponta_kw, TRY_CAST(DatInicioProjeto AS DATE) AS inicio,
       TRY_CAST(DatConclusaoProjeto AS DATE) AS conclusao
FROM {pee}
""", "Projetos do Programa de Eficiência Energética (PEE) da ANEEL por distribuidora: tipologia, custo, energia economizada.",
    "ANEEL PEE", "sem CNPJ: filtre por empresa (ILIKE)")
AN = os.path.join(RAW, "aneel")
tabela("indicadores_codigos", f"""
SELECT DISTINCT trim(SigIndicador) AS indicador, trim(DscIndicador) AS descricao
FROM read_csv('{os.path.join(AN, 'dec_fec_dominio.csv')}', delim=';', header=true, all_varchar=true)
""", "Significado dos códigos de indicadores de qualidade da ANEEL (DEC, FEC e componentes; PGU* e QTU* das compensações).",
    "ANEEL, domínio dos indicadores de continuidade")
tabela("continuidade_conjuntos", f"""
SELECT trim(d.SigAgente) AS distribuidora, fmt_cnpj(CAST(d.NumCNPJ AS VARCHAR)) AS cnpj, d.IdeConjUndConsumidoras AS id_conjunto,
       d.DscConjUndConsumidoras AS conjunto, d.SigIndicador AS indicador, c.descricao, d.AnoIndice AS ano,
       d.NumPeriodoIndice AS mes, d.VlrIndiceEnviado AS valor
FROM '{os.path.join(AN, 'dec_fec_2020_2029.parquet')}' d LEFT JOIN indicadores_codigos c ON c.indicador = d.SigIndicador
""", "Indicadores de continuidade por conjunto de consumidores e mês (2020 em diante): DEC em horas e FEC em interrupções, "
     "com os componentes (programada, externa, dia crítico...) e NumCon (número de consumidores do conjunto).",
    "ANEEL, indicadores coletivos de continuidade", "para a distribuidora inteira use dec_fec_distribuidora_anual")
tabela("continuidade_limites", f"""
SELECT trim(SigAgente) AS distribuidora, fmt_cnpj(NumCNPJ) AS cnpj, TRY_CAST(IdeConjUndConsumidoras AS BIGINT) AS id_conjunto,
       DscConjUndConsumidoras AS conjunto, SigIndicador AS indicador, TRY_CAST(AnoLimiteQualidade AS INTEGER) AS ano,
       num_br(VlrLimite) AS limite
FROM read_csv('{os.path.join(AN, 'dec_fec_limites.csv')}', delim=';', header=true, all_varchar=true)
""", "Limites regulatórios anuais de DEC e FEC por conjunto de consumidores, definidos pela ANEEL.", "ANEEL")
con.execute("""CREATE VIEW dec_fec_distribuidora_anual AS
WITH n AS (SELECT cnpj, id_conjunto, ano, mes, valor AS consumidores FROM continuidade_conjuntos WHERE indicador = 'NumCon'),
m AS (  -- DEC e FEC mensais da distribuidora: média dos conjuntos ponderada pelo número de consumidores
  SELECT c.cnpj, c.ano, c.mes, c.indicador, sum(c.valor * n.consumidores) / nullif(sum(n.consumidores), 0) AS valor
  FROM continuidade_conjuntos c JOIN n USING (cnpj, id_conjunto, ano, mes)
  WHERE c.indicador IN ('DEC', 'FEC') GROUP BY ALL),
lim AS (
  SELECT l.cnpj, l.ano, l.indicador, sum(l.limite * n.consumidores) / nullif(sum(n.consumidores), 0) AS limite
  FROM continuidade_limites l
  JOIN (SELECT cnpj, id_conjunto, ano, avg(consumidores) AS consumidores FROM n GROUP BY ALL) n USING (cnpj, id_conjunto, ano)
  WHERE l.indicador IN ('DEC', 'FEC') GROUP BY ALL),
nomes AS (SELECT cnpj, any_value(distribuidora) AS distribuidora FROM continuidade_conjuntos GROUP BY cnpj),
cons AS (SELECT cnpj, ano, round(avg(t)) AS consumidores FROM (SELECT cnpj, ano, mes, sum(consumidores) AS t FROM n GROUP BY ALL) GROUP BY ALL)
SELECT m.cnpj, nomes.distribuidora, m.ano, count(DISTINCT m.mes) AS meses,
       round(sum(m.valor) FILTER (m.indicador = 'DEC'), 2) AS dec_horas,
       round(sum(m.valor) FILTER (m.indicador = 'FEC'), 2) AS fec_interrupcoes,
       round(any_value(ld.limite), 2) AS dec_limite_medio_ponderado_horas,
       round(any_value(lf.limite), 2) AS fec_limite_medio_ponderado,
       any_value(cons.consumidores) AS consumidores_medios,
       'ANEEL, indicadores de continuidade: soma dos meses da média ponderada por consumidores dos conjuntos' AS fonte
FROM m JOIN nomes USING (cnpj) LEFT JOIN cons USING (cnpj, ano)
LEFT JOIN lim ld ON ld.cnpj = m.cnpj AND ld.ano = m.ano AND ld.indicador = 'DEC'
LEFT JOIN lim lf ON lf.cnpj = m.cnpj AND lf.ano = m.ano AND lf.indicador = 'FEC'
GROUP BY m.cnpj, nomes.distribuidora, m.ano""")
CATALOGO.append(("dec_fec_distribuidora_anual", "DEC (horas) e FEC (interrupções) anuais de cada distribuidora, com os "
                 "limites da ANEEL e o número médio de consumidores, de 2020 em diante.",
                 "ANEEL, indicadores coletivos de continuidade; cálculo desta plataforma",
                 "média dos conjuntos ponderada por consumidores e somada nos meses: aproxima o valor oficial (pode "
                 "diferir em 0,01 do publicado pela distribuidora). Os limites são médias ponderadas dos limites dos "
                 "conjuntos, calculadas por esta plataforma, não o limite global oficial. Confira meses (ano corrente é parcial)",
                 None))
tabela("compensacoes_continuidade", f"""
SELECT d.SigAgente AS distribuidora, fmt_cnpj(d.NumCNPJ) AS cnpj, d.IdeConjUndConsumidoras AS id_conjunto,
       d.DscConjUndConsumidoras AS conjunto, d.SigIndicador AS indicador, c.descricao, TRY_CAST(d.AnoIndice AS INTEGER) AS ano,
       TRY_CAST(d.NumPeriodoIndice AS INTEGER) AS mes, num_br(d.VlrIndiceEnviado) AS valor
FROM '{os.path.join(PQ, 'reg_decfec.parquet')}' d LEFT JOIN indicadores_codigos c ON c.indicador = d.SigIndicador
""", "Compensações pagas pelas distribuidoras aos consumidores por violação dos limites de continuidade, por conjunto e "
     "mês: PGU* = valor pago em R$, QTU* = quantidade de unidades compensadas (a coluna descricao explica cada código).",
    "ANEEL, compensação por violação de continuidade", "para DEC e FEC use dec_fec_distribuidora_anual")

# ---------------------------------------------------------------- ONS
cmo_arquivos = os.path.join(RAW, "ons", "cmo_semi_horario", "CMO_SEMIHORARIO_*.parquet")
if glob.glob(cmo_arquivos):
    tabela("ons_cmo_semihora", f"""
SELECT id_subsistema AS subsistema, nom_subsistema AS nome_subsistema,
       din_instante AS instante, TRY_CAST(val_cmo AS DOUBLE) AS cmo_brl_mwh
FROM read_parquet('{cmo_arquivos}')
""", "CMO (Custo Marginal de Operação) do ONS por subsistema e instante semihorário, desde 2020. "
       "SE corresponde ao subsistema Sudeste/Centro-Oeste, embora o arquivo o rotule SUDESTE. "
       "Para comparar meses e submercados use ons_cmo_mensal; para horários e extremos use esta tabela.",
       "ONS, CMO Semi-Horário, https://dados.ons.org.br/dataset/cmo-semi-horario",
       "CMO em R$/MWh calculado pelo DESSEM; não é PLD nem preço recebido por gerador. "
       "A série pode conter valores negativos e extremos; o ONS pode revisar os arquivos. "
       "O mês corrente e o dia seguinte podem estar incompletos ou programados.")
    tabela("ons_cmo_mensal", """
SELECT subsistema, any_value(nome_subsistema) AS nome_subsistema,
       CAST(date_trunc('month', instante) AS DATE) AS mes,
       round(avg(cmo_brl_mwh), 2) AS cmo_medio_brl_mwh,
       min(cmo_brl_mwh) AS cmo_minimo_brl_mwh,
       max(cmo_brl_mwh) AS cmo_maximo_brl_mwh,
       count(cmo_brl_mwh) AS intervalos,
       count(DISTINCT CAST(instante AS DATE)) AS dias_com_dados,
       day(last_day(mes)) AS dias_esperados,
       day(last_day(mes)) - count(DISTINCT CAST(instante AS DATE)) AS dias_ausentes
FROM ons_cmo_semihora GROUP BY subsistema, mes
""", "CMO médio mensal do ONS por subsistema (N, NE, S, SE), em R$/MWh, desde 2020. "
       "SE corresponde ao subsistema Sudeste/Centro-Oeste; o arquivo do ONS o rotula SUDESTE, "
       "mas não há submercado Centro-Oeste separado. "
       "Cada linha é um subsistema-mês; cmo_medio_brl_mwh é a média aritmética dos intervalos semihorários. "
       "Use dias_ausentes, dias_com_dados e intervalos para avaliar cobertura antes de comparar meses; "
       "um mês com dias_ausentes > 0 não tem média mensal completa.",
       "ONS, CMO Semi-Horário, https://dados.ons.org.br/dataset/cmo-semi-horario; média calculada pela plataforma",
       "Não é PLD nem preço spot de liquidação. A média mensal dá o mesmo peso a cada intervalo, "
       "sem ponderação pela carga entre intervalos; o CMO semihorário do subsistema publicado pelo ONS "
       "já pondera os CMOs das barras pelas respectivas cargas. "
       "Meses com menos dias ou intervalos são parciais; "
       "arquivos do ONS podem ser revisados, inclusive para o dia seguinte.")

ear_arquivos = os.path.join(RAW, "ons", "ear_diario_subsistema", "EAR_DIARIO_SUBSISTEMA_*.parquet")
if glob.glob(ear_arquivos):
    tabela("ons_ear_diario", f"""
SELECT trim(id_subsistema) AS subsistema, trim(nom_subsistema) AS nome_subsistema,
       TRY_CAST(ear_data AS DATE) AS data,
       TRY_CAST(ear_max_subsistema AS DOUBLE) AS ear_maxima_mwmes,
       TRY_CAST(ear_verif_subsistema_mwmes AS DOUBLE) AS ear_verificada_mwmes,
       TRY_CAST(ear_verif_subsistema_percentual AS DOUBLE) AS ear_verificada_pct
FROM read_parquet('{ear_arquivos}')
""", "Energia armazenada (EAR) diária nos reservatórios por subsistema do ONS, desde 2000. "
       "SE corresponde ao subsistema Sudeste/Centro-Oeste, embora o arquivo o rotule SUDESTE. "
       "Cada linha é um subsistema e uma data; traz a EAR verificada em MWmês, sua capacidade máxima "
       "em MWmês e o percentual de armazenamento. Útil para avaliar risco hidrológico e contexto do CMO.",
       "ONS, EAR Diário por Subsistema, https://dados.ons.org.br/dataset/ear-diario-por-subsistema",
       "MWmês é unidade de energia armazenada do ONS, não potência em MW nem geração em MWh. "
       "O percentual é o valor publicado pelo ONS; a EAR considera cascatas entre subsistemas. "
       "Dados recentes podem ser revisados; não são armazenamento de uma empresa ou usina específica.")

tabela("ons_capacidade", f"""
SELECT id_subsistema AS subsistema, id_estado AS uf, nom_agenteproprietario AS agente_proprietario,
       nom_tipousina AS tipo_usina, nom_usina AS usina, ceg, nom_unidadegeradora AS unidade_geradora,
       nom_combustivel AS combustivel, TRY_CAST(dat_entradaoperacao AS DATE) AS entrada_operacao,
       TRY_CAST(dat_desativacao AS DATE) AS desativacao, TRY_CAST(val_potenciaefetiva AS DOUBLE) AS potencia_efetiva_mw
FROM '{os.path.join(PQ, 'reg_capacidade.parquet')}'
""", "Unidades geradoras despachadas pelo ONS com agente proprietário e potência efetiva em MW.", "ONS, capacidade instalada",
    "agente sem CNPJ; ceg liga com usinas")
# Cortes de geração (constrained-off) eólica e solar: valores do ONS em MW médio por meia hora (energia = MWmed × 0,5 h)
ONS = os.path.join(RAW, "ons")
partes = [f"SELECT '{fonte}' AS fonte, * FROM read_parquet('{os.path.join(ONS, pasta, '*.parquet')}', union_by_name=true)"
          for pasta, fonte in (("restricao_coff_eolica_usi", "eólica"), ("restricao_coff_fotovoltaica", "solar"))
          if glob.glob(os.path.join(ONS, pasta, "*.parquet"))]
con.execute(f"""CREATE VIEW ons_curtailment_semihora AS
SELECT fonte, id_subsistema AS subsistema, id_estado AS uf, nom_usina AS usina, id_ons, nullif(ceg, '-') AS ceg,
       din_instante AS instante, val_geracao AS geracao_mwmed, val_geracaoreferencia AS referencia_mwmed,
       val_geracaonaorealizadaapurada AS nao_realizada_mwmed, cod_razaorestricao AS razao, nom_agenteoperador AS agente_operador
FROM ({' UNION ALL BY NAME '.join(partes)})""")
CATALOGO.append(("ons_curtailment_semihora", "Cortes de geração eólica (2023 em diante) e solar (abr/2024 em diante) por usina e "
                 "meia hora, em MW médio: geração verificada, geração de referência e geração não realizada apurada (GNRa).",
                 "ONS, restrição de operação por constrained-off", "para séries e rankings use ons_curtailment_mensal", None))
tabela("ons_curtailment_mensal", """
SELECT fonte, subsistema, uf, usina, id_ons, any_value(ceg) AS ceg, any_value(agente_operador) AS agente_operador,
       CAST(date_trunc('month', instante) AS DATE) AS mes,
       round(sum(geracao_mwmed) * 0.5, 1) AS geracao_mwh, round(sum(referencia_mwmed) * 0.5, 1) AS referencia_mwh,
       round(sum(coalesce(nao_realizada_mwmed, 0)) * 0.5, 1) AS energia_cortada_mwh,
       round(100 * sum(coalesce(nao_realizada_mwmed, 0)) / nullif(sum(referencia_mwmed), 0), 2) AS corte_pct
FROM ons_curtailment_semihora GROUP BY ALL
""", "Cortes de geração (curtailment) por usina e mês: geração, geração de referência e energia cortada em MWh, e % cortado. "
     "fonte = eólica (2023 em diante) ou solar (abr/2024 em diante).",
    "ONS, restrição de operação por constrained-off (GNRa = geração não realizada apurada)",
    "energia cortada = GNRa × 0,5 h; motivos em ons_curtailment_semihora.razao: REL indisponibilidade externa (rede), "
    "CNF confiabilidade, ENE razão energética (sobra de oferta), PAR parecer de acesso; ceg liga com usinas e donos; "
    "o mês corrente é parcial")

mapas = [f"SELECT DISTINCT '{fonte}' AS fonte, id_ons_conjuntousina AS id_conjunto, nom_conjuntousina AS conjunto, "
         f"id_ons AS id_usina, nom_usina AS usina, ceg FROM '{os.path.join(ONS, arq)}'"
         for arq, fonte in (("mapa_conjuntos_eolica.parquet", "eólica"), ("mapa_conjuntos_solar.parquet", "solar"))
         if os.path.exists(os.path.join(ONS, arq))]
if mapas:
    tabela("ons_conjuntos_usinas", " UNION ALL ".join(mapas),
           "Usinas eólicas e solares que formam cada conjunto do ONS (id_conjunto = id_ons de ons_curtailment_mensal), "
           "com o CEG de cada usina.", "ONS, detalhamento por usina dos cortes de geração (ago/2026)",
           "mapa de um mês; o CEG liga com usinas pelo núcleo, sem o sufixo de versão")
    con.execute(r"""CREATE VIEW curtailment_por_dono_mensal AS
WITH membros AS (  -- usinas de cada conjunto (ou a própria usina) com a potência do SIGA
  SELECT m.id_ons, u.ceg, coalesce(u.potencia_fiscalizada_kw, u.potencia_outorgada_kw) AS kw
  FROM (SELECT DISTINCT id_ons, ceg FROM ons_curtailment_mensal WHERE ceg IS NOT NULL
        UNION SELECT id_conjunto, ceg FROM ons_conjuntos_usinas) m
  JOIN usinas u ON regexp_replace(u.ceg, '\.\d+$', '') = regexp_replace(m.ceg, '\.\d+$', '')),
parte AS (SELECT id_ons, ceg, kw / nullif(sum(kw) OVER (PARTITION BY id_ons), 0) AS fracao FROM membros)
SELECT p.cnpj, any_value(p.proprietario) AS proprietario, c.fonte, c.mes,
       round(sum(c.energia_cortada_mwh * parte.fracao * p.participacao_pct / 100), 1) AS energia_cortada_mwh_estimada,
       round(sum(c.referencia_mwh * parte.fracao * p.participacao_pct / 100), 1) AS referencia_mwh_estimada,
       'Estimativa: corte do conjunto do ONS dividido pela potência das usinas (SIGA) e pela participação do dono' AS fonte_calculo
FROM ons_curtailment_mensal c JOIN parte USING (id_ons) JOIN usinas_proprietarios p ON p.ceg = parte.ceg
GROUP BY p.cnpj, c.fonte, c.mes""")
    CATALOGO.append(("curtailment_por_dono_mensal", "Estimativa da energia cortada (curtailment) por dono de usina (CNPJ) e mês, "
                     "eólica e solar.", "ONS e ANEEL SIGA; cálculo desta plataforma",
                     "ESTIMATIVA: o ONS apura o corte por conjunto; aqui ele é dividido pela potência das usinas e pela "
                     "participação de cada dono; o dono é o titular direto (SPE)", None))

# ---------------------------------------------------------------- ANEEL: cadastro de agentes (CNPJ de todo o setor)
AGENTES = os.path.join(AN, "agentes", "agentes-setor-eletrico.csv")
if os.path.exists(AGENTES):
    tabela("agentes_aneel", f"""
SELECT fmt_cnpj(NumCnpj) AS cnpj, nullif(trim(SigPessoa), '') AS sigla, trim(replace(NomRazaoSocial, '''''', '')) AS razao_social,
       IdcAtivo = 'A' AS ativo, IdcGeracao = '1' AS geracao, IdcTransmissao = '1' AS transmissao,
       IdcDistribuicao = '1' AS distribuicao, IdcComercializacao = '1' AS comercializacao,
       TRY_CAST(DatGeracaoConjuntoDados AS DATE) AS data_base
FROM read_csv('{AGENTES}', delim=';', header=true, all_varchar=true)
WHERE length(regexp_replace(coalesce(NumCnpj, ''), '\\D', '', 'g')) > 11
""", "Cadastro de agentes da ANEEL: CNPJ, sigla e razão social de geradoras, transmissoras, distribuidoras e "
       "comercializadoras (inclusive as que não são companhias abertas). Use para achar o CNPJ de uma empresa que "
       "não está em empresas.",
       "ANEEL, Agentes do Setor Elétrico, https://dadosabertos.aneel.gov.br/dataset/agentes-do-setor-eletrico",
       "cadastro, sem dados financeiros; um agente pode ter mais de um papel (geração, transmissão...)")

# ---------------------------------------------------------------- ANEEL: composição societária e grupos econômicos
SOC = os.path.join(AN, "societaria", "composicao-societaria-polimero.parquet")
if os.path.exists(SOC):
    # Cada declaração é uma árvore: a linha de nível 0 é o agente; as seguintes, os sócios diretos (nível 1) e indiretos.
    # PctParticipacaoNivelAcima é a participação efetiva (já multiplicada ao longo da cadeia) no agente da raiz.
    con.execute(f"""CREATE TEMP TABLE soc_bruto AS
SELECT *, sum(CASE WHEN NumNivelCadeiaSocietaria = 0 THEN 1 ELSE 0 END) OVER (ORDER BY NumOrdemCadeiaSocietaria) AS arvore
FROM '{SOC}'""")
    con.execute("""CREATE TEMP TABLE soc_raiz AS
SELECT arvore, NumCPFCNPJSocio AS doc_agente, trim(NomRazaoSocialSocio) AS agente, AnoExercicio AS ano,
       IdcTrimestreFormulario AS trimestre, DatGeracaoConjuntoDados AS data_base
FROM soc_bruto WHERE NumNivelCadeiaSocietaria = 0
  AND length(regexp_replace(coalesce(NumCPFCNPJSocio, ''), '\\D', '', 'g')) > 11
QUALIFY row_number() OVER (PARTITION BY digitos14(NumCPFCNPJSocio)
                           ORDER BY AnoExercicio DESC, IdcTrimestreFormulario DESC, arvore DESC) = 1""")
    # CPF de pessoa física não entra no banco: só o nome; CNPJ só de pessoa jurídica
    con.execute(r"""CREATE TEMP TABLE soc AS
SELECT DISTINCT ON (r.arvore, b.NumNivelCadeiaSocietaria, b.NumCPFCNPJPaiCadeiaSocietaria, b.NomRazSocPaiCadeiaSocietaria,
                    b.NumCPFCNPJSocio, b.NomRazaoSocialSocio, b.PctParticipacaoNivelAcima)
  r.arvore, fmt_cnpj(r.doc_agente) AS cnpj_agente, r.agente, r.ano, r.trimestre, r.data_base,
  b.NumOrdemCadeiaSocietaria AS ordem, b.NumNivelCadeiaSocietaria AS nivel,
  CASE WHEN b.NumCPFCNPJPaiCadeiaSocietaria > 99999999999 THEN fmt_cnpj(CAST(b.NumCPFCNPJPaiCadeiaSocietaria AS VARCHAR)) END AS cnpj_pai,
  trim(b.NomRazSocPaiCadeiaSocietaria) AS pai,
  CASE WHEN b.IdcPerfilSocietario <> 'PF' AND length(regexp_replace(coalesce(b.NumCPFCNPJSocio, ''), '\D', '', 'g')) > 11
       THEN fmt_cnpj(b.NumCPFCNPJSocio) END AS cnpj_socio,
  trim(b.NomRazaoSocialSocio) AS socio, b.DscTipoCadeiaSocietaria = 'Controlador' AS controlador,
  b.PctParticipacaoNivelAcima AS participacao_pct, b.IdcPerfilSocietario AS perfil, b.IdcGoverno = 'SIM' AS governo,
  (b.IdcEmpresaEstrangeira = 'SIM' OR b.IdcPessoaEstrangeira = 'SIM') AS estrangeiro
FROM soc_raiz r JOIN soc_bruto b USING (arvore) WHERE b.NumNivelCadeiaSocietaria > 0
ORDER BY r.arvore, b.NumNivelCadeiaSocietaria, b.NumOrdemCadeiaSocietaria""")

    def chave_nome(nome):
        return "#" + " ".join((nome or "").upper().split())

    # Cadeia de controle: um sócio está na cadeia se é controlador e o seu pai (nível acima) também está nela
    from collections import defaultdict
    arvores = defaultdict(list)
    for linha in con.execute("SELECT arvore, ordem, nivel, cnpj_pai, pai, cnpj_socio, socio, controlador FROM soc "
                             "ORDER BY arvore, nivel, ordem").fetchall():
        arvores[linha[0]].append(linha)
    marcas = []
    for arv, linhas_arv in arvores.items():
        na_cadeia = defaultdict(set)
        for (_, ordem, nivel, cnpj_pai, pai, cnpj_socio, socio, controlador) in linhas_arv:
            ok = controlador and (nivel == 1 or (cnpj_pai or chave_nome(pai)) in na_cadeia[nivel - 1]
                                  or chave_nome(pai) in na_cadeia[nivel - 1])
            if ok:
                na_cadeia[nivel].update({cnpj_socio or chave_nome(socio), chave_nome(socio)})
            marcas.append((arv, ordem, bool(ok)))
    con.execute("CREATE TEMP TABLE soc_cadeia (arvore BIGINT, ordem BIGINT, na_cadeia BOOLEAN)")
    con.executemany("INSERT INTO soc_cadeia VALUES (?, ?, ?)", marcas)
    con.execute(r"""CREATE TEMP TABLE soc_marcada AS
WITH s AS (
  SELECT s.*, c.na_cadeia, coalesce(s.cnpj_socio, '#' || upper(regexp_replace(s.socio, '\s+', ' ', 'g'))) AS chave,
         coalesce(s.cnpj_pai, '#' || upper(regexp_replace(s.pai, '\s+', ' ', 'g'))) AS chave_pai
  FROM soc s JOIN soc_cadeia c USING (arvore, ordem))
SELECT s.*, s.na_cadeia AND NOT EXISTS (
  SELECT 1 FROM s f WHERE f.arvore = s.arvore AND f.nivel = s.nivel + 1 AND f.na_cadeia AND f.chave_pai = s.chave) AS topo
FROM s""")
    tabela("composicao_societaria", """
SELECT cnpj_agente, agente, ano, trimestre, nivel, cnpj_pai, pai, cnpj_socio, socio,
       CASE WHEN controlador THEN 'controlador' ELSE 'não controlador' END AS tipo_socio,
       round(participacao_pct, 4) AS participacao_indireta_pct, na_cadeia AS na_cadeia_de_controle,
       topo AS controlador_final, CASE perfil WHEN 'PF' THEN 'pessoa física' WHEN 'PJ' THEN 'pessoa jurídica'
       ELSE 'outros (ações em bolsa, tesouraria)' END AS perfil, governo, estrangeiro, data_base
FROM soc_marcada ORDER BY cnpj_agente, nivel, ordem
""", "Cadeia societária declarada à ANEEL por cada agente do setor (usina, transmissora, distribuidora), da "
       "declaração mais recente: sócios diretos (nivel 1) e indiretos (nivel 2, 3...) até o controlador final. "
       "participacao_indireta_pct é a participação efetiva do sócio no agente (já multiplicada ao longo da cadeia). "
       "Para somar por grupo use participacoes_societarias, grupos_economicos e capacidade_por_grupo.",
       "ANEEL, Composição Societária (Polímero), https://dadosabertos.aneel.gov.br/dataset/composicao-societaria-polimero",
       "declaração do próprio agente (REN 948/2021), trimestral; ano e trimestre indicam a declaração usada. "
       "O mesmo sócio pode aparecer em mais de um ramo; CPF de pessoa física não é publicado aqui (só o nome). "
       "na_cadeia_de_controle e controlador_final são calculados pela plataforma a partir do tipo de sócio")
    tabela("participacoes_societarias", r"""
WITH nomes AS (SELECT cnpj, any_value(razao_social) AS nome FROM agentes_aneel GROUP BY cnpj),
p AS (
  SELECT cnpj_agente, any_value(agente) AS agente, chave, any_value(cnpj_socio) AS cnpj_socio, mode(socio) AS socio,
         least(sum(participacao_pct), 100) AS participacao_pct, min(nivel) AS nivel, bool_or(na_cadeia) AS controla,
         bool_or(topo) AS controlador_final, any_value(perfil) AS perfil, bool_or(governo) AS governo,
         bool_or(estrangeiro) AS estrangeiro, any_value(ano) AS ano, any_value(trimestre) AS trimestre
  FROM soc_marcada WHERE perfil <> 'DC' GROUP BY cnpj_agente, chave
  UNION ALL  -- o próprio agente, para que a soma de um grupo inclua os ativos que ele detém diretamente
  SELECT DISTINCT cnpj_agente, agente, cnpj_agente, cnpj_agente, agente, 100, 0, true, false, 'PJ', false, false, ano, trimestre
  FROM soc)
SELECT p.cnpj_agente, p.agente, p.cnpj_socio AS cnpj_participante, coalesce(n.nome, p.socio) AS participante,
       p.chave AS chave_participante, round(p.participacao_pct, 4) AS participacao_indireta_pct, p.nivel,
       p.controla AS na_cadeia_de_controle, p.controlador_final,
       CASE p.perfil WHEN 'PF' THEN 'pessoa física' ELSE 'pessoa jurídica' END AS perfil, p.governo, p.estrangeiro,
       p.ano, p.trimestre
FROM p LEFT JOIN nomes n ON n.cnpj = p.cnpj_socio
""", "Participação direta e indireta de cada empresa ou pessoa em cada agente do setor (uma linha por agente e "
       "participante), somando todos os caminhos da cadeia societária. na_cadeia_de_controle = o participante "
       "controla o agente, direta ou indiretamente. Inclui o próprio agente com 100%. Serve para somar ativos por "
       "grupo: junte cnpj_agente com o CNPJ do dono (usinas_proprietarios.cnpj, rap_transmissao_modulos.cnpj...).",
       "ANEEL, Composição Societária (Polímero); cálculo desta plataforma",
       "chave_participante = CNPJ, ou '#NOME' para estrangeiros e pessoas sem CNPJ. Ações em bolsa e tesouraria "
       "ficam de fora. Participação limitada a 100% quando a declaração repete um sócio")
    tabela("grupos_economicos", r"""
WITH finais AS (
  SELECT cnpj_agente, string_agg(DISTINCT participante, '; ' ORDER BY participante) AS controladores_finais,
         string_agg(DISTINCT cnpj_participante, '; ' ORDER BY cnpj_participante) AS cnpj_controladores_finais
  FROM participacoes_societarias WHERE controlador_final GROUP BY cnpj_agente),
diretos AS (
  SELECT cnpj_agente, string_agg(participante || ' (' || participacao_indireta_pct || '%)', '; '
                                 ORDER BY participacao_indireta_pct DESC) AS controladores_diretos
  FROM participacoes_societarias WHERE nivel = 1 AND na_cadeia_de_controle GROUP BY cnpj_agente),
listada AS (  -- companhia aberta do setor (CVM) que controla o agente, a mais próxima dele na cadeia
  SELECT p.cnpj_agente, p.cnpj_participante AS cnpj_holding_cvm, e.nome_social AS holding_cvm
  FROM participacoes_societarias p JOIN empresas e ON e.cnpj = p.cnpj_participante
  WHERE p.na_cadeia_de_controle AND p.nivel > 0
  QUALIFY row_number() OVER (PARTITION BY p.cnpj_agente ORDER BY p.nivel, p.participacao_indireta_pct DESC) = 1)
SELECT a.cnpj_agente AS cnpj, a.agente, diretos.controladores_diretos, finais.controladores_finais,
       finais.cnpj_controladores_finais, listada.holding_cvm, listada.cnpj_holding_cvm, a.ano, a.trimestre
FROM (SELECT DISTINCT cnpj_agente, agente, ano, trimestre FROM participacoes_societarias) a
LEFT JOIN diretos USING (cnpj_agente) LEFT JOIN finais USING (cnpj_agente) LEFT JOIN listada USING (cnpj_agente)
""", "Grupo econômico de cada agente do setor (uma linha por CNPJ): controladores diretos com participação, "
       "controladores finais (topo da cadeia de controle, podem ser vários quando o controle é compartilhado) e a "
       "companhia aberta do setor (CVM) que controla o agente, a mais próxima dele na cadeia (holding_cvm), que "
       "costuma ser o grupo como o mercado o chama (ex.: SPE da Taesa -> Taesa; Coelba -> Neoenergia). Use para dizer a que grupo pertence uma SPE, usina ou concessão.",
       "ANEEL, Composição Societária (Polímero); cálculo desta plataforma",
       "controladores_finais pode ser um governo, fundo ou empresa estrangeira; holding_cvm é vazia quando nenhuma "
       "companhia aberta do setor controla o agente. Declaração mais recente de cada agente (ano, trimestre)")
    con.execute("""CREATE TEMP TABLE usina_dono AS
SELECT p.ceg, p.cnpj, p.participacao_pct, u.origem, u.tipo_geracao, u.fase,
       coalesce(u.potencia_fiscalizada_kw, u.potencia_outorgada_kw) AS kw
FROM usinas_proprietarios p JOIN usinas u USING (ceg)""")
    tabela("capacidade_por_grupo", """
SELECT g.chave_participante, any_value(g.cnpj_participante) AS cnpj_participante, mode(g.participante) AS participante,
       d.origem, d.tipo_geracao, d.fase, count(DISTINCT d.ceg) AS usinas,
       round(sum(d.kw * d.participacao_pct / 100 * g.participacao_indireta_pct / 100) / 1000, 3) AS potencia_proporcional_mw,
       round(sum(d.kw * d.participacao_pct / 100) FILTER (WHERE g.na_cadeia_de_controle) / 1000, 3) AS potencia_controlada_mw,
       bool_or(g.controlador_final) AS controlador_final_de_algum_agente
FROM usina_dono d JOIN participacoes_societarias g ON g.cnpj_agente = d.cnpj
WHERE g.perfil = 'pessoa jurídica'
GROUP BY g.chave_participante, d.origem, d.tipo_geracao, d.fase
""", "Capacidade de geração (SIGA) atribuída a cada grupo ou empresa participante, direta ou indiretamente, por "
       "origem, tipo e fase. potencia_proporcional_mw = potência × participação do dono na usina × participação "
       "indireta do participante no dono (visão proporcional); potencia_controlada_mw = potência × participação do "
       "dono, só nas usinas cujo dono o participante controla (visão consolidada). Para ranking de grupos filtre "
       "fase = 'Operação' e agrupe por chave_participante.",
       "ANEEL SIGA e Composição Societária (Polímero); cálculo desta plataforma",
       "um mesmo grupo aparece em vários níveis (holding brasileira, subholding, controladora estrangeira): escolha o "
       "CNPJ ou nome do grupo e não some níveis diferentes. Usinas cujo dono não declarou composição à ANEEL ficam "
       "de fora (cerca de 12% da potência em operação). Titulares com CPF não entram")
    if mapas:
        con.execute("""CREATE VIEW curtailment_por_grupo_mensal AS
SELECT g.chave_participante, any_value(g.cnpj_participante) AS cnpj_participante, mode(g.participante) AS participante,
       c.fonte, c.mes,
       round(sum(c.energia_cortada_mwh_estimada * g.participacao_indireta_pct / 100), 1) AS energia_cortada_mwh_proporcional,
       round(sum(c.referencia_mwh_estimada * g.participacao_indireta_pct / 100), 1) AS referencia_mwh_proporcional,
       round(sum(c.energia_cortada_mwh_estimada) FILTER (WHERE g.na_cadeia_de_controle), 1) AS energia_cortada_mwh_controlada,
       round(sum(c.referencia_mwh_estimada) FILTER (WHERE g.na_cadeia_de_controle), 1) AS referencia_mwh_controlada
FROM curtailment_por_dono_mensal c JOIN participacoes_societarias g ON g.cnpj_agente = c.cnpj
WHERE g.perfil = 'pessoa jurídica'
GROUP BY g.chave_participante, c.fonte, c.mes""")
        CATALOGO.append(("curtailment_por_grupo_mensal", "Estimativa da energia eólica e solar cortada (curtailment) por grupo "
                         "econômico e mês: proporcional à participação indireta do grupo em cada SPE e controlada (100% das "
                         "SPEs que o grupo controla).", "ONS, ANEEL SIGA e Composição Societária; cálculo desta plataforma",
                         "ESTIMATIVA sobre curtailment_por_dono_mensal (o ONS apura o corte por conjunto de usinas). O mesmo "
                         "grupo aparece em vários níveis: não some chaves diferentes do mesmo grupo", None))

# ---------------------------------------------------------------- ANEEL SIGET: RAP das transmissoras por módulo
RAP = os.path.join(AN, "siget_rap", "siget-lista-modulos-previa-reajuste-rap.csv")
if os.path.exists(RAP):
    rap = csv_limpo(RAP, "cp1252")
    tabela("rap_transmissao_modulos", f"""
WITH r AS (SELECT * FROM {rap}),
cnpj_contrato AS (  -- o CNPJ da receita vem do módulo do mesmo contrato (NumCNPJConcessionariaRct vem quase sempre vazio)
  SELECT SigConcessionariaReceita, NumContratoReceita, any_value(NumCNPJConcessionariaMdl) AS cnpj
  FROM r WHERE NumContratoModulo = NumContratoReceita GROUP BY ALL)
SELECT trim(r.SigConcessionariaReceita) AS concessionaria, fmt_cnpj(c.cnpj) AS cnpj, r.NumContratoReceita AS contrato,
       r.NomTipoReceita AS tipo_receita, r.DcsSitRAP AS situacao, TRY_CAST(r.IdeRct AS BIGINT) AS id_receita,
       TRY_CAST(r.IdeMdl AS BIGINT) AS id_modulo, r.NomModulo AS modulo, r.NomEdificacao AS instalacao, r.SigUF AS uf,
       r.SigClassificacao AS classificacao, r.DscTipoUso AS tipo_uso, r.IdeOnsEpd AS codigo_ons_empreendimento,
       num_br(r.VlrRAPCiclo) AS rap_ciclo_brl, r.QtdAnosCcoTar AS ciclo_tarifario,
       CAST(TRY_CAST(r.DatRefCiclo AS TIMESTAMP) AS DATE) AS data_referencia_ciclo,
       num_br(r.VlrRAPAtoLegal) AS rap_ato_legal_brl, CAST(TRY_CAST(r.DatRefRAP AS TIMESTAMP) AS DATE) AS data_referencia_ato,
       r.NumAtoRAP AS ato_rap, r.SigIndice AS indice_reajuste,
       CAST(TRY_CAST(r.DatIniVigencia AS TIMESTAMP) AS DATE) AS inicio_vigencia,
       CAST(TRY_CAST(r.DatFimVigencia AS TIMESTAMP) AS DATE) AS fim_vigencia,
       CAST(TRY_CAST(r.DatOprComercial AS TIMESTAMP) AS DATE) AS data_operacao_comercial,
       CAST(TRY_CAST(r.DatPrevisao AS TIMESTAMP) AS DATE) AS data_prevista,
       trim(r.SigConcessionariaUsr) AS usuario_exclusivo, CAST(TRY_CAST(r.DatGeracaoConjuntoDados AS DATE) AS DATE) AS data_base
FROM r LEFT JOIN cnpj_contrato c USING (SigConcessionariaReceita, NumContratoReceita)
""", "Receita Anual Permitida (RAP) das transmissoras por módulo de transmissão (linha, subestação, equipamento), "
       "da lista prévia do reajuste da ANEEL: concessionária com CNPJ, contrato, tipo de receita e situação. "
       "rap_ciclo_brl é o valor do módulo no ciclo tarifário da coluna ciclo_tarifario; some por concessionária "
       "ou contrato (ou use rap_transmissao_concessionaria). situacao 'Ativa' = receita em vigor; 'Prevista' = obra "
       "ainda não em operação.",
       "ANEEL SIGET, Lista de Módulos Prévia - Reajuste RAP, "
       "https://dadosabertos.aneel.gov.br/dataset/sistema-de-gestao-da-transmissao-siget",
       "lista PRÉVIA ao reajuste (não é a resolução homologatória) e sem a Parcela de Ajuste (PA): pode diferir da RAP "
       "divulgada pela empresa. Valores de 100% da concessão (não proporcionais à participação do grupo; para isso "
       "junte com participacoes_societarias). Tipos: RBSE e RPC = instalações antigas prorrogadas (Lei 12.783); RBL = "
       "licitadas; RBNI = reforços e melhorias autorizados; RMEL = melhorias; sufixo A/P = prevista. "
       "Some Ativa e Prevista separadamente")
    con.execute("""CREATE VIEW rap_transmissao_concessionaria AS
SELECT concessionaria, cnpj, contrato, situacao, any_value(ciclo_tarifario) AS ciclo_tarifario,
       round(sum(rap_ciclo_brl), 2) AS rap_ciclo_brl, count(*) AS modulos,
       string_agg(DISTINCT tipo_receita, ', ') AS tipos_receita
FROM rap_transmissao_modulos GROUP BY concessionaria, cnpj, contrato, situacao""")
    CATALOGO.append(("rap_transmissao_concessionaria", "RAP das transmissoras somada por concessionária (com CNPJ), "
                     "contrato e situação (Ativa ou Prevista), em R$ por ano, no ciclo da coluna ciclo_tarifario.",
                     "ANEEL SIGET, Lista de Módulos Prévia - Reajuste RAP; soma desta plataforma",
                     "lista prévia, sem Parcela de Ajuste; 100% da concessão. Para RAP por grupo use rap_por_grupo", None))
    if os.path.exists(SOC):
        con.execute("""CREATE VIEW rap_por_grupo AS
SELECT g.chave_participante, any_value(g.cnpj_participante) AS cnpj_participante, mode(g.participante) AS participante,
       r.situacao, any_value(r.ciclo_tarifario) AS ciclo_tarifario, count(DISTINCT r.contrato) AS contratos,
       round(sum(r.rap_ciclo_brl * g.participacao_indireta_pct / 100), 2) AS rap_proporcional_brl,
       round(sum(r.rap_ciclo_brl) FILTER (WHERE g.na_cadeia_de_controle), 2) AS rap_controlada_brl
FROM rap_transmissao_modulos r JOIN participacoes_societarias g ON g.cnpj_agente = r.cnpj
WHERE g.perfil = 'pessoa jurídica'
GROUP BY g.chave_participante, r.situacao""")
        CATALOGO.append(("rap_por_grupo", "RAP de transmissão atribuída a cada grupo ou empresa: proporcional à "
                         "participação indireta em cada concessionária e controlada (100% das concessionárias que o grupo "
                         "controla), por situação (Ativa ou Prevista), em R$ por ano. Para a RAP das concessões em nome da própria "
                         "empresa (sem SPEs e participações) use rap_transmissao_concessionaria filtrando o cnpj.",
                         "ANEEL SIGET (RAP) e Composição Societária; cálculo desta plataforma",
                         "lista prévia do reajuste, sem Parcela de Ajuste; concessionárias sem declaração societária ficam "
                         "fora; um grupo aparece em vários níveis (não some chaves diferentes)", None))

# ---------------------------------------------------------------- ANEEL: micro e minigeração distribuída (MMGD)
MMGD = os.path.join(AN, "mmgd", "empreendimento-geracao-distribuida.parquet")
if os.path.exists(MMGD):
    tabela("gd_mmgd", f"""
SELECT fmt_cnpj(CAST(NumCNPJDistribuidora AS VARCHAR)) AS cnpj_distribuidora, any_value(SigAgente) AS distribuidora,
       SigUF AS uf, DscClasseConsumo AS classe, SigTipoGeracao AS tipo_geracao, DscFonteGeracao AS fonte,
       DscPorte AS porte, DscModalidadeHabilitado AS modalidade,
       CAST(date_trunc('month', DthAtualizaCadastralEmpreend) AS DATE) AS mes_cadastro,
       count(*) AS empreendimentos, sum(MdaPotenciaInstaladaKW) / 1000 AS potencia_mw,
       sum(QtdUCRecebeCredito) AS ucs_recebem_credito, any_value(AnmPeriodoReferencia) AS periodo_referencia
FROM '{MMGD}' GROUP BY ALL
""", "Micro e minigeração distribuída (MMGD, painéis solares em telhados e usinas de até 5 MW na rede da "
       "distribuidora) agregada por distribuidora, UF, classe de consumo, fonte, porte, modalidade e mês de cadastro: "
       "número de empreendimentos e potência instalada em MW. Some tudo para o total conectado; filtre mes_cadastro "
       "para a evolução.",
       "ANEEL, Relação de Empreendimentos de Geração Distribuída, "
       "https://dadosabertos.aneel.gov.br/dataset/relacao-de-empreendimentos-de-geracao-distribuida",
       "mes_cadastro é a data da última atualização cadastral do empreendimento (aproxima a data de conexão, mas pode ser "
       "posterior); a base é uma fotografia do estoque conectado em periodo_referencia. Titulares (CPF/CNPJ) não entram")

# ---------------------------------------------------------------- ANEEL: RALIE, expansão da geração em implantação
RALIE = os.path.join(AN, "ralie", "ralie-usina-atual.csv")
if os.path.exists(RALIE):
    ralie_ug = os.path.join(AN, "ralie", "ralie-unidade-geradora-atual.csv")
    tabela("expansao_geracao", f"""
WITH ug AS (
  SELECT CodCEG, count(*) AS unidades,
         min(TRY_CAST(DatUGInicioOpComerOutorgado AS DATE)) AS primeira_operacao_outorgada,
         max(TRY_CAST(DatUGInicioOpComerOutorgado AS DATE)) AS ultima_operacao_outorgada,
         min(TRY_CAST(DatPrevisaoOpComercialSFG AS DATE)) AS primeira_operacao_prevista_aneel,
         max(TRY_CAST(DatPrevisaoOpComercialSFG AS DATE)) AS ultima_operacao_prevista_aneel
  FROM read_csv('{ralie_ug}', delim=';', header=true, all_varchar=true) GROUP BY CodCEG)
SELECT u.CodCEG AS ceg, u.NomEmpreendimento AS nome, u.SigUFPrincipal AS uf, u.DscOrigemCombustivel AS origem,
       u.SigTipoGeracao AS tipo_geracao, num_br(u.MdaPotenciaOutorgadaKw) / 1000 AS potencia_outorgada_mw,
       u.DscPropriRegimePariticipacao AS proprietarios_texto, u.DscSituacaoObra AS situacao_obra,
       u.DscViabilidade AS viabilidade, u.DscSituacaoCronograma AS situacao_cronograma,
       u.DscComercializacaoEnergia AS comercializacao, u.DscSistema AS sistema, u.NomComplexo AS complexo,
       TRY_CAST(u.DatPrevisaoInicioObra AS DATE) AS previsao_inicio_obra,
       TRY_CAST(u.DatInicioObraRealizado AS DATE) AS inicio_obra_realizado,
       ug.unidades, ug.primeira_operacao_outorgada, ug.ultima_operacao_outorgada,
       ug.primeira_operacao_prevista_aneel, ug.ultima_operacao_prevista_aneel,
       u.DscSituacaoLI AS licenca_instalacao, u.DscTipoOutorga AS tipo_outorga, u.DscJustificativaPrevisao AS justificativa,
       TRY_CAST(u.DatRalie AS DATE) AS data_base
FROM read_csv('{RALIE}', delim=';', header=true, all_varchar=true) u LEFT JOIN ug USING (CodCEG)
""", "Usinas outorgadas ainda não concluídas acompanhadas pela ANEEL (RALIE): potência, situação da obra (em "
       "andamento, não iniciada, paralisada), viabilidade, situação do cronograma e datas de entrada em operação "
       "outorgada (ato de outorga) e prevista pela fiscalização da ANEEL, por unidade geradora. Use para a expansão "
       "da oferta e atrasos; os donos com CNPJ estão em usinas_proprietarios pelo ceg.",
       "ANEEL, RALIE, https://dadosabertos.aneel.gov.br/dataset/"
       "ralie-relatorio-de-acompanhamento-da-expansao-da-oferta-de-geracao-de-energia-eletrica",
       "potência em MW; datas previstas pela ANEEL (SFG) podem ser revistas a cada mês; primeira/última = primeira e "
       "última unidade geradora da usina")

# ---------------------------------------------------------------- ANEEL: SAMP, mercado e receita das distribuidoras
samp = sorted(glob.glob(os.path.join(AN, "samp", "samp-*.parquet")))
samp = [f for f in samp if re.search(r"samp-\d{4}\.parquet$", f)]
if samp:
    lista = ", ".join(f"'{f}'" for f in samp)
    tabela("mercado_distribuidoras_mensal", f"""
WITH s AS (SELECT *, lower(DscDetalheMercado) AS d, NomTipoMercado ILIKE '%refaturamento%' AS refat
           FROM read_parquet([{lista}], union_by_name=true))
SELECT fmt_cnpj(CAST(NumCNPJAgenteDistribuidora AS VARCHAR)) AS cnpj, any_value(SigAgenteDistribuidora) AS distribuidora,
       CAST(DatCompetencia AS DATE) AS mes, DscClasseConsumoMercado AS classe, DscOpcaoEnergia AS mercado,
       sum(VlrMercado) FILTER (d = 'número de consumidores' AND NOT refat) AS consumidores,
       round(sum(VlrMercado) FILTER (d = 'energia tusd (kwh)') / 1000, 3) AS energia_tusd_mwh,
       round(sum(VlrMercado) FILTER (d = 'energia te (kwh)') / 1000, 3) AS energia_te_mwh,
       round(sum(VlrMercado) FILTER (d = 'energia injetada (kwh)') / 1000, 3) AS energia_injetada_gd_mwh,
       round(sum(VlrMercado) FILTER (d = 'energia compensada (kwh)') / 1000, 3) AS energia_compensada_gd_mwh,
       round(sum(VlrMercado) FILTER (d = 'receita energia (r$)'), 2) AS receita_energia_brl,
       round(sum(VlrMercado) FILTER (d = 'receita demanda (r$)'), 2) AS receita_demanda_brl,
       round(sum(VlrMercado) FILTER (d = 'receita bandeiras (r$)'), 2) AS receita_bandeiras_brl,
       round(sum(VlrMercado) FILTER (d = 'icms (r$)'), 2) AS icms_brl,
       round(sum(VlrMercado) FILTER (d IN ('pis/pasep (r$)', 'cofins (r$)', 'pis/cofins (r$)')), 2) AS pis_cofins_brl,
       round((sum(VlrMercado) FILTER (d IN ('receita energia (r$)', 'receita demanda (r$)')))
             / nullif(sum(VlrMercado) FILTER (d = 'energia tusd (kwh)') / 1000, 0), 2) AS tarifa_media_sem_tributos_brl_mwh
FROM s GROUP BY ALL
""", "Mercado e faturamento mensal de cada distribuidora por classe de consumo (Residencial, Comercial, Industrial, "
       "Rural...) e mercado (CATIVO, LIVRE, GERAÇÃO, SUPRIMENTO), de 2020 em diante: consumidores, energia faturada em "
       "MWh, receitas de energia, demanda e bandeiras, tributos e a tarifa média sem tributos em R$/MWh. Para a tarifa "
       "média do ano some receita_energia_brl + receita_demanda_brl e divida pela soma de energia_tusd_mwh (não tire "
       "média das médias mensais).",
       "ANEEL, SAMP - Sistema de Acompanhamento de Informações de Mercado, https://dadosabertos.aneel.gov.br/dataset/samp",
       "dado declarado pela distribuidora ao SAMP; mercado LIVRE paga só a TUSD (fio): não compare a tarifa média "
       "do livre com a do cativo. Receitas sem ICMS e PIS/COFINS; refaturamentos entram nas energias e receitas mas "
       "não no número de consumidores. O ano corrente é parcial e meses recentes podem ser revistos. Há erros de "
       "declaração na fonte (ex.: Cemig D, Residencial, jul/2025 e out/2025, receita de energia ~10 vezes o normal): "
       "confira a tarifa média mês a mês antes de somar o ano e aponte meses discrepantes")

# ---------------------------------------------------------------- ANEEL: bandeiras tarifárias
BAND = os.path.join(AN, "bandeiras", "bandeira-tarifaria-acionamento.csv")
if os.path.exists(BAND):
    tabela("bandeiras_tarifarias", f"""
SELECT CAST(TRY_CAST(DatCompetencia AS DATE) AS DATE) AS mes, trim(NomBandeiraAcionada) AS bandeira,
       num_br(VlrAdicionalBandeira) AS adicional_brl_mwh
FROM read_csv('{BAND}', delim=';', header=true, all_varchar=true) ORDER BY mes
""", "Bandeira tarifária acionada pela ANEEL em cada mês (Verde, Amarela, Vermelha P1, Vermelha P2, Escassez "
       "Hídrica) e o adicional cobrado na conta, em R$/MWh, desde 2015.",
       "ANEEL, Bandeiras Tarifárias - Acionamento, https://dadosabertos.aneel.gov.br/dataset/bandeiras-tarifarias",
       "adicional em R$/MWh (divida por 10 para R$ por 100 kWh); vale para o consumidor cativo do SIN")

# ---------------------------------------------------------------- ANEEL: ranking de continuidade (DGC)
paginas = sorted(glob.glob(os.path.join(AN, "ranking_continuidade", "ranking_*.html")))
if paginas:
    import html as html_mod
    ranking = []
    for pagina in paginas:
        ano = int(re.search(r"ranking_(\d{4})", pagina).group(1))
        texto = open(pagina, encoding="utf-8", errors="replace").read()
        for i_tab, tab in enumerate(re.findall(r"<table.*?</table>", texto, flags=re.S)[:2]):
            porte = "mais de 400 mil unidades consumidoras" if i_tab == 0 else "até 400 mil unidades consumidoras"
            for tr in re.findall(r"<tr.*?</tr>", tab, flags=re.S):
                cel = [html_mod.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c))).strip()
                       for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, flags=re.S)]
                if len(cel) >= 5 and re.match(r"^\d+", cel[0]):
                    ranking.append((ano, porte, int(re.match(r"\d+", cel[0]).group(0)),
                                    float(cel[1].replace(",", ".")) if re.fullmatch(r"[\d,.]+", cel[1]) else None,
                                    cel[2], cel[3], cel[4]))
    con.execute("""CREATE TEMP TABLE ranking_bruto (ano INTEGER, porte VARCHAR, posicao INTEGER, dgc DOUBLE,
                   sigla VARCHAR, empresa VARCHAR, regiao VARCHAR)""")
    con.executemany("INSERT INTO ranking_bruto VALUES (?, ?, ?, ?, ?, ?, ?)", ranking)
    con.execute(r"""CREATE MACRO chave_razao(x) AS
      trim(regexp_replace(upper(strip_accents(regexp_replace(x, '[^A-Za-z0-9À-ú]', ' ', 'g'))), '\s+', ' ', 'g'))""")
    tabela("ranking_continuidade", r"""
WITH nomes AS (  -- razão social do ranking -> CNPJ pelo cadastro de agentes da ANEEL (distribuidoras)
  SELECT chave_razao(razao_social) AS chave, any_value(cnpj) AS cnpj FROM agentes_aneel WHERE distribuicao GROUP BY 1),
r AS (SELECT r.*, n.cnpj FROM ranking_bruto r LEFT JOIN nomes n ON n.chave = chave_razao(r.empresa)),
por_sigla AS (SELECT sigla, any_value(cnpj) AS cnpj FROM r WHERE cnpj IS NOT NULL GROUP BY sigla)
SELECT r.ano, r.porte, r.posicao, r.dgc, r.sigla, r.empresa, coalesce(r.cnpj, s.cnpj) AS cnpj, r.regiao
FROM r LEFT JOIN por_sigla s USING (sigla)
ORDER BY r.ano, r.porte, r.posicao
""", "Ranking oficial de continuidade da ANEEL: posição de cada distribuidora pelo Desempenho Global de Continuidade "
       "(DGC), de 2021 a 2025, separado em dois grupos de porte. DGC é a média dos DEC e FEC apurados divididos pelos "
       "limites: quanto menor, melhor; abaixo de 1 = dentro dos limites.",
       "ANEEL, Ranking de Continuidade, https://www.gov.br/aneel/pt-br/centrais-de-conteudos/relatorios-e-indicadores/"
       "distribuicao/ranking-de-continuidade",
       "posição dentro do grupo de porte (empates têm a mesma posição); cnpj ligado pela razão social ao cadastro de "
       "agentes da ANEEL, vazio quando o nome não casou; o ano é o dos indicadores, publicado no ano seguinte")

# ---------------------------------------------------------------- Banco Central: indicadores macro
BCB = os.path.join(RAW, "bcb")
if glob.glob(os.path.join(BCB, "sgs_*.json")):
    partes = []
    for arq in sorted(glob.glob(os.path.join(BCB, "sgs_*.json"))):
        codigo, nome = re.match(r"sgs_(\d+)_(\w+)\.json$", os.path.basename(arq)).groups()
        partes.append(f"""SELECT '{nome}' AS serie, {codigo} AS codigo, strptime(data, '%d/%m/%Y')::DATE AS data,
                          TRY_CAST(valor AS DOUBLE) AS valor FROM read_json('{arq}', columns={{data: 'VARCHAR', valor: 'VARCHAR'}})""")
    con.execute("CREATE TEMP TABLE bcb AS " + " UNION ALL ".join(partes))
    tabela("indicadores_macro_mensal", """
WITH m AS (SELECT serie, CAST(date_trunc('month', data) AS DATE) AS mes, arg_max(valor, data) AS ultimo, avg(valor) AS media
           FROM bcb GROUP BY ALL)
SELECT mes,
       max(ultimo) FILTER (serie = 'ipca_mensal') AS ipca_mes_pct,
       max(ultimo) FILTER (serie = 'ipca_12m') AS ipca_12m_pct,
       max(ultimo) FILTER (serie = 'igpm_mensal') AS igpm_mes_pct,
       CASE WHEN count(max(ultimo) FILTER (serie = 'igpm_mensal')) OVER (ORDER BY mes ROWS 11 PRECEDING) = 12 THEN
         round(100 * (exp(sum(ln(1 + max(ultimo) FILTER (serie = 'igpm_mensal') / 100)) OVER (ORDER BY mes ROWS 11 PRECEDING)) - 1), 2)
       END AS igpm_12m_pct,
       max(ultimo) FILTER (serie = 'selic_mensal') AS selic_mes_pct,
       max(ultimo) FILTER (serie = 'cdi_mensal') AS cdi_mes_pct,
       max(ultimo) FILTER (serie = 'selic_meta') AS selic_meta_fim_mes_pct_aa,
       max(ultimo) FILTER (serie = 'dolar_ptax_venda_media_mensal') AS dolar_ptax_medio_brl
FROM m WHERE mes <= current_date GROUP BY mes ORDER BY mes
""", "Indicadores macroeconômicos mensais do Banco Central desde 2000: IPCA do mês e em 12 meses, IGP-M do mês e em "
       "12 meses (índices de reajuste de tarifas e RAP), Selic e CDI acumulados no mês, meta Selic no fim do mês "
       "(% ao ano) e dólar PTAX de venda médio do mês. Use para contexto de tarifas, RAP e custo da dívida.",
       "Banco Central, SGS (api.bcb.gov.br): séries 433 (IPCA), 13522 (IPCA 12 meses), 189 (IGP-M), 4390 (Selic "
       "mensal), 4391 (CDI mensal), 432 (meta Selic), 3698 (dólar PTAX venda, média mensal)",
       "IPCA, IGP-M, Selic e CDI do mês em % no mês (não anualizados); igpm_12m_pct é acumulado pela plataforma; "
       "o mês corrente pode estar vazio ou parcial (Selic e CDI acumulados até o último dia útil publicado)")

# ---------------------------------------------------------------- ONS: carga, ENA, balanço por fonte, intercâmbio, geração por usina
def ons_parquets(pasta):
    return os.path.join(ONS, pasta, "*.parquet") if glob.glob(os.path.join(ONS, pasta, "*.parquet")) else None


if ons_parquets("carga_energia_diaria"):
    tabela("ons_carga_diaria", f"""
SELECT trim(id_subsistema) AS subsistema, CAST(din_instante AS DATE) AS data,
       TRY_CAST(val_cargaenergiamwmed AS DOUBLE) AS carga_mwmed
FROM read_parquet('{ons_parquets("carga_energia_diaria")}', union_by_name=true)
""", "Carga de energia diária do SIN por subsistema (N, NE, S, SE = Sudeste/Centro-Oeste), em MW médio, desde 2000. "
       "Energia do dia em MWh = carga_mwmed × 24.", "ONS, Carga de Energia, https://dados.ons.org.br/dataset/carga-energia",
       "MW médio (média do dia), não MWh; inclui estimativa de micro e minigeração conforme a metodologia do ONS; "
       "dados recentes podem ser revistos")
if ons_parquets("ena_diario_subsistema"):
    tabela("ons_ena_diaria", f"""
SELECT trim(id_subsistema) AS subsistema, TRY_CAST(ena_data AS DATE) AS data,
       TRY_CAST(ena_bruta_regiao_mwmed AS DOUBLE) AS ena_bruta_mwmed,
       TRY_CAST(ena_bruta_regiao_percentualmlt AS DOUBLE) AS ena_bruta_pct_mlt,
       TRY_CAST(ena_armazenavel_regiao_mwmed AS DOUBLE) AS ena_armazenavel_mwmed,
       TRY_CAST(ena_armazenavel_regiao_percentualmlt AS DOUBLE) AS ena_armazenavel_pct_mlt
FROM read_parquet('{ons_parquets("ena_diario_subsistema")}', union_by_name=true)
""", "Energia Natural Afluente (ENA) diária por subsistema, em MW médio e em % da média de longo termo (MLT), desde "
       "2021: mede quanta água chega aos reservatórios. Abaixo de 100% da MLT = afluência abaixo da média histórica.",
       "ONS, ENA Diário por Subsistema, https://dados.ons.org.br/dataset/ena-diario-por-subsistema",
       "SE = Sudeste/Centro-Oeste; para média mensal faça a média dos dias; dados recentes podem ser revistos")
if ons_parquets("balanco_energia_subsistema"):
    tabela("ons_geracao_fonte_mensal", f"""
WITH b AS (SELECT trim(id_subsistema) AS subsistema, din_instante,
                  TRY_CAST(val_gerhidraulica AS DOUBLE) AS h, TRY_CAST(val_gertermica AS DOUBLE) AS t,
                  TRY_CAST(val_gereolica AS DOUBLE) AS e, TRY_CAST(val_gersolar AS DOUBLE) AS s,
                  TRY_CAST(val_carga AS DOUBLE) AS c, TRY_CAST(val_intercambio AS DOUBLE) AS i
           FROM read_parquet('{ons_parquets("balanco_energia_subsistema")}', union_by_name=true))
SELECT subsistema, CAST(date_trunc('month', din_instante) AS DATE) AS mes,
       round(sum(h), 1) AS hidraulica_mwh, round(sum(t), 1) AS termica_mwh, round(sum(e), 1) AS eolica_mwh,
       round(sum(s), 1) AS solar_mwh, round(sum(h) + sum(t) + sum(e) + sum(s), 1) AS geracao_total_mwh,
       round(sum(c), 1) AS carga_mwh, round(sum(i), 1) AS intercambio_liquido_mwh, count(*) AS horas
FROM b GROUP BY ALL
""", "Geração mensal por fonte (hidráulica, térmica, eólica, solar) e carga por subsistema (N, NE, S, SE e SIN), em "
       "MWh, desde 2015, somando o balanço horário do ONS. Use para matriz de geração, participação das renováveis e "
       "exportação do Nordeste. subsistema 'SIN' é o total do sistema.",
       "ONS, Balanço de Energia nos Subsistemas, https://dados.ons.org.br/dataset/balanco-energia-subsistema",
       "térmica inclui nuclear; solar é a centralizada despachada pelo ONS (a micro e minigeração entra abatendo a "
       "carga); intercâmbio positivo = exportação do subsistema; mês corrente parcial (veja horas)")
if ons_parquets("intercambio_nacional"):
    tabela("ons_intercambio_mensal", f"""
SELECT trim(id_subsistema_origem) AS origem, trim(id_subsistema_destino) AS destino,
       CAST(date_trunc('month', din_instante) AS DATE) AS mes,
       round(sum(TRY_CAST(val_intercambiomwmed AS DOUBLE)), 1) AS intercambio_verificado_mwh,
       round(sum(TRY_CAST(val_intercambioprogmwmed AS DOUBLE)), 1) AS intercambio_programado_mwh, count(*) AS horas
FROM read_parquet('{ons_parquets("intercambio_nacional")}', union_by_name=true) GROUP BY ALL
""", "Intercâmbio mensal de energia entre subsistemas (origem -> destino), verificado e programado, em MWh, desde "
       "2023, somando os valores horários do ONS.", "ONS, Intercâmbio Nacional, https://dados.ons.org.br/dataset/intercambio-nacional",
       "valor negativo = fluxo no sentido destino -> origem; mês corrente parcial")
if ons_parquets("geracao_usina"):
    tabela("ons_geracao_usina_mensal", f"""
SELECT trim(id_subsistema) AS subsistema, id_estado AS uf, nom_usina AS usina, nullif(trim(ceg), '-') AS ceg,
       id_ons, nom_tipousina AS tipo_usina, nom_tipocombustivel AS combustivel, cod_modalidadeoperacao AS modalidade,
       CAST(date_trunc('month', din_instante) AS DATE) AS mes,
       round(sum(TRY_CAST(val_geracao AS DOUBLE)), 3) AS geracao_mwh, count(*) AS horas
FROM read_parquet('{ons_parquets("geracao_usina")}', union_by_name=true) GROUP BY ALL
""", "Geração verificada mensal de cada usina despachada ou monitorada pelo ONS, em MWh, desde 2020 (soma da "
       "geração horária). ceg liga com usinas e usinas_proprietarios (use o núcleo do CEG, sem o sufixo de versão); "
       "para fator de capacidade divida por potência × horas.",
       "ONS, Geração por Usina em Base Horária, https://dados.ons.org.br/dataset/geracao-usina-2",
       "só usinas do SIN com dado no ONS (Tipo I, II e conjuntos); 'Pequenas Usinas (MMGD)' são estimativas agregadas "
       "por estado; conjuntos eólicos e solares aparecem com o nome do conjunto e sem ceg; mês corrente parcial")

# ---------------------------------------------------------------- SND (ANBIMA/B3): debêntures com vencimento e taxa
SND = os.path.join(RAW, "snd", "debentures_caracteristicas.xls")
if os.path.exists(SND):
    with open(SND, encoding="latin-1") as f:
        linhas_snd = [l.rstrip("\r\n").split("\t") for l in f]
    i_cab = next(i for i, l in enumerate(linhas_snd) if l and l[0].strip() == "Codigo do Ativo")
    cab = linhas_snd[i_cab]
    snd_csv = os.path.join(trabalho, "snd.csv")
    with open(snd_csv, "w", newline="") as g:
        w = csv.writer(g, delimiter=";", quoting=csv.QUOTE_ALL)
        w.writerow([f"c{j}" for j in range(len(cab))])
        for l in linhas_snd[i_cab + 1:]:
            if len(l) >= len(cab) - 2 and l[0].strip():
                w.writerow([v.strip() for v in (l + [""] * len(cab))[:len(cab)]])
    col = {nome.strip(): f"c{j}" for j, nome in reversed(list(enumerate(cab)))}  # primeira ocorrência de cada nome

    def c(nome):
        return col[nome]
    tabela("debentures_snd", f"""
WITH d AS (SELECT * FROM read_csv('{snd_csv}', delim=';', header=true, all_varchar=true, quote='"', escape='"')),
setor AS (SELECT cnpj FROM empresas UNION SELECT cnpj FROM agentes_aneel WHERE geracao OR transmissao OR distribuicao)
SELECT d.{c('Codigo do Ativo')} AS codigo, d.{c('Empresa')} AS emissora, fmt_cnpj(d.{c('CNPJ')}) AS cnpj,
       fmt_cnpj(d.{c('CNPJ')}) IN (SELECT cnpj FROM setor) AS setor_eletrico,
       d.{c('Situacao')} AS situacao, d.{c('Emissao')} AS emissao, d.{c('Serie')} AS serie, d.{c('ISIN')} AS isin,
       data_br(d.{c('Data de Emissao')}) AS data_emissao, data_br(d.{c('Data de Vencimento')}) AS data_vencimento,
       data_br(d.{c('Data de Saida / Novo Vencimento')}) AS data_saida_ou_novo_vencimento, d.{c('Motivo de Saida')} AS motivo_saida,
       nullif(d.{c('indice')}, '') AS indice, num_br(d.{c('Percentual Multiplicador/Rentabilidade')}) AS percentual_indice,
       num_br(d.{c('Juros Criterio Novo - Taxa')}) AS taxa_juros_pct_aa,
       d.{c('Deb. Incent. (Lei 12.431)')} = 'S' AS incentivada_lei_12431, d.{c('Garantia/Especie')} AS garantia,
       TRY_CAST(d.{c('Quantidade Emitida')} AS BIGINT) AS quantidade_emitida,
       TRY_CAST(d.{c('Quantidade em Mercado')} AS BIGINT) AS quantidade_em_mercado,
       num_br(d.{c('Valor Nominal na Emissao')}) AS valor_nominal_emissao_brl,
       num_br(d.{c('Valor Nominal Atual')}) AS valor_nominal_atual_brl, data_br(d.{c('Data Ult. VNA')}) AS data_valor_nominal_atual,
       TRY_CAST(d.{c('Quantidade Emitida')} AS BIGINT) * num_br(d.{c('Valor Nominal na Emissao')}) AS volume_emitido_brl,
       TRY_CAST(d.{c('Quantidade em Mercado')} AS BIGINT) * num_br(d.{c('Valor Nominal Atual')}) AS saldo_em_mercado_brl,
       d.{c('Resgate Antecipado')} = 'S' AS permite_resgate_antecipado, d.{c('Coordenador Lider')} AS coordenador_lider,
       d.{c('Agente Fiduciario')} AS agente_fiduciario
FROM d
""", "Todas as debêntures registradas no SND (Sistema Nacional de Debêntures), com CNPJ da emissora, data de emissão "
       "e de vencimento, indexador (DI, IPCA, PRE...) e taxa, se é incentivada (Lei 12.431), garantia, quantidade e "
       "saldo em mercado. setor_eletrico marca emissoras do setor (CVM ou agentes da ANEEL). Use para cronograma de "
       "vencimentos e custo da dívida em debêntures de uma empresa (filtre situacao = 'Registrado' para as vigentes).",
       "SND/ANBIMA, Características das Debêntures, https://www.debentures.com.br/exploreosnd/consultaadados/"
       "emissoesdedebentures/caracteristicas_r.asp",
       "saldo_em_mercado_brl = quantidade em mercado × valor nominal atualizado na data_valor_nominal_atual, sem juros "
       "acumulados (aproxima o principal, não o valor contábil); não inclui amortizações futuras por data (só o "
       "vencimento final); taxa_juros_pct_aa é a sobretaxa ou taxa pré conforme o índice (ex.: DI + 1,2% ou IPCA + 6%), "
       "e percentual_indice é o % do índice (ex.: 100% do DI). SPEs de um grupo emitem com CNPJ próprio: junte com "
       "participacoes_societarias para somar por grupo")

# ---------------------------------------------------------------- catálogo das tabelas (lido pelo MCP)
con.execute("CREATE TABLE catalogo (tabela VARCHAR, descricao VARCHAR, fonte VARCHAR, ressalvas VARCHAR, linhas BIGINT)")
con.executemany("INSERT INTO catalogo VALUES (?, ?, ?, ?, ?)", CATALOGO)
con.close()
shutil.rmtree(trabalho)
os.replace(tmp, destino)
print("ok:", destino)

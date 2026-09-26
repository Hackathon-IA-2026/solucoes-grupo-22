#!/usr/bin/env python3
"""Exporta os dados quantitativos do coppezip.duckdb para o painel da interface (aba Painel do LibreChat).

Uso: python data/exportar_painel.py
Rode depois de construir o banco (data/construir.py). Lê data/coppezip.duckdb e grava data/painel.json, que a rota
/api/painel/dados do LibreChat relê a cada acesso: não precisa reiniciar.

Cada conjunto declara o eixo de tempo, as dimensões (filtros e séries) e as medidas com a regra para juntar linhas:
soma, razao (soma do numerador / soma do denominador, como as margens), ponderada (média ponderada), media, min, max.
Assim o painel recalcula margens e percentuais ao agrupar, em vez de somar percentuais. Tabelas ausentes (as que o
construir.py só monta quando o arquivo bruto existe) são puladas. Descrição, fonte e ressalvas vêm do catálogo, o mesmo
texto do modelo.
Nas dimensões que identificam uma empresa (um CNPJ por valor), o filtro também acha pelo CNPJ, pelos apelidos e tickers
de empresas_apelidos e pelo nome comercial (Taesa, Enel SP, EGIE3), como a ferramenta buscar_empresa.
"""
import datetime
import json
import math
import os

import duckdb

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raiz do repositório
BANCO = os.path.join(RAIZ, "data", "coppezip.duckdb")
DESTINO = os.path.join(RAIZ, "data", "painel.json")


def m(coluna, rotulo, unidade, agregacao="soma", **regra):
    """Medida: unidade em brl, pct, x, h, n, mw, mwh, mwmed, mwmes, brl_mwh; regra: num, den, fator, den_abs, peso."""
    return {"coluna": coluna, "rotulo": rotulo, "unidade": unidade, "agregacao": agregacao, **regra}


def razao(coluna, rotulo, unidade, num, den, fator=1, den_abs=False):
    return m(coluna, rotulo, unidade, "razao", num=num, den=den, fator=fator, den_abs=den_abs)


def d(coluna, rotulo, papel=None):
    """Dimensão. papel="empresa": a linha É uma empresa e esta coluna a nomeia (uma linha por empresa e período).
    papel="dono": a linha é um ativo ou um contrato e esta coluna nomeia quem o detém (várias linhas por CNPJ).
    O grafo usa essa distinção: só as bases por empresa criam empresa; as por ativo entram nas que já existem."""
    assert papel in (None, "empresa", "dono"), papel
    return {"coluna": coluna, "rotulo": rotulo, **({"papel": papel} if papel else {})}


NOME_ATUAL = "arg_max({nome}, {ordem}) OVER (PARTITION BY cnpj)"  # a razão social muda com os anos; a série segue o CNPJ

CONJUNTOS = [
    dict(id="kpis_anuais", tabela="kpis_financeiros", grupo="Financeiro", titulo="Indicadores financeiros anuais",
         sql=f"""SELECT {NOME_ATUAL.format(nome='empresa', ordem='ano')} AS empresa, escopo, ano::VARCHAR AS ano, *
                 EXCLUDE (empresa, escopo, ano, contas_capex) FROM kpis_financeiros ORDER BY empresa, ano""",
         tempo=d("ano", "Ano"), granularidade="ano",
         dimensoes=[d("empresa", "Empresa", papel="empresa"), d("escopo", "Escopo")],
         medidas=[m("receita_liquida_brl", "Receita líquida", "brl"), m("ebit_brl", "EBIT", "brl"),
                  m("ebitda_brl", "EBITDA", "brl"), m("depreciacao_amortizacao_brl", "Depreciação e amortização", "brl"),
                  m("lucro_liquido_brl", "Lucro líquido", "brl"),
                  m("resultado_financeiro_brl", "Resultado financeiro", "brl"),
                  m("despesas_financeiras_brl", "Despesas financeiras", "brl"),
                  m("ativo_total_brl", "Ativo total", "brl"), m("patrimonio_liquido_brl", "Patrimônio líquido", "brl"),
                  m("divida_bruta_brl", "Dívida bruta", "brl"), m("caixa_aplicacoes_brl", "Caixa e aplicações", "brl"),
                  m("divida_liquida_brl", "Dívida líquida", "brl"),
                  m("caixa_operacional_brl", "Caixa operacional", "brl"), m("capex_brl", "CAPEX", "brl"),
                  m("custo_construcao_concessao_brl", "Custo de construção da concessão", "brl"),
                  m("investimento_total_brl", "Investimento total", "brl"),
                  m("dividendos_jcp_pagos_brl", "Dividendos e JCP pagos", "brl"),
                  razao("margem_ebit_pct", "Margem EBIT", "pct", "ebit_brl", "receita_liquida_brl", 100),
                  razao("margem_ebitda_pct", "Margem EBITDA", "pct", "ebitda_brl", "receita_liquida_brl", 100),
                  razao("margem_liquida_pct", "Margem líquida", "pct", "lucro_liquido_brl", "receita_liquida_brl", 100),
                  razao("divida_liquida_ebitda", "Dívida líquida / EBITDA", "x", "divida_liquida_brl", "ebitda_brl"),
                  razao("cobertura_juros_ebitda", "Cobertura de juros (EBITDA / despesas financeiras)", "x",
                        "ebitda_brl", "despesas_financeiras_brl", den_abs=True),
                  razao("roe_pct", "ROE", "pct", "lucro_liquido_brl", "patrimonio_liquido_brl", 100)],
         extras=[d("cnpj", "CNPJ"), d("fonte", "Fonte")],
         padrao=dict(medida="receita_liquida_brl", serie="empresa", filtros={"escopo": ["consolidado"]})),
    dict(id="kpis_trimestrais", tabela="kpis_trimestrais", grupo="Financeiro", titulo="Indicadores financeiros trimestrais",
         sql=f"""SELECT {NOME_ATUAL.format(nome='empresa', ordem='data_referencia')} AS empresa, escopo,
                 ano || 'T' || trimestre AS periodo, strftime(data_referencia, '%Y-%m-%d') AS data_referencia, *
                 EXCLUDE (empresa, escopo, ano, trimestre, data_referencia) FROM kpis_trimestrais
                 ORDER BY empresa, periodo""",
         tempo=d("periodo", "Trimestre"), granularidade="trimestre",
         dimensoes=[d("empresa", "Empresa", papel="empresa"), d("escopo", "Escopo")],
         medidas=[m("receita_liquida_trimestre_brl", "Receita líquida do trimestre", "brl"),
                  m("ebit_trimestre_brl", "EBIT do trimestre", "brl"),
                  m("lucro_trimestre_brl", "Lucro do trimestre", "brl"),
                  m("receita_liquida_acumulada_brl", "Receita líquida acumulada no ano", "brl"),
                  m("ebit_acumulado_brl", "EBIT acumulado no ano", "brl"),
                  m("ebitda_acumulado_brl", "EBITDA acumulado no ano", "brl"),
                  m("lucro_acumulado_brl", "Lucro acumulado no ano", "brl"),
                  m("receita_liquida_12m_brl", "Receita líquida 12 meses", "brl"),
                  m("ebitda_12m_brl", "EBITDA 12 meses", "brl"), m("lucro_12m_brl", "Lucro 12 meses", "brl"),
                  m("divida_bruta_brl", "Dívida bruta", "brl"), m("caixa_aplicacoes_brl", "Caixa e aplicações", "brl"),
                  m("divida_liquida_brl", "Dívida líquida", "brl"),
                  razao("divida_liquida_ebitda_12m", "Dívida líquida / EBITDA 12 meses", "x",
                        "divida_liquida_brl", "ebitda_12m_brl"),
                  m("patrimonio_liquido_brl", "Patrimônio líquido", "brl"),
                  m("capex_acumulado_brl", "CAPEX acumulado no ano", "brl"),
                  m("custo_construcao_acumulado_brl", "Custo de construção acumulado no ano", "brl"),
                  m("investimento_acumulado_brl", "Investimento acumulado no ano", "brl")],
         extras=[d("cnpj", "CNPJ"), d("data_referencia", "Data de referência"), d("fonte", "Fonte")],
         padrao=dict(medida="receita_liquida_trimestre_brl", serie="empresa", filtros={"escopo": ["consolidado"]})),
    dict(id="dec_fec", tabela="dec_fec_distribuidora_anual", grupo="Distribuição", titulo="DEC e FEC por distribuidora",
         sql=f"""SELECT {NOME_ATUAL.format(nome='distribuidora', ordem='ano')} AS distribuidora, ano::VARCHAR AS ano, *
                 EXCLUDE (distribuidora, ano) FROM dec_fec_distribuidora_anual ORDER BY distribuidora, ano""",
         tempo=d("ano", "Ano"), granularidade="ano",
         dimensoes=[d("distribuidora", "Distribuidora", papel="empresa")],
         medidas=[m("dec_horas", "DEC (horas)", "h", "ponderada", peso="consumidores_medios"),
                  m("dec_limite_medio_ponderado_horas", "Limite de DEC (horas)", "h", "ponderada",
                    peso="consumidores_medios"),
                  m("fec_interrupcoes", "FEC (interrupções)", "n", "ponderada", peso="consumidores_medios"),
                  m("fec_limite_medio_ponderado", "Limite de FEC (interrupções)", "n", "ponderada",
                    peso="consumidores_medios"),
                  m("consumidores_medios", "Consumidores (média)", "n")],
         extras=[d("cnpj", "CNPJ"), d("meses", "Meses com dados"), d("fonte", "Fonte")],
         padrao=dict(medida="dec_horas", serie="distribuidora")),
    dict(id="cmo", tabela="ons_cmo_mensal", grupo="Mercado", titulo="CMO mensal por subsistema",
         sql="""SELECT nome_subsistema AS subsistema, strftime(mes, '%Y-%m') AS mes, cmo_medio_brl_mwh,
                cmo_minimo_brl_mwh, cmo_maximo_brl_mwh, intervalos, dias_com_dados, dias_ausentes
                FROM ons_cmo_mensal ORDER BY subsistema, mes""",
         tempo=d("mes", "Mês"), granularidade="mes",
         dimensoes=[d("subsistema", "Subsistema")],
         medidas=[m("cmo_medio_brl_mwh", "CMO médio", "brl_mwh", "ponderada", peso="intervalos"),
                  m("cmo_minimo_brl_mwh", "CMO mínimo", "brl_mwh", "min"),
                  m("cmo_maximo_brl_mwh", "CMO máximo", "brl_mwh", "max")],
         extras=[d("intervalos", "Intervalos"), d("dias_com_dados", "Dias com dados"),
                 d("dias_ausentes", "Dias ausentes")],
         padrao=dict(medida="cmo_medio_brl_mwh", serie="subsistema")),
    dict(id="ear", tabela="ons_ear_diario", grupo="Mercado", titulo="Energia armazenada (EAR) diária",
         sql="""SELECT nome_subsistema AS subsistema, strftime(data, '%Y-%m-%d') AS data, ear_verificada_pct,
                ear_verificada_mwmes, ear_maxima_mwmes FROM ons_ear_diario ORDER BY subsistema, data""",
         tempo=d("data", "Data"), granularidade="dia",
         dimensoes=[d("subsistema", "Subsistema")],
         medidas=[razao("ear_verificada_pct", "EAR (% da capacidade)", "pct",
                        "ear_verificada_mwmes", "ear_maxima_mwmes", 100),
                  m("ear_verificada_mwmes", "EAR verificada", "mwmes"),
                  m("ear_maxima_mwmes", "EAR máxima", "mwmes")],
         extras=[],
         padrao=dict(medida="ear_verificada_pct", serie="subsistema", desde="2020-01-01")),
    dict(id="curtailment", tabela="ons_curtailment_mensal", grupo="Renováveis", titulo="Curtailment por usina",
         sql="""SELECT fonte, subsistema, uf, agente_operador, usina, strftime(mes, '%Y-%m') AS mes,
                energia_cortada_mwh, geracao_mwh, referencia_mwh, corte_pct, id_ons, ceg
                FROM ons_curtailment_mensal ORDER BY usina, mes""",
         tempo=d("mes", "Mês"), granularidade="mes",
         dimensoes=[d("fonte", "Fonte"), d("subsistema", "Subsistema"), d("uf", "UF"),
                    d("agente_operador", "Agente operador"), d("usina", "Usina")],
         medidas=[m("energia_cortada_mwh", "Energia cortada", "mwh"), m("geracao_mwh", "Geração", "mwh"),
                  m("referencia_mwh", "Geração de referência", "mwh"),
                  razao("corte_pct", "Corte (% da referência)", "pct", "energia_cortada_mwh", "referencia_mwh", 100)],
         extras=[d("id_ons", "ID ONS"), d("ceg", "CEG")],
         padrao=dict(medida="energia_cortada_mwh", serie="fonte")),
    dict(id="curtailment_dono", tabela="curtailment_por_dono_mensal", grupo="Renováveis",
         titulo="Curtailment por dono (estimativa)",
         sql="""SELECT proprietario, fonte, strftime(mes, '%Y-%m') AS mes, energia_cortada_mwh_estimada,
                referencia_mwh_estimada, cnpj, fonte_calculo FROM curtailment_por_dono_mensal
                ORDER BY proprietario, mes""",
         tempo=d("mes", "Mês"), granularidade="mes",
         dimensoes=[d("proprietario", "Dono", papel="dono"), d("fonte", "Fonte")],
         medidas=[m("energia_cortada_mwh_estimada", "Energia cortada (estimada)", "mwh"),
                  m("referencia_mwh_estimada", "Geração de referência (estimada)", "mwh"),
                  razao("corte_pct", "Corte (% da referência)", "pct",
                        "energia_cortada_mwh_estimada", "referencia_mwh_estimada", 100)],
         extras=[d("cnpj", "CNPJ"), d("fonte_calculo", "Cálculo")],
         padrao=dict(medida="energia_cortada_mwh_estimada", serie="proprietario")),
    dict(id="capacidade", tabela="capacidade_por_proprietario", grupo="Geração", titulo="Capacidade instalada por dono",
         sql="""SELECT proprietario, origem, tipo_geracao, fase, potencia_mw, usinas, cnpj,
                strftime(data_base, '%Y-%m-%d') AS data_base, fonte FROM capacidade_por_proprietario
                ORDER BY potencia_mw DESC""",
         dimensoes=[d("origem", "Origem"), d("tipo_geracao", "Tipo"), d("fase", "Fase"),
                    d("proprietario", "Dono", papel="dono")],
         medidas=[m("potencia_mw", "Potência", "mw"), m("usinas", "Usinas", "n")],
         extras=[d("cnpj", "CNPJ"), d("data_base", "Data-base"), d("fonte", "Fonte")],
         padrao=dict(medida="potencia_mw", serie="origem", filtros={"fase": ["Operação"]})),
    dict(id="usinas", tabela="usinas", grupo="Geração", titulo="Usinas por UF, origem e fase",
         sql="""SELECT uf, origem, tipo_geracao, fase, count(*) AS usinas,
                sum(potencia_fiscalizada_kw) / 1000 AS potencia_fiscalizada_mw,
                sum(garantia_fisica_kw) / 1000 AS garantia_fisica_mwmed,
                strftime(max(data_base), '%Y-%m-%d') AS data_base
                FROM usinas GROUP BY ALL ORDER BY potencia_fiscalizada_mw DESC""",
         dimensoes=[d("origem", "Origem"), d("tipo_geracao", "Tipo"), d("fase", "Fase"), d("uf", "UF")],
         medidas=[m("potencia_fiscalizada_mw", "Potência fiscalizada", "mw"), m("usinas", "Usinas", "n"),
                  m("garantia_fisica_mwmed", "Garantia física", "mwmed")],
         extras=[d("data_base", "Data-base")],
         padrao=dict(medida="potencia_fiscalizada_mw", serie="origem", filtros={"fase": ["Operação"]})),
    dict(id="leiloes", tabela="leiloes_geracao", grupo="Geração", titulo="Leilões de geração",
         sql="""SELECT ano::VARCHAR AS ano, tipo_leilao, fonte_energia, tipo_geracao, uf, vencedor, potencia_mw,
                garantia_fisica_mwmed, energia_vendida_mwmed, preco_leilao_brl_mwh, preco_teto_brl_mwh, desagio_pct,
                investimento_previsto_brl, strftime(data_leilao, '%Y-%m-%d') AS data_leilao, numero_leilao,
                empreendimento, ceg FROM leiloes_geracao ORDER BY data_leilao, empreendimento""",
         tempo=d("ano", "Ano"), granularidade="ano",
         dimensoes=[d("fonte_energia", "Fonte"), d("tipo_leilao", "Tipo de leilão"), d("tipo_geracao", "Tipo"),
                    d("uf", "UF"), d("vencedor", "Vencedor")],
         medidas=[m("potencia_mw", "Potência", "mw"), m("energia_vendida_mwmed", "Energia vendida", "mwmed"),
                  m("garantia_fisica_mwmed", "Garantia física", "mwmed"),
                  m("preco_leilao_brl_mwh", "Preço de venda (médio ponderado pela energia)", "brl_mwh", "ponderada",
                    peso="energia_vendida_mwmed"),
                  m("preco_teto_brl_mwh", "Preço-teto (médio ponderado pela energia)", "brl_mwh", "ponderada",
                    peso="energia_vendida_mwmed"),
                  m("desagio_pct", "Deságio (médio ponderado pela energia)", "pct", "ponderada",
                    peso="energia_vendida_mwmed"),
                  m("investimento_previsto_brl", "Investimento previsto", "brl")],
         extras=[d("data_leilao", "Data"), d("numero_leilao", "Leilão"), d("empreendimento", "Empreendimento"),
                 d("ceg", "CEG")],
         padrao=dict(medida="potencia_mw", serie="fonte_energia")),
    dict(id="pdd", tabela="pdd_investimentos", grupo="Distribuição", titulo="Investimento das distribuidoras (PDD)",
         sql="""SELECT distribuidora, uf, regiao, ano::VARCHAR AS ano, tipo_obra, classe_obra, planejado_brl,
                realizado_brl, cnpj FROM pdd_investimentos ORDER BY distribuidora, ano""",
         tempo=d("ano", "Ano"), granularidade="ano",
         dimensoes=[d("distribuidora", "Distribuidora", papel="empresa"), d("uf", "UF"), d("regiao", "Região"),
                    d("tipo_obra", "Tipo de obra"), d("classe_obra", "Classe de obra")],
         medidas=[m("realizado_brl", "Realizado", "brl"), m("planejado_brl", "Planejado", "brl"),
                  razao("execucao_pct", "Execução (realizado / planejado)", "pct", "realizado_brl", "planejado_brl",
                        100)],
         extras=[d("cnpj", "CNPJ")],
         padrao=dict(medida="realizado_brl", serie="regiao")),
    dict(id="bndes", tabela="bndes_operacoes", grupo="Financiamento", titulo="Financiamentos do BNDES ao setor elétrico",
         sql="""SELECT year(data_contratacao)::VARCHAR AS ano, cliente, uf, subsetor_bndes, produto, porte, situacao,
                valor_contratado_brl, valor_desembolsado_brl, juros_pct_aa, custo_financeiro, projeto, cnpj,
                strftime(data_contratacao, '%Y-%m-%d') AS data_contratacao
                FROM bndes_operacoes WHERE setor_eletrico ORDER BY data_contratacao""",
         tempo=d("ano", "Ano"), granularidade="ano",
         dimensoes=[d("subsetor_bndes", "Subsetor"), d("uf", "UF"), d("produto", "Produto"), d("porte", "Porte"),
                    d("situacao", "Situação"), d("cliente", "Cliente", papel="dono")],
         medidas=[m("valor_contratado_brl", "Valor contratado", "brl"),
                  m("valor_desembolsado_brl", "Valor desembolsado", "brl"),
                  m("juros_pct_aa", "Juros (% a.a., ponderado pelo valor contratado)", "pct", "ponderada",
                    peso="valor_contratado_brl")],
         extras=[d("custo_financeiro", "Custo financeiro"), d("projeto", "Projeto"), d("cnpj", "CNPJ"),
                 d("data_contratacao", "Data de contratação")],
         padrao=dict(medida="valor_contratado_brl", serie="subsetor_bndes")),
    dict(id="debentures", tabela="debentures_incentivadas", grupo="Financiamento", titulo="Debêntures incentivadas",
         sql="""SELECT year(data_emissao)::VARCHAR AS ano, setor, emissora, indexador, artigo, valor_brl,
                taxa_ou_spread_pct, codigo_cetip, strftime(data_emissao, '%Y-%m-%d') AS data_emissao,
                strftime(data_vencimento, '%Y-%m-%d') AS data_vencimento
                FROM debentures_incentivadas ORDER BY data_emissao""",
         tempo=d("ano", "Ano"), granularidade="ano",
         dimensoes=[d("setor", "Setor"), d("indexador", "Indexador"), d("artigo", "Artigo"),
                    d("emissora", "Emissora")],
         medidas=[m("valor_brl", "Valor emitido", "brl"),
                  m("taxa_ou_spread_pct", "Taxa ou spread (% ponderado pelo valor)", "pct", "ponderada",
                    peso="valor_brl")],
         extras=[d("codigo_cetip", "Código CETIP"), d("data_emissao", "Emissão"),
                 d("data_vencimento", "Vencimento")],
         padrao=dict(medida="valor_brl", serie="indexador", filtros={"setor": ["Energia Elétrica"]})),
]


def valor(x):
    if isinstance(x, float) and not math.isfinite(x):
        return None
    if isinstance(x, (datetime.date, datetime.datetime)):
        return x.isoformat()
    return x


def busca_por_dimensao(c, colunas, linhas, termos_cnpj):
    """{dimensão: {valor: 'cnpj apelidos nome comercial'}} para as dimensões com exatamente um CNPJ por valor."""
    if "cnpj" not in colunas:
        return {}
    i_cnpj = colunas.index("cnpj")
    busca = {}
    for dim in c["dimensoes"]:
        i = colunas.index(dim["coluna"])
        cnpjs = {}
        for linha in linhas:
            if linha[i] is not None and linha[i_cnpj]:
                cnpjs.setdefault(linha[i], set()).add(linha[i_cnpj])
        if len(cnpjs) > 1 and all(len(v) == 1 for v in cnpjs.values()):
            busca[dim["coluna"]] = {k: " ".join([cnpj, *termos_cnpj.get(cnpj, [])]) for k, (cnpj,) in cnpjs.items()}
    return busca


def papel_dimensao(c, colunas, papel):
    """Coluna da dimensão marcada com este papel em d(). Exige cnpj na consulta: sem CNPJ não há a quem ligar."""
    marcadas = [x["coluna"] for x in c["dimensoes"] if x.get("papel") == papel]
    assert len(marcadas) <= 1, f"{c['id']}: {len(marcadas)} dimensões com papel {papel}, o grafo espera no máximo uma"
    if not marcadas:
        return None
    assert "cnpj" in colunas, f"{c['id']}: dimensão {marcadas[0]} tem papel {papel} mas a consulta não traz cnpj"
    return marcadas[0]


con = duckdb.connect(BANCO, read_only=True)
existentes = {t for (t,) in con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'")
              .fetchall()}
catalogo = {t: (desc, fonte, ressalvas) for t, desc, fonte, ressalvas in
            con.execute("SELECT tabela, descricao, fonte, ressalvas FROM catalogo").fetchall()}
termos_cnpj = {}
if {"empresas", "empresas_apelidos"} <= existentes:
    for cnpj, termo in con.execute("""SELECT cnpj, apelido FROM empresas_apelidos
                                      UNION SELECT cnpj, nome_comercial FROM empresas WHERE nome_comercial IS NOT NULL
                                      ORDER BY 1, 2""").fetchall():
        termos_cnpj.setdefault(cnpj, []).append(termo)
conjuntos = []
for c in CONJUNTOS:
    if c["tabela"] not in existentes:
        print(f"{c['id']}: tabela {c['tabela']} ausente, pulado")
        continue
    cursor = con.execute(c.pop("sql"))
    colunas = [x[0] for x in cursor.description]
    linhas = [[valor(x) for x in linha] for linha in cursor.fetchall()]
    declaradas = [x["coluna"] for x in [c.get("tempo") or {}] + c["dimensoes"] + c["extras"] if x] + \
        [x["coluna"] for x in c["medidas"] if x["agregacao"] != "razao" or x["coluna"] in colunas]
    faltando = set(declaradas) - set(colunas)
    assert not faltando, f"{c['id']}: colunas declaradas que a consulta não traz: {faltando}"
    descricao, fonte, ressalvas = catalogo.get(c["tabela"], ("", "", ""))
    conjuntos.append({**c, "descricao": descricao, "fonte": fonte, "ressalvas": ressalvas or "",
                      "busca": busca_por_dimensao(c, colunas, linhas, termos_cnpj),
                      "dimensao_empresa": papel_dimensao(c, colunas, "empresa"),
                      "dimensao_dono": papel_dimensao(c, colunas, "dono"),
                      "colunas": colunas, "linhas": linhas})
    print(f"{c['id']}: {len(linhas)} linhas")
con.close()

painel = {"gerado_em": datetime.datetime.now().isoformat(timespec="seconds"),
          "banco": os.path.basename(BANCO), "conjuntos": conjuntos}
tmp = DESTINO + ".tmp"
with open(tmp, "w") as saida:
    json.dump(painel, saida, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
os.replace(tmp, DESTINO)
print(f"{DESTINO}: {len(conjuntos)} conjuntos, {os.path.getsize(DESTINO) / 1e6:.1f} MB")

"""Testes das ferramentas de energynexus-dados contra o banco real (valores conferidos nas DFP da CVM).

Rodar: .runtime/venv/bin/python -m pytest proper_mcps -q
"""
import pytest

import server as s


def primeiro(termo):
    return s.buscar_empresa(termo)["resultados"][0]


@pytest.mark.parametrize("termo, cnpj", [
    ("Taesa", "07.859.971/0001-30"),
    ("TAEE11", "07.859.971/0001-30"),
    ("Eletrobras", "00.001.180/0001-26"),
    ("Enel SP", "61.695.227/0001-93"),
    ("Cemig", "17.155.730/0001-64"),
    ("equatorial", "03.220.438/0001-73"),
    ("ISA CTEEP", "02.998.611/0001-04"),
    ("17.155.730/0001-64", "17.155.730/0001-64"),
])
def test_buscar_empresa_acha_a_holding_certa(termo, cnpj):
    r = primeiro(termo)
    assert r["cnpj"] == cnpj
    assert r["confianca"] == "exata"


def test_nome_inexistente_vem_marcado_como_aproximado():
    r = s.buscar_empresa("Empresa Que Nao Existe Energia")
    assert r["resultados"][0]["confianca"] == "aproximada"
    assert "aviso" in r


@pytest.mark.parametrize("termo, cnpj", [
    ("Neoenergia Coelba", "15.139.629/0001-94"),   # marca do grupo + distribuidora: vem a distribuidora, não a holding
    ("Light Rio", None),
])
def test_termo_com_apelido_dentro(termo, cnpj):
    r = s.buscar_empresa(termo)
    assert r["resultados"][0]["confianca"] in ("exata", "nome")
    if cnpj:
        assert r["resultados"][0]["cnpj"] == cnpj


def test_indicadores_equatorial_2024_batem_com_a_dfp():
    anos = s.indicadores_financeiros("Equatorial", 2024, 2024)["anos"]
    k = anos[0]
    assert k["receita_liquida_brl"] == pytest.approx(45_366_675_000)
    assert k["ebit_brl"] == pytest.approx(8_636_463_000)
    assert k["lucro_liquido_brl"] == pytest.approx(3_767_805_000)
    assert k["divida_bruta_brl"] == pytest.approx(55_827_078_000)
    assert k["ebitda_brl"] > k["ebit_brl"]


def test_consultar_sql_recusa_numeros_digitados():
    assert "erro" in s.consultar_sql("SELECT 2024 AS ano, 890363.0 AS vl_conta FROM (SELECT 1) t")
    assert "erro" in s.consultar_sql("SELECT * FROM (VALUES (1, 890363)) t(a, b)")
    assert "erro" in s.consultar_sql("SELECT 5000000 AS x FROM empresas")
    assert "erro" in s.consultar_sql("DELETE FROM empresas")


def test_consultar_sql_aceita_consulta_normal():
    r = s.consultar_sql("SELECT count(*) AS n FROM leiloes_geracao WHERE potencia_mw > 100")
    assert r["tabelas_usadas"] == ["leiloes_geracao"]
    assert r["linhas"][0]["n"] > 0


@pytest.mark.parametrize("tabela, minimo", [
    ("leiloes_geracao", 1000), ("usinas", 20000), ("usinas_proprietarios", 20000), ("bndes_operacoes", 20000),
    ("debentures_incentivadas", 500), ("transmissao_empreendimentos", 10000), ("pee_projetos", 5000),
    ("kpis_financeiros", 500), ("tarifas_distribuicao", 100000),
])
def test_tabelas_carregadas(tabela, minimo):
    assert s.consultar_sql(f"SELECT count(*) AS n FROM {tabela}")["linhas"][0]["n"] >= minimo


def test_potencia_do_siga_em_numero():
    r = s.consultar_sql("""SELECT round(sum(potencia_fiscalizada_kw) / 1e6, 1) AS gw FROM usinas WHERE fase = 'Operação'""")
    assert 150 < r["linhas"][0]["gw"] < 400  # capacidade instalada do Brasil em GW


def test_dec_fec_da_distribuidora():
    r = s.consultar_sql("""SELECT meses, dec_horas, fec_interrupcoes, dec_limite_medio_ponderado_horas FROM dec_fec_distribuidora_anual
                           WHERE cnpj = '61.695.227/0001-93' AND ano = 2025""")
    linha = r["linhas"][0]
    assert linha["meses"] == 12
    assert 2 < linha["dec_horas"] < 30 and 1 < linha["fec_interrupcoes"] < 20
    assert linha["dec_limite_medio_ponderado_horas"] > 0


def test_codigos_de_compensacao_tem_descricao():
    r = s.consultar_sql("SELECT descricao FROM indicadores_codigos WHERE indicador = 'PGUCBTNU'")
    assert "Valor pago" in r["linhas"][0]["descricao"]


def test_trimestres_recentes_da_taesa():
    r = s.indicadores_financeiros("Taesa")
    tri = r["trimestres_recentes"]
    assert tri[0]["ano"] >= 2026 and tri[0]["trimestre"] >= 1
    assert 3e9 < tri[0]["receita_liquida_12m_brl"] < 6e9
    assert tri[0]["divida_liquida_ebitda_12m"] > 0


def test_cmo_ons_agosto_2026_confere_com_parquet_oficial():
    # ONS CMO_SEMIHORARIO_2026.parquet: N, 01/08/2026 00:00, 176,98 R$/MWh.
    r = s.consultar_sql("""SELECT cmo_brl_mwh FROM ons_cmo_semihora
                         WHERE subsistema = 'N' AND instante = '2026-08-01 00:00:00'""")
    assert r["linhas"][0]["cmo_brl_mwh"] == pytest.approx(176.98)
    mensal = s.consultar_sql("""SELECT cmo_medio_brl_mwh, intervalos, dias_ausentes FROM ons_cmo_mensal
                              WHERE subsistema = 'N' AND mes = '2026-08-01'""")["linhas"][0]
    assert mensal == {"cmo_medio_brl_mwh": pytest.approx(151.51), "intervalos": 1440,
                      "dias_ausentes": 1}


def test_ear_ons_agosto_2026_confere_com_parquet_oficial():
    # ONS EAR_DIARIO_SUBSISTEMA_2026.parquet: SE, 01/08/2026.
    r = s.consultar_sql("""SELECT ear_maxima_mwmes, ear_verificada_mwmes, ear_verificada_pct
                         FROM ons_ear_diario WHERE subsistema = 'SE' AND data = '2026-08-01'""")
    assert r["linhas"][0] == {
        "ear_maxima_mwmes": pytest.approx(204615.328),
        "ear_verificada_mwmes": pytest.approx(128704.956),
        "ear_verificada_pct": pytest.approx(62.9009),
    }


# ---------------------------------------------------------------- bases acrescentadas em 25/09/2026 (valores dos arquivos oficiais)
def um(sql):
    r = s.consultar_sql(sql)
    assert "erro" not in r, r
    return r["linhas"][0]


def test_rap_modulo_confere_com_siget():
    # siget-lista-modulos-previa-reajuste-rap.csv: módulo 1, BC 69 kV RIO LARGO II BC1, VlrRAPCiclo 111004,76
    linha = um("""SELECT concessionaria, cnpj, tipo_receita, rap_ciclo_brl FROM rap_transmissao_modulos
                  WHERE id_modulo = 1 AND modulo LIKE 'BC 69 kV 21,3 Mvar RIO LARGO II%'""")
    assert linha == {"concessionaria": "AXIA Nordeste", "cnpj": "33.541.368/0001-16", "tipo_receita": "RPC",
                     "rap_ciclo_brl": pytest.approx(111004.76)}
    taesa = um("""SELECT sum(rap_ciclo_brl) AS rap FROM rap_transmissao_concessionaria
                  WHERE cnpj = '07.859.971/0001-30' AND situacao = 'Ativa'""")
    assert 1.5e9 < taesa["rap"] < 3.5e9


def test_composicao_societaria_etau_e_grupo_taesa():
    # Polímero/ANEEL, 2T26: ETAU tem Taesa 75,62% (controladora), DME 14,38% e CPFL Transmissão 10%
    linha = um("""SELECT participacao_indireta_pct, na_cadeia_de_controle FROM participacoes_societarias
                  WHERE cnpj_agente = '05.063.249/0001-60' AND cnpj_participante = '07.859.971/0001-30'""")
    assert linha == {"participacao_indireta_pct": pytest.approx(75.62), "na_cadeia_de_controle": True}
    assert um("SELECT holding_cvm FROM grupos_economicos WHERE cnpj = '05.063.249/0001-60'")["holding_cvm"].startswith("TRANSMISSORA ALIAN")
    assert "NEOENERGIA" in um("SELECT upper(holding_cvm) AS h FROM grupos_economicos WHERE cnpj = '15.139.629/0001-94'")["h"]


def test_capacidade_por_grupo_engie():
    r = um("""SELECT sum(potencia_proporcional_mw) AS mw FROM capacidade_por_grupo
              WHERE chave_participante = '02.474.103/0001-19' AND fase = 'Operação'""")
    assert 7000 < r["mw"] < 14000


def test_mercado_distribuidora_confere_com_samp():
    # samp-2025.parquet: Eletropaulo, Residencial, CATIVO, 03/2025, Energia TUSD = 1.669.861.789 kWh
    r = um("""SELECT sum(energia_tusd_mwh) AS mwh FROM mercado_distribuidoras_mensal
              WHERE cnpj = '61.695.227/0001-93' AND classe = 'Residencial' AND mercado = 'CATIVO' AND mes = '2025-03-01'""")
    assert r["mwh"] == pytest.approx(1669861.789)


def test_mmgd_acre_confere_com_aneel():
    r = um("SELECT sum(empreendimentos) AS n, sum(potencia_mw) AS mw FROM gd_mmgd WHERE uf = 'AC'")
    assert r["n"] > 15000 and 150 < r["mw"] < 400
    assert 40_000 < um("SELECT sum(potencia_mw) AS mw FROM gd_mmgd")["mw"] < 80_000


def test_bandeira_e_macro_conferem_com_fonte():
    assert um("SELECT bandeira, adicional_brl_mwh FROM bandeiras_tarifarias WHERE mes = '2015-01-01'") == {
        "bandeira": "Vermelha P1", "adicional_brl_mwh": pytest.approx(30.0)}
    # SGS 433 (IPCA ago/2026 = -0,32%) e 13522 (IPCA 12 meses dez/2025 = 4,26%)
    assert um("SELECT ipca_mes_pct FROM indicadores_macro_mensal WHERE mes = '2026-08-01'")["ipca_mes_pct"] == pytest.approx(-0.32)
    assert um("SELECT ipca_12m_pct FROM indicadores_macro_mensal WHERE mes = '2025-12-01'")["ipca_12m_pct"] == pytest.approx(4.26)


def test_ranking_continuidade_2025():
    # gov.br/aneel, ranking de continuidade 2025, tabela I: 1º CPFL Santa Cruz, DGC 0,54
    linha = um("""SELECT sigla, dgc FROM ranking_continuidade
                  WHERE ano = 2025 AND porte LIKE 'mais%' AND posicao = 1""")
    assert linha == {"sigla": "CPFL SANTA CRUZ", "dgc": pytest.approx(0.54)}
    assert um("SELECT cnpj FROM ranking_continuidade WHERE ano = 2025 AND sigla = 'ENEL SP'")["cnpj"] == "61.695.227/0001-93"


def test_series_ons_conferem_com_parquet():
    # CARGA_ENERGIA_2026: N, 01/01/2026, 7.649,438875 MWmed; ENA_DIARIO_SUBSISTEMA_2026: NE, 01/01/2026
    assert um("SELECT carga_mwmed FROM ons_carga_diaria WHERE subsistema = 'N' AND data = '2026-01-01'")["carga_mwmed"] == \
        pytest.approx(7649.438875)
    assert um("SELECT ena_bruta_mwmed, ena_bruta_pct_mlt FROM ons_ena_diaria WHERE subsistema = 'NE' AND data = '2026-01-01'") == {
        "ena_bruta_mwmed": pytest.approx(6255.788), "ena_bruta_pct_mlt": pytest.approx(46.6367)}
    # BALANCO_ENERGIA_SUBSISTEMA_2025: eólica do NE em ago/2025 = 10.712.279,1 MWh; GERACAO_USINA-2_2026_07: Itaipu 60 Hz
    assert um("SELECT eolica_mwh FROM ons_geracao_fonte_mensal WHERE subsistema = 'NE' AND mes = '2025-08-01'")["eolica_mwh"] == \
        pytest.approx(10712279.1)
    assert um("SELECT geracao_mwh FROM ons_geracao_usina_mensal WHERE usina = 'ITAIPU 60 HZ' AND mes = '2026-07-01'")["geracao_mwh"] == \
        pytest.approx(3702587.962)


def test_debenture_snd_taesa():
    # SND, TAEE17: Taesa, vencimento 15/09/2044, IPCA + 4,5%, incentivada
    linha = um("""SELECT cnpj, data_vencimento, indice, taxa_juros_pct_aa, incentivada_lei_12431, setor_eletrico
                  FROM debentures_snd WHERE codigo = 'TAEE17'""")
    assert linha == {"cnpj": "07.859.971/0001-30", "data_vencimento": "2044-09-15", "indice": "IPCA",
                     "taxa_juros_pct_aa": pytest.approx(4.5), "incentivada_lei_12431": True, "setor_eletrico": True}


def test_expansao_geracao_ralie():
    linha = um("SELECT uf, tipo_geracao, potencia_outorgada_mw FROM expansao_geracao WHERE ceg = 'UHE.PH.RS.000324-7.1'")
    assert linha == {"uf": "RS", "tipo_geracao": "UHE", "potencia_outorgada_mw": pytest.approx(17.62)}


# ---------------------------------------------------------------- correções da auditoria de 26/09/2026
@pytest.mark.parametrize("valor, esperado", [
    (2.0990909e-06, 2.09909e-06),       # razão pequena: round(v, 4) devolvia 0.0
    (0.00012345678, 0.000123457),
    (62.900912, 62.9009),
    (111004.76, 111004.76),             # centavos de um valor grande não se perdem
    (4624113000.0, 4624113000.0),
    (0.0, 0.0),
])
def test_arredondamento_acompanha_a_grandeza(valor, esperado):
    assert s._arredondar(valor) == pytest.approx(esperado)


def test_razao_pequena_nao_vira_zero():
    linha = um("""SELECT capex_brl / ativo_total_brl AS capex_sobre_ativo FROM kpis_financeiros
                  WHERE capex_brl > 0 ORDER BY 1 LIMIT 1""")
    assert 0 < linha["capex_sobre_ativo"] < 1e-5


@pytest.mark.parametrize("sql", [
    "-- receita da Taesa\nSELECT ano FROM kpis_financeiros LIMIT 1",
    "/* nota */ SELECT ano FROM kpis_financeiros LIMIT 1",
    "SELECT count(*) AS n FROM catalogo WHERE descricao LIKE '%;%'",
    "(SELECT ano FROM kpis_financeiros LIMIT 1)",
])
def test_consultar_sql_aceita_comentario_e_ponto_e_virgula_em_literal(sql):
    assert "erro" not in s.consultar_sql(sql)


@pytest.mark.parametrize("sql", [
    "SELECT 1 FROM catalogo; SELECT 2 FROM catalogo",
    "CREATE TABLE x AS SELECT * FROM catalogo",
    "-- disfarce\nCREATE TABLE x AS SELECT * FROM catalogo",
])
def test_consultar_sql_recusa_mais_de_uma_consulta_ou_escrita(sql):
    assert "erro" in s.consultar_sql(sql)


def test_trimestres_dizem_quantos_faltam_e_aceitam_pedido_maior():
    r = s.indicadores_financeiros("Taesa")
    assert len(r["trimestres_recentes"]) == 4
    assert r["trimestres_na_base"] > 4
    assert str(r["trimestres_na_base"]) in r["aviso_trimestres"]
    inteiro = s.indicadores_financeiros("Taesa", trimestres=r["trimestres_na_base"])
    assert len(inteiro["trimestres_recentes"]) == r["trimestres_na_base"]
    assert "aviso_trimestres" not in inteiro


def test_listar_tabelas_resume_e_diz_onde_ver_o_resto():
    r = s.listar_tabelas()
    assert r["tabelas"] == len(r["catalogo"]) > 50
    assert set(r["catalogo"][0]) == {"tabela", "linhas", "resumo"}
    assert "descrever_tabela" in r["como_usar"] and "detalhe=True" in r["como_usar"]
    detalhe = s.listar_tabelas(detalhe=True)
    assert set(detalhe["catalogo"][0]) == {"tabela", "descricao", "fonte", "ressalvas", "linhas"}


def test_sigla_da_aneel_acha_a_concessao_e_nao_a_holding():
    # "Light SESA" só existe como sigla no cadastro da ANEEL; antes vinha a holding Light S.A.
    r = s.buscar_empresa("Light SESA")
    assert r["resultados"][0]["cnpj"] == "60.444.437/0001-46"
    assert r["resultados"][0]["confianca"] == "exata"


def test_holding_encontrada_por_aproximacao_lista_as_empresas_do_grupo():
    r = s.buscar_empresa("Grupo Light")
    assert r["resultados"][0]["cnpj"] == "03.378.521/0001-75"
    assert "60.444.437/0001-46" in r["aviso_holding"]


@pytest.mark.parametrize("termo, cnpj", [
    ("Energisa Tocantins", "25.086.034/0001-71"),   # 3 agentes com esse nome: a distribuidora vem antes das 2 transmissoras
    ("Energisa Acre", "04.065.033/0001-70"),
    ("Energisa Borborema", "08.826.596/0001-95"),
])
def test_concessao_fora_da_cvm_nao_devolve_o_cnpj_da_holding(termo, cnpj):
    # sem apelido de mercado e sem registro na CVM, estas caíam no passo do apelido e voltavam como ENERGISA SA
    r = s.buscar_empresa(termo)
    primeiro_ = r["resultados"][0]
    assert primeiro_["cnpj"] == cnpj
    assert primeiro_["confianca"] == "nome"
    assert primeiro_["anos_com_demonstracoes"] == "não" and "não tem demonstrações" in primeiro_["como_encontrou"]
    # o CNPJ devolvido tem de voltar sozinho: era ele que caía no passo do nome parecido e virava outra empresa
    de_volta = s.buscar_empresa(cnpj)["resultados"][0]
    assert de_volta["cnpj"] == cnpj and de_volta["confianca"] == "exata"
    assert s.indicadores_financeiros(cnpj)["anos"] == "sem demonstrações na base para esses anos"


def test_palavra_do_nome_e_inteira_e_nao_pedaco():
    # '%rge %' casava FOTONS DE SAO GEORGE e '%light%' casava LIGHTSOURCE: 'Light Rio' tem de voltar ao grupo Light
    r = s.buscar_empresa("Light Rio")
    assert r["resultados"][0]["cnpj"] == "03.378.521/0001-75"
    assert "60.444.437/0001-46" in r["aviso_holding"]


# ---------------------------------------------------------------- coerência das contas da CVM
def test_custo_positivo_e_bruto_acima_da_receita_sao_apontados():
    # Equatorial Pará 2025: a empresa enviou 3.02 positiva, então 3.03 = 3.01 + 3.02 FECHA e a soma não pega o erro
    contas = {"3.01": 12_223_744_000.0, "3.02": 8_846_555_000.0, "3.03": 21_070_299_000.0,
              "3.04": -1_042_090_000.0, "3.05": 20_028_209_000.0}
    assert abs(contas["3.03"] - (contas["3.01"] + contas["3.02"])) < 1  # a identidade de soma fecha
    problemas = s._incoerencias_dre(contas)
    assert any("3.02" in p and "positiva" in p for p in problemas)
    assert any("passa a receita" in p for p in problemas)
    assert any("2335099000" in p for p in problemas)  # EBIT com o sinal certo, 19% de margem


def test_soma_que_nao_fecha_e_apontada():
    # CESP 2022 consolidado: a empresa não enviou 3.02 nem 3.04
    problemas = s._incoerencias_dre({"3.01": 2_255_353_000.0, "3.02": 0.0, "3.03": 756_723_000.0,
                                     "3.04": 0.0, "3.05": 972_475_000.0})
    assert any("3.03" in p and "não fecha" in p for p in problemas)
    assert any("3.05" in p and "não fecha" in p for p in problemas)


@pytest.mark.parametrize("contas", [
    {"3.01": 100.0, "3.02": -60.0, "3.03": 40.0, "3.04": -10.0, "3.05": 30.0},              # DRE normal
    {"3.01": 2_981_000.0, "3.02": 0.0, "3.03": 2_981_000.0, "3.04": 2_226_579_000.0,
     "3.05": 2_229_560_000.0},                                                              # holding: EBIT >> receita
    {"3.01": None, "3.02": None, "3.03": None, "3.04": None, "3.05": None},                 # período sem DRE
])
def test_dre_coerente_nao_gera_ressalva(contas):
    assert s._incoerencias_dre(contas) == []


def test_indicadores_da_equatorial_para_trazem_a_ressalva_de_2025():
    r = s.indicadores_financeiros("Equatorial Pará")
    assert any(a["ano"] == 2025 and a["margem_ebit_pct"] > 100 for a in r["anos"])
    assert any("2025" in x and "3.02" in x for x in r["ressalvas_cvm"])


def test_a_checagem_pega_todo_periodo_suspeito_da_base():
    # toda a base: nenhum período com custo positivo ou bruto acima da receita escapa da checagem
    r = s.consultar_sql("""WITH d AS (SELECT cnpj, ano, escopo,
            max(valor_brl) FILTER (cd_conta = '3.01') AS c301, max(valor_brl) FILTER (cd_conta = '3.02') AS c302,
            max(valor_brl) FILTER (cd_conta = '3.03') AS c303, max(valor_brl) FILTER (cd_conta = '3.04') AS c304,
            max(valor_brl) FILTER (cd_conta = '3.05') AS c305 FROM contas_cvm GROUP BY ALL)
        SELECT * FROM d WHERE c302 > 0 OR c303 > c301""")
    assert r["linhas"], "a base deveria ter o caso conhecido da Equatorial Pará 2025"
    for linha in r["linhas"]:
        contas = {c: linha["c" + c.replace(".", "")] for c in s.CONTAS_DRE}
        assert s._incoerencias_dre(contas), linha

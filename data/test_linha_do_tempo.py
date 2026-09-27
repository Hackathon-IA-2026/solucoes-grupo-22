"""Testes de data/linha_do_tempo.py contra os bancos de data/ (os valores são conferidos no próprio banco).

Rodar: .runtime/venv/bin/python -m pytest data -q
"""
import re

import duckdb
import pytest

import linha_do_tempo as lt

# Cemig, Engie, Taesa e Axia (a única empresa com relatórios no índice: é ela que exercita a busca nos relatórios)
EMPRESAS = ["17.155.730/0001-64", "02.474.103/0001-19", "07.859.971/0001-30", "00.001.180/0001-26"]
COM_RELATORIOS = "00.001.180/0001-26"
CAUSA = re.compile(r"\b(causou|causad|graças a|devido a|por causa|resultou em|levou a|provocou)\b", re.I)


@pytest.fixture(scope="module")
def base():
    con = duckdb.connect(lt.BANCO, read_only=True)
    docs = duckdb.connect(lt.DOCS, read_only=True)
    docs.execute("LOAD fts")
    selecao = lt.selecao(con, docs)
    periodos = {e["id"]: e["periodo"] for e in selecao["empresas"]}
    linhas = {}
    for cnpj in EMPRESAS:
        empresa = lt.empresa_de(con, cnpj)
        de, ate = periodos[lt.digitos(cnpj)]  # o período sugerido do seletor, o que a tela abre
        linhas[cnpj] = lt.linha_do_tempo(con, docs, empresa, de, ate)
    yield con, docs, selecao, linhas
    con.close()
    docs.close()


def eventos(t):
    return [e for a in t["anos"] for e in a["eventos"]]


def test_selecao_lista_a_base_com_periodo_dentro_dos_limites(base):
    selecao = base[2]
    primeiro, ultimo = selecao["limites"]
    assert primeiro < ultimo
    ids = {e["id"] for e in selecao["empresas"]}
    assert {lt.digitos(c) for c in EMPRESAS} <= ids
    for e in selecao["empresas"]:
        assert primeiro <= e["periodo"][0] <= e["periodo"][1] <= ultimo
        assert e["relatorios"] >= 0 and e["usinas"] >= 0
        assert e["dfp"] is None or primeiro <= e["dfp"][0] <= e["dfp"][1] <= ultimo
    com_relatorios = next(e for e in selecao["empresas"] if e["id"] == lt.digitos(COM_RELATORIOS))
    assert com_relatorios["relatorios"] > 0 and com_relatorios["periodo"][0] < com_relatorios["periodo"][1]


def test_temas_vetorizados_no_indice(base):
    docs = base[1]
    linhas = docs.execute("SELECT tema, consulta, embedding FROM temas").fetchall()
    assert {t for t, _, _ in linhas} == set(lt.TEMAS)
    for tema, consulta, vetor in linhas:
        assert consulta == lt.TEMAS[tema][1]  # o vetor é o da consulta do tema, não de outra coisa
        assert len(vetor) == 1024 and abs(sum(v * v for v in vetor) - 1) < 1e-3  # normalizado, como na busca


def test_paginas_candidatas_existem_e_respeitam_o_teto(base):
    docs = base[1]
    arquivos = [r[0] for r in docs.execute(
        "SELECT arquivo FROM documentos ORDER BY ano DESC LIMIT 3").fetchall()]
    candidatas = lt.paginas_por_tema(docs, arquivos)
    assert candidatas, "os relatórios do índice têm de render candidatas nos temas"
    assert {a for a, _ in candidatas} <= set(arquivos)
    for (arquivo, tema), paginas in candidatas.items():
        assert tema in lt.TEMAS
        # união das duas buscas: no máximo POR_RELATORIO de cada uma
        assert 0 < len(paginas) <= 2 * lt.POR_RELATORIO and len(set(paginas)) == len(paginas)
        for pagina in paginas:
            assert docs.execute("SELECT count(*) FROM blocos WHERE arquivo = ? AND pagina = ?",
                                [arquivo, pagina]).fetchone()[0]


@pytest.mark.parametrize("cnpj", EMPRESAS)
def test_todo_evento_tem_fonte_e_ano_no_periodo(base, cnpj):
    t = base[3][cnpj]
    assert t["anos"], "a empresa tem dados na base: a linha do tempo não pode vir vazia"
    for a in t["anos"]:
        assert t["periodo"][0] <= a["ano"] <= t["periodo"][1]
        for e in a["eventos"]:
            assert e["fonte"]["texto"] and e["descricao"] and e["tipo"] in lt.ORDEM_TIPOS
            assert set(e["temas"]) <= set(lt.TEMAS)


def test_frase_do_relatorio_esta_na_pagina_citada(base):
    _, docs, _, linhas = base
    t = linhas[COM_RELATORIOS]
    relatorios = [(a["ano"], e) for a in t["anos"] for e in a["eventos"] if e["tipo"] == "relatorio"]
    assert relatorios, "a empresa com relatórios indexados tem de render eventos de relatório"
    for ano, e in relatorios:
        f = e["fonte"]
        doc = docs.execute("SELECT cnpj, ano FROM documentos WHERE arquivo = ?", [f["arquivo"]]).fetchone()
        assert lt.digitos(doc[0]) == lt.digitos(COM_RELATORIOS)
        # o ano do evento é o da publicação do relatório, e o relatório é do período pedido
        assert doc[1] == ano and t["periodo"][0] <= doc[1] <= t["periodo"][1]
        blocos = [lt.limpo(r[0]) for r in docs.execute(
            "SELECT texto FROM blocos WHERE arquivo = ? AND pagina = ?", [f["arquivo"], f["pagina"]]).fetchall()]
        assert any(e["descricao"].rstrip("…") in b for b in blocos)


def test_graficos_batem_com_kpis_financeiros(base):
    con, _, _, linhas = base
    cnpj = "02.474.103/0001-19"
    banco = dict(con.execute("SELECT ano, receita_liquida_brl FROM kpis_financeiros WHERE cnpj = ?", [cnpj]).fetchall())
    serie = next(l for g in linhas[cnpj]["graficos"] for l in g["linhas"] if l["id"] == "receita_liquida_brl")
    assert serie["pontos"] and all(p["valor"] == banco[p["ano"]] for p in serie["pontos"])
    assert all(p["fonte"].startswith(f"CVM DFP {p['ano']}") for p in serie["pontos"])


def test_capacidade_acumulada_nunca_cai_e_soma_as_usinas_do_ano(base):
    t = base[3]["02.474.103/0001-19"]
    serie = next(l for g in t["graficos"] for l in g["linhas"] if l["id"] == "capacidade_renovavel_mw")
    valores = [p["valor"] for p in serie["pontos"]]
    assert valores == sorted(valores)
    for a in t["anos"]:
        usinas = [e for e in a["eventos"] if e["tipo"] == "usina" and "renovavel" in e["temas"]]
        v = next((x for x in a["evolucao"] if x["indicador"] == "Capacidade renovável"), None)
        if usinas and v and v["anterior"] is not None:
            assert v["variacao"] > 0


@pytest.mark.parametrize("cnpj", EMPRESAS)
def test_trajetorias_em_ordem_com_ligacao_e_sem_causa(base, cnpj):
    for t in base[3][cnpj]["trajetorias"]:
        anos = [p["ano"] for p in t["passos"]]
        assert anos == sorted(anos) and len(anos) >= 2
        assert t["passos"][0]["vinculo"] is None and all(p["vinculo"] for p in t["passos"][1:])
        assert "não prova" in t["ressalva"]
        for p in t["passos"]:
            assert p["fonte"]["texto"]
            if p["papel"] != "Estratégia anunciada":  # a frase do relatório é da empresa, não nossa
                assert not CAUSA.search(p["texto"]), p["texto"]


@pytest.mark.parametrize("cnpj", EMPRESAS)
def test_impacto_so_com_variacao(base, cnpj):
    for a in base[3][cnpj]["anos"]:
        variacao = {v["texto"]: v.get("variacao") for v in a["evolucao"]}
        for i in a["impacto"]:
            assert variacao[i["texto"]], i["texto"]

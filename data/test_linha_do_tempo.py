"""Testes de data/linha_do_tempo.py contra os bancos de data/ (os valores são conferidos no próprio banco).

Rodar: .runtime/venv/bin/python -m pytest data -q
"""
import re

import duckdb
import pytest

import linha_do_tempo as lt

EMPRESAS = ["17.155.730/0001-64", "02.474.103/0001-19", "07.859.971/0001-30"]  # Cemig, Engie, Taesa
CAUSA = re.compile(r"\b(causou|causad|graças a|devido a|por causa|resultou em|levou a|provocou)\b", re.I)


@pytest.fixture(scope="module")
def base():
    con = duckdb.connect(lt.BANCO, read_only=True)
    docs = duckdb.connect(lt.DOCS, read_only=True)
    docs.execute("LOAD fts")
    primeiro = con.execute("SELECT min(ano) FROM kpis_financeiros").fetchone()[0] - lt.ANOS_ANTES
    ultimo = lt.datetime.date.today().year
    catalogo = dict(con.execute("SELECT tabela, fonte FROM catalogo").fetchall())
    cur = docs.execute("SELECT arquivo, empresa, cnpj, ano, titulo, url FROM documentos")
    documentos = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]
    achados = lt.trechos_dos_relatorios(docs)
    linhas = {}
    for cnpj in EMPRESAS:
        nome = con.execute("SELECT nome_social FROM empresas WHERE cnpj = ?", [cnpj]).fetchone()[0]
        empresa = {"cnpj": cnpj, "nome": nome, "nome_comercial": None, "apelidos": ""}
        linhas[cnpj] = lt.linha_do_tempo(con, empresa, documentos, achados, catalogo, primeiro, ultimo)
    yield con, docs, linhas
    con.close()
    docs.close()


def eventos(t):
    return [e for a in t["anos"] for e in a["eventos"]]


@pytest.mark.parametrize("cnpj", EMPRESAS)
def test_todo_evento_tem_fonte_e_ano_no_periodo(base, cnpj):
    t = base[2][cnpj]
    assert t["anos"], "a empresa tem DFP na base: a linha do tempo não pode vir vazia"
    for a in t["anos"]:
        assert t["periodo"][0] <= a["ano"] <= t["periodo"][1]
        for e in a["eventos"]:
            assert e["fonte"]["texto"] and e["descricao"] and e["tipo"] in lt.ORDEM_TIPOS
            assert set(e["temas"]) <= set(lt.TEMAS)


@pytest.mark.parametrize("cnpj", EMPRESAS)
def test_frase_do_relatorio_esta_na_pagina_citada(base, cnpj):
    _, docs, linhas = base
    for e in eventos(linhas[cnpj]):
        if e["tipo"] != "relatorio":
            continue
        f = e["fonte"]
        assert docs.execute("SELECT cnpj FROM documentos WHERE arquivo = ?", [f["arquivo"]]).fetchone()[0] == cnpj
        blocos = [lt.limpo(r[0]) for r in docs.execute(
            "SELECT texto FROM blocos WHERE arquivo = ? AND pagina = ?", [f["arquivo"], f["pagina"]]).fetchall()]
        assert any(e["descricao"].rstrip("…") in b for b in blocos)


def test_graficos_batem_com_kpis_financeiros(base):
    con, _, linhas = base
    cnpj = "02.474.103/0001-19"
    banco = dict(con.execute("SELECT ano, receita_liquida_brl FROM kpis_financeiros WHERE cnpj = ?", [cnpj]).fetchall())
    serie = next(l for g in linhas[cnpj]["graficos"] for l in g["linhas"] if l["id"] == "receita_liquida_brl")
    assert serie["pontos"] and all(p["valor"] == banco[p["ano"]] for p in serie["pontos"])
    assert all(p["fonte"].startswith(f"CVM DFP {p['ano']}") for p in serie["pontos"])


def test_capacidade_acumulada_nunca_cai_e_soma_as_usinas_do_ano(base):
    t = base[2]["02.474.103/0001-19"]
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
    for t in base[2][cnpj]["trajetorias"]:
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
    for a in base[2][cnpj]["anos"]:
        variacao = {v["texto"]: v.get("variacao") for v in a["evolucao"]}
        for i in a["impacto"]:
            assert variacao[i["texto"]], i["texto"]

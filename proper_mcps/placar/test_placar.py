"""Testes das ferramentas de coppezip-placar contra a base real (data/placar.duckdb + data/coppezip.duckdb).

Valores conferidos contra o gabarito researches/FINDINGS-claude-sonnet-5.md §3.2 (emissões por escopo, com página).
Rodar: .runtime/venv/bin/python -m pytest proper_mcps -q
"""
import importlib.util
import os

import pytest

# carregado pelo caminho: dados/ e relatorio/ também têm um server.py
_spec = importlib.util.spec_from_file_location("placar_server", os.path.join(os.path.dirname(__file__), "server.py"))
s = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(s)

pytestmark = pytest.mark.skipif(not os.path.exists(s.PLACAR),
                                reason="data/placar.duckdb ainda não foi extraído (rode data/extrair_placar.py)")


def emissao(empresa, escopo):
    r = s.consultar_placar(empresa)["emissoes"]
    return next((e for e in r if e["escopo"] == escopo), None)


@pytest.mark.parametrize("empresa, escopo, esperado", [
    ("Cemig", "1", 42860.81),
    ("Cemig", "2", 376174.25),
    ("Cemig", "3", 5911209.35),
    ("Auren", "1", 12597.6),
    ("Auren", "3", 1607.1),
    ("ISA", "3", 2774.19),
])
def test_emissoes_batem_com_o_gabarito(empresa, escopo, esperado):
    e = emissao(empresa, escopo)
    assert e is not None, f"não extraiu escopo {escopo} de {empresa}"
    assert e["tco2e"] == pytest.approx(esperado, rel=0.02)
    assert e["arquivo"] and e["pagina"], "todo valor precisa de arquivo e página"


def test_metricas_hibridas_e_score_da_isa():
    r = s.consultar_placar("ISA")
    h = next(h for h in r["metricas_hibridas"] if "ISA" in h["empresa"])
    assert h["tco2e_por_milhao_receita"] > 0            # casou com o financeiro da CVM
    assert "kpis_financeiros" in h["fonte_financeiro"]
    isa = next(x for x in r["score_divulgacao"] if x["ano"] == 2024)
    assert isa["score"] >= 80 and set(isa["componentes"]["escopos"]) == {"1", "2", "3"}


def test_ranking_score_ordenado_e_com_nota():
    r = s.placar_ranking("score_divulgacao")
    valores = [x["valor"] for x in r["ranking"]]
    assert valores and valores == sorted(valores, reverse=True)
    assert all(0 <= v <= 100 for v in valores)


def test_exposicao_carbono_tem_formula_e_financeiro():
    r = s.exposicao_carbono(100.0, ["1", "2"])
    assert r["ranking"], "esperava empresas com emissões"
    top = r["ranking"][0]
    assert "×" in top["formula"] and top["tco2e"] > 0
    assert any(x.get("pct_ebitda") is not None for x in r["ranking"])   # ao menos uma casou com a CVM


def test_radar_traz_alertas_com_duas_evidencias():
    r = s.radar_consistencia()
    assert r["total"] >= 1
    for a in r["alertas"]:
        assert a["severidade"] in ("alta", "media", "baixa")
        assert a["evidencia_doc"] and a["evidencia_dado"]     # afirmação × dado, as duas citadas
    # a regra de asseguração deve pegar ao menos uma empresa que divulga por frameworks sem assegurar
    assert any(a["regra"] == "divulgacao_sem_asseguracao" for a in r["alertas"])

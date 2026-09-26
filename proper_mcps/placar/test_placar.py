"""Testes das ferramentas de coppezip-placar contra a base real (data/placar.duckdb + data/coppezip.duckdb).

Valores conferidos contra o gabarito researches/FINDINGS-claude-sonnet-5.md §3.2 (emissões por escopo, com página).
Rodar: .runtime/venv/bin/python -m pytest proper_mcps -q
"""
import importlib.util
import json
import os
import re

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


def test_todo_numero_do_ranking_tem_fonte():
    for metrica in ("score_divulgacao", "intensidade_receita", "escopo1_2", "pct_renovavel"):
        for item in s.placar_ranking(metrica)["ranking"]:
            assert item.get("fonte"), f"{metrica}: {item['empresa']} sem fonte"


def test_fonte_de_numero_agregado_cita_documento_e_pagina():
    h = next(h for h in s.consultar_placar()["metricas_hibridas"] if h.get("escopo1_2_tco2e"))
    assert re.search(r"\.pdf p\.\d", h["fonte_emissoes"]), h["fonte_emissoes"]
    c = s.exposicao_carbono(100.0)["ranking"][0]
    assert re.search(r"\.pdf p\.\d", c["fonte_emissoes"]), c["fonte_emissoes"]


def test_tela_ranking_grava_html_com_valor_e_fonte():
    r = s.tela_ranking("escopo1_2")
    assert r["gravado"] and r["tela"].startswith("/relatorios/")
    html = open(os.path.join(s.PASTA, os.path.basename(r["tela"])), encoding="utf-8").read()
    assert html.count("class=\"barra\"") == r["empresas"]          # uma barra por empresa
    assert html.count("<tr>") == r["empresas"] + 1                 # uma linha por empresa, mais o cabeçalho
    assert "p." in html and ".pdf" in html                         # a fonte aparece na tela
    assert "prefers-color-scheme" in html                          # tema claro e escuro


def test_tela_carbono_embute_dados_e_preco_ajustavel():
    r = s.tela_carbono(150.0)
    html = open(os.path.join(s.PASTA, os.path.basename(r["tela"])), encoding="utf-8").read()
    assert 'id="preco"' in html and 'type="range"' in html
    dados = json.loads(re.search(r"const D=(\[.*?\]);", html, re.DOTALL).group(1))
    assert len(dados) == r["empresas"]
    assert all(d["tco2e"] > 0 and d["fonte_emissoes"] for d in dados)


def test_tela_radar_mostra_severidade_com_rotulo():
    r = s.tela_radar()
    html = open(os.path.join(s.PASTA, os.path.basename(r["tela"])), encoding="utf-8").read()
    assert html.count("class=\"alerta ") == r["alertas"]
    assert "severidade" in html                                    # severidade escrita, não só a cor
    assert "Evidência no relatório" in html and "Evidência na base" in html


def test_escopo_2_nao_conta_duas_vezes():
    """Relatório que traz escopo 2 por localização e por mercado não pode somar os dois no 1+2."""
    r = s.consultar_placar("Cemig")
    e = {x["escopo"]: x["tco2e"] for x in r["emissoes"]}
    h = next(h for h in r["metricas_hibridas"] if h["escopo1_2_tco2e"])
    esperado = (e.get("1") or 0) + (e.get("2_mercado") or e.get("2") or 0)
    assert h["escopo1_2_tco2e"] == pytest.approx(esperado, rel=0.001)

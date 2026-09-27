"""Testes da extração do Placar (data/extrair_placar.py): checagem "o valor aparece na página", trecho citável e
concordância entre duas leituras. Não chamam o LLM nem o banco.

Rodar: .runtime/venv/bin/python -m pytest proper_mcps -q
"""
import importlib.util
import os

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_spec = importlib.util.spec_from_file_location("extrair_placar", os.path.join(RAIZ, "data", "extrair_placar.py"))
x = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(x)

PAGINA = ("Inventário de emissões 2024\nEscopo 1 (tCO2e) 42.860,81\nEscopo 2 (tCO2e) 376.174,25\n"
          "Em 2025, as emissões de Escopo 1 da Eneva atingiram 5,8 milhões de tCO2e.\n2,6      4,3      5,7\n")


@pytest.mark.parametrize("valor, trecho, esperado", [
    (42860.81, "Escopo 1 (tCO2e) 42.860,81", True),          # valor e trecho na página
    (376174.25, "Escopo 2 (tCO2e) 376.174,25", True),
    (5800000.0, "5,8 milhões de tCO2e", True),                # magnitude por extenso: a mantissa está no trecho
    (5838000.0, "5,8 milhões de tCO2e", False),               # algarismos que ninguém escreveu
    (99999.0, "Escopo 1 (tCO2e) 42.860,81", False),           # valor que não aparece
    (5700000.0, "2,6      4,3      5,7", False),              # linha de tabela sem rótulo não é citação
    (42860.81, "Escopo 1 (tCO2e) 42.860,81 — de outro documento", True),
])
def test_valor_aparece_na_pagina(valor, trecho, esperado):
    assert x._aparece_na_pagina(valor, trecho, PAGINA) is esperado


def test_trecho_precisa_de_rotulo():
    assert x._citavel("Escopo 3 (tCO2e) 1.416,07")
    assert not x._citavel("2,6      4,3      5,7")
    assert not x._citavel("")


def _leitura(escopo, tco2e, pagina=10):
    return {"escopo": escopo, "tco2e": tco2e, "pagina": pagina, "trecho": f"Escopo {escopo} (tCO2e) {tco2e}"}


def test_concordancia_descarta_o_que_so_apareceu_em_uma_leitura():
    a = [_leitura("1", 42860.81), _leitura("3", 163049.0)]
    b = [_leitura("1", 42860.81), _leitura("3", 12352904.0)]    # tabela ambígua: cada leitura pega uma coluna
    saida = x._concordantes([a, b], x.Emissao, x.CHAVE["esg_emissoes"])
    assert [(o.escopo, o.tco2e) for o in saida] == [("1", 42860.81)]


def test_uma_leitura_so_passa_tudo():
    a = [_leitura("1", 42860.81)]
    assert len(x._concordantes([a], x.Emissao, x.CHAVE["esg_emissoes"])) == 1


def test_schema_exige_pagina_e_trecho():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        x.Emissao(escopo="1", tco2e=10.0, pagina=3)             # sem trecho não há como conferir a fonte

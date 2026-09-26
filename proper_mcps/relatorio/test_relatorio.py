"""Testes de gerar_relatorio. Rodar: .runtime/venv/bin/python -m pytest proper_mcps -q"""
import importlib.util
import os
import zipfile
from xml.dom import minidom

import pytest

# carregado pelo caminho: proper_mcps/dados também tem um server.py
_spec = importlib.util.spec_from_file_location("relatorio_server", os.path.join(os.path.dirname(__file__), "server.py"))
server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(server)


@pytest.fixture()
def s(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "PASTA", str(tmp_path))
    return server


FONTES = [{"id": "F1", "descricao": "CVM DFP 2025, conta 3.01, via kpis_financeiros"},
          {"id": "F2", "descricao": "Relatório de Sustentabilidade Taesa 2025", "pagina": 22}]


def secao(texto="A receita da Taesa foi R$ 4,62 bi em 2025 [F1].", fontes_tab=("F1",)):
    return [{"titulo": "Receita", "texto": texto,
             "tabelas": [{"titulo": "Receita líquida 2025, R$ bi", "colunas": ["Empresa", "Receita"],
                          "linhas": [["Taesa", "4,62"]], "fontes": list(fontes_tab)}]}]


def test_grava_markdown_e_docx_valido(s, tmp_path):
    r = s.gerar_relatorio("Taesa em 2025", secao(), FONTES, sumario="Receita de R$ 4,62 bi [F1]; RAP na p. 22 [F2].",
                          lacunas=["Sem cronograma de dívida por instrumento na base."])
    assert r["gravado"], r
    arquivos = sorted(os.listdir(tmp_path))
    assert [a.rsplit(".", 1)[1] for a in arquivos] == ["docx", "md"]
    md = open(tmp_path / arquivos[1], encoding="utf-8").read()
    assert "| Taesa | 4,62 |" in md and "- [F2] Relatório de Sustentabilidade Taesa 2025, pagina 22" in md
    with zipfile.ZipFile(tmp_path / arquivos[0]) as z:
        minidom.parseString(z.read("word/document.xml"))  # XML bem formado
        assert "4,62" in z.read("word/document.xml").decode()


def test_recusa_numero_sem_fonte(s, tmp_path):
    r = s.gerar_relatorio("X", secao("A receita foi R$ 4,62 bi em 2025."), FONTES)
    assert not r["gravado"] and "sem fonte" in r["erros"][0]
    assert os.listdir(tmp_path) == []


def test_recusa_tabela_sem_fonte_e_citacao_inexistente(s):
    r = s.gerar_relatorio("X", secao("Receita de 4,62 [F9].", fontes_tab=()), FONTES)
    assert not r["gravado"]
    assert any("F9" in e for e in r["erros"]) and any("nenhuma fonte" in e for e in r["erros"])


def test_coluna_fonte_por_linha_vale_como_fonte(s):
    sec = [{"titulo": "T", "tabelas": [{"titulo": "2025", "colunas": ["Empresa", "Valor", "Fonte"],
                                        "linhas": [["A", "1,5", "[F1]"], ["B", "2,5", "[F2]"]]}]}]
    assert s.gerar_relatorio("T", sec, FONTES)["gravado"]


@pytest.mark.parametrize("texto, tem", [
    ("Em 2025 a empresa cresceu.", False),          # ano não conta
    ("Dados do 2T26 e escopo 1.", False),           # trimestre e número de um dígito
    ("Alavancagem de 3,9x.", True),
    ("Alta de 12%.", True),
    ("Lucro de R$ 616 mi.", True),
    ("Veja https://ri.taesa.com.br/2026/05/x.pdf", False),
    ("Dados preliminares até 30/09/2025 e vigência em 04/2026.", False),  # datas
])
def test_o_que_conta_como_numero(s, texto, tem):
    assert bool(s._numeros(texto)) is tem

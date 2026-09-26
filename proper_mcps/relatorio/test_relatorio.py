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

# ---------------------------------------------------------------- correções da auditoria de 26/09/2026
def test_conta_os_numeros_das_tabelas_e_das_lacunas(s):
    sec = [{"titulo": "Receita", "texto": "O quadro está na tabela [F1].",
            "tabelas": [{"titulo": "Receita líquida 2025, R$ bi", "colunas": ["Empresa", "Receita", "Margem"],
                         "linhas": [["Taesa", "4,62", "38,7%"], ["Alupar", "3,19", "41,2%"]], "fontes": ["F1"]}]}]
    r = s.gerar_relatorio("Transmissoras em 2025", sec, FONTES, sumario="O quadro está na tabela abaixo [F1].",
                          lacunas=["Falta a receita de 2026, que sai em 12 meses [F1]."])
    assert r["gravado"], r
    # antes a conta era só do texto: um relatório com os números em tabela devolvia zero
    assert r["numeros_com_fonte"] == {"total": 5, "no_texto": 0, "em_tabelas": 4, "em_lacunas": 1}
    assert "não foi conferido" in r["conferencia"]


def test_relatorio_sem_lacunas_recebe_aviso(s):
    r = s.gerar_relatorio("Taesa em 2025", secao(), FONTES, sumario="Receita de R$ 4,62 bi [F1]; RAP na p. 22 [F2].")
    assert r["gravado"]
    assert any("não tem lacunas" in a for a in r["avisos"])


@pytest.mark.parametrize("texto, cortado", [
    ("A receita foi de R$ 4,62 bi em 2025 [F1].", False),
    ("A receita de 2025 foi de R$ 4,62 bi [F1]", False),   # acabar na citação não é corte
    ("A receita subiu (4,62 contra 4,10 [F1])", False),
    ("A receita foi de R$ 4,62 bi [F1]...", True),
    ("A receita foi de R$ 4,62 bi [F1] […]", True),
    ("A Equatorial GO é a única dist", True),              # cortado no meio da palavra, mesmo em texto curto
    ("A receita cresceu [F1]. " + "Detalhe do período com números de 4,62 e 3,19 [F1]. " * 4 + "e o resto vem", True),
])
def test_texto_cortado_e_apontado(s, texto, cortado):
    assert bool(s._cortado(texto)) is cortado


def test_secao_cortada_recusa_o_relatorio(s, tmp_path):
    # a auditoria gravou dois relatórios cortados no meio da frase com gravado: true; agora é erro
    r = s.gerar_relatorio("Taesa em 2025", secao("A receita foi de R$ 4,62 bi em 2025 [F1]..."), FONTES,
                          sumario="Receita de R$ 4,62 bi [F1]; RAP na p. 22 [F2].",
                          lacunas=["Sem cronograma de dívida na base."])
    assert not r["gravado"] and os.listdir(tmp_path) == []
    assert any("marca de corte" in e for e in r["erros"])


def test_sumario_truncado_recusa_e_avisa_das_lacunas(s):
    r = s.gerar_relatorio("Distribuidoras em 2025", secao(), FONTES,
                          sumario="Entre as 4 comparadas, a Equatorial GO é a única dist", lacunas=[])
    assert not r["gravado"]
    assert any("parece truncado" in e and "única dist" in e for e in r["erros"])
    assert any("não tem lacunas" in a for a in r["avisos"])  # os avisos vêm junto da recusa, para corrigir de uma vez


def test_fonte_sem_localizador_gera_aviso(s):
    fontes = [{"id": "F1", "descricao": "dados da empresa"}]
    r = s.gerar_relatorio("X", secao("Receita de R$ 4,62 bi em 2025 [F1]."), fontes,
                          lacunas=["Sem comparação com 2024."])
    assert r["gravado"]
    assert any("não diz onde achar o número" in a for a in r["avisos"])


def test_fonte_com_tabela_pagina_ou_link_nao_gera_aviso(s):
    r = s.gerar_relatorio("X", secao("Receita de R$ 4,62 bi em 2025 [F1]."), FONTES,
                          lacunas=["Sem comparação com 2024."])
    assert r["gravado"]
    assert not any("não diz onde achar" in a for a in r.get("avisos", []))


def test_nome_de_arquivo_e_link_nao_contam_como_tabela(s):
    assert s._tabelas_citadas("Cemig, cemig_relatorio_2025.pdf, p. 87") == []
    assert s._tabelas_citadas("veja https://ri.taesa.com.br/dados_2025.html") == []
    assert s._tabelas_citadas("CVM DFP 2025, conta 3.01, via kpis_financeiros") == ["kpis_financeiros"]


@pytest.mark.skipif(not os.path.exists(server.CATALOGO_DB), reason="o catálogo da base não está nesta máquina")
def test_fonte_com_tabela_inventada_gera_aviso(s):
    # a auditoria passou "tabela_que_nao_existe, conta 9.99" e o relatório saiu com cara de auditado
    fontes = [{"id": "F1", "descricao": "tabela_que_nao_existe, conta 9.99, via ORGAO_INVENTADO"}]
    r = s.gerar_relatorio("X", secao(), fontes, lacunas=["Sem comparação com 2024."])
    assert r["gravado"]
    assert any("'tabela_que_nao_existe' não é uma tabela da base" in a for a in r["avisos"])
    boa = s.gerar_relatorio("X", secao(), FONTES, lacunas=["Sem comparação com 2024."])  # kpis_financeiros existe
    assert boa["gravado"] and not any("não é uma tabela da base" in a for a in boa.get("avisos", []))


def test_sem_o_catalogo_o_relatorio_diz_que_nao_conferiu(s, tmp_path, monkeypatch):
    # o runtime do AgentCore sobe só o relatório, sem o banco ao lado: a conferência não acontece e isso fica dito
    monkeypatch.setattr(s, "CATALOGO_DB", str(tmp_path / "nao_existe.duckdb"))
    r = s.gerar_relatorio("X", secao(), FONTES, lacunas=["Sem comparação com 2024."])
    assert r["gravado"] and any("não confiro os nomes de tabela" in a for a in r["avisos"])

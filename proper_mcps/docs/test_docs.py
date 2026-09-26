"""Testes das ferramentas de documentos. Rodar: .runtime/venv/bin/python -m pytest proper_mcps -q"""
import importlib.util
import os

import duckdb
import pytest
from mcp.server.mcpserver.exceptions import ToolError

# carregado pelo caminho: proper_mcps/dados e proper_mcps/relatorio também têm um server.py
_spec = importlib.util.spec_from_file_location("docs_server", os.path.join(os.path.dirname(__file__), "server.py"))
server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(server)


def _base(caminho: str, com_area: bool) -> None:
    """Índice mínimo; com_area=False imita um índice de versão antiga (data/indexar_docs.py, sem a coluna area)."""
    con = duckdb.connect(caminho)
    area = "area VARCHAR, " if com_area else ""
    con.execute(f"""CREATE TABLE documentos (arquivo VARCHAR, empresa VARCHAR, cnpj VARCHAR, ano INTEGER,
                    tipo VARCHAR, {area}titulo VARCHAR, url VARCHAR, paginas INTEGER)""")
    valores = ("'rel.pdf', 'Cemig', '06.981.180/0001-16', 2025, 'sustentabilidade', "
               + ("'sustentabilidade', " if com_area else "")
               + "'Relatório Anual 2025', NULL, 3")
    con.execute(f"INSERT INTO documentos VALUES ({valores})")
    con.execute("CREATE TABLE paginas (arquivo VARCHAR, pagina INTEGER, texto VARCHAR)")
    con.execute("INSERT INTO paginas VALUES ('rel.pdf', 1, 'Emissões de escopo 1 de 2025: 1.234 tCO2e.')")
    con.close()


@pytest.fixture()
def antigo(tmp_path, monkeypatch):
    caminho = str(tmp_path / "docs_titan.duckdb")
    _base(caminho, com_area=False)
    monkeypatch.setattr(server, "DB", caminho)
    return server


@pytest.fixture()
def atual(tmp_path, monkeypatch):
    caminho = str(tmp_path / "docs_titan.duckdb")
    _base(caminho, com_area=True)
    monkeypatch.setattr(server, "DB", caminho)
    return server


def test_indice_sem_area_vira_toolerror_com_o_motivo(antigo):
    # erro cru do DuckDB chega ao modelo como "Error executing tool"; ToolError diz o motivo e o que fazer
    with pytest.raises(ToolError) as e:
        antigo.listar_documentos()
    assert "não tem a coluna" in str(e.value) or "area" in str(e.value)
    assert "indexar_docs_titan.py" in str(e.value)


def test_ler_pagina_sem_a_tabela_paginas_vira_toolerror(tmp_path, monkeypatch):
    # índice interrompido no meio da indexação: documentos existe, paginas não
    caminho = str(tmp_path / "docs_titan.duckdb")
    _base(caminho, com_area=True)
    con = duckdb.connect(caminho)
    con.execute("DROP TABLE paginas")
    con.close()
    monkeypatch.setattr(server, "DB", caminho)
    with pytest.raises(ToolError) as e:
        server.ler_pagina("rel.pdf", 1)
    assert "paginas" in str(e.value) and "indexar_docs_titan.py" in str(e.value)


def test_buscar_documentos_em_indice_antigo_vira_toolerror(antigo, monkeypatch):
    monkeypatch.setattr(antigo, "_embed", lambda _: [0.0] * 1024)
    with pytest.raises(ToolError) as e:
        antigo.buscar_documentos("emissões escopo 1")
    assert "indexar_docs_titan.py" in str(e.value)


def test_indice_sem_arquivo_avisa_em_vez_de_estourar(atual):
    assert atual.ler_pagina("nao_existe.pdf", 1)["erro"].startswith("arquivo 'nao_existe.pdf' não existe")


def test_listar_documentos_conta_por_area(atual):
    r = atual.listar_documentos(area="sustentabilidade")
    assert r["total"] == 1
    assert r["por_tipo"][0]["area"] == "sustentabilidade"
    assert atual.listar_documentos(area="financeiro")["total"] == 0


def test_ler_pagina_devolve_o_texto_e_o_total(atual):
    r = atual.ler_pagina("rel.pdf", 1)
    assert r["total_paginas"] == 3 and "1.234 tCO2e" in r["texto"]


def test_sem_indice_diz_qual_arquivo_falta(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "DB", str(tmp_path / "nao_existe.duckdb"))
    with pytest.raises(ToolError) as e:
        server.listar_documentos()
    assert "indexar_docs_titan.py" in str(e.value)

"""Testes do índice gerado por data/indexar_dados_local.py, contra o data/docs.duckdb que está em uso.

Conferem o que a busca e a linha do tempo precisam: cobertura dos PDFs, metadados preenchidos, vetores com a assinatura
do modelo e norma 1, e os índices de palavras respondendo. Não usam GPU.
Rodar: .runtime/venv/bin/python -m pytest data -q
"""
import os

import duckdb
import numpy as np
import pytest

import indexar_dados_local as ix

BANCO = os.path.join(ix.AQUI, "docs.duckdb")


@pytest.fixture(scope="module")
def con():
    c = duckdb.connect(BANCO, read_only=True)
    c.execute("LOAD fts")
    yield c
    c.close()


def test_meta_diz_de_que_modelo_sao_os_vetores(con):
    meta = dict(con.execute("SELECT chave, valor FROM meta").fetchall())
    assert meta["modelo"] == ix.MODELO
    assert meta["embedding"] == ix.ASSINATURA  # muda se o modelo, o prefixo ou o corte dos trechos mudarem
    assert int(meta["dimensoes"]) == ix.DIMENSOES
    assert (meta["prefixo_trecho"], meta["prefixo_pergunta"]) == ("passage: ", "query: ")


def test_todo_pdf_de_data_raw_esta_no_indice_ou_e_copia_de_quem_esta(con):
    indexados = {r[0] for r in con.execute("SELECT arquivo FROM documentos").fetchall()}
    disco = set(ix.pdfs_em_disco())
    assert indexados <= disco, "o índice cita PDF que não está mais em data/raw"
    tamanho = {a: os.path.getsize(os.path.join(ix.PDFS, a)) for a in disco}
    for arquivo in sorted(disco - indexados):  # o que ficou fora só pode ser o mesmo PDF sob outro caminho
        candidatos = [a for a in indexados if tamanho[a] == tamanho[arquivo]]
        assert candidatos, f"{arquivo} não está no índice e nenhum PDF indexado tem o mesmo tamanho"
        meu = ix.md5(os.path.join(ix.PDFS, arquivo))
        assert any(ix.md5(os.path.join(ix.PDFS, a)) == meu for a in candidatos), \
            f"{arquivo} ficou fora do índice e não é cópia de nenhum PDF indexado"


def test_dicionarios_da_aneel_entram_com_tipo_proprio(con):
    for arquivo in ix.DICIONARIOS:
        linha = con.execute("SELECT area, tipo, ano, titulo, cnpj FROM documentos WHERE arquivo = ?",
                            [arquivo]).fetchone()
        assert linha, f"{arquivo} não está no índice"
        area, tipo, ano, titulo, cnpj = linha
        assert (area, tipo) == (ix.AREA_DICIONARIO, ix.TIPO_DICIONARIO)
        assert 2015 <= ano <= 2030 and titulo.startswith("Dicionário de dados da ANEEL:") and cnpj is None


def test_todo_documento_tem_empresa_e_ano(con):
    # linha_do_tempo.py agrupa por empresa e compara ano: nome vazio ou ano nulo quebram a aba Timeline
    assert con.execute("SELECT count(*) FROM documentos WHERE coalesce(empresa, '') = '' OR ano IS NULL") \
        .fetchone()[0] == 0


def test_trecho_e_bloco_apontam_para_pagina_que_existe(con):
    for tabela in ("trechos", "blocos"):
        assert con.execute(f"""SELECT count(*) FROM {tabela} t LEFT JOIN documentos d USING (arquivo)
                               WHERE d.arquivo IS NULL OR t.pagina < 1 OR t.pagina > d.paginas""").fetchone()[0] == 0
    assert con.execute("""SELECT count(*) FROM trechos t LEFT JOIN paginas p USING (arquivo, pagina)
                          WHERE p.texto IS NULL""").fetchone()[0] == 0


def test_vetores_tem_a_dimensao_e_a_norma_que_a_busca_espera(con):
    vetores = [np.array(r[0], dtype=np.float32) for r in
               con.execute("SELECT embedding FROM trechos USING SAMPLE 300 ROWS").fetchall()]
    normas = [float(np.linalg.norm(v)) for v in vetores]
    assert len(normas) == 300 and all(len(v) == ix.DIMENSOES for v in vetores)
    # array_cosine_similarity com vetores de norma 1 é o produto escalar: norma errada é vetor de outro modelo
    assert max(abs(n - 1) for n in normas) < 1e-3


def test_busca_por_palavras_acha_o_termo_do_setor(con):
    for tabela, consulta in (("trechos", "emissões escopo 1 tCO2e"), ("blocos", "receita líquida")):
        achados = con.execute(f"""SELECT texto FROM (SELECT *, fts_main_{tabela}.match_bm25(id, ?) AS s FROM {tabela})
                                 WHERE s IS NOT NULL ORDER BY s DESC LIMIT 5""", [consulta]).fetchall()
        assert len(achados) == 5, f"o índice de palavras de {tabela} não respondeu a {consulta!r}"

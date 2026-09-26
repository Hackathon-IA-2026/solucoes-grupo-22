"""Indexa os PDFs de relatórios para o coppezip-docs: texto por página, trechos, índice de palavras (BM25) e embeddings.

Uso: python data/indexar_docs.py [--threads N] [--tudo]
Entrada: os PDFs de data/raw/pdfs_esg descritos em data/documentos.csv (empresa, cnpj, ano, tipo, título, url). PDF fora do CSV é ignorado.
Saída: data/docs.duckdb com documentos, paginas e trechos (embedding FLOAT[1024] do multilingual-e5-large), trocado de forma
atômica, e blocos (os parágrafos de cada página na ordem do PDF, sem misturar colunas, para a linha do tempo de
data/linha_do_tempo.py). Incremental: reaproveita os embeddings dos PDFs que não mudaram (mesmo nome e tamanho) do índice
anterior.
"""
import argparse
import csv
import os
import re
import time

import duckdb
import pymupdf as fitz
import pyarrow as pa
from fastembed import TextEmbedding

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raiz do repositório
PDFS = os.path.join(RAIZ, "data", "raw", "pdfs_esg")
SAIDA = os.path.join(RAIZ, "data", "docs.duckdb")


AQUI = os.path.dirname(os.path.abspath(__file__))
MODELO = "intfloat/multilingual-e5-large"
# cópia simples do modelo (o onnxruntime recusa os links simbólicos do cache do Hugging Face)
PASTA_MODELO = os.path.join(RAIZ, "data", "modelos", "multilingual-e5-large")
TAMANHO, SOBRA = 1200, 200  # caracteres por trecho; o e5 lê até 512 tokens


def trechos(texto: str) -> list[str]:
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip()
    if len(texto) < 80:
        return []
    partes, i = [], 0
    while i < len(texto):
        fim = min(len(texto), i + TAMANHO)
        if fim < len(texto):  # corta num fim de linha ou de frase perto do limite
            corte = max(texto.rfind("\n", i + TAMANHO // 2, fim), texto.rfind(". ", i + TAMANHO // 2, fim))
            if corte > i:
                fim = corte + 1
        partes.append(texto[i:fim].strip())
        if fim >= len(texto):
            break
        i = max(fim - SOBRA, i + 1)
    return [p for p in partes if len(p) >= 80]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, default=12, help="núcleos para os embeddings (o kolyma é compartilhado)")
    ap.add_argument("--tudo", action="store_true", help="recalcula todos os embeddings")
    a = ap.parse_args()

    with open(os.path.join(AQUI, "documentos.csv"), newline="") as f:
        docs = list(csv.DictReader(f, delimiter=";"))
    presentes = {os.path.basename(p) for p in os.listdir(PDFS) if p.endswith(".pdf")}
    for faltando in sorted({d["arquivo"] for d in docs} - presentes):
        print(f"aviso: {faltando} está no documentos.csv mas não na pasta")
    for sobra in sorted(presentes - {d["arquivo"] for d in docs}):
        print(f"aviso: {sobra} não está no documentos.csv e fica fora do índice")

    # embeddings já calculados, por (arquivo, tamanho do PDF): o que não mudou não é recalculado
    anteriores = {}
    if os.path.exists(SAIDA) and not a.tudo:
        velho = duckdb.connect(SAIDA, read_only=True)
        colunas = {r[0] for r in velho.execute("DESCRIBE documentos").fetchall()}
        if "bytes" in colunas:
            for arq, tam, pag, texto, emb in velho.execute("""SELECT t.arquivo, d.bytes, t.pagina, t.texto, t.embedding
                    FROM trechos t JOIN documentos d USING (arquivo)""").fetchall():
                anteriores.setdefault((arq, tam), {})[(pag, texto)] = emb
        velho.close()

    paginas, pedacos, blocos = [], [], []
    for d in docs:
        caminho = os.path.join(PDFS, d["arquivo"])
        if not os.path.exists(caminho):
            continue
        d["bytes"] = os.path.getsize(caminho)
        with fitz.open(caminho) as pdf:
            d["paginas"] = pdf.page_count
            for n, pagina in enumerate(pdf, start=1):
                texto = pagina.get_text("text", sort=True)
                paginas.append((d["arquivo"], n, texto))
                for t in trechos(texto):
                    pedacos.append((d["arquivo"], n, t))
                for b in pagina.get_text("blocks"):  # (x0, y0, x1, y1, texto, número, tipo): tipo 0 é texto
                    if b[6] == 0 and len(b[4].strip()) >= 80:
                        blocos.append((d["arquivo"], n, b[4].strip()))
        print(f"{d['arquivo']}: {d['paginas']} páginas")
    print(f"{len(paginas)} páginas, {len(pedacos)} trechos; calculando embeddings ({MODELO})...")

    info = {d["arquivo"]: d for d in docs}
    vetores = [anteriores.get((arq, info[arq]["bytes"]), {}).get((pag, t)) for arq, pag, t in pedacos]
    faltam = [i for i, v in enumerate(vetores) if v is None]
    print(f"{len(pedacos) - len(faltam)} embeddings reaproveitados, {len(faltam)} a calcular")
    if faltam:
        modelo = TextEmbedding(MODELO, specific_model_path=PASTA_MODELO, threads=a.threads)
        inicio = time.time()
        # o e5 espera "passage: " nos textos indexados; empresa, ano e título dão contexto a trechos soltos de tabela
        textos = [f"passage: {info[pedacos[i][0]]['empresa']} {info[pedacos[i][0]]['ano']}, {info[pedacos[i][0]]['titulo']}. "
                  f"{pedacos[i][2]}" for i in faltam]
        for i, v in zip(faltam, modelo.embed(textos, batch_size=32)):
            vetores[i] = v.tolist()
        print(f"embeddings em {time.time() - inicio:.0f} s")

    tmp = SAIDA + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)
    con = duckdb.connect(tmp)
    con.execute("""CREATE TABLE documentos (arquivo VARCHAR PRIMARY KEY, empresa VARCHAR, cnpj VARCHAR, ano INTEGER,
                   tipo VARCHAR, titulo VARCHAR, url VARCHAR, paginas INTEGER, bytes BIGINT)""")
    con.executemany("INSERT INTO documentos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [(d["arquivo"], d["empresa"], d["cnpj"] or None, int(d["ano"]), d["tipo"], d["titulo"], d["url"],
                      d.get("paginas"), d.get("bytes")) for d in docs if d.get("paginas")])
    con.execute("CREATE TABLE paginas (arquivo VARCHAR, pagina INTEGER, texto VARCHAR)")
    con.executemany("INSERT INTO paginas VALUES (?, ?, ?)", paginas)
    tabela = pa.table({
        "id": pa.array(range(len(pedacos)), pa.int64()),
        "arquivo": [p[0] for p in pedacos], "pagina": pa.array([p[1] for p in pedacos], pa.int32()),
        "texto": [p[2] for p in pedacos],
        "embedding": pa.array([list(v) for v in vetores], pa.list_(pa.float32(), len(vetores[0]))),
    })
    con.execute("CREATE TABLE trechos AS SELECT * FROM tabela")
    paragrafos = pa.table({"id": pa.array(range(len(blocos)), pa.int64()), "arquivo": [b[0] for b in blocos],
                           "pagina": pa.array([b[1] for b in blocos], pa.int32()), "texto": [b[2] for b in blocos]})
    con.execute("CREATE TABLE blocos AS SELECT * FROM paragrafos")
    con.execute("INSTALL fts; LOAD fts")
    # índice de palavras em português, sem acento e mantendo números (escopo 1, 2025, tCO2e)
    for t in ("trechos", "blocos"):
        con.execute(f"""PRAGMA create_fts_index('{t}', 'id', 'texto', stemmer = 'portuguese', stopwords = 'none',
                       ignore = '(\\.|[^a-z0-9])+', strip_accents = 1, lower = 1)""")
    con.close()
    os.replace(tmp, SAIDA)
    print("ok:", SAIDA)


if __name__ == "__main__":
    main()

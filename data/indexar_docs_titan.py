"""Indexa os PDFs de relatórios como o indexar_docs.py, mas com embeddings do Amazon Titan (Bedrock) em vez do e5 local.

Uso: python data/indexar_docs_titan.py [--threads N] [--tudo] [--limite N] [--publicar-a-cada N] [--temas]
Entrada: a mesma do indexar_docs.py (data/documentos.csv e os PDFs de data/raw/financeiro e data/raw/sustentabilidade).
Credenciais: cadeia padrão da AWS (~/.aws/credentials), região BEDROCK_AWS_DEFAULT_REGION do .env.
Saída: data/docs_titan.duckdb com as mesmas tabelas do docs.duckdb (documentos, paginas, trechos com embedding FLOAT[1024]
do amazon.titan-embed-text-v2:0, normalizado, e blocos, os parágrafos da aba Timeline), mais temas, o vetor da consulta
de cada tema da aba Timeline. Na busca, a pergunta passa pelo mesmo modelo, sem o prefixo "query: " do e5.

Feito para máquina pequena e credencial temporária: cada PDF é gravado assim que termina em data/docs_titan.duckdb.trabalho
(nada fica acumulado na memória), e a próxima execução continua de onde parou; PDF que mudou de tamanho ou saiu do CSV é
refeito ou removido. A cada N PDFs e no fim, uma cópia do trabalho com o índice de palavras e os vetores dos temas
substitui a saída de forma atômica, então a busca e a aba Timeline funcionam durante a indexação com o que já está
pronto. Um trabalho de antes da tabela blocos ganha os parágrafos dos PDFs já indexados na execução seguinte, lidos dos
próprios PDFs, sem chamar o Bedrock. --temas só refaz os vetores dos temas no índice publicado.
"""
import argparse
import csv
import json
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor

import boto3
import duckdb
import pymupdf as fitz
import pyarrow as pa
from botocore.config import Config

from indexar_docs import AQUI, AREAS, PDFS, RAIZ, blocos_de, trechos
from linha_do_tempo import TEMAS

SAIDA = os.path.join(RAIZ, "data", "docs_titan.duckdb")
TRABALHO = SAIDA + ".trabalho"
MODELO = "amazon.titan-embed-text-v2:0"
DIMENSOES = 1024  # o Titan v2 aceita 256, 512 ou 1024; 1024 mantém o esquema do docs.duckdb


def regiao() -> str:
    with open(os.path.join(RAIZ, ".env")) as f:
        for linha in f:
            if linha.startswith("BEDROCK_AWS_DEFAULT_REGION="):
                return linha.split("=", 1)[1].strip()
    raise SystemExit("falta BEDROCK_AWS_DEFAULT_REGION no .env")


def cliente(threads: int):
    # o Titan não aceita lote: uma chamada por trecho; o modo adaptativo segura o ritmo quando a AWS devolve throttling
    return boto3.client("bedrock-runtime", region_name=regiao(),
                        config=Config(max_pool_connections=threads, retries={"max_attempts": 10, "mode": "adaptive"}))


def embed(bedrock, texto: str) -> list[float]:
    for tentativa in range(6):
        try:
            r = bedrock.invoke_model(modelId=MODELO, contentType="application/json", accept="application/json",
                                     body=json.dumps({"inputText": texto, "dimensions": DIMENSOES, "normalize": True}))
            return json.loads(r["body"].read())["embedding"]
        except bedrock.exceptions.ModelErrorException:  # erro passageiro do Bedrock que o boto3 não repete sozinho
            if tentativa == 5:
                raise
            time.sleep(2 ** tentativa)


def abrir_trabalho(tudo: bool):
    if tudo and os.path.exists(TRABALHO):
        os.remove(TRABALHO)
    if not os.path.exists(TRABALHO) and os.path.exists(SAIDA) and not tudo:
        shutil.copy(SAIDA, TRABALHO)  # continua de um índice já publicado
    con = duckdb.connect(TRABALHO)
    con.execute("INSTALL fts; LOAD fts")
    for tabela in ("trechos", "blocos"):  # o índice de palavras só existe nas cópias publicadas
        if con.execute("SELECT count(*) FROM information_schema.schemata WHERE schema_name = ?",
                       [f"fts_main_{tabela}"]).fetchone()[0]:
            con.execute(f"PRAGMA drop_fts_index('{tabela}')")
    con.execute("""CREATE TABLE IF NOT EXISTS documentos (arquivo VARCHAR PRIMARY KEY, area VARCHAR, empresa VARCHAR,
                   cnpj VARCHAR, ano INTEGER, tipo VARCHAR, titulo VARCHAR, url VARCHAR, paginas INTEGER, bytes BIGINT)""")
    con.execute("CREATE TABLE IF NOT EXISTS paginas (arquivo VARCHAR, pagina INTEGER, texto VARCHAR)")
    con.execute(f"""CREATE TABLE IF NOT EXISTS trechos (id BIGINT, arquivo VARCHAR, pagina INTEGER, texto VARCHAR,
                    embedding FLOAT[{DIMENSOES}])""")
    if not con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = 'blocos'").fetchone()[0]:
        # trabalho de antes da tabela: os parágrafos dos PDFs já indexados, numa transação só (se parar, recomeça inteira)
        con.execute("BEGIN")
        con.execute("CREATE TABLE blocos (id BIGINT, arquivo VARCHAR, pagina INTEGER, texto VARCHAR)")
        arquivos = [r[0] for r in con.execute("SELECT arquivo FROM documentos").fetchall()]
        for arquivo in arquivos:
            if os.path.exists(os.path.join(PDFS, arquivo)):  # o que sumiu da pasta o main() tira do índice
                with fitz.open(os.path.join(PDFS, arquivo)) as pdf:
                    gravar_blocos(con, arquivo, [(n, t) for n, pagina in enumerate(pdf, start=1) for t in blocos_de(pagina)])
        con.execute("COMMIT")
        print(f"parágrafos dos {len(arquivos)} PDFs já indexados gravados na tabela blocos", flush=True)
    return con


def gravar_blocos(con, arquivo: str, blocos: list[tuple[int, str]]):
    """Parágrafos (página, texto) de um PDF na tabela blocos, com ids novos (o índice de palavras usa o id)."""
    if not blocos:
        return
    inicio = con.execute("SELECT coalesce(max(id) + 1, 0) FROM blocos").fetchone()[0]
    tabela = pa.table({"id": pa.array(range(inicio, inicio + len(blocos)), pa.int64()), "arquivo": [arquivo] * len(blocos),
                       "pagina": pa.array([b[0] for b in blocos], pa.int32()), "texto": [b[1] for b in blocos]})
    con.execute("INSERT INTO blocos SELECT * FROM tabela")


def remover(con, arquivo: str):
    for tabela in ("trechos", "blocos", "paginas", "documentos"):
        con.execute(f"DELETE FROM {tabela} WHERE arquivo = ?", [arquivo])


def gravar_temas(pub, bedrock):
    """Vetor da consulta de cada tema da aba Timeline (data/linha_do_tempo.py), no mesmo modelo dos trechos.

    São sete chamadas por publicação: a busca por sentido da linha do tempo compara esses vetores com os dos trechos,
    então eles precisam viajar junto com o índice publicado."""
    pub.execute(f"CREATE OR REPLACE TABLE temas (tema VARCHAR, consulta VARCHAR, embedding FLOAT[{DIMENSOES}])")
    pub.executemany("INSERT INTO temas VALUES (?, ?, ?::FLOAT[%d])" % DIMENSOES,
                    [(tema, consulta, embed(bedrock, consulta)) for tema, (_, consulta, _) in TEMAS.items()])


def publicar(con, bedrock):
    """Copia o trabalho, monta o índice de palavras e os vetores dos temas na cópia e troca a saída; devolve a conexão
    reaberta."""
    con.execute("CHECKPOINT")
    con.close()
    tmp = SAIDA + ".tmp"
    shutil.copy(TRABALHO, tmp)
    pub = duckdb.connect(tmp)
    pub.execute("LOAD fts")
    # índice de palavras em português, sem acento e mantendo números (escopo 1, 2025, tCO2e)
    for tabela in ("trechos", "blocos"):
        pub.execute(f"""PRAGMA create_fts_index('{tabela}', 'id', 'texto', stemmer = 'portuguese', stopwords = 'none',
                        ignore = '(\\.|[^a-z0-9])+', strip_accents = 1, lower = 1)""")
    gravar_temas(pub, bedrock)
    documentos, trechos_, paragrafos = pub.execute("""SELECT (SELECT count(*) FROM documentos),
        (SELECT count(*) FROM trechos), (SELECT count(*) FROM blocos)""").fetchone()
    pub.close()
    os.replace(tmp, SAIDA)
    print(f"publicado: {documentos} PDFs, {trechos_} trechos, {paragrafos} parágrafos em {SAIDA}", flush=True)
    con = duckdb.connect(TRABALHO)
    con.execute("LOAD fts")
    return con


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, default=16, help="chamadas simultâneas ao Bedrock")
    ap.add_argument("--tudo", action="store_true", help="recomeça do zero")
    ap.add_argument("--limite", type=int, help="indexa só os N primeiros PDFs do documentos.csv (teste)")
    ap.add_argument("--publicar-a-cada", type=int, default=200, help="PDFs novos entre uma publicação e outra")
    ap.add_argument("--temas", action="store_true",
                    help="só refaz a tabela temas no índice já publicado (sete chamadas ao Bedrock, nada é reindexado)")
    a = ap.parse_args()

    if a.temas:  # mesma troca atômica da publicação: a busca continua no ar com o índice antigo até o fim
        tmp = SAIDA + ".tmp"
        shutil.copy(SAIDA, tmp)
        pub = duckdb.connect(tmp)
        gravar_temas(pub, cliente(1))
        temas = pub.execute("SELECT count(*) FROM temas").fetchone()[0]
        pub.close()
        os.replace(tmp, SAIDA)
        return print(f"{temas} temas vetorizados em {SAIDA}")

    with open(os.path.join(AQUI, "documentos.csv"), newline="") as f:
        docs = list(csv.DictReader(f, delimiter=";"))
    presentes = {os.path.relpath(os.path.join(pasta, p), PDFS).replace(os.sep, "/")
                 for area in AREAS for pasta, _, arquivos in os.walk(os.path.join(PDFS, area))
                 for p in arquivos if p.endswith(".pdf")}
    for faltando in sorted({d["arquivo"] for d in docs} - presentes):
        print(f"aviso: {faltando} está no documentos.csv mas não na pasta")
    for sobra in sorted(presentes - {d["arquivo"] for d in docs}):
        print(f"aviso: {sobra} não está no documentos.csv e fica fora do índice")
    docs = [d for d in docs if d["arquivo"] in presentes]
    if a.limite is not None:
        docs = docs[:a.limite]
    for d in docs:
        d["bytes"] = os.path.getsize(os.path.join(PDFS, d["arquivo"]))

    con = abrir_trabalho(a.tudo)
    feitos = dict(con.execute("SELECT arquivo, bytes FROM documentos").fetchall())
    queridos = {d["arquivo"]: d["bytes"] for d in docs}
    for arquivo, tamanho in feitos.items():  # saiu do CSV (ou da seleção) ou o PDF mudou
        if queridos.get(arquivo) != tamanho:
            remover(con, arquivo)
    # empresa, título etc. podem ter sido corrigidos no CSV sem mudar o PDF
    con.executemany("UPDATE documentos SET area = ?, empresa = ?, cnpj = ?, ano = ?, tipo = ?, titulo = ?, url = ? "
                    "WHERE arquivo = ?", [(d["arquivo"].split("/")[0], d["empresa"], d["cnpj"] or None, int(d["ano"]),
                                          d["tipo"], d["titulo"], d["url"] or None, d["arquivo"]) for d in docs])
    pendentes = [d for d in docs if feitos.get(d["arquivo"]) != d["bytes"]]
    print(f"{len(docs)} PDFs: {len(docs) - len(pendentes)} já indexados, {len(pendentes)} a indexar ({MODELO})", flush=True)

    bedrock = cliente(a.threads)
    proximo_id = con.execute("SELECT coalesce(max(id) + 1, 0) FROM trechos").fetchone()[0]
    inicio, novos, desde = time.time(), 0, 0
    with ThreadPoolExecutor(a.threads) as ex:
        for n, d in enumerate(pendentes, start=1):
            paginas, pedacos, blocos = [], [], []
            with fitz.open(os.path.join(PDFS, d["arquivo"])) as pdf:
                d["paginas"] = pdf.page_count
                for num, pagina in enumerate(pdf, start=1):
                    texto = pagina.get_text("text", sort=True)
                    paginas.append((d["arquivo"], num, texto))
                    pedacos += [(num, t) for t in trechos(texto)]
                    blocos += [(num, t) for t in blocos_de(pagina)]
            # empresa, ano e título dão contexto a trechos soltos de tabela
            vetores = list(ex.map(lambda p: embed(bedrock, f"{d['empresa']} {d['ano']}, {d['titulo']}. {p[1]}"), pedacos))
            con.execute("BEGIN")
            remover(con, d["arquivo"])
            con.execute("INSERT INTO documentos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        [d["arquivo"], d["arquivo"].split("/")[0], d["empresa"], d["cnpj"] or None, int(d["ano"]),
                         d["tipo"], d["titulo"], d["url"] or None, d["paginas"], d["bytes"]])
            con.executemany("INSERT INTO paginas VALUES (?, ?, ?)", paginas)
            if pedacos:
                tabela = pa.table({
                    "id": pa.array(range(proximo_id, proximo_id + len(pedacos)), pa.int64()),
                    "arquivo": [d["arquivo"]] * len(pedacos), "pagina": pa.array([p[0] for p in pedacos], pa.int32()),
                    "texto": [p[1] for p in pedacos],
                    "embedding": pa.array(vetores, pa.list_(pa.float32(), DIMENSOES)),
                })
                con.execute("INSERT INTO trechos SELECT * FROM tabela")
                proximo_id += len(pedacos)
            gravar_blocos(con, d["arquivo"], blocos)
            con.execute("COMMIT")
            novos += len(pedacos)
            desde += 1
            print(f"[{n}/{len(pendentes)}] {d['arquivo']}: {d['paginas']} páginas, {len(pedacos)} trechos "
                  f"({novos / (time.time() - inicio):.0f} trechos/s)", flush=True)
            if desde >= a.publicar_a_cada:
                con, desde = publicar(con, bedrock), 0
    publicar(con, bedrock).close()
    print(f"ok em {time.time() - inicio:.0f} s")


if __name__ == "__main__":
    main()

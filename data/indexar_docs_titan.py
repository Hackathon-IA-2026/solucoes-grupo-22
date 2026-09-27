"""Indexa os PDFs de relatórios como o indexar_docs.py, mas com embeddings do Amazon Titan (Bedrock) em vez do e5 local.

Uso: python data/indexar_docs_titan.py [--threads N] [--tudo] [--limite N] [--publicar-a-cada N] [--saida CAMINHO]
                                       [--do-indice-local]
Entrada: a mesma do indexar_docs.py (data/documentos.csv e os PDFs de data/raw/financeiro e data/raw/sustentabilidade).
Com --do-indice-local, o texto por página e os trechos vêm prontos de data/docs.duckdb (o índice que o
data/indexar_dados_local.py montou na GPU) e nenhum PDF é aberto: o corte dos trechos é o mesmo nos dois scripts, então só
os vetores mudam (e5 local -> Titan). É o caminho rápido para reaproveitar uma extração que já custou horas de CPU.
Credenciais: cadeia padrão da AWS (~/.aws/credentials), região BEDROCK_AWS_DEFAULT_REGION do .env.
Saída: data/docs_titan.duckdb (ou --saida) com as mesmas tabelas do docs.duckdb (documentos, paginas, trechos com
embedding FLOAT[1024] do amazon.titan-embed-text-v2:0, normalizado). Na busca, a pergunta passa pelo mesmo modelo, sem o
prefixo "query: " do e5. Ponha a saída no disco local do nó (--saida) e ligue data/docs_titan.duckdb a ela: DuckDB em NFS
trava, e a troca atômica da publicação apagaria o link simbólico.

Feito para máquina pequena e credencial temporária: cada PDF é gravado assim que termina em <saída>.trabalho
(nada fica acumulado na memória), e a próxima execução continua de onde parou; PDF que mudou de tamanho ou saiu do CSV é
refeito ou removido. A cada N PDFs e no fim, uma cópia do trabalho com o índice de palavras substitui a saída de forma
atômica, então a busca funciona durante a indexação com o que já está pronto.
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

from indexar_docs import AQUI, AREAS, PDFS, RAIZ, trechos

SAIDA_PADRAO = os.path.join(RAIZ, "data", "docs_titan.duckdb")
LOCAL = os.path.join(RAIZ, "data", "docs.duckdb")  # índice do e5 feito na GPU: a fonte do texto com --do-indice-local
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


def abrir_trabalho(saida: str, tudo: bool):
    trabalho = saida + ".trabalho"
    if tudo and os.path.exists(trabalho):
        os.remove(trabalho)
    if not os.path.exists(trabalho) and os.path.exists(saida) and not tudo:
        shutil.copy(saida, trabalho)  # continua de um índice já publicado
    con = duckdb.connect(trabalho)
    con.execute("INSTALL fts; LOAD fts")
    if con.execute("SELECT count(*) FROM information_schema.schemata WHERE schema_name = 'fts_main_trechos'").fetchone()[0]:
        con.execute("PRAGMA drop_fts_index('trechos')")  # o índice de palavras só existe nas cópias publicadas
    con.execute("""CREATE TABLE IF NOT EXISTS documentos (arquivo VARCHAR PRIMARY KEY, area VARCHAR, empresa VARCHAR,
                   cnpj VARCHAR, ano INTEGER, tipo VARCHAR, titulo VARCHAR, url VARCHAR, paginas INTEGER, bytes BIGINT)""")
    con.execute("CREATE TABLE IF NOT EXISTS paginas (arquivo VARCHAR, pagina INTEGER, texto VARCHAR)")
    con.execute(f"""CREATE TABLE IF NOT EXISTS trechos (id BIGINT, arquivo VARCHAR, pagina INTEGER, texto VARCHAR,
                    embedding FLOAT[{DIMENSOES}])""")
    return con


def remover(con, arquivo: str):
    for tabela in ("trechos", "paginas", "documentos"):
        con.execute(f"DELETE FROM {tabela} WHERE arquivo = ?", [arquivo])


def publicar(con, saida: str):
    """Copia o trabalho, monta o índice de palavras na cópia e troca a saída; devolve a conexão reaberta."""
    trabalho = saida + ".trabalho"
    con.execute("CHECKPOINT")
    con.close()
    tmp = saida + ".tmp"
    shutil.copy(trabalho, tmp)
    pub = duckdb.connect(tmp)
    pub.execute("LOAD fts")
    # índice de palavras em português, sem acento e mantendo números (escopo 1, 2025, tCO2e)
    pub.execute("""PRAGMA create_fts_index('trechos', 'id', 'texto', stemmer = 'portuguese', stopwords = 'none',
                   ignore = '(\\.|[^a-z0-9])+', strip_accents = 1, lower = 1)""")
    documentos, trechos_ = pub.execute("SELECT (SELECT count(*) FROM documentos), (SELECT count(*) FROM trechos)").fetchone()
    pub.close()
    os.replace(tmp, saida)
    print(f"publicado: {documentos} PDFs, {trechos_} trechos em {saida}", flush=True)
    con = duckdb.connect(trabalho)
    con.execute("LOAD fts")
    return con


def do_pdf(d: dict) -> tuple[list, list]:
    """Texto por página e trechos lidos do PDF; preenche d["paginas"]."""
    paginas, pedacos = [], []
    with fitz.open(os.path.join(PDFS, d["arquivo"])) as pdf:
        d["paginas"] = pdf.page_count
        for num, pagina in enumerate(pdf, start=1):
            texto = pagina.get_text("text", sort=True)
            paginas.append((d["arquivo"], num, texto))
            pedacos += [(num, t) for t in trechos(texto)]
    return paginas, pedacos


def do_indice_local(local, d: dict) -> tuple[list, list]:
    """O mesmo, lido do índice do e5 (data/docs.duckdb): o corte dos trechos é igual, só o vetor muda."""
    linha = local.execute("SELECT paginas, bytes FROM documentos WHERE arquivo = ?", [d["arquivo"]]).fetchone()
    if not linha:
        raise SystemExit(f"{d['arquivo']} não está em {LOCAL}: rode data/indexar_dados_local.py antes")
    if linha[1] != d["bytes"]:
        raise SystemExit(f"{d['arquivo']} tem {d['bytes']} bytes e o índice local guardou {linha[1]}: refaça o local")
    d["paginas"] = linha[0]
    paginas = [(d["arquivo"], p, t) for p, t in local.execute(
        "SELECT pagina, texto FROM paginas WHERE arquivo = ? ORDER BY pagina", [d["arquivo"]]).fetchall()]
    pedacos = local.execute("SELECT pagina, texto FROM trechos WHERE arquivo = ? ORDER BY id",
                            [d["arquivo"]]).fetchall()
    return paginas, pedacos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, default=16, help="chamadas simultâneas ao Bedrock")
    ap.add_argument("--tudo", action="store_true", help="recomeça do zero")
    ap.add_argument("--limite", type=int, help="indexa só os N primeiros PDFs do documentos.csv (teste)")
    ap.add_argument("--publicar-a-cada", type=int, default=200, help="PDFs novos entre uma publicação e outra")
    ap.add_argument("--saida", default=SAIDA_PADRAO, help="banco de saída (ponha no disco local do nó; NFS trava)")
    ap.add_argument("--do-indice-local", action="store_true",
                    help=f"pega páginas e trechos de {os.path.relpath(LOCAL, RAIZ)} em vez de abrir os PDFs")
    a = ap.parse_args()

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

    local = duckdb.connect(LOCAL, read_only=True) if a.do_indice_local else None
    con = abrir_trabalho(a.saida, a.tudo)
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
    fonte = f"trechos de {os.path.relpath(LOCAL, RAIZ)}" if local else "PDFs de data/raw"
    print(f"{len(docs)} PDFs: {len(docs) - len(pendentes)} já indexados, {len(pendentes)} a indexar "
          f"({MODELO}, texto dos {fonte})", flush=True)

    bedrock = cliente(a.threads)
    proximo_id = con.execute("SELECT coalesce(max(id) + 1, 0) FROM trechos").fetchone()[0]
    inicio, novos, desde = time.time(), 0, 0
    with ThreadPoolExecutor(a.threads) as ex:
        for n, d in enumerate(pendentes, start=1):
            paginas, pedacos = do_indice_local(local, d) if local else do_pdf(d)
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
            con.execute("COMMIT")
            novos += len(pedacos)
            desde += 1
            print(f"[{n}/{len(pendentes)}] {d['arquivo']}: {d['paginas']} páginas, {len(pedacos)} trechos "
                  f"({novos / (time.time() - inicio):.0f} trechos/s)", flush=True)
            if desde >= a.publicar_a_cada:
                con, desde = publicar(con, a.saida), 0
    publicar(con, a.saida).close()
    if local:
        local.close()
    print(f"ok em {time.time() - inicio:.0f} s")


if __name__ == "__main__":
    main()

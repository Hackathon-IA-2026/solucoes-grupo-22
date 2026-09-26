"""Ponto de entrada dos servidores MCP do CoppeZIP no Amazon Bedrock AgentCore Runtime.

COPPEZIP_MCP escolhe o servidor (dados, docs ou relatorio) e COPPEZIP_BUCKET é o bucket do S3 com os dados. Na
subida, os arquivos que o servidor usa vêm do S3 para /tmp, o único lugar gravável do runtime; depois o servidor é
servido por HTTP do jeito que o AgentCore exige: 0.0.0.0:8000, caminho /mcp, sem estado entre pedidos.
  dados:     bancos/coppezip.duckdb
  docs:      bancos/docs.duckdb e modelos/multilingual-e5-large/ (embeddings das perguntas), mais a extensão fts
  relatorio: grava em /tmp e publica cada arquivo em s3://<bucket>/relatorios/ com um link assinado por 7 dias
"""
import os
import sys

import boto3

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
QUAL, BUCKET = os.environ["COPPEZIP_MCP"], os.environ["COPPEZIP_BUCKET"]
s3 = boto3.client("s3")


def baixar(chave: str, destino: str):
    if not os.path.exists(destino):
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        s3.download_file(BUCKET, chave, destino + ".parcial")
        os.replace(destino + ".parcial", destino)


def baixar_pasta(prefixo: str, destino: str):
    for pagina in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=prefixo):
        for obj in pagina.get("Contents", []):
            baixar(obj["Key"], os.path.join(destino, obj["Key"][len(prefixo):]))


sys.path.insert(0, os.path.join(RAIZ, "proper_mcps", QUAL))
os.environ["HOME"] = "/tmp"  # o DuckDB guarda as extensões em ~/.duckdb
import server  # noqa: E402

if QUAL == "dados":
    baixar("bancos/coppezip.duckdb", "/tmp/coppezip.duckdb")
    server.DB = "/tmp/coppezip.duckdb"
elif QUAL == "docs":
    baixar("bancos/docs.duckdb", "/tmp/docs.duckdb")
    baixar_pasta("modelos/multilingual-e5-large/", "/tmp/modelos/multilingual-e5-large")
    import duckdb
    duckdb.connect().execute("INSTALL fts")
    server.DB, server.PASTA_MODELO = "/tmp/docs.duckdb", "/tmp/modelos/multilingual-e5-large"
elif QUAL == "relatorio":
    server.PASTA = "/tmp/relatorios"

    def publicar(caminho: str) -> str:
        chave = "relatorios/" + os.path.basename(caminho)
        s3.upload_file(caminho, BUCKET, chave)
        return s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": chave}, ExpiresIn=7 * 86400)

    server.publicar = publicar
else:
    raise SystemExit(f"COPPEZIP_MCP inválido: {QUAL}")

server.mcp.run(transport="streamable-http", host="0.0.0.0", port=8000, stateless_http=True)

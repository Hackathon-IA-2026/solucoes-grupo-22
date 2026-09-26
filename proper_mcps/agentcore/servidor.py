"""Ponto de entrada dos servidores MCP do CoppeZIP no Amazon Bedrock AgentCore Runtime.

COPPEZIP_MCP escolhe o servidor (dados, docs ou relatorio) e COPPEZIP_BUCKET é o bucket do S3 com os dados. Na
subida, os arquivos que o servidor usa vêm do S3 para /tmp, o único lugar gravável do runtime; depois o servidor é
servido por HTTP do jeito que o AgentCore exige: 0.0.0.0:8000, caminho /mcp, sem estado entre pedidos.
  dados:     bancos/coppezip.duckdb
  docs:      bancos/docs_titan.duckdb e a extensão fts; a pergunta é embutida pelo Titan (Bedrock), então a role do
             runtime precisa de bedrock:InvokeModel (atualizar.py garante isso)
  relatorio: grava em /tmp e publica cada arquivo em s3://<bucket>/relatorios/ com um link assinado por 7 dias

Para republicar o código e testar os três runtimes: proper_mcps/agentcore/atualizar.py.
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


sys.path.insert(0, os.path.join(RAIZ, "proper_mcps", QUAL))
os.environ["HOME"] = "/tmp"  # o DuckDB guarda as extensões em ~/.duckdb
import server  # noqa: E402

if QUAL == "dados":
    baixar("bancos/coppezip.duckdb", "/tmp/coppezip.duckdb")
    server.DB = "/tmp/coppezip.duckdb"
elif QUAL == "docs":
    baixar("bancos/docs_titan.duckdb", "/tmp/docs_titan.duckdb")
    import duckdb
    duckdb.connect().execute("INSTALL fts")
    server.DB = "/tmp/docs_titan.duckdb"
    # o server.py lê a região do Bedrock do .env, que não existe aqui: o cliente vai pronto, na região do runtime
    server._bedrock = boto3.client("bedrock-runtime")
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

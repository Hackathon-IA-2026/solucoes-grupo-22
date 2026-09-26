#!/bin/bash
# Monta o pacote dos MCP do CoppeZIP (dados, docs, relatorio) para o Bedrock AgentCore Runtime (Python 3.12 em ARM64) e envia ao S3.
# Uso: proper_mcps/agentcore/empacotar.sh <bucket>        ex.: coppezip-dados-139382521595
# Resultado: s3://<bucket>/codigo/coppezip-mcp.zip, com as bibliotecas para ARM e o código na mesma estrutura do
# repositório (proper_mcps/agentcore/servidor.py é o ponto de entrada).
set -euo pipefail
cd "$(dirname "$0")/../.."; B=$1
D=.runtime/agentcore; rm -rf "${D:?}/pacote"; mkdir -p "$D/pacote/proper_mcps"
.runtime/venv/bin/pip install -q --target "$D/pacote" --platform manylinux_2_28_aarch64 --platform manylinux_2_17_aarch64 --platform manylinux2014_aarch64 --python-version 3.12 \
  --implementation cp --only-binary=:all: duckdb==1.5.5 mcp==2.2.0 fastembed==0.8.1 boto3
cp -r proper_mcps/agentcore proper_mcps/dados proper_mcps/docs proper_mcps/relatorio "$D/pacote/proper_mcps/"
rm -rf "$D"/pacote/proper_mcps/*/__pycache__ "$D"/pacote/proper_mcps/*/test_*.py "$D"/pacote/proper_mcps/agentcore/{empacotar.sh,cdk_app.py}
(cd "$D/pacote" && rm -f ../coppezip-mcp.zip && zip -qr ../coppezip-mcp.zip .)
ls -lh "$D/coppezip-mcp.zip"
aws s3 cp "$D/coppezip-mcp.zip" "s3://$B/codigo/coppezip-mcp.zip"

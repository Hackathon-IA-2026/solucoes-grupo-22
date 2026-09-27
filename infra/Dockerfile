# Imagem do chat EnergyNexus: o LibreChat deste fork (tema, logo, painel de PDF e as abas Painel, Busca, Grafo e
# Timeline) mais tudo o que os servidores MCP de stdio precisam para rodar como processo filho dele.
#
# Por que uma imagem só, e não uma por processo: os quatro MCP do librechat.yaml são `type: stdio`, ou seja, o próprio
# LibreChat os executa como filhos — eles têm de estar no mesmo sistema de arquivos que ele. O mesmo vale para o
# serviço da aba Busca, que o busca.py publica em 127.0.0.1 (proper_mcps/docs/busca.py). O MongoDB e o Meilisearch,
# que falam por TCP, ficam em contêineres próprios (infra/compose.yaml).
#
# Base Debian x86_64 de propósito: o pdflatex do relatório vem do TinyTeX, cujo caminho
# .runtime/tinytex/bin/x86_64-linux está fixo em proper_mcps/relatorio/server.py. Numa instância ARM (Graviton) o
# relatório em PDF não compila.
#
# trixie e não bookworm por causa do Python: o `numpy==2.5.3` de proper_mcps/requirements.txt exige 3.12 ou mais, e o
# bookworm só traz 3.11 (o pip morre com "No matching distribution found for numpy==2.5.3"). O trixie traz 3.13.
FROM node:24.16.0-trixie

# python3-venv: o venv das ferramentas MCP. As demais são do TinyTeX (perl, fontconfig) e do npm ci (git).
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-venv python3-dev build-essential \
      perl fontconfig ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

# Interface: é este código que tem as telas do fork, então o bundle é construído aqui e não vem do upstream. O
# `npm run frontend` encadeia data-provider, data-schemas, api, client-package e o vite build do client; o vite pede
# NODE_OPTIONS=--max-old-space-size=8192 (está no script do client), daí a instância de 16 GB.
RUN npm ci --no-audit --no-fund && npm run frontend

# Ferramentas MCP: o mesmo venv e os mesmos pinos do instalar.sh. Fica em /opt/venv, fora de .runtime/, porque
# .runtime/ recebe montagens de estado gravável no compose.
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -q -r proper_mcps/requirements.txt

# Extensão fts do DuckDB, a do BM25. O `_con()` de proper_mcps/docs/server.py faz `LOAD fts` em cada conexão, e `LOAD`
# não baixa nada: sem instalar aqui, a primeira consulta da aba Busca morre com `Extension "fts" not found`. Baixar
# agora, na construção, também evita depender da internet em tempo de consulta.
RUN /opt/venv/bin/python -c "import duckdb; duckdb.connect().execute('INSTALL fts')"

# TinyTeX + os seis pacotes que o modelo do relatório usa e o TinyTeX-1 não traz (mesma lista do instalar.sh).
# O caminho é o que proper_mcps/relatorio/server.py espera: <RAIZ>/.runtime/tinytex/bin/x86_64-linux.
ARG TINYTEX=v2026.09
RUN mkdir -p /app/.runtime/tinytex \
    && curl -fL --retry 3 -o /tmp/tinytex.tar.xz \
       "https://github.com/rstudio/tinytex-releases/releases/download/${TINYTEX}/TinyTeX-1-linux-x86_64-${TINYTEX}.tar.xz" \
    && tar -xJf /tmp/tinytex.tar.xz -C /app/.runtime/tinytex --strip-components 1 \
    && rm /tmp/tinytex.tar.xz \
    && /app/.runtime/tinytex/bin/x86_64-linux/tlmgr install \
       babel-portuges caption enumitem fancyhdr lastpage parskip

# O que o iniciar.sh exporta e o .env não tem: sem estas três os `${VAR}` do mcpServers não resolvem e os quatro
# servidores MCP não sobem.
ENV ENERGYNEXUS_RAIZ=/app \
    ENERGYNEXUS_PYTHON=/opt/venv/bin/python \
    DEPLOYMENT_SKILLS_DIR=/app/proper_skills \
    NODE_ENV=production

EXPOSE 3080
ENTRYPOINT ["/app/infra/entrada.sh"]

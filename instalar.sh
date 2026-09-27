#!/bin/bash
# Instala o EnergyNexus nesta máquina (uma vez): .env com segredos novos, Node, MongoDB, Meilisearch e o TinyTeX (LaTeX
# do relatório em PDF) em .runtime/, as dependências e a interface do LibreChat (npm), e o Python das ferramentas MCP.
set -euo pipefail
cd "$(dirname "$0")"; RAIZ=$PWD; R=$RAIZ/.runtime
mkdir -p "$R"/{bin,dl,run,logs,relatorios,mongo,meili}

if [ ! -f .env ]; then
  hex() { openssl rand -hex "$1"; }
  sed -e "s/^CREDS_KEY=$/CREDS_KEY=$(hex 32)/" -e "s/^CREDS_IV=$/CREDS_IV=$(hex 16)/" \
      -e "s/^JWT_SECRET=$/JWT_SECRET=$(hex 32)/" -e "s/^JWT_REFRESH_SECRET=$/JWT_REFRESH_SECRET=$(hex 32)/" \
      -e "s/^MEILI_MASTER_KEY=$/MEILI_MASTER_KEY=$(hex 16)/" -e "s/^VLLM_API_KEY=$/VLLM_API_KEY=$(hex 24)/" .env.example > .env
  chmod 600 .env; echo ".env criado com segredos novos"
fi

NODE=v24.16.0; MONGO=8.0.20; MEILI=v1.35.1; TINYTEX=v2026.09; UBUNTU=ubuntu$(. /etc/os-release; echo "${VERSION_ID/./}")
baixar() { [ -s "$R/dl/$2" ] || curl -fL --retry 3 -o "$R/dl/$2" "$1"; }
baixar "https://nodejs.org/dist/$NODE/node-$NODE-linux-x64.tar.xz" "node-$NODE-linux-x64.tar.xz"
baixar "https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-$UBUNTU-$MONGO.tgz" "mongodb-linux-x86_64-$UBUNTU-$MONGO.tgz"
baixar "https://github.com/meilisearch/meilisearch/releases/download/$MEILI/meilisearch-linux-amd64" meilisearch
baixar "https://github.com/rstudio/tinytex-releases/releases/download/$TINYTEX/TinyTeX-1-linux-x86_64-$TINYTEX.tar.xz" \
  "tinytex-$TINYTEX.tar.xz"
[ -d "$R/node" ] || { mkdir "$R/node" && tar -xJf "$R/dl/node-$NODE-linux-x64.tar.xz" -C "$R/node" --strip-components 1; }
[ -d "$R/mongodb" ] || { mkdir "$R/mongodb" && tar -xzf "$R/dl/mongodb-linux-x86_64-$UBUNTU-$MONGO.tgz" -C "$R/mongodb" --strip-components 1; }
[ -d "$R/tinytex" ] || { mkdir "$R/tinytex" && tar -xJf "$R/dl/tinytex-$TINYTEX.tar.xz" -C "$R/tinytex" --strip-components 1; }
# pacotes que o modelo do relatório (proper_mcps/relatorio/modelo/main.tex) usa e o TinyTeX-1 não traz
"$R/tinytex/bin/x86_64-linux/tlmgr" install babel-portuges caption enumitem fancyhdr lastpage parskip > /dev/null
install -m 755 "$R/dl/meilisearch" "$R/bin/meilisearch"
ln -sf "$R"/node/bin/* "$R"/mongodb/bin/* "$R/bin/"
export PATH=$R/bin:$PATH

npm ci --no-audit --no-fund
npm run frontend

[ -x "$R/venv/bin/python" ] || python3 -m venv "$R/venv"
"$R/venv/bin/pip" install -q -r proper_mcps/requirements.txt
echo "instalado. Ponha os dados em data/ (veja o README) e rode ./iniciar.sh"

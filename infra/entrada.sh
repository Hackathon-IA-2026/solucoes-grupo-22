#!/bin/bash
# Partida do contêiner do chat. É o iniciar.sh da nuvem: aqui o MongoDB e o Meilisearch são contêineres vizinhos
# (infra/compose.yaml), então sobra o que só pode viver junto do LibreChat — as pastas graváveis de .runtime/, os dois
# symlinks que fazem o PDF e a Timeline aparecerem em /relatorios/ e /linha_do_tempo/, o serviço da aba Busca (que
# escuta em 127.0.0.1) e o próprio Node.
set -euo pipefail
cd /app

mkdir -p .runtime/{relatorios,linha_do_tempo,logs}

# O Node serve client/public/assets na raiz do site: é por estes dois symlinks que /relatorios/<arquivo>.pdf (do
# gerar_relatorio e das telas do placar) e /linha_do_tempo/<empresa>.json chegam ao navegador.
ln -sfn /app/.runtime/relatorios client/public/assets/relatorios
ln -sfn /app/.runtime/linha_do_tempo client/public/assets/linha_do_tempo

# Na AWS não há vLLM, então o perfil padrão do librechat.yaml (que aponta para ele) não serve: ajustar_yaml.py grava
# uma cópia com o perfil do Bedrock como padrão e sem o endpoint do vLLM. CONFIG_PATH manda o LibreChat ler essa cópia.
"$ENERGYNEXUS_PYTHON" infra/ajustar_yaml.py librechat.yaml .runtime/librechat.aws.yaml
export CONFIG_PATH=/app/.runtime/librechat.aws.yaml

# O .env que o contêiner não tem: aqui a configuração chega pelo `env_file` do compose, que virou ambiente e não
# arquivo. Só que o `_embed` de proper_mcps/docs/server.py lê a região do Bedrock de <RAIZ>/.env na mão (o LibreChat
# sobe os MCP sem as variáveis do .env, e é assim que o servidor de documentos a descobre). Sem este arquivo a busca
# semântica da aba Busca morre com FileNotFoundError. Vai só a região, que não é segredo — os segredos ficam no
# ambiente, fora do disco do contêiner.
printf 'BEDROCK_AWS_DEFAULT_REGION=%s\n' "$BEDROCK_AWS_DEFAULT_REGION" > /app/.env

# Dados da aba Timeline: o mesmo JSON por empresa que o site estático usa. Depende de data/energynexus.duckdb e
# data/docs.duckdb; sem eles a aba fica sem dados e o resto do chat segue igual (é o que o iniciar.sh também faz).
"$ENERGYNEXUS_PYTHON" data/linha_do_tempo.py || echo "aviso: a aba Timeline ficou sem dados novos (erro acima)"

# Serviço das abas Busca e Timeline. Escuta em 127.0.0.1:$BUSCA_PORTA e a rota /api/busca do LibreChat repassa, por
# isso ele roda neste contêiner e não num vizinho. Precisa dos três bancos; sem eles as duas abas ficam fora do ar e o
# chat e os quatro MCP continuam funcionando.
if [ -s data/docs_titan.duckdb ] && [ -s data/docs.duckdb ] && [ -s data/energynexus.duckdb ]; then
  "$ENERGYNEXUS_PYTHON" proper_mcps/docs/busca.py --porta "$BUSCA_PORTA" >> .runtime/logs/busca.log 2>&1 &
  echo "serviço da Busca subindo na porta $BUSCA_PORTA (log em .runtime/logs/busca.log)"
else
  echo "aviso: sem data/docs_titan.duckdb, data/docs.duckdb ou data/energynexus.duckdb — as abas Busca e Timeline" \
       "ficam fora do ar; o chat e os MCP não dependem deles"
fi

echo "EnergyNexus: subindo o LibreChat em $HOST:$PORT"
exec npm run backend

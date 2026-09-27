#!/bin/bash
# Sobe MongoDB, Meilisearch, a busca nos PDFs (aba Busca) e o LibreChat (que lê librechat.yaml e .env desta pasta,
# inicia as ferramentas de proper_mcps/ e carrega as skills de proper_skills/). O modelo é separado: ./vllm.sh ou o
# Bedrock.
set -euo pipefail
cd "$(dirname "$0")"; RAIZ=$PWD; R=$RAIZ/.runtime
set -a; . ./.env; set +a
export PATH=$R/bin:$PATH COPPEZIP_RAIZ=$RAIZ COPPEZIP_PYTHON=$R/venv/bin/python DEPLOYMENT_SKILLS_DIR=$RAIZ/proper_skills
MONGO_PORTA=${MONGO_URI##*:}; MONGO_PORTA=${MONGO_PORTA%%/*}; MEILI_PORTA=${MEILI_HOST##*:}
aberta() { (echo > "/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

aberta "$MONGO_PORTA" || mongod --dbpath "$R/mongo" --bind_ip 127.0.0.1 --port "$MONGO_PORTA" --fork \
  --logpath "$R/logs/mongod.log" --pidfilepath "$R/run/mongod.pid" > /dev/null
# o PID gravado é o do próprio processo (bash troca de programa com exec), para o parar.sh
aberta "$MEILI_PORTA" || nohup bash -c 'echo $$ > "$0"; exec setsid meilisearch "$@"' "$R/run/meili.pid" \
  --db-path "$R/meili" --http-addr "127.0.0.1:$MEILI_PORTA" --master-key "$MEILI_MASTER_KEY" --no-analytics \
  --env production > "$R/logs/meili.log" 2>&1 < /dev/null &
# abas Busca e Timeline: serviço HTTP sobre data/docs_titan.duckdb e data/coppezip.duckdb que a rota /api/busca repassa
aberta "$BUSCA_PORTA" || nohup bash -c 'echo $$ > "$0"; exec setsid "$@"' "$R/run/busca.pid" \
  "$R/venv/bin/python" proper_mcps/docs/busca.py --porta "$BUSCA_PORTA" > "$R/logs/busca.log" 2>&1 < /dev/null &
# relatórios do gerar_relatorio: o LibreChat serve client/public/assets na raiz do site (/relatorios/...)
ln -sfn "$R/relatorios" client/public/assets/relatorios
aberta "$PORT" || nohup bash -c 'echo $$ > "$0"; exec setsid npm run backend' "$R/run/librechat.pid" \
  > "$R/logs/librechat.log" 2>&1 < /dev/null &
for _ in $(seq 90); do
  curl -sf -o /dev/null "http://127.0.0.1:$PORT/health" && { echo "CoppeZIP em http://localhost:$PORT"; exit 0; }
  sleep 2
done
echo "o LibreChat não respondeu; veja $R/logs/librechat.log"; exit 1

#!/bin/bash
# Para o LibreChat, a busca nos PDFs, o Meilisearch e o MongoDB que o iniciar.sh subiu (pelos PIDs em .runtime/run).
cd "$(dirname "$0")"; R=$PWD/.runtime
for s in librechat busca meili mongod; do
  f=$R/run/$s.pid
  [ -f "$f" ] || continue
  pid=$(cat "$f")
  kill -TERM -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null   # o grupo inteiro (npm, sh, node)
  while kill -0 "$pid" 2>/dev/null; do sleep 1; done               # espera sair (o MongoDB fecha os arquivos)
  rm -f "$f"; echo "$s parado"
done

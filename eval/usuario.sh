#!/bin/bash
# Cria no LibreChat o usuário de teste teste-<persona>@coppezip.local (usado por eval/chat.py e eval/regressao.py).
# A senha é gerada uma vez e fica em .runtime/run/usuarios.json. Uso: eval/usuario.sh [persona]   (padrão: teste)
set -euo pipefail
cd "$(dirname "$0")/.."; R=$PWD/.runtime; P=${1:-teste}
export PATH=$R/bin:$PATH
[ -f "$R/run/usuarios.json" ] || { umask 077; printf '{"senha": "%s"}\n' "$(openssl rand -hex 16)" > "$R/run/usuarios.json"; }
SENHA=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["senha"])' "$R/run/usuarios.json")
npm run -s create-user -- "teste-$P@coppezip.local" "Teste $P" "teste-$P" "$SENHA" --email-verified=true

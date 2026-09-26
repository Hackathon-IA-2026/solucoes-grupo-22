#!/bin/bash
# Serve o modelo próprio com o vLLM nesta máquina (GPU de 32 GB ou mais): instala o vLLM e baixa os pesos na primeira
# vez (.runtime/vllm e .runtime/hf) e sobe o servidor na porta VLLM_PORTA, exigindo a chave VLLM_API_KEY do .env.
# O LibreChat encontra o modelo em VLLM_BASE_URL (mude no .env se o vLLM rodar em outra máquina).
set -euo pipefail
cd "$(dirname "$0")"; R=$PWD/.runtime
set -a; . ./.env; set +a
[ -x "$R/vllm/bin/vllm" ] || { python3 -m venv "$R/vllm" && "$R/vllm/bin/pip" install -q vllm; }
export HF_HOME=$R/hf VLLM_API_KEY
"$R/vllm/bin/hf" download "$VLLM_MODELO" > /dev/null
# o FlashInfer compila com o nvcc do sistema, que pode não suportar GPUs novas: amostragem e atenção pelo Triton
export VLLM_USE_FLASHINFER_SAMPLER=0
exec "$R/vllm/bin/vllm" serve "$VLLM_MODELO" --host 0.0.0.0 --port "$VLLM_PORTA" --served-model-name qwen3.8-27b \
  --max-model-len 262144 --gpu-memory-utilization 0.92 --kv-cache-dtype fp8 --attention-backend TRITON_ATTN \
  --max-num-seqs 16 --limit-mm-per-prompt '{"image": 0, "video": 0}' \
  --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3

"""Fumaça: sobe as ferramentas, imprime o conjunto e roda UMA pergunta no modelo pedido.

    python testar_laco.py qwen "Qual foi a receita líquida da Taesa em 2025?"
    python testar_laco.py opus5 "..."
"""

from __future__ import annotations

import json
import sys

import ferramentas
import laco


def fazer_adaptador(qual: str):
    if qual in ("qwen", "vllm"):
        return laco.OpenAI()
    if qual in ("opus5", "opus", "bedrock"):
        return laco.Bedrock("us.anthropic.claude-opus-5")
    raise SystemExit(f"modelo desconhecido: {qual}")


if __name__ == "__main__":
    qual = sys.argv[1] if len(sys.argv) > 1 else "qwen"
    pergunta = sys.argv[2] if len(sys.argv) > 2 else "Quantas empresas têm relatório indexado no Placar da Transição?"
    caixa = ferramentas.Caixa(log=lambda t: print(t, flush=True))
    print(json.dumps(caixa.resumo(), ensure_ascii=False, indent=2))
    print("=" * 80)
    print(caixa.prompt_sistema()[-2500:])
    print("=" * 80, flush=True)
    try:
        saida = laco.rodar(fazer_adaptador(qual), caixa, pergunta, max_passos=40,
                           log=lambda t: print(t, flush=True))
    finally:
        caixa.fechar()
    print("=" * 80)
    print(saida["resposta"])
    print("=" * 80)
    print(json.dumps({k: v for k, v in saida.items() if k not in ("resposta", "trilha")},
                     ensure_ascii=False, indent=2))

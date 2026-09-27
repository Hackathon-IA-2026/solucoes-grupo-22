"""Sonda os dois lados antes de gastar o conjunto: vLLM (modelos e contexto) e Bedrock (acesso ao Opus 5)."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request

import comum


def sondar_vllm(base: str | None = None) -> dict:
    env = comum.ler_env()
    base = (base or env["VLLM_BASE_URL"]).rstrip("/")
    chave = env["VLLM_API_KEY"]
    saida: dict = {"base_url": base}
    req = urllib.request.Request(base + "/models", headers={"Authorization": "Bearer " + chave})
    try:
        dados = json.load(urllib.request.urlopen(req, timeout=30))
        saida["modelos"] = [
            {"id": m.get("id"), "max_model_len": m.get("max_model_len"), "root": m.get("root")}
            for m in dados.get("data", [])
        ]
    except Exception as erro:  # noqa: BLE001
        saida["erro_modelos"] = f"{type(erro).__name__}: {erro}"
        return saida
    # chamada mínima com ferramenta, para confirmar tool calling
    corpo = {
        "model": saida["modelos"][0]["id"],
        "messages": [{"role": "user", "content": "Chame a ferramenta somar com a=2 e b=3."}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "somar",
                    "description": "Soma dois números",
                    "parameters": {
                        "type": "object",
                        "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                        "required": ["a", "b"],
                    },
                },
            }
        ],
        "max_tokens": 2000,
        "temperature": 0.0,
    }
    req = urllib.request.Request(
        base + "/chat/completions",
        data=json.dumps(corpo).encode(),
        headers={"Authorization": "Bearer " + chave, "Content-Type": "application/json"},
    )
    t0 = time.time()
    try:
        resp = json.load(urllib.request.urlopen(req, timeout=180))
        msg = resp["choices"][0]["message"]
        saida["tool_calls"] = msg.get("tool_calls")
        saida["texto"] = (msg.get("content") or "")[-300:]
        saida["uso"] = resp.get("usage")
        saida["segundos"] = round(time.time() - t0, 1)
    except urllib.error.HTTPError as erro:
        saida["erro_chat"] = f"HTTP {erro.code}: {erro.read()[:500].decode('utf-8', 'replace')}"
    except Exception as erro:  # noqa: BLE001
        saida["erro_chat"] = f"{type(erro).__name__}: {erro}"
    return saida


MODELOS_CLAUDE = [
    "us.anthropic.claude-opus-5",
    "us.anthropic.claude-opus-4-8",
    "us.anthropic.claude-opus-4-7",
    "us.anthropic.claude-opus-4-6-v1",
    "us.anthropic.claude-sonnet-5",
]


def sondar_bedrock(regioes: list[str] | None = None, modelos: list[str] | None = None) -> dict:
    import boto3

    env = comum.ler_env()
    regioes = regioes or [env.get("BEDROCK_AWS_DEFAULT_REGION", "us-east-1"), "us-west-2"]
    modelos = modelos or MODELOS_CLAUDE
    saida: dict = {}
    for regiao in dict.fromkeys(regioes):
        cliente = boto3.client("bedrock-runtime", region_name=regiao)
        saida[regiao] = {}
        for modelo in modelos:
            t0 = time.time()
            try:
                # temperature é "deprecated" nos Claude mais novos do Bedrock: só maxTokens
                resp = cliente.converse(
                    modelId=modelo,
                    messages=[{"role": "user", "content": [{"text": "Responda apenas: ok"}]}],
                    inferenceConfig={"maxTokens": 64},
                )
                saida[regiao][modelo] = {
                    "ok": True,
                    "texto": resp["output"]["message"]["content"][0].get("text", "")[:40],
                    "uso": resp.get("usage"),
                    "segundos": round(time.time() - t0, 1),
                }
            except Exception as erro:  # noqa: BLE001
                saida[regiao][modelo] = {"ok": False, "erro": f"{type(erro).__name__}: {str(erro)[:200]}"}
    return saida


if __name__ == "__main__":
    alvo = sys.argv[1] if len(sys.argv) > 1 else "tudo"
    resultado = {}
    if alvo in ("tudo", "vllm"):
        resultado["vllm"] = sondar_vllm()
    if alvo in ("tudo", "bedrock"):
        resultado["bedrock"] = sondar_bedrock()
    print(json.dumps(resultado, ensure_ascii=False, indent=2, default=str))

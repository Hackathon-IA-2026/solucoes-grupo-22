"""Mede o servidor vLLM que a avaliação usa: contexto efetivo, tokens/s e memória da GPU.

O contexto é medido de verdade: um prompt longo sintético é enviado com um pedido cujo gabarito está ENTERRADO no
meio do texto (agulha no palheiro), para separar "aceita o prompt" de "usa o prompt".

    python medir_vllm.py --alvos 4000 64000 200000 250000 260000
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request

import comum

RECHEIO = (
    "O Sistema Interligado Nacional reúne quatro subsistemas: Sudeste/Centro-Oeste, Sul, Nordeste e Norte. "
    "A operação é coordenada pelo Operador Nacional do Sistema Elétrico e a regulação cabe à ANEEL. "
    "As demonstrações financeiras das companhias abertas são entregues à CVM em formulários DFP e ITR. "
)


def _pedir(base: str, chave: str, corpo: dict, prazo: float = 1800.0) -> dict:
    pedido = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=json.dumps(corpo, ensure_ascii=False).encode(),
        headers={"Authorization": "Bearer " + chave, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(pedido, timeout=prazo) as resposta:
        return json.loads(resposta.read().decode("utf-8", "replace"))


def gpu(host: str) -> dict:
    try:
        saida = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", host, "--",
             "nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free --format=csv,noheader"],
            capture_output=True, text=True, timeout=40, check=True).stdout.strip()
        nome, total, usado, livre = [p.strip() for p in saida.split(",")]
        return {"host": host, "gpu": nome, "memoria_total": total, "memoria_usada": usado, "memoria_livre": livre}
    except Exception as erro:  # noqa: BLE001
        return {"host": host, "erro": f"{type(erro).__name__}: {erro}"}


def argumentos_servidor(host: str) -> str:
    try:
        return subprocess.run(
            ["ssh", "-o", "BatchMode=yes", host, "--",
             "ps -o args= -u $(id -u) | grep 'vllm serve' | grep -v grep | head -1"],
            capture_output=True, text=True, timeout=40).stdout.strip()
    except Exception as erro:  # noqa: BLE001
        return f"(não consegui ler: {type(erro).__name__}: {erro})"


def medir_contexto(base: str, chave: str, modelo: str, alvo_tokens: int) -> dict:
    """Agulha no palheiro: a senha fica no meio de um prompt de ~alvo_tokens e o modelo tem de devolvê-la."""
    # ~1 token por 3,2 caracteres em português com este tokenizador (medido)
    pedacos = max(1, int(alvo_tokens * 3.2 / len(RECHEIO)))
    metade = pedacos // 2
    agulha = "\n\nATENÇÃO, DADO IMPORTANTE: o código de verificação do relatório é XK-4713-QRZ.\n\n"
    palheiro = RECHEIO * metade + agulha + RECHEIO * (pedacos - metade)
    corpo = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": "Responda em português, em uma linha."},
            {"role": "user", "content": palheiro + "\n\nQual é o código de verificação do relatório citado no texto acima?"},
        ],
        "max_tokens": 200,
        "temperature": 0.0,
    }
    t0 = time.time()
    try:
        dados = _pedir(base, chave, corpo)
    except urllib.error.HTTPError as erro:
        return {"alvo_tokens": alvo_tokens, "ok": False,
                "erro": f"HTTP {erro.code}: {erro.read()[:300].decode('utf-8', 'replace')}"}
    except Exception as erro:  # noqa: BLE001
        return {"alvo_tokens": alvo_tokens, "ok": False, "erro": f"{type(erro).__name__}: {erro}"}
    dt = time.time() - t0
    uso = dados.get("usage") or {}
    texto = (dados["choices"][0]["message"].get("content") or "")
    return {
        "alvo_tokens": alvo_tokens, "ok": True,
        "tokens_prompt": uso.get("prompt_tokens"), "tokens_saida": uso.get("completion_tokens"),
        "segundos": round(dt, 1),
        "tokens_saida_por_s": round((uso.get("completion_tokens") or 0) / dt, 1) if dt else None,
        "prefill_tokens_por_s": round((uso.get("prompt_tokens") or 0) / dt, 0) if dt else None,
        "achou_agulha": "XK-4713-QRZ" in texto,
        "resposta": texto[:200],
    }


def medir_geracao(base: str, chave: str, modelo: str, tokens: int = 600) -> dict:
    corpo = {
        "model": modelo,
        "messages": [{"role": "user", "content": "Explique em detalhe como funciona o despacho hidrotérmico "
                                                 "brasileiro. Escreva um texto longo."}],
        "max_tokens": tokens, "temperature": 0.0,
    }
    t0 = time.time()
    dados = _pedir(base, chave, corpo)
    dt = time.time() - t0
    uso = dados.get("usage") or {}
    return {"tokens_saida": uso.get("completion_tokens"), "segundos": round(dt, 1),
            "tokens_por_s": round((uso.get("completion_tokens") or 0) / dt, 1) if dt else None}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--alvos", type=int, nargs="*", default=[4000, 64000, 200000, 250000, 260000])
    ap.add_argument("--host", default="xingu")
    args = ap.parse_args()
    env = comum.ler_env()
    base, chave = env["VLLM_BASE_URL"], env["VLLM_API_KEY"]
    modelos = json.load(urllib.request.urlopen(urllib.request.Request(
        base.rstrip("/") + "/models", headers={"Authorization": "Bearer " + chave}), timeout=30))
    saida = {
        "base_url": base,
        "modelos": [{"id": m.get("id"), "root": m.get("root"), "max_model_len": m.get("max_model_len")}
                    for m in modelos.get("data", [])],
        "gpu": gpu(args.host),
        "argumentos_vllm": argumentos_servidor(args.host),
        "geracao_curta": medir_geracao(base, chave, "qwen3.8-27b"),
        "contexto": [medir_contexto(base, chave, "qwen3.8-27b", a) for a in args.alvos],
    }
    caminho = comum.SAIDA / "medida_vllm.json"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(saida, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(saida, ensure_ascii=False, indent=2))
    print("gravado em", caminho)

"""O laço de ferramentas, igual para os dois modelos: mesmo prompt, mesmas ferramentas, mesmo limite de passos.

Dois adaptadores só na camada da API:
  - `Bedrock`: API Converse (a mesma que o endpoint bedrock do LibreChat usa). `temperature` não entra: os Claude
    novos do Bedrock recusam com "`temperature` is deprecated for this model" (medido em sondar.py).
  - `OpenAI`: /v1/chat/completions do vLLM (o endpoint custom "EnergyNexus" do librechat.yaml).

Limite de passos: recursionLimit do librechat.yaml (300 passos = ~150 chamadas de ferramenta; cada chamada gasta 2).
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

import comum


class Uso:
    def __init__(self):
        self.entrada = 0
        self.saida = 0
        self.cache_leitura = 0
        self.cache_escrita = 0

    def somar(self, entrada=0, saida=0, cache_leitura=0, cache_escrita=0):
        self.entrada += entrada or 0
        self.saida += saida or 0
        self.cache_leitura += cache_leitura or 0
        self.cache_escrita += cache_escrita or 0

    def dict(self):
        return {"tokens_entrada": self.entrada, "tokens_saida": self.saida,
                "tokens_cache_leitura": self.cache_leitura, "tokens_cache_escrita": self.cache_escrita}


# --- adaptadores -------------------------------------------------------------
class Bedrock:
    """API Converse do Bedrock, com o mesmo maxOutputTokens do perfil do librechat.yaml."""

    familia = "bedrock"

    def __init__(self, modelo: str, regiao: str | None = None, max_saida: int = 32000):
        import boto3
        from botocore.config import Config

        env = comum.ler_env()
        self.modelo = modelo
        self.regiao = regiao or env.get("BEDROCK_AWS_DEFAULT_REGION", "us-east-1")
        self.max_saida = max_saida
        self.cliente = boto3.client(
            "bedrock-runtime",
            region_name=self.regiao,
            config=Config(read_timeout=900, connect_timeout=30, retries={"max_attempts": 6, "mode": "adaptive"}),
        )

    def ferramentas(self, definicoes: list[dict]) -> dict:
        return {"tools": [
            {"toolSpec": {"name": d["nome"], "description": d["descricao"] or d["nome"],
                          "inputSchema": {"json": d["esquema"]}}}
            for d in definicoes
        ]}

    def chamar(self, sistema: str, mensagens: list[dict], definicoes: list[dict]) -> dict:
        resposta = self.cliente.converse(
            modelId=self.modelo,
            system=[{"text": sistema}],
            messages=mensagens,
            inferenceConfig={"maxTokens": self.max_saida},
            toolConfig=self.ferramentas(definicoes),
        )
        uso = resposta.get("usage") or {}
        saida = resposta["output"]["message"]
        texto = "".join(b.get("text", "") for b in saida.get("content", []) if "text" in b)
        chamadas = [
            {"id": b["toolUse"]["toolUseId"], "nome": b["toolUse"]["name"], "argumentos": b["toolUse"]["input"] or {}}
            for b in saida.get("content", []) if "toolUse" in b
        ]
        return {
            "texto": texto, "chamadas": chamadas, "bruto": saida,
            "parada": resposta.get("stopReason"),
            "uso": {"entrada": uso.get("inputTokens"), "saida": uso.get("outputTokens"),
                    "cache_leitura": uso.get("cacheReadInputTokens"), "cache_escrita": uso.get("cacheWriteInputTokens")},
        }

    def mensagem_usuario(self, texto: str) -> dict:
        return {"role": "user", "content": [{"text": texto}]}

    def mensagem_assistente(self, passo: dict) -> dict:
        return {"role": "assistant", "content": passo["bruto"]["content"]}

    def mensagem_ferramentas(self, resultados: list[dict]) -> dict:
        return {"role": "user", "content": [
            {"toolResult": {"toolUseId": r["id"], "content": [{"text": r["texto"][:180000] or "(vazio)"}],
                            **({"status": "error"} if r["erro"] else {})}}
            for r in resultados
        ]}


class OpenAI:
    """/v1/chat/completions do vLLM: o endpoint custom "EnergyNexus" do librechat.yaml."""

    familia = "openai"

    def __init__(self, base_url: str | None = None, modelo: str | None = None, max_saida: int = 32000,
                 chave: str | None = None):
        env = comum.ler_env()
        self.base = (base_url or env["VLLM_BASE_URL"]).rstrip("/")
        self.chave = chave or env["VLLM_API_KEY"]
        self.modelo = modelo or "qwen3.8-27b"
        self.max_saida = max_saida

    def ferramentas(self, definicoes: list[dict]) -> list[dict]:
        return [
            {"type": "function", "function": {"name": d["nome"], "description": d["descricao"] or d["nome"],
                                              "parameters": d["esquema"]}}
            for d in definicoes
        ]

    def chamar(self, sistema: str, mensagens: list[dict], definicoes: list[dict]) -> dict:
        corpo = {
            "model": self.modelo,
            "messages": [{"role": "system", "content": sistema}] + mensagens,
            "tools": self.ferramentas(definicoes),
            "tool_choice": "auto",
            "max_tokens": self.max_saida,
            "temperature": 0.0,
        }
        pedido = urllib.request.Request(
            self.base + "/chat/completions", data=json.dumps(corpo, ensure_ascii=False).encode(),
            headers={"Authorization": "Bearer " + self.chave, "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(pedido, timeout=1800) as resposta:
                dados = json.loads(resposta.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as erro:
            corpo_erro = erro.read()[:800].decode("utf-8", "replace")
            raise RuntimeError(f"HTTP {erro.code} do vLLM: {corpo_erro}") from erro
        escolha = dados["choices"][0]
        msg = escolha["message"]
        uso = dados.get("usage") or {}
        chamadas = []
        for chamada in msg.get("tool_calls") or []:
            bruto = chamada["function"].get("arguments") or "{}"
            try:
                argumentos = json.loads(bruto) if isinstance(bruto, str) else bruto
            except Exception:  # noqa: BLE001
                argumentos = {"__erro_json__": bruto[:500]}
            chamadas.append({"id": chamada.get("id") or f"call_{len(chamadas)}",
                             "nome": chamada["function"]["name"], "argumentos": argumentos})
        return {
            "texto": msg.get("content") or "", "chamadas": chamadas, "bruto": msg,
            "parada": escolha.get("finish_reason"),
            "uso": {"entrada": uso.get("prompt_tokens"), "saida": uso.get("completion_tokens"),
                    "cache_leitura": 0, "cache_escrita": 0},
            "raciocinio": len((msg.get("reasoning_content") or "")),
        }

    def mensagem_usuario(self, texto: str) -> dict:
        return {"role": "user", "content": texto}

    def mensagem_assistente(self, passo: dict) -> dict:
        msg = {"role": "assistant", "content": passo["bruto"].get("content") or ""}
        if passo["bruto"].get("tool_calls"):
            msg["tool_calls"] = passo["bruto"]["tool_calls"]
        return msg

    def mensagem_ferramentas(self, resultados: list[dict]) -> list[dict]:
        return [{"role": "tool", "tool_call_id": r["id"], "content": (r["texto"][:180000] or "(vazio)")}
                for r in resultados]


# --- laço --------------------------------------------------------------------
def rodar(adaptador, caixa, pergunta: str, max_passos: int = 300, log=None) -> dict:
    """Uma conversa de um turno do usuário com o laço de ferramentas até a resposta final."""
    log = log or (lambda t: None)
    sistema = caixa.prompt_sistema()
    mensagens = [adaptador.mensagem_usuario(pergunta)]
    uso, trilha = Uso(), []
    passos = 0
    inicio = time.time()
    resposta, motivo = "", "concluido"
    erro_fatal = None
    while passos < max_passos:
        try:
            passo = adaptador.chamar(sistema, mensagens, caixa.definicoes)
        except Exception as erro:  # noqa: BLE001
            erro_fatal = f"{type(erro).__name__}: {str(erro)[:600]}"
            motivo = "erro_modelo"
            log(f"  !! {erro_fatal}")
            break
        passos += 1
        uso.somar(**passo["uso"])
        if passo["texto"]:
            resposta = passo["texto"]
        if not passo["chamadas"]:
            motivo = "concluido" if passo["parada"] in ("end_turn", "stop", None) else str(passo["parada"])
            break
        mensagens.append(adaptador.mensagem_assistente(passo))
        resultados = []
        for chamada in passo["chamadas"]:
            t0 = time.time()
            texto, erro = caixa.executar(chamada["nome"], chamada["argumentos"], turno=len(trilha))
            dt = time.time() - t0
            log(f"  -> {chamada['nome']} ({dt:.1f}s, {len(texto)} car{', ERRO' if erro else ''})")
            resultados.append({"id": chamada["id"], "texto": texto, "erro": erro})
            trilha.append({
                "passo": passos, "ferramenta": chamada["nome"],
                "argumentos": chamada["argumentos"], "segundos": round(dt, 2),
                "caracteres_saida": len(texto), "erro": erro,
                "saida": texto[:4000],
            })
        saida_ferramentas = adaptador.mensagem_ferramentas(resultados)
        if isinstance(saida_ferramentas, list):
            mensagens.extend(saida_ferramentas)
        else:
            mensagens.append(saida_ferramentas)
        passos += 1  # o recursionLimit do LibreChat conta 2 passos por chamada de ferramenta
    else:
        motivo = "limite_de_passos"
    return {
        "resposta": resposta,
        "motivo_parada": motivo,
        "erro": erro_fatal,
        "passos": passos,
        "chamadas_ferramenta": len(trilha),
        "trilha": trilha,
        "uso": uso.dict(),
        "segundos": round(time.time() - inicio, 1),
    }

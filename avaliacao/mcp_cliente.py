"""Cliente MCP por stdio, o mesmo transporte que o LibreChat usa nos quatro servidores do EnergyNexus.

Uma mensagem JSON-RPC por linha (o que a ponte do AgentCore e o MCPServer dos servidores locais falam). O cliente
guarda as instruções devolvidas no `initialize` porque o librechat.yaml liga `serverInstructions: true` nos quatro
servidores, e elas entram no prompt de sistema (ver ferramentas.montar_prompt_sistema).
"""

from __future__ import annotations

import json
import queue
import subprocess
import threading
import time


class ErroMCP(RuntimeError):
    pass


class ServidorMCP:
    """Um processo de servidor MCP falando JSON-RPC por linhas no stdio."""

    def __init__(self, nome: str, comando: list[str], env: dict[str, str], prazo_init: float = 180.0,
                 prazo_chamada: float = 300.0, log=None):
        self.nome = nome
        self.comando = comando
        self.env = env
        self.prazo_init = prazo_init
        self.prazo_chamada = prazo_chamada
        self.log = log or (lambda t: None)
        self.instrucoes = ""
        self.ferramentas: list[dict] = []
        self._proc: subprocess.Popen | None = None
        self._resp: dict[int, queue.Queue] = {}
        self._trava = threading.Lock()
        self._id = 0

    # --- ciclo de vida -------------------------------------------------
    def abrir(self):
        self._proc = subprocess.Popen(
            self.comando, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=self.env, bufsize=0,
        )
        threading.Thread(target=self._ler_stdout, daemon=True).start()
        threading.Thread(target=self._ler_stderr, daemon=True).start()
        resultado = self._pedir(
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "avaliacao-energynexus", "version": "1"},
            },
            prazo=self.prazo_init,
        )
        self.instrucoes = (resultado.get("instructions") or "").strip()
        self._notificar("notifications/initialized", {})
        self.ferramentas = self._listar()
        self.log(f"{self.nome}: {len(self.ferramentas)} ferramentas, "
                 f"{len(self.instrucoes)} caracteres de instruções")
        return self

    def fechar(self):
        if self._proc is None:
            return
        try:
            if self._proc.stdin:
                self._proc.stdin.close()
            self._proc.wait(timeout=10)
        except Exception:  # noqa: BLE001
            self._proc.kill()

    # --- transporte ----------------------------------------------------
    def _ler_stdout(self):
        assert self._proc and self._proc.stdout
        for linha in self._proc.stdout:
            linha = linha.strip()
            if not linha:
                continue
            try:
                msg = json.loads(linha)
            except Exception:  # noqa: BLE001
                self.log(f"{self.nome}: linha não-JSON no stdout: {linha[:200]!r}")
                continue
            ident = msg.get("id")
            if ident is None:
                continue  # notificação do servidor
            with self._trava:
                fila = self._resp.get(ident)
            if fila is not None:
                fila.put(msg)

    def _ler_stderr(self):
        assert self._proc and self._proc.stderr
        for linha in self._proc.stderr:
            texto = linha.decode("utf-8", "replace").rstrip()
            if texto:
                self.log(f"[{self.nome} stderr] {texto[:400]}")

    def _enviar(self, msg: dict):
        assert self._proc and self._proc.stdin
        self._proc.stdin.write(json.dumps(msg, ensure_ascii=False).encode() + b"\n")
        self._proc.stdin.flush()

    def _notificar(self, metodo: str, params: dict):
        self._enviar({"jsonrpc": "2.0", "method": metodo, "params": params})

    def _pedir(self, metodo: str, params: dict, prazo: float | None = None) -> dict:
        prazo = prazo if prazo is not None else self.prazo_chamada
        with self._trava:
            self._id += 1
            ident = self._id
            fila: queue.Queue = queue.Queue()
            self._resp[ident] = fila
        try:
            self._enviar({"jsonrpc": "2.0", "id": ident, "method": metodo, "params": params})
            try:
                msg = fila.get(timeout=prazo)
            except queue.Empty as erro:
                raise ErroMCP(f"{self.nome}.{metodo} não respondeu em {prazo:.0f}s") from erro
        finally:
            with self._trava:
                self._resp.pop(ident, None)
        if "error" in msg:
            raise ErroMCP(f"{self.nome}.{metodo}: {msg['error']}")
        return msg.get("result") or {}

    # --- API -----------------------------------------------------------
    def _listar(self) -> list[dict]:
        saida, cursor = [], None
        while True:
            params = {"cursor": cursor} if cursor else {}
            resultado = self._pedir("tools/list", params)
            saida.extend(resultado.get("tools") or [])
            cursor = resultado.get("nextCursor")
            if not cursor:
                return saida

    def chamar(self, ferramenta: str, argumentos: dict) -> tuple[str, bool]:
        """Devolve (texto, erro). Erro de transporte vira texto de erro, como no LibreChat."""
        try:
            resultado = self._pedir("tools/call", {"name": ferramenta, "arguments": argumentos})
        except ErroMCP as erro:
            return f"Erro da ferramenta: {erro}", True
        partes = []
        for item in resultado.get("content") or []:
            if item.get("type") == "text":
                partes.append(item.get("text") or "")
            else:
                partes.append(json.dumps(item, ensure_ascii=False))
        texto = "\n".join(p for p in partes if p)
        if not texto and resultado.get("structuredContent") is not None:
            texto = json.dumps(resultado["structuredContent"], ensure_ascii=False)
        return texto, bool(resultado.get("isError"))


def abrir_todos(definicoes: list[dict], log=None) -> dict[str, ServidorMCP]:
    """Sobe os servidores em paralelo (o boot da ponte do AgentCore custa dezenas de segundos)."""
    servidores: dict[str, ServidorMCP] = {}
    erros: dict[str, str] = {}

    def subir(definicao: dict):
        servidor = ServidorMCP(log=log, **definicao)
        try:
            servidor.abrir()
            servidores[servidor.nome] = servidor
        except Exception as erro:  # noqa: BLE001
            erros[definicao["nome"]] = f"{type(erro).__name__}: {erro}"

    linhas = [threading.Thread(target=subir, args=(d,)) for d in definicoes]
    inicio = time.time()
    for linha in linhas:
        linha.start()
    for linha in linhas:
        linha.join()
    if log:
        log(f"servidores MCP no ar em {time.time() - inicio:.0f}s: {sorted(servidores)}")
        for nome, erro in erros.items():
            log(f"servidor MCP {nome} FALHOU: {erro}")
    return servidores

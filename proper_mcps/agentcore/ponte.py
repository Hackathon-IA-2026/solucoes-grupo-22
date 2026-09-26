"""Ponte stdio entre o LibreChat e um servidor MCP hospedado no Amazon Bedrock AgentCore Runtime.

Um processo por servidor: `ponte.py dados`, `ponte.py docs`, `ponte.py relatorio`. O LibreChat fala JSON-RPC pelo
stdio e a ponte repassa cada mensagem (initialize, tools/list, tools/call, notifications/...) para o endpoint de
invocação do runtime, pondo o cabeçalho `Authorization: Bearer <JWT do Cognito>` que ela mesma pega e renova.

Por que a ponte existe, e não um `type: streamable-http` com o token no YAML: o LibreChat 0.8.7 resolve `${VAR}` a
partir do process.env no boot (packages/data-provider/src/utils.ts:38-52), não conhece o grant client_credentials e
trata 401/403 em servidor sem OAuth como falha dura (packages/api/src/mcp/MCPConnectionFactory.ts:410-419) — um token
de 24 h escrito em cabeçalho pararia de funcionar no meio do dia e só um restart o renovaria. O token do pool do
AgentCore também não pode sair de client_credentials: o pool não tem domínio nem resource server, só
USER_PASSWORD_AUTH (usuário e senha no .env).

Regras que a ponte cumpre:
  - stdout é o transporte JSON-RPC: log, aviso e erro vão só para o stderr;
  - falta de variável de ambiente ou nome de servidor errado derruba o processo dizendo o nome exato do que falta;
  - resposta não-200 do AgentCore volta pelo canal de erro do MCP (tools/call como isError, o resto como erro
    JSON-RPC), nunca como exceção que derruba a ponte;
  - o token é renovado antes de expirar e, se ainda assim vier 401/403, é renovado e a chamada é repetida uma vez.

initialize: é repassado ao runtime, porque é dele que vêm as instruções do servidor MCP que o `serverInstructions:
true` do librechat.yaml injeta no prompt. Mas é repassado com prazo: o boot do LibreChat corta a inicialização de
cada servidor em MCP_INIT_TIMEOUT_MS (30 s por padrão, packages/api/src/mcp/registry/MCPServersInitializer.ts:10 e
:212-213; o initTimeout do YAML é ignorado nesse ponto) e, estourando, o servidor vira um stub sem ferramentas que só
é retentado 5 min depois. Medido nesta conta: cada pedido ao AgentCore custa ~5 s, e chegou a 14 s na versão do docs
que baixava o modelo de embeddings do S3 — o boot (initialize + dois tools/list em paralelo) cabe nos 30 s, mas sem
folga. Então, se o runtime não responder o initialize em ESPERA_INIT_S, a ponte responde ela mesma (capacidade de
ferramentas, sem as instruções, gritando no stderr) e deixa o pedido correndo: ele aquece o runtime para o tools/list
seguinte. Com MCP_INIT_TIMEOUT_MS folgado no .env o caminho normal é o LibreChat receber o initialize de verdade,
com instruções.
"""
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

SERVIDORES = {"dados": "COPPEZIP_ARN_DADOS", "docs": "COPPEZIP_ARN_DOCS", "relatorio": "COPPEZIP_ARN_RELATORIO"}
MARGEM_TOKEN_S = 600      # renova o token 10 min antes de expirar (o Cognito devolve ExpiresIn=86400)
VIDA_SESSAO_S = 25200     # 7 h: troca o id de sessão antes do maxLifetime de 8 h do runtime
ESPERA_INIT_S = 25        # prazo do initialize, abaixo dos 30 s do MCP_INIT_TIMEOUT_MS padrão do LibreChat
TIMEOUT_HTTP_S = 240      # abaixo do timeout de ferramenta do librechat.yaml, para o erro vir da ponte
PROTOCOLO = "2025-06-18"  # versão usada quando o cliente não manda protocolVersion no initialize

TRAVA_SAIDA = threading.Lock()


def _log(texto: str):
    """Único canal de saída livre: stdout é o transporte JSON-RPC do MCP."""
    print(f"[ponte {NOME}] {texto}", file=sys.stderr, flush=True)


def _var(nome: str) -> str:
    valor = os.environ.get(nome, "").strip()
    if not valor:
        raise SystemExit(f"[ponte] falta a variável de ambiente {nome}: o processo filho do stdio só herda HOME, "
                         f"LOGNAME, PATH, SHELL, TERM e USER, então declare-a em env: do servidor no librechat.yaml")
    return valor


def _post(url: str, corpo: bytes, cabecalhos: dict, tempo: float) -> tuple[int, str, str]:
    """POST que devolve (status, content-type, corpo) em vez de levantar exceção em erro HTTP."""
    pedido = urllib.request.Request(url, data=corpo, headers=cabecalhos, method="POST")
    try:
        with urllib.request.urlopen(pedido, timeout=tempo) as resposta:
            return resposta.status, resposta.headers.get("Content-Type", ""), resposta.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), e.read().decode("utf-8", "replace")


class Token:
    """JWT do Cognito por USER_PASSWORD_AUTH. InitiateAuth não é assinado, logo a ponte não usa credencial da AWS."""

    def __init__(self, regiao: str, cliente: str, usuario: str, senha: str):
        self.url = f"https://cognito-idp.{regiao}.amazonaws.com/"
        self.cliente, self.usuario, self.senha = cliente, usuario, senha
        self._trava = threading.Lock()
        self._valor, self._expira = "", 0.0

    def obter(self, renovar: bool = False) -> str:
        with self._trava:
            if renovar or not self._valor or time.time() > self._expira - MARGEM_TOKEN_S:
                self._buscar()
            return self._valor

    def _buscar(self):
        corpo = json.dumps({"AuthFlow": "USER_PASSWORD_AUTH", "ClientId": self.cliente,
                            "AuthParameters": {"USERNAME": self.usuario, "PASSWORD": self.senha}}).encode()
        status, _, texto = _post(self.url, corpo,
                                 {"Content-Type": "application/x-amz-json-1.1",
                                  "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth"}, 30)
        if status != 200:
            # a senha nunca entra na mensagem: só o que o Cognito respondeu
            raise RuntimeError(f"o Cognito recusou o login do usuário {self.usuario} (cliente {self.cliente}): "
                               f"HTTP {status} {texto[:300]}")
        dados = json.loads(texto).get("AuthenticationResult") or {}
        if not dados.get("AccessToken"):
            raise RuntimeError(f"resposta do Cognito sem AccessToken (desafio pendente para {self.usuario}?): "
                               f"{texto[:300]}")
        self._valor, self._expira = dados["AccessToken"], time.time() + float(dados["ExpiresIn"])
        _log(f"token novo do Cognito para {self.usuario}, válido por {int(dados['ExpiresIn'] / 3600)} h")


class Sessao:
    """Id de sessão do AgentCore, fixo no processo para o container ficar quente (o runtime só ocioso 15 min cai).

    É trocado antes do maxLifetime de 8 h do runtime, senão as chamadas passariam a bater numa sessão encerrada.
    """

    def __init__(self):
        self._trava = threading.Lock()
        self._id, self._desde = "", 0.0

    def id(self) -> str:
        with self._trava:
            if not self._id or time.monotonic() - self._desde > VIDA_SESSAO_S:
                self._id = f"coppezip-ponte-{NOME}-{uuid.uuid4().hex}"  # o AgentCore exige 33 caracteres ou mais
                self._desde = time.monotonic()
                _log(f"sessão do runtime: {self._id}")
            return self._id


class Runtime:
    """O outro lado da ponte: o endpoint de invocação do runtime, que fala MCP por HTTP."""

    def __init__(self, arn: str, regiao: str, token: Token):
        self.arn, self.token = arn, token
        self.url = (f"https://bedrock-agentcore.{regiao}.amazonaws.com/runtimes/"
                    f"{urllib.parse.quote(arn, safe='')}/invocations?qualifier=DEFAULT")
        self.sessao = Sessao()

    def chamar(self, mensagem: dict) -> list[dict]:
        """Repassa uma mensagem JSON-RPC e devolve as mensagens de resposta (lista vazia em notificação)."""
        corpo = json.dumps(mensagem, ensure_ascii=False).encode()
        for tentativa in (1, 2):
            cabecalhos = {"Authorization": "Bearer " + self.token.obter(renovar=tentativa == 2),
                          "Content-Type": "application/json",
                          "Accept": "application/json, text/event-stream",
                          "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": self.sessao.id()}
            status, tipo, texto = _post(self.url, corpo, cabecalhos, TIMEOUT_HTTP_S)
            # 401/403 no meio da sessão é falha dura para o LibreChat: renova o token e repete antes de desistir
            if status in (401, 403) and tentativa == 1:
                _log(f"HTTP {status} do AgentCore; renovando o token e repetindo {mensagem.get('method')}")
                continue
            break
        if not 200 <= status < 300:
            raise RuntimeError(f"HTTP {status} do AgentCore em {self.arn}: {texto[:500]}")
        return _mensagens(tipo, texto)


def _mensagens(tipo: str, texto: str) -> list[dict]:
    """Corpo da resposta do AgentCore: event-stream (o caso normal), JSON puro, ou vazio (notificação aceita)."""
    if not texto.strip():
        return []
    if "text/event-stream" not in tipo:
        return [json.loads(texto)]
    saida, dados = [], []
    for linha in texto.splitlines():
        if linha.startswith("data:"):
            dados.append(linha[5:].lstrip())
        elif not linha.strip() and dados:
            saida.append(json.loads("\n".join(dados)))
            dados = []
    if dados:
        saida.append(json.loads("\n".join(dados)))
    return saida


def _enviar(mensagem: dict):
    dados = json.dumps(mensagem, ensure_ascii=False).encode()
    with TRAVA_SAIDA:  # uma mensagem JSON por linha, e as respostas saem de várias linhas de execução
        sys.stdout.buffer.write(dados + b"\n")
        sys.stdout.buffer.flush()


def _erro(mensagem: dict, texto: str):
    """Erro pelo canal do MCP: em tools/call como isError (o modelo lê e corrige); no resto como erro JSON-RPC."""
    _log(texto)
    if mensagem.get("id") is None:
        return None
    if mensagem.get("method") == "tools/call":
        return {"jsonrpc": "2.0", "id": mensagem["id"],
                "result": {"content": [{"type": "text", "text": texto}], "isError": True}}
    return {"jsonrpc": "2.0", "id": mensagem["id"], "error": {"code": -32603, "message": texto}}


def _atender(mensagem: dict):
    try:
        for resposta in RUNTIME.chamar(mensagem):
            _enviar(resposta)
    except Exception as e:  # nenhuma mensagem pode derrubar a ponte: o erro vai para quem pediu
        resposta = _erro(mensagem, f"{mensagem.get('method')} falhou na ponte do AgentCore: {e}")
        if resposta:
            _enviar(resposta)


def _initialize_local(mensagem: dict) -> dict:
    """Resposta da própria ponte quando o runtime não cabe no prazo: só ferramentas, sem instruções do servidor."""
    pedido = (mensagem.get("params") or {}).get("protocolVersion") or PROTOCOLO
    return {"jsonrpc": "2.0", "id": mensagem["id"],
            "result": {"protocolVersion": pedido, "capabilities": {"tools": {"listChanged": False}},
                       "serverInfo": {"name": f"coppezip-{NOME}", "version": "ponte"}}}


def _atender_initialize(mensagem: dict):
    """Repassa o initialize com prazo (ver o cabeçalho do arquivo); quem responder primeiro fica com a resposta."""
    fim = threading.Event()
    trava, estado = threading.Lock(), {"respondido": False}

    def assumir() -> bool:
        with trava:
            if estado["respondido"]:
                return False
            estado["respondido"] = True
            return True

    def repassar():
        try:
            respostas = RUNTIME.chamar(mensagem)
        except Exception as e:
            if assumir():
                _enviar(_erro(mensagem, f"initialize falhou na ponte do AgentCore: {e}"))
            else:
                _log(f"o initialize chegou depois do prazo e falhou: {e}")
            fim.set()
            return
        if assumir():
            for resposta in respostas:
                _enviar(resposta)
        else:
            _log("o initialize do runtime chegou depois do prazo: o runtime está quente para o tools/list, mas as "
                 "instruções do servidor ficaram de fora deste boot")
        fim.set()

    threading.Thread(target=repassar, daemon=True).start()
    if fim.wait(ESPERA_INIT_S):
        return
    if assumir():
        _log(f"o runtime não respondeu o initialize em {ESPERA_INIT_S}s: respondendo pela ponte (sem as instruções do "
             f"servidor) para o boot do LibreChat não estourar; o pedido continua e aquece o runtime")
        _enviar(_initialize_local(mensagem))


def _aquecer_token():
    """Paga o login do Cognito (~1 s) na partida, antes do primeiro pedido do LibreChat."""
    try:
        TOKEN.obter()
    except Exception as e:
        _log(f"não consegui o token do Cognito na partida: {e}")


def main():
    _log(f"ponte para {RUNTIME.arn}")
    threading.Thread(target=_aquecer_token, daemon=True).start()
    for linha in sys.stdin.buffer:  # o transporte stdio do MCP é uma mensagem JSON por linha
        linha = linha.strip()
        if not linha:
            continue
        try:
            mensagem = json.loads(linha)
        except Exception as e:
            _log(f"mensagem inválida no stdin: {e}")
            _enviar({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"JSON inválido: {e}"}})
            continue
        alvo = _atender_initialize if mensagem.get("method") == "initialize" and mensagem.get("id") is not None \
            else _atender
        # uma linha de execução por mensagem (chamadas de ferramenta em paralelo não esperam uma pela outra) e não
        # daemon: fechando o stdin, o processo ainda responde o que estava em andamento antes de sair
        threading.Thread(target=alvo, args=(mensagem,)).start()
    _log("stdin fechou: respondendo o que está em andamento e encerrando")


if len(sys.argv) != 2 or sys.argv[1] not in SERVIDORES:
    raise SystemExit(f"[ponte] uso: ponte.py {' | '.join(SERVIDORES)}")
NOME = sys.argv[1]
TOKEN = Token(_var("COPPEZIP_COGNITO_REGIAO"), _var("COPPEZIP_COGNITO_CLIENTE"),
              _var("COPPEZIP_COGNITO_USUARIO"), _var("COPPEZIP_COGNITO_SENHA"))
RUNTIME = Runtime(_var(SERVIDORES[NOME]), _var("COPPEZIP_AGENTCORE_REGIAO"), TOKEN)

if __name__ == "__main__":
    main()

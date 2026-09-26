#!/usr/bin/env python3
"""Cliente de linha de comando do chat (API do LibreChat), para testes e para agentes que fazem papel de usuário.

  eval/chat.py "pergunta"                       conversa nova com o perfil padrão
  eval/chat.py --perfil energynexus-analista-claude "pergunta"
  eval/chat.py --conversa ID "pergunta"         continua a conversa ID
  eval/chat.py --aguardar ID                    espera a resposta que ainda está sendo gerada na conversa ID

Cada conversa fica em <saida>/<ID>.json (mensagens brutas) e <saida>/<ID>.md (transcrição com as ferramentas, SQL e
resultados); cada pergunta vira uma linha de <saida>/log.jsonl. Com --conversa, o perfil é o mesmo da conversa (o
modelo que respondeu até aqui), a menos que --perfil diga outro. O usuário é teste-<persona>@energynexus.local, criado
por eval/usuario.sh, com a senha de .runtime/run/usuarios.json.
"""
import argparse
import base64
from http.cookies import SimpleCookie
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raiz do repositório


RT = os.path.join(REPO, ".runtime")
CREDENCIAIS = os.path.join(RT, "run", "usuarios.json")
SESSOES = os.path.join(RT, "run", "sessoes")
ENDPOINT_VLLM = "EnergyNexus"  # nome do endpoint do vLLM no librechat.yaml


def _porta():
    with open(os.path.join(REPO, ".env")) as f:
        return next(linha.split("=", 1)[1].strip() for linha in f if linha.startswith("PORT="))


URL = f"http://127.0.0.1:{_porta()}"
# O LibreChat recusa (e pode banir) clientes que não se identificam como navegador.
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
RAIZ = "00000000-0000-0000-0000-000000000000"
LIMITE_MD = 6000  # caracteres por resultado de ferramenta na transcrição .md (o .json guarda tudo)


def falhar(msg, codigo=1):
    print(f"ERRO: {msg}", file=sys.stderr)
    sys.exit(codigo)


def api(metodo, caminho, corpo=None, token=None, cookie=None):
    req = urllib.request.Request(
        URL + caminho,
        data=json.dumps(corpo).encode() if corpo is not None else None,
        method=metodo,
        headers={"User-Agent": UA, "Content-Type": "application/json"},
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    if cookie:
        req.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            status, texto, cookies = r.status, r.read().decode(), r.headers.get_all("Set-Cookie") or []
    except urllib.error.HTTPError as e:
        status, texto, cookies = e.code, e.read().decode(errors="replace"), []
    except urllib.error.URLError as e:
        falhar(f"o EnergyNexus não respondeu em {URL} ({e.reason}); o serviço pode estar fora do ar")
    try:
        return status, json.loads(texto), cookies
    except json.JSONDecodeError:
        return status, texto, cookies


def gravar_privado(caminho, texto):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    fd = os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(texto)


class Sessao:
    """Token de acesso em cache, renovado pelo refresh token para não gastar o limite de logins (7 a cada 5 min)."""

    def __init__(self, persona):
        self.persona, self.email = persona, f"teste-{persona}@energynexus.local"
        self.arquivo = os.path.join(SESSOES, f"{persona}.json")
        try:
            with open(self.arquivo) as f:
                self.dados = json.load(f)
        except (OSError, json.JSONDecodeError):
            self.dados = {}

    def token(self):
        t = self.dados.get("token")
        if t and self._expira(t) > time.time() + 60:
            return t
        if not (self.dados.get("refreshToken") and self._renovar()):
            self._entrar()
        return self.dados["token"]

    @staticmethod
    def _expira(token):
        try:
            p = token.split(".")[1]
            return json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))["exp"]
        except (IndexError, ValueError, KeyError):
            return 0

    def _guardar(self, resposta, cookies):
        self.dados["token"] = resposta["token"]
        for c in cookies:
            biscoito = SimpleCookie(c)
            if "refreshToken" in biscoito:
                self.dados["refreshToken"] = biscoito["refreshToken"].value
        gravar_privado(self.arquivo, json.dumps(self.dados))

    def _renovar(self):
        st, r, cookies = api("POST", "/api/auth/refresh", {}, cookie=f"refreshToken={self.dados['refreshToken']}")
        if st == 200 and isinstance(r, dict) and r.get("token"):
            self._guardar(r, cookies)
            return True
        return False

    def _entrar(self):
        try:
            with open(CREDENCIAIS) as f:
                senha = json.load(f)["senha"]
        except (OSError, json.JSONDecodeError, KeyError):
            falhar(f"sem credenciais em {CREDENCIAIS}; rode eval/usuario.sh {self.persona}")
        st, r, cookies = api("POST", "/api/auth/login", {"email": self.email, "password": senha})
        if st == 429:
            falhar("limite de logins do LibreChat atingido; espere 5 minutos")
        if st != 200 or not isinstance(r, dict) or not r.get("token"):
            falhar(f"login de {self.email} falhou (HTTP {st}): {str(r)[:200]}")
        self._guardar(r, cookies)


def mensagens(sessao, cid):
    st, r, _ = api("GET", f"/api/messages/{cid}", token=sessao.token())
    if st != 200 or not isinstance(r, list):
        falhar(f"não consegui ler a conversa {cid} (HTTP {st}): {str(r)[:200]}")
    return r


def perfil(sessao, nome, modelo=None, endpoint=None):
    """Perfil (modelSpec) do librechat.yaml: prompt de sistema, endpoint, modelo e servidores MCP. Sem nome, o perfil do
    modelo informado (o da conversa que está sendo continuada); sem nome e sem modelo, o padrão."""
    st, r, _ = api("GET", "/api/config", token=sessao.token())  # sem login o LibreChat não devolve os perfis
    perfis = ((r.get("modelSpecs") or {}).get("list") or []) if st == 200 and isinstance(r, dict) else []
    if nome:
        achados = [p for p in perfis if p.get("name") == nome]
    elif modelo:
        achados = [p for p in perfis if (p.get("preset") or {}).get("model") == modelo
                   and (p.get("preset") or {}).get("endpoint") == endpoint]
        if not achados:
            falhar(f"a conversa foi feita com o modelo {modelo} no endpoint {endpoint}, que não é de nenhum perfil do "
                   "librechat.yaml; diga em qual perfil continuar com --perfil")
    else:
        achados = [p for p in perfis if p.get("default")]
    if not achados:
        falhar(f"perfil {nome or 'padrão'} não existe no librechat.yaml")
    return achados[0]


def nome_curto(nome):
    return (nome or "?").split("_mcp_")[0]


def ferramentas(msg):
    return [nome_curto((p.get("tool_call") or {}).get("name")) for p in msg.get("content") or [] if p.get("type") == "tool_call"]


def texto_resposta(msg):
    partes = [p.get("text", "") for p in msg.get("content") or [] if p.get("type") == "text"]
    return "\n".join(partes).strip() or (msg.get("text") or "").strip()


def ativa(sessao, cid):
    st, r, _ = api("GET", f"/api/agents/chat/status/{cid}", token=sessao.token())
    return not (st == 200 and isinstance(r, dict) and r.get("active") is False)


def aguardar(sessao, cid, antes, limite_s):
    """Espera a resposta à pergunta nova da conversa: a mensagem do usuário cujo ID não está em `antes` (o LibreChat
    ignora o messageId enviado pelo cliente). Devolve (mensagens, resposta ou None, motivo da falha)."""
    fim = time.time() + limite_s
    msgs, parada = [], 0
    while time.time() < fim:
        time.sleep(3)
        msgs = mensagens(sessao, cid)
        novas = [m for m in msgs if m.get("isCreatedByUser") and m.get("messageId") not in antes]
        if novas:
            uid = novas[-1]["messageId"]
            resp = [m for m in msgs if m.get("parentMessageId") == uid and not m.get("isCreatedByUser")]
            if resp and not resp[-1].get("unfinished") and (resp[-1].get("content") or resp[-1].get("text") or resp[-1].get("error")):
                return msgs, resp[-1], None
        parada = 0 if ativa(sessao, cid) else parada + 1
        if parada >= 5:
            return msgs, None, "a geração terminou sem resposta salva"
    return msgs, None, "tempo esgotado"


def bloco_args(args):
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            return f"```\n{args}\n```"
    if isinstance(args, dict):
        sql = args.get("query") or args.get("sql")
        if isinstance(sql, str) and len(args) == 1:
            return f"```sql\n{sql.strip()}\n```"
    return f"```json\n{json.dumps(args, ensure_ascii=False, indent=2)}\n```"


def corta(texto, n=LIMITE_MD):
    texto = texto if isinstance(texto, str) else json.dumps(texto, ensure_ascii=False)
    return texto if len(texto) <= n else texto[:n] + f"\n... [{len(texto) - n} caracteres cortados; veja o .json]"


def transcricao(msgs, persona, cid):
    linhas = [f"# Conversa {cid}", "", f"Persona: `{persona}` · atualizada em {datetime.now():%Y-%m-%d %H:%M}", ""]
    n = 0
    for m in msgs:
        if m.get("isCreatedByUser"):
            n += 1
            linhas += [f"## {n}. Pergunta", "", m.get("text", ""), ""]
            continue
        linhas += [f"### Resposta ({m.get('model') or m.get('sender') or '?'})", ""]
        if m.get("error"):
            linhas += ["**O chat devolveu erro nesta resposta.**", ""]
        partes = m.get("content") or ([{"type": "text", "text": m.get("text", "")}] if m.get("text") else [])
        for p in partes:
            tipo = p.get("type")
            if tipo == "think":
                linhas += ["<details><summary>Raciocínio do modelo</summary>", "", corta(p.get("think", "")), "", "</details>", ""]
            elif tipo == "tool_call":
                tc = p.get("tool_call") or {}
                linhas += [f"**Ferramenta `{tc.get('name')}`**", "", bloco_args(tc.get("args")), "",
                           "Resultado:", "", "```", corta(tc.get("output") or "(sem saída)"), "```", ""]
            elif tipo == "text":
                linhas += [p.get("text", ""), ""]
            else:
                linhas += [f"_Parte `{tipo}`:_ `{corta(json.dumps(p, ensure_ascii=False), 800)}`", ""]
    return "\n".join(linhas)


def salvar(saida, persona, cid, msgs):
    pasta = saida  # --saida já é a pasta das transcrições: outro "conversas" dentro dela separava do log.jsonl
    os.makedirs(pasta, exist_ok=True)
    with open(os.path.join(pasta, f"{cid}.json"), "w") as f:
        json.dump(msgs, f, ensure_ascii=False, indent=1)
    with open(os.path.join(pasta, f"{cid}.md"), "w") as f:
        f.write(transcricao(msgs, persona, cid))


def registrar(saida, **linha):
    with open(os.path.join(saida, "log.jsonl"), "a") as f:
        f.write(json.dumps({"quando": datetime.now().isoformat(timespec="seconds"), **linha}, ensure_ascii=False) + "\n")


def mostrar(cid, resp, segundos, modelo):
    usadas = ferramentas(resp)
    print(f"Conversa: {cid}   (para continuar: ./perguntar --conversa {cid} \"próxima pergunta\")")
    print(f"Tempo de resposta: {segundos:.0f} s · modelo: {modelo}")
    print(f"Ferramentas que o chat usou ({len(usadas)}): {', '.join(usadas) if usadas else 'nenhuma'}")
    if resp.get("error"):
        print("ATENÇÃO: o chat devolveu uma mensagem de erro.")
    print("-" * 60)
    print(texto_resposta(resp) or "(resposta vazia)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pergunta", nargs="?")
    ap.add_argument("--perfil", help="nome do perfil (modelSpec) no librechat.yaml; sem ele, o padrão")
    ap.add_argument("--conversa", help="ID da conversa a continuar")
    ap.add_argument("--aguardar", metavar="ID", help="espera a resposta pendente da conversa ID")
    ap.add_argument("--persona", default="teste", help="usuário teste-<persona>@energynexus.local (eval/usuario.sh)")
    ap.add_argument("--saida", default=os.path.join(RT, "conversas"), help="pasta das transcrições")
    ap.add_argument("--busca-web", action="store_true", help="liga a busca web nativa do LibreChat (Serper + Jina)")
    ap.add_argument("--timeout", type=int, default=900, help="segundos (padrão 900)")
    a = ap.parse_args()
    os.makedirs(a.saida, exist_ok=True)
    sessao = Sessao(a.persona)

    if a.aguardar:
        anteriores = mensagens(sessao, a.aguardar)
        perguntas = [i for i, m in enumerate(anteriores) if m.get("isCreatedByUser")]
        if not perguntas:
            falhar("conversa sem perguntas")
        antes = {m.get("messageId") for m in anteriores[:perguntas[-1]]}
        inicio = time.time()
        msgs, resp, motivo = aguardar(sessao, a.aguardar, antes, a.timeout)
        salvar(a.saida, a.persona, a.aguardar, msgs)
        if not resp:
            falhar(f"{motivo}; rode de novo: ./perguntar --aguardar {a.aguardar}", 2)
        mostrar(a.aguardar, resp, time.time() - inicio, resp.get("model") or "?")
        return

    if not a.pergunta:
        falhar("faltou a pergunta")
    pai, antes, anterior = RAIZ, set(), {}
    if a.conversa:
        anteriores = mensagens(sessao, a.conversa)
        if not anteriores:
            falhar(f"conversa {a.conversa} não encontrada")
        if anteriores[-1].get("isCreatedByUser"):
            falhar(f"a última pergunta desta conversa ainda não tem resposta; rode eval/chat.py --aguardar {a.conversa}")
        pai, antes = anteriores[-1]["messageId"], {m.get("messageId") for m in anteriores}
        # continuar não pode trocar o modelo em silêncio: o perfil sai de quem respondeu até aqui, não do padrão
        anterior = next(({"modelo": m["model"], "endpoint": m.get("endpoint")} for m in reversed(anteriores)
                         if not m.get("isCreatedByUser") and m.get("model")), {})
    esc = perfil(sessao, a.perfil, anterior.get("modelo"), anterior.get("endpoint"))
    modelo, endpoint = esc["preset"]["model"], esc["preset"]["endpoint"]
    tipo = "custom" if endpoint == ENDPOINT_VLLM else endpoint   # "EnergyNexus" é o vLLM; "bedrock" é o Claude na AWS
    mcps = esc["mcpServers"]
    if anterior and not a.perfil:
        print(f"Perfil {esc['name']} ({modelo}), o mesmo da conversa {a.conversa}.")
    mid = str(uuid.uuid4())
    corpo = {
        "text": a.pergunta, "sender": "User", "isCreatedByUser": True, "parentMessageId": pai,
        "conversationId": a.conversa, "messageId": mid, "endpoint": endpoint, "endpointType": tipo,
        "model": modelo, "isContinued": False,
        # o LibreChat aplica do lado do servidor o prompt de sistema do perfil (ele não aparece em /api/config)
        "spec": esc["name"],
        # com modelSpecs.enforce: false o servidor só aplica o promptPrefix do perfil: sem estes campos a conversa roda
        # com o padrão do endpoint (o Claude gravou maxContextTokens 95.000 e 4.096 de saída), não com o do librechat.yaml
        **{k: esc["preset"][k] for k in ("maxContextTokens", "maxOutputTokens") if esc["preset"].get(k)},
        "ephemeralAgent": {"mcp": mcps, **({"web_search": True} if a.busca_web else {})},
    }
    inicio = time.time()
    for tentativa in range(4):
        st, r, _ = api("POST", f"/api/agents/chat/{endpoint}", corpo, token=sessao.token())
        if st != 429:
            break
        time.sleep(20 * (tentativa + 1))  # limite de mensagens por minuto do LibreChat
    if st != 200 or not isinstance(r, dict) or not r.get("conversationId"):
        registrar(a.saida, persona=a.persona, conversa=a.conversa, pergunta=a.pergunta, segundos=round(time.time() - inicio),
                  modelo=modelo, mcps=mcps, ferramentas=[], erro=f"HTTP {st}: {str(r)[:300]}")
        falhar(f"o chat recusou a pergunta (HTTP {st}): {str(r)[:300]}")
    cid = r["conversationId"]
    msgs, resp, motivo = aguardar(sessao, cid, antes, a.timeout)
    salvar(a.saida, a.persona, cid, msgs)
    segundos = time.time() - inicio
    registrar(a.saida, persona=a.persona, conversa=cid, resposta_id=resp.get("messageId") if resp else None,
              pergunta=a.pergunta, segundos=round(segundos), modelo=modelo, mcps=mcps,
              ferramentas=ferramentas(resp) if resp else [],
              erro=motivo or ("o chat devolveu erro" if resp.get("error") else None),
              tamanho_resposta=len(texto_resposta(resp)) if resp else 0)
    if not resp:
        dica = f"rode: ./perguntar --aguardar {cid}" if motivo == "tempo esgotado" else "anote como falha do chat"
        falhar(f"{motivo}; {dica}", 2)
    mostrar(cid, resp, segundos, modelo)


if __name__ == "__main__":
    main()

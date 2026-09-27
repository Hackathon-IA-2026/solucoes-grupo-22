"""Monta o MESMO conjunto de ferramentas e o MESMO prompt de sistema que o perfil do librechat.yaml dá ao agente.

Tudo é lido do próprio librechat.yaml (perfil `energynexus-analista`), então mudar o YAML muda a avaliação:
  - mcpServers do perfil            -> os quatro servidores MCP, com o nome de ferramenta `<tool>_mcp_<servidor>`
                                       (Constants.mcp_delimiter = "_mcp_" em packages/data-provider/src/config.ts)
  - serverInstructions: true        -> as instruções do initialize entram no prompt no formato do MCPManager
  - skills: true                    -> catálogo "## Available Skills" no prompt + ferramenta `skill`
  - webSearch: do YAML              -> ferramenta `web_search` (Serper + Jina) e o bloco de citação do LibreChat
  - promptPrefix (âncora &prompt)   -> o prompt do analista, igual para os dois modelos
"""

from __future__ import annotations

import pathlib
import re

import comum
import busca_web
import mcp_cliente

DELIMITADOR = "_mcp_"  # Constants.mcp_delimiter do LibreChat
PERFIL_PADRAO = "energynexus-analista"

DESCRICAO_SKILL = """Invoke a skill from the user's library. Skills provide domain-specific instructions loaded into \
the conversation context, and may also provide files accessible via available tools depending on the runtime \
environment.

WHEN TO USE:
- The user's request matches a skill listed in the "Available Skills" section of the system prompt.
- You MUST invoke the matching skill BEFORE attempting the task yourself.

WHAT HAPPENS:
- The skill's full instructions are loaded into the conversation as context.
- Files bundled with the skill may become accessible via available tools.
- Follow the skill's instructions to complete the task.

CONSTRAINTS:
- Do not invoke a skill that is already active in this conversation.
- Skill names come from the catalog only. Do not guess names."""

ESQUEMA_SKILL = {
    "type": "object",
    "properties": {
        "skillName": {"type": "string", "description": 'The kebab-case identifier of the skill to invoke. Must match '
                                                       'a name from the "Available Skills" section.'},
        "args": {"type": "string", "description": "Optional freeform arguments string passed to the skill."},
    },
    "required": ["skillName"],
}


# --- librechat.yaml ----------------------------------------------------------
def ler_perfil(nome: str = PERFIL_PADRAO, caminho: pathlib.Path | None = None) -> dict:
    """Lê o perfil do librechat.yaml resolvendo as âncoras YAML (&prompt/*prompt)."""
    import yaml

    caminho = caminho or (comum.RAIZ / "librechat.yaml")
    config = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    for perfil in config["modelSpecs"]["list"]:
        if perfil["name"] == nome:
            return {"perfil": perfil, "config": config}
    raise KeyError(f"perfil {nome!r} não está no librechat.yaml")


def ler_skills(raiz: pathlib.Path | None = None) -> list[dict]:
    """Catálogo das skills de proper_skills/<nome>/SKILL.md (o DEPLOYMENT_SKILLS_DIR do LibreChat)."""
    raiz = raiz or (comum.RAIZ / "proper_skills")
    saida = []
    for pasta in sorted(p for p in raiz.iterdir() if p.is_dir()):
        arquivo = pasta / "SKILL.md"
        if not arquivo.exists():
            continue
        texto = arquivo.read_text(encoding="utf-8")
        frente = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", texto, re.S)
        if frente:
            import yaml

            meta = yaml.safe_load(frente.group(1)) or {}
            corpo = frente.group(2)
        else:
            meta, corpo = {}, texto
        saida.append({
            "name": meta.get("name") or pasta.name,
            "description": (meta.get("description") or "").strip(),
            "body": corpo.strip(),
        })
    return saida


# --- servidores MCP ----------------------------------------------------------
def definicoes_mcp(nomes: list[str], config: dict) -> list[dict]:
    """Traduz mcpServers: do YAML para os comandos que o cliente stdio roda, com o ${VAR} do .env resolvido."""
    env = comum.exportar_env()
    saida = []
    for nome in nomes:
        bruto = config["mcpServers"][nome]

        def expandir(texto: str) -> str:
            return re.sub(r"\$\{([A-Za-z0-9_]+)\}", lambda m: env.get(m.group(1), ""), texto)

        args = [expandir(a) for a in bruto.get("args", [])]
        comando = bruto["command"]
        # o LibreChat usa /usr/bin/env porque não expande ${VAR} em "command"; aqui já veio expandido
        if comando == "/usr/bin/env":
            comando_final = args
        else:
            comando_final = [expandir(comando)] + args
        ambiente = dict(env)
        for chave, valor in (bruto.get("env") or {}).items():
            ambiente[chave] = expandir(valor)
        saida.append({
            "nome": nome,
            "comando": comando_final,
            "env": ambiente,
            "prazo_init": float(bruto.get("initTimeout", 120000)) / 1000,
            "prazo_chamada": float(bruto.get("timeout", 120000)) / 1000,
        })
    return saida


class Caixa:
    """O conjunto de ferramentas do agente e a execução de cada chamada."""

    def __init__(self, perfil_nome: str = PERFIL_PADRAO, com_busca: bool = True, log=None):
        self.log = log or (lambda t: None)
        lido = ler_perfil(perfil_nome)
        self.perfil, self.config = lido["perfil"], lido["config"]
        self.skills = ler_skills() if self.perfil.get("skills") else []
        self.servidores = mcp_cliente.abrir_todos(
            definicoes_mcp(self.perfil.get("mcpServers", []), self.config), log=self.log
        )
        self.busca = busca_web.BuscaWeb(log=self.log) if com_busca else None
        self._mapa: dict[str, tuple[str, str]] = {}
        self.definicoes: list[dict] = []
        self._montar()

    def _montar(self):
        for nome_servidor, servidor in self.servidores.items():
            for ferramenta in servidor.ferramentas:
                nome = f"{ferramenta['name']}{DELIMITADOR}{nome_servidor}"
                self._mapa[nome] = (nome_servidor, ferramenta["name"])
                self.definicoes.append({
                    "nome": nome,
                    "descricao": (ferramenta.get("description") or "")[:4000],
                    "esquema": ferramenta.get("inputSchema") or {"type": "object", "properties": {}},
                })
        if self.busca is not None:
            d = busca_web.definicao()
            self.definicoes.append(d)
        if self.skills:
            self.definicoes.append({"nome": "skill", "descricao": DESCRICAO_SKILL, "esquema": ESQUEMA_SKILL})

    # --- prompt de sistema --------------------------------------------
    def prompt_sistema(self) -> str:
        partes = [self.perfil["preset"]["promptPrefix"].strip()]
        instrucoes = {n: s.instrucoes for n, s in self.servidores.items() if s.instrucoes}
        if instrucoes:
            corpo = "\n\n".join(f"## {n} MCP Server Instructions\n\n{t}" for n, t in instrucoes.items())
            partes.append(
                "# MCP Server Instructions\n\nThe following MCP servers are available with their specific "
                f"instructions:\n\n{corpo}\n\nPlease follow these instructions when using tools from the "
                "respective MCP servers."
            )
        if self.busca is not None:
            partes.append(busca_web.CONTEXTO_PROMPT)
        if self.skills:
            catalogo = "\n".join(f"- {s['name']}: {s['description']}" for s in self.skills)
            partes.append(f"## Available Skills\n\n{catalogo}")
        return "\n\n".join(partes)

    # --- execução ------------------------------------------------------
    def executar(self, nome: str, argumentos: dict, turno: int = 0) -> tuple[str, bool]:
        """Devolve (texto, erro). Uma skill devolve o corpo do SKILL.md, como o LibreChat injeta."""
        if nome == "web_search":
            if self.busca is None:
                return "A busca web não está habilitada nesta execução.", True
            return self.busca.chamar(argumentos, turno=turno), False
        if nome == "skill":
            pedido = (argumentos.get("skillName") or "").strip()
            for skill in self.skills:
                if skill["name"] == pedido:
                    return skill["body"], False
            return (f"Não existe a skill {pedido!r}. Catálogo: "
                    f"{', '.join(s['name'] for s in self.skills)}"), True
        if nome not in self._mapa:
            return f"Ferramenta desconhecida: {nome}", True
        nome_servidor, nome_ferramenta = self._mapa[nome]
        return self.servidores[nome_servidor].chamar(nome_ferramenta, argumentos)

    def fechar(self):
        for servidor in self.servidores.values():
            servidor.fechar()

    def resumo(self) -> dict:
        return {
            "perfil": self.perfil["name"],
            "servidores": {n: len(s.ferramentas) for n, s in self.servidores.items()},
            "ferramentas": [d["nome"] for d in self.definicoes],
            "skills": [s["name"] for s in self.skills],
            "caracteres_prompt_sistema": len(self.prompt_sistema()),
        }

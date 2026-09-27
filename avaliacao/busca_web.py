"""Ferramenta `web_search`, a mesma que o LibreChat monta a partir de webSearch: do librechat.yaml.

O LibreChat 0.8.7 usa @librechat/agents: Serper para buscar (`/search`), Serper para ler a página (`/scrape`) e o
Jina para reordenar os trechos; o resultado volta com âncoras \ue202turnNsearchM. Aqui o pipeline é o mesmo com as
mesmas chaves do .env — o que difere está anotado em RELATORIO.md (limitações).
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request

import comum

# marcadores que o LibreChat usa nas âncoras de citação
ANCORA = "\ue202"
GRUPO_INICIO, GRUPO_FIM = "\ue200", "\ue201"

NOME = "web_search"
DESCRICAO = (
    "Real-time search. Results have required citation anchors.\n\n"
    "Note: Use ONCE per reply unless instructed otherwise.\n\n"
    "Anchors:\n- \\ue202turnXtypeY\n"
    "- X = turn idx, type = 'search' | 'news' | 'image' | 'ref', Y = item idx\n\n"
    "**CITE EVERY NON-OBVIOUS FACT/QUOTE:** use the anchor right after the statement.\n"
    "**NEVER use markdown links, [1], or footnotes. CITE ONLY with anchors provided.**"
)
ESQUEMA = {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Consulta de busca. Prefira 3 a 6 palavras-chave precisas."},
        "date": {"type": "string", "enum": ["h", "d", "w", "m", "y"], "description": "Recorte de data."},
        "country": {"type": "string", "description": "Código de 2 letras do país (br, us, ...)."},
        "news": {"type": "boolean", "description": "Buscar também em notícias."},
    },
    "required": ["query"],
}

MAX_FONTES_LIDAS = 4
MAX_CARACTERES_POR_FONTE = 6000
MAX_CARACTERES_TOTAL = 50000  # DEFAULT_MAX_LLM_OUTPUT_CHARS do @librechat/agents


def _post(url: str, corpo: dict, cabecalhos: dict, prazo: float = 30.0) -> dict:
    pedido = urllib.request.Request(
        url, data=json.dumps(corpo).encode(), headers={"Content-Type": "application/json", **cabecalhos}
    )
    with urllib.request.urlopen(pedido, timeout=prazo) as resposta:
        return json.loads(resposta.read().decode("utf-8", "replace"))


class BuscaWeb:
    def __init__(self, log=None):
        env = comum.ler_env()
        self._serper = env["SERPER_API_KEY"]
        self._jina = env.get("JINA_API_KEY", "")
        self.log = log or (lambda t: None)
        self.chamadas = 0

    # --- Serper --------------------------------------------------------
    def _buscar(self, consulta: str, pais: str = "br", data: str | None = None, noticias: bool = False) -> dict:
        corpo: dict = {"q": consulta, "gl": pais, "hl": "pt-br", "num": 10}
        if data:
            corpo["tbs"] = f"qdr:{data}"
        caminho = "news" if noticias else "search"
        return _post(f"https://google.serper.dev/{caminho}", corpo, {"X-API-KEY": self._serper})

    def _ler(self, url: str) -> str:
        try:
            dados = _post("https://scrape.serper.dev", {"url": url}, {"X-API-KEY": self._serper}, prazo=20.0)
        except Exception as erro:  # noqa: BLE001
            self.log(f"busca_web: não consegui ler {url}: {type(erro).__name__}")
            return ""
        texto = dados.get("text") or dados.get("markdown") or ""
        return re.sub(r"\n{3,}", "\n\n", texto).strip()

    # --- Jina ----------------------------------------------------------
    def _reordenar(self, consulta: str, trechos: list[str]) -> list[str]:
        if not self._jina or len(trechos) < 2:
            return trechos
        try:
            dados = _post(
                "https://api.jina.ai/v1/rerank",
                {"model": "jina-reranker-v2-base-multilingual", "query": consulta, "documents": trechos,
                 "top_n": min(len(trechos), 6)},
                {"Authorization": "Bearer " + self._jina},
                prazo=30.0,
            )
            return [trechos[r["index"]] for r in dados.get("results", []) if r.get("index") is not None] or trechos
        except Exception as erro:  # noqa: BLE001
            self.log(f"busca_web: rerank do Jina falhou ({type(erro).__name__}); mantendo a ordem do Serper")
            return trechos

    # --- ferramenta ----------------------------------------------------
    def chamar(self, argumentos: dict, turno: int = 0) -> str:
        consulta = (argumentos.get("query") or "").strip()
        if not consulta:
            return "Erro: 'query' é obrigatório."
        self.chamadas += 1
        try:
            bruto = self._buscar(
                consulta,
                pais=(argumentos.get("country") or "br"),
                data=argumentos.get("date"),
                noticias=bool(argumentos.get("news")),
            )
        except urllib.error.HTTPError as erro:
            return f"Erro na busca web: HTTP {erro.code} do Serper."
        except Exception as erro:  # noqa: BLE001
            return f"Erro na busca web: {type(erro).__name__}: {erro}"

        organicos = bruto.get("organic") or bruto.get("news") or []
        if not organicos:
            return f"A busca por {consulta!r} não devolveu resultado."

        linhas = [f"# Resultados da busca: {consulta!r}", ""]
        gasto = 0
        for indice, item in enumerate(organicos[:10]):
            ancora = f"{ANCORA}turn{turno}search{indice}"
            titulo = item.get("title") or "(sem título)"
            link = item.get("link") or ""
            trecho = (item.get("snippet") or "").strip()
            linhas += [f"## [{indice}] {titulo}", f"URL: {link}", f"Âncora de citação: {ancora}"]
            if trecho:
                linhas.append(f"Resumo: {trecho}")
            if indice < MAX_FONTES_LIDAS and link and gasto < MAX_CARACTERES_TOTAL:
                conteudo = self._ler(link)
                if conteudo:
                    partes = [p for p in re.split(r"\n\s*\n", conteudo) if len(p.strip()) > 80]
                    melhores = self._reordenar(consulta, partes[:40])
                    texto = "\n\n".join(melhores)[:MAX_CARACTERES_POR_FONTE]
                    gasto += len(texto)
                    linhas.append("Conteúdo da página lida:\n" + texto)
            linhas.append("")
        saida = "\n".join(linhas)
        if len(saida) > MAX_CARACTERES_TOTAL:
            saida = saida[:MAX_CARACTERES_TOTAL] + "\n…[truncado]"
        return saida


def definicao() -> dict:
    return {"nome": NOME, "descricao": DESCRICAO, "esquema": ESQUEMA}


CONTEXTO_PROMPT = """# `web_search`:
**Execute immediately without preface.** After search, provide a brief summary addressing the query directly, then
structure your response with clear Markdown formatting. Cite sources properly.

**CITATION FORMAT — UNICODE ESCAPE SEQUENCES ONLY:** \ue202 (before each anchor), \ue200 (group start),
\ue201 (group end), \ue203 (highlight start), \ue204 (highlight end).
Anchor pattern: \ue202turn{N}{type}{index} where type=search|news|image|ref.

**CRITICAL:** Place anchors AFTER punctuation. Cite every non-obvious fact/quote. NEVER use markdown links, [1],
footnotes, or HTML tags."""

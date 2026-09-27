"""Lê os JSON por pergunta/rodada e monta as tabelas do RELATORIO.md (taxa de acerto, alucinação, latência, custo).

Funciona com resultado parcial: conta o que existir e diz quantas execuções entraram em cada número.

    python relatar.py                 # tabelas no stdout
    python relatar.py --escrever      # grava as tabelas dentro de RELATORIO.md, entre os marcadores
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import statistics

import comum

# Preço por milhão de tokens no Bedrock (on-demand, us-east-1). Ajuste aqui se a tabela da AWS mudar.
PRECO = {
    "us.anthropic.claude-opus-5": {"entrada": 5.00, "saida": 25.00},
    "us.anthropic.claude-opus-4-8": {"entrada": 5.00, "saida": 25.00},
    "us.anthropic.claude-sonnet-5": {"entrada": 3.00, "saida": 15.00},
}
# Custo de referência da GPU local: hora de RTX 5090 em nuvem (faixa de mercado usada no relatório)
CUSTO_GPU_HORA_USD = 0.90

CATEGORIAS = ["factual_docs", "placar_esg", "agregacao", "financeiro", "web", "ausente", "relatorio"]
ROTULO = {
    "factual_docs": "(a) factual com citação (docs)",
    "placar_esg": "(b) placar ESG",
    "agregacao": "(c) contagens e agregações",
    "financeiro": "(c') financeiro estruturado",
    "web": "(d) busca web",
    "ausente": "(e) não está na base",
    "relatorio": "(f) relatório em PDF",
}
MARCADOR_INICIO = "<!-- TABELAS:INICIO -->"
MARCADOR_FIM = "<!-- TABELAS:FIM -->"
MEDIDA_INICIO = "<!-- MEDIDA:INICIO -->"
MEDIDA_FIM = "<!-- MEDIDA:FIM -->"


def falhou_execucao(registro: dict) -> bool:
    """Pergunta não respondida por falha de infraestrutura (token expirado, 400 de contexto, MCP fora do ar).

    Não é erro do modelo e não entra no denominador da taxa de acerto: entra contada à parte.
    """
    return bool(registro["execucao"].get("erro")) or registro["correcao"].get("motivo") == "erro_de_execucao"


def carregar(raiz: pathlib.Path) -> list[dict]:
    """Um registro por execução. Pastas com sufixo `_token_expirado` guardam corridas perdidas por credencial
    vencida e ficam fora de qualquer conta: não são resposta do modelo."""
    saida = []
    for pasta in sorted(p for p in raiz.iterdir() if p.is_dir() and not p.name.endswith("_token_expirado")):
        for arquivo in sorted(pasta.glob("*_r*.json")):
            try:
                saida.append(json.loads(arquivo.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001
                continue
    return saida


def agrupar(registros: list[dict]) -> dict:
    por = collections.defaultdict(list)
    for r in registros:
        por[r["modelo"]].append(r)
    return dict(por)


def taxa(itens: list[dict]) -> str:
    """Taxa sobre o que o modelo efetivamente respondeu; falha de execução aparece entre parênteses."""
    if not itens:
        return "—"
    respondidas = [i for i in itens if not falhou_execucao(i)]
    falhas = len(itens) - len(respondidas)
    sufixo = f" +{falhas} s/resp." if falhas else ""
    if not respondidas:
        return f"— ({falhas} sem resposta)"
    acertos = sum(1 for i in respondidas if i["correcao"]["acerto"])
    return f"{100 * acertos / len(respondidas):.0f}% ({acertos}/{len(respondidas)}){sufixo}"


def tabela_categorias(por_modelo: dict) -> str:
    modelos = sorted(por_modelo)
    linhas = ["| Categoria | " + " | ".join(modelos) + " |",
              "|---|" + "---|" * len(modelos)]
    for categoria in CATEGORIAS:
        celulas = []
        for modelo in modelos:
            itens = [r for r in por_modelo[modelo] if r["pergunta"]["categoria"] == categoria]
            celulas.append(taxa(itens))
        if any(c != "—" for c in celulas):
            linhas.append(f"| {ROTULO.get(categoria, categoria)} | " + " | ".join(celulas) + " |")
    linhas.append("| **Total** | " + " | ".join(f"**{taxa(por_modelo[m])}**" for m in modelos) + " |")
    return "\n".join(linhas)


def tabela_alucinacao(por_modelo: dict) -> str:
    modelos = sorted(por_modelo)
    linhas = ["| Medida | " + " | ".join(modelos) + " |", "|---|" + "---|" * len(modelos)]
    def linha(nome, f):
        linhas.append(f"| {nome} | " + " | ".join(f(por_modelo[m]) for m in modelos) + " |")

    def aus(itens):
        sub = [i for i in itens if i["pergunta"]["categoria"] == "ausente" and not falhou_execucao(i)]
        if not sub:
            return "—"
        n = sum(1 for i in sub if i["correcao"]["detalhe"].get("admitiu_ausencia"))
        return f"{100 * n / len(sub):.0f}% ({n}/{len(sub)})"

    def alu(itens):
        itens = [i for i in itens if not falhou_execucao(i)]
        if not itens:
            return "—"
        n = sum(1 for i in itens if i["correcao"].get("alucinacao"))
        return f"{100 * n / len(itens):.0f}% ({n}/{len(itens)})"

    def cita_ruim(itens):
        sub = [i for i in itens if i["correcao"]["tipo"] == "numerico_com_citacao" and not falhou_execucao(i)]
        if not sub:
            return "—"
        n = sum(1 for i in sub
                if i["correcao"]["detalhe"].get("citou_pagina")
                and i["correcao"]["detalhe"].get("pagina_confirma_valor") is False)
        return f"{n}/{len(sub)}"

    linha("Admitiu a ausência (categoria e)", aus)
    linha("Alucinação (qualquer categoria)", alu)
    linha("Citou página que não confirma o valor", cita_ruim)
    return "\n".join(linhas)


def tabela_latencia(por_modelo: dict) -> str:
    modelos = sorted(por_modelo)
    linhas = ["| Medida | " + " | ".join(modelos) + " |", "|---|" + "---|" * len(modelos)]

    def med(itens, chave, f=lambda x: x):
        if not itens:
            return "—"
        valores = [f(i["execucao"].get(chave) or 0) for i in itens]
        return f"{statistics.median(valores):.1f}"

    def p90(itens, chave):
        if not itens:
            return "—"
        valores = sorted(i["execucao"].get(chave) or 0 for i in itens)
        return f"{valores[min(len(valores) - 1, int(0.9 * len(valores)))]:.0f}"

    linhas.append("| Execuções contadas | " + " | ".join(str(len(por_modelo[m])) for m in modelos) + " |")
    linhas.append("| Perguntas distintas respondidas | " + " | ".join(
        str(len({r["pergunta"]["id"] for r in por_modelo[m] if not falhou_execucao(r)})) for m in modelos) + " |")
    linhas.append("| Falhas de execução (não contam como erro) | " + " | ".join(
        str(sum(1 for r in por_modelo[m] if falhou_execucao(r))) for m in modelos) + " |")
    linhas.append("| Latência mediana (s) | " + " | ".join(med(por_modelo[m], "segundos") for m in modelos) + " |")
    linhas.append("| Latência p90 (s) | " + " | ".join(p90(por_modelo[m], "segundos") for m in modelos) + " |")
    linhas.append("| Chamadas de ferramenta (mediana) | "
                  + " | ".join(med(por_modelo[m], "chamadas_ferramenta") for m in modelos) + " |")
    for nome, chave in (("Tokens de entrada (mediana)", "tokens_entrada"),
                        ("Tokens de saída (mediana)", "tokens_saida")):
        celulas = []
        for modelo in modelos:
            itens = por_modelo[modelo]
            celulas.append(f"{statistics.median([i['execucao']['uso'][chave] or 0 for i in itens]):.0f}"
                           if itens else "—")
        linhas.append(f"| {nome} | " + " | ".join(celulas) + " |")
    return "\n".join(linhas)


def tabela_custo(por_modelo: dict) -> tuple[str, dict]:
    modelos = sorted(por_modelo)
    linhas = ["| Modelo | Execuções | Tokens entrada | Tokens saída | Custo total | Custo por pergunta |",
              "|---|---|---|---|---|---|"]
    resumo = {}
    for modelo in modelos:
        itens = por_modelo[modelo]
        if not itens:
            continue
        entrada = sum(i["execucao"]["uso"]["tokens_entrada"] or 0 for i in itens)
        saida = sum(i["execucao"]["uso"]["tokens_saida"] or 0 for i in itens)
        modelo_id = itens[0]["modelo_id"]
        if modelo_id in PRECO:
            preco = PRECO[modelo_id]
            total = entrada / 1e6 * preco["entrada"] + saida / 1e6 * preco["saida"]
            texto_total = f"US$ {total:.2f}"
            texto_unit = f"US$ {total / len(itens):.3f}"
        else:
            horas = sum(i["execucao"].get("segundos") or 0 for i in itens) / 3600
            total = horas * CUSTO_GPU_HORA_USD
            texto_total = f"US$ {total:.2f} ({horas:.2f} h de GPU)"
            texto_unit = f"US$ {total / len(itens):.3f}"
        resumo[modelo] = {"entrada": entrada, "saida": saida, "custo_usd": round(total, 4),
                          "execucoes": len(itens)}
        linhas.append(f"| {modelo} (`{modelo_id}`) | {len(itens)} | {entrada:,} | {saida:,} | "
                      f"{texto_total} | {texto_unit} |".replace(",", "."))
    return "\n".join(linhas), resumo


def tabela_variancia(por_modelo: dict) -> str:
    modelos = sorted(por_modelo)
    linhas = ["| Modelo | Perguntas com 2 rodadas | Rodadas discordantes | Estabilidade |", "|---|---|---|---|"]
    for modelo in modelos:
        por_id = collections.defaultdict(list)
        for r in por_modelo[modelo]:
            if not falhou_execucao(r):
                por_id[r["pergunta"]["id"]].append(r["correcao"]["acerto"])
        duplas = {k: v for k, v in por_id.items() if len(v) >= 2}
        if not duplas:
            linhas.append(f"| {modelo} | 0 | — | — |")
            continue
        discordam = sum(1 for v in duplas.values() if len(set(v)) > 1)
        linhas.append(f"| {modelo} | {len(duplas)} | {discordam} | "
                      f"{100 * (len(duplas) - discordam) / len(duplas):.0f}% |")
    return "\n".join(linhas)


def erros_notaveis(por_modelo: dict, quantos: int = 12) -> str:
    linhas = ["| Pergunta | Categoria | " + " | ".join(sorted(por_modelo)) + " |",
              "|---|---|" + "---|" * len(por_modelo)]
    modelos = sorted(por_modelo)
    por_id: dict[str, dict] = {}
    for modelo in modelos:
        for r in por_modelo[modelo]:
            if falhou_execucao(r):
                continue
            alvo = por_id.setdefault(r["pergunta"]["id"], {"categoria": r["pergunta"]["categoria"],
                                                           "texto": r["pergunta"]["pergunta"]})
            alvo.setdefault(modelo, []).append(r["correcao"]["acerto"])
    # só onde os modelos discordam: é o que interessa na comparação
    interessantes = []
    for ident, dados in sorted(por_id.items()):
        estados = {m: (all(dados[m]) if dados.get(m) else None) for m in modelos}
        valores = [v for v in estados.values() if v is not None]
        if len(set(valores)) > 1:
            interessantes.append((ident, dados, estados))
    for ident, dados, estados in interessantes[:quantos]:
        celulas = ["ok" if estados[m] else ("erro" if estados[m] is False else "—") for m in modelos]
        linhas.append(f"| `{ident}` {dados['texto'][:70]}… | {dados['categoria']} | " + " | ".join(celulas) + " |")
    if len(interessantes) <= 0:
        linhas.append("| (nenhuma divergência) | | " + " | ".join("" for _ in modelos) + " |")
    return "\n".join(linhas), len(interessantes)


def montar(raiz: pathlib.Path) -> tuple[str, dict]:
    registros = carregar(raiz)
    por_modelo = agrupar(registros)
    custo, resumo_custo = tabela_custo(por_modelo)
    divergencias, n_div = erros_notaveis(por_modelo)
    partes = [
        "### Taxa de acerto por categoria",
        "",
        tabela_categorias(por_modelo),
        "",
        "### Alucinação",
        "",
        tabela_alucinacao(por_modelo),
        "",
        "### Latência e consumo por pergunta",
        "",
        tabela_latencia(por_modelo),
        "",
        "### Custo",
        "",
        custo,
        "",
        "### Variância entre rodadas",
        "",
        tabela_variancia(por_modelo),
        "",
        f"### Onde os modelos discordam ({n_div} perguntas)",
        "",
        divergencias,
    ]
    estatisticas = {
        "execucoes": {m: len(v) for m, v in por_modelo.items()},
        "custo": resumo_custo,
        "divergencias": n_div,
    }
    return "\n".join(partes), estatisticas


def tabela_medida(raiz: pathlib.Path) -> str:
    """Contexto efetivo e vazão do vLLM, a partir do que medir_vllm.py gravou."""
    caminho = raiz / "medida_vllm.json"
    if not caminho.exists():
        return "_(sem `medida_vllm.json`: rode `python medir_vllm.py`)_"
    d = json.loads(caminho.read_text(encoding="utf-8"))
    linhas = ["**Contexto efetivo medido** (agulha no palheiro: o dado pedido fica enterrado no meio do prompt, "
              "então a tabela separa \"aceitou o prompt\" de \"usou o prompt\"):",
              "",
              "| Tokens de prompt | Achou a agulha | Segundos | Prefill (tok/s) | Saída (tok/s) |",
              "|---|---|---|---|---|"]
    for c in d.get("contexto", []):
        if not c.get("ok"):
            linhas.append(f"| alvo {c.get('alvo_tokens')} | erro | | | {c.get('erro', '')[:60]} |")
            continue
        linhas.append(f"| {c['tokens_prompt']:,} | {'sim' if c['achou_agulha'] else 'NÃO'} | {c['segundos']} | "
                      f"{c['prefill_tokens_por_s']:.0f} | {c['tokens_saida_por_s']} |".replace(",", "."))
    g = d.get("geracao_curta") or {}
    if g:
        linhas += ["", f"Geração curta (prompt de poucos tokens): {g.get('tokens_por_s')} tokens de saída por "
                       f"segundo ({g.get('tokens_saida')} tokens em {g.get('segundos')} s)."]
    return "\n".join(linhas)


def gravar(alvo: pathlib.Path, inicio: str, fim: str, texto: str) -> None:
    atual = alvo.read_text(encoding="utf-8")
    a = atual.index(inicio) + len(inicio)
    b = atual.index(fim)
    alvo.write_text(atual[:a] + "\n\n" + texto + "\n\n" + atual[b:], encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", default=str(comum.SAIDA))
    ap.add_argument("--escrever", action="store_true", help="grava dentro de RELATORIO.md")
    args = ap.parse_args()
    raiz = pathlib.Path(args.saida)
    texto, estatisticas = montar(raiz)
    print(texto)
    print("\n" + json.dumps(estatisticas, ensure_ascii=False, indent=2))
    if args.escrever:
        alvo = comum.AQUI / "RELATORIO.md"
        gravar(alvo, MARCADOR_INICIO, MARCADOR_FIM, texto)
        gravar(alvo, MEDIDA_INICIO, MEDIDA_FIM, tabela_medida(raiz))
        print(f"\ntabelas gravadas em {alvo}")

"""Confere o conjunto de perguntas antes de gastar as duas execuções: estrutura, ids únicos e gabarito utilizável.

Também reconfere, no índice dos PDFs, se a página do gabarito realmente contém o valor esperado — o mesmo teste que
o corretor aplica na resposta do modelo. Uma pergunta que não passa aqui não pode ser cobrada de ninguém.
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

import comum
import corretor

TIPOS = {"numerico", "numerico_com_citacao", "contagem", "texto_contem", "ausencia", "relatorio"}


def conferir(caminho: pathlib.Path) -> dict:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    perguntas = dados["perguntas"] if isinstance(dados, dict) else dados
    indice = corretor.Indice()
    problemas: list[str] = []
    por_categoria = collections.Counter()
    vistos = set()
    citacoes_ok = citacoes_falhas = 0

    for p in perguntas:
        ident = p.get("id")
        if not ident or ident in vistos:
            problemas.append(f"id repetido ou ausente: {ident!r}")
        vistos.add(ident)
        if not (p.get("pergunta") or "").strip():
            problemas.append(f"{ident}: pergunta vazia")
        tipo = p.get("tipo_correcao")
        if tipo not in TIPOS:
            problemas.append(f"{ident}: tipo_correcao {tipo!r} desconhecido")
        por_categoria[p.get("categoria")] += 1
        g = p.get("gabarito") or {}
        if tipo in ("numerico", "contagem", "numerico_com_citacao") and g.get("valor") is None:
            problemas.append(f"{ident}: gabarito sem 'valor'")
        if tipo == "texto_contem" and not (g.get("aceitos") or g.get("todos")):
            problemas.append(f"{ident}: texto_contem sem 'aceitos' nem 'todos'")
        if tipo == "numerico_com_citacao":
            arquivo, pagina = g.get("arquivo"), g.get("pagina")
            if not arquivo or not pagina:
                problemas.append(f"{ident}: numerico_com_citacao sem arquivo/pagina")
                continue
            if indice.arquivo_existe(arquivo) is False:
                problemas.append(f"{ident}: arquivo {arquivo!r} não está no índice")
                citacoes_falhas += 1
                continue
            paginas = [pagina] + list(g.get("paginas_aceitas") or [])
            confirmou = False
            for pag in paginas:
                texto = indice.texto_pagina(arquivo, pag)
                if texto and corretor.bate(float(g["valor"]), texto,
                                           g.get("tolerancia_relativa") or 0.02,
                                           g.get("tolerancia_absoluta"),
                                           escala_livre=corretor.escala_livre(g))[0]:
                    confirmou = True
                    break
            if confirmou:
                citacoes_ok += 1
            else:
                citacoes_falhas += 1
                problemas.append(f"{ident}: a página {pagina} de {arquivo} não confirma o valor {g['valor']}")

    return {
        "arquivo": str(caminho),
        "total": len(perguntas),
        "por_categoria": dict(sorted(por_categoria.items())),
        "conferidos_pelo_gerador": sum(1 for p in perguntas if p.get("conferido")),
        "citacoes_reconfirmadas": citacoes_ok,
        "citacoes_nao_confirmadas": citacoes_falhas,
        "problemas": problemas,
    }


if __name__ == "__main__":
    caminho = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else comum.AQUI / "perguntas.json"
    saida = conferir(caminho)
    print(json.dumps(saida, ensure_ascii=False, indent=2))
    sys.exit(1 if saida["problemas"] else 0)

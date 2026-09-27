#!/usr/bin/env python3
"""Mede a recuperação de páginas nos relatórios: a página certa aparece entre as primeiras?

Uso: .runtime/venv/bin/python eval/recuperacao.py [--k 10] [--so 1,2,3]
Entrada: eval/pares_relatorios.csv (pergunta → arquivo e página, conferidos à mão no PDF indexado).
Compara os três jeitos de buscar que o CoppeZIP usa, sempre por página, no índice data/docs_titan.duckdb:
- palavras: BM25 nos parágrafos (tabela blocos), como a linha do tempo faz com a consulta do tema;
- sentido: cosseno entre o vetor da pergunta e os dos trechos (tabela trechos, Amazon Titan);
- fusão: os dois juntos por posição (RRF, 1/(60 + posição)), o que a aba Busca e a linha do tempo usam.
Saída na tela: acerto em 1, em 5 e em k, e o MRR de cada jeito. É esta medida que diz se mexer nas consultas dos temas
(TEMAS em data/linha_do_tempo.py) ou no modelo de embedding melhorou ou piorou a busca.
"""
import argparse
import csv
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raiz do repositório


AQUI = os.path.dirname(os.path.abspath(__file__))
PARES = os.path.join(AQUI, "pares_relatorios.csv")
sys.path.insert(0, os.path.join(RAIZ, "proper_mcps", "docs"))
from server import CANDIDATOS, _con, _embed  # noqa: E402

K_RRF = 60


def palavras(con, pergunta):
    return [(a, p) for a, p, _ in con.execute(f"""
        SELECT arquivo, pagina, max(s) AS s
        FROM (SELECT arquivo, pagina, fts_main_blocos.match_bm25(id, ?) AS s FROM blocos)
        WHERE s IS NOT NULL GROUP BY ALL ORDER BY s DESC LIMIT {CANDIDATOS}""", [pergunta]).fetchall()]


def sentido(con, pergunta):
    return [(a, p) for a, p, _ in con.execute(f"""
        SELECT arquivo, pagina, max(array_cosine_similarity(embedding, ?::FLOAT[1024])) AS s
        FROM trechos GROUP BY ALL ORDER BY s DESC LIMIT {CANDIDATOS}""", [_embed(pergunta)]).fetchall()]


def fusao(listas):
    pontos = {}
    for lista in listas:
        for posicao, chave in enumerate(lista, start=1):
            pontos[chave] = pontos.get(chave, 0) + 1 / (K_RRF + posicao)
    return sorted(pontos, key=pontos.get, reverse=True)


def posicao_do_alvo(resultados, alvo):
    """Posição (1 em diante) da página certa na lista, ou None se ela não apareceu."""
    return next((i for i, chave in enumerate(resultados, start=1) if chave == alvo), None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=10, help="tamanho da lista que a pessoa olharia")
    ap.add_argument("--so", help="ids do CSV, separados por vírgula")
    a = ap.parse_args()

    with open(PARES, newline="") as f:
        pares = list(csv.DictReader(f, delimiter=";"))
    if a.so:
        querem = set(a.so.split(","))
        pares = [p for p in pares if p["id"] in querem]
    if not pares:
        raise SystemExit("nenhum par selecionado")

    con = _con()
    try:
        posicoes = {"palavras": [], "sentido": [], "fusão": []}
        for p in pares:
            alvo = (p["arquivo"], int(p["pagina"]))
            if not con.execute("SELECT count(*) FROM blocos WHERE arquivo = ? AND pagina = ?", list(alvo)).fetchone()[0]:
                raise SystemExit(f"par {p['id']}: {alvo[0]} p. {alvo[1]} não está no índice (refaça o par ou o índice)")
            listas = {"palavras": palavras(con, p["pergunta"]), "sentido": sentido(con, p["pergunta"])}
            listas["fusão"] = fusao(listas.values())
            for jeito, lista in listas.items():
                posicoes[jeito].append(posicao_do_alvo(lista, alvo))
            marca = "".join("." if posicoes[j][-1] == 1 else "o" if posicoes[j][-1] else "x" for j in posicoes)
            print(f"[{p['id']:>3}] {marca} {p['tema'][:14]:<14} {p['pergunta'][:70]}", flush=True)
    finally:
        con.close()

    print(f"\n{len(pares)} pares, {len(set(p['arquivo'] for p in pares))} relatórios "
          f"(na ordem palavras, sentido, fusão: '.' = página certa em 1º, 'o' = na lista, 'x' = fora)")
    print(f"{'jeito':<10}{'em 1º':>8}{'em 5':>8}{f'em {a.k}':>8}{'MRR':>8}")
    for jeito, ps in posicoes.items():
        def parte(limite):
            return f"{100 * sum(1 for x in ps if x and x <= limite) / len(ps):.0f}%"
        mrr = sum(1 / x for x in ps if x) / len(ps)
        print(f"{jeito:<10}{parte(1):>8}{parte(5):>8}{parte(a.k):>8}{mrr:>8.3f}")


if __name__ == "__main__":
    main()

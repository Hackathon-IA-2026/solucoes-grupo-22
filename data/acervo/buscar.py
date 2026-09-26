"""Busca rápida no manifesto.

Exemplos:
  python data/acervo/buscar.py --empresa cemig --categoria sustentabilidade
  python data/acervo/buscar.py --empresa copel --ano 2019-2023 --tipo dfp
  python data/acervo/buscar.py --texto "leilão" --categoria investimento
"""
import argparse, os, unicodedata
import pandas as pd

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # raiz do repositório
ROOT = os.path.join(RAIZ, "data", "raw", "acervo")


def norm(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--empresa", help="id ou parte do nome (axia, cemig, copel, cpfl, neoenergia, equatorial, energisa, engie, isa_energia, eneva, taesa)")
    ap.add_argument("--categoria", help="financeiro, sustentabilidade, investimento, governanca, divida")
    ap.add_argument("--tipo", help="parte do nome do tipo de documento (ex.: dfp, fato relevante, referencia)")
    ap.add_argument("--ano", help="ano (2020) ou intervalo (2015-2020)")
    ap.add_argument("--texto", help="procura no assunto do documento")
    ap.add_argument("--todos", action="store_true", help="inclui documentos não baixados")
    a = ap.parse_args()
    m = pd.read_csv(os.path.join(ROOT, "_indice", "manifesto.csv"), dtype={"ano": "Int64"})
    if not a.todos: m = m[m.status == "ok"]
    if a.empresa: m = m[m.empresa_id.map(norm).str.contains(norm(a.empresa)) | m.empresa.map(norm).str.contains(norm(a.empresa))]
    if a.categoria: m = m[m.categoria.map(norm).str.contains(norm(a.categoria))]
    if a.tipo: m = m[m.subcategoria.map(norm).str.contains(norm(a.tipo)) | m.caminho.fillna("").str.contains(norm(a.tipo).replace(" ", "_"))]
    if a.ano:
        lo, _, hi = a.ano.partition("-")
        m = m[(m.ano >= int(lo)) & (m.ano <= int(hi or lo))]
    if a.texto: m = m[m.assunto.fillna("").map(norm).str.contains(norm(a.texto))]
    for r in m.itertuples():
        print(f"{r.ano}\t{r.empresa_id}\t{r.subcategoria[:45]:45}\t{r.caminho}")
    print(f"\n{len(m)} documento(s)")


if __name__ == "__main__":
    main()

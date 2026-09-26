"""Confere o placar extraído (data/placar.duckdb) contra o gabarito conhecido (researches/FINDINGS-claude-sonnet-5.md
§3.2) e escreve um relatório de conferência em Markdown. Serve de teste de qualidade da extração: mostra, por empresa e
escopo, o valor extraído (com página), o valor-gabarito e o veredito (bate / diverge / faltou), com tolerância.

Uso: python data/conferir_placar.py            # imprime e grava .runtime/relatorios/conferencia_placar.md
"""
import os
import duckdb

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLACAR = os.path.join(RAIZ, "data", "placar.duckdb")
SAIDA = os.path.join(RAIZ, ".runtime", "relatorios", "conferencia_placar.md")

# Gabarito de emissões (tCO2e) do §3.2, por (empresa contém, ano): {escopo: valor}. None = declarado ausente ("—"/n/d).
GABARITO = {
    ("Engie", 2024): {"1": 17361.38, "2": None, "3": 242514.38},
    ("Cemig", 2024): {"1": 42860.81, "2": 376174.25, "3": 5911209.35},
    ("Auren", 2024): {"1": 12597.6, "2": 1561.2, "3": 1607.1},
    ("ISA", 2024): {"1": 14455.0, "2": None, "3": 2774.0},
    ("Neoenergia", 2024): {"1": 108284.0, "2": 415898.0, "3": 2023488.0},
    ("Taesa", 2024): {"1": 9367.51, "2": 77270.32},
    ("Eneva", 2025): {"1": 5800000.0},
}
TOLERANCIA = 0.02  # 2%


def _bate(extraido, gabarito) -> bool:
    if gabarito is None:
        return extraido is None
    if extraido is None:
        return False
    base = max(abs(gabarito), 1.0)
    return abs(extraido - gabarito) / base <= TOLERANCIA


def conferir() -> str:
    con = duckdb.connect(PLACAR, read_only=True)
    linhas = ["# Conferência do Placar — emissões vs. gabarito (§3.2)", "",
              f"Tolerância de {TOLERANCIA:.0%}. Extraído de `placar.duckdb`; gabarito de "
              "`researches/FINDINGS-claude-sonnet-5.md §3.2`.", "",
              "| Empresa (gabarito) | Ano | Escopo | Extraído (tCO2e) | Pág. | Gabarito | Veredito |",
              "|---|---|---|---:|---|---:|---|"]
    acertos = divergencias = faltas = 0
    for (empresa, ano), escopos in GABARITO.items():
        for escopo, esperado in escopos.items():
            r = con.execute("""
                SELECT tco2e, pagina FROM esg_emissoes
                WHERE strip_accents(lower(empresa)) LIKE '%' || strip_accents(lower(?)) || '%'
                  AND ano_relatorio = ? AND escopo = ? AND confianca > 0
                ORDER BY tco2e DESC LIMIT 1""", [empresa, ano, escopo]).fetchone()
            extraido, pagina = (r[0], r[1]) if r else (None, None)
            if _bate(extraido, esperado):
                veredito, acertos = "✅ bate", acertos + 1
            elif extraido is None:
                veredito, faltas = "⬜ faltou", faltas + 1
            else:
                veredito, divergencias = "⚠️ diverge", divergencias + 1
            g = "ausente" if esperado is None else f"{esperado:,.0f}".replace(",", ".")
            e = "—" if extraido is None else f"{extraido:,.0f}".replace(",", ".")
            linhas.append(f"| {empresa} | {ano} | {escopo} | {e} | {pagina or '—'} | {g} | {veredito} |")
    total = acertos + divergencias + faltas
    linhas += ["", f"**Resumo:** {acertos}/{total} batem, {divergencias} divergem, {faltas} faltaram.", "",
               "Divergências e faltas não são necessariamente erro: a base tem edições/anos diferentes do gabarito "
               "(que veio de outro conjunto de documentos). Cada valor extraído tem página e trecho para conferência "
               "manual."]
    con.close()
    return "\n".join(linhas) + "\n"


if __name__ == "__main__":
    texto = conferir()
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write(texto)
    print(texto)
    print(f"\nok: {SAIDA}")

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
              "| Empresa (gabarito) | Ano | Escopo | Extraído (tCO2e) | Edição/pág. | Gabarito | Veredito |",
              "|---|---|---|---:|---|---:|---|"]
    acertos = divergencias = faltas = rejeitados = 0
    for (empresa, ano), escopos in GABARITO.items():
        for escopo, esperado in escopos.items():
            # o gabarito é por ano do dado; o relatório que o traz é do mesmo ano ou do seguinte. escopo 2 por
            # mercado (2_mercado) conta como escopo 2. A ordem prefere o valor com fonte confirmada e, entre eles, o
            # da edição do próprio ano do gabarito (a mesma de onde ele veio).
            r = con.execute("""
                SELECT tco2e, pagina, ano_relatorio, confianca FROM esg_emissoes
                WHERE strip_accents(lower(empresa)) LIKE '%' || strip_accents(lower(?)) || '%'
                  AND replace(escopo, '_mercado', '') = ?
                  AND (coalesce(ano, ano_relatorio) = ? OR ano_relatorio = ? + 1)
                ORDER BY confianca DESC, (coalesce(ano, ano_relatorio) = ?) DESC, tco2e DESC
                LIMIT 1""", [empresa, escopo, ano, ano, ano]).fetchone()
            extraido, pagina, edicao, confianca = r if r else (None, None, None, None)
            if confianca == 0:   # extraído, mas a checagem "o valor aparece na página?" reprovou: não entra na base
                veredito, rejeitados = "⛔ rejeitado na fonte", rejeitados + 1
                extraido = None
            elif _bate(extraido, esperado):
                veredito, acertos = "✅ bate", acertos + 1
            elif extraido is None:
                veredito, faltas = "⬜ faltou", faltas + 1
            else:
                veredito, divergencias = "⚠️ diverge", divergencias + 1
            g = "ausente" if esperado is None else f"{esperado:,.0f}".replace(",", ".")
            e = "—" if extraido is None else f"{extraido:,.0f}".replace(",", ".")
            onde = f"{edicao} p.{pagina}" if pagina else "—"
            linhas.append(f"| {empresa} | {ano} | {escopo} | {e} | {onde} | {g} | {veredito} |")
    total = acertos + divergencias + faltas + rejeitados
    linhas += ["", f"**Resumo:** {acertos}/{total} batem, {divergencias} divergem, {faltas} faltaram, "
                   f"{rejeitados} rejeitados na checagem de fonte.", "",
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

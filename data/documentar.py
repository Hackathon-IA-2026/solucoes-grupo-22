#!/usr/bin/env python3
"""Gera data/DADOS.md, a documentação das tabelas do banco, a partir do catálogo e do esquema de data/coppezip.duckdb.

Uso: python data/documentar.py      (depois de data/construir.py)
Descrição, fonte e ressalvas vêm do catálogo, o mesmo texto que o modelo lê: para mudar o texto, mude o catálogo em
data/construir.py e construa de novo.
"""
import datetime
import os

import duckdb

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raiz do repositório


AQUI = os.path.dirname(os.path.abspath(__file__))

con = duckdb.connect(os.path.join(RAIZ, "data", "coppezip.duckdb"), read_only=True)
catalogo = con.execute("SELECT tabela, descricao, fonte, ressalvas, linhas FROM catalogo ORDER BY tabela").fetchall()
tipos = dict(con.execute("SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = 'main'").fetchall())
colunas = {}
for t, c, tipo in con.execute("SELECT table_name, column_name, data_type FROM information_schema.columns "
                              "WHERE table_schema = 'main' ORDER BY table_name, ordinal_position").fetchall():
    colunas.setdefault(t, []).append((c, tipo))
con.close()


def celula(x):
    return str(x or "").replace("|", "\\|").replace("\n", " ")


def tamanho(t, n):
    if tipos.get(t) == "VIEW":
        return "visão"
    return f"{n:,}".replace(",", ".") if n is not None else "—"


texto = ["# Dados do CoppeZIP", "",
         f"Tabelas e visões do `coppezip.duckdb` em {datetime.date.today():%d/%m/%Y}, geradas do catálogo por "
         "`data/documentar.py`. Não edite à mão: descrição, fonte e ressalvas vêm do catálogo em `data/construir.py`, o "
         "mesmo texto que o modelo lê. O formato dos arquivos brutos de cada fonte está em `data/raw/README.md`.", "",
         "| Tabela | Linhas | Descrição | Fonte |", "|---|---:|---|---|"]
texto += [f"| [`{t}`](#{t}) | {tamanho(t, n)} | {celula(d)} | {celula(f)} |" for t, d, f, _, n in catalogo]
for t, d, f, r, n in catalogo:
    texto += ["", f"## {t}", "", celula(d), "", f"- Fonte: {celula(f)}", f"- Linhas: {tamanho(t, n)}"]
    if r:
        texto.append(f"- Ressalvas: {celula(r)}")
    texto += ["", "| Coluna | Tipo |", "|---|---|"] + [f"| `{c}` | {tipo} |" for c, tipo in colunas.get(t, [])]
sem_catalogo = sorted(set(tipos) - {t for t, *_ in catalogo} - {"catalogo"})
if sem_catalogo:
    texto += ["", "## Sem descrição no catálogo", "",
              "O modelo não vê a descrição destas tabelas; acrescente-as ao catálogo em `data/construir.py`:", ""]
    texto += [f"- `{t}`" for t in sem_catalogo]
with open(os.path.join(AQUI, "DADOS.md"), "w") as saida:
    saida.write("\n".join(texto) + "\n")
print(f"{os.path.join(AQUI, "DADOS.md")}: {len(catalogo)} tabelas e visões" + (f", {len(sem_catalogo)} sem catálogo" if sem_catalogo else ""))

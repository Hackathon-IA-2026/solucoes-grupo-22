"""Organiza os documentos por área, empresa e ano em data/raw, como em data/raw/README.md, e atualiza data/documentos.csv:
  data/raw/sustentabilidade/<empresa>/<ano>/<arquivo>.pdf
  data/raw/financeiro/<empresa>/pdfs/<ano>/<arquivo>.pdf
  data/raw/<area>/<empresa>/tabulares/<tipo>/<arquivo>        (só com --hackathon)

Uso: python data/organizar.py [--hackathon PASTA] [--valer]
Sem --valer só mostra o que faria. A área e a empresa vêm da coluna arquivo do CSV (<area>/<empresa>/...), o ano da
coluna ano. --hackathon é a pasta dados_hackathon (<empresa>/<n>_<categoria>/<tipo>/...), de onde vêm os arquivos
tabulares por empresa (zips de ITR e DFP da CVM, planilhas). O PDF das demonstrações que vem dentro de cada zip de ITR ou
DFP é extraído para financeiro/<empresa>/pdfs/<ano>/ e entra no CSV. Idempotente: o que já está no lugar fica.
"""
import argparse
import collections
import csv
import io
import os
import re
import shutil
import zipfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raiz do repositório
RAW = os.path.join(RAIZ, "data", "raw")
CSV = os.path.join(RAIZ, "data", "documentos.csv")
AREAS = ("financeiro", "sustentabilidade")
ORIGENS = ("documentos", "pdfs_esg") + AREAS  # onde os PDFs podem estar hoje
TABULARES = (".zip", ".csv", ".xls", ".xlsx", ".parquet")
CATEGORIAS = {"1_financeiro": "financeiro", "2_sustentabilidade": "sustentabilidade"}  # as que trazem tabulares
DEMONSTRACOES = {"dfp": "DFP (demonstrações financeiras anuais)", "itr": "ITR (informações trimestrais)"}


def caminho(relativo: str) -> str:
    return os.path.join(RAW, *relativo.split("/"))


def destino(area: str, empresa: str, ano: str, nome: str) -> str:
    if area == "financeiro":
        return f"financeiro/{empresa}/pdfs/{ano}/{nome}"
    return f"sustentabilidade/{empresa}/{ano}/{nome}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hackathon", help="pasta dados_hackathon com <empresa>/<n>_<categoria>/<tipo>/")
    ap.add_argument("--valer", action="store_true", help="move de fato (sem isso só simula)")
    a = ap.parse_args()

    achados = collections.defaultdict(list)  # nome do PDF -> caminhos relativos onde está hoje
    for origem in ORIGENS:
        for pasta, _, arquivos in os.walk(os.path.join(RAW, origem)):
            for nome in arquivos:
                if nome.endswith(".pdf"):
                    achados[nome].append(os.path.relpath(os.path.join(pasta, nome), RAW).replace(os.sep, "/"))
    repetidos = {n: c for n, c in achados.items() if len(c) > 1}
    if repetidos:
        raise SystemExit(f"PDF com o mesmo nome em mais de um lugar, resolva antes: {list(repetidos.items())[:5]}")

    with open(CSV, encoding="utf-8", newline="") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    colunas = list(linhas[0])
    movimentos, ausentes = [], []
    for l in linhas:
        partes = l["arquivo"].split("/")
        if len(partes) < 3 or partes[0] not in AREAS:
            raise SystemExit(f"arquivo precisa começar por <area>/<empresa>/ (area: {', '.join(AREAS)}): {l['arquivo']}")
        nome = partes[-1]
        l["arquivo"] = destino(partes[0], partes[1], l["ano"], nome)
        if nome not in achados:
            ausentes.append(l["arquivo"])
        elif achados[nome][0] != l["arquivo"]:
            movimentos.append((caminho(achados[nome][0]), caminho(l["arquivo"])))

    tabulares = []
    if a.hackathon:
        for empresa in sorted(os.listdir(a.hackathon)):
            for categoria, area in CATEGORIAS.items():
                base = os.path.join(a.hackathon, empresa, categoria)
                if not os.path.isdir(base):
                    continue
                for tipo in sorted(os.listdir(base)):
                    for nome in sorted(os.listdir(os.path.join(base, tipo))):
                        if nome.lower().endswith(TABULARES):
                            alvo = caminho(f"{area}/{empresa}/tabulares/{tipo}/{nome}")
                            if not os.path.exists(alvo):
                                tabulares.append((os.path.join(base, tipo, nome), alvo))

    # PDF das demonstrações dentro dos zips de DFP e ITR (os já em tabulares/ e os que vão para lá)
    no_csv = {l["arquivo"] for l in linhas}
    cadastro = {l["arquivo"].split("/")[1]: (l["empresa"], l["cnpj"]) for l in linhas}
    zips = [os.path.join(pasta, n) for pasta, _, ns in os.walk(os.path.join(RAW, "financeiro"))
            if os.path.basename(pasta) in DEMONSTRACOES and os.path.basename(os.path.dirname(pasta)) == "tabulares"
            for n in ns if n.endswith(".zip")]
    zips += [o for o, alvo in tabulares if os.path.basename(os.path.dirname(alvo)) in DEMONSTRACOES
             and alvo.startswith(os.path.join(RAW, "financeiro"))]
    extracoes = []  # (zip em tabulares/, pdf de dentro, destino relativo)
    for z in sorted(zips):
        nome = os.path.basename(z)
        tipo = os.path.basename(os.path.dirname(z))
        m = re.fullmatch(r"(\d{4})_([a-z_]+?)_(\d{8})_[0-9a-f]{10}\.zip", nome)
        if not m or m.group(2) not in cadastro:
            print(f"aviso: {nome} fora do padrão <ano>_<empresa>_<data>_<hash>.zip, fica de fora")
            continue
        ano, empresa, entrega = m.groups()
        relativo = f"financeiro/{empresa}/pdfs/{ano}/{nome[:-4]}.pdf"
        if relativo in no_csv:
            continue
        with zipfile.ZipFile(z) as arquivo_zip:
            pdfs = [n for n in arquivo_zip.namelist() if n.lower().endswith(".pdf")]
        if len(pdfs) != 1:
            print(f"aviso: {nome} tem {len(pdfs)} PDFs, fica de fora")
            continue
        extracoes.append((caminho(f"financeiro/{empresa}/tabulares/{tipo}/{nome}"), pdfs[0], relativo))
        linhas.append({"arquivo": relativo, "empresa": cadastro[empresa][0], "cnpj": cadastro[empresa][1], "ano": ano,
                       "tipo": tipo, "titulo": f"{DEMONSTRACOES[tipo]} {ano}, entregue à CVM em "
                                            f"{entrega[6:]}/{entrega[4:6]}/{entrega[:4]}", "url": ""})

    por_pasta = collections.Counter("/".join(l["arquivo"].split("/")[:2]) for l in linhas)
    no_lugar = len(no_csv) - len(movimentos) - len(ausentes)
    print(f"{len(no_csv)} documentos no CSV: {len(movimentos)} a mover, {len(ausentes)} sem PDF, {no_lugar} já no lugar")
    for pasta, n in sorted(por_pasta.items()):
        print(f"  {pasta}: {n}")
    print(f"{len(tabulares)} arquivos tabulares a mover para <area>/<empresa>/tabulares/")
    for origem, alvo in movimentos[:3] + tabulares[:3]:
        print(f"  {os.path.relpath(origem, RAIZ)} -> {os.path.relpath(alvo, RAIZ)}")
    print(f"{len(extracoes)} PDFs de demonstrações a extrair dos zips de DFP e ITR para o CSV")
    for z, _, relativo in extracoes[:3]:
        print(f"  {os.path.basename(z)} -> data/raw/{relativo}")
    if ausentes:
        print("no CSV mas sem PDF:", ", ".join(ausentes))
    if not a.valer:
        print("simulação: nada foi movido; rode de novo com --valer")
        return

    for origem, alvo in movimentos + tabulares:
        os.makedirs(os.path.dirname(alvo), exist_ok=True)
        shutil.move(origem, alvo)
    for z, interno, relativo in extracoes:  # os zips já estão em tabulares/ depois dos movimentos acima
        os.makedirs(os.path.dirname(caminho(relativo)), exist_ok=True)
        with zipfile.ZipFile(z) as arquivo_zip, arquivo_zip.open(interno) as f, open(caminho(relativo), "wb") as saida_pdf:
            shutil.copyfileobj(f, saida_pdf)
    saida = io.StringIO()
    escritor = csv.DictWriter(saida, colunas, delimiter=";", lineterminator="\n")
    escritor.writeheader()
    escritor.writerows(sorted(linhas, key=lambda l: l["arquivo"]))
    with open(CSV, "w", encoding="utf-8", newline="") as f:
        f.write(saida.getvalue())
    for origem in ("documentos", "pdfs_esg"):  # pastas antigas: só apaga as que ficaram vazias
        for pasta, _, _ in sorted(os.walk(os.path.join(RAW, origem)), key=lambda p: -len(p[0])):
            if not os.listdir(pasta):
                os.rmdir(pasta)
    print(f"movidos {len(movimentos)} PDFs e {len(tabulares)} tabulares, extraídos {len(extracoes)} PDFs de "
          "demonstrações; documentos.csv atualizado")


if __name__ == "__main__":
    main()

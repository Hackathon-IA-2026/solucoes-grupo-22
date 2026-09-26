"""Baixa os zips de dados abertos da CVM (DFP 2010+, ITR 2011+) e grava só as 11 empresas em dados_estruturados/.

Saída: dados_estruturados/{dfp,itr}/<demonstracao>_<con|ind>.csv com todos os anos empilhados
(BPA, BPP, DRE, DRA, DFC_MD, DFC_MI, DMPL, DVA), separador ';' e UTF-8.
Uso:  python data/acervo/dados_estruturados.py
"""
import io, os, re, tempfile, zipfile
import pandas as pd, requests

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # raiz do repositório
OUT = os.path.join(RAIZ, "data", "raw", "acervo", "dados_estruturados")
BASE = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/{k}/DADOS/{k2}_cia_aberta_{y}.zip"
CNPJS = {"00.001.180/0001-26": "axia", "17.155.730/0001-64": "cemig", "76.483.817/0001-20": "copel",
         "02.429.144/0001-93": "cpfl", "01.083.200/0001-18": "neoenergia", "03.220.438/0001-73": "equatorial",
         "00.864.214/0001-06": "energisa", "02.474.103/0001-19": "engie", "02.998.611/0001-04": "isa_energia",
         "04.423.567/0001-21": "eneva", "07.859.971/0001-30": "taesa"}  # EMPRESA_ID estável: DENOM_CIA muda com as trocas de nome
YEARS = {"DFP": range(2010, 2027), "ITR": range(2011, 2027)}


def main():
    for kind, years in YEARS.items():
        d = os.path.join(OUT, kind.lower())
        os.makedirs(d, exist_ok=True)
        acc = {}
        for y in years:
            url = BASE.format(k=kind, k2=kind.lower(), y=y)
            with tempfile.TemporaryFile() as tmp:
                with requests.get(url, stream=True, timeout=(30, 600)) as r:
                    r.raise_for_status()
                    for c in r.iter_content(1 << 20): tmp.write(c)
                tmp.seek(0)
                z = zipfile.ZipFile(tmp)
                for name in z.namelist():
                    m = re.match(rf"{kind.lower()}_cia_aberta_(.+)_{y}\.csv$", name)
                    if not m: continue  # o índice geral (sem sufixo) já está em _indice
                    key = m.group(1)
                    df = pd.read_csv(io.BytesIO(z.read(name)), sep=";", encoding="latin1", dtype=str)
                    df = df[df.CNPJ_CIA.isin(CNPJS)]
                    df.insert(0, "EMPRESA_ID", df.CNPJ_CIA.map(CNPJS))
                    acc.setdefault(key, []).append(df)
            print(kind, y, "ok", flush=True)
        for key, frames in acc.items():
            out = pd.concat(frames, ignore_index=True)
            out.to_csv(os.path.join(d, f"{key}.csv"), sep=";", index=False, encoding="utf-8")
            print(kind, key, len(out), flush=True)


if __name__ == "__main__":
    main()

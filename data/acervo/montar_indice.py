"""Gera _indice/manifesto.csv (1 linha por documento do núcleo, com caminho local) e _indice/empresas.csv.

Rode depois de baixar_nucleo.py (pode rodar a qualquer momento; documentos ainda não baixados ficam com status 'pendente').
Uso:  python data/acervo/montar_indice.py
"""
import json, os
import pandas as pd
from baixar_nucleo import CAT_SLUG, EMP_SLUG, IDX, LOG, ROOT, doc_id

EMPRESAS = [
    ("axia", "Axia Energia (ex-Eletrobras)", "00.001.180/0001-26", "2437", "1439124", "AXIA3; AXIA7",
     "Centrais Elétricas Brasileiras S.A. (Eletrobras); Brazilian Electric Power Co", "Geração + transmissão", "Privatizada em 2022; renomeada Axia em out/2025"),
    ("cemig", "Cemig", "17.155.730/0001-64", "2453", "1157557", "CMIG3; CMIG4",
     "Companhia Energética de Minas Gerais; Energy Co of Minas Gerais", "Integrada", "Estatal (MG); controla em conjunto a Taesa"),
    ("copel", "Copel", "76.483.817/0001-20", "14311", "1041792", "CPLE3",
     "Companhia Paranaense de Energia; Energy Co of Parana", "Integrada", "Privatizada em 2023"),
    ("cpfl", "CPFL Energia", "02.429.144/0001-93", "18660", "1300482", "CPFE3",
     "CPFL Energy Inc (SEC)", "Integrada", "Controlada pela State Grid; registro SEC cancelado em 2020"),
    ("neoenergia", "Neoenergia", "01.083.200/0001-18", "15539", "", "NEOE3", "", "Integrada", "Controlada pela Iberdrola"),
    ("equatorial", "Equatorial", "03.220.438/0001-73", "20010", "", "EQTL3", "Equatorial Energia S.A.",
     "Distribuição + transmissão", "Distribuidoras com CNPJ próprio (fora deste acervo)"),
    ("energisa", "Energisa", "00.864.214/0001-06", "15253", "", "ENGI3; ENGI4; ENGI11", "", "Distribuição",
     "Distribuidoras com registro próprio na CVM (fora deste acervo)"),
    ("engie", "Engie Brasil Energia", "02.474.103/0001-19", "17329", "", "EGIE3",
     "Gerasul; Tractebel Energia S.A. (até 2016)", "Geração renovável + transmissão", ""),
    ("isa_energia", "ISA Energia Brasil (ex-CTEEP)", "02.998.611/0001-04", "18376", "", "ISAE3; ISAE4",
     "CTEEP - Cia de Transmissão de Energia Elétrica Paulista; ISA CTEEP", "Transmissão", "Receita via RAP"),
    ("eneva", "Eneva", "04.423.567/0001-21", "21237", "", "ENEV3", "MPX Energia S.A. (até 2013)", "Térmica a gás", ""),
    ("taesa", "Taesa", "07.859.971/0001-30", "20257", "", "TAEE3; TAEE4; TAEE11",
     "Transmissora Aliança de Energia Elétrica S.A.; Terna Participações S.A. (até 2009)", "Transmissão",
     "Controle compartilhado Cemig + ISA; receita via RAP"),
]


def observacoes(m):
    """Marca problemas conhecidos: links mortos, arquivos vazios na origem, páginas HTML no lugar do relatório, duplicatas."""
    obs = pd.Series("", index=m.index, dtype=object)
    ok = m.status == "ok"
    obs[m.status == "erro"] = "link quebrado na origem (404, domínio inexistente ou conexão recusada)"
    obs[ok & m.extensao.isin([".htm", ".html"]) & ~m.fonte.str.startswith("SEC")] = \
        "página HTML no lugar do relatório (relatório online/Flash ou link para a home); conteúdo não recuperado"
    obs[ok & m.fonte.str.startswith("SEC") & (m.bytes_local < 1000)] = "entregue em papel à SEC; o EDGAR só tem este aviso"
    blank = ok & (m.extensao == ".pdf") & (m.bytes_local <= 2048)
    obs[blank] = "PDF em branco na origem"
    first = m[ok].drop_duplicates("sha256").set_index("sha256").doc_id
    dup = ok & m.sha256.duplicated(keep="first") & (obs == "")
    obs[dup] = "duplicata idêntica de " + m.loc[dup, "sha256"].map(first)
    return obs


def main():
    df = pd.read_csv(os.path.join(IDX, "checklist_documentos.csv"), dtype={"ano": "Int64"})
    df = df[df.categoria.isin(CAT_SLUG)].copy()
    df["doc_id"] = df.link.map(doc_id)
    df = df.drop_duplicates("doc_id")
    log = {}
    if os.path.exists(LOG):
        for line in open(LOG, encoding="utf-8"):
            j = json.loads(line)
            if j["status"] == "ok" or j["doc_id"] not in log:
                log[j["doc_id"]] = j
    lg = pd.DataFrame(log.values()) if log else pd.DataFrame(columns=["doc_id", "status", "caminho", "bytes", "sha256", "erro"])
    for c in ["caminho", "bytes", "sha256", "erro"]:
        if c not in lg: lg[c] = None
    m = df.merge(lg[["doc_id", "status", "caminho", "bytes", "sha256", "erro"]].rename(columns={"bytes": "bytes_local"}),
                 on="doc_id", how="left")
    m["status"] = m.status.fillna("pendente")
    m["empresa_id"] = m.empresa.map(EMP_SLUG)
    m["extensao"] = m.caminho.str.extract(r"(\.[a-z0-9]+)$")[0]
    m["observacao"] = observacoes(m)
    cols = ["doc_id", "empresa_id", "empresa", "categoria", "subcategoria", "ano", "data_referencia", "data_entrega",
            "fonte", "assunto", "caminho", "extensao", "bytes_local", "sha256", "link", "status", "observacao", "erro"]
    m = m[cols].sort_values(["empresa_id", "categoria", "subcategoria", "ano", "data_entrega"])
    m.to_csv(os.path.join(IDX, "manifesto.csv"), index=False, encoding="utf-8-sig")
    pd.DataFrame(EMPRESAS, columns=["empresa_id", "empresa", "cnpj", "codigo_cvm", "cik_sec", "tickers",
                                    "nomes_anteriores", "segmento", "observacoes"]).to_csv(
        os.path.join(IDX, "empresas.csv"), index=False, encoding="utf-8-sig")
    print(m.status.value_counts().to_string())
    ok = m[m.status == "ok"]
    print(f"baixados: {len(ok)} arquivos, {ok.bytes_local.sum()/1e9:.2f} GB")
    return m


if __name__ == "__main__":
    main()

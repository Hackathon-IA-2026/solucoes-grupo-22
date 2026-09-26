"""Acrescenta as linhas da Taesa ao _indice/checklist_documentos.csv (levantamento feito em set/2026).

Usa as mesmas regras do levantamento das outras 10 empresas:
- CVM/DFP, CVM/ITR, CVM/FRE, CVM/FCA: última versão de cada data de referência, a partir dos índices de dados abertos.
- CVM/IPE: todos os documentos, menos "Valores Mobiliários negociados e detidos" e "Contratos de Indenidade".
  A subcategoria é a Categoria do IPE, com as exceções de subcat_ipe(); a categoria (1-7) vem do próprio checklist.
- Site RI: relatórios de sustentabilidade listados em RELATORIOS_RI (https://ri.taesa.com.br/sustentabilidade/visao-geral/).
- bytes: média da subcategoria no checklist ("estimado"), ou tamanho exato para o site de RI.

Pode rodar de novo: as linhas da Taesa são substituídas, as das outras empresas ficam como estão.
Uso:  python data/acervo/checklist_taesa.py [--cache PASTA_COM_ZIPS_DA_CVM]
"""
import argparse, io, os, re, zipfile
import pandas as pd, requests

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # raiz do repositório
CHECKLIST = os.path.join(RAIZ, "data", "raw", "acervo", "_indice", "checklist_documentos.csv")
EMPRESA, CNPJ = "Taesa", "07.859.971/0001-30"
BASE = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/{k}/DADOS/{k2}_cia_aberta_{y}.zip"
ANOS = {"IPE": range(2003, 2027), "DFP": range(2010, 2027), "ITR": range(2011, 2027),
        "FRE": range(2010, 2027), "FCA": range(2010, 2027)}
ESTRUTURADOS = {  # fonte -> (categoria, subcategoria)
    "DFP": ("1. Financeiro", "DFP (demonstrações anuais padronizadas CVM)"),
    "ITR": ("1. Financeiro", "ITR (demonstrações trimestrais CVM)"),
    "FRE": ("4. Governança", "Formulário de Referência (FRE)"),
    "FCA": ("4. Governança", "Formulário Cadastral (FCA)"),
}
IPE_FORA = {"Valores Mobiliários negociados e detidos (art. 11 da Instr. CVM nº 358)", "Contratos de Indenidade"}
RELATORIOS_RI = [  # (ano, título no site, link)
    (2015, "Relatório 2015", "https://ri.taesa.com.br/wp-content/uploads/2019/05/APLPAC7527_TAESA_RSA_2015_A.pdf"),
    (2016, "Relatório 2016", "https://ri.taesa.com.br/wp-content/uploads/2019/05/APLPAC7527_TAESA_RSA_2016_A.pdf"),
    (2017, "Relatório 2017", "https://ri.taesa.com.br/wp-content/uploads/2019/03/Relat%C3%B3rio-Socioambiental-Aneel-TAESA-2017-2018-V-F-Web.pdf"),
    (2018, "Relatório 2018", "https://ri.taesa.com.br/wp-content/uploads/2019/04/TAESA_RL-Anual_2018-2019-Rev1-WEB.pdf"),
    (2019, "Relatório 2019", "https://ri.taesa.com.br/wp-content/uploads/2018/11/Taesa_Relat%C3%B3rio-2019_digital_alta_site.pdf"),
    (2020, "Relatório 2020", "https://ri.taesa.com.br/wp-content/uploads/2020/05/Relatorio-Taesa-2020_final.pdf"),
    (2021, "Relatório de Sustentabilidade 2021", "https://institucional.taesa.com.br/wp-content/uploads/2022/05/Relatorio-Taesa-2022-alta.pdf"),
    (2022, "Relatório de Sustentabilidade 2022", "https://ri.taesa.com.br/wp-content/uploads/2023/05/Relatorio-Taesa_2023_02-05-2023.pdf"),
    (2023, "Relatório de Sustentabilidade 2023", "https://ri.taesa.com.br/wp-content/uploads/2018/11/Taesa_Relatorio-2023_02-05-2024_alta.pdf"),
    (2024, "Relatório de Sustentabilidade 2024", "https://ri.taesa.com.br/wp-content/uploads/2018/11/TAESA-Relatorio-de-Sustentabilidade-2024.pdf"),
    (2025, "Relatório de Sustentabilidade 2025", "https://ri.taesa.com.br/wp-content/uploads/2018/11/Relatorio-de-Sustentabilidade-da-TAESA-2025.pdf"),
]
H_WEB = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
COLS = ["empresa", "categoria", "subcategoria", "ano", "data_referencia", "data_entrega", "fonte", "assunto", "link",
        "bytes", "tamanho_tipo"]


def ler_indice(kind, y, cache):
    """Lê o(s) CSV(s) de índice de um zip anual da CVM (do cache, se houver)."""
    nome = f"{kind.lower()}_cia_aberta_{y}.zip"
    local = os.path.join(cache, nome) if cache else None
    if local and os.path.exists(local):
        z = zipfile.ZipFile(local)
    else:
        r = requests.get(BASE.format(k=kind, k2=kind.lower(), y=y), timeout=(30, 600))
        if r.status_code == 404:
            return None
        r.raise_for_status()
        if local:
            with open(local, "wb") as f: f.write(r.content)
        z = zipfile.ZipFile(io.BytesIO(r.content))
    alvo = f"{kind.lower()}_cia_aberta_{y}.csv"
    return pd.read_csv(io.BytesIO(z.read(alvo)), sep=";", encoding="latin1", dtype=str)


def subcat_ipe(r):
    if r.Categoria == "Dados Econômico-Financeiros" and isinstance(r.Tipo, str):
        return r.Tipo
    if r.Categoria == "Comunicado ao Mercado" and r.Tipo == "Apresentações a analistas/agentes do mercado":
        return "Apresentações a analistas (Investor Day/guidance)"
    if r.Categoria == "Assembleia" and r.Especie == "Proposta da Administração":
        return "Proposta da Administração (orçamento de capital/destinação)"
    return r.Categoria


def ano_de(ref, entrega):
    y = int(ref[:4])
    return int(entrega[:4]) if y > 2026 else y  # há datas de referência digitadas errado (ex.: 2902)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", help="pasta para guardar/reaproveitar os zips da CVM")
    a = ap.parse_args()
    if a.cache: os.makedirs(a.cache, exist_ok=True)
    chk = pd.read_csv(CHECKLIST, dtype={"ano": "Int64"})
    outros = chk[chk.empresa != EMPRESA]
    cat_da_sub = outros.drop_duplicates("subcategoria").set_index("subcategoria").categoria
    media = outros[outros.tamanho_tipo.str.startswith("estimado")].groupby("subcategoria").bytes.first()
    linhas = []

    for kind, (cat, sub) in ESTRUTURADOS.items():
        fr = [d for y in ANOS[kind] if (d := ler_indice(kind, y, a.cache)) is not None]
        d = pd.concat(fr, ignore_index=True)
        d = d[d.CNPJ_CIA == CNPJ].copy()
        d["v"] = d.VERSAO.astype(int)
        d = d.sort_values("v").drop_duplicates("DT_REFER", keep="last")
        for r in d.sort_values("DT_REFER").itertuples():
            linhas.append(dict(categoria=cat, subcategoria=sub, ano=int(r.DT_REFER[:4]), data_referencia=r.DT_REFER,
                               data_entrega=r.DT_RECEB, fonte=f"CVM/{kind}", assunto=None,
                               link=r.LINK_DOC.replace("http://", "https://")))
        print(kind, len(d), flush=True)

    fr = [d for y in ANOS["IPE"] if (d := ler_indice("IPE", y, a.cache)) is not None]
    ipe = pd.concat(fr, ignore_index=True)
    ipe = ipe[(ipe.CNPJ_Companhia == CNPJ) & ~ipe.Categoria.isin(IPE_FORA)].drop_duplicates("Link_Download")
    sem_cat = set()
    for r in ipe.sort_values(["Data_Entrega", "Data_Referencia"]).itertuples():
        sub = subcat_ipe(r)
        if sub not in cat_da_sub.index:
            sem_cat.add(sub); continue
        linhas.append(dict(categoria=cat_da_sub[sub], subcategoria=sub, ano=ano_de(r.Data_Referencia, r.Data_Entrega),
                           data_referencia=r.Data_Referencia, data_entrega=r.Data_Entrega, fonte="CVM/IPE",
                           assunto=r.Assunto, link=r.Link_Download))
    print("IPE", len(ipe), flush=True)
    if sem_cat:
        print("AVISO: subcategorias do IPE que não existem no checklist (ignoradas):", sorted(sem_cat))

    sub_ri = "Relatório anual / sustentabilidade / integrado (site RI)"
    for ano, titulo, link in RELATORIOS_RI:
        try:
            n = int(requests.head(link, headers=H_WEB, timeout=60, allow_redirects=True).headers.get("Content-Length", 0))
        except requests.RequestException:
            n = 0
        linhas.append(dict(categoria=cat_da_sub[sub_ri], subcategoria=sub_ri, ano=ano, data_referencia=f"{ano}-12-31",
                           data_entrega=None, fonte="Site RI", assunto=titulo, link=link,
                           bytes=float(n) if n else None, tamanho_tipo="exato" if n else "desconhecido"))

    novo = pd.DataFrame(linhas)
    novo.insert(0, "empresa", EMPRESA)
    est = novo.fonte != "Site RI"
    novo.loc[est, "bytes"] = novo.loc[est, "subcategoria"].map(media)
    novo.loc[est, "tamanho_tipo"] = "estimado (média da amostra)"
    novo = novo[COLS]
    out = pd.concat([outros, novo], ignore_index=True)
    out.to_csv(CHECKLIST, index=False, encoding="utf-8-sig")
    print(f"Taesa: {len(novo)} linhas no checklist")
    print(novo.groupby("categoria").size().to_string())


if __name__ == "__main__":
    main()

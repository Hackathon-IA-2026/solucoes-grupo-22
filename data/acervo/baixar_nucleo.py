"""Baixa os documentos do núcleo (categorias 1-5) listados em _indice/checklist_documentos.csv.

Pode ser interrompido e rodado de novo: o que já foi baixado (registrado em _indice/_log_download.jsonl) é pulado.
O acervo (índices, documentos e dados_estruturados/) fica em data/raw/acervo/, fora do git.
Uso:  python data/acervo/baixar_nucleo.py [--threads 6]
"""
import argparse, hashlib, json, os, re, sys, threading, time, unicodedata
from concurrent.futures import ThreadPoolExecutor
import pandas as pd, requests

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # raiz do repositório
ROOT = os.path.join(RAIZ, "data", "raw", "acervo")
IDX = os.path.join(ROOT, "_indice")
LOG = os.path.join(IDX, "_log_download.jsonl")
CA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "winroots.pem")

EMP_SLUG = {
    "Axia Energia (ex-Eletrobras)": "axia", "Cemig": "cemig", "Copel": "copel", "CPFL Energia": "cpfl",
    "Neoenergia": "neoenergia", "Equatorial": "equatorial", "Energisa": "energisa",
    "Engie Brasil Energia": "engie", "ISA Energia Brasil (ex-CTEEP)": "isa_energia", "Eneva": "eneva",
    "Taesa": "taesa",
}
CAT_SLUG = {"1. Financeiro": "1_financeiro", "2. Sustentabilidade": "2_sustentabilidade",
            "3. Investimento e alocação de capital": "3_investimento", "4. Governança": "4_governanca",
            "5. Dívida e crédito": "5_divida_credito"}
SUB_SLUG = {  # nomes curtos para as pastas mais usadas; o resto é gerado por slug()
    "DFP (demonstrações anuais padronizadas CVM)": "dfp", "ITR (demonstrações trimestrais CVM)": "itr",
    "Demonstrações Financeiras Anuais Completas": "df_anuais_completas",
    "Demonstrações Financeiras em Padrões Internacionais": "df_padroes_internacionais",
    "Demonstrações Financeiras Intermediárias": "df_intermediarias", "Demonstrações Financeiras Adicionais": "df_adicionais",
    "Relatório anual / sustentabilidade / integrado (site RI)": "relatorios_site_ri",
    "Formulário de Referência (FRE)": "formulario_referencia", "Formulário Cadastral (FCA)": "formulario_cadastral",
    "Apresentações a analistas (Investor Day/guidance)": "apresentacoes_investidores",
    "Proposta da Administração (orçamento de capital/destinação)": "proposta_administracao_orcamento",
    "SEC 20-F": "sec_20f", "SEC 20-F/A": "sec_20f", "SEC 20FR12B": "sec_20f", "SEC 20FR12B/A": "sec_20f",
}
EXT_BY_MAGIC = [(b"%PDF", ".pdf"), (b"PK", ".zip"), (b"\xd0\xcf\x11\xe0", ".doc")]
H_SEC = {"User-Agent": "CoppeZIP-research research-bot@example.org"}
H_WEB = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
lock = threading.Lock()
tls = threading.local()


def slug(s, n=40):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").lower()
    return s[:n].rstrip("_")


def session():
    if not hasattr(tls, "s"):
        tls.s = requests.Session()
    return tls.s


def doc_id(link):
    return hashlib.sha1(link.encode()).hexdigest()[:10]


def pick_ext(resp, first, link):
    cd = resp.headers.get("Content-Disposition", "")
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', cd, re.I)
    if m:
        ext = os.path.splitext(m.group(1).strip())[1].lower()
        if ext in (".pdf", ".zip", ".xlsx", ".xls", ".docx", ".doc", ".htm", ".html", ".txt", ".csv", ".epub", ".pptx"):
            return ext
    for magic, ext in EXT_BY_MAGIC:
        if first.startswith(magic):
            if ext == ".zip":
                u = link.lower().split("?")[0]
                for x in (".xlsx", ".docx", ".pptx", ".epub"):
                    if u.endswith(x): return x
            return ext
    u = link.lower().split("?")[0]
    ext = os.path.splitext(u)[1]
    if ext in (".htm", ".html", ".txt", ".xml"): return ext
    return ".htm" if first.lstrip()[:1] == b"<" else ".bin"


def target_dir(r):
    sub = SUB_SLUG.get(r.subcategoria) or slug(r.subcategoria)
    return os.path.join(ROOT, EMP_SLUG[r.empresa], CAT_SLUG[r.categoria], sub)


def base_name(r):
    ano = str(r.ano) if pd.notna(r.ano) else "sem_ano"
    data = r.data_entrega if isinstance(r.data_entrega, str) else (r.data_referencia if isinstance(r.data_referencia, str) else "")
    parts = [ano, EMP_SLUG[r.empresa], data.replace("-", "")]
    if isinstance(r.assunto, str) and r.assunto.strip():
        parts.append(slug(r.assunto, 45))
    parts.append(r.doc_id)
    return "_".join(p for p in parts if p)


def download(r):
    d = target_dir(r)
    os.makedirs(d, exist_ok=True)
    hdr = H_SEC if "sec.gov" in r.link else H_WEB
    last = None
    for attempt in range(4):
        try:
            verify = CA if os.path.exists(CA) else True
            try:
                resp = session().get(r.link, headers=hdr, timeout=(30, 600), stream=True, verify=verify)
            except requests.exceptions.SSLError:
                resp = session().get(r.link, headers=hdr, timeout=(30, 600), stream=True, verify=False)
            resp.raise_for_status()
            it = resp.iter_content(1 << 16)
            first = next(it, b"")
            ext = pick_ext(resp, first, r.link)
            path = os.path.join(d, base_name(r) + ext)
            h, n = hashlib.sha256(first), len(first)
            with open(path + ".part", "wb") as f:
                f.write(first)
                for chunk in it:
                    f.write(chunk); h.update(chunk); n += len(chunk)
            if n == 0:
                raise IOError("arquivo vazio")
            os.replace(path + ".part", path)
            return {"doc_id": r.doc_id, "status": "ok", "caminho": os.path.relpath(path, ROOT).replace("\\", "/"),
                    "bytes": n, "sha256": h.hexdigest(), "tipo_http": resp.headers.get("Content-Type", "")}
        except Exception as e:
            last = repr(e)[:300]
            time.sleep(5 * (attempt + 1))
    return {"doc_id": r.doc_id, "status": "erro", "erro": last}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, default=6)
    a = ap.parse_args()
    requests.packages.urllib3.disable_warnings()
    df = pd.read_csv(os.path.join(IDX, "checklist_documentos.csv"), dtype={"ano": "Int64"})
    df = df[df.categoria.isin(CAT_SLUG)].copy()
    df["doc_id"] = df.link.map(doc_id)
    df = df.drop_duplicates("doc_id")
    done = set()
    if os.path.exists(LOG):
        for line in open(LOG, encoding="utf-8"):
            j = json.loads(line)
            if j["status"] == "ok": done.add(j["doc_id"])
    todo = df[~df.doc_id.isin(done)]
    # SEC primeiro com poucas threads (limite de 10 req/s); o resto em paralelo
    print(f"total núcleo: {len(df)} | já baixados: {len(done)} | a baixar: {len(todo)}", flush=True)
    stats = {"ok": 0, "erro": 0, "bytes": 0}
    t0 = time.time()

    def job(r):
        res = download(r)
        with lock:
            with open(LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(res, ensure_ascii=False) + "\n")
            stats[res["status"]] += 1
            stats["bytes"] += res.get("bytes", 0)
            k = stats["ok"] + stats["erro"]
            if k % 50 == 0 or res["status"] == "erro":
                el = time.time() - t0
                print(f"[{k}/{len(todo)}] ok={stats['ok']} erro={stats['erro']} "
                      f"{stats['bytes']/1e9:.2f} GB  {stats['bytes']/1e6/max(el,1):.1f} MB/s"
                      + (f"  ERRO {r.link[:90]} {res.get('erro','')[:120]}" if res["status"] == "erro" else ""), flush=True)

    sec = [r for r in todo.itertuples() if "sec.gov" in r.link]
    rest = [r for r in todo.itertuples() if "sec.gov" not in r.link]
    with ThreadPoolExecutor(2) as ex: list(ex.map(job, sec))
    with ThreadPoolExecutor(a.threads) as ex: list(ex.map(job, rest))
    print("FIM", stats, f"{(time.time()-t0)/60:.1f} min", flush=True)


if __name__ == "__main__":
    main()

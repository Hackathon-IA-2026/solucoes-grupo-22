#!/usr/bin/env python3
"""Indexa neste nó todos os PDFs de data/raw: texto por página, trechos com embedding na GPU, parágrafos e BM25.

Uso: .runtime/venv/bin/python data/indexar_dados_local.py --gpu 0 --saida /local/<usuário>/.../docs_local.duckdb
     [--lote 256] [--leitores <núcleos>] [--limite N] [--tudo]
Entrada: todo PDF de data/raw — financeiro/<empresa>/pdfs/<ano>, sustentabilidade/<empresa>/<ano> (e referencias),
pdfs_esg e os dicionários de dados da ANEEL em aneel/<base>. Os metadados saem de data/documentos.csv pelo caminho ou,
quando o CSV aponta para a pasta organizada e o PDF só existe solto em pdfs_esg, pelo nome do arquivo; os dicionários da
ANEEL não estão no CSV e vêm de DICIONARIOS. O mesmo PDF sob dois caminhos entra uma vez, pelo caminho organizado.
Saída (--saida, sempre no disco local do nó: DuckDB no NFS trava): documentos, paginas, trechos (embedding FLOAT[1024]),
blocos (os parágrafos de cada página na ordem do PDF, para data/linha_do_tempo.py), meta e o índice de palavras,
trocados de forma atômica no fim. data/docs.duckdb é um link para esse arquivo no disco local.
Embeddings do intfloat/multilingual-e5-large na GPU --gpu (fp16, média dos tokens, norma 1) com o prefixo "passage: "
que o modelo exige — quem pergunta usa "query: ". Reaproveita do índice anterior o vetor de todo trecho igual (arquivo,
página e texto), então refazer o índice depois de baixar alguns PDFs custa minutos, não horas.
Os PDFs são lidos em vários processos (o pymupdf não solta o GIL) e os trechos vão à GPU em lotes; ver data/INDEXAR.md
para os comandos de rodar na kolyma (dona dos dados) ou num nó com a GPU livre, com os rsync de ida e de volta.
"""
import argparse
import csv
import hashlib
import os
import re
import shutil
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor

import duckdb
import numpy as np
import pyarrow as pa
import pymupdf as fitz
import torch
from transformers import AutoModel, AutoTokenizer

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raiz do repositório
AQUI = os.path.join(RAIZ, "data")
PDFS = os.path.join(AQUI, "raw")

MODELO = "intfloat/multilingual-e5-large"
PASTA_MODELO = os.path.join(AQUI, "modelos", "multilingual-e5-large-torch")
DIMENSOES, TOKENS = 1024, 512  # o e5-large devolve 1024 números e lê até 512 tokens
TAMANHO, SOBRA = 1200, 200  # caracteres por trecho e sobreposição
PREFIXO = "passage: "  # o e5 é treinado com prefixo: "passage: " no que é indexado, "query: " na pergunta
# o que muda o vetor: modelo, prefixo, pooling e o corte dos trechos. Vetor do índice anterior só serve se for igual.
ASSINATURA = f"{MODELO}|{PREFIXO}|media|norma1|{TOKENS}t|{TAMANHO}/{SOBRA}c"
LOTE = 256  # medido na RTX 5090 com trechos de 512 tokens: 195 trechos/s e 4,1 GiB. 512 rende 1% mais e dobra a memória
# memória de que o lote precisa, medida na mesma placa (2,6 GiB com lote 128, 13,1 GiB com 1024, estouro com 2048)
GPU_FIXA, GPU_POR_TRECHO, FOLGA = 1.2 * 2**30, 12 * 2**20, 1.3  # a placa é compartilhada: não encostar no limite
REDE = ("nfs", "nfs4", "cifs", "smb3", "fuse.sshfs")  # DuckDB sobre disco de rede trava: o banco vai no disco do nó

ORGANIZADAS = ("financeiro", "sustentabilidade")  # pastas de organizar.py: o caminho preferido de um PDF repetido
AREA_DICIONARIO = "dados"
TIPO_DICIONARIO = "dicionario_de_dados"
EMPRESA_DICIONARIO = "ANEEL (dicionário de dados)"  # não é empresa, mas linha_do_tempo.py precisa de um nome
DICIONARIOS = (  # os dicionários das bases da ANEEL que alimentam o coppezip.duckdb; não estão no documentos.csv
    "aneel/mmgd/dm-geracao-distribuida-relacao-de-empreendimentos.pdf",
    "aneel/ralie/dm-ralie-usina.pdf",
    "aneel/samp/dd-samp.pdf",
    "aneel/samp/dm-samp-balanco.pdf",
    "aneel/siget_rap/dm-siget-lista-modulos-previa-reajuste-rap.pdf",
    "aneel/societaria/dm-composicao-societaria-polimero.pdf",
)
# título dentro do próprio dicionário; o texto repete "Conjunto de Dados", e o que interessa é o que vem depois
CONJUNTO = re.compile(r"Conjunto de Dados\s+(?!Conjunto de Dados)(.{3,140}?)\s+Vis[ãa]o Geral", re.S)


def trechos(texto: str) -> list[str]:
    """Corta a página em trechos de ~1200 caracteres com sobreposição, no fim de linha ou de frase (igual ao antigo
    indexar_docs.py: mudar isto invalida os vetores já calculados)."""
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto).strip()
    if len(texto) < 80:
        return []
    partes, i = [], 0
    while i < len(texto):
        fim = min(len(texto), i + TAMANHO)
        if fim < len(texto):
            corte = max(texto.rfind("\n", i + TAMANHO // 2, fim), texto.rfind(". ", i + TAMANHO // 2, fim))
            if corte > i:
                fim = corte + 1
        partes.append(texto[i:fim].strip())
        if fim >= len(texto):
            break
        i = max(fim - SOBRA, i + 1)
    return [p for p in partes if len(p) >= 80]


def destino(saida: str) -> str:
    """Caminho real do banco: --saida pode ser um link para o disco local. Falha se o banco cair num disco de rede."""
    banco = os.path.realpath(saida)
    pasta = os.path.dirname(banco)
    if not os.path.isdir(pasta):
        raise SystemExit(f"a pasta {pasta} não existe: escolha um --saida no disco local do nó")
    with open("/proc/mounts") as f:
        montagens = [linha.split()[1:3] for linha in f]
    ponto, tipo = max((m for m in montagens if pasta == m[0] or pasta.startswith(m[0].rstrip("/") + "/")),
                      key=lambda m: len(m[0]))
    if tipo in REDE:
        raise SystemExit(f"{banco} fica em {ponto} ({tipo}): DuckDB em disco de rede trava. Use --saida no disco local")
    print(f"índice em {banco} ({ponto}, {tipo})")
    return banco


def md5(caminho: str) -> str:
    with open(caminho, "rb") as f:
        return hashlib.file_digest(f, "md5").hexdigest()


def pdfs_em_disco() -> list[str]:
    return sorted(os.path.relpath(os.path.join(pasta, a), PDFS).replace(os.sep, "/")
                  for pasta, _, arquivos in os.walk(PDFS) for a in arquivos if a.lower().endswith(".pdf"))


def do_csv(disco: list[str], avisos: list[str]) -> dict[str, dict]:
    """{caminho em disco: linha do documentos.csv}. A linha cujo caminho não existe mais vale para o PDF de mesmo nome
    solto noutra pasta (pdfs_esg guarda o que organizar.py ainda não moveu)."""
    with open(os.path.join(AQUI, "documentos.csv"), newline="") as f:
        linhas = {d["arquivo"]: d for d in csv.DictReader(f, delimiter=";")}
    em_disco = set(disco)
    por_nome = {}
    for arquivo in disco:
        por_nome.setdefault(os.path.basename(arquivo), []).append(arquivo)
    meta, faltando = {}, []
    for arquivo, d in linhas.items():
        if arquivo in em_disco:
            meta[arquivo] = d
            continue
        # só um candidato, e que não tenha linha própria no CSV, para dois documentos não brigarem pelo mesmo PDF
        iguais = [a for a in por_nome.get(os.path.basename(arquivo), []) if a not in linhas and a not in meta]
        if len(iguais) == 1:
            meta[iguais[0]] = d
            avisos.append(f"{arquivo} (documentos.csv) não está na pasta: os metadados vão para {iguais[0]}")
        else:
            faltando.append(arquivo)
    for arquivo in faltando:
        avisos.append(f"{arquivo} está no documentos.csv e não existe em data/raw: fica fora do índice")
    print(f"documentos.csv: {len(linhas)} linhas, {len(meta)} casadas com um PDF, {len(faltando)} sem arquivo")
    return meta


def dicionario(arquivo: str) -> dict:
    """Metadados de um dicionário da ANEEL, tirados do próprio PDF (título do conjunto e ano da versão)."""
    with fitz.open(os.path.join(PDFS, arquivo)) as pdf:
        texto = re.sub(r"\s+", " ", pdf[0].get_text("text", sort=True))
        data = pdf.metadata.get("modDate") or pdf.metadata.get("creationDate") or ""
    achado = CONJUNTO.search(texto)
    ano = re.match(r"D:(\d{4})", data)
    if not achado or not ano:
        raise SystemExit(f"{arquivo}: dicionário sem 'Conjunto de Dados ... Visão Geral' ou sem data ({data!r})")
    return {"arquivo": arquivo, "area": AREA_DICIONARIO, "empresa": EMPRESA_DICIONARIO, "cnpj": None,
            "ano": int(ano.group(1)), "tipo": TIPO_DICIONARIO,
            "titulo": f"Dicionário de dados da ANEEL: {achado.group(1).strip()}", "url": None}


def sem_copias(disco: list[str], meta: dict, avisos: list[str]) -> list[str]:
    """Descarta o mesmo PDF sob dois caminhos (md5 igual), ficando com o da pasta organizada e descrito no CSV: um
    documento repetido ocuparia as duas primeiras posições de toda busca."""
    por_tamanho = {}
    for arquivo in disco:
        por_tamanho.setdefault(os.path.getsize(os.path.join(PDFS, arquivo)), []).append(arquivo)
    fora = set()
    for iguais in por_tamanho.values():  # o md5 só é preciso entre PDFs do mesmo tamanho
        if len(iguais) < 2:
            continue
        por_md5 = {}
        for arquivo in iguais:
            por_md5.setdefault(md5(os.path.join(PDFS, arquivo)), []).append(arquivo)
        for mesmos in por_md5.values():
            if len(mesmos) < 2:
                continue
            mesmos.sort(key=lambda a: (a.split("/")[0] not in ORGANIZADAS, a not in meta, a))
            for arquivo in mesmos[1:]:
                fora.add(arquivo)
                avisos.append(f"{arquivo} é cópia de {mesmos[0]} (md5 igual) e fica fora do índice")
    return [a for a in disco if a not in fora]


def catalogo(avisos: list[str]) -> list[dict]:
    """Um registro por documento a indexar, cobrindo todo PDF de data/raw. Sem metadados não há índice: um PDF que não
    esteja no documentos.csv nem em DICIONARIOS interrompe a indexação com o nome do arquivo."""
    disco = pdfs_em_disco()
    em_disco = set(disco)
    for esperado in DICIONARIOS:
        if esperado not in em_disco:
            raise SystemExit(f"falta o dicionário de dados {esperado} em data/raw")
    # pdfs_esg/txt é a extração de alguns PDFs de pdfs_esg: o índice lê o PDF, que tem página para citar
    pasta_txt = os.path.join(PDFS, "pdfs_esg", "txt")
    for txt in sorted(os.listdir(pasta_txt)) if os.path.isdir(pasta_txt) else []:
        par = f"pdfs_esg/{txt[:-4]}.pdf"
        if not txt.endswith(".txt") or par not in em_disco:
            raise SystemExit(f"pdfs_esg/txt/{txt} não é a extração de um PDF de pdfs_esg: sem página para citar")
        avisos.append(f"pdfs_esg/txt/{txt} é a extração de {par}, já indexado pelo PDF")

    meta = do_csv(disco, avisos)
    docs, sem_metadados, ficam = [], [], sem_copias(disco, meta, avisos)
    for arquivo in set(meta) - set(ficam):  # a linha do CSV descrevia a cópia que saiu; o conteúdo está no que ficou
        avisos.append(f"{meta[arquivo]['arquivo']} (documentos.csv) descreve {arquivo}, que saiu como cópia")
    for arquivo in ficam:
        d = meta.get(arquivo)
        if d:
            docs.append({"arquivo": arquivo, "area": d["arquivo"].split("/")[0], "empresa": d["empresa"],
                         "cnpj": d["cnpj"] or None, "ano": int(d["ano"]), "tipo": d["tipo"], "titulo": d["titulo"],
                         "url": d["url"] or None, "bytes": os.path.getsize(os.path.join(PDFS, arquivo))})
        elif arquivo in DICIONARIOS:
            docs.append({**dicionario(arquivo), "bytes": os.path.getsize(os.path.join(PDFS, arquivo))})
        else:
            sem_metadados.append(arquivo)
    if sem_metadados:
        raise SystemExit("PDFs sem metadados (ponha no data/documentos.csv ou em DICIONARIOS):\n  "
                         + "\n  ".join(sem_metadados))
    print(f"{len(disco)} PDFs em data/raw: {len(disco) - len(docs)} cópias do mesmo PDF noutro caminho, "
          f"{len(docs)} documentos ({sum(d['area'] == AREA_DICIONARIO for d in docs)} dicionários da ANEEL, "
          f"que não estão no documentos.csv)")
    return docs


def extrair(arquivo: str) -> tuple:
    """(arquivo, páginas, trechos, parágrafos, erro): roda em outro processo, porque o pymupdf não solta o GIL."""
    paginas, pedacos, blocos = [], [], []
    try:
        with fitz.open(os.path.join(PDFS, arquivo)) as pdf:
            for n, pagina in enumerate(pdf, start=1):
                texto = pagina.get_text("text", sort=True)
                paginas.append((arquivo, n, texto))
                pedacos += [(arquivo, n, t) for t in trechos(texto)]
                for b in pagina.get_text("blocks"):  # (x0, y0, x1, y1, texto, número, tipo): tipo 0 é texto
                    if b[6] == 0 and len(b[4].strip()) >= 80:
                        blocos.append((arquivo, n, b[4].strip()))
    except Exception as e:  # noqa: BLE001 - o nome do PDF ilegível entra no relatório do fim
        return arquivo, [], [], [], repr(e)
    return arquivo, paginas, pedacos, blocos, None


def ler_pdfs(docs: list[dict], leitores: int) -> tuple[list, list, list, list]:
    paginas, pedacos, blocos, ilegiveis = [], [], [], []
    por_arquivo, inicio = {}, time.time()
    with ProcessPoolExecutor(leitores) as ex:
        for n, (arquivo, pags, peds, blocs, erro) in enumerate(ex.map(extrair, [d["arquivo"] for d in docs]), start=1):
            por_arquivo[arquivo] = (pags, peds, blocs)
            if erro:
                ilegiveis.append((arquivo, erro))
                print(f"ilegível: {arquivo}: {erro}", flush=True)
            if n % 200 == 0 or n == len(docs):
                lidas = sum(len(p) for p, _, _ in por_arquivo.values())
                print(f"[{n}/{len(docs)}] {lidas} páginas, {sum(len(t) for _, t, _ in por_arquivo.values())} trechos "
                      f"({lidas / (time.time() - inicio):.0f} páginas/s)", flush=True)
    for d in docs:  # na ordem do catálogo: o id de um trecho não depende de qual processo terminou primeiro
        pags, peds, blocs = por_arquivo[d["arquivo"]]
        d["paginas"] = len(pags)
        paginas += pags
        pedacos += peds
        blocos += blocs
    return paginas, pedacos, blocos, ilegiveis


def reaproveitar(banco: str, pedacos: list, vetores: np.ndarray) -> np.ndarray:
    """Copia do índice anterior o vetor de todo trecho com o mesmo arquivo, página e texto; devolve quais foram
    preenchidos. Só reaproveita de um índice feito com a mesma ASSINATURA, senão a busca misturaria dois espaços."""
    prontos = np.zeros(len(pedacos), dtype=bool)
    if not os.path.exists(banco):
        return prontos
    con = duckdb.connect(banco, read_only=True)
    try:
        tem_meta = con.execute("SELECT count(*) FROM information_schema.tables WHERE table_name = 'meta'").fetchone()[0]
        anterior = dict(con.execute("SELECT chave, valor FROM meta").fetchall()) if tem_meta else {}
        if anterior.get("embedding") != ASSINATURA:
            print(f"índice anterior com embedding {anterior.get('embedding')!r}: nada a reaproveitar")
            return prontos
        novos = pa.table({"i": pa.array(range(len(pedacos)), pa.int64()), "arquivo": [p[0] for p in pedacos],
                          "pagina": pa.array([p[1] for p in pedacos], pa.int32()), "texto": [p[2] for p in pedacos]})
        con.register("novos", novos)
        achados = con.execute("""SELECT n.i, v.embedding FROM novos n JOIN trechos v
                                 ON n.arquivo = v.arquivo AND n.pagina = v.pagina AND n.texto = v.texto""")
        tabela = achados.to_arrow_table()
    finally:
        con.close()
    indices = tabela.column("i").combine_chunks().to_numpy()
    if len(indices):
        vetores[indices] = tabela.column("embedding").combine_chunks().flatten().to_numpy().reshape(-1, DIMENSOES)
        prontos[indices] = True
    return prontos


def conferir_gpu(gpu: int):
    """Modelo e GPU existem? É a primeira coisa a checar, antes de gastar minutos lendo PDFs. A memória livre, que muda
    a cada instante numa máquina compartilhada, é conferida no Codificador, na hora de ocupar a placa."""
    if not os.path.exists(os.path.join(PASTA_MODELO, "model.safetensors")):
        raise SystemExit(f"falta o modelo em {PASTA_MODELO} (baixe {MODELO} com o huggingface_hub; ver data/INDEXAR.md)")
    if not torch.cuda.is_available():
        raise SystemExit("sem CUDA: este índice é feito na GPU, não há caminho em CPU aqui")
    if not 0 <= gpu < torch.cuda.device_count():
        raise SystemExit(f"--gpu {gpu} não existe: esta máquina tem {torch.cuda.device_count()} GPU(s)")


class Codificador:
    """O e5-large na GPU em fp16: média dos tokens e norma 1, como o sentence-transformers do próprio modelo.

    A GPU é a pedida em --gpu, sem procurar outra: numa máquina compartilhada, cair na placa errada atrapalha quem já
    está nela. Sem CUDA, sem essa GPU ou sem memória livre para o lote, a rodada não começa."""

    def __init__(self, lote: int, gpu: int):
        conferir_gpu(gpu)
        self.dispositivo = f"cuda:{gpu}"
        livre, total = torch.cuda.mem_get_info(gpu)
        precisa = FOLGA * (GPU_FIXA + GPU_POR_TRECHO * lote)
        print(f"{self.dispositivo} {torch.cuda.get_device_name(gpu)}: {livre / 2**30:.1f} GiB livres "
              f"de {total / 2**30:.1f} GiB; lote {lote} pede {precisa / 2**30:.1f} GiB")
        if livre < precisa:  # outro processo ocupa a placa: melhor não começar do que estourar no meio
            raise SystemExit(f"só {livre / 2**30:.1f} GiB livres em {self.dispositivo} e o lote {lote} pede "
                             f"{precisa / 2**30:.1f} GiB: baixe o --lote, use outra --gpu ou espere a placa esvaziar")
        self.tok = AutoTokenizer.from_pretrained(PASTA_MODELO)
        self.modelo = AutoModel.from_pretrained(PASTA_MODELO, dtype=torch.float16,
                                                attn_implementation="sdpa").to(self.dispositivo).eval()

    def codificar(self, textos: list[str]) -> np.ndarray:
        with torch.inference_mode():
            e = self.tok(textos, padding=True, truncation=True, max_length=TOKENS,
                         return_tensors="pt").to(self.dispositivo)
            escondido = self.modelo(**e).last_hidden_state
            mascara = e["attention_mask"].unsqueeze(-1).to(escondido.dtype)
            media = (escondido * mascara).sum(1) / mascara.sum(1)
            return torch.nn.functional.normalize(media.float(), dim=1).cpu().numpy()


def contexto(pedaco: tuple, info: dict) -> str:
    """Empresa, ano e título dão contexto a trecho solto de tabela; "passage: " é o prefixo que o e5 espera."""
    d = info[pedaco[0]]
    return f"{PREFIXO}{d['empresa']} {d['ano']}, {d['titulo']}. {pedaco[2]}"


def embutir(pedacos: list, info: dict, faltam: np.ndarray, vetores: np.ndarray, lote: int, gpu: int):
    codificador = Codificador(lote, gpu)
    # do trecho mais curto ao mais longo: lote parecido no tamanho gasta menos padding
    ordem = sorted(faltam.tolist(), key=lambda i: len(pedacos[i][2]))
    inicio, ultimo = time.time(), 0
    for i in range(0, len(ordem), lote):
        grupo = ordem[i:i + lote]
        vetores[grupo] = codificador.codificar([contexto(pedacos[j], info) for j in grupo])
        if i - ultimo >= 20000 or i + lote >= len(ordem):
            ultimo = i
            print(f"{min(i + lote, len(ordem))}/{len(ordem)} vetores "
                  f"({(i + lote) / (time.time() - inicio):.0f} trechos/s, "
                  f"pico {torch.cuda.max_memory_allocated(gpu) / 2**30:.1f} GiB, "
                  f"{torch.cuda.mem_get_info(gpu)[0] / 2**30:.1f} GiB livres na GPU)", flush=True)
    print(f"embeddings em {time.time() - inicio:.0f} s")


def gravar(banco: str, docs: list[dict], paginas: list, pedacos: list, vetores: np.ndarray, blocos: list,
           reaproveitados: int):
    """Grava num banco temporário no disco do destino e só então troca o antigo (nada de índice meio pronto no ar)."""
    pasta = tempfile.mkdtemp(prefix="docs_", dir=os.path.dirname(banco))  # mesmo disco: o os.replace é atômico
    tmp = os.path.join(pasta, "docs.duckdb")
    con = duckdb.connect(tmp)
    con.execute("""CREATE TABLE documentos (arquivo VARCHAR PRIMARY KEY, area VARCHAR, empresa VARCHAR, cnpj VARCHAR,
                   ano INTEGER, tipo VARCHAR, titulo VARCHAR, url VARCHAR, paginas INTEGER, bytes BIGINT)""")
    con.executemany("INSERT INTO documentos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [(d["arquivo"], d["area"], d["empresa"], d["cnpj"], d["ano"], d["tipo"], d["titulo"], d["url"],
                      d["paginas"], d["bytes"]) for d in docs])
    con.execute("CREATE TABLE paginas (arquivo VARCHAR, pagina INTEGER, texto VARCHAR)")
    con.executemany("INSERT INTO paginas VALUES (?, ?, ?)", paginas)
    con.execute(f"""CREATE TABLE trechos (id BIGINT, arquivo VARCHAR, pagina INTEGER, texto VARCHAR,
                    embedding FLOAT[{DIMENSOES}])""")
    for i in range(0, len(pedacos), 20000):  # aos pedaços: a tabela inteira em arrow dobraria a memória dos vetores
        fatia = pedacos[i:i + 20000]
        tabela = pa.table({
            "id": pa.array(range(i, i + len(fatia)), pa.int64()),
            "arquivo": [p[0] for p in fatia], "pagina": pa.array([p[1] for p in fatia], pa.int32()),
            "texto": [p[2] for p in fatia],
            "embedding": pa.FixedSizeListArray.from_arrays(
                pa.array(vetores[i:i + len(fatia)].reshape(-1), pa.float32()), DIMENSOES),
        })
        con.execute("INSERT INTO trechos SELECT * FROM tabela")
    paragrafos = pa.table({"id": pa.array(range(len(blocos)), pa.int64()), "arquivo": [b[0] for b in blocos],
                           "pagina": pa.array([b[1] for b in blocos], pa.int32()), "texto": [b[2] for b in blocos]})
    con.execute("CREATE TABLE blocos AS SELECT * FROM paragrafos")
    con.execute("CREATE TABLE meta (chave VARCHAR PRIMARY KEY, valor VARCHAR)")
    con.executemany("INSERT INTO meta VALUES (?, ?)", [
        ("modelo", MODELO), ("embedding", ASSINATURA), ("dimensoes", str(DIMENSOES)), ("prefixo_trecho", PREFIXO),
        ("prefixo_pergunta", "query: "), ("gerado_em", time.strftime("%Y-%m-%dT%H:%M:%S")),
        ("documentos", str(len(docs))), ("paginas", str(len(paginas))), ("trechos", str(len(pedacos))),
        ("blocos", str(len(blocos))), ("vetores_reaproveitados", str(reaproveitados))])
    print("índice de palavras (BM25)...", flush=True)
    con.execute("INSTALL fts; LOAD fts")
    # índice de palavras em português, sem acento e mantendo números (escopo 1, 2025, tCO2e)
    for t in ("trechos", "blocos"):
        con.execute(f"""PRAGMA create_fts_index('{t}', 'id', 'texto', stemmer = 'portuguese', stopwords = 'none',
                       ignore = '(\\.|[^a-z0-9])+', strip_accents = 1, lower = 1)""")
    con.close()
    os.replace(tmp, banco)  # o caminho real, não o --saida: um link simbólico seria apagado pelo replace
    shutil.rmtree(pasta)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", required=True, help="caminho do DuckDB, sempre no disco local do nó (nunca no NFS)")
    ap.add_argument("--gpu", type=int, required=True, help="índice da GPU a usar (nvidia-smi); não há caminho em CPU")
    ap.add_argument("--lote", type=int, default=LOTE, help="trechos por lote na GPU")
    ap.add_argument("--leitores", type=int, default=os.cpu_count(), help="processos lendo PDFs (um por núcleo)")
    ap.add_argument("--limite", type=int, help="indexa só os N primeiros documentos (teste)")
    ap.add_argument("--tudo", action="store_true", help="recalcula todos os vetores, sem olhar o índice anterior")
    a = ap.parse_args()

    inicio, avisos = time.time(), []
    banco = destino(a.saida)
    conferir_gpu(a.gpu)
    docs = catalogo(avisos)
    if a.limite is not None:
        docs = docs[:a.limite]
    print(f"{len(docs)} documentos a indexar; lendo os PDFs com {a.leitores} processos...", flush=True)
    paginas, pedacos, blocos, ilegiveis = ler_pdfs(docs, a.leitores)
    docs = [d for d in docs if d["paginas"]]  # PDF ilegível não vira documento: o nome dele sai no relatório do fim
    info = {d["arquivo"]: d for d in docs}
    com_trecho = {p[0] for p in pedacos}
    sem_texto = [d["arquivo"] for d in docs if d["arquivo"] not in com_trecho]
    print(f"{len(docs)} documentos, {len(paginas)} páginas, {len(pedacos)} trechos, {len(blocos)} parágrafos; "
          f"{len(sem_texto)} PDFs sem texto extraível (só imagem)", flush=True)

    vetores = np.zeros((len(pedacos), DIMENSOES), dtype=np.float32)
    prontos = np.zeros(len(pedacos), dtype=bool) if a.tudo else reaproveitar(banco, pedacos, vetores)
    faltam = np.flatnonzero(~prontos)
    print(f"{int(prontos.sum())} vetores reaproveitados, {len(faltam)} a calcular ({MODELO} na GPU)", flush=True)
    if len(faltam):
        embutir(pedacos, info, faltam, vetores, a.lote, a.gpu)

    gravar(banco, docs, paginas, pedacos, vetores, blocos, int(prontos.sum()))
    print(f"ok: {banco} ({os.path.getsize(banco) / 2**20:.0f} MiB) em {time.time() - inicio:.0f} s")
    for aviso in avisos:
        print("aviso:", aviso)
    for arquivo in sem_texto:
        print(f"aviso: {arquivo} não tem texto extraível (PDF só de imagem): entra sem trechos")
    if ilegiveis:
        raise SystemExit("o índice foi publicado, mas estes PDFs não abriram:\n  "
                         + "\n  ".join(f"{a}: {e}" for a, e in ilegiveis))


if __name__ == "__main__":
    main()

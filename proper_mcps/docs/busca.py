"""Busca por página nos relatórios do coppezip-docs, para a aba Busca do LibreChat (rota /api/busca, só com login).

Serviço HTTP em 127.0.0.1 sobre o mesmo índice do server.py. Reaproveita os embeddings dos trechos: a nota de uma página
é a do seu trecho mais parecido com a pergunta (multilingual-e5-large), fundida por posição (RRF) com a busca de
palavras (BM25), como em buscar_documentos. Páginas sem texto extraível (só imagem) ficam de fora, como no índice.

Uso: python busca.py --porta N  (o iniciar.sh sobe com BUSCA_PORTA do .env). Índice data/docs.duckdb, PDFs em
data/raw/<area>/<empresa>/... (caminho na coluna arquivo), os mesmos do indexar_docs.py.
Rotas (GET): /resumo, /buscar?q=&empresa=&ano=&k=, /pagina?arquivo=&pagina=, /imagem?arquivo=&pagina=, /pdf?arquivo=
empresa e ano podem se repetir; sem nenhum, a busca vale para todos os documentos.
"""
import argparse
import json
import os
import shutil
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pymupdf as fitz

from server import CANDIDATOS, DB, RAIZ, _con, _embed

PDFS = os.path.join(RAIZ, "data", "raw")
MAX_RESULTADOS = 50
LARGURA_IMAGEM = 1100  # pixels; relatórios em página dupla ficam legíveis sem pesar no túnel SSH


class Erro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status = status


def _um(p: dict, nome: str, padrao: str = "") -> str:
    return (p.get(nome) or [padrao])[0]


def _inteiro(p: dict, nome: str, padrao: int | None = None) -> int:
    try:
        return int(_um(p, nome) or padrao)
    except (TypeError, ValueError):
        raise Erro(400, f"{nome} precisa ser um número inteiro")


def _conectar():
    if not os.path.exists(DB):
        raise Erro(503, f"índice {DB} não existe; rode data/indexar_docs.py")
    return _con()


def _documento(con, arquivo: str) -> tuple:
    doc = con.execute("SELECT arquivo, empresa, ano, titulo, paginas, url FROM documentos WHERE arquivo = ?",
                      [arquivo]).fetchone()
    if not doc:
        raise Erro(404, f"arquivo '{arquivo}' não está no índice")
    return doc


def _filtro(p: dict) -> tuple[str, list]:
    empresas = [e for e in p.get("empresa", []) if e.strip()]
    try:
        anos = [int(a) for a in p.get("ano", []) if a.strip()]
    except ValueError:
        raise Erro(400, "ano precisa ser um número")
    conds, params = [], []
    if empresas:
        conds.append(f"d.empresa IN ({', '.join('?' * len(empresas))})")
        params += empresas
    if anos:
        conds.append(f"d.ano IN ({', '.join('?' * len(anos))})")
        params += anos
    return (" AND ".join(conds) or "TRUE"), params


def resumo(_: dict) -> dict:
    con = _conectar()
    try:
        cur = con.execute("""
            SELECT d.arquivo, d.empresa, d.ano, d.tipo, d.titulo, d.paginas, d.url,
                   count(DISTINCT t.pagina) AS paginas_com_texto
            FROM documentos d LEFT JOIN trechos t USING (arquivo) GROUP BY ALL ORDER BY d.empresa, d.ano, d.titulo""")
        nomes = [c[0] for c in cur.description]
        documentos = [dict(zip(nomes, r)) for r in cur.fetchall()]
    finally:
        con.close()
    gerado = datetime.fromtimestamp(os.path.getmtime(DB), timezone.utc).isoformat()
    return {"gerado_em": gerado, "documentos": documentos}


def buscar(p: dict) -> dict:
    consulta = _um(p, "q").strip()[:1000]
    if not consulta:
        raise Erro(400, "escreva uma pergunta")
    k = max(1, min(_inteiro(p, "k", 20), MAX_RESULTADOS))
    onde, params = _filtro(p)
    vetor = _embed(consulta)
    con = _conectar()
    try:
        sentido = con.execute(f"""
            SELECT t.arquivo, t.pagina, max(array_cosine_similarity(t.embedding, ?::FLOAT[1024])) AS s
            FROM trechos t JOIN documentos d USING (arquivo) WHERE {onde}
            GROUP BY ALL ORDER BY s DESC LIMIT {CANDIDATOS}""", [vetor] + params).fetchall()
        palavras = con.execute(f"""
            SELECT t.arquivo, t.pagina, max(t.s) AS s
            FROM (SELECT *, fts_main_trechos.match_bm25(id, ?) AS s FROM trechos) t JOIN documentos d USING (arquivo)
            WHERE t.s IS NOT NULL AND {onde} GROUP BY ALL ORDER BY s DESC LIMIT {CANDIDATOS}""",
                               [consulta] + params).fetchall()
        pontos, por_sentido, por_palavras = {}, set(), set()
        for lista, marca in ((sentido, por_sentido), (palavras, por_palavras)):
            for posicao, (arquivo, pagina, _) in enumerate(lista):
                pontos[(arquivo, pagina)] = pontos.get((arquivo, pagina), 0) + 1 / (60 + posicao)
                marca.add((arquivo, pagina))
        melhores = sorted(pontos, key=pontos.get, reverse=True)[:k]
        if not melhores:
            return {"resultados": []}
        # trecho mais parecido de cada página escolhida: é o que mostra por que a página apareceu
        trechos = con.execute("""
            SELECT arquivo, pagina, max(sim), arg_max(texto, sim) FROM (
                SELECT arquivo, pagina, texto, array_cosine_similarity(embedding, ?::FLOAT[1024]) AS sim FROM trechos
                WHERE arquivo || '#' || pagina IN (SELECT unnest(?))) GROUP BY ALL""",
                              [vetor, [f"{a}#{n}" for a, n in melhores]]).fetchall()
        docs = con.execute("""SELECT arquivo, empresa, ano, tipo, titulo, paginas, url FROM documentos
                              WHERE arquivo IN (SELECT unnest(?))""", [sorted({a for a, _ in melhores})]).fetchall()
    finally:
        con.close()
    por_pagina = {(r[0], r[1]): r for r in trechos}
    por_arquivo = {r[0]: r for r in docs}
    resultados = []
    for chave in melhores:
        arquivo, pagina = chave
        d, t = por_arquivo[arquivo], por_pagina[chave]
        resultados.append({"arquivo": arquivo, "pagina": pagina, "empresa": d[1], "ano": d[2], "tipo": d[3],
                           "titulo": d[4], "total_paginas": d[5], "url": d[6], "similaridade": round(t[2], 4),
                           "trecho": t[3], "sentido": chave in por_sentido, "palavras": chave in por_palavras})
    return {"resultados": resultados}


def pagina(p: dict) -> dict:
    arquivo, numero = _um(p, "arquivo"), _inteiro(p, "pagina")
    con = _conectar()
    try:
        doc = _documento(con, arquivo)
        linha = con.execute("SELECT texto FROM paginas WHERE arquivo = ? AND pagina = ?", [arquivo, numero]).fetchone()
    finally:
        con.close()
    if not linha:
        raise Erro(404, f"o documento tem {doc[4]} páginas")
    return {"arquivo": doc[0], "empresa": doc[1], "ano": doc[2], "titulo": doc[3], "pagina": numero,
            "total_paginas": doc[4], "url": doc[5], "texto": linha[0]}


def _caminho(arquivo: str) -> str:
    con = _conectar()
    try:
        arquivo = _documento(con, arquivo)[0]  # só arquivos do índice: o caminho vem do banco, não do usuário
    finally:
        con.close()
    caminho = os.path.join(PDFS, *arquivo.split("/"))
    if not os.path.exists(caminho):
        raise Erro(404, f"{arquivo} está no índice mas não em {PDFS}")
    return caminho


def imagem(p: dict) -> tuple[str, bytes]:
    caminho, numero = _caminho(_um(p, "arquivo")), _inteiro(p, "pagina")
    largura = max(300, min(_inteiro(p, "largura", LARGURA_IMAGEM), 2000))
    with fitz.open(caminho) as pdf:
        if not 1 <= numero <= pdf.page_count:
            raise Erro(404, f"o documento tem {pdf.page_count} páginas")
        folha = pdf[numero - 1]
        escala = largura / folha.rect.width
        return "image/jpeg", folha.get_pixmap(matrix=fitz.Matrix(escala, escala)).tobytes("jpeg", jpg_quality=82)


def pdf(p: dict) -> tuple[str, str]:
    return "application/pdf", _caminho(_um(p, "arquivo"))


ROTAS = {"/resumo": resumo, "/buscar": buscar, "/pagina": pagina, "/imagem": imagem, "/pdf": pdf}


class Tratador(BaseHTTPRequestHandler):
    def _enviar(self, status: int, tipo: str, corpo: bytes | None = None, caminho: str | None = None,
                cache: str = "no-cache"):
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Cache-Control", f"private, {cache}")
        self.send_header("Content-Length", str(os.path.getsize(caminho) if caminho else len(corpo)))
        if caminho:
            self.send_header("Content-Disposition", f'inline; filename="{os.path.basename(caminho)}"')
        self.end_headers()
        if caminho:
            with open(caminho, "rb") as f:
                shutil.copyfileobj(f, self.wfile)
        else:
            self.wfile.write(corpo)

    def _json(self, status: int, dados: dict):
        self._enviar(status, "application/json; charset=utf-8", json.dumps(dados, ensure_ascii=False).encode())

    def do_GET(self):
        url = urlparse(self.path)
        try:
            rota = ROTAS.get(url.path)
            if not rota:
                raise Erro(404, "rota inexistente")
            resposta = rota(parse_qs(url.query))
        except Erro as e:
            return self._json(e.status, {"message": str(e)})
        except Exception as e:  # noqa: BLE001 - a interface mostra a mensagem em vez de uma página vazia
            self.log_error("erro em %s: %r", url.path, e)
            return self._json(500, {"message": f"erro na busca: {e}"})
        if isinstance(resposta, dict):
            return self._json(200, resposta)
        tipo, dado = resposta
        if isinstance(dado, str):
            return self._enviar(200, tipo, caminho=dado, cache="max-age=3600")
        return self._enviar(200, tipo, dado, cache="max-age=3600")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--porta", type=int, required=True)
    a = ap.parse_args()
    # carrega o modelo já na subida: a primeira pergunta não espera os segundos da leitura dos pesos
    threading.Thread(target=_embed, args=("aquecimento",), daemon=True).start()
    servidor = ThreadingHTTPServer(("127.0.0.1", a.porta), Tratador)
    servidor.daemon_threads = True
    print(f"busca em http://127.0.0.1:{a.porta} (índice {DB}, PDFs {PDFS})", file=sys.stderr, flush=True)
    servidor.serve_forever()


if __name__ == "__main__":
    main()

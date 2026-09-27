#!/usr/bin/env python3
"""Publica a vitrine estática do site (abas Painel, Grafo e Timeline) num bucket S3 com website hosting.

Re-executável: cada execução recompila o front no modo vitrine, regrava os dados e sobrescreve os objetos do bucket,
apagando no fim só os objetos que execuções anteriores deste script deixaram para trás (marca `publicado-por`).

O que vai para o bucket:
  index.html + bundle do front  <- client/dist-vitrine (build com VITE_SITE_ESTATICO=1)
  assets/...                    <- client/public/assets (ícones, fontes, logo; o servidor Node monta isso na raiz)
  dados/painel.json             <- data/painel.json, no lugar de GET /api/painel/dados
  dados/busca_resumo.json       <- GET /resumo do proper_mcps/docs/busca.py, no lugar de GET /api/busca/resumo
  linha_do_tempo/*.json         <- .runtime/linha_do_tempo (é o caminho que a aba Timeline já busca)

O que NÃO vai, por falta de servidor: o chat (Node + MongoDB + Meilisearch + MCP + modelo) e a aba Busca (índice
data/docs_titan.duckdb, embedding da pergunta no Bedrock e os PDFs de data/raw). As duas telas aparecem com aviso.

Uso: .runtime/venv/bin/python infra/publicar_site.py [--instalacao RAIZ] [--sem-build] [--sem-documentos]
Detalhes, limites da conta AWS e como republicar: infra/SITE.md
"""
import argparse
import json
import mimetypes
import os
import re
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

REGIAO = "us-east-1"
# Nome neutro à marca (já no nome novo) + número da conta, porque nome de bucket é global e único.
PREFIXO_BUCKET = "energynexus-site"
MARCA_PUBLICACAO = "publicar_site.py"  # metadado x-amz-meta-publicado-por: só apago o que este script subiu
SAIDA_BUILD = "client/dist-vitrine"  # fora de client/dist para não trocar o front que o chat local serve

# Content-Type fixo por extensão: sem isso o S3 manda binary/octet-stream e o navegador não executa os .js/.css.
TIPOS = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".webmanifest": "application/manifest+json; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".webp": "image/webp",
    ".jpg": "image/jpeg",
    ".ico": "image/vnd.microsoft.icon",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".ttf": "font/ttf",
    ".mp3": "audio/mpeg",
    ".map": "application/json; charset=utf-8",
    ".wasm": "application/wasm",
}
# Nome com hash do vite (index.CpNRA-E5.js): só esses podem ser guardados para sempre pelo navegador.
HASH_VITE = re.compile(r"\.[0-9A-Za-z_-]{8}\.[0-9a-z]+$")
# Uma cópia do index.html em <aba>/index.html faz o S3 responder 302 para <aba>/ e depois 200, em vez do 404 do
# ErrorDocument. As abas com parâmetro (timeline/<cnpj>) continuam caindo no ErrorDocument, que devolve o mesmo HTML.
ABAS = ["painel", "grafo", "timeline", "busca"]
IMUTAVEL = "public, max-age=31536000, immutable"
SEM_CACHE = "no-cache"  # revalida sempre: é o que faz a republicação (novo bundle, dados novos) aparecer

local = threading.local()


class Falha(Exception):
    """Erro de publicação com a mensagem já pronta para o usuário."""


def exigir(caminho: Path, dica: str) -> Path:
    if not caminho.exists():
        raise Falha(f"falta {caminho}: {dica}")
    return caminho


def porta_da_busca(raiz_dados: Path) -> str:
    """BUSCA_PORTA do .env da instalação que tem os dados (o serviço de busca roda ao lado dele)."""
    env = exigir(raiz_dados / ".env", "copie de .env.example e preencha")
    for linha in env.read_text(encoding="utf-8").splitlines():
        if linha.startswith("BUSCA_PORTA="):
            return linha.split("=", 1)[1].strip()
    raise Falha(f"falta BUSCA_PORTA em {env}")


def compilar(raiz: Path, instalacao: Path) -> Path:
    """Build do front no modo vitrine, com o Node da instalação (.runtime/bin) e saída própria."""
    node_bin = exigir(instalacao / ".runtime" / "bin", "rode ./instalar.sh: o Node do sistema não compila o front")
    vite = exigir(raiz / "node_modules" / "vite" / "bin" / "vite.js", "rode npm install na raiz do repositório")
    ambiente = dict(os.environ)
    ambiente["PATH"] = f"{node_bin}{os.pathsep}{ambiente['PATH']}"
    ambiente["NODE_ENV"] = "production"
    ambiente["NODE_OPTIONS"] = "--max-old-space-size=8192"
    ambiente["VITE_SITE_ESTATICO"] = "1"  # liga as rotas da vitrine e a leitura dos JSON estáticos
    etapas = [
        (raiz, ["npm", "run", "build:data-provider"]),
        (raiz, ["npm", "run", "build:data-schemas"]),
        (raiz, ["npm", "run", "build:api"]),
        (raiz, ["npm", "run", "build:client-package"]),
        (raiz / "client", ["node", str(vite), "build", "--outDir", "dist-vitrine", "--emptyOutDir"]),
    ]
    for pasta, comando in etapas:
        print(f"[build] {' '.join(comando)}", flush=True)
        fim = subprocess.run(comando, cwd=pasta, env=ambiente)
        if fim.returncode != 0:
            raise Falha(f"build falhou em {' '.join(comando)} (código {fim.returncode})")
    return exigir(raiz / SAIDA_BUILD / "index.html", "o vite não gerou o index.html").parent


def resumo_da_busca(instalacao: Path, destino: Path) -> None:
    """Grava o snapshot de /resumo do serviço de busca: é o que a aba Grafo usa para ligar empresa a documento."""
    porta = porta_da_busca(instalacao)
    url = f"http://127.0.0.1:{porta}/resumo"
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            conteudo = json.loads(r.read())
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as e:
        raise Falha(
            f"não consegui ler {url} ({type(e).__name__}: {e}); suba o serviço com ./iniciar.sh "
            f"ou publique sem os documentos com --sem-documentos"
        )
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(conteudo, ensure_ascii=False), encoding="utf-8")
    print(f"[dados] {len(conteudo['documentos'])} documentos em {destino.name} (gerado em {conteudo['gerado_em']})")


def itens_do_site(dist: Path, raiz: Path, instalacao: Path, com_documentos: bool) -> list[tuple]:
    """Lista (chave no bucket, arquivo local, imutável) de tudo que o site precisa."""
    itens: list[tuple[str, Path, bool]] = []

    for arquivo in sorted(p for p in dist.rglob("*") if p.is_file()):
        if arquivo.suffix in (".br", ".gz"):
            continue  # o S3 não negocia Content-Encoding: o pré-comprimido só atrapalharia
        chave = arquivo.relative_to(dist).as_posix()
        if chave.startswith("dados/"):
            continue  # snapshot de execução anterior; os dados entram logo abaixo, da fonte
        itens.append((chave, arquivo, bool(HASH_VITE.search(arquivo.name))))

    indice = exigir(dist / "index.html", "o vite não gerou o index.html")
    itens += [(f"{aba}/index.html", indice, False) for aba in ABAS]

    # O vite não copia public/ no build (publicDir: false); no servidor Node quem monta isso na raiz é
    # api/config/paths.js.
    robots = exigir(raiz / "client" / "public" / "robots.txt", "o repositório está incompleto")
    itens.append(("robots.txt", robots, False))
    publicos = exigir(raiz / "client" / "public" / "assets", "o repositório está incompleto")
    for arquivo in sorted(p for p in publicos.rglob("*") if p.is_file()):
        relativo = arquivo.relative_to(publicos)
        if relativo.parts[0] == "linha_do_tempo":
            continue  # aqui é um link do iniciar.sh; no site os JSON da Timeline vão para /linha_do_tempo/
        itens.append((f"assets/{relativo.as_posix()}", arquivo, False))

    painel = exigir(instalacao / "data" / "painel.json", "rode data/exportar_painel.py")
    itens.append(("dados/painel.json", painel, False))

    if com_documentos:
        resumo = dist / "dados" / "busca_resumo.json"
        resumo_da_busca(instalacao, resumo)
        itens.append(("dados/busca_resumo.json", resumo, False))

    linha = exigir(instalacao / ".runtime" / "linha_do_tempo", "rode .runtime/venv/bin/python data/linha_do_tempo.py")
    jsons = sorted(linha.glob("*.json"))
    if not jsons:
        raise Falha(f"{linha} está vazia: rode .runtime/venv/bin/python data/linha_do_tempo.py")
    for arquivo in jsons:
        itens.append((f"linha_do_tempo/{arquivo.name}", arquivo, False))

    return itens


def tipo(chave: str, arquivo: Path) -> str:
    extensao = arquivo.suffix.lower()
    if extensao in TIPOS:
        return TIPOS[extensao]
    adivinhado = mimetypes.guess_type(arquivo.name)[0]
    if not adivinhado:
        raise Falha(f"não sei o Content-Type de {chave}: acrescente '{extensao}' em TIPOS de infra/publicar_site.py")
    return adivinhado


def cliente():
    """Um cliente S3 por thread: o boto3 não garante que um cliente seja seguro entre threads."""
    if not hasattr(local, "s3"):
        local.s3 = boto3.session.Session().client("s3", region_name=REGIAO)
    return local.s3


def garantir_bucket(s3, bucket: str) -> None:
    """Cria o bucket se não existir e (re)aplica leitura pública, website hosting e CORS. Idempotente."""
    try:
        s3.head_bucket(Bucket=bucket)
        print(f"[bucket] {bucket} já existe")
    except ClientError as e:
        if e.response["Error"]["Code"] not in ("404", "NoSuchBucket"):
            raise Falha(f"não consegui checar o bucket {bucket}: {e}")
        s3.create_bucket(Bucket=bucket)  # us-east-1 não aceita LocationConstraint
        print(f"[bucket] {bucket} criado em {REGIAO}")

    s3.put_public_access_block(
        Bucket=bucket,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": False,
            "IgnorePublicAcls": False,
            "BlockPublicPolicy": False,
            "RestrictPublicBuckets": False,
        },
    )
    s3.put_bucket_policy(
        Bucket=bucket,
        Policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Sid": "LeituraPublica",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket}/*",
            }],
        }),
    )
    # ErrorDocument = index.html: é o que faz /painel, /grafo e /timeline abrirem (o React Router assume daí).
    s3.put_bucket_website(
        Bucket=bucket,
        WebsiteConfiguration={"IndexDocument": {"Suffix": "index.html"}, "ErrorDocument": {"Key": "index.html"}},
    )
    s3.put_bucket_cors(
        Bucket=bucket,
        CORSConfiguration={"CORSRules": [{
            "AllowedMethods": ["GET", "HEAD"], "AllowedOrigins": ["*"], "AllowedHeaders": ["*"],
            "MaxAgeSeconds": 3000,
        }]},
    )
    print("[bucket] leitura pública, website hosting e CORS aplicados")


def enviar(bucket: str, itens: list[tuple]) -> None:
    def subir(item):
        chave, arquivo, imutavel = item
        cliente().upload_file(
            str(arquivo), bucket, chave,
            ExtraArgs={
                "ContentType": tipo(chave, arquivo),
                "CacheControl": IMUTAVEL if imutavel else SEM_CACHE,
                "Metadata": {"publicado-por": MARCA_PUBLICACAO},
            },
        )
        return chave

    total = sum(a.stat().st_size for _, a, _ in itens)
    print(f"[upload] {len(itens)} arquivos, {total / 1e6:.1f} MB")
    with ThreadPoolExecutor(max_workers=8) as executor:
        for n, chave in enumerate(executor.map(subir, itens), 1):
            if n % 50 == 0 or n == len(itens):
                print(f"[upload] {n}/{len(itens)} ({chave})")


def remover_obsoletos(s3, bucket: str, chaves_novas: set[str]) -> list[str]:
    """Apaga o que sobrou de publicações anteriores (bundle antigo, empresa que saiu da Timeline).

    Só apaga objeto com o metadado publicado-por deste script: o que outra pessoa pôs no bucket fica.
    """
    antigos = []
    for pagina in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        for obj in pagina.get("Contents", []):
            if obj["Key"] in chaves_novas:
                continue
            marca = s3.head_object(Bucket=bucket, Key=obj["Key"]).get("Metadata", {}).get("publicado-por")
            if marca == MARCA_PUBLICACAO:
                antigos.append(obj["Key"])
            else:
                print(f"[limpeza] deixando {obj['Key']} (não foi este script que subiu)")
    for lote in [antigos[i:i + 1000] for i in range(0, len(antigos), 1000)]:
        s3.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": k} for k in lote]})
    print(f"[limpeza] {len(antigos)} objetos obsoletos apagados")
    return antigos


def conferir(url_site: str, com_documentos: bool) -> None:
    """GET de verdade nas rotas que importam, com status, Content-Type e o começo do corpo."""
    alvos = [("/", "página inicial"), ("/painel", "aba Painel (302 para /painel/ e 200)"),
             ("/grafo", "aba Grafo"), ("/timeline", "aba Timeline"), ("/busca", "aba Busca, com o aviso"),
             ("/dados/painel.json", "dados do Painel e do Grafo"),
             ("/linha_do_tempo/empresas.json", "lista de empresas da Timeline")]
    if com_documentos:
        alvos.append(("/dados/busca_resumo.json", "documentos indexados (Grafo)"))
    for caminho, o_que in alvos:
        try:
            with urllib.request.urlopen(url_site + caminho, timeout=120) as r:
                status, tipo_resposta, corpo = r.status, r.headers.get("Content-Type"), r.read(220)
        except urllib.error.HTTPError as e:
            status, tipo_resposta, corpo = e.code, e.headers.get("Content-Type"), e.read(220)
        print(f"[confere] {caminho} -> {status} {tipo_resposta} ({o_que})")
        print(f"          {corpo[:200]!r}")
        if status != 200:
            raise Falha(f"{url_site}{caminho} respondeu {status}, esperava 200")


def argumentos():
    p = argparse.ArgumentParser(description="Publica a vitrine estática do site num bucket S3.")
    p.add_argument("--instalacao", type=Path,
                   help="raiz da instalação que tem .runtime/ e data/painel.json (padrão: este repositório)")
    p.add_argument("--bucket", help=f"nome do bucket (padrão: {PREFIXO_BUCKET}-<conta>)")
    p.add_argument("--sem-build", action="store_true", help="reaproveita o client/dist-vitrine já compilado")
    p.add_argument("--sem-documentos", action="store_true",
                   help="publica sem dados/busca_resumo.json; o Grafo mostra o aviso de documentos indisponíveis")
    return p.parse_args()


def main() -> int:
    args = argumentos()
    raiz = Path(__file__).resolve().parent.parent
    instalacao = (args.instalacao or raiz).resolve()

    try:
        conta = boto3.client("sts", region_name=REGIAO).get_caller_identity()["Account"]
    except (ClientError, BotoCoreError) as e:
        raise Falha(f"sem credencial AWS válida (~/.aws/credentials): {type(e).__name__}: {e}")
    bucket = args.bucket or f"{PREFIXO_BUCKET}-{conta}"
    print(f"[aws] conta {conta}, bucket {bucket}, região {REGIAO}")

    dist = compilar(raiz, instalacao) if not args.sem_build else exigir(
        raiz / SAIDA_BUILD, "compile antes (rode sem --sem-build)")
    itens = itens_do_site(dist, raiz, instalacao, not args.sem_documentos)

    s3 = boto3.client("s3", region_name=REGIAO)
    garantir_bucket(s3, bucket)
    enviar(bucket, itens)
    remover_obsoletos(s3, bucket, {chave for chave, _, _ in itens})

    url_site = f"http://{bucket}.s3-website-{REGIAO}.amazonaws.com"
    conferir(url_site, not args.sem_documentos)
    print(f"\nSite no ar: {url_site}/")
    print(f"HTTPS só por arquivo, sem página inicial: https://{bucket}.s3.amazonaws.com/index.html")
    print("Sem chat e sem aba Busca (precisam de servidor). Detalhes em infra/SITE.md.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Falha as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        sys.exit(1)

"""Baixa as bases públicas que alimentam o banco da plataforma (idempotente: pula o que já existe).

Uso: python data/baixar.py [--forcar] [--fonte ...]
Grava em DIR/raw/ (padrão data/raw). Os arquivos do Drive
(ANEEL, ONS, BNDES, ANBIMA, PDFs) são trazidos com rclone; este script cobre o que tem URL pública estável.
"""
import argparse
import base64
import json
import os
import re
import sys
import tempfile
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raiz do repositório


CVM = "https://dados.cvm.gov.br/dados/CIA_ABERTA"
ANEEL_DEC = "https://dadosabertos.aneel.gov.br/dataset/d5f0712e-62f6-4736-8dff-9991f10758a7/resource"
ARQUIVOS = {
    "cvm/cad_cia_aberta.csv": f"{CVM}/CAD/DADOS/cad_cia_aberta.csv",
    **{f"cvm/dfp/dfp_cia_aberta_{a}.zip": f"{CVM}/DOC/DFP/DADOS/dfp_cia_aberta_{a}.zip" for a in range(2020, 2026)},
    **{f"cvm/fca/fca_cia_aberta_{a}.zip": f"{CVM}/DOC/FCA/DADOS/fca_cia_aberta_{a}.zip" for a in (2025, 2026)},
    # ITR: demonstrações trimestrais (o ano corrente e o anterior, para os últimos 12 meses)
    **{f"cvm/itr/itr_cia_aberta_{a}.zip": f"{CVM}/DOC/ITR/DADOS/itr_cia_aberta_{a}.zip" for a in (2024, 2025, 2026)},
    # ANEEL: indicadores coletivos de continuidade (DEC e FEC), limites por conjunto e dicionário dos códigos
    "aneel/dec_fec_2020_2029.parquet": f"{ANEEL_DEC}/d7f70fb1-725c-4748-afeb-65c6a78df550/download/indicadores-continuidade-coletivos-2020-2029.parquet",
    "aneel/dec_fec_limites.csv": f"{ANEEL_DEC}/fd69e1dd-fd66-4269-b60c-cc0b7eb221b4/download/indicadores-continuidade-coletivos-limite.csv",
    "aneel/dec_fec_dominio.csv": f"{ANEEL_DEC}/17fc99b7-e707-4ec4-9553-a43d7a41f7a6/download/dominio-indicadores.csv",
    # ONS: um mês do detalhamento por usina, usado como mapa conjunto -> usinas (com CEG) dos cortes de geração
    "ons/mapa_conjuntos_eolica.parquet": "https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/restricao_coff_eolica_detail_tm/RESTRICAO_COFF_EOLICA_DETAIL_2026_08.parquet",
    "ons/mapa_conjuntos_solar.parquet": "https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/restricao_coff_fotovoltaica_detail_tm/RESTRICAO_COFF_FOTOVOLTAICA_DETAIL_2026_08.parquet",
}
# ANEEL, dados abertos (dadosabertos.aneel.gov.br): arquivos únicos, regravados pela agência a cada atualização
ANEEL = "https://dadosabertos.aneel.gov.br/dataset"
ARQUIVOS_ANEEL = {
    # composição societária declarada à ANEEL (REN 948/2021): cadeia de controle de cada agente até o controlador final
    "aneel/societaria/composicao-societaria-polimero.parquet": f"{ANEEL}/cb79864b-0cfd-475a-8b7a-f8f23d86cf31/resource/958af64f-863b-4557-a404-5729c4a06a09/download/composicao-societaria-polimero.parquet",
    "aneel/societaria/dm-composicao-societaria-polimero.pdf": f"{ANEEL}/cb79864b-0cfd-475a-8b7a-f8f23d86cf31/resource/3e48fa49-8dcb-44aa-9a7c-7673fff1c74b/download/dm-composicao-societaria-polimero.pdf",
    # SIGET: RAP por módulo de transmissão (lista prévia do reajuste) e dicionário
    "aneel/siget_rap/siget-lista-modulos-previa-reajuste-rap.csv": f"{ANEEL}/beefe870-7452-4830-a7b0-6611e3d5eff6/resource/5e4e4916-fd70-44c7-a0eb-92bfb4efad6b/download/siget-lista-modulos-previa-reajuste-rap.csv",
    "aneel/siget_rap/dm-siget-lista-modulos-previa-reajuste-rap.pdf": f"{ANEEL}/beefe870-7452-4830-a7b0-6611e3d5eff6/resource/f662316a-3873-4d01-904f-3e162b0a05a1/download/dm-siget-lista-de-modulos-previa-reajuste-receita-anual-permitida-rap.pdf",
    # micro e minigeração distribuída (MMGD): um registro por empreendimento conectado
    "aneel/mmgd/empreendimento-geracao-distribuida.parquet": f"{ANEEL}/5e0fafd2-21b9-4d5b-b622-40438d40aba2/resource/cd29f6eb-e08d-4db7-b6fb-ed6e3b682d27/download/empreendimento-geracao-distribuida.parquet",
    "aneel/mmgd/dm-geracao-distribuida-relacao-de-empreendimentos.pdf": f"{ANEEL}/5e0fafd2-21b9-4d5b-b622-40438d40aba2/resource/3fabb9e8-668a-4f94-8f0e-ed9cd2682979/download/dm-geracao-distribuida-relacao-de-empreendimentos.pdf",
    # RALIE: acompanhamento da expansão da geração (usinas em construção e previstas, com cronograma)
    "aneel/ralie/ralie-usina-atual.csv": f"{ANEEL}/57e4b8b5-a5db-40e6-9901-27ca629d0477/resource/4a615df8-4c25-48fa-bbea-873a36a79518/download/ralie-usina-atual.csv",
    "aneel/ralie/ralie-unidade-geradora-atual.csv": f"{ANEEL}/57e4b8b5-a5db-40e6-9901-27ca629d0477/resource/8a794ee4-3d41-4ce7-a80a-ae7702a16b7b/download/ralie-unidade-geradora-atual.csv",
    "aneel/ralie/dm-ralie-usina.pdf": f"{ANEEL}/57e4b8b5-a5db-40e6-9901-27ca629d0477/resource/63cf6fcc-14f1-43d4-b8d8-e011d51cdc32/download/dm-ralie-relatorio-de-acompanhamento-da-expansao-da-oferta-de-geracao-usina.pdf",
    # SAMP balanço: mercado e receita das distribuidoras por mês e classe de consumo
    "aneel/samp/samp-balanco.parquet": f"{ANEEL}/3193ebab-81b3-406e-be0e-f968a4a21689/resource/cffe3c15-9d3e-4187-ae63-e097cf88c0af/download/samp-balanco.parquet",
    "aneel/samp/dd-samp.pdf": f"{ANEEL}/3e153db4-a503-4093-88be-75d31b002dcf/resource/7dbb8074-9168-4e11-9380-1aab3c9ebba3/download/dd-samp.pdf",
    "aneel/samp/dm-samp-balanco.pdf": f"{ANEEL}/3193ebab-81b3-406e-be0e-f968a4a21689/resource/84ee7a78-e7b3-4e43-99ba-99e1d71b2a7c/download/dm-samp-balanco.pdf",
    # bandeiras tarifárias: acionamento mensal e adicional em R$/MWh
    "aneel/bandeiras/bandeira-tarifaria-acionamento.csv": f"{ANEEL}/7f43a020-6dc5-44b8-80b4-d97eaa94436c/resource/0591b8f6-fe54-437b-b72b-1aa2efd46e42/download/bandeira-tarifaria-acionamento.csv",
    "aneel/bandeiras/bandeira-tarifaria-adicional.csv": f"{ANEEL}/7f43a020-6dc5-44b8-80b4-d97eaa94436c/resource/5879ca80-b3bd-45b1-a135-d9b77c1d5b36/download/bandeira-tarifaria-adicional.csv",
    # cadastro de agentes (CNPJ, sigla e razão social de distribuidoras, transmissoras e geradoras)
    "aneel/agentes/agentes-setor-eletrico.csv": f"{ANEEL}/71d1007e-7e14-4875-8758-7e3a0d1118df/resource/64250fc9-4f7a-4d97-b0d4-3c090e005e1c/download/agentes-setor-eletrico.csv",
    # ranking oficial de continuidade (DGC) das distribuidoras, publicado como tabela HTML no gov.br
    **{f"aneel/ranking_continuidade/ranking_{a}.html":
       f"https://www.gov.br/aneel/pt-br/centrais-de-conteudos/relatorios-e-indicadores/distribuicao/ranking-de-continuidade/{a}"
       for a in range(2021, 2026)},
    # SND (ANBIMA/B3): características de todas as debêntures registradas, com CNPJ, vencimento, índice e taxa
    "snd/debentures_caracteristicas.xls": "https://www.debentures.com.br/exploreosnd/consultaadados/emissoesdedebentures/caracteristicas_e.asp?tip_deb=publicas&",
}
# Banco Central, SGS: séries macro mensais (código SGS -> arquivo). Diárias vêm em janelas de 10 anos.
BCB_SERIES = {433: "ipca_mensal", 13522: "ipca_12m", 189: "igpm_mensal", 4390: "selic_mensal", 4391: "cdi_mensal",
              432: "selic_meta", 3698: "dolar_ptax_venda_media_mensal"}
# ONS, catálogo CKAN (dados.ons.org.br): conjunto -> (pasta em raw/ons, regex do nome do arquivo, primeiro período)
ONS_SERIES = {
    "carga-energia": ("carga_energia_diaria", r"CARGA_ENERGIA_(\d{4})\.parquet", "2000"),
    "ena-diario-por-subsistema": ("ena_diario_subsistema", r"ENA_DIARIO_SUBSISTEMA_(\d{4})\.parquet", "2000"),
    "balanco-energia-subsistema": ("balanco_energia_subsistema", r"BALANCO_ENERGIA_SUBSISTEMA_(\d{4})\.parquet", "2015"),
    "intercambio-nacional": ("intercambio_nacional", r"INTERCAMBIO_NACIONAL_(\d{4})\.parquet", "2015"),
    "geracao-usina-2": ("geracao_usina", r"GERACAO_USINA-2_(\d{4}(?:_\d{2})?)\.parquet", "2020"),
}
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
# B3: carteira teórica de um índice. A API recebe o pedido como JSON em base64 no fim da URL. O código do índice de
# energia elétrica é IEEX; com "IEE" a B3 responde 200 com results: null (foi assim que um iee_api.json vazio entrou na
# árvore), por isso baixar_b3 exige results preenchido antes de gravar.
B3_INDICES = {"cvm/iee_api.json": "IEEX"}
B3_CARTEIRA = "https://sistemaswebb3-listados.b3.com.br/indexProxy/indexCall/GetPortfolioDay/"


def baixar(url, destino):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    # Um nome exclusivo preserva downloads parciais de uma execução anterior.
    with tempfile.NamedTemporaryFile(dir=os.path.dirname(destino), suffix=".part", delete=False) as f:
        tmp = f.name
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                while bloco := r.read(1 << 20):
                    f.write(bloco)
            os.replace(tmp, destino)
        except BaseException:
            os.unlink(tmp)
            raise


def arquivos_ons(dataset: str, desde: str) -> dict:
    """Parquets mensais de um conjunto de dados do ONS (portal CKAN), a partir de AAAA_MM."""
    req = urllib.request.Request(f"https://dados.ons.org.br/api/3/action/package_show?id={dataset}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        recursos = json.load(r)["result"]["resources"]
    saida = {}
    for rec in recursos:
        url = rec.get("url") or ""
        m = re.search(r"_(\d{4}_\d{2})\.parquet$", url)
        if m and m.group(1) >= desde:
            saida[f"ons/{dataset}/{url.rsplit('/', 1)[1]}"] = url
    return saida


def arquivos_ons_anuais(dataset: str, prefixo: str, pasta: str) -> dict:
    """Parquets anuais publicados no catálogo CKAN oficial do ONS."""
    url_catalogo = f"https://dados.ons.org.br/api/3/action/package_show?id={dataset}"
    req = urllib.request.Request(url_catalogo, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        recursos = json.load(r)["result"]["resources"]
    saida = {}
    for rec in recursos:
        url = rec.get("url") or ""
        nome = url.rsplit("/", 1)[-1]
        if rec.get("format", "").upper() == "PARQUET" and re.fullmatch(rf"{prefixo}_\d{{4}}\.parquet", nome):
            saida[f"ons/{pasta}/{nome}"] = url
    return saida


def arquivos_ons_catalogo(dataset: str, pasta: str, padrao: str, desde: str) -> dict:
    """Parquets de um conjunto do ONS cujo nome casa com o padrão (grupo 1 = período AAAA ou AAAA_MM)."""
    req = urllib.request.Request(f"https://dados.ons.org.br/api/3/action/package_show?id={dataset}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        recursos = json.load(r)["result"]["resources"]
    saida = {}
    for rec in recursos:
        url = rec.get("url") or ""
        nome = url.rsplit("/", 1)[-1]
        m = re.fullmatch(padrao, nome)
        if m and m.group(1) >= desde:
            saida[f"ons/{pasta}/{nome}"] = url
    return saida


def arquivos_aneel_catalogo(dataset: str, pasta: str, padrao: str, desde: str) -> dict:
    """Arquivos de um conjunto da ANEEL (CKAN) cujo nome casa com o padrão (grupo 1 = ano), a partir de um ano."""
    req = urllib.request.Request(f"https://dadosabertos.aneel.gov.br/api/3/action/package_show?id={dataset}",
                                 headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        recursos = json.load(r)["result"]["resources"]
    saida = {}
    for rec in recursos:
        url = rec.get("url") or ""
        nome = url.rsplit("/", 1)[-1]
        m = re.fullmatch(padrao, nome)
        if m and m.group(1) >= desde:
            saida[f"aneel/{pasta}/{nome}"] = url
    return saida


def baixar_bcb(dados: str, forcar: bool) -> int:
    """Séries do SGS do Banco Central em JSON (api.bcb.gov.br), de 2000 em diante, em raw/bcb/sgs_<codigo>.json."""
    import datetime
    falhas = 0
    pasta = os.path.join(dados, "raw", "bcb")
    os.makedirs(pasta, exist_ok=True)
    for codigo, nome in BCB_SERIES.items():
        destino = os.path.join(pasta, f"sgs_{codigo}_{nome}.json")
        if os.path.exists(destino) and not forcar:
            continue
        pontos = []
        try:
            for inicio in range(2000, datetime.date.today().year + 1, 10):  # a API limita séries diárias a 10 anos
                url = (f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json"
                       f"&dataInicial=01/01/{inicio}&dataFinal=31/12/{inicio + 9}")
                req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
                for tentativa in range(3):  # a API do SGS às vezes devolve página de erro em HTML
                    try:
                        with urllib.request.urlopen(req, timeout=120) as r:
                            pontos += json.load(r)
                        break
                    except ValueError:
                        if tentativa == 2:
                            raise
            with open(destino + ".part", "w") as f:
                json.dump(pontos, f)
            os.replace(destino + ".part", destino)
            print(f"ok    bcb/{os.path.basename(destino)} ({len(pontos)} pontos)")
        except Exception as e:
            falhas += 1
            print(f"FALHA bcb {codigo}: {e}", file=sys.stderr)
    return falhas


def baixar_b3(dados: str, forcar: bool) -> int:
    """Carteira teórica dos índices da B3 em JSON. Só grava resposta com results: sem isso a falha é ALTA (conta como
    falha e não escreve arquivo), porque um JSON vazio no lugar do certo passa batido na montagem do banco."""
    falhas = 0
    for rel, indice in B3_INDICES.items():
        destino = os.path.join(dados, "raw", rel)
        if os.path.exists(destino) and os.path.getsize(destino) > 0 and not forcar:
            continue
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        pedido = {"language": "pt-br", "pageNumber": 1, "pageSize": 120, "index": indice, "segment": "1"}
        url = B3_CARTEIRA + base64.b64encode(json.dumps(pedido, separators=(",", ":")).encode()).decode()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                corpo = json.load(r)
            if not corpo.get("results"):
                raise ValueError(f"resposta sem results (índice {indice} existe na B3?); nada foi gravado")
            with open(destino + ".part", "w") as f:
                json.dump(corpo, f, ensure_ascii=False)
            os.replace(destino + ".part", destino)
            print(f"ok    {rel} ({len(corpo['results'])} ativos, carteira de {corpo['header']['date']})")
        except Exception as e:
            falhas += 1
            print(f"FALHA b3 {indice}: {e}", file=sys.stderr)
    return falhas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--forcar", action="store_true", help="baixa de novo mesmo o que já existe")
    ap.add_argument("--fonte", choices=("todas", "ons-cmo", "ons-ear", "aneel", "bcb", "ons-series", "b3"),
                    default="todas", help="limita a coleta a uma fonte")
    a = ap.parse_args()
    falhas = 0
    alvos = dict(ARQUIVOS) if a.fonte == "todas" else {}
    # cortes de geração (constrained-off) eólica e solar por usina e meia hora, 2023 em diante
    for dataset in (("restricao_coff_eolica_usi", "restricao_coff_fotovoltaica") if a.fonte == "todas" else ()):
        try:
            alvos.update(arquivos_ons(dataset, "2023_01"))
        except Exception as e:
            falhas += 1
            print(f"FALHA listar {dataset} no ONS: {e}", file=sys.stderr)
    for dataset, prefixo, pasta in (
        ("cmo-semi-horario", "CMO_SEMIHORARIO", "cmo_semi_horario"),
        ("ear-diario-por-subsistema", "EAR_DIARIO_SUBSISTEMA", "ear_diario_subsistema"),
    ):
        if a.fonte != "todas" and a.fonte != ("ons-cmo" if prefixo == "CMO_SEMIHORARIO" else "ons-ear"):
            continue
        try:
            alvos.update(arquivos_ons_anuais(dataset, prefixo, pasta))
        except Exception as e:
            falhas += 1
            print(f"FALHA listar {dataset} no ONS: {e}", file=sys.stderr)
    if a.fonte in ("todas", "aneel"):
        alvos.update(ARQUIVOS_ANEEL)
        try:  # SAMP: mercado e receita das distribuidoras, um Parquet por ano
            alvos.update(arquivos_aneel_catalogo("samp", "samp", r"samp-(\d{4})\.parquet", "2020"))
        except Exception as e:
            falhas += 1
            print(f"FALHA listar samp na ANEEL: {e}", file=sys.stderr)
    if a.fonte in ("todas", "bcb"):
        falhas += baixar_bcb(os.path.join(RAIZ, "data"), a.forcar)
    if a.fonte in ("todas", "b3"):
        falhas += baixar_b3(os.path.join(RAIZ, "data"), a.forcar)
    for dataset, (pasta, padrao, desde) in (ONS_SERIES.items() if a.fonte in ("todas", "ons-series") else ()):
        try:
            alvos.update(arquivos_ons_catalogo(dataset, pasta, padrao, desde))
        except Exception as e:
            falhas += 1
            print(f"FALHA listar {dataset} no ONS: {e}", file=sys.stderr)
    for rel, url in alvos.items():
        destino = os.path.join(os.path.join(RAIZ, "data"), "raw", rel)
        if os.path.exists(destino) and not a.forcar:
            continue
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        try:
            baixar(url, destino)
            print(f"ok    {rel} ({os.path.getsize(destino) / 1e6:.1f} MB)")
        except Exception as e:  # uma fonte fora do ar não impede as outras
            falhas += 1
            print(f"FALHA {rel}: {e}", file=sys.stderr)
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()

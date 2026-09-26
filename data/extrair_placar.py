"""Extrai o Placar da Transição (dados ESG estruturados) dos relatórios de data/docs.duckdb para data/placar.duckdb.

Cada valor guarda arquivo, página, trecho literal, confiança e método, para citar como os demais números da
plataforma. As páginas candidatas são achadas por palavra-chave (sem carregar o modelo de embeddings); a extração é
feita pelo LLM (Bedrock/Claude por padrão) com schema Pydantic; e todo valor passa pela checagem "aparece na página?".

Uso:
  python data/extrair_placar.py                      # todos os grupos, todos os documentos
  python data/extrair_placar.py --grupo emissoes     # só um grupo
  python data/extrair_placar.py --empresa ISA --grupo emissoes
  python data/extrair_placar.py --limite-paginas 4 --seco   # não grava, só imprime
"""
import argparse
import json
import os
import re
import unicodedata
from datetime import datetime, timezone

import duckdb
from pydantic import BaseModel, ValidationError

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raiz do repositório
DOCS = os.path.join(RAIZ, "data", "docs.duckdb")
PLACAR = os.path.join(RAIZ, "data", "placar.duckdb")

MODELO_BEDROCK = "us.anthropic.claude-sonnet-5"
REGIAO = os.environ.get("BEDROCK_AWS_DEFAULT_REGION", "us-west-2")


# ------------------------------------------------------------------ utilidades de texto e número
def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()


def _digitos(valor) -> str:
    """Só os algarismos de um número, para comparar formatações diferentes (1.234,5 ~ 1234,50 ~ 1234.5)."""
    if valor is None:
        return ""
    s = re.sub(r"[^\d]", "", f"{valor}")
    return s.lstrip("0") or "0"


def _aparece_na_pagina(valor: float | None, trecho: str, texto_pagina: str) -> bool:
    """Confiança mínima: o trecho está na página e os algarismos do valor aparecem. Aceita magnitude por extenso
    ("R$ 9,7 bilhões" -> 9,7e9; "5,8 milhões" -> 5,8e6): a mantissa (dígitos sem os zeros do multiplicador) tem de
    estar no trecho citado."""
    trecho_ok = bool(trecho) and _sem_acento(trecho)[:40] in _sem_acento(texto_pagina)
    if valor is None:
        return trecho_ok
    cheio = _digitos(valor)
    mantissa = cheio.rstrip("0") or cheio
    for alvo, onde in ((cheio, texto_pagina), (cheio, trecho), (mantissa, trecho)):
        if len(alvo) >= 2 and _digitos_no_texto(alvo, onde):
            return True
    return len(cheio) < 2 and trecho_ok   # valor de 1 dígito: basta o trecho na página


def _digitos_no_texto(alvo: str, texto: str) -> bool:
    """alvo (só dígitos) aparece no texto tolerando . , e espaço entre os algarismos."""
    if not alvo:
        return False
    padrao = r"[.,\s]*".join(re.escape(c) for c in alvo)
    return re.search(padrao, texto or "") is not None


# ------------------------------------------------------------------ schemas Pydantic por grupo
class Emissao(BaseModel):
    escopo: str            # "1", "2", "2_mercado" ou "3"
    tco2e: float | None    # normalizado para toneladas de CO2 equivalente
    intensidade: float | None = None
    unidade_intensidade: str | None = None
    ano: int | None = None
    pagina: int
    trecho: str


class Meta(BaseModel):
    tipo: str              # "net_zero", "reducao_absoluta", "reducao_intensidade"
    ano_alvo: int | None = None
    escopo_coberto: str | None = None
    valor_alvo: float | None = None
    base_ano: int | None = None
    pagina: int
    trecho: str


class Renovavel(BaseModel):
    pct_capacidade_renovavel: float | None = None
    pct_geracao_renovavel: float | None = None
    ano: int | None = None
    pagina: int
    trecho: str


class Capex(BaseModel):
    capex_total_brl: float | None = None    # em reais
    capex_verde_brl: float | None = None
    definicao_verde: str | None = None
    ano: int | None = None
    pagina: int
    trecho: str


class Framework(BaseModel):
    framework: str         # "GRI", "SASB", "TCFD", "IFRS_S2", "CDP"
    asseguracao_externa: bool | None = None
    assegurador: str | None = None
    pagina: int
    trecho: str


GRUPOS = {
    "emissoes": {
        "modelo": Emissao,
        "tabela": "esg_emissoes",
        "padrao": r"escopo [123]|tco2|toneladas de co|gases de efeito estufa|inventario de emiss|pegada de carbono|ghg",
        "instrucao": (
            "Extraia as emissões de gases de efeito estufa (GEE) desta página. Um item por escopo (1, 2, 3; "
            "escopo 2 por mercado use \"2_mercado\"). Use o TOTAL de cada escopo (não subcategorias) e, se houver "
            "vários anos, o do ano do relatório. tco2e SEMPRE em toneladas de CO2 equivalente: se a tabela estiver "
            "em mil tCO2e, multiplique por 1000. Se houver intensidade (tCO2e/MWh, tCO2e/GWh...), preencha "
            "intensidade e unidade_intensidade. Não some escopos; não invente. Se a página não trouxer emissões, []."
        ),
    },
    "metas": {
        "modelo": Meta,
        "tabela": "esg_metas",
        "padrao": r"net zero|neutralidade|carbono neutro|zero l[ií]quido|meta de redu|sbti|science based|descarboniza",
        "instrucao": (
            "Extraia metas climáticas: net zero/neutralidade (tipo \"net_zero\"), redução absoluta de emissões "
            "(\"reducao_absoluta\") ou de intensidade (\"reducao_intensidade\"). ano_alvo é o ano da meta; "
            "escopo_coberto quais escopos; valor_alvo o percentual/valor quando houver; base_ano o ano-base. []"
            " se a página não trouxer meta climática com número ou ano."
        ),
    },
    "renovavel": {
        "modelo": Renovavel,
        "tabela": "esg_renovavel",
        "padrao": r"renov[aá]ve|matriz (de gera|energ)|capacidade instalada|% de gera|fontes limpas|energia limpa",
        "instrucao": (
            "Extraia o percentual renovável da empresa: pct_capacidade_renovavel (% da capacidade instalada) e/ou "
            "pct_geracao_renovavel (% da geração). Só percentuais explícitos no texto. [] se não houver."
        ),
    },
    "capex": {
        "modelo": Capex,
        "tabela": "esg_capex",
        "padrao": r"investiment|capex|capital investido|aplica[cç][aã]o de recursos",
        "instrucao": (
            "Extraia o investimento (CAPEX) reportado: capex_total_brl em reais (R$ bi -> multiplique por 1e9, "
            "R$ mi -> 1e6) e capex_verde_brl se o texto separar investimento verde/sustentável/de transição "
            "(preencha definicao_verde com como o relatório chama). [] se a página não trouxer CAPEX com valor."
        ),
    },
    "frameworks": {
        "modelo": Framework,
        "tabela": "esg_frameworks",
        "padrao": r"\bgri\b|\bsasb\b|\btcfd\b|ifrs s2|\bcdp\b|assegura|assurance|verifica[cç][aã]o independente|iso 14064",
        "instrucao": (
            "Extraia os frameworks de divulgação citados (framework em {GRI, SASB, TCFD, IFRS_S2, CDP}), um item "
            "por framework. asseguracao_externa=true só se o texto disser que houve verificação/asseguração externa "
            "independente (e assegurador se nomeado). [] se a página não citar nenhum desses frameworks."
        ),
    },
}


# ------------------------------------------------------------------ LLM (Bedrock)
_bedrock = None


def _llm(instrucao: str, texto_pagina: str, pagina: int, empresa: str, ano: int) -> list[dict]:
    global _bedrock
    if _bedrock is None:
        import boto3
        _bedrock = boto3.client("bedrock-runtime", region_name=REGIAO)
    sistema = (
        "Você extrai dados ESG de relatórios corporativos para uma base rastreável. Responda SOMENTE com um array "
        "JSON (sem texto fora dele, sem markdown). Cada objeto deve conter os campos pedidos e, obrigatoriamente, "
        "\"pagina\" (o número informado) e \"trecho\" (uma frase COPIADA LITERALMENTE da página que contém o "
        "valor). Nunca infira números que não estejam escritos na página. Se nada se aplica, responda []."
    )
    prompt = (f"{instrucao}\n\nEmpresa: {empresa}. Ano do relatório: {ano}. Página {pagina}.\n"
              f"Use pagina={pagina}.\n\n--- TEXTO DA PÁGINA ---\n{texto_pagina[:9000]}")
    r = _bedrock.converse(
        modelId=MODELO_BEDROCK,
        system=[{"text": sistema}],
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 2000},
    )
    blocos = r["output"]["message"]["content"]
    saida = next((b["text"] for b in blocos if "text" in b), "").strip()
    m = re.search(r"\[.*\]", saida, re.DOTALL)   # tolera cercas ```json
    if not m:
        return []
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return []


# ------------------------------------------------------------------ candidatos e extração
def paginas_candidatas(con, arquivo: str, padrao: str, limite: int) -> list[tuple[int, str]]:
    rx = re.compile(padrao, re.IGNORECASE)
    linhas = con.execute("SELECT pagina, texto FROM paginas WHERE arquivo = ? ORDER BY pagina", [arquivo]).fetchall()
    marcadas = [(len(rx.findall(_sem_acento(t))), p, t) for p, t in linhas]
    marcadas = [x for x in marcadas if x[0] > 0]
    marcadas.sort(reverse=True)   # mais ocorrências primeiro
    return [(p, t) for _, p, t in marcadas[:limite]]


def extrair_documento(con, doc: dict, grupo: str, limite_paginas: int, seco: bool) -> list[dict]:
    g = GRUPOS[grupo]
    achados = []
    for pagina, texto in paginas_candidatas(con, doc["arquivo"], g["padrao"], limite_paginas):
        try:
            brutos = _llm(g["instrucao"], texto, pagina, doc["empresa"], doc["ano"])
        except Exception as e:
            print(f"    ! erro LLM em {doc['arquivo']} p.{pagina}: {e}")
            continue
        for item in brutos:
            item.setdefault("pagina", pagina)
            try:
                obj = g["modelo"](**item)
            except ValidationError:
                continue
            d = obj.model_dump()
            valor = next((d[k] for k in ("tco2e", "valor_alvo", "pct_capacidade_renovavel", "capex_total_brl")
                          if d.get(k) is not None), None)
            texto_p = con.execute("SELECT texto FROM paginas WHERE arquivo=? AND pagina=?",
                                  [doc["arquivo"], obj.pagina]).fetchone()
            texto_p = texto_p[0] if texto_p else texto
            confianca = 1.0 if _aparece_na_pagina(valor, obj.trecho, texto_p) else 0.0
            achados.append({**d, "arquivo": doc["arquivo"], "cnpj": doc["cnpj"], "empresa": doc["empresa"],
                            "ano_relatorio": doc["ano"], "confianca": confianca})
    if not seco:
        return achados
    for a in achados:
        marca = "ok " if a["confianca"] else "SUSPEITO"
        print(f"    [{marca}] {json.dumps({k: v for k, v in a.items() if k != 'trecho'}, ensure_ascii=False)}")
    return achados


# ------------------------------------------------------------------ persistência
COLUNAS_FONTE = ("arquivo VARCHAR, pagina INTEGER, trecho VARCHAR, confianca DOUBLE, "
                 "metodo VARCHAR, modelo VARCHAR, extraido_em TIMESTAMP")

DDL = {
    "esg_emissoes": f"cnpj VARCHAR, empresa VARCHAR, ano_relatorio INTEGER, escopo VARCHAR, tco2e DOUBLE, "
                    f"intensidade DOUBLE, unidade_intensidade VARCHAR, ano INTEGER, {COLUNAS_FONTE}",
    "esg_metas": f"cnpj VARCHAR, empresa VARCHAR, ano_relatorio INTEGER, tipo VARCHAR, ano_alvo INTEGER, "
                 f"escopo_coberto VARCHAR, valor_alvo DOUBLE, base_ano INTEGER, {COLUNAS_FONTE}",
    "esg_renovavel": f"cnpj VARCHAR, empresa VARCHAR, ano_relatorio INTEGER, pct_capacidade_renovavel DOUBLE, "
                     f"pct_geracao_renovavel DOUBLE, ano INTEGER, {COLUNAS_FONTE}",
    "esg_capex": f"cnpj VARCHAR, empresa VARCHAR, ano_relatorio INTEGER, capex_total_brl DOUBLE, "
                 f"capex_verde_brl DOUBLE, definicao_verde VARCHAR, ano INTEGER, {COLUNAS_FONTE}",
    "esg_frameworks": f"cnpj VARCHAR, empresa VARCHAR, ano_relatorio INTEGER, framework VARCHAR, "
                      f"asseguracao_externa BOOLEAN, assegurador VARCHAR, {COLUNAS_FONTE}",
}


def gravar(con, tabela: str, achados: list[dict], modelo: str):
    cols = [c.split()[0] for c in DDL[tabela].split(", ")]
    agora = datetime.now(timezone.utc)
    arquivos = list({a["arquivo"] for a in achados})
    if arquivos:  # idempotente: reescreve o que já havia daquele(s) documento(s)
        con.execute(f"DELETE FROM {tabela} WHERE arquivo IN (SELECT unnest(?))", [arquivos])
    for a in achados:
        a.setdefault("metodo", "llm+pagina")
        a["modelo"] = modelo
        a["extraido_em"] = agora
        valores = [a.get(c) for c in cols]
        con.execute(f"INSERT INTO {tabela} ({', '.join(cols)}) VALUES ({', '.join(['?'] * len(cols))})", valores)


# colunas que carregam o valor principal de cada tabela (a que precisa aparecer na página), em ordem de preferência
VALOR = {
    "esg_emissoes": ["tco2e"], "esg_metas": ["valor_alvo"],
    "esg_renovavel": ["pct_capacidade_renovavel", "pct_geracao_renovavel"],
    "esg_capex": ["capex_total_brl", "capex_verde_brl"], "esg_frameworks": [],
}


def revalidar():
    """Recomputa a confiança de todas as tabelas a partir do trecho e do valor já gravados (sem chamar o LLM).
    Útil ao afinar a checagem 'valor aparece na página'."""
    docs = duckdb.connect(DOCS, read_only=True)
    paginas = {(a, p): t for a, p, t in docs.execute("SELECT arquivo, pagina, texto FROM paginas").fetchall()}
    docs.close()
    con = duckdb.connect(PLACAR)
    for tabela, cands in VALOR.items():
        cols = [c.split()[0] for c in DDL[tabela].split(", ")]
        linhas = [dict(zip(cols, r)) for r in con.execute(f"SELECT {', '.join(cols)} FROM {tabela}").fetchall()]
        for d in linhas:
            valor = next((d[c] for c in cands if d.get(c) is not None), None)
            texto = paginas.get((d["arquivo"], d["pagina"]), "")
            d["confianca"] = 1.0 if _aparece_na_pagina(valor, d.get("trecho"), texto) else 0.0
        con.execute(f"DELETE FROM {tabela}")
        for d in linhas:
            con.execute(f"INSERT INTO {tabela} ({', '.join(cols)}) VALUES ({', '.join(['?'] * len(cols))})",
                        [d.get(c) for c in cols])
        ok = sum(1 for d in linhas if d["confianca"] > 0)
        print(f"  {tabela}: {ok}/{len(linhas)} com fonte confirmada")
    con.close()
    print(f"ok: {PLACAR}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--revalidar", action="store_true", help="recomputa a confiança sem LLM e sai")
    ap.add_argument("--grupo", choices=list(GRUPOS), help="limita a um grupo (padrão: todos)")
    ap.add_argument("--empresa", help="filtra por nome de empresa (substring)")
    ap.add_argument("--limite-paginas", type=int, default=4, help="páginas candidatas por documento e grupo")
    ap.add_argument("--seco", action="store_true", help="não grava; só imprime o que extrairia")
    a = ap.parse_args()
    if a.revalidar:
        revalidar()
        return

    docs_con = duckdb.connect(DOCS, read_only=True)
    onde = "WHERE tipo NOT IN ('regulacao', 'referencia')"
    params = []
    if a.empresa:
        onde += " AND strip_accents(lower(empresa)) LIKE '%' || strip_accents(lower(?)) || '%'"
        params.append(a.empresa)
    docs = [dict(zip(("arquivo", "empresa", "cnpj", "ano", "tipo"), r)) for r in docs_con.execute(
        f"SELECT arquivo, empresa, cnpj, ano, tipo FROM documentos {onde} ORDER BY empresa, ano", params).fetchall()]

    grupos = [a.grupo] if a.grupo else list(GRUPOS)
    saida = None if a.seco else duckdb.connect(PLACAR)
    if saida:
        for t, ddl in DDL.items():
            saida.execute(f"CREATE TABLE IF NOT EXISTS {t} ({ddl})")

    for grupo in grupos:
        print(f"\n=== grupo {grupo} ===")
        total = 0
        for doc in docs:
            achados = extrair_documento(docs_con, doc, grupo, a.limite_paginas, a.seco)
            bons = [x for x in achados if x["confianca"] > 0]
            if achados:
                print(f"  {doc['empresa']} {doc['ano']}: {len(bons)}/{len(achados)} com fonte confirmada")
            if saida and achados:
                gravar(saida, GRUPOS[grupo]["tabela"], achados, MODELO_BEDROCK)
            total += len(bons)
        print(f"  -> {total} valores com fonte confirmada no grupo {grupo}")
    if saida:
        saida.close()
        print(f"\nok: {PLACAR}")


if __name__ == "__main__":
    main()

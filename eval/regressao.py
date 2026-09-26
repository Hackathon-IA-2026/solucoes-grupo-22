#!/usr/bin/env python3
"""Bateria de regressão: perguntas com resposta conhecida feitas ao chat de verdade, corrigidas automaticamente.

Uso: python3 eval/regressao.py [--perfil coppezip-analista-claude] [--so ID,ID] [--paralelo 2]
Cada caso confere a resposta com expressões regulares (o que precisa aparecer e o que não pode aparecer) e as
ferramentas usadas. Resultado em avaliacoes/regressao_<data>/ (transcrições + resumo.md) e placar na tela.
Os valores esperados vêm das DFP da CVM e dos relatórios indexados; mude aqui quando a base mudar.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # raiz do repositório


AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(RAIZ, ".runtime", "avaliacoes")

# id, pergunta, precisa (regex, todas), nao_pode (regex, nenhuma), ferramentas (pelo menos uma de cada grupo)
CASOS = [
    ("empresa-taesa", "Qual foi a receita líquida da Taesa em 2025?",
     [r"4[,.]6\d*\s*(bi|bilh)|4\.6\d\d[,.]?\d*\s*(mi|milh)|4\.6\d\d\.\d{3}\.\d{3}"], [r"AES ELPA"], [["indicadores_financeiros", "consultar_sql"]]),
    ("empresa-eletrobras", "Qual foi o lucro líquido da Eletrobras em 2024?",
     [r"(?i)axia", r"10[,.]3[78]\d*\s*(bi|bilh)|10\.38\d"], [], [["indicadores_financeiros", "consultar_sql"]]),
    ("empresa-enel-sp", "Qual a tarifa TUSD vigente mais recente da Enel SP para o subgrupo B1 residencial?",
     [r"(?i)eletropaulo|enel"], [r"(?i)EDP S[ãa]o Paulo"], [["consultar_sql"]]),
    ("ebitda-equatorial", "Qual foi o EBITDA da Equatorial em 2024 e como ele foi calculado?",
     [r"11[,.]3\d*\s*(bi|bilh)|11\.39\d", r"(?i)deprecia"], [], [["indicadores_financeiros", "consultar_sql"]]),
    ("alavancagem-comparada", "Compare a dívida líquida/EBITDA de 2025 da Equatorial e da Taesa.",
     [r"3[,.]9\d?\s*x|3[,.]9\d?\s*vezes|3[,.]90", r"3[,.]6\d?\s*x|3[,.]6\d?\s*vezes|3[,.]66"], [], [["indicadores_financeiros", "consultar_sql"]]),
    ("serie-receita", "Mostre a receita líquida da Equatorial de 2020 a 2025.",
     [r"17[,.]8\d?|17\.89", r"52[,.]0\d?|52\.07"], [], [["indicadores_financeiros", "consultar_sql"]]),
    ("capacidade-engie", "Qual é a capacidade instalada em operação da Engie Brasil Energia por fonte, segundo a ANEEL?",
     [r"(?i)h[ií]dric|hidrel", r"(?i)MW"], [r"7[,.]69\s*MW"], [["consultar_sql"]]),
    ("leiloes", "Quantos empreendimentos solares foram contratados em leilões de geração em 2019 e qual o deságio médio?",
     [r"\d"], [r"(?i)n[ãa]o (h[áa]|existe|temos) dados? de leil"], [["consultar_sql"]]),
    ("bndes", "Quanto o BNDES contratou em operações não automáticas com empresas do setor elétrico em 2023?",
     [r"(?i)bi|mi"], [], [["consultar_sql"]]),
    ("debentures-taesa", "Quais debêntures incentivadas a Taesa emitiu e em que valores?",
     [r"(?i)TAEE|TAES"], [], [["consultar_sql"]]),
    ("docs-cemig-emissoes", "Quais foram as emissões de escopo 1 e escopo 2 da Cemig no inventário de 2025? Cite a página.",
     [r"(?i)escopo 1", r"(?i)p[áa]g|p\. ?\d"], [], [["buscar_documentos", "ler_pagina"]]),
    ("docs-meta-engie", "Qual é a meta de descarbonização ou net zero da Engie Brasil? Cite o relatório e a página.",
     [r"(?i)net.?zero|carbono|emiss", r"(?i)p[áa]g|p\. ?\d"], [], [["buscar_documentos", "ler_pagina"]]),
    ("docs-cvm-244", "O que a Resolução CVM 244 de 2026 mudou no relatório de sustentabilidade baseado no IFRS S1 e S2?",
     [r"(?i)193"], [], [["buscar_documentos", "ler_pagina"]]),
    # casos da rodada 2 das personas (24/09): investimento de transmissora, cortes de geração, DEC/FEC e respostas vazias
    ("investimento-taesa", "Quanto a Taesa investiu em 2025, incluindo as obras das concessões?",
     [r"1[,.]7[78]\d*\s*(bi|bilh)|1\.78\d[,.]?\d*\s*(mi|milh)"], [r"(?i)investi\w* (total )?de R\$ ?43"], [["indicadores_financeiros", "consultar_sql"]]),
    ("curtailment-2025", "Quanta energia eólica foi cortada (curtailment) no Brasil em 2025, em TWh, e qual o percentual da geração de referência?",
     [r"26[,.][12]\d*\s*TWh", r"19[,.][34]\d*\s*%"], [], [["consultar_sql"]]),
    ("curtailment-nordeste-2024", "No ano de 2024, quanta energia eólica e solar foi restringida por curtailment no submercado Nordeste?",
     [r"9[,.][45]\d*\s*TWh|9\.4\d\d[,.]?\d*\s*GWh"], [], [["consultar_sql"]]),
    ("dec-fec-enel-2024", "Qual foi o DEC e o FEC da Enel SP em 2024 e como eles se comparam com os limites?",
     [r"6[,.]68", r"3[,.]2[01]", r"(?i)m[ée]dia ponderada|m[ée]dio ponderado|ponderad"], [], [["consultar_sql"]]),
    ("ranking-renovaveis", "Quais grupos econômicos têm mais capacidade renovável em operação no Brasil segundo a ANEEL?",
     [r"(?i)MW|GW"], [], [["consultar_sql"]]),
    ("trimestre-taesa", "Qual foi a receita líquida da Taesa no 2º trimestre de 2026 e a dívida líquida/EBITDA dos últimos 12 meses?",
     [r"1[.,]06[78]|1[,.]07\s*(bi|bilh)", r"3[,.]4[78]"], [], [["indicadores_financeiros", "consultar_sql"]]),
    # casos da rodada 3 (24-25/09): entidade de grupo x distribuidora, escala em bilhões e dados novos do ONS
    ("entidade-coelba", "Qual foi a receita líquida da Neoenergia Coelba em 2025?",
     [r"18[,.]3[78]\d*\s*(bi|bilh)|18\.3[78]\d[,.]?\d*\s*(mi|milh)"], [r"52[,.]6\d*\s*(bi|bilh)"], [["indicadores_financeiros", "consultar_sql"]]),
    ("escala-axia", "Qual foi a receita líquida da Axia (ex-Eletrobras) em 2024?",
     [r"40[,.]1[78]\d*\s*(bi|bilh)|40\.18\d[,.]?\d*\s*(mi|milh)"], [r"4[,.]0[12]\s*(bi|bilh)"], [["indicadores_financeiros", "consultar_sql"]]),
    ("cmo-sudeste", "Qual foi o CMO médio do subsistema Sudeste em julho de 2026, segundo o ONS?",
     [r"111[,.]5\d?"], [], [["consultar_sql"]]),
    # casos das bases acrescentadas em 25/09 (valores conferidos nos arquivos da ANEEL e do SND)
    ("grupo-eolica", "Quais grupos econômicos têm mais capacidade eólica em operação no Brasil, considerando as participações indiretas nas SPEs?",
     [r"(?i)enel", r"3[,.][12]\d*\s*GW|3\.2\d\d[,.]?\d*\s*MW"], [], [["consultar_sql"]]),
    ("rap-taesa", "Qual a RAP ativa das concessões em nome da própria Taesa (CNPJ 07.859.971/0001-30), sem somar SPEs nem participações, segundo a lista prévia do reajuste da ANEEL?",
     [r"2[,.]31\d*\s*(bi|bilh)|2\.31\d[,.]?\d*\s*(mi|milh)"], [], [["consultar_sql"]]),
    ("debentures-taesa-2028", "Quanto das debêntures da Taesa (holding) em circulação vence até o fim de 2028, segundo o SND?",
     [r"2[,.]2[67]\d*\s*(bi|bilh)|2\.26[78][,.]?\d*\s*(mi|milh)"], [], [["consultar_sql"]]),
    ("ranking-continuidade-2025", "Qual distribuidora ficou em primeiro lugar no ranking de continuidade da ANEEL de 2025, entre as de mais de 400 mil unidades consumidoras, e com que DGC?",
     [r"(?i)santa cruz", r"0[,.]54"], [], [["consultar_sql"]]),
    # o PLD da CCEE não está na base; desde 25/09 há o CMO do ONS, que pode aparecer desde que não seja chamado de PLD
    ("sem-dado", "Qual foi o PLD horário do submercado Sudeste ontem?",
     [r"(?i)n[ãa]o (tenho|h[áa]|consta|est[áa]|dispon|possuo|encontr|[ée] (exatamente )?o PLD)|indispon|sem (acesso|dados)|CMO"],
     [r"(?i)PLD (hor[áa]rio )?(foi|de|m[ée]dio de) R\$"], []),
    # Fase 2 — Placar da Transição (emissões conferidas no gabarito de researches/FINDINGS-claude-sonnet-5.md §3.2)
    ("placar-cemig", "Quais foram as emissões de escopo 1, 2 e 3 da Cemig no relatório mais recente? Cite a página.",
     [r"42[,.]86\d", r"376[,.]17\d|376\.174", r"5[,.]9\d+\s*(mi|milh)|5\.911[,.]?\d*", r"(?i)p[áa]g|p\. ?\d"], [],
     [["consultar_placar", "buscar_documentos"]]),
    ("placar-ranking-divulgacao", "Faça um ranking das elétricas pelo score de divulgação ESG e explique o que entra no score.",
     [r"(?i)escopo", r"(?i)assegura|framework|meta", r"(?i)\.pdf|p\. ?\d"], [], [["placar_ranking", "consultar_placar"]]),
    ("radar-consistencia", "Quais alertas o radar de consistência aponta hoje e em que evidências cada um se apoia?",
     [r"(?i)assegura", r"(?i)\.pdf|p\. ?\d"], [r"(?i)fraude comprovad|greenwashing comprovad"], [["radar_consistencia"]]),
    ("carbono-150", "Se o carbono custasse R$ 150 por tonelada, qual seria a exposição das elétricas frente ao EBITDA?",
     [r"(?i)EBITDA", r"150", r"%"], [r"(?i)pre[cç]o (de carbono )?(vigente|atual) no Brasil [ée] R\$"], [["exposicao_carbono"]]),
    ("tela-carbono", "Monte uma tela para eu ver a exposição a preço de carbono.",
     [r"/relatorios/\S+\.html"], [], [["tela_carbono", "tela_ranking"]]),
    # o modo é do usuário: sem pedido de conclusão, compara e mostra, mas não dá veredito nem recomendação
    ("modo-descritivo", "A Cemig é melhor que a CPFL na transição energética?",
     [r"(?i)conclus|parecer|descritiv|se (voc[êe] )?quiser"], [r"(?i)minha recomenda[çc]|recomendo (comprar|vender|investir)"],
     [["consultar_placar", "placar_ranking", "consultar_sql"]]),
]


def rodar(caso, persona, perfil, pasta):
    ident, pergunta, precisa, nao_pode, grupos = caso
    d = os.path.join(pasta, ident)
    os.makedirs(d, exist_ok=True)
    p = subprocess.run([sys.executable, os.path.join(AQUI, "chat.py"), "--persona", persona, "--saida", d, pergunta]
                       + (["--perfil", perfil] if perfil else []),
                       capture_output=True, text=True, timeout=1800)
    saida = p.stdout
    usadas = re.search(r"Ferramentas que o chat usou \(\d+\): (.*)", saida)
    usadas = [f.strip() for f in usadas.group(1).split(",")] if usadas else []
    resposta = saida.split("-" * 60, 1)[-1]
    falhas = [f"faltou /{r}/" for r in precisa if not re.search(r, resposta)]
    falhas += [f"não podia ter /{r}/" for r in nao_pode if re.search(r, resposta)]
    falhas += [f"não usou nenhuma de {g}" for g in grupos if not set(g) & set(usadas)]
    if p.returncode != 0:
        falhas.append(f"erro: {p.stderr.strip()[:200]}")
    segundos = re.search(r"Tempo de resposta: (\d+) s", saida)
    return {"id": ident, "ok": not falhas, "falhas": falhas, "ferramentas": usadas,
            "segundos": int(segundos.group(1)) if segundos else None, "pergunta": pergunta}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", default="teste")
    ap.add_argument("--perfil", help="perfil do librechat.yaml (padrão: o perfil padrão)")
    ap.add_argument("--so", help="ids separados por vírgula")
    ap.add_argument("--paralelo", type=int, default=2)  # o LibreChat aceita 2 mensagens simultâneas por usuário
    a = ap.parse_args()
    casos = [c for c in CASOS if not a.so or c[0] in a.so.split(",")]
    pasta = os.path.join(SAIDA, f"regressao_{datetime.now():%Y-%m-%d_%H%M%S}")
    os.makedirs(pasta, exist_ok=True)
    with ThreadPoolExecutor(a.paralelo) as ex:
        resultados = list(ex.map(lambda c: rodar(c, a.persona, a.perfil, pasta), casos))
    linhas = [f"# Regressão {datetime.now():%Y-%m-%d %H:%M}", "",
              f"**{sum(r['ok'] for r in resultados)}/{len(resultados)} casos passaram**", "",
              "| caso | ok | tempo (s) | ferramentas | falhas |", "|---|---|---|---|---|"]
    for r in resultados:
        linhas.append(f"| {r['id']} | {'sim' if r['ok'] else 'NÃO'} | {r['segundos']} | {', '.join(r['ferramentas'])} | "
                      f"{'; '.join(r['falhas'])} |")
    open(os.path.join(pasta, "resumo.md"), "w").write("\n".join(linhas) + "\n")
    json.dump(resultados, open(os.path.join(pasta, "resultados.json"), "w"), ensure_ascii=False, indent=1)
    print("\n".join(linhas))
    print(f"\nTranscrições em {pasta}")


if __name__ == "__main__":
    main()

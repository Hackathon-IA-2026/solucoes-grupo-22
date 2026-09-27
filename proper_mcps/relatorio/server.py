"""Servidor MCP "energynexus-relatorio": o relatório final em PDF, no modelo LaTeX do Energy Nexus.

Ferramenta: gerar_relatorio. Recebe os campos da capa (título, subtítulo, período), o conteúdo em LaTeX (as seis
seções do modelo) e as referências em BibTeX; confere a forma — a estrutura do modelo, as citações e a presença de
fonte em cada número, nunca o valor em si contra a base; preenche modelo/main.tex e modelo/referencias.bib (o template
oficial, alterado só nos campos e no conteúdo, como ele pede) e compila com o pdflatex do TinyTeX em .runtime/tinytex
(instalar.sh). O PDF e o fonte LaTeX (.zip) vão para .runtime/relatorios, que o iniciar.sh liga em
client/public/assets/relatorios: o navegador os abre em /relatorios/.
As regras de redação (as instruções do template) estão no roteiro proper_skills/relatorio-energynexus/SKILL.md.
"""
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import unicodedata
import zipfile
from datetime import datetime

import duckdb
from mcp.server.mcpserver import MCPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # raiz do repositório
CATALOGO_DB = os.path.join(RAIZ, "data", "energynexus.duckdb")  # só para conferir nomes de tabela citados no relatório


MODELO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modelo")
PASTA = os.path.join(RAIZ, ".runtime", "relatorios")
TEX = os.path.join(RAIZ, ".runtime", "tinytex", "bin", "x86_64-linux")
URL_BASE = "/relatorios"  # o LibreChat serve .runtime/relatorios nesse caminho (iniciar.sh)



def publicar(caminho: str) -> str:
    """Link para baixar um arquivo gravado. Aqui o LibreChat serve a pasta; no AgentCore o arquivo vai para o S3."""
    return f"{URL_BASE}/{os.path.basename(caminho)}"

INSTRUCOES = """Use gerar_relatorio quando o usuário pedir relatório, memorando, ficha, nota para comitê ou documento
para guardar ou enviar. Antes, carregue o roteiro relatorio-energynexus com a ferramenta skill e levante os dados com
as outras ferramentas: gerar_relatorio só confere e compila, não busca dados. Se ela recusar, corrija o que apontou e
chame de novo. No fim, copie na resposta o bloco :::artifact que ela devolve: ele abre o PDF ao lado do chat."""

mcp = MCPServer("energynexus-relatorio", instructions=INSTRUCOES)

SECOES = ["Sumário Executivo", "Introdução", "Dados e Metodologia", "Resultados", "Discussão e Pontos de Atenção",
          "Conclusões e Recomendações"]
TIPOS_BIB = {"misc", "techreport", "article", "book"}
CAMPOS_BIB = ("author", "title", "year")

# comandos que mudariam o template, leriam ou gravariam arquivos, ou que o modelo não suporta (figuras)
PROIBIDO = re.compile(
    r"\\(documentclass|usepackage|RequirePackage|input|include|includeonly|openin|openout|read|write|immediate|"
    r"newread|newwrite|scantokens|everyeof|catcode|def|edef|gdef|xdef|let|newcommand|renewcommand|providecommand|"
    r"makeatletter|csname|special|hypersetup|pagestyle|thispagestyle|geometry|newgeometry|definecolor|bibliography|"
    r"bibliographystyle|nocite|tableofcontents|appendix|chapter|part|includegraphics|verbatiminput)(?![A-Za-z])"
    r"|\\(begin|end)\{(document|titlepage|thebibliography|figure)\*?\}|\^\^")
CITE = re.compile(r"\\[Cc]ite[a-z]*\*?(?:\[[^\]]*\]){0,2}\{([^}]*)\}")
SECAO = re.compile(r"\\section\*?(?:\[[^\]]*\])?\{([^}]*)\}")
TABELA = re.compile(r"\\begin\{table\*?\}.*?\\end\{table\*?\}", re.S)
URL = re.compile(r"https?://\S+")
# número "de verdade": com separador, percentual, múltiplo (3,9x) ou 2+ dígitos; anos (1900-2099) e datas não contam
DATA = re.compile(r"\b\d{1,2}/\d{1,2}(/\d{2,4})?\b|\b\d{1,2}/(19|20)\d\d\b")
NUMERO = re.compile(r"(?<![\w/])(\d+(?:[.,]\d+)*)(\s*%|x\b)?(?![0-9A-WYZa-wyzÀ-ÿ])")
# fim de parágrafo: pontuação, fecho de ambiente ou de argumento, percentual escapado, fecho de citação
FIM = re.compile(r"[.!?:;%)\]}»”\"']\s*$")
# marca de corte no fim do parágrafo; no meio dele "[...]" é supressão dentro de uma citação literal, e vale
CORTE = re.compile(r"(\.\.\.|…|\[truncad[^\]]*\]|\[cortad[^\]]*\])[\s»”\"')\]]*$", re.I)
ARQUIVO = re.compile(r"\S+\.(?:pdf|docx?|xlsx?|csv|parquet|zip|tex|bib|duckdb)\b", re.I)
NOME_TABELA = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b")
# a origem de um número também pode ser a ferramenta que o calculou, não só a tabela: estes nomes valem como fonte
FERRAMENTAS = {"buscar_empresa", "indicadores_financeiros", "listar_tabelas", "descrever_tabela", "valores_distintos",
               "consultar_sql", "buscar_documentos", "ler_pagina", "listar_documentos", "consultar_placar",
               "placar_ranking", "radar_consistencia", "exposicao_carbono", "gerar_relatorio"}


def _sem_comentarios(tex: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", tex)


def _numeros(tex: str) -> list[str]:
    t = CITE.sub(" ", tex)
    t = re.sub(r"\\(label|ref|eqref|pageref|url|href)\{[^}]*\}", " ", t)
    t = t.replace("\\%", "%").replace("{,}", ",").replace("\\,", "").replace("~", " ")
    t = re.sub(r"\\[A-Za-z]+\*?", " ", t)  # nomes de comandos; o texto dos argumentos continua
    t = DATA.sub(" ", URL.sub(" ", re.sub(r"[{}\[\]]", " ", t)))
    achados = []
    for m in NUMERO.finditer(t):
        n, sufixo = m.group(1), m.group(2)
        if re.fullmatch(r"(19|20)\d\d", n) and not sufixo:
            continue
        if sufixo or re.search(r"[.,]", n) or len(n) >= 2:
            achados.append(n + (sufixo or "").strip())
    return achados


def _unidades(conteudo: str) -> list[str]:
    """Parágrafos e itens de lista fora das tabelas: a unidade que precisa citar a fonte dos números que contém."""
    t = TABELA.sub("\n\n", conteudo)
    t = re.sub(r"\\(sub)*section\*?(\[[^\]]*\])?\{[^}]*\}", "\n\n", t)
    t = re.sub(r"\\(begin|end)\{(itemize|enumerate|description)\}|\\item\b", "\n\n", t)
    return [" ".join(p.split()) for p in re.split(r"\n\s*\n", t) if p.strip()]


def _tabelas_citadas(texto: str) -> list[str]:
    """Nomes em snake_case que o texto apresenta como tabela da base. Saem antes: os argumentos de \\cite, \\label e
    \\ref (as chaves BibTeX também são snake_case), links e nomes de arquivo. No LaTeX o nome vem escapado
    (indicadores\\_financeiros), então o \\_ volta a ser _ antes da busca."""
    t = CITE.sub(" ", texto or "")
    t = re.sub(r"\\(label|ref|eqref|pageref|autoref|url|href)\{[^}]*\}", " ", t)
    t = ARQUIVO.sub(" ", URL.sub(" ", t)).replace("\\_", "_")
    return list(dict.fromkeys(NOME_TABELA.findall(t)))


def _catalogo() -> set[str] | None:
    """Tabelas da base, em minúsculas, ou None quando o banco não está ao lado do servidor — aí a conferência dos
    nomes fica registrada como aviso, em vez de sumir sem dizer nada."""
    if not os.path.exists(CATALOGO_DB):
        return None
    con = duckdb.connect(CATALOGO_DB, read_only=True)
    try:
        return {t.lower() for (t,) in con.execute("SELECT tabela FROM catalogo").fetchall()}
    finally:
        con.close()


def _conferir_tabelas(citados: dict[str, list[str]]) -> list[str]:
    """Avisos para nome de tabela que não está no catálogo. A auditoria passou 'tabela_que_nao_existe, conta 9.99' e o
    relatório saiu com cara de auditado. Aviso, não erro: nome de indicador ou de arquivo pode cair aqui por engano."""
    if not any(citados.values()):
        return []
    try:
        catalogo = _catalogo()
        impedimento = f"o banco {os.path.basename(CATALOGO_DB)} não está ao lado do servidor"
    except duckdb.Error as e:  # banco em uso por quem o reconstrói, ou de outra versão
        catalogo, impedimento = None, f"o catálogo não abriu ({e})"
    if catalogo is None:
        return [f"não confiro os nomes de tabela citados: {impedimento}"]
    conhecidos = catalogo | FERRAMENTAS
    return [f"{onde}: '{n}' não é uma tabela nem uma ferramenta da base (confira em listar_tabelas); se o número vem "
            f"de documento ou link, cite o documento e a página" for onde, nomes in citados.items() for n in nomes
            if n.lower() not in conhecidos]


def _paragrafos(conteudo: str) -> list[str]:
    """Parágrafos de texto corrido: sem tabelas, listas e títulos, onde faltar pontuação no fim é estilo, não corte."""
    t = TABELA.sub("\n\n", conteudo)
    t = re.sub(r"\\begin\{(itemize|enumerate|description)\}.*?\\end\{\1\}", "\n\n", t, flags=re.S)
    t = re.sub(r"\\(sub)*section\*?(\[[^\]]*\])?\{[^}]*\}", "\n\n", t)
    return [" ".join(p.split()) for p in re.split(r"\n\s*\n", t) if p.strip()]


def _entradas(bib: str) -> tuple[list[tuple[str, str, set, str]], list[str]]:
    """(tipo, chave, campos, texto) de cada entrada BibTeX; linhas de comentário ficam de fora."""
    bib = "\n".join(l for l in bib.splitlines() if not l.lstrip().startswith("%"))
    entradas, erros, pos = [], [], 0
    inicio = re.compile(r"@(\w+)\s*\{\s*([^,\s{}]*)\s*,")
    while m := inicio.search(bib, pos):
        nivel, j = 1, m.end()
        while j < len(bib) and nivel:
            nivel += {"{": 1, "}": -1}.get(bib[j], 0)
            j += 1
        if nivel:
            erros.append(f"referência {m.group(2) or m.group(1)}: chaves {{ }} desbalanceadas")
            break
        campos = {c.lower() for c in re.findall(r"(\w+)\s*=", bib[m.end():j - 1])}
        entradas.append((m.group(1).lower(), m.group(2), campos, bib[m.start():j]))
        pos = j
    return entradas, erros


def _conferir(titulo, periodo, conteudo, referencias) -> tuple[list[str], list[str], dict, set]:
    erros, avisos = [], []
    if not titulo.strip():
        erros.append("falta o título")
    if not re.fullmatch(r"\d{2}/\d{2}/\d{4} a \d{2}/\d{2}/\d{4}", periodo.strip()):
        erros.append(f"período '{periodo}' fora do formato DD/MM/AAAA a DD/MM/AAAA (ex.: 01/01/2021 a 31/12/2025)")

    for n, linha in enumerate(conteudo.splitlines(), 1):
        m = re.search(r"(?<!\\)%", linha)
        if m and re.search(r"\d\s?$", linha[:m.start()]):
            erros.append(f"linha {n} do conteúdo: '%' sem barra vira comentário e apaga o resto da linha; "
                         f"escreva \\% (ex.: 12,5\\%)")
    texto = _sem_comentarios(conteudo)
    for m in PROIBIDO.finditer(texto):
        onde = texto[:m.start()].count("\n") + 1
        if "includegraphics" in m.group(0) or "figure" in m.group(0):
            erros.append(f"linha {onde} do conteúdo: o relatório não aceita figuras; mostre os dados em tabela")
        else:
            erros.append(f"linha {onde} do conteúdo: {m.group(0)} não é permitido (o preâmbulo, a capa e as "
                         f"referências são do modelo)")
    for n, linha in enumerate(texto.splitlines(), 1):
        if re.search(r"\b(R|US)\$", linha):
            erros.append(f"linha {n} do conteúdo: escreva R\\$ (com barra) em valores monetários")
        puro = re.sub(r"\\(label|ref|eqref|pageref|url|href)\{[^}]*\}|" + CITE.pattern, " ", linha)
        puro = re.sub(r"\$[^$]*\$", " ", puro.replace("\\$", " "))
        if re.search(r"(?<!\\)[_#]", puro):
            erros.append(f"linha {n} do conteúdo: escreva \\_ e \\# fora de \\cite, \\label e \\ref")

    titulos = [" ".join(t.split()) for t in SECAO.findall(texto)]
    if titulos != SECOES:
        erros.append("as seções têm de ser exatamente estas seis, nesta ordem, com \\section{...}: "
                     + "; ".join(SECOES) + f". Veio: {'; '.join(titulos) or 'nenhuma'}")

    entradas, erros_bib = _entradas(referencias)
    erros += erros_bib
    chaves = {}
    for tipo, chave, campos, _ in entradas:
        if not re.fullmatch(r"[a-z0-9_]+", chave):
            erros.append(f"referência '{chave}': use chave fonte_tema_ano, em minúsculas, sem acentos nem espaços")
        if chave in chaves:
            erros.append(f"referência '{chave}' repetida")
        if tipo not in TIPOS_BIB:
            erros.append(f"referência '{chave}': tipo @{tipo}; use misc, techreport, article ou book")
        faltam = [c for c in CAMPOS_BIB if c not in campos]
        if faltam:
            erros.append(f"referência '{chave}': faltam os campos {', '.join(faltam)}")
        chaves[chave] = campos

    citadas = {c.strip() for grupo in CITE.findall(texto) for c in grupo.split(",")}
    if not citadas:
        erros.append("o relatório não cita nenhuma fonte; use \\cite{chave} depois de cada fato")
    for c in sorted(citadas - set(chaves) - {"energynexus_db"}):
        erros.append(f"\\cite{{{c}}} não existe nas referências")
    for c in sorted(set(chaves) - citadas):
        avisos.append(f"a referência {c} não é citada e não aparece no PDF")

    rotulos = re.findall(r"\\label\{([^}]*)\}", texto)
    for r in sorted({r for r in rotulos if rotulos.count(r) > 1}):
        erros.append(f"\\label{{{r}}} repetido")
    for r in sorted(set(re.findall(r"\\(?:eq|page|auto)?ref\{([^}]*)\}", texto)) - set(rotulos)):
        erros.append(f"\\ref{{{r}}} aponta para um \\label que não existe")

    if re.search(r"\\begin\{tabular", TABELA.sub("", texto)):
        erros.append("tabela fora do ambiente table: use o modelo (table com \\caption, \\label{tab:...} e \\fonte)")
    for i, tab in enumerate(TABELA.findall(texto), 1):
        nome = re.search(r"\\caption\{([^}]*)\}", tab)
        onde = f"tabela {i}" + (f" ({nome.group(1)[:60]})" if nome else "")
        if not nome:
            erros.append(f"{onde}: falta \\caption com o título descritivo")
        if not re.search(r"\\label\{tab:", tab):
            erros.append(f"{onde}: falta \\label{{tab:...}}")
        if not re.search(r"\\fonte\{.*\\cite", tab, re.S):
            erros.append(f"{onde}: falta a linha de fonte, \\fonte{{\\cite{{chave}}}}")
    for u in _unidades(texto):
        nums = _numeros(u)
        if nums and not CITE.search(u):
            erros.append(f"o trecho \"{u[:90]}\" tem número ({', '.join(nums[:3])}) sem \\cite")

    # dois relatórios da auditoria foram gravados cortados no meio da frase (a resposta do modelo estourou o limite de
    # saída) e ninguém percebeu. Todo parágrafo de texto corrido acaba em pontuação ou no fecho de um ambiente, então
    # acabar no meio da frase é erro; item de lista e título ficam fora, esses acabam sem ponto por estilo
    for p in _paragrafos(texto):
        if CORTE.search(p):
            erros.append(f"o trecho \"...{p[-60:]}\" termina com marca de corte; reenvie o texto completo")
        elif not FIM.search(p):
            erros.append(f"o trecho \"...{p[-60:]}\" termina no meio da frase, sem pontuação nem fecho de ambiente: "
                         f"parece truncado (a resposta estourou o limite de saída); reenvie o texto completo")

    avisos += _conferir_tabelas({"o conteúdo": _tabelas_citadas(texto),
                                 # sem o "@misc{chave," do começo: a chave BibTeX também é snake_case
                                 **{f"referência {chave}": _tabelas_citadas(re.sub(r"^@\w+\s*\{[^,]*,", " ", bruto))
                                    for _, chave, _, bruto in entradas}})
    return erros, avisos, chaves, citadas


# ------------------------------------------------------------------------------------------------ montagem
def _campo(texto: str) -> str:
    """Texto simples da capa: escapa & % $ # _ que vierem sem barra."""
    return re.sub(r"(?<!\\)([&%$#_])", r"\\\1", " ".join(str(texto or "").split()))


def _main_tex(titulo, subtitulo, periodo, conteudo) -> tuple[str, int]:
    """O template com os campos e o conteúdo; devolve também a linha do main.tex onde o conteúdo começa."""
    with open(os.path.join(MODELO, "main.tex"), encoding="utf-8") as f:
        modelo = f.read()
    for comando, valor in (("titulorelatorio", titulo), ("subtitulorelatorio", subtitulo),
                           ("periodoanalise", periodo)):
        modelo = re.sub(r"(\\newcommand\{\\" + comando + r"\})\{[^\n]*\}",
                        lambda m: m.group(1) + "{" + _campo(valor) + "}", modelo, count=1)
    ini = modelo.index("\\section{Sumário Executivo}")
    fim = modelo.rindex("%% =", 0, modelo.index("%%  FIM DO CONTEÚDO"))
    return modelo[:ini] + conteudo + "\n\n" + modelo[fim:], modelo[:ini].count("\n") + 1


def _referencias_bib(referencias: str, chaves: dict, hoje: str) -> tuple[str, list[tuple[int, str]]]:
    """O referencias.bib do template mais as entradas do relatório; devolve também a linha em que cada uma começa."""
    with open(os.path.join(MODELO, "referencias.bib"), encoding="utf-8") as f:
        modelo = f.read()
    if "energynexus_db" in chaves:
        modelo = re.sub(r"@misc\{energynexus_db,.*?\n\}\n", "", modelo, flags=re.S)
    else:
        modelo = modelo.replace("Versão/extração: DD/MM/AAAA. Tabela/consulta: NOME\\_DA\\_TABELA.",
                                f"Extração: {hoje}.")
    bib, linhas = modelo.rstrip("\n"), []
    for _, chave, _, texto in _entradas(referencias)[0]:
        linhas.append((bib.count("\n") + 3, chave))
        bib += "\n\n" + texto
    return bib + "\n", linhas


def _erros_latex(log: str, inicio: int) -> list[str]:
    """Mensagens "! ..." do main.log com a linha do conteúdo (l.N, contada a partir do início do conteúdo)."""
    linhas, erros = log.splitlines(), []
    for i, linha in enumerate(linhas):
        if not linha.startswith("! "):
            continue
        onde = next((re.match(r"l\.(\d+) (.*)", l) for l in linhas[i + 1:i + 15] if re.match(r"l\.\d+ ", l)), None)
        if onde and int(onde.group(1)) >= inicio:
            erros.append(f"linha {int(onde.group(1)) - inicio + 1} do conteúdo: {linha[2:]} "
                         f"(logo depois de \"{onde.group(2).strip()[-80:]}\")")
        else:
            erros.append(f"{linha[2:]}" + (f" (campos da capa: \"{onde.group(2).strip()[-80:]}\")" if onde else ""))
    return erros[:5]


def _compilar(pasta: str, inicio_tex: int, entradas_bib: list[tuple[int, str]]) -> tuple[list[str], int]:
    """pdflatex, bibtex e mais duas passadas (sumário, referências e "Página x de y"); devolve erros e páginas."""
    env = {**os.environ, "PATH": TEX + os.pathsep + os.environ.get("PATH", ""),
           "openin_any": "p", "openout_any": "p"}  # o TeX só lê e grava dentro da pasta de trabalho
    pdflatex = [os.path.join(TEX, "pdflatex"), "-interaction=nonstopmode", "-halt-on-error", "-no-shell-escape",
                "main.tex"]
    for passo in (pdflatex, [os.path.join(TEX, "bibtex"), "main"], pdflatex, pdflatex):
        try:
            r = subprocess.run(passo, cwd=pasta, env=env, capture_output=True, text=True, errors="replace",
                               timeout=25)  # 4 passos cabem no timeout do servidor no librechat.yaml (120 s)
        except subprocess.TimeoutExpired:
            return ["o LaTeX não terminou em 25 s; simplifique as tabelas e confira chaves { } e ambientes"], 0
        if passo[0].endswith("bibtex"):
            with open(os.path.join(pasta, "main.blg"), encoding="utf-8", errors="replace") as f:
                blg = f.read()
            erros = []
            for msg, n in re.findall(r"^(.*?)---line (\d+) of file referencias\.bib", blg, re.M):
                chave = next((c for ini, c in reversed(entradas_bib) if ini <= int(n)), None)
                erros.append(f"referência {chave}: {msg.strip()}" if chave else f"referências: {msg.strip()}")
            if erros or r.returncode > 1:
                return erros or [blg.strip().splitlines()[-1]], 0
            continue
        with open(os.path.join(pasta, "main.log"), encoding="utf-8", errors="replace") as f:
            log = f.read()
        if r.returncode:
            return _erros_latex(log, inicio_tex) or [f"o pdflatex falhou (código {r.returncode})"], 0
    erros = [f"\\{'cite' if m.group(1) == 'Citation' else 'ref'}{{{m.group(2)}}} ficou indefinido"
             for m in re.finditer(r"(Citation|Reference) `([^']*)' on page \d+ undefined", log)]
    erros += [f"\\label{{{m}}} definido mais de uma vez" for m in re.findall(r"Label `([^']*)' multiply defined", log)]
    paginas = re.search(r"Output written on main\.pdf \((\d+) page", log)
    return erros, int(paginas.group(1)) if paginas else 0


def _slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:50] or "relatorio"


@mcp.tool()
def gerar_relatorio(titulo: str, subtitulo: str, periodo: str, conteudo: str, referencias: str) -> str:
    """Monta o relatório final no modelo do Energy Nexus e compila o PDF. Siga o roteiro relatorio-energynexus.

    titulo, subtitulo: texto simples da capa. periodo: "DD/MM/AAAA a DD/MM/AAAA".
    conteudo: LaTeX com as seis seções, nesta ordem e com estes títulos: Sumário Executivo, Introdução, Dados e
      Metodologia, Resultados, Discussão e Pontos de Atenção, Conclusões e Recomendações (\\section{...} seguida de
      \\label{sec:...}); dentro delas só \\subsection e \\subsubsection. Todo parágrafo ou item com número cita a fonte
      com \\cite{chave}; tabela no ambiente table com \\caption, \\label{tab:...} e \\fonte{\\cite{chave}}. Escape
      % & $ _ # no texto (R\\$ 4,62 bilhões; 12,5\\%). Sem figuras.
    referencias: entradas BibTeX (@misc, @techreport, @article ou @book), uma por fonte citada, com author, title,
      year, url quando houver e note ("Acesso em: DD/MM/AAAA."). A entrada energynexus_db (base interna) já existe.
    Recusa, sem gerar, se faltar ou sobrar seção, se um trecho com número não citar fonte, se uma chave citada não
    existir nas referências, se o texto parecer truncado ou se o LaTeX não compilar; a resposta diz o que corrigir.
    A conferência é de forma (estrutura e citação): os valores não são reconferidos contra a base.
    """
    titulo, subtitulo, periodo = str(titulo or ""), str(subtitulo or ""), str(periodo or "")
    conteudo = str(conteudo or "").replace("\r\n", "\n").strip("\n")  # as linhas dos erros são as deste texto
    referencias = str(referencias or "")
    erros, avisos, chaves, citadas = _conferir(titulo, periodo, conteudo, referencias)
    if erros:
        return ("Relatório NÃO gerado. Corrija e chame gerar_relatorio de novo:\n- "
                + "\n- ".join(list(dict.fromkeys(erros))[:25]))
    quando = datetime.now()
    tex, inicio_tex = _main_tex(titulo, subtitulo, periodo, conteudo)
    bib, entradas_bib = _referencias_bib(referencias, chaves, f"{quando:%d/%m/%Y}")
    with tempfile.TemporaryDirectory(prefix="relatorio-") as pasta:
        shutil.copytree(os.path.join(MODELO, "imagens"), os.path.join(pasta, "imagens"))
        for nome_arquivo, texto in (("main.tex", tex), ("referencias.bib", bib)):
            with open(os.path.join(pasta, nome_arquivo), "w", encoding="utf-8") as f:
                f.write(texto)
        erros, paginas = _compilar(pasta, inicio_tex, entradas_bib)
        if erros:
            return ("Relatório NÃO gerado: o LaTeX não compilou. Corrija e chame gerar_relatorio de novo:\n- "
                    + "\n- ".join(erros))
        os.makedirs(PASTA, exist_ok=True)
        nome = f"{quando:%Y%m%d-%H%M%S}-{_slug(titulo)}-{secrets.token_hex(4)}"
        shutil.copy(os.path.join(pasta, "main.pdf"), os.path.join(PASTA, nome + ".pdf"))
        with zipfile.ZipFile(os.path.join(PASTA, nome + ".zip"), "w", zipfile.ZIP_DEFLATED) as z:
            for arquivo in ("main.tex", "referencias.bib", "imagens/zip_logo.png"):
                z.write(os.path.join(pasta, arquivo), arquivo)
    pdf = publicar(os.path.join(PASTA, nome + ".pdf"))
    rotulo = re.sub(r'["{}\n]', "", " ".join(titulo.split()))
    return "\n".join([
        f"Relatório gerado: {paginas} páginas, {len(citadas)} referências.",
        f"PDF: {pdf}",
        f"Fonte LaTeX (main.tex, referencias.bib e imagens): {publicar(os.path.join(PASTA, nome + '.zip'))}",
        "Conferência de forma: todo trecho com número cita \\cite e toda tabela tem linha de fonte. Os valores NÃO "
        "foram reconferidos na base — não diga ao usuário que os números foram conferidos automaticamente.",
        *(["Avisos: " + "; ".join(avisos)] if avisos else []),
        "",
        "Na resposta ao usuário, resuma os principais achados em 2 a 4 frases e termine com o bloco abaixo, copiado",
        "sem nenhuma mudança: ele abre o PDF grande no painel ao lado do chat, com o botão de baixar.",
        "",
        f':::artifact{{identifier="relatorio-{nome}" type="application/pdf" title="{rotulo}.pdf"}}',
        "```",
        pdf,
        "```",
        ":::",
    ])


if __name__ == "__main__":
    mcp.run()

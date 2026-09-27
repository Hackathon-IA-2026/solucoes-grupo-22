"""Servidor MCP "coppezip-relatorio": grava o relatório final da análise em Markdown, DOCX e LaTeX, com fontes conferidas.

Ferramenta: gerar_relatorio. Recebe título, sumário, seções (texto, tabelas e subseções), lacunas e a lista de fontes, e
recusa o relatório se algum trecho com número não citar uma fonte ([F1], [F2]...) ou se uma tabela com números não tiver
fonte.
Os arquivos vão para .runtime/relatorios, que o iniciar.sh liga em client/public/assets/relatorios do LibreChat; o
navegador os baixa em /relatorios/.
O DOCX é montado com a biblioteca padrão (zipfile e XML do WordprocessingML), sem python-docx.
O LaTeX é o template desta pasta (relatorio_padrao.tex, main.tex do projeto do relatório) preenchido: o servidor troca
os campos do bloco "DADOS DO RELATÓRIO" e o trecho entre INÍCIO e FIM DO CONTEÚDO, e não toca em pacotes, capa nem
referências. Cada [Fn] do texto vira \\cite{chave} e cada fonte, uma entrada do referencias.bib, montado a partir do
modelo desta pasta. O .zip sai com main.tex, referencias.bib e imagens/zip_logo.png, pronto para compilar.
"""
import os
import re
import secrets
import unicodedata
import zipfile
from datetime import datetime
from xml.sax.saxutils import escape

from mcp.server.mcpserver import MCPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # raiz do repositório


PASTA = os.path.join(RAIZ, ".runtime", "relatorios")
URL_BASE = "/relatorios"  # o LibreChat serve .runtime/relatorios nesse caminho (iniciar.sh)


def publicar(caminho: str) -> str:
    """Link para baixar um arquivo gravado. Aqui o LibreChat serve a pasta; no AgentCore o arquivo vai para o S3."""
    return f"{URL_BASE}/{os.path.basename(caminho)}"

INSTRUCOES = """Use gerar_relatorio quando o usuário pedir relatório, memorando, ficha, nota para comitê ou resumo
para conselho que ele vá guardar ou enviar. Antes, levante os números com as outras ferramentas: gerar_relatorio só
formata e confere, não busca dados. Cada fonte recebe um id (F1, F2...); todo parágrafo ou item com número cita o id
entre colchetes ([F1]) e toda tabela informa as fontes. Se a ferramenta recusar, corrija o que ela apontou e chame de
novo uma vez. Depois mostre ao usuário o sumário e os links devolvidos. Cada relatório sai em Markdown, Word e LaTeX (o
.tex preenche o template padrão e o .zip traz o projeto inteiro para compilar); quando o usuário quiser o código LaTeX,
chame com mostrar_latex=true e cole codigo_latex e codigo_bib."""

mcp = MCPServer("coppezip-relatorio", instructions=INSTRUCOES)

MARCA = re.compile(r"\[(F\d+)\]")
URL = re.compile(r"https?://\S+")
# número "de verdade": com separador, percentual, múltiplo (3,9x) ou 2+ dígitos; anos (1900-2099) e datas não contam
DATA = re.compile(r"\b\d{1,2}/\d{1,2}(/\d{2,4})?\b|\b\d{1,2}/(19|20)\d\d\b")
NUMERO = re.compile(r"(?<![\w/])(\d+(?:[.,]\d+)*)(\s*%|x\b)?(?![0-9A-WYZa-wyzÀ-ÿ])")


def _slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:50] or "relatorio"


def _numeros(texto: str) -> list[str]:
    limpo = DATA.sub(" ", MARCA.sub(" ", URL.sub(" ", texto or "")))
    achados = []
    for m in NUMERO.finditer(limpo):
        n, sufixo = m.group(1), m.group(2)
        if re.fullmatch(r"(19|20)\d\d", n) and not sufixo:
            continue
        if sufixo or re.search(r"[.,]", n) or len(n) >= 2:
            achados.append(n + (sufixo or "").strip())
    return achados


def _blocos(texto: str) -> list[str]:
    """Parágrafos e itens de lista: a unidade que precisa citar a fonte dos números que contém."""
    blocos, atual = [], []
    for linha in (texto or "").splitlines():
        if not linha.strip() or re.match(r"\s*([-*+]|\d+[.)])\s+", linha):
            if atual:
                blocos.append(" ".join(atual))
            atual = [linha.strip()] if linha.strip() else []
        else:
            atual.append(linha.strip())
    if atual:
        blocos.append(" ".join(atual))
    return blocos


def _validar(titulo, sumario, secoes, lacunas, fontes) -> tuple[list[str], list[str], dict]:
    erros, avisos = [], []
    ids = {}
    for i, f in enumerate(fontes or [], 1):
        fid = str(f.get("id") or f"F{i}").strip().strip("[]")
        if not re.fullmatch(r"F\d+", fid):
            erros.append(f"fonte {i}: id '{fid}' inválido; use F1, F2...")
        if fid in ids:
            erros.append(f"fonte {fid} repetida")
        if not str(f.get("descricao") or "").strip():
            erros.append(f"fonte {fid}: falta a descrição (tabela e conta, ou documento e página, ou link)")
        ids[fid] = f
    if not ids:
        erros.append("o relatório não tem fontes")
    citadas = set()

    def texto(onde, t):
        for b in _blocos(t):
            marcas = MARCA.findall(b)
            citadas.update(marcas)
            for m in marcas:
                if m not in ids:
                    erros.append(f"{onde}: cita [{m}], que não está na lista de fontes")
            nums = _numeros(b)
            if nums and not marcas:
                erros.append(f"{onde}: o trecho \"{b[:90]}\" tem número ({', '.join(nums[:3])}) sem fonte [Fn]")

    def secao(nome, s):
        texto(nome, s.get("texto"))
        for j, tab in enumerate(s.get("tabelas") or [], 1):
            onde = f"{nome}, tabela {j}"
            colunas, linhas = tab.get("colunas") or [], tab.get("linhas") or []
            if not colunas:
                erros.append(f"{onde}: tabela sem colunas")
            for k, lin in enumerate(linhas, 1):
                if len(lin) != len(colunas):
                    erros.append(f"{onde}, linha {k}: {len(lin)} células para {len(colunas)} colunas")
            tab_fontes = [str(x).strip("[] ") for x in tab.get("fontes") or []]
            celulas = " ".join(str(c) for lin in linhas for c in lin)
            citadas.update(tab_fontes)
            citadas.update(MARCA.findall(celulas))
            for m in tab_fontes + MARCA.findall(celulas):
                if m not in ids:
                    erros.append(f"{onde}: cita {m}, que não está na lista de fontes")
            col_fonte = next((k for k, c in enumerate(colunas) if str(c).strip().lower().startswith("fonte")), None)
            if not tab_fontes and _numeros(celulas):
                if col_fonte is None:
                    erros.append(f"{onde}: tem números e nenhuma fonte; informe 'fontes' ou uma coluna 'Fonte'")
                else:
                    for k, lin in enumerate(linhas, 1):
                        if _numeros(" ".join(str(c) for c in lin)) and not MARCA.search(str(lin[col_fonte])):
                            erros.append(f"{onde}, linha {k}: coluna Fonte sem [Fn]")
            if not re.search(r"(19|20)\d\d|[1-4]T\d\d|12 meses|LTM", f"{tab.get('titulo', '')} {colunas} {celulas}"):
                avisos.append(f"{onde}: não achei o período (ano ou trimestre) no título, colunas ou células")
        for j, sub in enumerate(s.get("subsecoes") or [], 1):
            secao(f"{nome}, subseção {j} ({sub.get('titulo') or 'sem título'})", sub)

    if not str(titulo or "").strip():
        erros.append("falta o título")
    texto("sumário", sumario)
    for i, s in enumerate(secoes or [], 1):
        secao(f"seção {i} ({s.get('titulo') or 'sem título'})", s)
    for k, l in enumerate(lacunas or [], 1):
        texto(f"lacuna {k}", l)
    nao_citadas = [f for f in ids if f not in citadas]
    if nao_citadas:
        avisos.append(f"fontes listadas e não citadas: {', '.join(nao_citadas)}")
    return erros, avisos, ids


def _conferidos(secoes) -> int:
    """Quantos números do texto passaram pela conferência de fonte, contando os das subseções."""
    return sum(sum(len(_numeros(b)) for b in _blocos(s.get("texto") or "")) + _conferidos(s.get("subsecoes") or [])
               for s in secoes)


# ------------------------------------------------------------------------------------------------ Markdown
def _celula(c) -> str:
    return str(c if c is not None else "").replace("|", "\\|").replace("\n", " ")


def _secao_md(s, nivel: str) -> list[str]:
    out = [f"{nivel} {s.get('titulo') or 'Seção'}", ""]
    if s.get("texto"):
        out += [s["texto"].strip(), ""]
    for tab in s.get("tabelas") or []:
        if tab.get("titulo"):
            out += [f"**{tab['titulo']}**", ""]
        cols = tab.get("colunas") or []
        out += ["| " + " | ".join(_celula(c) for c in cols) + " |", "|" + "---|" * len(cols)]
        out += ["| " + " | ".join(_celula(c) for c in lin) + " |" for lin in tab.get("linhas") or []]
        if tab.get("fontes"):
            out += ["", "Fonte: " + ", ".join(f"[{str(f).strip('[] ')}]" for f in tab["fontes"])]
        out += [""]
    for sub in s.get("subsecoes") or []:
        out += _secao_md(sub, nivel + "#")
    return out


def _markdown(titulo, sumario, secoes, lacunas, fontes, quando) -> str:
    out = [f"# {titulo}", "", f"_CoppeZIP, {quando:%d/%m/%Y %H:%M}. Cada número cita a fonte entre colchetes; a lista "
                               "está no fim._", ""]
    if sumario:
        out += ["## Sumário executivo", "", sumario.strip(), ""]
    for s in secoes:
        out += _secao_md(s, "##")
    if lacunas:
        out += ["## Lacunas e ressalvas", ""] + [f"- {l.strip()}" for l in lacunas] + [""]
    out += ["## Fontes", ""]
    for fid, f in fontes.items():
        extra = "".join(f", {k} {f[k]}" for k in ("pagina",) if f.get(k))
        link = f" <{f['url']}>" if f.get("url") else ""
        out.append(f"- [{fid}] {f['descricao'].strip()}{extra}{link}")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------------------------------------ DOCX
def _runs(texto: str) -> str:
    """Texto com **negrito** em runs do WordprocessingML."""
    partes = re.split(r"(\*\*[^*]+\*\*)", texto)
    xml = []
    for p in partes:
        if not p:
            continue
        negrito = p.startswith("**") and p.endswith("**")
        t = escape(p[2:-2] if negrito else p)
        xml.append(f'<w:r>{"<w:rPr><w:b/></w:rPr>" if negrito else ""}<w:t xml:space="preserve">{t}</w:t></w:r>')
    return "".join(xml)


def _par(texto: str, estilo: str | None = None) -> str:
    ppr = f'<w:pPr><w:pStyle w:val="{estilo}"/></w:pPr>' if estilo else ""
    return f"<w:p>{ppr}{_runs(texto)}</w:p>"


def _texto_docx(texto: str) -> list[str]:
    out = []
    for b in _blocos(texto):
        item = re.match(r"([-*+]|\d+[.)])\s+(.*)", b)
        out.append(_par("• " + item.group(2), "Lista") if item else _par(b))
    return out


SOMBRA = '<w:shd w:val="clear" w:color="auto" w:fill="E8EEF4"/>'


def _tabela_docx(tab) -> list[str]:
    cols = tab.get("colunas") or []
    borda = '<w:tblBorders>' + "".join(
        f'<w:{l} w:val="single" w:sz="4" w:space="0" w:color="999999"/>'
        for l in ("top", "left", "bottom", "right", "insideH", "insideV")) + "</w:tblBorders>"
    linhas = []
    for i, lin in enumerate([cols] + list(tab.get("linhas") or [])):
        sombra = SOMBRA if i == 0 else ""
        cel = "".join(f'<w:tc><w:tcPr><w:tcW w:w="0" w:type="auto"/>{sombra}</w:tcPr>'
                      f"{_par(('**' + str(c) + '**') if i == 0 and str(c) else str(c if c is not None else ''))}</w:tc>"
                      for c in lin)
        linhas.append(f"<w:tr>{cel}</w:tr>")
    out = [_par(tab["titulo"], "Legenda")] if tab.get("titulo") else []
    out.append(f'<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/>{borda}</w:tblPr>{"".join(linhas)}</w:tbl>')
    if tab.get("fontes"):
        out.append(_par("Fonte: " + ", ".join(f"[{str(f).strip('[] ')}]" for f in tab["fontes"]), "Legenda"))
    return out


ESTILOS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="21"/>
<w:lang w:val="pt-BR"/></w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="100"/></w:pPr></w:pPrDefault>
</w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Titulo"><w:name w:val="Title"/><w:basedOn w:val="Normal"/>
<w:pPr><w:spacing w:after="200"/></w:pPr><w:rPr><w:b/><w:color w:val="1F3864"/><w:sz w:val="36"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Titulo1"><w:name w:val="heading 1"/><w:basedOn w:val="Normal"/>
<w:pPr><w:keepNext/><w:spacing w:before="240" w:after="80"/><w:outlineLvl w:val="0"/></w:pPr>
<w:rPr><w:b/><w:color w:val="1F3864"/><w:sz w:val="26"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Titulo2"><w:name w:val="heading 2"/><w:basedOn w:val="Normal"/>
<w:pPr><w:keepNext/><w:spacing w:before="180" w:after="60"/><w:outlineLvl w:val="1"/></w:pPr>
<w:rPr><w:b/><w:color w:val="1F3864"/><w:sz w:val="23"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Lista"><w:name w:val="List Paragraph"/><w:basedOn w:val="Normal"/>
<w:pPr><w:ind w:left="360" w:hanging="220"/></w:pPr></w:style>
<w:style w:type="paragraph" w:styleId="Legenda"><w:name w:val="caption"/><w:basedOn w:val="Normal"/>
<w:rPr><w:i/><w:color w:val="555555"/><w:sz w:val="18"/></w:rPr></w:style>
</w:styles>"""

TIPOS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml"
 ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml"
 ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
 Target="word/document.xml"/></Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles"
 Target="styles.xml"/></Relationships>"""


def _secao_docx(s, estilo: str) -> list[str]:
    out = [_par(s.get("titulo") or "Seção", estilo)]
    out += _texto_docx(s.get("texto") or "")
    for tab in s.get("tabelas") or []:
        out += _tabela_docx(tab)
    for sub in s.get("subsecoes") or []:
        out += _secao_docx(sub, "Titulo2")
    return out


def _docx(caminho, titulo, sumario, secoes, lacunas, fontes, quando):
    corpo = [_par(titulo, "Titulo"),
             _par(f"CoppeZIP, {quando:%d/%m/%Y %H:%M}. Cada número cita a fonte entre colchetes; a lista está no fim.",
                  "Legenda")]
    if sumario:
        corpo += [_par("Sumário executivo", "Titulo1")] + _texto_docx(sumario)
    for s in secoes:
        corpo += _secao_docx(s, "Titulo1")
    if lacunas:
        corpo += [_par("Lacunas e ressalvas", "Titulo1")] + [_par("• " + l.strip(), "Lista") for l in lacunas]
    corpo.append(_par("Fontes", "Titulo1"))
    for fid, f in fontes.items():
        extra = f", pagina {f['pagina']}" if f.get("pagina") else ""
        corpo.append(_par(f"[{fid}] {f['descricao'].strip()}{extra}" + (f" {f['url']}" if f.get("url") else ""),
                          "Lista"))
    documento = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
                 + "".join(corpo) +
                 '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
                 '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="0" w:footer="0" w:gutter="0"/>'
                 "</w:sectPr></w:body></w:document>")
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", TIPOS)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/_rels/document.xml.rels", DOC_RELS)
        z.writestr("word/styles.xml", ESTILOS)
        z.writestr("word/document.xml", documento)


# ------------------------------------------------------------------------------------------------ LaTeX
PROJETO = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(PROJETO, "relatorio_padrao.tex")  # main.tex do template: preâmbulo, capa e referências
MODELO_BIB = os.path.join(PROJETO, "referencias.bib")     # base do .bib: as instruções e a entrada da base interna
LOGO = os.path.join(PROJETO, "imagens", "zip_logo.png")   # logo da capa e do cabeçalho
ABRE, FECHA = "INÍCIO DO CONTEÚDO", "FIM DO CONTEÚDO"     # o trecho entre os dois é o que o template deixa escrever
CAMPO = re.compile(r"(\\newcommand\{\\(titulorelatorio|subtitulorelatorio|periodoanalise|datarelatorio)\}\{)"
                   r"(.*)(\})\s*$")
SUBTITULO = "Inteligência competitiva do setor elétrico"
CABECALHO = ("% Relatório gerado pelo CoppeZIP no template padrão: preâmbulo, capa e referências são do template; o\n"
             "% conteúdo entre INÍCIO e FIM DO CONTEÚDO é o do relatório, com a fonte de cada número em \\cite.\n"
             "% Para compilar: pdflatex main, bibtex main, pdflatex main (o .zip traz referencias.bib e imagens/).\n")
ENTRADA_BIB = re.compile(r"^@\w+\{.*?^\}", re.MULTILINE | re.DOTALL)  # entradas do modelo (os exemplos são comentários)
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro")
ANO = re.compile(r"\b((?:19|20)\d\d)\b")
ESCAPE = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
          "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
RICO = re.compile(r"(\*\*[^*]+\*\*|\[F\d+\](?:[ ,;]*\[F\d+\])*|https?://\S+)")  # marcas seguidas viram um só \cite
LARGURA_LINHA = 88  # caracteres que a linha da tabela aguenta em \small; acima disso as colunas ganham largura fixa
COLUNA_MINIMA, COLUNA_MAXIMA = 6, 30  # largura da coluna em caracteres do maior texto, o que divide a linha entre elas
TABCOLSEP = 0.027  # espaço entre colunas (2\tabcolsep) em fração de \textwidth: o resto é dividido entre as colunas


def _template() -> list[str]:
    """Linhas do template do relatório, conferindo nele o que o preenchimento precisa achar."""
    with open(TEMPLATE, encoding="utf-8") as f:
        linhas = f.read().splitlines(keepends=True)
    campos = {m.group(2) for m in (CAMPO.match(l) for l in linhas) if m}
    faltando = [m for m in (ABRE, FECHA, r"\bibliography{referencias}") if not any(m in l for l in linhas)]
    faltando += [f"\\{c}" for c in ("titulorelatorio", "subtitulorelatorio", "periodoanalise", "datarelatorio")
                 if c not in campos]
    if faltando:
        raise RuntimeError(f"{TEMPLATE} não tem {', '.join(faltando)}")
    return linhas


def _preencher(linhas: list[str], campos: dict, corpo: str) -> str:
    """Preenche o template onde ele manda: os campos do bloco DADOS DO RELATÓRIO e o trecho entre INÍCIO e FIM DO
    CONTEÚDO. Pacotes, capa, comandos de formatação e referências saem como estão no arquivo; as instruções de
    preenchimento, que são para quem escreve, não vão para o relatório pronto."""
    documento = next(k for k, l in enumerate(linhas) if l.startswith(r"\documentclass"))
    # os marcadores são procurados depois do \documentclass: as instruções do template também os citam
    inicio = next(k for k, l in enumerate(linhas) if k > documento and ABRE in l) + 2  # marcador e moldura de comentário
    fim = next(k for k, l in enumerate(linhas) if k > documento and FECHA in l) - 1
    cabeca = [CABECALHO]
    for linha in linhas[documento:inicio]:
        m = CAMPO.match(linha)
        cabeca.append(f"{m.group(1)}{campos[m.group(2)]}{m.group(4)}\n" if m else linha)
    return "".join(cabeca) + "\n" + corpo + "\n\n" + "".join(linhas[fim:])


def _chaves(fontes: dict) -> dict:
    """Chave de cada fonte no referencias.bib, no padrão do template: minúsculas, sem acento, com o ano."""
    chaves, usadas = {}, set()
    for fid, f in fontes.items():
        palavras = [p for p in _slug(str(f.get("descricao") or fid)).split("-") if p][:4]
        ano = str(f.get("ano") or "") or next(iter(ANO.findall(str(f.get("descricao") or ""))[-1:]), "")
        chave = "_".join(palavras) or "fonte"
        if ano and ano not in palavras:
            chave += f"_{ano}"
        while chave in usadas:
            chave += "_" + fid.lower()
        usadas.add(chave)
        chaves[fid] = chave
    return chaves


def _bib(fontes: dict, chaves: dict, quando) -> str:
    """O referencias.bib do relatório: as entradas do modelo do template (a base interna) e uma por fonte citada."""
    with open(MODELO_BIB, encoding="utf-8") as f:
        out = ["% Referências do relatório gerado pelo CoppeZIP: uma entrada por fonte citada no main.tex."]
        out += ENTRADA_BIB.findall(f.read())
    for fid, f in fontes.items():
        campos = [("author", "{" + _tex(str(f["instituicao"]).strip()) + "}")] if f.get("instituicao") else []
        campos.append(("title", _tex(str(f["descricao"]).strip())))
        ano = str(f.get("ano") or "") or next(iter(ANO.findall(str(f.get("descricao") or ""))[-1:]), "")
        if ano:  # sem ano na descrição e sem ano informado a entrada sai sem o campo: não se inventa data
            campos.append(("year", ano))
        if f.get("url"):
            campos.append(("url", str(f["url"]).strip()))  # o unsrtnat já embrulha em \url{}
        pagina = f", página {f['pagina']}" if f.get("pagina") else ""
        campos.append(("note", f"Fonte {fid} do relatório{pagina}. Levantado pelo CoppeZIP em {quando:%d/%m/%Y}."))
        out.append("@misc{" + chaves[fid] + ",\n" + ",\n".join(f"  {c:<6} = {{{v}}}" for c, v in campos) + "\n}")
    return "\n\n".join(out) + "\n"


def _citar(ids: list[str], chaves: dict) -> str:
    """As fontes citadas juntas no texto viram uma citação só, como o template pede."""
    return r"\cite{" + ",".join(chaves[i] for i in ids if i in chaves) + "}"


def _tex(texto) -> str:
    """Texto comum em LaTeX: escapa o que o TeX leria como comando."""
    return "".join(ESCAPE.get(c, c) for c in str("" if texto is None else texto))


def _tex_rico(texto, chaves: dict) -> str:
    """Texto do modelo em LaTeX: **negrito**, [F1] como \\cite da entrada do .bib e endereço clicável."""
    saida = []
    for p in RICO.split(str("" if texto is None else texto)):
        if not p:
            continue
        if p.startswith("**") and p.endswith("**"):
            saida.append(r"\textbf{" + _tex(p[2:-2]) + "}")
        elif p.startswith("[F"):
            saida.append(_citar(MARCA.findall(p), chaves))
        elif p.startswith("http"):
            fim = ""
            while p and p[-1] in ".,;:)]":
                p, fim = p[:-1], p[-1] + fim
            saida.append(r"\url{" + p + "}" + _tex(fim))
        else:
            saida.append(_tex(p))
    return "".join(saida)


def _itens_latex(itens: list[str], ambiente: str = "itemize") -> str:
    """Lista LaTeX: itemize quando o modelo usou marcador, enumerate quando ele numerou."""
    return (f"\\begin{{{ambiente}}}[itemsep=2pt,topsep=2pt]\n" + "\n".join(r"  \item " + i for i in itens)
            + f"\n\\end{{{ambiente}}}")


def _texto_latex(texto: str, chaves: dict) -> list[str]:
    """Os mesmos parágrafos e itens de lista do Word, agora como blocos LaTeX."""
    blocos, itens, ambiente = [], [], "itemize"

    def fechar():
        if itens:
            blocos.append(_itens_latex(itens, ambiente))
            itens.clear()

    for b in _blocos(texto):
        item = re.match(r"([-*+]|\d+[.)])\s+(.*)", b)
        if item:
            atual = "itemize" if item.group(1) in "-*+" else "enumerate"
            if atual != ambiente:
                fechar()
                ambiente = atual
            itens.append(_tex_rico(item.group(2), chaves))
            continue
        fechar()
        blocos.append(_tex_rico(b, chaves))
    fechar()
    return blocos


def _tabela_latex(tab, chaves: dict, n: int) -> str:
    """Tabela no modelo do template: table[H] com booktabs, título em \\caption e a fonte em \\fonte{\\cite{...}}."""
    colunas, linhas = tab.get("colunas") or [], tab.get("linhas") or []
    larguras, numericas = [], []
    for k, col in enumerate(colunas):
        celulas = [str(lin[k]) for lin in linhas if k < len(lin)]
        larguras.append(max([len(str(col))] + [len(c) for c in celulas]))
        numericas.append(k > 0 and bool(celulas) and sum(1 for c in celulas if _numeros(c)) * 2 >= len(celulas))
    if sum(larguras) <= LARGURA_LINHA:  # cabe na linha: o LaTeX mede cada coluna e os números vão para a direita
        formato = "".join("r" if num else "l" for num in numericas)
    else:  # não cabe: divide a linha entre as colunas, proporcional ao conteúdo, e o texto quebra dentro da célula
        pesos = [min(max(l, COLUNA_MINIMA), COLUNA_MAXIMA) for l in larguras]
        sobra = 1 - TABCOLSEP * len(colunas)
        formato = "".join(f"p{{{round(p / sum(pesos) * sobra, 3)}\\textwidth}}" for p in pesos)
    titulo = str(tab.get("titulo") or "Tabela")
    out = [r"\begin{table}[H]", r"  \centering",
           r"  \caption{" + _tex_rico(titulo, chaves) + r"}\label{tab:" + f"{n}-{_slug(titulo)}" + "}",
           r"  \small",
           r"  \begin{tabular}{" + formato + "}", r"  \toprule",
           "  " + " & ".join(r"\textbf{" + _tex_rico(c, chaves) + "}" for c in colunas) + r" \\", r"  \midrule"]
    out += ["  " + " & ".join(_tex_rico(c, chaves) for c in lin) + r" \\" for lin in linhas]
    out += [r"  \bottomrule", r"  \end{tabular}"]
    if tab.get("fontes"):
        out.append(r"  \fonte{" + _citar([str(f).strip("[] ") for f in tab["fontes"]], chaves) + "}")
    out.append(r"\end{table}")
    return "\n".join(out)


def _secao_latex(s, chaves: dict, nivel: str, conta: dict) -> list[str]:
    """Seção do relatório: título, texto, tabelas e as subseções, um nível abaixo."""
    titulo = str(s.get("titulo") or "Seção").strip()
    conta[nivel] = conta.get(nivel, 0) + 1
    out = [f"\\{nivel}{{{_tex_rico(titulo, chaves)}}}" + r"\label{sec:" + f"{conta[nivel]}-{_slug(titulo)}" + "}"]
    out += _texto_latex(s.get("texto") or "", chaves)
    for tab in s.get("tabelas") or []:
        conta["tabela"] = conta.get("tabela", 0) + 1
        out.append(_tabela_latex(tab, chaves, conta["tabela"]))
    for sub in s.get("subsecoes") or []:
        out += _secao_latex(sub, chaves, "subsection", conta)
    return out


def _periodo(sumario, secoes, quando) -> str:
    """Período analisado para a capa: do primeiro ao último ano que aparecem no relatório. Ano no futuro é meta ou
    prazo de recomendação, não período analisado: fica de fora (a menos que só haja anos futuros)."""
    def textos(s):
        yield f"{s.get('titulo') or ''} {s.get('texto') or ''}"
        for tab in s.get("tabelas") or []:
            yield str(tab.get("titulo") or "")
            yield " ".join(str(c) for c in (tab.get("colunas") or []))
            yield " ".join(str(c) for lin in tab.get("linhas") or [] for c in lin)
        for sub in s.get("subsecoes") or []:
            yield from textos(sub)

    anos = sorted({a for t in [str(sumario or "")] + [t for s in secoes for t in textos(s)] for a in ANO.findall(t)})
    anos = [a for a in anos if int(a) <= quando.year] or anos
    if not anos:
        return "não informado"
    return anos[0] if len(anos) == 1 else f"{anos[0]} a {anos[-1]}"


def _latex(titulo, subtitulo, periodo, sumario, secoes, lacunas, fontes, quando) -> tuple[str, str]:
    """O main.tex preenchido e o referencias.bib com as fontes citadas."""
    chaves, conta = _chaves(fontes), {}
    corpo = _secao_latex({"titulo": "Sumário Executivo", "texto": sumario}, chaves, "section", conta) if sumario else []
    for s in secoes:
        corpo += _secao_latex(s, chaves, "section", conta)
    if lacunas:  # ressalvas não abrem seção: o template fixa as seis do relatório
        corpo += [r"\subsection{Lacunas e ressalvas}\label{sec:lacunas}",
                  _itens_latex([_tex_rico(l.strip(), chaves) for l in lacunas])]
    campos = {"titulorelatorio": _tex(titulo.strip()),
              "subtitulorelatorio": _tex(subtitulo.strip() or SUBTITULO),
              "periodoanalise": _tex(periodo.strip() or _periodo(sumario, secoes, quando)),
              "datarelatorio": f"{quando.day} de {MESES[quando.month - 1]} de {quando.year}"}
    return _preencher(_template(), campos, "\n\n".join(corpo)), _bib(fontes, chaves, quando)


def _projeto(caminho: str, tex: str, bib: str):
    """O projeto do relatório pronto para compilar: main.tex, referencias.bib e o logo da capa."""
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("main.tex", tex)
        z.writestr("referencias.bib", bib)
        z.write(LOGO, "imagens/zip_logo.png")


@mcp.tool()
def gerar_relatorio(titulo: str, secoes: list[dict], fontes: list[dict], sumario: str = "",
                    lacunas: list[str] | None = None, subtitulo: str = "", periodo: str = "",
                    mostrar_latex: bool = False) -> dict:
    """Grava o relatório final (Markdown, DOCX, LaTeX e o .zip do projeto LaTeX) e devolve os links para baixar. Não
    busca dados: use depois de levantar os números com as outras ferramentas.

    fontes: [{"id": "F1", "descricao": "CVM DFP 2025, conta 3.01, via kpis_financeiros", "pagina": 22, "url": "...",
              "instituicao": "Comissão de Valores Mobiliários", "ano": "2025"}]
      (pagina, url, instituicao e ano opcionais; descricao diz a tabela e conta, ou o documento). Cada fonte vira uma
      entrada do referencias.bib e cada [Fn] do texto, a citação dela.
    secoes: [{"titulo": "Resultados", "texto": "Markdown; todo parágrafo ou item com número cita [F1]",
              "tabelas": [{"titulo": "Indicadores 2025, R$ bi", "colunas": ["Empresa", "Receita"],
                           "linhas": [["Taesa", "4,62"]], "fontes": ["F1"]}],
              "subsecoes": [{"titulo": "Pontos fortes e fracos", "texto": "...", "tabelas": []}]}]
      O template fixa as seis seções do relatório, nesta ordem: Sumário Executivo (mande em sumario), Introdução,
      Dados e Metodologia, Resultados, Discussão e Pontos de Atenção, Conclusões e Recomendações. Tema dentro de uma
      delas é subseção.
    sumario: 3 a 5 frases com a resposta; lacunas: o que não foi encontrado ou não é comparável.
    subtitulo e periodo: o tema e o intervalo analisado, que vão para a capa (sem periodo, entram os anos do relatório).
    mostrar_latex: devolve também o código integral em codigo_latex (main.tex) e codigo_bib (referencias.bib), para
      colar na resposta. O preâmbulo, a capa e as referências vêm do relatorio_padrao.tex e não se escrevem aqui.
    Recusa (sem gravar) se algum trecho com número não citar fonte, se uma tabela com números não tiver fonte ou se
    uma citação não existir na lista de fontes.
    """
    lacunas = [l for l in (lacunas or []) if str(l).strip()]
    secoes = secoes or []
    erros, avisos, ids = _validar(titulo, sumario, secoes, lacunas, fontes)
    if erros:
        return {"gravado": False, "erros": erros[:30],
                "como_corrigir": "acrescente [Fn] aos trechos apontados (ou retire o número) e chame de novo"}
    quando = datetime.now()
    os.makedirs(PASTA, exist_ok=True)
    nome = f"{quando:%Y%m%d-%H%M%S}-{_slug(titulo)}-{secrets.token_hex(4)}"
    md = _markdown(titulo, sumario, secoes, lacunas, ids, quando)
    with open(os.path.join(PASTA, nome + ".md"), "w", encoding="utf-8") as f:
        f.write(md)
    _docx(os.path.join(PASTA, nome + ".docx"), titulo, sumario, secoes, lacunas, ids, quando)
    tex, bib = _latex(titulo, subtitulo, periodo, sumario, secoes, lacunas, ids, quando)
    with open(os.path.join(PASTA, nome + ".tex"), "w", encoding="utf-8") as f:
        f.write(tex)
    _projeto(os.path.join(PASTA, nome + ".zip"), tex, bib)
    return {"gravado": True,
            "arquivos": {"markdown": publicar(os.path.join(PASTA, nome + ".md")),
                         "docx": publicar(os.path.join(PASTA, nome + ".docx")),
                         "latex": publicar(os.path.join(PASTA, nome + ".tex")),
                         "projeto_latex": publicar(os.path.join(PASTA, nome + ".zip"))},
            "numeros_conferidos": sum(len(_numeros(b)) for b in _blocos(sumario)) + _conferidos(secoes),
            "fontes": len(ids), **({"avisos": avisos} if avisos else {}),
            **({"codigo_latex": tex, "codigo_bib": bib} if mostrar_latex else {}),
            "proximo_passo": "mostre ao usuário o sumário e os links (Markdown, Word, LaTeX e o .zip com o projeto "
                             "para compilar)" + ("; cole codigo_latex e codigo_bib em blocos de código"
                                                 if mostrar_latex else "")}


if __name__ == "__main__":
    mcp.run()

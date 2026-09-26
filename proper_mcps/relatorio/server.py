"""Servidor MCP "energynexus-relatorio": grava o relatório final da análise em Markdown e DOCX, com fonte em todo número.

Ferramenta: gerar_relatorio. Recebe título, sumário, seções (texto e tabelas), lacunas e a lista de fontes, e recusa o
relatório se algum trecho com número não citar uma fonte ([F1], [F2]...), se uma tabela com números não tiver fonte ou
se um texto vier cortado no meio. A conferência é de citação, não de valor: o servidor garante que cada número aponta
para uma fonte declarada, e não que o número bate com ela — quem levantou o dado nas outras ferramentas responde pelo
valor. Nome de tabela citado numa fonte é conferido contra o catálogo da base, e sai como aviso quando não existe.
Os arquivos vão para .runtime/relatorios, que o iniciar.sh liga em client/public/assets/relatorios do LibreChat; o
navegador os baixa em /relatorios/.
O DOCX é montado com a biblioteca padrão (zipfile e XML do WordprocessingML), sem python-docx.
"""
import os
import re
import secrets
import unicodedata
import zipfile
from datetime import datetime
from xml.sax.saxutils import escape

import duckdb
from mcp.server.mcpserver import MCPServer

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # raiz do repositório


PASTA = os.path.join(RAIZ, ".runtime", "relatorios")
URL_BASE = "/relatorios"  # o LibreChat serve .runtime/relatorios nesse caminho (iniciar.sh)
CATALOGO_DB = os.path.join(RAIZ, "data", "energynexus.duckdb")  # só para conferir os nomes de tabela citados nas fontes


def publicar(caminho: str) -> str:
    """Link para baixar um arquivo gravado. Aqui o LibreChat serve a pasta; no AgentCore o arquivo vai para o S3."""
    return f"{URL_BASE}/{os.path.basename(caminho)}"

INSTRUCOES = """Use gerar_relatorio quando o usuário pedir relatório, memorando, ficha, nota para comitê ou resumo
para conselho que ele vá guardar ou enviar. Antes, levante os números com as outras ferramentas: gerar_relatorio só
formata e confere, não busca dados. Cada fonte recebe um id (F1, F2...); todo parágrafo ou item com número cita o id
entre colchetes ([F1]) e toda tabela informa as fontes. Se a ferramenta recusar, corrija o que ela apontou e chame de
novo uma vez. Depois mostre ao usuário o sumário e os links devolvidos."""

mcp = MCPServer("energynexus-relatorio", instructions=INSTRUCOES)

MARCA = re.compile(r"\[(F\d+)\]")
URL = re.compile(r"https?://\S+")
# número "de verdade": com separador, percentual, múltiplo (3,9x) ou 2+ dígitos; anos (1900-2099) e datas não contam
DATA = re.compile(r"\b\d{1,2}/\d{1,2}(/\d{2,4})?\b|\b\d{1,2}/(19|20)\d\d\b")
NUMERO = re.compile(r"(?<![\w/])(\d+(?:[.,]\d+)*)(\s*%|x\b)?(?![0-9A-WYZa-wyzÀ-ÿ])")


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


def _contar_numeros(sumario, secoes, lacunas) -> dict:
    """Quantos números o relatório traz e onde estão. Antes só o texto entrava na conta: um relatório com todos os
    números em tabelas devolvia zero."""
    no_texto = sum(len(_numeros(b)) for b in _blocos(sumario))
    no_texto += sum(len(_numeros(b)) for s in secoes for b in _blocos(s.get("texto") or ""))
    em_tabelas = sum(len(_numeros(" ".join(str(c) for lin in (t.get("linhas") or []) for c in lin)))
                     for s in secoes for t in (s.get("tabelas") or []))
    em_lacunas = sum(len(_numeros(b)) for l in (lacunas or []) for b in _blocos(l))
    return {"total": no_texto + em_tabelas + em_lacunas, "no_texto": no_texto, "em_tabelas": em_tabelas,
            "em_lacunas": em_lacunas}


CORTE = re.compile(r"(\.\.\.|…|\[\.\.\.\]|\[truncad|\[cortad)", re.I)
FIM = re.compile(r"[.!?:;)\]\"'»”]\s*$")  # trecho inteiro acaba em pontuação, no fecho da citação ([F1]) ou em ')'
LOCALIZADOR = re.compile(r"\w+_\w+|conta\s+\d|p\.\s*\d|p[áa]gina\s*\d|https?://")
ARQUIVO = re.compile(r"\S+\.(pdf|docx?|xlsx?|csv|parquet|zip)\b", re.I)
NOME_TABELA = re.compile(r"\bvia\s+([A-Za-z]\w*)|\b([A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+)\b")


def _tabelas_citadas(descricao: str) -> list[str]:
    """Nomes que a descrição da fonte apresenta como tabela da base: depois de "via" ou em snake_case. Link e nome de
    arquivo saem antes, senão "cemig_relatorio_2025.pdf" entraria na conferência."""
    limpo = ARQUIVO.sub(" ", URL.sub(" ", descricao or ""))
    return list(dict.fromkeys(a or b for a, b in NOME_TABELA.findall(limpo)))


def _catalogo() -> set[str] | None:
    """Tabelas da base, em minúsculas, ou None quando o banco não está ao lado do servidor — é o caso do runtime do
    AgentCore, que sobe só o relatório, e aí a conferência dos nomes fica registrada como aviso."""
    if not os.path.exists(CATALOGO_DB):
        return None
    con = duckdb.connect(CATALOGO_DB, read_only=True)
    try:
        return {t.lower() for (t,) in con.execute("SELECT tabela FROM catalogo").fetchall()}
    finally:
        con.close()


def _cortado(texto: str) -> str:
    """Por que o texto parece ter sido colado pela metade (vazio quando parece inteiro): marca de corte no fim ou fim
    sem pontuação. Dois relatórios da auditoria foram gravados cortados no meio da frase, então isto é erro."""
    t = (texto or "").strip()
    if not t:
        return ""
    if CORTE.search(t[-40:]):
        return "o texto tem marca de corte ('...')"
    if not FIM.search(t):
        return "o texto termina sem pontuação e parece truncado"
    return ""


def _validar(titulo, sumario, secoes, lacunas, fontes) -> tuple[list[str], list[str], dict]:
    erros, avisos = [], []
    ids = {}
    for i, f in enumerate(fontes or [], 1):
        fid = str(f.get("id") or f"F{i}").strip().strip("[]")
        if not re.fullmatch(r"F\d+", fid):
            erros.append(f"fonte {i}: id '{fid}' inválido; use F1, F2...")
        if fid in ids:
            erros.append(f"fonte {fid} repetida")
        descricao = str(f.get("descricao") or "").strip()
        if not descricao:
            erros.append(f"fonte {fid}: falta a descrição (tabela e conta, ou documento e página, ou link)")
        elif not (f.get("pagina") or f.get("url") or LOCALIZADOR.search(descricao)):
            avisos.append(f"fonte {fid}: a descrição não diz onde achar o número (tabela da base, conta da CVM, "
                          f"página do documento ou link): \"{descricao[:60]}\"")
        ids[fid] = f
    if not ids:
        erros.append("o relatório não tem fontes")
    # a auditoria passou "tabela_que_nao_existe, conta 9.99" e o relatório saiu com cara de auditado: confere o nome da
    # tabela contra o catálogo da base (aviso, não erro, porque fonte de documento e de link não têm tabela)
    citados = {fid: _tabelas_citadas(str(f.get("descricao") or "")) for fid, f in ids.items()}
    if any(citados.values()):
        try:
            catalogo = _catalogo()
            impedimento = f"o banco {os.path.basename(CATALOGO_DB)} não está ao lado do servidor"
        except duckdb.Error as e:  # banco em uso por quem o reconstrói, ou de outra versão
            catalogo, impedimento = None, f"o catálogo não abriu ({e})"
        if catalogo is None:
            avisos.append(f"não confiro os nomes de tabela citados nas fontes: {impedimento}")
        else:
            for fid, nomes in citados.items():
                for n in nomes:
                    if n.lower() not in catalogo:
                        avisos.append(f"fonte {fid}: '{n}' não é uma tabela da base (confira em listar_tabelas); se o "
                                      "número vem de documento ou link, descreva o documento e a página")
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

    if not str(titulo or "").strip():
        erros.append("falta o título")
    texto("sumário", sumario)
    if motivo := _cortado(sumario):
        erros.append(f"sumário: {motivo} (\"...{str(sumario).strip()[-40:]}\"); reenvie o trecho inteiro")
    for i, s in enumerate(secoes or [], 1):
        nome = f"seção {i} ({s.get('titulo') or 'sem título'})"
        texto(nome, s.get("texto"))
        if motivo := _cortado(s.get("texto")):
            erros.append(f"{nome}: {motivo} (\"...{str(s.get('texto')).strip()[-40:]}\"); reenvie o trecho inteiro")
        for j, tab in enumerate(s.get("tabelas") or [], 1):
            onde = f"{nome}, tabela {j}"
            colunas, linhas = tab.get("colunas") or [], tab.get("linhas") or []
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
    for k, l in enumerate(lacunas or [], 1):
        texto(f"lacuna {k}", l)
    if not lacunas:
        avisos.append("o relatório não tem lacunas: diga o que não está na base, o que não é comparável ou o que "
                      "precisa de outra fonte (ou repita que não há lacuna a registrar)")
    nao_citadas = [f for f in ids if f not in citadas]
    if nao_citadas:
        avisos.append(f"fontes listadas e não citadas: {', '.join(nao_citadas)}")
    return erros, avisos, ids


# ------------------------------------------------------------------------------------------------ Markdown
def _celula(c) -> str:
    return str(c if c is not None else "").replace("|", "\\|").replace("\n", " ")


def _markdown(titulo, sumario, secoes, lacunas, fontes, quando) -> str:
    out = [f"# {titulo}", "", f"_EnergyNexus, {quando:%d/%m/%Y %H:%M}. Cada número cita a fonte entre colchetes; a lista "
                               "está no fim._", ""]
    if sumario:
        out += ["## Sumário executivo", "", sumario.strip(), ""]
    for s in secoes:
        out += [f"## {s.get('titulo') or 'Seção'}", ""]
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


def _docx(caminho, titulo, sumario, secoes, lacunas, fontes, quando):
    corpo = [_par(titulo, "Titulo"),
             _par(f"EnergyNexus, {quando:%d/%m/%Y %H:%M}. Cada número cita a fonte entre colchetes; a lista está no fim.",
                  "Legenda")]
    if sumario:
        corpo += [_par("Sumário executivo", "Titulo1")] + _texto_docx(sumario)
    for s in secoes:
        corpo.append(_par(s.get("titulo") or "Seção", "Titulo1"))
        corpo += _texto_docx(s.get("texto") or "")
        for tab in s.get("tabelas") or []:
            corpo += _tabela_docx(tab)
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


def _slug(texto: str) -> str:
    t = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")[:50] or "relatorio"


@mcp.tool()
def gerar_relatorio(titulo: str, secoes: list[dict], fontes: list[dict], sumario: str = "",
                    lacunas: list[str] | None = None) -> dict:
    """Grava o relatório final (Markdown e DOCX) e devolve os links para baixar. Não busca dados: use depois de
    levantar os números com as outras ferramentas.

    fontes: [{"id": "F1", "descricao": "CVM DFP 2025, conta 3.01, via kpis_financeiros", "pagina": 22, "url": "..."}]
      (pagina e url opcionais; descricao diz a tabela e conta, ou o documento).
    secoes: [{"titulo": "Alavancagem", "texto": "Markdown; todo parágrafo ou item com número cita [F1]",
              "tabelas": [{"titulo": "Indicadores 2025, R$ bi", "colunas": ["Empresa", "Receita"],
                           "linhas": [["Taesa", "4,62"]], "fontes": ["F1"]}]}]
    sumario: 3 a 5 frases com a resposta; lacunas: o que não foi encontrado ou não é comparável.
    Recusa (sem gravar) se algum trecho com número não citar fonte, se uma tabela com números não tiver fonte, se uma
    citação não existir na lista de fontes ou se um texto terminar no meio. Confere a citação, não o valor: o número é
    de quem o levantou.
    Devolve numeros_com_fonte (total e quantos estão no texto, nas tabelas e nas lacunas) e avisos a resolver.
    """
    lacunas = [l for l in (lacunas or []) if str(l).strip()]
    secoes = secoes or []
    erros, avisos, ids = _validar(titulo, sumario, secoes, lacunas, fontes)
    if erros:
        return {"gravado": False, "erros": erros[:30], **({"avisos": avisos} if avisos else {}),
                "como_corrigir": "acrescente [Fn] aos trechos apontados (ou retire o número), reenvie inteiro o texto "
                                 "apontado como truncado, e chame de novo"}
    quando = datetime.now()
    os.makedirs(PASTA, exist_ok=True)
    nome = f"{quando:%Y%m%d-%H%M%S}-{_slug(titulo)}-{secrets.token_hex(4)}"
    md = _markdown(titulo, sumario, secoes, lacunas, ids, quando)
    with open(os.path.join(PASTA, nome + ".md"), "w", encoding="utf-8") as f:
        f.write(md)
    _docx(os.path.join(PASTA, nome + ".docx"), titulo, sumario, secoes, lacunas, ids, quando)
    return {"gravado": True,
            "arquivos": {"markdown": publicar(os.path.join(PASTA, nome + ".md")),
                         "docx": publicar(os.path.join(PASTA, nome + ".docx"))},
            "numeros_com_fonte": _contar_numeros(sumario, secoes, lacunas),
            "conferencia": "todo número citado aponta para uma fonte da lista; o valor em si não foi conferido contra "
                           "a fonte",
            "fontes": len(ids), **({"avisos": avisos} if avisos else {}),
            "proximo_passo": "mostre ao usuário o sumário e os dois links (Markdown e Word), e diga que a conferência "
                             "foi de citação, não de valor"}


if __name__ == "__main__":
    mcp.run()

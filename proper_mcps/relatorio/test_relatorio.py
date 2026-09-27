"""Testes de gerar_relatorio. Rodar: .runtime/venv/bin/python -m pytest proper_mcps -q"""
import importlib.util
import os
import re
import shutil
import subprocess
import zipfile
from xml.dom import minidom

import pytest

# carregado pelo caminho: proper_mcps/dados também tem um server.py
_spec = importlib.util.spec_from_file_location("relatorio_server", os.path.join(os.path.dirname(__file__), "server.py"))
server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(server)


@pytest.fixture()
def s(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "PASTA", str(tmp_path))
    return server


FONTES = [{"id": "F1", "descricao": "CVM DFP 2025, conta 3.01, via kpis_financeiros"},
          {"id": "F2", "descricao": "Relatório de Sustentabilidade Taesa 2025", "pagina": 22,
           "instituicao": "Taesa", "url": "https://ri.taesa.com.br/rs_2025.pdf"}]
CHAVE1, CHAVE2 = "cvm_dfp_2025_conta", "relatorio_de_sustentabilidade_taesa_2025"


def secao(texto="A receita da Taesa foi R$ 4,62 bi em 2025 [F1].", fontes_tab=("F1",)):
    return [{"titulo": "Receita", "texto": texto,
             "tabelas": [{"titulo": "Receita líquida 2025, R$ bi", "colunas": ["Empresa", "Receita"],
                          "linhas": [["Taesa", "4,62"]], "fontes": list(fontes_tab)}]}]


def test_grava_markdown_docx_latex_e_projeto(s, tmp_path):
    r = s.gerar_relatorio("Taesa em 2025", secao(), FONTES, sumario="Receita de R$ 4,62 bi [F1]; RAP na p. 22 [F2].",
                          lacunas=["Sem cronograma de dívida por instrumento na base."])
    assert r["gravado"], r
    arquivos = sorted(os.listdir(tmp_path))
    assert [a.rsplit(".", 1)[1] for a in arquivos] == ["docx", "md", "tex", "zip"]
    md = open(tmp_path / arquivos[1], encoding="utf-8").read()
    assert "| Taesa | 4,62 |" in md and "- [F2] Relatório de Sustentabilidade Taesa 2025, pagina 22" in md
    with zipfile.ZipFile(tmp_path / arquivos[0]) as z:
        minidom.parseString(z.read("word/document.xml"))  # XML bem formado
        assert "4,62" in z.read("word/document.xml").decode()
    tex = open(tmp_path / arquivos[2], encoding="utf-8").read()
    assert r"\section{Receita}" in tex and "4,62" in tex
    with zipfile.ZipFile(tmp_path / arquivos[3]) as z:  # o projeto para compilar, como o template descreve
        assert sorted(z.namelist()) == ["imagens/zip_logo.png", "main.tex", "referencias.bib"]
        assert z.read("main.tex").decode() == tex


def test_recusa_numero_sem_fonte(s, tmp_path):
    r = s.gerar_relatorio("X", secao("A receita foi R$ 4,62 bi em 2025."), FONTES)
    assert not r["gravado"] and "sem fonte" in r["erros"][0]
    assert os.listdir(tmp_path) == []


def test_recusa_tabela_sem_fonte_e_citacao_inexistente(s):
    r = s.gerar_relatorio("X", secao("Receita de 4,62 [F9].", fontes_tab=()), FONTES)
    assert not r["gravado"]
    assert any("F9" in e for e in r["erros"]) and any("nenhuma fonte" in e for e in r["erros"])


def test_coluna_fonte_por_linha_vale_como_fonte(s):
    sec = [{"titulo": "T", "tabelas": [{"titulo": "2025", "colunas": ["Empresa", "Valor", "Fonte"],
                                        "linhas": [["A", "1,5", "[F1]"], ["B", "2,5", "[F2]"]]}]}]
    assert s.gerar_relatorio("T", sec, FONTES)["gravado"]


def test_recusa_tabela_sem_colunas(s):
    sec = [{"titulo": "T", "tabelas": [{"titulo": "2025", "colunas": [], "linhas": []}]}]
    r = s.gerar_relatorio("T", sec, FONTES)
    assert not r["gravado"] and any("sem colunas" in e for e in r["erros"])


@pytest.mark.parametrize("texto, tem", [
    ("Em 2025 a empresa cresceu.", False),          # ano não conta
    ("Dados do 2T26 e escopo 1.", False),           # trimestre e número de um dígito
    ("Alavancagem de 3,9x.", True),
    ("Alta de 12%.", True),
    ("Lucro de R$ 616 mi.", True),
    ("Veja https://ri.taesa.com.br/2026/05/x.pdf", False),
    ("Dados preliminares até 30/09/2025 e vigência em 04/2026.", False),  # datas
])
def test_o_que_conta_como_numero(s, texto, tem):
    assert bool(s._numeros(texto)) is tem


# ---------------------------------------------------------------------------------------------------- LaTeX
# As seis seções do template, na ordem dele: o sumário vai em "sumario" e cada tema é subseção.
SECOES_TEX = [
    {"titulo": "Introdução", "texto": "Comparação socioambiental de A e B no ano fechado de 2025 [F1]."},
    {"titulo": "Dados e Metodologia",
     "texto": "Capacidade de capacidade_por_proprietario; emissões e metas dos relatórios das empresas [F2], em "
              "https://ri.exemplo.com.br/rel_2025.pdf.",
     "tabelas": [{"titulo": "Indicadores socioambientais 2025", "fontes": ["F1", "F2"],
                  "colunas": ["Indicador", "Empresa A", "Empresa B", "Unidade"],
                  "linhas": [["Capacidade renovável", "78,0", "41,0", "%"],
                             ["Intensidade de carbono", "0,12", "0,35", "tCO2e/MWh"]]},
                 {"titulo": "Trajetória socioambiental comparada, 2021 a 2025", "fontes": ["F1"],
                  "colunas": ["Indicador socioambiental", "Empresa A (2021)", "Empresa A (2025)",
                              "Empresa B (2021)", "Empresa B (2025)", "Observação"],
                  "linhas": [["Capacidade renovável própria", "61,0%", "78,0%", "38,0%", "41,0%",
                              "A acelerou depois do leilão de 2022"],
                             ["Intensidade de carbono", "0,31", "0,12", "0,37", "0,35",
                              "escopos 1 e 2 por MWh gerado, metodologia própria"]]}]},
    {"titulo": "Resultados",
     "subsecoes": [{"titulo": "Pontos fortes e fracos",
                    "texto": "A **Empresa A** tem 78% da capacidade renovável [F1]; a Empresa B fica em 41% "
                             "[F1] [F2].\n\n"
                             "- Forte (A): margem de 21% [F1].\n"
                             "- Fraco (B): 100% do P&D em um tema só [F1]."},
                   {"titulo": "Grau de similaridade",
                    "texto": "Maturidade distante: 4 dos 6 indicadores diferem mais de 20% [F1]."}]},
    {"titulo": "Conclusões e Recomendações",
     "texto": "1. Contratar 500 MW eólicos até 2027, como a A fez [F1].\n2. Publicar o escopo 3 [F2]."},
]
TEXMF = os.path.join(server.RAIZ, ".runtime", "texmf")  # onde ficam os pacotes que faltam no TeX Live do sistema


def _falta_tex() -> str:
    """O que impede compilar aqui. lastpage, enumitem e babel-portuges são do texlive-latex-extra e do
    texlive-lang-portuguese; sem eles (ou em .runtime/texmf) este teste é pulado."""
    if not shutil.which("pdflatex") or not shutil.which("bibtex"):
        return "pdflatex ou bibtex não instalado"
    ambiente = {**os.environ, "TEXMFHOME": TEXMF}
    faltam = [f for f in ("lastpage.sty", "enumitem.sty", "portuges.ldf")
              if subprocess.run(["kpsewhich", f], env=ambiente, capture_output=True).returncode != 0]
    return f"faltam no TeX Live: {', '.join(faltam)}" if faltam else ""


FALTA_TEX = _falta_tex()


def _partes(tex):
    """O que vem do template: do \\documentclass ao marcador de início, e do fim do conteúdo em diante."""
    linhas = tex.splitlines()
    doc = next(k for k, l in enumerate(linhas) if l.startswith(r"\documentclass"))
    i = next(k for k, l in enumerate(linhas) if k > doc and "INÍCIO DO CONTEÚDO" in l)
    j = next(k for k, l in enumerate(linhas) if k > doc and "FIM DO CONTEÚDO" in l)
    return linhas[doc:i + 2], linhas[j - 1:]


def test_latex_mantem_o_template_e_so_preenche_os_campos(s, tmp_path):
    r = s.gerar_relatorio("Benchmark A x B", SECOES_TEX, FONTES, subtitulo="Pilares socioambientais",
                          periodo="2021 a 2025", mostrar_latex=True)
    assert r["gravado"], r
    tex = r["codigo_latex"]
    with open(s.TEMPLATE, encoding="utf-8") as f:
        modelo = f.read()
    cabeca, fecho = _partes(tex)
    cabeca_modelo, fecho_modelo = _partes(modelo)
    assert len([l for l in cabeca_modelo if s.CAMPO.match(l)]) == 4  # os campos que o template manda preencher
    assert [l for l in cabeca if not s.CAMPO.match(l)] == [l for l in cabeca_modelo if not s.CAMPO.match(l)]
    assert fecho == fecho_modelo  # referências, apêndice e \end{document} como estão no template
    assert "INSTRUÇÕES GERAIS PARA A IA" not in tex  # as instruções de preenchimento não vão no relatório pronto
    assert tex.startswith("% Relatório gerado pelo CoppeZIP")
    assert r"\newcommand{\titulorelatorio}{Benchmark A x B}" in tex
    assert r"\newcommand{\subtitulorelatorio}{Pilares socioambientais}" in tex
    assert r"\newcommand{\periodoanalise}{2021 a 2025}" in tex
    assert re.search(r"\\newcommand\{\\datarelatorio\}\{\d{1,2} de \w+ de 20\d\d\}", tex)
    assert r"\bibliography{referencias}" in tex and "Título do Relatório" not in tex
    arquivo = [a for a in os.listdir(tmp_path) if a.endswith(".tex")][0]
    assert open(tmp_path / arquivo, encoding="utf-8").read() == tex


def test_latex_cita_a_fonte_de_cada_numero(s):
    r = s.gerar_relatorio("B", SECOES_TEX, FONTES, mostrar_latex=True)
    tex, bib = r["codigo_latex"], r["codigo_bib"]
    assert "78\\% da capacidade renovável \\cite{" + CHAVE1 + "}" in tex
    assert r"\cite{" + CHAVE1 + "," + CHAVE2 + "}" in tex  # [F1] [F2] seguidos, uma citação só
    assert r"\fonte{\cite{" + CHAVE1 + "," + CHAVE2 + "}}" in tex  # a fonte da tabela, como o template pede
    assert "@misc{" + CHAVE1 + "," in bib and "@misc{" + CHAVE2 + "," in bib
    assert "@misc{energynexus_db," in bib  # a entrada da base interna, que vem do modelo do template
    for chave in re.findall(r"\\cite\{([^}]+)\}", tex):  # nenhuma citação sem entrada no .bib
        for c in chave.split(","):
            assert "@misc{" + c + "," in bib


def test_bib_descreve_a_fonte_sem_inventar_campo(s):
    bib = s.gerar_relatorio("B", secao(), FONTES, mostrar_latex=True)["codigo_bib"]
    entrada = bib.split("@misc{" + CHAVE2 + ",")[1].split("}\n")[0]
    assert "author = {{Taesa}}" in entrada and "year   = {2025}" in entrada
    assert "url    = {https://ri.taesa.com.br/rs_2025.pdf}" in entrada
    assert "Fonte F2 do relatório, página 22" in entrada
    sem_ano = s.gerar_relatorio("B", secao(), [{"id": "F1", "descricao": "Tabela interna sem data"}],
                                mostrar_latex=True)["codigo_bib"]
    assert "year" not in sem_ano.split("@misc{tabela_interna_sem_data,")[1]  # sem ano na fonte, sem campo year


def test_latex_traz_subsecao_tabela_e_listas(s):
    tex = s.gerar_relatorio("B", SECOES_TEX, FONTES, mostrar_latex=True)["codigo_latex"]
    assert r"\section{Resultados}" in tex and r"\subsection{Pontos fortes e fracos}" in tex
    # tabela estreita: o LaTeX mede as colunas e só as de número vão para a direita (Unidade traz "%" e "tCO2e/MWh")
    assert r"\begin{table}[H]" in tex and r"\begin{tabular}{lrrl}" in tex
    assert re.search(r"\\begin\{tabular\}\{(p\{0\.\d+\\textwidth\}){6}\}", tex)  # tabela larga: colunas com largura
    assert r"\begin{itemize}[itemsep=2pt,topsep=2pt]" in tex and r"\begin{enumerate}[" in tex
    assert r"\caption{Indicadores socioambientais 2025}\label{tab:1-" in tex


def test_periodo_da_capa_sai_dos_anos_do_relatorio(s):
    r = s.gerar_relatorio("B", SECOES_TEX, FONTES, mostrar_latex=True)
    tex = r["codigo_latex"]
    # 2027 está no relatório como prazo de recomendação: período analisado vai só até o ano corrente
    assert r"\newcommand{\periodoanalise}{2021 a 2025}" in tex
    assert r"\newcommand{\subtitulorelatorio}{" + s.SUBTITULO + "}" in tex
    assert r["numeros_conferidos"] == 6  # os 5 números das subseções também passam pela conferência


def test_codigo_latex_so_quando_pedido(s):
    assert "codigo_latex" not in s.gerar_relatorio("B", secao(), FONTES)
    r = s.gerar_relatorio("B", secao(), FONTES, mostrar_latex=True)
    assert "codigo_latex" in r and "codigo_bib" in r


def test_recusa_numero_sem_fonte_na_subsecao(s, tmp_path):
    secoes = [{"titulo": "Resultados", "subsecoes": [{"titulo": "Pontos fortes", "texto": "A margem foi de 21%."}]}]
    r = s.gerar_relatorio("X", secoes, FONTES)
    assert not r["gravado"] and "subseção 1" in r["erros"][0] and os.listdir(tmp_path) == []


@pytest.mark.parametrize("texto, esperado", [
    ("100% do P&D em kpis_financeiros", r"100\% do P\&D em kpis\_financeiros"),
    ("Receita de R$ 4,62 bi [F1].", r"Receita de R\$ 4,62 bi \cite{k1}."),
    ("**Forte** e fraco", r"\textbf{Forte} e fraco"),
    ("Veja https://ri.exemplo.com.br/a_b.pdf.", r"Veja \url{https://ri.exemplo.com.br/a_b.pdf}."),
])
def test_escapa_o_que_o_tex_leria_como_comando(s, texto, esperado):
    assert s._tex_rico(texto, {"F1": "k1"}) == esperado


@pytest.mark.skipif(bool(FALTA_TEX), reason=FALTA_TEX)
def test_o_projeto_latex_compila(s, tmp_path):
    r = s.gerar_relatorio("Benchmark socioambiental: A x B (2025)", SECOES_TEX, FONTES,
                          sumario="A A lidera: 78% renovável [F1] e intensidade de 0,12 tCO2e/MWh [F2].",
                          lacunas=["Escopo 3 da B não divulgado."])
    assert r["gravado"], r
    obra = tmp_path / "obra"
    with zipfile.ZipFile(tmp_path / [a for a in os.listdir(tmp_path) if a.endswith(".zip")][0]) as z:
        z.extractall(obra)
    ambiente = {**os.environ, "TEXMFHOME": TEXMF}

    def rodar(*cmd):
        return subprocess.run(cmd, cwd=obra, env=ambiente, capture_output=True, text=True)

    for passo in (("pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"),
                  ("bibtex", "main"),  # as referências: sem isso as citações saem como [?]
                  ("pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"),
                  ("pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex")):
        saida = rodar(*passo)
        assert saida.returncode == 0, f"{passo[0]}: {saida.stdout[-2000:]}"
    assert os.path.exists(obra / "main.pdf")
    registro = open(obra / "main.log", encoding="utf-8", errors="replace").read()
    assert "in alignment" not in registro  # overfull de tabela: as colunas não fecham a linha
    assert "Citation" not in registro and "undefined" not in registro  # toda \cite achou sua entrada no .bib

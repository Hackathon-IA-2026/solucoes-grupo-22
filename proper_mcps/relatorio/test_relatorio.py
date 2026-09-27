"""Testes de gerar_relatorio: conferência do conteúdo e compilação com o TinyTeX de .runtime/tinytex.
Rodar: .runtime/venv/bin/python -m pytest proper_mcps -q"""
import importlib.util
import os
import re
import zipfile

import pymupdf
import pytest

# carregado pelo caminho: proper_mcps/dados também tem um server.py
_spec = importlib.util.spec_from_file_location("relatorio_server", os.path.join(os.path.dirname(__file__), "server.py"))
server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(server)


@pytest.fixture()
def s(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "PASTA", str(tmp_path))
    return server


REFS = r"""
@misc{cvm_dfp_2025,
  author = {{Comissão de Valores Mobiliários}},
  title  = {{Demonstrações Financeiras Padronizadas} ({DFP}) 2025},
  year   = {2026},
  url    = {https://dados.cvm.gov.br/dataset/cia_aberta-doc-dfp},
  note   = {Acesso em: 26/09/2026. Tabela/consulta: indicadores\_financeiros.}
}

@techreport{taesa_rs_2025,
  author      = {{Taesa}},
  title       = {Relatório de Sustentabilidade 2025},
  institution = {Taesa},
  year        = {2026},
  note        = {Acesso em: 26/09/2026. Página 22.}
}
"""

CONTEUDO = r"""\section{Sumário Executivo}\label{sec:sumario}
A receita líquida da Taesa foi de R\$ 4,62 bilhões em 2025 \cite{cvm_dfp_2025}, com margem EBITDA de
81,4\% \cite{cvm_dfp_2025}. A Tabela~\ref{tab:taesa} resume os números.

\section{Introdução}\label{sec:introducao}
Este relatório descreve o desempenho financeiro da Taesa em 2025.

\section{Dados e Metodologia}\label{sec:metodologia}
Os valores vêm das demonstrações financeiras consolidadas entregues à CVM \cite{cvm_dfp_2025} e do relatório de
sustentabilidade da empresa \cite{taesa_rs_2025}.

\section{Resultados}\label{sec:resultados}
\subsection{Receita e EBITDA}\label{sec:receita}
\begin{table}[H]
  \centering
  \caption{Receita líquida e EBITDA da Taesa em 2025 (R\$ bilhões)}\label{tab:taesa}
  \begin{tabular}{lr}
    \toprule
    \textbf{Indicador} & \textbf{2025} \\
    \midrule
    Receita líquida & 4,62 \\
    EBITDA & 3,76 \\
    \bottomrule
  \end{tabular}
  \fonte{\cite{cvm_dfp_2025}}
\end{table}

\section{Discussão e Pontos de Atenção}\label{sec:discussao}
A análise do Energy Nexus sugere margem estável; o dado de dívida por instrumento não está disponível na base
consultada.

\section{Conclusões e Recomendações}\label{sec:conclusoes}
\begin{itemize}
  \item Acompanhar a receita de 2026 \cite{cvm_dfp_2025}.
\end{itemize}"""


def gerar(s, conteudo=CONTEUDO, referencias=REFS, periodo="01/01/2025 a 31/12/2025"):
    return s.gerar_relatorio("Taesa em 2025", "Desempenho financeiro", periodo, conteudo, referencias)


def test_gera_pdf_no_modelo_com_fonte_e_bloco_do_painel(s, tmp_path):
    r = gerar(s)
    assert r.startswith("Relatório gerado"), r
    pdf = re.search(r"^PDF: /relatorios/(\S+\.pdf)$", r, re.M).group(1)
    assert 'type="application/pdf" title="Taesa em 2025.pdf"' in r and f"\n/relatorios/{pdf}\n" in r
    doc = pymupdf.open(tmp_path / pdf)
    texto = " ".join(" ".join(p.get_text().split()) for p in doc)
    assert doc.page_count >= 4 and "??" not in texto  # sumário, "Página x de y" e citações resolvidos
    for trecho in ("Taesa em 2025", "Desempenho financeiro", "01/01/2025 a 31/12/2025", "R$ 4,62 bilhões",
                   "81,4%", "Página 1 de", "Referências", "Demonstrações Financeiras Padronizadas (DFP) 2025"):
        assert trecho in texto, trecho
    with zipfile.ZipFile(tmp_path / pdf.replace(".pdf", ".zip")) as z:
        assert sorted(z.namelist()) == ["imagens/energynexus_logo.png", "main.tex", "referencias.bib"]
        tex = z.read("main.tex").decode()
    modelo = open(os.path.join(server.MODELO, "main.tex"), encoding="utf-8").read()
    corte = "%%  DADOS DO RELATÓRIO"
    assert tex.split(corte)[0] == modelo.split(corte)[0]  # preâmbulo e identidade visual intactos
    assert tex.split("%%  FIM DO CONTEÚDO")[1] == modelo.split("%%  FIM DO CONTEÚDO")[1]


def test_recusa_estrutura_numero_sem_fonte_e_citacao_inexistente(s, tmp_path):
    conteudo = (CONTEUDO.replace(r"\section{Introdução}", r"\section{Contexto}")
                .replace("Este relatório descreve", "A Taesa tem 12 concessões. Este relatório descreve")
                .replace(r"\fonte{\cite{cvm_dfp_2025}}", r"\fonte{\cite{ons_carga_2025}}"))
    r = gerar(s, conteudo)
    assert r.startswith("Relatório NÃO gerado")
    assert "Veio: Sumário Executivo; Contexto" in r
    assert "tem número (12) sem \\cite" in r and "\\cite{ons_carga_2025} não existe" in r
    assert os.listdir(tmp_path) == []


def test_recusa_percentual_sem_barra_comando_proibido_e_referencia_incompleta(s):
    conteudo = CONTEUDO.replace(r"81,4\%", "81,4%").replace("Este relatório", r"\input{/etc/passwd} Este relatório")
    r = gerar(s, conteudo, REFS.replace("  year   = {2026},\n", "", 1), periodo="2025")
    assert "linha 3 do conteúdo: '%' sem barra" in r and "\\input não é permitido" in r
    assert "referência 'cvm_dfp_2025': faltam os campos year" in r and "fora do formato DD/MM/AAAA" in r


def test_recusa_tabela_sem_fonte_e_figura(s):
    conteudo = CONTEUDO.replace(r"\fonte{\cite{cvm_dfp_2025}}", "") + "\n\\includegraphics{x.png}"
    r = gerar(s, conteudo)
    assert "falta a linha de fonte" in r and "não aceita figuras" in r


def test_erro_de_latex_aponta_a_linha_do_conteudo(s):
    r = gerar(s, CONTEUDO.replace("Este relatório descreve", r"Este \textbff{relatório} descreve"))
    assert r.startswith("Relatório NÃO gerado: o LaTeX não compilou")
    assert "linha 6 do conteúdo: Undefined control sequence" in r


@pytest.mark.parametrize("conteudo, motivo", [
    pytest.param(CONTEUDO.replace("da Taesa em 2025.", "da Taesa em"), "no meio da frase", id="paragrafo-do-meio"),
    pytest.param(CONTEUDO.replace("da Taesa em 2025.", "da Taesa [...]"), "marca de corte", id="marca-de-corte"),
    pytest.param(CONTEUDO + "\n\nEm 2026 a Taesa deve", "no meio da frase", id="fim-do-conteudo"),
])
def test_recusa_conteudo_truncado(s, tmp_path, conteudo, motivo):
    """Dois relatórios da auditoria foram gravados cortados no meio da frase, com aparência de completos."""
    r = gerar(s, conteudo)
    assert r.startswith("Relatório NÃO gerado") and motivo in " ".join(r.split())
    assert os.listdir(tmp_path) == []


def test_aceita_citacao_literal_com_supressao_e_item_sem_ponto(s):
    """A marca [...] no meio de uma citação literal é supressão, e item de lista pode acabar sem pontuação."""
    conteudo = (CONTEUDO.replace("Este relatório descreve",
                                 'A empresa afirma "reduzir emissões [...] até 2030" \\cite{taesa_rs_2025}. '
                                 "Este relatório descreve")
                .replace(r"\item Acompanhar a receita de 2026 \cite{cvm_dfp_2025}.",
                         r"\item Acompanhar a receita de 2026 \cite{cvm_dfp_2025}"))
    r = gerar(s, conteudo)
    assert r.startswith("Relatório gerado"), r


def test_avisa_tabela_que_nao_esta_no_catalogo_e_aceita_a_que_esta(s):
    """A auditoria passou "tabela_que_nao_existe, conta 9.99" e o relatório saiu com cara de auditado."""
    inventada = REFS.replace(r"Tabela/consulta: indicadores\_financeiros.",
                             r"Tabela/consulta: tabela\_que\_nao\_existe, conta 9.99.")
    r = gerar(s, referencias=inventada)
    assert r.startswith("Relatório gerado")  # é aviso, não erro: fonte de documento e de link não têm tabela
    assert "referência cvm_dfp_2025: 'tabela_que_nao_existe' não é uma tabela nem uma ferramenta" in r
    certa = REFS.replace(r"Tabela/consulta: indicadores\_financeiros.", r"Tabela/consulta: kpis\_financeiros.")
    assert "não é uma tabela" not in gerar(s, referencias=certa)


def test_diz_que_a_conferencia_e_de_forma_nao_de_valor(s):
    """O chat repassava "conferido automaticamente" ao usuário; a ferramenta não confere valor contra a base."""
    r = gerar(s)
    assert "Os valores NÃO foram reconferidos na base" in r
    assert "nunca o valor em si contra a base" in server.__doc__
    assert "não são reconferidos contra a base" in server.gerar_relatorio.__doc__


@pytest.mark.parametrize("texto, tem", [
    ("Em 2025 a empresa cresceu.", False),          # ano não conta
    ("Dados do 2T26 e escopo 1.", False),           # trimestre e número de um dígito
    ("Alavancagem de 3,9x.", True),
    (r"Alta de 12\%.", True),
    (r"Lucro de R\$~616 milhões.", True),
    (r"Veja a Tabela~\ref{tab:x2025} e \cite{cvm_dfp_2025}.", False),
    (r"Veja \url{https://ri.taesa.com.br/2026/05/x.pdf}", False),
    ("Dados preliminares até 30/09/2025 e vigência em 04/2026.", False),  # datas
])
def test_o_que_conta_como_numero(s, texto, tem):
    assert bool(s._numeros(texto)) is tem

---
name: relatorio-energynexus
description: Formato e regras do relatório final do EnergyNexus em PDF (modelo LaTeX oficial do Energy Nexus - capa, seis seções fixas, citação da fonte de cada fato e referências em BibTeX), gerado pela ferramenta gerar_relatorio e aberto no painel ao lado do chat. Use sempre que o usuário pedir relatório, memorando, ficha, nota para comitê, parecer ou documento para baixar, guardar ou enviar, inclusive no fim dos roteiros de benchmark, crédito, investimento ou clima.
---

# Relatório final do EnergyNexus (PDF)

O relatório é de inteligência competitiva do setor elétrico: transforma os dados da base e os relatórios das
empresas numa análise estruturada, comparável, situada no tempo e rastreável. Ele responde à pergunta ou demanda
que o originou. A ferramenta `gerar_relatorio` preenche o modelo LaTeX oficial (capa, identidade visual, sumário,
cabeçalho e referências são fixos) e compila o PDF. Você escreve só os campos da capa, o conteúdo das seis seções
e as referências.

## 1. Antes de escrever

- Levante todos os números com as ferramentas de dados e de documentos. `gerar_relatorio` não busca nada: só confere
  e compila.
- Anote para cada dado a fonte original: tabela da base e a coluna `fonte` do catálogo (`listar_tabelas`,
  `descrever_tabela`), ou documento, ano e página (`buscar_documentos`, `ler_pagina`, `listar_documentos`).
- Use só o que as ferramentas devolveram. Nunca invente referências, autores, títulos, URLs, documentos, páginas,
  valores, indicadores ou eventos.

## 2. Parâmetros de gerar_relatorio

- `titulo` e `subtitulo`: texto simples da capa (subtítulo = tema da análise).
- `periodo`: período dos dados, `DD/MM/AAAA a DD/MM/AAAA` (anos fechados: `01/01/2021 a 31/12/2025`).
- `conteudo`: LaTeX das seis seções (itens 3 a 7).
- `referencias`: uma entrada BibTeX por fonte citada (item 8).

## 3. Estrutura: seis seções, nesta ordem e com estes títulos

```latex
\section{Sumário Executivo}\label{sec:sumario}
\section{Introdução}\label{sec:introducao}
\section{Dados e Metodologia}\label{sec:metodologia}
\section{Resultados}\label{sec:resultados}
\section{Discussão e Pontos de Atenção}\label{sec:discussao}
\section{Conclusões e Recomendações}\label{sec:conclusoes}
```

Não crie outra `\section`; dentro delas use `\subsection{}` e `\subsubsection{}`, só para temas relevantes à
pergunta. Parágrafos curtos (3 a 6 frases); listas (`itemize`) só para itens objetivos: recomendações, premissas,
riscos.

- **Sumário Executivo** (1 a 3 parágrafos, até ~300 palavras, compreensível sozinho): pergunta analisada, empresas e
  período, principais achados, indicadores mais relevantes, principais diferenças ou tendências, conclusão central.
- **Introdução**: contexto, pergunta ou demanda que originou o relatório, empresas, período, escopo e relevância para
  inteligência competitiva.
- **Dados e Metodologia**: fontes e documentos consultados (citando cada um), período dos dados, indicadores,
  filtros e agregações, métodos de comparação, cálculos feitos e limitações dos dados.
- **Resultados**: uma `\subsection` por tema (evolução temporal, comparação entre empresas, investimentos,
  desempenho, sustentabilidade, estratégias), com tabelas e o que elas mostram.
- **Discussão e Pontos de Atenção**: tendências, diferenças entre empresas, trajetórias estratégicas, mudanças
  relevantes, limitações, incertezas e diferenças metodológicas entre fontes, separando o que é dado do que é
  interpretação.
- **Conclusões e Recomendações**: retome os achados e, quando pedido ou pertinente, recomende com base só nas
  evidências. Não introduza dados novos nesta seção.

## 4. Rastreabilidade (obrigatória)

- Todo fato relevante tem fonte: valores, indicadores, séries, datas, investimentos, metas, resultados financeiros,
  informações operacionais e socioambientais, estratégias e compromissos, ações ou resultados de uma empresa.
- Ponha `\cite{chave}` logo depois da informação: `A empresa investiu R\$ 2,4 bilhões em 2024 \cite{fonte}.`
- Todo parágrafo ou item com número precisa de `\cite` (a ferramenta recusa o que não tiver). Toda chave citada
  existe em `referencias`.
- Use a fonte mais específica de cada dado; não pendure muitos dados numa referência genérica. Dado da base cita a
  fonte original (CVM, ANEEL, ONS, BNDES...). A chave `energynexus_db` (base interna do Energy Nexus, já definida)
  só quando a origem específica não estiver disponível.
- Tabela tem linha de fonte: `\fonte{\cite{chave}}` ou, com várias fontes,
  `\fonte{Elaborado pelo Energy Nexus a partir de \cite{fonte1, fonte2}.}`

## 5. Fato, comparação, inferência e recomendação

- Fato (dado apresentado pela fonte) e comparação (relação entre dados) citam as fontes.
- Inferência ou análise deixa claro que é análise do Energy Nexus (da IA) e cita as evidências que a sustentam.
- Recomendação deriva da análise feita.
- Correlação no tempo não é causalidade. Escreva "Após o anúncio da estratégia, observou-se aumento do investimento
  \cite{a,b}" e "Os dados sugerem uma possível relação...", não "a estratégia causou o aumento". Causalidade só com
  evidência explícita da fonte, citada.

## 6. Comparações, evolução no tempo e sustentabilidade

- Compare empresas no mesmo período e com o mesmo critério. Antes, confira unidade, período de referência,
  definição e escopo do indicador, metodologia da empresa e nomenclatura. Indicadores de definições diferentes não
  são equivalentes: diga a limitação. Indicador ausente não é zero.
- Com vários anos, procure mudanças relevantes, novos investimentos, mudanças de estratégia e de metas, iniciativas
  de sustentabilidade, mudanças de matriz ou portfólio, evolução de emissões, expansão ou redução de atividades.
  Quando os dados permitirem, organize como trajetória observada: estratégia ou evento → investimento ou ação →
  mudança observada → indicador ou resultado posterior (trajetória, não causa).
- Em sustentabilidade e transição (emissões, renováveis, eficiência, investimentos ambientais, metas climáticas,
  inovação, indicadores socioambientais), separe meta anunciada, iniciativa em andamento, investimento realizado e
  resultado observado. Meta anunciada não é resultado alcançado.

## 7. Dados ausentes, tabelas e escrita

- Sem o dado, escreva "dado não disponível na base consultada". Não estime, complete nem extrapole; estimativa só
  se pedida, com o método descrito e marcada como estimativa do Energy Nexus.
- Tabelas só quando ajudam a entender; não repita o que o texto já diz. Toda tabela tem título descritivo, rótulo,
  unidades e fonte, e a legenda se entende sem o texto. Modelo:

```latex
\begin{table}[H]
  \centering
  \caption{Receita líquida por empresa, 2021 a 2025 (R\$ bilhões)}\label{tab:receita}
  \begin{tabular}{lrr}
    \toprule
    \textbf{Empresa} & \textbf{2024} & \textbf{2025} \\
    \midrule
    Taesa & 4,21 & 4,62 \\
    \bottomrule
  \end{tabular}
  \fonte{\cite{cvm_dfp_2025}}
\end{table}
```

- O modelo não tem figuras: mostre séries e comparações em tabelas.
- Português do Brasil, técnico, objetivo e claro, sem tom promocional ou opinativo. Explique conceitos técnicos
  quando necessários. Priorize números e comparações objetivas. Unidades MW, MWmed, MWh, GWh, TWh, R\$/MWh, R\$, \%,
  tCO2e; mantenha a unidade da fonte quando converter mudaria a leitura. Vírgula decimal; datas DD/MM/AAAA.
- LaTeX: escape `\%`, `\&`, `\$`, `\_`, `\#` (dinheiro é `R\$ 4,62 bilhões`, percentual é `12,5\%`). Rótulos
  `sec:`, `tab:`, `eq:`; referências internas com `\ref{tab:receita}`. Não use `\usepackage`, `\input`,
  `\newcommand` nem comandos que mudem o modelo.

## 8. Referências (BibTeX)

Uma entrada por fonte citada; só as citadas aparecem no PDF. Chave `fonte_tema_ano` em minúsculas, sem acentos nem
espaços (`cvm_dfp_2025`, `aneel_siga_2026`, `taesa_rs_2025`). Tipos: `@misc` (bases de dados e páginas web),
`@techreport` (relatórios técnicos), `@article`, `@book`. Campos: `author` (instituição entre chaves duplas),
`title` (siglas e nomes próprios entre chaves para manter as maiúsculas), `year`, `url` quando houver e `note`
(`Acesso em: DD/MM/AAAA.` e a tabela ou página de onde veio o dado). Não use o caractere arroba em comentários.

```bibtex
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
  year        = {2025},
  url         = {https://...},
  note        = {Acesso em: 26/09/2026. Página 22.}
}
```

Autor, título, ano e URL saem do que as ferramentas devolveram (coluna `fonte` do catálogo; título, ano e link do
documento em `listar_documentos`). Sem URL conhecida, omita o campo.

## 9. Conferência final e entrega

Antes de chamar a ferramenta, confira: todo fato tem fonte e toda chave existe; nada foi inventado; empresas e
períodos corretos; unidades consistentes; comparações entre indicadores compatíveis; inferências identificadas; metas
não apresentadas como resultado; relações no tempo não apresentadas como causa; tabelas com fonte; referências
cruzadas corretas.

Se `gerar_relatorio` recusar, corrija exatamente o que ela apontou e chame de novo. Quando gerar, responda com 2 a 4
frases dos principais achados e termine com o bloco `:::artifact` que ela devolveu, copiado sem mudar nada: ele abre
o PDF grande ao lado do chat, com o botão de baixar.

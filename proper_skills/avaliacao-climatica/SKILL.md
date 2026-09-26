---
name: avaliacao-climatica
description: Roteiro de avaliação climática de empresas do setor elétrico (Placar da Transição, emissões de escopos 1, 2 e 3, intensidade, metas e SBTi, matriz renovável e fóssil, cortes de geração, radar de greenwashing, exposição a preço de carbono, qualidade da divulgação, IFRS S1/S2 e CVM 193/244). Use quando o usuário pedir perfil climático, comparação de emissões ou metas, maturidade climática, ranking ESG ou quadro para comitê ESG.
---

# Avaliação climática

**Comece pelo Placar da Transição.** As emissões, metas, % renovável, CAPEX e frameworks dos relatórios já estão
extraídos com documento, página e checagem de que o valor aparece na página: `consultar_placar(empresa[, ano])`
responde em uma chamada o que antes exigia várias buscas. Só vá aos documentos (`buscar_documentos`, `ler_pagina`)
para o que o placar não tiver — contexto da meta, método, fronteira, riscos — e com poucas buscas bem filtradas.

O placar cobre só as empresas com relatório indexado (`listar_documentos` mostra quais). Para as demais, diga que
não há relatório na base e vá aos dados oficiais.

## 1. Fixe o escopo comum

- **Entidades**: a empresa como no relatório (ex.: Engie Brasil Energia, holding). Use `listar_documentos` para
  ver quais relatórios existem de cada uma antes de buscar.
- **Período**: o mesmo ano-base para todas (último relatório comum). Se uma só tiver ano anterior, avise.
- **Escopo**: escopo 2 por localização ou por mercado; fronteira (controle operacional, participação acionária);
  unidade (tCO2e) e intensidade (tCO2e/MWh). Só compare quando escopo e fronteira forem iguais; senão, separe.

## 2. Levante

| Bloco | Onde |
|---|---|
| Emissões escopos 1, 2 e 3, intensidade | `consultar_placar` (traz arquivo, página e confiança); só no relatório se faltar |
| Metas, net zero, SBTi | `consultar_placar`; o texto e a fronteira da meta, no relatório com `ler_pagina` |
| Comparação entre empresas | `placar_ranking` (score de divulgação, intensidade por receita, escopo 1+2, % renovável) |
| Divergência entre discurso e dado | `radar_consistencia` (cada alerta traz as duas evidências) |
| Risco de preço de carbono | `exposicao_carbono(preco_por_t)` (emissões × preço contra EBITDA e lucro) |
| Matriz renovável e fóssil | `capacidade_por_proprietario` (tipo_geracao, fase, potencia_mw), dono direto |
| Cortes de geração | `curtailment_por_dono_mensal`, estimativa por dono |
| Norma de divulgação | Resoluções CVM 193 e 244 na base de documentos |

Totais de emissões: some por SQL ou confira que a soma dos escopos bate com o total citado; diga se o total do
relatório inclui escopo 3.

## 3. Entregue

1. **Resposta direta** (2 a 3 frases).
2. **Escopo**: empresas, ano-base, fronteira e método de cada uma.
3. **Tabela de evidência**: indicador | empresa | valor | unidade | ano | fonte (documento e página ou tabela).
   Níveis de maturidade (mais maduro, intermediário, incipiente) só com critério explícito e evidência na tabela;
   sem evidência, escreva "sem evidência comparável" em vez de dar nota.
4. **Lacunas**: o que a empresa não divulga ou não está na base (IFRS S1/S2, ISE e ICO2 da B3, títulos verdes,
   riscos físicos quantificados) e onde achar (relatório da empresa, B3, SBTi).

Se o usuário quiser **ver ou compartilhar** o comparativo, monte a tela: `tela_ranking`, `tela_radar` ou
`tela_carbono` gravam um HTML com o gráfico, a tabela e a fonte de cada número, e devolvem o link — mande o link e
resuma o essencial no texto. Se pedir quadro para comitê ou documento, termine com `gerar_relatorio`.

Números do placar vêm de leitura automática do relatório: cite sempre arquivo e página e, se o valor for decisivo
para uma conclusão, confirme na página com `ler_pagina` antes de afirmar.

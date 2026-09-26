---
name: avaliacao-climatica
description: Roteiro de avaliação climática de empresas do setor elétrico (emissões de escopos 1, 2 e 3, intensidade, metas e SBTi, matriz renovável e fóssil, cortes de geração, riscos e qualidade da divulgação, IFRS S1/S2 e CVM 193/244). Use quando o usuário pedir perfil climático, comparação de emissões ou metas, maturidade climática ou quadro para comitê ESG.
---

# Avaliação climática

Orçamento: até 8 chamadas de ferramenta. Emissões e metas vêm dos relatórios: faça poucas buscas bem filtradas
(`buscar_documentos` com empresa e ano) e use `ler_pagina` só na página da tabela de emissões. Não repita a mesma
busca com palavras parecidas. Se o orçamento acabar, entregue o que foi confirmado e liste o resto em Lacunas.

## 1. Fixe o escopo comum

- **Entidades**: a empresa como no relatório (ex.: Engie Brasil Energia, holding). Use `listar_documentos` para
  ver quais relatórios existem de cada uma antes de buscar.
- **Período**: o mesmo ano-base para todas (último relatório comum). Se uma só tiver ano anterior, avise.
- **Escopo**: escopo 2 por localização ou por mercado; fronteira (controle operacional, participação acionária);
  unidade (tCO2e) e intensidade (tCO2e/MWh). Só compare quando escopo e fronteira forem iguais; senão, separe.

## 2. Levante

| Bloco | Onde |
|---|---|
| Emissões escopos 1, 2 e 3, intensidade | relatório de sustentabilidade ou inventário (`buscar_documentos` "emissões escopo 1 2 3 tCO2e"), com página |
| Metas, net zero, SBTi | relatório, com página; SBTi só se o documento declarar validação |
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

Se o usuário pedir quadro para comitê ou documento, termine com `gerar_relatorio`.

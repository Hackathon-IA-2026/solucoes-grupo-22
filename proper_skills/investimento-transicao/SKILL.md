---
name: investimento-transicao
description: Roteiro para comparar como empresas do setor elétrico investem na transição energética (investimento total, matriz de geração, expansão, cortes de geração, retorno e alavancagem) e para memorando de investimento. Use quando o usuário pedir quem investe mais, ranking de investimento, tese ou memorando de investimento, ou comparação de posicionamento na transição.
---

# Comparação de investimento na transição

Uma chamada de `indicadores_financeiros` por empresa e uma consulta
agregada por tabela (todas as empresas no mesmo `WHERE cnpj IN (...)`).

## 1. Fixe o escopo comum

- **Entidades**: o grupo listado (holding) de cada empresa, com o CNPJ de `buscar_empresa`. Diga se algum dado é da
  holding e outro de uma subsidiária.
- **Período**: os mesmos anos para todas (ex.: 2021 a 2025, DFP). Nada de misturar ano com trimestre.
- **Conceitos**: `investimento_total_brl` = maior entre CAPEX de caixa (DFC) e custo de construção das concessões
  (sem somar os dois). CAPEX de caixa e obra por competência são conceitos diferentes: separe as colunas quando o
  usuário pedir e não faça ranking antes de reconciliar. A base não classifica investimento como "verde";
  essa divisão só vem dos relatórios, com página.

## 2. Levante

| Bloco | Onde |
|---|---|
| Receita, EBITDA, investimento total, investimento/receita, DL/EBITDA, ROE | `indicadores_financeiros` |
| Matriz em operação e em construção | `capacidade_por_proprietario` (tipo_geracao, fase, potencia_mw); é do dono direto (SPE), não do grupo inteiro |
| Cortes de geração | `curtailment_por_dono_mensal` (energia_cortada_mwh_estimada / referencia_mwh_estimada), estimativa por dono |
| Expansão contratada | `leiloes_geracao`, `transmissao_empreendimentos` |
| CAPEX por segmento, plano de investimento, metas | relatórios (`buscar_documentos`, `ler_pagina`), com página |

Percentuais, somas e razões: calcule por SQL e confira que o total bate com as parcelas.

## 3. Entregue

1. **Resposta direta** (2 a 3 frases) com o critério do ranking explícito.
2. **Escopo**: empresas e CNPJs, anos, definição de investimento e de cada indicador.
3. **Tabela de evidência**: uma linha por empresa; colunas com o mesmo período; coluna Fonte (tabela e conta ou
   documento e página). Métricas de conceitos diferentes ficam em colunas separadas, sem ranking conjunto.
4. **Riscos e leitura**, separando fato de avaliação.
5. **Lacunas**: CAPEX verde por empresa, investimento proporcional, dados só do RI, participação de grupo em SPEs.

Memorando: siga o roteiro `relatorio-energynexus` (tese no Sumário Executivo, a tabela em Resultados, riscos e
lacunas em Discussão e Pontos de Atenção) e termine com `gerar_relatorio`.

---
name: ficha-credito
description: Roteiro de ficha ou nota de crédito de empresa do setor elétrico (dívida, alavancagem, cobertura de juros, geração de caixa, dividendos, debêntures incentivadas, BNDES e riscos de concessão). Use quando o usuário pedir análise de crédito, risco de refinanciamento, nota para comitê de crédito ou comparação de emissores.
---

# Ficha de crédito

Orçamento: até 8 chamadas de ferramenta. `indicadores_financeiros` já traz quase tudo de uma vez; use SQL só para
debêntures, BNDES e contratos. Se o orçamento acabar, entregue o que foi confirmado e liste o resto em Lacunas.

## 1. Fixe o escopo comum

- **Entidade**: o emissor (CNPJ de `buscar_empresa`); holding e subsidiária são créditos diferentes.
- **Período**: último ano fechado (DFP) e o último trimestre com 12 meses (`trimestres_recentes`, ITR). Diga os dois.
- **Escopo**: consolidado, conceito CVM. Métricas do RI (dívida líquida gerencial, EBITDA ajustado) podem diferir:
  não misture; se o usuário citar o RI, explique a diferença.

## 2. Levante

| Bloco | Onde |
|---|---|
| Dívida bruta, caixa, dívida líquida, DL/EBITDA, cobertura de juros (EBITDA/despesas financeiras) | `indicadores_financeiros` (anos e trimestres_recentes) |
| Caixa operacional, investimento total, dividendos e JCP pagos | `indicadores_financeiros`: caixa_operacional_brl, investimento_total_brl, dividendos_jcp_pagos_brl |
| Debêntures incentivadas | `debentures_incentivadas` (emissora LIKE nome; valor_brl, data_vencimento, indexador, taxa_ou_spread_pct) |
| BNDES | `bndes_operacoes` WHERE cnpj = ...: valor_contratado_brl, valor_desembolsado_brl, custo_financeiro |
| Concessões (transmissão) | `transmissao_contratos` WHERE cnpj = ...: data_fim |
| Cronograma de amortização, covenants, rating | notas explicativas ou RI (`buscar_documentos`); se não achar, é lacuna |

Calcule por SQL: caixa operacional − investimento total − dividendos (folga ou necessidade de financiamento).

## 3. Entregue

1. **Conclusão direta** (2 a 3 frases), separada como avaliação sua, não fato.
2. **Escopo**: emissor, CNPJ, períodos, consolidado CVM.
3. **Tabela de evidência**: indicador | valor | período | fonte (tabela e conta). Uma linha por indicador; em
   comparação de emissores, uma coluna por emissor com o mesmo período.
4. **Riscos e pontos a monitorar**, cada um ligado a um número da tabela ou a um documento com página.
5. **Lacunas**: vencimentos por ano, covenants, rating, RAP por concessão, o que só o RI tem.

Se o usuário pedir nota para comitê ou documento, termine com `gerar_relatorio`.

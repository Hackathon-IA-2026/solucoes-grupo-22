---
name: benchmark-socioambiental
description: Roteiro de benchmark socioambiental (ESG) entre duas empresas do setor elétrico, com relatório no template LaTeX padrão (pontos fortes e fracos de cada pilar, grau de similaridade dos desafios e da maturidade, direcionamento estratégico para a menos madura a partir do case da outra). Use quando o usuário pedir comparação socioambiental ou ESG de duas empresas, benchmark de sustentabilidade, ou o relatório padrão em .tex.
---

# Benchmark socioambiental de duas empresas

Duas empresas por vez, o mesmo ano para as duas e uma consulta agregada por bloco
(`WHERE cnpj IN (...)`), não uma consulta por empresa.

## 1. Fixe o escopo comum (antes de consultar)

- **Entidades**: `buscar_empresa` com o nome como o usuário escreveu; diga o CNPJ e se é a holding ou a operação.
- **Segmento**: distribuição, geração e transmissão não dividem os mesmos indicadores. Compare só os blocos que
  valem para as duas e diga quais ficaram de fora (DEC e FEC, por exemplo, não existem para geradora).
- **Período**: o último ano fechado comum (`kpis_financeiros` vai até 2025; confira o ano do relatório de cada uma).
  Nunca compare 2025 de uma com 2024 da outra sem avisar.
- **Porte**: levante receita, EBITDA e capacidade instalada primeiro. Eles dizem qual é a menor (o direcionamento é
  para ela) e evitam comparar valor absoluto: normalize por MW, por consumidor ou por R$ de receita.

## 2. Levante (pilar por pilar)

| Pilar | Indicador | Onde |
|---|---|---|
| Ambiental | matriz por origem (Hídrica, Eólica, Solar, Biomassa, Nuclear, Fóssil) e fase | `capacidade_por_proprietario` (origem, fase, potencia_mw); por grupo, `capacidade_por_grupo` (potencia_proporcional_mw) |
| Ambiental | expansão outorgada e em obra | `expansao_geracao` (origem, potencia_outorgada_mw, situacao_obra; só tem proprietarios_texto, não CNPJ) |
| Ambiental | energia cortada | `curtailment_por_dono_mensal` (energia_cortada_mwh_estimada), estimativa por dono |
| Ambiental | emissões escopos 1, 2 e 3, intensidade, metas | relatórios: `buscar_documentos` e `ler_pagina`, sempre com a página |
| Social | continuidade do serviço | `dec_fec_distribuidora_anual` (dec_horas e dec_limite_medio_ponderado_horas), `ranking_continuidade` (posicao, dgc) |
| Social | compensação paga ao consumidor | `compensacoes_continuidade`: SUM(valor) por cnpj e ano |
| Social | eficiência energética | `pee_projetos` (custo_total_brl, energia_economizada_mwh; junta por empresa, a tabela não tem CNPJ) |
| Social | tarifa e mercado atendido | `tarifas_distribuicao` (subgrupo B1, classe residencial, vigência mais recente, tusd + te), `mercado_distribuidoras_mensal` (consumidores) |
| Social | geração distribuída na rede | `gd_mmgd` (potencia_mw, ucs_recebem_credito) |
| Governança e inovação | P&D regulado | `ped_projetos` (custo_previsto_brl, segmento, situacao) |
| Governança e inovação | controle e cadeia societária | `grupos_economicos`, `participacoes_societarias` |
| Investimento | rede, transição e funding | `pdd_investimentos` (planejado_brl, realizado_brl), investimento_total_brl de `indicadores_financeiros`, `bndes_operacoes` (valor_contratado_brl), `debentures_incentivadas` (por emissora) |

Razões, somas e percentuais por SQL, não de cabeça. Indicador que existe só para uma das duas: escreva "sem dado
comparável" e não troque por outro parecido. Em `pee_projetos` os acentos da tipologia estão gravados errado: filtre
por prefixo (`tipologia LIKE 'Ilumina%'`).

## 3. Entregue (as três seções são obrigatórias)

1. **Resposta direta** (2 a 3 frases): quem lidera cada pilar e qual das duas é a menos madura.
2. **Escopo**: empresas, CNPJs, segmento, ano, o que é dado da base e o que é declaração do relatório.
3. **Tabela de evidência**: indicador | unidade | empresa A | empresa B | ano | Fonte, com `[Fn]` em cada linha.
4. **Pontos fortes e fracos**: o positivo e o negativo de cada pilar, empresa por empresa, cada afirmação presa a um
   número da tabela. Sem número, é ressalva, não ponto forte.
5. **Grau de similaridade**: os desafios e a maturidade são equivalentes? Diga o critério antes do veredito (por
   exemplo, diferença abaixo de 20% em 4 dos 6 indicadores) e classifique em equivalentes, próximas ou distantes.
6. **Direcionamento estratégico**: 3 a 5 decisões para a menor ou menos madura, cada uma com o case da outra (o que
   ela fez e o número que alcançou) e o indicador que deve mudar. Não recomende o que a base não sustenta.
7. **Lacunas**: o que nenhuma das duas divulga ou não está na base (escopo 3, meta validada pelo SBTi, indicadores
   sociais de quadro próprio) e onde achar.
## 4. Relatório

Feche com `gerar_relatorio`, seguindo o roteiro **relatorio-energynexus** (carregue-o com a ferramenta skill): é ele
que tem os parâmetros da chamada e as regras das referências. O modelo fixa seis seções e a ferramenta não abre
outras, então os blocos acima entram nelas assim:

| Seção do modelo | O que vai nela |
|---|---|
| Sumário Executivo | o bloco 1 |
| Introdução | o escopo (bloco 2): empresas, CNPJs, segmento, ano |
| Dados e Metodologia | o que é dado da base e o que é declaração do relatório, a tabela de evidência (bloco 3) e o critério da similaridade |
| Resultados | **Pontos fortes e fracos** (bloco 4) e **Grau de similaridade** (bloco 5) |
| Discussão e Pontos de Atenção | o que limita a comparação (definição diferente, escopo diferente, indicador sem par) e as lacunas do bloco 7 |
| Conclusões e Recomendações | o **Direcionamento estratégico** (bloco 6), em lista numerada |

No `subtitulo` vão as duas empresas e o tema; no `periodo`, o ano ou o intervalo comparado. Cada fato leva a fonte
(tabela da base, ou documento, ano e página), que vira referência no PDF.

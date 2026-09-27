---
name: benchmark-distribuidoras
description: Roteiro de benchmark regulatório de distribuidoras de energia (DEC, FEC, limites, compensações, tarifa, PDD, P&D e eficiência). Use quando o usuário pedir para comparar distribuidoras entre si ou com os limites da ANEEL, avaliar qualidade do serviço ou montar quadro regulatório de uma concessão.
---

# Benchmark regulatório de distribuidoras

Prefira uma consulta SQL agregada por tabela, com todas as distribuidoras
no mesmo `WHERE cnpj IN (...)`.

## 1. Fixe o escopo comum (antes de consultar)

- **Entidades**: a distribuidora (concessão), não o grupo. Use `buscar_empresa` com o nome dado pelo usuário
  ("Neoenergia Coelba", "Enel SP", "Cemig D"). Se vier holding ou confiança aproximada, diga qual CNPJ usou.
- **Período**: o último ano fechado comum a todas (confira `meses = 12` em `dec_fec_distribuidora_anual`).
  Nunca compare 2025 de uma com 2024 de outra sem avisar.
- **Escopo**: indicadores apurados pela ANEEL por distribuidora; limites da tabela são médias ponderadas pelos
  consumidores calculadas pela plataforma, não o limite global oficial.

## 2. Levante (tabelas da base)

| Bloco | Tabela e colunas |
|---|---|
| Continuidade | `dec_fec_distribuidora_anual`: dec_horas, fec_interrupcoes, dec_limite_medio_ponderado_horas, fec_limite_medio_ponderado, consumidores_medios |
| Compensações | `compensacoes_continuidade`: SUM(valor) FILTER (indicador LIKE 'PGU%') por cnpj e ano (R$). Os 48 indicadores `QTU*` são quantidade de unidades compensadas: somar com os `PGU*` mistura reais com contagem (Cemig-D 2024: 131.360.837,88 sem filtro contra 128.836.221,88 certos) |
| Tarifa | `tarifas_distribuicao`: subgrupo='B1', classe='Residencial', subclasse='Residencial', modalidade='Convencional', posto='Não se aplica', detalhe='Não se aplica', base_tarifaria='Tarifa de Aplicação', vigência mais recente (tusd + te, R$/MWh, com a data). Só `subgrupo` e `classe` deixam 60 linhas por distribuidora, de 548,35 (Branca fora-ponta com SCEE) a 2.081,06 (Branca na ponta) — Equatorial PA em 01/01/2026 é 978,30. Variação entre tarifas não é o efeito médio do reajuste |
| Ranking da ANEEL | `ranking_continuidade`: posicao, dgc, porte por ano (235 linhas, 2021-2025). A posição é dentro do `porte` ("mais de 400 mil unidades consumidoras" ou "até 400 mil unidades consumidoras"): diga a posição, o total do mesmo porte e ano e o porte por extenso (Cemig-D em 2025: 31º de 33 entre as de mais de 400 mil), nunca a posição solta |
| Violação por conjunto | `continuidade_limites` + `continuidade_conjuntos`: DEC/FEC apurado contra o limite de cada conjunto, para contar quantos conjuntos violaram |
| Investimento regulatório | `pdd_investimentos`: SUM(planejado_brl), SUM(realizado_brl) por ano |
| Inovação | `ped_projetos` (custo_previsto_brl) e `pee_projetos` (custo_total_brl, energia_economizada_mwh) |
| Alavancagem do grupo | `kpis_financeiros` do grupo controlador (divida_liquida_ebitda) — ou a ferramenta `indicadores_financeiros`, que lê essa tabela. Marque a linha como grupo e não misture com a concessão |

## 3. Entregue

1. **Resposta direta** (2 a 3 frases): onde a distribuidora está pior ou melhor que os pares e os limites.
2. **Escopo**: distribuidoras e CNPJs, ano, o que é média ponderada e o que é oficial.
3. **Tabela de evidência**: uma linha por distribuidora; colunas DEC, limite DEC, DEC/limite, FEC, limite FEC,
   FEC/limite, compensações (R$ mi), e a coluna Fonte (tabela e ano). Razões calculadas por SQL, não de cabeça.
4. **Lacunas**: o que não está na base (limite global oficial por distribuidora, efeito médio do reajuste) e onde achar
   (resolução homologatória do reajuste). Ranking da ANEEL e violação por conjunto **estão** na base
   (`ranking_continuidade`, `continuidade_limites`, `continuidade_conjuntos`): consulte antes de declarar lacuna.

Se o usuário pedir documento para enviar, carregue o roteiro `relatorio-energynexus` e termine com `gerar_relatorio`.

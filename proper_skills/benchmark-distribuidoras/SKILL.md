---
name: benchmark-distribuidoras
description: Roteiro de benchmark regulatório de distribuidoras de energia (DEC, FEC, limites, compensações, tarifa, PDD, P&D e eficiência). Use quando o usuário pedir para comparar distribuidoras entre si ou com os limites da ANEEL, avaliar qualidade do serviço ou montar quadro regulatório de uma concessão.
---

# Benchmark regulatório de distribuidoras

Orçamento: até 8 chamadas de ferramenta. Prefira uma consulta SQL agregada por tabela, com todas as distribuidoras
no mesmo `WHERE cnpj IN (...)`. Se o orçamento acabar, entregue o que já foi confirmado e liste o resto em Lacunas.

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
| Compensações | `compensacoes_continuidade`: SUM(valor) por cnpj e ano (R$) |
| Tarifa | `tarifas_distribuicao`: subgrupo B1, classe residencial, vigência mais recente (tusd + te, R$/MWh). Variação entre tarifas não é o efeito médio do reajuste |
| Investimento regulatório | `pdd_investimentos`: SUM(planejado_brl), SUM(realizado_brl) por ano |
| Inovação | `ped_projetos` (custo_previsto_brl) e `pee_projetos` (custo_total_brl, energia_economizada_mwh) |
| Alavancagem do grupo | `indicadores_financeiros` do grupo controlador (dívida líquida/EBITDA), marcado como grupo |

## 3. Entregue

1. **Resposta direta** (2 a 3 frases): onde a distribuidora está pior ou melhor que os pares e os limites.
2. **Escopo**: distribuidoras e CNPJs, ano, o que é média ponderada e o que é oficial.
3. **Tabela de evidência**: uma linha por distribuidora; colunas DEC, limite DEC, DEC/limite, FEC, limite FEC,
   FEC/limite, compensações (R$ mi), e a coluna Fonte (tabela e ano). Razões calculadas por SQL, não de cabeça.
4. **Lacunas**: o que não está na base (limite global oficial, conjuntos com violação, efeito médio do reajuste,
   ranking ANEEL) e onde achar (ANEEL: ranking de continuidade; resolução homologatória do reajuste).

Se o usuário pedir documento para enviar, termine com `gerar_relatorio`.

# PLANO_FASE2 — Central DFP / Placar da Transição

> **Status: proposta, aguardando aprovação.** Nada será codificado antes do seu "ok".
> Este plano **adapta** o prompt da Fase 2 (escrito para uma versão antiga em Chainlit + Ollama + SQLite +
> Chroma) ao stack **real** deste repositório: LibreChat + DuckDB + `proper_mcps/` + `proper_skills/` +
> modelos vLLM/Bedrock. As funcionalidades e as regras de rastreabilidade são as mesmas; muda o "como".

## 0. Tradução do prompt para o repo atual

| Prompt antigo | Aqui |
|---|---|
| GUI Chainlit `app.py`, seletores na caixa de mensagem | **LibreChat** (não se altera o cliente — regra do `CLAUDE.md`). Telas viram **artefatos HTML/PDF** servidos em `/relatorios/`. Modo Descritiva/Conclusiva vira **preset/perfil** no `librechat.yaml`. |
| LLM Qwen via Ollama :11435 (GPU 19 GiB) | **vLLM `EnergyNexus` (`qwen3.8-27b`)** em `VLLM_BASE_URL` **ou** **Bedrock** `us.anthropic.claude-sonnet-5`. Sem GPU local, sem carregar modelo novo — a restrição de GPU do prompt não se aplica. |
| SQLite `armazenamento/coppezip.sqlite` | **DuckDB** `data/energynexus.duckdb` (52 tabelas, `catalogo`). |
| Chroma + BM25 | **`data/docs.duckdb`** (BM25 do DuckDB + embeddings `multilingual-e5-large`), já montado. |
| `coppezip/`, `coppezip/mcp_web` | `proper_mcps/{dados,docs,relatorio}` + servidores novos. |
| `research/FINDINGS-claude-sonnet-5.md §3.2` | existe em **`researches/FINDINGS-claude-sonnet-5.md §3.2`** — usado como gabarito. |
| `dados/catalogo_fontes.yaml` | tabela **`catalogo`** no DuckDB (origem de cada tabela) + `data/documentos.csv` (fontes de docs). Amplia-se registrando ali. |
| `scripts/smoke_test.py` (8 perguntas-ouro) | **`eval/regressao.py`** (`CASOS`) + `eval/chat.py`. |
| "64 testes verdes" | suíte atual **`proper_mcps/**/test_*.py`** continua verde; somam-se testes novos. |

## 1. Princípios (inegociáveis)

1. **Não tocar no LibreChat** (`api/ client/ packages/ config/`) além do tema. Comportamento do chat só por
   `librechat.yaml`, `proper_mcps/`, `proper_skills/`.
2. **Estrutura fixa, sem fallbacks de caminho.** Dados extraídos vão para **um caminho novo e fixo**:
   `data/placar.duckdb` (espelha o precedente de `data/docs.duckdb`). Nada de variável de ambiente para caminho.
3. **Rastreabilidade total.** Todo valor novo guarda `arquivo`+`pagina`+`trecho` (doc), ou `tabela`+`sql` (banco),
   ou `url` (web), com `confianca` e `metodo`, e aparece **citado** ([D#]/[B#]/[W#]) em toda saída.
4. **Separação de responsabilidades entre bancos:**
   - `energynexus.duckdb` — derivado de fontes públicas por `data/construir.py` (reconstruído do zero; **não** recebe
     tabelas extraídas, senão a reconstrução atômica as apagaria).
   - `docs.duckdb` — RAG (páginas/trechos/embeddings).
   - **`placar.duckdb` (novo)** — tudo que o LLM extrai e o que se deriva disso. As ferramentas MCP fazem `ATTACH`
     dos três (o `dados` já lê `energynexus.duckdb`; o `placar` lê `placar.duckdb` e faz `ATTACH energynexus.duckdb` p/ métricas híbridas).
5. **Mínimo e funcionando.** Reaproveitar o que existe (skill `avaliacao-climatica`, servidor `relatorio`,
   busca híbrida do `docs`). Nada de camada nova sem uso.

## 2. Arquitetura

```
docs.duckdb (páginas/trechos)
      │
      ▼  data/extrair_placar.py  (LLM + Pydantic, recupera páginas via busca híbrida)
placar.duckdb  ── esg_emissoes, esg_metas, esg_renovavel, esg_capex, esg_frameworks,
      │            esg_score_divulgacao, promessas, promessas_execucao,
      │            alertas_consistencia, diff_edicoes   (todas com colunas de fonte)
      │
      ├── proper_mcps/placar/server.py   → ferramentas do agente (consultar_placar, promessa_entrega,
      │                                     radar_consistencia, exposicao_carbono, mapa_expansao,
      │                                     grafo_societario, diff_relatorios)
      │        (faz ATTACH energynexus.duckdb READ_ONLY p/ receita, EBITDA, usinas, leilões, BNDES, societário)
      │
      └── proper_mcps/visual/server.py   → gera artefato HTML/PDF autocontido em .runtime/relatorios/
                                            (Plotly/Leaflet/vis-network inline) e devolve link /relatorios/…
proper_skills/  → roteiros que orquestram as ferramentas acima + relatorio/visual
librechat.yaml  → registra os servidores novos; perfis "Descritiva"/"Conclusiva"
```

- **Backend de LLM da extração** (`data/extrair_placar.py`): cliente OpenAI-compatível apontando para
  `VLLM_BASE_URL`/`VLLM_MODELO` por padrão (LLM canônico do projeto); flag `--backend bedrock`
  (`bedrock-runtime`, `us.anthropic.claude-sonnet-5`) para máquinas sem acesso ao vLLM (como esta). Sem modelo local novo.
- **Deploy (AgentCore).** Os servidores novos ficam em `proper_mcps/` e entram no **mesmo pacote** publicado no
  AgentCore (como `dados`/`docs`/`relatorio`). É preciso subir `placar.duckdb` ao bucket S3 junto de
  `energynexus.duckdb`/`docs.duckdb`. Em dev local, testam-se por stdio. *(Observação: o `librechat.yaml` atual
  aponta os MCP para a AWS; para testar os servidores novos localmente, ou se aponta de volta ao local, ou se
  republica no AgentCore. Detalhe operacional a alinhar quando chegarmos ao merge.)*

## 3. Esquema de dados — `placar.duckdb`

Colunas de fonte comuns a toda tabela extraída: `arquivo VARCHAR, pagina INTEGER, trecho VARCHAR,
confianca DOUBLE, metodo VARCHAR, extraido_em TIMESTAMP, modelo VARCHAR`.

- **`esg_emissoes`** (`cnpj, empresa, ano, escopo` ∈ {1,2,2_mercado,3}, `tco2e DOUBLE, intensidade DOUBLE,
  unidade_intensidade` + fonte). Normaliza para tCO2e.
- **`esg_metas`** (`cnpj, ano_relatorio, tipo` ∈ {net_zero,reducao_absoluta,reducao_intensidade}, `ano_alvo,
  escopo_coberto, valor_alvo, base_ano` + fonte).
- **`esg_renovavel`** (`cnpj, ano, pct_capacidade_renovavel, pct_geracao_renovavel` + fonte).
- **`esg_capex`** (`cnpj, ano, capex_total_brl, capex_verde_brl, definicao_verde` + fonte). É o CAPEX **reportado
  no documento** (distinto do `investimento_total_brl` da DFP; ambos entram, com rótulo).
- **`esg_frameworks`** (`cnpj, ano, framework` ∈ {GRI,SASB,TCFD,IFRS_S2,CDP}, `asseguracao_externa BOOLEAN,
  assegurador` + fonte).
- **`esg_score_divulgacao`** (`cnpj, ano, score DOUBLE, componentes JSON`) — **derivada** (não extraída):
  cobertura de escopos + meta + framework + asseguração.
- **`promessas`** (`cnpj, ano_promessa, tipo` ∈ {capex,reducao_emissao,obra,meta_renovavel}, `descricao,
  valor DOUBLE, unidade, prazo_ano` + fonte).
- **`promessas_execucao`** (`promessa_id, valor_realizado, unidade, pct_execucao, status` ∈
  {cumprida,parcial,atrasada,sem_dado}, `fonte_realizado_tipo` ∈ {dfp,doc,siga,ons}, `fonte_realizado_ref`).
- **`alertas_consistencia`** (`cnpj, ano, regra, severidade` ∈ {alta,media,baixa}, `explicacao,
  valor_afirmado, valor_oficial, evidencia_doc, evidencia_dado`).
- **`diff_edicoes`** (`cnpj, ano_a, ano_b, categoria` ∈ {risco,meta,tom}, `mudanca` ∈ {entrou,saiu,alterou},
  `texto_a, pagina_a, texto_b, pagina_b`).

Exposição a carbono, mapa de expansão e grafo societário **não** são tabelas novas: são **consultas/visões**
sobre `esg_emissoes` × `kpis_financeiros` e sobre `usinas/leiloes_geracao/bndes_operacoes/grupos_economicos/
participacoes_societarias/usinas_proprietarios`.

## 4. Extração (LLM + Pydantic) e validação

**Pipeline** `data/extrair_placar.py` (idempotente, incremental por `arquivo`+`bytes`, como o `indexar_docs.py`):
1. Para cada `(empresa, ano)` de `docs.duckdb`, e para cada grupo de métrica, recuperar **páginas candidatas** com
   a busca híbrida já existente (consultas fixas: "emissões escopo 1 2 3 tCO2e", "meta net zero neutralidade",
   "capacidade instalada renovável %", "investimentos CAPEX", "GRI SASB TCFD asseguração", …).
2. Enviar o **texto da página** (via `paginas.texto`, não só o trecho) ao LLM com **schema Pydantic** e instrução
   estrita: "extraia só o que está literalmente na página; devolva `trecho` literal e `pagina`; se não houver, `null`;
   nunca infira; unidades como no texto". Saída JSON validada pelo Pydantic.
3. **Normalização de unidades** (mil tCO2e → tCO2e; R$ mil/mi/bi → R$; %, x).
4. **Escrever** em `placar.duckdb` com as colunas de fonte e `confianca` (do modelo + heurística).

**Prompts de extração** (um por grupo: emissões, metas, renovável, capex, frameworks): cabeçalho comum com as
regras acima + schema JSON + 1–2 exemplos few-shot tirados de páginas reais já conferidas.

**Validação automática** `data/conferir_placar.py`:
- **"O valor aparece no trecho?"** — o número normalizado (tolerando formatação) tem de estar em `trecho`/`paginas.texto`
  da página citada; senão o registro é marcado `confianca=0` e listado no relatório de conferência.
- **Gabarito**: comparação com `researches/FINDINGS-claude-sonnet-5.md §3.2` (escopos 1/2/3 por empresa, metas Net
  Zero, CAPEX 2024). Relatório Markdown com acertos/erros/faltas por empresa.

**Métricas híbridas** (visões em `placar.duckdb` com `ATTACH energynexus.duckdb`):
`tco2e/receita_liquida`, `capex/receita`, `capex_por_mw` (CAPEX × `capacidade_por_grupo`/`usinas`), e
`score_divulgacao`. Cada métrica cita as duas fontes (B# da DFP/SIGA + D# do relatório).

## 5. As 8 funcionalidades (adaptadas)

1. **Placar da Transição** — fundação (§3–4). Ferramenta `consultar_placar(empresa|ano|metrica)`; skill
   `placar-transicao`; **tela**: `visual` gera `ranking.html` (Plotly, célula com fonte clicável → tooltip D#/B#).
2. **Promessa × Entrega** — extrai `promessas` (compromissos com prazo/valor) e casa com o realizado
   (DFP/DFC, relatório seguinte, SIGA/ONS) em `promessas_execucao`; `%` e status, com as **duas citações lado a lado**.
   Ferramenta `promessa_entrega(empresa)`; skill `promessa-entrega`.
3. **Radar de consistência (anti-greenwashing)** — motor de regras (`proper_mcps/placar/regras.py`), começa com 4:
   (a) "% renovável" × usinas por fonte no SIGA/ONS; (b) "CAPEX recorde" × série do DFC; (c) "expansão em transmissão"
   × leilões vencidos + BNDES; (d) "meta Net Zero" × tendência de escopo 1. Cada alerta: severidade, explicação e as
   duas evidências. Ferramenta `radar_consistencia`; fácil somar regras (uma classe por regra).
4. **Diff entre edições** — compara relatório/FRE de anos diferentes da mesma empresa (riscos que entram/saem, metas
   alteradas, tom). `diff_relatorios(empresa, ano_a, ano_b)` → `diff_edicoes`, com citação das duas edições.
5. **Exposição a preço de carbono** — visão `escopo1 (+2) × preço R$/t` (ajustável) contra lucro/EBITDA
   (`kpis_financeiros`). Ferramenta `exposicao_carbono(preco_por_t, escopos)`; ranking; **fórmulas visíveis**.
   Ajuste do preço na **tela** (input HTML que recalcula no cliente com dados embutidos).
6. **Mapa da expansão** — por grupo: `usinas` (construção/operação por fonte/UF) + `leiloes_geracao` +
   `transmissao_*` + `bndes_operacoes`, resolvendo grupo por `grupos_economicos`/apelidos/`usinas_proprietarios`.
   Ferramenta `mapa_expansao(grupo)`; **tela**: `mapa.html` (Leaflet + tabelas, com fonte).
7. **Briefing de uma página** — comando/skill `dossie-empresa`: junta indicadores, gráficos, placar,
   promessas×entregas e alertas em **um PDF de uma página** (gerador do `relatorio` estendido p/ layout 1-página +
   gráfico), citações em nota de rodapé.
8. **Grafo societário** — holding → controladas → usinas/ativos → indicadores, de `participacoes_societarias` +
   `composicao_societaria` + `usinas_proprietarios` + cadastro. Ferramenta `grafo_societario(grupo)`; **tela**:
   `grafo.html` (vis-network inline), referência por nó.

**Modo Descritiva/Conclusiva** (regra: escolhido **pelo usuário**, nunca pelo modelo): dois **presets/perfis** no
`librechat.yaml` (`energynexus-analista-descritiva` e `-conclusiva`), com a diferença de instrução no `promptPrefix`.
*(Limitação: o "seletor na caixa de mensagem" do Chainlit não existe no LibreChat sem alterar o cliente; o
equivalente é o seletor de perfil/preset. Registrado nos riscos.)*

## 6. "Telas" como artefatos (sem alterar o cliente)

Servidor novo `proper_mcps/visual/server.py`: cada ferramenta monta um **HTML autocontido** (bibliotecas inline,
dados embutidos) em `.runtime/relatorios/` e devolve o link `/relatorios/<arquivo>.html` (mesmo mecanismo do
`relatorio`). Plotly (ranking/exposição), Leaflet (mapa), vis-network (grafo). Toda célula/nó/ponto carrega a
fonte (tooltip/rodapé D#/B#/W#). Validação de citação análoga à do `relatorio` (recusa número sem fonte).

## 7. Testes e aceite

- **pytest** (padrão `proper_mcps/**/test_*.py`): extração (schema, normalização de unidade), validação
  ("valor na página"), cada regra do radar, métricas híbridas, e cada ferramenta MCP nova. Os testes atuais
  continuam verdes.
- **Gabarito**: teste que compara a extração com `FINDINGS §3.2` (escopos por empresa dentro de tolerância).
- **Regressão** (`eval/regressao.py`): novos `CASOS`-ouro, um por funcionalidade (ex.: "maior intensidade de
  emissões entre X, Y, Z", "status da promessa de CAPEX da Neoenergia", "alertas de consistência da <empresa>").
- **E2E Playwright** (nova pasta `eval/e2e/`, dep adicionada só ali): abre os artefatos `/relatorios/*.html`
  (ranking, mapa, grafo, dossiê) e verifica que renderizam e que **cada número/célula tem fonte**; opcionalmente
  dirige o chat do LibreChat para disparar uma ferramenta e abrir o artefato.
- **Nenhum número sem fonte** em nenhuma saída (ferramenta, artefato, relatório).

## 8. Lacunas conhecidas (adaptadas)

- **Cobertura dos relatórios (conferida em 26/09/2026)**: 14 relatórios indexados, de 12 empresas — Alupar 2023,
  Auren 2024, Celesc 2025, Cemig 2025 (inventário GEE e TCFD), Copel 2023, CPFL 2024 e 2025, EDP 2024, Eneva 2025,
  Engie 2025, Equatorial 2024, ISA 2024 e 2025. O placar cobre só essas empresas-ano e as ferramentas dizem isso.
- **Documento truncado**: o problema não é a Equatorial (o `equatorial_rs2024.pdf` tem 184 páginas, completo; não há
  edição 2025 na base). É o **CPFL 2024**, com **15 páginas** — parcial. A edição 2025 (163 páginas) está completa e
  é a que o placar usa. Para fechar: rebaixar o CPFL 2024 e o Equatorial 2025 de outra origem (RI da empresa),
  registrar em `data/documentos.csv` e reindexar `docs.duckdb`. **Não feito nesta fase.**
- **CAPEX ausente**: o "147 empresas-ano sem CAPEX / `capex_detalhe`/`DS_CONTA`" é do projeto antigo (SQLite).
  **Auditado em 26/09/2026** (`kpis_financeiros`, escopo consolidado, 2020-2025): 313 empresa-anos, **nenhum sem
  valor** de `investimento_total_brl` (cobertura de 100% em todos os anos). Em **30 deles (9,6%)** o valor é
  **zero** — holdings e SPEs que não reportam a linha de investimento na DFP (Rio Paranapanema, Multiner, Proman,
  Celeo Redes, CELGPAR...). A plataforma mostra zero, não estima. Nada a mudar em `data/construir.py`; a lacuna do
  projeto antigo não existe nesta base.

## 9. Worktrees e ordem de execução

- **`wt-esg`** (fundação): `placar.duckdb`, `extrair_placar.py`, `conferir_placar.py`, prompts/Pydantic, tabelas
  ESG, `consultar_placar`, score, métricas híbridas. **Bloqueia as demais.**
- **`wt-analises`**: promessa×entrega, radar de consistência (regras), diff de edições, exposição a carbono.
- **`wt-visual`**: `proper_mcps/visual` (ranking/mapa/grafo/dossiê), skills, presets Descritiva/Conclusiva, E2E.
- Cada worktree: módulo isolado + testes verdes. **Merge completo de volta na `main`**, suíte unificada
  (pytest + `eval/regressao.py`) verde, e sistema integrado testado no chat. Sem `push` sem seu pedido.

## 10. Riscos

| Risco | Mitigação |
|---|---|
| Alucinação/erro na extração | validação "valor na página" + `confianca` + gabarito §3.2; `confianca=0` não entra em ranking. |
| vLLM (`xingu`) inacessível de fora | extração com `--backend bedrock` (Claude) nesta máquina; vLLM no servidor. |
| Poucos docs (48) e Equatorial truncada | cobertura explícita por empresa/ano; lacunas citadas; rebaixar Equatorial. |
| Sem GUI custom (LibreChat) | telas como artefatos HTML/PDF; modo por perfil. Registrado como limitação. |
| Paridade no AgentCore | subir `placar.duckdb` ao S3 e republicar os MCP; testar local por stdio antes. |
| Token/credencial expira (Cognito 24h, STS) | fora do escopo da Fase 2; já documentado. |
| Números não determinísticos entre modelos | tolerância nos testes de gabarito; fixar `temperature=0` na extração. |

## 11. O que preciso de você

1. **Aprovação** deste plano (ou ajustes).
2. **Backend de extração**: uso Bedrock (Claude) nesta máquina, certo? (o vLLM `xingu` não responde daqui).
3. **Escopo do MVP**: topo recomendado = **§1 Placar** + **§3 Radar** + **§5 Exposição a carbono** (dão o maior
   impacto sobre a base já pronta). §6/§8 (mapa/grafo) e §7 (dossiê) na sequência. Confirma essa ordem?

---

## 12. Estado da execução (26/09/2026)

**Escopo entregue** (MVP aprovado: Placar + Radar + Exposição a carbono, com as telas):

| Entrega | Onde |
|---|---|
| Extração ESG com fonte por página | `data/extrair_placar.py` → `data/placar.duckdb` (5 tabelas) |
| Conferência contra o gabarito §3.2 | `data/conferir_placar.py` → `.runtime/relatorios/conferencia_placar.md` |
| Placar, ranking, radar e exposição a carbono | `proper_mcps/placar/server.py` (4 ferramentas) |
| Telas HTML (ranking, radar, carbono) | mesmas, `tela_*`, servidas em `/relatorios/` |
| Roteiros | `proper_skills/avaliacao-climatica` (atualizado) e `proper_skills/modo-conclusivo` (novo) |
| Testes | `proper_mcps/placar/test_placar.py`, `test_extracao.py`, `eval/e2e/telas.js`, 6 casos novos em `eval/regressao.py` |

**Decisões que mudaram em relação ao plano** (e por quê):

1. **As telas ficaram no `energynexus-placar`**, não num servidor `visual` novo: o MVP não tem mapa nem grafo, e as
   telas reusam direto as funções do placar (uma camada a menos, nada de importar um `server.py` de outro).
2. **Sem Plotly/Leaflet/vis-network**: o gráfico é de barras em HTML e CSS, com o tema do chat. "Autocontido" de
   verdade — sem CDN e sem jogar 3,5 MB de JavaScript no repositório — e o E2E consegue ler cada barra pelo DOM.
3. **Modo Descritiva/Conclusiva**: virou regra no `promptPrefix` (padrão descritivo) mais o roteiro
   `modo-conclusivo`, que **o usuário** carrega. Dois perfis no `librechat.yaml` exigiriam duplicar o prompt
   inteiro (YAML não concatena âncoras), e a escolha continua sendo do usuário, nunca do modelo.
4. **Concordância entre duas leituras** na extração (não estava no plano): tabela achatada em PDF é ambígua e o
   modelo escolhia colunas diferentes a cada leitura (ISA 2025 p.94 chegou a dar 12,3 Mt de escopo 3 numa
   transmissora). Agora o valor só entra se duas leituras da mesma página concordarem — e o trecho citado precisa
   ter rótulo, não só algarismos.

**Fora desta entrega**: promessa × entrega (§2), diff entre edições (§4), mapa da expansão (§6), briefing de uma
página (§7) e grafo societário (§8); publicação do `energynexus-placar` no AgentCore (precisa do `placar.duckdb` no
S3 — os outros três MCP já rodam lá).

**Resultado medido (26/09/2026, tudo rodado nesta máquina):**

| Verificação | Resultado |
|---|---|
| `.runtime/venv/bin/python -m pytest proper_mcps -q` | **78 testes verdes** (ferramentas, telas, extração) |
| `node eval/e2e/telas.js` | **10 checagens verdes** (barras, fonte em toda linha, dobrar o preço dobra a exposição) |
| `eval/regressao.py` (casos novos) | **6/6**, de 21 a 90 s por pergunta |
| `data/conferir_placar.py` | 7/18 batem com o gabarito §3.2; 4 divergem (edições diferentes), 6 faltam (empresa sem relatório na base), 1 rejeitado na checagem de fonte |
| Base extraída (`placar.duckdb`) | emissões 43/48 com fonte confirmada (8 empresas), metas 19/26 (5), renovável 6/13 (5), CAPEX 11/15 (6), frameworks 39/56 (10) |
| Pergunta real no chat | "tela da exposição a R$ 150/t" → 63 s, `exposicao_carbono` + `tela_carbono`, link e as duas maiores com arquivo, página e a conta |

**Limitações registradas** (além das lacunas do §8):

- **"% renovável declarado × SIGA" quase não dispara**: o relatório é da holding e o SIGA atribui a usina ao CNPJ
  que participa dela (a térmica da EDP, por exemplo, não está sob o CNPJ do relatório). E quando a empresa só
  divulga "% da **geração**", não dá para confrontar com a **capacidade** do SIGA — o radar registra em
  `nao_comparaveis` em vez de inventar um alerta.
- **Extração não é determinística**: o Claude no Bedrock não aceita `temperature` fixa (o parâmetro foi depreciado
  para o Sonnet 5), então duas rodadas podem achar coisas diferentes numa tabela ambígua. É justamente o que a
  concordância de duas leituras filtra — ao custo de perder valor real de vez em quando (a CPFL só entrou com 3
  páginas candidatas; com 6 as duas leituras não fecharam).
- **Escopo faltando**: Auren e Engie entram na exposição a carbono só com o escopo 1, porque o relatório indexado
  não traz o 2. A ferramenta devolve `escopos_sem_valor` e a tela mostra a ressalva na linha.

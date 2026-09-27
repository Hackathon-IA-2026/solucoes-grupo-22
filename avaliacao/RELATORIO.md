# Opus 5 (Bedrock) × Qwen local (vLLM, RTX 5090) nas ferramentas do EnergyNexus

Comparação da **taxa de acertos** de dois modelos operando exatamente o mesmo conjunto de ferramentas do
agente `energynexus-analista` do LibreChat, sobre 76 perguntas com gabarito conferido no próprio repositório.

## Resumo

| | Opus 5 (Bedrock) | Qwen3.8-27B-INT4 (vLLM, RTX 5090) |
|---|---|---|
| Perguntas respondidas | 76 de 76 (1 rodada) | 74 de 76 (2 rodadas, 148 execuções) |
| **Taxa de acerto** | **88% (67/76)** | **81% (120/148)** |
| Alucinação | 7% (5/76) | 7% (10/148) |
| Latência mediana | 58,5 s | 45,6 s |
| Custo da corrida | US$ 49,00 (US$ 0,645 por pergunta) | 3,63 h de GPU ≈ US$ 3,26 (US$ 0,021 por execução) |

Os sete pontos de diferença saem de três lugares: o Qwen erra mais número financeiro estruturado (75% contra 92%),
não entregou nenhum dos dois relatórios em PDF (duas tentativas terminaram sem o artefato e duas estouraram o
contexto do servidor) e é menos consistente na citação de documento e página (79% contra 86%). Em compensação empata na
busca web e nas contagens do índice, e custa ~30× menos por resposta. **As duas categorias fracas são as mesmas
nos dois modelos**: "não está na base" (58% e 54%) — ou seja, quase metade das vezes qualquer um dos dois tenta
responder o que a base não tem — e é aí, não na aritmética, que está o risco de usar o agente sem revisão.

## 1. O que foi medido

Cada pergunta é respondida por um laço de ferramentas que reproduz o do LibreChat:

- **as mesmas 19 ferramentas**: 17 de MCP (`energynexus-dados` e `energynexus-docs` pela ponte
  `proper_mcps/agentcore/ponte.py` no AgentCore; `energynexus-placar` e `energynexus-relatorio` locais por stdio),
  mais `web_search` (Serper `/search` + `scrape` + rerank Jina) e `skill`;
- **o mesmo prompt de sistema**: o `promptPrefix` do perfil, o bloco de instruções que o
  `MCPManager.formatInstructionsForContext` injeta (`serverInstructions: true`), o contexto de citação da busca web
  e o catálogo `## Available Skills` com as 7 skills de `proper_skills/` (18.540 caracteres, sha `81d1835e`);
- **os mesmos limites**: `recursionLimit` 300 (dois passos por chamada de ferramenta, como no LibreChat),
  `maxOutputTokens` 32.000, `maxContextTokens` 262.144;
- nomes de ferramenta com o mesmo sufixo `_mcp_<servidor>` que o LibreChat monta com `Constants.mcp_delimiter`.

As 76 perguntas cobrem as categorias pedidas: (a) factual com citação de arquivo e página, (b) números do placar
ESG, (c) contagens e agregações do índice (mais uma faixa de financeiro estruturado vindo da CVM), (d) busca web,
(e) perguntas cuja resposta correta é "não está na base" — é a medida de alucinação — e (f) geração de relatório
em PDF. Os gabaritos saíram de `data/conferir_placar.py`, de `data/documentos.csv`, dos índices DuckDB (abertos em
`read_only`) e da leitura da página citada; `conferir_conjunto.py` reconfirma as 26 citações no índice antes de
qualquer execução (76/76 válidas, 26/26 citações confirmadas).

A correção é por regra, sem juiz de modelo: comparação numérica com tolerância e leitura de número em formato
brasileiro com sufixo de escala ("R$ 2,3 bi"), conferência de citação (o documento é identificado e a página
citada contém de fato o valor, verificado em `docs.duckdb`), verificação de "não sei" para a categoria (e) e,
para (f), chamada bem-sucedida de `gerar_relatorio` mais o bloco `:::artifact` na resposta.

## 2. Os dois modelos

| | Opus 5 | Qwen local |
|---|---|---|
| Identificador | `us.anthropic.claude-opus-5` (Bedrock Converse, `us-east-1`) | `RedHatAI/Qwen3.8-27B-INT4` servido como `qwen3.8-27b` |
| Acesso | confirmado com chamada mínima antes da corrida, em `us-east-1` e `us-west-2` | vLLM em `xingu`, uma RTX 5090 |
| Contexto | 1M no modelo; a avaliação limita em 262.144 para igualar ao perfil | 262.144 (`--max-model-len`) |
| Saída máxima | 32.000 | 32.000 |
| Amostragem | nenhum parâmetro: `temperature` é *deprecated* nos Claude novos do Bedrock e a chamada é recusada se enviado | `temperature` 0,0 |

O Qwen escolhido é o mais forte que cabia na restrição: 27B com quantização INT4 (W4A16), servido em **uma** RTX
5090 de 32 GiB, operando em 262.144 tokens de contexto — dentro da faixa de 250 mil a 1 milhão pedida, na ponta de
baixo. Ver a seção 5 para por que não foi possível subir um servidor novo em `tocantins` e por que este é o
melhor Qwen disponível na máquina.

### Configuração de GPU e vLLM

```
vllm serve RedHatAI/Qwen3.8-27B-INT4 --host 0.0.0.0 --port 8001 --served-model-name qwen3.8-27b
  --tensor-parallel-size 1 --gpu-memory-utilization 0.93 --kv-cache-dtype fp8
  --attention-backend TRITON_ATTN --max-num-seqs 16 --limit-mm-per-prompt '{"image": 0, "video": 0}'
  --enable-auto-tool-choice --tool-call-parser qwen3_coder --reasoning-parser qwen3
  --max-model-len 262144
```

GPU: NVIDIA GeForce RTX 5090, 32.607 MiB no total, **31.334 MiB ocupados** (743 MiB livres) — o modelo INT4 mais o
cache KV em fp8 em 262 mil tokens praticamente enchem a placa. Um nó só para o vLLM (`xingu`), mais `kolyma`, que
era a escritora do placar; nenhuma A100 e no máximo dois nós, como pedido.

<!-- MEDIDA:INICIO -->

**Contexto efetivo medido** (agulha no palheiro: o dado pedido fica enterrado no meio do prompt, então a tabela separa "aceitou o prompt" de "usou o prompt"):

| Tokens de prompt | Achou a agulha | Segundos | Prefill (tok/s) | Saída (tok/s) |
|---|---|---|---|---|
| 3.245 | sim | 2.1 | 1565 | 51.1 |
| 50.768 | sim | 19.1 | 2664 | 4.6 |
| 158.443 | sim | 93.7 | 1692 | 1.2 |
| 198.009 | sim | 126.9 | 1560 | 0.9 |
| 205.966 | sim | 111.1 | 1854 | 0.8 |
| 207.572 | sim | 100.2 | 2073 | 0.9 |
| 261.373 | sim | 167.4 | 1562 | 0.8 |

Geração curta (prompt de poucos tokens): 85.6 tokens de saída por segundo (600 tokens em 7.0 s).

<!-- MEDIDA:FIM -->

O contexto de 262.144 tokens é **usado**, não só aceito: a agulha foi encontrada com 261.373 tokens de prompt, a
1.500 tokens de prefill por segundo. Em uma sondagem anterior, com 253.489 tokens, o modelo não achou a agulha uma
vez — um único ponto, mas suficiente para não prometer recuperação perfeita no topo da janela. O preço do contexto
longo é a vazão: 85,6 tokens de saída por segundo em prompt curto contra menos de 1 acima de 200 mil tokens.

## 3. Resultados

<!-- TABELAS:INICIO -->

### Taxa de acerto por categoria

| Categoria | opus5 | qwen |
|---|---|---|
| (a) factual com citação (docs) | 86% (12/14) | 79% (22/28) |
| (b) placar ESG | 100% (18/18) | 92% (33/36) |
| (c) contagens e agregações | 91% (10/11) | 100% (20/20) +2 s/resp. |
| (c') financeiro estruturado | 92% (11/12) | 75% (18/24) |
| (d) busca web | 100% (7/7) | 100% (14/14) |
| (e) não está na base | 58% (7/12) | 54% (13/24) |
| (f) relatório em PDF | 100% (2/2) | 0% (0/2) +2 s/resp. |
| **Total** | **88% (67/76)** | **81% (120/148) +4 s/resp.** |

### Alucinação

| Medida | opus5 | qwen |
|---|---|---|
| Admitiu a ausência (categoria e) | 58% (7/12) | 58% (14/24) |
| Alucinação (qualquer categoria) | 7% (5/76) | 7% (10/148) |
| Citou página que não confirma o valor | 0/26 | 0/52 |

### Latência e consumo por pergunta

| Medida | opus5 | qwen |
|---|---|---|
| Execuções contadas | 76 | 152 |
| Perguntas distintas respondidas | 76 | 74 |
| Falhas de execução (não contam como erro) | 0 | 4 |
| Latência mediana (s) | 58.5 | 45.6 |
| Latência p90 (s) | 103 | 193 |
| Chamadas de ferramenta (mediana) | 4.0 | 3.0 |
| Tokens de entrada (mediana) | 75632 | 47032 |
| Tokens de saída (mediana) | 1813 | 1394 |

### Custo

| Modelo | Execuções | Tokens entrada | Tokens saída | Custo total | Custo por pergunta |
|---|---|---|---|---|---|
| opus5 (`us.anthropic.claude-opus-5`) | 76 | 8.769.130 | 206.120 | US$ 49.00 | US$ 0.645 |
| qwen (`qwen3.8-27b`) | 152 | 16.458.050 | 477.804 | US$ 3.26 (3.63 h de GPU) | US$ 0.021 |

### Variância entre rodadas

| Modelo | Perguntas com 2 rodadas | Rodadas discordantes | Estabilidade |
|---|---|---|---|
| opus5 | 0 | — | — |
| qwen | 74 | 4 | 95% |

### Onde os modelos discordam (11 perguntas)

| Pergunta | Categoria | opus5 | qwen |
|---|---|---|---|
| `ag10` Quantas distribuidoras entraram no ranking de continuidade da ANEEL de… | agregacao | erro | ok |
| `au01` Qual foi a receita liquida da Light em 2018?… | ausente | ok | erro |
| `au04` Qual foi o indice de rotatividade (turnover) dos empregados da Energis… | ausente | erro | ok |
| `au09` Qual foi a receita da Iberdrola, a controladora da Neoenergia, em 2025… | ausente | ok | erro |
| `au12` Qual e a tarifa de gas natural canalizado cobrada pelas distribuidoras… | ausente | ok | erro |
| `fd13` Qual foi a receita liquida consolidada da Cemig em 2025 conforme o doc… | factual_docs | ok | erro |
| `fi03` Compare a alavancagem (divida liquida sobre EBITDA) de 2025 da Equator… | financeiro | ok | erro |
| `fi08` Qual a RAP ativa das concessoes em nome da propria Taesa (CNPJ 07.859.… | financeiro | ok | erro |
| `pl13` Quanto a Eneva emitiu de escopo 1 em 2025 e quanto isso variou frente … | placar_esg | ok | erro |
| `pl18` Em que ano a EDP promete ser Net Zero e qual a meta de producao renova… | placar_esg | ok | erro |
| `re02` Gere um relatorio em PDF sobre a alavancagem das transmissoras e distr… | relatorio | ok | erro |

<!-- TABELAS:FIM -->

## 4. Custo

As 76 perguntas custaram **US$ 49,00** no Opus 5 — 8.769.130 tokens de entrada e 206.120 de saída, ou
**US$ 0,645 por pergunta**. O Qwen consumiu 3,63 horas de parede de uma RTX 5090 para as 152 execuções das duas
rodadas, o que a US$ 0,90 a hora dá **US$ 3,26**, ou **US$ 0,021 por execução**: cerca de **30 vezes mais barato
por resposta**, com 7 pontos percentuais menos de acerto.

Os preços de Opus 5 usados na tabela acima são os publicados pela Anthropic para o modelo
(US$ 5,00 por milhão de tokens de entrada e US$ 25,00 por milhão de saída). O Bedrock é operado pela AWS com
tabela própria: o número deve ser relido contra a página de preços do Bedrock antes de virar previsão de gasto.
Não houve cache de prompt em nenhum dos lados, então o custo é o pior caso — o prompt de sistema de ~18,5 mil
caracteres e o histórico de ferramentas foram reenviados a cada passo.

O custo do Qwen é o tempo de GPU: as horas de parede da corrida multiplicadas por uma hora de RTX 5090, tomada em
US$ 0,90 (faixa de mercado em nuvem; a máquina do projeto é própria, então o custo marginal real é energia).
A comparação é grosseira de propósito: uma GPU ocupada por uma corrida serve outras em paralelo (`--max-num-seqs
16`), enquanto o token do Bedrock é pago por uso.

## 5. Limitações do método

Onde a avaliação **não** reproduz o LibreChat:

1. **Servidor vLLM pré-existente, não instalado por esta avaliação.** A instrução era criar um venv novo no disco
   local de `tocantins` e subir o vLLM lá. Na hora da avaliação `tocantins` tinha 11,3 GiB livres na GPU, e nenhum
   Qwen com 250 mil tokens de contexto caberia nisso (o menor candidato, Qwen2.5-7B-1M AWQ, pede ~12,2 GiB com KV
   em fp8 a 262 mil). Em vez de entregar um Qwen pequeno demais ou nenhum, a avaliação usou o servidor que já
   estava no ar em `xingu` com um Qwen bem mais forte no contexto exigido. Consequência: os parâmetros do vLLM são
   os que o servidor já tinha (registrados acima), não escolhidos aqui, e o servidor atendia outras cargas.
2. **Correção por regra, não por juiz.** Um número certo dentro da tolerância conta como acerto mesmo que o
   raciocínio esteja errado, e uma resposta certa escrita de forma inesperada pode ser contada como erro. É o
   preço de ter correção reprodutível e sem custo de modelo.
3. **A citação é aceita pelo nome humano do documento.** O `promptPrefix` pede que o agente cite documento e
   página, não o caminho do arquivo. Por isso `arquivo_citado` aceita "Relatório de Sustentabilidade 2024 da
   Cemig, p. 139" como identificação do documento `sustentabilidade/cemig/2024/cemig_ras2024.pdf`, exigindo
   companhia mais ano; a página citada ainda é conferida no índice. A regra foi afrouxada **depois** das corridas,
   ao ver que respostas certas e rastreáveis estavam sendo reprovadas, e aplicada aos dois modelos pelo
   `recorrigir.py` — a mesma régua para os dois, mas não a régua com que a primeira corrida foi pontuada.
4. **Um gabarito estava errado e foi corrigido depois das corridas.** O escopo 1 da ISA Energia em 2024 (`pl08`)
   estava como 14.455 tCO2e, que é a coluna de **2022** da tabela "Emissões brutas"; a coluna de 2024 traz
   11.940,55. Os dois modelos foram repontuados com o valor certo. A extração do placar terminou durante a
   avaliação e confirmou duas outras divergências conhecidas (Engie 2024 escopo 2 = 0 por I-RECs; ISA 2024
   escopo 1/2 com colunas trocadas no gabarito antigo) — nenhuma delas virou pergunta.
5. **Sem interface, sem streaming, sem memória de conversa.** Cada pergunta é uma conversa nova de um turno; o
   LibreChat carrega histórico, arquivos anexados e artefatos na tela. Também não há cache de prompt, que o
   LibreChat usa.
6. **A busca web consome cota real do Serper** e a web muda: as 7 perguntas da categoria (d) foram escolhidas com
   resposta estável, mas não são reprodutíveis com garantia.
7. **Uma rodada para Opus 5, duas para o Qwen.** As credenciais da AWS expiraram no meio da primeira corrida do
   Opus 5 (`ExpiredTokenException` depois de 6 perguntas) e as 70 restantes foram gravadas como falha em segundos.
   Com credenciais novas a corrida foi retomada — `rodar.py` pula pergunta que já tem arquivo — e completou as
   76 perguntas em **uma** rodada, dividida em três processos por categoria para caber na janela da credencial.
   Os 146 arquivos perdidos para o token vencido estão separados em `opus5_token_expirado/` e **não** entram em
   nenhuma conta: não são erro do modelo, são pergunta não respondida. Consequências: a variância entre rodadas só
   pode ser lida para o Qwen, e a taxa do Opus 5 vem de uma amostra de uma execução por pergunta.
8. **Duas perguntas o Qwen não conseguiu responder por limite de contexto**, nas duas rodadas: `ag03` e `re01`
   acumularam ~230 mil tokens de entrada e, somados aos 32 mil de saída pedidos, passaram dos 262.144 do servidor
   (HTTP 400 do vLLM). Contam como falha de execução, não como resposta errada — e são exatamente o custo de
   operar na ponta de baixo da faixa de contexto pedida.
9. **`data/placar.duckdb` estava sendo escrito** por outra extração durante a montagem do conjunto, então nenhum
   gabarito saiu dele: as perguntas de emissões foram ancoradas no texto da página em `docs.duckdb`, que é
   estável. A extração terminou depois e os valores conferidos batem com os do conjunto.

## 6. O que ficou fora

- A segunda rodada do Opus 5 (variância entre rodadas medida só no Qwen).
- Um vLLM instalado por esta avaliação em `tocantins`, pelo motivo da limitação 1.
- Comparação com o `qwen3.8-27b` do endpoint "EnergyNexus" do `librechat.yaml` em contexto maior que 262.144: é o
  teto do servidor.
- Medição de cache de prompt e de custo com cache, que mudaria bastante a conta do Opus 5.

## 7. Como reproduzir

Ver [README.md](README.md). Os resultados por pergunta e rodada, os logs e as medidas ficam fora do git, em
`AVALIACAO_SAIDA` (`/local/$USER/avaliacao-opus5-qwen`): um JSON por execução com a resposta, a trilha de
ferramentas, os tokens, o tempo e a correção.

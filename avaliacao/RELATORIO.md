# Opus 5 (Bedrock) × Qwen local (vLLM, RTX 5090) nas ferramentas do EnergyNexus

Comparação da **taxa de acertos** de dois modelos operando exatamente o mesmo conjunto de ferramentas do
agente `energynexus-analista` do LibreChat, sobre 76 perguntas com gabarito conferido no próprio repositório.

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
<!-- MEDIDA:FIM -->

## 3. Resultados

<!-- TABELAS:INICIO -->
<!-- TABELAS:FIM -->

## 4. Custo

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
   Opus 5 (`ExpiredTokenException` após 6 execuções) e a corrida foi retomada com credenciais novas, em uma
   rodada só, para caber no prazo. Os 146 arquivos gravados com falha de token estão separados em
   `opus5_token_expirado/` e **não** entram em nenhuma conta: não são erro do modelo, são pergunta não respondida.
   A variância entre rodadas, portanto, só pode ser lida para o Qwen.
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

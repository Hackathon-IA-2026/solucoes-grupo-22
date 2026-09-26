# EnergyNexus

Chat de inteligência do setor elétrico brasileiro. É o LibreChat (esta pasta, v0.8.7 com o tema do EnergyNexus) mais as
nossas peças: o modelo (o nosso Qwen3.8-27B no vLLM ou o Claude pelo Amazon Bedrock) consulta dados públicos (CVM,
ANEEL, ONS, BNDES, ANBIMA, Banco Central) e relatórios das empresas pelas ferramentas MCP e responde com a fonte de
cada número.

## Demo

Sem link público: o chat roda nos servidores do IMPA e é aberto por túnel SSH (veja "Rodar").

## Tecnologias utilizadas

- Linguagem: Python (ferramentas, dados e testes), JavaScript/Node (LibreChat), Bash (scripts)
- Framework(s): LibreChat v0.8.7, MCP (Model Context Protocol), vLLM
- Banco de dados: DuckDB (dados do setor e índice dos relatórios), MongoDB e Meilisearch (usuários e conversas do chat)
- Modelos: Qwen3.8-27B INT4 (próprio, no vLLM) e Claude Sonnet 5 (Amazon Bedrock); embeddings Amazon Titan Text Embeddings v2 (Bedrock)
- APIs / Serviços externos: dados abertos da CVM, ANEEL, ONS, BNDES, ANBIMA e Banco Central; Amazon Bedrock; Serper e
  Jina (busca web, opcional)

## O que é nosso

| Pasta ou arquivo | O que é |
|---|---|
| `librechat.yaml` | configuração do chat: modelos, perfis do analista (prompt), ferramentas MCP e busca web |
| `.env.example` | modelo do `.env` (portas, segredos, endereço do vLLM, região do Bedrock) |
| `instalar.sh`, `iniciar.sh`, `parar.sh` | instalar uma vez, subir e parar o chat |
| `vllm.sh` | sobe o modelo próprio numa máquina com GPU |
| `proper_mcps/` | ferramentas MCP: `dados` (banco DuckDB), `docs` (busca nos relatórios em PDF; `busca.py` atende a aba Busca), `relatorio` (Markdown e Word) |
| `proper_skills/` | roteiros do analista: benchmark de distribuidoras, ficha de crédito, investimento na transição, avaliação climática |
| `data/` | coleta (`baixar.py`), montagem do banco (`construir.py`), índice dos PDFs (`indexar_docs_titan.py`, em uso; `indexar_docs.py` é a versão com o e5 local), dados da aba Painel (`exportar_painel.py`), dados da aba Timeline (`linha_do_tempo.py`) e documentação das tabelas (`DADOS.md`); os dados em si ficam aqui, fora do git |
| `researches/` | pesquisa de fontes de dados e dicionário de dados |
| `eval/` | cliente do chat (`chat.py`) e regressão com perguntas de resposta conhecida (`regressao.py`) |
| `client/src/style.css` | o tema do EnergyNexus |
| abas Painel, Busca e Grafo | `client/src/components/EnergyNexus/`, `client/src/components/Nav/EnergyNexusNavButtons.tsx`, as rotas `/painel`, `/busca` e `/grafo` em `client/src/routes/index.tsx`, e `api/server/routes/painel.js` e `busca.js` (registradas em `api/server/index.js` e `routes/index.js`) |
| aba Timeline | `client/src/components/Timeline/`: evolução de cada empresa (eventos por ano, impacto, indicadores e fontes), trajetórias estratégicas e gráficos; registrada em `client/src/routes/index.tsx`, `client/src/hooks/Nav/useSideNavLinks.ts` e na chave `com_ui_timeline` das traduções |

O resto (`api/`, `client/`, `packages/`, `config/`...) é o LibreChat. Mudou algo em `client/`? Recompile com
`PATH=$PWD/.runtime/bin:$PATH npm run frontend` (o Node do sistema pode ser antigo demais). O README original está em `README.librechat.md`.

## Pré-requisitos

- Linux com `python3` (com `venv`), `curl`, `git` e `openssl`. Node, MongoDB e Meilisearch o `instalar.sh` baixa
  sozinho para `.runtime/`.
- Para o modelo próprio: GPU NVIDIA de 32 GB ou mais. Sem GPU, use o Claude pelo Bedrock ou aponte para um vLLM em
  outra máquina.
- Internet na primeira vez (bibliotecas, binários e, no `vllm.sh`, cerca de 19 GB de pesos).

Nada é fixo de usuário ou de máquina: tudo fica dentro da pasta onde o repositório foi clonado (`.runtime/` para
binários, bancos do chat, logs e vLLM; `data/` para os dados) e as escolhas locais (portas, chaves, endereço do modelo)
ficam no `.env`.

## Rodar

```bash
./instalar.sh     # uma vez: .env, Node, MongoDB, Meilisearch (em .runtime/), npm e o Python das ferramentas
./iniciar.sh      # sobe o chat em http://localhost:3080
./parar.sh
./vllm.sh         # numa máquina com GPU (32 GB ou mais): instala o vLLM, baixa os pesos e serve o modelo
```

De outra máquina, abra um túnel: `ssh -N -L 3080:127.0.0.1:3080 <máquina>`.

### Modelo

- **Próprio (vLLM):** `./vllm.sh` instala o vLLM em `.runtime/vllm`, baixa os pesos para `.runtime/hf` e serve
  `VLLM_MODELO` na porta `VLLM_PORTA`, exigindo a chave `VLLM_API_KEY`. Se ele rodar em outra máquina, ajuste
  `VLLM_BASE_URL` no `.env` do chat; a chave tem que ser a mesma nas duas. As opções do vLLM (contexto de 256 mil
  tokens, cache em fp8, atenção pelo Triton, 16 conversas simultâneas) foram ajustadas para o Qwen3.8-27B INT4 numa
  RTX 5090; em outra GPU pode ser preciso mudá-las no script.
- **Amazon Bedrock (Claude):** ponha as credenciais da AWS em `~/.aws/credentials` e reinicie o chat. No seletor, use
  o perfil "EnergyNexus Analista (Claude)". A região está em `BEDROCK_AWS_DEFAULT_REGION`.

## Dados

Os dados não vão para o git. Coloque em `data/`:

| Caminho | Como obter |
|---|---|
| `data/raw/`, `data/parquet/` | `python data/baixar.py` (fontes oficiais) e o Drive do projeto (`EnergyNexus-dados-brutos`) |
| `data/energynexus.duckdb` | `.runtime/venv/bin/python data/construir.py`, depois `data/documentar.py` |
| `data/modelos/multilingual-e5-large/` | o modelo `intfloat/multilingual-e5-large` do Hugging Face, copiado sem links simbólicos |
| `data/docs_titan.duckdb` | `.runtime/venv/bin/python data/indexar_docs_titan.py`, com as credenciais da AWS em `~/.aws/credentials` (o índice em uso; `data/indexar_docs.py` monta a versão com o e5 local em `data/docs.duckdb`, que o chat não usa). PDFs em `data/raw/sustentabilidade/<empresa>/<ano>/` e `data/raw/financeiro/<empresa>/pdfs/<ano>/`, organizados por `data/organizar.py` e descritos em `data/documentos.csv` |
| `data/painel.json` | `.runtime/venv/bin/python data/exportar_painel.py`, depois do `construir.py` |

Os bancos prontos também estão no Drive, em `bancos/`. A aba Timeline lê os parágrafos dos relatórios da tabela `blocos`
do `docs.duckdb`: um índice feito antes dela precisa ser refeito com `data/indexar_docs.py` (os embeddings são
reaproveitados). O `iniciar.sh` monta a linha do tempo de cada empresa (`data/linha_do_tempo.py`) a cada início.

### Abas Painel, Busca e Grafo

Ao lado do chat (ícones na barra lateral), só para usuários logados:

- **Painel** (`/painel`): dashboards das tabelas do banco que o analista consulta (indicadores financeiros, DEC/FEC,
  CMO, EAR, curtailment, capacidade, usinas, leilões, PDD, BNDES, debêntures): um cartão com tendência para cada medida
  numérica, evolução no tempo (até 8 empresas comparadas), ranking e as linhas da base com download em CSV. O filtro de
  empresa acha pelo nome, apelido, ticker ou CNPJ. Cores das séries em `--painel-1..8` do `style.css`. Lê
  `data/painel.json`, relido a cada acesso: depois de reconstruir o banco, basta rodar `data/exportar_painel.py` de novo.
- **Busca** (`/busca`): responde "em que página está isso?" nos PDFs indexados, com o trecho, a imagem da página e o
  PDF. Usa o mesmo índice e modelo do `energynexus-docs` (`data/docs_titan.duckdb`, Titan pelo Bedrock); o `iniciar.sh` sobe
  `proper_mcps/docs/busca.py` em `127.0.0.1:BUSCA_PORTA` e o LibreChat repassa `/api/busca`.
- **Grafo** (`/grafo`, `?empresa=<CNPJ só com dígitos>`): grafo de conhecimento de uma empresa, trazido do EnergyNexus
  (Chainlit). Empresa → categoria (cada base do painel com dados dela, e os documentos por área) → indicadores (as
  medidas do painel, por período, com a mesma regra de agregação) e referências (a base, ou o PDF, agrupados por tipo).
  A empresa é o CNPJ, que liga as bases do `painel.json` entre si e aos documentos de `/api/busca/resumo`; não há
  serviço novo, o grafo é montado no navegador (`grafo/dados.ts`). Sem o serviço de busca, sai só com as bases.
  Arraste para navegar, roda do mouse para zoom, duplo clique recolhe ou expande, clique abre os dados e a fonte (com o
  PDF, pela rota da Busca). As cores vêm do tema (claro e escuro) e o CSS só usa classes `kg-`.

## Testes

```bash
.runtime/venv/bin/python -m pytest proper_mcps data -q   # ferramentas e linha do tempo, contra os bancos de data/
eval/usuario.sh                                       # uma vez: usuário de teste no LibreChat
python3 eval/chat.py "Qual foi a receita líquida da Taesa em 2025?"
python3 eval/regressao.py                             # 27 perguntas; --perfil energynexus-analista-claude para o Claude
```

## Licença

Este projeto está sob a licença MIT — veja o arquivo [LICENSE](./LICENSE). O LibreChat, que é a base desta pasta,
também é MIT: [LICENSE.librechat](./LICENSE.librechat).

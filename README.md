# EnergyNexus

Chat de inteligência do setor elétrico brasileiro. É o LibreChat (esta pasta, v0.8.7 com o tema e a logo do
EnergyNexus) mais as nossas peças: o modelo (o nosso Qwen3.8-27B no vLLM ou o Claude pelo Amazon Bedrock) consulta
dados públicos (CVM, ANEEL, ONS, BNDES, ANBIMA, Banco Central) e relatórios das empresas pelas ferramentas MCP,
responde com a fonte de cada número e entrega o relatório final em PDF, no modelo do Energy Nexus, aberto ao lado do
chat.

## Demo

Sem link público: o chat roda nos servidores do IMPA e é aberto por túnel SSH (veja "Rodar").

## Tecnologias utilizadas

- Linguagem: Python (ferramentas, dados e testes), JavaScript/Node (LibreChat), Bash (scripts), LaTeX (relatório)
- Framework(s): LibreChat v0.8.7, MCP (Model Context Protocol), vLLM
- Banco de dados: DuckDB (dados do setor e índice dos relatórios), MongoDB e Meilisearch (usuários e conversas do chat)
- Modelos: Qwen3.8-27B INT4 (próprio, no vLLM) e Claude Sonnet 5 (Amazon Bedrock); embeddings Amazon Titan Text Embeddings v2 (Bedrock)
- APIs / Serviços externos: dados abertos da CVM, ANEEL, ONS, BNDES, ANBIMA e Banco Central; Amazon Bedrock; Serper e
  Jina (busca web, opcional)

## O que é nosso

| Pasta ou arquivo | O que é |
|---|---|
| `librechat.yaml` | configuração do chat: modelos, perfis do analista (prompt), ferramentas MCP e busca web |
| `.env.example` | modelo do `.env` (nome do app, portas, segredos, endereço do vLLM, região do Bedrock) |
| `instalar.sh`, `iniciar.sh`, `parar.sh` | instalar uma vez, subir e parar o chat |
| `vllm.sh` | sobe o modelo próprio numa máquina com GPU |
| `proper_mcps/` | ferramentas MCP: `dados` (banco DuckDB), `docs` (busca nos relatórios em PDF; `busca.py` atende a aba Busca), `relatorio` (relatório final em PDF, com o modelo LaTeX em `relatorio/modelo/`), `placar` (Placar da Transição, radar de consistência, exposição a carbono e as telas em HTML) |
| `proper_skills/` | roteiros do analista: relatório final (`relatorio-energynexus`), benchmark de distribuidoras, ficha de crédito, investimento na transição, avaliação climática e o modo conclusivo |
| `data/` | coleta (`baixar.py`), montagem do banco (`construir.py`), índice dos PDFs (`indexar_docs_titan.py`, em uso; `indexar_docs.py` é a versão com o e5 local), extração do placar ESG (`extrair_placar.py`, `conferir_placar.py`), dados da aba Painel (`exportar_painel.py`), dados da aba Timeline (`linha_do_tempo.py`) e documentação das tabelas (`DADOS.md`); os dados em si ficam aqui, fora do git |
| `researches/` | pesquisa de fontes de dados e dicionário de dados |
| `eval/` | cliente do chat (`chat.py`), regressão com perguntas de resposta conhecida (`regressao.py`) e o E2E das telas (`e2e/telas.js`) |
| `client/src/style.css` | o tema do EnergyNexus |
| `client/public/assets/` (logo e ícones), `client/index.html`, `client/vite.config.ts` | a logo e o nome do EnergyNexus |
| `client/src/utils/artifacts.ts`, `client/src/components/Artifacts/ArtifactTabs.tsx` e `DownloadArtifact.tsx` | o painel lateral do LibreChat mostra o relatório em PDF e baixa o arquivo |
| abas Painel, Busca e Grafo | `client/src/components/Coppezip/`, `client/src/components/Nav/CoppezipNavButtons.tsx`, as rotas `/painel`, `/busca` e `/grafo` em `client/src/routes/index.tsx`, e `api/server/routes/painel.js` e `busca.js` (registradas em `api/server/index.js` e `routes/index.js`) |
| aba Timeline | `client/src/components/Timeline/`: evolução de cada empresa (eventos por ano, impacto, indicadores e fontes), trajetórias estratégicas e gráficos; registrada em `client/src/routes/index.tsx`, `client/src/hooks/Nav/useSideNavLinks.ts` e na chave `com_ui_timeline` das traduções |

O resto (`api/`, `client/`, `packages/`, `config/`...) é o LibreChat. Mudou algo em `client/`? Recompile com
`PATH=$PWD/.runtime/bin:$PATH npm run frontend` (o Node do sistema pode ser antigo demais). O README original está em `README.librechat.md`.

## Placar da Transição

O que a empresa **diz** no relatório, ao lado do que os dados oficiais **mostram**. `data/extrair_placar.py` lê os
relatórios já indexados e monta `data/placar.duckdb` com emissões por escopo, metas climáticas, % renovável, CAPEX e
frameworks de divulgação — cada valor com arquivo, página e o trecho literal. Dois filtros mantêm a base limpa: o
valor só entra se **aparecer na página citada** e se **duas leituras do modelo concordarem** (tabela achatada em PDF
é ambígua e o modelo escolhe colunas diferentes a cada leitura). `data/conferir_placar.py` compara a extração com o
gabarito conferido à mão.

No chat, as ferramentas de `energynexus-placar`:

| Ferramenta | O que faz |
|---|---|
| `consultar_placar` | o placar de uma empresa, com métricas híbridas (tCO2e por R$ mi de receita, CAPEX/receita) |
| `placar_ranking` | ranking entre empresas: score de divulgação, intensidade, escopo 1+2, % renovável |
| `radar_consistencia` | alertas de divergência entre o relatório e o dado oficial (SIGA/CVM), com as duas evidências |
| `exposicao_carbono` | emissões × preço de carbono contra EBITDA e lucro, com a fórmula |
| `tela_ranking`, `tela_radar`, `tela_carbono` | a mesma informação como página HTML (gráfico, tabela e a fonte de cada número), servida em `/relatorios/` |

A resposta é **descritiva** por padrão; parecer e recomendação só quando o usuário pedir (roteiro `modo-conclusivo`).

## Relatório final

Quando o usuário pede um relatório (ou memorando, ficha, nota para comitê), o modelo carrega o roteiro
`proper_skills/relatorio-energynexus/SKILL.md` (as instruções do modelo oficial: seis seções fixas, fonte de cada fato,
distinção entre fato e análise, referências em BibTeX), levanta os dados e chama `gerar_relatorio`. A ferramenta confere
a estrutura e as citações, preenche `proper_mcps/relatorio/modelo/main.tex` e `referencias.bib` (o template, alterado
só nos campos e no conteúdo), compila com o pdflatex do TinyTeX (`.runtime/tinytex`) e grava o PDF e o fonte LaTeX em
`.runtime/relatorios`, servidos em `/relatorios/`. A resposta traz um bloco `:::artifact` do tipo `application/pdf`:
o PDF abre grande no painel à direita, com o botão de baixar.

## Pré-requisitos

- Linux com `python3` (com `venv`), `curl`, `git` e `openssl`. Node, MongoDB, Meilisearch e o TinyTeX o `instalar.sh`
  baixa sozinho para `.runtime/`.
- Para o modelo próprio: GPU NVIDIA de 32 GB ou mais. Sem GPU, use o Claude pelo Bedrock ou aponte para um vLLM em
  outra máquina.
- Internet na primeira vez (bibliotecas, binários, pacotes do LaTeX e, no `vllm.sh`, cerca de 19 GB de pesos).

Nada é fixo de usuário ou de máquina: tudo fica dentro da pasta onde o repositório foi clonado (`.runtime/` para
binários, bancos do chat, logs, relatórios e vLLM; `data/` para os dados) e as escolhas locais (portas, chaves, endereço
do modelo) ficam no `.env`.

## Rodar

```bash
./instalar.sh     # uma vez: .env, Node, MongoDB, Meilisearch, TinyTeX (em .runtime/), npm e o Python das ferramentas
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
| `data/raw/`, `data/parquet/` | `python data/baixar.py` (fontes oficiais) e o Drive do projeto (`CoppeZIP-dados-brutos`) |
| `data/coppezip.duckdb` | `.runtime/venv/bin/python data/construir.py`, depois `data/documentar.py` |
| `data/modelos/multilingual-e5-large/` | o modelo `intfloat/multilingual-e5-large` do Hugging Face, copiado sem links simbólicos |
| `data/docs_titan.duckdb` | `.runtime/venv/bin/python data/indexar_docs_titan.py`, com as credenciais da AWS em `~/.aws/credentials` (o índice em uso; `data/indexar_docs.py` monta a versão com o e5 local em `data/docs.duckdb`, que o chat não usa). PDFs em `data/raw/sustentabilidade/<empresa>/<ano>/` e `data/raw/financeiro/<empresa>/pdfs/<ano>/`, organizados por `data/organizar.py` e descritos em `data/documentos.csv` |
| `data/painel.json` | `.runtime/venv/bin/python data/exportar_painel.py`, depois do `construir.py` |
| `data/placar.duckdb` | `.runtime/venv/bin/python data/extrair_placar.py` (lê as páginas de `data/docs.duckdb` e extrai pelo Bedrock; confira com `data/conferir_placar.py`) |

Os bancos prontos também estão no Drive, em `bancos/`; o banco guarda o nome antigo (`coppezip.duckdb`), o mesmo do
Drive. A aba Timeline lê os parágrafos dos relatórios da tabela `blocos`
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
- **Grafo** (`/grafo`, `?empresa=<CNPJ só com dígitos>`): grafo de conhecimento de uma empresa, trazido do CoppeZIP
  (Chainlit). Empresa → categoria (cada base do painel com dados dela, e os documentos por área) → indicadores (as
  medidas do painel, por período, com a mesma regra de agregação) e referências (a base, ou o PDF, agrupados por tipo).
  A empresa é o CNPJ, que liga as bases do `painel.json` entre si e aos documentos de `/api/busca/resumo`; não há
  serviço novo, o grafo é montado no navegador (`grafo/dados.ts`). Sem o serviço de busca, sai só com as bases.
  Arraste para navegar, roda do mouse para zoom, duplo clique recolhe ou expande, clique abre os dados e a fonte (com o
  PDF, pela rota da Busca). As cores vêm do tema (claro e escuro) e o CSS só usa classes `kg-`.

## Testes

```bash
.runtime/venv/bin/python -m pytest proper_mcps data -q   # ferramentas (relatório: TinyTeX) e linha do tempo
eval/usuario.sh                                       # uma vez: usuário de teste no LibreChat
python3 eval/chat.py "Qual foi a receita líquida da Taesa em 2025?"
python3 eval/regressao.py                             # perguntas de resposta conhecida; --perfil energynexus-analista-claude para o Claude
node eval/e2e/telas.js                                # abre as telas do placar no navegador e confere fonte e recálculo
```

## Licença

Este projeto está sob a licença MIT — veja o arquivo [LICENSE](./LICENSE). O LibreChat, que é a base desta pasta,
também é MIT: [LICENSE.librechat](./LICENSE.librechat).

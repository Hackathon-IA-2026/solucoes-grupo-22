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
- Modelos: Qwen3.8-27B INT4 (próprio, no vLLM) e Claude Sonnet 5 (Amazon Bedrock); embeddings multilingual-e5-large
- APIs / Serviços externos: dados abertos da CVM, ANEEL, ONS, BNDES, ANBIMA e Banco Central; Amazon Bedrock; Serper e
  Jina (busca web, opcional)

## O que é nosso

| Pasta ou arquivo | O que é |
|---|---|
| `librechat.yaml` | configuração do chat: modelos, perfis do analista (prompt), ferramentas MCP e busca web |
| `.env.example` | modelo do `.env` (nome do app, portas, segredos, endereço do vLLM, região do Bedrock) |
| `instalar.sh`, `iniciar.sh`, `parar.sh` | instalar uma vez, subir e parar o chat |
| `vllm.sh` | sobe o modelo próprio numa máquina com GPU |
| `proper_mcps/` | ferramentas MCP: `dados` (banco DuckDB), `docs` (busca nos relatórios em PDF), `relatorio` (relatório final em PDF, com o modelo LaTeX em `relatorio/modelo/`) |
| `proper_skills/` | roteiros do analista: relatório final (`relatorio-energynexus`), benchmark de distribuidoras, ficha de crédito, investimento na transição, avaliação climática |
| `data/` | coleta (`baixar.py`), montagem do banco (`construir.py`), índice dos PDFs (`indexar_docs.py`) e documentação das tabelas (`DADOS.md`); os dados em si ficam aqui, fora do git |
| `researches/` | pesquisa de fontes de dados e dicionário de dados |
| `eval/` | cliente do chat (`chat.py`) e regressão com perguntas de resposta conhecida (`regressao.py`) |
| `client/src/style.css` | o tema do EnergyNexus |
| `client/public/assets/` (logo e ícones), `client/index.html`, `client/vite.config.ts` | a logo e o nome do EnergyNexus |
| `client/src/utils/artifacts.ts`, `client/src/components/Artifacts/ArtifactTabs.tsx` e `DownloadArtifact.tsx` | o painel lateral do LibreChat mostra o relatório em PDF e baixa o arquivo |

O resto (`api/`, `client/`, `packages/`, `config/`...) é o LibreChat. O README original está em `README.librechat.md`.

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
| `data/docs.duckdb` | `.runtime/venv/bin/python data/indexar_docs.py` (PDFs em `data/raw/pdfs_esg/`) |

Os bancos prontos também estão no Drive, em `bancos/`. O banco guarda o nome antigo (`coppezip.duckdb`), o mesmo do
Drive.

## Testes

```bash
.runtime/venv/bin/python -m pytest proper_mcps -q     # ferramentas, contra o banco de data/ (e o relatório, com o TinyTeX)
eval/usuario.sh                                       # uma vez: usuário de teste no LibreChat
python3 eval/chat.py "Qual foi a receita líquida da Taesa em 2025?"
python3 eval/regressao.py                             # 27 perguntas; --perfil energynexus-analista-claude para o Claude
```

## Licença

Este projeto está sob a licença MIT — veja o arquivo [LICENSE](./LICENSE). O LibreChat, que é a base desta pasta,
também é MIT: [LICENSE.librechat](./LICENSE.librechat).

# CLAUDE.md

Guia para agentes que trabalham neste repositório. Responda e escreva em português do Brasil.

## O que é

CoppeZIP: chat de inteligência do setor elétrico. A raiz é o LibreChat v0.8.7 (no LibreChat mudamos só o tema,
`client/src/style.css`, e as abas Painel, Busca, Grafo e Timeline, registradas em `client/src/routes/index.tsx`,
`client/src/hooks/Nav/useSideNavLinks.ts` e nas traduções). Tudo o que é nosso está em:

- `librechat.yaml`: modelos (vLLM `CoppeZIP` e `bedrock`), perfis do analista com o prompt (âncora `&prompt`,
  reaproveitada pelo perfil do Claude), servidores MCP e busca web;
- `.env.example`: portas (inclusive `BUSCA_PORTA`), segredos, endereço do vLLM, região do Bedrock (o `.env` real nunca
  vai para o git);
- `instalar.sh`, `iniciar.sh`, `parar.sh`, `vllm.sh`;
- `proper_mcps/` (dados, docs, relatorio), `proper_skills/`, `data/`, `researches/`, `eval/`;
- `data/linha_do_tempo.py`: biblioteca que monta os dados da aba Timeline (eventos, trajetórias e gráficos) do
  `coppezip.duckdb` e do `docs_titan.duckdb`, **na hora**, para a empresa e o período que a pessoa escolhe; quem a chama
  é o serviço da Busca (`/timeline_empresas` e `/timeline`, repassados pela rota `/api/busca`). Nada é gerado de
  antemão. As páginas de relatório de cada tema saem de duas buscas somadas: BM25 nos parágrafos (`blocos`) e cosseno
  entre o vetor da consulta do tema (tabela `temas`, gravada pelo `indexar_docs_titan.py`) e os vetores dos `trechos`.

## Regras

- **Estrutura fixa, sem fallbacks.** Os caminhos saem da raiz do repositório: `data/coppezip.duckdb`,
  `data/docs_titan.duckdb` (índice dos PDFs em uso, Titan), `data/docs.duckdb` (versão e5, sem uso), `data/modelos/`, `data/raw/`, `.runtime/`. Não crie variáveis de ambiente para caminho nem
  valores padrão alternativos; o que é configurável (portas, chaves, endereço do modelo) fica no `.env`.
- **Mínimo e funcionando.** Não deixe código que não foi testado nem arquivos sem uso. Prefira mudar o que existe a
  criar camadas novas.
- **Não mexa no código do LibreChat** (`api/`, `client/`, `packages/`, `config/`) além do tema e das abas Painel,
  Busca, Grafo e Timeline. Comportamento do chat se muda pelo `librechat.yaml`. Mudou `client/`?
  `PATH=$PWD/.runtime/bin:$PATH npm run frontend` (com o Node do sistema o build falha depois de apagar
  `packages/data-provider/dist`).
- **Nunca vão para o git:** `.env`, `.runtime/`, dados (`data/raw`, `data/parquet`, `data/modelos`, `data/*.duckdb`,
  `data/painel.json`), chaves, senhas.
- **Commits:** mensagem em português no estilo `dados: ...`, `mcp: ...`, `chat: ...`. Autor: o usuário do repositório.
  Não acrescente `Co-Authored-By` nem outra atribuição de IA.
- Pergunta do usuário não é pedido de mudança: responda sem implementar.

## Como testar

```bash
.runtime/venv/bin/python -m pytest proper_mcps data -q   # ferramentas MCP e linha do tempo, contra os bancos de data/
./iniciar.sh && eval/usuario.sh                          # chat no ar e usuário de teste (uma vez)
python3 eval/chat.py "Qual foi a receita líquida da Taesa em 2025?"          # modelo padrão (vLLM)
python3 eval/chat.py --perfil coppezip-analista-claude "a mesma pergunta"     # Claude pelo Bedrock
python3 eval/regressao.py                                # 27 perguntas com resposta conhecida
.runtime/venv/bin/python eval/recuperacao.py             # busca nos relatórios: pares de eval/pares_relatorios.csv
```

Mudou o banco (`data/construir.py` ou `data/indexar_docs_titan.py`)? Rode os testes das ferramentas, a regressão e
`data/exportar_painel.py`. Mudou as consultas dos temas (`TEMAS`) ou o modelo de embedding? Regrave os vetores dos temas
(`.runtime/venv/bin/python data/indexar_docs_titan.py --temas`) e rode o `eval/recuperacao.py` antes e depois, para saber
se melhorou. Mudou o prompt ou o `librechat.yaml`? Reinicie (`./parar.sh && ./iniciar.sh`) e rode a regressão.

## Onde mexer

| Quero... | Arquivo |
|---|---|
| nova base de dados | `data/baixar.py` (coleta), `data/construir.py` (tabela e entrada no catálogo), teste em `proper_mcps/dados/test_server.py`, depois `data/documentar.py` |
| nova ferramenta | `proper_mcps/<servidor>/server.py` e registro em `mcpServers` do `librechat.yaml` |
| novo roteiro do analista | `proper_skills/<nome>/SKILL.md` |
| regra de resposta | `promptPrefix` do perfil `coppezip-analista` no `librechat.yaml` |
| novo caso de regressão | `CASOS` em `eval/regressao.py`, com o valor conferido na fonte |
| nova tabela na aba Painel | `CONJUNTOS` em `data/exportar_painel.py` |
| aba Busca | `proper_mcps/docs/busca.py` (serviço) e `client/src/components/Coppezip/BuscaView.tsx` (tela) |
| aba Grafo | `client/src/components/Coppezip/grafo/dados.ts` (nós a partir do `painel.json` e dos documentos), `modelo.ts` (layout), `GraphView.tsx` e `grafo.css` (tela); página em `GrafoView.tsx` |
| aba Timeline | dados em `data/linha_do_tempo.py` (temas, eventos, trajetórias; teste em `data/test_linha_do_tempo.py`), rotas em `proper_mcps/docs/busca.py`, tela em `client/src/components/Timeline/` (depois `npm run frontend`) |
| medir a busca nos relatórios | pares conferidos à mão em `eval/pares_relatorios.csv`, medida em `eval/recuperacao.py` |

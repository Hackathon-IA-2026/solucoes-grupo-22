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
- `proper_mcps/` (dados, docs, relatorio, placar), `proper_skills/`, `data/`, `researches/`, `eval/`;
- `data/linha_do_tempo.py`: os dados da aba Timeline (eventos, trajetórias e gráficos de cada empresa), gerados dos dois
  bancos em `.runtime/linha_do_tempo/` pelo `iniciar.sh` e servidos em `/linha_do_tempo/`.

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
python3 eval/regressao.py                                # 34 perguntas com resposta conhecida
node eval/e2e/telas.js                                   # telas do placar no navegador (fonte em cada número)
```

Mudou o banco (`data/construir.py` ou `data/indexar_docs.py`)? Rode os testes das ferramentas, a regressão e
`data/exportar_painel.py`; a linha do tempo se refaz no próximo `./iniciar.sh` (ou com
`.runtime/venv/bin/python data/linha_do_tempo.py`). Mudou o prompt ou o `librechat.yaml`? Reinicie
(`./parar.sh && ./iniciar.sh`) e rode a regressão. Mudou a extração do placar (`data/extrair_placar.py`)? Rode
`data/conferir_placar.py` (gabarito §3.2) além dos testes.

## Onde mexer

| Quero... | Arquivo |
|---|---|
| nova base de dados | `data/baixar.py` (coleta), `data/construir.py` (tabela e entrada no catálogo), teste em `proper_mcps/dados/test_server.py`, depois `data/documentar.py` |
| nova ferramenta | `proper_mcps/<servidor>/server.py` e registro em `mcpServers` do `librechat.yaml` |
| novo roteiro do analista | `proper_skills/<nome>/SKILL.md` |
| novo dado ESG no placar | grupo (schema Pydantic + instrução) em `data/extrair_placar.py`, gabarito em `data/conferir_placar.py`, teste em `proper_mcps/placar/` |
| nova regra do radar de consistência | `radar_consistencia` em `proper_mcps/placar/server.py` (todo alerta com as duas evidências) |
| nova tela (HTML) | seção "telas" de `proper_mcps/placar/server.py`; confira com `node eval/e2e/telas.js` |
| regra de resposta | `promptPrefix` do perfil `coppezip-analista` no `librechat.yaml` |
| novo caso de regressão | `CASOS` em `eval/regressao.py`, com o valor conferido na fonte |
| nova tabela na aba Painel | `CONJUNTOS` em `data/exportar_painel.py` |
| aba Busca | `proper_mcps/docs/busca.py` (serviço) e `client/src/components/Coppezip/BuscaView.tsx` (tela) |
| aba Grafo | `client/src/components/Coppezip/grafo/dados.ts` (nós a partir do `painel.json` e dos documentos), `modelo.ts` (layout), `GraphView.tsx` e `grafo.css` (tela); página em `GrafoView.tsx` |
| aba Timeline | dados em `data/linha_do_tempo.py` (temas, eventos, trajetórias; teste em `data/test_linha_do_tempo.py`), tela em `client/src/components/Timeline/` (depois `npm run frontend`) |

# CLAUDE.md

Guia para agentes que trabalham neste repositório. Responda e escreva em português do Brasil.

## O que é

CoppeZIP: chat de inteligência do setor elétrico. A raiz é o LibreChat v0.8.7 (o único arquivo do LibreChat que
mudamos é `client/src/style.css`, o tema). Tudo o que é nosso está em:

- `librechat.yaml`: modelos (vLLM `CoppeZIP` e `bedrock`), perfis do analista com o prompt (âncora `&prompt`,
  reaproveitada pelo perfil do Claude), servidores MCP e busca web;
- `.env.example`: portas, segredos, endereço do vLLM, região do Bedrock (o `.env` real nunca vai para o git);
- `instalar.sh`, `iniciar.sh`, `parar.sh`, `vllm.sh`;
- `proper_mcps/` (dados, docs, relatorio), `proper_skills/`, `data/`, `researches/`, `eval/`.

## Regras

- **Estrutura fixa, sem fallbacks.** Os caminhos saem da raiz do repositório: `data/coppezip.duckdb`,
  `data/docs.duckdb`, `data/modelos/`, `data/raw/`, `.runtime/`. Não crie variáveis de ambiente para caminho nem
  valores padrão alternativos; o que é configurável (portas, chaves, endereço do modelo) fica no `.env`.
- **Mínimo e funcionando.** Não deixe código que não foi testado nem arquivos sem uso. Prefira mudar o que existe a
  criar camadas novas.
- **Não mexa no código do LibreChat** (`api/`, `client/`, `packages/`, `config/`) além do tema. Comportamento do chat
  se muda pelo `librechat.yaml`.
- **Nunca vão para o git:** `.env`, `.runtime/`, dados (`data/raw`, `data/parquet`, `data/modelos`, `data/*.duckdb`),
  chaves, senhas.
- **Commits:** mensagem em português no estilo `dados: ...`, `mcp: ...`, `chat: ...`. Autor: o usuário do repositório.
  Não acrescente `Co-Authored-By` nem outra atribuição de IA.
- Pergunta do usuário não é pedido de mudança: responda sem implementar.

## Como testar

```bash
.runtime/venv/bin/python -m pytest proper_mcps -q        # ferramentas MCP, contra o banco de data/
./iniciar.sh && eval/usuario.sh                          # chat no ar e usuário de teste (uma vez)
python3 eval/chat.py "Qual foi a receita líquida da Taesa em 2025?"          # modelo padrão (vLLM)
python3 eval/chat.py --perfil coppezip-analista-claude "a mesma pergunta"     # Claude pelo Bedrock
python3 eval/regressao.py                                # 27 perguntas com resposta conhecida
```

Mudou o banco (`data/construir.py`)? Rode os testes das ferramentas e a regressão. Mudou o prompt ou o
`librechat.yaml`? Reinicie (`./parar.sh && ./iniciar.sh`) e rode a regressão.

## Onde mexer

| Quero... | Arquivo |
|---|---|
| nova base de dados | `data/baixar.py` (coleta), `data/construir.py` (tabela e entrada no catálogo), teste em `proper_mcps/dados/test_server.py`, depois `data/documentar.py` |
| nova ferramenta | `proper_mcps/<servidor>/server.py` e registro em `mcpServers` do `librechat.yaml` |
| novo roteiro do analista | `proper_skills/<nome>/SKILL.md` |
| regra de resposta | `promptPrefix` do perfil `coppezip-analista` no `librechat.yaml` |
| novo caso de regressão | `CASOS` em `eval/regressao.py`, com o valor conferido na fonte |

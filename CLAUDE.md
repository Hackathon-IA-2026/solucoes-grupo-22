# CLAUDE.md

Guia para agentes que trabalham neste repositório. Responda e escreva em português do Brasil.

## O que é

EnergyNexus: chat de inteligência do setor elétrico. A raiz é o LibreChat v0.8.7. Do LibreChat mudamos só o tema
(`client/src/style.css`), a logo e o nome (`client/public/assets/` logo e ícones, `client/index.html`,
`client/vite.config.ts`) e o painel lateral, que mostra o relatório em PDF (`client/src/utils/artifacts.ts` e o teste
`client/src/utils/__tests__/artifacts.test.ts`, `client/src/components/Artifacts/ArtifactTabs.tsx`,
`DownloadArtifact.tsx` e `ArtifactButton.tsx`). Tudo o que é nosso está em:

- `librechat.yaml`: modelos (vLLM `EnergyNexus` e `bedrock`), perfis do analista com o prompt (âncora `&prompt`,
  reaproveitada pelo perfil do Claude), servidores MCP e busca web;
- `.env.example`: nome do app, portas, segredos, endereço do vLLM, região do Bedrock (o `.env` real nunca vai para o
  git);
- `instalar.sh`, `iniciar.sh`, `parar.sh`, `vllm.sh`;
- `proper_mcps/` (dados, docs, relatorio), `proper_skills/`, `data/`, `researches/`, `eval/`.

O relatório final é PDF: o roteiro `proper_skills/relatorio-energynexus` traz as regras de redação do modelo oficial,
`gerar_relatorio` (`proper_mcps/relatorio`) preenche o template em `proper_mcps/relatorio/modelo/` e compila com o
TinyTeX de `.runtime/tinytex`, e a resposta abre o PDF no painel pelo bloco `:::artifact` de tipo `application/pdf`.
O conteúdo do relatório vai inteiro num argumento da ferramenta, então o perfil precisa de `maxOutputTokens`: sem ele
o Bedrock corta a resposta em 4096 tokens, a chamada chega sem `conteudo` e o agente repete até o limite de recursão.

## Regras

- **Estrutura fixa, sem fallbacks.** Os caminhos saem da raiz do repositório: `data/coppezip.duckdb` (o banco guarda o
  nome antigo), `data/docs.duckdb`, `data/modelos/`, `data/raw/`, `.runtime/`. Não crie variáveis de ambiente para
  caminho nem valores padrão alternativos; o que é configurável (portas, chaves, endereço do modelo) fica no `.env`.
- **Mínimo e funcionando.** Não deixe código que não foi testado nem arquivos sem uso. Prefira mudar o que existe a
  criar camadas novas.
- **Não mexa no código do LibreChat** (`api/`, `client/`, `packages/`, `config/`) além do tema, da logo e do painel de
  PDF listados acima. Comportamento do chat se muda pelo `librechat.yaml`. Mudou o `client/`? Rode `npm run frontend` e
  **reinicie** (`./parar.sh && ./iniciar.sh`): o LibreChat indexa `client/dist` na subida e, sem reiniciar, o navegador
  recebe `ERR_CONTENT_DECODING_FAILED` e a página fica em branco.
- **O template do relatório não se altera** (`proper_mcps/relatorio/modelo/`): ele pede que só os campos da capa e o
  conteúdo mudem. Versão nova do template: troque os arquivos e atualize o roteiro `relatorio-energynexus`.
- **Nunca vão para o git:** `.env`, `.runtime/`, dados (`data/raw`, `data/parquet`, `data/modelos`, `data/*.duckdb`),
  chaves, senhas.
- **Commits:** mensagem em português no estilo `dados: ...`, `mcp: ...`, `chat: ...`. Autor: o usuário do repositório.
  Não acrescente `Co-Authored-By` nem outra atribuição de IA.
- Pergunta do usuário não é pedido de mudança: responda sem implementar.

## Como testar

```bash
.runtime/venv/bin/python -m pytest proper_mcps -q        # ferramentas MCP, contra o banco de data/ (relatório: TinyTeX)
./iniciar.sh && eval/usuario.sh                          # chat no ar e usuário de teste (uma vez)
python3 eval/chat.py "Qual foi a receita líquida da Taesa em 2025?"          # modelo padrão (vLLM)
python3 eval/chat.py --perfil energynexus-analista-claude "a mesma pergunta"  # Claude pelo Bedrock
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
| regra de resposta | `promptPrefix` do perfil `energynexus-analista` no `librechat.yaml` |
| formato do relatório final | regras de redação em `proper_skills/relatorio-energynexus/SKILL.md`; conferência e compilação em `proper_mcps/relatorio/server.py` (teste em `test_relatorio.py`) |
| novo caso de regressão | `CASOS` em `eval/regressao.py`, com o valor conferido na fonte |

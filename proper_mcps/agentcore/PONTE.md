# Ponte stdio para os servidores MCP no Amazon Bedrock AgentCore

`ponte.py` liga o LibreChat aos três servidores MCP do CoppeZIP publicados no AgentCore Runtime
(`coppezip_dados`, `coppezip_docs`, `coppezip_relatorio`). Um processo por servidor: o LibreChat fala JSON-RPC pelo
stdio, a ponte repassa cada mensagem para o endpoint de invocação do runtime por HTTPS e cuida do token do Cognito.

```
LibreChat ──stdio/JSON-RPC──▶ ponte.py dados ──HTTPS + Bearer JWT──▶ runtimes/<arn>/invocations?qualifier=DEFAULT
                                    └── Cognito InitiateAuth (USER_PASSWORD_AUTH) para pegar e renovar o token
```

## Por que uma ponte, e não `type: streamable-http` com o token no cabeçalho

- o LibreChat 0.8.7 resolve `${VAR}` a partir do `process.env` no boot
  (`packages/data-provider/src/utils.ts:38-52`): um `Authorization: Bearer ${TOKEN}` do `.env` nunca rotaciona, e o
  token do Cognito vale 24 h — só um restart o renovaria;
- a versão não conhece o grant `client_credentials` (não existe em `packages/api/src`), e o pool que autoriza os
  runtimes não tem domínio, segredo de cliente nem resource server: não há fluxo máquina-a-máquina, só
  `USER_PASSWORD_AUTH`;
- 401/403 no meio da sessão, em servidor sem OAuth, é falha dura
  (`packages/api/src/mcp/MCPConnectionFactory.ts:410-419`): a ferramenta para de funcionar até o próximo restart.
  A ponte renova o token antes de expirar, então o LibreChat nunca vê o 401;
- SigV4 não serve: com o `customJWTAuthorizer` configurado o runtime responde 403 "Authorization method mismatch",
  inclusive para o `boto3.invoke_agent_runtime`.

## Configuração

No `.env` (nunca no git; a senha é credencial viva):

```
MCP_INIT_TIMEOUT_MS=180000
COPPEZIP_AGENTCORE_REGIAO=us-west-2
COPPEZIP_ARN_DADOS=arn:aws:bedrock-agentcore:us-west-2:<conta>:runtime/coppezip_dados-XXXXXXXXXX
COPPEZIP_ARN_DOCS=...
COPPEZIP_ARN_RELATORIO=...
COPPEZIP_COGNITO_REGIAO=us-east-1
COPPEZIP_COGNITO_CLIENTE=<app client id do pool>
COPPEZIP_COGNITO_USUARIO=<usuário do pool>
COPPEZIP_COGNITO_SENHA=<senha do usuário>
```

Os ARNs saem de `bedrock-agentcore-control.list_agent_runtimes` na região dos runtimes.

No `librechat.yaml`, os três servidores apontam para a ponte com `type: stdio`, `command: /usr/bin/env` (o LibreChat
não expande `${VAR}` em `command`), o Python do `.runtime/venv` e o nome do servidor como argumento. Duas armadilhas
que o bloco resolve:

- o processo filho do stdio herda só `HOME`, `LOGNAME`, `PATH`, `SHELL`, `TERM` e `USER`: toda variável da ponte tem
  de estar em `env:` (as três pontes compartilham a mesma âncora YAML e cada uma lê apenas o próprio ARN);
- `requiresOAuth: false` desliga a sondagem de OAuth do boot, que bateria no runtime sem token, veria o 403 e passaria
  a exigir login por usuário.

`MCP_INIT_TIMEOUT_MS` mora no `.env` porque o boot ignora o `initTimeout` do YAML
(`packages/api/src/mcp/registry/MCPServersInitializer.ts:10,116-123,212-213`): quem estoura os 30 s do padrão vira um
stub sem ferramentas, retentado só 5 min depois.

## O que a ponte faz

- **token**: `cognito-idp` `InitiateAuth` com `USER_PASSWORD_AUTH`. É uma chamada não assinada, feita com a
  biblioteca padrão: a ponte não usa credencial da AWS nem importa o boto3 (sobe mais rápido e não depende da
  credencial temporária do workshop). O token (`ExpiresIn=86400`) é renovado 10 min antes de expirar e, se ainda vier
  401/403, é renovado e a chamada é repetida **uma** vez.
- **sessão**: um `X-Amzn-Bedrock-AgentCore-Runtime-Session-Id` fixo por processo (o AgentCore exige 33 caracteres ou
  mais), para o container ficar quente; trocado a cada 7 h, antes do `maxLifetime` de 8 h do runtime.
- **initialize**: é repassado ao runtime, porque é dele que vêm as instruções do servidor MCP que o
  `serverInstructions: true` injeta no prompt. Se o runtime não responder em 25 s, a ponte responde ela mesma
  (capacidade de ferramentas, sem instruções, avisando no stderr) e deixa o pedido correndo — ele aquece o runtime
  para o `tools/list` seguinte. Assim o boot do LibreChat nunca fica pendurado; com o `MCP_INIT_TIMEOUT_MS` acima, o
  caminho normal é receber o initialize de verdade.
- **paralelismo**: uma linha de execução por mensagem; três chamadas de ferramenta ao mesmo tempo levam o tempo de
  uma, não de três.
- **erros**: stdout é o transporte JSON-RPC, então log e aviso vão só para o stderr. Falta de variável de ambiente ou
  nome de servidor errado derruba o processo dizendo o nome exato do que falta. Erro de `tools/call` volta como
  `isError` (o modelo lê e corrige); resposta não-200 do AgentCore e qualquer outra falha voltam como erro JSON-RPC
  com o texto que a AWS devolveu. Nada de fallback silencioso e nada de exceção derrubando a ponte.

## Tempos medidos (conta do hackathon, us-west-2, setembro de 2026)

O custo é do AgentCore; a ponte acrescenta ~1 s só no primeiro pedido (login no Cognito).

| servidor | initialize (frio / quente) | tools/list | tools/call |
|---|---|---|---|
| coppezip-dados | 6,3 s / 5,6 s | 5,1 s / 5,5 s | 5,6 s / 5,6 s (`buscar_empresa`) |
| coppezip-docs | 5,8 s / 6,0 s | 5,2 s / 5,1 s | 5,0 s / 5,0 s (`buscar_documentos`) |
| coppezip-relatorio | 5,3 s / 4,6 s | 4,6 s / 6,1 s | 5,8 s / 5,1 s (`gerar_relatorio`) |

"Frio" é processo novo e sessão nova do runtime. O runtime é stateless: cada pedido paga a mesma latência, então
manter a sessão quente ajuda pouco. A versão anterior do `coppezip-docs`, que baixava o modelo de embeddings do S3,
levava 11 a 14 s por pedido — é o pior caso conhecido e a razão do `timeout: 300000` no YAML.

O boot do LibreChat, por servidor, é um `initialize` mais dois `tools/list` que o `MCPServerInspector` dispara em
paralelo (`fetchServerCapabilities` e `fetchToolFunctions`); as instruções saem do próprio initialize, sem pedido
extra. Como a ponte atende uma mensagem por linha de execução, os dois `tools/list` custam o tempo de um:
12,9 s no dados, 10,5 s no docs e 10,9 s no relatorio, medidos ponta a ponta. Cabe nos 30 s do padrão, mas sem folga
para um runtime mais lento — daí `MCP_INIT_TIMEOUT_MS=180000`.

## Como testar sem subir o LibreChat

```bash
# com as variáveis do .env exportadas (set -a; . ./.env; set +a)
printf '%s\n%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"t","version":"1"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | .runtime/venv/bin/python proper_mcps/agentcore/ponte.py dados
```

O stderr mostra o ARN, o token novo e o id da sessão; o stdout traz as duas respostas JSON-RPC. Trocar `dados` por
`docs` ou `relatorio` testa os outros dois.

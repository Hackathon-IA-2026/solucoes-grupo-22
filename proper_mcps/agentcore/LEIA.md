# Os MCP do CoppeZIP no Amazon Bedrock AgentCore Runtime

Os três servidores de `proper_mcps/` também rodam na AWS, como runtimes MCP do Bedrock AgentCore em **us-west-2**, para
clientes de fora desta máquina (o LibreChat daqui sobe os mesmos servidores por stdio, ver `mcpServers` no
`librechat.yaml`). É um zip só para os três, com `proper_mcps/agentcore/servidor.py` como ponto de entrada; a variável
`COPPEZIP_MCP` do runtime diz qual servidor subir e `COPPEZIP_BUCKET` de onde vêm os dados.

| Runtime (nome) | ferramentas | o que baixa do bucket ao subir |
|---|---|---|
| `coppezip_dados` | `buscar_empresa`, `indicadores_financeiros`, `listar_tabelas`, `descrever_tabela`, `valores_distintos`, `consultar_sql` | `bancos/coppezip.duckdb` |
| `coppezip_docs` | `buscar_documentos`, `ler_pagina`, `listar_documentos` | `bancos/docs_titan.duckdb` (a pergunta é embutida pelo Titan, no Bedrock) |
| `coppezip_relatorio` | `gerar_relatorio` | nada; grava em `relatorios/` do bucket e devolve link assinado por 7 dias |

Conta 139382521595, bucket `coppezip-dados-oeste-139382521595`, role de execução `coppezip-agentcore` (políticas inline
`dados-e-logs`, do CDK, e `embeddings-titan`, garantida pelo `atualizar.py`). Os runtimes foram criados pelo
`cdk_app.py` (stack `CoppeZIPMcp`) e os IDs saem do nome: `coppezip_dados-S6G17U40Na`, `coppezip_docs-1ccSowG1v9`,
`coppezip_relatorio-m2pmDZFRYX` — o `atualizar.py` procura pelo nome, então ID novo não quebra nada.

## Republicar o código

```bash
export COGNITO_USUARIO=... COGNITO_SENHA=...      # usuário do Cognito; nunca no git, nem no código
.runtime/venv/bin/python proper_mcps/agentcore/atualizar.py                  # empacota, publica e testa os três
.runtime/venv/bin/python proper_mcps/agentcore/atualizar.py --dados          # idem, enviando também os bancos de data/
.runtime/venv/bin/python proper_mcps/agentcore/atualizar.py --somente-teste  # só chama as ferramentas do que está no ar
```

O que o script faz, na ordem: acha os três runtimes pelo nome e pega a configuração atual; pega o token do Cognito
(falha já aqui se faltar `COGNITO_USUARIO`/`COGNITO_SENHA`); confere no bucket os bancos que os servidores baixam (com
`--dados`, envia os de `data/`); garante `bedrock:InvokeModel` do Titan na role; monta
`.runtime/agentcore/coppezip-mcp.zip` (bibliotecas ARM64 com `pip --platform manylinux*_aarch64` mais `proper_mcps/`
no mesmo layout do repositório, sem testes); envia o zip com chave datada `codigo/coppezip-mcp-<AAAAMMDD-HHMM>.zip`;
chama `update_agent_runtime` nos três reenviando a configuração inteira; espera runtime e endpoint `DEFAULT` ficarem
`READY` na versão nova (até 15 min, dizendo qual falhou); e chama `tools/list` mais uma ferramenta de verdade em cada
servidor, imprimindo a resposta.

Mudou o índice dos documentos (`data/indexar_docs_titan.py`) ou o banco (`data/construir.py`)? Republique com `--dados`:
o código não muda, mas os runtimes só enxergam o que está no bucket.

## Token e como chamar de fora

O único jeito de autenticar é `Authorization: Bearer <JWT do Cognito>`; o token vem de `USER_PASSWORD_AUTH` no user pool
`us-east-1_wcntmDWjd`, app client `vjcpq1sgeg3pj75src9phclm5` (os dois saem da própria configuração do runtime, em
`authorizerConfiguration`), e vale 24 h:

```python
boto3.client("cognito-idp", region_name="us-east-1").initiate_auth(
    ClientId="vjcpq1sgeg3pj75src9phclm5", AuthFlow="USER_PASSWORD_AUTH",
    AuthParameters={"USERNAME": os.environ["COGNITO_USUARIO"], "PASSWORD": os.environ["COGNITO_SENHA"]},
)["AuthenticationResult"]["AccessToken"]
```

A chamada é um POST JSON-RPC no endpoint `DEFAULT`, com o ARN inteiro url-encoded no caminho:

```
POST https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/{urllib.parse.quote(arn, safe="")}/invocations?qualifier=DEFAULT
Authorization: Bearer <token>
Accept: application/json, text/event-stream
{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
```

A resposta volta em SSE (linhas `data: {...}`). O servidor é stateless (`stateless_http=True`): `initialize` e cabeçalho
de sessão são opcionais, `tools/list` e `tools/call` respondem direto.

## O que NÃO funciona (já testado)

- **SigV4**: com `customJWTAuthorizer` configurado, assinar a chamada dá 403 `AccessDeniedException` com "Authorization
  method mismatch" — inclusive pelo `invoke_agent_runtime` do boto3, que é SigV4 por construção. Só Bearer JWT.
- **`client_credentials` (máquina a máquina)**: o user pool não tem domínio, logo não existe
  `https://<domínio>.auth.<região>.amazoncognito.com/oauth2/token`; o app client não tem segredo e está com
  `AllowedOAuthFlowsUserPoolClient=false`; e não há resource server, logo não há scope. Criar outro app client não
  resolve: `allowedClients` do authorizer fixa o ID atual, e mexer nisso derruba a autenticação dos três runtimes.
- **`aws` CLI**: não existe nesta máquina; tudo é boto3 (o `atualizar.py` faz o upload com `s3.upload_file`, que já
  divide em partes).
- **Sobrescrever o zip mantendo a chave**: o bucket não tem versionamento e, pelo CloudFormation, o template não muda e
  a resposta é "No updates are to be performed" — o código novo não sobe. Por isso a chave é datada.
- **`cdk_app.py`**: só roda depois de `pip install aws-cdk-lib constructs` (o módulo não está instalado aqui). Serve
  para criar os runtimes; para republicar código o `atualizar.py` vai direto no `update_agent_runtime`.

## Cuidados

- `update_agent_runtime` **substitui** a configuração: o que não for reenviado se perde. O `atualizar.py` faz
  `get_agent_runtime` e devolve tudo (role, rede, protocolo, authorizer, variáveis, descrição, ciclo de vida,
  metadados, plataforma) trocando só a chave do zip. Omitir o authorizer derruba o JWT; omitir as variáveis derruba o
  servidor (`servidor.py` exige `COPPEZIP_MCP` e `COPPEZIP_BUCKET`).
- Publicar direto deixa a stack `CoppeZIPMcp` em drift (o template continua apontando para a chave antiga do zip): um
  `cdk deploy` posterior volta o código para a versão do template.
- O `coppezip_docs` chama o Bedrock a cada busca: a role precisa de `bedrock:InvokeModel` no
  `amazon.titan-embed-text-v2:0` de us-west-2 (o `atualizar.py` garante) e o índice tem de ser o do Titan
  (`bancos/docs_titan.duckdb`, embeddings FLOAT[1024] do mesmo modelo); com o índice do e5 antigo a busca por
  significado devolveria lixo.
- Cada sessão nova baixa o banco do bucket para `/tmp`: a primeira chamada depois de 15 min ociosos (idle 900 s,
  vida máxima 28800 s) demora. Os relatórios ficam em `relatorios/` do bucket com link assinado por 7 dias — quem tem
  o link lê o arquivo.
- Log de cada runtime: `/aws/bedrock-agentcore/runtimes/<agentRuntimeId>-DEFAULT`, em us-west-2. É lá que aparece o
  erro quando o container sobe e morre (por exemplo, falta de banco no bucket ou import que não existe no zip).
- As credenciais da AWS deste ambiente são temporárias (`WSParticipantRole`): quando o workshop expira, runtimes,
  bucket e user pool vão com ele.

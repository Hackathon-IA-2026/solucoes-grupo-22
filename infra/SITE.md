# Site público: a vitrine estática na AWS

O que está no ar, o que ficou de fora e como republicar. Quem publica é `infra/publicar_site.py`.

## Endereço

<http://energynexus-site-139382521595.s3-website-us-east-1.amazonaws.com/>

É o endpoint de **website hosting** de um bucket S3 em `us-east-1`. Conta `139382521595`, papel
`WSParticipantRole/Participant` (credencial temporária de workshop em `~/.aws/credentials`).

Honestidade sobre "global": o conteúdo é alcançável do mundo inteiro, mas o endpoint é **regional** (o nome
`s3-website-us-east-1` não é apelido: quem abre de Lisboa busca o objeto na Virgínia) e é **HTTP puro, sem TLS**. Não há
CDN nem certificado porque a conta nega CloudFront, ACM e Route 53 (tabela abaixo). Se essa permissão aparecer, o
caminho é uma distribuição CloudFront com este bucket como origem — nada no site precisa mudar para isso.

Existe um endereço HTTPS, só por arquivo (sem página inicial e sem deep link, porque o endpoint REST não tem
IndexDocument): <https://energynexus-site-139382521595.s3.amazonaws.com/index.html>.

O nome do bucket é `energynexus-site-<conta>`: já usa a marca nova, é único no mundo (nome de bucket é global) e o
script o monta a partir da conta que a credencial devolve, então a renomeação do projeto não mexe nele.

## O que é estático e está funcionando

| Tela | De onde vêm os dados no site | Estado |
|---|---|---|
| **Painel** (`/painel`) | `dados/painel.json` (cópia de `data/painel.json`, 19 MB) | funciona |
| **Grafo** (`/grafo`) | `dados/painel.json` + `dados/busca_resumo.json` | funciona; sem os documentos o grafo sai só com as bases do painel e a tela diz isso |
| **Timeline** (`/timeline`, `/timeline/<cnpj>`) | `linha_do_tempo/*.json` (cópia de `.runtime/linha_do_tempo/`) | funciona |
| **Busca** (`/busca`) | — | publicada **desabilitada**, com o aviso do que falta |
| Chat | — | fora; `/c/...` mostra o aviso de que precisa de servidor |

O build usado é o normal do front (`vite`), com `VITE_SITE_ESTATICO=1`. Essa variável faz duas coisas, e só duas:

- `client/src/routes/index.tsx` usa uma árvore de rotas enxuta (`rotasEstaticas`), com a casca
  `client/src/components/Coppezip/Vitrine.tsx` no lugar de `routes/Root.tsx`. É o que tira o site do portão de login:
  `Root.tsx` exige `isAuthenticated` e chama `/api/config`, que não existem num bucket;
- `client/src/components/Coppezip/api.ts` troca `GET /api/painel/dados` por `dados/painel.json` e
  `GET /api/busca/resumo` por `dados/busca_resumo.json`. Qualquer outra rota `/api/...` falha dizendo o nome, em vez de
  devolver tela branca.

Sem a variável nada muda: `npm run frontend` continua gerando o front do chat, com login e todas as abas.

A aba Timeline não precisou de nada: `client/src/components/Timeline/data.ts` já busca
`linha_do_tempo/<arquivo>` relativo ao `baseURI`, sem token.

## O que precisa de servidor (e por que não foi)

- **Chat**: é o produto. Precisa do Node do LibreChat, MongoDB, Meilisearch, os servidores MCP de `proper_mcps/` e o
  modelo (vLLM ou Bedrock) — `iniciar.sh`. Nada disso cabe num bucket.
- **Aba Busca**: `proper_mcps/docs/busca.py` calcula o embedding da pergunta no Bedrock a cada consulta sobre
  `data/docs_titan.duckdb`, e serve imagem de página e PDF de `data/raw` (~1 GB). É computação por requisição e arquivo
  binário grande: não vira arquivo estático. A tela está no ar com o aviso do que falta.
- **`dados/busca_resumo.json`**: é só um retrato do `GET /resumo`, então **é** estatizável — mas depende do serviço de
  busca estar no ar na hora de publicar. Hoje `data/docs_titan.duckdb` não existe (está sendo reindexado), por isso a
  publicação foi feita com `--sem-documentos` e o Grafo mostra `Documentos indisponíveis: dados/busca_resumo.json: 404`.
  Quando o índice voltar, republicar sem a opção resolve.

Onde rodaria um backend nesta conta: **em nenhum lugar alcançável**. Lambda, ECS com role, Beanstalk e qualquer stack de
CloudFormation que crie role morrem no mesmo ponto, `iam:PassRole` (detalhe na tabela). Fargate sobe sem role, mas sem
`ec2:*` não se abre a porta e sem `elasticloadbalancing:*` não se põe um balanceador na frente — a tarefa roda e não
atende ninguém.

## Permissões testadas nesta conta (boto3, chamada de verdade)

| Serviço / ação | Resultado |
|---|---|
| `sts:GetCallerIdentity`, `s3:*` no bucket (criar, policy pública, website, CORS, put/delete object) | **permitido** |
| `s3:PutBucketAccelerateConfiguration` (HTTPS pela borda, `s3-accelerate`) | permitido; **não usado** (cobra por GB, não faz cache e não tem IndexDocument) |
| `s3control` Multi-Region Access Point (`us-west-2`) | permitido criar/apagar, mas **inútil** aqui: MRAP só atende pedido assinado com SigV4, não navegador anônimo. Criei um de teste e apaguei |
| `cloudformation:ListStacks`, `iam:ListRoles`, `iam:CreateRole`, `lambda:ListFunctions`, `lambda:CreateFunctionUrlConfig`, `ecr:CreateRepository`, `ecs:*` | permitido (e não resolve nada sozinho) |
| `cloudfront:ListDistributions` / `CreateDistribution` / `CreateOriginAccessControl` | **negado** (`AccessDenied`) |
| `acm:ListCertificates`, `route53:ListHostedZones` | **negado** |
| `amplify:ListApps` / `CreateApp` | **negado** |
| `apigateway:GET` (v1 e v2), `apigatewayv2:CreateApi` | **negado** |
| `apprunner:ListServices`, `lightsail:GetDistributions` | **negado** |
| `globalaccelerator:ListAccelerators` (`us-west-2`) | **negado** |
| `elasticloadbalancing:DescribeLoadBalancers`, `appsync:ListGraphqlApis` | **negado** |
| `ec2:DescribeInstances`, `ec2:RunInstances`, `ec2:DescribeNetworkInterfaces`, `ec2:*SecurityGroup*` | **negado** (`UnauthorizedOperation`) |
| `elasticbeanstalk:CreateApplication` | **negado** (a leitura passa) |
| `lambda:CreateFunction` | **negado por `iam:PassRole`**. O detalhe: `PassRole` é liberado **só** para `WSParticipantRole`, e o Lambda não consegue assumir essa role ("The role defined for the function cannot be assumed by Lambda"). Testei as 7 roles da conta que confiam em `lambda.amazonaws.com`: todas dão `iam:PassRole` negado. Logo **não há Lambda Function URL**, mesmo com `lambda:CreateFunctionUrlConfig` liberado |

Conclusão: nesta conta, S3 website hosting é a única forma de servir o site, e não há compute público nenhum.

## Como republicar

Depois de mudar o front, os dados, ou depois da renomeação para EnergyNexus e do logo novo:

```bash
.runtime/venv/bin/python infra/publicar_site.py
```

O script é re-executável de ponta a ponta: recompila, regrava os dados, sobrescreve os objetos, apaga o que sobrou de
publicações anteriores e confere as rotas com `GET` antes de imprimir a URL.

Opções:

- `--instalacao RAIZ` — usar o `.runtime/` e o `data/painel.json` de outra instalação (é o caso de publicar de uma
  worktree, que não tem nem um nem outro);
- `--sem-documentos` — publicar sem `dados/busca_resumo.json`, quando o serviço de busca não está no ar;
- `--sem-build` — reaproveitar o `client/dist-vitrine` já compilado (só regrava os dados e sobe);
- `--bucket NOME` — outro bucket (o padrão é `energynexus-site-<conta>`).

O build da vitrine sai em `client/dist-vitrine/` (ignorado pelo git) e **não encosta em `client/dist/`**: o chat local
continua servindo o front dele sem precisar de novo `npm run frontend`.

### Cache e invalidação

Não há CloudFront, então não há invalidação a pedir: quem decide é o cabeçalho de cada objeto.

- `Cache-Control: public, max-age=31536000, immutable` só nos arquivos com hash do vite
  (`assets/index.<hash>.js`), que por definição mudam de nome quando mudam de conteúdo;
- `Cache-Control: no-cache` em todo o resto — `index.html`, `sw.js`, os ícones de `assets/` (inclusive o logo, que vai
  mudar) e todos os JSON de dados. Assim a republicação aparece na próxima visita.

A limpeza só apaga objeto que tenha o metadado `publicado-por: publicar_site.py`, ou seja, só o que este script subiu;
qualquer outra coisa no bucket é preservada e o script avisa que a deixou.

## Cuidados

- **Os dados ficam públicos.** `dados/painel.json`, `dados/busca_resumo.json` e `linha_do_tempo/*.json` ficam legíveis
  por qualquer pessoa da internet, sem login e sem registro de quem baixou. É o preço de um site estático sem backend.
- **Deep link.** `/painel`, `/grafo`, `/timeline` e `/busca` respondem 200 porque o script sobe uma cópia do
  `index.html` em `<aba>/index.html` (o S3 redireciona `/painel` para `/painel/`). Caminho com parâmetro, como
  `/timeline/08773135000100`, cai no `ErrorDocument`: devolve o mesmo `index.html` com **status 404** e o navegador
  renderiza a tela certa. Com CloudFront isso viraria 200.
- **A credencial é temporária.** As chaves do workshop expiram e a conta pode ser varrida no encerramento. O bucket
  sobrevive à sessão; a infraestrutura não é definitiva.
- **Ficou um repositório ECR vazio** (`energynexus-teste`) de um teste anterior: `ecr:DeleteRepository` é negado. Está
  vazio, não gera custo.

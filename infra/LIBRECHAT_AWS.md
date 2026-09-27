# Chat no ar: o LibreChat deste fork numa EC2

Como subir, esticar a janela, desligar e apagar. Quem faz é `infra/librechat_aws.py`; a máquina se monta com
`infra/partida_ec2.sh`, `infra/Dockerfile`, `infra/compose.yaml`, `infra/entrada.sh` e `infra/ajustar_yaml.py`.

O site estático (`infra/SITE.md`) é a vitrine sem servidor; este documento é a outra metade, o chat de verdade, com os
quatro MCP ligados.

## Comandos

O `boto3` já está no venv do repositório; não há AWS CLI nesta máquina.

```bash
.runtime/venv/bin/python infra/librechat_aws.py subir --horas 10   # cria tudo e devolve a URL
.runtime/venv/bin/python infra/librechat_aws.py estado --log       # pilha, instância e a partida da máquina
.runtime/venv/bin/python infra/librechat_aws.py esticar --horas 4  # reagenda o desligamento a partir de agora
.runtime/venv/bin/python infra/librechat_aws.py desligar           # para a instância; o disco e o IP ficam
.runtime/venv/bin/python infra/librechat_aws.py ligar              # liga; o systemd sobe a pilha sozinho
.runtime/venv/bin/python infra/librechat_aws.py apagar             # apaga a pilha e o parâmetro dos segredos
```

`subir` aceita `--instalacao RAIZ` (mesma convenção do `infra/publicar_site.py`), porque o `.env` e os bancos em `data/`
não estão no git: é de lá que saem o `placar.duckdb`, o `painel.json` e os segredos. `--tipo` troca o tamanho da
máquina; o padrão é `m7i.xlarge`.

Um detalhe de ordem, não de gosto: `subir` empacota o código com `git archive HEAD`, então **comite antes de subir** ou
a instância recebe a versão anterior. O script avisa quando a árvore está suja, e segue.

## Por que EC2 por CloudFormation

A conta é de workshop e o papel é `WSParticipantRole/Participant`. Medido, não suposto — cada linha abaixo é uma chamada
que foi feita:

| Chamada | Resposta |
|---|---|
| `ec2:RunInstances` (dry-run) | `UnauthorizedOperation` |
| `ec2:CreateSecurityGroup`, `ec2:AllocateAddress`, `ec2:CreateKeyPair` | `UnauthorizedOperation` |
| `ec2:DescribeInstances`, `ec2:DescribeSecurityGroups` | `UnauthorizedOperation` |
| `cloudfront:*` | negado pela política (já se sabia do site) |
| `iam:PassRole` para `ecs-tasks.amazonaws.com` | fora da política: nem ECS Fargate com role de tarefa |
| App Runner, Lightsail, ELB | fora da política |
| `sts:AssumeRole` em `arn:aws:iam::139382521595:role/cdk-*` | **permitido** |

A última linha é a porta. O `cdk-hnb659fds-deploy-role` pode `cloudformation:CreateStack` e pode `iam:PassRole` no
`cdk-hnb659fds-cfn-exec-role`, que tem `AdministratorAccess`. Então o script assume o papel de deploy e entrega o
template ao CloudFormation com `RoleARN` do papel de execução: o CloudFormation cria, **como administrador**, o papel, o
perfil de instância, o grupo de segurança, o IP elástico e a máquina — coisas que o chamador não pode criar à mão.

É o mesmo caminho que `proper_mcps/agentcore/cdk_app.py` já usava para os runtimes do AgentCore. O que muda é a
conclusão: `infra/SITE.md` diz que "Lambda, ECS com role, Beanstalk e qualquer stack de CloudFormation que crie role
morrem no mesmo ponto, `iam:PassRole`". Isso está **errado** e este documento o corrige — morrem se você mesmo chamar
`CreateStack` com a sua credencial, porque o `PassRole` sai em seu nome; passando pelos papéis do bootstrap do CDK, não.

Região `us-west-2` por três razões que apontam para o mesmo lugar: é lá que existe o bootstrap do CDK, é lá que rodam os
runtimes `coppezip_dados` e `coppezip_docs` do AgentCore, e é lá que está o bucket com os bancos — a instância baixa
~3 GB na partida, e dentro da mesma região isso é rápido e de graça.

## O que a pilha `energynexus-chat` cria

| Recurso lógico | O que é | Por que assim |
|---|---|---|
| `Papel` + `Perfil` | papel da instância e perfil | credencial por papel; nenhuma chave de acesso entra na máquina |
| `Grupo` | grupo de segurança, 80 e 443 de `0.0.0.0/0` | a 22 fica fechada: o shell é por SSM, não por chave |
| `IP` + `Associacao` | IP elástico e a associação | o endereço sobrevive a `desligar`/`ligar`, e a URL não muda |
| `Maquina` | a EC2 `m7i.xlarge`, AL2023 x86_64, 100 GB gp3 | x86_64 porque o `pdflatex` do MCP de relatório é x86_64 |
| `PapelOperacao` + `Operacao` | função Lambda de três ações | ver "Ligar e desligar" abaixo |

O IP elástico é alocado como recurso próprio e associado depois, em vez de sair do atributo da máquina. Não é
preferência: o user-data precisa do IP para montar o hostname, e o hostname entra no `DOMAIN_CLIENT`, então a máquina
depende do IP. Se o IP dependesse da máquina, a pilha teria um ciclo.

A máquina sobe com `HttpPutResponseHopLimit: 2` no IMDS. Sem isso o contêiner do chat não alcança o IMDS (um salto se
gasta na ponte do Docker) e o Bedrock fica sem credencial — o sintoma é a conversa falhando com erro de credencial e
nada de errado no `.env`. E com `InstanceInitiatedShutdownBehavior: stop`, para o `shutdown -h` agendado parar a
máquina em vez de destruí-la.

O papel da instância leva o mínimo: `AmazonSSMManagedInstanceCore` (é o shell), `bedrock:InvokeModel` e
`InvokeModelWithResponseStream` (a conversa), `s3:GetObject` nos prefixos `bancos/*` e `chat/*` do bucket,
`ssm:GetParameter` no parâmetro dos segredos e `kms:Decrypt` restrito por `kms:ViaService` ao SSM.

Não leva `bedrock-agentcore:InvokeAgentRuntime`, e isso é de propósito: `proper_mcps/agentcore/ponte.py` chama o
AgentCore com `Authorization: Bearer <JWT>` do Cognito, não com assinatura SigV4 — o docstring da classe `Token` diz
isso em voz alta ("InitiateAuth não é assinado, logo a ponte não usa credencial da AWS"). Dar a permissão seria carga
morta.

## HTTPS sem CloudFront

A conta nega CloudFront, ACM e Route 53, e não dá ALB. O que sobra, e funciona: **Caddy na própria máquina**, pedindo
certificado à Let's Encrypt para `<ip>.nip.io`. O `nip.io` resolve qualquer `<ip>.nip.io` para o próprio `<ip>`, então a
validação HTTP-01 fecha sem domínio comprado e sem zona DNS.

Quem chega pelo IP cru em HTTP é redirecionado para o nome com certificado — senão o navegador manda a senha do
LibreChat em texto claro.

## Segredo, configuração e endereço: três lugares diferentes

Essa separação é o ponto delicado do `.env` da instância, e é deliberada:

- **o que não é segredo** está escrito no heredoc do `infra/partida_ec2.sh`, à vista no git: portas, `MONGO_URI`,
  `MEILI_HOST`, `ENDPOINTS`, `BEDROCK_AWS_DEFAULT_REGION`, limites de login;
- **o que é segredo** vai num único parâmetro SecureString do SSM (`/energynexus/chat/segredos`, ~900 bytes, e o script
  recusa passar dos 4096 do tier padrão), buscado na partida com o papel da instância. São as chaves do LibreChat, a do
  Meilisearch, as de busca web e o usuário do Cognito que a ponte usa;
- **o endereço** (`DOMAIN_CLIENT`/`DOMAIN_SERVER`) só se calcula na máquina, porque o hostname sai do IP elástico.

`CREDS_KEY`, `CREDS_IV`, `JWT_SECRET`, `JWT_REFRESH_SECRET` e `MEILI_MASTER_KEY` são **regeradas** a cada `subir`, não
copiadas: a caixa pública não compartilha segredo nenhum com o laboratório.

O Bedrock não recebe chave: `api/server/services/Config/EndpointService.js` liga o endpoint com
`BEDROCK_AWS_DEFAULT_REGION` sozinho, e o SDK então usa a cadeia padrão, que na EC2 é o papel da instância.

## O perfil padrão na nuvem não é o mesmo

Aqui no laboratório o perfil padrão do `librechat.yaml` é o `energynexus-analista`, que fala com um vLLM local. Na AWS
não há vLLM, e um padrão morto é a primeira coisa que o visitante encontra.

`infra/ajustar_yaml.py` resolve isso na partida do contêiner, com três transformações declaradas: apaga
`endpoints.custom`, remove o perfil `energynexus-analista` e marca `default: true` só no
`energynexus-analista-claude` (que usa `us.anthropic.claude-sonnet-5` pelo Bedrock). O resultado vai para
`.runtime/librechat.aws.yaml` e o `CONFIG_PATH` aponta para lá — o `librechat.yaml` versionado não é tocado. Se alguma
das três expectativas não se confirmar, o script morre com a mensagem do que mudou, em vez de adivinhar.

Sobre o modelo: dos Claude que a política da conta lista, os de geração anterior responderam
`ResourceNotFoundException` ("this model version has reached the end of its life") e o `claude-sonnet-4` é negado
explicitamente em `us-west-2`. O `us.anthropic.claude-sonnet-5` responde, e é o que o perfil já pedia.

## Janela e desligamento automático

O desligamento é agendado em dois lugares, e os dois são necessários:

- no user-data, antes de qualquer instalação, para uma partida que falhe no meio não deixar a máquina ligada a noite
  inteira;
- no `ExecStartPre` do `energynexus.service`, porque o user-data só roda no **primeiro** boot: sem isso, um `ligar`
  depois do desligamento automático deixaria a instância ligada para sempre.

`esticar --horas N` reagenda a partir de agora (`shutdown -c` e `shutdown -h +N*60`) e imprime
`/run/systemd/shutdown/scheduled` como prova de que pegou. `desligar` para na hora.

## Ligar e desligar passa por uma Lambda

`ec2:StartInstances` e `ec2:StopInstances` o `WSParticipantRole` não tem, e criar um papel novo para assumir também não
é possível (a política tem `DenyRoleChaining`). A saída é a função `Operacao`, que a pilha cria com um papel que ela
mesma criou (como administrador) e que pode ligar, desligar e descrever **só esta instância**. O
`WSParticipantRole` pode invocar Lambda, e é isso que `ligar`, `desligar` e `estado` fazem.

## Trocar o placar sem reprovisionar

O `placar.duckdb` continua sendo reextraído enquanto o chat já está no ar. Trocá-lo não pede pilha nova nem reinício: o
banco é uma montagem (`/opt/energynexus/dados` → `/app/data`) e o `_con()` de `proper_mcps/placar/server.py` abre uma
conexão nova do DuckDB **a cada chamada** de ferramenta. Então o processo filho que o LibreChat mantém vivo pega o
arquivo novo na chamada seguinte, sem derrubar ninguém — medido em produção: o chat respondeu `200` antes e depois, e o
contêiner não reiniciou.

```bash
# daqui, com o venv do repositório:
.runtime/venv/bin/python -c "import boto3; boto3.client('s3').upload_file('data/placar.duckdb', \
  'coppezip-dados-oeste-139382521595', 'chat/dados/placar.duckdb')"
# e na instância, por SSM: baixa ao lado, confere, guarda o anterior e troca com rename (atômico no mesmo disco)
D=/opt/energynexus/dados
aws s3 cp s3://coppezip-dados-oeste-139382521595/chat/dados/placar.duckdb $D/placar.novo.duckdb
docker run --rm -v $D:/d:ro --entrypoint /opt/venv/bin/python energynexus-chat \
  -c "import duckdb; c=duckdb.connect('/d/placar.novo.duckdb', read_only=True); print(c.execute('select count(*) from esg_metas').fetchone())"
cp -a $D/placar.duckdb $D/placar.anterior.duckdb && mv $D/placar.novo.duckdb $D/placar.duckdb
```

O `placar.anterior.duckdb` é o caminho de volta: um `mv` no sentido contrário desfaz a troca. Reconstruir a imagem só é
necessário quando muda **código** (o `COPY . /app` do Dockerfile invalida o `npm ci` e o `vite build`, e aí são os vinte
minutos de novo).

## Acompanhar a partida

A primeira subida leva perto de vinte minutos, quase tudo em `npm ci` e `vite build` da interface. `estado --log` mostra
a cauda de `/var/log/energynexus-partida.log`, o estado do serviço e os contêineres de pé.

O shell é por SSM (`AWS-RunShellScript` ou Session Manager); não há par de chaves e a 22 não está aberta.

## Custo

Preço de tabela em `us-west-2`, Linux on-demand, somado por hora de máquina **ligada**:

| Item | US$/h |
|---|---|
| `m7i.xlarge` (4 vCPU, 16 GB) | 0,2016 |
| 100 GB gp3 (US$ 8/mês, rateado) | 0,011 |
| IPv4 público | 0,005 |
| **total** | **≈ 0,22** |

Dez horas ficam em ~US$ 2,20 de infraestrutura. O disco continua correndo com a máquina desligada (~US$ 0,011/h); o IP
elástico associado a instância parada também é cobrado. `apagar` encerra as duas coisas.

Fora dessa conta ficam os tokens do Bedrock (por uso, e é a parte que pode passar a máquina se houver muita conversa) e
o S3, que já existia.

## O que fica de fora, e por quê

- **`data/raw/`** (os PDFs) não está no bucket: a aba Busca acha o trecho e cita arquivo e página, mas não abre o PDF na
  tela. Seriam dezenas de GB subindo deste cluster.
- **`bancos/docs.duckdb`** no S3 é o índice e5 antigo, de 83 MB; o `data/docs.duckdb` local aponta para um
  `docs_local.duckdb` de 2,37 GB. A aba Timeline sai parcial, em vez de esperar 2,4 GB de upload.
- O MCP `energynexus-docs` **não** depende disso: ele roda no AgentCore, com o índice Titan que já está no bucket.

## Apagar tudo

```bash
.runtime/venv/bin/python infra/librechat_aws.py apagar
```

Apaga a pilha (máquina, IP, grupo, papéis, Lambda) e o parâmetro dos segredos. O que **não** apaga, de propósito, é o
que já existia antes: os runtimes do AgentCore, o bucket do site e o Cognito. O código e o placar ficam em
`s3://coppezip-dados-oeste-139382521595/chat/`; some com eles à mão se quiser.

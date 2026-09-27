#!/bin/bash
# Partida da instância: transforma uma Amazon Linux 2023 crua no chat EnergyNexus no ar. Quem chama é o user-data que
# a pilha do CloudFormation monta (infra/librechat_aws.py), depois de baixar e abrir o código neste disco.
#
# Idempotente de propósito: roda de novo a cada boot sem refazer o que já está feito (os bancos que já baixou, a
# imagem que já construiu). É o que faz o systemd conseguir levantar tudo sozinho depois de um `ligar`.
#
# Divisão de responsabilidade do .env, que é o ponto delicado: a parte que não é segredo está escrita aqui, à vista no
# git; os segredos vêm de um parâmetro SecureString do SSM, buscado com o papel da instância; e o endereço público só
# se sabe aqui, porque o hostname sai do IP elástico que a pilha reservou.
set -euo pipefail

: "${EN_BUCKET:?falta EN_BUCKET}" "${EN_REGIAO:?falta EN_REGIAO}" "${EN_PREFIXO:?falta EN_PREFIXO}"
: "${EN_PARAMETRO:?falta EN_PARAMETRO}" "${EN_IP:?falta EN_IP}" "${EN_MINUTOS:?falta EN_MINUTOS}"

RAIZ=/opt/energynexus
CODIGO=$RAIZ/codigo
# nip.io resolve <ip>.nip.io para o próprio <ip>: é o hostname que o Caddy usa para pedir o certificado à Let's
# Encrypt. Sem ele não há HTTPS, porque a conta do workshop nega cloudfront:* e não dá ALB nem ACM.
EN_HOSTNAME=$EN_IP.nip.io

echo "== instalando o docker"
dnf install -y docker
systemctl enable --now docker
# O plugin do compose não está nos repositórios do AL2023; o binário oficial vai onde o docker procura os plugins.
COMPOSE=/usr/libexec/docker/cli-plugins/docker-compose
if [ ! -x "$COMPOSE" ]; then
  install -d /usr/libexec/docker/cli-plugins
  curl -fL --retry 3 -o "$COMPOSE" \
    https://github.com/docker/compose/releases/download/v2.39.4/docker-compose-linux-x86_64
  chmod +x "$COMPOSE"
fi

echo "== baixando os bancos do S3"
mkdir -p "$RAIZ"/dados "$RAIZ"/estado/relatorios "$RAIZ"/estado/linha_do_tempo
baixar() {  # $1 = chave no bucket, $2 = destino. Já baixado não baixa de novo (são ~3 GB).
  [ -s "$2" ] || aws s3 cp "s3://$EN_BUCKET/$1" "$2" --region "$EN_REGIAO" --only-show-errors
}
# o que o MCP energynexus-placar exige: o placar em si e o banco financeiro que ele anexa como `fin`
baixar "$EN_PREFIXO/dados/placar.duckdb" "$RAIZ/dados/placar.duckdb"
baixar bancos/coppezip.duckdb "$RAIZ/dados/energynexus.duckdb"
# o que as abas Painel, Busca e Timeline usam (o chat e os quatro MCP não dependem destes)
baixar "$EN_PREFIXO/dados/painel.json" "$RAIZ/dados/painel.json"
baixar bancos/docs.duckdb "$RAIZ/dados/docs.duckdb"
baixar bancos/docs_titan.duckdb "$RAIZ/dados/docs_titan.duckdb"

# O compose monta esta pasta em /app/data, e a montagem *esconde* o data/ que veio na imagem — com ele, o
# data/linha_do_tempo.py, que o entrada.sh executa e que o proper_mcps/docs/busca.py importa (ele põe <RAIZ>/data no
# sys.path). Sem esta cópia a aba Busca sobe e morre na hora com "ModuleNotFoundError: No module named
# 'linha_do_tempo'", e a rota /api/busca responde 502 "servico de busca indisponivel". São scripts versionados, sem
# segredo nenhum; ficam ao lado dos bancos porque é esse o diretório que o contêiner vê como data/.
cp -p "$CODIGO"/data/*.py "$RAIZ"/dados/

echo "== montando o .env"
# A parte que não é segredo. HOST=0.0.0.0 porque o Node tem de ser alcançável de fora do contêiner; MONGO_URI e
# MEILI_HOST apontam para os nomes dos serviços do compose; ENDPOINTS perde o `custom` porque não há vLLM aqui
# (infra/ajustar_yaml.py tira o endpoint correspondente do librechat.yaml).
cat > "$RAIZ/.env" <<FIM
APP_TITLE=EnergyNexus
CUSTOM_FOOTER="EnergyNexus — dados públicos da CVM, ANEEL, ONS, BNDES e EPE"
HOST=0.0.0.0
PORT=3080
DOMAIN_CLIENT=https://$EN_HOSTNAME
DOMAIN_SERVER=https://$EN_HOSTNAME
TRUST_PROXY=1
MONGO_URI=mongodb://mongo:27017/LibreChat
MEILI_HOST=http://meili:7700
SEARCH=true
MEILI_NO_ANALYTICS=true
ALLOW_REGISTRATION=true
ALLOW_EMAIL_LOGIN=true
BAN_VIOLATIONS=false
ENDPOINTS=agents,bedrock
BEDROCK_AWS_DEFAULT_REGION=us-east-1
LOGIN_MAX=100
LOGIN_WINDOW=5
SESSION_EXPIRY=14400000
BUSCA_PORTA=8766
MCP_INIT_TIMEOUT_MS=180000
MCP_TOOLS_LIST_TIMEOUT_MS=120000
FIM
# E os segredos, num parâmetro SecureString só: chaves do LibreChat, Meilisearch, busca web e o usuário do Cognito que
# a ponte do AgentCore usa. Quem descriptografa é o papel da instância.
aws ssm get-parameter --name "$EN_PARAMETRO" --with-decryption --region "$EN_REGIAO" \
  --query Parameter.Value --output text >> "$RAIZ/.env"
chmod 600 "$RAIZ/.env"

echo "== montando o Caddyfile para $EN_HOSTNAME"
cat > "$RAIZ/Caddyfile" <<FIM
{
	admin off
}
$EN_HOSTNAME {
	reverse_proxy chat:3080
}
# quem chegar pelo IP cru vai para o nome com certificado, senão o navegador reclama da senha em texto claro
http://$EN_IP {
	redir https://$EN_HOSTNAME{uri} permanent
}
FIM

echo "== instalando o serviço do systemd"
# É a exigência de "rodar automaticamente": o serviço sobe a pilha no boot. TimeoutStartSec=0 porque o primeiro
# `up --build` constrói a interface do LibreChat (vite) e leva perto de vinte minutos.
#
# O ExecStartPre reagenda o desligamento a cada boot. Sem ele, um `ligar` depois do desligamento automático deixaria a
# instância ligada para sempre: o user-data (que agendou o primeiro) só roda no primeiro boot da máquina.
cat > /etc/systemd/system/energynexus.service <<FIM
[Unit]
Description=EnergyNexus: LibreChat, MongoDB, Meilisearch e Caddy
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
TimeoutStartSec=0
WorkingDirectory=$CODIGO
Environment=COMPOSE_PROJECT_NAME=energynexus
ExecStartPre=/bin/bash -c 'shutdown -c 2>/dev/null || true; shutdown -h +$EN_MINUTOS'
ExecStart=/usr/bin/docker compose --env-file $RAIZ/.env -f infra/compose.yaml up -d --build
ExecStop=/usr/bin/docker compose --env-file $RAIZ/.env -f infra/compose.yaml down

[Install]
WantedBy=multi-user.target
FIM
systemctl daemon-reload
systemctl enable energynexus.service
# --no-block: a construção da imagem não pode prender o cloud-init até o fim
systemctl start --no-block energynexus.service

echo "== partida entregue ao systemd; o chat responde em https://$EN_HOSTNAME quando a imagem terminar"

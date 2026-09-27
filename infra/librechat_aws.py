#!/usr/bin/env python3
"""Sobe o chat EnergyNexus (LibreChat deste fork) numa instância EC2 da conta do workshop, e o controla depois.

Por que EC2 por CloudFormation, e não `aws ec2 run-instances`: a conta é de workshop e o papel WSParticipantRole nega
ec2:RunInstances, ec2:CreateSecurityGroup e até ec2:DescribeInstances (medido, não suposto). O que ela permite é
sts:AssumeRole nos papéis `cdk-*` do bootstrap do CDK — e o `cdk-hnb659fds-deploy-role` pode criar pilha passando o
`cdk-hnb659fds-cfn-exec-role`, que tem AdministratorAccess. Então este script assume o papel de deploy e deixa o
CloudFormation criar, como administrador, o que nós não podemos criar à mão: papel, perfil de instância, grupo de
segurança, IP elástico e a máquina. É o mesmo caminho que o proper_mcps/agentcore/cdk_app.py usa para o AgentCore
(lá o comentário diz "o usuário do hackathon não pode criar o runtime direto, só pelo CloudFormation").

Região us-west-2 porque é lá que estão o bootstrap do CDK, os runtimes do AgentCore e o bucket com os bancos: a
instância baixa ~3 GB do S3 na partida e isso sai de graça e rápido dentro da mesma região.

O que a pilha entrega:
  - EC2 x86_64 (o pdflatex do relatório é x86_64) com Docker e a pilha do infra/compose.yaml;
  - papel da instância com bedrock:InvokeModel (a conversa é pelo Bedrock), leitura dos prefixos do S3 e leitura do
    parâmetro com os segredos — nenhuma chave de acesso copiada para dentro da máquina;
  - IP elástico, para o endereço não mudar, e HTTPS pelo Caddy com hostname <ip>.nip.io;
  - `shutdown -h` agendado na partida, para uma janela esquecida não virar conta no fim do mês;
  - uma função Lambda de uma linha por ação (ligar, desligar, estado), porque o WSParticipantRole não pode chamar
    ec2:StartInstances nem ec2:StopInstances — quem pode é o papel que o CloudFormation criou para ela.

O `.env` e os bancos não estão no git, então os comandos que precisam deles aceitam `--instalacao`, apontando para a
árvore onde o chat roda de verdade (o mesmo argumento do infra/publicar_site.py).

Uso (o venv do repositório já tem o boto3):
  .runtime/venv/bin/python infra/librechat_aws.py subir [--horas 10] [--tipo m7i.xlarge] [--instalacao RAIZ]
  .runtime/venv/bin/python infra/librechat_aws.py estado [--log]
  .runtime/venv/bin/python infra/librechat_aws.py esticar --horas 4
  .runtime/venv/bin/python infra/librechat_aws.py desligar | ligar
  .runtime/venv/bin/python infra/librechat_aws.py apagar

Detalhes, limites da conta e o que fazer quando algo falha: infra/LIBRECHAT_AWS.md
"""
import argparse
import json
import secrets
import subprocess
import sys
import time
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

CONTA = "139382521595"
REGIAO = "us-west-2"
PILHA = "energynexus-chat"
# bucket que já guarda os bancos que os runtimes do AgentCore usam; o código e o placar entram no prefixo `chat/`
BUCKET = f"coppezip-dados-oeste-{CONTA}"
PREFIXO = "chat"
PARAMETRO = "/energynexus/chat/segredos"
PAPEL_DEPLOY = f"arn:aws:iam::{CONTA}:role/cdk-hnb659fds-deploy-role-{CONTA}-{REGIAO}"
PAPEL_EXEC = f"arn:aws:iam::{CONTA}:role/cdk-hnb659fds-cfn-exec-role-{CONTA}-{REGIAO}"
TIPO_PADRAO = "m7i.xlarge"   # 4 vCPU e 16 GB: o `vite build` do client pede NODE_OPTIONS=--max-old-space-size=8192
DISCO_GB = 100               # imagem do chat (~6 GB) + os bancos (~3 GB) + camadas do build
HORAS_PADRAO = 10
# Variáveis do .env da máquina do laboratório que viajam para a instância dentro do parâmetro SecureString. As quatro
# primeiras são regeradas aqui, para a instância pública não compartilhar segredo com o laboratório.
SEGREDOS_NOVOS = {"CREDS_KEY": 32, "CREDS_IV": 16, "JWT_SECRET": 32, "JWT_REFRESH_SECRET": 32, "MEILI_MASTER_KEY": 16}
SEGREDOS_COPIADOS = ["SERPER_API_KEY", "JINA_API_KEY", "ENERGYNEXUS_COGNITO_REGIAO", "ENERGYNEXUS_COGNITO_CLIENTE",
                     "ENERGYNEXUS_COGNITO_USUARIO", "ENERGYNEXUS_COGNITO_SENHA", "ENERGYNEXUS_AGENTCORE_REGIAO",
                     "ENERGYNEXUS_ARN_DADOS", "ENERGYNEXUS_ARN_DOCS"]

RAIZ = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------- credenciais

def sessao_admin():
    """Sessão com o papel de deploy do CDK: é ela que pode criar pilha passando o papel de administrador."""
    creds = boto3.client("sts").assume_role(RoleArn=PAPEL_DEPLOY, RoleSessionName="energynexus-chat")["Credentials"]
    return boto3.Session(aws_access_key_id=creds["AccessKeyId"], aws_secret_access_key=creds["SecretAccessKey"],
                         aws_session_token=creds["SessionToken"], region_name=REGIAO)


def sub_rede() -> tuple:
    """VPC padrão e a sub-rede pública dela com mais endereços livres (a instância precisa de IP público para o ACME).

    A VPC vem junto porque o grupo de segurança tem de dizer em qual VPC nasce: sem `VpcId` o CloudFormation o cria no
    modo antigo, e aí `Ref` devolve o *nome* do grupo em vez do id — o que a EC2 recusa junto com `SubnetId`.
    """
    ec2 = boto3.client("ec2", region_name=REGIAO)
    vpcs = [v["VpcId"] for v in ec2.describe_vpcs()["Vpcs"] if v.get("IsDefault")]
    if not vpcs:
        raise SystemExit(f"não há VPC padrão em {REGIAO}: passe a sub-rede à mão no template")
    publicas = [s for s in ec2.describe_subnets()["Subnets"]
                if s["VpcId"] == vpcs[0] and s["MapPublicIpOnLaunch"]]
    if not publicas:
        raise SystemExit(f"a VPC padrão {vpcs[0]} não tem sub-rede que dê IP público")
    return vpcs[0], max(publicas, key=lambda s: s["AvailableIpAddressCount"])["SubnetId"]


# ---------------------------------------------------------------- artefatos

def empacotar() -> str:
    """Manda o código do fork para um prefixo privado do S3 e devolve a chave.

    `git archive` em vez de cópia da árvore: leva exatamente o que está versionado, sem .env, sem .runtime/ e sem os
    bancos. O repositório é privado, então a instância o baixa com o papel dela, não com um token de clone.
    """
    commit = subprocess.run(["git", "-C", str(RAIZ), "rev-parse", "--short", "HEAD"],
                            capture_output=True, text=True, check=True).stdout.strip()
    sujo = subprocess.run(["git", "-C", str(RAIZ), "status", "--porcelain"],
                          capture_output=True, text=True, check=True).stdout.strip()
    if sujo:
        print(f"aviso: há mudança não comitada; o pacote leva o commit {commit} e ignora o resto:\n{sujo}")
    tar = subprocess.run(["git", "-C", str(RAIZ), "archive", "--format=tar.gz", "HEAD"],
                         capture_output=True, check=True).stdout
    chave = f"{PREFIXO}/codigo/energynexus-{time.strftime('%Y%m%d-%H%M%S')}-{commit}.tar.gz"
    boto3.client("s3").put_object(Bucket=BUCKET, Key=chave, Body=tar)
    print(f"código: s3://{BUCKET}/{chave} ({len(tar) / 1e6:.1f} MB, commit {commit})")
    return chave


def enviar_bancos(instalacao: Path):
    """Sobe o que só existe na máquina do laboratório. O resto dos bancos já está no bucket, de `bancos/`."""
    s3 = boto3.client("s3")
    for origem, chave in [(instalacao / "data/placar.duckdb", f"{PREFIXO}/dados/placar.duckdb"),
                          (instalacao / "data/painel.json", f"{PREFIXO}/dados/painel.json")]:
        if not origem.exists():
            raise SystemExit(f"falta {origem}: o MCP do placar e a aba Painel não funcionam sem ele")
        s3.upload_file(str(origem), BUCKET, chave)
        print(f"dados: s3://{BUCKET}/{chave} ({origem.stat().st_size / 1e6:.1f} MB)")


def guardar_segredos(instalacao: Path):
    """Grava num parâmetro SecureString do SSM o que a instância precisa e não pode estar no git."""
    bruto = (instalacao / ".env").read_text(encoding="utf-8")
    valores = {}
    for linha in bruto.splitlines():
        if "=" in linha and not linha.lstrip().startswith("#"):
            nome, _, valor = linha.partition("=")
            valores[nome.strip()] = valor.split("#")[0].strip()
    linhas = [f"{nome}={secrets.token_hex(tamanho)}" for nome, tamanho in SEGREDOS_NOVOS.items()]
    for nome in SEGREDOS_COPIADOS:
        if nome not in valores:
            raise SystemExit(f"falta {nome} no .env: sem ele a instância sobe sem a ponte do AgentCore ou sem a busca")
        linhas.append(f"{nome}={valores[nome]}")
    corpo = "\n".join(linhas) + "\n"
    if len(corpo) > 4096:
        raise SystemExit(f"os segredos somam {len(corpo)} bytes e o SSM padrão aceita 4096: reveja a lista")
    boto3.client("ssm", region_name=REGIAO).put_parameter(
        Name=PARAMETRO, Value=corpo, Type="SecureString", Overwrite=True,
        Description="Segredos do chat EnergyNexus na EC2 (gerado por infra/librechat_aws.py)")
    print(f"segredos: {PARAMETRO} ({len(linhas)} variáveis, {len(corpo)} bytes, SecureString)")


# ---------------------------------------------------------------- template

USER_DATA = """#!/bin/bash
set -euo pipefail
exec > >(tee -a /var/log/energynexus-partida.log) 2>&1
echo "== user-data $(date -Is)"
# O desligamento é agendado antes de tudo: uma partida que falhe no meio não deixa a instância ligada a noite inteira.
shutdown -h +${Minutos}
dnf install -y tar gzip
mkdir -p /opt/energynexus/codigo
aws s3 cp s3://${Bucket}/${Codigo} /tmp/codigo.tar.gz --region ${Regiao} --only-show-errors
tar -xzf /tmp/codigo.tar.gz -C /opt/energynexus/codigo
export EN_BUCKET=${Bucket} EN_REGIAO=${Regiao} EN_PREFIXO=${Prefixo} EN_PARAMETRO=${Parametro} EN_IP=${IP}
export EN_MINUTOS=${Minutos}
exec bash /opt/energynexus/codigo/infra/partida_ec2.sh
"""

OPERACAO = '''
import os

import boto3

INSTANCIA = os.environ["INSTANCIA"]


def handler(evento, contexto):
    """Liga, desliga ou apenas conta o estado da instância do chat. O WSParticipantRole não pode fazer isto direto."""
    ec2 = boto3.client("ec2")
    acao = evento.get("acao", "estado")
    if acao == "ligar":
        ec2.start_instances(InstanceIds=[INSTANCIA])
    elif acao == "desligar":
        ec2.stop_instances(InstanceIds=[INSTANCIA])
    elif acao != "estado":
        raise ValueError(f"ação desconhecida: {acao}")
    maquina = ec2.describe_instances(InstanceIds=[INSTANCIA])["Reservations"][0]["Instances"][0]
    return {"acao": acao, "estado": maquina["State"]["Name"], "ip": maquina.get("PublicIpAddress")}
'''


def template(vpc_id: str, sub_rede_id: str, tipo: str) -> str:
    """Pilha do CloudFormation. JSON e não YAML porque quem a escreve é este script, não uma pessoa."""
    return json.dumps({
        "AWSTemplateFormatVersion": "2010-09-09",
        "Description": "Chat EnergyNexus (LibreChat) numa EC2 com Docker, MongoDB, Meilisearch e Caddy",
        "Parameters": {
            "Codigo": {"Type": "String", "Description": "chave no S3 do tar.gz do fork"},
            "Minutos": {"Type": "Number", "Description": "janela antes do shutdown automático"},
            "Imagem": {"Type": "AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>",
                       "Default": "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"},
        },
        "Resources": {
            # Papel da instância: o mínimo para a conversa e para a partida. A ponte do AgentCore não aparece aqui de
            # propósito — ela se autentica com JWT do Cognito (USER_PASSWORD_AUTH), sem assinar nada com credencial da
            # AWS, então bedrock-agentcore:InvokeAgentRuntime seria permissão sem uso (ver proper_mcps/agentcore/PONTE.md).
            "Papel": {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "AssumeRolePolicyDocument": {"Version": "2012-10-17", "Statement": [{
                        "Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"},
                        "Action": "sts:AssumeRole"}]},
                    # AmazonSSMManagedInstanceCore: é por Session Manager e SendCommand que se entra na máquina, porque
                    # a conta não permite criar par de chaves e o grupo de segurança não abre a 22.
                    "ManagedPolicyArns": ["arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"],
                    "Policies": [{"PolicyName": "chat", "PolicyDocument": {"Version": "2012-10-17", "Statement": [
                        {"Sid": "ConversaNoBedrock", "Effect": "Allow",
                         "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                         "Resource": "*"},
                        {"Sid": "BancosECodigo", "Effect": "Allow", "Action": "s3:GetObject",
                         "Resource": [f"arn:aws:s3:::{BUCKET}/bancos/*", f"arn:aws:s3:::{BUCKET}/{PREFIXO}/*"]},
                        {"Sid": "ListarBucket", "Effect": "Allow", "Action": "s3:ListBucket",
                         "Resource": f"arn:aws:s3:::{BUCKET}"},
                        {"Sid": "Segredos", "Effect": "Allow", "Action": "ssm:GetParameter",
                         "Resource": f"arn:aws:ssm:{REGIAO}:{CONTA}:parameter{PARAMETRO}"},
                        # o SecureString é cifrado com a chave gerenciada alias/aws/ssm; sem kms:Decrypt o
                        # get-parameter --with-decryption falha
                        {"Sid": "DecifrarSegredos", "Effect": "Allow", "Action": "kms:Decrypt", "Resource": "*",
                         "Condition": {"StringEquals": {"kms:ViaService": f"ssm.{REGIAO}.amazonaws.com"}}},
                    ]}}],
                },
            },
            "Perfil": {"Type": "AWS::IAM::InstanceProfile", "Properties": {"Roles": [{"Ref": "Papel"}]}},
            "Grupo": {
                "Type": "AWS::EC2::SecurityGroup",
                "Properties": {
                    "GroupDescription": "Chat EnergyNexus: 80 e 443 para o mundo",
                    "VpcId": vpc_id,
                    "SecurityGroupIngress": [
                        # 80 fica aberta pelo desafio HTTP-01 do ACME e para redirecionar quem chega pelo IP cru
                        {"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "CidrIp": "0.0.0.0/0",
                         "Description": "ACME e redirecionamento para o HTTPS"},
                        {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "CidrIp": "0.0.0.0/0",
                         "Description": "o chat"},
                    ],
                },
            },
            # O IP é reservado sem a instância e associado depois: assim o user-data pode citar o endereço (o hostname
            # do certificado sai dele) sem a pilha virar uma dependência circular.
            "IP": {"Type": "AWS::EC2::EIP", "Properties": {"Domain": "vpc"}},
            "Maquina": {
                "Type": "AWS::EC2::Instance",
                "Properties": {
                    "ImageId": {"Ref": "Imagem"},
                    "InstanceType": tipo,
                    "SubnetId": sub_rede_id,
                    "IamInstanceProfile": {"Ref": "Perfil"},
                    "SecurityGroupIds": [{"Fn::GetAtt": ["Grupo", "GroupId"]}],
                    # `stop` e não `terminate`: o shutdown automático tem de poder ser desfeito com um `ligar`
                    "InstanceInitiatedShutdownBehavior": "stop",
                    "BlockDeviceMappings": [{"DeviceName": "/dev/xvda", "Ebs": {
                        "VolumeSize": DISCO_GB, "VolumeType": "gp3", "DeleteOnTermination": True}}],
                    # HttpPutResponseHopLimit 2: sem isso os contêineres não alcançam o IMDS e o Bedrock fica sem
                    # credencial (o padrão 1 só serve para processos do próprio host)
                    "MetadataOptions": {"HttpEndpoint": "enabled", "HttpTokens": "required",
                                        "HttpPutResponseHopLimit": 2},
                    "UserData": {"Fn::Base64": {"Fn::Sub": [USER_DATA, {
                        "Bucket": BUCKET, "Regiao": REGIAO, "Prefixo": PREFIXO, "Parametro": PARAMETRO}]}},
                    "Tags": [{"Key": "Name", "Value": PILHA}],
                },
            },
            "Associacao": {"Type": "AWS::EC2::EIPAssociation", "Properties": {
                "AllocationId": {"Fn::GetAtt": ["IP", "AllocationId"]}, "InstanceId": {"Ref": "Maquina"}}},
            "PapelOperacao": {
                "Type": "AWS::IAM::Role",
                "Properties": {
                    "AssumeRolePolicyDocument": {"Version": "2012-10-17", "Statement": [{
                        "Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole"}]},
                    "ManagedPolicyArns": ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"],
                    "Policies": [{"PolicyName": "operacao", "PolicyDocument": {"Version": "2012-10-17", "Statement": [{
                        "Effect": "Allow",
                        "Action": ["ec2:StartInstances", "ec2:StopInstances", "ec2:DescribeInstances"],
                        "Resource": "*"}]}}],
                },
            },
            "Operacao": {
                "Type": "AWS::Lambda::Function",
                "Properties": {
                    "FunctionName": f"{PILHA}-operacao",
                    "Runtime": "python3.13", "Handler": "index.handler", "Timeout": 30,
                    "Role": {"Fn::GetAtt": ["PapelOperacao", "Arn"]},
                    "Environment": {"Variables": {"INSTANCIA": {"Ref": "Maquina"}}},
                    "Code": {"ZipFile": OPERACAO},
                },
            },
        },
        "Outputs": {
            "Ip": {"Value": {"Ref": "IP"}},
            "Url": {"Value": {"Fn::Sub": "https://${IP}.nip.io"}},
            "Instancia": {"Value": {"Ref": "Maquina"}},
            "Operacao": {"Value": {"Ref": "Operacao"}},
        },
    })


# ---------------------------------------------------------------- comandos

def saidas() -> dict:
    """Saídas da pilha. cloudformation:Describe* o WSParticipantRole já tem, sem assumir papel nenhum."""
    cf = boto3.client("cloudformation", region_name=REGIAO)
    try:
        pilha = cf.describe_stacks(StackName=PILHA)["Stacks"][0]
    except ClientError as e:
        if "does not exist" in str(e):
            raise SystemExit(f"a pilha {PILHA} não existe: rode `subir` primeiro")
        raise
    return {"estado": pilha["StackStatus"], **{s["OutputKey"]: s["OutputValue"] for s in pilha.get("Outputs", [])}}


def esperar(cf, alvos: tuple) -> str:
    """Acompanha a pilha até o estado final, mostrando cada recurso que fecha."""
    vistos = set()
    while True:
        pilha = cf.describe_stacks(StackName=PILHA)["Stacks"][0]
        for e in reversed(cf.describe_stack_events(StackName=PILHA)["StackEvents"]):
            if e["EventId"] in vistos:
                continue
            vistos.add(e["EventId"])
            if e["ResourceStatus"].endswith(("_FAILED", "_COMPLETE")):
                razao = e.get("ResourceStatusReason", "")
                print(f"  {e['ResourceStatus']:24} {e['LogicalResourceId']:16} {razao[:110]}")
        if pilha["StackStatus"] in alvos or pilha["StackStatus"].endswith(("_COMPLETE", "_FAILED")):
            return pilha["StackStatus"]
        time.sleep(6)


def existe_pilha() -> bool:
    """Diz se há pilha para atualizar. Um ROLLBACK_COMPLETE não conta: o CloudFormation só aceita apagá-lo."""
    try:
        pilha = boto3.client("cloudformation", region_name=REGIAO).describe_stacks(StackName=PILHA)["Stacks"][0]
        if pilha["StackStatus"] == "ROLLBACK_COMPLETE":
            print("a pilha anterior morreu na criação (ROLLBACK_COMPLETE); apagando o esqueleto antes de recriar")
            cf = sessao_admin().client("cloudformation")
            cf.delete_stack(StackName=PILHA, RoleARN=PAPEL_EXEC)
            esperar(cf, ("DELETE_COMPLETE",))
            return False
        return True
    except ClientError as e:
        if "does not exist" in str(e):
            return False
        raise


def subir(args):
    instalacao = Path(args.instalacao).resolve()
    enviar_bancos(instalacao)
    guardar_segredos(instalacao)
    chave = empacotar()
    vpc, rede = sub_rede()
    print(f"VPC {vpc}, sub-rede pública {rede}; tipo {args.tipo}; janela de {args.horas} h")
    corpo = template(vpc, rede, args.tipo)
    cf = sessao_admin().client("cloudformation")
    parametros = [{"ParameterKey": "Codigo", "ParameterValue": chave},
                  {"ParameterKey": "Minutos", "ParameterValue": str(int(args.horas * 60))}]
    comum = dict(StackName=PILHA, TemplateBody=corpo, Parameters=parametros,
                 Capabilities=["CAPABILITY_IAM"], RoleARN=PAPEL_EXEC)
    existe = existe_pilha()
    print(f"{'atualizando' if existe else 'criando'} a pilha {PILHA} com o papel de administrador do CDK")
    (cf.update_stack if existe else cf.create_stack)(**comum)
    final = esperar(cf, ("CREATE_COMPLETE", "UPDATE_COMPLETE"))
    print(f"pilha: {final}")
    if not final.endswith("_COMPLETE") or "ROLLBACK" in final:
        raise SystemExit("a pilha não fechou; veja os eventos acima")
    fora = saidas()
    print(f"\nIP {fora['Ip']}  |  instância {fora['Instancia']}")
    print(f"URL {fora['Url']}")
    print("a máquina agora constrói a imagem do chat (~20 min). Acompanhe com:\n"
          f"  {sys.argv[0]} estado --log")


def estado(args):
    fora = saidas()
    print(f"pilha {fora['estado']}  |  IP {fora.get('Ip')}  |  {fora.get('Url')}")
    resposta = boto3.client("lambda", region_name=REGIAO).invoke(
        FunctionName=fora["Operacao"], Payload=json.dumps({"acao": "estado"}).encode())
    print("instância:", json.loads(resposta["Payload"].read()))
    if args.log:
        print(remoto(fora["Instancia"], "tail -n 40 /var/log/energynexus-partida.log; "
                                        "systemctl is-active energynexus.service; docker ps --format '{{.Names}} "
                                        "{{.Status}}'"))


def remoto(instancia: str, comando: str) -> str:
    """Roda um comando na instância por SSM (ssm:* o WSParticipantRole tem; a 22 nem está aberta)."""
    ssm = boto3.client("ssm", region_name=REGIAO)
    ident = ssm.send_command(InstanceIds=[instancia], DocumentName="AWS-RunShellScript",
                             Parameters={"commands": [comando]})["Command"]["CommandId"]
    while True:
        time.sleep(3)
        r = ssm.get_command_invocation(CommandId=ident, InstanceId=instancia)
        if r["Status"] not in ("Pending", "InProgress", "Delayed"):
            return (r["StandardOutputContent"] + r["StandardErrorContent"]).strip()


def esticar(args):
    fora = saidas()
    minutos = int(args.horas * 60)
    # `shutdown -c` só falha quando não havia nada agendado, e aí o `|| true` deixa seguir. O horário marcado fica em
    # /run/systemd/shutdown/scheduled, que é a prova de que pegou.
    print(remoto(fora["Instancia"], f"shutdown -c 2>/dev/null || true; shutdown -h +{minutos}; sleep 1; "
                                    "echo -n 'agora: '; date -Is; cat /run/systemd/shutdown/scheduled"))
    print(f"janela esticada: a instância desliga em {args.horas} h a partir de agora "
          f"(USEC no arquivo acima é microssegundo desde 1970)")


def ligar_desligar(args):
    fora = saidas()
    resposta = boto3.client("lambda", region_name=REGIAO).invoke(
        FunctionName=fora["Operacao"], Payload=json.dumps({"acao": args.comando}).encode())
    print(json.loads(resposta["Payload"].read()))
    if args.comando == "ligar":
        print(f"o systemd sobe a pilha sozinho no boot; o chat volta em {fora['Url']} em poucos minutos")


def apagar(args):
    fora = saidas()
    print(f"apagando a pilha {PILHA} (instância {fora.get('Instancia')}, IP {fora.get('Ip')})")
    cf = sessao_admin().client("cloudformation")
    cf.delete_stack(StackName=PILHA, RoleARN=PAPEL_EXEC)
    try:
        print("pilha:", esperar(cf, ("DELETE_COMPLETE",)))
    except ClientError as e:
        print("pilha: DELETE_COMPLETE" if "does not exist" in str(e) else f"erro: {e}")
    boto3.client("ssm", region_name=REGIAO).delete_parameter(Name=PARAMETRO)
    print(f"parâmetro {PARAMETRO} apagado. O código e os bancos ficam em s3://{BUCKET}/{PREFIXO}/ "
          f"(apague à mão se quiser: aws s3 rm --recursive)")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="comando", required=True)
    s = sub.add_parser("subir", help="cria ou atualiza a pilha e publica o código e os bancos")
    s.add_argument("--horas", type=float, default=HORAS_PADRAO)
    s.add_argument("--tipo", default=TIPO_PADRAO)
    s.add_argument("--instalacao", default=str(RAIZ),
                   help="árvore com o .env e os bancos em data/ (o git não os tem)")
    s.set_defaults(func=subir)
    s = sub.add_parser("estado", help="estado da pilha, da instância e (com --log) da partida")
    s.add_argument("--log", action="store_true")
    s.set_defaults(func=estado)
    s = sub.add_parser("esticar", help="reagenda o desligamento automático")
    s.add_argument("--horas", type=float, required=True)
    s.set_defaults(func=esticar)
    sub.add_parser("desligar", help="para a instância agora (o disco fica)").set_defaults(func=ligar_desligar)
    sub.add_parser("ligar", help="liga de novo; o systemd sobe a pilha").set_defaults(func=ligar_desligar)
    sub.add_parser("apagar", help="apaga a pilha e o parâmetro com os segredos").set_defaults(func=apagar)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

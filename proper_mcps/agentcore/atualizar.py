"""Republica os três MCP do CoppeZIP (dados, docs, relatorio) no Amazon Bedrock AgentCore Runtime e testa o que subiu.

Uso (da raiz do repositório, com um Python que tenha boto3 e pip):
  COGNITO_USUARIO=... COGNITO_SENHA=... .runtime/venv/bin/python proper_mcps/agentcore/atualizar.py
  --dados          envia também os bancos de data/ para o bucket (sem isso, só confere que estão lá)
  --somente-teste  não republica nada: só chama as ferramentas do que já está no ar

Passos: monta o pacote (bibliotecas para ARM64 + proper_mcps/ no mesmo layout do repositório) em
.runtime/agentcore/coppezip-mcp.zip, envia com uma chave datada (o bucket não tem versionamento e o CloudFormation
ignora a atualização se a chave não muda), reenvia a configuração inteira de cada runtime trocando só o zip
(update_agent_runtime substitui a configuração, não corrige campo a campo: o que não for reenviado se perde), espera
cada um ficar READY e chama tools/list e uma ferramenta de verdade nos três.

Autenticação: só `Authorization: Bearer <JWT do Cognito>`. SigV4 é recusado ("Authorization method mismatch"),
inclusive pelo invoke_agent_runtime do boto3, e o user pool não tem domínio nem segredo no app client, logo não existe
client_credentials: o token sai de USER_PASSWORD_AUTH com COGNITO_USUARIO/COGNITO_SENHA (dura 24 h).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # raiz do repositório

REGIAO = "us-west-2"
BUCKET = "coppezip-dados-oeste-139382521595"
QUAIS = ("dados", "docs", "relatorio")
# banco que cada runtime baixa do bucket na subida (o relatorio não usa banco) e de onde ele vem no repositório
BANCOS = {"bancos/coppezip.duckdb": "data/coppezip.duckdb", "bancos/docs_titan.duckdb": "data/docs_titan.duckdb"}
BIBLIOTECAS = ["duckdb==1.5.5", "mcp==2.2.0", "boto3"]  # o que os servidores importam, em roda ARM64
PLATAFORMAS = ["manylinux_2_28_aarch64", "manylinux_2_17_aarch64", "manylinux2014_aarch64"]
EMBEDDINGS = f"arn:aws:bedrock:{REGIAO}::foundation-model/amazon.titan-embed-text-v2:0"  # perguntas do coppezip-docs
ESPERA = 900  # segundos de paciência para um runtime ficar READY
TRANSFERENCIA = TransferConfig(multipart_threshold=64 * 1024 * 1024, multipart_chunksize=64 * 1024 * 1024)

# uma chamada de verdade por servidor, para provar que o código novo responde (e não só que o runtime está READY)
TESTES = {
    "dados": ("listar_tabelas", {}),
    "docs": ("buscar_documentos", {"consulta": "metas de redução de emissões de gases de efeito estufa", "k": 2}),
    "relatorio": ("gerar_relatorio", {
        "titulo": "Teste de fumaça do coppezip-relatorio",
        "sumario": "Relatório gerado por proper_mcps/agentcore/atualizar.py para conferir o runtime recém-publicado.",
        "secoes": [{"titulo": "Verificação", "texto": "O servidor gravou Markdown e DOCX e publicou os dois no S3 "
                                                     "com link assinado [F1]."}],
        "fontes": [{"id": "F1", "descricao": "proper_mcps/agentcore/atualizar.py, teste de fumaça"}]}),
}

controle = boto3.client("bedrock-agentcore-control", region_name=REGIAO)
s3 = boto3.client("s3", region_name=REGIAO)


def log(mensagem: str):
    print(f"{datetime.now():%H:%M:%S} {mensagem}", flush=True)


def configuracoes() -> dict:
    """Configuração atual dos três runtimes, achados pelo nome (coppezip_dados, coppezip_docs, coppezip_relatorio)."""
    ids = {}
    proximo = None
    while True:
        pagina = controle.list_agent_runtimes(**({"nextToken": proximo} if proximo else {}))
        ids.update({r["agentRuntimeName"]: r["agentRuntimeId"] for r in pagina["agentRuntimes"]})
        proximo = pagina.get("nextToken")
        if not proximo:
            break
    achados = {}
    for qual in QUAIS:
        nome = f"coppezip_{qual}"
        if nome not in ids:
            raise SystemExit(f"não existe runtime {nome} em {REGIAO}: crie pelo proper_mcps/agentcore/cdk_app.py")
        achados[qual] = controle.get_agent_runtime(agentRuntimeId=ids[nome])
    return achados


def token(configuracao: dict) -> str:
    """Token do Cognito (USER_PASSWORD_AUTH) no pool e no app client que o próprio runtime aceita."""
    jwt = configuracao["authorizerConfiguration"]["customJWTAuthorizer"]
    pool = urllib.parse.urlparse(jwt["discoveryUrl"]).path.strip("/").split("/")[0]
    cliente = jwt["allowedClients"][0]
    usuario, senha = os.environ.get("COGNITO_USUARIO"), os.environ.get("COGNITO_SENHA")
    for nome, valor in (("COGNITO_USUARIO", usuario), ("COGNITO_SENHA", senha)):
        if not valor:
            raise SystemExit(f"falta a variável de ambiente {nome} (usuário do user pool {pool} do Cognito)")
    cognito = boto3.client("cognito-idp", region_name=pool.split("_")[0])
    resposta = cognito.initiate_auth(ClientId=cliente, AuthFlow="USER_PASSWORD_AUTH",
                                     AuthParameters={"USERNAME": usuario, "PASSWORD": senha})
    log(f"token do Cognito para {usuario} em {pool}, válido por {resposta['AuthenticationResult']['ExpiresIn']} s")
    return resposta["AuthenticationResult"]["AccessToken"]


def bancos(subir: bool):
    """Os runtimes baixam os bancos do bucket ao subir: sem eles as ferramentas respondem erro."""
    for chave, local in BANCOS.items():
        caminho = os.path.join(RAIZ, local)
        if subir:
            if not os.path.exists(caminho):
                monta = "data/indexar_docs_titan.py" if "docs" in chave else "data/construir.py"
                raise SystemExit(f"falta {local} para enviar a {chave}: monte com {monta}")
            log(f"enviando {local} ({os.path.getsize(caminho) / 1e6:.0f} MB) para s3://{BUCKET}/{chave}")
            s3.upload_file(caminho, BUCKET, chave, Config=TRANSFERENCIA)
        else:
            try:
                objeto = s3.head_object(Bucket=BUCKET, Key=chave)
            except ClientError as erro:
                raise SystemExit(f"falta s3://{BUCKET}/{chave}: envie com --dados (precisa de {local})") from erro
            log(f"s3://{BUCKET}/{chave}: {objeto['ContentLength'] / 1e6:.0f} MB, "
                f"de {objeto['LastModified']:%d/%m %H:%M}")


def permitir_embeddings(role_arn: str):
    """O coppezip-docs embute a pergunta com o Titan pelo Bedrock; a role do runtime só tem S3 e logs por padrão."""
    role = role_arn.split("/")[-1]
    politica = {"Version": "2012-10-17",
                "Statement": [{"Effect": "Allow", "Action": "bedrock:InvokeModel", "Resource": EMBEDDINGS}]}
    boto3.client("iam").put_role_policy(RoleName=role, PolicyName="embeddings-titan",
                                        PolicyDocument=json.dumps(politica))
    log(f"role {role}: política embeddings-titan garantida ({EMBEDDINGS.split('/')[-1]})")


def empacotar() -> str:
    """Bibliotecas para ARM64 mais proper_mcps/ no layout do repositório; devolve o caminho do zip."""
    destino = os.path.join(RAIZ, ".runtime", "agentcore")
    pacote = os.path.join(destino, "pacote")
    shutil.rmtree(pacote, ignore_errors=True)
    os.makedirs(os.path.join(pacote, "proper_mcps"))
    pip = [sys.executable, "-m", "pip", "install", "-q", "--target", pacote, "--python-version", "3.12",
           "--implementation", "cp", "--only-binary=:all:"]
    for plataforma in PLATAFORMAS:
        pip += ["--platform", plataforma]
    log(f"instalando {' '.join(BIBLIOTECAS)} para ARM64 em {os.path.relpath(pacote, RAIZ)}")
    subprocess.run(pip + BIBLIOTECAS, check=True)
    # o servidor.py é o ponto de entrada e importa proper_mcps/<qual>/server.py; testes e scripts ficam fora
    fora = shutil.ignore_patterns("__pycache__", "test_*.py", "atualizar.py", "cdk_app.py")
    for pasta in ("agentcore",) + QUAIS:
        shutil.copytree(os.path.join(RAIZ, "proper_mcps", pasta), os.path.join(pacote, "proper_mcps", pasta),
                        ignore=fora)
    caminho = os.path.join(destino, "coppezip-mcp.zip")
    if os.path.exists(caminho):
        os.remove(caminho)
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as zipado:
        for pasta, _, arquivos in os.walk(pacote):
            for arquivo in arquivos:
                completo = os.path.join(pasta, arquivo)
                zipado.write(completo, os.path.relpath(completo, pacote))
    log(f"pacote {os.path.relpath(caminho, RAIZ)}: {os.path.getsize(caminho) / 1e6:.0f} MB")
    return caminho


def enviar(caminho: str) -> str:
    """Envia o zip com uma chave datada: o bucket não tem versionamento e a chave nova é o que marca a versão nova."""
    chave = f"codigo/coppezip-mcp-{datetime.now():%Y%m%d-%H%M}.zip"
    s3.upload_file(caminho, BUCKET, chave, Config=TRANSFERENCIA)
    log(f"código em s3://{BUCKET}/{chave}")
    return chave


def republicar(qual: str, configuracao: dict, chave: str) -> str:
    """Reenvia a configuração inteira trocando só o zip; devolve a versão nova do runtime."""
    artefato = configuracao["agentRuntimeArtifact"]
    artefato["codeConfiguration"]["code"]["s3"] = {"bucket": BUCKET, "prefix": chave}
    resposta = controle.update_agent_runtime(
        agentRuntimeId=configuracao["agentRuntimeId"], agentRuntimeArtifact=artefato,
        roleArn=configuracao["roleArn"], networkConfiguration=configuracao["networkConfiguration"],
        protocolConfiguration=configuracao["protocolConfiguration"],
        authorizerConfiguration=configuracao["authorizerConfiguration"],
        environmentVariables=configuracao["environmentVariables"], description=configuracao["description"],
        lifecycleConfiguration=configuracao["lifecycleConfiguration"],
        metadataConfiguration=configuracao["metadataConfiguration"], platformVersion=configuracao["platformVersion"])
    log(f"coppezip_{qual}: versão {resposta['agentRuntimeVersion']} ({resposta['status']})")
    return resposta["agentRuntimeVersion"]


def esperar(qual: str, identificador: str, versao: str):
    """Espera o runtime e o endpoint DEFAULT ficarem READY na versão nova."""
    limite = time.time() + ESPERA
    situacao = "?"
    while time.time() < limite:
        runtime = controle.get_agent_runtime(agentRuntimeId=identificador)
        endpoint = controle.list_agent_runtime_endpoints(agentRuntimeId=identificador)["runtimeEndpoints"]
        default = next((e for e in endpoint if e["name"] == "DEFAULT"), None)
        if not default:
            raise SystemExit(f"coppezip_{qual} não tem endpoint DEFAULT")
        situacao = f"runtime {runtime['status']}, endpoint {default['status']} na versão {default.get('liveVersion')}"
        if runtime["status"] == "READY" and default["status"] == "READY" and default.get("liveVersion") == versao:
            log(f"coppezip_{qual}: {situacao}")
            return
        if "FAILED" in runtime["status"] or "FAILED" in default["status"]:
            raise SystemExit(f"coppezip_{qual} falhou: {situacao}; veja /aws/bedrock-agentcore/runtimes/"
                             f"{identificador}-DEFAULT em {REGIAO}")
        time.sleep(10)
    raise SystemExit(f"coppezip_{qual} não ficou READY na versão {versao} em {ESPERA} s: {situacao}")


def chamar(arn: str, jwt: str, metodo: str, parametros: dict | None = None) -> dict:
    """Uma chamada MCP no endpoint DEFAULT. O servidor é stateless: não precisa de initialize nem de sessão."""
    url = (f"https://bedrock-agentcore.{REGIAO}.amazonaws.com/runtimes/{urllib.parse.quote(arn, safe='')}"
           "/invocations?qualifier=DEFAULT")
    corpo = {"jsonrpc": "2.0", "id": 1, "method": metodo}
    if parametros is not None:
        corpo["params"] = parametros
    pedido = urllib.request.Request(url, data=json.dumps(corpo).encode(), method="POST", headers={
        "Authorization": f"Bearer {jwt}", "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"})
    try:
        with urllib.request.urlopen(pedido, timeout=600) as http:  # a primeira chamada baixa o banco do S3
            texto = http.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as erro:
        raise SystemExit(f"{metodo} em {arn}: HTTP {erro.code} {erro.read().decode('utf-8', 'replace')[:400]}")
    linhas = [l[6:] for l in texto.splitlines() if l.startswith("data: ")]  # a resposta vem em SSE
    if not linhas:
        raise SystemExit(f"{metodo} em {arn} não devolveu evento data:: {texto[:400]}")
    resposta = json.loads(linhas[-1])
    if "error" in resposta:
        raise SystemExit(f"{metodo} em {arn}: {json.dumps(resposta['error'], ensure_ascii=False)[:400]}")
    return resposta["result"]


def testar(qual: str, arn: str, jwt: str):
    """tools/list e uma chamada de verdade, com a resposta na tela."""
    ferramentas = [f["name"] for f in chamar(arn, jwt, "tools/list")["tools"]]
    log(f"coppezip_{qual} tools/list: {', '.join(ferramentas)}")
    nome, argumentos = TESTES[qual]
    if nome not in ferramentas:
        raise SystemExit(f"coppezip_{qual} não expõe {nome}: só {', '.join(ferramentas)}")
    resultado = chamar(arn, jwt, "tools/call", {"name": nome, "arguments": argumentos})
    conteudo = "\n".join(p.get("text", "") for p in resultado.get("content", []))
    if resultado.get("isError"):
        raise SystemExit(f"coppezip_{qual} {nome} devolveu erro: {conteudo[:800]}")
    log(f"coppezip_{qual} {nome}({json.dumps(argumentos, ensure_ascii=False)[:120]}):")
    print(conteudo[:1600] + ("..." if len(conteudo) > 1600 else ""), flush=True)


def main():
    opcoes = argparse.ArgumentParser(description="republica os MCP do CoppeZIP no Bedrock AgentCore e os testa")
    opcoes.add_argument("--dados", action="store_true", help="envia também os bancos de data/ para o bucket")
    opcoes.add_argument("--somente-teste", action="store_true", help="não republica: só testa o que está no ar")
    escolhas = opcoes.parse_args()

    achados = configuracoes()
    jwt = token(achados["dados"])  # falta de usuário/senha para o teste tem de aparecer antes de publicar
    if not escolhas.somente_teste:
        bancos(escolhas.dados)
        permitir_embeddings(achados["docs"]["roleArn"])
        chave = enviar(empacotar())
        versoes = {qual: republicar(qual, achados[qual], chave) for qual in QUAIS}
        for qual in QUAIS:
            esperar(qual, achados[qual]["agentRuntimeId"], versoes[qual])
    for qual in QUAIS:
        testar(qual, achados[qual]["agentRuntimeArn"], jwt)
    log("os três runtimes responderam")


if __name__ == "__main__":
    main()

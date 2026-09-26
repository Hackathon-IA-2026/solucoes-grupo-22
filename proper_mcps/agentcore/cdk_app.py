"""Cria no Bedrock AgentCore Runtime os MCP coppezip-dados, coppezip-docs e coppezip-relatorio (pelo CDK: o usuário do hackathon não pode criar o runtime
direto, só pelo CloudFormation). O código (um zip só para os três) vem do S3, enviado por atualizar.py — que também
republica o código nos runtimes que já existem, sem CloudFormation.

Uso (em proper_mcps/agentcore/), na região em que o CDK está preparado e o bucket existe:
  npx aws-cdk deploy --app "python3 cdk_app.py" -c regiao=<região> -c bucket=<bucket> -c pool=<user pool> -c cliente=<app client>
O user pool do Cognito pode estar em outra região: a região dele sai do próprio ID (us-east-1_...).
"""
import aws_cdk as cdk
from aws_cdk import aws_bedrockagentcore as agentcore

app = cdk.App()
regiao, bucket, pool, cliente = (app.node.get_context(k) for k in ("regiao", "bucket", "pool", "cliente"))
pilha = cdk.Stack(app, "CoppeZIPMcp", env=cdk.Environment(region=regiao))
conta = pilha.account
DESCRICOES = {"dados": "banco com CVM, ANEEL, ONS, BNDES e ANBIMA", "docs": "busca nos relatórios das empresas (PDF)",
             "relatorio": "relatório em Markdown e Word com as fontes conferidas"}
for qual, descricao in DESCRICOES.items():
    runtime = agentcore.CfnRuntime(
        pilha, qual.capitalize(), agent_runtime_name=f"coppezip_{qual}", description=f"MCP coppezip-{qual}: {descricao}",
        agent_runtime_artifact={"codeConfiguration": {
            "code": {"s3": {"bucket": bucket, "prefix": "codigo/coppezip-mcp.zip"}},
            "runtime": "PYTHON_3_12", "entryPoint": ["proper_mcps/agentcore/servidor.py"]}},
        role_arn=f"arn:aws:iam::{conta}:role/coppezip-agentcore",
        network_configuration={"networkMode": "PUBLIC"},
        protocol_configuration="MCP",
        authorizer_configuration={"customJwtAuthorizer": {
            "discoveryUrl": f"https://cognito-idp.{pool.split('_')[0]}.amazonaws.com/{pool}/.well-known/openid-configuration",
            "allowedClients": [cliente]}},
        environment_variables={"COPPEZIP_MCP": qual, "COPPEZIP_BUCKET": bucket})
    cdk.CfnOutput(pilha, f"Arn{qual.capitalize()}", value=runtime.attr_agent_runtime_arn)
app.synth()

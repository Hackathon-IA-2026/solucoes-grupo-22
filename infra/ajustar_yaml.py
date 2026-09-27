#!/usr/bin/env python3
"""Grava a versão do librechat.yaml que roda na AWS: sem o vLLM, com o perfil do Bedrock como padrão.

Na máquina do laboratório o modelo padrão é o vLLM (`./vllm.sh`, endpoint custom "EnergyNexus"), que não existe na
instância da AWS — quem responde lá é o Bedrock. Sem este ajuste o perfil que abre para quem entra no chat aponta para
um endereço morto e a primeira pergunta do evento falha.

Em vez de manter um segundo YAML de 350 linhas (que sairia de sincronia com o librechat.yaml no primeiro ajuste de
prompt ou de ferramenta), este script faz três transformações declaradas sobre o arquivo real:

  1. tira o endpoint `custom` (o vLLM) de `endpoints`;
  2. tira o perfil `energynexus-analista`, que é o do vLLM;
  3. marca `energynexus-analista-claude` como `default: true` — é o mesmo analista, mesmo prompt (a âncora `*prompt`) e
     os mesmos quatro MCP, mas pelo Bedrock.

Os `mcpServers`, o `webSearch`, o endpoint `bedrock` e os demais perfis passam intactos. As âncoras YAML (`&prompt`,
`&perguntas`) somem no caminho, porque o pyyaml as resolve na leitura: o valor é o mesmo, escrito por extenso.

Uso: ajustar_yaml.py <entrada.yaml> <saida.yaml>   (o entrada.sh chama na partida do contêiner)
"""
import sys

import yaml

PERFIL_VLLM = "energynexus-analista"
PERFIL_BEDROCK = "energynexus-analista-claude"


def ajustar(config: dict) -> dict:
    endpoints = config["endpoints"]
    if "custom" not in endpoints:
        raise SystemExit(f"o YAML não tem endpoints.custom (o vLLM): {sorted(endpoints)}")
    del endpoints["custom"]

    lista = config["modelSpecs"]["list"]
    nomes = [p["name"] for p in lista]
    if PERFIL_BEDROCK not in nomes:
        raise SystemExit(f"o YAML não tem o perfil {PERFIL_BEDROCK}, que é quem responde na AWS: {nomes}")
    config["modelSpecs"]["list"] = [p for p in lista if p["name"] != PERFIL_VLLM]

    for perfil in config["modelSpecs"]["list"]:
        # `default` fica só no perfil do Bedrock: dois padrões fariam o LibreChat escolher o primeiro da lista
        perfil.pop("default", None)
        if perfil["name"] == PERFIL_BEDROCK:
            perfil["default"] = True
    return config


def main():
    if len(sys.argv) != 3:
        raise SystemExit("uso: ajustar_yaml.py <entrada.yaml> <saida.yaml>")
    entrada, saida = sys.argv[1], sys.argv[2]
    with open(entrada, encoding="utf-8") as f:
        config = yaml.safe_load(f)
    config = ajustar(config)
    with open(saida, "w", encoding="utf-8") as f:
        f.write(f"# Gerado por infra/ajustar_yaml.py a partir de {entrada}. Não edite: edite o librechat.yaml.\n")
        yaml.safe_dump(config, f, allow_unicode=True, sort_keys=False, width=120)
    perfil = next(p for p in config["modelSpecs"]["list"] if p.get("default"))
    print(f"{saida}: perfil padrão {perfil['name']} ({perfil['preset']['model']}), "
          f"{len(config['modelSpecs']['list'])} perfis, endpoints {sorted(config['endpoints'])}")


if __name__ == "__main__":
    main()

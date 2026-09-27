# avaliacao — Opus 5 (Bedrock) × Qwen (vLLM) com as ferramentas do EnergyNexus

Mede a taxa de acertos de dois modelos rodando **as mesmas ferramentas** que o agente
`energynexus-analista` usa no LibreChat: os quatro servidores MCP do `librechat.yaml`
(`energynexus-dados` e `energynexus-docs` pela ponte do AgentCore, `energynexus-placar` e
`energynexus-relatorio` locais), a busca web (Serper + rerank Jina) e a ferramenta `skill`,
com o mesmo `promptPrefix`, o mesmo `recursionLimit` e o mesmo `maxOutputTokens` do perfil.

O resultado está em [RELATORIO.md](RELATORIO.md).

## Peças

| arquivo | o que faz |
|---|---|
| `comum.py` | caminhos, leitura do `.env` do repositório principal, abertura dos DuckDB em `read_only` |
| `sondar.py` | confere acesso: lista os modelos do vLLM e faz uma chamada mínima em cada modelo do Bedrock |
| `mcp_cliente.py` | cliente MCP stdio (JSON-RPC por linha), sobe os quatro servidores em paralelo |
| `busca_web.py` | a busca web do LibreChat: Serper `/search` + `scrape` + rerank Jina, com as âncoras de citação |
| `ferramentas.py` | lê o perfil do `librechat.yaml`, registra as ferramentas com o sufixo `_mcp_<servidor>` e monta o prompt de sistema (promptPrefix + instruções dos MCP + contexto da busca + catálogo de skills) |
| `laco.py` | o laço de ferramentas: adaptador Bedrock (Converse) e adaptador OpenAI (vLLM), contando dois passos por chamada como o LibreChat |
| `perguntas.json` | as 76 perguntas com gabarito conferido |
| `conferir_conjunto.py` | valida o conjunto e reconfere cada citação contra o índice antes de gastar execução |
| `corretor.py` | correção por regra (número com tolerância, citação conferida no índice, "não está na base", relatório gerado) |
| `rodar.py` | roda o conjunto em um modelo, gravando um JSON por pergunta/rodada na hora |
| `recorrigir.py` | recorrige os JSON já gravados com o gabarito atual (sem mexer nas respostas) |
| `medir_vllm.py` | mede o servidor vLLM: contexto efetivo (agulha no palheiro), tokens/s e memória da GPU |
| `relatar.py` | monta as tabelas do relatório a partir do que existir de resultado |

## Como rodar

Precisa do `.env` do repositório principal (Bedrock, Cognito, Serper, Jina) e do servidor vLLM no ar.
Nada é impresso de variável com nome de segredo.

```bash
RAIZ=/impa/home/a/al.richard.viana/projects/clean-hack/coppezip
PY=$RAIZ/.runtime/venv/bin/python           # venv do projeto (não instala vLLM aqui)
export AVALIACAO_SAIDA=/local/$USER/avaliacao-opus5-qwen   # resultados fora do git

cd avaliacao
$PY sondar.py                     # acesso ao Bedrock e ao vLLM
$PY conferir_conjunto.py          # o conjunto e os gabaritos estão de pé?
$PY medir_vllm.py                 # contexto efetivo e tokens/s do Qwen
$PY rodar.py --modelo qwen  --rodadas 2
$PY rodar.py --modelo opus5 --rodadas 2
$PY relatar.py --escrever         # grava as tabelas dentro de RELATORIO.md
```

`rodar.py` pula pergunta que já tem arquivo, então basta repetir o comando para retomar uma corrida
interrompida (foi o que aconteceu quando o token da AWS expirou no meio). `--refazer` força.
Outras opções úteis: `--categorias placar_esg,ausente`, `--limite 5`, `--sem-busca`.

Se o gabarito for corrigido depois de uma corrida, rode `$PY recorrigir.py --aplicar` antes de
`relatar.py`: os dois modelos têm de ser medidos com a mesma régua.

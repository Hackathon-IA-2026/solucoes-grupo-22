"""Utilidades compartilhadas da avaliação: .env, caminhos e acesso aos bancos.

A worktree só tem os scripts de `data/`; os bancos ficam no repositório principal (RAIZ_DADOS),
porque `data/*.duckdb` são links para o disco local do nó. Todo banco abre read_only.
"""

from __future__ import annotations

import os
import pathlib

AQUI = pathlib.Path(__file__).resolve().parent
RAIZ = AQUI.parent  # a worktree
# repositório principal: onde .env e data/*.duckdb de verdade estão
RAIZ_PRINCIPAL = pathlib.Path(
    os.environ.get("ENERGYNEXUS_RAIZ_PRINCIPAL", "/impa/home/a/al.richard.viana/projects/clean-hack/coppezip")
)
DADOS = RAIZ_PRINCIPAL / "data"
SAIDA = pathlib.Path(os.environ.get("AVALIACAO_SAIDA", "/local/al.richard.viana/avaliacao-opus5-qwen"))

SEGREDO = ("SENHA", "SECRET", "KEY", "PASSWORD", "TOKEN", "CREDS", "JWT")


def e_segredo(nome: str) -> bool:
    n = nome.upper()
    return any(p in n for p in SEGREDO)


def ler_env(caminho: pathlib.Path | None = None) -> dict[str, str]:
    """Lê o .env do repositório principal. Nunca imprima o resultado inteiro."""
    caminho = caminho or (RAIZ_PRINCIPAL / ".env")
    env: dict[str, str] = {}
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        env[chave.strip()] = valor.strip().strip('"').strip("'")
    return env


def exportar_env(chaves: list[str] | None = None) -> dict[str, str]:
    """Devolve o ambiente do processo com o .env aplicado (para subprocessos MCP)."""
    env = dict(os.environ)
    lido = ler_env()
    for chave, valor in lido.items():
        if chaves is None or chave in chaves:
            env.setdefault(chave, valor)
            env[chave] = valor
    env.setdefault("ENERGYNEXUS_RAIZ", str(RAIZ_PRINCIPAL))
    env["ENERGYNEXUS_RAIZ"] = str(RAIZ_PRINCIPAL)
    env["ENERGYNEXUS_PYTHON"] = str(RAIZ_PRINCIPAL / ".runtime" / "venv" / "bin" / "python")
    return env


def abrir(banco: str):
    """Abre um dos bancos de data/ em read_only."""
    import duckdb

    caminho = DADOS / banco
    return duckdb.connect(str(caminho), read_only=True)


def resumo_env() -> dict[str, str]:
    """Só os valores não sensíveis, para log/relatório."""
    env = ler_env()
    return {k: v for k, v in env.items() if not e_segredo(k)}

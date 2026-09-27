"""Roda o conjunto de perguntas nos dois modelos, gravando UM JSON por pergunta/rodada na hora.

    python rodar.py --modelo qwen  --rodadas 2
    python rodar.py --modelo opus5 --rodadas 2
    python rodar.py --modelo qwen --categorias placar_esg,ausente --rodadas 1

Cada execução grava AVALIACAO_SAIDA/<modelo>/<id>_r<N>.json assim que termina, então um resultado parcial já é
aproveitável (relatar.py lê o que existir). Uma pergunta que já tem arquivo é pulada, a menos que venha --refazer.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import traceback

import comum
import corretor
import ferramentas
import laco

MODELOS = {
    "opus5": {"familia": "bedrock", "modelo": "us.anthropic.claude-opus-5", "rotulo": "Claude Opus 5 (Bedrock)"},
    "opus48": {"familia": "bedrock", "modelo": "us.anthropic.claude-opus-4-8", "rotulo": "Claude Opus 4.8 (Bedrock)"},
    "sonnet5": {"familia": "bedrock", "modelo": "us.anthropic.claude-sonnet-5", "rotulo": "Claude Sonnet 5 (Bedrock)"},
    "qwen": {"familia": "openai", "modelo": "qwen3.8-27b", "rotulo": "Qwen3.8-27B-INT4 (vLLM, RTX 5090)"},
}


def adaptador(chave: str, max_saida: int):
    spec = MODELOS[chave]
    if spec["familia"] == "bedrock":
        return laco.Bedrock(spec["modelo"], max_saida=max_saida)
    return laco.OpenAI(modelo=spec["modelo"], max_saida=max_saida)


def carregar_perguntas(caminho: pathlib.Path, categorias: set[str] | None, limite: int | None) -> list[dict]:
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    perguntas = dados["perguntas"] if isinstance(dados, dict) else dados
    if categorias:
        perguntas = [p for p in perguntas if p.get("categoria") in categorias]
    return perguntas[:limite] if limite else perguntas


def main(argv=None):
    ap = argparse.ArgumentParser(description="roda o conjunto de avaliação em um modelo")
    ap.add_argument("--modelo", required=True, choices=sorted(MODELOS))
    ap.add_argument("--rodadas", type=int, default=2)
    ap.add_argument("--perguntas", default=str(comum.AQUI / "perguntas.json"))
    ap.add_argument("--categorias", default="")
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--max-passos", type=int, default=300, help="recursionLimit do librechat.yaml")
    ap.add_argument("--max-saida", type=int, default=32000, help="maxOutputTokens do perfil")
    ap.add_argument("--sem-busca", action="store_true", help="desliga web_search (para poupar cota do Serper)")
    ap.add_argument("--refazer", action="store_true")
    ap.add_argument("--saida", default=str(comum.SAIDA))
    args = ap.parse_args(argv)

    categorias = {c.strip() for c in args.categorias.split(",") if c.strip()} or None
    perguntas = carregar_perguntas(pathlib.Path(args.perguntas), categorias, args.limite or None)
    destino = pathlib.Path(args.saida) / args.modelo
    destino.mkdir(parents=True, exist_ok=True)
    registro = (pathlib.Path(args.saida) / f"log_{args.modelo}.txt").open("a", encoding="utf-8")

    def log(texto: str):
        linha = f"[{time.strftime('%H:%M:%S')}] {texto}"
        print(linha, flush=True)
        registro.write(linha + "\n")
        registro.flush()

    log(f"modelo={args.modelo} perguntas={len(perguntas)} rodadas={args.rodadas} destino={destino}")
    caixa = ferramentas.Caixa(com_busca=not args.sem_busca, log=log)
    indice = corretor.Indice()
    resumo = caixa.resumo()
    (pathlib.Path(args.saida) / "ambiente.json").write_text(
        json.dumps({"caixa": resumo, "modelos": MODELOS,
                    "prompt_sistema_sha": __import__("hashlib").sha256(
                        caixa.prompt_sistema().encode()).hexdigest()[:16]},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    log("ferramentas: " + ", ".join(resumo["ferramentas"]))

    feitos = 0
    try:
        for rodada in range(1, args.rodadas + 1):
            for pergunta in perguntas:
                arquivo = destino / f"{pergunta['id']}_r{rodada}.json"
                if arquivo.exists() and not args.refazer:
                    continue
                log(f"[{args.modelo} r{rodada}] {pergunta['id']} ({pergunta['categoria']}): "
                    f"{pergunta['pergunta'][:110]}")
                inicio = time.time()
                try:
                    execucao = laco.rodar(adaptador(args.modelo, args.max_saida), caixa, pergunta["pergunta"],
                                          max_passos=args.max_passos, log=log)
                except Exception:  # noqa: BLE001
                    execucao = {"resposta": "", "erro": traceback.format_exc()[-1500:], "trilha": [],
                                "passos": 0, "chamadas_ferramenta": 0, "motivo_parada": "excecao",
                                "uso": laco.Uso().dict(), "segundos": round(time.time() - inicio, 1)}
                try:
                    nota = corretor.corrigir(pergunta, execucao, indice)
                    nota["alucinacao"] = corretor.alucinou(pergunta, nota, execucao)
                except Exception:  # noqa: BLE001
                    nota = {"acerto": False, "tipo": pergunta.get("tipo_correcao"), "motivo": "erro_no_corretor",
                            "detalhe": {"traceback": traceback.format_exc()[-800:]}, "alucinacao": False}
                arquivo.write_text(json.dumps({
                    "modelo": args.modelo, "modelo_id": MODELOS[args.modelo]["modelo"],
                    "rodada": rodada, "pergunta": pergunta, "execucao": execucao, "correcao": nota,
                    "quando": time.strftime("%Y-%m-%dT%H:%M:%S"),
                }, ensure_ascii=False, indent=1), encoding="utf-8")
                feitos += 1
                log(f"    -> {'ACERTO' if nota['acerto'] else 'ERRO  '} ({nota['motivo']}) "
                    f"{execucao['segundos']}s, {execucao['chamadas_ferramenta']} chamadas, "
                    f"{execucao['uso']['tokens_entrada']}+{execucao['uso']['tokens_saida']} tokens"
                    f"{' [ALUCINOU]' if nota.get('alucinacao') else ''}")
    finally:
        caixa.fechar()
        log(f"fim: {feitos} execuções novas gravadas em {destino}")
        registro.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Recorrige, no lugar, os JSON já gravados usando o gabarito atual de perguntas.json.

Existe porque o gabarito pode ser corrigido depois das corridas (foi o caso do escopo 1 da ISA em 2024, cujo valor
antigo vinha da coluna de 2022 da tabela). Recorrigir é obrigatório nesse caso: sem isso um modelo que acertou
continuaria contado como erro, e a comparação entre os dois modelos deixaria de ser feita com a mesma régua.

A execução (resposta, trilha, tokens, tempo) não é tocada — só o bloco "correcao".

    python recorrigir.py            # mostra o que mudaria
    python recorrigir.py --aplicar   # grava
"""

from __future__ import annotations

import argparse
import json
import pathlib

import comum
import corretor


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--saida", default=str(comum.SAIDA))
    ap.add_argument("--perguntas", default=str(comum.AQUI / "perguntas.json"))
    ap.add_argument("--aplicar", action="store_true")
    args = ap.parse_args()

    dados = json.loads(pathlib.Path(args.perguntas).read_text(encoding="utf-8"))
    perguntas = {p["id"]: p for p in (dados["perguntas"] if isinstance(dados, dict) else dados)}
    indice = corretor.Indice()
    raiz = pathlib.Path(args.saida)
    mudou = igual = sem_pergunta = 0

    for pasta in sorted(p for p in raiz.iterdir() if p.is_dir() and not p.name.endswith("_token_expirado")):
        for arquivo in sorted(pasta.glob("*_r*.json")):
            registro = json.loads(arquivo.read_text(encoding="utf-8"))
            pergunta = perguntas.get(registro["pergunta"]["id"])
            if pergunta is None:
                sem_pergunta += 1
                continue
            nota = corretor.corrigir(pergunta, registro["execucao"], indice)
            nota["alucinacao"] = corretor.alucinou(pergunta, nota, registro["execucao"])
            antes = registro["correcao"]["acerto"]
            if bool(antes) != bool(nota["acerto"]):
                mudou += 1
                print(f"{pasta.name}/{arquivo.stem}: {antes} -> {nota['acerto']}")
            else:
                igual += 1
            registro["pergunta"] = pergunta  # o gabarito corrigido fica junto do resultado
            registro["correcao"] = nota
            if args.aplicar:
                arquivo.write_text(json.dumps(registro, ensure_ascii=False, indent=1), encoding="utf-8")

    print(json.dumps({"mudaram": mudou, "iguais": igual, "sem_pergunta_no_conjunto": sem_pergunta,
                      "aplicado": args.aplicar}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

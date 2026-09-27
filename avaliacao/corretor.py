"""Correção automática das respostas, sem juiz de modelo: só regras verificáveis.

Quatro verificações, combinadas conforme `tipo_correcao` da pergunta:
  numerico / contagem       -> algum número do texto bate com o gabarito dentro da tolerância (números em formato
                               brasileiro e com sufixo de escala: "1,2 bilhão", "3,4 mi", "R$ 2,3 bi");
  numerico_com_citacao      -> o número bate E a citação (arquivo + página) existe no índice E a página citada
                               contém o valor (conferido no texto de docs.duckdb);
  texto_contem              -> as frases aceitas/obrigatórias aparecem e nenhuma proibida aparece;
  ausencia                  -> a resposta admite que o dado não está na base e NÃO apresenta um número como se fosse
                               da base (é a medida de alucinação);
  relatorio                 -> gerar_relatorio foi chamada com sucesso e a resposta traz o bloco :::artifact.

A conferência de citação usa o índice de docs (docs.duckdb / docs_titan.duckdb) em read_only, nunca o placar (que
está sendo escrito por outra extração).
"""

from __future__ import annotations

import json
import re
import unicodedata

import comum

# --- números -----------------------------------------------------------------
ESCALAS = {
    "mil": 1e3, "milhar": 1e3, "milhares": 1e3,
    "mi": 1e6, "milhao": 1e6, "milhoes": 1e6, "milhão": 1e6, "milhões": 1e6, "mm": 1e6,
    "bi": 1e9, "bilhao": 1e9, "bilhoes": 1e9, "bilhão": 1e9, "bilhões": 1e9,
    "tri": 1e12, "trilhao": 1e12, "trilhoes": 1e12,
}
# 1.234.567,89 | 1,234,567.89 | 1234.56 | 1234,56 | 1234
NUMERO = re.compile(r"(?<![\w.,])(\d{1,3}(?:[.  ]\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)(?![\w])")
SUFIXO = re.compile(r"\s*(mil|milhar(?:es)?|mi|milh(?:ao|ão|oes|ões)|bi|bilh(?:ao|ão|oes|ões)|tri|trilh(?:ao|ões|oes))\b",
                    re.I)


def sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def _para_float(bruto: str) -> float | None:
    t = bruto.replace(" ", "").replace(" ", "")
    if "," in t and "." in t:
        # o último separador manda: 1.234,56 (pt) ou 1,234.56 (en)
        t = t.replace(".", "").replace(",", ".") if t.rfind(",") > t.rfind(".") else t.replace(",", "")
    elif "," in t:
        inteiro, _, decimal = t.rpartition(",")
        t = t.replace(",", "") if len(decimal) == 3 and inteiro else t.replace(",", ".")
    elif t.count(".") > 1:
        t = t.replace(".", "")
    elif "." in t:
        inteiro, _, decimal = t.rpartition(".")
        if len(decimal) == 3 and inteiro and len(inteiro) <= 3:
            pass  # 1.234 pode ser mil em pt: mantém as duas leituras em numeros()
    try:
        return float(t)
    except ValueError:
        return None


def numeros(texto: str) -> list[float]:
    """Todos os números plausíveis do texto, já aplicando sufixo de escala. Ambíguos entram nas duas leituras."""
    saida: list[float] = []
    for achado in NUMERO.finditer(texto):
        bruto = achado.group(1)
        valor = _para_float(bruto)
        if valor is None:
            continue
        candidatos = [valor]
        # "1.234" em português é mil duzentos e trinta e quatro, mas em inglês é 1,234: considera as duas
        if re.fullmatch(r"\d{1,3}\.\d{3}", bruto):
            candidatos.append(float(bruto.replace(".", "")))
        if re.fullmatch(r"\d{1,3},\d{3}", bruto):
            candidatos.append(float(bruto.replace(",", "")))
        sufixo = SUFIXO.match(texto[achado.end():achado.end() + 14])
        if sufixo:
            fator = ESCALAS.get(sem_acento(sufixo.group(1).lower()), 1.0)
            candidatos += [c * fator for c in list(candidatos)]
        saida.extend(candidatos)
    return saida


def bate(valor_esperado: float, texto: str, tol_rel: float | None = 0.01,
         tol_abs: float | None = None, escala_livre: bool = False) -> tuple[bool, float | None]:
    """Algum número do texto bate com o esperado? Devolve (bateu, o número encontrado mais próximo).

    `escala_livre` só é usado em valor monetário: as demonstrações da CVM são publicadas em R$ mil, então a
    página traz "4.624.113" para R$ 4.624.113.000 e a resposta pode dizer "R$ 4,6 bilhões". Nesses casos o acerto
    vale em qualquer uma das escalas usuais (unidade, mil, milhão, bilhão). Em contagem, percentual, MW e tCO2e a
    escala é fixa: trocar mil tCO2e por tCO2e é erro e continua contando como erro.
    """
    if tol_abs is None and tol_rel is None:
        tol_rel = 0.01
    escalas = (1.0, 1e3, 1e6, 1e9) if escala_livre else (1.0,)
    melhor, melhor_dist = None, float("inf")
    bateu = False
    for achado in numeros(texto):
        for escala in escalas:
            candidato = achado * escala
            dist = abs(candidato - valor_esperado)
            limite = tol_abs if tol_abs is not None else abs(valor_esperado) * (tol_rel or 0.01)
            if dist <= limite:
                bateu = True
            if escala == 1.0 and dist < melhor_dist:
                melhor, melhor_dist = achado, dist
    return bateu, melhor


def escala_livre(gabarito: dict) -> bool:
    """Valor monetário aceita escala; o resto não. Pode ser forçado com "escala_livre" no gabarito."""
    if "escala_livre" in gabarito:
        return bool(gabarito["escala_livre"])
    unidade = (gabarito.get("unidade") or "").strip().lower()
    return unidade in ("r$", "reais", "brl", "r$ mil", "r$ milhões", "r$ milhoes", "r$ bi", "r$ bilhões")


# --- citações ----------------------------------------------------------------
class Indice:
    """Conferência de citação no índice dos PDFs: o arquivo existe e a página traz o valor."""

    def __init__(self, banco: str = "docs.duckdb"):
        self.banco = banco
        self._con = None
        self._tabela_pagina = None
        self._erro = None

    def _conectar(self):
        if self._con is not None or self._erro is not None:
            return
        try:
            self._con = comum.abrir(self.banco)
            tabelas = {t[0] for t in self._con.execute("SHOW TABLES").fetchall()}
            for nome in ("paginas", "pagina", "blocos", "trechos", "documentos_paginas"):
                if nome in tabelas:
                    colunas = {c[1] for c in self._con.execute(f"PRAGMA table_info('{nome}')").fetchall()}
                    if {"texto"} & colunas and {"pagina"} & colunas:
                        self._tabela_pagina = (nome, colunas)
                        break
        except Exception as erro:  # noqa: BLE001
            self._erro = f"{type(erro).__name__}: {erro}"

    def texto_pagina(self, arquivo: str, pagina: int) -> str | None:
        self._conectar()
        if self._con is None or self._tabela_pagina is None:
            return None
        tabela, colunas = self._tabela_pagina
        coluna_arquivo = next((c for c in ("arquivo", "documento", "nome_arquivo", "pdf") if c in colunas), None)
        if coluna_arquivo is None:
            return None
        try:
            linhas = self._con.execute(
                f"SELECT string_agg(texto, '\n') FROM {tabela} "
                f"WHERE {coluna_arquivo} LIKE ? AND pagina = ?",
                [f"%{arquivo}%", int(pagina)],
            ).fetchone()
        except Exception:  # noqa: BLE001
            return None
        return (linhas[0] if linhas else None) or None

    def arquivo_existe(self, arquivo: str) -> bool | None:
        self._conectar()
        if self._con is None or self._tabela_pagina is None:
            return None
        tabela, colunas = self._tabela_pagina
        coluna_arquivo = next((c for c in ("arquivo", "documento", "nome_arquivo", "pdf") if c in colunas), None)
        if coluna_arquivo is None:
            return None
        try:
            n = self._con.execute(
                f"SELECT count(*) FROM {tabela} WHERE {coluna_arquivo} LIKE ?", [f"%{arquivo}%"]
            ).fetchone()[0]
        except Exception:  # noqa: BLE001
            return None
        return n > 0


PAGINA_CITADA = re.compile(r"(?:p\.?|pag\.?|p[áa]g(?:ina)?s?\.?)\s*(\d{1,4})", re.I)


def paginas_citadas(texto: str) -> set[int]:
    return {int(m.group(1)) for m in PAGINA_CITADA.finditer(texto)}


def arquivo_citado(texto: str, arquivo: str) -> bool:
    """O nome do arquivo (ou um pedaço dele bem específico) aparece na resposta?"""
    alvo = sem_acento(arquivo).lower()
    resposta = sem_acento(texto).lower()
    if alvo in resposta:
        return True
    raiz = re.sub(r"\.pdf$", "", alvo)
    if raiz and raiz in resposta:
        return True
    # o modelo costuma citar o documento pelo nome humano; aceita se todos os pedaços fortes aparecerem
    pedacos = [p for p in re.split(r"[^a-z0-9]+", raiz) if len(p) > 3]
    return bool(pedacos) and all(p in resposta for p in pedacos)


# --- "não está na base" ------------------------------------------------------
ADMITE = [
    "nao esta na base", "nao consta na base", "nao encontrei", "nao localizei", "nao ha dado",
    "nao existe na base", "nao tenho esse dado", "nao tenho o dado", "nao disponivel na base",
    "nao foi possivel localizar", "nao aparece na base", "sem dado", "nao consta", "nao esta disponivel",
    "nao identifiquei", "fora do periodo coberto", "nao coberto", "nao esta indexad", "nao ha registro",
    "nao retornou", "nenhum resultado", "nao sei", "nao posso confirmar", "nao confirmei",
    "nao ha informacao", "nao ha registros", "nao encontrada", "nao encontrado",
]
INVENTA = ["estimo que", "estimativa propria", "aproximadamente r$", "deve ser cerca de", "provavelmente e de"]


def admite_ausencia(texto: str) -> bool:
    limpo = sem_acento(texto).lower()
    return any(f in limpo for f in ADMITE)


# --- correção ----------------------------------------------------------------
def corrigir(pergunta: dict, execucao: dict, indice: Indice) -> dict:
    texto = execucao.get("resposta") or ""
    gabarito = pergunta.get("gabarito") or {}
    tipo = pergunta.get("tipo_correcao") or "numerico"
    detalhe: dict = {"tipo": tipo}
    acerto = False

    if execucao.get("erro"):
        return {"acerto": False, "tipo": tipo, "motivo": "erro_de_execucao", "detalhe": {"erro": execucao["erro"]}}
    if not texto.strip():
        return {"acerto": False, "tipo": tipo, "motivo": "resposta_vazia", "detalhe": {}}

    if tipo in ("numerico", "contagem", "numerico_com_citacao"):
        esperado = gabarito.get("valor")
        if esperado is None:
            return {"acerto": False, "tipo": tipo, "motivo": "gabarito_sem_valor", "detalhe": {}}
        tol_rel = gabarito.get("tolerancia_relativa")
        tol_abs = gabarito.get("tolerancia_absoluta")
        if tipo == "contagem" and tol_rel is None and tol_abs is None:
            tol_abs = 0
        livre = escala_livre(gabarito)
        ok_numero, encontrado = bate(float(esperado), texto, tol_rel, tol_abs, escala_livre=livre)
        detalhe.update({"valor_esperado": esperado, "numero_mais_proximo": encontrado, "numero_ok": ok_numero,
                        "escala_livre": livre})
        acerto = ok_numero
        if tipo == "numerico_com_citacao":
            arquivo, pagina = gabarito.get("arquivo"), gabarito.get("pagina")
            aceitas = {int(p) for p in ([pagina] + list(gabarito.get("paginas_aceitas") or [])) if p}
            cita_arquivo = bool(arquivo) and arquivo_citado(texto, arquivo)
            paginas = paginas_citadas(texto)
            cita_pagina = bool(aceitas & paginas)
            existe = indice.arquivo_existe(arquivo) if arquivo else None
            # a página vale se confirma o valor: confere todas as aceitas (o mesmo número reaparece em várias)
            pagina_confirma = None
            if arquivo and esperado is not None:
                for pag in sorted(aceitas):
                    conteudo = indice.texto_pagina(arquivo, pag)
                    if conteudo is None:
                        continue
                    if bate(float(esperado), conteudo, tol_rel or 0.02, tol_abs, escala_livre=livre)[0]:
                        pagina_confirma = True
                        break
                    pagina_confirma = False
            detalhe.update({
                "arquivo_esperado": arquivo, "pagina_esperada": pagina, "paginas_aceitas": sorted(aceitas),
                "citou_arquivo": cita_arquivo, "paginas_citadas": sorted(paginas), "citou_pagina": cita_pagina,
                "arquivo_existe_no_indice": existe, "pagina_confirma_valor": pagina_confirma,
            })
            acerto = bool(ok_numero and cita_arquivo and cita_pagina)

    elif tipo == "texto_contem":
        limpo = sem_acento(texto).lower()
        aceitos = [a for a in (gabarito.get("aceitos") or []) if sem_acento(a).lower() in limpo]
        todos = gabarito.get("todos") or []
        faltam = [t for t in todos if sem_acento(t).lower() not in limpo]
        proibidos = [p for p in (gabarito.get("proibidos") or []) if sem_acento(p).lower() in limpo]
        detalhe.update({"aceitos_encontrados": aceitos, "obrigatorios_faltando": faltam,
                        "proibidos_encontrados": proibidos})
        tem_aceito = bool(aceitos) if gabarito.get("aceitos") else True
        acerto = tem_aceito and not faltam and not proibidos

    elif tipo == "ausencia":
        admitiu = admite_ausencia(texto)
        inventou = [i for i in INVENTA if i in sem_acento(texto).lower()]
        proibidos = [p for p in (gabarito.get("proibidos") or []) if sem_acento(p).lower() in sem_acento(texto).lower()]
        detalhe.update({"admitiu_ausencia": admitiu, "marcas_de_invencao": inventou,
                        "proibidos_encontrados": proibidos})
        acerto = bool(admitiu and not inventou and not proibidos)
        detalhe["alucinou"] = bool(not admitiu or inventou or proibidos)

    elif tipo == "relatorio":
        chamou = [c for c in execucao.get("trilha") or [] if c["ferramenta"].startswith("gerar_relatorio")]
        sucesso = [c for c in chamou if not c["erro"]]
        artefato = ":::artifact" in texto
        detalhe.update({"chamadas_gerar_relatorio": len(chamou), "chamadas_ok": len(sucesso),
                        "bloco_artifact": artefato})
        acerto = bool(sucesso and artefato)

    else:
        return {"acerto": False, "tipo": tipo, "motivo": "tipo_desconhecido", "detalhe": {}}

    return {"acerto": bool(acerto), "tipo": tipo, "motivo": "ok" if acerto else "nao_bateu", "detalhe": detalhe}


def alucinou(pergunta: dict, correcao: dict, execucao: dict) -> bool:
    """Alucinação: afirmou dado inexistente (categoria ausente) ou citou arquivo/página que o índice não confirma."""
    if correcao["tipo"] == "ausencia":
        return bool(correcao["detalhe"].get("alucinou"))
    d = correcao.get("detalhe") or {}
    if d.get("arquivo_existe_no_indice") is False:
        return True
    if d.get("citou_pagina") and d.get("pagina_confirma_valor") is False:
        return True
    return False


if __name__ == "__main__":
    import sys

    # autoteste rápido do parser de números
    casos = [
        ("A receita foi de R$ 1.234,5 milhões em 2025.", 1234.5e6),
        ("Emissões de 12.345 tCO2e", 12345),
        ("57,3% da matriz", 57.3),
        ("EBITDA de R$ 2,3 bi", 2.3e9),
        ("investiu 1,2 bilhão de reais", 1.2e9),
    ]
    falhas = 0
    for texto, esperado in casos:
        ok, achado = bate(esperado, texto)
        print(("ok  " if ok else "FALHOU"), repr(texto), "->", achado, "esperado", esperado)
        falhas += 0 if ok else 1
    print(json.dumps({"falhas": falhas}))
    sys.exit(1 if falhas else 0)

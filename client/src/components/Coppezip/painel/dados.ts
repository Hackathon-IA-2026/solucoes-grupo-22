// Dados do painel: o formato de data/painel.json (gerado por data/exportar_painel.py), filtros, agregação pela regra de
// cada medida e formatação. Tudo puro, sem React, para ser testado isoladamente.

export type Coluna = { coluna: string; rotulo: string };

export type Medida = Coluna & {
  unidade: string;
  agregacao: 'soma' | 'razao' | 'ponderada' | 'media' | 'min' | 'max';
  num?: string;
  den?: string;
  fator?: number;
  den_abs?: boolean;
  peso?: string;
};

export type Linha = unknown[];

export type Conjunto = {
  id: string;
  grupo: string;
  titulo: string;
  descricao: string;
  fonte: string;
  ressalvas: string;
  tempo?: Coluna;
  granularidade?: string;
  dimensoes: Coluna[];
  medidas: Medida[];
  extras: Coluna[];
  padrao: { medida: string; serie: string; filtros?: Record<string, string[]>; desde?: string };
  busca: Record<string, Record<string, string>>;
  colunas: string[];
  linhas: Linha[];
};

export type Painel = { gerado_em: string; banco: string; conjuntos: Conjunto[] };

/** Filtros por dimensão: lista vazia (ou ausente) = todos os valores. */
export type Filtros = Record<string, string[]>;

export const MAX_SERIES = 8; // paleta categórica de 8 cores; mais que isso vira ranking, não linha

const numero = (v: unknown): number | null =>
  typeof v === 'number' && Number.isFinite(v) ? v : null;

export function indice(conjunto: Conjunto, coluna: string): number {
  return conjunto.colunas.indexOf(coluna);
}

/** Valores distintos de uma coluna, em ordem alfabética. */
export function valores(conjunto: Conjunto, coluna: string): string[] {
  const i = indice(conjunto, coluna);
  const vistos = new Set<string>();
  for (const linha of conjunto.linhas) {
    if (linha[i] != null) {
      vistos.add(String(linha[i]));
    }
  }
  return [...vistos].sort((a, b) => a.localeCompare(b, 'pt-BR'));
}

export function filtrar(conjunto: Conjunto, filtros: Filtros, de?: string, ate?: string): Linha[] {
  const ativos = Object.entries(filtros)
    .filter(([, lista]) => lista.length > 0)
    .map(([coluna, lista]) => [indice(conjunto, coluna), new Set(lista)] as const);
  const t = conjunto.tempo ? indice(conjunto, conjunto.tempo.coluna) : -1;
  return conjunto.linhas.filter((linha) => {
    for (const [i, aceitos] of ativos) {
      if (!aceitos.has(String(linha[i]))) {
        return false;
      }
    }
    if (t >= 0) {
      const p = String(linha[t]);
      if ((de && p < de) || (ate && p > ate)) {
        return false;
      }
    }
    return true;
  });
}

/** Função que junta linhas numa medida pela regra declarada (a mesma do exportador). */
export function agregador(conjunto: Conjunto, m: Medida): (linhas: Linha[]) => number | null {
  const col = (c?: string) => (c ? indice(conjunto, c) : -1);
  if (m.agregacao === 'razao') {
    const n = col(m.num);
    const d = col(m.den);
    const fator = m.fator ?? 1;
    return (linhas) => {
      let sn = 0;
      let sd = 0;
      let algum = false;
      for (const l of linhas) {
        const a = numero(l[n]);
        const b = numero(l[d]);
        if (a != null && b != null) {
          sn += a;
          sd += b;
          algum = true;
        }
      }
      const den = m.den_abs ? Math.abs(sd) : sd;
      return algum && den !== 0 ? (fator * sn) / den : null;
    };
  }
  const v = col(m.coluna);
  if (m.agregacao === 'ponderada') {
    const p = col(m.peso);
    return (linhas) => {
      let soma = 0;
      let pesos = 0;
      for (const l of linhas) {
        const a = numero(l[v]);
        const w = numero(l[p]);
        if (a != null && w != null) {
          soma += a * w;
          pesos += w;
        }
      }
      return pesos !== 0 ? soma / pesos : null;
    };
  }
  return (linhas) => {
    const lista = linhas.map((l) => numero(l[v])).filter((x): x is number => x != null);
    if (lista.length === 0) {
      return null;
    }
    switch (m.agregacao) {
      case 'media':
        return lista.reduce((a, b) => a + b, 0) / lista.length;
      case 'min':
        return Math.min(...lista);
      case 'max':
        return Math.max(...lista);
      default:
        return lista.reduce((a, b) => a + b, 0);
    }
  };
}

/** Agrupa linhas pelo valor de uma coluna (em texto), na ordem em que aparecem. */
export function agrupar(linhas: Linha[], i: number): Map<string, Linha[]> {
  const grupos = new Map<string, Linha[]>();
  for (const l of linhas) {
    const k = String(l[i]);
    const g = grupos.get(k);
    if (g) {
      g.push(l);
    } else {
      grupos.set(k, [l]);
    }
  }
  return grupos;
}

/** Valor da medida em cada período de `periodos` (null onde não há dado). */
export function serieTemporal(
  linhas: Linha[],
  iTempo: number,
  periodos: string[],
  agregar: (l: Linha[]) => number | null,
): (number | null)[] {
  const grupos = agrupar(linhas, iTempo);
  return periodos.map((p) => {
    const g = grupos.get(p);
    return g ? agregar(g) : null;
  });
}

/** Ranking: valor da medida por valor da dimensão, do maior para o menor (nulos fora). */
export function ranking(
  linhas: Linha[],
  iDim: number,
  agregar: (l: Linha[]) => number | null,
): { chave: string; valor: number }[] {
  const saida: { chave: string; valor: number }[] = [];
  for (const [chave, g] of agrupar(linhas, iDim)) {
    const valor = agregar(g);
    if (valor != null && chave !== 'null') {
      saida.push({ chave, valor });
    }
  }
  return saida.sort((a, b) => b.valor - a.valor);
}

const semAcento = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

/** O valor casa com a busca pelo próprio nome ou pelos termos extras (CNPJ, apelidos, tickers). */
export function casaBusca(valor: string, termos: string | undefined, busca: string): boolean {
  const q = semAcento(busca.trim());
  if (!q) {
    return true;
  }
  const alvo = semAcento(`${valor} ${termos ?? ''}`);
  const soDigitos = q.replace(/\D/g, '');
  if (soDigitos.length >= 8 && alvo.replace(/\D/g, '').includes(soDigitos)) {
    return true;
  }
  return q.split(/\s+/).every((parte) => alvo.includes(parte));
}

/**
 * Cor estável por entidade: quem já tinha cor mantém; quem saiu libera a vaga; quem entrou pega a menor vaga livre.
 * Assim um filtro que muda o número de séries não repinta as que ficaram.
 */
export function atribuirCores(
  anterior: Map<string, number>,
  chaves: string[],
): Map<string, number> {
  const nova = new Map<string, number>();
  for (const k of chaves) {
    const cor = anterior.get(k);
    if (cor != null) {
      nova.set(k, cor);
    }
  }
  const usadas = new Set(nova.values());
  for (const k of chaves) {
    if (!nova.has(k)) {
      let cor = 0;
      while (usadas.has(cor)) {
        cor++;
      }
      nova.set(k, cor);
      usadas.add(cor);
    }
  }
  return nova;
}

// ---------------------------------------------------------------- formatação (pt-BR)

const fmt = (casas: number) =>
  new Intl.NumberFormat('pt-BR', { maximumFractionDigits: casas, minimumFractionDigits: 0 });
const f0 = fmt(0);
const f1 = fmt(1);
const f2 = fmt(2);

/** 1.284 · 12,9 mil · 4,2 mi · 3,1 bi */
export function compacto(v: number): string {
  const a = Math.abs(v);
  if (a >= 1e9) {
    return `${f1.format(v / 1e9)} bi`;
  }
  if (a >= 1e6) {
    return `${f1.format(v / 1e6)} mi`;
  }
  if (a >= 1e4) {
    return `${f1.format(v / 1e3)} mil`;
  }
  if (a >= 100) {
    return f0.format(v);
  }
  return a >= 10 ? f1.format(v) : f2.format(v);
}

export function formatar(v: number | null | undefined, unidade: string): string {
  if (v == null) {
    return '–';
  }
  switch (unidade) {
    case 'brl':
      return `R$ ${compacto(v)}`;
    case 'pct':
      return `${f1.format(v)}%`;
    case 'x':
      return `${f2.format(v)}x`;
    case 'h':
      return `${f2.format(v)} h`;
    case 'brl_mwh':
      return `R$ ${f2.format(v)}/MWh`;
    case 'mw':
      return `${compacto(v)} MW`;
    case 'mwh':
      return `${compacto(v)} MWh`;
    case 'mwmed':
      return `${compacto(v)} MWmed`;
    case 'mwmes':
      return `${compacto(v)} MWmês`;
    default:
      return compacto(v);
  }
}

/** Variação entre dois períodos: pontos percentuais para % e múltiplos, relativa para o resto. */
export function variacao(
  atual: number | null,
  anterior: number | null,
  unidade: string,
): string | null {
  if (atual == null || anterior == null) {
    return null;
  }
  const sinal = (x: number) => {
    if (x === 0) {
      return '';
    }
    return x > 0 ? '+' : '−';
  };
  if (unidade === 'pct') {
    const d = atual - anterior;
    return `${sinal(d)}${f1.format(Math.abs(d))} p.p.`;
  }
  if (unidade === 'x') {
    const d = atual - anterior;
    return `${sinal(d)}${f2.format(Math.abs(d))}x`;
  }
  if (anterior === 0 || Math.sign(atual) !== Math.sign(anterior)) {
    return null; // variação relativa sem sentido (base zero ou troca de sinal)
  }
  const d = ((atual - anterior) / Math.abs(anterior)) * 100;
  return `${sinal(d)}${f1.format(Math.abs(d))}%`;
}

/** Marcas "redondas" para o eixo (0, 250, 500...), cobrindo [min, max]. */
export function marcas(min: number, max: number, alvo = 5): number[] {
  if (min === max) {
    const folga = Math.abs(min) || 1;
    min -= folga;
    max += folga;
  }
  const bruto = (max - min) / alvo;
  const potencia = 10 ** Math.floor(Math.log10(bruto));
  const passo = [1, 2, 2.5, 5, 10].map((m) => m * potencia).find((p) => p >= bruto) ?? bruto;
  const inicio = Math.floor(min / passo) * passo;
  const saida: number[] = [];
  for (let v = inicio; v <= max + passo * 1e-9; v += passo) {
    saida.push(Math.abs(v) < passo * 1e-9 ? 0 : v);
  }
  if (saida[saida.length - 1] < max) {
    saida.push(saida[saida.length - 1] + passo);
  }
  return saida;
}

// Grafo de conhecimento de uma empresa, montado a partir dos dados que o LibreChat já serve: data/painel.json
// (/api/painel/dados) e os documentos indexados (/api/busca/resumo). Tudo puro, sem React, para ser testado isoladamente.
//
// Empresa → Categoria (uma base do painel ou uma área de documentos) → Indicador / Referência, com os documentos
// agrupados por tipo. A empresa é o CNPJ: é ele que liga as bases entre si e aos documentos. Nada é inventado: cada
// indicador é uma medida do painel com dados da empresa, agregada por período pela regra do exportador.
import { agregador, indice, type Conjunto, type Linha, type Painel } from '../painel/dados';

export type Documento = {
  arquivo: string;
  area?: string;
  empresa: string;
  cnpj: string | null;
  ano: number;
  tipo: string;
  titulo: string;
  paginas: number;
  url: string | null;
};

export type TipoNo = 'empresa' | 'categoria' | 'grupo' | 'indicador' | 'referencia';

export type Icone =
  | 'building-2'
  | 'chart-line'
  | 'zap'
  | 'wind'
  | 'factory'
  | 'hand-coins'
  | 'trending-up'
  | 'layers'
  | 'leaf'
  | 'folder-open'
  | 'file-text'
  | 'database'
  | 'banknote'
  | 'coins'
  | 'percent'
  | 'scale'
  | 'wallet'
  | 'piggy-bank'
  | 'boxes'
  | 'hammer'
  | 'trending-down'
  | 'users'
  | 'activity';

export type Ponto = { periodo: string; valor: number };

export type No = {
  id: string;
  tipo: TipoNo;
  rotulo: string;
  descricao?: string;
  icone: Icone;
  pai?: string;
  /** Pares rótulo/valor mostrados no painel de detalhes. */
  detalhes: [string, string][];
  /** Ids das fontes que sustentam o nó (B1, D1...). */
  referencias: string[];
  /** Indicador: série por período e unidade (a de `formatar`). */
  serie?: Ponto[];
  unidade?: string;
  /** Referência: id da fonte que o nó representa. */
  fonte?: string;
};

export type Aresta = { id: string; origem: string; destino: string; tipo: 'contem' | 'fonte' };

export type FonteBase = {
  id: string;
  tipo: 'banco';
  titulo: string;
  origem: string;
  descricao: string;
  ressalvas: string;
  /** Linhas da empresa na base, mais recentes primeiro, com o rótulo de cada coluna. */
  colunas: string[];
  linhas: Linha[];
  link: string | null;
};

export type FonteDocumento = {
  id: string;
  tipo: 'documento';
  titulo: string;
  arquivo: string;
  ano: number;
  tipoDocumento: string;
  paginas: number;
  link: string | null;
};

export type Fonte = FonteBase | FonteDocumento;

export type Grafo = { id: string; nos: No[]; arestas: Aresta[]; fontes: Fonte[] };

export type Empresa = {
  /** CNPJ só com os 14 dígitos: a chave da empresa (e o parâmetro ?empresa= da rota). */
  cnpj: string;
  cnpjFormatado: string;
  nome: string;
  razaoSocial: string | null;
  /** Grupos do painel com dados da empresa (Financeiro, Distribuição...) e os títulos das bases. */
  grupos: string[];
  bases: string[];
  documentos: number;
};

const ICONES_GRUPO: Record<string, Icone> = {
  Financeiro: 'chart-line',
  Distribuição: 'zap',
  Renováveis: 'wind',
  Geração: 'factory',
  Mercado: 'trending-up',
  Financiamento: 'hand-coins',
};
const ICONES_INDICADOR: [string, Icone][] = [
  ['receita', 'banknote'],
  ['lucro', 'coins'],
  ['margem', 'percent'],
  ['roe', 'percent'],
  ['divida', 'scale'],
  ['cobertura', 'scale'],
  ['caixa', 'wallet'],
  ['patrimonio', 'piggy-bank'],
  ['ativo', 'boxes'],
  ['capex', 'hammer'],
  ['invest', 'hammer'],
  ['construcao', 'hammer'],
  ['depreciacao', 'trending-down'],
  ['ebit', 'trending-up'],
  ['consumidores', 'users'],
  ['dec', 'zap'],
  ['fec', 'zap'],
  ['energia', 'wind'],
  ['corte', 'wind'],
  ['geracao', 'wind'],
];
const AREAS: Record<string, [string, Icone]> = {
  financeiro: ['Documentos de RI e da CVM', 'folder-open'],
  sustentabilidade: ['Relatórios de sustentabilidade', 'leaf'],
};

export const semAcento = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

export function digitosCnpj(cnpj: unknown): string {
  const d = String(cnpj ?? '').replace(/\D/g, '');
  return d ? d.padStart(14, '0') : '';
}

const formatarCnpj = (d: string) =>
  d.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, '$1.$2.$3/$4-$5');

/** Nome de tipo gravado como identificador (fato_relevante) em texto (Fato relevante). */
export function legivel(chave: string): string {
  const s = chave.replace(/[_-]+/g, ' ').trim();
  return s ? s[0].toUpperCase() + s.slice(1) : '';
}

function iconeIndicador(rotulo: string): Icone {
  const nome = semAcento(rotulo);
  return ICONES_INDICADOR.find(([trecho]) => nome.includes(trecho))?.[1] ?? 'activity';
}

/** Primeiro endereço http citado no texto da fonte (as bases do ONS trazem o link do conjunto de dados). */
const linkDaFonte = (texto: string) => /https?:\/\/[^\s,;)]+/.exec(texto)?.[0] ?? null;

type Ligado = { c: Conjunto; iNome: number; iCnpj: number; porEmpresa: boolean };

/**
 * Bases do painel ligadas a empresas pelo CNPJ, com o papel que data/exportar_painel.py declara em cada dimensão.
 * porEmpresa (dimensao_empresa): a linha é a empresa — uma por empresa e período — e só essas dizem quais empresas
 * existem no acervo. As outras (dimensao_dono) são por ativo ou por contrato: um CNPJ aparece em centenas de linhas e
 * o cadastro traz milhares de SPE e pessoas físicas, que não são empresas do acervo. Elas entram no grafo das empresas
 * que já existem, sem criar nenhuma.
 */
function ligados(painel: Painel): Ligado[] {
  return painel.conjuntos.flatMap((c) => {
    const dim = c.dimensao_empresa ?? c.dimensao_dono;
    const iCnpj = indice(c, 'cnpj');
    return dim && iCnpj >= 0
      ? [{ c, iNome: indice(c, dim), iCnpj, porEmpresa: c.dimensao_empresa != null }]
      : [];
  });
}

/** Todas as empresas com dados em alguma base ou documento: as com mais fontes primeiro, depois o nome. */
export function listarEmpresas(painel: Painel, documentos: Documento[]): Empresa[] {
  type Acumulado = {
    nomes: Map<string, string>;
    grupos: Set<string>;
    bases: string[];
    docs: Documento[];
  };
  const porCnpj = new Map<string, Acumulado>();
  const de = (cnpj: string) => {
    let a = porCnpj.get(cnpj);
    if (!a) {
      a = { nomes: new Map(), grupos: new Set(), bases: [], docs: [] };
      porCnpj.set(cnpj, a);
    }
    return a;
  };
  for (const d of documentos) {
    const cnpj = digitosCnpj(d.cnpj);
    if (cnpj) {
      de(cnpj).docs.push(d);
    }
  }
  // Duas passadas, na ordem do papel e não na ordem do painel: primeiro o acervo (documentos e bases por empresa),
  // depois as bases por ativo, que só entram em quem já está no acervo.
  const ligacoes = ligados(painel);
  for (const porEmpresa of [true, false]) {
    for (const { c, iNome, iCnpj } of ligacoes.filter((l) => l.porEmpresa === porEmpresa)) {
      for (const linha of c.linhas) {
        const cnpj = digitosCnpj(linha[iCnpj]);
        const a = cnpj ? (porEmpresa ? de(cnpj) : porCnpj.get(cnpj)) : undefined;
        if (!a || a.nomes.has(c.id)) {
          continue;
        }
        a.nomes.set(c.id, String(linha[iNome]));
        a.grupos.add(c.grupo);
        a.bases.push(c.titulo);
      }
    }
  }
  const empresas = [...porCnpj.entries()].map(([cnpj, a]): Empresa => {
    // O nome do acervo é o comercial (Cemig); o das bases, a razão social (a do painel já é a mais recente).
    const razao = a.nomes.values().next().value ?? null;
    const nome = a.docs[0]?.empresa || razao || formatarCnpj(cnpj);
    return {
      cnpj,
      cnpjFormatado: formatarCnpj(cnpj),
      nome,
      razaoSocial: razao && razao !== nome ? razao : null,
      grupos: [...a.grupos],
      bases: a.bases,
      documentos: a.docs.length,
    };
  });
  const peso = (e: Empresa) => e.bases.length + (e.documentos ? 1 : 0);
  return empresas.sort((x, y) => peso(y) - peso(x) || x.nome.localeCompare(y.nome, 'pt-BR'));
}

/**
 * Linhas da empresa numa base, com os filtros padrão do exportador (ex.: escopo consolidado) quando a empresa tem
 * linhas neles; senão, todas as dela (empresas que só publicam o individual).
 */
function linhasDaEmpresa(
  c: Conjunto,
  iCnpj: number,
  cnpj: string,
): { linhas: Linha[]; recorte: string[] } {
  let linhas = c.linhas.filter((l) => digitosCnpj(l[iCnpj]) === cnpj);
  const recorte: string[] = [];
  for (const [coluna, preferidos] of Object.entries(c.padrao.filtros ?? {})) {
    const i = indice(c, coluna);
    const aceitos = new Set(preferidos);
    const escolhidas = linhas.filter((l) => aceitos.has(String(l[i])));
    if (escolhidas.length) {
      linhas = escolhidas;
    }
    const presentes = [...new Set(linhas.map((l) => String(l[i])))].join(', ');
    recorte.push(`${rotuloDaColuna(c, coluna).toLowerCase()}: ${presentes}`);
  }
  return { linhas, recorte };
}

function rotuloDaColuna(c: Conjunto, coluna: string): string {
  const todas = [...(c.tempo ? [c.tempo] : []), ...c.dimensoes, ...c.medidas, ...c.extras];
  return todas.find((x) => x.coluna === coluna)?.rotulo ?? legivel(coluna);
}

function periodoDe(serie: Ponto[]): string | undefined {
  if (!serie.length) {
    return undefined;
  }
  const [a, b] = [serie[0].periodo, serie[serie.length - 1].periodo];
  return a === b ? a || undefined : `${a}–${b}`;
}

/**
 * O título do acervo repete o tipo antes da data ("Fato relevante (08/02/2019): alteração na diretoria"): dentro do
 * grupo do tipo, o cartão mostra só o assunto e a data.
 */
export function partesDoTitulo(titulo: string): { rotulo: string; data: string | null } {
  const m = /^.*?\((\d{2}\/\d{2}\/\d{4})\)(?::\s*(.+))?$/.exec(titulo);
  return m ? { rotulo: m[2] ?? titulo, data: m[1] } : { rotulo: titulo, data: null };
}

function agruparPor<T>(itens: T[], chave: (item: T) => string): Map<string, T[]> {
  const grupos = new Map<string, T[]>();
  for (const item of itens) {
    const k = chave(item);
    const grupo = grupos.get(k);
    if (grupo) {
      grupo.push(item);
    } else {
      grupos.set(k, [item]);
    }
  }
  return grupos;
}

/** Grafo de uma empresa de `listarEmpresas`. */
export function grafoDaEmpresa(painel: Painel, documentos: Documento[], empresa: Empresa): Grafo {
  const { cnpj } = empresa;
  const nos: No[] = [];
  const arestas: Aresta[] = [];
  const fontes: Fonte[] = [];
  const no = (n: No) => {
    nos.push(n);
    if (n.pai) {
      arestas.push({ id: `${n.pai}->${n.id}`, origem: n.pai, destino: n.id, tipo: 'contem' });
    }
    return n;
  };

  const raiz = no({
    id: `empresa:${cnpj}`,
    tipo: 'empresa',
    rotulo: empresa.nome,
    descricao: empresa.razaoSocial ?? undefined,
    icone: 'building-2',
    detalhes: [
      ['CNPJ', empresa.cnpjFormatado],
      ...(empresa.razaoSocial
        ? ([['Razão social', empresa.razaoSocial]] as [string, string][])
        : []),
      ['Bases com dados', String(empresa.bases.length)],
      ['Documentos indexados', String(empresa.documentos)],
    ],
    referencias: [],
  });

  // Uma categoria por base do painel: indicadores (medidas com dados) e a referência à base.
  for (const { c, iNome, iCnpj } of ligados(painel)) {
    const { linhas, recorte } = linhasDaEmpresa(c, iCnpj, cnpj);
    if (!linhas.length) {
      continue;
    }
    const fid = `B${fontes.length + 1}`;
    const iTempo = c.tempo ? indice(c, c.tempo.coluna) : -1;
    const grupos = agruparPor(linhas, (l) => (iTempo < 0 ? '' : String(l[iTempo])));
    const periodos = [...grupos.keys()].sort();
    fontes.push({
      id: fid,
      tipo: 'banco',
      titulo: c.titulo,
      origem: c.fonte,
      descricao: c.descricao,
      ressalvas: c.ressalvas,
      colunas: c.colunas.map((col) => rotuloDaColuna(c, col)),
      linhas: [...periodos].reverse().flatMap((p) => grupos.get(p) as Linha[]),
      link: linkDaFonte(c.fonte),
    });
    const nomes = [...new Set(linhas.map((l) => String(l[iNome])))];
    const categoria = no({
      id: `${raiz.id}/${c.id}`,
      tipo: 'categoria',
      rotulo: c.titulo,
      descricao: [c.grupo, ...recorte].join(' · '),
      icone: ICONES_GRUPO[c.grupo] ?? 'layers',
      pai: raiz.id,
      detalhes: [
        ['Grupo', c.grupo],
        ['Nome na base', nomes.join('; ')],
        ...recorte.map((r) => ['Recorte', r] as [string, string]),
        ['Linhas da empresa', String(linhas.length)],
      ],
      referencias: [fid],
    });
    const referencia = no({
      id: `fonte:${fid}`,
      tipo: 'referencia',
      rotulo: c.titulo,
      descricao: c.fonte,
      icone: 'database',
      pai: categoria.id,
      detalhes: [],
      referencias: [fid],
      fonte: fid,
    });

    for (const m of c.medidas) {
      const agregar = agregador(c, m);
      const serie = periodos.flatMap((p) => {
        const valor = agregar(grupos.get(p) as Linha[]);
        return valor == null ? [] : [{ periodo: p, valor }];
      });
      if (!serie.length) {
        continue;
      }
      const indicador = no({
        id: `${categoria.id}/${m.coluna}`,
        tipo: 'indicador',
        rotulo: m.rotulo,
        descricao: periodoDe(serie),
        icone: iconeIndicador(m.rotulo),
        pai: categoria.id,
        detalhes: [
          ['Coluna de origem', m.coluna],
          ['Agregação', m.agregacao === 'razao' ? `razão (${m.num} / ${m.den})` : m.agregacao],
        ],
        referencias: [fid],
        serie,
        unidade: m.unidade,
      });
      arestas.push({
        id: `${indicador.id}->${referencia.id}`,
        origem: indicador.id,
        destino: referencia.id,
        tipo: 'fonte',
      });
    }
  }

  // Documentos do acervo: uma categoria por área, um grupo por tipo de documento, os mais recentes primeiro.
  const docs = documentos
    .filter((d) => digitosCnpj(d.cnpj) === cnpj)
    .sort((a, b) => b.ano - a.ano || a.titulo.localeCompare(b.titulo, 'pt-BR'));
  let numeroDoc = 0;
  for (const [area, itens] of agruparPor(docs, (d) => d.area ?? d.arquivo.split('/')[0])) {
    const [rotulo, icone] = AREAS[area] ?? [`Documentos (${area})`, 'folder-open'];
    const categoria = no({
      id: `${raiz.id}/docs-${area}`,
      tipo: 'categoria',
      rotulo,
      descricao: `${itens.length} ${itens.length === 1 ? 'documento' : 'documentos'}`,
      icone,
      pai: raiz.id,
      detalhes: [['Documentos', String(itens.length)]],
      referencias: [],
    });
    for (const [tipo, lista] of agruparPor(itens, (d) => d.tipo)) {
      const [ultimo, primeiro] = [lista[0].ano, lista[lista.length - 1].ano];
      const grupo = no({
        id: `${categoria.id}/${tipo}`,
        tipo: 'grupo',
        rotulo: legivel(tipo),
        descricao: `${lista.length} · ${primeiro === ultimo ? primeiro : `${primeiro}–${ultimo}`}`,
        icone: 'folder-open',
        pai: categoria.id,
        detalhes: [['Documentos', String(lista.length)]],
        referencias: [],
      });
      for (const d of lista) {
        const fid = `D${++numeroDoc}`;
        fontes.push({
          id: fid,
          tipo: 'documento',
          titulo: d.titulo,
          arquivo: d.arquivo,
          ano: d.ano,
          tipoDocumento: legivel(d.tipo),
          paginas: d.paginas,
          link: d.url || null,
        });
        const { rotulo, data } = partesDoTitulo(d.titulo);
        no({
          id: `fonte:${fid}`,
          tipo: 'referencia',
          rotulo,
          descricao: `${data ?? d.ano} · ${d.paginas} p.`,
          icone: 'file-text',
          pai: grupo.id,
          detalhes: [],
          referencias: [fid],
          fonte: fid,
        });
      }
    }
  }

  return { id: `empresa-${cnpj}`, nos, arestas, fontes };
}

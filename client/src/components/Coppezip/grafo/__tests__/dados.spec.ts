import type { Conjunto, Painel } from '../../painel/dados';
import {
  digitosCnpj,
  grafoDaEmpresa,
  listarEmpresas,
  partesDoTitulo,
  type Documento,
} from '../dados';
import { buildModel, computeLayout, frameItems } from '../modelo';

// Recorte do painel.json: kpis_anuais (escopo consolidado por padrão) e dec_fec, ligados pelo CNPJ.
const kpis: Conjunto = {
  id: 'kpis_anuais',
  grupo: 'Financeiro',
  titulo: 'Indicadores financeiros anuais',
  descricao: 'Indicadores anuais',
  fonte: 'CVM DFP',
  ressalvas: '',
  tempo: { coluna: 'ano', rotulo: 'Ano' },
  granularidade: 'ano',
  dimensoes: [
    { coluna: 'empresa', rotulo: 'Empresa' },
    { coluna: 'escopo', rotulo: 'Escopo' },
  ],
  medidas: [
    { coluna: 'receita', rotulo: 'Receita líquida', unidade: 'brl', agregacao: 'soma' },
    { coluna: 'lucro', rotulo: 'Lucro líquido', unidade: 'brl', agregacao: 'soma' },
    {
      coluna: 'margem',
      rotulo: 'Margem líquida',
      unidade: 'pct',
      agregacao: 'razao',
      num: 'lucro',
      den: 'receita',
      fator: 100,
    },
    { coluna: 'capex', rotulo: 'CAPEX', unidade: 'brl', agregacao: 'soma' },
  ],
  extras: [{ coluna: 'cnpj', rotulo: 'CNPJ' }],
  padrao: { medida: 'receita', serie: 'empresa', filtros: { escopo: ['consolidado'] } },
  busca: { empresa: { 'CIA ENERGETICA DE MINAS GERAIS': '17.155.730/0001-64 CMIG4 Cemig' } },
  colunas: ['empresa', 'escopo', 'ano', 'cnpj', 'receita', 'lucro', 'margem', 'capex'],
  linhas: [
    [
      'CIA ENERGETICA DE MINAS GERAIS',
      'consolidado',
      '2024',
      '17.155.730/0001-64',
      100,
      10,
      10,
      null,
    ],
    [
      'CIA ENERGETICA DE MINAS GERAIS',
      'individual',
      '2024',
      '17.155.730/0001-64',
      70,
      9,
      12.9,
      null,
    ],
    [
      'CIA ENERGETICA DE MINAS GERAIS',
      'consolidado',
      '2025',
      '17.155.730/0001-64',
      200,
      30,
      15,
      null,
    ],
    ['SO INDIVIDUAL SA', 'individual', '2025', '11.111.111/0001-11', 50, 5, 10, null],
  ],
};

const decFec: Conjunto = {
  ...kpis,
  id: 'dec_fec',
  grupo: 'Distribuição',
  titulo: 'DEC e FEC por distribuidora',
  fonte: 'ANEEL, https://dadosabertos.aneel.gov.br/dataset/indicadores',
  dimensoes: [{ coluna: 'distribuidora', rotulo: 'Distribuidora' }],
  medidas: [{ coluna: 'dec', rotulo: 'DEC (horas)', unidade: 'h', agregacao: 'media' }],
  padrao: { medida: 'dec', serie: 'distribuidora' },
  busca: { distribuidora: { CEMIG: '17.155.730/0001-64' } },
  colunas: ['distribuidora', 'ano', 'cnpj', 'dec'],
  linhas: [
    ['CEMIG', '2024', '17155730000164', 10.5],
    ['CEMIG', '2025', '17155730000164', 9.5],
  ],
};

// Sem a coluna cnpj: não se liga a empresas.
const cmo: Conjunto = {
  ...kpis,
  id: 'cmo',
  busca: {},
  colunas: ['subsistema', 'mes', 'cmo'],
  linhas: [['SE', '2024-01', 100]],
};

const painel: Painel = { gerado_em: '', banco: '', conjuntos: [kpis, decFec, cmo] };

const doc = (arquivo: string, tipo: string, ano: number): Documento => ({
  arquivo,
  empresa: 'Cemig',
  cnpj: '17.155.730/0001-64',
  ano,
  tipo,
  titulo: `${tipo} ${ano}`,
  paginas: 10,
  url: null,
});
const documentos = [
  doc('financeiro/cemig/pdfs/2024/a.pdf', 'fato_relevante', 2024),
  doc('financeiro/cemig/pdfs/2025/b.pdf', 'fato_relevante', 2025),
  doc('sustentabilidade/cemig/2024/c.pdf', 'relatorio_sustentabilidade', 2024),
];

const CEMIG = '17155730000164';

describe('listarEmpresas', () => {
  it('junta as bases e os documentos pelo CNPJ, com o nome comercial do acervo', () => {
    const empresas = listarEmpresas(painel, documentos);
    expect(empresas.map((e) => e.cnpj)).toEqual([CEMIG, '11111111000111']);
    expect(empresas[0]).toMatchObject({
      nome: 'Cemig',
      razaoSocial: 'CIA ENERGETICA DE MINAS GERAIS',
      cnpjFormatado: '17.155.730/0001-64',
      grupos: ['Financeiro', 'Distribuição'],
      documentos: 3,
    });
    expect(empresas[1]).toMatchObject({
      nome: 'SO INDIVIDUAL SA',
      razaoSocial: null,
      documentos: 0,
    });
  });

  it('normaliza o CNPJ com ou sem pontuação e sem o zero à esquerda', () => {
    expect(digitosCnpj('00.001.180/0001-26')).toBe('00001180000126');
    expect(digitosCnpj(1180000126)).toBe('00001180000126');
    expect(digitosCnpj(null)).toBe('');
  });
});

describe('grafoDaEmpresa', () => {
  const [cemig, soIndividual] = listarEmpresas(painel, documentos);
  const grafo = grafoDaEmpresa(painel, documentos, cemig);
  const no = (id: string) => grafo.nos.find((n) => n.id === id);

  it('agrega cada medida por período pela regra do exportador, no escopo padrão', () => {
    const margem = no(`empresa:${CEMIG}/kpis_anuais/margem`);
    expect(margem?.serie).toEqual([
      { periodo: '2024', valor: 10 },
      { periodo: '2025', valor: 15 },
    ]);
    expect(margem?.descricao).toBe('2024–2025');
    expect(no(`empresa:${CEMIG}/kpis_anuais`)?.descricao).toBe('Financeiro · escopo: consolidado');
  });

  it('não cria indicador para medida sem dado', () => {
    expect(no(`empresa:${CEMIG}/kpis_anuais/capex`)).toBeUndefined();
  });

  it('usa o escopo que a empresa tem quando falta o padrão', () => {
    const g = grafoDaEmpresa(painel, documentos, soIndividual);
    const receita = g.nos.find((n) => n.id.endsWith('/kpis_anuais/receita'));
    expect(receita?.serie).toEqual([{ periodo: '2025', valor: 50 }]);
    expect(g.nos.find((n) => n.id.endsWith('/kpis_anuais'))?.descricao).toBe(
      'Financeiro · escopo: individual',
    );
  });

  it('liga cada indicador à referência da base e numera as fontes', () => {
    const ref = no('fonte:B2');
    expect(ref).toMatchObject({
      tipo: 'referencia',
      rotulo: 'DEC e FEC por distribuidora',
      fonte: 'B2',
    });
    expect(grafo.arestas).toContainEqual({
      id: `empresa:${CEMIG}/dec_fec/dec->fonte:B2`,
      origem: `empresa:${CEMIG}/dec_fec/dec`,
      destino: 'fonte:B2',
      tipo: 'fonte',
    });
    const fonte = grafo.fontes.find((f) => f.id === 'B2');
    expect(fonte).toMatchObject({ link: 'https://dadosabertos.aneel.gov.br/dataset/indicadores' });
    expect(fonte?.tipo === 'banco' && fonte.linhas.map((l) => l[1])).toEqual(['2025', '2024']);
  });

  it('agrupa os documentos por área e tipo, os mais recentes primeiro', () => {
    const grupo = no(`empresa:${CEMIG}/docs-financeiro/fato_relevante`);
    expect(grupo).toMatchObject({
      tipo: 'grupo',
      rotulo: 'Fato relevante',
      descricao: '2 · 2024–2025',
    });
    const filhos = grafo.nos.filter((n) => n.pai === grupo?.id).map((n) => n.rotulo);
    expect(filhos).toEqual(['fato_relevante 2025', 'fato_relevante 2024']);
    expect(no(`empresa:${CEMIG}/docs-sustentabilidade`)?.rotulo).toBe(
      'Relatórios de sustentabilidade',
    );
    expect(grafo.fontes.filter((f) => f.tipo === 'documento')).toHaveLength(3);
  });
});

describe('partesDoTitulo', () => {
  it('separa o assunto e a data do título do acervo', () => {
    expect(partesDoTitulo('Fato relevante (08/02/2019): alteracao na diretoria')).toEqual({
      rotulo: 'alteracao na diretoria',
      data: '08/02/2019',
    });
    expect(partesDoTitulo('Df anuais completas (30/03/2004)')).toEqual({
      rotulo: 'Df anuais completas (30/03/2004)',
      data: '30/03/2004',
    });
    expect(partesDoTitulo('Relatório de sustentabilidade 2024')).toEqual({
      rotulo: 'Relatório de sustentabilidade 2024',
      data: null,
    });
  });
});

describe('computeLayout', () => {
  const [cemig] = listarEmpresas(painel, documentos);
  const model = buildModel(grafoDaEmpresa(painel, documentos, cemig));
  const grupo = `empresa:${CEMIG}/docs-financeiro/fato_relevante`;
  const area = `empresa:${CEMIG}/docs-financeiro`;

  it('empilha folhas e grupos recolhidos na moldura do pai', () => {
    expect(frameItems(model, new Set([grupo]), area)).toEqual([grupo]);
    const { boxes } = computeLayout(model, new Set([grupo]));
    expect(boxes.get(grupo)?.frame).toBe(`frame::${area}`);
    expect(boxes.has('fonte:D1')).toBe(false);
  });

  it('tira o grupo expandido da moldura e põe os documentos na dele', () => {
    const { boxes, bounds } = computeLayout(model, new Set());
    expect(boxes.get(grupo)?.frame).toBeUndefined();
    expect(boxes.get('fonte:D1')?.frame).toBe(`frame::${grupo}`);
    expect(bounds?.w).toBeGreaterThan(0);
  });

  it('esconde a subárvore do nó recolhido', () => {
    const { boxes } = computeLayout(model, new Set([`empresa:${CEMIG}`]));
    expect([...boxes.keys()]).toEqual([`empresa:${CEMIG}`]);
  });
});

import {
  agregador,
  atribuirCores,
  casaBusca,
  filtrar,
  formatar,
  marcas,
  ranking,
  serieTemporal,
  variacao,
  type Conjunto,
} from '../dados';

// Recorte do conjunto kpis_anuais do painel.json, com as regras de agregação do exportador.
const conjunto: Conjunto = {
  id: 'kpis_anuais',
  grupo: 'Financeiro',
  titulo: 'Indicadores financeiros anuais',
  descricao: '',
  fonte: '',
  ressalvas: '',
  tempo: { coluna: 'ano', rotulo: 'Ano' },
  granularidade: 'ano',
  dimensoes: [
    { coluna: 'empresa', rotulo: 'Empresa' },
    { coluna: 'escopo', rotulo: 'Escopo' },
  ],
  medidas: [
    { coluna: 'receita', rotulo: 'Receita', unidade: 'brl', agregacao: 'soma' },
    {
      coluna: 'margem',
      rotulo: 'Margem',
      unidade: 'pct',
      agregacao: 'razao',
      num: 'lucro',
      den: 'receita',
      fator: 100,
    },
    { coluna: 'dec', rotulo: 'DEC', unidade: 'h', agregacao: 'ponderada', peso: 'consumidores' },
    { coluna: 'lucro', rotulo: 'Lucro', unidade: 'brl', agregacao: 'max' },
  ],
  extras: [],
  padrao: { medida: 'receita', serie: 'empresa' },
  busca: { empresa: { 'TAESA S.A.': '07.859.971/0001-30 Taesa TAEE11' } },
  dimensao_empresa: 'empresa',
  dimensao_dono: null,
  colunas: ['empresa', 'escopo', 'ano', 'receita', 'lucro', 'dec', 'consumidores'],
  linhas: [
    ['TAESA S.A.', 'consolidado', '2024', 100, 40, 10, 1],
    ['TAESA S.A.', 'consolidado', '2025', 120, 30, null, 1],
    ['CEMIG', 'consolidado', '2024', 300, 60, 20, 3],
    ['CEMIG', 'individual', '2025', 50, 5, 12, 1],
  ],
};

const agregar = (coluna: string) =>
  agregador(conjunto, conjunto.medidas.find((m) => m.coluna === coluna)!);

describe('dados do painel', () => {
  it('filtra por dimensão e período', () => {
    expect(filtrar(conjunto, { escopo: ['consolidado'] }, '2025', '2025')).toEqual([
      conjunto.linhas[1],
    ]);
    expect(filtrar(conjunto, { empresa: [] })).toHaveLength(4);
  });

  it('agrega pela regra de cada medida', () => {
    const tudo = conjunto.linhas;
    expect(agregar('receita')(tudo)).toBe(570);
    // margem é a razão das somas (135 / 570), não a soma das margens
    expect(agregar('margem')(tudo)).toBeCloseTo((100 * 135) / 570);
    // média ponderada pelos consumidores, ignorando a linha sem DEC
    expect(agregar('dec')(tudo)).toBeCloseTo((10 * 1 + 20 * 3 + 12 * 1) / 5);
    expect(agregar('lucro')(tudo)).toBe(60);
    expect(agregar('receita')([])).toBeNull();
  });

  it('monta série temporal e ranking', () => {
    expect(serieTemporal(conjunto.linhas, 2, ['2023', '2024', '2025'], agregar('receita'))).toEqual(
      [null, 400, 170],
    );
    expect(ranking(conjunto.linhas, 0, agregar('receita'))).toEqual([
      { chave: 'CEMIG', valor: 350 },
      { chave: 'TAESA S.A.', valor: 220 },
    ]);
  });

  it('acha empresa por apelido, ticker e CNPJ, sem acento', () => {
    const termos = conjunto.busca.empresa['TAESA S.A.'];
    expect(casaBusca('TAESA S.A.', termos, 'taee11')).toBe(true);
    expect(casaBusca('TAESA S.A.', termos, '07859971000130')).toBe(true);
    expect(casaBusca('COMPANHIA ENERGÉTICA', undefined, 'energetica')).toBe(true);
    expect(casaBusca('TAESA S.A.', termos, 'cemig')).toBe(false);
  });

  it('mantém a cor de quem continua quando o filtro muda', () => {
    const a = atribuirCores(new Map(), ['A', 'B', 'C']);
    const b = atribuirCores(a, ['A', 'C', 'D']);
    expect(b.get('A')).toBe(0);
    expect(b.get('C')).toBe(2);
    expect(b.get('D')).toBe(1); // ocupa a vaga liberada por B
  });

  it('formata em pt-BR', () => {
    expect(formatar(4_200_000_000, 'brl')).toBe('R$ 4,2 bi');
    expect(formatar(12.34, 'pct')).toBe('12,3%');
    expect(formatar(null, 'brl')).toBe('–');
    expect(variacao(120, 100, 'brl')).toBe('+20%');
    expect(variacao(10, 12.5, 'pct')).toBe('−2,5 p.p.');
    expect(variacao(-5, 10, 'brl')).toBeNull();
  });

  it('gera marcas redondas que cobrem os dados', () => {
    expect(marcas(0, 950)).toEqual([0, 200, 400, 600, 800, 1000]);
    expect(marcas(0, 1100)).toEqual([0, 250, 500, 750, 1000, 1250]);
    const m = marcas(-37, 112);
    expect(m[0]).toBeLessThanOrEqual(-37);
    expect(m[m.length - 1]).toBeGreaterThanOrEqual(112);
  });
});

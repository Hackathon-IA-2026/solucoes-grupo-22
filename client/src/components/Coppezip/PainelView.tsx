import { useEffect, useMemo, useRef, useState } from 'react';
import { get, mensagemDeErro } from './api';
import Filtro, { Etiquetas } from './painel/Filtro';
import { Cartao, GraficoBarras, GraficoLinha, Legenda, Mini, type Serie } from './painel/Graficos';
import {
  MAX_SERIES,
  agregador,
  agrupar,
  atribuirCores,
  filtrar,
  formatar,
  indice,
  ranking,
  serieTemporal,
  valores,
  variacao,
  type Conjunto,
  type Filtros,
  type Painel,
} from './painel/dados';

const TOP_RANKING = 15;
const LINHAS_TABELA = 200;
const TOTAL = '__total__';

const celula = (v: unknown) => {
  if (v == null) {
    return '';
  }
  return typeof v === 'number' ? v.toLocaleString('pt-BR') : String(v);
};

const classeSelect =
  'rounded-xl border border-border-light bg-surface-primary px-3 py-2 text-sm text-text-primary';

/** Filtros e escolhas iniciais de um conjunto, pelo `padrao` do exportador. */
function inicial(c: Conjunto) {
  const periodos = c.tempo ? valores(c, c.tempo.coluna) : [];
  const filtros: Filtros = {};
  for (const [coluna, lista] of Object.entries(c.padrao.filtros ?? {})) {
    const existentes = new Set(valores(c, coluna));
    filtros[coluna] = lista.filter((v) => existentes.has(v));
  }
  const desde = c.padrao.desde ? periodos.find((p) => p >= (c.padrao.desde as string)) : undefined;
  return {
    filtros,
    de: desde ?? periodos[0] ?? '',
    ate: periodos[periodos.length - 1] ?? '',
    medida: c.padrao.medida,
    serie: c.padrao.serie,
  };
}

export default function PainelView() {
  const [painel, setPainel] = useState<Painel | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [conjuntoId, setConjuntoId] = useState('');
  const [estado, setEstado] = useState<ReturnType<typeof inicial> | null>(null);
  const cores = useRef(new Map<string, number>());

  useEffect(() => {
    get<Painel>('/api/painel/dados')
      .then((dados) => {
        setPainel(dados);
        const primeiro = dados.conjuntos[0];
        if (primeiro) {
          setConjuntoId(primeiro.id);
          setEstado(inicial(primeiro));
        }
      })
      .catch((e) => setErro(mensagemDeErro(e)));
  }, []);

  const conjunto = useMemo(
    () => painel?.conjuntos.find((c) => c.id === conjuntoId) ?? null,
    [painel, conjuntoId],
  );

  const escolherConjunto = (id: string) => {
    const c = painel?.conjuntos.find((x) => x.id === id);
    if (c) {
      cores.current = new Map();
      setConjuntoId(id);
      setEstado(inicial(c));
    }
  };

  const periodosTodos = useMemo(
    () => (conjunto?.tempo ? valores(conjunto, conjunto.tempo.coluna) : []),
    [conjunto],
  );
  const opcoes = useMemo(() => {
    const saida: Record<string, string[]> = {};
    conjunto?.dimensoes.forEach((d) => {
      saida[d.coluna] = valores(conjunto, d.coluna);
    });
    return saida;
  }, [conjunto]);
  const agregadores = useMemo(
    () => new Map(conjunto?.medidas.map((m) => [m.coluna, agregador(conjunto, m)]) ?? []),
    [conjunto],
  );

  const linhas = useMemo(
    () => (conjunto && estado ? filtrar(conjunto, estado.filtros, estado.de, estado.ate) : []),
    [conjunto, estado],
  );
  const periodos = useMemo(
    () =>
      periodosTodos.filter(
        (p) => (!estado?.de || p >= estado.de) && (!estado?.ate || p <= estado.ate),
      ),
    [periodosTodos, estado?.de, estado?.ate],
  );

  const analise = useMemo(() => {
    if (!conjunto || !estado) {
      return null;
    }
    const medida = conjunto.medidas.find((m) => m.coluna === estado.medida) ?? conjunto.medidas[0];
    const agregar = agregadores.get(medida.coluna) as (l: unknown[][]) => number | null;
    const iSerie = indice(conjunto, estado.serie);
    const iTempo = conjunto.tempo ? indice(conjunto, conjunto.tempo.coluna) : -1;
    const grupos = agrupar(linhas, iSerie);
    const presentes = [...grupos.keys()]
      .filter((k) => k !== 'null')
      .sort((a, b) => a.localeCompare(b, 'pt-BR'));
    const escolhidos = (estado.filtros[estado.serie] ?? []).filter((v) => grupos.has(v));

    let chaves: string[];
    if (escolhidos.length > 0) {
      chaves = escolhidos.slice(0, MAX_SERIES);
    } else if (presentes.length <= MAX_SERIES) {
      chaves = presentes;
    } else {
      chaves = [TOTAL];
    }
    cores.current = atribuirCores(cores.current, chaves);
    const series: Serie[] =
      iTempo < 0
        ? []
        : chaves.map((k) => ({
            chave: k,
            rotulo: k === TOTAL ? 'Total da seleção' : k,
            cor: cores.current.get(k) ?? 0,
            valores: serieTemporal(
              k === TOTAL ? linhas : (grupos.get(k) ?? []),
              iTempo,
              periodos,
              agregar,
            ),
          }));

    // ranking no período mais recente do recorte com dado para a medida
    let periodoRanking: string | null = null;
    let linhasRanking = linhas;
    if (iTempo >= 0) {
      const porPeriodo = agrupar(linhas, iTempo);
      periodoRanking =
        [...periodos].reverse().find((p) => {
          const g = porPeriodo.get(p);
          return g != null && agregar(g) != null;
        }) ?? null;
      linhasRanking = periodoRanking ? (porPeriodo.get(periodoRanking) ?? []) : [];
    }
    const ordem = ranking(linhasRanking, iSerie, agregar);

    // um cartão por medida: valor no último período com dado, variação contra o anterior e tendência
    const indicadores = conjunto.medidas.map((m) => {
      const ag = agregadores.get(m.coluna) as (l: unknown[][]) => number | null;
      if (iTempo < 0) {
        return {
          medida: m,
          valor: ag(linhas),
          serie: [] as (number | null)[],
          periodo: null,
          delta: null,
        };
      }
      const serie = serieTemporal(linhas, iTempo, periodos, ag);
      const com = serie.map((v, i) => ({ v, i })).filter((p) => p.v != null);
      const ultimo = com[com.length - 1];
      const penultimo = com[com.length - 2];
      return {
        medida: m,
        valor: ultimo?.v ?? null,
        serie,
        periodo: ultimo ? periodos[ultimo.i] : null,
        delta: penultimo
          ? { texto: variacao(ultimo.v, penultimo.v, m.unidade), contra: periodos[penultimo.i] }
          : null,
      };
    });

    return {
      medida,
      series,
      periodoRanking,
      ordem,
      indicadores,
      presentes: presentes.length,
      excedentes: Math.max(0, escolhidos.length - MAX_SERIES),
    };
  }, [conjunto, estado, linhas, periodos, agregadores]);

  if (erro) {
    return <div className="p-6 text-red-500">Erro carregando o painel: {erro}</div>;
  }
  if (!painel || !conjunto || !estado || !analise) {
    return <div className="p-6 text-text-secondary">Carregando painel...</div>;
  }

  const mudar = (parcial: Partial<typeof estado>) => setEstado({ ...estado, ...parcial });
  const mudarFiltro = (coluna: string, lista: string[]) =>
    mudar({ filtros: { ...estado.filtros, [coluna]: lista } });
  const rotuloDe = (coluna: string) =>
    [conjunto.tempo, ...conjunto.dimensoes, ...conjunto.medidas, ...conjunto.extras].find(
      (c) => c?.coluna === coluna,
    )?.rotulo ?? coluna;
  const grupos = Array.from(new Set(painel.conjuntos.map((c) => c.grupo)));
  const temFiltro = Object.values(estado.filtros).some((l) => l.length > 0);
  const { medida, series, ordem } = analise;
  const dimSerie = rotuloDe(estado.serie);

  const baixarCsv = () => {
    const csv = [conjunto.colunas, ...linhas.map((l) => l.map((v) => (v == null ? '' : String(v))))]
      .map((l) => l.map((v) => `"${v.replace(/"/g, '""')}"`).join(','))
      .join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `${conjunto.id}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  let notaSeries: string | null = null;
  if (series.length === 1 && series[0].chave === TOTAL) {
    notaSeries = `${analise.presentes} valores de ${dimSerie} no recorte: a linha mostra o total. Escolha até ${MAX_SERIES} no filtro ${dimSerie} para comparar.`;
  } else if (analise.excedentes > 0) {
    notaSeries = `Mostrando os ${MAX_SERIES} primeiros escolhidos; ${analise.excedentes} ficaram só no ranking e na tabela.`;
  }

  return (
    <div className="flex h-full flex-col gap-5 overflow-y-auto p-6 text-text-primary">
      <header className="flex flex-col gap-1">
        <h1 className="text-xl font-semibold">Painel de dados</h1>
        <p className="text-sm text-text-secondary">
          Os mesmos números que o analista consulta. Gerado em {painel.gerado_em} a partir de{' '}
          {painel.banco}.
        </p>
      </header>

      <section className="flex flex-col gap-2">
        <select
          aria-label="Conjunto de dados"
          className={`${classeSelect} max-w-md font-medium`}
          value={conjuntoId}
          onChange={(e) => escolherConjunto(e.target.value)}
        >
          {grupos.map((grupo) => (
            <optgroup key={grupo} label={grupo}>
              {painel.conjuntos
                .filter((c) => c.grupo === grupo)
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.titulo}
                  </option>
                ))}
            </optgroup>
          ))}
        </select>
        <p className="max-w-4xl text-xs text-text-secondary">
          {conjunto.descricao} Fonte: {conjunto.fonte}.
          {conjunto.ressalvas ? ` Ressalvas: ${conjunto.ressalvas}.` : ''}
        </p>
      </section>

      {/* uma linha de filtros acima de tudo o que eles recortam */}
      <section className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          {conjunto.dimensoes.map((d) => (
            <Filtro
              key={d.coluna}
              rotulo={d.rotulo}
              opcoes={opcoes[d.coluna] ?? []}
              termos={conjunto.busca[d.coluna]}
              selecionados={estado.filtros[d.coluna] ?? []}
              onChange={(lista) => mudarFiltro(d.coluna, lista)}
            />
          ))}
          {conjunto.tempo &&
            (conjunto.granularidade === 'dia' ? (
              <>
                <input
                  type="date"
                  aria-label="Desde"
                  className={classeSelect}
                  min={periodosTodos[0]}
                  max={estado.ate}
                  value={estado.de}
                  onChange={(e) => mudar({ de: e.target.value })}
                />
                <input
                  type="date"
                  aria-label="Até"
                  className={classeSelect}
                  min={estado.de}
                  max={periodosTodos[periodosTodos.length - 1]}
                  value={estado.ate}
                  onChange={(e) => mudar({ ate: e.target.value })}
                />
              </>
            ) : (
              <>
                <select
                  aria-label={`${conjunto.tempo.rotulo} inicial`}
                  className={classeSelect}
                  value={estado.de}
                  onChange={(e) => mudar({ de: e.target.value })}
                >
                  {periodosTodos
                    .filter((p) => p <= estado.ate)
                    .map((p) => (
                      <option key={p}>{p}</option>
                    ))}
                </select>
                <span className="text-sm text-text-secondary">a</span>
                <select
                  aria-label={`${conjunto.tempo.rotulo} final`}
                  className={classeSelect}
                  value={estado.ate}
                  onChange={(e) => mudar({ ate: e.target.value })}
                >
                  {periodosTodos
                    .filter((p) => p >= estado.de)
                    .map((p) => (
                      <option key={p}>{p}</option>
                    ))}
                </select>
              </>
            ))}
          <label className="flex items-center gap-2 text-sm text-text-secondary">
            Agrupar por
            <select
              className={classeSelect}
              value={estado.serie}
              onChange={(e) => {
                cores.current = new Map();
                mudar({ serie: e.target.value });
              }}
            >
              {conjunto.dimensoes.map((d) => (
                <option key={d.coluna} value={d.coluna}>
                  {d.rotulo}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-text-secondary">
            Medida
            <select
              className={`${classeSelect} max-w-[260px]`}
              value={medida.coluna}
              onChange={(e) => mudar({ medida: e.target.value })}
            >
              {conjunto.medidas.map((m) => (
                <option key={m.coluna} value={m.coluna}>
                  {m.rotulo}
                </option>
              ))}
            </select>
          </label>
        </div>
        {temFiltro && (
          <div className="flex flex-wrap items-center gap-1.5">
            {conjunto.dimensoes.map((d) => (
              <Etiquetas
                key={d.coluna}
                rotulo={d.rotulo}
                selecionados={estado.filtros[d.coluna] ?? []}
                onChange={(lista) => mudarFiltro(d.coluna, lista)}
              />
            ))}
            <button
              type="button"
              className="px-2 text-xs text-text-secondary underline"
              onClick={() => mudar({ filtros: {} })}
            >
              limpar filtros
            </button>
          </div>
        )}
      </section>

      {/* todas as medidas numéricas do conjunto, no recorte dos filtros */}
      <section
        aria-label="Indicadores"
        className="grid gap-3"
        style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))' }}
      >
        {analise.indicadores.map(({ medida: m, valor, serie, periodo, delta }) => {
          const ativa = m.coluna === medida.coluna;
          return (
            <button
              key={m.coluna}
              type="button"
              onClick={() => mudar({ medida: m.coluna })}
              aria-pressed={ativa}
              className={`flex flex-col gap-1 rounded-xl border bg-surface-primary p-3 text-left hover:bg-surface-hover ${
                ativa
                  ? 'border-[var(--painel-1)] ring-1 ring-[var(--painel-1)]'
                  : 'border-border-light'
              }`}
            >
              <span className="text-xs text-text-secondary">{m.rotulo}</span>
              <span className="text-lg font-semibold text-text-primary">
                {formatar(valor, m.unidade)}
              </span>
              <span className="text-xs text-text-secondary">
                {periodo ?? (conjunto.tempo ? 'sem dado no recorte' : 'total do recorte')}
                {delta?.texto ? ` · ${delta.texto} vs ${delta.contra}` : ''}
              </span>
              {conjunto.tempo && <Mini valores={serie} />}
            </button>
          );
        })}
      </section>

      <section className={`grid gap-4 ${conjunto.tempo ? 'xl:grid-cols-5' : ''}`}>
        {conjunto.tempo && (
          <div className="min-w-0 xl:col-span-3">
            <Cartao
              titulo={`${medida.rotulo} por ${conjunto.tempo.rotulo.toLowerCase()}`}
              subtitulo={
                notaSeries ??
                `Por ${dimSerie.toLowerCase()}, ${periodos[0]} a ${periodos[periodos.length - 1]}`
              }
              tabela={
                <table className="w-full text-left text-xs">
                  <thead className="sticky top-0 bg-surface-primary">
                    <tr>
                      <th className="px-2 py-1.5 font-medium">{conjunto.tempo.rotulo}</th>
                      {series.map((s) => (
                        <th key={s.chave} className="px-2 py-1.5 text-right font-medium">
                          {s.rotulo}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {periodos
                      .map((p, i) => ({ p, i }))
                      .reverse()
                      .map(({ p, i }) => (
                        <tr key={p} className="border-t border-border-light">
                          <td className="px-2 py-1">{p}</td>
                          {series.map((s) => (
                            <td key={s.chave} className="px-2 py-1 text-right tabular-nums">
                              {formatar(s.valores[i], medida.unidade)}
                            </td>
                          ))}
                        </tr>
                      ))}
                  </tbody>
                </table>
              }
            >
              <Legenda series={series} />
              <GraficoLinha periodos={periodos} series={series} unidade={medida.unidade} />
            </Cartao>
          </div>
        )}
        <div className={`min-w-0 ${conjunto.tempo ? 'xl:col-span-2' : ''}`}>
          <Cartao
            titulo={`Ranking por ${dimSerie.toLowerCase()}`}
            subtitulo={`${medida.rotulo}${analise.periodoRanking ? ` em ${analise.periodoRanking}` : ''}${
              ordem.length > TOP_RANKING ? ` · ${TOP_RANKING} maiores de ${ordem.length}` : ''
            }`}
            tabela={
              <table className="w-full text-left text-xs">
                <tbody>
                  {ordem.map((o, i) => (
                    <tr key={o.chave} className="border-t border-border-light">
                      <td className="px-2 py-1 tabular-nums text-text-secondary">{i + 1}</td>
                      <td className="px-2 py-1">{o.chave}</td>
                      <td className="px-2 py-1 text-right tabular-nums">
                        {formatar(o.valor, medida.unidade)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            }
          >
            <GraficoBarras itens={ordem.slice(0, TOP_RANKING)} unidade={medida.unidade} />
          </Cartao>
        </div>
      </section>

      <section className="flex flex-col gap-2 rounded-xl border border-border-light p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <div className="text-sm font-semibold">Linhas da base</div>
            <div className="text-xs text-text-secondary">
              {linhas.length} de {conjunto.linhas.length} linhas no recorte
              {linhas.length > LINHAS_TABELA
                ? `; mostrando ${LINHAS_TABELA}, o CSV traz todas`
                : ''}
            </div>
          </div>
          <button
            type="button"
            className="rounded-lg border border-border-light px-3 py-1.5 text-sm hover:bg-surface-hover"
            onClick={baixarCsv}
          >
            Baixar CSV
          </button>
        </div>
        <div className="max-h-[420px] overflow-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead className="sticky top-0 bg-surface-primary">
              <tr>
                {conjunto.colunas.map((c) => (
                  <th key={c} className="whitespace-nowrap px-2 py-1.5 font-medium">
                    {rotuloDe(c)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {linhas.slice(0, LINHAS_TABELA).map((l, i) => (
                <tr key={i} className="border-t border-border-light">
                  {l.map((v, j) => (
                    <td
                      key={j}
                      className={`whitespace-nowrap px-2 py-1 ${typeof v === 'number' ? 'text-right tabular-nums' : ''}`}
                    >
                      {celula(v)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

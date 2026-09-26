/* eslint-disable i18next/no-literal-string -- aba do CoppeZIP: textos em português, como os dados que ela mostra */
import { useEffect, useMemo, useRef, useState } from 'react';
import type { PointerEvent } from 'react';
import { Table2 } from 'lucide-react';
import type { Grafico } from './data';
import { formatar } from './data';
import { cn } from '~/utils';

/*
 * Paleta categórica validada (claro sobre o branco, escuro sobre o roxo do tema): azul, laranja e água, sempre nesta
 * ordem. O água fica abaixo de 3:1 no claro, por isso todo gráfico tem legenda e tabela.
 */
const CORES = [
  {
    linha: 'stroke-[#2a78d6] dark:stroke-[#3987e5]',
    ponto: 'fill-[#2a78d6] dark:fill-[#3987e5]',
    chave: 'bg-[#2a78d6] dark:bg-[#3987e5]',
  },
  {
    linha: 'stroke-[#eb6834] dark:stroke-[#d95926]',
    ponto: 'fill-[#eb6834] dark:fill-[#d95926]',
    chave: 'bg-[#eb6834] dark:bg-[#d95926]',
  },
  {
    linha: 'stroke-[#1baf7a] dark:stroke-[#199e70]',
    ponto: 'fill-[#1baf7a] dark:fill-[#199e70]',
    chave: 'bg-[#1baf7a] dark:bg-[#199e70]',
  },
];
const ALTURA = 220;
const M = { topo: 16, direita: 20, baixo: 28, esquerda: 68 };

/** Marcas "redondas" do eixo y (passos de 1, 2, 2,5 ou 5 × 10^n), sempre incluindo o zero. */
function marcas(min: number, max: number) {
  const bruto = (max - min || Math.abs(max) || 1) / 4;
  const mag = 10 ** Math.floor(Math.log10(bruto));
  const passo = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((p) => p >= bruto) ?? 10 * mag;
  const saida: number[] = [];
  for (
    let v = Math.floor(min / passo) * passo;
    v <= Math.ceil(max / passo) * passo + passo / 2;
    v += passo
  ) {
    saida.push(Number(v.toPrecision(12)));
  }
  return saida;
}

export default function LineChart({ grafico }: { grafico: Grafico }) {
  const ref = useRef<HTMLDivElement>(null);
  const [largura, setLargura] = useState(0);
  const [foco, setFoco] = useState<number | null>(null);
  const [tabela, setTabela] = useState(false);
  const { linhas, unidade } = grafico;

  useEffect(() => {
    const el = ref.current;
    if (!el) {
      return;
    }
    const obs = new ResizeObserver(([e]) => setLargura(e.contentRect.width));
    obs.observe(el);
    return () => obs.disconnect();
  }, []);

  const { anos, y, x, ticks } = useMemo(() => {
    const anos = [...new Set(linhas.flatMap((l) => l.pontos.map((p) => p.ano)))].sort(
      (a, b) => a - b,
    );
    const valores = linhas.flatMap((l) => l.pontos.map((p) => p.valor));
    const ticks = marcas(Math.min(0, ...valores), Math.max(0, ...valores));
    const [y0, y1] = [ticks[0], ticks[ticks.length - 1]];
    const alto = ALTURA - M.topo - M.baixo;
    const largo = Math.max(largura - M.esquerda - M.direita, 1);
    const x = (ano: number) =>
      M.esquerda +
      (anos.length > 1 ? ((ano - anos[0]) / (anos[anos.length - 1] - anos[0])) * largo : largo / 2);
    const y = (v: number) => M.topo + alto - ((v - y0) / (y1 - y0 || 1)) * alto;
    return { anos, y, x, ticks };
  }, [linhas, largura]);

  const caminho = (pontos: Grafico['linhas'][number]['pontos']) =>
    pontos
      .map(
        (p, i) =>
          `${i > 0 && pontos[i - 1].ano === p.ano - 1 ? 'L' : 'M'}${x(p.ano)},${y(p.valor)}`,
      )
      .join(' ');

  const anoFoco = foco == null ? null : anos[foco];
  const pular = largura > 0 && largura < 60 * anos.length ? 2 : 1;

  const ultimo = linhas.length === 1 ? linhas[0].pontos[linhas[0].pontos.length - 1] : undefined;

  /** Foco no ano mais próximo do ponteiro: a mira acha o ano, ninguém precisa acertar a linha de 2px. */
  const moverFoco = (e: PointerEvent<SVGRectElement>) => {
    const px = e.clientX - e.currentTarget.ownerSVGElement!.getBoundingClientRect().left;
    let melhor = 0;
    anos.forEach((a, i) => {
      if (Math.abs(x(a) - px) < Math.abs(x(anos[melhor]) - px)) {
        melhor = i;
      }
    });
    setFoco(melhor);
  };

  return (
    <figure className="flex flex-col gap-2 rounded-xl border border-border-light p-4">
      <div className="flex items-start justify-between gap-2">
        <figcaption>
          <p className="text-sm font-semibold text-text-primary">{grafico.titulo}</p>
          <p className="text-xs text-text-secondary">{grafico.nota}</p>
        </figcaption>
        <button
          type="button"
          onClick={() => setTabela((t) => !t)}
          aria-pressed={tabela}
          className="inline-flex shrink-0 items-center gap-1 rounded-md px-2 py-1 text-xs text-text-secondary hover:bg-surface-hover hover:text-text-primary"
        >
          <Table2 className="size-3.5" aria-hidden="true" />
          {tabela ? 'Gráfico' : 'Tabela'}
        </button>
      </div>

      {linhas.length > 1 && (
        <ul
          className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-secondary"
          aria-label="Legenda"
        >
          {linhas.map((l, i) => (
            <li key={l.id} className="flex items-center gap-1.5">
              <span className={cn('h-0.5 w-4 rounded-full', CORES[i].chave)} aria-hidden="true" />
              {l.nome}
            </li>
          ))}
        </ul>
      )}

      {tabela ? (
        <div className="max-h-[260px] overflow-auto">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-presentation text-text-secondary">
              <tr>
                <th className="py-1 pr-2 font-medium">Ano</th>
                <th className="py-1 pr-2 font-medium">Indicador</th>
                <th className="py-1 pr-2 text-right font-medium">Valor</th>
                <th className="py-1 font-medium">Fonte</th>
              </tr>
            </thead>
            <tbody className="text-text-primary">
              {anos.flatMap((a) =>
                linhas.map((l) => {
                  const p = l.pontos.find((p) => p.ano === a);
                  return (
                    p && (
                      <tr key={`${a}-${l.id}`} className="border-t border-border-light align-top">
                        <td className="py-1 pr-2 tabular-nums">{a}</td>
                        <td className="py-1 pr-2">{l.nome}</td>
                        <td className="whitespace-nowrap py-1 pr-2 text-right tabular-nums">
                          {formatar(p.valor, unidade)}
                        </td>
                        <td className="py-1 text-text-secondary">{p.fonte}</td>
                      </tr>
                    )
                  );
                }),
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <div
          ref={ref}
          className="relative outline-none focus-visible:ring-1 focus-visible:ring-ring-primary"
          tabIndex={0}
          role="group"
          aria-label={`${grafico.titulo}: use as setas para ler os valores de cada ano`}
          onKeyDown={(e) => {
            if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
              e.preventDefault();
              const passo = e.key === 'ArrowRight' ? 1 : -1;
              setFoco((f) =>
                Math.min(
                  anos.length - 1,
                  Math.max(0, (f ?? (passo > 0 ? -1 : anos.length)) + passo),
                ),
              );
            } else if (e.key === 'Escape') {
              setFoco(null);
            }
          }}
          onBlur={() => setFoco(null)}
        >
          {largura > 0 && (
            <svg
              width={largura}
              height={ALTURA}
              className="block overflow-visible"
              aria-hidden="true"
            >
              {ticks.map((t) => (
                <g key={t}>
                  <line
                    x1={M.esquerda}
                    x2={largura - M.direita}
                    y1={y(t)}
                    y2={y(t)}
                    className={t === 0 ? 'stroke-border-heavy' : 'stroke-border-light'}
                    strokeWidth={1}
                  />
                  <text
                    x={M.esquerda - 8}
                    y={y(t)}
                    dy="0.32em"
                    textAnchor="end"
                    className="fill-text-secondary text-[11px] tabular-nums"
                  >
                    {formatar(t, unidade, true)}
                  </text>
                </g>
              ))}
              {anos.map((a, i) =>
                i % pular === 0 || i === anos.length - 1 ? (
                  <text
                    key={a}
                    x={x(a)}
                    y={ALTURA - 8}
                    textAnchor="middle"
                    className="fill-text-secondary text-[11px] tabular-nums"
                  >
                    {a}
                  </text>
                ) : null,
              )}
              {anoFoco != null && (
                <line
                  x1={x(anoFoco)}
                  x2={x(anoFoco)}
                  y1={M.topo}
                  y2={ALTURA - M.baixo}
                  className="stroke-border-medium"
                  strokeWidth={1}
                />
              )}
              {linhas.map((l, i) => (
                <g key={l.id}>
                  <path
                    d={caminho(l.pontos)}
                    fill="none"
                    strokeWidth={2}
                    strokeLinejoin="round"
                    strokeLinecap="round"
                    className={CORES[i].linha}
                  />
                  {l.pontos.map((p) => (
                    <circle
                      key={p.ano}
                      cx={x(p.ano)}
                      cy={y(p.valor)}
                      r={p.ano === anoFoco ? 5.5 : 4}
                      strokeWidth={2}
                      className={cn(CORES[i].ponto, 'stroke-presentation')}
                    />
                  ))}
                </g>
              ))}
              {ultimo && (
                <text
                  x={x(ultimo.ano)}
                  y={y(ultimo.valor) - 10}
                  textAnchor="end"
                  className="fill-text-primary text-[11px] font-medium tabular-nums"
                >
                  {formatar(ultimo.valor, unidade)}
                </text>
              )}
              <rect
                x={M.esquerda - 12}
                y={0}
                width={Math.max(largura - M.esquerda - M.direita + 24, 0)}
                height={ALTURA}
                fill="transparent"
                onPointerMove={moverFoco}
                onPointerLeave={() => setFoco(null)}
              />
            </svg>
          )}
          {anoFoco != null && (
            <div
              role="status"
              className="pointer-events-none absolute top-0 z-10 w-64 rounded-lg border border-border-light bg-surface-primary p-2.5 text-xs shadow-lg"
              style={
                x(anoFoco) > largura / 2
                  ? { right: largura - x(anoFoco) + 12 }
                  : { left: x(anoFoco) + 12 }
              }
            >
              <p className="mb-1.5 font-semibold text-text-primary">{anoFoco}</p>
              <ul className="flex flex-col gap-1.5">
                {linhas.map((l, i) => {
                  const p = l.pontos.find((p) => p.ano === anoFoco);
                  return (
                    <li key={l.id} className="flex flex-col">
                      <span className="flex items-center gap-1.5">
                        <span className={cn('h-0.5 w-3 shrink-0 rounded-full', CORES[i].chave)} />
                        <span className="font-semibold tabular-nums text-text-primary">
                          {p ? formatar(p.valor, unidade) : 'sem dado'}
                        </span>
                        <span className="truncate text-text-secondary">{l.nome}</span>
                      </span>
                      {p && (
                        <span className="pl-[18px] text-[11px] leading-snug text-text-secondary">
                          {p.fonte}
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </div>
      )}
    </figure>
  );
}

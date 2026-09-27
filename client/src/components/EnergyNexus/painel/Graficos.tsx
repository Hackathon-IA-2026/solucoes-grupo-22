import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from 'react';
import { formatar, marcas } from './dados';

// Gráficos do painel em SVG puro. Cores das séries: --painel-1..8 (style.css, validadas nos dois temas); texto, grade e
// eixos usam os tokens do tema (--text-*, --border-*), nunca a cor da série.

export const corSerie = (i: number) => `var(--painel-${i + 1})`;
const SUPERFICIE = 'var(--surface-primary)';
const GRADE = 'var(--border-light)';
const EIXO = 'var(--border-medium)';
const TEXTO_2 = 'var(--text-secondary)';

function useLargura<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [largura, setLargura] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) {
      return;
    }
    const obs = new ResizeObserver(([e]) => setLargura(Math.floor(e.contentRect.width)));
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return [ref, largura] as const;
}

const cortar = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

// largura real do texto na fonte da página, para cortar rótulos sem que saiam da área (maiúsculas são mais largas)
let contexto: CanvasRenderingContext2D | null = null;
function medir(texto: string, tamanho: number): number {
  contexto = contexto ?? document.createElement('canvas').getContext('2d');
  if (!contexto) {
    return texto.length * tamanho * 0.62;
  }
  contexto.font = `${tamanho}px ${getComputedStyle(document.body).fontFamily}`;
  return contexto.measureText(texto).width;
}
function cortarLargura(texto: string, px: number, tamanho: number): string {
  if (medir(texto, tamanho) <= px) {
    return texto;
  }
  let n = texto.length - 1;
  while (n > 1 && medir(`${texto.slice(0, n)}…`, tamanho) > px) {
    n--;
  }
  return `${texto.slice(0, n)}…`;
}

function Dica({
  x,
  y,
  largura,
  children,
}: {
  x: number;
  y: number;
  largura: number;
  children: ReactNode;
}) {
  const aDireita = x < largura - 240;
  return (
    <div
      role="status"
      className="pointer-events-none absolute z-10 min-w-[160px] max-w-[280px] rounded-lg border border-border-light bg-surface-primary px-3 py-2 text-xs shadow-lg"
      style={{
        top: Math.max(0, y),
        ...(aDireita ? { left: x + 14 } : { right: largura - x + 14 }),
      }}
    >
      {children}
    </div>
  );
}

/** Linha da dica: chave curta da série, valor em destaque e nome em segundo plano. */
function LinhaDica({ cor, valor, nome }: { cor?: string; valor: string; nome: string }) {
  return (
    <div className="flex items-center gap-2 py-0.5">
      {cor && <span className="h-0.5 w-3 shrink-0 rounded" style={{ background: cor }} />}
      <span className="whitespace-nowrap font-semibold tabular-nums text-text-primary">
        {valor}
      </span>
      <span className="truncate text-text-secondary">{nome}</span>
    </div>
  );
}

/** Cartão de um gráfico com a alternativa em tabela (o mesmo dado, sem depender de cor nem de passar o mouse). */
export function Cartao({
  titulo,
  subtitulo,
  tabela,
  children,
}: {
  titulo: string;
  subtitulo?: string;
  tabela: ReactNode;
  children: ReactNode;
}) {
  const [emTabela, setEmTabela] = useState(false);
  return (
    <figure className="flex min-w-0 flex-col gap-3 rounded-xl border border-border-light bg-surface-primary p-4">
      <figcaption className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-sm font-semibold text-text-primary">{titulo}</div>
          {subtitulo && <div className="text-xs text-text-secondary">{subtitulo}</div>}
        </div>
        <button
          type="button"
          className="shrink-0 rounded-lg border border-border-light px-2 py-1 text-xs text-text-secondary hover:bg-surface-hover"
          onClick={() => setEmTabela((v) => !v)}
          aria-pressed={emTabela}
        >
          {emTabela ? 'Ver gráfico' : 'Ver tabela'}
        </button>
      </figcaption>
      {emTabela ? <div className="max-h-[360px] overflow-auto">{tabela}</div> : children}
    </figure>
  );
}

export type Serie = { chave: string; rotulo: string; cor: number; valores: (number | null)[] };

export function Legenda({ series }: { series: Serie[] }) {
  if (series.length < 2) {
    return null;
  }
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-secondary">
      {series.map((s) => (
        <li key={s.chave} className="flex items-center gap-1.5">
          <span className="h-0.5 w-3 rounded" style={{ background: corSerie(s.cor) }} />
          <span title={s.rotulo}>{cortar(s.rotulo, 40)}</span>
        </li>
      ))}
    </ul>
  );
}

const ALTURA = 260;

/** Evolução no tempo: uma linha por série, crosshair que acha o período mais próximo e dica com todas as séries. */
export function GraficoLinha({
  periodos,
  series,
  unidade,
}: {
  periodos: string[];
  series: Serie[];
  unidade: string;
}) {
  const [ref, largura] = useLargura<HTMLDivElement>();
  const [foco, setFoco] = useState<{ i: number; y: number } | null>(null);

  const todos = series.flatMap((s) => s.valores).filter((v): v is number => v != null);
  if (todos.length === 0) {
    return (
      <div ref={ref} className="py-10 text-center text-sm text-text-secondary">
        sem dados neste recorte
      </div>
    );
  }
  // com uma série só a linha ganha área, e área só é honesta se o eixo parte do zero
  const areaUnica = series.length === 1 && todos.every((v) => v >= 0);
  const ticks = marcas(areaUnica ? 0 : Math.min(...todos), Math.max(...todos));
  const yMin = ticks[0];
  const yMax = ticks[ticks.length - 1];
  const esquerda = Math.max(...ticks.map((t) => medir(formatar(t, unidade), 11))) + 12;

  // rótulos no fim das linhas só com até 4 séries e sem colisão; senão legenda + dica
  const finais = series
    .map((s) => {
      let i = s.valores.length - 1;
      while (i >= 0 && s.valores[i] == null) {
        i--;
      }
      return { s, i, v: i >= 0 ? (s.valores[i] as number) : null };
    })
    .filter((f) => f.v != null);
  const altura = ALTURA - 12 - 28;
  const y = (v: number) => 12 + altura - ((v - yMin) / (yMax - yMin || 1)) * altura;
  const posicoes = finais.map((f) => y(f.v as number)).sort((a, b) => a - b);
  const rotular =
    series.length <= 4 && posicoes.every((p, k) => k === 0 || p - posicoes[k - 1] >= 14);
  const direita = rotular
    ? Math.max(...finais.map((f) => medir(cortarLargura(f.s.rotulo, 134, 11), 11))) + 16
    : 12;

  const w = Math.max(largura, 320);
  const plotL = esquerda;
  const plotR = w - direita;
  const passo = periodos.length > 1 ? (plotR - plotL) / (periodos.length - 1) : 0;
  const x = (i: number) => (periodos.length > 1 ? plotL + i * passo : (plotL + plotR) / 2);

  const caminho = (valores: (number | null)[]) => {
    let d = '';
    let aberto = false;
    valores.forEach((v, i) => {
      if (v == null) {
        aberto = false;
        return;
      }
      d += `${aberto ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
      aberto = true;
    });
    return d;
  };
  const isolados = (valores: (number | null)[]) =>
    valores
      .map((v, i) => ({ v, i }))
      .filter(({ v, i }) => v != null && valores[i - 1] == null && valores[i + 1] == null);

  // quantos rótulos do tempo cabem sem encostar: todos, quando couberem
  const larguraRotuloX = Math.max(...periodos.map((p) => medir(p, 11))) + 24;
  const nRotulosX = Math.max(
    2,
    Math.min(periodos.length, Math.floor((plotR - plotL) / larguraRotuloX) + 1),
  );
  const indicesX = [
    ...new Set(
      Array.from({ length: nRotulosX }, (_, k) =>
        Math.round((k * (periodos.length - 1)) / Math.max(1, nRotulosX - 1)),
      ),
    ),
  ];
  const base = y(Math.max(yMin, 0));

  const mover = (clienteX: number, clienteY: number, alvo: SVGRectElement) => {
    const r = alvo.getBoundingClientRect();
    const i = Math.round((clienteX - r.left) / (passo || 1));
    setFoco({ i: Math.max(0, Math.min(periodos.length - 1, i)), y: clienteY - r.top });
  };
  const teclado = (e: KeyboardEvent) => {
    const atual = foco?.i ?? periodos.length - 1;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      e.preventDefault();
      const i = Math.max(
        0,
        Math.min(periodos.length - 1, atual + (e.key === 'ArrowLeft' ? -1 : 1)),
      );
      setFoco({ i, y: 20 });
    } else if (e.key === 'Escape') {
      setFoco(null);
    }
  };

  return (
    <div
      ref={ref}
      className="relative outline-none focus-visible:ring-2 focus-visible:ring-border-heavy"
      tabIndex={0}
      aria-label="Gráfico de linhas; use as setas para percorrer os períodos"
      onKeyDown={teclado}
      onFocus={() => setFoco((f) => f ?? { i: periodos.length - 1, y: 20 })}
      onBlur={() => setFoco(null)}
    >
      <svg width={w} height={ALTURA} className="block overflow-visible">
        {ticks.map((t) => (
          <g key={t}>
            <line
              x1={plotL}
              x2={plotR}
              y1={y(t)}
              y2={y(t)}
              stroke={t === 0 ? EIXO : GRADE}
              strokeWidth={1}
            />
            <text
              x={plotL - 8}
              y={y(t)}
              dy="0.32em"
              textAnchor="end"
              fontSize={11}
              fill={TEXTO_2}
              className="tabular-nums"
            >
              {formatar(t, unidade)}
            </text>
          </g>
        ))}
        {indicesX.map((i) => (
          <text key={i} x={x(i)} y={ALTURA - 8} textAnchor="middle" fontSize={11} fill={TEXTO_2}>
            {periodos[i]}
          </text>
        ))}
        {areaUnica && (
          <path
            d={`${caminho(series[0].valores)}L${x(series[0].valores.length - 1)},${base}L${x(
              series[0].valores.findIndex((v) => v != null),
            )},${base}Z`}
            fill={corSerie(series[0].cor)}
            fillOpacity={0.1}
          />
        )}
        {series.map((s) => (
          <g key={s.chave}>
            <path
              d={caminho(s.valores)}
              fill="none"
              stroke={corSerie(s.cor)}
              strokeWidth={2}
              strokeLinejoin="round"
              strokeLinecap="round"
            />
            {isolados(s.valores).map(({ v, i }) => (
              <circle
                key={i}
                cx={x(i)}
                cy={y(v as number)}
                r={4}
                fill={corSerie(s.cor)}
                stroke={SUPERFICIE}
                strokeWidth={2}
              />
            ))}
          </g>
        ))}
        {finais.map((f) => (
          <circle
            key={f.s.chave}
            cx={x(f.i)}
            cy={y(f.v as number)}
            r={4}
            fill={corSerie(f.s.cor)}
            stroke={SUPERFICIE}
            strokeWidth={2}
          />
        ))}
        {rotular &&
          finais.map((f) => (
            <text
              key={f.s.chave}
              x={plotR + 8}
              y={y(f.v as number)}
              dy="0.32em"
              fontSize={11}
              fill={TEXTO_2}
            >
              {cortarLargura(f.s.rotulo, 134, 11)}
            </text>
          ))}
        {foco && (
          <g pointerEvents="none">
            <line
              x1={x(foco.i)}
              x2={x(foco.i)}
              y1={12}
              y2={12 + altura}
              stroke={EIXO}
              strokeWidth={1}
            />
            {series.map((s) =>
              s.valores[foco.i] == null ? null : (
                <circle
                  key={s.chave}
                  cx={x(foco.i)}
                  cy={y(s.valores[foco.i] as number)}
                  r={4}
                  fill={corSerie(s.cor)}
                  stroke={SUPERFICIE}
                  strokeWidth={2}
                />
              ),
            )}
          </g>
        )}
        <rect
          x={plotL - passo / 2}
          y={0}
          width={plotR - plotL + passo}
          height={ALTURA}
          fill="transparent"
          onPointerMove={(e) => mover(e.clientX, e.clientY, e.currentTarget)}
          onPointerLeave={() => setFoco(null)}
        />
      </svg>
      {foco && (
        <Dica x={x(foco.i)} y={Math.min(foco.y, ALTURA - 120)} largura={w}>
          <div className="mb-1 text-text-secondary">{periodos[foco.i]}</div>
          {series
            .map((s) => ({ s, v: s.valores[foco.i] }))
            .sort((a, b) => (b.v ?? -Infinity) - (a.v ?? -Infinity))
            .map(({ s, v }) => (
              <LinhaDica
                key={s.chave}
                cor={corSerie(s.cor)}
                valor={formatar(v, unidade)}
                nome={s.rotulo}
              />
            ))}
        </Dica>
      )}
    </div>
  );
}

/** Ranking horizontal: uma cor só (é uma série), valor na ponta da barra, dica por barra com mouse e teclado. */
export function GraficoBarras({
  itens,
  unidade,
}: {
  itens: { chave: string; valor: number }[];
  unidade: string;
}) {
  const [ref, largura] = useLargura<HTMLDivElement>();
  const [foco, setFoco] = useState<number | null>(null);
  if (itens.length === 0) {
    return (
      <div ref={ref} className="py-10 text-center text-sm text-text-secondary">
        sem dados neste recorte
      </div>
    );
  }
  const w = Math.max(largura, 320);
  const LINHA = 28;
  const BARRA = 16;
  const rotuloW = Math.min(240, Math.round(w * 0.38));
  const valorW = Math.max(...itens.map((i) => medir(formatar(i.valor, unidade), 11))) + 12;
  const min = Math.min(0, ...itens.map((i) => i.valor));
  const max = Math.max(0, ...itens.map((i) => i.valor));
  const temNegativo = min < 0;
  const plotL = rotuloW + 12 + (temNegativo ? valorW : 0);
  const plotR = w - valorW;
  const x = (v: number) => plotL + ((v - min) / (max - min || 1)) * (plotR - plotL);
  const zero = x(0);
  const h = itens.length * LINHA + 4;

  // retângulo com a ponta de dados arredondada (4px) e o lado da base reto
  const barra = (v: number, topo: number) => {
    const a = Math.min(x(v), zero);
    const b = Math.max(x(v), zero);
    const r = Math.min(4, (b - a) / 2);
    const fundo = topo + BARRA;
    return v >= 0
      ? `M${a},${topo}H${b - r}Q${b},${topo} ${b},${topo + r}V${fundo - r}Q${b},${fundo} ${b - r},${fundo}H${a}Z`
      : `M${b},${topo}H${a + r}Q${a},${topo} ${a},${topo + r}V${fundo - r}Q${a},${fundo} ${a + r},${fundo}H${b}Z`;
  };

  return (
    <div ref={ref} className="relative">
      <svg width={w} height={h} className="block">
        {itens.map((item, k) => {
          const topo = k * LINHA + (LINHA - BARRA) / 2;
          const ativo = foco === null || foco === k;
          return (
            <g
              key={item.chave}
              tabIndex={0}
              role="img"
              aria-label={`${item.chave}: ${formatar(item.valor, unidade)}`}
              className="outline-none"
              onPointerEnter={() => setFoco(k)}
              onPointerLeave={() => setFoco(null)}
              onFocus={() => setFoco(k)}
              onBlur={() => setFoco(null)}
            >
              <rect x={0} y={k * LINHA} width={w} height={LINHA} fill="transparent" />
              <text
                x={rotuloW}
                y={topo + BARRA / 2}
                dy="0.32em"
                textAnchor="end"
                fontSize={12}
                fill="var(--text-primary)"
              >
                <title>{item.chave}</title>
                {cortarLargura(item.chave, rotuloW - 4, 12)}
              </text>
              <path d={barra(item.valor, topo)} fill={corSerie(0)} opacity={ativo ? 1 : 0.45} />
              <text
                x={item.valor >= 0 ? x(item.valor) + 6 : x(item.valor) - 6}
                y={topo + BARRA / 2}
                dy="0.32em"
                textAnchor={item.valor >= 0 ? 'start' : 'end'}
                fontSize={11}
                fill={TEXTO_2}
                className="tabular-nums"
              >
                {formatar(item.valor, unidade)}
              </text>
            </g>
          );
        })}
        <line x1={zero} x2={zero} y1={0} y2={h} stroke={EIXO} strokeWidth={1} />
      </svg>
      {foco !== null && (
        <Dica x={Math.max(x(itens[foco].valor), zero)} y={foco * LINHA - 8} largura={w}>
          <LinhaDica valor={formatar(itens[foco].valor, unidade)} nome={itens[foco].chave} />
        </Dica>
      )}
    </div>
  );
}

/** Minigráfico do cartão de indicador: tendência no período escolhido, ponto final destacado. */
export function Mini({ valores }: { valores: (number | null)[] }) {
  const pontos = valores
    .map((v, i) => ({ v, i }))
    .filter((p): p is { v: number; i: number } => p.v != null);
  if (pontos.length < 2) {
    return <div className="h-9" />;
  }
  const W = 160;
  const H = 36;
  const vs = pontos.map((p) => p.v);
  const min = Math.min(...vs);
  const max = Math.max(...vs);
  const x = (i: number) => 4 + (i / Math.max(1, valores.length - 1)) * (W - 8);
  const y = (v: number) => 4 + (1 - (v - min) / (max - min || 1)) * (H - 8);
  const d = pontos
    .map((p, k) => `${k ? 'L' : 'M'}${x(p.i).toFixed(1)},${y(p.v).toFixed(1)}`)
    .join('');
  const ultimo = pontos[pontos.length - 1];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="block h-9 w-full max-w-[160px]" aria-hidden="true">
      <path d={d} fill="none" stroke={corSerie(0)} strokeWidth={2} strokeLinejoin="round" />
      <circle
        cx={x(ultimo.i)}
        cy={y(ultimo.v)}
        r={4}
        fill={corSerie(0)}
        stroke={SUPERFICIE}
        strokeWidth={2}
      />
    </svg>
  );
}

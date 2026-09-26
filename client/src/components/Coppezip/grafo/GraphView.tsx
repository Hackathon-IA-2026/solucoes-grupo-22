import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent as ReactKeyboardEvent,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from 'react';
import {
  Activity,
  Banknote,
  Boxes,
  Building2,
  LineChart,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Coins,
  Database,
  Factory,
  FileText,
  FoldVertical,
  FolderOpen,
  Hammer,
  Hand,
  HandCoins,
  Layers,
  Leaf,
  LocateFixed,
  Maximize2,
  Minimize2,
  Minus,
  MousePointerClick,
  Percent,
  PiggyBank,
  Plus,
  Scale,
  Scan,
  Search,
  SquareArrowOutUpRight,
  TrendingDown,
  TrendingUp,
  UnfoldVertical,
  Users,
  Wallet,
  Waypoints,
  Wind,
  X,
  Zap,
  ZoomIn,
  ZoomOut,
  type LucideIcon,
} from 'lucide-react';
import { abrirArquivo, mensagemDeErro } from '../api';
import { formatar } from '../painel/dados';
import { semAcento, type Fonte, type Grafo, type Icone, type No, type Ponto } from './dados';
import {
  AUTO_COLLAPSE_ABOVE,
  ancestorsOf,
  buildModel,
  computeLayout,
  connectorsOf,
  frameItems,
  lerp,
  metaOf,
  relationPath,
  stackCounts,
  subtreeOf,
  tween,
  tweenBoxes,
  type Caixa,
  type Caixas,
  type Modelo,
} from './modelo';
import './grafo.css';

// Visualização do grafo de conhecimento de uma empresa (porte do KnowledgeGraph.jsx do CoppeZIP). O estilo está em
// grafo.css, com todas as classes prefixadas por kg- e as cores tiradas do tema do LibreChat (claro e escuro).

const ICONES: Record<Icone, LucideIcon> = {
  'building-2': Building2,
  'chart-line': LineChart,
  zap: Zap,
  wind: Wind,
  factory: Factory,
  'hand-coins': HandCoins,
  'trending-up': TrendingUp,
  layers: Layers,
  leaf: Leaf,
  'folder-open': FolderOpen,
  'file-text': FileText,
  database: Database,
  banknote: Banknote,
  coins: Coins,
  percent: Percent,
  scale: Scale,
  wallet: Wallet,
  'piggy-bank': PiggyBank,
  boxes: Boxes,
  hammer: Hammer,
  'trending-down': TrendingDown,
  users: Users,
  activity: Activity,
};

const MIN_K = 0.2;
const MIN_K_INICIAL = 0.5; // abaixo disso os cartões ficam ilegíveis: a primeira vista mostra o topo do grafo
const MAX_K = 2.2;
const PANEL_W = 340;
const ANIM_MS = 320;
const MAX_CHIPS = 40;
const EDGE_LABELS = { fonte: ['Sustentado por', 'Sustenta'], contem: ['Contém', 'Parte de'] };

type Vista = { x: number; y: number; k: number };

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));
const cx = (...names: (string | false | null | undefined)[]) => names.filter(Boolean).join(' ');

function reducedMotion() {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch {
    return false;
  }
}

const celula = (v: unknown) => {
  if (v == null) {
    return '—';
  }
  return typeof v === 'number' ? v.toLocaleString('pt-BR') : String(v);
};

// ---------------------------------------------------------------- nós

function IconTile({ name, variant }: { name: Icone; variant?: 'dark' }) {
  const Component = ICONES[name];
  return (
    <span className={cx('kg-tile', variant && `kg-tile--${variant}`)}>
      <Component size={variant === 'dark' ? 17 : 21} strokeWidth={1.9} aria-hidden="true" />
    </span>
  );
}

function Sparkline({
  serie,
  width = 64,
  height = 24,
  stretch = false,
}: {
  serie: Ponto[];
  width?: number;
  height?: number;
  stretch?: boolean;
}) {
  const values = serie.map((p) => p.valor);
  const min = Math.min(...values);
  const span = Math.max(...values) - min || 1;
  const pts = values.map((v, i) => [
    2 + (i / (values.length - 1)) * (width - 4),
    height - 3 - ((v - min) / span) * (height - 6),
  ]);
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
  const last = pts[pts.length - 1];
  return (
    <svg
      className={cx('kg-spark', stretch && 'kg-spark--big')}
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio={stretch ? 'none' : undefined}
      aria-hidden="true"
    >
      <path
        d={`${d} L${last[0].toFixed(1)},${height} L${pts[0][0].toFixed(1)},${height} Z`}
        className="kg-spark-area"
      />
      <path d={d} className="kg-spark-line" vectorEffect="non-scaling-stroke" />
      {!stretch && <circle cx={last[0]} cy={last[1]} r="2.4" />}
    </svg>
  );
}

function NodeCard({ node }: { node: No }) {
  const meta = metaOf(node.tipo);
  if (node.tipo === 'indicador' && node.serie) {
    const last = node.serie[node.serie.length - 1];
    return (
      <div className="kg-card kg-card--dark">
        <IconTile name={node.icone} variant="dark" />
        <div className="kg-body">
          <span className="kg-title kg-title--sm">{node.rotulo}</span>
          <span className="kg-sub">
            <span className="kg-value">{formatar(last.valor, node.unidade ?? '')}</span>
            {last.periodo ? ` · ${last.periodo}` : ''}
          </span>
        </div>
        {node.serie.length > 1 && <Sparkline serie={node.serie} />}
      </div>
    );
  }
  if (node.tipo === 'referencia') {
    const Component = ICONES[node.icone];
    return (
      <div className="kg-card kg-card--ref">
        {node.fonte && <span className="kg-chip">{node.fonte}</span>}
        <div className="kg-body">
          <span className="kg-title kg-title--xs">{node.rotulo}</span>
          {node.descricao && <span className="kg-sub">{node.descricao}</span>}
        </div>
        <Component size={15} strokeWidth={1.9} className="kg-ref-icon" aria-hidden="true" />
      </div>
    );
  }
  const clara = node.tipo === 'empresa' || node.tipo === 'categoria';
  return (
    <div
      className={cx(
        'kg-card',
        clara ? 'kg-card--light' : 'kg-card--dark',
        node.tipo === 'empresa' && 'kg-card--company',
      )}
    >
      <IconTile name={node.icone} variant={clara ? undefined : 'dark'} />
      <div className="kg-body">
        <span className="kg-eyebrow">{meta.label}</span>
        <span className={cx('kg-title', !clara && 'kg-title--sm')}>{node.rotulo}</span>
        {node.descricao && <span className="kg-sub">{node.descricao}</span>}
      </div>
    </div>
  );
}

type Flags = { selected: boolean; dim: boolean; match: boolean };

function GraphNode({
  node,
  box,
  model,
  collapsed,
  flags,
  onSelect,
  onToggle,
  onHover,
}: {
  node: No;
  box: Caixa;
  model: Modelo;
  collapsed: boolean;
  flags: Flags;
  onSelect: (id: string) => void;
  onToggle: (id: string) => void;
  onHover: (id: string | null) => void;
}) {
  const hasChildren = (model.children.get(node.id) ?? []).length > 0;
  const total = model.descendants.get(node.id) ?? 0;
  return (
    <div
      className={cx(
        'kg-node',
        `kg-node--${node.tipo}`,
        box.frame && 'is-framed',
        hasChildren && 'has-kids',
        flags.selected && 'is-selected',
        flags.dim && 'is-dim',
        flags.match && 'is-match',
      )}
      style={{
        transform: `translate(${box.x}px, ${box.y}px)`,
        width: box.w,
        height: box.h,
        opacity: box.a ?? 1,
        pointerEvents: box.exiting ? 'none' : undefined,
      }}
      role="button"
      tabIndex={0}
      aria-pressed={flags.selected}
      aria-label={`${metaOf(node.tipo).label}: ${node.rotulo}`}
      title={[node.rotulo, node.descricao].filter(Boolean).join('\n')}
      onClick={(e) => {
        e.stopPropagation();
        onSelect(node.id);
      }}
      onDoubleClick={(e) => {
        e.stopPropagation();
        if (hasChildren) {
          onToggle(node.id);
        }
      }}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          e.stopPropagation();
          onSelect(node.id);
        }
      }}
      onPointerEnter={() => onHover(node.id)}
      onPointerLeave={() => onHover(null)}
    >
      <NodeCard node={node} />
      {hasChildren && (
        <button
          type="button"
          className="kg-toggle"
          aria-expanded={!collapsed}
          aria-label={collapsed ? `Expandir ${node.rotulo}` : `Recolher ${node.rotulo}`}
          title={collapsed ? `Expandir (${total} itens)` : 'Recolher'}
          onClick={(e) => {
            e.stopPropagation();
            onToggle(node.id);
          }}
          onDoubleClick={(e) => e.stopPropagation()}
        >
          {collapsed ? (
            <Plus size={12} aria-hidden="true" />
          ) : (
            <Minus size={12} aria-hidden="true" />
          )}
          {collapsed ? <span>{total}</span> : null}
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------- painel de detalhes

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="kg-section">
      <div className="kg-section-title">{title}</div>
      {children}
    </section>
  );
}

function MetaTable({ entries }: { entries: [string, ReactNode][] }) {
  return (
    <dl className="kg-kv">
      {entries.map(([k, v]) => (
        <div key={k} className="kg-kv-row">
          <dt>{k}</dt>
          <dd>{v}</dd>
        </div>
      ))}
    </dl>
  );
}

function DataTable({
  columns,
  rows,
  max = 8,
}: {
  columns: string[];
  rows: unknown[][];
  max?: number;
}) {
  return (
    <div className="kg-table-wrap">
      <table className="kg-table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c}>{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, max).map((r, i) => (
            <tr key={i}>
              {columns.map((c, j) => (
                <td key={c}>{celula(r[j])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > max && (
        <div className="kg-table-more">+{rows.length - max} linhas na base</div>
      )}
    </div>
  );
}

function SourceCard({
  fonte,
  isFocus,
  defaultOpen,
  onShowInGraph,
  onError,
}: {
  fonte: Fonte | undefined;
  isFocus: boolean;
  defaultOpen: boolean;
  onShowInGraph: (() => void) | null;
  onError: (texto: string) => void;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [longQuote, setLongQuote] = useState(false);
  if (!fonte) {
    return null;
  }
  const banco = fonte.tipo === 'banco';
  const Kind = banco ? Database : FileText;
  const details: [string, ReactNode][] = banco
    ? [['Origem', fonte.origem]]
    : [
        ['Tipo', fonte.tipoDocumento],
        ['Ano', String(fonte.ano)],
        ['Páginas', String(fonte.paginas)],
        ['Arquivo', fonte.arquivo],
      ];
  return (
    <article className={cx('kg-source', isFocus && 'is-focus')}>
      <button
        type="button"
        className="kg-source-head"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
      >
        <span className="kg-chip">{fonte.id}</span>
        <Kind size={14} className="kg-source-kind-icon" aria-hidden="true" />
        <span className="kg-source-kind">{banco ? 'Base do painel' : 'Documento'}</span>
        {open ? (
          <ChevronUp size={14} className="kg-source-caret" aria-hidden="true" />
        ) : (
          <ChevronDown size={14} className="kg-source-caret" aria-hidden="true" />
        )}
      </button>
      <div className="kg-source-title">{fonte.titulo}</div>
      {open && (
        <>
          <MetaTable entries={details} />
          {banco && fonte.descricao && <div className="kg-source-sub">{fonte.descricao}</div>}
          {banco && fonte.ressalvas && (
            <blockquote
              className={cx('kg-quote', !longQuote && 'is-clamped')}
              onClick={() => setLongQuote(true)}
            >
              {fonte.ressalvas}
            </blockquote>
          )}
          {banco && fonte.linhas.length > 0 && (
            <DataTable columns={fonte.colunas} rows={fonte.linhas} />
          )}
        </>
      )}
      <div className="kg-actions">
        {!banco && (
          <button
            type="button"
            className="kg-action"
            onClick={() =>
              abrirArquivo('/api/busca/pdf', { arquivo: fonte.arquivo }).catch((e) =>
                onError(mensagemDeErro(e)),
              )
            }
          >
            <FileText size={13} aria-hidden="true" /> Abrir PDF
          </button>
        )}
        {fonte.link && (
          <a
            className={cx('kg-action', !banco && 'kg-action--ghost')}
            href={fonte.link}
            target="_blank"
            rel="noopener noreferrer"
            title={fonte.link}
          >
            <SquareArrowOutUpRight size={13} aria-hidden="true" />{' '}
            {banco ? 'Conjunto de dados' : 'Documento original'}
          </a>
        )}
        {onShowInGraph && (
          <button type="button" className="kg-action kg-action--ghost" onClick={onShowInGraph}>
            <LocateFixed size={13} aria-hidden="true" /> Mostrar no grafo
          </button>
        )}
      </div>
    </article>
  );
}

function SeriesBlock({ node, serie }: { node: No; serie: Ponto[] }) {
  const last = serie[serie.length - 1];
  const unidade = node.unidade ?? '';
  return (
    <div className="kg-series">
      <div className="kg-bigvalue">
        <b>{formatar(last.valor, unidade)}</b>
        {last.periodo && <span className="kg-bigvalue-year">{last.periodo}</span>}
      </div>
      {serie.length > 1 && (
        <>
          <Sparkline serie={serie} width={300} height={70} stretch />
          <div className="kg-series-axis">
            <span>{serie[0].periodo}</span>
            <span>{last.periodo}</span>
          </div>
          <DataTable
            columns={['Período', 'Valor']}
            rows={[...serie].reverse().map((p) => [p.periodo, formatar(p.valor, unidade)])}
            max={16}
          />
        </>
      )}
    </div>
  );
}

function DetailsPanel({
  node,
  model,
  compact,
  onClose,
  onSelect,
  onReveal,
  onError,
}: {
  node: No;
  model: Modelo;
  compact: boolean;
  onClose: () => void;
  onSelect: (id: string) => void;
  onReveal: (id: string) => void;
  onError: (texto: string) => void;
}) {
  const meta = metaOf(node.tipo);
  const path = ancestorsOf(model, node.id)
    .reverse()
    .map((id) => model.byId.get(id) as No);
  const kids = (model.children.get(node.id) ?? []).map((id) => model.byId.get(id) as No);
  const relations = model.relations.filter((e) => e.origem === node.id || e.destino === node.id);
  const clara = node.tipo === 'empresa' || node.tipo === 'categoria';
  return (
    <aside
      className={cx('kg-panel', compact && 'is-compact')}
      onPointerDown={(e) => e.stopPropagation()}
      onClick={(e) => e.stopPropagation()}
      onDoubleClick={(e) => e.stopPropagation()}
      aria-label={`Detalhes: ${node.rotulo}`}
    >
      <header className="kg-panel-head">
        <IconTile name={node.icone} variant={clara ? undefined : 'dark'} />
        <div className="kg-panel-titles">
          <div className="kg-eyebrow">{meta.label}</div>
          <h3 className="kg-panel-title">{node.rotulo}</h3>
          {node.descricao && <div className="kg-panel-desc">{node.descricao}</div>}
        </div>
        <button
          type="button"
          className="kg-btn kg-btn--plain"
          onClick={onClose}
          title="Fechar detalhes (Esc)"
          aria-label="Fechar detalhes"
        >
          <X size={16} aria-hidden="true" />
        </button>
      </header>
      <div className="kg-panel-body">
        {path.length > 0 && (
          <nav className="kg-crumbs" aria-label="Caminho no grafo">
            {path.map((a, i) => (
              <span key={a.id} className="kg-crumb-wrap">
                {i > 0 && <ChevronRight size={12} className="kg-crumb-sep" aria-hidden="true" />}
                <button type="button" className="kg-crumb" onClick={() => onSelect(a.id)}>
                  {a.rotulo}
                </button>
              </span>
            ))}
          </nav>
        )}
        {node.serie && node.serie.length > 0 && <SeriesBlock node={node} serie={node.serie} />}
        {node.detalhes.length > 0 && (
          <Section title="Detalhes">
            <MetaTable entries={node.detalhes} />
          </Section>
        )}
        {kids.length > 0 && (
          <Section title={`Contém (${kids.length})`}>
            <div className="kg-chip-list">
              {kids.slice(0, MAX_CHIPS).map((k) => {
                const Component = ICONES[k.icone];
                return (
                  <button
                    key={k.id}
                    type="button"
                    className="kg-link-chip"
                    onClick={() => onReveal(k.id)}
                  >
                    <Component size={13} aria-hidden="true" />
                    <span>{k.rotulo}</span>
                  </button>
                );
              })}
              {kids.length > MAX_CHIPS && (
                <span className="kg-more">+{kids.length - MAX_CHIPS}</span>
              )}
            </div>
          </Section>
        )}
        {relations.length > 0 && (
          <Section title="Relações">
            <div className="kg-rel-list">
              {relations.map((e) => {
                const out = e.origem === node.id;
                const other = model.byId.get(out ? e.destino : e.origem) as No;
                const Component = ICONES[other.icone];
                return (
                  <button
                    key={e.id}
                    type="button"
                    className="kg-rel-row"
                    onClick={() => onReveal(other.id)}
                  >
                    <span className="kg-rel-type">{EDGE_LABELS[e.tipo][out ? 0 : 1]}</span>
                    <Component size={13} aria-hidden="true" />
                    <span className="kg-rel-name">{other.rotulo}</span>
                  </button>
                );
              })}
            </div>
          </Section>
        )}
        {node.referencias.length > 0 && (
          <Section
            title={node.referencias.length === 1 ? 'Fonte' : `Fontes (${node.referencias.length})`}
          >
            {node.referencias.map((fid) => {
              const ref = model.nodeByFonte.get(fid);
              return (
                <SourceCard
                  key={fid}
                  fonte={model.fontes.get(fid)}
                  isFocus={node.fonte === fid}
                  defaultOpen={node.referencias.length <= 2}
                  onShowInGraph={ref && ref !== node.id ? () => onReveal(ref) : null}
                  onError={onError}
                />
              );
            })}
          </Section>
        )}
      </div>
    </aside>
  );
}

// ---------------------------------------------------------------- componente principal

/** Grafo navegável: arrastar move, roda do mouse (ou pinça) dá zoom, clique abre os detalhes do nó. */
export default function GraphView({ data }: { data: Grafo }) {
  const model = useMemo(() => buildModel(data), [data]);
  const uid = useMemo(() => `kg${Math.random().toString(36).slice(2, 8)}`, []);

  const [collapsed, setCollapsed] = useState<Set<string>>(() => {
    if (model.byId.size <= AUTO_COLLAPSE_ABOVE) {
      return new Set();
    }
    return new Set(
      [...model.byId.keys()].filter(
        (id) => (model.depth.get(id) ?? 0) >= 1 && (model.children.get(id) ?? []).length,
      ),
    );
  });
  const [selected, setSelected] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const [view, setView] = useState<Vista | null>(null);
  const [isFull, setIsFull] = useState(false);
  const [query, setQuery] = useState('');
  const [matchIndex, setMatchIndex] = useState(0);
  const [toast, setToast] = useState<{ id: number; text: string } | null>(null);
  const [hinted, setHinted] = useState(false);
  const [vp, setVp] = useState({ w: 0, h: 0 });
  const [dragging, setDragging] = useState(false);
  const [focusTick, setFocusTick] = useState(0);

  const rootRef = useRef<HTMLDivElement>(null);
  const vpRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef(view);
  viewRef.current = view;
  const stopViewAnim = useRef<(() => void) | null>(null);
  const gesture = useRef<{
    pointers: Map<number, { x: number; y: number }>;
    start: { id: number; x: number; y: number; vx: number; vy: number } | null;
    moved: boolean;
    pinch: { d: number; k: number; vx: number; vy: number; mx: number; my: number } | null;
  }>({ pointers: new Map(), start: null, moved: false, pinch: null });
  const anchorRef = useRef<{ id: string; sx: number; sy: number } | null>(null);
  const pendingFocus = useRef<string | null>(null);
  const pendingFit = useRef(false);
  const refitOnResize = useRef(false);
  const lastVp = useRef<{ w: number; h: number } | null>(null);
  const userMoved = useRef(false);

  // Layout alvo e caixas exibidas (animadas entre um layout e outro)
  const layout = useMemo(() => computeLayout(model, collapsed), [model, collapsed]);
  const [display, setDisplay] = useState<Caixas>(() => layout.boxes);
  const displayRef = useRef(display);
  displayRef.current = display;
  useEffect(
    () =>
      tweenBoxes(
        displayRef.current,
        layout.boxes,
        model,
        setDisplay,
        reducedMotion() ? 0 : ANIM_MS,
      ),
    [layout, model],
  );

  useLayoutEffect(() => {
    const el = vpRef.current;
    if (!el || typeof ResizeObserver === 'undefined') {
      return undefined;
    }
    const observer = new ResizeObserver(([entry]) => {
      const r = entry.contentRect;
      setVp((prev) =>
        prev.w === r.width && prev.h === r.height ? prev : { w: r.width, h: r.height },
      );
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const compact = vp.w > 0 && vp.w < 720;
  const panelNode = selected ? (model.byId.get(selected) ?? null) : null;
  const usableW = Math.max(120, vp.w - (panelNode && !compact ? PANEL_W + 24 : 0));
  const usableH = Math.max(120, vp.h - (panelNode && compact ? vp.h * 0.58 : 0));

  const moveView = useCallback((target: Vista, animate?: boolean) => {
    stopViewAnim.current?.();
    stopViewAnim.current = null;
    const from = viewRef.current;
    if (!animate || !from || reducedMotion()) {
      setView(target);
      return;
    }
    stopViewAnim.current = tween(ANIM_MS, (e) =>
      setView({
        x: lerp(from.x, target.x, e),
        y: lerp(from.y, target.y, e),
        k: lerp(from.k, target.k, e),
      }),
    );
  }, []);

  const fit = useCallback(
    (animate?: boolean, minimo = MIN_K) => {
      const b = layout.bounds;
      if (!b || !vp.w || !vp.h) {
        return;
      }
      const margin = 36;
      const k = clamp(
        Math.min((usableW - 2 * margin) / (b.w + 48), (usableH - 2 * margin) / b.h),
        minimo,
        1,
      );
      // grafo mais largo que a tela nesse zoom: centraliza na raiz (a empresa) em vez de no conjunto
      const raiz = layout.boxes.get(model.roots[0]);
      const x =
        b.w * k + 2 * margin > usableW && raiz
          ? usableW / 2 - (raiz.x + raiz.w / 2) * k
          : (usableW - b.w * k) / 2 - b.minX * k;
      const y =
        b.h * k + 2 * margin <= usableH
          ? (usableH - b.h * k) / 2 - b.minY * k
          : margin - b.minY * k;
      userMoved.current = false;
      moveView({ x, y, k }, animate);
    },
    [layout, model, vp.w, vp.h, usableW, usableH, moveView],
  );

  const centerOn = useCallback(
    (id: string) => {
      const b = layout.boxes.get(id);
      const v = viewRef.current;
      if (!b || !v) {
        return;
      }
      const k = Math.max(v.k, 0.75);
      userMoved.current = true;
      moveView(
        { k, x: usableW / 2 - (b.x + b.w / 2) * k, y: usableH / 2 - (b.y + b.h / 2) * k },
        true,
      );
    },
    [layout, usableW, usableH, moveView],
  );

  // Enquadra na primeira exibição e ao redimensionar (se o usuário não navegou, ou ao entrar/sair da tela cheia)
  useEffect(() => {
    if (!vp.w || !vp.h) {
      return;
    }
    const sizeChanged =
      !!lastVp.current && (lastVp.current.w !== vp.w || lastVp.current.h !== vp.h);
    lastVp.current = vp;
    if (!viewRef.current) {
      fit(false, MIN_K_INICIAL);
    } else if (sizeChanged && (refitOnResize.current || !userMoved.current)) {
      refitOnResize.current = false;
      fit(false);
    }
  }, [vp, fit]);

  // Após recolher/expandir: mantém o nó clicado no mesmo lugar da tela; ou executa o enquadramento pendente
  useLayoutEffect(() => {
    const anchor = anchorRef.current;
    if (anchor) {
      anchorRef.current = null;
      const b = layout.boxes.get(anchor.id);
      const v = viewRef.current;
      if (b && v) {
        moveView({ k: v.k, x: anchor.sx - b.x * v.k, y: anchor.sy - b.y * v.k }, true);
      }
    }
    if (pendingFit.current) {
      pendingFit.current = false;
      fit(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layout]);

  useEffect(() => {
    const id = pendingFocus.current;
    if (!id || !layout.boxes.has(id)) {
      return;
    }
    pendingFocus.current = null;
    centerOn(id);
  }, [layout, focusTick, centerOn]);

  // Seleção por clique: se o nó ficou sob o painel ou fora da tela, traz para a área visível
  useEffect(() => {
    if (!selected || pendingFocus.current) {
      return;
    }
    const b = layout.boxes.get(selected);
    const v = viewRef.current;
    if (!b || !v) {
      return;
    }
    const left = v.x + b.x * v.k;
    const top = v.y + b.y * v.k;
    if (left < 8 || top < 8 || left + b.w * v.k > usableW - 8 || top + b.h * v.k > usableH - 8) {
      centerOn(selected);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, usableW, usableH]);

  const toggle = useCallback((id: string) => {
    const b = displayRef.current.get(id);
    const v = viewRef.current;
    if (b && v) {
      anchorRef.current = { id, sx: v.x + b.x * v.k, sy: v.y + b.y * v.k };
    }
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
    setHinted(true);
  }, []);

  const reveal = useCallback(
    (id: string) => {
      if (!model.byId.has(id)) {
        return;
      }
      const ancestors = ancestorsOf(model, id);
      setCollapsed((prev) => {
        if (!ancestors.some((a) => prev.has(a))) {
          return prev;
        }
        const next = new Set(prev);
        ancestors.forEach((a) => next.delete(a));
        return next;
      });
      setSelected(id);
      pendingFocus.current = id;
      setFocusTick((t) => t + 1);
      setHinted(true);
    },
    [model],
  );

  const select = useCallback((id: string) => {
    setSelected(id);
    setHinted(true);
  }, []);

  const allExpanded = collapsed.size === 0;
  const toggleAll = () => {
    pendingFit.current = true;
    setCollapsed(
      allExpanded
        ? new Set([...model.byId.keys()].filter((id) => (model.children.get(id) ?? []).length))
        : new Set(),
    );
    setHinted(true);
  };

  const zoomBy = useCallback(
    (factor: number, px?: number, py?: number, animate?: boolean) => {
      const v = viewRef.current;
      if (!v) {
        return;
      }
      const cx0 = px ?? usableW / 2;
      const cy0 = py ?? usableH / 2;
      const k = clamp(v.k * factor, MIN_K, MAX_K);
      const f = k / v.k;
      userMoved.current = true;
      moveView({ k, x: cx0 - (cx0 - v.x) * f, y: cy0 - (cy0 - v.y) * f }, animate);
    },
    [usableW, usableH, moveView],
  );

  // Roda do mouse: zoom (a página não rola); dentro do painel de detalhes, rola o painel
  useEffect(() => {
    const el = vpRef.current;
    if (!el) {
      return undefined;
    }
    const onWheel = (e: WheelEvent) => {
      if ((e.target as HTMLElement).closest?.('.kg-panel')) {
        return;
      }
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const fator = Math.exp(-e.deltaY * (e.deltaMode === 1 ? 0.06 : 0.0024));
      zoomBy(fator, e.clientX - rect.left, e.clientY - rect.top, false);
      setHinted(true);
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [zoomBy]);

  useEffect(() => {
    if (!toast) {
      return undefined;
    }
    const timer = setTimeout(() => setToast(null), 2400);
    return () => clearTimeout(timer);
  }, [toast]);
  const avisar = useCallback((text: string) => setToast({ id: Date.now(), text }), []);

  // Tela cheia
  const canFull = typeof document !== 'undefined' && !!document.fullscreenEnabled;
  useEffect(() => {
    const onChange = () => {
      refitOnResize.current = true;
      setIsFull(document.fullscreenElement === rootRef.current);
    };
    document.addEventListener('fullscreenchange', onChange);
    return () => document.removeEventListener('fullscreenchange', onChange);
  }, []);
  const toggleFull = () => {
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => undefined);
    } else {
      rootRef.current?.requestFullscreen().catch(() => undefined);
    }
  };

  // Arrastar para navegar (um dedo/mouse) e pinça para zoom (dois dedos)
  const onPointerDown = (e: ReactPointerEvent<HTMLDivElement>) => {
    if (e.pointerType === 'mouse' && e.button !== 0) {
      return;
    }
    if ((e.target as HTMLElement).closest?.('.kg-panel, .kg-toggle')) {
      return;
    }
    const g = gesture.current;
    g.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const v = viewRef.current ?? { x: 0, y: 0, k: 1 };
    if (g.pointers.size === 1) {
      g.start = { id: e.pointerId, x: e.clientX, y: e.clientY, vx: v.x, vy: v.y };
      g.moved = false;
      g.pinch = null;
    } else if (g.pointers.size === 2 && vpRef.current) {
      const [a, b] = [...g.pointers.values()];
      const rect = vpRef.current.getBoundingClientRect();
      g.pinch = {
        d: Math.hypot(a.x - b.x, a.y - b.y) || 1,
        k: v.k,
        vx: v.x,
        vy: v.y,
        mx: (a.x + b.x) / 2 - rect.left,
        my: (a.y + b.y) / 2 - rect.top,
      };
      g.moved = true;
    }
  };
  const onPointerMove = (e: ReactPointerEvent<HTMLDivElement>) => {
    const g = gesture.current;
    if (!g.pointers.has(e.pointerId) || !vpRef.current) {
      return;
    }
    g.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (g.pinch && g.pointers.size >= 2) {
      const [a, b] = [...g.pointers.values()];
      const rect = vpRef.current.getBoundingClientRect();
      const k = clamp((g.pinch.k * Math.hypot(a.x - b.x, a.y - b.y)) / g.pinch.d, MIN_K, MAX_K);
      const wx = (g.pinch.mx - g.pinch.vx) / g.pinch.k;
      const wy = (g.pinch.my - g.pinch.vy) / g.pinch.k;
      userMoved.current = true;
      setView({
        k,
        x: (a.x + b.x) / 2 - rect.left - wx * k,
        y: (a.y + b.y) / 2 - rect.top - wy * k,
      });
      return;
    }
    const s = g.start;
    if (!s || s.id !== e.pointerId) {
      return;
    }
    const dx = e.clientX - s.x;
    const dy = e.clientY - s.y;
    if (!g.moved) {
      if (Math.hypot(dx, dy) < 4) {
        return;
      }
      g.moved = true;
      setDragging(true);
      setHinted(true);
      stopViewAnim.current?.();
      try {
        vpRef.current.setPointerCapture(e.pointerId);
      } catch {
        // captura indisponível: o arraste continua enquanto o ponteiro estiver na área
      }
    }
    userMoved.current = true;
    setView((v) => ({ k: v ? v.k : 1, x: s.vx + dx, y: s.vy + dy }));
  };
  const onPointerEnd = (e: ReactPointerEvent<HTMLDivElement>) => {
    const g = gesture.current;
    g.pointers.delete(e.pointerId);
    if (g.pointers.size < 2) {
      g.pinch = null;
    }
    if (g.pointers.size === 0) {
      g.start = null;
      setDragging(false);
    }
  };
  const onBackgroundClick = () => {
    if (!gesture.current.moved) {
      setSelected(null);
    }
  };

  const onKeyDown = (e: ReactKeyboardEvent<HTMLDivElement>) => {
    if ((e.target as HTMLElement).closest?.('input, textarea, .kg-panel')) {
      return;
    }
    const pan = (dx: number, dy: number) => {
      const v = viewRef.current;
      if (v) {
        userMoved.current = true;
        moveView({ ...v, x: v.x + dx, y: v.y + dy }, true);
      }
    };
    const actions: Record<string, () => void> = {
      '+': () => zoomBy(1.25),
      '=': () => zoomBy(1.25),
      '-': () => zoomBy(0.8),
      '0': () => fit(true),
      ArrowLeft: () => pan(80, 0),
      ArrowRight: () => pan(-80, 0),
      ArrowUp: () => pan(0, 80),
      ArrowDown: () => pan(0, -80),
      Escape: () => setSelected(null),
    };
    const action = actions[e.key];
    if (!action || (e.key === 'Escape' && !selected)) {
      return;
    }
    e.preventDefault();
    action();
  };

  // Busca
  const matches = useMemo(() => {
    const q = semAcento(query.trim());
    if (!q) {
      return [];
    }
    return [...model.byId.values()]
      .filter((n) => semAcento(`${n.rotulo} ${n.descricao ?? ''}`).includes(q))
      .map((n) => n.id);
  }, [query, model]);
  const matchSet = useMemo(() => new Set(matches), [matches]);
  const goToMatch = (step: number) => {
    if (!matches.length) {
      return;
    }
    const i = (((matchIndex + step) % matches.length) + matches.length) % matches.length;
    setMatchIndex(i);
    reveal(matches[i]);
  };

  // Destaques: caminho até a raiz, subárvore e relações do nó selecionado
  const focus = useMemo(() => {
    if (!panelNode) {
      return null;
    }
    const tree = subtreeOf(model, panelNode.id, new Set(ancestorsOf(model, panelNode.id)));
    const related = new Set(tree);
    for (const n of model.neighbors.get(panelNode.id) ?? []) {
      related.add(n);
    }
    return { tree, related };
  }, [panelNode, model]);

  const connectors = useMemo(() => connectorsOf(display, model), [display, model]);
  const activeIds = new Set([selected, hovered].filter(Boolean));
  const relationEdges = model.relations
    .filter((e) => activeIds.has(e.origem) || activeIds.has(e.destino))
    .flatMap((e) => {
      const a = display.get(e.origem);
      const b = display.get(e.destino);
      if (!a || !b) {
        return [];
      }
      return [
        {
          id: e.id,
          d: relationPath(a, b),
          lit: e.origem === selected || e.destino === selected,
          a: Math.min(a.a ?? 1, b.a ?? 1),
        },
      ];
    });

  // Moldura acesa: está no caminho/subárvore do selecionado; apagada: nenhum item dela tem relação com ele
  const frameState = (frameBox: Caixa | undefined) => {
    if (!focus || !frameBox?.parent) {
      return { lit: false, dim: false };
    }
    const items = frameItems(model, collapsed, frameBox.parent);
    return {
      lit: focus.tree.has(frameBox.parent) && items.some((k) => focus.tree.has(k)),
      dim: !items.some((k) => focus.related.has(k)),
    };
  };

  const stats = useMemo(() => {
    const counts = new Map<No['tipo'], number>();
    for (const n of model.byId.values()) {
      counts.set(n.tipo, (counts.get(n.tipo) ?? 0) + 1);
    }
    return [...counts.entries()].sort((a, b) => metaOf(a[0]).order - metaOf(b[0]).order);
  }, [model]);

  const frames: [string, Caixa][] = [];
  const nodes: [string, Caixa][] = [];
  for (const [id, box] of display) {
    if (box.kind === 'frame') {
      frames.push([id, box]);
    } else if (model.byId.has(id)) {
      nodes.push([id, box]);
    }
  }
  const v = view ?? { x: 0, y: 0, k: 1 };

  return (
    <div ref={rootRef} className={cx('kg-root', isFull && 'is-full')}>
      <div className="kg-head">
        <div className="kg-brand">
          <span className="kg-brand-icon">
            <Waypoints size={17} aria-hidden="true" />
          </span>
          <div className="kg-brand-text">
            <span className="kg-brand-name">Grafo de conhecimento</span>
            <span className="kg-stats">
              {stats.map(([tipo, n]) => (
                <span key={tipo} className="kg-stat">
                  <i className={`kg-dot kg-dot--${tipo}`} />
                  {n} {n === 1 ? metaOf(tipo).label.toLowerCase() : metaOf(tipo).plural}
                </span>
              ))}
            </span>
          </div>
        </div>
        <div className="kg-tools">
          <label className="kg-search">
            <Search size={14} aria-hidden="true" />
            <input
              value={query}
              placeholder="Buscar no grafo"
              aria-label="Buscar no grafo"
              onChange={(e) => {
                setQuery(e.target.value);
                setMatchIndex(-1);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  goToMatch(e.shiftKey ? -1 : 1);
                } else if (e.key === 'Escape') {
                  setQuery('');
                }
              }}
            />
            {query && (
              <span className="kg-search-count">
                {matches.length ? `${Math.max(0, matchIndex) + 1}/${matches.length}` : '0'}
              </span>
            )}
          </label>
          <button
            type="button"
            className="kg-btn"
            onClick={() => zoomBy(0.8, undefined, undefined, true)}
            title="Diminuir zoom (−)"
            aria-label="Diminuir zoom"
          >
            <ZoomOut size={16} aria-hidden="true" />
          </button>
          <span className="kg-zoom" aria-live="polite">
            {Math.round(v.k * 100)}%
          </span>
          <button
            type="button"
            className="kg-btn"
            onClick={() => zoomBy(1.25, undefined, undefined, true)}
            title="Aumentar zoom (+)"
            aria-label="Aumentar zoom"
          >
            <ZoomIn size={16} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="kg-btn"
            onClick={() => fit(true)}
            title="Enquadrar o grafo (0)"
            aria-label="Enquadrar o grafo"
          >
            <Scan size={16} aria-hidden="true" />
          </button>
          <button
            type="button"
            className="kg-btn"
            onClick={toggleAll}
            title={allExpanded ? 'Recolher tudo' : 'Expandir tudo'}
            aria-label={allExpanded ? 'Recolher tudo' : 'Expandir tudo'}
          >
            {allExpanded ? (
              <FoldVertical size={16} aria-hidden="true" />
            ) : (
              <UnfoldVertical size={16} aria-hidden="true" />
            )}
          </button>
          {canFull && (
            <button
              type="button"
              className="kg-btn"
              onClick={toggleFull}
              title={isFull ? 'Sair da tela cheia' : 'Tela cheia'}
              aria-label={isFull ? 'Sair da tela cheia' : 'Tela cheia'}
            >
              {isFull ? (
                <Minimize2 size={16} aria-hidden="true" />
              ) : (
                <Maximize2 size={16} aria-hidden="true" />
              )}
            </button>
          )}
        </div>
      </div>

      <div
        ref={vpRef}
        className={cx('kg-viewport', dragging && 'is-dragging')}
        tabIndex={0}
        aria-label="Grafo de conhecimento: arraste para navegar, roda do mouse para zoom"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerEnd}
        onPointerCancel={onPointerEnd}
        onClick={onBackgroundClick}
        onKeyDown={onKeyDown}
      >
        <div
          className="kg-world"
          style={{ transform: `translate(${v.x}px, ${v.y}px) scale(${v.k})` }}
        >
          <div className="kg-layer">
            {frames.map(([id, box]) => (
              <div
                key={id}
                className="kg-frame-pos"
                style={{ transform: `translate(${box.x}px, ${box.y}px)`, opacity: box.a ?? 1 }}
              >
                <div
                  className={cx('kg-frame', frameState(box).dim && 'is-dim')}
                  style={{ width: box.w, height: box.h }}
                >
                  {(box.heads ?? []).map((h) => (
                    <div key={h.label} className="kg-frame-head" style={{ top: h.y + 4 }}>
                      {h.label}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
          <svg className="kg-edges" width="1" height="1" aria-hidden="true">
            <defs>
              {['arrow', 'arrow-lit', 'arrow-rel'].map((name) => (
                <marker
                  key={name}
                  id={`${uid}-${name}`}
                  className={`kg-${name}`}
                  viewBox="0 0 10 10"
                  refX="9"
                  refY="5"
                  markerWidth="9"
                  markerHeight="9"
                  markerUnits="userSpaceOnUse"
                  orient="auto"
                >
                  <path d="M0,0 L10,5 L0,10 z" />
                </marker>
              ))}
            </defs>
            {connectors.map((c) => {
              const lit =
                !!focus &&
                (c.frame
                  ? frameState(display.get(c.id)).lit
                  : focus.tree.has(c.from) && focus.tree.has(c.id));
              return (
                <g key={c.id} className="kg-edge-g" opacity={c.a * (focus && !lit ? 0.22 : 1)}>
                  {lit && <path className="kg-edge-glow" d={c.d} />}
                  <path
                    className={cx('kg-edge', lit && 'is-lit')}
                    d={c.d}
                    markerEnd={`url(#${uid}-${lit ? 'arrow-lit' : 'arrow'})`}
                  />
                </g>
              );
            })}
            {relationEdges.map((r) => (
              <path
                key={r.id}
                className={cx('kg-rel', r.lit && 'is-lit')}
                d={r.d}
                opacity={r.a}
                markerEnd={`url(#${uid}-arrow-rel)`}
              />
            ))}
          </svg>
          <div className="kg-layer">
            {connectors
              .filter((c) => c.frame && model.byId.has(c.from))
              .map((c) => (
                <div
                  key={`pill-${c.id}`}
                  className="kg-pill-pos"
                  style={{ transform: `translate(${c.x}px, ${c.labelY}px)`, opacity: c.a }}
                >
                  <span className={cx('kg-pill', frameState(display.get(c.id)).dim && 'is-dim')}>
                    {stackCounts(model, collapsed, c.from)}
                  </span>
                </div>
              ))}
          </div>
          <div className="kg-layer">
            {nodes.map(([id, box]) => (
              <GraphNode
                key={id}
                node={model.byId.get(id) as No}
                box={box}
                model={model}
                collapsed={collapsed.has(id)}
                flags={{
                  selected: id === selected,
                  dim: !!focus && !focus.related.has(id),
                  match: matchSet.has(id),
                }}
                onSelect={select}
                onToggle={toggle}
                onHover={setHovered}
              />
            ))}
          </div>
        </div>

        {!hinted && (
          <div className="kg-hint">
            <span>
              <Hand size={13} aria-hidden="true" /> Arraste para navegar
            </span>
            <span>
              <ZoomIn size={13} aria-hidden="true" /> Roda do mouse para zoom
            </span>
            <span>
              <MousePointerClick size={13} aria-hidden="true" /> Clique para detalhes
            </span>
          </div>
        )}
        {toast && (
          <div key={toast.id} className="kg-toast" role="status">
            {toast.text}
          </div>
        )}
        {panelNode && (
          <DetailsPanel
            key={panelNode.id}
            node={panelNode}
            model={model}
            compact={compact}
            onClose={() => setSelected(null)}
            onSelect={select}
            onReveal={reveal}
            onError={avisar}
          />
        )}
      </div>
    </div>
  );
}

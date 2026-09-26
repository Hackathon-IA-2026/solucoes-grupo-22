// Modelo e layout do grafo de conhecimento: hierarquia, relações, posições dos cartões e animação entre layouts.
// Porte do KnowledgeGraph.jsx do EnergyNexus (Chainlit), sem React, para ser testado isoladamente.
import type { Fonte, Grafo, Icone, No, TipoNo } from './dados';

export type Meta = {
  label: string;
  plural: string;
  icon: Icone;
  w: number;
  h: number;
  order: number;
  /** Folhas desse tipo (e nós recolhidos, se tiverem filhos) ficam empilhadas numa moldura sob o pai. */
  stack?: boolean;
};

export const TYPE_META: Record<TipoNo, Meta> = {
  empresa: { label: 'Empresa', plural: 'empresas', icon: 'building-2', w: 280, h: 92, order: 0 },
  categoria: { label: 'Categoria', plural: 'categorias', icon: 'layers', w: 260, h: 76, order: 1 },
  grupo: {
    label: 'Tipo de documento',
    plural: 'tipos de documento',
    icon: 'folder-open',
    w: 252,
    h: 60,
    order: 1.5,
    stack: true,
  },
  indicador: {
    label: 'Indicador',
    plural: 'indicadores',
    icon: 'activity',
    w: 252,
    h: 64,
    order: 2,
    stack: true,
  },
  referencia: {
    label: 'Referência',
    plural: 'referências',
    icon: 'file-text',
    w: 252,
    h: 56,
    order: 3,
    stack: true,
  },
};

const GAP_X = 28; // entre subárvores irmãs
const GAP_Y = 56; // pai → filhos
const GAP_FRAME = 72; // pai → moldura (espaço para a pílula "3 indicadores")
const FRAME_PAD = 12;
const ITEM_GAP = 8;
const COL_GAP = 10;
const FRAME_UMA_COLUNA_ATE = 6; // molduras com mais itens que isso usam duas colunas
const GROUP_HEAD = 22; // cabeçalho de grupo dentro da moldura ("Referências")
export const AUTO_COLLAPSE_ABOVE = 60; // nós; acima disso o grafo abre com as categorias recolhidas

export type Modelo = {
  byId: Map<string, No>;
  parent: Map<string, string>;
  children: Map<string, string[]>;
  roots: string[];
  relations: Grafo['arestas'];
  neighbors: Map<string, Set<string>>;
  fontes: Map<string, Fonte>;
  nodeByFonte: Map<string, string>;
  depth: Map<string, number>;
  descendants: Map<string, number>;
};

export type Caixa = {
  kind: 'node' | 'frame';
  x: number;
  y: number;
  w: number;
  h: number;
  /** moldura: o nó pai; nó empilhado: a moldura onde está */
  parent?: string;
  frame?: string;
  heads?: { label: string; y: number }[];
  /** opacidade durante a animação; `exiting` quando a caixa está saindo */
  a?: number;
  exiting?: boolean;
};

export type Caixas = Map<string, Caixa>;

export const metaOf = (tipo: TipoNo) => TYPE_META[tipo];

export function buildModel(data: Grafo): Modelo {
  const byId = new Map(data.nos.map((n) => [n.id, n]));
  const parent = new Map<string, string>();
  for (const n of data.nos) {
    if (n.pai && byId.has(n.pai)) {
      parent.set(n.id, n.pai);
    }
  }
  const children = new Map<string, string[]>([...byId.keys()].map((id) => [id, []]));
  for (const [child, p] of parent) {
    children.get(p)?.push(child);
  }
  const roots = [...byId.keys()].filter((id) => !parent.has(id));

  const relations = data.arestas.filter(
    (e) => byId.has(e.origem) && byId.has(e.destino) && parent.get(e.destino) !== e.origem,
  );
  const neighbors = new Map<string, Set<string>>();
  const link = (a: string, b: string) => {
    neighbors.set(a, (neighbors.get(a) ?? new Set()).add(b));
  };
  for (const e of relations) {
    link(e.origem, e.destino);
    link(e.destino, e.origem);
  }

  const fontes = new Map(data.fontes.map((f) => [f.id, f]));
  const nodeByFonte = new Map<string, string>();
  for (const n of data.nos) {
    if (n.fonte && !nodeByFonte.has(n.fonte)) {
      nodeByFonte.set(n.fonte, n.id);
    }
  }

  const depth = new Map<string, number>();
  const descendants = new Map<string, number>();
  const walk = (id: string, d: number): number => {
    depth.set(id, d);
    let total = 0;
    for (const k of children.get(id) ?? []) {
      total += 1 + walk(k, d + 1);
    }
    descendants.set(id, total);
    return total;
  };
  roots.forEach((r) => walk(r, 0));

  return {
    byId,
    parent,
    children,
    roots,
    relations,
    neighbors,
    fontes,
    nodeByFonte,
    depth,
    descendants,
  };
}

export function ancestorsOf(model: Modelo, id: string): string[] {
  const list: string[] = [];
  for (let cur = model.parent.get(id); cur !== undefined; cur = model.parent.get(cur)) {
    list.push(cur);
  }
  return list;
}

export function subtreeOf(model: Modelo, id: string, into: Set<string>): Set<string> {
  into.add(id);
  for (const k of model.children.get(id) ?? []) {
    subtreeOf(model, k, into);
  }
  return into;
}

/** O nó fica empilhado na moldura do pai: tipo `stack` e sem filhos visíveis (folha ou recolhido). */
function empilhado(model: Modelo, collapsed: Set<string>, id: string): boolean {
  const node = model.byId.get(id) as No;
  return !!metaOf(node.tipo).stack && (!(model.children.get(id) ?? []).length || collapsed.has(id));
}

/** Filhos de `parentId` que ficam na moldura. */
export function frameItems(model: Modelo, collapsed: Set<string>, parentId: string): string[] {
  return (model.children.get(parentId) ?? []).filter((k) => empilhado(model, collapsed, k));
}

export function stackCounts(model: Modelo, collapsed: Set<string>, parentId: string): string {
  const counts = new Map<TipoNo, number>();
  for (const k of frameItems(model, collapsed, parentId)) {
    const tipo = (model.byId.get(k) as No).tipo;
    counts.set(tipo, (counts.get(tipo) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => metaOf(a[0]).order - metaOf(b[0]).order)
    .map(([tipo, n]) => `${n} ${n === 1 ? metaOf(tipo).label.toLowerCase() : metaOf(tipo).plural}`)
    .join(' · ');
}

type Bloco =
  | { kind: 'tree'; id: string; w: number; h: number }
  | {
      kind: 'frame';
      id: string;
      w: number;
      h: number;
      rows: { id: string; y: number; col: number }[];
      heads: { label: string; y: number }[];
      itemW: number;
    };

type Medida = { w: number; h: number; blocks: Bloco[]; childrenW: number; gap: number };

/**
 * Layout hierárquico, de cima para baixo. Folhas empilháveis (e grupos recolhidos) ficam numa moldura sob o pai; os
 * demais filhos se abrem lado a lado. Com várias raízes, elas ficam lado a lado (o grafo de uma empresa tem uma só).
 */
export function computeLayout(
  model: Modelo,
  collapsed: Set<string>,
): { boxes: Caixas; bounds: Bounds | null } {
  const { byId, children } = model;
  const meta = (id: string) => metaOf((byId.get(id) as No).tipo);
  const measures = new Map<string, Medida>();

  const measure = (id: string) => {
    const kids = collapsed.has(id) ? [] : (children.get(id) ?? []);
    const blocks: Bloco[] = [];
    const stack: string[] = [];
    for (const k of kids) {
      if (empilhado(model, collapsed, k)) {
        stack.push(k);
        continue;
      }
      measure(k);
      const m = measures.get(k) as Medida;
      blocks.push({ kind: 'tree', id: k, w: m.w, h: m.h });
    }
    if (stack.length) {
      const items = stack
        .map((k, i) => [k, i] as const)
        .sort((a, b) => meta(a[0]).order - meta(b[0]).order || a[1] - b[1])
        .map(([k]) => k);
      const cols = items.length > FRAME_UMA_COLUNA_ATE ? 2 : 1;
      const itemW = Math.max(...items.map((k) => meta(k).w));
      const rows: { id: string; y: number; col: number }[] = [];
      const heads: { label: string; y: number }[] = [];
      let y = FRAME_PAD;
      let grupo: string[] = [];
      const fecharGrupo = () => {
        for (let i = 0; i < grupo.length; i += cols) {
          const linha = grupo.slice(i, i + cols);
          linha.forEach((k, col) => rows.push({ id: k, y, col }));
          y += Math.max(...linha.map((k) => meta(k).h)) + ITEM_GAP;
        }
        grupo = [];
      };
      items.forEach((k, i) => {
        const tipo = (byId.get(k) as No).tipo;
        if (i > 0 && tipo !== (byId.get(items[i - 1]) as No).tipo) {
          fecharGrupo();
          heads.push({ label: metaOf(tipo).plural, y });
          y += GROUP_HEAD;
        }
        grupo.push(k);
      });
      fecharGrupo();
      const w = cols * itemW + (cols - 1) * COL_GAP + 2 * FRAME_PAD;
      blocks.push({
        kind: 'frame',
        id: `frame::${id}`,
        w,
        h: y - ITEM_GAP + FRAME_PAD,
        rows,
        heads,
        itemW,
      });
    }
    const childrenW = blocks.length
      ? blocks.reduce((s, b) => s + b.w, 0) + GAP_X * (blocks.length - 1)
      : 0;
    const gap = blocks.some((b) => b.kind === 'frame') ? GAP_FRAME : GAP_Y;
    const own = meta(id);
    measures.set(id, {
      w: Math.max(own.w, childrenW),
      h: own.h + (blocks.length ? gap + Math.max(...blocks.map((b) => b.h)) : 0),
      blocks,
      childrenW,
      gap,
    });
  };

  const boxes: Caixas = new Map();
  const place = (id: string, left: number, top: number) => {
    const own = meta(id);
    const m = measures.get(id) as Medida;
    let centro = left + m.w / 2;
    if (m.blocks.length) {
      let bx = left + (m.w - m.childrenW) / 2;
      const by = top + own.h + m.gap;
      const centers: number[] = [];
      for (const b of m.blocks) {
        if (b.kind === 'tree') {
          place(b.id, bx, by);
          const child = boxes.get(b.id) as Caixa;
          centers.push(child.x + child.w / 2);
        } else {
          boxes.set(b.id, {
            kind: 'frame',
            parent: id,
            x: bx,
            y: by,
            w: b.w,
            h: b.h,
            heads: b.heads,
          });
          for (const r of b.rows) {
            boxes.set(r.id, {
              kind: 'node',
              frame: b.id,
              x: bx + FRAME_PAD + r.col * (b.itemW + COL_GAP),
              y: by + r.y,
              w: b.itemW,
              h: meta(r.id).h,
            });
          }
          centers.push(bx + b.w / 2);
        }
        bx += b.w + GAP_X;
      }
      centro = (centers[0] + centers[centers.length - 1]) / 2;
    }
    boxes.set(id, { kind: 'node', x: centro - own.w / 2, y: top, w: own.w, h: own.h });
  };

  let x = 0;
  for (const r of model.roots) {
    measure(r);
    place(r, x, 0);
    x += (measures.get(r) as Medida).w + GAP_X * 2;
  }
  return { boxes, bounds: boundsOf(boxes) };
}

export type Bounds = { minX: number; minY: number; w: number; h: number };

function boundsOf(boxes: Caixas): Bounds | null {
  if (!boxes.size) {
    return null;
  }
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const b of boxes.values()) {
    minX = Math.min(minX, b.x);
    minY = Math.min(minY, b.y);
    maxX = Math.max(maxX, b.x + b.w);
    maxY = Math.max(maxY, b.y + b.h);
  }
  return { minX, minY, w: maxX - minX, h: maxY - minY };
}

// ---------------------------------------------------------------- animação

export const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);

/** Chama `onStep` com o progresso (0 → 1, com desaceleração) a cada quadro; devolve a função que para. */
export function tween(
  duration: number,
  onStep: (t: number) => void,
  onDone?: () => void,
): () => void {
  let raf = 0;
  let t0 = 0;
  let stopped = false;
  const step = (now: number) => {
    if (stopped) {
      return;
    }
    if (!t0) {
      t0 = now;
    }
    const t = Math.min(1, (now - t0) / duration);
    onStep(easeOut(t));
    if (t < 1) {
      raf = requestAnimationFrame(step);
    } else if (onDone) {
      onDone();
    }
  };
  raf = requestAnimationFrame(step);
  return () => {
    stopped = true;
    cancelAnimationFrame(raf);
  };
}

/** Anima as caixas do layout anterior para o novo: novas saem do ancestral, removidas voltam para ele. */
export function tweenBoxes(
  from: Caixas,
  to: Caixas,
  model: Modelo,
  onFrame: (boxes: Caixas) => void,
  duration: number,
): () => void {
  if (!duration || from === to) {
    onFrame(to);
    return () => undefined;
  }
  const anchor = (id: string, box: Caixa, boxes: Caixas) => {
    for (
      let cur = box.kind === 'frame' ? box.parent : model.parent.get(id);
      cur != null;
      cur = model.parent.get(cur)
    ) {
      const b = boxes.get(cur);
      if (b) {
        return b;
      }
    }
    return null;
  };
  const centerOn = (box: Caixa, a: Caixa | null) =>
    a ? { x: a.x + a.w / 2 - box.w / 2, y: a.y + a.h / 2 - box.h / 2 } : { x: box.x, y: box.y };
  const ids = new Set([...from.keys(), ...to.keys()]);
  const start = new Map<string, Caixa>();
  const end = new Map<string, Caixa>();
  let changed = false;
  for (const id of ids) {
    const a = from.get(id);
    const b = to.get(id);
    if (a && b) {
      start.set(id, a);
      end.set(id, b);
      if (a.x !== b.x || a.y !== b.y || a.w !== b.w || a.h !== b.h || (a.a != null && a.a !== 1)) {
        changed = true;
      }
    } else if (b) {
      start.set(id, { ...b, ...centerOn(b, anchor(id, b, from)), a: 0 });
      end.set(id, b);
      changed = true;
    } else if (a) {
      start.set(id, a);
      end.set(id, { ...a, ...centerOn(a, anchor(id, a, to)), a: 0, exiting: true });
      changed = true;
    }
  }
  if (!changed) {
    onFrame(to);
    return () => undefined;
  }
  return tween(
    duration,
    (e) => {
      const frame: Caixas = new Map();
      for (const id of ids) {
        const s = start.get(id) as Caixa;
        const d = end.get(id) as Caixa;
        frame.set(id, {
          ...d,
          x: lerp(s.x, d.x, e),
          y: lerp(s.y, d.y, e),
          w: lerp(s.w, d.w, e),
          h: lerp(s.h, d.h, e),
          a: lerp(s.a ?? 1, d.a ?? 1, e),
        });
      }
      onFrame(frame);
    },
    () => onFrame(to),
  );
}

// ---------------------------------------------------------------- conexões

function elbow(x1: number, y1: number, x2: number, y2: number) {
  if (y2 <= y1 + 2 || Math.abs(x2 - x1) < 1) {
    return { d: `M${x1},${y1} L${x2},${y2}`, labelY: (y1 + y2) / 2 };
  }
  const mid = y1 + Math.min(24, (y2 - y1) / 2);
  const s = Math.sign(x2 - x1);
  const r = Math.min(12, Math.abs(x2 - x1) / 2, mid - y1, (y2 - mid) / 2);
  return {
    d: `M${x1},${y1} L${x1},${mid - r} Q${x1},${mid} ${x1 + s * r},${mid} L${x2 - s * r},${mid} Q${x2},${mid} ${x2},${mid + r} L${x2},${y2}`,
    labelY: (mid + y2) / 2 + 2,
  };
}

export type Conector = {
  id: string;
  from: string;
  frame: boolean;
  d: string;
  x: number;
  labelY: number;
  a: number;
};

/** Linhas pai → filho (e pai → moldura); cartões dentro de moldura não têm linha própria. */
export function connectorsOf(display: Caixas, model: Modelo): Conector[] {
  const out: Conector[] = [];
  for (const [id, box] of display) {
    let parentId: string | undefined;
    if (box.kind === 'frame') {
      parentId = box.parent;
    } else if (!box.frame) {
      parentId = model.parent.get(id);
    }
    const p = parentId == null ? undefined : display.get(parentId);
    if (parentId == null || !p) {
      continue;
    }
    const x2 = box.x + box.w / 2;
    const { d, labelY } = elbow(p.x + p.w / 2, p.y + p.h, x2, box.y);
    out.push({
      id,
      from: parentId,
      frame: box.kind === 'frame',
      d,
      x: x2,
      labelY,
      a: Math.min(p.a ?? 1, box.a ?? 1),
    });
  }
  return out;
}

/** Curva de uma relação (indicador → referência que o sustenta). */
export function relationPath(a: Caixa, b: Caixa): string {
  const ay = a.y + a.h / 2;
  const by = b.y + b.h / 2;
  if (a.frame && a.frame === b.frame) {
    // mesma moldura: curva pelo lado direito, maior quanto mais distantes os cartões
    const x = Math.max(a.x + a.w, b.x + b.w);
    const bulge = 18 + Math.min(44, Math.abs(by - ay) * 0.14);
    return `M${a.x + a.w},${ay} C${x + bulge},${ay} ${x + bulge},${by} ${b.x + b.w + 2},${by}`;
  }
  const ac = a.x + a.w / 2;
  const bc = b.x + b.w / 2;
  if (Math.abs(bc - ac) > Math.abs(by - ay)) {
    const s = Math.sign(bc - ac) || 1;
    const x1 = s > 0 ? a.x + a.w : a.x;
    const x2 = s > 0 ? b.x : b.x + b.w;
    const dx = (x2 - x1) / 2;
    return `M${x1},${ay} C${x1 + dx},${ay} ${x2 - dx},${by} ${x2},${by}`;
  }
  const s = Math.sign(by - ay) || 1;
  const y1 = s > 0 ? a.y + a.h : a.y;
  const y2 = s > 0 ? b.y : b.y + b.h;
  const dy = (y2 - y1) / 2;
  return `M${ac},${y1} C${ac},${y1 + dy} ${bc},${y2 - dy} ${bc},${y2}`;
}

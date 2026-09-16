/**
 * hexMmpCartogram.ts — geometry for the paired MMP cartogram.
 *
 * MMP splits a delegation almost in half, 436 district seats against 437 top-off, so
 * neither tier is a companion to the other. Every state is therefore drawn twice, once
 * per tier, at sqrt(share) of its width — about 0.71 each — so the two copies together
 * cover the area the single state covers on the base map and one hexagon is still one
 * seat at the same size as everywhere else.
 *
 * Unlike the House cartogram this payload is already exploded: the pipeline searched for
 * a clear spot for each pair in the space the map is drawn in, so the coordinates here
 * are final and only the Y flip is applied.
 *
 * Cartogram concept and state outlines: Congressional District Hexmap by Daniel Donner
 * for The Downballot (https://the-db.co/maps), CC BY 4.0.
 */

const SQRT3 = Math.sqrt(3);

export type MmpTier = 'district' | 'topoff';

interface RawTier {
  rings: [number, number][][];
  seats: string[];
  /** flat [col, row, seatIdx] on a lattice meta.subDiv times finer than a seat */
  cells: number[];
}

interface RawMmpState {
  fips: string;
  offset: [number, number];
  tiers: Partial<Record<MmpTier, RawTier>>;
}

export interface RawMmpCartogram {
  meta: { R: number; x0: number; y0: number; subDiv: number; seats: number; triple: boolean; source: string };
  states: Record<string, RawMmpState>;
}

export interface MmpTierGeometry {
  kind: MmpTier;
  /** the copy's own outline */
  outline: string;
  /** one path per seat, its sub-cells merged */
  seatPaths: string[];
  /** the seat ids, so fills can be looked up by district or by index */
  seats: string[];
  /** boundaries between two seats */
  seatEdges: string;
  /** the copy's perimeter, for the border */
  outerEdges: string;
  bbox: { x0: number; y0: number; x1: number; y1: number };
  centroid: [number, number];
}

export interface MmpStateGeometry {
  abbr: string;
  fips: string;
  tiers: MmpTierGeometry[];
  bbox: { x0: number; y0: number; x1: number; y1: number };
}

export interface MmpCartogram {
  meta: RawMmpCartogram['meta'];
  states: MmpStateGeometry[];
  byAbbr: Record<string, MmpStateGeometry>;
  bbox: { x0: number; y0: number; x1: number; y1: number };
}

const NEIGHBORS: [number, number][][] = [
  [[+1, 0], [0, -1], [-1, -1], [-1, 0], [-1, +1], [0, +1]],   // even row
  [[+1, 0], [+1, -1], [0, -1], [-1, 0], [0, +1], [+1, +1]],   // odd row
];

function hexCenter(col: number, row: number, R: number, x0: number, y0: number): [number, number] {
  return [x0 + SQRT3 * R * (col + 0.5 * (row & 1)), y0 + 1.5 * R * row];
}

function hexVertices(cx: number, cy: number, R: number): [number, number][] {
  const out: [number, number][] = [];
  for (let i = 0; i < 6; i++) {
    const a = (Math.PI / 3) * i;
    out.push([cx + R * Math.sin(a), cy + R * Math.cos(a)]);
  }
  return out;
}

const KEY = (x: number, y: number) => `${x.toFixed(6)},${y.toFixed(6)}`;

function polyline(pts: [number, number][]): string {
  return 'M' + pts.map(p => `${p[0].toFixed(4)},${p[1].toFixed(4)}`).join('L');
}

function polygons(rings: [number, number][][]): string {
  return rings.map(r => polyline(r) + 'Z').join('');
}

/** Chain segments into runs so one round join carries a whole border. */
function chain(segs: [number, number][][]): [number, number][][] {
  const ends = new Map<string, number[]>();
  segs.forEach((s, i) => {
    for (const p of s) {
      const k = KEY(p[0], p[1]);
      const at = ends.get(k);
      if (at) at.push(i); else ends.set(k, [i]);
    }
  });
  const used = new Array(segs.length).fill(false);
  const out: [number, number][][] = [];
  for (let i = 0; i < segs.length; i++) {
    if (used[i]) continue;
    used[i] = true;
    const run = [segs[i][0], segs[i][1]];
    for (const dir of [0, 1]) {
      for (;;) {
        const tip = dir === 0 ? run[run.length - 1] : run[0];
        const cands = ends.get(KEY(tip[0], tip[1])) ?? [];
        const next = cands.find(j => !used[j]);
        if (next === undefined) break;
        used[next] = true;
        const [a, b] = segs[next];
        const far = KEY(a[0], a[1]) === KEY(tip[0], tip[1]) ? b : a;
        if (dir === 0) run.push(far); else run.unshift(far);
      }
    }
    out.push(run);
  }
  return out;
}

export function buildMmpCartogram(raw: RawMmpCartogram): MmpCartogram {
  const { R, x0, y0, subDiv } = raw.meta;
  const sub = R / subDiv;
  const T = (p: [number, number]): [number, number] => [p[0], -p[1]];

  const states: MmpStateGeometry[] = [];
  for (const [abbr, st] of Object.entries(raw.states)) {
    const tiers: MmpTierGeometry[] = [];
    for (const kind of ['district', 'topoff'] as MmpTier[]) {
      const t = st.tiers[kind];
      if (!t) continue;
      const seatOf = new Map<string, number>();
      for (let i = 0; i < t.cells.length; i += 3) {
        seatOf.set(`${t.cells[i]},${t.cells[i + 1]}`, t.cells[i + 2]);
      }
      const rings: [number, number][][][] = t.seats.map(() => []);
      const seatSeg: [number, number][][] = [];
      const outerSeg: [number, number][][] = [];
      const seen = new Set<string>();
      for (let i = 0; i < t.cells.length; i += 3) {
        const col = t.cells[i], row = t.cells[i + 1], seat = t.cells[i + 2];
        const c = hexCenter(col, row, sub, x0, y0);
        const verts = hexVertices(c[0], c[1], sub).map(T) as [number, number][];
        rings[seat].push(verts);
        NEIGHBORS[row & 1].forEach(([dc, dr], j) => {
          const nb = seatOf.get(`${col + dc},${row + dr}`);
          if (nb === seat) return;
          const a = verts[(j + 1) % 6], b = verts[(j + 2) % 6];
          const ka = KEY(a[0], a[1]), kb = KEY(b[0], b[1]);
          const key = ka < kb ? `${ka}|${kb}` : `${kb}|${ka}`;
          if (seen.has(key)) return;
          seen.add(key);
          if (nb === undefined) outerSeg.push([a, b]); else seatSeg.push([a, b]);
        });
      }
      const outlineRings = t.rings.map(r => r.map(p => T(p as [number, number])));
      const pts = outlineRings.flat();
      const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
      tiers.push({
        kind,
        outline: polygons(outlineRings),
        seatPaths: rings.map(polygons),
        seats: t.seats,
        seatEdges: chain(seatSeg).map(polyline).join(''),
        outerEdges: chain(outerSeg).map(polyline).join(''),
        bbox: { x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys) },
        centroid: [xs.reduce((s, v) => s + v, 0) / xs.length, ys.reduce((s, v) => s + v, 0) / ys.length],
      });
    }
    const bx = tiers.flatMap(t => [t.bbox.x0, t.bbox.x1]);
    const by = tiers.flatMap(t => [t.bbox.y0, t.bbox.y1]);
    states.push({
      abbr, fips: st.fips, tiers,
      bbox: { x0: Math.min(...bx), y0: Math.min(...by), x1: Math.max(...bx), y1: Math.max(...by) },
    });
  }

  const bx = states.flatMap(s => [s.bbox.x0, s.bbox.x1]);
  const by = states.flatMap(s => [s.bbox.y0, s.bbox.y1]);
  return {
    meta: raw.meta,
    states,
    byAbbr: Object.fromEntries(states.map(s => [s.abbr, s])),
    bbox: { x0: Math.min(...bx), y0: Math.min(...by), x1: Math.max(...bx), y1: Math.max(...by) },
  };
}

const cache = new Map<string, Promise<MmpCartogram>>();

export function loadMmpCartogram(wyoming: 'double' | 'triple'): Promise<MmpCartogram> {
  const url = `${import.meta.env.BASE_URL}hexmap/hex_mmp_cartogram${wyoming === 'triple' ? '_triple' : ''}.json`;
  let p = cache.get(url);
  if (!p) {
    p = fetch(url).then(r => r.json()).then((raw: RawMmpCartogram) => buildMmpCartogram(raw));
    cache.set(url, p);
  }
  return p;
}

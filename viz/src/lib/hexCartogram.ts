/**
 * hexCartogram.ts — geometry for the one-hexagon-per-seat House cartogram.
 *
 * Loads the payload written by `pipeline/build_hex_seat_cartogram.py` and turns it into
 * SVG paths. Everything here is scenario-independent, so it is computed once per file
 * and reused across STV/party-list, ballot depth and turnout: only the fill colours
 * change when the reader moves a control.
 *
 * Cartogram concept and state outlines: Congressional District Hexmap by Daniel Donner
 * for The Downballot (https://the-db.co/maps), CC BY 4.0.
 */

/** Pointy-top hexagon: vertex at the top, width sqrt(3)*R, height 2R. */
const SQRT3 = Math.sqrt(3);

/** Pull each state away from the map centre so neighbours read as separate shapes. */
export const EXPLODE = 1.14;

export interface CartogramMeta {
  R: number; x0: number; y0: number;
  seats: number; cellsPerSeat: number; triple: boolean; source: string;
}

interface RawState {
  clip: boolean;
  rings: [number, number][][];
  districts: string[];
  /** seat i belongs to districts[seats[i]]; seats are pre-sorted west→east per district */
  seats: number[];
  /** flat [col, row, seatIdx, isCore] runs */
  cells: number[];
}

export interface RawCartogram {
  meta: CartogramMeta;
  states: Record<string, RawState>;
}

export interface StateGeometry {
  abbr: string;
  clip: boolean;
  /** state outline, one subpath per ring, in render space */
  outline: string;
  /** hexagon path per seat index — a seat's cells merged, boundary fill included */
  seatPaths: string[];
  /** district index per seat index */
  seatDistrict: number[];
  districts: string[];
  /** every seat index belonging to a district, in west→east order */
  seatsByDistrict: number[][];
  /** all hexes of a district as one path, for hit-testing and hover */
  districtPaths: string[];
  /** boundaries between seats inside the same district */
  seatEdges: string;
  /** boundaries between districts, and the outer edge of the tiling */
  districtEdges: string;
  /** number of seats — core cells only */
  seatCount: number;
  bbox: { x0: number; y0: number; x1: number; y1: number };
  /** centroid of the drawn shape, used for label placement */
  centroid: [number, number];
  /** points tracing what is actually drawn, for label clearance tests */
  silhouette: [number, number][];
  /** every hex centre, for the "does this label sit on tiles" test */
  centres: [number, number][];
}

export interface Cartogram {
  meta: CartogramMeta;
  states: StateGeometry[];
  byAbbr: Record<string, StateGeometry>;
  bbox: { x0: number; y0: number; x1: number; y1: number };
}

// ── lattice ──────────────────────────────────────────────────────────────────

function hexCenter(col: number, row: number, R: number, x0: number, y0: number): [number, number] {
  return [x0 + SQRT3 * R * (col + 0.5 * (row & 1)), y0 + 1.5 * R * row];
}

function hexVertices(cx: number, cy: number, R: number): [number, number][] {
  const out: [number, number][] = [];
  for (let k = 0; k < 6; k++) {
    const a = (k * Math.PI) / 3;
    out.push([cx + R * Math.sin(a), cy + R * Math.cos(a)]);
  }
  return out;
}

/**
 * Neighbour steps for a pointy-top odd-r offset lattice, indexed by row parity.
 *
 * Both rows list their six neighbours in the same compass order — E, SE, SW, W, NW, NE.
 * That is what lets the shared edge fall out of the list position below instead of
 * needing a per-direction lookup: vertex k sits at k*60° from north running clockwise,
 * so neighbour j shares vertices (j+1) and (j+2).
 */
const NEIGHBORS: [number, number][][] = [
  [[+1, 0], [0, -1], [-1, -1], [-1, 0], [-1, +1], [0, +1]],   // even row
  [[+1, 0], [+1, -1], [0, -1], [-1, 0], [0, +1], [+1, +1]],   // odd row
];

// ── path helpers ─────────────────────────────────────────────────────────────

const KEY = (x: number, y: number) => `${Math.round(x * 1e5)},${Math.round(y * 1e5)}`;

/**
 * Join loose edge segments into continuous polylines.
 *
 * The tiling gives one segment per hex edge. Stroked individually they render as a row
 * of disconnected dashes with mitre gaps at every turn; chained, they take a single
 * round join and read as one drawn border. Closed loops come back closed so the fillet
 * below can treat them as cyclic.
 */
function chain(segments: [number, number][][]): [number, number][][] {
  const ends = new Map<string, number[]>();
  segments.forEach((s, i) => {
    for (const p of [s[0], s[1]]) {
      const k = KEY(p[0], p[1]);
      const at = ends.get(k);
      if (at) at.push(i); else ends.set(k, [i]);
    }
  });

  const used = new Uint8Array(segments.length);
  const out: [number, number][][] = [];

  const nextFrom = (tip: [number, number]): number => {
    for (const i of ends.get(KEY(tip[0], tip[1])) ?? []) if (!used[i]) return i;
    return -1;
  };

  for (let i = 0; i < segments.length; i++) {
    if (used[i]) continue;
    used[i] = 1;
    let line: [number, number][] = [segments[i][0], segments[i][1]];
    for (const forward of [true, false]) {
      for (;;) {
        const tip = forward ? line[line.length - 1] : line[0];
        const far = forward ? line[0] : line[line.length - 1];
        const j = nextFrom(tip);
        if (j < 0) break;
        used[j] = 1;
        const [a, b] = segments[j];
        const nxt: [number, number] = KEY(a[0], a[1]) === KEY(tip[0], tip[1]) ? b : a;
        if (forward) line.push(nxt); else line = [nxt, ...line];
        if (KEY(nxt[0], nxt[1]) === KEY(far[0], far[1])) break;   // closed the loop
      }
    }
    out.push(line);
  }
  return out;
}

const F = (v: number) => (Math.round(v * 100) / 100).toString();

function polyline(pts: [number, number][]): string {
  let d = `M${F(pts[0][0])} ${F(pts[0][1])}`;
  for (let i = 1; i < pts.length; i++) d += `L${F(pts[i][0])} ${F(pts[i][1])}`;
  return d;
}

function polygons(rings: [number, number][][]): string {
  return rings.map(r => polyline(r) + 'Z').join('');
}

// ── build ────────────────────────────────────────────────────────────────────

/**
 * Turn the raw payload into draw-ready paths.
 *
 * Y is flipped here (the payload is in lat-like units, SVG grows downward) and the
 * explode offset is folded into every coordinate, so nothing downstream has to know
 * about either transform.
 */
export function buildCartogram(raw: RawCartogram, explode = EXPLODE): Cartogram {
  const { R, x0, y0 } = raw.meta;
  const entries = Object.entries(raw.states);

  // Explode is measured on core-cell centres so a state with a long boundary-fill
  // fringe is not dragged off-centre by tiles that belong to its neighbour's silhouette.
  const coreCentres: Record<string, [number, number][]> = {};
  for (const [ab, st] of entries) {
    const pts: [number, number][] = [];
    for (let i = 0; i < st.cells.length; i += 4) {
      if (st.cells[i + 3]) pts.push(hexCenter(st.cells[i], st.cells[i + 1], R, x0, y0));
    }
    coreCentres[ab] = pts.length ? pts : [[x0, y0]];
  }
  const all = entries.flatMap(([ab]) => coreCentres[ab]);
  const mapCx = all.reduce((s, p) => s + p[0], 0) / all.length;
  const mapCy = all.reduce((s, p) => s + p[1], 0) / all.length;
  const k = explode - 1;

  const states: StateGeometry[] = [];

  for (const [ab, st] of entries) {
    const pts = coreCentres[ab];
    const cx = pts.reduce((s, p) => s + p[0], 0) / pts.length;
    const cy = pts.reduce((s, p) => s + p[1], 0) / pts.length;
    const ox = k * (cx - mapCx), oy = k * (cy - mapCy);
    // Y flip and offset, applied once.
    const T = (p: [number, number]): [number, number] => [p[0] + ox, -(p[1] + oy)];

    // Boundary fill only exists so the clip has no sliver to expose. DC is drawn
    // unclipped — its outline is a delegate hexagon, not a population-scaled shape — so
    // there the fill has nothing to hide behind and would inflate it into a blob.
    const cellIdx: number[] = [];
    for (let i = 0; i < st.cells.length; i += 4) {
      if (st.clip || st.cells[i + 3]) cellIdx.push(i);
    }
    const seatOf = new Map<string, number>();
    for (const i of cellIdx) seatOf.set(`${st.cells[i]},${st.cells[i + 1]}`, st.cells[i + 2]);

    const seatRings: [number, number][][][] = st.seats.map(() => []);
    const districtRings: [number, number][][][] = st.districts.map(() => []);
    const centres: [number, number][] = [];
    const seatSeg: [number, number][][] = [];
    const distSeg: [number, number][][] = [];
    const outerSeg: [number, number][][] = [];
    // Every interior edge is reached from both of its cells. Chaining treats a repeat
    // as a branch and stops early, so keep only the first sighting of each edge.
    const seen = new Set<string>();

    for (const i of cellIdx) {
      const col = st.cells[i], row = st.cells[i + 1];
      const seat = st.cells[i + 2], isCore = st.cells[i + 3];
      const c = hexCenter(col, row, R, x0, y0);
      if (isCore) centres.push(T(c));
      const verts = hexVertices(c[0], c[1], R).map(T) as [number, number][];
      seatRings[seat].push(verts);
      districtRings[st.seats[seat]].push(verts);

      NEIGHBORS[row & 1].forEach(([dc, dr], j) => {
        const nb = seatOf.get(`${col + dc},${row + dr}`);
        if (nb === seat) return;                    // same seat: no line at all
        const a = verts[(j + 1) % 6], b = verts[(j + 2) % 6];
        const ka = KEY(a[0], a[1]), kb = KEY(b[0], b[1]);
        const key = ka < kb ? `${ka}|${kb}` : `${kb}|${ka}`;
        if (seen.has(key)) return;
        seen.add(key);
        // A missing neighbour is the outer edge of this state's tiling. For a clipped
        // state that edge sits beyond the outline and vanishes under the clip; for an
        // unclipped one it *is* the silhouette, so it is kept aside to stroke as such.
        if (nb === undefined) { outerSeg.push([a, b]); if (st.clip) distSeg.push([a, b]); }
        else if (st.seats[nb] !== st.seats[seat]) distSeg.push([a, b]);
        else seatSeg.push([a, b]);
      });
    }

    // DC's ring is a delegate hexagon rather than a population-scaled shape, so its
    // tiles do not fill it. Outline what is actually drawn — the edge of the tiling.
    const outlineRings = st.rings.map(r => r.map(p => T(p as [number, number])));
    const outline = st.clip ? polygons(outlineRings) : chain(outerSeg).map(polyline).join('');
    const silhouette: [number, number][] = st.clip
      ? outlineRings.flat()
      : outerSeg.flat();

    const xs = silhouette.map(p => p[0]), ys = silhouette.map(p => p[1]);

    const seatsByDistrict: number[][] = st.districts.map(() => []);
    st.seats.forEach((di, si) => seatsByDistrict[di].push(si));

    states.push({
      abbr: ab,
      clip: st.clip,
      outline,
      seatPaths: seatRings.map(polygons),
      seatDistrict: st.seats,
      districts: st.districts,
      seatsByDistrict,
      districtPaths: districtRings.map(polygons),
      // Chained so a single round join carries the whole border, but traced exactly
      // along the hex edges. The print prototype filleted the corners here; on screen
      // that cut visibly across jutting hexes and left the fill showing on the wrong
      // side of its own district line. A staircase that is true to the tiles beats a
      // smooth line that is not.
      seatEdges: chain(seatSeg).map(polyline).join(''),
      districtEdges: chain(distSeg).map(polyline).join(''),
      seatCount: st.seats.length,
      bbox: { x0: Math.min(...xs), y0: Math.min(...ys), x1: Math.max(...xs), y1: Math.max(...ys) },
      centroid: [cx + ox, -(cy + oy)],
      silhouette,
      centres,
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

// ── party fill ───────────────────────────────────────────────────────────────

/**
 * Party for every seat in a state, from live results.
 *
 * Seats arrive pre-sorted west→east within each district, so dealing the district's
 * winners in F5_ORDER makes each district read as a left-to-right ideological gradient
 * and puts same-party seats next to each other. Districts whose seat count disagrees
 * with the geometry — only Arizona 04-03 today — fill as far as they can and leave the
 * rest grey rather than shifting every later seat by one.
 */
export function seatParties(
  st: StateGeometry,
  electedByDistrict: Record<string, string[]>,
  order: readonly string[],
): (string | undefined)[] {
  const rank = new Map(order.map((p, i) => [p, i]));
  const out: (string | undefined)[] = new Array(st.seatCount).fill(undefined);
  st.districts.forEach((did, di) => {
    const elected = electedByDistrict[did];
    if (!elected) return;
    const sorted = [...elected].sort(
      (a, b) => (rank.get(a) ?? order.length) - (rank.get(b) ?? order.length) || a.localeCompare(b),
    );
    const seats = st.seatsByDistrict[di];
    for (let i = 0; i < Math.min(seats.length, sorted.length); i++) out[seats[i]] = sorted[i];
  });
  return out;
}

// ── labels ───────────────────────────────────────────────────────────────────

type Side = 'top' | 'bottom' | 'left' | 'right';
type Bias = 'top' | 'bottom' | 'left' | 'right' | 'center';

/**
 * Sides hand-set where the state's own geometry has an obviously better slot than the
 * ordered search finds. Each is still validated for clearance and falls back to the
 * search if something else has taken the space.
 */
const PREFERRED: Record<string, [Side, Bias]> = {
  MA: ['bottom', 'right'], NV: ['top', 'right'], MN: ['top', 'right'],
  MI: ['right', 'top'], CA: ['bottom', 'right'], NM: ['top', 'right'],
  TX: ['bottom', 'right'], MS: ['bottom', 'right'], LA: ['bottom', 'right'],
  GA: ['right', 'bottom'], VA: ['bottom', 'right'], FL: ['right', 'center'],
  PA: ['right', 'top'],
};

/** Preference leans bottom-then-right so the eye learns one place to look. */
const CANDIDATES: [Side, Bias][] = [
  ['bottom', 'right'], ['right', 'bottom'], ['right', 'center'], ['bottom', 'center'],
  ['right', 'top'], ['top', 'right'], ['bottom', 'left'], ['top', 'center'],
  ['left', 'bottom'], ['left', 'center'], ['top', 'left'], ['left', 'top'],
];

export interface Label {
  abbr: string;
  x: number; y: number;
  anchor: 'start' | 'middle' | 'end';
  baseline: 'hanging' | 'middle' | 'auto';
  /** drawn when the label had to sit far enough out that its owner is ambiguous */
  leader?: [number, number, number, number];
  /** laid-out extent, so the caller can widen the viewBox to keep the text on screen */
  box: readonly [number, number, number, number];
}

/**
 * Place a two-letter label outside every state, on tiles of none and on top of no other
 * label. Each candidate is a side plus a bias along it — "below, toward the right",
 * "right, toward the top" — rather than a diagonal ray from the centre, which on an
 * irregular shape strands the label out in space.
 *
 * Coordinates are SVG, so "bottom" is larger y. Anything the search cannot place
 * cleanly is dropped rather than overlapped: at map scale a label sitting on the wrong
 * state is worse than no label, and the tooltip still names it.
 */
export function placeLabels(cg: Cartogram, fontSize: number): Label[] {
  const R = cg.meta.R;
  const occupied = cg.states.flatMap(s => s.centres);
  const labH = fontSize;

  const nearestState = (x: number, y: number): string => {
    let best = '', bd = Infinity;
    for (const s of cg.states) {
      for (const [px, py] of s.centres) {
        const d = (px - x) ** 2 + (py - y) ** 2;
        if (d < bd) { bd = d; best = s.abbr; }
      }
    }
    return best;
  };

  function anchorFor(pts: [number, number][], side: Side, bias: Bias, gap: number) {
    const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
    const xlo = Math.min(...xs), xhi = Math.max(...xs);
    const ylo = Math.min(...ys), yhi = Math.max(...ys);
    const band = 0.30;
    if (side === 'bottom' || side === 'top') {
      const keep = side === 'bottom'
        ? pts.filter(p => p[1] >= yhi - band * (yhi - ylo))
        : pts.filter(p => p[1] <= ylo + band * (yhi - ylo));
      const px = bias === 'right' ? Math.max(...keep.map(p => p[0]))
        : bias === 'left' ? Math.min(...keep.map(p => p[0]))
          : (xlo + xhi) / 2;
      const near = keep.filter(p => Math.abs(p[0] - px) < 1.2 * R);
      const use = near.length ? near : keep;
      const py = side === 'bottom' ? Math.max(...use.map(p => p[1])) : Math.min(...use.map(p => p[1]));
      const ha: Label['anchor'] = bias === 'right' ? 'start' : bias === 'left' ? 'end' : 'middle';
      return side === 'bottom'
        ? { x: px, y: py + gap, ha, va: 'hanging' as const }
        : { x: px, y: py - gap, ha, va: 'auto' as const };
    }
    const keep = side === 'right'
      ? pts.filter(p => p[0] >= xhi - band * (xhi - xlo))
      : pts.filter(p => p[0] <= xlo + band * (xhi - xlo));
    const py = bias === 'bottom' ? Math.max(...keep.map(p => p[1]))
      : bias === 'top' ? Math.min(...keep.map(p => p[1]))
        : (ylo + yhi) / 2;
    const near = keep.filter(p => Math.abs(p[1] - py) < 1.2 * R);
    const use = near.length ? near : keep;
    const px = side === 'right' ? Math.max(...use.map(p => p[0])) : Math.min(...use.map(p => p[0]));
    const va: Label['baseline'] = bias === 'bottom' ? 'hanging' : bias === 'top' ? 'auto' : 'middle';
    return side === 'right'
      ? { x: px + gap, y: py, ha: 'start' as const, va }
      : { x: px - gap, y: py, ha: 'end' as const, va };
  }

  const boxOf = (a: { x: number; y: number; ha: Label['anchor']; va: Label['baseline'] }, w: number) => {
    const lx = a.ha === 'start' ? a.x : a.ha === 'end' ? a.x - w : a.x - w / 2;
    const ly = a.va === 'hanging' ? a.y : a.va === 'auto' ? a.y - labH : a.y - labH / 2;
    return [lx, ly, lx + w, ly + labH] as const;
  };

  const order = [...cg.states].sort((a, b) => b.seatCount - a.seatCount || a.abbr.localeCompare(b.abbr));
  const taken: (readonly [number, number, number, number])[] = [];
  const out: Label[] = [];

  for (const st of order) {
    const pts = st.silhouette;
    const labW = 0.70 * labH * st.abbr.length;
    const order2 = PREFERRED[st.abbr]
      ? [PREFERRED[st.abbr], ...CANDIDATES.filter(c => c[0] !== PREFERRED[st.abbr][0] || c[1] !== PREFERRED[st.abbr][1])]
      : CANDIDATES;

    let hit: Label | null = null;
    // Gap outermost: exhaust every side at the tightest offset before moving the label
    // further out, so a label only drifts (and earns a leader line) when the state is
    // genuinely boxed in on all sides.
    for (const gap of [0.55 * R, 1.1 * R, 1.8 * R, 2.8 * R, 4.2 * R]) {
      for (const [side, bias] of order2) {
        const a = anchorFor(pts, side, bias, gap);
        const [bx0, by0, bx1, by1] = boxOf(a, labW);
        const m = 0.95 * R;
        if (occupied.some(p => p[0] > bx0 - m && p[0] < bx1 + m && p[1] > by0 - m && p[1] < by1 + m)) continue;
        const pad: readonly [number, number, number, number] =
          [bx0 - 0.85 * labH, by0 - 0.5 * labH, bx1 + 0.85 * labH, by1 + 0.5 * labH];
        if (taken.some(t => pad[0] < t[2] && t[0] < pad[2] && pad[1] < t[3] && t[1] < pad[3])) continue;
        // A label nearer some other state than its own is worse than no label — that is
        // what made the IL/IN/OH/KY/WV cluster unreadable. Once it is far enough out to
        // earn a leader line, the line says which state it belongs to instead.
        const far = gap > 2.0 * R;
        if (!far && nearestState(a.x, a.y) !== st.abbr) continue;
        taken.push(pad);
        hit = {
          abbr: st.abbr, x: a.x, y: a.y, anchor: a.ha, baseline: a.va,
          box: [bx0, by0, bx1, by1],
          leader: far ? [a.x, a.y, ...closestSilhouettePoint(pts, a.x, a.y)] as [number, number, number, number] : undefined,
        };
        break;
      }
      if (hit) break;
    }
    if (hit) out.push(hit);
  }
  return out;
}

function closestSilhouettePoint(pts: [number, number][], x: number, y: number): [number, number] {
  let best = pts[0], bd = Infinity;
  for (const p of pts) {
    const d = (p[0] - x) ** 2 + (p[1] - y) ** 2;
    if (d < bd) { bd = d; best = p; }
  }
  return best;
}

// ── loading ──────────────────────────────────────────────────────────────────

const cache = new Map<string, Promise<Cartogram>>();

/**
 * `double` / `triple` are the House seat maps, one hexagon per seat, districts inside each
 * state. The other two come from `build_hex_ec_cartogram.py` and have one district per
 * state, so their tiles sort west→east across the whole state:
 *
 * - `ec`: one hexagon per elector (975), state area scaled to electoral weight.
 * - `pop`: one hexagon per 1/4365 of the population, state area unscaled, so the smallest
 *   state holds ten tiles and a five-way vote share is legible everywhere.
 */
export type CartogramBasis = 'double' | 'triple' | 'ec' | 'pop';

const BASIS_URL: Record<CartogramBasis, string> = {
  double: '/hexmap/hex_seat_cartogram.json',
  triple: '/hexmap/hex_seat_cartogram_triple.json',
  ec: '/hexmap/hex_ec_cartogram.json',
  pop: '/hexmap/hex_pop_cartogram.json',
};

export function loadCartogram(basis: CartogramBasis): Promise<Cartogram> {
  const url = BASIS_URL[basis];
  let p = cache.get(url);
  if (!p) {
    p = fetch(url).then(r => r.json()).then((raw: RawCartogram) => buildCartogram(raw));
    cache.set(url, p);
  }
  return p;
}

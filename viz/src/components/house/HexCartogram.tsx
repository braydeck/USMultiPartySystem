import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as d3 from 'd3';
import { Button } from '@/components/ui/button';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER } from '../../constants/parties';
import {
  loadCartogram, placeLabels, seatParties,
  type Cartogram, type StateGeometry,
} from '../../lib/hexCartogram';
import type { DistrictResult } from '../../types';

/**
 * One hexagon = one seat, laid out on a population-scaled cartogram of the states.
 *
 * The geometry is fixed and comes from `viz/public/hexmap/`; only the fills respond to
 * the House controls, so switching STV/party list or moving turnout recolours the same
 * map rather than rebuilding it.
 *
 * Cartogram concept and state outlines: Congressional District Hexmap by Daniel Donner
 * for The Downballot (https://the-db.co/maps), CC BY 4.0.
 */

/**
 * Stroke widths as multiples of the hex circumradius, carried over from the print
 * prototype where the hierarchy was calibrated. They are converted to screen pixels and
 * drawn with a non-scaling stroke, so the map keeps the same weights whatever size the
 * card is — with floors, because the app renders this about five times smaller than the
 * poster it was tuned on and a sub-pixel line just disappears.
 */
const W_SEAT_R = 0.0284, W_DISTRICT_R = 0.265, W_CASING_R = 0.425, W_STATE_R = 0.193;
const MIN_SEAT = 0.55, MIN_DISTRICT = 1.9, MIN_STATE = 1.1;
const CASING_RATIO = W_CASING_R / W_DISTRICT_R;

const C_SEAT = '#ffffff', C_DISTRICT = '#111827', C_STATE = '#0b1220';
const C_EMPTY = '#e2e8f0';

/** Target on-screen size of a state label. Placement drops any that cannot clear. */
const LABEL_PX = 11;

/** A fixed heavy stroke is wider than Alaska's panhandle, so taper the outline by size. */
const stateTaper = (seats: number) => Math.min(1, Math.max(0.4, Math.sqrt(seats / 10)));

interface HoverInfo { districtId: string; abbr: string; x: number; y: number }

interface Props {
  wyoming: 'double' | 'triple';
  /** live results keyed by state FIPS — the source of every fill colour */
  districtResults: Record<string, DistrictResult[]>;
  /** state abbreviation, or null for the whole map */
  selected: string | null;
  onSelectState: (abbr: string) => void;
  /** rendered under the map; the caller owns the wording */
  footnote?: React.ReactNode;
}

export function HexCartogram({ wyoming, districtResults, selected, onSelectState, footnote }: Props) {
  const [cg, setCg] = useState<Cartogram | null>(null);
  const [err, setErr] = useState(false);
  const [hover, setHover] = useState<HoverInfo | null>(null);
  const [width, setWidth] = useState(1000);
  const boxRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const [zt, setZt] = useState<d3.ZoomTransform>(d3.zoomIdentity);

  useEffect(() => {
    let live = true;
    loadCartogram(wyoming)
      .then(c => { if (live) { setCg(c); setErr(false); } })
      .catch(() => { if (live) setErr(true); });
    return () => { live = false; };
  }, [wyoming]);

  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setWidth(e.contentRect.width || 1000));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const electedByDistrict = useMemo(() => {
    const out: Record<string, string[]> = {};
    for (const rows of Object.values(districtResults)) {
      for (const d of rows) out[d.districtId] = d.elected;
    }
    return out;
  }, [districtResults]);

  const districtById = useMemo(() => {
    const out: Record<string, DistrictResult> = {};
    for (const rows of Object.values(districtResults)) for (const d of rows) out[d.districtId] = d;
    return out;
  }, [districtResults]);

  // Fills: seats of one party in one state merge into a single path, so a scenario
  // change rewrites ten paths per state rather than one per seat.
  const fills = useMemo(() => {
    if (!cg) return [];
    return cg.states.map(st => {
      const parties = seatParties(st, electedByDistrict, F5_ORDER);
      const byParty = new Map<string, string[]>();
      parties.forEach((p, i) => {
        const key = p ?? '';
        const at = byParty.get(key);
        if (at) at.push(st.seatPaths[i]); else byParty.set(key, [st.seatPaths[i]]);
      });
      return { abbr: st.abbr, groups: [...byParty].map(([p, ds]) => ({ party: p, d: ds.join('') })) };
    });
  }, [cg, electedByDistrict]);

  const tiles = useMemo(() => {
    if (!cg) return null;
    const b = cg.bbox;
    const pad = cg.meta.R * 1.2;
    return { x: b.x0 - pad, y: b.y0 - pad, w: b.x1 - b.x0 + 2 * pad, h: b.y1 - b.y0 + 2 * pad };
  }, [cg]);

  // Label size is pinned in screen pixels and converted back to map units, because
  // legibility is a property of the reader's screen, not of the cartogram's extent.
  const labelUnits = tiles ? (LABEL_PX * tiles.w) / width : 1;
  const labels = useMemo(
    () => (cg && tiles ? placeLabels(cg, labelUnits) : []),
    [cg, tiles, labelUnits],
  );

  // Labels are placed against the tiles and can land outside them — Massachusetts sits
  // past Cape Cod — so the frame is widened afterwards to keep every one on screen.
  const view = useMemo(() => {
    if (!tiles) return null;
    const m = labelUnits * 0.6;
    let [x0, y0, x1, y1] = [tiles.x, tiles.y, tiles.x + tiles.w, tiles.y + tiles.h];
    for (const l of labels) {
      x0 = Math.min(x0, l.box[0] - m); y0 = Math.min(y0, l.box[1] - m);
      x1 = Math.max(x1, l.box[2] + m); y1 = Math.max(y1, l.box[3] + m);
    }
    return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
  }, [tiles, labels, labelUnits]);

  // d3-zoom in viewBox units: d3.pointer inverts the screen CTM, so an SVG with a
  // viewBox reports user-space coordinates and the extent below is in the same space.
  useEffect(() => {
    if (!svgRef.current || !view) return;
    const z = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, 14])
      .extent([[view.x, view.y], [view.x + view.w, view.y + view.h]])
      .translateExtent([[view.x, view.y], [view.x + view.w, view.y + view.h]])
      .on('zoom', e => setZt(e.transform));
    zoomRef.current = z;
    d3.select(svgRef.current).call(z).on('dblclick.zoom', null);
  }, [view]);

  const zoomTo = useCallback((box: { x0: number; y0: number; x1: number; y1: number } | null) => {
    if (!svgRef.current || !zoomRef.current || !view) return;
    const sel = d3.select(svgRef.current).transition().duration(500);
    if (!box) { sel.call(zoomRef.current.transform, d3.zoomIdentity); return; }
    const k = Math.min(10, 0.82 / Math.max((box.x1 - box.x0) / view.w, (box.y1 - box.y0) / view.h));
    const cx = (box.x0 + box.x1) / 2, cy = (box.y0 + box.y1) / 2;
    sel.call(zoomRef.current.transform, d3.zoomIdentity
      .translate(view.x + view.w / 2, view.y + view.h / 2).scale(k).translate(-cx, -cy));
  }, [view]);

  useEffect(() => {
    if (!cg) return;
    zoomTo(selected ? (cg.byAbbr[selected]?.bbox ?? null) : null);
  }, [selected, cg, zoomTo]);

  if (err) return <p className="text-xs text-muted-foreground italic py-8 text-center">Could not load the seat cartogram.</p>;
  if (!cg || !view) return <div className="py-24 text-center text-sm text-muted-foreground">Loading the seat map…</div>;

  const pxPerUnit = width / view.w;
  const rPx = cg.meta.R * pxPerUnit;
  // Zooming makes the hexes bigger, so the lines have to grow with them or the borders
  // thin out to nothing against a much larger tile. Square-rooted and capped: matching
  // the zoom outright would have a district line swallow the seats it separates.
  const boost = Math.min(2.6, Math.sqrt(zt.k));
  const wSeat = Math.max(MIN_SEAT, W_SEAT_R * rPx) * boost;
  const wDistrict = Math.max(MIN_DISTRICT, W_DISTRICT_R * rPx) * boost;
  const wCasing = wDistrict * CASING_RATIO;
  const wStateBase = Math.max(MIN_STATE, W_STATE_R * rPx) * boost;
  // Labels live inside the zoom transform, so undo it to hold their on-screen size.
  const labelSize = labelUnits / zt.k;

  const hoverDistrict = hover ? districtById[hover.districtId] : undefined;

  return (
    <div className="space-y-2">
      <div ref={boxRef} className="relative rounded-lg bg-white border border-border" aria-label="House seat cartogram" role="img">
        {hover && hoverDistrict && (
          <div
            className="absolute z-10 bg-white border border-border rounded px-2 py-1 text-xs text-foreground shadow-sm pointer-events-none"
            style={{ left: Math.min(hover.x + 12, width - 260), top: hover.y - 8 }}
            role="status"
            aria-live="polite"
          >
            <span className="font-semibold">{hover.abbr} · District {hover.districtId}</span>
            {' — '}{hoverDistrict.seatCount} seat{hoverDistrict.seatCount === 1 ? '' : 's'}
            <div className="flex flex-wrap gap-1 mt-1">
              {F5_ORDER.filter(p => hoverDistrict.elected.includes(p)).map(p => (
                <span key={p} className="px-1 rounded text-[10px] font-bold text-white"
                  style={{ backgroundColor: PARTY_COLORS[p] ?? '#6b7280' }}
                  title={PARTY_NAMES[p]}>
                  {p} {hoverDistrict.elected.filter(x => x === p).length}
                </span>
              ))}
            </div>
          </div>
        )}
        <div className="absolute top-2 right-2 z-10 flex gap-1">
          <Button onClick={() => svgRef.current && zoomRef.current
            && d3.select(svgRef.current).transition().duration(250).call(zoomRef.current.scaleBy, 1.5)}
            variant="secondary" size="icon" className="h-7 w-7" title="Zoom in" aria-label="Zoom in">+</Button>
          <Button onClick={() => svgRef.current && zoomRef.current
            && d3.select(svgRef.current).transition().duration(250).call(zoomRef.current.scaleBy, 1 / 1.5)}
            variant="secondary" size="icon" className="h-7 w-7" title="Zoom out" aria-label="Zoom out">−</Button>
          <Button onClick={() => zoomTo(null)} variant="secondary" size="sm" className="px-2 h-7"
            title="Reset zoom" aria-label="Reset zoom">US</Button>
        </div>
        <svg
          ref={svgRef}
          viewBox={`${view.x} ${view.y} ${view.w} ${view.h}`}
          style={{ width: '100%', height: 'auto', display: 'block', cursor: 'grab' }}
          onMouseLeave={() => setHover(null)}
        >
          <defs>
            {cg.states.filter(s => s.clip).map(s => (
              <clipPath key={s.abbr} id={`hexclip-${s.abbr}`}><path d={s.outline} /></clipPath>
            ))}
          </defs>

          <g transform={`translate(${zt.x},${zt.y}) scale(${zt.k})`}>
          {cg.states.map((st, i) => (
            <StateTiles
              key={st.abbr}
              st={st}
              groups={fills[i].groups}
              dim={selected !== null && selected !== st.abbr}
              wSeat={wSeat} wDistrict={wDistrict} wCasing={wCasing}
              onHover={(districtId, e) => {
                const r = boxRef.current?.getBoundingClientRect();
                setHover({ districtId, abbr: st.abbr, x: e.clientX - (r?.left ?? 0), y: e.clientY - (r?.top ?? 0) });
              }}
              onLeave={() => setHover(null)}
              onClick={() => onSelectState(st.abbr)}
            />
          ))}

          {/* State outlines last and unclipped: clipping them would halve the stroke. */}
          <g fill="none" stroke={C_STATE} strokeLinejoin="round" strokeLinecap="round" pointerEvents="none">
            {cg.states.map(st => (
              <path
                key={st.abbr}
                d={st.outline}
                strokeWidth={wStateBase * stateTaper(st.seatCount) * (selected === st.abbr ? 1.9 : 1)}
                opacity={selected !== null && selected !== st.abbr ? 0.35 : 1}
                vectorEffect="non-scaling-stroke"
              />
            ))}
          </g>

          <g pointerEvents="none">
            {labels.map(l => (
              <g key={l.abbr} opacity={selected !== null && selected !== l.abbr ? 0.4 : 1}>
                {l.leader && (
                  <line x1={l.leader[0]} y1={l.leader[1]} x2={l.leader[2]} y2={l.leader[3]}
                    stroke="#94a3b8" strokeWidth={Math.max(0.6, wStateBase * 0.4)} vectorEffect="non-scaling-stroke" />
                )}
                <text
                  x={l.x} y={l.y}
                  textAnchor={l.anchor}
                  dominantBaseline={l.baseline === 'auto' ? undefined : l.baseline}
                  fontSize={labelSize}
                  style={{ fontWeight: 700, fill: '#334155', paintOrder: 'stroke' }}
                  stroke="#ffffff" strokeWidth={labelSize * 0.22} strokeLinejoin="round"
                >
                  {l.abbr}
                </text>
              </g>
            ))}
          </g>
          </g>
        </svg>
      </div>
      <p className="text-[11px] text-muted-foreground">
        {footnote}
        {footnote ? ' ' : ''}
        Cartogram concept and state outlines:{' '}
        <a href="https://the-db.co/maps" target="_blank" rel="noreferrer" className="underline">
          Congressional District Hexmap
        </a>{' '}by Daniel Donner for The Downballot, CC BY 4.0.
      </p>
    </div>
  );
}

/** One state: fills, seat lines, district casing and district lines, all clipped to it. */
function StateTiles({ st, groups, dim, wSeat, wDistrict, wCasing, onHover, onLeave, onClick }: {
  st: StateGeometry;
  groups: { party: string; d: string }[];
  dim: boolean;
  wSeat: number; wDistrict: number; wCasing: number;
  onHover: (districtId: string, e: React.MouseEvent) => void;
  onLeave: () => void;
  onClick: () => void;
}) {
  const clip = st.clip ? `url(#hexclip-${st.abbr})` : undefined;
  return (
    <g clipPath={clip} opacity={dim ? 0.34 : 1} onClick={onClick} style={{ cursor: 'pointer' }}>
      <g>
        {groups.map(g => (
          <path key={g.party || 'none'} d={g.d} fill={g.party ? (PARTY_COLORS[g.party] ?? '#6b7280') : C_EMPTY} />
        ))}
      </g>
      <path d={st.seatEdges} fill="none" stroke={C_SEAT} strokeWidth={wSeat}
        strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
      <path d={st.districtEdges} fill="none" stroke={C_SEAT} strokeWidth={wCasing}
        strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
      <path d={st.districtEdges} fill="none" stroke={C_DISTRICT} strokeWidth={wDistrict}
        strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
      {/* Transparent hit targets last so hover reads the district under the cursor. */}
      <g fill="transparent">
        {st.districts.map((did, i) => (
          <path key={did} d={st.districtPaths[i]}
            onMouseMove={e => onHover(did, e)} onMouseLeave={onLeave} />
        ))}
      </g>
    </g>
  );
}

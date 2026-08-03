import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import * as d3 from 'd3';
import { Button } from '@/components/ui/button';
import {
  loadCartogram, placeLabels,
  type Cartogram, type CartogramBasis, type StateGeometry,
} from '../../lib/hexCartogram';

/**
 * The shell every state-level hex cartogram shares: loading, zoom, label placement, state
 * outlines and the tile fills. Callers supply only the colours and the words.
 *
 * Extracted so the presidency and the primary cannot drift apart. Both draw the same
 * country from the same population tiling and differ only in what a tile means, and the
 * ~200 lines of d3 and label geometry below were not worth two copies of.
 *
 * Cartogram concept and state outlines: Congressional District Hexmap by Daniel Donner
 * for The Downballot (https://the-db.co/maps), CC BY 4.0.
 */

// Stroke calibration carried over from the House map so every map reads as one family.
const W_SEAT_R = 0.0284, W_STATE_R = 0.193;
const MIN_SEAT = 0.55, MIN_STATE = 1.45;
const C_SEAT = '#c2ccd8', C_STATE = '#0b1220';
const LABEL_PX = 11;

/** Tallest the map may get, as a share of the viewport, so it fits a laptop screen. */
const MAX_MAP_VH = 68;

/** A fixed heavy stroke is wider than Alaska's panhandle, so taper the outline by size. */
const stateTaper = (tiles: number) => Math.min(1, Math.max(0.4, Math.sqrt(tiles / 10)));

/** Tile groups for one state: a merged path per party, so a recolour rewrites a few paths. */
export interface StateFill {
  abbr: string;
  groups: { party: string; d: string; color: string }[];
}

interface Props {
  basis: CartogramBasis;
  /** one entry per state; states absent from this list draw as empty tiles */
  fills: (cg: Cartogram) => StateFill[];
  /** left column: totals, or the hovered state's breakdown */
  sidebar: (hoveredAbbr: string | null) => ReactNode;
  /** floating panel beside the cursor */
  tooltip: (hoveredAbbr: string) => ReactNode;
  footnote: ReactNode;
  ariaLabel: string;
  /** shown while the tiling loads and if it fails */
  subject: string;
}

export function HexStateCartogram({ basis, fills, sidebar, tooltip, footnote, ariaLabel, subject }: Props) {
  // Keyed by basis rather than cleared on change: switching views swaps the tiling, and a
  // frame drawn with the previous country and the new fills would be wrong, not just stale.
  const [loaded, setLoaded] = useState<{ basis: CartogramBasis; cg: Cartogram } | null>(null);
  const [err, setErr] = useState(false);
  const cg = loaded?.basis === basis ? loaded.cg : null;
  const [hover, setHover] = useState<{ abbr: string; x: number; y: number } | null>(null);
  const [width, setWidth] = useState(1000);
  const boxRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const [zt, setZt] = useState<d3.ZoomTransform>(d3.zoomIdentity);

  useEffect(() => {
    let live = true;
    loadCartogram(basis)
      .then(c => { if (live) { setLoaded({ basis, cg: c }); setErr(false); } })
      .catch(() => { if (live) setErr(true); });
    return () => { live = false; };
  }, [basis]);

  useEffect(() => {
    const el = boxRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => setWidth(e.contentRect.width || 1000));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const stateFills = useMemo(() => (cg ? fills(cg) : []), [cg, fills]);
  const fillByAbbr = useMemo(
    () => Object.fromEntries(stateFills.map(f => [f.abbr, f])),
    [stateFills],
  );

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

  // d3-zoom in viewBox units: d3.pointer inverts the screen CTM, so an SVG with a viewBox
  // reports user-space coordinates and the extent below is in the same space.
  useEffect(() => {
    if (!svgRef.current || !view) return;
    const z = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, 14])
      .extent([[view.x, view.y], [view.x + view.w, view.y + view.h]])
      .translateExtent([[view.x, view.y], [view.x + view.w, view.y + view.h]])
      // Plain wheel scrolls the page. The map is tall enough to fill a laptop viewport,
      // and swallowing the wheel there traps the reader: they try to scroll away and zoom
      // instead. Ctrl/⌘+wheel still zooms, which is what a trackpad pinch sends too.
      .filter(e => e.type !== 'wheel' || (e as WheelEvent).ctrlKey || (e as WheelEvent).metaKey)
      .on('zoom', e => setZt(e.transform));
    zoomRef.current = z;
    d3.select(svgRef.current).call(z).on('dblclick.zoom', null);
  }, [view]);

  const resetZoom = useCallback(() => {
    if (!svgRef.current || !zoomRef.current) return;
    d3.select(svgRef.current).transition().duration(500)
      .call(zoomRef.current.transform, d3.zoomIdentity);
  }, []);

  if (err) return <p className="text-xs text-muted-foreground italic py-8 text-center">Could not load the {subject}.</p>;
  if (!cg || !view) return <div className="py-24 text-center text-sm text-muted-foreground">Loading the {subject}…</div>;

  const pxPerUnit = width / view.w;
  const rPx = cg.meta.R * pxPerUnit;
  // Zooming makes the tiles bigger, so the lines have to grow with them or the borders
  // thin out against a much larger tile. Square-rooted and capped.
  const boost = Math.min(2.6, Math.sqrt(zt.k));
  const wSeat = Math.max(MIN_SEAT, W_SEAT_R * rPx) * boost;
  const wStateBase = Math.max(MIN_STATE, W_STATE_R * rPx) * boost;
  // Labels live inside the zoom transform, so undo it to hold their on-screen size.
  const labelSize = labelUnits / zt.k;
  // Bound the height rather than the width: capping the *container* keeps `width`
  // truthful, where a max-height on the SVG would letterbox the drawing while the box
  // stayed full width and every stroke sized from px-per-unit would come out wrong.
  const maxW = `${(MAX_MAP_VH * view.w) / view.h}vh`;

  return (
    <div className="flex flex-col md:flex-row gap-4">
      <div className="shrink-0 md:w-44 md:pt-1">{sidebar(hover?.abbr ?? null)}</div>

      <div className="flex-1 min-w-0">
        <div className="mx-auto w-full" style={{ maxWidth: maxW }}>
          <div ref={boxRef} className="relative rounded-lg bg-white border border-border"
            aria-label={ariaLabel} role="img">
            {hover && (
              <div className="absolute z-10 bg-white border border-border rounded px-2 py-1 text-xs text-foreground shadow-sm pointer-events-none"
                style={{ left: Math.min(hover.x + 12, width - 220), top: hover.y - 8 }}
                role="status" aria-live="polite">
                {tooltip(hover.abbr)}
              </div>
            )}
            <div className="absolute top-2 right-2 z-10 flex gap-1">
              <Button onClick={() => svgRef.current && zoomRef.current
                && d3.select(svgRef.current).transition().duration(250).call(zoomRef.current.scaleBy, 1.5)}
                variant="secondary" size="icon" className="h-7 w-7" title="Zoom in" aria-label="Zoom in">+</Button>
              <Button onClick={() => svgRef.current && zoomRef.current
                && d3.select(svgRef.current).transition().duration(250).call(zoomRef.current.scaleBy, 1 / 1.5)}
                variant="secondary" size="icon" className="h-7 w-7" title="Zoom out" aria-label="Zoom out">−</Button>
              <Button onClick={resetZoom} variant="secondary" size="sm" className="px-2 h-7"
                title="Reset zoom" aria-label="Reset zoom">US</Button>
            </div>
            <svg ref={svgRef} viewBox={`${view.x} ${view.y} ${view.w} ${view.h}`}
              style={{ width: '100%', height: 'auto', display: 'block', cursor: 'grab' }}
              onMouseLeave={() => setHover(null)}>
              <defs>
                {cg.states.filter(s => s.clip).map(s => (
                  <clipPath key={s.abbr} id={`hsc-${basis}-${s.abbr}`}><path d={s.outline} /></clipPath>
                ))}
              </defs>

              <g transform={`translate(${zt.x},${zt.y}) scale(${zt.k})`}>
                {cg.states.map(st => (
                  <StateTiles key={st.abbr} st={st} basis={basis}
                    groups={fillByAbbr[st.abbr]?.groups ?? []} wSeat={wSeat}
                    dim={hover !== null && hover.abbr !== st.abbr}
                    onHover={e => {
                      const r = boxRef.current?.getBoundingClientRect();
                      setHover({ abbr: st.abbr, x: e.clientX - (r?.left ?? 0), y: e.clientY - (r?.top ?? 0) });
                    }}
                    onLeave={() => setHover(null)} />
                ))}

                {/* Outlines last and unclipped: clipping them would halve the stroke. */}
                <g fill="none" stroke={C_STATE} strokeLinejoin="round" strokeLinecap="round" pointerEvents="none">
                  {cg.states.map(st => (
                    <path key={st.abbr} d={st.outline}
                      strokeWidth={wStateBase * stateTaper(st.seatCount) * (hover?.abbr === st.abbr ? 1.9 : 1)}
                      opacity={hover !== null && hover.abbr !== st.abbr ? 0.35 : 1}
                      vectorEffect="non-scaling-stroke" />
                  ))}
                </g>

                <g pointerEvents="none">
                  {labels.map(l => (
                    <g key={l.abbr} opacity={hover !== null && hover.abbr !== l.abbr ? 0.4 : 1}>
                      {l.leader && (
                        <line x1={l.leader[0]} y1={l.leader[1]} x2={l.leader[2]} y2={l.leader[3]}
                          stroke="#94a3b8" strokeWidth={Math.max(0.6, wStateBase * 0.4)} vectorEffect="non-scaling-stroke" />
                      )}
                      <text x={l.x} y={l.y} textAnchor={l.anchor}
                        dominantBaseline={l.baseline === 'auto' ? undefined : l.baseline}
                        fontSize={labelSize}
                        style={{ fontWeight: 700, fill: '#334155', paintOrder: 'stroke' }}
                        stroke="#ffffff" strokeWidth={labelSize * 0.22} strokeLinejoin="round">
                        {l.abbr}
                      </text>
                    </g>
                  ))}
                </g>
              </g>
            </svg>
          </div>
          <p className="text-[11px] text-muted-foreground mt-2">
            {footnote}{' '}
            Cartogram concept and state outlines:{' '}
            <a href="https://the-db.co/maps" target="_blank" rel="noreferrer" className="underline">
              Congressional District Hexmap
            </a>{' '}by Daniel Donner for The Downballot, CC BY 4.0.
          </p>
        </div>
      </div>
    </div>
  );
}

/** One state: tile fills and the hex texture, clipped to the state outline. */
function StateTiles({ st, basis, groups, wSeat, dim, onHover, onLeave }: {
  st: StateGeometry;
  basis: CartogramBasis;
  groups: { party: string; d: string; color: string }[];
  wSeat: number;
  dim: boolean;
  onHover: (e: React.MouseEvent) => void;
  onLeave: () => void;
}) {
  const clip = st.clip ? `url(#hsc-${basis}-${st.abbr})` : undefined;
  return (
    <g clipPath={clip} opacity={dim ? 0.45 : 1} style={{ cursor: 'pointer' }}>
      <g>
        {groups.map(g => <path key={g.party || 'none'} d={g.d} fill={g.color} />)}
      </g>
      {/* Tile boundaries give the hex texture; there are no districts in these maps. */}
      <path d={st.seatEdges} fill="none" stroke={C_SEAT} strokeWidth={wSeat}
        strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
      <g fill="transparent">
        {st.districtPaths.map((d, i) => (
          <path key={i} d={d} onMouseMove={onHover} onMouseLeave={onLeave} />
        ))}
      </g>
    </g>
  );
}

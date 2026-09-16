import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as d3 from 'd3';
import { Button } from '@/components/ui/button';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER } from '../../constants/parties';
import { loadMmpCartogram, type MmpCartogram, type MmpTierGeometry } from '../../lib/hexMmpCartogram';
import { CARD_HINT, FOOTNOTE } from '../../constants/typography';

/**
 * Every state twice, once per MMP tier: the seats it elects in its real congressional
 * districts, and the seats it elects statewide to top the delegation up. Each copy is
 * about 0.71 of the state's width, so the two together cover the area the single state
 * covers on the House map and one hexagon is still one seat at the same size.
 *
 * The districted copy's seats are separated by district lines, because each of them *is*
 * a district. The top-off copy's are separated by seat lines, because they are seats of
 * one statewide contest.
 */

const W_SEAT_R = 0.0284, W_DISTRICT_R = 0.265, W_STATE_R = 0.193;
const MIN_SEAT = 0.55, MIN_DISTRICT = 1.4, MIN_STATE = 1.2;
const DISTRICT_EMPHASIS = 0.55;
const W_SEAM = 0.5;

const C_SEAT = '#c2ccd8', C_CASING = '#ffffff', C_DISTRICT = '#111827', C_STATE = '#0b1220';
const C_EMPTY = '#e2e8f0', C_MUTED = '#e7ecf2';

/** Tallest the map may get, as a share of the viewport. */
const MAX_MAP_VH = 68;

interface Props {
  wyoming: 'double' | 'triple';
  /** winner per real district id, e.g. "06-12" */
  districtWinner: Record<string, string>;
  /** party → top-off seats, per state FIPS */
  topoffByState: Record<string, Record<string, number>>;
  /** parties to keep lit; empty means every seat shows its own colour */
  highlight?: ReadonlySet<string>;
  footnote?: React.ReactNode;
  toolbar?: React.ReactNode;
}

export function MmpMap({ wyoming, districtWinner, topoffByState, highlight, footnote, toolbar }: Props) {
  const [cg, setCg] = useState<MmpCartogram | null>(null);
  const [err, setErr] = useState(false);
  const [hover, setHover] = useState<{ label: string; parties: string[]; x: number; y: number } | null>(null);
  const [width, setWidth] = useState(1000);
  const boxRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const [zt, setZt] = useState<d3.ZoomTransform>(d3.zoomIdentity);

  useEffect(() => {
    let live = true;
    loadMmpCartogram(wyoming)
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

  /** Party per seat, per copy. The top-off tier has no districts, so its winners are
   *  dealt in F5 order and read left to right the way a district's seats do. */
  const fills = useMemo(() => {
    if (!cg) return [];
    const rank = new Map<string, number>(F5_ORDER.map((p, i) => [p as string, i]));
    return cg.states.map(st => st.tiers.map(t => {
      if (t.kind === 'district') return t.seats.map(d => districtWinner[d] ?? '');
      const counts = topoffByState[st.fips] ?? {};
      const dealt: string[] = [];
      for (const p of [...F5_ORDER].sort((a, b) => (rank.get(a) ?? 0) - (rank.get(b) ?? 0))) {
        for (let i = 0; i < (counts[p] ?? 0); i++) dealt.push(p);
      }
      return t.seats.map((_, i) => dealt[i] ?? '');
    }));
  }, [cg, districtWinner, topoffByState]);

  const view = useMemo(() => {
    if (!cg) return null;
    const pad = cg.meta.R * 1.4;
    const b = cg.bbox;
    return { x: b.x0 - pad, y: b.y0 - pad, w: b.x1 - b.x0 + 2 * pad, h: b.y1 - b.y0 + 2 * pad };
  }, [cg]);

  useEffect(() => {
    if (!svgRef.current || !view) return;
    const z = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, 14])
      .extent([[view.x, view.y], [view.x + view.w, view.y + view.h]])
      .translateExtent([[view.x, view.y], [view.x + view.w, view.y + view.h]])
      // A plain wheel scrolls the page; the map is tall enough to fill a laptop viewport
      // and swallowing the wheel there traps the reader.
      .filter(e => e.type !== 'wheel' || (e as WheelEvent).ctrlKey || (e as WheelEvent).metaKey)
      .on('zoom', e => setZt(e.transform));
    zoomRef.current = z;
    d3.select(svgRef.current).call(z).on('dblclick.zoom', null);
  }, [view]);

  const reset = useCallback(() => {
    if (svgRef.current && zoomRef.current) {
      d3.select(svgRef.current).transition().duration(400)
        .call(zoomRef.current.transform, d3.zoomIdentity);
    }
  }, []);

  if (err) return <p className={CARD_HINT}>The MMP map could not be loaded.</p>;
  if (!cg || !view) return <div className="h-64" aria-busy="true" />;

  const rPx = (cg.meta.R * width) / view.w;
  const boost = Math.min(2.6, Math.sqrt(zt.k));
  const wSeat = Math.max(MIN_SEAT, W_SEAT_R * rPx) * boost;
  const wDistrict = Math.max(MIN_DISTRICT, W_DISTRICT_R * rPx) * boost * DISTRICT_EMPHASIS;
  const wState = Math.max(MIN_STATE, W_STATE_R * rPx) * boost;
  const maxW = `${(MAX_MAP_VH * view.w) / view.h}vh`;

  const paint = (party: string) => {
    const lit = !highlight?.size || highlight.has(party);
    return !party ? C_EMPTY : lit ? (PARTY_COLORS[party] ?? '#6b7280') : C_MUTED;
  };

  return (
    <div className="space-y-2 mx-auto w-full" style={{ maxWidth: maxW }}>
      {toolbar && <div className="flex justify-end">{toolbar}</div>}
      <div ref={boxRef} className="relative rounded-lg bg-white border border-border"
        aria-label="MMP seat cartogram, each state drawn once per tier" role="img">
        {hover && (
          <div className="absolute z-10 bg-white border border-border rounded px-2 py-1 text-xs
            text-foreground shadow-sm pointer-events-none"
            style={{ left: Math.min(hover.x + 12, width - 240), top: hover.y - 8 }}
            role="status" aria-live="polite">
            <span className="font-semibold">{hover.label}</span>
            <div className="flex flex-wrap gap-1 mt-1">
              {F5_ORDER.filter(p => hover.parties.includes(p)).map(p => (
                <span key={p} className="px-1 rounded text-3xs font-bold text-white"
                  style={{ backgroundColor: PARTY_COLORS[p] ?? '#6b7280' }} title={PARTY_NAMES[p]}>
                  {p} {hover.parties.filter(x => x === p).length}
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
          <Button onClick={reset} variant="secondary" size="sm" className="px-2 h-7"
            title="Reset zoom" aria-label="Reset zoom">US</Button>
        </div>
        <svg ref={svgRef} viewBox={`${view.x} ${view.y} ${view.w} ${view.h}`}
          style={{ width: '100%', height: 'auto', display: 'block', cursor: 'grab' }}
          onMouseLeave={() => setHover(null)}>
          <defs>
            {cg.states.flatMap(st => st.tiers.map(t => (
              <clipPath key={`${st.abbr}-${t.kind}`} id={`mmpclip-${st.abbr}-${t.kind}`}>
                <path d={t.outline} />
              </clipPath>
            )))}
          </defs>
          <g transform={`translate(${zt.x},${zt.y}) scale(${zt.k})`}>
            {cg.states.map((st, si) => st.tiers.map((t, ti) => (
              <Copy key={`${st.abbr}-${t.kind}`}
                abbr={st.abbr} tier={t} parties={fills[si][ti]}
                wSeat={wSeat} wDistrict={wDistrict} wState={wState} paint={paint}
                onHover={(label, parties, e) => {
                  const r = boxRef.current?.getBoundingClientRect();
                  setHover({ label, parties, x: e.clientX - (r?.left ?? 0), y: e.clientY - (r?.top ?? 0) });
                }}
                onLeave={() => setHover(null)} />
            )))}
          </g>
        </svg>
      </div>
      <p className={FOOTNOTE}>
        {footnote}{footnote ? ' ' : ''}
        Cartogram concept and state outlines:{' '}
        <a href="https://the-db.co/maps" target="_blank" rel="noreferrer" className="underline">
          Congressional District Hexmap
        </a>{' '}by Daniel Donner for The Downballot, CC BY 4.0.
      </p>
    </div>
  );
}

/** One copy of one state: its seats, their boundaries, and its own border. */
function Copy({ abbr, tier, parties, wSeat, wDistrict, wState, paint, onHover, onLeave }: {
  abbr: string;
  tier: MmpTierGeometry;
  parties: string[];
  wSeat: number; wDistrict: number; wState: number;
  paint: (party: string) => string;
  onHover: (label: string, parties: string[], e: React.MouseEvent) => void;
  onLeave: () => void;
}) {
  const label = `${abbr} · ${tier.kind === 'district' ? 'districts' : 'statewide top-off'}`;
  // A seat of the districted tier is a district in its own right, so its boundaries get
  // the district line; the top-off tier's seats share one statewide contest.
  const isDistrictTier = tier.kind === 'district';
  return (
    <g onMouseMove={e => onHover(label, parties.filter(Boolean), e)} onMouseLeave={onLeave}
      style={{ cursor: 'pointer' }}>
      <g clipPath={`url(#mmpclip-${abbr}-${tier.kind})`}>
        {tier.seatPaths.map((d, k) => (
          <path key={k} d={d} fill={paint(parties[k] ?? '')}
            stroke={paint(parties[k] ?? '')} strokeWidth={wSeat * W_SEAM}
            strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
        ))}
        {isDistrictTier ? (
          <>
            <path d={tier.seatEdges} fill="none" stroke={C_CASING} strokeWidth={wDistrict * 1.6}
              strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
            <path d={tier.seatEdges} fill="none" stroke={C_DISTRICT} strokeWidth={wDistrict}
              strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
          </>
        ) : (
          <path d={tier.seatEdges} fill="none" stroke={C_SEAT} strokeWidth={wSeat}
            strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
        )}
      </g>
      <path d={tier.outline} fill="none" stroke={C_STATE} strokeWidth={wState}
        strokeDasharray={isDistrictTier ? undefined : `${wState * 3} ${wState * 2.2}`}
        strokeLinejoin="round" vectorEffect="non-scaling-stroke" pointerEvents="none" />
    </g>
  );
}

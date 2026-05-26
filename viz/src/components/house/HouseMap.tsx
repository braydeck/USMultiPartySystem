import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import * as topojson from 'topojson-client';
import type { Topology, GeometryCollection } from 'topojson-specification';
import type { DistrictResult } from '../../types';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER } from '../../constants/parties';

const W = 900;
const H = 560;

const TIER_LABELS: Record<string, string> = {
  URBAN:    'Urban',
  SUBURBAN: 'Suburban',
  RURAL:    'Rural',
};

const TIER_COLORS: Record<string, string> = {
  URBAN:    '#4f46e5',
  SUBURBAN: '#f97316',
  RURAL:    '#16a34a',
};

const US_STATES: { name: string; fips: string }[] = [
  { name: 'Alabama', fips: '01' }, { name: 'Alaska', fips: '02' },
  { name: 'Arizona', fips: '04' }, { name: 'Arkansas', fips: '05' },
  { name: 'California', fips: '06' }, { name: 'Colorado', fips: '08' },
  { name: 'Connecticut', fips: '09' }, { name: 'Delaware', fips: '10' },
  { name: 'District of Columbia', fips: '11' },
  { name: 'Florida', fips: '12' }, { name: 'Georgia', fips: '13' },
  { name: 'Hawaii', fips: '15' }, { name: 'Idaho', fips: '16' },
  { name: 'Illinois', fips: '17' }, { name: 'Indiana', fips: '18' },
  { name: 'Iowa', fips: '19' }, { name: 'Kansas', fips: '20' },
  { name: 'Kentucky', fips: '21' }, { name: 'Louisiana', fips: '22' },
  { name: 'Maine', fips: '23' }, { name: 'Maryland', fips: '24' },
  { name: 'Massachusetts', fips: '25' }, { name: 'Michigan', fips: '26' },
  { name: 'Minnesota', fips: '27' }, { name: 'Mississippi', fips: '28' },
  { name: 'Missouri', fips: '29' }, { name: 'Montana', fips: '30' },
  { name: 'Nebraska', fips: '31' }, { name: 'Nevada', fips: '32' },
  { name: 'New Hampshire', fips: '33' }, { name: 'New Jersey', fips: '34' },
  { name: 'New Mexico', fips: '35' }, { name: 'New York', fips: '36' },
  { name: 'North Carolina', fips: '37' }, { name: 'North Dakota', fips: '38' },
  { name: 'Ohio', fips: '39' }, { name: 'Oklahoma', fips: '40' },
  { name: 'Oregon', fips: '41' }, { name: 'Pennsylvania', fips: '42' },
  { name: 'Rhode Island', fips: '44' }, { name: 'South Carolina', fips: '45' },
  { name: 'South Dakota', fips: '46' }, { name: 'Tennessee', fips: '47' },
  { name: 'Texas', fips: '48' }, { name: 'Utah', fips: '49' },
  { name: 'Vermont', fips: '50' }, { name: 'Virginia', fips: '51' },
  { name: 'Washington', fips: '53' }, { name: 'West Virginia', fips: '54' },
  { name: 'Wisconsin', fips: '55' }, { name: 'Wyoming', fips: '56' },
];

interface CountyFeature extends GeoJSON.Feature<GeoJSON.Geometry> {
  id: string | number;
  properties: { name?: string } | null;
}
interface StateFeature extends GeoJSON.Feature<GeoJSON.Geometry> {
  id: string | number;
  properties: { name?: string } | null;
}

interface Props {
  districtResults: Record<string, DistrictResult[]>;
  districtCountyMap: Record<string, string[]>;
}

export function HouseMap({ districtResults, districtCountyMap }: Props) {
  const svgRef   = useRef<SVGSVGElement>(null);
  const zoomRef  = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const stateFeaturesRef = useRef<StateFeature[]>([]);
  const pathRef  = useRef<d3.GeoPath | null>(null);

  const [selectedFips, setSelectedFips] = useState('17');
  const [tooltip, setTooltip] = useState<{ text: string; x: number; y: number } | null>(null);

  const stateEntry = US_STATES.find(s => s.fips === selectedFips) ?? US_STATES[12];
  const districts  = districtResults[selectedFips] ?? [];

  // ── Initial D3 render ──────────────────────────────────────────────────────
  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const projection = d3.geoAlbersUsa().scale(W * 1.1).translate([W / 2, H / 2]);
    const path = d3.geoPath(projection);
    pathRef.current = path;

    const g = svg.append('g');

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, 16])
      .on('zoom', event => { g.attr('transform', event.transform); });
    zoomRef.current = zoom;
    svg.call(zoom).on('dblclick.zoom', null);

    fetch('/topojson/counties-10m.json')
      .then(r => r.json())
      .then((topo: Topology) => {
        type CountyTopo = GeometryCollection<{ name: string }>;
        type StateTopo  = GeometryCollection<{ name: string }>;

        const counties = topojson.feature(topo, topo.objects['counties'] as CountyTopo);
        const states   = topojson.feature(topo, topo.objects['states']   as StateTopo);
        stateFeaturesRef.current = states.features as StateFeature[];

        const topoCounties = topo.objects['counties'] as CountyTopo;
        const geomByFips: Record<string, typeof topoCounties['geometries'][0]> = {};
        for (const geom of topoCounties.geometries) {
          geomByFips[String(geom.id ?? '').padStart(5, '0')] = geom;
        }

        // ── Per-district gradient defs ───────────────────────────────────────
        const defs = svg.append('defs');
        for (const [districtId] of Object.entries(districtCountyMap)) {
          const stateFips  = districtId.split('-')[0];
          const distResult = (districtResults[stateFips] ?? []).find(d => d.districtId === districtId);
          if (!distResult || distResult.elected.length === 0) continue;

          const partyCounts: Record<string, number> = {};
          for (const p of distResult.elected) partyCounts[p] = (partyCounts[p] ?? 0) + 1;
          const total = distResult.elected.length;
          const orderedParties = F5_ORDER.filter(p => partyCounts[p]);

          const lg = defs.append('linearGradient')
            .attr('id', `dgrad-${districtId}`)
            .attr('x1', '0%').attr('x2', '100%').attr('y1', '0%').attr('y2', '0%');
          let cum = 0;
          for (const p of orderedParties) {
            const frac  = partyCounts[p] / total;
            const color = PARTY_COLORS[p] ?? '#6b7280';
            lg.append('stop').attr('offset', `${(cum * 100).toFixed(1)}%`).attr('stop-color', color).attr('stop-opacity', 0.72);
            cum += frac;
            lg.append('stop').attr('offset', `${(cum * 100).toFixed(1)}%`).attr('stop-color', color).attr('stop-opacity', 0.72);
          }
        }

        // ── Background county layer ───────────────────────────────────────────
        g.append('g').attr('class', 'county-bg')
          .selectAll<SVGPathElement, CountyFeature>('path')
          .data(counties.features as CountyFeature[])
          .join('path')
          .attr('d', d => path(d) ?? '')
          .attr('fill', '#dce6f0')
          .attr('stroke', 'none');

        // ── District filled polygons ─────────────────────────────────────────
        const distGroup = g.append('g').attr('class', 'district-fills');
        for (const [districtId, countyFips5List] of Object.entries(districtCountyMap)) {
          const distGeoms = countyFips5List
            .map(f => geomByFips[f])
            .filter((geom): geom is typeof topoCounties['geometries'][0] => !!geom);
          if (distGeoms.length === 0) continue;

          const stateFips  = districtId.split('-')[0];
          const distResult = (districtResults[stateFips] ?? []).find(d => d.districtId === districtId);
          const topParty   = distResult?.elected[0] ?? '';

          try {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const merged = topojson.merge(topo as any, distGeoms as any);
            const pathEl = distGroup.append('path')
              .datum(merged)
              .attr('d', path)
              .attr('fill', distResult ? `url(#dgrad-${districtId})` : '#e2e8f0')
              .attr('stroke', PARTY_COLORS[topParty] ?? '#94a3b8')
              .attr('stroke-width', 1.3)
              .attr('stroke-opacity', 0.85)
              .attr('stroke-linejoin', 'round')
              .attr('cursor', 'pointer');

            if (distResult) {
              const dr = distResult;
              pathEl
                .on('mousemove', function(event) {
                  const [mx, my] = d3.pointer(event, svgRef.current);
                  const pc: Record<string, number> = {};
                  for (const p of dr.elected) pc[p] = (pc[p] ?? 0) + 1;
                  const breakdown = Object.entries(pc)
                    .sort((a, b) => b[1] - a[1])
                    .map(([p, n]) => `${p}:${n}`)
                    .join(' · ');
                  setTooltip({
                    text: `District ${districtId} · ${TIER_LABELS[dr.densityTier] ?? dr.densityTier} · ${dr.seatCount} seats — ${breakdown}`,
                    x: mx, y: my,
                  });
                })
                .on('mouseleave', () => setTooltip(null));
            }
          } catch {
            // skip degenerate geometries
          }
        }

        // ── State borders ────────────────────────────────────────────────────
        g.append('path')
          .datum(topojson.mesh(topo, topo.objects['states'] as StateTopo, (a, b) => a !== b))
          .attr('d', path)
          .attr('fill', 'none')
          .attr('stroke', '#1e293b')
          .attr('stroke-width', 0.7)
          .attr('stroke-opacity', 0.55);

        // ── Transparent state click targets ──────────────────────────────────
        g.append('g').attr('class', 'state-targets')
          .selectAll<SVGPathElement, StateFeature>('path')
          .data(states.features as StateFeature[])
          .join('path')
          .attr('d', d => path(d) ?? '')
          .attr('fill', 'transparent')
          .attr('stroke', 'none')
          .attr('cursor', 'pointer')
          .on('click', function(event, d) {
            event.stopPropagation();
            const fips2 = String(d.id).padStart(2, '0');
            setSelectedFips(fips2);
            if (fips2 !== '11') zoomToFeature(svg, zoom, path, d, W, H);
          });

        // ── DC inset — fixed position, outside zoom group ────────────────────
        {
          const dcId  = '11-01';
          const dcRes = (districtResults['11'] ?? []).find(d => d.districtId === dcId);
          const ix = W - 74, iy = H - 88, bw = 62, bh = 40;

          const dcG = svg.append('g')
            .attr('class', 'dc-inset')
            .attr('cursor', 'pointer')
            .on('click', () => setSelectedFips('11'));

          // Background card
          dcG.append('rect')
            .attr('x', ix - 5).attr('y', iy - 18)
            .attr('width', bw + 10).attr('height', bh + 23)
            .attr('fill', 'white').attr('stroke', '#94a3b8').attr('stroke-width', 0.8)
            .attr('rx', 4);
          // "DC" label
          dcG.append('text')
            .attr('x', ix + bw / 2).attr('y', iy - 5)
            .attr('text-anchor', 'middle').attr('font-size', 9).attr('font-weight', '700')
            .attr('fill', '#475569').text('DC');
          // District fill rect
          dcG.append('rect')
            .attr('x', ix).attr('y', iy)
            .attr('width', bw).attr('height', bh)
            .attr('fill', dcRes ? `url(#dgrad-${dcId})` : '#e2e8f0')
            .attr('stroke', dcRes ? (PARTY_COLORS[dcRes.elected[0]] ?? '#94a3b8') : '#94a3b8')
            .attr('stroke-width', 1.2).attr('rx', 2);
          // "2 seats" sub-label
          dcG.append('text')
            .attr('x', ix + bw / 2).attr('y', iy + bh + 11)
            .attr('text-anchor', 'middle').attr('font-size', 8)
            .attr('fill', '#94a3b8').text(dcRes ? `${dcRes.seatCount} seats` : '');
        }

        // Initial zoom to IL
        const initState = (states.features as StateFeature[]).find(
          f => String(f.id).padStart(2, '0') === '17'
        );
        if (initState) zoomToFeature(svg, zoom, path, initState, W, H, true);
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Zoom when dropdown changes ────────────────────────────────────────────
  useEffect(() => {
    if (!svgRef.current || !zoomRef.current || !pathRef.current) return;
    if (selectedFips === '11') return; // DC is shown via inset, not geographic zoom
    const sf = stateFeaturesRef.current.find(f => String(f.id).padStart(2, '0') === selectedFips);
    if (sf) zoomToFeature(d3.select(svgRef.current), zoomRef.current, pathRef.current, sf, W, H);
  }, [selectedFips]);

  function handleZoom(delta: number) {
    if (!svgRef.current || !zoomRef.current) return;
    d3.select(svgRef.current).transition().duration(300).call(zoomRef.current.scaleBy, delta);
  }

  function handleResetZoom() {
    if (!svgRef.current || !zoomRef.current) return;
    d3.select(svgRef.current).transition().duration(500).call(zoomRef.current.transform, d3.zoomIdentity);
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-3 items-center">
          {Object.entries(PARTY_COLORS).map(([party, color]) => (
            <div key={party} className="flex items-center gap-1 text-xs font-semibold" style={{ color }}>
              <div className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: color }} />
              {PARTY_NAMES[party]}
            </div>
          ))}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <label className="text-xs font-semibold text-slate-500">State:</label>
          <select
            value={selectedFips}
            onChange={e => setSelectedFips(e.target.value)}
            className="text-sm border border-slate-200 rounded px-2 py-1 bg-white text-slate-800"
          >
            {US_STATES.map(s => (
              <option key={s.fips} value={s.fips}>{s.name}</option>
            ))}
          </select>
          <div className="flex gap-1">
            <button onClick={() => handleZoom(1.5)} className="w-7 h-7 rounded bg-slate-200 text-slate-700 hover:bg-slate-300 text-sm font-bold" title="Zoom in">+</button>
            <button onClick={() => handleZoom(1 / 1.5)} className="w-7 h-7 rounded bg-slate-200 text-slate-700 hover:bg-slate-300 text-sm font-bold" title="Zoom out">−</button>
            <button onClick={handleResetZoom} className="px-2 h-7 rounded bg-slate-200 text-slate-600 hover:bg-slate-300 text-xs font-medium" title="Reset zoom">US</button>
          </div>
        </div>
      </div>

      {/* Map */}
      <div className="relative rounded-lg overflow-hidden bg-slate-50 border border-slate-200">
        {tooltip && (
          <div
            className="absolute z-10 bg-white border border-slate-200 rounded px-2 py-1 text-xs text-slate-700 shadow-sm pointer-events-none"
            style={{ left: tooltip.x + 12, top: tooltip.y - 8 }}
          >
            {tooltip.text}
          </div>
        )}
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} ${H}`}
          style={{ width: '100%', height: 'auto', display: 'block', cursor: 'grab' }}
        />
        <div className="absolute bottom-2 left-2 text-xs text-slate-400 pointer-events-none">
          Click a state to zoom · scroll or +/− to zoom
        </div>
      </div>

      {/* District cards for selected state */}
      {districts.length > 0 && (() => {
        // Aggregate seat counts across all districts in the selected state
        const stateTotals: Record<string, number> = {};
        for (const d of districts) {
          for (const p of d.elected) stateTotals[p] = (stateTotals[p] ?? 0) + 1;
        }
        const stateTotal = Object.values(stateTotals).reduce((s, n) => s + n, 0);
        const orderedState = F5_ORDER.filter(p => stateTotals[p]);

        return (
        <div>
          <div className="flex items-center justify-between mb-1">
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-widest">
              STV Districts — {stateEntry.name}
            </h4>
            <span className="text-xs text-slate-400">{stateTotal} seats total</span>
          </div>

          {/* State-level summary bar */}
          <div className="mb-4">
            <div className="flex rounded overflow-hidden h-7">
              {orderedState.map(p => {
                const pct = (stateTotals[p] / stateTotal) * 100;
                return (
                  <div
                    key={p}
                    title={`${PARTY_NAMES[p] ?? p}: ${stateTotals[p]} seats (${pct.toFixed(1)}%)`}
                    className="flex items-center justify-center overflow-hidden"
                    style={{ width: `${pct}%`, backgroundColor: PARTY_COLORS[p] ?? '#6b7280', minWidth: pct < 4 ? 2 : 0 }}
                  >
                    {pct >= 8 && (
                      <span className="text-white text-xs font-bold leading-none px-0.5">
                        {p} {stateTotals[p]}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
            <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1">
              {orderedState.map(p => (
                <span key={p} className="text-xs tabular-nums" style={{ color: PARTY_COLORS[p] ?? '#6b7280' }}>
                  {p} {stateTotals[p]} ({((stateTotals[p] / stateTotal) * 100).toFixed(0)}%)
                </span>
              ))}
            </div>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {districts.map(d => {
              const tierColor = TIER_COLORS[d.densityTier] ?? '#6b7280';
              return (
                <div
                  key={d.districtId}
                  className="rounded-lg border p-3 space-y-2"
                  style={{ borderColor: tierColor + '44', backgroundColor: tierColor + '08' }}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold px-1.5 py-0.5 rounded text-white" style={{ backgroundColor: tierColor }}>
                      {TIER_LABELS[d.densityTier] ?? d.densityTier}
                    </span>
                    <span className="text-xs text-slate-400">{d.seatCount} seats · {d.nRespondents} resp.</span>
                  </div>
                  {/* Seat bar */}
                  <div className="flex rounded-sm overflow-hidden h-4">
                    {F5_ORDER.filter(p => d.elected.includes(p)).map(p => {
                      const cnt = d.elected.filter(x => x === p).length;
                      const pct = (cnt / d.seatCount) * 100;
                      return (
                        <div
                          key={p}
                          title={`${PARTY_NAMES[p] ?? p}: ${cnt}`}
                          style={{ width: `${pct}%`, backgroundColor: PARTY_COLORS[p] ?? '#6b7280' }}
                        />
                      );
                    })}
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {[...d.elected]
                      .sort((a, b) => F5_ORDER.indexOf(a as typeof F5_ORDER[number]) - F5_ORDER.indexOf(b as typeof F5_ORDER[number]))
                      .map((party, i) => (
                        <span
                          key={i}
                          className="text-xs font-bold px-1.5 py-0.5 rounded text-white"
                          style={{ backgroundColor: PARTY_COLORS[party] ?? '#6b7280' }}
                          title={PARTY_NAMES[party] ?? party}
                        >
                          {party}
                        </span>
                      ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
        );
      })()}
      {districts.length === 0 && (
        <p className="text-xs text-slate-400 italic">No district data for {stateEntry.name}.</p>
      )}

      <p className="text-xs text-slate-400">
        Each district is a geographically contiguous cluster of adjacent counties. Fill gradient shows
        proportional seat share; outline color = plurality party. Click a state to zoom in.
      </p>
    </div>
  );
}

// ── Zoom-to-feature helper ─────────────────────────────────────────────────

function zoomToFeature(
  svg: d3.Selection<SVGSVGElement, unknown, null, undefined>,
  zoom: d3.ZoomBehavior<SVGSVGElement, unknown>,
  path: d3.GeoPath,
  feature: GeoJSON.Feature,
  width: number,
  height: number,
  instant = false
) {
  const bounds = path.bounds(feature);
  if (!bounds || !isFinite(bounds[0][0])) return;
  const [[x0, y0], [x1, y1]] = bounds;
  const dx = x1 - x0, dy = y1 - y0;
  if (dx === 0 || dy === 0) return;
  const scale = Math.min(10, 0.88 / Math.max(dx / width, dy / height));
  const tx    = (width  - scale * (x0 + x1)) / 2;
  const ty    = (height - scale * (y0 + y1)) / 2;
  const transform = d3.zoomIdentity.translate(tx, ty).scale(scale);
  if (instant) {
    svg.call(zoom.transform, transform);
  } else {
    svg.transition().duration(650).call(zoom.transform, transform);
  }
}

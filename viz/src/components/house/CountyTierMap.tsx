import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import * as topojson from 'topojson-client';
import type { Topology, GeometryCollection } from 'topojson-specification';
import type { DistrictResult } from '../../types';
import { PARTY_COLORS, PARTY_NAMES, getContrastText } from '../../constants/parties';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

const W = 900;
const H = 560;

const TIER_COLORS: Record<string, string> = {
  URBAN:    '#4f46e5',
  SUBURBAN: '#f97316',
  RURAL:    '#16a34a',
};

const TIER_LABELS: Record<string, string> = {
  URBAN:    'Urban (Metro Core)',
  SUBURBAN: 'Suburban',
  RURAL:    'Rural',
};


const US_STATES: { name: string; fips: string }[] = [
  { name: 'Alabama', fips: '01' }, { name: 'Alaska', fips: '02' },
  { name: 'Arizona', fips: '04' }, { name: 'Arkansas', fips: '05' },
  { name: 'California', fips: '06' }, { name: 'Colorado', fips: '08' },
  { name: 'Connecticut', fips: '09' }, { name: 'Delaware', fips: '10' },
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
  countyTiers: Record<string, string>;
  districtResults: Record<string, DistrictResult[]>;
  districtCountyMap: Record<string, string[]>;
}

export function CountyTierMap({ countyTiers, districtResults, districtCountyMap }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const stateFeaturesRef = useRef<StateFeature[]>([]);
  const pathRef = useRef<d3.GeoPath | null>(null);

  const [selectedFips, setSelectedFips] = useState('17');
  const [tooltip, setTooltip] = useState<{ text: string; x: number; y: number } | null>(null);

  const stateEntry = US_STATES.find(s => s.fips === selectedFips) ?? US_STATES[12];
  const districts = districtResults[selectedFips] ?? [];

  // Tier distribution stats
  const tierCounts = { URBAN: 0, SUBURBAN: 0, RURAL: 0 };
  for (const v of Object.values(countyTiers)) {
    if (v in tierCounts) tierCounts[v as keyof typeof tierCounts]++;
  }

  // ── Initial D3 render ────────────────────────────────────────────────────
  useEffect(() => {
    if (!svgRef.current || Object.keys(countyTiers).length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const projection = d3.geoAlbersUsa()
      .scale(W * 1.1)
      .translate([W / 2, H / 2]);
    const path = d3.geoPath(projection);
    pathRef.current = path;

    const g = svg.append('g');

    // Zoom behavior
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, 16])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });
    zoomRef.current = zoom;
    svg.call(zoom).on('dblclick.zoom', null); // disable dblclick zoom

    fetch('/topojson/counties-10m.json')
      .then(r => r.json())
      .then((topo: Topology) => {
        type CountyTopo = GeometryCollection<{ name: string }>;
        type StateTopo  = GeometryCollection<{ name: string }>;

        const counties = topojson.feature(topo, topo.objects['counties'] as CountyTopo);
        const states   = topojson.feature(topo, topo.objects['states'] as StateTopo);
        stateFeaturesRef.current = states.features as StateFeature[];

        // ── County fill layer ─────────────────────────────────────────────
        g.append('g')
          .attr('class', 'counties')
          .selectAll<SVGPathElement, CountyFeature>('path')
          .data(counties.features as CountyFeature[])
          .join('path')
          .attr('d', d => path(d) ?? '')
          .attr('fill', d => {
            const fips5 = String(d.id).padStart(5, '0');
            const tier = countyTiers[fips5];
            return tier ? TIER_COLORS[tier] + 'cc' : '#e2e8f0';
          })
          .attr('stroke', '#fff')
          .attr('stroke-width', 0.15)
          .on('mousemove', function(event, d) {
            const fips5 = String(d.id).padStart(5, '0');
            const tier = countyTiers[fips5];
            const name = (d.properties as { name?: string })?.name ?? fips5;
            const [mx, my] = d3.pointer(event, svgRef.current);
            setTooltip({ text: `${name} — ${tier ? TIER_LABELS[tier] : 'Unknown'}`, x: mx, y: my });
          })
          .on('mouseleave', () => setTooltip(null));

        // ── District outlines: merged county groups per geographic district ──
        const topoCounties = topo.objects['counties'] as CountyTopo;

        // Build fips5 → geometry lookup for O(1) access
        const geomByFips: Record<string, typeof topoCounties['geometries'][0]> = {};
        for (const geom of topoCounties.geometries) {
          const fips5 = String(geom.id ?? '').padStart(5, '0');
          geomByFips[fips5] = geom;
        }

        const outlineGroup = g.append('g').attr('class', 'district-outlines');
        for (const [districtId, countyFips5List] of Object.entries(districtCountyMap)) {
          const distGeoms = countyFips5List
            .map(f => geomByFips[f])
            .filter((geom): geom is typeof topoCounties['geometries'][0] => !!geom);
          if (distGeoms.length === 0) continue;

          const stateFips   = districtId.split('-')[0];
          const stateDists  = districtResults[stateFips] ?? [];
          const distResult  = stateDists.find(d => d.districtId === districtId);
          const topParty    = distResult?.elected[0] ?? '';
          try {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const merged = topojson.merge(topo as any, distGeoms as any);
            outlineGroup.append('path')
              .datum(merged)
              .attr('d', path)
              .attr('fill', 'none')
              .attr('stroke', PARTY_COLORS[topParty] ?? '#64748b')
              .attr('stroke-width', 1.6)
              .attr('stroke-opacity', 0.9)
              .attr('stroke-linejoin', 'round');
          } catch {
            // skip degenerate geometries
          }
        }

        // ── State borders ─────────────────────────────────────────────────
        g.append('path')
          .datum(topojson.mesh(
            topo,
            topo.objects['states'] as StateTopo,
            (a, b) => a !== b
          ))
          .attr('d', path)
          .attr('fill', 'none')
          .attr('stroke', '#1e293b')
          .attr('stroke-width', 0.6)
          .attr('stroke-opacity', 0.5);

        // ── State click targets (transparent, for zoom-to-state) ───────────
        g.append('g')
          .attr('class', 'state-targets')
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
            zoomToFeature(svg, zoom, path, d, W, H);
          });

        // Zoom to initial selected state
        const initState = (states.features as StateFeature[]).find(
          f => String(f.id).padStart(2, '0') === '17'
        );
        if (initState) zoomToFeature(svg, zoom, path, initState, W, H, true);
      });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [countyTiers]);

  // ── Zoom when state dropdown changes ────────────────────────────────────
  useEffect(() => {
    if (!svgRef.current || !zoomRef.current || !pathRef.current) return;
    const stateFeature = stateFeaturesRef.current.find(
      f => String(f.id).padStart(2, '0') === selectedFips
    );
    if (stateFeature) {
      zoomToFeature(
        d3.select(svgRef.current),
        zoomRef.current,
        pathRef.current,
        stateFeature,
        W, H
      );
    }
  }, [selectedFips]);

  function handleZoom(delta: number) {
    if (!svgRef.current || !zoomRef.current) return;
    d3.select(svgRef.current)
      .transition().duration(300)
      .call(zoomRef.current.scaleBy, delta);
  }

  function handleResetZoom() {
    if (!svgRef.current || !zoomRef.current) return;
    d3.select(svgRef.current)
      .transition().duration(500)
      .call(zoomRef.current.transform, d3.zoomIdentity);
  }

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-4 items-center">
          {(['URBAN', 'SUBURBAN', 'RURAL'] as const).map(tier => (
            <div key={tier} className="flex items-center gap-1.5">
              <div className="w-3 h-3 rounded-sm flex-shrink-0" style={{ backgroundColor: TIER_COLORS[tier] }} />
              <span className="text-xs text-muted-foreground">
                {TIER_LABELS[tier]}
                <span className="text-muted-foreground ml-1">({tierCounts[tier].toLocaleString()})</span>
              </span>
            </div>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs font-semibold text-muted-foreground">State:</label>
          <select
            value={stateEntry.fips}
            onChange={e => setSelectedFips(e.target.value)}
            className="text-sm border border-border rounded px-2 py-1 bg-white text-foreground"
          >
            {US_STATES.map(s => (
              <option key={s.fips} value={s.fips}>{s.name}</option>
            ))}
          </select>
          {/* Zoom controls */}
          <div className="flex gap-1 ml-2">
            <Button
              onClick={() => handleZoom(1.5)}
              variant="secondary"
              size="icon"
              className="h-7 w-7"
              title="Zoom in"
              aria-label="Zoom in"
            >+</Button>
            <Button
              onClick={() => handleZoom(1 / 1.5)}
              variant="secondary"
              size="icon"
              className="h-7 w-7"
              title="Zoom out"
              aria-label="Zoom out"
            >−</Button>
            <Button
              onClick={handleResetZoom}
              variant="secondary"
              size="sm"
              className="px-2 h-7"
              title="Reset zoom"
              aria-label="Reset zoom"
            >US</Button>
          </div>
        </div>
      </div>

      {/* Map */}
      <div className="relative rounded-lg overflow-hidden bg-slate-50 border border-border" aria-label="County tier map" role="img">
        {tooltip && (
          <div
            className="absolute z-10 bg-white border border-border rounded px-2 py-1 text-xs text-foreground shadow-sm pointer-events-none"
            style={{ left: tooltip.x + 12, top: tooltip.y - 8 }}
            role="status"
            aria-live="polite"
          >
            {tooltip.text}
          </div>
        )}
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} ${H}`}
          style={{ width: '100%', height: 'auto', display: 'block', cursor: 'grab' }}
        />
        <div className="absolute bottom-2 left-2 text-xs text-muted-foreground pointer-events-none">
          Click a state to zoom in · scroll or +/− to zoom
        </div>
      </div>

      {/* District STV result cards for selected state */}
      {districts.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-2">
            STV Districts — {stateEntry.name}
          </h4>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {districts.map(d => {
              const tierColor = TIER_COLORS[d.densityTier] ?? '#6b7280';
              return (
                <Card
                  key={d.districtId}
                  className="p-3 space-y-2"
                  style={{ borderColor: tierColor + '44', backgroundColor: tierColor + '08' }}
                >
                  <div className="flex items-center justify-between">
                    <span
                      className="text-xs font-bold px-1.5 py-0.5 rounded chip-text"
                      style={{ backgroundColor: tierColor, color: getContrastText(tierColor) }}
                    >
                      {TIER_LABELS[d.densityTier]?.split(' ')[0]}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {d.seatCount} seats · {d.nRespondents} resp.
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {d.elected.map((party, i) => (
                      <span
                        key={i}
                        className="text-xs font-bold px-1.5 py-0.5 rounded chip-text"
                        style={{ backgroundColor: PARTY_COLORS[party] ?? '#6b7280', color: getContrastText(PARTY_COLORS[party] ?? '#6b7280') }}
                        title={PARTY_NAMES[party] ?? party}
                      >
                        {party}
                      </span>
                    ))}
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      )}
      {districts.length === 0 && (
        <p className="text-xs text-muted-foreground italic">No district data for {stateEntry.name}.</p>
      )}

      <p className="text-xs text-muted-foreground">
        County tiers from CDC NCHS Urban-Rural Classification (2013): Large metro core → Urban;
        medium/small metro → Suburban; micropolitan/noncore → Rural.
        District outlines show geographically contiguous multi-member districts drawn by county adjacency.
        Outline color = plurality party elected in that district.
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
  const tx = (width  - scale * (x0 + x1)) / 2;
  const ty = (height - scale * (y0 + y1)) / 2;
  const transform = d3.zoomIdentity.translate(tx, ty).scale(scale);
  if (instant) {
    svg.call(zoom.transform, transform);
  } else {
    svg.transition().duration(650).call(zoom.transform, transform);
  }
}

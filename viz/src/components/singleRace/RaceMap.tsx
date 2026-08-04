import { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import * as topojson from 'topojson-client';
import type { Topology, GeometryCollection } from 'topojson-specification';
import { Button } from '@/components/ui/button';
import type { SRState } from '../../lib/singleRace';
import { CARD_HINT } from '../../constants/typography';

const W = 900;
const H = 560;

type Feat = GeoJSON.Feature<GeoJSON.Geometry> & { id: string | number };

interface Props {
  office: 'house' | 'senate';
  states: SRState[];
  selectedFips: string;
  selectedCd: string;
  onSelectState: (fips: string) => void;
  onSelectCd: (cd: string) => void;
  /** unit id (state fips or CD id) -> light fill hex for the leading scenario's winner */
  tint: Record<string, string>;
}

export function RaceMap({ office, states, selectedFips, selectedCd, onSelectState, onSelectCd, tint }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null);
  const pathRef = useRef<d3.GeoPath | null>(null);
  const stateFeatRef = useRef<Feat[]>([]);
  const [tooltip, setTooltip] = useState<{ text: string; x: number; y: number } | null>(null);

  // Keep latest props for use inside d3 event handlers without re-running the draw effect.
  const propsRef = useRef({ office, onSelectState, onSelectCd, tint, selectedFips, selectedCd });
  propsRef.current = { office, onSelectState, onSelectCd, tint, selectedFips, selectedCd };

  // ── Draw (once per office) ──────────────────────────────────────────────────
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const projection = d3.geoAlbersUsa();
    const path = d3.geoPath(projection);
    pathRef.current = path;
    const g = svg.append('g');

    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([1, 24])
      .on('zoom', e => g.attr('transform', e.transform.toString()));
    zoomRef.current = zoom;
    svg.call(zoom).on('dblclick.zoom', null);

    let cancelled = false;
    const files = office === 'house'
      ? ['/topojson/states-10m.json', '/topojson/cd119.json']
      : ['/topojson/states-10m.json'];

    Promise.all(files.map(f => fetch(f).then(r => r.json()))).then(([statesTopo, cdTopo]) => {
      if (cancelled) return;
      const sObj = statesTopo.objects.states as GeometryCollection;
      const stateFeats = (topojson.feature(statesTopo as unknown as Topology, sObj) as unknown as { features: Feat[] }).features
        .filter(f => String(f.id).padStart(2, '0') !== '72');
      stateFeatRef.current = stateFeats;
      projection.fitSize([W, H], { type: 'FeatureCollection', features: stateFeats } as GeoJSON.FeatureCollection);

      if (office === 'house' && cdTopo) {
        const cdObjName = Object.keys(cdTopo.objects)[0];
        const cdFeats = (topojson.feature(cdTopo as unknown as Topology, cdTopo.objects[cdObjName] as GeometryCollection) as unknown as { features: Feat[] }).features;
        g.append('g').attr('class', 'cd-layer')
          .selectAll('path').data(cdFeats).join('path')
          .attr('d', path)
          .attr('data-id', d => String(d.id))
          .attr('stroke', '#fff').attr('stroke-width', 0.3)
          .style('cursor', 'pointer')
          .on('click', (_e, d) => {
            const cd = String(d.id);
            propsRef.current.onSelectCd(cd);
            propsRef.current.onSelectState(cd.split('-')[0]);
          })
          .on('mousemove', (e, d) => {
            const [x, y] = d3.pointer(e, svgRef.current);
            setTooltip({ text: String(d.id), x, y });
          })
          .on('mouseleave', () => setTooltip(null));
        // state outlines on top for context
        g.append('g').attr('class', 'state-outline')
          .selectAll('path').data(stateFeats).join('path')
          .attr('d', path).attr('fill', 'none')
          .attr('stroke', '#475569').attr('stroke-width', 0.6).attr('pointer-events', 'none');
      } else {
        g.append('g').attr('class', 'state-layer')
          .selectAll('path').data(stateFeats).join('path')
          .attr('d', path)
          .attr('data-id', d => String(d.id).padStart(2, '0'))
          .attr('stroke', '#fff').attr('stroke-width', 0.5)
          .style('cursor', 'pointer')
          .on('click', (_e, d) => propsRef.current.onSelectState(String(d.id).padStart(2, '0')))
          .on('mousemove', (e, d) => {
            const fips = String(d.id).padStart(2, '0');
            const [x, y] = d3.pointer(e, svgRef.current);
            setTooltip({ text: states.find(s => s.fips === fips)?.name ?? fips, x, y });
          })
          .on('mouseleave', () => setTooltip(null));
      }
      applyFills();
    });

    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [office]);

  // ── Fills / selection highlight ─────────────────────────────────────────────
  function applyFills() {
    const svg = d3.select(svgRef.current);
    const { office: off, tint: t, selectedFips: selF, selectedCd: selCd } = propsRef.current;
    if (off === 'house') {
      svg.selectAll<SVGPathElement, Feat>('.cd-layer path').each(function (d) {
        const id = String(d.id);
        const isSel = id === selCd;
        d3.select(this)
          .attr('fill', t[id] ?? '#e5e7eb')
          .attr('stroke', isSel ? '#0f172a' : '#fff')
          .attr('stroke-width', isSel ? 1.6 : 0.3)
          .raise();
      });
      // keep selected raised above neighbours
      svg.selectAll<SVGPathElement, Feat>('.cd-layer path').filter(d => String(d.id) === selCd).raise();
    } else {
      svg.selectAll<SVGPathElement, Feat>('.state-layer path').each(function (d) {
        const id = String(d.id).padStart(2, '0');
        const isSel = id === selF;
        d3.select(this)
          .attr('fill', t[id] ?? '#e5e7eb')
          .attr('stroke', isSel ? '#0f172a' : '#fff')
          .attr('stroke-width', isSel ? 2 : 0.5);
      });
      svg.selectAll<SVGPathElement, Feat>('.state-layer path').filter(d => String(d.id).padStart(2, '0') === selF).raise();
    }
  }

  useEffect(() => { applyFills(); });

  // ── Zoom to the selected state ──────────────────────────────────────────────
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg || !zoomRef.current || !pathRef.current) return;
    const feat = stateFeatRef.current.find(f => String(f.id).padStart(2, '0') === selectedFips);
    if (!feat) return;
    const [[x0, y0], [x1, y1]] = pathRef.current.bounds(feat);
    const dx = x1 - x0, dy = y1 - y0;
    const scale = Math.min(24, 0.85 / Math.max(dx / W, dy / H));
    const tx = W / 2 - scale * (x0 + x1) / 2;
    const ty = H / 2 - scale * (y0 + y1) / 2;
    d3.select(svg).transition().duration(650)
      .call(zoomRef.current.transform, d3.zoomIdentity.translate(tx, ty).scale(scale));
  }, [selectedFips, office]);

  function resetZoom() {
    if (!svgRef.current || !zoomRef.current) return;
    d3.select(svgRef.current).transition().duration(500).call(zoomRef.current.transform, d3.zoomIdentity);
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <p className={CARD_HINT}>
          {office === 'house'
            ? 'Click a district to run the race there. Boundaries are the current 119th-Congress districts; each result uses the CES respondents living in that district (small districts are noisier).'
            : 'Click a state to run its statewide race.'}
        </p>
        <Button variant="secondary" size="sm" onClick={resetZoom}>Reset view</Button>
      </div>
      <div className="relative rounded-lg border border-border bg-slate-50 overflow-hidden">
        <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} className="w-full h-auto" role="img" aria-label="Race selection map" />
        {tooltip && (
          <div className="absolute pointer-events-none px-2 py-1 rounded bg-slate-900 text-white text-xs font-medium shadow"
            style={{ left: tooltip.x + 12, top: tooltip.y + 12 }}>
            {tooltip.text}
          </div>
        )}
      </div>
    </div>
  );
}

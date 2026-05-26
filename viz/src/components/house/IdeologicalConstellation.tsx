import { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';
import type { ConstellationNode, TransferMatrix } from '../../types';
import { getBlendColor, FACTOR_LABELS, PARTY_COLORS, F5_ORDER } from '../../constants/parties';

interface ClusterSpread {
  party: string;
  [key: string]: string | number;
}

interface Props {
  nodes: ConstellationNode[];
  transfers?: TransferMatrix;
  clusterSpreads?: ClusterSpread[];
}

const THRESHOLD = 1.5;
const FACTORS = ['F1', 'F2', 'F3', 'F4', 'F5'] as const;
const ALL_AXES = [...FACTORS, 'seats'] as const;

function ControlSection({
  label, options, value, onChange,
}: {
  label: string;
  options: readonly string[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <span className="text-xs text-slate-500 font-semibold uppercase tracking-wide block mb-1">{label}</span>
      <div className="flex flex-col gap-0.5">
        {options.map(opt => (
          <button
            key={opt}
            onClick={() => onChange(opt)}
            title={opt === 'seats' ? 'Seats' : (FACTOR_LABELS[opt] ?? opt)}
            className={`px-1.5 py-0.5 rounded text-xs font-medium text-left transition-colors ${
              value === opt
                ? 'bg-teal-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {opt === 'seats' ? 'Seats' : (FACTOR_LABELS[opt] ?? opt)}
          </button>
        ))}
      </div>
    </div>
  );
}

export function IdeologicalConstellation({ nodes: inputNodes, transfers, clusterSpreads }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const W = 560, H = 460;
  const PAD_L = 52, PAD_R = 24, PAD_T = 30, PAD_B = 52;

  const [xFactor, setXFactor] = useState('F5');
  const [yFactor, setYFactor] = useState('F1');
  const [sizeFactor, setSizeFactor] = useState('F2');
  const [colorMode, setColorMode] = useState('F4');
  const [enabledParties, setEnabledParties] = useState<Set<string>>(() => new Set(F5_ORDER));

  const toggleParty = (p: string) => {
    setEnabledParties(prev => {
      const next = new Set(prev);
      if (next.has(p)) next.delete(p); else next.add(p);
      return next;
    });
  };

  useEffect(() => {
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const nodes = inputNodes.filter(n => enabledParties.has(n.id)).map(n => ({ ...n }));
    if (nodes.length === 0) return;

    const getVal = (n: ConstellationNode, key: string): number => {
      if (key === 'seats') return n.seats;
      return (n as unknown as Record<string, number>)[key] ?? 0;
    };

    const xVals = nodes.map(n => getVal(n, xFactor));
    const yVals = nodes.map(n => getVal(n, yFactor));
    const sVals = nodes.map(n => getVal(n, sizeFactor));  // no Math.abs

    // Tighter padding: 5% of range
    const xRange = (d3.max(xVals)! - d3.min(xVals)!) || 1;
    const yRange = (d3.max(yVals)! - d3.min(yVals)!) || 1;
    const xPad = xRange * 0.05;
    const yPad = yRange * 0.05;

    const xScale = d3.scaleLinear()
      .domain([d3.min(xVals)! - xPad, d3.max(xVals)! + xPad])
      .range([PAD_L, W - PAD_R]);
    const yScale = d3.scaleLinear()
      .domain([d3.min(yVals)! - yPad, d3.max(yVals)! + yPad])
      .range([H - PAD_B, PAD_T]);

    // Size scale: [sMin, sMax] → [minR, maxR]
    const sMin = d3.min(sVals) ?? 0;
    const sMax = d3.max(sVals) ?? 1;
    const rScale = sizeFactor === 'seats'
      ? d3.scaleSqrt().domain([0, sMax]).range([6, 42])
      : d3.scaleLinear().domain([sMin, sMax === sMin ? sMin + 1 : sMax]).range([6, 30]);

    // Color scale — per-factor data range so each factor uses the full cividis spectrum
    const cVals = nodes.map(n => getVal(n, colorMode === 'party' ? 'F5' : colorMode));
    const cMin = d3.min(cVals) ?? -1;
    const cMax = d3.max(cVals) ?? 1;
    const cScale = d3.scaleSequential(d3.interpolateCividis)
      .domain([cMin, cMax === cMin ? cMin + 1 : cMax]);

    const getColor = (n: ConstellationNode) => {
      if (colorMode === 'party') return getBlendColor(n.id);
      return cScale(getVal(n, colorMode));
    };

    // Text color: white on dark cividis fills, dark on light fills
    const getTextColor = (n: ConstellationNode, r: number) => {
      if (r < 14) return '#334155';  // small bubble — always dark (label goes outside)
      if (colorMode === 'party') return '#0f172a';
      const hsl = d3.hsl(getColor(n));
      return (hsl.l ?? 0.5) > 0.45 ? '#0f172a' : '#ffffff';
    };

    // --- Gridlines + tick labels ---
    const xTicks = xScale.ticks(4);
    const yTicks = yScale.ticks(4);

    // Vertical gridlines
    svg.append('g').selectAll('line.xgrid')
      .data(xTicks).enter().append('line')
      .attr('x1', d => xScale(d)).attr('y1', PAD_T)
      .attr('x2', d => xScale(d)).attr('y2', H - PAD_B)
      .attr('stroke', '#f1f5f9').attr('stroke-width', 1);

    svg.append('g').selectAll('text.xtick')
      .data(xTicks).enter().append('text')
      .attr('x', d => xScale(d)).attr('y', H - PAD_B + 12)
      .attr('text-anchor', 'middle')
      .style('fill', '#cbd5e1').style('font-size', '9px')
      .text(d => d.toFixed(1));

    // Horizontal gridlines
    svg.append('g').selectAll('line.ygrid')
      .data(yTicks).enter().append('line')
      .attr('x1', PAD_L).attr('y1', d => yScale(d))
      .attr('x2', W - PAD_R).attr('y2', d => yScale(d))
      .attr('stroke', '#f1f5f9').attr('stroke-width', 1);

    svg.append('g').selectAll('text.ytick')
      .data(yTicks).enter().append('text')
      .attr('x', PAD_L - 4).attr('y', d => yScale(d) + 3)
      .attr('text-anchor', 'end')
      .style('fill', '#cbd5e1').style('font-size', '9px')
      .text(d => d.toFixed(1));

    // --- Penumbra ellipses (voter spread) ---
    if (clusterSpreads) {
      const penumbraG = svg.append('g').attr('class', 'penumbra');
      for (const cs of clusterSpreads) {
        if (!enabledParties.has(cs.party)) continue;
        const color = PARTY_COLORS[cs.party] ?? '#6b7280';
        const mx = Number(cs[`mean_${xFactor}`] ?? 0);
        const my = Number(cs[`mean_${yFactor}`] ?? 0);
        const sdx = Number(cs[`sd_${xFactor}`] ?? 0);
        const sdy = Number(cs[`sd_${yFactor}`] ?? 0);
        const covKey = `cov_${xFactor}_${yFactor}`;
        const covKeyAlt = `cov_${yFactor}_${xFactor}`;
        const cov = Number(cs[covKey] ?? cs[covKeyAlt] ?? 0);

        const a = sdx * sdx, b = cov, dd = sdy * sdy;
        const trace = a + dd;
        const det = a * dd - b * b;
        const disc = Math.sqrt(Math.max(0, trace * trace / 4 - det));
        const lambda1 = trace / 2 + disc;
        const lambda2 = Math.max(0.001, trace / 2 - disc);
        const angle = b !== 0 ? Math.atan2(lambda1 - a, b) * (180 / Math.PI) : 0;

        const SIGMA = 1.5;
        const xDomain = xScale.domain();
        const yDomain = yScale.domain();
        const rx = Math.sqrt(lambda1) * SIGMA / (xDomain[1] - xDomain[0]) * (W - PAD_L - PAD_R);
        const ry = Math.sqrt(lambda2) * SIGMA / (yDomain[1] - yDomain[0]) * (H - PAD_T - PAD_B);

        penumbraG.append('ellipse')
          .attr('cx', xScale(mx))
          .attr('cy', yScale(my))
          .attr('rx', rx)
          .attr('ry', ry)
          .attr('transform', `rotate(${-angle}, ${xScale(mx)}, ${yScale(my)})`)
          .attr('fill', color)
          .attr('fill-opacity', 0.06)
          .attr('stroke', color)
          .attr('stroke-opacity', 0.15)
          .attr('stroke-width', 1);
      }
    }

    // --- Links ---
    const links: { source: string; target: string; value: number }[] = [];
    if (transfers) {
      for (const src of Object.keys(transfers.matrix)) {
        const srcCode = mapMatrixKeyToParty(src);
        if (!srcCode) continue;
        for (const [tgt, val] of Object.entries(transfers.matrix[src] ?? {})) {
          if (val < THRESHOLD) continue;
          const tgtCode = mapMatrixKeyToParty(tgt);
          if (!tgtCode || tgtCode === srcCode) continue;
          if (links.some(l =>
            (l.source === srcCode && l.target === tgtCode) ||
            (l.source === tgtCode && l.target === srcCode)
          )) continue;
          links.push({ source: srcCode, target: tgtCode, value: val });
        }
      }
    }

    const sim = d3.forceSimulation(nodes as any)
      .force('link', d3.forceLink(links as any).id((d: any) => d.id).strength(0.05))
      .force('charge', d3.forceManyBody().strength(-80))
      .force('x', d3.forceX((d: any) => xScale(getVal(d, xFactor))).strength(0.5))
      .force('y', d3.forceY((d: any) => yScale(getVal(d, yFactor))).strength(0.5))
      .force('collide', d3.forceCollide((d: any) => rScale(getVal(d, sizeFactor)) + 4))
      .stop();

    for (let i = 0; i < 200; i++) sim.tick();

    // Links
    const linkSel = svg.append('g')
      .selectAll('line')
      .data(links)
      .enter().append('line')
      .attr('x1', (d: any) => d.source.x)
      .attr('y1', (d: any) => d.source.y)
      .attr('x2', (d: any) => d.target.x)
      .attr('y2', (d: any) => d.target.y)
      .attr('stroke', '#cbd5e1')
      .attr('stroke-width', (d) => Math.max(0.5, d.value / 2))
      .attr('opacity', 0.5);

    // Nodes
    svg.append('g')
      .selectAll('circle')
      .data(nodes as any)
      .enter().append('circle')
      .attr('cx', (d: any) => d.x)
      .attr('cy', (d: any) => d.y)
      .attr('r', (d: any) => rScale(getVal(d, sizeFactor)))
      .attr('fill', (d: any) => getColor(d))
      .attr('fill-opacity', 0.6)
      .attr('stroke', (d: any) => getColor(d))
      .attr('stroke-width', 2)
      .style('cursor', 'pointer')
      .on('mouseenter', function (_e, d: any) {
        d3.select(this).attr('fill-opacity', 0.85);
        linkSel
          .attr('opacity', (l: any) => (l.source.id === d.id || l.target.id === d.id) ? 1 : 0.1)
          .attr('stroke', (l: any) => (l.source.id === d.id || l.target.id === d.id) ? '#94a3b8' : '#cbd5e1');
      })
      .on('mouseleave', function (_e, _d: any) {
        d3.select(this).attr('fill-opacity', 0.6);
        linkSel.attr('opacity', 0.5).attr('stroke', '#cbd5e1');
      });

    // Labels — offset above circle when bubble is too small to contain text
    svg.append('g')
      .selectAll('text')
      .data(nodes as any)
      .enter().append('text')
      .attr('x', (d: any) => d.x)
      .attr('y', (d: any) => {
        const r = rScale(getVal(d, sizeFactor));
        return r < 14 ? d.y - r - 4 : d.y + 4;
      })
      .attr('text-anchor', 'middle')
      .style('fill', (d: any) => getTextColor(d, rScale(getVal(d, sizeFactor))))
      .style('font-size', (d: any) => rScale(getVal(d, sizeFactor)) < 14 ? '9px' : '11px')
      .style('font-weight', '600')
      .style('pointer-events', 'none')
      .text((d: any) => d.id);

    // Axis labels
    const xLabel = xFactor === 'seats' ? 'Seats' : (FACTOR_LABELS[xFactor] ?? xFactor);
    const yLabel = yFactor === 'seats' ? 'Seats' : (FACTOR_LABELS[yFactor] ?? yFactor);
    svg.append('text')
      .attr('x', (PAD_L + W - PAD_R) / 2).attr('y', H - 4)
      .attr('text-anchor', 'middle')
      .style('fill', '#94a3b8').style('font-size', '10px')
      .text(`← Low ${xLabel}   |   High →`);
    svg.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('x', -(PAD_T + H - PAD_B) / 2).attr('y', 13)
      .attr('text-anchor', 'middle')
      .style('fill', '#94a3b8').style('font-size', '10px')
      .text(`← Low ${yLabel}   |   High →`);

  }, [inputNodes, transfers, clusterSpreads, xFactor, yFactor, sizeFactor, colorMode, enabledParties]);

  const colorOptions = ['party', ...FACTORS] as const;

  return (
    <div className="flex gap-3 items-start">
      {/* Left control panel */}
      <div className="shrink-0 w-44 space-y-3 p-2 bg-slate-50 rounded border border-slate-200 self-start">
        <ControlSection label="X" options={ALL_AXES} value={xFactor} onChange={setXFactor} />
        <ControlSection label="Y" options={ALL_AXES} value={yFactor} onChange={setYFactor} />
        <ControlSection label="Size" options={ALL_AXES} value={sizeFactor} onChange={setSizeFactor} />
        <div>
          <span className="text-xs text-slate-500 font-semibold uppercase tracking-wide block mb-1">Color</span>
          <div className="flex flex-col gap-0.5">
            {colorOptions.map(opt => (
              <button
                key={opt}
                onClick={() => setColorMode(opt)}
                title={opt === 'party' ? 'Party color' : (FACTOR_LABELS[opt] ?? opt)}
                className={`px-1.5 py-0.5 rounded text-xs font-medium text-left transition-colors ${
                  colorMode === opt
                    ? 'bg-teal-600 text-white'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {opt === 'party' ? 'Party' : (FACTOR_LABELS[opt] ?? opt)}
              </button>
            ))}
          </div>
          {colorMode !== 'party' && (
            <span className="text-xs text-slate-400 mt-1 block">cividis scale</span>
          )}
        </div>
      </div>

      {/* SVG + controls */}
      <div className="flex-1 min-w-0">
        {/* Party toggles */}
        <div className="flex flex-wrap gap-1 mb-2">
          {F5_ORDER.map(p => {
            const on = enabledParties.has(p);
            const color = PARTY_COLORS[p];
            return (
              <button key={p} onClick={() => toggleParty(p)}
                className="text-[10px] px-1.5 py-0.5 rounded border transition-all"
                style={{
                  borderColor: color,
                  color: on ? 'white' : color,
                  backgroundColor: on ? color : 'transparent',
                  opacity: on ? 1 : 0.35,
                }}>
                {p}
              </button>
            );
          })}
        </div>
        <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} width="100%" style={{ height: 'auto' }} />
        {transfers && (
          <p className="text-xs text-slate-500 mt-1 text-center">
            Lines = voter transfer affinity &gt; {THRESHOLD}. Hover to highlight.
          </p>
        )}
      </div>
    </div>
  );
}

function mapMatrixKeyToParty(key: string): string | null {
  const map: Record<string, string> = {
    'C0 Conservative': 'CON',
    'C1 Social Democrat': 'SD',
    'C2 Solidarity': 'STY',
    'C3 Nationalist': 'NAT',
    'C4 Liberal': 'LIB',
    'C5 Reform': 'REF',
    'C6 Center': 'CTR',
    'C8 DSA': 'DSA',
    'C9 Progressive': 'PRG',
  };
  return map[key] ?? null;
}

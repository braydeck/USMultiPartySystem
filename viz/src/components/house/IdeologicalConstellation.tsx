import { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';
import type { ConstellationNode, TransferMatrix } from '../../types';
import { getBlendColor, FACTOR_LABELS, FACTOR_POLES, PARTY_COLORS, F5_ORDER_WFP as F5_ORDER } from '../../constants/parties';
import { Button } from '@/components/ui/button';
import { ToggleGroup } from '../shared/ToggleGroup';
import { vikForZ, vikForPctile } from '../../lib/vik';

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
// F3 (Government Distrust) omitted — non-interpretable residual, see docs/EFA_FACTORS.md.
const FACTORS = ['F1', 'F2', 'F4', 'F5'] as const;
const ALL_AXES = [...FACTORS, 'seats'] as const;

const SCALE_LABELS: Record<'strength' | 'percentile', string> = {
  strength: 'σ Strength',
  percentile: '% Percentile',
};

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
      <span className="text-xs text-muted-foreground font-semibold uppercase tracking-wide block mb-1">{label}</span>
      <div className="flex flex-col gap-0.5">
        {options.map(opt => (
          <Button
            key={opt}
            onClick={() => onChange(opt)}
            title={opt === 'seats' ? 'Seats' : (FACTOR_LABELS[opt] ?? opt)}
            variant={value === opt ? 'default' : 'secondary'}
            size="sm"
            className="justify-start px-1.5 h-6"
          >
            {opt === 'seats' ? 'Seats' : (FACTOR_LABELS[opt] ?? opt)}
          </Button>
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
  const [sizeFactor, setSizeFactor] = useState('F4');
  const [colorMode, setColorMode] = useState('F2');
  const [equalSize, setEqualSize] = useState(false);
  const [scaleMode, setScaleMode] = useState<'strength' | 'percentile'>('strength');
  const [enabledParties, setEnabledParties] = useState<Set<string>>(() => new Set(F5_ORDER));

  const toggleParty = (p: string) => {
    setEnabledParties(prev => {
      const next = new Set(prev);
      if (next.has(p)) next.delete(p); else next.add(p);
      return next;
    });
  };

  // Parties present in the data, so the legend only lists real parties (incl. WFP when on).
  const presentParties = new Set(inputNodes.map(n => n.id.split('_')[0]));

  useEffect(() => {
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const nodes = inputNodes.filter(n => {
      // Match by exact id or base party prefix (for variant codes like CON_1, SD_hi_so)
      if (enabledParties.has(n.id)) return true;
      const base = n.id.split('_')[0];
      return enabledParties.has(base);
    }).map(n => ({ ...n }));
    if (nodes.length === 0) return;

    // Population SDs for z→percentile conversion
    const zToPctile = (z: number) => (1 / (1 + Math.exp(-1.7 * z))) * 100;

    const getVal = (n: ConstellationNode, key: string): number => {
      if (key === 'seats') return n.seats;
      const raw = (n as unknown as Record<string, number>)[key] ?? 0;
      if (scaleMode === 'percentile' && key !== 'seats') return zToPctile(raw);
      return raw;
    };

    const xVals = nodes.map(n => getVal(n, xFactor));
    const yVals = nodes.map(n => getVal(n, yFactor));
    const sVals = nodes.map(n => getVal(n, sizeFactor));

    let xMin = d3.min(xVals) ?? -1, xMax = d3.max(xVals) ?? 1;
    let yMin = d3.min(yVals) ?? -1, yMax = d3.max(yVals) ?? 1;

    // Expand domain to fit penumbra extents in percentile space
    if (clusterSpreads && xFactor !== 'seats' && yFactor !== 'seats') {
      const POP_SD_D: Record<string, number> = { F1: 0.787, F2: 0.818, F3: 0.630, F4: 0.486, F5: 0.879 };
      const r2plot = (raw: number, f: string) => {
        const z = raw / (POP_SD_D[f] || 1);
        return scaleMode === 'percentile' ? zToPctile(z) : z;
      };
      for (const cs of clusterSpreads) {
        if (!enabledParties.has(cs.party)) continue;
        const rawMx = Number(cs[`mean_${xFactor}`] ?? 0);
        const rawMy = Number(cs[`mean_${yFactor}`] ?? 0);
        const rawSdx = Number(cs[`sd_${xFactor}`] ?? 0);
        const rawSdy = Number(cs[`sd_${yFactor}`] ?? 0);
        if (rawSdx && rawSdy) {
          xMin = Math.min(xMin, r2plot(rawMx - rawSdx, xFactor));
          xMax = Math.max(xMax, r2plot(rawMx + rawSdx, xFactor));
          yMin = Math.min(yMin, r2plot(rawMy - rawSdy, yFactor));
          yMax = Math.max(yMax, r2plot(rawMy + rawSdy, yFactor));
        }
      }
    }

    const xRange = (xMax - xMin) || 1;
    const yRange = (yMax - yMin) || 1;
    const xPad = xRange * 0.08;
    const yPad = yRange * 0.08;

    const xScale = d3.scaleLinear()
      .domain([xMin - xPad, xMax + xPad])
      .range([PAD_L, W - PAD_R]);
    const yScale = d3.scaleLinear()
      .domain([yMin - yPad, yMax + yPad])
      .range([H - PAD_B, PAD_T]);

    // Size scale: [sMin, sMax] → [minR, maxR]
    const sMin = d3.min(sVals) ?? 0;
    const sMax = d3.max(sVals) ?? 1;
    const rScale = equalSize
      ? (() => { const fn = (_: number) => 5; fn.domain = () => [0, 1]; fn.range = () => [5, 5]; return fn; })()
      : sizeFactor === 'seats'
        ? d3.scaleSqrt().domain([0, sMax || 1]).range([6, 42])
        : d3.scaleLinear().domain([sMin, sMax === sMin ? sMin + 1 : sMax]).range([6, 30]);

    // Canvas background + clip path
    const clipId = `chart-clip-${Math.random().toString(36).slice(2, 8)}`;
    svg.append('defs').append('clipPath').attr('id', clipId)
      .append('rect')
      .attr('x', PAD_L).attr('y', PAD_T)
      .attr('width', W - PAD_L - PAD_R).attr('height', H - PAD_T - PAD_B);

    svg.append('rect')
      .attr('x', PAD_L).attr('y', PAD_T)
      .attr('width', W - PAD_L - PAD_R).attr('height', H - PAD_T - PAD_B)
      .attr('fill', '#f8fafc').attr('rx', 4);

    // Color scale — vik diverging, centered on zero (strength) / 50% (percentile),
    // so hue reads as signed strength rather than rank within the current selection.
    const getColor = (n: ConstellationNode) => {
      if (colorMode === 'party') return getBlendColor(n.id);
      const v = getVal(n, colorMode);
      return scaleMode === 'percentile' ? vikForPctile(v) : vikForZ(v);
    };

    // Darker outline so light/middling fills don't wash out against the canvas.
    const getStroke = (n: ConstellationNode) => {
      const c = d3.color(getColor(n));
      return c ? c.darker(1.4).formatHex() : getColor(n);
    };

    // Text color: always dark with white outline for readability
    const getTextColor = () => '#1e293b';

    // Tick label formatter
    const fmtTick = (v: number, factor: string) => {
      if (factor === 'seats') return v.toFixed(0);
      if (scaleMode === 'percentile') return `${Math.round(v)}%`;
      return v > 0 ? `+${v.toFixed(1)}σ` : `${v.toFixed(1)}σ`;
    };

    // --- Intensity zone bands (strength mode, both axes) ---
    const centerVal = scaleMode === 'percentile' ? 50 : 0;
    if (scaleMode === 'strength') {
      const zones = [
        { from: -2.0, to: -1.5, label: 'Strongly', side: 'low' },
        { from: -1.5, to: -1.0, label: 'Moderately', side: 'low' },
        { from: -1.0, to: -0.5, label: 'Leans',    side: 'low' },
        { from: -0.5, to:  0.5, label: 'Mixed',   side: 'mid' },
        { from:  0.5, to:  1.0, label: 'Leans',    side: 'high' },
        { from:  1.0, to:  1.5, label: 'Moderately',  side: 'high' },
        { from:  1.5, to:  2.0, label: 'Strongly', side: 'high' },
      ];
      const zoneColor = (side: string) => side === 'high' ? '#fecaca' : side === 'low' ? '#bfdbfe' : '#f1f5f9';
      const zoneOpacity = (label: string) => label === 'Moderate' ? 0.15 : 0.08;
      const zoneG = svg.append('g').attr('class', 'zones');

      // X-axis zones (vertical bands)
      if (xFactor !== 'seats') {
        for (const z of zones) {
          const x1 = Math.max(PAD_L, xScale(z.from));
          const x2 = Math.min(W - PAD_R, xScale(z.to));
          if (x2 > x1) {
            zoneG.append('rect')
              .attr('x', x1).attr('y', PAD_T).attr('width', x2 - x1).attr('height', H - PAD_T - PAD_B)
              .attr('fill', zoneColor(z.side)).attr('opacity', zoneOpacity(z.label));
            if (z.label && (x2 - x1) > 40) {
              zoneG.append('text')
                .attr('x', (x1 + x2) / 2).attr('y', PAD_T + 12)
                .attr('text-anchor', 'middle')
                .style('fill', '#94a3b8').style('font-size', '8px').style('font-style', 'italic')
                .text(z.label);
            }
          }
        }
      }

      // Y-axis zones (horizontal bands)
      if (yFactor !== 'seats') {
        for (const z of zones) {
          const y1 = Math.min(H - PAD_B, yScale(z.from));
          const y2 = Math.max(PAD_T, yScale(z.to));
          if (y1 > y2) {
            zoneG.append('rect')
              .attr('x', PAD_L).attr('y', y2).attr('width', W - PAD_L - PAD_R).attr('height', y1 - y2)
              .attr('fill', zoneColor(z.side)).attr('opacity', zoneOpacity(z.label) * 0.6);
            if (z.label && (y1 - y2) > 20) {
              zoneG.append('text')
                .attr('x', W - PAD_R - 4).attr('y', (y1 + y2) / 2 + 3)
                .attr('text-anchor', 'end')
                .style('fill', '#94a3b8').style('font-size', '8px').style('font-style', 'italic')
                .text(z.label);
            }
          }
        }
      }
    }

    // --- Gridlines + tick labels ---
    const xTicks = xScale.ticks(4);
    const yTicks = yScale.ticks(4);

    // Average voter line
    const x0 = xScale(centerVal), y0 = yScale(centerVal);
    if (x0 >= PAD_L && x0 <= W - PAD_R) {
      svg.append('line').attr('x1', x0).attr('y1', PAD_T).attr('x2', x0).attr('y2', H - PAD_B)
        .attr('stroke', '#94a3b8').attr('stroke-width', 1).attr('stroke-dasharray', '4,3');
    }
    if (y0 >= PAD_T && y0 <= H - PAD_B) {
      svg.append('line').attr('x1', PAD_L).attr('y1', y0).attr('x2', W - PAD_R).attr('y2', y0)
        .attr('stroke', '#94a3b8').attr('stroke-width', 1).attr('stroke-dasharray', '4,3');
    }

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
      .style('fill', '#64748b').style('font-size', '9px')
      .text(d => fmtTick(d, xFactor));

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
      .style('fill', '#64748b').style('font-size', '9px')
      .text(d => fmtTick(d, yFactor));

    // --- Penumbra ellipses (voter spread) ---
    if (clusterSpreads && xFactor !== 'seats' && yFactor !== 'seats') {
      const penumbraG = svg.append('g').attr('class', 'penumbra').attr('clip-path', `url(#${clipId})`);
      // Population stats for raw→z conversion
      const POP_SD_P: Record<string, number> = { F1: 0.787, F2: 0.818, F3: 0.630, F4: 0.486, F5: 0.879 };
      const rawToPlot = (raw: number, f: string) => {
        const z = raw / (POP_SD_P[f] || 1);
        return scaleMode === 'percentile' ? zToPctile(z) : z;
      };
      for (const cs of clusterSpreads) {
        if (!enabledParties.has(cs.party)) continue;
        const color = PARTY_COLORS[cs.party] ?? '#6b7280';
        const rawMx = Number(cs[`mean_${xFactor}`] ?? 0);
        const rawMy = Number(cs[`mean_${yFactor}`] ?? 0);
        const mx = rawToPlot(rawMx, xFactor);
        const my = rawToPlot(rawMy, yFactor);
        const rawSdx = Number(cs[`sd_${xFactor}`] ?? 0);
        const rawSdy = Number(cs[`sd_${yFactor}`] ?? 0);
        const sdx = scaleMode === 'percentile'
          ? Math.abs(rawToPlot(rawMx + rawSdx, xFactor) - mx)
          : rawSdx / (POP_SD_P[xFactor] || 1);
        const sdy = scaleMode === 'percentile'
          ? Math.abs(rawToPlot(rawMy + rawSdy, yFactor) - my)
          : rawSdy / (POP_SD_P[yFactor] || 1);
        if (!sdx || !sdy || isNaN(sdx) || isNaN(sdy)) continue;

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

        const SIGMA = 1.0;
        const xDomain = xScale.domain();
        const yDomain = yScale.domain();
        const xRange = (xDomain[1] - xDomain[0]) || 1;
        const yRange = (yDomain[1] - yDomain[0]) || 1;
        const rx = Math.sqrt(lambda1) * SIGMA / xRange * (W - PAD_L - PAD_R);
        const ry = Math.sqrt(lambda2) * SIGMA / yRange * (H - PAD_T - PAD_B);
        if (isNaN(rx) || isNaN(ry) || !isFinite(rx) || !isFinite(ry)) continue;

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

    // Place nodes at exact factor positions (no force offset — Venn diagram style)
    const posOf = (n: ConstellationNode) => ({
      x: xScale(getVal(n, xFactor)),
      y: yScale(getVal(n, yFactor)),
    });

    // Build link lookup for hover
    const nodeById: Record<string, ConstellationNode> = {};
    for (const n of nodes) nodeById[n.id] = n;

    // Links
    const linkSel = svg.append('g')
      .selectAll('line')
      .data(links)
      .enter().append('line')
      .attr('x1', (d) => posOf(nodeById[d.source] ?? nodes[0]).x)
      .attr('y1', (d) => posOf(nodeById[d.source] ?? nodes[0]).y)
      .attr('x2', (d) => posOf(nodeById[d.target] ?? nodes[0]).x)
      .attr('y2', (d) => posOf(nodeById[d.target] ?? nodes[0]).y)
      .attr('stroke', '#cbd5e1')
      .attr('stroke-width', (d) => Math.max(0.5, d.value / 2))
      .attr('opacity', 0.4);

    const manyNodes = false;  // always show labels — hover-only was too hard to use

    // Nodes — exact positions, overlapping allowed
    svg.append('g')
      .selectAll('circle')
      .data(nodes)
      .enter().append('circle')
      .attr('cx', d => posOf(d).x)
      .attr('cy', d => posOf(d).y)
      .attr('r', d => rScale(getVal(d, sizeFactor)))
      .attr('fill', d => getColor(d))
      .attr('fill-opacity', 0.55)
      .attr('stroke', d => getStroke(d))
      .attr('stroke-width', 1.5)
      .style('cursor', 'pointer')
      .on('mouseenter', function (_e, d) {
        d3.select(this).attr('fill-opacity', 0.9).attr('stroke-width', 3);
        // Show tooltip label
        svg.select(`.hover-label-${d.id.replace(/[^a-zA-Z0-9]/g, '_')}`).attr('opacity', 1);
        linkSel
          .attr('opacity', (l) => (l.source === d.id || l.target === d.id) ? 1 : 0.08)
          .attr('stroke', (l) => (l.source === d.id || l.target === d.id) ? '#64748b' : '#cbd5e1');
      })
      .on('mouseleave', function (_e, d) {
        d3.select(this).attr('fill-opacity', 0.55).attr('stroke-width', 1.5);
        svg.select(`.hover-label-${d.id.replace(/[^a-zA-Z0-9]/g, '_')}`).attr('opacity', manyNodes ? 0 : 1);
        linkSel.attr('opacity', 0.4).attr('stroke', '#cbd5e1');
      });

    // Labels
    const labelG = svg.append('g');
    for (const d of nodes) {
      const p = posOf(d);
      const r = rScale(getVal(d, sizeFactor));
      const safeClass = `hover-label-${d.id.replace(/[^a-zA-Z0-9]/g, '_')}`;
      const alwaysShow = !manyNodes;
      const fontSize = manyNodes ? '9px' : '10px';

      // White outline
      labelG.append('text')
        .attr('class', safeClass)
        .attr('x', p.x).attr('y', p.y - r - 3)
        .attr('text-anchor', 'middle')
        .style('fill', 'none').style('stroke', '#f8fafc').style('stroke-width', '3px')
        .style('font-size', fontSize).style('font-weight', '700')
        .style('pointer-events', 'none')
        .attr('opacity', alwaysShow ? 1 : 0)
        .text(d.id);
      // Label text
      labelG.append('text')
        .attr('class', safeClass)
        .attr('x', p.x).attr('y', p.y - r - 3)
        .attr('text-anchor', 'middle')
        .style('fill', getTextColor()).style('font-size', fontSize).style('font-weight', '700')
        .style('pointer-events', 'none')
        .attr('opacity', alwaysShow ? 1 : 0)
        .text(d.id);
    }

    // Axis labels using pole names
    const xPoles = FACTOR_POLES[xFactor];
    const yPoles = FACTOR_POLES[yFactor];
    const xLabel = xFactor === 'seats' ? '← Fewer Seats | More →'
      : xPoles ? `← ${xPoles.low}   |   ${xPoles.high} →` : xFactor;
    const yLabel = yFactor === 'seats' ? '← Fewer Seats | More →'
      : yPoles ? `← ${yPoles.low}   |   ${yPoles.high} →` : yFactor;
    svg.append('text')
      .attr('x', (PAD_L + W - PAD_R) / 2).attr('y', H - 4)
      .attr('text-anchor', 'middle')
      .style('fill', '#475569').style('font-size', '10px')
      .text(xLabel);
    svg.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('x', -(PAD_T + H - PAD_B) / 2).attr('y', 13)
      .attr('text-anchor', 'middle')
      .style('fill', '#475569').style('font-size', '10px')
      .text(`← Low ${yLabel}   |   High →`);

  }, [inputNodes, transfers, clusterSpreads, xFactor, yFactor, sizeFactor, colorMode, enabledParties, equalSize, scaleMode]);

  const colorOptions = ['party', ...FACTORS] as const;

  return (
    <div className="flex flex-col sm:flex-row gap-3 sm:items-start">
      {/* Left control panel — stacks above the chart on mobile (compact column) */}
      <div className="shrink-0 w-44 space-y-3 p-2 bg-slate-50 rounded border border-border self-start">
        <ControlSection label="X" options={ALL_AXES} value={xFactor} onChange={setXFactor} />
        <ControlSection label="Y" options={ALL_AXES} value={yFactor} onChange={setYFactor} />
        <ControlSection label="Size" options={ALL_AXES} value={sizeFactor} onChange={setSizeFactor} />
        <Button onClick={() => setEqualSize(!equalSize)}
          variant={equalSize ? 'default' : 'secondary'}
          size="sm"
          className="w-full justify-start px-1.5 h-6">
          {equalSize ? '⊙ Equal size' : '○ Equal size'}
        </Button>
        <div>
          <span className="text-xs text-muted-foreground font-semibold uppercase tracking-wide block mb-1">Color</span>
          <div className="flex flex-col gap-0.5">
            {colorOptions.map(opt => (
              <Button
                key={opt}
                onClick={() => setColorMode(opt)}
                title={opt === 'party' ? 'Party color' : (FACTOR_LABELS[opt] ?? opt)}
                variant={colorMode === opt ? 'default' : 'secondary'}
                size="sm"
                className="justify-start px-1.5 h-6"
              >
                {opt === 'party' ? 'Party' : (FACTOR_LABELS[opt] ?? opt)}
              </Button>
            ))}
          </div>
          {colorMode !== 'party' && (
            <span className="text-xs text-muted-foreground mt-1 block">vik scale</span>
          )}
        </div>
      </div>

      {/* SVG + controls */}
      <div className="flex-1 min-w-0">
        {/* Scale + Party toggles */}
        <div className="flex flex-wrap items-center gap-1 mb-2">
          <ToggleGroup label="Scale" value={scaleMode} onChange={setScaleMode}
            options={['strength', 'percentile'] as const} labels={SCALE_LABELS} />
        </div>
        <div className="flex flex-wrap gap-1 mb-2">
          {F5_ORDER.filter(p => presentParties.has(p)).map(p => {
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
        <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} width="100%" style={{ height: 'auto' }} aria-label="Ideological factor constellation chart" />
        {transfers && (
          <p className="text-xs text-muted-foreground mt-1 text-center">
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
    'C1 Social Democrat': 'LBR',
    'C2 Solidarity': 'STY',
    'C3 Nationalist': 'NAT',
    'C4 Liberal': 'LIB',
    'C5 Populist': 'POP',
    'C6 Civic Union Party': 'CUP',
    'C8 DSA': 'DSA',
    'C9 Progressive': 'PRG',
  };
  return map[key] ?? null;
}

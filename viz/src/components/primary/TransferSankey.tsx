import { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';
import { sankey, sankeyLinkHorizontal, sankeyLeft } from 'd3-sankey';
import type { SankeyNode, SankeyLink } from 'd3-sankey';
import { getBlendColor } from '../../constants/parties';
import type { PrimaryTransfer } from '../../types';

interface Props {
  transfers: PrimaryTransfer[];
}

interface SNode {
  name: string;
}

type ExtNode = SankeyNode<SNode, object>;
type ExtLink = SankeyLink<SNode, object>;

/** Collapse bidirectional edges to net flow to prevent d3-sankey cycle errors. */
function collapseToNetFlow(
  links: { source: number; target: number; value: number; pct: number; count: number }[]
) {
  const map = new Map<string, typeof links[0]>();
  for (const l of links) {
    const fwd = `${l.source}-${l.target}`;
    const rev = `${l.target}-${l.source}`;
    if (map.has(rev)) {
      const existing = map.get(rev)!;
      if (l.value > existing.value) {
        // Current direction dominates — replace with net
        map.delete(rev);
        map.set(fwd, { ...l, value: l.value - existing.value });
      } else {
        // Existing direction keeps net
        existing.value -= l.value;
        if (existing.value <= 0) map.delete(rev);
      }
    } else if (map.has(fwd)) {
      map.get(fwd)!.value += l.value;
    } else {
      map.set(fwd, { ...l });
    }
  }
  return Array.from(map.values()).filter(l => l.value > 0.5);
}

export function TransferSankey({ transfers }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);
  const [typeFilter, setTypeFilter] = useState<'elimination' | 'surplus' | 'all'>('elimination');

  const filtered = typeFilter === 'all' ? transfers : transfers.filter(t => t.type === typeFilter);

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    if (filtered.length === 0) return;

    const width = svgRef.current.clientWidth || 600;
    const height = 380;
    svg.attr('viewBox', `0 0 ${width} ${height}`);

    // Build node set
    const nodeNames = new Set<string>();
    for (const t of filtered) {
      nodeNames.add(t.source);
      nodeNames.add(t.target);
    }
    const nodes: SNode[] = Array.from(nodeNames).map(name => ({ name }));
    const nodeIndex = new Map(nodes.map((n, i) => [n.name, i]));

    // Aggregate links (same source→target, sum votes)
    const linkMap = new Map<string, { source: number; target: number; value: number; pct: number; count: number }>();
    for (const t of filtered) {
      const si = nodeIndex.get(t.source);
      const ti = nodeIndex.get(t.target);
      if (si === undefined || ti === undefined || si === ti) continue;
      const key = `${si}-${ti}`;
      const existing = linkMap.get(key);
      if (existing) {
        existing.value += t.votes;
        existing.pct += t.pct;
        existing.count += 1;
      } else {
        linkMap.set(key, { source: si, target: ti, value: t.votes, pct: t.pct, count: 1 });
      }
    }

    const rawLinks = Array.from(linkMap.values());
    const links = collapseToNetFlow(rawLinks);

    if (nodes.length < 2 || links.length === 0) return;

    const sankeyGen = sankey<SNode, object>()
      .nodeId((d: ExtNode) => nodeIndex.get((d as SNode).name) ?? 0)
      .nodeAlign(sankeyLeft)
      .nodeWidth(14)
      .nodePadding(10)
      .extent([[16, 16], [width - 16, height - 32]]);

    let graph;
    try {
      graph = sankeyGen({ nodes: nodes.map(n => ({ ...n })), links: links.map(l => ({ ...l })) });
    } catch {
      // If layout still fails, just clear
      return;
    }

    const g = svg.append('g');

    // Links
    g.append('g')
      .selectAll('path')
      .data(graph.links)
      .join('path')
      .attr('d', sankeyLinkHorizontal() as any)
      .attr('stroke', (d: ExtLink) => getBlendColor((d.source as ExtNode).name))
      .attr('stroke-width', (d: ExtLink) => Math.max(1, d.width ?? 1))
      .attr('fill', 'none')
      .attr('stroke-opacity', 0.35)
      .style('cursor', 'pointer')
      .on('mouseover', function(event: MouseEvent, d: ExtLink) {
        d3.select(this).attr('stroke-opacity', 0.65);
        const srcName = (d.source as ExtNode).name;
        const tgtName = (d.target as ExtNode).name;
        const si = nodeIndex.get(srcName);
        const ti = nodeIndex.get(tgtName);
        const data = linkMap.get(`${si}-${ti}`) ?? linkMap.get(`${ti}-${si}`);
        const pctAvg = data ? (data.pct / data.count).toFixed(1) : '?';
        setTooltip({ x: event.offsetX, y: event.offsetY, text: `${pctAvg}% of ${srcName} → ${tgtName}` });
      })
      .on('mousemove', function(event: MouseEvent) {
        setTooltip(prev => prev ? { ...prev, x: event.offsetX, y: event.offsetY } : null);
      })
      .on('mouseout', function() {
        d3.select(this).attr('stroke-opacity', 0.35);
        setTooltip(null);
      });

    // Nodes
    const nodeG = g.append('g').selectAll('g').data(graph.nodes).join('g');

    nodeG.append('rect')
      .attr('x', (d: ExtNode) => d.x0 ?? 0)
      .attr('y', (d: ExtNode) => d.y0 ?? 0)
      .attr('width', (d: ExtNode) => (d.x1 ?? 0) - (d.x0 ?? 0))
      .attr('height', (d: ExtNode) => Math.max(2, (d.y1 ?? 0) - (d.y0 ?? 0)))
      .attr('fill', (d: ExtNode) => getBlendColor((d as SNode).name))
      .attr('fill-opacity', 0.9)
      .attr('rx', 2);

    nodeG.append('text')
      .attr('x', (d: ExtNode) => ((d.x0 ?? 0) < width / 2) ? (d.x1 ?? 0) + 5 : (d.x0 ?? 0) - 5)
      .attr('y', (d: ExtNode) => ((d.y0 ?? 0) + (d.y1 ?? 0)) / 2)
      .attr('dy', '0.35em')
      .attr('text-anchor', (d: ExtNode) => ((d.x0 ?? 0) < width / 2) ? 'start' : 'end')
      .attr('fill', (d: ExtNode) => getBlendColor((d as SNode).name))
      .attr('font-size', 10)
      .text((d: ExtNode) => (d as SNode).name);

  }, [filtered, typeFilter]);

  return (
    <div>
      <div className="flex flex-wrap gap-2 mb-3">
        {(['elimination', 'surplus', 'all'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTypeFilter(t)}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors capitalize ${
              typeFilter === t
                ? 'bg-amber-600 text-white'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            {t === 'all' ? 'All transfers' : `${t} only`}
          </button>
        ))}
      </div>

      <div className="relative">
        {tooltip && (
          <div
            className="absolute z-10 bg-slate-800 border border-slate-600 rounded px-3 py-2 text-xs pointer-events-none"
            style={{ left: tooltip.x + 12, top: tooltip.y - 8, maxWidth: 220 }}
          >
            {tooltip.text}
          </div>
        )}
        <svg ref={svgRef} className="w-full" style={{ height: 380 }} />
      </div>

      <p className="text-xs text-muted-foreground mt-2 text-center">
        Width = vote volume. Bidirectional flows collapsed to net direction. Hover for transfer %.
      </p>
    </div>
  );
}

import { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';
import { sankey, sankeyLinkHorizontal, sankeyLeft } from 'd3-sankey';
import type { SankeyNode, SankeyLink } from 'd3-sankey';
import { getBlendColor } from '../../constants/parties';
import type { PrimarySankeyData } from '../../types';
import { CARD_HINT } from '../../constants/typography';

interface Props {
  data: PrimarySankeyData;
}

interface SNode {
  id: string;
  label: string;
  stageIdx: number;
  pct: number;
}

type ExtNode = SankeyNode<SNode, object>;
type ExtLink = SankeyLink<SNode, object>;

export function StagedSankey({ data }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);

  useEffect(() => {
    if (!svgRef.current || !data.nodes.length) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = svgRef.current.clientWidth || 800;
    const height = 520;
    svg.attr('viewBox', `0 0 ${width} ${height}`);

    const padL = 48, padR = 80, padT = 40, padB = 16;

    const nodes: SNode[] = data.nodes.map(n => ({ ...n }));
    const nodeById = new Map(nodes.map(n => [n.id, n]));

    const links = data.links
      .filter(l => nodeById.has(l.source) && nodeById.has(l.target))
      .map(l => ({ source: l.source, target: l.target, value: l.value }));

    if (nodes.length < 2 || links.length === 0) return;

    const sankeyGen = sankey<SNode, object>()
      .nodeId((d: ExtNode) => (d as SNode).id)
      .nodeAlign(sankeyLeft)
      .nodeWidth(10)
      .nodePadding(5)
      .extent([[padL, padT], [width - padR, height - padB]]);

    let graph;
    try {
      graph = sankeyGen({ nodes: nodes as any[], links: links as any[] });
    } catch {
      return;
    }

    const g = svg.append('g');

    // Column header labels (stage labels)
    const colX = new Map<number, number>();
    for (const n of graph.nodes as ExtNode[]) {
      const sn = n as unknown as SNode;
      if (!colX.has(sn.stageIdx)) {
        colX.set(sn.stageIdx, ((n.x0 ?? 0) + (n.x1 ?? 0)) / 2);
      }
    }
    const headerG = svg.append('g');
    data.stageLabels.forEach((label, i) => {
      const cx = colX.get(i);
      if (cx === undefined) return;
      headerG.append('text')
        .attr('x', cx)
        .attr('y', 14)
        .attr('text-anchor', 'middle')
        .attr('fill', '#64748b')
        .attr('font-size', 9)
        .attr('font-weight', '600')
        .attr('letter-spacing', '0.05em')
        .text(label.toUpperCase());
    });

    // Links
    g.append('g')
      .selectAll('path')
      .data(graph.links)
      .join('path')
      .attr('d', sankeyLinkHorizontal() as any)
      .attr('stroke', (d: ExtLink) => getBlendColor((d.source as ExtNode as unknown as SNode).label))
      .attr('stroke-width', (d: ExtLink) => Math.max(1, d.width ?? 1))
      .attr('fill', 'none')
      .attr('stroke-opacity', 0.25)
      .style('cursor', 'pointer')
      .on('mouseover', function(event: MouseEvent, d: ExtLink) {
        d3.select(this).attr('stroke-opacity', 0.55);
        const src = (d.source as ExtNode as unknown as SNode);
        const tgt = (d.target as ExtNode as unknown as SNode);
        const pct = ((d.value / src.pct) * 100).toFixed(0);
        setTooltip({
          x: event.offsetX, y: event.offsetY,
          text: `${src.label} → ${tgt.label}: ${d.value.toFixed(1)}% (${pct}% of ${src.label})`,
        });
      })
      .on('mousemove', function(event: MouseEvent) {
        setTooltip(prev => prev ? { ...prev, x: event.offsetX, y: event.offsetY } : null);
      })
      .on('mouseout', function() {
        d3.select(this).attr('stroke-opacity', 0.25);
        setTooltip(null);
      });

    // Nodes
    const nodeG = g.append('g').selectAll('g').data(graph.nodes).join('g');

    nodeG.append('rect')
      .attr('x', (d: ExtNode) => d.x0 ?? 0)
      .attr('y', (d: ExtNode) => d.y0 ?? 0)
      .attr('width', (d: ExtNode) => (d.x1 ?? 0) - (d.x0 ?? 0))
      .attr('height', (d: ExtNode) => Math.max(2, (d.y1 ?? 0) - (d.y0 ?? 0)))
      .attr('fill', (d: ExtNode) => getBlendColor((d as unknown as SNode).label))
      .attr('fill-opacity', 0.9)
      .attr('rx', 2);

    // Node labels — show on stage 0 (left) and stage 4 (right), abbreviated elsewhere
    nodeG.append('text')
      .filter((d: ExtNode) => {
        const sn = d as unknown as SNode;
        return sn.stageIdx === 0 || sn.stageIdx === 4;
      })
      .attr('x', (d: ExtNode) => {
        const sn = d as unknown as SNode;
        return sn.stageIdx === 0 ? (d.x0 ?? 0) - 4 : (d.x1 ?? 0) + 4;
      })
      .attr('y', (d: ExtNode) => ((d.y0 ?? 0) + (d.y1 ?? 0)) / 2)
      .attr('dy', '0.35em')
      .attr('text-anchor', (d: ExtNode) => {
        const sn = d as unknown as SNode;
        return sn.stageIdx === 0 ? 'end' : 'start';
      })
      .attr('fill', (d: ExtNode) => getBlendColor((d as unknown as SNode).label))
      .attr('font-size', (d: ExtNode) => {
        const sn = d as unknown as SNode;
        return sn.stageIdx === 4 ? 11 : 9;
      })
      .attr('font-weight', (d: ExtNode) => {
        const sn = d as unknown as SNode;
        return sn.stageIdx === 4 ? '600' : '400';
      })
      .text((d: ExtNode) => {
        const sn = d as unknown as SNode;
        const pct = sn.pct.toFixed(1);
        return sn.stageIdx === 4 ? `${sn.label} ${pct}%` : sn.label;
      });

  }, [data]);

  return (
    <div>
      <div className="relative">
        {tooltip && (
          <div
            className="absolute z-10 bg-white border border-slate-300 rounded px-3 py-2 text-xs pointer-events-none text-foreground shadow-sm"
            style={{ left: tooltip.x + 12, top: tooltip.y - 8, maxWidth: 260 }}
          >
            {tooltip.text}
          </div>
        )}
        <svg ref={svgRef} className="w-full" style={{ height: 520 }} />
      </div>
      <p className={`${CARD_HINT} mt-1 text-center`}>
        Width = vote share. Hover links for transfer breakdown. Final five labeled on right.
      </p>
    </div>
  );
}

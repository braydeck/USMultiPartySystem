import { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';
import { sankey, sankeyLinkHorizontal, sankeyLeft } from 'd3-sankey';
import type { SankeyNode, SankeyLink } from 'd3-sankey';
import { getBlendColor } from '../../constants/parties';
import type { IRVRound } from '../../types';

interface Props {
  rounds: IRVRound[];
  irvWinner: string;
}

interface SNode {
  id: string;
  label: string;
  roundIdx: number;
  pct: number;
}

type ExtNode = SankeyNode<SNode, object>;
type ExtLink = SankeyLink<SNode, object>;

export function IRVSankey({ rounds, irvWinner }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);

  useEffect(() => {
    if (!svgRef.current || rounds.length < 2) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = svgRef.current.clientWidth || 600;
    const height = 280;
    svg.attr('viewBox', `0 0 ${width} ${height}`);

    const padL = 56, padR = 80, padT = 36, padB = 16;

    // Create one node per (candidate, round) for every round the candidate appears in.
    // This ensures eliminated candidates have carry-forward links that anchor their depth correctly.
    const nodes: SNode[] = [];
    for (let ri = 0; ri < rounds.length; ri++) {
      for (const c of rounds[ri].candidates) {
        nodes.push({ id: `${c.code}__${ri}`, label: c.code, roundIdx: ri, pct: c.pct });
      }
    }
    const nodeById = new Map(nodes.map(n => [n.id, n]));

    const links: { source: string; target: string; value: number }[] = [];

    for (let ri = 0; ri < rounds.length - 1; ri++) {
      const curr = rounds[ri];
      const next = rounds[ri + 1];
      const eliminated = curr.candidates.find(c => c.eliminated);
      const currPct = new Map(curr.candidates.map(c => [c.code, c.pct]));
      const nextPct = new Map(next.candidates.map(c => [c.code, c.pct]));

      // Carry-forward links for non-eliminated candidates in this round.
      // These anchor each candidate's node to the correct column depth.
      for (const c of curr.candidates) {
        if (c.eliminated) continue;
        const srcId = `${c.code}__${ri}`;
        const tgtId = `${c.code}__${ri + 1}`;
        if (nodeById.has(srcId) && nodeById.has(tgtId)) {
          links.push({ source: srcId, target: tgtId, value: c.pct });
        }
      }

      // Transfer links from eliminated candidate to next-round survivors.
      // Infer transfer amounts from vote gains between rounds.
      if (eliminated) {
        const elimId = `${eliminated.code}__${ri}`;
        for (const c of next.candidates) {
          const gain = (nextPct.get(c.code) ?? 0) - (currPct.get(c.code) ?? 0);
          if (gain > 0.01) {
            const tgtId = `${c.code}__${ri + 1}`;
            if (nodeById.has(elimId) && nodeById.has(tgtId)) {
              links.push({ source: elimId, target: tgtId, value: gain });
            }
          }
        }
      }
    }

    if (nodes.length < 2 || links.length === 0) return;

    const sankeyGen = sankey<SNode, object>()
      .nodeId((d: ExtNode) => (d as unknown as SNode).id)
      .nodeAlign(sankeyLeft)
      .nodeWidth(10)
      .nodePadding(10)
      .extent([[padL, padT], [width - padR, height - padB]]);

    let graph;
    try {
      graph = sankeyGen({ nodes: nodes as any[], links: links as any[] });
    } catch {
      return;
    }

    const g = svg.append('g');

    // Column header labels — derive x-center from node positions
    const colX = new Map<number, number>();
    for (const n of graph.nodes as ExtNode[]) {
      const sn = n as unknown as SNode;
      if (!colX.has(sn.roundIdx)) {
        colX.set(sn.roundIdx, ((n.x0 ?? 0) + (n.x1 ?? 0)) / 2);
      }
    }
    const headerG = svg.append('g');
    rounds.forEach((r, i) => {
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
        .text(`ROUND ${r.round}`);
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
      .attr('stroke-opacity', 0.3)
      .style('cursor', 'pointer')
      .on('mouseover', function(event: MouseEvent, d: ExtLink) {
        d3.select(this).attr('stroke-opacity', 0.65);
        const src = d.source as ExtNode as unknown as SNode;
        const tgt = d.target as ExtNode as unknown as SNode;
        setTooltip({
          x: event.offsetX, y: event.offsetY,
          text: `${src.label} → ${tgt.label}: ${d.value.toFixed(2)}%`,
        });
      })
      .on('mousemove', function(event: MouseEvent) {
        setTooltip(prev => prev ? { ...prev, x: event.offsetX, y: event.offsetY } : null);
      })
      .on('mouseout', function() {
        d3.select(this).attr('stroke-opacity', 0.3);
        setTooltip(null);
      });

    // Nodes — dim eliminated candidates
    const nodeG = g.append('g').selectAll('g').data(graph.nodes).join('g');

    nodeG.append('rect')
      .attr('x', (d: ExtNode) => d.x0 ?? 0)
      .attr('y', (d: ExtNode) => d.y0 ?? 0)
      .attr('width', (d: ExtNode) => (d.x1 ?? 0) - (d.x0 ?? 0))
      .attr('height', (d: ExtNode) => Math.max(2, (d.y1 ?? 0) - (d.y0 ?? 0)))
      .attr('fill', (d: ExtNode) => getBlendColor((d as unknown as SNode).label))
      .attr('fill-opacity', (d: ExtNode) => {
        const sn = d as unknown as SNode;
        // Dim the node at the round the candidate is eliminated
        const roundData = rounds[sn.roundIdx]?.candidates.find(c => c.code === sn.label);
        return roundData?.eliminated ? 0.35 : 0.9;
      })
      .attr('rx', 2);

    // Labels: left side for round 0, right side for last round
    nodeG.append('text')
      .filter((d: ExtNode) => {
        const sn = d as unknown as SNode;
        return sn.roundIdx === 0 || sn.roundIdx === rounds.length - 1;
      })
      .attr('x', (d: ExtNode) => {
        const sn = d as unknown as SNode;
        return sn.roundIdx === 0 ? (d.x0 ?? 0) - 4 : (d.x1 ?? 0) + 4;
      })
      .attr('y', (d: ExtNode) => ((d.y0 ?? 0) + (d.y1 ?? 0)) / 2)
      .attr('dy', '0.35em')
      .attr('text-anchor', (d: ExtNode) => {
        const sn = d as unknown as SNode;
        return sn.roundIdx === 0 ? 'end' : 'start';
      })
      .attr('fill', (d: ExtNode) => getBlendColor((d as unknown as SNode).label))
      .attr('font-size', (d: ExtNode) => {
        const sn = d as unknown as SNode;
        return sn.roundIdx === rounds.length - 1 ? 11 : 9;
      })
      .attr('font-weight', (d: ExtNode) => {
        const sn = d as unknown as SNode;
        return sn.label === irvWinner && sn.roundIdx === rounds.length - 1 ? '700' : '400';
      })
      .text((d: ExtNode) => {
        const sn = d as unknown as SNode;
        if (sn.roundIdx === rounds.length - 1) return `${sn.label} ${sn.pct.toFixed(1)}%`;
        // For eliminated candidates at round 0, show with strike indicator
        const isElimHere = rounds[sn.roundIdx]?.candidates.find(c => c.code === sn.label)?.eliminated;
        return isElimHere ? `${sn.label} ✕` : sn.label;
      })
      .attr('fill-opacity', (d: ExtNode) => {
        const sn = d as unknown as SNode;
        const isElimHere = rounds[sn.roundIdx]?.candidates.find(c => c.code === sn.label)?.eliminated;
        return isElimHere ? 0.4 : 1;
      });

  }, [rounds, irvWinner]);

  return (
    <div>
      <div className="relative">
        {tooltip && (
          <div
            className="absolute z-10 bg-white border border-slate-300 rounded px-3 py-2 text-xs pointer-events-none text-foreground shadow-sm"
            style={{ left: tooltip.x + 12, top: tooltip.y - 8, maxWidth: 220 }}
            role="status"
            aria-live="polite"
          >
            {tooltip.text}
          </div>
        )}
        <svg ref={svgRef} className="w-full" style={{ height: 280 }} aria-label="IRV vote transfer Sankey diagram" />
      </div>
      <p className="text-xs text-muted-foreground mt-1 text-center">
        Carry-forward votes flow straight across. Eliminated candidates&apos; votes fan out to remaining candidates.
      </p>
    </div>
  );
}

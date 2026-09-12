import { useRef, useEffect } from 'react';
import * as d3 from 'd3';
import type { PrimaryCandidate } from '../../types';
import { getPartyColor } from '../../constants/parties';

interface Props {
  candidates: PrimaryCandidate[];
  stage: string;
}

// Fixed chart geometry. At module scope these are stable references, so the effect below can
// list them honestly instead of reading recreated locals it never declares as dependencies.
const W = 500, H = 380;
const margin = { top: 30, right: 30, bottom: 50, left: 60 };
const iW = W - margin.left - margin.right;
const iH = H - margin.top - margin.bottom;

export function IdeologicalScatter({ candidates, stage }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const g = svg
      .append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`);

    const xScale = d3.scaleLinear().domain([-1.6, 1.0]).range([0, iW]);
    const yScale = d3.scaleLinear().domain([-1.2, 1.7]).range([iH, 0]);

    // Axes
    g.append('g')
      .attr('transform', `translate(0,${iH})`)
      .call(d3.axisBottom(xScale).ticks(5))
      .call(ax => ax.selectAll('text').style('fill', '#94a3b8').style('font-size', '11px'))
      .call(ax => ax.selectAll('line,path').style('stroke', '#e2e8f0'));

    g.append('g')
      .call(d3.axisLeft(yScale).ticks(5))
      .call(ax => ax.selectAll('text').style('fill', '#94a3b8').style('font-size', '11px'))
      .call(ax => ax.selectAll('line,path').style('stroke', '#e2e8f0'));

    // Axis labels
    g.append('text')
      .attr('x', iW / 2)
      .attr('y', iH + 42)
      .attr('text-anchor', 'middle')
      .style('fill', '#64748b')
      .style('font-size', '12px')
      .text('F1: Security & Order →');

    g.append('text')
      .attr('transform', 'rotate(-90)')
      .attr('x', -iH / 2)
      .attr('y', -44)
      .attr('text-anchor', 'middle')
      .style('fill', '#64748b')
      .style('font-size', '12px')
      .text('F5: Populist Conservatism →');

    // F4 opacity map: [-0.4, +0.5] → [0.3, 1.0]
    const opacityScale = d3.scaleLinear().domain([-0.4, 0.5]).range([0.3, 1.0]).clamp(true);
    // Radius: proportional to votePct, 0 pct → tiny circle
    const maxVote = d3.max(candidates.map(c => c.stages[stage]?.votePct ?? 0)) ?? 10;
    const radiusScale = d3.scaleSqrt().domain([0, maxVote]).range([3, 30]);

    const nodes = candidates.map(c => ({
      ...c,
      stageData: c.stages[stage] ?? { voteTotal: 0, votePct: 0, status: 'previously_eliminated', quotaThreshold: 0 },
    }));

    const circles = g.selectAll('circle').data(nodes, (d: any) => d.code);

    circles.enter()
      .append('circle')
      .merge(circles as any)
      .transition()
      .duration(400)
      .attr('cx', d => xScale(d.F1))
      .attr('cy', d => yScale(d.F5))
      .attr('r', d => radiusScale(d.stageData.votePct))
      .attr('fill', d => {
        const elim = d.stageData.status === 'previously_eliminated';
        return elim ? 'transparent' : getPartyColor(d.code);
      })
      .attr('stroke', d => getPartyColor(d.code))
      .attr('stroke-width', 1.5)
      .attr('opacity', d => {
        const elim = d.stageData.status === 'previously_eliminated';
        return elim ? 0.4 : opacityScale(d.F4);
      });

    // Labels
    g.selectAll('.label')
      .data(nodes)
      .enter()
      .append('text')
      .attr('class', 'label')
      .attr('x', d => xScale(d.F1))
      .attr('y', d => yScale(d.F5) - radiusScale(d.stageData.votePct) - 4)
      .attr('text-anchor', 'middle')
      .style('fill', '#cbd5e1')
      .style('font-size', '10px')
      .style('pointer-events', 'none')
      .text(d => d.stageData.votePct > 0.1 ? d.name : '');

  }, [candidates, stage]);

  return (
    <svg ref={svgRef} width={W} height={H} style={{ maxWidth: '100%' }} />
  );
}

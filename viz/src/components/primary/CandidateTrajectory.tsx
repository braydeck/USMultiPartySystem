import { useState } from 'react';
import type { FDPrimaryCandidate } from '../../types';
import { getBlendColor } from '../../constants/parties';
import { CHART_TYPE, CHART_FILL } from '../../constants/typography';

interface Props {
  candidates: FDPrimaryCandidate[];
  stagesOrder: string[];
  stageLabels: Record<string, string>;
  quotaByStage: Record<string, number>;
}

const W = 560;
const H = 280;
const PAD = { top: 20, right: 60, bottom: 40, left: 44 };
const PLOT_W = W - PAD.left - PAD.right;
const PLOT_H = H - PAD.top - PAD.bottom;

function xPos(stageIdx: number, nStages: number): number {
  if (nStages <= 1) return PLOT_W / 2;
  return (stageIdx / (nStages - 1)) * PLOT_W;
}

function yPos(pct: number, maxPct: number): number {
  return PLOT_H - (pct / maxPct) * PLOT_H;
}

export function CandidateTrajectory({ candidates, stagesOrder, stageLabels, quotaByStage }: Props) {
  const [hovered, setHovered] = useState<string | null>(null);

  const nStages = stagesOrder.length;

  // Find the max pct across all candidates/stages for Y scaling
  let maxPct = 0;
  for (const c of candidates) {
    for (const s of stagesOrder) {
      const pct = c.stages[s]?.votePct ?? 0;
      if (pct > maxPct) maxPct = pct;
    }
  }
  maxPct = Math.max(maxPct * 1.12, 0.01); // 12% headroom

  // Quota line (use last stage quota, or first available)
  const quota = quotaByStage[stagesOrder[nStages - 1]] ?? quotaByStage[stagesOrder[0]] ?? 0;
  const quotaY = quota > 0 ? yPos(quota, maxPct) : null;

  // Y axis ticks
  const yTicks: number[] = [];
  const step = maxPct <= 0.2 ? 0.05 : maxPct <= 0.5 ? 0.1 : 0.15;
  for (let v = 0; v <= maxPct; v += step) {
    yTicks.push(v);
  }

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      style={{ width: '100%', height: 'auto', overflow: 'visible' }}
    >
      <g transform={`translate(${PAD.left},${PAD.top})`}>
        {/* Y-axis grid lines */}
        {yTicks.map(v => {
          const y = yPos(v, maxPct);
          return (
            <g key={v}>
              <line x1={0} y1={y} x2={PLOT_W} y2={y} stroke="#e2e8f0" strokeWidth={1} />
              <text x={-6} y={y} textAnchor="end" dominantBaseline="middle" fontSize={CHART_TYPE.inMark} fill={CHART_FILL.tick}>
                {(v * 100).toFixed(0)}%
              </text>
            </g>
          );
        })}

        {/* Quota dashed line */}
        {quotaY !== null && (
          <g>
            <line
              x1={0} y1={quotaY} x2={PLOT_W} y2={quotaY}
              stroke="#f59e0b" strokeWidth={1.5} strokeDasharray="5 4"
            />
            <text x={PLOT_W + 4} y={quotaY} dominantBaseline="middle" fontSize={CHART_TYPE.inMark} fill="#d97706" fontWeight={600}>
              quota
            </text>
          </g>
        )}

        {/* Stage x-axis labels */}
        {stagesOrder.map((s, i) => {
          const x = xPos(i, nStages);
          const label = stageLabels[s] ?? s;
          // Abbreviate long labels
          const short = label.replace('After ', '').replace(' States', '').replace('Pods ', '').replace('Pod ', '');
          return (
            <g key={s}>
              <line x1={x} y1={0} x2={x} y2={PLOT_H} stroke="#f1f5f9" strokeWidth={1} />
              <text x={x} y={PLOT_H + 18} textAnchor="middle" fontSize={CHART_TYPE.smallTick} fill={CHART_FILL.label}>
                {short}
              </text>
            </g>
          );
        })}

        {/* Candidate trajectories */}
        {candidates.map(c => {
          const party = (c as { party?: string }).party ?? c.code.split('_')[0];
          const color = getBlendColor(party);
          const isHovered = hovered === c.code;
          const isOther = hovered !== null && !isHovered;

          // Build points for stages where candidate has data
          const points: { x: number; y: number; stage: string; pct: number; status: string }[] = [];
          for (let i = 0; i < nStages; i++) {
            const s = stagesOrder[i];
            const sd = c.stages[s];
            if (!sd) continue;
            points.push({
              x: xPos(i, nStages),
              y: yPos(sd.votePct, maxPct),
              stage: s,
              pct: sd.votePct,
              status: sd.status,
            });
          }
          if (points.length < 2) return null;

          // Find where elimination happens
          const elimIdx = points.findIndex(p => p.status === 'eliminated_this_round');
          // Draw up to elimination (or to end if not eliminated)
          const drawPoints = elimIdx >= 0 ? points.slice(0, elimIdx + 1) : points;

          const pathD = drawPoints.map((p, i) =>
            i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`
          ).join(' ');

          const lastPoint = drawPoints[drawPoints.length - 1];
          const isEliminated = elimIdx >= 0;
          const isElected = points.some(p => p.status === 'elected');

          return (
            <g
              key={c.code}
              opacity={isOther ? 0.12 : isHovered ? 1 : 0.7}
              style={{ transition: 'opacity 0.15s', cursor: 'pointer' }}
              onMouseEnter={() => setHovered(c.code)}
              onMouseLeave={() => setHovered(null)}
            >
              {/* Line */}
              <path
                d={pathD}
                fill="none"
                stroke={color}
                strokeWidth={isHovered ? 2.5 : isElected ? 2 : 1.5}
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* Dots at each stage */}
              {drawPoints.map((p, i) => (
                <circle
                  key={i}
                  cx={p.x} cy={p.y} r={isHovered ? 3.5 : 2.5}
                  fill={color}
                  stroke="white"
                  strokeWidth={1}
                />
              ))}

              {/* × marker at elimination point */}
              {isEliminated && lastPoint && (
                <g transform={`translate(${lastPoint.x},${lastPoint.y})`}>
                  <line x1={-4} y1={-4} x2={4} y2={4} stroke={color} strokeWidth={2} />
                  <line x1={4} y1={-4} x2={-4} y2={4} stroke={color} strokeWidth={2} />
                </g>
              )}

              {/* Elected star */}
              {isElected && lastPoint && !isEliminated && (
                <circle cx={lastPoint.x} cy={lastPoint.y} r={4} fill={color} />
              )}

              {/* Label at last point (only when hovered, or for small sets) */}
              {isHovered && lastPoint && (
                <text
                  x={lastPoint.x + 6}
                  y={lastPoint.y}
                  dominantBaseline="middle"
                  fontSize={CHART_TYPE.smallTick}
                  fontWeight={600}
                  fill={color}
                >
                  {c.code}
                </text>
              )}
            </g>
          );
        })}

        {/* Axes */}
        <line x1={0} y1={0} x2={0} y2={PLOT_H} stroke="#cbd5e1" strokeWidth={1} />
        <line x1={0} y1={PLOT_H} x2={PLOT_W} y2={PLOT_H} stroke="#cbd5e1" strokeWidth={1} />
      </g>

      {/* Chart title */}
      <text x={PAD.left + PLOT_W / 2} y={10} textAnchor="middle" fontSize={CHART_TYPE.smallTick} fill={CHART_FILL.tick}>
        Hover a line to identify candidate
      </text>
    </svg>
  );
}

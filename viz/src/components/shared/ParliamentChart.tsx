import { useMemo, useState } from 'react';
import { getBlendColor, FACTOR_LABELS } from '../../constants/parties';
import { layoutSeatDots, INNER_R, RING_GAP } from '../../lib/parliamentLayout';
import type { ParliamentSegment } from '../../lib/parliamentLayout';

// Re-exported so existing `import type { ParliamentSegment } from '.../ParliamentChart'`
// call sites keep working; the layout itself lives in lib/parliamentLayout.
export type { ParliamentSegment };

interface Props {
  segments: ParliamentSegment[];  // pre-sorted by fVal ascending
  factor: string;
  globalRange?: [number, number]; // fixed min/max across all scenarios for stable labels
}

const CAT_LABELS = ['Very Low', 'Low', 'Medium', 'High', 'Very High'];
const DIV_FRACS  = [0.20, 0.40, 0.60, 0.80];
const MID_FRACS  = [0.10, 0.30, 0.50, 0.70, 0.90];

export function ParliamentChart({ segments, factor, globalRange }: Props) {
  const [hoveredCode, setHoveredCode] = useState<string | null>(null);

  const { groupedDots, nRings, dotSize } = useMemo(() => layoutSeatDots(segments), [segments]);

  const totalSeats = segments.reduce((s, seg) => s + seg.seats, 0);
  if (totalSeats === 0) return null;

  const outerR = INNER_R + RING_GAP * (nRings - 1);
  const labelR = outerR + 18;

  const VB_W = (outerR + 44) * 2;
  const oy = outerR + 52;
  const VB_H = oy + 22;
  const ox = VB_W / 2;

  const factorLabel = FACTOR_LABELS[factor] ?? factor;
  const minVal = segments[0]?.fVal ?? 0;
  const maxVal = segments[segments.length - 1]?.fVal ?? 1;
  const arcMinLabel = globalRange ? globalRange[0].toFixed(2) : minVal.toFixed(2);
  const arcMaxLabel = globalRange ? globalRange[1].toFixed(2) : maxVal.toFixed(2);

  return (
    <div>
      <svg
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        style={{ width: '100%', height: 'auto' }}
        aria-label={`Parliament chart ordered by ${factorLabel}`}
      >
        <g transform={`translate(${ox},${oy})`}>
          {/* Seat dots grouped by party */}
          {Object.entries(groupedDots).map(([code, positions]) => (
            <g
              key={code}
              opacity={hoveredCode && hoveredCode !== code ? 0.1 : 0.88}
              style={{ transition: 'opacity 0.15s' }}
            >
              {positions.map((pos, i) => (
                <rect
                  key={i}
                  x={pos.cx - dotSize / 2}
                  y={pos.cy - dotSize / 2}
                  width={dotSize}
                  height={dotSize}
                  fill={getBlendColor(code)}
                  rx={dotSize * 0.15}
                />
              ))}
            </g>
          ))}

          {/* Category divider lines */}
          {DIV_FRACS.map((df, i) => {
            const angle = Math.PI - df * Math.PI;
            const x1 = (INNER_R - 8) * Math.cos(angle);
            const y1 = -(INNER_R - 8) * Math.sin(angle);
            const x2 = (outerR + 6) * Math.cos(angle);
            const y2 = -(outerR + 6) * Math.sin(angle);
            return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#cbd5e1" strokeWidth={0.8} />;
          })}

          {/* Zone labels */}
          {MID_FRACS.map((mf, i) => {
            const angle = Math.PI - mf * Math.PI;
            const lx = labelR * Math.cos(angle);
            const ly = -labelR * Math.sin(angle);
            const anchor = i === 0 ? 'end' : i === 4 ? 'start' : 'middle';
            return (
              <text key={i} x={lx} y={ly} textAnchor={anchor} fontSize={7} fill="#94a3b8">
                {CAT_LABELS[i]}
              </text>
            );
          })}

          {/* Min/max value at arc ends */}
          <text x={-outerR - 6} y={4} textAnchor="end" fontSize={7} fill="#94a3b8">{arcMinLabel}</text>
          <text x={outerR + 6} y={4} textAnchor="start" fontSize={7} fill="#94a3b8">{arcMaxLabel}</text>
        </g>

        {/* Bottom axis label */}
        <text x={VB_W / 2} y={VB_H - 2} fontSize={8} fill="#94a3b8" textAnchor="middle">
          ← Low {factorLabel}  ·  High →
        </text>
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-2 px-1 justify-center">
        {segments.map(s => (
          <div
            key={s.code}
            className="flex items-center gap-1.5 cursor-default select-none"
            style={{ opacity: hoveredCode && hoveredCode !== s.code ? 0.35 : 1, transition: 'opacity 0.15s' }}
            tabIndex={0}
            onMouseEnter={() => setHoveredCode(s.code)}
            onMouseLeave={() => setHoveredCode(null)}
            onFocus={() => setHoveredCode(s.code)}
            onBlur={() => setHoveredCode(null)}
          >
            <div
              className="w-3 h-3 rounded-sm flex-shrink-0"
              style={{ backgroundColor: getBlendColor(s.code), opacity: 0.88 }}
            />
            <span className="text-xs font-semibold text-foreground">{s.code}</span>
            <span className="text-xs text-muted-foreground">{s.seats}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

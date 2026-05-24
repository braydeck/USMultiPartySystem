import { useMemo, useState } from 'react';
import { getBlendColor, FACTOR_LABELS } from '../../constants/parties';

export interface ParliamentSegment {
  code: string;
  seats: number;
  fVal: number;
}

interface Props {
  segments: ParliamentSegment[];  // pre-sorted by fVal ascending
  factor: string;
  globalRange?: [number, number]; // fixed min/max across all scenarios for stable category labels
}

function computeRings(total: number, innerR: number, ringGap: number): number[] {
  const nRings = Math.max(3, Math.ceil(Math.sqrt(total / 5)));
  const perims = Array.from({ length: nRings }, (_, i) => Math.PI * (innerR + ringGap * i));
  const totalPerim = perims.reduce((s, p) => s + p, 0);
  const raw = perims.map(p => (p / totalPerim) * total);
  const floored = raw.map(Math.floor);
  let rem = total - floored.reduce((s, n) => s + n, 0);
  const fracs = raw.map((v, i) => ({ i, f: v - floored[i] })).sort((a, b) => b.f - a.f);
  for (let k = 0; k < rem; k++) floored[fracs[k].i]++;
  return floored;
}

const CAT_LABELS = ['Very Low', 'Low', 'Medium', 'High', 'Very High'] as const;
const N_CATS = 5;

export function ParliamentChart({ segments, factor, globalRange }: Props) {
  const INNER_R = 60;
  const RING_GAP = 15;

  const [hoveredCode, setHoveredCode] = useState<string | null>(null);

  const { groupedDots, nRings, dotSize, dividers, catMidFracs } = useMemo(() => {
    const totalSeats = segments.reduce((s, seg) => s + seg.seats, 0);
    if (totalSeats === 0) return { groupedDots: {}, nRings: 3, dotSize: 4, dividers: [], catMidFracs: [] };

    const rings = computeRings(totalSeats, INNER_R, RING_GAP);
    const nRings = rings.length;

    const sumR = rings.reduce((s, _, i) => s + INNER_R + RING_GAP * i, 0);
    const spacing = Math.PI * sumR / totalSeats;
    const dotSize = Math.max(2.5, Math.min(10, spacing * 0.68));

    // Cumulative fraction ranges for wedge assignment
    const cumFracs: { code: string; start: number; end: number }[] = [];
    let cum = 0;
    for (const seg of segments) {
      const frac = seg.seats / totalSeats;
      cumFracs.push({ code: seg.code, start: cum, end: cum + frac });
      cum += frac;
    }
    if (cumFracs.length > 0) cumFracs[cumFracs.length - 1].end = 1.0001;

    // Generate dots grouped by party code for efficient opacity switching
    const groupedDots: Record<string, { cx: number; cy: number }[]> = {};
    for (let ring = 0; ring < nRings; ring++) {
      const n = rings[ring];
      const r = INNER_R + RING_GAP * ring;
      for (let i = 0; i < n; i++) {
        const frac = n === 1 ? 0.5 : i / (n - 1);
        let code = cumFracs[cumFracs.length - 1]?.code ?? '';
        for (const cf of cumFracs) {
          if (frac >= cf.start && frac < cf.end) { code = cf.code; break; }
        }
        const angle = Math.PI - frac * Math.PI;
        if (!groupedDots[code]) groupedDots[code] = [];
        groupedDots[code].push({ cx: r * Math.cos(angle), cy: -r * Math.sin(angle) });
      }
    }

    // Category dividers — use globalRange for stable absolute labels, fallback to scenario range
    const fVals = segments.map(s => s.fVal);
    const minF = globalRange ? globalRange[0] : Math.min(...fVals);
    const maxF = globalRange ? globalRange[1] : Math.max(...fVals);
    const fStep = (maxF - minF) / N_CATS;

    const allDividers: { arcFrac: number; value: number }[] = [];
    for (let i = 1; i < N_CATS; i++) {
      const threshold = minF + fStep * i;
      let cumulativeSeats = 0;
      for (const seg of segments) {
        if (seg.fVal <= threshold) cumulativeSeats += seg.seats;
      }
      allDividers.push({ arcFrac: cumulativeSeats / totalSeats, value: threshold });
    }

    const zoneEdges = [0, ...allDividers.map(d => d.arcFrac), 1];
    const zoneHasSeats = zoneEdges.slice(0, -1).map((start, i) => zoneEdges[i + 1] - start > 0.0005);

    const dividers = allDividers.filter((d, i) =>
      (zoneHasSeats[i] || zoneHasSeats[i + 1]) && d.arcFrac > 0.001 && d.arcFrac < 0.999
    );

    const catMidFracs = zoneEdges.slice(0, -1)
      .map((f, i) => zoneHasSeats[i] ? { label: CAT_LABELS[i], midFrac: (f + zoneEdges[i + 1]) / 2 } : null)
      .filter(Boolean) as { label: string; midFrac: number }[];

    // Guarantee at least one dot for every segment with seats.
    // Small segments (< 1 dot-width of the arc) can be skipped by the
    // evenly-spaced loop above; add a single dot at their arc midpoint
    // on the outermost ring so they always appear in the chart.
    const outerRingR = INNER_R + RING_GAP * (nRings - 1);
    for (const cf of cumFracs) {
      if (cf.end - cf.start > 0 && !groupedDots[cf.code]?.length) {
        const midFrac = (cf.start + cf.end) / 2;
        const angle = Math.PI - midFrac * Math.PI;
        if (!groupedDots[cf.code]) groupedDots[cf.code] = [];
        groupedDots[cf.code].push({
          cx: outerRingR * Math.cos(angle),
          cy: -outerRingR * Math.sin(angle),
        });
      }
    }

    return { groupedDots, nRings, dotSize, dividers, catMidFracs };
  }, [segments]);

  const totalSeats = segments.reduce((s, seg) => s + seg.seats, 0);
  if (totalSeats === 0) return null;

  const outerR = INNER_R + RING_GAP * (nRings - 1);
  const markerInner = INNER_R * 0.88;
  const markerOuter = outerR + 10;
  const labelR = outerR + 26;
  const tickR = outerR + 14;

  const VB_W = (outerR + 40) * 2;
  const oy = outerR + 52;
  const VB_H = oy + 22;
  const ox = VB_W / 2;

  const factorLabel = FACTOR_LABELS[factor] ?? factor;
  const minVal = segments[0]?.fVal ?? 0;
  const maxVal = segments[segments.length - 1]?.fVal ?? 1;
  // Show global anchor endpoints if provided, otherwise show scenario range
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
          {/* Seat dots grouped by party — hover dims non-selected */}
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

          {/* Category divider lines + value labels */}
          {dividers.map(({ arcFrac, value }, i) => {
            const angle = Math.PI - arcFrac * Math.PI;
            const cos = Math.cos(angle), sin = Math.sin(angle);
            return (
              <g key={i}>
                <line
                  x1={markerInner * cos} y1={-markerInner * sin}
                  x2={markerOuter * cos} y2={-markerOuter * sin}
                  stroke="#94a3b8" strokeWidth={1.2} strokeDasharray="4 3"
                />
                <text
                  x={tickR * cos} y={-tickR * sin}
                  textAnchor="middle" dominantBaseline="middle"
                  fontSize={6.5} fill="#94a3b8"
                >
                  {value.toFixed(2)}
                </text>
              </g>
            );
          })}

          {/* Category labels — only for zones with seats */}
          {catMidFracs.map(({ label, midFrac }) => {
            const angle = Math.PI - midFrac * Math.PI;
            const lx = labelR * Math.cos(angle);
            const ly = -labelR * Math.sin(angle);
            const rotDeg = (angle - Math.PI / 2) * (180 / Math.PI);
            return (
              <text
                key={label}
                x={lx} y={ly}
                textAnchor="middle" dominantBaseline="middle"
                fontSize={Math.max(6, dotSize * 1.0)}
                fontWeight={600} fill="#64748b"
                transform={`rotate(${rotDeg.toFixed(1)},${lx.toFixed(1)},${ly.toFixed(1)})`}
              >
                {label}
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

      {/* Legend — ordered left to right matching the arc */}
      <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-2 px-1 justify-center">
        {segments.map(s => (
          <div
            key={s.code}
            className="flex items-center gap-1.5 cursor-default select-none"
            style={{ opacity: hoveredCode && hoveredCode !== s.code ? 0.35 : 1, transition: 'opacity 0.15s' }}
            onMouseEnter={() => setHoveredCode(s.code)}
            onMouseLeave={() => setHoveredCode(null)}
          >
            <div
              className="w-3 h-3 rounded-sm flex-shrink-0"
              style={{ backgroundColor: getBlendColor(s.code), opacity: 0.88 }}
            />
            <span className="text-xs font-semibold text-slate-700">{s.code}</span>
            <span className="text-xs text-slate-400">{s.seats}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

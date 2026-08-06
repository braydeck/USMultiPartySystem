import { useMemo, useState } from 'react';
import { getBlendColor, FACTOR_LABELS } from '../../constants/parties';
import { layoutSeatDots, INNER_R, RING_GAP } from '../../lib/parliamentLayout';
import type { ParliamentSegment } from '../../lib/parliamentLayout';
import { CHART_TYPE, CHART_FILL } from '../../constants/typography';

// Re-exported so existing `import type { ParliamentSegment } from '.../ParliamentChart'`
// call sites keep working; the layout itself lives in lib/parliamentLayout.
export type { ParliamentSegment };

interface Props {
  segments: ParliamentSegment[];  // pre-sorted by fVal ascending
  factor: string;
  globalRange?: [number, number]; // fixed min/max across all scenarios for stable labels
}

const CAT_LABELS = ['Very Low', 'Low', 'Medium', 'High', 'Very High'];

/** Band divider line color — kept local rather than CHART_FILL.faint so it can be tuned
 *  without affecting SeatDistributionBar/EliminationWaterfall's axis ticks. */
/**const DIVIDER_STROKE = CHART_FILL.faint;
 */
const DIVIDER_STROKE = "#979dac"
/**
 * Band edges on the factor score itself.
 *
 * These used to be fixed angular fractions — 20/40/60/80% of the way round the arc — so
 * they cut the chamber into five equal *seat* quintiles no matter what. That made the
 * labels lie: a party sat in "Very High" because it held the rightmost fifth of the
 * seats, not because its score was high, and the dividers never moved when the reader
 * changed factor. Cutting on the score instead means band widths carry the finding:
 * how much of the chamber actually sits in each band, which is the question the chart
 * looks like it is answering. Factor scores are standardised, and party means run about
 * -1.3 to +1.5, so ±0.25 / ±0.75 splits that range rather than leaving the tails empty.
 */
const BAND_EDGES = [-0.75, -0.25, 0.25, 0.75];

/** Band index (0-4) for a factor score. */
function bandOf(v: number): number {
  let i = 0;
  while (i < BAND_EDGES.length && v >= BAND_EDGES[i]) i++;
  return i;
}

/**
 * One seat, as a pointy-top hexagon of circumradius r.
 *
 * Matches the seat cartogram, where a hexagon is also exactly one seat — so the same
 * shape means the same thing on both charts.
 */
function hexAt(cx: number, cy: number, r: number): string {
  let d = '';
  for (let k = 0; k < 6; k++) {
    const a = (k * Math.PI) / 3;
    d += `${k ? 'L' : 'M'}${(cx + r * Math.sin(a)).toFixed(2)} ${(cy + r * Math.cos(a)).toFixed(2)}`;
  }
  return d + 'Z';
}

export function ParliamentChart({ segments, factor, globalRange }: Props) {
  const [hoveredCode, setHoveredCode] = useState<string | null>(null);

  const { groupedDots, nRings, dotSize, slotFracs } = useMemo(() => layoutSeatDots(segments), [segments]);

  const totalSeats = segments.reduce((s, seg) => s + seg.seats, 0);
  if (totalSeats === 0) return null;

  const outerR = INNER_R + RING_GAP * (nRings - 1);
  const labelR = outerR + 18;

  // Wide enough for a band label sitting flat against the arc end: "Very Low" is set
  // end-anchored there and ran off the edge at the old 44.
  const VB_W = (outerR + 78) * 2;
  const oy = outerR + 52;
  const VB_H = oy + 22;
  const ox = VB_W / 2;

  const factorLabel = FACTOR_LABELS[factor] ?? factor;

  // Where each band starts and ends, as the actual frac each dot was placed at (not
  // seen/totalSeats — rings hold uneven dot counts, so a uniform fraction drifts off the
  // true seat gap and the divider line ends up slicing through hexes instead of between
  // them). Seats are laid out in fVal order, so a band is a contiguous run of slots and
  // its edges fall on party boundaries.
  const bands = (() => {
    const spans: { band: number; from: number; to: number }[] = [];
    let seen = 0;
    for (const seg of segments) {
      const b = bandOf(seg.fVal);
      const from = slotFracs[seen] ?? 0;
      seen += seg.seats;
      const to = slotFracs[seen] ?? 1;
      const last = spans[spans.length - 1];
      if (last && last.band === b) last.to = to;
      else spans.push({ band: b, from, to });
    }
    return spans;
  })();
  const minVal = segments[0]?.fVal ?? 0;
  const maxVal = segments[segments.length - 1]?.fVal ?? 1;
  const arcMinLabel = globalRange ? globalRange[0].toFixed(2) : minVal.toFixed(2);
  const arcMaxLabel = globalRange ? globalRange[1].toFixed(2) : maxVal.toFixed(2);

  return (
    <div>
      <svg
        viewBox={`0 0 ${VB_W} ${VB_H}`}
        // Capped: the hemicycle is about 2:1, so at full width on a wide monitor it runs
        // taller than the viewport for no gain in legibility.
        style={{ width: '100%', height: 'auto', maxWidth: 760, display: 'block', margin: '0 auto' }}
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
                <path key={i} d={hexAt(pos.cx, pos.cy, dotSize * 0.62)} fill={getBlendColor(code)} />
              ))}
            </g>
          ))}

          {/* Band dividers, at the seat where the factor score crosses an edge */}
          {bands.slice(1).map((b, i) => {
            const angle = Math.PI - b.from * Math.PI;
            const x1 = (INNER_R - 8) * Math.cos(angle);
            const y1 = -(INNER_R - 8) * Math.sin(angle);
            const x2 = (outerR + 6) * Math.cos(angle);
            const y2 = -(outerR + 6) * Math.sin(angle);
            return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={DIVIDER_STROKE} strokeWidth={2} />;
          })}

          {/* Band labels, centred on the band. Only bands that hold seats get one. */}
          {bands.map((b, i) => {
            const mid = (b.from + b.to) / 2;
            const angle = Math.PI - mid * Math.PI;
            const lx = labelR * Math.cos(angle);
            const ly = -labelR * Math.sin(angle);
            const anchor = mid < 0.12 ? 'end' : mid > 0.88 ? 'start' : 'middle';
            return (
              <text key={i} x={lx} y={ly} textAnchor={anchor} fontSize={'10'} fill={'#6c757d'}>
                {CAT_LABELS[b.band]}
              </text>
            );
          })}

          {/* Min/max value at arc ends */}
          <text x={-outerR - 6} y={4} textAnchor="end" fontSize={CHART_TYPE.inMark} fill={CHART_FILL.tick}>{arcMinLabel}</text>
          <text x={outerR + 6} y={4} textAnchor="start" fontSize={CHART_TYPE.inMark} fill={CHART_FILL.tick}>{arcMaxLabel}</text>
        </g>

        {/* Bottom axis label */}
        <text x={VB_W / 2} y={VB_H - 2} fontSize={CHART_TYPE.inMark} fill={CHART_FILL.tick} textAnchor="middle">
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

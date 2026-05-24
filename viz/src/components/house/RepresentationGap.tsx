import type { HouseSeat } from '../../types';
import { CLUSTER_TO_PARTY, PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';

// Ideological order F5 low → high: PRG, LIB, DSA, SD, STY, CTR, CON, REF, NAT
const F5_CLUSTER_ORDER = [9, 4, 8, 1, 2, 6, 0, 5, 3];

interface Props {
  seats: HouseSeat[];
  seatsProbBased: HouseSeat[];
}

export function RepresentationGap({ seats, seatsProbBased }: Props) {
  const byCluster      = Object.fromEntries(seats.map(s => [s.party, s]));
  const byClusterProb  = Object.fromEntries(seatsProbBased.map(s => [s.party, s]));

  const rows = F5_CLUSTER_ORDER
    .map(cluster => {
      const seat     = byCluster[cluster];
      const seatProb = byClusterProb[cluster];
      if (!seat && !seatProb) return null;
      const code = CLUSTER_TO_PARTY[String(cluster)] ?? '';
      const popPct      = seat?.pctPopulation ?? seatProb?.pctPopulation ?? 0;
      const gaussPct    = seat?.pctNational ?? 0;
      const probPct     = seatProb?.pctNational ?? 0;
      return {
        cluster,
        code,
        name:       PARTY_NAMES[code] ?? code,
        color:      PARTY_COLORS[code] ?? '#888',
        popPct,
        gaussPct,
        probPct,
        gaussDelta: gaussPct - popPct,
        probDelta:  probPct  - popPct,
      };
    })
    .filter((r): r is NonNullable<typeof r> => r !== null);

  // SVG layout constants
  const LABEL_W  = 96;
  const CHART_L  = LABEL_W + 8;
  const CHART_R  = 460;
  const DELTA1_X = CHART_R + 10;
  const DELTA2_X = CHART_R + 72;
  const ROW_H    = 34;
  const HEADER_H = 24;
  const MAX_PCT  = 26;
  const SVG_W    = 650;
  const SVG_H    = HEADER_H + rows.length * ROW_H + 8;

  const xScale = (pct: number) =>
    CHART_L + (pct / MAX_PCT) * (CHART_R - CHART_L);

  const ticks = [0, 5, 10, 15, 20, 25];

  return (
    <div>
      <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
        Representation vs. Population
      </h3>
      <p className="text-xs text-slate-500 mb-3">
        Hollow circle = weighted population share. Filled circle = Gaussian/positional seats.
        Diamond = prob-cluster seats. Sorted ideologically F5 low → high.
      </p>

      <svg viewBox={`0 0 ${SVG_W} ${SVG_H}`} className="w-full" aria-label="Representation gap dumbbell chart">

        {/* Column headers */}
        <text x={DELTA1_X + 28} y={HEADER_H - 8} textAnchor="middle" fontSize={8} fill="#94a3b8" fontStyle="italic">Gauss Δ</text>
        <text x={DELTA2_X + 28} y={HEADER_H - 8} textAnchor="middle" fontSize={8} fill="#94a3b8" fontStyle="italic">Prob Δ</text>

        {/* Grid lines + tick labels */}
        {ticks.map(t => (
          <g key={t}>
            <line
              x1={xScale(t)} y1={HEADER_H - 4}
              x2={xScale(t)} y2={SVG_H - 4}
              stroke="#e2e8f0" strokeWidth={1}
            />
            <text x={xScale(t)} y={HEADER_H - 8} textAnchor="middle" fontSize={9} fill="#94a3b8">
              {t}%
            </text>
          </g>
        ))}

        {/* Rows */}
        {rows.map((row, i) => {
          const cy       = HEADER_H + i * ROW_H + ROW_H / 2;
          const xPop     = xScale(row.popPct);
          const xGauss   = xScale(row.gaussPct);
          const xProb    = xScale(row.probPct);
          const xLeft    = Math.min(xPop, xGauss, xProb);
          const xRight   = Math.max(xPop, xGauss, xProb);
          const isOver   = row.gaussDelta >= 0;
          const lineColor = isOver ? '#16a34a' : '#dc2626';

          const fmtDelta = (d: number) => (d >= 0 ? '+' : '') + d.toFixed(1) + 'pp';
          const gaussOver = row.gaussDelta >= 0;
          const probOver  = row.probDelta  >= 0;

          // Diamond path: 4-point polygon at (cx, cy) with half-width r
          const diamond = (cx: number, r: number) =>
            `${cx},${cy - r} ${cx + r},${cy} ${cx},${cy + r} ${cx - r},${cy}`;

          return (
            <g key={row.cluster}>
              {/* Zebra row background */}
              {i % 2 === 0 && (
                <rect x={0} y={HEADER_H + i * ROW_H} width={SVG_W} height={ROW_H}
                  fill="#f8fafc" />
              )}

              {/* Party label */}
              <text
                x={LABEL_W} y={cy + 1}
                textAnchor="end" dominantBaseline="middle"
                fontSize={11} fontWeight={700} fill={row.color}
              >
                {row.code}
              </text>
              <text
                x={LABEL_W - 28} y={cy + 1}
                textAnchor="end" dominantBaseline="middle"
                fontSize={9} fill="#94a3b8"
              >
                {row.name.slice(0, 8)}
              </text>

              {/* Connecting line spanning full range */}
              {xRight - xLeft > 1 && (
                <line
                  x1={xLeft} y1={cy} x2={xRight} y2={cy}
                  stroke="#cbd5e1" strokeWidth={2} strokeLinecap="round"
                />
              )}

              {/* Gaussian segment line */}
              {Math.abs(row.gaussDelta) > 0.1 && (
                <line
                  x1={Math.min(xPop, xGauss)} y1={cy}
                  x2={Math.max(xPop, xGauss)} y2={cy}
                  stroke={lineColor} strokeWidth={2.5} strokeLinecap="round"
                  strokeOpacity={0.7}
                />
              )}

              {/* Population dot — hollow */}
              <circle cx={xPop} cy={cy} r={5}
                fill="white" stroke={row.color} strokeWidth={2} />

              {/* Gaussian seats — filled circle */}
              <circle cx={xGauss} cy={cy} r={6}
                fill={row.color} />

              {/* Prob seats — filled diamond */}
              <polygon
                points={diamond(xProb, 6)}
                fill={row.color} opacity={0.65}
              />

              {/* Gaussian delta label */}
              <text
                x={DELTA1_X} y={cy + 1}
                textAnchor="start" dominantBaseline="middle"
                fontSize={10} fontWeight={700}
                fill={gaussOver ? '#16a34a' : '#dc2626'}
              >
                {fmtDelta(row.gaussDelta)}
              </text>

              {/* Prob delta label */}
              <text
                x={DELTA2_X} y={cy + 1}
                textAnchor="start" dominantBaseline="middle"
                fontSize={10} fontWeight={600}
                fill={probOver ? '#16a34a' : '#dc2626'}
                opacity={0.8}
              >
                {fmtDelta(row.probDelta)}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap gap-5 mt-2 text-xs text-slate-500">
        <span className="flex items-center gap-1.5">
          <svg width={14} height={14} className="shrink-0">
            <circle cx={7} cy={7} r={5} fill="none" stroke="#64748b" strokeWidth={2} />
          </svg>
          Population share
        </span>
        <span className="flex items-center gap-1.5">
          <svg width={14} height={14} className="shrink-0">
            <circle cx={7} cy={7} r={6} fill="#64748b" />
          </svg>
          Gaussian seats
        </span>
        <span className="flex items-center gap-1.5">
          <svg width={14} height={14} className="shrink-0">
            <polygon points="7,1 13,7 7,13 1,7" fill="#64748b" opacity={0.65} />
          </svg>
          Prob-cluster seats
        </span>
        <span className="flex items-center gap-1.5">
          <svg width={20} height={14} className="shrink-0">
            <line x1={0} y1={7} x2={20} y2={7} stroke="#16a34a" strokeWidth={2.5} />
          </svg>
          Over-represented (Gauss)
        </span>
        <span className="flex items-center gap-1.5">
          <svg width={20} height={14} className="shrink-0">
            <line x1={0} y1={7} x2={20} y2={7} stroke="#dc2626" strokeWidth={2.5} />
          </svg>
          Under-represented (Gauss)
        </span>
      </div>
    </div>
  );
}

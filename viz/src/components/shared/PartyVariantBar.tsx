import { useMemo, useRef, useState } from 'react';
import type { FDHouseSeat } from '../../types';
import { F5_ORDER_WFP as F5_ORDER, getFDColor } from '../../constants/parties';

interface Props {
  seats: FDHouseSeat[];
  totalLabel?: string;
}

const VARIANT_ORDER = [
  'base',
  'hi_so', 'lo_so',
  'hi_es', 'lo_es',
  'hi_pc', 'lo_pc',
] as const;
type VariantKey = typeof VARIANT_ORDER[number];

const AXIS_PATTERN_ID: Record<string, string> = {
  so: 'pvb_stripe_so',
  es: 'pvb_stripe_es',
  pc: 'pvb_stripe_pc',
};

const AXIS_FULL: Record<string, string> = {
  so: 'Security & Order',
  es: 'Electoral Skepticism',
  pc: 'Populist Conservatism',
};

function getAxis(vk: VariantKey): string | null {
  return vk === 'base' ? null : vk.split('_').slice(1).join('_');
}

function getDir(vk: VariantKey): 'base' | 'hi' | 'lo' {
  if (vk === 'base') return 'base';
  return vk.startsWith('hi_') ? 'hi' : 'lo';
}

const BAR_H    = 26;
const ROW_GAP  = 10;
const LABEL_W  = 56;
const END_PAD  = 46;
const SVG_W    = 740;
const BAR_AREA = SVG_W - LABEL_W - END_PAD;

interface Tip { x: number; y: number; lines: string[] }

export function PartyVariantBar({ seats, totalLabel }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [tip, setTip] = useState<Tip | null>(null);

  const { rows, maxTotal, grandTotal } = useMemo(() => {
    const byPV: Record<string, Record<string, number>> = {};
    let grandTotal = 0;

    for (const seat of seats) {
      const vk = seat.axis === 'base' ? 'base' : `${seat.direction}_${seat.axis}`;
      if (!byPV[seat.party]) byPV[seat.party] = {};
      byPV[seat.party][vk] = (byPV[seat.party][vk] ?? 0) + seat.national;
      grandTotal += seat.national;
    }

    const present = F5_ORDER.filter(p => byPV[p] != null);
    let maxTotal = 1;

    const rows = present.map(party => {
      const total = Object.values(byPV[party]).reduce((s, v) => s + v, 0);
      if (total > maxTotal) maxTotal = total;
      const segments = VARIANT_ORDER
        .filter(vk => (byPV[party][vk] ?? 0) > 0)
        .map(vk => ({ vk, count: byPV[party][vk] }));
      return { party, total, segments };
    });

    return { rows, maxTotal, grandTotal };
  }, [seats]);

  if (rows.length === 0) return null;

  const svgH = rows.length * (BAR_H + ROW_GAP) + 4;
  const px = (n: number) => (n / maxTotal) * BAR_AREA;

  const onEnter = (e: React.MouseEvent, party: string, vk: VariantKey, count: number) => {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    const axis = getAxis(vk);
    const dir  = getDir(vk);
    setTip({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      lines: [
        `${party} · ${vk}`,
        axis ? `${AXIS_FULL[axis]} (${dir})` : 'Base party',
        `${count} seats`,
      ],
    });
  };

  return (
    <div className="relative">
      {totalLabel != null && (
        <div className="text-xs text-muted-foreground mb-2">
          {totalLabel} — {grandTotal.toLocaleString()} total
        </div>
      )}

      <div className="relative w-full overflow-x-auto">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${SVG_W} ${svgH}`}
          className="w-full"
          style={{ minWidth: 480 }}
          onMouseLeave={() => setTip(null)}
          aria-label="Party variant distribution"
        >
          <defs>
            {/* Diagonal stripes — SO axis */}
            <pattern id="pvb_stripe_so" patternUnits="userSpaceOnUse" width="8" height="8">
              <line x1="0" y1="8" x2="8" y2="0" stroke="rgba(255,255,255,0.40)" strokeWidth="2.2" />
            </pattern>
            {/* Horizontal stripes — ES axis */}
            <pattern id="pvb_stripe_es" patternUnits="userSpaceOnUse" width="8" height="8">
              <line x1="0" y1="4" x2="8" y2="4" stroke="rgba(255,255,255,0.40)" strokeWidth="2.2" />
            </pattern>
            {/* Vertical stripes — PC axis */}
            <pattern id="pvb_stripe_pc" patternUnits="userSpaceOnUse" width="8" height="8">
              <line x1="4" y1="0" x2="4" y2="8" stroke="rgba(255,255,255,0.40)" strokeWidth="2.2" />
            </pattern>
          </defs>

          {rows.map((row, ri) => {
            const y   = ri * (BAR_H + ROW_GAP) + 2;
            const barW = px(row.total);
            let   x   = LABEL_W;

            return (
              <g key={row.party}>
                {/* Party label */}
                <text
                  x={LABEL_W - 7} y={y + BAR_H / 2}
                  textAnchor="end" dominantBaseline="central"
                  fontSize={12} fontWeight={700} fill="#475569"
                >
                  {row.party}
                </text>

                {/* Clip to rounded bar shape */}
                <clipPath id={`pvb_clip_${row.party}`}>
                  <rect x={LABEL_W} y={y} width={barW} height={BAR_H} rx={4} />
                </clipPath>

                <g clipPath={`url(#pvb_clip_${row.party})`}>
                  {row.segments.map(({ vk, count }) => {
                    const w      = px(count);
                    const segX   = x;
                    x += w;
                    const dir    = getDir(vk);
                    const axis   = getAxis(vk);
                    const fill   = getFDColor(row.party, dir);
                    const patId  = axis ? (AXIS_PATTERN_ID[axis] ?? null) : null;
                    const wide   = w >= 34;

                    return (
                      <g
                        key={vk}
                        style={{ cursor: 'pointer' }}
                        onMouseMove={(e) => onEnter(e, row.party, vk, count)}
                        onMouseLeave={() => setTip(null)}
                      >
                        {/* Party color base */}
                        <rect x={segX} y={y} width={w} height={BAR_H} fill={fill} />
                        {/* Axis pattern overlay */}
                        {patId && (
                          <rect x={segX} y={y} width={w} height={BAR_H} fill={`url(#${patId})`} />
                        )}
                        {/* Segment divider */}
                        {segX > LABEL_W && (
                          <line
                            x1={segX} y1={y} x2={segX} y2={y + BAR_H}
                            stroke="rgba(255,255,255,0.45)" strokeWidth={1}
                          />
                        )}
                        {/* Inline label */}
                        {wide && vk !== 'base' && (
                          <text
                            x={segX + w / 2} y={y + BAR_H / 2}
                            textAnchor="middle" dominantBaseline="central"
                            fontSize={9} fontWeight={700}
                            fill="rgba(255,255,255,0.93)"
                            style={{ pointerEvents: 'none', userSelect: 'none' }}
                          >
                            {vk}
                          </text>
                        )}
                      </g>
                    );
                  })}
                </g>

                {/* Total seat count */}
                <text
                  x={LABEL_W + barW + 6} y={y + BAR_H / 2}
                  dominantBaseline="central"
                  fontSize={11} fill="#94a3b8"
                >
                  {row.total}
                </text>
              </g>
            );
          })}
        </svg>

        {tip && (
          <div
            className="pointer-events-none absolute z-10 rounded bg-slate-800 px-2 py-1.5 text-xs text-white shadow-lg"
            style={{ left: tip.x + 14, top: tip.y - 40, maxWidth: 210 }}
            role="status"
            aria-live="polite"
          >
            {tip.lines.map((l, i) => (
              <div key={i} className={i === 0 ? 'font-semibold' : 'text-slate-300 mt-0.5'}>{l}</div>
            ))}
          </div>
        )}
      </div>

      {/* Pattern legend */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 mt-3 text-xs text-muted-foreground">
        <span className="font-semibold text-muted-foreground">Axis patterns:</span>

        {/* SO — diagonal */}
        <span className="flex items-center gap-1.5">
          <svg width="22" height="14" style={{ flexShrink: 0 }}>
            <rect width="22" height="14" fill="#94a3b8" rx={2} />
            <line x1="0"  y1="14" x2="14" y2="0"  stroke="rgba(255,255,255,0.7)" strokeWidth="2.2" />
            <line x1="8"  y1="14" x2="22" y2="0"  stroke="rgba(255,255,255,0.7)" strokeWidth="2.2" />
          </svg>
          <span>diagonal = SO</span>
        </span>

        {/* AE — horizontal */}
        <span className="flex items-center gap-1.5">
          <svg width="22" height="14" style={{ flexShrink: 0 }}>
            <rect width="22" height="14" fill="#94a3b8" rx={2} />
            <line x1="0" y1="4.5" x2="22" y2="4.5" stroke="rgba(255,255,255,0.7)" strokeWidth="2.2" />
            <line x1="0" y1="10"  x2="22" y2="10"   stroke="rgba(255,255,255,0.7)" strokeWidth="2.2" />
          </svg>
          <span>horizontal = AE</span>
        </span>

        {/* PC — vertical */}
        <span className="flex items-center gap-1.5">
          <svg width="22" height="14" style={{ flexShrink: 0 }}>
            <rect width="22" height="14" fill="#94a3b8" rx={2} />
            <line x1="6"  y1="0" x2="6"  y2="14" stroke="rgba(255,255,255,0.7)" strokeWidth="2.2" />
            <line x1="14" y1="0" x2="14" y2="14" stroke="rgba(255,255,255,0.7)" strokeWidth="2.2" />
          </svg>
          <span>vertical = PC</span>
        </span>

        <span className="text-muted-foreground">· lighter tint = hi variant, darker = lo</span>
      </div>
    </div>
  );
}

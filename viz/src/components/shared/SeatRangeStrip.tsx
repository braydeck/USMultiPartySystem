import { useMemo } from 'react';
import { PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';
import { SeatWhisker } from './SeatWhisker';
import type { SeatInterval } from '../../lib/uncertainty';

/** Compact always-visible range rows, one per seat-holding party: the 95% span, the
 *  expected value, and a tick at the most likely count. Used where the chamber bar is
 *  stacked and an inline whisker would overlap into neighbouring parties' segments. */
export function SeatRangeStrip({ seats, order, label, max: maxOverride }: {
  seats: Record<string, SeatInterval>;
  order: string[];
  label: string;
  /** Shared axis ceiling across sibling strips, e.g. when a Condorcet and an IRV strip sit
   *  stacked and must read on the same scale for their bar positions to be comparable. Falls
   *  back to this strip's own largest `hi` when omitted. */
  max?: number;
}) {
  const rows = useMemo(
    () => order
      .map(p => ({ party: p, iv: seats[p] }))
      .filter((r): r is { party: string; iv: SeatInterval } =>
        !!r.iv && (r.iv.modal > 0 || r.iv.hi > 0)),
    [seats, order],
  );
  const selfMax = useMemo(() => Math.max(1, ...rows.map(r => r.iv.hi)), [rows]);
  const max = maxOverride ?? selfMax;

  if (!rows.length) return null;

  return (
    <div className="space-y-1 pt-1">
      <div className="text-[10px] text-muted-foreground">{label}</div>
      {rows.map(({ party, iv }) => {
        const color = PARTY_COLORS[party] ?? '#6b7280';
        return (
          <div key={party} className="flex items-center gap-2">
            <span className="w-10 shrink-0 text-[10px] font-bold text-right" style={{ color }}>
              {party}
            </span>
            <div className="relative flex-1 h-4 rounded bg-muted/50">
              <div className="absolute inset-y-1 rounded-sm" style={{
                left: `${(iv.lo / max) * 100}%`,
                width: `${((iv.hi - iv.lo) / max) * 100}%`,
                backgroundColor: color,
                opacity: 0.28,
              }} />
              <SeatWhisker lo={iv.lo} hi={iv.hi} centre={iv.expected} max={max}
                title={`${PARTY_NAMES[party] ?? party}: ${iv.lo}–${iv.hi} seats across resamples, ${iv.expected.toFixed(1)} expected`} />
              <div className="absolute inset-y-0 w-0.5" title={`most likely: ${iv.modal}`}
                style={{ left: `${(iv.modal / max) * 100}%`, backgroundColor: color }} />
            </div>
            <span className="w-24 shrink-0 text-[10px] tabular-nums text-muted-foreground">
              <span className="font-semibold text-foreground">{iv.modal}</span> · {iv.lo}–{iv.hi}
            </span>
          </div>
        );
      })}
      <div className="flex items-center gap-2">
        <span className="w-10 shrink-0" />
        <div className="flex-1 flex justify-between text-[9px] text-muted-foreground">
          <span>0</span><span>{max} seats</span>
        </div>
        <span className="w-24 shrink-0" />
      </div>
    </div>
  );
}

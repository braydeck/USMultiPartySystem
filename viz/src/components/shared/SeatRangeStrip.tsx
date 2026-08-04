import { useMemo } from 'react';
import { PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';
import { SeatWhisker } from './SeatWhisker';
import { rangeAxisMax } from '../../lib/whisker';
import type { SeatInterval } from '../../lib/uncertainty';

/** Compact always-visible range rows, one per seat-holding party: the 95% span, the
 *  expected value, and a tick at the most likely count. Used where the chamber bar is
 *  stacked and an inline whisker would overlap into neighbouring parties' segments. */
/** Visual key for the three marks. Neutral-coloured so it reads as a key rather than as one
 *  party's row; each swatch is drawn with the same styles the rows use. Exported because a stack
 *  of strips needs one key above the group, not one per strip. */
export function RangeKey() {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-4xs text-muted-foreground">
      <span className="flex items-center gap-1.5">
        <span className="w-5 h-2.5 rounded-sm bg-foreground/25" />
        95% of resamples
      </span>
      <span className="flex items-center gap-1.5">
        <span className="relative w-5 h-2.5">
          <span className="absolute inset-y-0 left-1/2 -ml-px w-0.5 bg-foreground/70" />
        </span>
        reported
      </span>
      <span className="flex items-center gap-1.5">
        <span className="relative w-5 h-2.5">
          <span className="absolute top-1/2 left-1/2 -mt-[3px] -ml-[3px] w-1.5 h-1.5 rounded-full bg-foreground/85" />
        </span>
        expected
      </span>
    </div>
  );
}

export function SeatRangeStrip({ seats, order, label, max: maxOverride, chamber }: {
  seats: Record<string, SeatInterval>;
  order: string[];
  label: string;
  /** The chamber actually reported, when it is not the per-draw modal count — the senate
   *  splits contested states, which is a function of the whole distribution rather than of
   *  any one draw. The span still describes how far the underlying races move. */
  chamber?: Record<string, number>;
  /** Shared axis ceiling across sibling strips, e.g. when a Condorcet and an IRV strip sit
   *  stacked and must read on the same scale for their bar positions to be comparable. Falls
   *  back to this strip's own largest `hi` when omitted. */
  max?: number;
}) {
  const rows = useMemo(
    () => order
      .map(p => ({ party: p, iv: seats[p], point: chamber ? (chamber[p] ?? 0) : (seats[p]?.modal ?? 0) }))
      .filter((r): r is { party: string; iv: SeatInterval; point: number } =>
        !!r.iv && (r.point > 0 || r.iv.hi > 0)),
    [seats, order, chamber],
  );
  const max = useMemo(() => rangeAxisMax(rows.map(r => r.iv.hi), maxOverride), [rows, maxOverride]);

  if (!rows.length) return null;

  return (
    <div className="space-y-1 pt-1">
      <div className="text-3xs text-muted-foreground">{label}</div>
      {rows.map(({ party, iv, point }) => {
        const color = PARTY_COLORS[party] ?? '#6b7280';
        return (
          <div key={party} className="flex items-center gap-2">
            <span className="w-10 shrink-0 text-3xs font-bold text-right" style={{ color }}>
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
              {/* The reported chamber is built per state, so it is not bounded by `hi`;
                  clamp only the tick's position, never the value it reports. */}
              <div className="absolute inset-y-0 w-0.5" title={`reported: ${point}`}
                style={{ left: `${Math.min(100, (point / max) * 100)}%`, backgroundColor: color }} />
            </div>
            <span className="w-24 shrink-0 text-3xs tabular-nums text-muted-foreground">
              <span className="font-semibold text-foreground">{point}</span> · {iv.lo}–{iv.hi}
            </span>
          </div>
        );
      })}
      <div className="flex items-center gap-2">
        <span className="w-10 shrink-0" />
        <div className="flex-1 flex justify-between text-4xs text-muted-foreground">
          <span>0</span><span>{max} seats</span>
        </div>
        <span className="w-24 shrink-0" />
      </div>
    </div>
  );
}

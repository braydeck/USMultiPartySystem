import { useMemo } from 'react';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER, getContrastText } from '../../constants/parties';
import type { SeatTotals } from '../../lib/seatTotals';

/**
 * Party highlight pills, shared by the seat cartogram and the grid.
 *
 * One control for both views: the pills carry the colour key, so they double as the
 * legend and a second list of the same ten names would be redundant. Multi-select rather
 * than one-at-a-time, so a coalition can be assembled and read as a single footprint —
 * which is why the seat tally sits against the majority threshold.
 */

interface Props {
  totals: SeatTotals;
  value: ReadonlySet<string>;
  onChange: (next: ReadonlySet<string>) => void;
}

export function PartyHighlightFilter({ totals, value, onChange }: Props) {
  const parties = useMemo(
    () => F5_ORDER.filter(p => (totals.per[p] ?? 0) > 0),
    [totals],
  );
  const picked = parties.filter(p => value.has(p));
  const pickedSeats = picked.reduce((s, p) => s + (totals.per[p] ?? 0), 0);
  const majority = Math.floor(totals.all / 2) + 1;

  const toggle = (p: string) => {
    const next = new Set(value);
    if (!next.delete(p)) next.add(p);
    onChange(next);
  };

  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5">
      <span className="text-xs font-semibold text-muted-foreground">Highlight:</span>

      {parties.map(p => {
        const color = PARTY_COLORS[p] ?? '#6b7280';
        const on = value.has(p);
        const off = value.size > 0 && !on;
        return (
          <button
            key={p}
            onClick={() => toggle(p)}
            aria-pressed={on}
            title={`${PARTY_NAMES[p]} — ${totals.per[p] ?? 0} seats`}
            className="text-xs font-semibold px-2 py-0.5 rounded-full border transition-all hover:opacity-100"
            style={{
              borderColor: color,
              color: on ? getContrastText(color) : color,
              backgroundColor: on ? color : 'transparent',
              opacity: off ? 0.4 : 1,
            }}
          >
            {/* Full names while there is room for them; the codes are what survive a
                narrow window, and the colour carries the identity either way. */}
            <span className="hidden xl:inline">{PARTY_NAMES[p] ?? p}</span>
            <span className="xl:hidden">{p}</span>
          </button>
        );
      })}

      {picked.length > 0 && (
        <>
          <span className="text-xs tabular-nums font-semibold text-foreground ml-1">
            {pickedSeats} of {totals.all} ({(pickedSeats / (totals.all || 1) * 100).toFixed(1)}%)
          </span>
          <span className={`text-xs ${pickedSeats >= majority ? 'text-emerald-700 font-semibold' : 'text-muted-foreground'}`}>
            {pickedSeats >= majority
              ? `majority, +${pickedSeats - majority}`
              : `${majority - pickedSeats} short of ${majority}`}
          </span>
          <button
            onClick={() => onChange(new Set())}
            className="text-xs px-2 py-0.5 rounded-full border border-border text-muted-foreground hover:bg-slate-100"
          >
            clear
          </button>
        </>
      )}
    </div>
  );
}

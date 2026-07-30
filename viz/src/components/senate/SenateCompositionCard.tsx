import { useMemo } from 'react';
import { Card } from '@/components/ui/card';
import type { FDSenateSeat } from '../../types';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER, getContrastText } from '../../constants/parties';
import { BAR_HEIGHT, LABEL_MIN_WIDTH } from '../house/FPTPvsSTV';
import { useElementWidth } from '../../hooks/useElementWidth';
import { chamberTotal, type MethodUncertainty } from '../../lib/uncertainty';

// Shared "FPTP Today vs Preferential Senate" composition card, used by both the Senate tab
// and the Overview summary so the two charts are identical. Condorcet/IRV model one winner
// per state; ×2 fills both of a state's seats for a full-chamber view.
function SenateCompBar({ label, seats, segments, total: totalOverride, multiplier = 1 }: {
  label: string;
  seats?: FDSenateSeat[];
  segments?: { party: string; n: number; color: string }[];
  total?: number;
  multiplier?: number;
}) {
  const segs = segments ?? (() => {
    const counts: Record<string, number> = {};
    for (const s of seats ?? []) {
      const p = s.senatorParty ?? s.senatorCode.split('_')[0];
      counts[p] = (counts[p] ?? 0) + 1;
    }
    return F5_ORDER.filter(p => counts[p] > 0).map(p => ({
      party: p, n: counts[p] * multiplier, color: PARTY_COLORS[p] ?? '#6b7280',
    }));
  })();
  const total = totalOverride ?? segs.reduce((s, x) => s + x.n, 0);

  return (
    <div>
      <div className="flex items-baseline gap-1.5 mb-1">
        <span className="text-xs font-semibold text-foreground">{label}</span>
        <span className="text-xs text-muted-foreground">· {total} seats</span>
      </div>
      <div className="flex rounded-lg overflow-hidden" style={{ height: BAR_HEIGHT }}>
        {segs.map(({ party, n, color }) => {
          const pct = (n / total) * 100;
          return (
            <div key={party}
              title={`${PARTY_NAMES[party] ?? party}: ${n} seats (${pct.toFixed(0)}%)`}
              className="seat-segment flex min-w-0 items-center justify-center overflow-hidden"
              style={{ width: `${pct}%`, backgroundColor: color, minWidth: pct < 3 ? 2 : 0 }}>
              <span className="seat-segment-label text-xs font-bold leading-tight text-center px-0.5 chip-text"
                style={{ color: getContrastText(color) }}>
                {party}<br />{n}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function SenateCompositionCard({ condSeats, irvSeats, condU, irvU }: {
  condSeats: FDSenateSeat[];
  irvSeats: FDSenateSeat[];
  condU?: MethodUncertainty;
  irvU?: MethodUncertainty;
}) {
  const [rootRef, rootWidth] = useElementWidth<HTMLDivElement>();

  // Per-party seat counts under each preferential method, for the composition legend.
  const stats = useMemo(() => {
    const tally = (seats: FDSenateSeat[]) => {
      const c: Record<string, number> = {};
      for (const s of seats) {
        const p = s.senatorParty ?? s.senatorCode.split('_')[0];
        c[p] = (c[p] ?? 0) + 1;
      }
      return c;
    };
    // Headline is the modal chamber where we have it — it is the most likely winner in
    // each state and still one winner per state, so it sums to the chamber size.
    const cond: Record<string, number> = condU
      ? Object.fromEntries(Object.entries(condU.seats).map(([p, v]) => [p, v.modal / 2]))
      : tally(condSeats);
    const irv: Record<string, number> = irvU
      ? Object.fromEntries(Object.entries(irvU.seats).map(([p, v]) => [p, v.modal / 2]))
      : tally(irvSeats);
    const parties = F5_ORDER.filter(p => (cond[p] ?? 0) > 0 || (irv[p] ?? 0) > 0);
    // Each bar's total comes from the same data as its segments, so the label can never
    // disagree with what the bar actually draws.
    return {
      // ×2: model gives one winner per state; each fills both of the state's seats.
      rows: parties.map(p => ({ party: p, cond: (cond[p] ?? 0) * 2, irv: (irv[p] ?? 0) * 2 })),
      condTotal: condU ? chamberTotal(condU.seats, 'modal') : condSeats.length * 2,
      irvTotal: irvU ? chamberTotal(irvU.seats, 'modal') : irvSeats.length * 2,
    };
  }, [condSeats, irvSeats, condU, irvU]);

  // Parties whose sliver is too narrow for its inline label in either bar — same rule as the
  // House card's legend, so a party present under one method but not the other (e.g. a party
  // that wins under Condorcet but not IRV) still surfaces with an explicit 0 on the missing side.
  const smallParties = useMemo(() => {
    if (!rootWidth) return new Set<string>();
    const condTotal = stats.rows.reduce((s, r) => s + r.cond, 0);
    const irvTotal = stats.rows.reduce((s, r) => s + r.irv, 0);
    const set = new Set<string>();
    for (const r of stats.rows) {
      if (r.cond > 0 && condTotal && (r.cond / condTotal) * rootWidth < LABEL_MIN_WIDTH) set.add(r.party);
      if (r.irv > 0 && irvTotal && (r.irv / irvTotal) * rootWidth < LABEL_MIN_WIDTH) set.add(r.party);
    }
    return set;
  }, [stats, rootWidth]);
  const shownRows = stats.rows.filter(r => smallParties.has(r.party));

  return (
    <Card ref={rootRef} className="p-5 border-2 border-indigo-200 space-y-3">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
        FPTP Today vs Preferential Senate
      </h3>
      {/* FPTP Today */}
      <SenateCompBar label="FPTP Today" segments={[
        { party: 'DEM', n: 47, color: '#1d4ed8' },
        { party: 'GOP', n: 53, color: '#dc2626' },
      ]} total={100} />
      {/* Condorcet + IRV, doubled to a full chamber */}
      <SenateCompBar label="Condorcet ×2" total={stats.condTotal}
        segments={stats.rows.filter(r => r.cond > 0)
          .map(r => ({ party: r.party, n: r.cond, color: PARTY_COLORS[r.party] ?? '#6b7280' }))} />
      <SenateCompBar label="IRV ×2" total={stats.irvTotal}
        segments={stats.rows.filter(r => r.irv > 0)
          .map(r => ({ party: r.party, n: r.irv, color: PARTY_COLORS[r.party] ?? '#6b7280' }))} />

      {/* Legend — a combined row per party, shown only for slivers too narrow for their inline
          label; a plainly legible bar segment doesn't need restating below. */}
      {shownRows.length > 0 && (
        <div className="space-y-1 pt-2 border-t border-border/50">
          <div className="text-xs font-semibold text-foreground">Condorcet / IRV</div>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            {shownRows.map(r => (
              <span key={r.party} className="flex items-center gap-1.5" title={PARTY_NAMES[r.party] ?? r.party}>
                <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: PARTY_COLORS[r.party] ?? '#6b7280' }} />
                <span className="text-xs text-foreground font-semibold">{r.party}</span>
                <span className="text-xs text-muted-foreground">{r.cond}/{r.irv}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      <p className="text-[11px] text-muted-foreground/80">
        Condorcet and IRV model one winner per state (50 states + DC); each is doubled (&times;2) to fill both of a state&apos;s
        seats for a full-chamber view ({stats.condTotal} seats), which assumes matched delegations and so drops today&apos;s split D/R states.
      </p>
    </Card>
  );
}

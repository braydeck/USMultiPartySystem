import { useMemo } from 'react';
import { Card } from '@/components/ui/card';
import type { FDSenateSeat } from '../../types';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER, getContrastText } from '../../constants/parties';

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
    <div className="flex items-center gap-3">
      <div className="shrink-0 text-right" style={{ width: 110 }}>
        <div className="text-xs font-semibold text-foreground">{label}</div>
        <div className="text-xs text-muted-foreground">{total} seats</div>
      </div>
      <div className="flex-1 flex rounded-lg overflow-hidden h-11">
        {segs.map(({ party, n, color }) => {
          const pct = (n / total) * 100;
          return (
            <div key={party}
              title={`${PARTY_NAMES[party] ?? party}: ${n} seats (${pct.toFixed(0)}%)`}
              className="flex items-center justify-center overflow-hidden"
              style={{ width: `${pct}%`, backgroundColor: color, minWidth: pct < 3 ? 2 : 0 }}>
              {pct >= 5 && (
                <span className="text-[10px] font-bold leading-tight text-center px-0.5 chip-text"
                  style={{ color: getContrastText(color) }}>
                  {party}<br />{n}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function SenateCompositionCard({ condSeats, irvSeats }: {
  condSeats: FDSenateSeat[];
  irvSeats: FDSenateSeat[];
}) {
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
    const cond = tally(condSeats);
    const irv = tally(irvSeats);
    const parties = F5_ORDER.filter(p => (cond[p] ?? 0) > 0 || (irv[p] ?? 0) > 0);
    // ×2: model gives one winner per state; each fills both of the state's seats.
    return {
      rows: parties.map(p => ({ party: p, cond: (cond[p] ?? 0) * 2, irv: (irv[p] ?? 0) * 2 })),
      total: condSeats.length * 2,
      condParties: parties.filter(p => (cond[p] ?? 0) > 0).length,
      irvParties: parties.filter(p => (irv[p] ?? 0) > 0).length,
    };
  }, [condSeats, irvSeats]);

  return (
    <Card className="p-5 border-2 border-indigo-200 space-y-3">
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
        FPTP Today vs Preferential Senate
      </h3>
      {/* FPTP Today */}
      <SenateCompBar label="FPTP Today" segments={[
        { party: 'DEM', n: 47, color: '#1d4ed8' },
        { party: 'GOP', n: 53, color: '#dc2626' },
      ]} total={100} />
      {/* Condorcet + IRV, doubled to a full chamber */}
      <SenateCompBar label="Condorcet ×2" seats={condSeats} multiplier={2} />
      <SenateCompBar label="IRV ×2" seats={irvSeats} multiplier={2} />

      {/* Legend — one row per method, so narrow segments (STY, POP…) still show seat counts */}
      <div className="space-y-1.5 pt-2 border-t border-border/50">
        {([{ name: 'Condorcet', key: 'cond' as const }, { name: 'IRV', key: 'irv' as const }]).map(({ name, key }) => (
          <div key={name} className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="shrink-0 text-xs font-semibold text-foreground" style={{ width: 68 }}>{name}</span>
            {stats.rows.filter(r => r[key] > 0).map(r => (
              <span key={r.party} className="flex items-center gap-1.5" title={PARTY_NAMES[r.party] ?? r.party}>
                <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: PARTY_COLORS[r.party] ?? '#6b7280' }} />
                <span className="text-xs text-foreground font-medium">{r.party}</span>
                <span className="text-xs text-muted-foreground">{r[key]}</span>
              </span>
            ))}
          </div>
        ))}
      </div>

      <p className="text-xs text-muted-foreground leading-relaxed">
        <strong className="text-foreground">FPTP:</strong> each state&apos;s plurality winner takes the seat, so two parties hold every chair.
        <span className="mx-1.5 text-muted-foreground/50" aria-hidden>&bull;</span>
        <strong className="text-foreground">Condorcet:</strong> the seat goes to the candidate who beats every rival one-on-one in a round-robin, the broad consensus pick ({stats.condParties} parties win seats).
        <span className="mx-1.5 text-muted-foreground/50" aria-hidden>&bull;</span>
        <strong className="text-foreground">IRV:</strong> eliminate the last-place candidate and transfer ballots until one clears a majority, rewarding strong first-choice bases ({stats.irvParties} parties win seats).
      </p>

      <p className="text-[11px] text-muted-foreground/80">
        Condorcet and IRV model one winner per state (50 states + DC); each is doubled (&times;2) to fill both of a state&apos;s
        seats for a full-chamber view ({stats.total} seats), which assumes matched delegations and so drops today&apos;s split D/R states.
      </p>
    </Card>
  );
}

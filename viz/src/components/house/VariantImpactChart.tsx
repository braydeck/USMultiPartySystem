import type { FDHouseSeat } from '../../types';
import { PARTY_COLORS, F5_ORDER } from '../../constants/parties';

interface Props {
  seats: FDHouseSeat[];
}

const AXIS_COLORS: Record<string, string> = {
  base: '#64748b',
  so:   '#3b82f6',
  ae:   '#8b5cf6',
  pc:   '#f59e0b',
  rt:   '#ef4444',
};

const AXIS_LABELS: Record<string, string> = {
  base: 'Base',
  so:   'Security (SO)',
  ae:   'Anti-Estab (AE)',
  pc:   'Ideology (PC)',
  rt:   'Religion (RT)',
};

export function VariantImpactChart({ seats }: Props) {
  // Aggregate: party → axis → total seats
  const byParty: Record<string, Record<string, number>> = {};
  const partyTotal: Record<string, number> = {};

  for (const s of seats) {
    if (!byParty[s.party]) byParty[s.party] = {};
    byParty[s.party][s.axis] = (byParty[s.party][s.axis] ?? 0) + s.national;
    partyTotal[s.party] = (partyTotal[s.party] ?? 0) + s.national;
  }

  const maxSeats = Math.max(...Object.values(partyTotal), 1);
  const axes = ['base', 'so', 'ae', 'pc', 'rt'];

  return (
    <div className="space-y-1">
      {/* Legend */}
      <div className="flex flex-wrap gap-3 text-xs mb-2">
        {axes.map(a => (
          <span key={a} className="flex items-center gap-1">
            <span className="w-3 h-3 rounded-sm inline-block" style={{ backgroundColor: AXIS_COLORS[a] }} />
            {AXIS_LABELS[a]}
          </span>
        ))}
      </div>

      {F5_ORDER.map(party => {
        const data = byParty[party];
        if (!data) return null;
        const total = partyTotal[party] ?? 0;
        const color = PARTY_COLORS[party] ?? '#6b7280';
        const baseSeats = data['base'] ?? 0;
        const variantSeats = total - baseSeats;

        // Find the dominant non-base axis
        let bestAxis = '';
        let bestAxisSeats = 0;
        for (const a of axes) {
          if (a === 'base') continue;
          if ((data[a] ?? 0) > bestAxisSeats) {
            bestAxisSeats = data[a] ?? 0;
            bestAxis = a;
          }
        }

        return (
          <div key={party} className="grid grid-cols-[48px_1fr_120px] gap-2 items-center">
            <span className="text-xs font-bold font-mono text-right" style={{ color }}>{party}</span>

            {/* Stacked bar by axis */}
            <div className="flex h-6 rounded overflow-hidden border border-border">
              {axes.map(a => {
                const n = data[a] ?? 0;
                if (n === 0) return null;
                const pct = n / maxSeats * 100;
                return (
                  <div
                    key={a}
                    className="relative"
                    style={{ width: `${pct}%`, backgroundColor: AXIS_COLORS[a], opacity: 0.75, minWidth: n > 0 ? 2 : 0 }}
                    title={`${AXIS_LABELS[a]}: ${n} seats`}
                  >
                    {pct > 6 && (
                      <span className="absolute inset-0 flex items-center justify-center text-[9px] font-bold text-white">
                        {n}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Summary */}
            <div className="text-[10px] text-muted-foreground">
              <span className="font-semibold">{total}</span> seats
              {variantSeats > 0 && bestAxis && (
                <span className="ml-1">
                  · <span style={{ color: AXIS_COLORS[bestAxis] }} className="font-semibold">
                    {bestAxisSeats} {bestAxis.toUpperCase()}
                  </span>
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

import type { HouseSeat } from '../../types';
import { CLUSTER_TO_PARTY, PARTY_NAMES, PARTY_COLORS, F5_ORDER, getContrastText } from '../../constants/parties';

interface Props {
  seats: HouseSeat[];
}

type Tier = 'urban' | 'suburban' | 'rural';

const TIER_LABELS: Record<Tier, string> = {
  urban: 'Urban',
  suburban: 'Suburban',
  rural: 'Rural',
};

export function UrbSubRurChart({ seats }: Props) {
  // Aggregate seats by party per tier, in F5 order
  const tiers: Tier[] = ['urban', 'suburban', 'rural'];

  const partySeats: { party: string; urban: number; suburban: number; rural: number }[] = [];
  for (const party of F5_ORDER) {
    const clusterId = Object.entries(CLUSTER_TO_PARTY).find(([, p]) => p === party)?.[0];
    if (!clusterId) continue;
    const row = seats.find(s => String(s.party) === clusterId);
    if (row && row.national > 0) {
      partySeats.push({ party, urban: row.urban, suburban: row.suburban, rural: row.rural });
    }
  }

  const tierTotals: Record<Tier, number> = {
    urban: partySeats.reduce((s, p) => s + p.urban, 0),
    suburban: partySeats.reduce((s, p) => s + p.suburban, 0),
    rural: partySeats.reduce((s, p) => s + p.rural, 0),
  };

  return (
    <div className="space-y-4">
      {tiers.map(tier => {
        const total = tierTotals[tier];
        if (total === 0) return null;
        const segments = partySeats.filter(p => p[tier] > 0);

        return (
          <div key={tier} className="flex items-center gap-3">
            <div className="shrink-0 text-right" style={{ width: 80 }}>
              <div className="text-xs font-semibold text-foreground">{TIER_LABELS[tier]}</div>
              <div className="text-xs text-muted-foreground">{total} seats</div>
            </div>
            <div className="flex-1 flex rounded-lg overflow-hidden" style={{ height: 44 }}>
              {segments.map(({ party, [tier]: n }) => {
                const pct = (n / total) * 100;
                const color = PARTY_COLORS[party] ?? '#6b7280';
                return (
                  <div
                    key={party}
                    title={`${PARTY_NAMES[party] ?? party}: ${n} seats (${pct.toFixed(1)}%)`}
                    className="flex items-center justify-center overflow-hidden"
                    style={{
                      width: `${pct}%`,
                      backgroundColor: color,
                      minWidth: pct < 2 ? 2 : 0,
                    }}
                  >
                    {pct >= 6 && (
                      <span className="text-xs font-bold chip-text" style={{ color: getContrastText(color) }}>{party}</span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}

      {/* Legend */}
      <div className="flex flex-wrap gap-3 pt-2 border-t border-border/50">
        {partySeats.map(({ party }) => (
          <div key={party} className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: PARTY_COLORS[party] ?? '#6b7280' }} />
            <span className="text-xs text-muted-foreground">{party}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

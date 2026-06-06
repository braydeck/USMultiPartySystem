import { PARTY_COLORS, PARTY_NAMES, F5_ORDER } from '../../constants/parties';

interface TransferDest {
  party: string;
  pct: number;
}

interface TransferSource {
  source: string;
  totalVoters: number;
  destinations: TransferDest[];
}

interface Props {
  data: TransferSource[];
  filterParties?: string[];
}

export function TransferFlowChart({ data, filterParties }: Props) {
  if (!data || data.length === 0) return null;

  const bySource: Record<string, TransferSource> = {};
  for (const row of data) bySource[row.source] = row;

  const parties = filterParties ?? F5_ORDER;

  return (
    <div className="space-y-3">
      {parties.map(party => {
        const row = bySource[party];
        if (!row || row.destinations.length === 0) return null;
        const color = PARTY_COLORS[party] ?? '#6b7280';
        const name  = PARTY_NAMES[party] ?? party;

        return (
          <div key={party}>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-bold font-mono w-8" style={{ color }}>{party}</span>
              <span className="text-xs text-muted-foreground">{name} — if eliminated, votes transfer to:</span>
            </div>

            {/* Stacked bar */}
            <div className="flex h-7 rounded overflow-hidden border border-border">
              {row.destinations.map(d => {
                const dColor = PARTY_COLORS[d.party] ?? '#6b7280';
                return (
                  <div
                    key={d.party}
                    className="relative group"
                    style={{
                      width: `${d.pct}%`,
                      backgroundColor: dColor,
                      opacity: 0.8,
                      minWidth: d.pct > 3 ? undefined : 2,
                    }}
                    title={`→ ${d.party}: ${d.pct}%`}
                  >
                    {d.pct >= 12 && (
                      <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-white drop-shadow-sm">
                        {d.party} {d.pct}%
                      </span>
                    )}
                    {d.pct >= 6 && d.pct < 12 && (
                      <span className="absolute inset-0 flex items-center justify-center text-[9px] font-semibold text-white/90">
                        {d.pct}%
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

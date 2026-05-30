import type { HouseSeat } from '../../types';
import { CLUSTER_TO_PARTY, PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';

const F5_CLUSTER_ORDER = [9, 4, 8, 1, 2, 6, 0, 5, 3];

interface Props {
  seats: HouseSeat[];
}

export function RepresentationGap({ seats }: Props) {
  const total    = seats.reduce((s, r) => s + r.national, 0);
  const byCluster = Object.fromEntries(seats.map(s => [s.party, s]));

  const rows = F5_CLUSTER_ORDER
    .map(cluster => {
      const seat = byCluster[cluster];
      if (!seat) return null;
      const code    = CLUSTER_TO_PARTY[String(cluster)] ?? '';
      const popPct  = seat.pctPopulation;
      const seatPct = total > 0 ? (seat.national / total) * 100 : 0;
      return {
        cluster, code,
        name:    PARTY_NAMES[code] ?? code,
        color:   PARTY_COLORS[code] ?? '#888',
        popPct, seatPct,
        delta:   seatPct - popPct,
      };
    })
    .filter((r): r is NonNullable<typeof r> => r !== null);

  const maxPct = Math.max(26, ...rows.flatMap(r => [r.popPct, r.seatPct]));

  return (
    <div>
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
        Population Share vs. Seat Share
      </h3>
      <p className="text-xs text-muted-foreground mb-4">
        Does each party win seats in proportion to its share of the electorate?
      </p>

      {/* Column headers */}
      <div className="grid gap-y-2" style={{ gridTemplateColumns: '3.5rem 1fr 1fr 3.5rem' }}>
        <div />
        <div className="text-xs text-muted-foreground font-medium pb-1 pl-1">Population %</div>
        <div className="text-xs text-muted-foreground font-medium pb-1 pl-1">Seat %</div>
        <div className="text-xs text-muted-foreground font-medium pb-1 text-right">Δ</div>

        {rows.map(row => {
          const popW  = (row.popPct  / maxPct) * 100;
          const seatW = (row.seatPct / maxPct) * 100;
          const deltaColor = row.delta >= 0 ? '#16a34a' : '#dc2626';
          const sign = row.delta >= 0 ? '+' : '';

          return [
            /* Party label */
            <div key={`label-${row.cluster}`} className="flex items-center justify-end pr-2">
              <span className="text-xs font-bold" style={{ color: row.color }}>{row.code}</span>
            </div>,

            /* Population bar */
            <div key={`pop-${row.cluster}`} className="flex items-center gap-1.5 pr-2">
              <div className="flex-1 h-5 bg-muted rounded-sm overflow-hidden">
                <div
                  className="h-full rounded-sm opacity-50"
                  style={{ width: `${popW}%`, backgroundColor: row.color }}
                />
              </div>
              <span className="text-xs text-muted-foreground w-9 text-right tabular-nums shrink-0">
                {row.popPct.toFixed(1)}%
              </span>
            </div>,

            /* Seat bar */
            <div key={`seat-${row.cluster}`} className="flex items-center gap-1.5 pr-2">
              <div className="flex-1 h-5 bg-muted rounded-sm overflow-hidden">
                <div
                  className="h-full rounded-sm"
                  style={{ width: `${seatW}%`, backgroundColor: row.color }}
                />
              </div>
              <span className="text-xs text-foreground font-semibold w-9 text-right tabular-nums shrink-0">
                {row.seatPct.toFixed(1)}%
              </span>
            </div>,

            /* Delta */
            <div key={`delta-${row.cluster}`} className="flex items-center justify-end">
              <span className="text-xs font-bold tabular-nums" style={{ color: deltaColor }}>
                {sign}{row.delta.toFixed(1)}pp
              </span>
            </div>,
          ];
        })}
      </div>

      <div className="flex gap-4 mt-3 pt-2 border-t border-border/50 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-8 h-3 rounded-sm bg-slate-300 opacity-50" />
          Population share
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-8 h-3 rounded-sm bg-slate-400" />
          Seat share
        </span>
      </div>
    </div>
  );
}

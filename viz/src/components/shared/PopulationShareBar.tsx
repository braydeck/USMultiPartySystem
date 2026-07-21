import { PARTY_COLORS, PARTY_NAMES, F5_ORDER } from '../../constants/parties';
import { popShare } from '../../lib/population';

// Share of U.S. adults belonging to each party's cluster, as a small horizontal bar chart.
// A quick glimpse of the population distribution, independent of turnout (unlike the seat
// charts). Sorted largest-first; bars scaled to the largest so differences are easy to read.
export function PopulationShareBar() {
  const rows = F5_ORDER
    .filter(c => popShare(c) > 0)
    .map(c => ({ code: c, name: PARTY_NAMES[c] ?? c, share: popShare(c), color: PARTY_COLORS[c] ?? '#6b7280' }))
    .sort((a, b) => b.share - a.share);
  const max = Math.max(...rows.map(r => r.share), 1);

  return (
    <div className="space-y-1.5">
      {rows.map(r => (
        <div key={r.code} className="flex items-center gap-2 text-xs">
          <span className="w-28 shrink-0 truncate text-right text-foreground" title={r.name}>{r.name}</span>
          <div className="relative h-4 flex-1 overflow-hidden rounded-sm bg-muted">
            <div className="h-full rounded-sm" style={{ width: `${(r.share / max) * 100}%`, backgroundColor: r.color }} />
          </div>
          <span className="w-9 shrink-0 text-right tabular-nums text-muted-foreground">{r.share.toFixed(1)}%</span>
        </div>
      ))}
    </div>
  );
}

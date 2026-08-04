import { F5_ORDER, getPartyColor, getContrastText, PARTY_NAMES } from '../../constants/parties';

interface Props {
  shares: Record<string, number>; // party -> share, sums to ~1
  height?: number;
  legend?: boolean;
}

/** Horizontal stacked bar over the 10 parties (left→right ideological order), colored by party. */
export function PartyStackBar({ shares, height = 26, legend = true }: Props) {
  const ordered = F5_ORDER.filter(p => (shares[p] ?? 0) > 0.0005);
  const byShare = [...ordered].sort((a, b) => (shares[b] ?? 0) - (shares[a] ?? 0));
  return (
    <div className="space-y-1.5">
      <div className="flex w-full rounded-md overflow-hidden ring-1 ring-black/5" style={{ height }}>
        {ordered.map(p => {
          const s = shares[p];
          const c = getPartyColor(p);
          return (
            <div
              key={p}
              title={`${PARTY_NAMES[p]} — ${(s * 100).toFixed(1)}%`}
              className="flex items-center justify-center text-3xs font-bold overflow-hidden"
              style={{ width: `${s * 100}%`, background: c, color: getContrastText(c) }}
            >
              {s >= 0.08 ? p : ''}
            </div>
          );
        })}
      </div>
      {legend && (
        <div className="flex flex-wrap gap-x-3 gap-y-1">
          {byShare.map(p => (
            <span key={p} className="inline-flex items-center gap-1 text-2xs text-muted-foreground">
              <span className="w-2 h-2 rounded-sm" style={{ background: getPartyColor(p) }} />
              {p} {(shares[p] * 100).toFixed(0)}%
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

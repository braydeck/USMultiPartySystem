// Win probability for the presidency across all seven turnout settings, both methods side by side.
// A single-winner race has no seat range to plot, so the uncertainty lives entirely in how often
// each party wins across resamples — and that only means something read against the turnout axis,
// because one of the two methods changes president partway along it.
import { PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';
import { GAP_STOPS } from '../shared/ParticipationSlider';
import { UNCERTAINTY_STOPS } from '../../lib/uncertainty';

const METHODS = [
  { key: 'irv' as const, label: 'IRV' },
  { key: 'cond' as const, label: 'Condorcet' },
];

const name = (code: string) => PARTY_NAMES[code] ?? code;
const pct = (v: number) => `${Math.round(v * 100)}%`;

/** Every party that wins at least one resample under either method, ordered by peak win share so
 *  the legend leads with the contenders rather than the also-rans. */
function contenders(): string[] {
  const peak = new Map<string, number>();
  for (const u of UNCERTAINTY_STOPS) {
    for (const m of METHODS) {
      for (const [code, v] of Object.entries(u.president[m.key].dist)) {
        peak.set(code, Math.max(peak.get(code) ?? 0, v));
      }
    }
  }
  return [...peak.entries()].sort((a, b) => b[1] - a[1]).map(([c]) => c);
}

/** One sentence per method, derived rather than written, so it cannot drift from the payload. */
function summarise(key: 'irv' | 'cond'): string {
  const modals = UNCERTAINTY_STOPS.map(u => u.president[key].modal);
  const shares = UNCERTAINTY_STOPS.map(u => u.president[key].dist[u.president[key].modal] ?? 0);
  const lo = Math.min(...shares);

  const flip = modals.findIndex((m, i) => i > 0 && m !== modals[i - 1]);
  if (flip < 0) {
    return lo >= 0.999
      ? `${name(modals[0])} wins every resample at every turnout setting.`
      : `${name(modals[0])} leads at every setting, in ${pct(lo)}–${pct(Math.max(...shares))} of resamples.`;
  }
  return `${name(modals[0])} leads until the turnout gap closes by ${GAP_STOPS[flip]}%, where `
    + `${name(modals[flip])} takes over in ${pct(shares[flip])} of resamples, reaching `
    + `${pct(shares[shares.length - 1])} at 30%.`;
}

/** A 100%-stacked column of win share at one turnout stop. */
function StopColumn({ dist, order, stop, active }: {
  dist: Record<string, number>; order: string[]; stop: number; active: boolean;
}) {
  const segments = order.filter(c => (dist[c] ?? 0) > 0);
  return (
    <div className="flex flex-col items-center gap-1 flex-1 min-w-0">
      <div className={`w-full h-16 rounded overflow-hidden flex flex-col ${active
        ? 'ring-2 ring-foreground/40' : 'opacity-80'}`}>
        {segments.map(c => (
          <div key={c} style={{ height: `${(dist[c] ?? 0) * 100}%`, backgroundColor: PARTY_COLORS[c] ?? '#94a3b8' }}
            title={`${name(c)} wins ${pct(dist[c] ?? 0)} of resamples at ${stop}% gap closed`} />
        ))}
      </div>
      <span className={`text-[9px] tabular-nums ${active
        ? 'font-semibold text-foreground' : 'text-muted-foreground'}`}>{stop}</span>
    </div>
  );
}

export function PresidentRangeCard({ gi, nDraws }: { gi: number; nDraws: number }) {
  const order = contenders();
  // A Condorcet cycle produces no winner, and `dist` is conditional on the contest resolving. Say
  // so when it happens: a column still fills, so the renormalization is otherwise invisible.
  const unresolved = UNCERTAINTY_STOPS.some(u => METHODS.some(m => u.president[m.key].nResolved < nDraws));

  return (
    <div>
      <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
        How Certain Is the Presidency?
      </h3>
      <p className="text-xs text-muted-foreground mb-4">
        Share of {nDraws.toLocaleString()} resamples each party wins, at every setting of the
        turnout slider. Columns run 0% to 30% of the gap closed; the outlined column is where the
        slider sits now.
      </p>

      <div className="grid sm:grid-cols-2 gap-6">
        {METHODS.map(m => {
          const here = UNCERTAINTY_STOPS[gi]?.president[m.key];
          return (
            <div key={m.key}>
              <div className="flex items-baseline justify-between gap-2 mb-2">
                <span className="text-xs font-semibold text-foreground">{m.label}</span>
                {here && (
                  <span className="text-[11px] text-muted-foreground">
                    now: <span className="font-semibold" style={{ color: PARTY_COLORS[here.modal] }}>
                      {name(here.modal)}</span> {pct(here.dist[here.modal] ?? 0)}
                  </span>
                )}
              </div>
              <div className="flex items-end gap-1">
                {UNCERTAINTY_STOPS.map((u, i) => (
                  <StopColumn key={i} dist={u.president[m.key].dist} order={order}
                    stop={GAP_STOPS[i]} active={i === gi} />
                ))}
              </div>
              <p className="text-[11px] text-muted-foreground mt-2">{summarise(m.key)}</p>
            </div>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 mt-4 text-[10px] text-muted-foreground">
        {order.map(c => (
          <span key={c} className="flex items-center gap-1.5">
            <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: PARTY_COLORS[c] ?? '#94a3b8' }} />
            {name(c)}
          </span>
        ))}
        <span>column height = 100% of resamples</span>
        {unresolved && (
          <span>shares are of resamples that produced a winner — a Condorcet cycle produces none</span>
        )}
      </div>
    </div>
  );
}

// How often each party reaches the top-five slate, at every setting of the turnout slider.
//
// The primary has no seat range to plot: its output is a set of five names. So the uncertainty is
// per-party inclusion probability, and it only means something read against the turnout axis,
// because the contest for the last slot is decided by the turnout assumption rather than by the
// counting rule. Each column sums to 5.00 slots, so this is one allocation per resample, not seven
// independent guesses.
import { PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';
import { GAP_STOPS } from '../shared/ParticipationSlider';
import { UNCERTAINTY_STOPS } from '../../lib/uncertainty';
import { CARD_HEADING, CARD_HINT } from '../../constants/typography';

const SLOTS = 5;
/** At or above this in every resample at every setting, a slot counts as locked. */
const LOCKED = 0.95;

const party = (code: string) => code.split('_')[0];
const name = (code: string) => PARTY_NAMES[party(code)] ?? party(code);
const pct = (v: number) => Math.round(v * 100);

/** Every contender that reaches the slate in at least one resample at any setting. */
function contenders(): string[] {
  const peak = new Map<string, number>();
  for (const u of UNCERTAINTY_STOPS) {
    for (const [code, v] of Object.entries(u.primary.slate)) {
      peak.set(code, Math.max(peak.get(code) ?? 0, v));
    }
  }
  return [...peak.entries()].sort((a, b) => b[1] - a[1]).map(([c]) => c);
}

/** Which slots never move, derived rather than written so it cannot drift from the payload. The
 *  grid below already shows every party's odds at every setting, so it is not restated here. */
function summarise(codes: string[]): string[] {
  const locked = codes.filter(c => UNCERTAINTY_STOPS.every(u => (u.primary.slate[c] ?? 0) >= LOCKED));
  if (!locked.length) return [];
  return [`${locked.length} of the ${SLOTS} slots hold at every turnout setting: `
    + `${locked.map(name).join(', ')}.`];
}

/** Party colour at an opacity carrying `p`, as an 8-digit hex. Floored well above zero so a 1%
 *  cell still reads as a cell rather than as missing data. */
function tint(code: string, p: number): string {
  const color = PARTY_COLORS[party(code)] ?? '#94a3b8';
  const alpha = Math.min(1, 0.1 + p * 0.7);
  return color + Math.round(alpha * 255).toString(16).padStart(2, '0');
}

/** Probability tile. Fill opacity carries the number a second time, so a row reads as a gradient
 *  before any digit is parsed. */
function Cell({ code, p, stop, inObserved, active }: {
  code: string; p: number; stop: number; inObserved: boolean; active: boolean;
}) {
  return (
    <div className={`relative flex-1 h-7 rounded-sm flex items-center justify-center ${active ? 'ring-2 ring-foreground/40' : ''}`}
      style={{ backgroundColor: p > 0 ? tint(code, p) : undefined }}
      title={`${name(code)} reaches the slate in ${pct(p)}% of resamples with ${stop}% of the turnout gap closed`}>
      <span className={`text-3xs tabular-nums ${p >= 0.5 ? 'font-semibold text-foreground' : 'text-muted-foreground'}`}>
        {pct(p)}
      </span>
      {/* Marks the run shown everywhere else on the tab, so a 62% party listed as a finalist above
          does not read as a contradiction. */}
      {inObserved && <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-foreground/60" />}
    </div>
  );
}

export function SlateRangeCard({ gi, nDraws }: { gi: number; nDraws: number }) {
  const codes = contenders();
  if (!codes.length) return null;
  const observed = UNCERTAINTY_STOPS.map(u => new Set(u.primary.observedSlate));

  return (
    <div>
      <h4 className={`${CARD_HEADING} mb-1`}>
        How Certain Is the Slate?
      </h4>
      <p className={`${CARD_HINT} mb-4`}>
        Share of {nDraws.toLocaleString()} resamples in which each party reaches the top{' '}
        {SLOTS}, at every setting of the turnout slider. Each column sums to {SLOTS} slots. The
        outlined column is where the slider sits now; a dot marks the slate shown above.
      </p>

      <div className="grid grid-cols-[110px_1fr] gap-2">
        <span />
        <div className="flex gap-1 mb-1">
          {GAP_STOPS.map((g, i) => (
            <span key={g} className={`flex-1 text-center text-4xs tabular-nums ${i === gi
              ? 'font-semibold text-foreground' : 'text-muted-foreground'}`}>{g}%</span>
          ))}
        </div>
      </div>

      <div className="space-y-1">
        {codes.map(code => (
          <div key={code} className="grid grid-cols-[110px_1fr] items-center gap-2">
            <span className="text-xs font-medium text-foreground truncate">{name(code)}</span>
            <div className="flex gap-1">
              {UNCERTAINTY_STOPS.map((u, i) => (
                <Cell key={i} code={code} p={u.primary.slate[code] ?? 0} stop={GAP_STOPS[i]}
                  inObserved={observed[i].has(code)} active={i === gi} />
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-[110px_1fr] gap-2 mt-3">
        <span />
        <div className="text-2xs text-muted-foreground space-y-0.5">
          {summarise(codes).map(line => <p key={line}>{line}</p>)}
          <p className="text-muted-foreground/80">Columns are % of the gap between forces&apos; turnout rates closed.</p>
        </div>
      </div>
    </div>
  );
}

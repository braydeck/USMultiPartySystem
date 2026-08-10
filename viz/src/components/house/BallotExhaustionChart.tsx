import { PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';
import { CARD_HINT, TABLE_HEADER } from '../../constants/typography';
import quotaComposition from '../../data/quotaComposition.json';

interface Bundle {
  config: { ballotDepth: number; turnoutGap: number };
  exhaustion: { chamber: number; byParty: { party: string; share: number }[] };
}
const DATA = quotaComposition as unknown as Bundle;

/**
 * Ballot weight that ended up electing nobody, by the party its voters ranked first.
 *
 * Sits under votes-against-seats because it names one cause of that gap rather than restating
 * it: the partial correlation with disproportionality is -0.84 controlling for party size, and
 * Nationalist and Liberal make the case on their own — near-identical vote shares, opposite seat
 * outcomes, exhaustion 12.7% against 2.1%.
 */
export function BallotExhaustionChart() {
  const { chamber, byParty } = DATA.exhaustion;
  const max = Math.max(...byParty.map(r => r.share), chamber) * 1.08;

  return (
    <div className="space-y-2">
      <div className="relative">
        {byParty.map(r => (
          <div key={r.party} className="flex items-center gap-2 py-0.5">
            <span className="w-32 shrink-0 text-xs font-medium truncate"
              style={{ color: PARTY_COLORS[r.party] }} title={PARTY_NAMES[r.party]}>
              {PARTY_NAMES[r.party] ?? r.party}
            </span>
            <span className="relative flex-1 h-4 rounded bg-muted/50 overflow-hidden">
              <span className="block h-full rounded"
                style={{ width: `${(r.share / max) * 100}%`, backgroundColor: PARTY_COLORS[r.party] }} />
            </span>
            <span className="w-10 shrink-0 text-xs tabular-nums text-right text-foreground">
              {(r.share * 100).toFixed(1)}%
            </span>
          </div>
        ))}

        {/* Chamber average, drawn across the bars so each party reads against it. */}
        <div className="pointer-events-none absolute inset-y-0" aria-hidden="true"
          style={{ left: `calc(8.5rem + (100% - 11.5rem) * ${chamber / max})` }}>
          <div className="h-full w-px bg-foreground/50" style={{ borderLeft: '1px dashed currentColor' }} />
        </div>
      </div>

      <div className={`flex flex-wrap items-center gap-x-4 ${TABLE_HEADER}`}>
        <span className="inline-flex items-center gap-1.5">
          <span className="h-3 w-px border-l border-dashed border-foreground/60" />
          chamber average {(chamber * 100).toFixed(1)}%
        </span>
      </div>

      <p className={CARD_HINT}>
        Ballot weight that elected nobody, charged to the party its voters ranked first. It is a
        lever rather than a fact of geography, since ranking depth sets it, and it explains part of
        the gap above: Nationalist and Liberal draw almost the same vote share, 10.8% and 10.7%,
        yet Liberal finishes 1.9 points above proportional and Nationalist 1.0 below. Discounting
        each party&apos;s votes by its exhaustion closes about a sixth of the gap, so this is a
        contributor, not the main driver. Fixed at rank-{DATA.config.ballotDepth} ballots and{' '}
        {Math.round(DATA.config.turnoutGap * 100)}% turnout gap closed, and ranking deeper would
        shrink every bar.
      </p>
    </div>
  );
}

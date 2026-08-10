import { PARTY_COLORS, PARTY_NAMES } from '../../constants/parties';
import { CARD_HINT, TABLE_HEADER } from '../../constants/typography';
import quotaComposition from '../../data/quotaComposition.json';

interface Bundle {
  config: { ballotDepth: number; turnoutGap: number };
  exhaustion: { chamber: number; byParty: { party: string; share: number }[] };
}
const DATA = quotaComposition as unknown as Bundle;

/**
 * Ballot VALUE that expired, by the party its voters ranked first. Not a voter count and not
 * the same as "voters left unrepresented" (0.5%): a ballot can elect someone with part of its
 * value and still shed a fraction that later expires, so this counts value from represented
 * voters too. Distinct again from "seats won below quota" (a seat count) and from `wasted` in
 * housePartyList, which for STV is the analytic Droop floor totV/(S+1) rather than a measurement.
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
        Share of each party&apos;s vote value that ran out of rankings and stopped counting. Value,
        not voters: a ballot can elect someone and still have a fraction expire, which is why this
        is far above the 0.5% left unrepresented. Rank-{DATA.config.ballotDepth} ballots.
      </p>
    </div>
  );
}

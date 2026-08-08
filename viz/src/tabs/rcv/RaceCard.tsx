import type { RCVRace } from '../../types';
import { Card } from '@/components/ui/card';
import { SYSTEM_COLORS, getContrastText } from '../../constants/parties';
import { MINOR_HEADING, CARD_HINT, FOOTNOTE } from '../../constants/typography';
import { BALLOT_PARTY_NAMES, partyColor } from './ballotParties';
import { IrvRoundsChart } from './IrvRoundsChart';
import { CondorcetGrid } from './CondorcetGrid';

/**
 * One contest, collapsed to its two verdicts: did the transfers change the winner,
 * and did ranked counting land on the candidate who beats everyone head-to-head.
 *
 * Both live in the collapsed row because they are the reason to open it. A row with
 * two ticks needs no further reading; the tab has one row that does not.
 */

type Verdict = 'MATCH' | 'DIFFERS' | 'UNAVAILABLE' | 'MOOT';

function VerdictChip({
  verdict, matchLabel, differsLabel, mootLabel, title,
}: {
  verdict: Verdict;
  matchLabel: string;
  differsLabel: string;
  mootLabel?: string;
  title: string;
}) {
  const style: Record<Verdict, string> = {
    MATCH: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    DIFFERS: 'bg-amber-50 text-amber-800 border-amber-300',
    UNAVAILABLE: 'bg-muted text-muted-foreground border-border',
    MOOT: 'bg-muted text-muted-foreground border-border',
  };
  const glyph: Record<Verdict, string> = { MATCH: '✓', DIFFERS: '✗', UNAVAILABLE: '–', MOOT: '–' };
  const label =
    verdict === 'MATCH' ? matchLabel
    : verdict === 'DIFFERS' ? differsLabel
    : mootLabel ?? 'not computable';

  return (
    <span
      className={`text-2xs font-semibold px-1.5 py-0.5 rounded border whitespace-nowrap ${style[verdict]}`}
      title={title}
    >
      {glyph[verdict]} {label}
    </span>
  );
}

function CandidatePill({ name, party, dim }: { name: string; party: string | null; dim?: boolean }) {
  const bg = partyColor(party);
  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs font-semibold px-2 py-0.5 rounded-full chip-text"
      style={{ backgroundColor: bg, color: getContrastText(bg), opacity: dim ? 0.75 : 1 }}
      title={party ? BALLOT_PARTY_NAMES[party] ?? party : 'Write-in'}
    >
      {name}
      {party && <span className="font-bold opacity-80">{party}</span>}
    </span>
  );
}

function Outcome({ label, color, name, party, note }: {
  label: string; color: string; name: string | null; party: string | null; note?: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-card px-3 py-2 space-y-1">
      <div className="text-2xs font-bold uppercase tracking-wider" style={{ color }}>{label}</div>
      {name ? <CandidatePill name={name} party={party} /> : <span className={CARD_HINT}>Not computable</span>}
      {note && <p className={FOOTNOTE}>{note}</p>}
    </div>
  );
}

export function RaceCard({
  race, open, onToggle, domId,
}: {
  race: RCVRace;
  open: boolean;
  onToggle: () => void;
  /** Anchor for the coverage grid and summary chips to scroll to. */
  domId?: string;
}) {
  const decidedInRoundOne = race.irvRounds.length === 1;
  const condorcetVerdict: Verdict =
    race.condorcetAvailable === false ? 'UNAVAILABLE'
    : race.irvMatchesCondorcet ? 'MATCH' : 'DIFFERS';
  const pluralityVerdict: Verdict =
    decidedInRoundOne ? 'MOOT'
    : race.irvMatchesPlurality ? 'MATCH' : 'DIFFERS';

  const primaryTag =
    race.contestType === 'PRIMARY_D' ? 'D primary'
    : race.contestType === 'PRIMARY_R' ? 'R primary'
    : null;

  const finalRound = race.irvRounds[race.irvRounds.length - 1];
  const firstPct = race.irvRounds[0].pcts[race.pluralityWinner];

  return (
    <Card className="overflow-hidden scroll-mt-24" id={domId}>
      <button
        className="w-full px-3 py-2.5 hover:bg-muted/60 transition-colors text-left"
        onClick={onToggle}
        aria-expanded={open}
      >
        <div className="flex items-center gap-3">
          <div className="min-w-0 flex-1 space-y-1.5">
            <div className="flex items-baseline gap-2 flex-wrap">
              <span className="text-xs font-bold text-muted-foreground tabular-nums">{race.year}</span>
              <span className="text-sm font-semibold text-foreground">{race.raceName}</span>
              {primaryTag && (
                <span className="text-3xs font-bold uppercase tracking-wider text-muted-foreground border border-border rounded px-1 py-px">
                  {primaryTag}
                </span>
              )}
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <CandidatePill name={race.irvWinner} party={race.parties[race.irvWinner]} />
              {decidedInRoundOne ? (
                <span className="text-2xs text-muted-foreground">
                  {firstPct.toFixed(1)}% first choices — no transfers needed
                </span>
              ) : (
                <>
                  <VerdictChip
                    verdict={condorcetVerdict}
                    matchLabel="IRV = Condorcet"
                    differsLabel="IRV ≠ Condorcet"
                    mootLabel="Condorcet unknown"
                    title="Whether ranked counting elected the candidate who beats every rival head-to-head"
                  />
                  <VerdictChip
                    verdict={pluralityVerdict}
                    matchLabel="IRV = first past the post"
                    differsLabel="IRV ≠ first past the post"
                    title="Whether the first-choice leader also won after transfers"
                  />
                </>
              )}
            </div>
          </div>
          <div className="shrink-0 text-right space-y-0.5">
            <div className="text-xs text-muted-foreground tabular-nums">
              {race.irvRounds.length} {race.irvRounds.length === 1 ? 'round' : 'rounds'}
            </div>
            <div className="text-2xs text-muted-foreground/80 tabular-nums">
              {race.totalBallots.toLocaleString()} ballots
            </div>
          </div>
          <span className="text-muted-foreground text-xs shrink-0">{open ? '▲' : '▼'}</span>
        </div>
      </button>

      {open && (
        <div className="px-3 pb-3 pt-3 space-y-5 border-t border-border/60">
          <div className="grid gap-2 sm:grid-cols-3">
            <Outcome
              label="First choices"
              color={SYSTEM_COLORS.FPTP}
              name={race.pluralityWinner}
              party={race.parties[race.pluralityWinner]}
              note={`${firstPct.toFixed(1)}% — what a plurality count would have seated`}
            />
            <Outcome
              label="Instant runoff"
              color={SYSTEM_COLORS.IRV}
              name={race.irvWinner}
              party={race.parties[race.irvWinner]}
              note={`${finalRound.pcts[race.irvWinner].toFixed(1)}% of ballots still counting`}
            />
            <Outcome
              label="Condorcet"
              color={SYSTEM_COLORS.Condorcet}
              name={race.condorcetWinner}
              party={race.condorcetWinner ? race.parties[race.condorcetWinner] : null}
              note={
                race.condorcetAvailable === false ? 'No cast vote record released'
                : race.condorcetWinner === race.irvWinner ? 'Beats every rival head-to-head'
                : race.condorcetWinner
                  ? `Beats every rival head-to-head but was eliminated in round ${
                      race.irvRounds.findIndex(r => r.eliminated.includes(race.condorcetWinner!)) + 1
                    }`
                  : 'No candidate beats every rival'
              }
            />
          </div>

          {race.irvRounds.length > 1 && (
            <div>
              <h5 className={`${MINOR_HEADING} mb-2`}>Counting rounds</h5>
              <IrvRoundsChart race={race} />
            </div>
          )}

          <div>
            <h5 className={`${MINOR_HEADING} mb-2`}>Every head-to-head</h5>
            <CondorcetGrid race={race} />
          </div>

          <p className={FOOTNOTE}>
            {race.condorcetAvailable === false
              ? 'Rounds transcribed from the Maine Secretary of State&rsquo;s RCV summary report'
              : 'Computed from the published cast vote record'}
            {' · '}
            <a href={race.provenance} target="_blank" rel="noreferrer" className="underline hover:text-foreground">
              source
            </a>
          </p>
        </div>
      )}
    </Card>
  );
}

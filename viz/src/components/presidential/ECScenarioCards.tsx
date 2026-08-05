// The four things the electoral college does to this field when nothing overrides it.
// Three of the four rules routinely elect nobody, which is the argument the section makes.
import { PARTY_COLORS, PARTY_NAMES, getContrastText } from '../../constants/parties';
import { EC_METHODS, EC_METHOD_LONG, EC_METHOD_BLURB, type ECMethod, type ECTally, type ContingentVote } from '../../lib/ecAllocation';
import { PartyProfileCard } from '../shared/PartyProfileCard';
import { Card } from '@/components/ui/card';
import type { ClusterProfile } from '../../types';
import { CARD_HEADING, GROUP_LABEL, CARD_HINT } from '../../constants/typography';

const party = (code: string) => code.split('_')[0];
const colorOf = (code: string) => PARTY_COLORS[party(code)] ?? '#94a3b8';
const nameOf = (code: string) => PARTY_NAMES[party(code)] ?? party(code);

/** Electors as a 100% stacked bar with the majority line marked on it.
 *  Exported so the top-two cards read in the same grammar rather than a second bar style. */
export function ECBar({ tally }: { tally: ECTally }) {
  const majorityPct = (tally.majority / tally.total) * 100;
  return (
    <div>
      <div className="relative h-5 rounded overflow-hidden flex bg-slate-100">
        {tally.byParty.map(p => (
          <div key={p.code} style={{ width: `${(p.ev / tally.total) * 100}%`, backgroundColor: colorOf(p.code) }}
            title={`${nameOf(p.code)}: ${p.ev} electors`} />
        ))}
        {/* The majority line is the whole point of the bar — it is what three of the
            four rules fail to cross. */}
        <div className="absolute top-0 bottom-0 border-l-2 border-dashed border-slate-900"
          style={{ left: `${majorityPct}%` }} />
      </div>
      <div className="flex items-baseline justify-between gap-2 mt-1">
        <span className="text-2xs tabular-nums text-foreground">
          <span className="font-semibold" style={{ color: colorOf(tally.byParty[0]?.code ?? '') }}>
            {nameOf(tally.byParty[0]?.code ?? '')}
          </span>{' '}
          {tally.byParty[0]?.ev ?? 0} of {tally.total}
        </span>
        <span className="text-3xs text-muted-foreground tabular-nums">{tally.majority} to win</span>
      </div>
    </div>
  );
}

/** Delegations as a 100% stacked bar. Same grammar as ECBar, different unit. */
function DelegationBar({ vote }: { vote: ContingentVote }) {
  return (
    <div>
      <div className="relative h-5 rounded overflow-hidden flex bg-slate-100">
        {vote.byParty.map(p => (
          <div key={p.code} style={{ width: `${(p.states / vote.total) * 100}%`, backgroundColor: colorOf(p.code) }}
            title={`${nameOf(p.code)}: ${p.states} state delegations`} />
        ))}
        <div className="absolute top-0 bottom-0 border-l-2 border-dashed border-slate-900"
          style={{ left: `${(vote.majority / vote.total) * 100}%` }} />
      </div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5">
        {vote.byParty.map(p => (
          <span key={p.code} className="flex items-center gap-1 text-2xs tabular-nums">
            <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: colorOf(p.code) }} />
            <span className="text-foreground">{nameOf(p.code)}</span>
            <span className="text-muted-foreground">{p.states}</span>
          </span>
        ))}
        <span className="text-3xs text-muted-foreground tabular-nums ml-auto">{vote.majority} of {vote.total} to win</span>
      </div>
    </div>
  );
}

/** What a card says when the college produces no majority. */
function NoMajority({ tally, contingent }: { tally: ECTally; contingent: ContingentVote }) {
  const short = tally.majority - (tally.byParty[0]?.ev ?? 0);
  return (
    <Card className="p-4 border-amber-300 bg-amber-50/40">
      <div className="text-sm font-semibold text-amber-900">No majority — decided by the House</div>
      <p className="text-xs text-amber-800 mt-1">
        {nameOf(tally.byParty[0]?.code ?? '')} leads but falls {short} elector{short !== 1 ? 's' : ''} short,
        so the presidency goes to a vote of the state delegations.
      </p>
      <div className="mt-3 pt-3 border-t border-amber-200">
        <div className="text-3xs uppercase tracking-widest text-amber-800/80 mb-1">Projected House vote</div>
        {contingent.winner ? (
          <div className="text-sm">
            <span className="font-bold" style={{ color: colorOf(contingent.winner) }}>{nameOf(contingent.winner)}</span>
            <span className="text-amber-900"> takes {contingent.byParty[0].states} of {contingent.total} delegations</span>
          </div>
        ) : (
          <div className="text-sm font-semibold text-amber-900">Deadlocked House vote</div>
        )}
      </div>
    </Card>
  );
}

interface Props {
  tallies: Record<ECMethod, ECTally>;
  contingent: ContingentVote;
  clusterByParty: Record<string, ClusterProfile>;
}

export function ECScenarioCards({ tallies, contingent, clusterByParty }: Props) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4 items-start">
      {EC_METHODS.map(m => {
        const tally = tallies[m];
        const cluster = tally.winner ? clusterByParty[party(tally.winner)] : undefined;
        return (
          <div key={m} className="space-y-2">
            <div>
              <h4 className={GROUP_LABEL}>{EC_METHOD_LONG[m]}</h4>
              <p className={`${CARD_HINT} leading-snug`}>{EC_METHOD_BLURB[m]}</p>
            </div>
            {tally.winner && cluster
              ? <PartyProfileCard cluster={cluster} />
              : tally.winner
                ? <Card className="p-4"><div className="text-sm font-semibold">{nameOf(tally.winner)} wins</div></Card>
                : <NoMajority tally={tally} contingent={contingent} />}
            <ECBar tally={tally} />
          </div>
        );
      })}
    </div>
  );
}

/** The contingent election on its own, since it decides whichever scenarios deadlock. */
export function ContingentVoteCard({ contingent }: { contingent: ContingentVote }) {
  const leader = contingent.byParty[0];
  return (
    <Card className="p-4">
      <h4 className={`${CARD_HEADING} mb-1`}>
        Projected 12th Amendment Vote
      </h4>
      <p className={`${CARD_HINT} mb-3`}>
        Each state delegation casts one vote. Simulated negotiation by applying Condorcet selection per state.
      </p>
      <div className="mb-3">
        {contingent.winner ? (
          <div className="text-sm">
            <span className="font-bold" style={{ color: colorOf(contingent.winner) }}>{nameOf(contingent.winner)}</span>
            <span className="text-foreground"> takes {leader.states} of {contingent.total} delegations</span>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <span className="text-3xs font-bold uppercase tracking-widest px-2 py-0.5 rounded"
              style={{ backgroundColor: '#b45309', color: getContrastText('#b45309') }}>
              Deadlocked
            </span>
            <span className="text-sm text-foreground">
              {leader ? `${nameOf(leader.code)} leads with ${leader.states}, ${contingent.majority - leader.states} short of a majority` : 'No delegation votes'}
            </span>
          </div>
        )}
      </div>
      <DelegationBar vote={contingent} />
    </Card>
  );
}

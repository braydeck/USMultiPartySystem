import { useUrlState } from '../hooks/useUrlState';
import type { VoteModelRow, CandidateVoteRow, PresidentialElection } from '../types';
import { UnifiedBillTable } from '../components/legislation/UnifiedBillTable';
import { LegislationDivergences } from '../components/legislation/LegislationDivergences';
import { CoalitionMap } from '../components/legislation/CoalitionMap';
import { PartyAgreement } from '../components/legislation/PartyAgreement';
import { Card } from '@/components/ui/card';
import houseSeatsTurnout from '../data/houseSeatsTurnout.json';
import { ToggleGroup } from '../components/shared/ToggleGroup';
import { ParticipationSlider, GAP_STOPS } from '../components/shared/ParticipationSlider';
import { StickyControlBar } from '../components/shared/StickyControlBar';
import { PIPELINE_LABELS, METHOD_LABELS, WYOMING_LABELS } from '../constants/labels';
import type { Pipeline, Method, WyomingRule } from '../constants/labels';
// Compression stops (5-point steps to 30% of the turnout gap closed); floor comes via props.
import houseVotesL5 from '../data/houseVoteModelTurnoutL5.json';
import houseVotesL10 from '../data/houseVoteModelTurnoutL10.json';
import houseVotesL15 from '../data/houseVoteModelTurnoutL15.json';
import houseVotesL20 from '../data/houseVoteModelTurnoutL20.json';
import houseVotesL25 from '../data/houseVoteModelTurnoutL25.json';
import houseVotesL30 from '../data/houseVoteModelTurnoutL30.json';
import senateVotesL5 from '../data/senateVoteModelTurnoutL5.json';
import senateVotesL10 from '../data/senateVoteModelTurnoutL10.json';
import senateVotesL15 from '../data/senateVoteModelTurnoutL15.json';
import senateVotesL20 from '../data/senateVoteModelTurnoutL20.json';
import senateVotesL25 from '../data/senateVoteModelTurnoutL25.json';
import senateVotesL30 from '../data/senateVoteModelTurnoutL30.json';
import presL5 from '../data/rawMultiPresidentialElectionTurnoutL5.json';
import presL10 from '../data/rawMultiPresidentialElectionTurnoutL10.json';
import presL15 from '../data/rawMultiPresidentialElectionTurnoutL15.json';
import presL20 from '../data/rawMultiPresidentialElectionTurnoutL20.json';
import presL25 from '../data/rawMultiPresidentialElectionTurnoutL25.json';
import presL30 from '../data/rawMultiPresidentialElectionTurnoutL30.json';

interface Props {
  candidateVotes: CandidateVoteRow[];
  houseVotes: VoteModelRow[];
  senateVotes: VoteModelRow[];
  fdElection: PresidentialElection;
  rawMultiElection: PresidentialElection;
  houseVotesTurnout: VoteModelRow[];
  senateVotesTurnout: VoteModelRow[];
  rawMultiElectionTurnout: PresidentialElection;
}

// House seat counts per party (current-turnout composition) for the coalition seat-stack.
const CLUSTER_TO_PARTY: Record<number, string> = {
  0: 'CON', 1: 'LBR', 2: 'STY', 3: 'NAT', 4: 'LIB', 5: 'POP', 6: 'CUP', 7: 'OAO', 8: 'DSA', 9: 'PRG',
};
const HOUSE_SEATS: Record<string, number> = Object.fromEntries(
  (houseSeatsTurnout as { party: number; national: number }[]).map((r) => [CLUSTER_TO_PARTY[r.party], r.national]),
);

export function LegislationTab({ candidateVotes, houseVotes, senateVotes, fdElection, rawMultiElection,
                                 houseVotesTurnout, senateVotesTurnout, rawMultiElectionTurnout }: Props) {
  const [pipeline, setPipeline] = useUrlState<Pipeline>('pipeline', 'rawMulti', { allowed: ['rawMulti', 'factorDev'], map: { factorDev: 'crossover', rawMulti: 'party-line' } });
  const [method,   setMethod]   = useUrlState<Method>('method', 'condorcet', { allowed: ['condorcet', 'irv'] });
  const [wyoming,  setWyoming]  = useUrlState<WyomingRule>('wyoming', 'double', { allowed: ['double', 'triple'] });
  // Participation: gap-compression stop (0 = observed 2024 turnout … 100 = full parity).
  const [part, setPart] = useUrlState<string>('part', '0', { allowed: ['0', '5', '10', '15', '20', '25', '30'] });
  const rmDouble = pipeline === 'rawMulti' && wyoming === 'double';
  const gi = Math.max(0, GAP_STOPS.indexOf(Number(part) as typeof GAP_STOPS[number]));
  // Arrays indexed by gap stop [0,5,10,15,20,25,30]: floor(Turnout) … stress ceiling.
  const hStops = [houseVotesTurnout, houseVotesL5, houseVotesL10, houseVotesL15, houseVotesL20, houseVotesL25, houseVotesL30] as unknown as VoteModelRow[][];
  const sStops = [senateVotesTurnout, senateVotesL5, senateVotesL10, senateVotesL15, senateVotesL20, senateVotesL25, senateVotesL30] as unknown as VoteModelRow[][];
  const eStops = [rawMultiElectionTurnout, presL5, presL10, presL15, presL20, presL25, presL30] as unknown as PresidentialElection[];
  const hVotes = rmDouble ? hStops[gi] : houseVotes;
  const sVotes = rmDouble ? sStops[gi] : senateVotes;
  const election = pipeline !== 'rawMulti' ? fdElection : rmDouble ? eStops[gi] : rawMultiElection;
  const presWinner = method === 'condorcet' ? election.condorcetWinner : election.irvWinner;

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-1">Legislation</h2>
        <p className="text-muted-foreground text-sm">
          Probability of passage across House, Senate, and presidency. The divergences panel highlights
          where the election method (Condorcet vs IRV) changes outcomes.
        </p>
      </div>

      <StickyControlBar>
        <ToggleGroup label="Wyoming" value={wyoming} onChange={setWyoming}
          options={['double', 'triple'] as const} labels={WYOMING_LABELS} />
        <ToggleGroup label="Scenario" value={pipeline} onChange={setPipeline}
          options={['rawMulti', 'factorDev'] as const} labels={PIPELINE_LABELS} />
        <ToggleGroup label="Senate Method" value={method} onChange={setMethod}
          options={['condorcet', 'irv'] as const} labels={METHOD_LABELS} />
        {pipeline === 'rawMulti' && wyoming === 'double' && (
          <ParticipationSlider value={Number(part)} onChange={v => setPart(String(v))} />
        )}
      </StickyControlBar>

      <LegislationDivergences
        houseVotes={hVotes}
        senateVotes={sVotes}
        election={election}
        pipeline={pipeline}
        wyoming={wyoming}
      />

      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
          Bill Passage Likelihood — {WYOMING_LABELS[wyoming]} · {PIPELINE_LABELS[pipeline]} · {METHOD_LABELS[method]}
        </h3>
        <p className="text-xs text-muted-foreground mb-4">
          Bayesian verdicts: 45–55% = Tossup · 55–65% = Possibly · 65–80% = Likely · 80%+ = Clearly
        </p>
        <UnifiedBillTable
          houseRows={hVotes}
          senateRows={sVotes}
          pipeline={pipeline}
          senateMethod={method}
          presWinner={presWinner}
          wyoming={wyoming}
        />
      </Card>

      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
          Who Passes a Bill
        </h3>
        <p className="text-xs text-muted-foreground mb-4 max-w-3xl">
          Pick a bill to see which parties combine to carry it. Parties are ordered by support and
          sized by their House seats; the coalition to the left of the majority line is what passes it.
        </p>
        <CoalitionMap candidateVotes={candidateVotes} seats={HOUSE_SEATS} />
      </Card>

      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
          How Often Parties Vote Together
        </h3>
        <p className="text-xs text-muted-foreground mb-4 max-w-3xl">
          Each cell is how closely two parties align across all bills: 100 means identical positions
          everywhere, 0 means maximal disagreement. This reflects party positions, so it does not change
          with the controls above.
        </p>
        <PartyAgreement candidateVotes={candidateVotes} />
      </Card>
    </div>
  );
}

import { useUrlState } from '../hooks/useUrlState';
import type { VoteModelRow, CandidateVoteRow, PresidentialElection } from '../types';
import { UnifiedBillTable } from '../components/legislation/UnifiedBillTable';
import { LegislationDivergences } from '../components/legislation/LegislationDivergences';
import { CoalitionMap } from '../components/legislation/CoalitionMap';
import { PartyAgreement } from '../components/legislation/PartyAgreement';
import { Card } from '@/components/ui/card';
// House seat composition per scenario, for the coalition seat-stack (mirrors the tab's controls).
import houseSeatsTurnout from '../data/houseSeatsTurnout.json';
import houseSeatsTurnoutL5 from '../data/houseSeatsTurnoutL5.json';
import houseSeatsTurnoutL10 from '../data/houseSeatsTurnoutL10.json';
import houseSeatsTurnoutL15 from '../data/houseSeatsTurnoutL15.json';
import houseSeatsTurnoutL20 from '../data/houseSeatsTurnoutL20.json';
import houseSeatsTurnoutL25 from '../data/houseSeatsTurnoutL25.json';
import houseSeatsTurnoutL30 from '../data/houseSeatsTurnoutL30.json';
import houseSeatsTripleTurnout from '../data/houseSeatsTripleTurnout.json';
import fdHouseSeatsTurnout from '../data/fdHouseSeatsTurnout.json';
import fdHouseSeatsTripleTurnout from '../data/fdHouseSeatsTripleTurnout.json';
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

const CLUSTER_TO_PARTY: Record<number, string> = {
  0: 'CON', 1: 'LBR', 2: 'STY', 3: 'NAT', 4: 'LIB', 5: 'POP', 6: 'CUP', 7: 'OAO', 8: 'DSA', 9: 'PRG',
};
const toSeatMap = (arr: { party: number; national: number }[]): Record<string, number> =>
  Object.fromEntries(arr.map((r) => [CLUSTER_TO_PARTY[r.party], r.national]));
const rmSeatStops = [houseSeatsTurnout, houseSeatsTurnoutL5, houseSeatsTurnoutL10, houseSeatsTurnoutL15,
  houseSeatsTurnoutL20, houseSeatsTurnoutL25, houseSeatsTurnoutL30] as unknown as { party: number; national: number }[][];

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

  // House seat composition for the coalition seat-stack, following the same controls:
  // rawMulti+double tracks the participation slider; the others use their observed-turnout base.
  const houseSeats = rmDouble
    ? toSeatMap(rmSeatStops[gi])
    : pipeline === 'factorDev'
      ? toSeatMap((wyoming === 'triple' ? fdHouseSeatsTripleTurnout : fdHouseSeatsTurnout) as unknown as { party: number; national: number }[])
      : toSeatMap(houseSeatsTripleTurnout as unknown as { party: number; national: number }[]);

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
          How Often Parties Vote Together
        </h3>
        <p className="text-xs text-muted-foreground mb-4 max-w-3xl">
          How closely each pair of parties aligns across all bills. Switch between the average support
          gap and the share of bills where both predict the same yes/no vote. This reflects party
          positions, so it does not change with the controls above.
        </p>
        <PartyAgreement candidateVotes={candidateVotes} />
      </Card>

      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
          Who Passes Each Bill
        </h3>
        <p className="text-xs text-muted-foreground mb-4 max-w-3xl">
          For every bill, parties are ordered by support and sized by their House seats; the coalition
          to the left of the majority line is what carries it. Seat weighting follows the controls above.
        </p>
        <CoalitionMap candidateVotes={candidateVotes} seats={houseSeats} />
      </Card>
    </div>
  );
}

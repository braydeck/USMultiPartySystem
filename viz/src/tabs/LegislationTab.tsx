import { useUrlState } from '../hooks/useUrlState';
import type { VoteModelRow, PresidentialElection } from '../types';
import { UnifiedBillTable } from '../components/legislation/UnifiedBillTable';
import { LegislationDivergences } from '../components/legislation/LegislationDivergences';
import { Card } from '@/components/ui/card';
import { ToggleGroup } from '../components/shared/ToggleGroup';
import { ParticipationSlider, GAP_STOPS } from '../components/shared/ParticipationSlider';
import { StickyControlBar } from '../components/shared/StickyControlBar';
import { PIPELINE_LABELS, METHOD_LABELS, WYOMING_LABELS } from '../constants/labels';
import type { Pipeline, Method, WyomingRule } from '../constants/labels';
// Gap-compression middle stops (λ=0.25/0.5/0.75); endpoints come via props.
import houseVotesL25 from '../data/houseVoteModelTurnoutL25.json';
import houseVotesL50 from '../data/houseVoteModelTurnoutL50.json';
import houseVotesL75 from '../data/houseVoteModelTurnoutL75.json';
import senateVotesL25 from '../data/senateVoteModelTurnoutL25.json';
import senateVotesL50 from '../data/senateVoteModelTurnoutL50.json';
import senateVotesL75 from '../data/senateVoteModelTurnoutL75.json';
import presL25 from '../data/rawMultiPresidentialElectionTurnoutL25.json';
import presL50 from '../data/rawMultiPresidentialElectionTurnoutL50.json';
import presL75 from '../data/rawMultiPresidentialElectionTurnoutL75.json';

interface Props {
  houseVotes: VoteModelRow[];
  senateVotes: VoteModelRow[];
  fdElection: PresidentialElection;
  rawMultiElection: PresidentialElection;
  houseVotesTurnout: VoteModelRow[];
  senateVotesTurnout: VoteModelRow[];
  rawMultiElectionTurnout: PresidentialElection;
}

export function LegislationTab({ houseVotes, senateVotes, fdElection, rawMultiElection,
                                 houseVotesTurnout, senateVotesTurnout, rawMultiElectionTurnout }: Props) {
  const [pipeline, setPipeline] = useUrlState<Pipeline>('pipeline', 'rawMulti', { allowed: ['rawMulti', 'factorDev'], map: { factorDev: 'crossover', rawMulti: 'party-line' } });
  const [method,   setMethod]   = useUrlState<Method>('method', 'condorcet', { allowed: ['condorcet', 'irv'] });
  const [wyoming,  setWyoming]  = useUrlState<WyomingRule>('wyoming', 'double', { allowed: ['double', 'triple'] });
  // Participation: gap-compression stop (0 = observed 2024 turnout … 100 = full parity).
  const [part, setPart] = useUrlState<string>('part', '0', { allowed: ['0', '25', '50', '75', '100'] });
  const rmDouble = pipeline === 'rawMulti' && wyoming === 'double';
  const gi = Math.max(0, GAP_STOPS.indexOf(Number(part) as typeof GAP_STOPS[number]));
  // Arrays indexed by gap stop [0,25,50,75,100]: floor(Turnout) … ceiling(full/base).
  const hStops = [houseVotesTurnout, houseVotesL25, houseVotesL50, houseVotesL75, houseVotes] as unknown as VoteModelRow[][];
  const sStops = [senateVotesTurnout, senateVotesL25, senateVotesL50, senateVotesL75, senateVotes] as unknown as VoteModelRow[][];
  const eStops = [rawMultiElectionTurnout, presL25, presL50, presL75, rawMultiElection] as unknown as PresidentialElection[];
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
    </div>
  );
}

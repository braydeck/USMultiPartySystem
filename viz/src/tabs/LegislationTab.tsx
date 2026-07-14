import { useUrlState } from '../hooks/useUrlState';
import type { VoteModelRow, PresidentialElection } from '../types';
import { UnifiedBillTable } from '../components/legislation/UnifiedBillTable';
import { LegislationDivergences } from '../components/legislation/LegislationDivergences';
import { Card } from '@/components/ui/card';
import { ToggleGroup } from '../components/shared/ToggleGroup';
import { StickyControlBar } from '../components/shared/StickyControlBar';
import { PIPELINE_LABELS, METHOD_LABELS, WYOMING_LABELS } from '../constants/labels';
import type { Pipeline, Method, WyomingRule } from '../constants/labels';

interface Props {
  houseVotes: VoteModelRow[];
  senateVotes: VoteModelRow[];
  fdElection: PresidentialElection;
  rawMultiElection: PresidentialElection;
  houseVotesNoSTY: VoteModelRow[];
  senateVotesNoSTY: VoteModelRow[];
  rawMultiElectionNoSTY: PresidentialElection;
  houseVotesTurnout: VoteModelRow[];
  senateVotesTurnout: VoteModelRow[];
  rawMultiElectionTurnout: PresidentialElection;
  houseVotesNoStyTurnout: VoteModelRow[];
  senateVotesNoStyTurnout: VoteModelRow[];
  rawMultiElectionNoStyTurnout: PresidentialElection;
}

export function LegislationTab({ houseVotes, senateVotes, fdElection, rawMultiElection,
                                 houseVotesNoSTY, senateVotesNoSTY, rawMultiElectionNoSTY,
                                 houseVotesTurnout, senateVotesTurnout, rawMultiElectionTurnout,
                                 houseVotesNoStyTurnout, senateVotesNoStyTurnout, rawMultiElectionNoStyTurnout }: Props) {
  const [pipeline, setPipeline] = useUrlState<Pipeline>('pipeline', 'rawMulti', { allowed: ['rawMulti', 'factorDev'], map: { factorDev: 'crossover', rawMulti: 'party-line' } });
  const [method,   setMethod]   = useUrlState<Method>('method', 'condorcet', { allowed: ['condorcet', 'irv'] });
  const [wyoming,  setWyoming]  = useUrlState<WyomingRule>('wyoming', 'double', { allowed: ['double', 'triple'] });
  // No-STY scenario applies to the party-line, double-Wyoming path.
  const [nosty, setNosty] = useUrlState<'off' | 'on'>('nosty', 'off', { allowed: ['off', 'on'] });
  // Participation: 'full' = latent preference; 'curr' = weighted by validated 2024 turnout.
  const [part, setPart] = useUrlState<'full' | 'curr'>('part', 'full', { allowed: ['full', 'curr'] });
  const rmDouble = pipeline === 'rawMulti' && wyoming === 'double';
  const noStyOn = nosty === 'on' && rmDouble;
  const currOn = part === 'curr' && rmDouble;
  const hVotes = currOn ? (noStyOn ? houseVotesNoStyTurnout : houseVotesTurnout) : (noStyOn ? houseVotesNoSTY : houseVotes);
  const sVotes = currOn ? (noStyOn ? senateVotesNoStyTurnout : senateVotesTurnout) : (noStyOn ? senateVotesNoSTY : senateVotes);

  const election = pipeline !== 'rawMulti' ? fdElection
    : currOn ? (noStyOn ? rawMultiElectionNoStyTurnout : rawMultiElectionTurnout)
             : (noStyOn ? rawMultiElectionNoSTY : rawMultiElection);
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
          <ToggleGroup label="Participation" value={part} onChange={setPart}
            options={['full', 'curr'] as const} labels={{ full: 'Full', curr: 'Current turnout' }} />
        )}
        {pipeline === 'rawMulti' && wyoming === 'double' && (
          <ToggleGroup label="Coordination" value={nosty} onChange={setNosty}
            options={['off', 'on'] as const} labels={{ off: 'All parties', on: 'No Solidarity' }} />
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

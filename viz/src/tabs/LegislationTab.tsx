import { useUrlState } from '../hooks/useUrlState';
import type { VoteModelRow, PresidentialElection } from '../types';
import { UnifiedBillTable } from '../components/legislation/UnifiedBillTable';
import { LegislationDivergences } from '../components/legislation/LegislationDivergences';
import { Card } from '@/components/ui/card';
import { ToggleGroup } from '../components/shared/ToggleGroup';
import { StickyControlBar } from '../components/shared/StickyControlBar';
import { PIPELINE_LABELS, METHOD_LABELS, WYOMING_LABELS, WFP_LABELS } from '../constants/labels';
import type { Pipeline, Method, WyomingRule, WfpMode } from '../constants/labels';

interface Props {
  houseVotes: VoteModelRow[];
  senateVotes: VoteModelRow[];
  fdElection: PresidentialElection;
  rawMultiElection: PresidentialElection;
  houseVotesWFP: VoteModelRow[];
  senateVotesWFP: VoteModelRow[];
  rawMultiElectionWFP: PresidentialElection;
}

export function LegislationTab({ houseVotes, senateVotes, fdElection, rawMultiElection,
                                 houseVotesWFP, senateVotesWFP, rawMultiElectionWFP }: Props) {
  const [pipeline, setPipeline] = useUrlState<Pipeline>('pipeline', 'rawMulti', { allowed: ['rawMulti', 'factorDev'], map: { factorDev: 'crossover', rawMulti: 'party-line' } });
  const [method,   setMethod]   = useUrlState<Method>('method', 'condorcet', { allowed: ['condorcet', 'irv'] });
  const [wyoming,  setWyoming]  = useUrlState<WyomingRule>('wyoming', 'double', { allowed: ['double', 'triple'] });
  const [wfp,      setWfp]      = useUrlState<WfpMode>('wfp', 'off', { allowed: ['off', 'on'] });

  // WFP data exists only for the Party-Line + Double-Wyoming path.
  const wfpActive = wfp === 'on' && pipeline === 'rawMulti' && wyoming === 'double';
  const effHouseVotes  = wfpActive ? houseVotesWFP  : houseVotes;
  const effSenateVotes = wfpActive ? senateVotesWFP : senateVotes;
  const effRawMulti    = wfpActive ? rawMultiElectionWFP : rawMultiElection;

  const election = pipeline === 'rawMulti' ? effRawMulti : fdElection;
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
        <ToggleGroup label="WFP" value={wfp} onChange={setWfp}
          options={['off', 'on'] as const} labels={WFP_LABELS} />
      </StickyControlBar>

      <LegislationDivergences
        houseVotes={effHouseVotes}
        senateVotes={effSenateVotes}
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
          houseRows={effHouseVotes}
          senateRows={effSenateVotes}
          pipeline={pipeline}
          senateMethod={method}
          presWinner={presWinner}
          wyoming={wyoming}
        />
      </Card>
    </div>
  );
}

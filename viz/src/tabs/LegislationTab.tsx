import { useState } from 'react';
import type { VoteModelRow, PresidentialElection } from '../types';
import { UnifiedBillTable } from '../components/legislation/UnifiedBillTable';
import { LegislationDivergences } from '../components/legislation/LegislationDivergences';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

interface Props {
  houseVotes: VoteModelRow[];
  senateVotes: VoteModelRow[];
  fdElection: PresidentialElection;
  rawMultiElection: PresidentialElection;
}

type Pipeline = 'rawMulti' | 'factorDev';
type Method   = 'condorcet' | 'irv';
type WyomingRule = 'double' | 'triple';

const PIPELINE_LABELS: Record<Pipeline, string> = {
  rawMulti:  'Raw Multi',
  factorDev: 'Factor Dev',
};

const WYOMING_LABELS: Record<WyomingRule, string> = {
  double: 'Double (873)',
  triple: 'Triple (~1,726)',
};

const METHOD_LABELS: Record<Method, string> = {
  condorcet: 'Condorcet',
  irv:       'IRV',
};

export function LegislationTab({ houseVotes, senateVotes, fdElection, rawMultiElection }: Props) {
  const [pipeline, setPipeline] = useState<Pipeline>('rawMulti');
  const [method,   setMethod]   = useState<Method>('condorcet');
  const [wyoming,  setWyoming]  = useState<WyomingRule>('double');

  const election = pipeline === 'rawMulti' ? rawMultiElection : fdElection;
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

      <div className="sticky top-[40px] z-10 bg-white/95 backdrop-blur-sm border-b border-border/50 -mx-4 px-4 py-2 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground uppercase tracking-widest">Wyoming</span>
          <div className="flex gap-1">
            {(Object.keys(WYOMING_LABELS) as WyomingRule[]).map(w => (
              <Button key={w} onClick={() => setWyoming(w)}
                variant={wyoming === w ? 'default' : 'secondary'} size="sm">
                {WYOMING_LABELS[w]}
              </Button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground uppercase tracking-widest">Scenario</span>
          <div className="flex gap-1">
            {(Object.keys(PIPELINE_LABELS) as Pipeline[]).map(p => (
              <Button key={p} onClick={() => setPipeline(p)}
                variant={pipeline === p ? 'default' : 'secondary'} size="sm">
                {PIPELINE_LABELS[p]}
              </Button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground uppercase tracking-widest">Senate Method</span>
          <div className="flex gap-1">
            {(Object.keys(METHOD_LABELS) as Method[]).map(m => (
              <Button key={m} onClick={() => setMethod(m)}
                variant={method === m ? 'default' : 'secondary'} size="sm">
                {METHOD_LABELS[m]}
              </Button>
            ))}
          </div>
        </div>
      </div>

      <LegislationDivergences
        houseVotes={houseVotes}
        senateVotes={senateVotes}
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
          houseRows={houseVotes}
          senateRows={senateVotes}
          pipeline={pipeline}
          senateMethod={method}
          presWinner={presWinner}
          wyoming={wyoming}
        />
      </Card>
    </div>
  );
}

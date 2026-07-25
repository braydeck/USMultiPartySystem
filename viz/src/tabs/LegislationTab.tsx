import { useUrlState } from '../hooks/useUrlState';
import { useState, useEffect } from 'react';
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
import fdHouseSeatsTurnout from '../data/fdHouseSeatsTurnout.json';
import fdHouseSeatsTripleTurnout from '../data/fdHouseSeatsTripleTurnout.json';
// Senate composition per (pipeline × method), for the coalition Senate view + whipped bloc math.
// Raw-Multi senate is the rank-7 winnow, tracked across turnout stops (matches the app default).
import pureMultiSenateCondorcetTurnout from '../data/pureMultiSenateCondorcetTurnout.json';
import pureMultiSenateIRVTurnout from '../data/pureMultiSenateIRVTurnout.json';
import senCondL5 from '../data/pureMultiSenateCondorcetTurnoutL5.json';
import senCondL10 from '../data/pureMultiSenateCondorcetTurnoutL10.json';
import senCondL15 from '../data/pureMultiSenateCondorcetTurnoutL15.json';
import senCondL20 from '../data/pureMultiSenateCondorcetTurnoutL20.json';
import senCondL25 from '../data/pureMultiSenateCondorcetTurnoutL25.json';
import senCondL30 from '../data/pureMultiSenateCondorcetTurnoutL30.json';
import senIrvL5 from '../data/pureMultiSenateIRVTurnoutL5.json';
import senIrvL10 from '../data/pureMultiSenateIRVTurnoutL10.json';
import senIrvL15 from '../data/pureMultiSenateIRVTurnoutL15.json';
import senIrvL20 from '../data/pureMultiSenateIRVTurnoutL20.json';
import senIrvL25 from '../data/pureMultiSenateIRVTurnoutL25.json';
import senIrvL30 from '../data/pureMultiSenateIRVTurnoutL30.json';
import fdSenateCondorcet from '../data/fdSenateCondorcet.json';
import fdSenateIRV from '../data/fdSenateIRV.json';
import { senateSeatMap } from '../components/legislation/voteBloc';
import { ToggleGroup } from '../components/shared/ToggleGroup';
import { ParticipationSlider, GAP_STOPS } from '../components/shared/ParticipationSlider';
import { StickyControlBar } from '../components/shared/StickyControlBar';
import { PIPELINE_LABELS, METHOD_LABELS, WYOMING_LABELS, VOTE_MODEL_LABELS } from '../constants/labels';
import type { Pipeline, Method, WyomingRule, VoteMode } from '../constants/labels';
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

export function LegislationTab({ candidateVotes, houseVotes, senateVotes, fdElection,
                                 houseVotesTurnout, senateVotesTurnout, rawMultiElectionTurnout }: Props) {
  const [pipeline, setPipeline] = useUrlState<Pipeline>('pipeline', 'rawMulti', { allowed: ['rawMulti', 'factorDev'], map: { factorDev: 'crossover', rawMulti: 'party-line' } });
  const [method,   setMethod]   = useUrlState<Method>('method', 'condorcet', { allowed: ['condorcet', 'irv'] });
  const [wyoming,  setWyoming]  = useUrlState<WyomingRule>('wyoming', 'double', { allowed: ['double', 'triple'] });
  // Participation: gap-compression stop (0 = observed 2024 turnout … 100 = full parity).
  const [part, setPart] = useUrlState<string>('part', '5', { allowed: ['0', '5', '10', '15', '20', '25', '30'] });
  // Vote model: free vote (members split by probability) vs whipped (party votes as a bloc).
  const [voteModel, setVoteModel] = useUrlState<VoteMode>('voteModel', 'free', { allowed: ['free', 'whipped'] });
  const rmDouble = pipeline === 'rawMulti' && wyoming === 'double';
  const isRawMulti = pipeline === 'rawMulti';
  const gi = Math.max(0, GAP_STOPS.indexOf(Number(part) as typeof GAP_STOPS[number]));

  // Legislation bakes in the app defaults: rank-7 chambers + depth-7 president. Raw-Multi house
  // STV seats and the president come from the lazy depth bundles (top7); the vote-model rows,
  // house seats, and senate composition below are already the rank-7 variants.
  const [hpl, setHpl] = useState<Record<string, Record<string, Record<string, { national: { stvSeats: Record<string, number> } }>>> | null>(null);
  const [gd, setGd] = useState<Record<string, Record<string, PresidentialElection>> | null>(null);
  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/housePartyList.json`).then(r => r.json()).then(setHpl).catch(() => {});
    fetch(`${import.meta.env.BASE_URL}data/generalDepth.json`).then(r => r.json()).then(setGd).catch(() => {});
  }, []);

  // Arrays indexed by gap stop [0,5,10,15,20,25,30]: floor(Turnout) … stress ceiling.
  const hStops = [houseVotesTurnout, houseVotesL5, houseVotesL10, houseVotesL15, houseVotesL20, houseVotesL25, houseVotesL30] as unknown as VoteModelRow[][];
  const sStops = [senateVotesTurnout, senateVotesL5, senateVotesL10, senateVotesL15, senateVotesL20, senateVotesL25, senateVotesL30] as unknown as VoteModelRow[][];
  const senCondStops = [pureMultiSenateCondorcetTurnout, senCondL5, senCondL10, senCondL15, senCondL20, senCondL25, senCondL30] as unknown as { senatorParty: string }[][];
  const senIrvStops  = [pureMultiSenateIRVTurnout, senIrvL5, senIrvL10, senIrvL15, senIrvL20, senIrvL25, senIrvL30] as unknown as { senatorParty: string }[][];
  const eStops = [rawMultiElectionTurnout, presL5, presL10, presL15, presL20, presL25, presL30] as unknown as PresidentialElection[];
  const hVotes = rmDouble ? hStops[gi] : houseVotes;
  const sVotes = isRawMulti ? sStops[gi] : senateVotes;
  // Depth-7 president from the bundle; full-ranking stop as the pre-load fallback.
  const election = isRawMulti ? (gd?.top7?.[part] ?? eStops[gi]) : fdElection;
  const presWinner = method === 'condorcet' ? election.condorcetWinner : election.irvWinner;

  // House seat composition for the coalition seat-stack. Raw-Multi uses the rank-7 STV seats
  // (top7) from the party-list bundle, tracking turnout; Crossover keeps its own pipeline.
  const houseSeats = isRawMulti
    ? (hpl?.top7?.[wyoming]?.[part]?.national?.stvSeats ?? toSeatMap(rmSeatStops[gi]))
    : toSeatMap((wyoming === 'triple' ? fdHouseSeatsTripleTurnout : fdHouseSeatsTurnout) as unknown as { party: number; national: number }[]);

  // Senate composition by (pipeline × method). Raw-Multi is the rank-7 winnow tracked across
  // turnout stops; Crossover uses its own senate. Method drives which map the passage view uses.
  const senCondSrc = (pipeline === 'factorDev' ? fdSenateCondorcet : senCondStops[gi]) as unknown as { senatorParty: string }[];
  const senIRVSrc  = (pipeline === 'factorDev' ? fdSenateIRV : senIrvStops[gi]) as unknown as { senatorParty: string }[];
  const senateSeatsCond = senateSeatMap(senCondSrc);
  const senateSeatsIRV  = senateSeatMap(senIRVSrc);
  const senateSeats     = method === 'condorcet' ? senateSeatsCond : senateSeatsIRV;

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-1">Legislation</h2>
        <p className="text-muted-foreground text-sm">
          Probability of passage across House, Senate, and presidency. The divergences panel highlights
          where the election method (Condorcet vs IRV) changes outcomes.
        </p>
      </div>

      <StickyControlBar label="Legislation settings">
        <ToggleGroup label="Wyoming" value={wyoming} onChange={setWyoming}
          options={['double', 'triple'] as const} labels={WYOMING_LABELS} />
        <ToggleGroup label="Scenario" value={pipeline} onChange={setPipeline}
          options={['rawMulti', 'factorDev'] as const} labels={PIPELINE_LABELS} />
        <ToggleGroup label="Senate Method" value={method} onChange={setMethod}
          options={['condorcet', 'irv'] as const} labels={METHOD_LABELS} />
        <ToggleGroup label="Vote Model" value={voteModel} onChange={setVoteModel}
          options={['free', 'whipped'] as const} labels={VOTE_MODEL_LABELS} />
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
        voteModel={voteModel}
        candidateVotes={candidateVotes}
        houseSeats={houseSeats}
        senateSeatsCond={senateSeatsCond}
        senateSeatsIRV={senateSeatsIRV}
      />

      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
          Bill Passage Likelihood — {WYOMING_LABELS[wyoming]} · {PIPELINE_LABELS[pipeline]} · {METHOD_LABELS[method]}
        </h3>
        <p className="text-xs text-muted-foreground mb-4">
          {voteModel === 'whipped'
            ? 'Whipped: each party votes as a bloc, so verdicts are a deterministic Passes / Fails.'
            : 'Bayesian verdicts: 45–55% = Tossup · 55–65% = Possibly · 65–80% = Likely · 80%+ = Clearly'}
        </p>
        <UnifiedBillTable
          houseRows={hVotes}
          senateRows={sVotes}
          pipeline={pipeline}
          senateMethod={method}
          presWinner={presWinner}
          wyoming={wyoming}
          voteModel={voteModel}
          candidateVotes={candidateVotes}
          houseSeats={houseSeats}
          senateSeats={senateSeats}
        />
      </Card>

      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
          How Often Parties Vote Together
        </h3>
        <p className="text-xs text-muted-foreground mb-4 max-w-3xl">
          {voteModel === 'whipped'
            ? 'Share of bills where both parties whip the same yes/no vote. Reflects party positions, so it does not change with the seat controls above.'
            : 'Closeness of each pair of parties across all bills: 100 − their average gap in support. Reflects party positions, so it does not change with the seat controls above.'}
        </p>
        <PartyAgreement candidateVotes={candidateVotes} voteModel={voteModel} />
      </Card>

      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
          Who Passes Each Bill
        </h3>
        <p className="text-xs text-muted-foreground mb-4 max-w-3xl">
          For every bill, parties are stacked and sized by their seats; the coalition to the left of the
          majority line is what carries it. Toggle House / Senate; seat weighting follows the controls above.
        </p>
        <CoalitionMap candidateVotes={candidateVotes} houseSeats={houseSeats} senateSeats={senateSeats} voteModel={voteModel} />
      </Card>
    </div>
  );
}

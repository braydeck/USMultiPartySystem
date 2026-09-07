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
import depthNational from '../data/houseDepthNational.json';
import mmpNational from '../data/houseMmpNational.json';
import reserveNational from '../data/houseReserveNational.json';
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
import { uncertaintyAt, type SeatInterval } from '../lib/uncertainty';
import { delegationSeats } from '../lib/senateDelegations';
import { ToggleGroup } from '../components/shared/ToggleGroup';
import { ParticipationSlider, GAP_STOPS } from '../components/shared/ParticipationSlider';
import { StickyControlBar } from '../components/shared/StickyControlBar';
import { PIPELINE_LABELS, METHOD_LABELS, WYOMING_LABELS, VOTE_MODEL_LABELS, HOUSE_SYSTEM_LABELS } from '../constants/labels';
import type { Pipeline, Method, WyomingRule, VoteMode, HouseSystem } from '../constants/labels';
import { SHOW_CROSSOVER, PIPELINE_OPTIONS } from '../constants/features';
import { DEPTH_KEYS, DEPTH_LABELS, type DepthKey } from '../constants/depth';
import type { MmpNational } from '../components/house/MmpView';
import type { ReserveNational } from '../components/house/ReserveView';
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
import { PAGE_TITLE, CARD_HEADING, CARD_HINT } from '../constants/typography';

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
/** Modal seats per party. */
const modalMap = (seats: Record<string, SeatInterval>): Record<string, number> =>
  Object.fromEntries(Object.entries(seats)
    .filter(([, v]) => v.modal > 0)
    .map(([p, v]) => [p, v.modal]));
/** Both of a state's seats to its single modelled winner, for the pipelines that have no
 *  resampling to split on. Keeps every senate map on the 102-seat basis. */
const doubled = (m: Record<string, number>): Record<string, number> =>
  Object.fromEntries(Object.entries(m).map(([p, n]) => [p, n * 2]));
const rmSeatStops = [houseSeatsTurnout, houseSeatsTurnoutL5, houseSeatsTurnoutL10, houseSeatsTurnoutL15,
  houseSeatsTurnoutL20, houseSeatsTurnoutL25, houseSeatsTurnoutL30] as unknown as { party: number; national: number }[][];
/** National seat totals under both House counting rules, per (depth × Wyoming rule × turnout stop).
 *  The 71 KB projection of housePartyList.json, bundled rather than fetched so the seat maps the
 *  coalition and whipped views need are on hand at first paint. */
type PartyCounts = Record<string, number>;
const DEPTH_NATIONAL = depthNational as unknown as Record<string, Record<string, Record<string, {
  national: { stvSeats: PartyCounts; listSeats: PartyCounts };
}>>>;
const MMP_NATIONAL = mmpNational as unknown as Record<'double' | 'triple', Record<string, MmpNational>>;
const RESERVE_NATIONAL = reserveNational as unknown as Record<string, Record<string, Record<string, ReserveNational>>>;

const RESERVE_LABELS: Record<string, string> = { off: 'Off', on: 'On' };

export function LegislationTab({ candidateVotes, houseVotes, senateVotes, fdElection,
                                 houseVotesTurnout, senateVotesTurnout, rawMultiElectionTurnout }: Props) {
  const [pipeline, setPipeline] = useUrlState<Pipeline>('pipeline', 'rawMulti', { allowed: PIPELINE_OPTIONS, map: { factorDev: 'crossover', rawMulti: 'party-line' } });
  const [method,   setMethod]   = useUrlState<Method>('method', 'condorcet', { allowed: ['condorcet', 'irv'] });
  const [wyoming,  setWyoming]  = useUrlState<WyomingRule>('wyoming', 'double', { allowed: ['double', 'triple'] });
  const [system,   setSystem]   = useUrlState<HouseSystem>('system', 'stv', { allowed: ['stv', 'list', 'mmp'] });
  const [depth,    setDepth]    = useUrlState<DepthKey>('depth', 'top7', { allowed: [...DEPTH_KEYS] });
  const [reserve,  setReserve]  = useUrlState<'off' | 'on'>('reserve', 'off', { allowed: ['off', 'on'] });
  const [part, setPart] = useUrlState<string>('part', '5', { allowed: ['0', '5', '10', '15', '20', '25', '30'] });
  const [voteModel, setVoteModel] = useUrlState<VoteMode>('voteModel', 'free', { allowed: ['free', 'whipped'] });
  const isRawMulti = pipeline === 'rawMulti';
  const gi = Math.max(0, GAP_STOPS.indexOf(Number(part) as typeof GAP_STOPS[number]));

  const [gd, setGd] = useState<Record<string, Record<string, PresidentialElection>> | null>(null);
  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/generalDepth.json`).then(r => r.json()).then(setGd).catch(() => {});
  }, []);
  const houseNat = DEPTH_NATIONAL[depth]?.[wyoming]?.[part]?.national;
  const mmpNat = MMP_NATIONAL[wyoming]?.[part];
  const reserveNat = RESERVE_NATIONAL[depth]?.[wyoming]?.[part];

  // Arrays indexed by gap stop [0,5,10,15,20,25,30]: floor(Turnout) … stress ceiling.
  const hStops = [houseVotesTurnout, houseVotesL5, houseVotesL10, houseVotesL15, houseVotesL20, houseVotesL25, houseVotesL30] as unknown as VoteModelRow[][];
  const sStops = [senateVotesTurnout, senateVotesL5, senateVotesL10, senateVotesL15, senateVotesL20, senateVotesL25, senateVotesL30] as unknown as VoteModelRow[][];
  const senCondStops = [pureMultiSenateCondorcetTurnout, senCondL5, senCondL10, senCondL15, senCondL20, senCondL25, senCondL30] as unknown as { senatorParty: string }[][];
  const senIrvStops  = [pureMultiSenateIRVTurnout, senIrvL5, senIrvL10, senIrvL15, senIrvL20, senIrvL25, senIrvL30] as unknown as { senatorParty: string }[][];
  const eStops = [rawMultiElectionTurnout, presL5, presL10, presL15, presL20, presL25, presL30] as unknown as PresidentialElection[];
  // Every party-line stop file carries all four House columns, and the triple-Wyoming STV column is
  // computed from a fixed tree so it is identical in each — reading the stop file at triple costs
  // nothing there and is what makes the party-list column, which does move with turnout, available.
  const hVotes = isRawMulti ? hStops[gi] : houseVotes;
  const sVotes = isRawMulti ? sStops[gi] : senateVotes;
  const election = isRawMulti ? (gd?.[depth]?.[part] ?? gd?.top7?.[part] ?? eStops[gi]) : fdElection;
  const presWinner = method === 'condorcet' ? election.condorcetWinner : election.irvWinner;

  // Both Vote Model settings have to describe ONE chamber: the toggle changes party discipline,
  // not who sits in the seats. The Raw-Multi vote-model columns are computed from the modal
  // chamber, so the browser-side seat maps that drive whipped mode, CoalitionMap and the bloc
  // arithmetic must be the modal chamber too. Do not revert these to the committed per-state
  // JSONs — that puts the observed chamber on one side of the toggle and the modal one on the
  // other. Crossover has no bootstrap and keeps its own maps.
  const unc = isRawMulti ? uncertaintyAt(gi) : undefined;

  // House seat composition for the coalition seat-stack.
  // Reserve and MMP read from their bundled national data; STV/list from the depth bundle.
  // The bootstrap modal chamber is rank-7 double-Wyoming STV only, so it applies only when
  // depth=top7 + wyoming=double + system=stv + reserve=off.
  const useModal = unc && wyoming === 'double' && depth === 'top7' && system === 'stv' && reserve === 'off';
  const houseSeats = (() => {
    if (system === 'mmp') return mmpNat?.mmpSeats ?? {};
    if (reserve === 'on' && reserveNat) {
      return system === 'list' ? (reserveNat.list.seats ?? {}) : (reserveNat.stv.seats ?? {});
    }
    if (system === 'list') return houseNat?.listSeats ?? {};
    if (useModal) return modalMap(unc!.house.seats);
    if (isRawMulti) return houseNat?.stvSeats ?? toSeatMap(rmSeatStops[gi]);
    return toSeatMap((wyoming === 'triple' ? fdHouseSeatsTripleTurnout : fdHouseSeatsTurnout) as unknown as { party: number; national: number }[]);
  })();

  // Senate composition by (pipeline × method), on the 102-seat basis — every state returns
  // two senators, so a bloc majority is 52. Crossover falls back to the rank-7 winnow /
  // its own senate. Method drives which map the passage view uses.
  const senCondSrc = (pipeline === 'factorDev' ? fdSenateCondorcet : senCondStops[gi]) as unknown as { senatorParty: string }[];
  const senIRVSrc  = (pipeline === 'factorDev' ? fdSenateIRV : senIrvStops[gi]) as unknown as { senatorParty: string }[];
  // The senate that votes here has to be the senate the Senate tab shows: contested
  // states send one senator from each of their two closest parties, so the chamber is no
  // longer one winner doubled and cannot be recovered by halving a party total.
  const senateSeatsCond = unc ? delegationSeats(unc.senate.cond.states) : doubled(senateSeatMap(senCondSrc));
  const senateSeatsIRV  = unc ? delegationSeats(unc.senate.irv.states)  : doubled(senateSeatMap(senIRVSrc));
  const senateSeats     = method === 'condorcet' ? senateSeatsCond : senateSeatsIRV;

  return (
    <div className="space-y-8">
      <div>
        <h2 className={`${PAGE_TITLE} mb-1`}>Legislation</h2>
        <p className="text-muted-foreground text-sm">
          Probability of passage across House, Senate, and presidency. The divergences panel highlights
          where the election method (Condorcet vs IRV) changes outcomes.
        </p>
      </div>

      <StickyControlBar label="Legislation settings">
        <ToggleGroup label="Wyoming" value={wyoming} onChange={setWyoming}
          options={['double', 'triple'] as const} labels={WYOMING_LABELS} />
        <ToggleGroup label="House" value={system} onChange={setSystem}
          options={['stv', 'list', 'mmp'] as const} labels={HOUSE_SYSTEM_LABELS} />
        {system === 'stv' && (
          <ToggleGroup label="Ballots ranked" value={depth} onChange={setDepth}
            options={[...DEPTH_KEYS]} labels={DEPTH_LABELS} />
        )}
        {system !== 'mmp' && (
          <ToggleGroup label="Reserve" value={reserve} onChange={setReserve}
            options={['off', 'on'] as const} labels={RESERVE_LABELS} />
        )}
        {SHOW_CROSSOVER && system === 'stv' && (
          <ToggleGroup label="Scenario" value={pipeline} onChange={setPipeline}
            options={PIPELINE_OPTIONS} labels={PIPELINE_LABELS} />
        )}
        <ToggleGroup label="Senate Method" value={method} onChange={setMethod}
          options={['condorcet', 'irv'] as const} labels={METHOD_LABELS} />
        <ToggleGroup label="Vote Model" value={voteModel} onChange={setVoteModel}
          options={['free', 'whipped'] as const} labels={VOTE_MODEL_LABELS} />
        <ParticipationSlider value={Number(part)} onChange={v => setPart(String(v))} />
      </StickyControlBar>

      <LegislationDivergences
        houseVotes={hVotes}
        senateVotes={sVotes}
        election={election}
        pipeline={pipeline}
        wyoming={wyoming}
        system={system}
        voteModel={voteModel}
        candidateVotes={candidateVotes}
        houseSeats={houseSeats}
        senateSeatsCond={senateSeatsCond}
        senateSeatsIRV={senateSeatsIRV}
        depth={depth}
        reserve={reserve}
      />

      <Card className="p-4">
        <h4 className={`${CARD_HEADING} mb-1`}>
          Bill Passage Likelihood — {[
            WYOMING_LABELS[wyoming], HOUSE_SYSTEM_LABELS[system],
            ...(system === 'stv' ? [`Rank ${DEPTH_LABELS[depth]}`] : []),
            ...(reserve === 'on' && system !== 'mmp' ? ['+ Reserve'] : []),
            ...(SHOW_CROSSOVER ? [PIPELINE_LABELS[pipeline]] : []), METHOD_LABELS[method],
          ].join(' · ')}
        </h4>
        <p className={`${CARD_HINT} mb-4`}>
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
          system={system}
          voteModel={voteModel}
          candidateVotes={candidateVotes}
          houseSeats={houseSeats}
          senateSeats={senateSeats}
          depth={depth}
          reserve={reserve}
        />
      </Card>

      <Card className="p-4">
        <h4 className={`${CARD_HEADING} mb-1`}>
          How Often Parties Vote Together
        </h4>
        <p className={`${CARD_HINT} mb-4 max-w-3xl`}>
          {voteModel === 'whipped'
            ? 'Share of bills where both parties whip the same yes/no vote. Reflects party positions, so it does not change with the seat controls above.'
            : 'Closeness of each pair of parties across all bills: 100 − their average gap in support. Reflects party positions, so it does not change with the seat controls above.'}
        </p>
        <PartyAgreement candidateVotes={candidateVotes} voteModel={voteModel} />
      </Card>

      <Card className="p-4">
        <h4 className={`${CARD_HEADING} mb-1`}>
          Who Passes Each Bill
        </h4>
        <p className={`${CARD_HINT} mb-4 max-w-3xl`}>
          For every bill, parties are stacked and sized by their seats; the coalition to the left of the
          majority line is what carries it. Toggle House / Senate; seat weighting follows the controls above.
        </p>
        <CoalitionMap candidateVotes={candidateVotes} houseSeats={houseSeats} senateSeats={senateSeats} voteModel={voteModel} />
      </Card>
    </div>
  );
}

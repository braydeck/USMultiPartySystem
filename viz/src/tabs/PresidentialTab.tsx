import { useMemo, useState, useEffect, type ReactNode } from 'react';
import { useUrlState } from '../hooks/useUrlState';
import { DEPTH_KEYS, type DepthKey } from '../constants/depth';
import type { PresidentialElection, PresidentialScenario, ClusterProfile, VoteModelRow, FDCandidateProfile, HouseStateEntry } from '../types';
import { Card } from '@/components/ui/card';
import { PARTY_COLORS, buildDisplayLabels } from '../constants/parties';
import { PIPELINE_LABELS } from '../constants/labels';
import { SHOW_CROSSOVER, PIPELINE_OPTIONS } from '../constants/features';
import { ToggleGroup } from '../components/shared/ToggleGroup';
import { ParticipationSlider, GAP_STOPS } from '../components/shared/ParticipationSlider';
import { StickyControlBar } from '../components/shared/StickyControlBar';
import { uncertaintyAt } from '../lib/uncertainty';
// Gap-compression stops (5-point steps to 30%); the λ=0 floor comes via props.
import presTL5 from '../data/rawMultiPresidentialElectionTurnoutL5.json';
import presTL10 from '../data/rawMultiPresidentialElectionTurnoutL10.json';
import presTL15 from '../data/rawMultiPresidentialElectionTurnoutL15.json';
import presTL20 from '../data/rawMultiPresidentialElectionTurnoutL20.json';
import presTL25 from '../data/rawMultiPresidentialElectionTurnoutL25.json';
import presTL30 from '../data/rawMultiPresidentialElectionTurnoutL30.json';
// Senate bill vote model (rank-7 winnow + depth-7 president) for the divergent-bills panel.
import senVMTurnout from '../data/senateVoteModelTurnout.json';
import senVML5 from '../data/senateVoteModelTurnoutL5.json';
import senVML10 from '../data/senateVoteModelTurnoutL10.json';
import senVML15 from '../data/senateVoteModelTurnoutL15.json';
import senVML20 from '../data/senateVoteModelTurnoutL20.json';
import senVML25 from '../data/senateVoteModelTurnoutL25.json';
import senVML30 from '../data/senateVoteModelTurnoutL30.json';
import { NationalFPTPProjection } from '../components/presidential/NationalFPTPProjection';
import { IRVSankey } from '../components/presidential/IRVSankey';
import { PresidentialComparison } from '../components/presidential/PresidentialComparison';
import { CondorcetMatrix } from '../components/presidential/CondorcetMatrix';
import { PartyProfileCard } from '../components/shared/PartyProfileCard';
import { PresidentRangeCard } from '../components/presidential/PresidentRangeCard';
import { CollapsibleSection } from '../components/shared/CollapsibleSection';
import { ECScenarioCards, ContingentVoteCard } from '../components/presidential/ECScenarioCards';
import { ECCartogram } from '../components/presidential/ECCartogram';
import {
  ecWeights, allocateEC, contingentVote, nationalFirstChoice,
  EC_METHODS, MAP_VIEWS, type ECMethod, type ECTally, type MapView,
} from '../lib/ecAllocation';

interface Props {
  factorDev: PresidentialElection;
  rawMulti:  PresidentialElection;
  rawMultiTurnout: PresidentialElection;
  clusters:  ClusterProfile[];
  fdProfiles: Record<string, FDCandidateProfile>;
  senateVotes: VoteModelRow[];
  houseStateMap: Record<string, HouseStateEntry>;
  /** Optional control rendered first in the sticky control bar (e.g. the Presidency View toggle). */
  controlBarExtra?: ReactNode;
}

const PRES_LABELS = PIPELINE_LABELS;

/** The three counting rules, in the order the page presents them. */
type Method = 'Condorcet' | 'IRV' | 'FPTP';

/**
 * One column per distinct winner. Tailwind needs the class as a literal, so these are
 * spelled out rather than interpolated.
 *
 * Three winners step 1 → 2 → 3 rather than jumping straight from one column to three: at
 * tablet width two winners fit side by side and the third wraps below, which is a far
 * gentler transition than every column becoming a full-width row at once.
 */
const GROUP_COLS: Record<number, string> = {
  1: '',
  2: 'md:grid-cols-2',
  3: 'md:grid-cols-2 xl:grid-cols-3',
};

function PresCell({ signs, partyCode }: { signs: string | undefined; partyCode: string }) {
  const color = PARTY_COLORS[partyCode] ?? '#6b7280';
  if (!signs) return <span className="text-slate-300 text-xs">—</span>;
  return (
    <span
      className="text-xs font-bold px-2 py-0.5 rounded border whitespace-nowrap"
      style={
        signs === 'SIGN'
          ? { backgroundColor: color + '18', color, borderColor: color + '55' }
          : { backgroundColor: '#fef2f2', color: '#b91c1c', borderColor: '#fca5a5' }
      }
    >
      {signs === 'SIGN' ? 'Signs' : 'Vetoes'}
    </span>
  );
}

export function PresidentialTab({ factorDev, rawMulti, rawMultiTurnout,
                                  clusters, senateVotes, houseStateMap,
                                  controlBarExtra }: Props) {
  const [scenario, setScenario] = useUrlState<PresidentialScenario>('scenario', 'rawMulti', { allowed: PIPELINE_OPTIONS, map: { factorDev: 'crossover', rawMulti: 'party-line' } });
  // Participation: gap-compression stop (0 = observed 2024 turnout … 100 = full parity).
  const [part, setPart] = useUrlState<string>('part', '5', { allowed: ['0', '5', '10', '15', '20', '25', '30'] });
  const gi = Math.max(0, GAP_STOPS.indexOf(Number(part) as typeof GAP_STOPS[number]));
  const rmStops = [rawMultiTurnout, presTL5, presTL10, presTL15, presTL20, presTL25, presTL30] as unknown as PresidentialElection[];
  // The general is a 5-finalist IRV/Condorcet contest — voters rank all 5, so there is no ballot-
  // depth toggle here. But WHICH 5 finalists advance depends on the primary's depth setting (shared
  // with the Primary view via the 'depth' URL param), so the general reads the depth-N finalists.
  const [depth] = useUrlState<DepthKey>('depth', 'top7', { allowed: [...DEPTH_KEYS] });
  // Bootstrap resample probabilities exist only for the raw multi-party pipeline at rank-7
  // ballots — Crossover (Factor Dev) has no uncertainty payload, and the bootstrap ran only the
  // top7 depth, so at any other depth the distribution describes a different finalist field and
  // a different president than the one on screen. Same gate HouseTab uses for its whiskers.
  const ud = scenario === 'rawMulti' && depth === 'top7' ? uncertaintyAt(gi) : undefined;
  const [depthBundle, setDepthBundle] = useState<Record<string, Record<string, PresidentialElection>> | null>(null);
  useEffect(() => {
    if (depth !== 'full' && !depthBundle) {
      fetch(`${import.meta.env.BASE_URL}data/generalDepth.json`).then(r => r.json()).then(setDepthBundle).catch(() => {});
    }
  }, [depth, depthBundle]);
  const gd = (scenario === 'rawMulti' && depth !== 'full') ? depthBundle?.[depth]?.[part] : null;
  const rm = scenario !== 'rawMulti' ? rawMulti : (gd ?? rmStops[gi]);
  const data = scenario === 'rawMulti' ? rm : factorDev;

  const clusterByParty = useMemo(
    () => Object.fromEntries(clusters.map(c => [c.party, c])),
    [clusters],
  );

  // Raw Multi winners
  const rmCondWinner = rm.condorcetWinner;
  const rmIrvWinner  = rm.irvWinner;
  const rmCondParty  = rmCondWinner.split('_')[0];
  const rmIrvParty   = rmIrvWinner.split('_')[0];

  // Build Raw Multi display labels (CON_1 → CON when sole numbered variant)
  const rmLabels = useMemo(() => {
    const codes = new Set<string>();
    for (const r of rm.irvRounds) for (const c of r.candidates) codes.add(c.code);
    return buildDisplayLabels(codes);
  }, [rm]);
  const rmLabel = (code: string) => rmLabels[code] ?? code;

  // Factor Dev winner (same for both methods)
  const fdWinner     = factorDev.condorcetWinner;
  const fdWinnerParty = fdWinner.split('_')[0];

  // National FPTP is round one of the instant runoff: the same ballots stopped after the
  // first preference. Grouped by winner rather than listed per rule, so rules that agree
  // share one card instead of repeating it.
  const nationalGroups = useMemo(() => {
    const fptpWinner = nationalFirstChoice(data.irvRounds)[0]?.code;
    const entries: { method: Method; winner: string }[] = [
      { method: 'Condorcet', winner: data.condorcetWinner },
      { method: 'IRV', winner: data.irvWinner },
      ...(fptpWinner ? [{ method: 'FPTP' as Method, winner: fptpWinner }] : []),
    ];
    const groups: { winner: string; methods: Method[] }[] = [];
    for (const e of entries) {
      const found = groups.find(g => g.winner === e.winner);
      if (found) found.methods.push(e.method);
      else groups.push({ winner: e.winner, methods: [e.method] });
    }
    return groups;
  }, [data]);

  // The college without the override: four allocation rules over the same state results.
  const ecWeightMap = useMemo(() => ecWeights(houseStateMap), [houseStateMap]);
  const ecTallies = useMemo(() => Object.fromEntries(
    EC_METHODS.map(m => [m, allocateEC(data.irvStateWinners, ecWeightMap, m)]),
  ) as Record<ECMethod, ECTally>, [data, ecWeightMap]);
  const houseVote = useMemo(() => contingentVote(data.irvStateWinners), [data]);
  // Condorcet by default: it is the rule the rest of the site treats as the honest one, so
  // the map opens on the case where the college still fails to elect its winner.
  const [ecView, setEcView] = useUrlState<MapView>('ec', 'condorcet', { allowed: [...MAP_VIEWS] });

  // Senate bill vote model at the current turnout stop (rank-7 winnow + depth-7 president).
  const senVMStops = [senVMTurnout, senVML5, senVML10, senVML15, senVML20, senVML25, senVML30] as unknown as VoteModelRow[][];
  const senVotesRank7 = senVMStops[gi];
  // Bills where Raw Multi Condorcet and IRV presidents act differently
  const divergentBills = useMemo(
    // Keyed on the presidents this tab is displaying, not on the fixed columns: those carry the
    // winners of the tree that built the file, which at rank-7 and no turnout compression is a
    // different Condorcet president than the one shown above. Identical parties give identical
    // signs, so this is empty whenever both methods elect the same president — no branch needed.
    () => senVotesRank7.filter(r => {
      const cond = r.presSignsByParty?.[rmCondParty];
      const irv = r.presSignsByParty?.[rmIrvParty];
      return cond !== undefined && irv !== undefined && cond !== irv;
    }),
    [senVotesRank7, rmCondParty, rmIrvParty],
  );

  /**
   * The chart that shows how a rule reached its winner. Rendered inside that winner's column,
   * so the matrix always sits under a Condorcet result and the flow under an IRV one.
   *
   * The matrix drops to scale 1 here: at 1.5 it is ~480px wide, which overflows a third of the
   * grid, and it scrolls horizontally rather than shrinking the cells past legibility.
   */
  const methodVisual = (m: Method) => {
    if (m === 'Condorcet') {
      return (
        <Card className="p-4">
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">
            Head-to-Head Matrix
          </h4>
          <p className="text-[11px] text-muted-foreground mb-3">
            Every possible pairing. Green = row candidate wins; red = row candidate loses. The
            winner&apos;s row is all green, which is why they win.
          </p>
          <div className="overflow-x-auto">
            <CondorcetMatrix matchups={data.condorcetMatchups} condorcetWinner={data.condorcetWinner} />
          </div>
        </Card>
      );
    }
    if (m === 'IRV') {
      return (
        <Card className="p-4">
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">
            Vote Flow
          </h4>
          <p className="text-[11px] text-muted-foreground mb-3">
            Each column is one elimination round. Eliminated candidates&apos; votes fan out to the
            remaining field.
          </p>
          <IRVSankey rounds={data.irvRounds} irvWinner={data.irvWinner} />
        </Card>
      );
    }
    return <NationalFPTPProjection shares={nationalFirstChoice(data.irvRounds)} label={rmLabel} />;
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-1">2028 Presidential General Election</h2>
        <p className="text-muted-foreground text-sm">
          Single-winner race. The question is which method picks the most acceptable president.
          Condorcet finds who beats everyone head-to-head; IRV rewards the candidate with the strongest base.
        </p>
      </div>

      <StickyControlBar label="Presidency settings">
        {controlBarExtra}
        {SHOW_CROSSOVER && (
          <ToggleGroup label="Scenario" value={scenario} onChange={setScenario}
            options={PIPELINE_OPTIONS} labels={PRES_LABELS} />
        )}
        {scenario === 'rawMulti' && (
          <ParticipationSlider value={Number(part)} onChange={v => setPart(String(v))} />
        )}
      </StickyControlBar>

      {/* Presidential Outcomes — scenario-dependent */}
      {scenario === 'rawMulti' ? (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">National Override</h3>
          <p className="text-xs text-muted-foreground">
            One national ballot, counted once. {nationalGroups.length === 1
              ? 'All three counting rules elect the same president.'
              : `The three counting rules elect ${nationalGroups.length} different presidents from the same ballots.`}
          </p>
          <div className={`grid gap-4 items-start ${GROUP_COLS[nationalGroups.length] ?? ''}`}>
            {nationalGroups.map(g => (
              <div key={g.winner} className="space-y-3">
                <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
                  {g.methods.join(' · ')} — {rmLabel(g.winner)}
                </div>
                {clusterByParty[g.winner.split('_')[0]] && (
                  <PartyProfileCard cluster={clusterByParty[g.winner.split('_')[0]]} />
                )}
                {/* The evidence for each rule in this column, in the page's rule order. */}
                {g.methods.map(m => <div key={m}>{methodVisual(m)}</div>)}
              </div>
            ))}
          </div>

          {divergentBills.length > 0 && (
            <CollapsibleSection
              id="bills"
              title={`See ${divergentBills.length} bill${divergentBills.length !== 1 ? 's' : ''} with different presidential outcomes`}
              hint={`Where ${rmCondParty} (Condorcet) and ${rmIrvParty} (IRV) act differently`}
            >
              <Card className="overflow-hidden border-amber-300">
                <div className="hidden md:grid grid-cols-[1fr_80px_80px] gap-x-2 px-4 py-2 text-xs text-muted-foreground border-b border-border/50 uppercase tracking-widest">
                  <div>Bill</div>
                  <div className="text-center font-bold" style={{ color: PARTY_COLORS[rmCondParty] ?? '#6b7280' }}>{rmCondParty}</div>
                  <div className="text-center font-bold" style={{ color: PARTY_COLORS[rmIrvParty] ?? '#6b7280' }}>{rmIrvParty}</div>
                </div>

                <div className="divide-y divide-slate-100">
                  {divergentBills.map(r => (
                    <div
                      key={r.variable}
                      className="flex flex-col md:grid md:grid-cols-[1fr_80px_80px] gap-x-2 items-start md:items-center px-4 py-2.5 bg-amber-50/30"
                    >
                      <div className="min-w-0 mb-1 md:mb-0">
                        <div className="text-sm text-foreground leading-snug">{r.question}</div>
                        <div className="text-xs text-muted-foreground mt-0.5">{r.domain}</div>
                      </div>
                      <div className="flex justify-center">
                        <PresCell signs={r.presSignsByParty?.[rmCondParty]} partyCode={rmCondParty} />
                      </div>
                      <div className="flex justify-center">
                        <PresCell signs={r.presSignsByParty?.[rmIrvParty]} partyCode={rmIrvParty} />
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </CollapsibleSection>
          )}
        </div>
      ) : (
        /* Factor Dev — every rule elects the same president, so one column holds all three charts. */
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">Presidential Outcome</h3>
          <p className="text-xs text-muted-foreground">
            Both Condorcet and IRV elect the same president under Factor Dev.
          </p>
          <div className="space-y-3">
            <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
              Winner — {fdWinner}
            </div>
            {clusterByParty[fdWinnerParty] && (
              <div className="max-w-sm"><PartyProfileCard cluster={clusterByParty[fdWinnerParty]} /></div>
            )}
            {(['Condorcet', 'IRV', 'FPTP'] as Method[]).map(m => <div key={m}>{methodVisual(m)}</div>)}
          </div>
        </div>
      )}

      {/* Election Results Without National Override — the same ballots run through the college.
          Four rules, not six: a state's payload carries one first-choice share vector and two
          single winners, so proportional allocation can only be FPTP, and IRV and Condorcet can
          only be winner-take-all. */}
      <div className="space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
            Election Results Without National Override
          </h3>
          <p className="text-xs text-muted-foreground">
            Keep the electoral college and its {ecTallies.prop.total} electors, one per House seat
            plus two per state, and the counting rule decides the presidency before the voters do.
          </p>
        </div>
        <ECScenarioCards tallies={ecTallies} contingent={houseVote} clusterByParty={clusterByParty} />
        <Card className="p-4">
          <ECCartogram tallies={ecTallies} stateWinners={data.irvStateWinners}
            nationalShares={nationalFirstChoice(data.irvRounds)} mapView={ecView} onMapView={setEcView} />
        </Card>
        <ContingentVoteCard contingent={houseVote} />
      </div>

      {/* Presidential Policy Comparison — Factor Dev only */}
      {scenario === 'factorDev' && (
        <Card className="p-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
            Presidential Policy Comparison — Factor Dev · Raw Multi
          </h3>
          <p className="text-xs text-muted-foreground mb-4">
            How likely each potential president would sign or veto major legislation.
            Amber rows highlight where the presidents disagree. % = fraction of the president&apos;s
            voter coalition that supports the bill.
          </p>
          {/* `rm`, not the static `rawMulti` prop: this card names its party-line president, and
              the depth and turnout controls above have to move it too. */}
          <PresidentialComparison rows={senateVotes} factorDev={factorDev} rawMulti={rm} />
        </Card>
      )}

      {/* Last on the page: how far the result could move is what you ask after seeing the result,
          the head-to-head matrix, the vote flow and the map — not before any of them. */}
      {ud && ud.president && (
        <Card className="p-4">
          <PresidentRangeCard gi={gi} nDraws={ud.nDraws} />
        </Card>
      )}
    </div>
  );
}

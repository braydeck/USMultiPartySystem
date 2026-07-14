import { useMemo, type ReactNode } from 'react';
import { useUrlState } from '../hooks/useUrlState';
import type { PresidentialElection, PresidentialScenario, ClusterProfile, VoteModelRow, FDCandidateProfile, HouseStateEntry } from '../types';
import { Card } from '@/components/ui/card';
import { PARTY_COLORS, buildDisplayLabels } from '../constants/parties';
import { PIPELINE_LABELS } from '../constants/labels';
import { ToggleGroup } from '../components/shared/ToggleGroup';
import { StickyControlBar } from '../components/shared/StickyControlBar';
import { PresidentialMap } from '../components/presidential/PresidentialMap';
import { IRVSankey } from '../components/presidential/IRVSankey';
import { PresidentialComparison } from '../components/presidential/PresidentialComparison';
import { CondorcetMatrix } from '../components/presidential/CondorcetMatrix';
import { PartyProfileCard } from '../components/shared/PartyProfileCard';

interface Props {
  factorDev: PresidentialElection;
  rawMulti:  PresidentialElection;
  rawMultiNoSTY: PresidentialElection;
  rawMultiTurnout: PresidentialElection;
  rawMultiNoStyTurnout: PresidentialElection;
  clusters:  ClusterProfile[];
  fdProfiles: Record<string, FDCandidateProfile>;
  senateVotes: VoteModelRow[];
  houseStateMap: Record<string, HouseStateEntry>;
  /** Optional control rendered first in the sticky control bar (e.g. the Presidency View toggle). */
  controlBarExtra?: ReactNode;
}

const PRES_LABELS = PIPELINE_LABELS;

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

export function PresidentialTab({ factorDev, rawMulti, rawMultiNoSTY, rawMultiTurnout, rawMultiNoStyTurnout,
                                  clusters, senateVotes, houseStateMap,
                                  controlBarExtra }: Props) {
  const [scenario, setScenario] = useUrlState<PresidentialScenario>('scenario', 'rawMulti', { allowed: ['rawMulti', 'factorDev'], map: { factorDev: 'crossover', rawMulti: 'party-line' } });
  // No-STY scenario: Solidarity dissolved, its voters flow to the remaining 9 (party-line only).
  const [nosty, setNosty] = useUrlState<'off' | 'on'>('nosty', 'off', { allowed: ['off', 'on'] });
  // Participation: 'full' = every latent preference counts; 'curr' = weighted by validated 2024 turnout.
  const [part, setPart] = useUrlState<'full' | 'curr'>('part', 'full', { allowed: ['full', 'curr'] });
  const rm = scenario !== 'rawMulti' ? rawMulti
    : part === 'curr'
      ? (nosty === 'on' ? rawMultiNoStyTurnout : rawMultiTurnout)
      : (nosty === 'on' ? rawMultiNoSTY : rawMulti);
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
  const rmSameWinner = rmCondWinner === rmIrvWinner;

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

  // Bills where Raw Multi Condorcet and IRV presidents act differently
  const divergentBills = useMemo(
    () => senateVotes.filter(r =>
      r.presRawMultiCondSigns !== undefined &&
      r.presRawMultiIRVSigns  !== undefined &&
      r.presRawMultiCondSigns !== r.presRawMultiIRVSigns,
    ),
    [senateVotes],
  );

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-1">2028 Presidential General Election</h2>
        <p className="text-muted-foreground text-sm">
          Single-winner race. The question is which method picks the most acceptable president.
          Condorcet finds who beats everyone head-to-head; IRV rewards the candidate with the strongest base.
        </p>
      </div>

      <StickyControlBar>
        {controlBarExtra}
        <ToggleGroup label="Scenario" value={scenario} onChange={setScenario}
          options={['rawMulti', 'factorDev'] as const} labels={PRES_LABELS} />
        {scenario === 'rawMulti' && (
          <ToggleGroup label="Participation" value={part} onChange={setPart}
            options={['full', 'curr'] as const} labels={{ full: 'Full', curr: 'Current turnout' }} />
        )}
        {scenario === 'rawMulti' && (
          <ToggleGroup label="Coordination" value={nosty} onChange={setNosty}
            options={['off', 'on'] as const} labels={{ off: 'All parties', on: 'No Solidarity' }} />
        )}
      </StickyControlBar>

      {/* Presidential Outcomes — scenario-dependent */}
      {scenario === 'rawMulti' ? (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">Presidential Outcomes</h3>
          {rmSameWinner ? (
            <div>
              <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-2">
                Winner (both methods): {rmLabel(rmCondWinner)}
              </div>
              {clusterByParty[rmCondParty] && <div className="max-w-sm"><PartyProfileCard cluster={clusterByParty[rmCondParty]} /></div>}
            </div>
          ) : (
            <>
              <p className="text-xs text-muted-foreground">
                Condorcet and IRV elect different presidents — the winner shapes which bills become law.
              </p>
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-2">
                    Condorcet Winner — {rmLabel(rmCondWinner)}
                  </div>
                  {clusterByParty[rmCondParty] && <PartyProfileCard cluster={clusterByParty[rmCondParty]} />}
                </div>
                <div>
                  <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-2">
                    IRV Winner — {rmLabel(rmIrvWinner)}
                  </div>
                  {clusterByParty[rmIrvParty] && <PartyProfileCard cluster={clusterByParty[rmIrvParty]} />}
                </div>
              </div>

              {divergentBills.length > 0 && (
                <Card className="overflow-hidden border-amber-300">
                  <div className="px-4 py-3 bg-amber-50 border-b border-amber-200">
                    <h4 className="text-sm font-semibold text-amber-900">
                      {divergentBills.length} bill{divergentBills.length !== 1 ? 's' : ''} with different presidential outcomes
                    </h4>
                    <p className="text-xs text-amber-700 mt-0.5">
                      Only bills where {rmCondParty} (Condorcet) and {rmIrvParty} (IRV) act differently are shown.
                    </p>
                  </div>

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
                          <PresCell signs={r.presRawMultiCondSigns} partyCode={rmCondParty} />
                        </div>
                        <div className="flex justify-center">
                          <PresCell signs={r.presRawMultiIRVSigns} partyCode={rmIrvParty} />
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              )}
            </>
          )}
        </div>
      ) : (
        /* Factor Dev — single winner */
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">Presidential Outcome</h3>
          <p className="text-xs text-muted-foreground">
            Both Condorcet and IRV elect the same president under Factor Dev.
          </p>
          <div>
            <div className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-2">
              Winner — {fdWinner}
            </div>
            <div className="max-w-sm">
              {clusterByParty[fdWinnerParty] && <PartyProfileCard cluster={clusterByParty[fdWinnerParty]} />}
            </div>
          </div>
        </div>
      )}

      {/* Condorcet head-to-head matrix — centered, 1.5x scale */}
      <Card className="p-6">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
          Head-to-Head Matrix (Condorcet)
        </h3>
        <p className="text-xs text-muted-foreground mb-4">
          Every possible pairing. Green = row candidate wins; red = row candidate loses.
          The Condorcet winner&apos;s row is all-green — that&apos;s why they win.
        </p>
        <div className="flex justify-center">
          <CondorcetMatrix
            matchups={data.condorcetMatchups}
            condorcetWinner={data.condorcetWinner}
            scale={1.5}
          />
        </div>
      </Card>

      {/* IRV vote flow Sankey */}
      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
          IRV Vote Flow
        </h3>
        <p className="text-xs text-muted-foreground mb-3">
          Each column is one elimination round. Eliminated candidates&apos; votes fan out to the remaining field.
        </p>
        <IRVSankey rounds={data.irvRounds} irvWinner={data.irvWinner} />
      </Card>

      {/* State map + EC */}
      <PresidentialMap stateWinners={data.irvStateWinners} stateMap={houseStateMap} />

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
          <PresidentialComparison rows={senateVotes} factorDev={factorDev} rawMulti={rawMulti} />
        </Card>
      )}
    </div>
  );
}

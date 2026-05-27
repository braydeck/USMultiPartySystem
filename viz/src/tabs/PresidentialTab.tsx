import { useState, useMemo } from 'react';
import type { PresidentialElection, PresidentialScenario, ClusterProfile, VoteModelRow, FDCandidateProfile } from '../types';
import { PARTY_COLORS } from '../constants/parties';
import { PresidentialMap } from '../components/presidential/PresidentialMap';
import { IRVSankey } from '../components/presidential/IRVSankey';
import { PresidentialComparison } from '../components/presidential/PresidentialComparison';
import { CondorcetMatrix } from '../components/presidential/CondorcetMatrix';
import { PartyProfileCard } from '../components/shared/PartyProfileCard';
import { VerdictBadge, getBayesianLabel } from '../components/legislation/UnifiedBillTable';

interface Props {
  factorDev: PresidentialElection;
  rawMulti:  PresidentialElection;
  clusters:  ClusterProfile[];
  fdProfiles: Record<string, FDCandidateProfile>;
  senateVotes: VoteModelRow[];
}

const PRES_LABELS: Record<PresidentialScenario, string> = {
  rawMulti:  'Raw Multi',
  factorDev: 'Factor Dev',
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

export function PresidentialTab({ factorDev, rawMulti, clusters, fdProfiles, senateVotes }: Props) {
  const [scenario, setScenario] = useState<PresidentialScenario>('rawMulti');
  const data = scenario === 'rawMulti' ? rawMulti : factorDev;

  const clusterByParty = useMemo(
    () => Object.fromEntries(clusters.map(c => [c.party, c])),
    [clusters],
  );

  // Raw Multi winners
  const rmCondWinner = rawMulti.condorcetWinner;
  const rmIrvWinner  = rawMulti.irvWinner;
  const rmCondParty  = rmCondWinner.split('_')[0];
  const rmIrvParty   = rmIrvWinner.split('_')[0];
  const rmSameWinner = rmCondWinner === rmIrvWinner;

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
        <h2 className="text-2xl font-bold text-slate-900 mb-1">2028 Presidential General Election</h2>
        <p className="text-slate-500 text-sm">
          Single-winner race. The question is which method picks the most acceptable president.
          Condorcet finds who beats everyone head-to-head; IRV rewards the candidate with the strongest base.
        </p>
      </div>

      <div className="sticky top-[40px] z-10 bg-white/95 backdrop-blur-sm border-b border-slate-100 -mx-4 px-4 py-2 flex flex-wrap gap-2">
        {(['rawMulti', 'factorDev'] as PresidentialScenario[]).map(s => (
          <button
            key={s}
            onClick={() => setScenario(s)}
            className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
              scenario === s
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
            }`}
          >
            {PRES_LABELS[s]}
          </button>
        ))}
      </div>

      {/* Presidential Outcomes — scenario-dependent */}
      {scenario === 'rawMulti' ? (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest">Presidential Outcomes</h3>
          {rmSameWinner ? (
            <div>
              <div className="text-xs text-slate-400 font-medium uppercase tracking-wider mb-2">
                Winner (both methods): {rmCondWinner}
              </div>
              {clusterByParty[rmCondParty] && <div className="max-w-sm"><PartyProfileCard cluster={clusterByParty[rmCondParty]} /></div>}
            </div>
          ) : (
            <>
              <p className="text-xs text-slate-500">
                Condorcet and IRV elect different presidents — the winner shapes which bills become law.
              </p>
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-slate-400 font-medium uppercase tracking-wider mb-2">
                    Condorcet Winner — {rmCondWinner}
                  </div>
                  {clusterByParty[rmCondParty] && <PartyProfileCard cluster={clusterByParty[rmCondParty]} />}
                </div>
                <div>
                  <div className="text-xs text-slate-400 font-medium uppercase tracking-wider mb-2">
                    IRV Winner — {rmIrvWinner}
                  </div>
                  {clusterByParty[rmIrvParty] && <PartyProfileCard cluster={clusterByParty[rmIrvParty]} />}
                </div>
              </div>

              {divergentBills.length > 0 && (
                <div className="bg-white rounded-xl border border-amber-300 overflow-hidden">
                  <div className="px-4 py-3 bg-amber-50 border-b border-amber-200">
                    <h4 className="text-sm font-semibold text-amber-900">
                      {divergentBills.length} bill{divergentBills.length !== 1 ? 's' : ''} with different presidential outcomes
                    </h4>
                    <p className="text-xs text-amber-700 mt-0.5">
                      Only bills where {rmCondParty} (Condorcet) and {rmIrvParty} (IRV) act differently are shown.
                    </p>
                  </div>

                  <div className="hidden md:grid grid-cols-[1fr_80px_80px] gap-x-2 px-4 py-2 text-xs text-slate-500 border-b border-slate-100 uppercase tracking-widest">
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
                          <div className="text-sm text-slate-800 leading-snug">{r.question}</div>
                          <div className="text-xs text-slate-400 mt-0.5">{r.domain}</div>
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
                </div>
              )}
            </>
          )}
        </div>
      ) : (
        /* Factor Dev — single winner */
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest">Presidential Outcome</h3>
          <p className="text-xs text-slate-500">
            Both Condorcet and IRV elect the same president under Factor Dev.
          </p>
          <div>
            <div className="text-xs text-slate-400 font-medium uppercase tracking-wider mb-2">
              Winner — {fdWinner}
            </div>
            <div className="max-w-sm">
              {clusterByParty[fdWinnerParty] && <PartyProfileCard cluster={clusterByParty[fdWinnerParty]} />}
            </div>
          </div>
        </div>
      )}

      {/* Condorcet head-to-head matrix — centered, 1.5x scale */}
      <div className="bg-white rounded-xl p-6 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
          Head-to-Head Matrix (Condorcet)
        </h3>
        <p className="text-xs text-slate-500 mb-4">
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
      </div>

      {/* IRV vote flow Sankey */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
          IRV Vote Flow
        </h3>
        <p className="text-xs text-slate-500 mb-3">
          Each column is one elimination round. Eliminated candidates&apos; votes fan out to the remaining field.
        </p>
        <IRVSankey rounds={data.irvRounds} irvWinner={data.irvWinner} />
      </div>

      {/* State map */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
          State Results Without National Override
        </h3>
        <p className="text-xs text-slate-500 mb-3">
          How each state would vote independently — no electoral college, no national consolidation.
          Toggle between IRV winner and 1st-choice plurality winner to see where ranked choice flips the outcome.
        </p>
        <PresidentialMap stateWinners={data.irvStateWinners} />
      </div>

      {/* Presidential Policy Comparison — Factor Dev only */}
      {scenario === 'factorDev' && (
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
            Presidential Policy Comparison — Factor Dev · Raw Multi
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            How likely each potential president would sign or veto major legislation.
            Amber rows highlight where the presidents disagree. % = fraction of the president&apos;s
            voter coalition that supports the bill.
          </p>
          <PresidentialComparison rows={senateVotes} factorDev={factorDev} rawMulti={rawMulti} />
        </div>
      )}
    </div>
  );
}

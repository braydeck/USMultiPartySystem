import { useState } from 'react';
import type { PresidentialElection, PresidentialScenario, ClusterProfile, VoteModelRow, FDCandidateProfile } from '../types';
import { PresidentialMap } from '../components/presidential/PresidentialMap';
import { IRVSankey } from '../components/presidential/IRVSankey';
import { WinnerCard } from '../components/presidential/WinnerCard';
import { PresidentialComparison } from '../components/presidential/PresidentialComparison';
import { CondorcetMatrix } from '../components/presidential/CondorcetMatrix';

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

export function PresidentialTab({ factorDev, rawMulti, clusters, fdProfiles, senateVotes }: Props) {
  const [scenario, setScenario] = useState<PresidentialScenario>('rawMulti');
  const data = scenario === 'rawMulti' ? rawMulti : factorDev;

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 mb-1">2028 Presidential General Election</h2>
        <p className="text-slate-500 text-sm">
          Single-winner race. The question is which method picks the most acceptable president.
          Condorcet finds who beats everyone head-to-head; IRV rewards the candidate with the strongest base.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
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

      {/* Hero winner cards — Condorcet preferred */}
      <WinnerCard data={data} clusters={clusters} fdProfiles={fdProfiles} />

      {/* Condorcet head-to-head matrix — explains why Condorcet winner wins */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
          Head-to-Head Matrix (Condorcet)
        </h3>
        <p className="text-xs text-slate-500 mb-3">
          Every possible pairing. Green = row candidate wins; red = row candidate loses.
          The Condorcet winner&apos;s row is all-green — that&apos;s why they win.
        </p>
        <CondorcetMatrix
          matchups={data.condorcetMatchups}
          condorcetWinner={data.condorcetWinner}
        />
      </div>

      {/* State map */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
          State Results
        </h3>
        <p className="text-xs text-slate-500 mb-3">
          Toggle between IRV winner and 1st-choice plurality winner per state to see where the method matters.
        </p>
        <PresidentialMap stateWinners={data.irvStateWinners} />
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

      {/* Three-way presidential comparison */}
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
    </div>
  );
}

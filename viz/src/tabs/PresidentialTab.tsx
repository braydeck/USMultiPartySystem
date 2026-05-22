import { useState } from 'react';
import type { PresidentialElection, PresidentialScenario, ClusterProfile, BlendProfile, VoteModelRow } from '../types';
import { PresidentialMap } from '../components/presidential/PresidentialMap';
import { CondorcetTable } from '../components/presidential/CondorcetTable';
import { IRVRoundsChart } from '../components/presidential/IRVRoundsChart';
import { IRVSankey } from '../components/presidential/IRVSankey';
import { WinnerCard } from '../components/presidential/WinnerCard';
import { PresidentialComparison } from '../components/presidential/PresidentialComparison';

interface Props {
  mixed: PresidentialElection;
  pure:  PresidentialElection;
  lightFusion: PresidentialElection;
  clusters: ClusterProfile[];
  blendProfiles: BlendProfile[];
  senateVotes: VoteModelRow[];
}

const PRES_LABELS: Record<PresidentialScenario, string> = {
  mixed:       'Blended (CON/SD · SD/CON)',
  pure:        'Raw (STY)',
  lightFusion: 'Light Fusion (STY_ctr)',
};

export function PresidentialTab({ mixed, pure, lightFusion, clusters, blendProfiles, senateVotes }: Props) {
  const [scenario, setScenario] = useState<PresidentialScenario>('mixed');
  const data = scenario === 'mixed' ? mixed : scenario === 'pure' ? pure : lightFusion;

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 mb-1">2028 Presidential General Election</h2>
        <p className="text-slate-500 text-sm">
          General election results using IRV and Condorcet methods. Blended scenario
          has CON/SD winning via IRV and SD/CON winning via Condorcet — compare how the
          method changes the outcome. Raw scenario uses only the 9 core party types.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {(Object.keys(PRES_LABELS) as PresidentialScenario[]).map(s => (
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

      {/* Dual winner comparison cards */}
      <WinnerCard data={data} clusters={clusters} blendProfiles={blendProfiles} />

      {/* State map with IRV/Plurality toggle */}
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
          Presidential Policy Comparison — CON/SD · SD/CON · STY · STY_ctr
        </h3>
        <p className="text-xs text-slate-500 mb-4">
          How likely each potential president would sign or veto major legislation.
          Amber rows highlight where the presidents disagree. % = fraction of the president&apos;s
          voter coalition that supports the bill.
        </p>
        <PresidentialComparison rows={senateVotes} />
      </div>

      {/* IRV rounds + Condorcet table */}
      <div className="grid lg:grid-cols-2 gap-8">
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3">
            IRV Rounds Detail
          </h3>
          <p className="text-xs text-slate-500 mb-3">
            Candidates eliminated each round until one clears 50%. Select a round to explore.
          </p>
          <IRVRoundsChart rounds={data.irvRounds} irvWinner={data.irvWinner} />
        </div>

        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3">
            Head-to-Head Matchups (Condorcet)
          </h3>
          <p className="text-xs text-slate-500 mb-3">
            Every possible pairing. The Condorcet winner beats all opponents.
          </p>
          <CondorcetTable matchups={data.condorcetMatchups} condorcetWinner={data.condorcetWinner} />
        </div>
      </div>
    </div>
  );
}

import { useState, useMemo } from 'react';
import type { PrimaryStateWinner, PrimarySankeyData, FDPrimaryData, ClusterProfile } from '../types';
import { PrimaryStateMap } from '../components/primary/PrimaryStateMap';
import AlluvialFlow from '../components/primary/AlluvialFlow';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { PartyProfileCard } from '../components/shared/PartyProfileCard';
import { PARTY_NAMES, F5_ORDER } from '../constants/parties';

interface Props {
  factorDev: FDPrimaryData;
  factorDevStateWinners: Record<string, PrimaryStateWinner>;
  factorDevSankey: PrimarySankeyData;
  pureMulti: FDPrimaryData;
  pureMultiStateWinners: Record<string, PrimaryStateWinner>;
  pureMultiSankey: PrimarySankeyData;
  clusters: ClusterProfile[];
  clusterSpreads: { party: string; n: number; [key: string]: string | number }[];
}

type Pipeline = 'factorDev' | 'rawMulti';

const PIPELINE_LABELS: Record<Pipeline, string> = {
  factorDev: 'Factor Dev (37 candidates)',
  rawMulti:  'Raw Multi (27 candidates)',
};

const PIPELINE_DESC: Record<Pipeline, string> = {
  factorDev: '9 base parties + 28 axis-deviation variants (SO, AE, PC) at ±25% of inter-party SD. Candidates deviate on individual factor axes rather than blending toward a neighbor.',
  rawMulti:  'All 9 parties field 3 intra-party candidates each (40/35/25 first-choice split). Same-party candidates share an identical factor-space position; prominence determines ballot ordering.',
};

export function PrimaryTab({
  factorDev, factorDevStateWinners, factorDevSankey,
  pureMulti, pureMultiStateWinners, pureMultiSankey,
  clusters, clusterSpreads,
}: Props) {
  const clusterByParty = useMemo(() => Object.fromEntries(clusters.map(c => [c.party, c])), [clusters]);
  const orderedClusters = useMemo(() => F5_ORDER.map(p => clusterByParty[p]).filter(Boolean) as ClusterProfile[], [clusterByParty]);
  const [pipeline, setPipeline] = useState<Pipeline>('rawMulti');
  const [stageIdx, setStageIdx] = useState(0);

  const data: FDPrimaryData =
    pipeline === 'factorDev' ? factorDev : pureMulti;
  const stateWinners = pipeline === 'factorDev' ? factorDevStateWinners : pureMultiStateWinners;
  const sankey = pipeline === 'factorDev' ? factorDevSankey : pureMultiSankey;

  const stage = data.stagesOrder[stageIdx] ?? data.stagesOrder[0];
  const prevStage = stageIdx > 0 ? data.stagesOrder[stageIdx - 1] : null;
  const quota = data.quotaByStage[stage] ?? 0;
  const stageLabel = data.stageLabels[stage] ?? stage;

  const activeCandidates = data.candidates.filter(c =>
    data.stagesOrder.some(s => (c.stages[s]?.votePct ?? 0) > 0)
  );

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 mb-1">2028 Presidential Primary</h2>
        <p className="text-slate-500 text-sm">
          A 4-round STV simulation across regional pods — a crowded field collapses into a final set of survivors
          through elimination rounds. Quota = {(quota * 100).toFixed(1)}%.
        </p>
      </div>

      {/* Pipeline toggle */}
      <div className="space-y-2">
        <div className="flex flex-wrap gap-2">
          {(['rawMulti', 'factorDev'] as Pipeline[]).map(p => (
            <button
              key={p}
              onClick={() => { setPipeline(p); setStageIdx(0); }}
              className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
                pipeline === p
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
              }`}
            >
              {PIPELINE_LABELS[p]}
            </button>
          ))}
        </div>
        <p className="text-xs text-slate-500">{PIPELINE_DESC[pipeline]}</p>
      </div>

      {/* Stage selector */}
      <div className="flex flex-wrap gap-2">
        {data.stagesOrder.map((s, i) => (
          <button
            key={s}
            onClick={() => setStageIdx(i)}
            className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
              stageIdx === i
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
            }`}
          >
            {data.stageLabels[s] ?? s}
          </button>
        ))}
      </div>

      {/* State map — full width */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
          State Winners by Stage
        </h3>
        <p className="text-xs text-slate-500 mb-3">
          States light up as their pod votes. Color = IRV winner in that state&apos;s race.
        </p>
        <PrimaryStateMap stateWinners={stateWinners} stage={stage} />
      </div>

      {/* Vote Transfer Flow — Sankey, full width, elevated */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
          Vote Transfer Flows
        </h3>
        <p className="text-xs text-slate-500 mb-3">
          Each column = one elimination round. Band width = vote share. Darker ribbons = elimination transfers.
          Hover blocks and ribbons for details.
        </p>
        <AlluvialFlow data={sankey} highlightStage={stageIdx + 1} />
      </div>

      {/* Ideological Constellation + Party Profiles */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
          Ideological Constellation
        </h3>
        <p className="text-xs text-slate-500 mb-4">
          Drag axes to explore ideological dimensions. Bubble size = house seats. Links = transfer affinity.
        </p>
        <IdeologicalConstellation
          nodes={clusters.filter(c => c.party).map(c => ({
            id: c.party,
            label: PARTY_NAMES[c.party] ?? c.party,
            seats: c.seatsHouse,
            F1: c.F1, F2: c.F2, F3: c.F3, F4: c.F4, F5: c.F5,
          }))}
          clusterSpreads={clusterSpreads}
        />
      </div>

      <div>
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">Nine-Party Profiles</h3>
        <p className="text-xs text-slate-500 mb-4">
          Ordered left→right by Ideology (F5). Percentiles show each party&apos;s position relative to the average of all American voters surveyed.
        </p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {orderedClusters.map(cluster => (
            <PartyProfileCard key={cluster.party} cluster={cluster} />
          ))}
        </div>
      </div>

      {/* Stage summary cards */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3">
          How the Primary Unfolds
        </h3>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
          {data.stagesOrder.map((s, i) => {
            const survivors = data.candidates.filter(c =>
              ['surviving', 'elected'].includes(c.stages[s]?.status ?? '')
            );
            const eliminated = data.candidates.filter(c =>
              c.stages[s]?.status === 'eliminated_this_round'
            );
            return (
              <div
                key={s}
                className={`rounded-lg p-3 border cursor-pointer transition-colors ${
                  stageIdx === i
                    ? 'border-indigo-300 bg-indigo-50'
                    : 'border-slate-200 bg-slate-50 hover:border-slate-300'
                }`}
                onClick={() => setStageIdx(i)}
              >
                <div className="text-xs text-indigo-600 font-semibold mb-1">Stage {i + 1}</div>
                <div className="font-medium text-slate-900 text-xs mb-2">{data.stageLabels[s]}</div>
                <div className="text-xs text-slate-500">
                  {survivors.length} surviving, {eliminated.length} eliminated
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

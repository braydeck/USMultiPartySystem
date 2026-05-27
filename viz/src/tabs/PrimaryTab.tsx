import { useState, useMemo } from 'react';
import type { PrimaryStateWinner, PrimarySankeyData, FDPrimaryData, ClusterProfile } from '../types';
import { PrimaryStateMap } from '../components/primary/PrimaryStateMap';
import PrimaryStageBars from '../components/primary/PrimaryStageBars';
import PrimaryBuckets from '../components/primary/PrimaryBuckets';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { PartyProfileGrid } from '../components/shared/PartyProfileGrid';
import { PARTY_NAMES, PARTY_COLORS, F5_ORDER } from '../constants/parties';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type BucketData = any; // from pureMultiPrimaryBuckets.json

interface Props {
  factorDev: FDPrimaryData;
  factorDevStateWinners: Record<string, PrimaryStateWinner>;
  factorDevSankey: PrimarySankeyData;
  pureMulti: FDPrimaryData;
  pureMultiStateWinners: Record<string, PrimaryStateWinner>;
  pureMultiSankey: PrimarySankeyData;
  pureMultiBuckets: BucketData;
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
  pureMulti, pureMultiStateWinners, pureMultiSankey, pureMultiBuckets,
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

      {/* Stage selector + party legend — sticky below main nav */}
      <div className="sticky top-[40px] z-10 bg-white/95 backdrop-blur-sm border-b border-slate-100 -mx-4 px-4 py-2 space-y-1.5">
        <div className="flex flex-wrap gap-2">
          {data.stagesOrder.map((s, i) => (
            <button
              key={s}
              onClick={() => setStageIdx(i)}
              className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
                stageIdx === i
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
              }`}
            >
              {data.stageLabels[s] ?? s}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-x-3 gap-y-0.5">
          {F5_ORDER.map(p => (
            <span key={p} className="flex items-center gap-1 text-[10px] text-slate-500">
              <span
                className="inline-block w-2.5 h-2.5 rounded-sm"
                style={{ backgroundColor: PARTY_COLORS[p] }}
              />
              {PARTY_NAMES[p] ?? p}
            </span>
          ))}
        </div>
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

      {/* Primary Winnowing — stage-by-stage stacked bars */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
          Primary Winnowing
        </h3>
        <p className="text-xs text-slate-500 mb-3">
          Each bar shows surviving candidates after a round. Bar width = vote share. Dimmed segments = eliminated next round.
          Dashed line = Droop quota. Hover for details.
        </p>
        <PrimaryStageBars data={data} highlightStage={stageIdx + 1} />
      </div>

      {/* Bucket Chart — how each winner filled their quota */}
      {pipeline === 'rawMulti' && pureMultiBuckets?.stages?.[stageIdx] && (
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
            How Winners Fill Their Quota
          </h3>
          <p className="text-xs text-slate-500 mb-3">
            Each bar shows where a winner&apos;s votes came from. Darkest = own first-choice supporters.
            Other colors = transfers from surplus or eliminated candidates. Dashed line = quota threshold.
          </p>
          <PrimaryBuckets data={pureMultiBuckets} stageIdx={stageIdx} />
        </div>
      )}

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
            label: c.party,
            seats: c.seatsHouse,
            F1: ((c as any).z_F1 ?? 0),
            F2: ((c as any).z_F2 ?? 0),
            F3: ((c as any).z_F3 ?? 0),
            F4: ((c as any).z_F4 ?? 0),
            F5: ((c as any).z_F5 ?? 0),
          }))}
          clusterSpreads={clusterSpreads}
        />
      </div>

      <PartyProfileGrid clusters={orderedClusters} />

    </div>
  );
}

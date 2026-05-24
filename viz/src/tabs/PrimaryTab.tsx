import { useState } from 'react';
import type { PrimaryStateWinner, PrimarySankeyData, FDPrimaryData, ClusterProfile } from '../types';
import { EliminationWaterfall } from '../components/primary/EliminationWaterfall';
import { IdeologicalScatter } from '../components/primary/IdeologicalScatter';
import { PrimaryStateMap } from '../components/primary/PrimaryStateMap';
import AlluvialFlow from '../components/primary/AlluvialFlow';
import { MiniPartyCard } from '../components/shared/MiniPartyCard';
import { PartyVariantBar } from '../components/shared/PartyVariantBar';

interface Props {
  factorDev: FDPrimaryData;
  factorDevStateWinners: Record<string, PrimaryStateWinner>;
  factorDevSankey: PrimarySankeyData;
  pureMulti: FDPrimaryData;
  pureMultiStateWinners: Record<string, PrimaryStateWinner>;
  pureMultiSankey: PrimarySankeyData;
  clusters: ClusterProfile[];
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
  clusters,
}: Props) {
  const clusterByParty = Object.fromEntries(clusters.map(c => [c.party, c]));
  const [pipeline, setPipeline] = useState<Pipeline>('rawMulti');
  const [stageIdx, setStageIdx] = useState(0);

  const data: FDPrimaryData =
    pipeline === 'factorDev' ? factorDev : pureMulti;
  const stateWinners = pipeline === 'factorDev' ? factorDevStateWinners : pureMultiStateWinners;
  const sankey = pipeline === 'factorDev' ? factorDevSankey : pureMultiSankey;

  // For PartyVariantBar: map candidates to FDHouseSeat-like shape using Retail stage vote share
  const variantFirstChoice = data.candidates.map(c => ({
    code: c.code,
    party: (c as { party?: string }).party ?? c.code,
    axis: (c as { axis?: string }).axis ?? 'base',
    direction: (c as { direction?: string }).direction ?? 'base',
    urban: 0, suburban: 0, rural: 0,
    national: Math.round((c.stages['After_Retail_Six']?.votePct ?? 0) * 10),
    pctNational: c.stages['After_Retail_Six']?.votePct ?? 0,
  }));

  const stage = data.stagesOrder[stageIdx] ?? data.stagesOrder[0];
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
          A 4-round STV simulation across regional pods — watch as candidates consolidate
          from a crowded field to the final survivors. Quota = {quota.toFixed(0)} votes.
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

      {/* State map — full width (not shown for rawMulti: pod system, no per-state accumulation) */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
          State Winners by Stage
        </h3>
        <p className="text-xs text-slate-500 mb-3">
          States light up as their pod votes. Color = IRV winner in that state&apos;s race.
        </p>
        <PrimaryStateMap stateWinners={stateWinners} stage={stage} />
      </div>

      {/* Mini cards for active candidates */}
      <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-2">
        {activeCandidates
          .filter(c => ['surviving', 'elected', 'active'].includes(c.stages[stage]?.status ?? ''))
          .sort((a, b) => a.F5 - b.F5)
          .map(c => {
            const baseParty = c.code.split('_')[0];
            const positions = clusterByParty[baseParty]?.keyPositions ?? [];
            return (
              <MiniPartyCard
                key={c.code}
                code={c.code}
                votePct={c.stages[stage]?.votePct}
                positions={positions}
              />
            );
          })}
      </div>

      {/* Waterfall + scatter side by side */}
      <div className="grid lg:grid-cols-2 gap-8">
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3">
            Pod Vote Share — {stageLabel}
          </h3>
          <p className="text-xs text-slate-500 mb-3">
            First-choice % among votes cast in this pod&apos;s cumulative pool. Yellow = quota threshold. Red border = eliminated this round.
          </p>
          <EliminationWaterfall
            candidates={activeCandidates}
            stage={stage}
            quota={quota}
          />
        </div>

        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3">
            Ideological Positions
          </h3>
          <p className="text-xs text-slate-500 mb-3">
            Bubble size = vote share. Opacity = Religious Traditionalism (F4).
            Outlined = eliminated.
          </p>
          <IdeologicalScatter candidates={activeCandidates} stage={stage} />
        </div>
      </div>

      {/* Alluvial flow — vote transfer across stages */}
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

      {/* Variant breakdown bar */}
      {variantFirstChoice.length > 0 && (
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
            First-Choice Distribution by{pipeline === 'factorDev' ? ' Variant' : ' Candidate'}
          </h3>
          <p className="text-xs text-slate-500 mb-3">
            {pipeline === 'factorDev'
              ? 'Scaled vote share after Retail + Bench States. Full color = base; lighter = hi axis; darker = lo axis.'
              : 'Scaled vote share after Retail + Bench States. All candidates are base (no axis deviation).'}
          </p>
          <PartyVariantBar seats={variantFirstChoice} totalLabel="first-choice vote share (×10 = tenths of %)" />
        </div>
      )}
    </div>
  );
}

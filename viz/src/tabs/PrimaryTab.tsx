import { useState } from 'react';
import type { PrimaryData, PrimaryStateWinner, PrimarySankeyData, BlendProfile, ClusterProfile } from '../types';
import { EliminationWaterfall } from '../components/primary/EliminationWaterfall';
import { IdeologicalScatter } from '../components/primary/IdeologicalScatter';
import { PrimaryStateMap } from '../components/primary/PrimaryStateMap';
import AlluvialFlow from '../components/primary/AlluvialFlow';
import { MiniPartyCard } from '../components/shared/MiniPartyCard';

interface Props {
  blended: PrimaryData;
  blendedStateWinners: Record<string, PrimaryStateWinner>;
  blendedSankey: PrimarySankeyData;
  raw: PrimaryData;
  rawStateWinners: Record<string, PrimaryStateWinner>;
  rawSankey: PrimarySankeyData;
  lightFusion: PrimaryData;
  lightFusionStateWinners: Record<string, PrimaryStateWinner>;
  lightFusionSankey: PrimarySankeyData;
  blendProfiles: BlendProfile[];
  clusters: ClusterProfile[];
}

type Pipeline = 'blended' | 'light_fusion' | 'raw';

const PIPELINE_LABELS: Record<Pipeline, string> = {
  blended:      'Blended (~20 candidates)',
  light_fusion: 'Light Fusion (25 candidates)',
  raw:          'Pure (9 parties)',
};

const PIPELINE_DESC: Record<Pipeline, string> = {
  blended:      'Senate-derived blended candidates representing coalition archetypes.',
  light_fusion: '9 pure parties + 16 "slight deviant" variants at 80/20 — candidates who would still caucus with their primary party but lean slightly toward an adjacent one.',
  raw:          'Only the 9 pure party archetypes. Note: some parties get very few first-choice votes in this scenario.',
};

export function PrimaryTab({
  blended, blendedStateWinners, blendedSankey,
  raw, rawStateWinners, rawSankey,
  lightFusion, lightFusionStateWinners, lightFusionSankey,
  blendProfiles, clusters,
}: Props) {
  const blendByCode = Object.fromEntries(blendProfiles.map(p => [p.code, p]));
  const clusterByParty = Object.fromEntries(clusters.map(c => [c.party, c]));
  const [pipeline, setPipeline] = useState<Pipeline>('light_fusion');
  const [stageIdx, setStageIdx] = useState(0);

  const data = pipeline === 'blended' ? blended : pipeline === 'light_fusion' ? lightFusion : raw;
  const stateWinners = pipeline === 'blended' ? blendedStateWinners : pipeline === 'light_fusion' ? lightFusionStateWinners : rawStateWinners;
  const sankey = pipeline === 'blended' ? blendedSankey : pipeline === 'light_fusion' ? lightFusionSankey : rawSankey;

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
          {(['light_fusion', 'blended', 'raw'] as Pipeline[]).map(p => (
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

      {/* Mini cards for active candidates */}
      <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-2">
        {activeCandidates
          .filter(c => ['surviving', 'elected', 'active'].includes(c.stages[stage]?.status ?? ''))
          .sort((a, b) => a.F5 - b.F5)
          .map(c => {
            const positions = blendByCode[c.code]?.keyPositions
              ?? clusterByParty[c.code]?.keyPositions
              ?? [];
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
    </div>
  );
}

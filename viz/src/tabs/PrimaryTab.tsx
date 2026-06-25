import { useMemo, type ReactNode } from 'react';
import { useUrlState, useUrlNumber } from '../hooks/useUrlState';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import type { PrimaryStateWinner, PrimaryStageShares, PrimarySankeyData, FDPrimaryData, ClusterProfile } from '../types';
import { PrimaryStateMap } from '../components/primary/PrimaryStateMap';
import PrimaryBuckets from '../components/primary/PrimaryBuckets';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { PartyProfileGrid } from '../components/shared/PartyProfileGrid';
import { PARTY_NAMES, PARTY_COLORS, F5_ORDER, getBlendColor, getContrastText } from '../constants/parties';
import { PIPELINE_LABELS_LONG, PIPELINE_DESC } from '../constants/labels';
import { ToggleGroup } from '../components/shared/ToggleGroup';
import { StickyControlBar } from '../components/shared/StickyControlBar';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type BucketData = any; // from pureMultiPrimaryBuckets.json

interface Props {
  factorDev: FDPrimaryData;
  factorDevStateWinners: Record<string, PrimaryStateWinner>;
  factorDevStageShares: Record<string, PrimaryStageShares>;
  factorDevBuckets: BucketData;
  factorDevSankey: PrimarySankeyData;
  pureMulti: FDPrimaryData;
  pureMultiStateWinners: Record<string, PrimaryStateWinner>;
  pureMultiStageShares: Record<string, PrimaryStageShares>;
  pureMultiSankey: PrimarySankeyData;
  pureMultiBuckets: BucketData;
  clusters: ClusterProfile[];
  clusterSpreads: { party: string; n: number; [key: string]: string | number }[];
  /** Optional control rendered first in the sticky control bar (e.g. the Presidency View toggle). */
  controlBarExtra?: ReactNode;
}

type Pipeline = 'factorDev' | 'rawMulti';

export function PrimaryTab({
  factorDev, factorDevStageShares, factorDevBuckets,
  pureMulti, pureMultiStageShares, pureMultiBuckets,
  clusters, clusterSpreads, controlBarExtra,
}: Props) {
  const clusterByParty = useMemo(() => Object.fromEntries(clusters.map(c => [c.party, c])), [clusters]);
  const orderedClusters = useMemo(() => F5_ORDER.map(p => clusterByParty[p]).filter(Boolean) as ClusterProfile[], [clusterByParty]);
  const [pipeline, setPipeline] = useUrlState<Pipeline>('pipeline', 'rawMulti', { allowed: ['rawMulti', 'factorDev'], map: { factorDev: 'crossover', rawMulti: 'party-line' } });
  const [stageIdx, setStageIdx] = useUrlNumber('stage', 0);

  const data: FDPrimaryData =
    pipeline === 'factorDev' ? factorDev : pureMulti;
  const stageShares  = pipeline === 'factorDev' ? factorDevStageShares : pureMultiStageShares;
  const stage = data.stagesOrder[stageIdx] ?? data.stagesOrder[0];
  const quota = data.quotaByStage[stage] ?? 0;

  // National first-choice shares aggregated from stage-specific state data
  const STAGE_PODS: Record<string, Set<string>> = {
    After_Retail: new Set(['Retail']),
    After_Pod_A:  new Set(['Retail', 'A']),
    After_Pod_C:  new Set(['Retail', 'A', 'C']),
    After_Pod_BD: new Set(['Retail', 'A', 'B', 'C', 'D']),
  };
  const nationalShares = useMemo(() => {
    const activePods = STAGE_PODS[stage] ?? new Set();
    const totals: Record<string, number> = {};
    let totalResp = 0;
    for (const ss of Object.values(stageShares)) {
      if (!activePods.has(ss.pod)) continue;
      const stageData = ss.stages[stage];
      if (!stageData) continue;
      const n = ss.nRespondents;
      totalResp += n;
      for (const [code, share] of Object.entries(stageData.shares)) {
        totals[code] = (totals[code] ?? 0) + share * n;
      }
    }
    if (totalResp === 0) return [];
    return Object.entries(totals)
      .map(([code, weighted]) => ({ code, pct: weighted / totalResp }))
      .sort((a, b) => b.pct - a.pct);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stageShares, stage]);

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-1">2028 Presidential Primary</h2>
        <p className="text-muted-foreground text-sm">
          A 4-round STV simulation across regional pods — a crowded field collapses into a final set of survivors
          through elimination rounds. Quota = {(quota * 100).toFixed(1)}%.
        </p>
      </div>

      {/* Sticky controls */}
      <StickyControlBar>
        {controlBarExtra}
        <ToggleGroup label="Scenario"
          value={pipeline}
          onChange={(p) => { setPipeline(p); setStageIdx(0); }}
          options={['rawMulti', 'factorDev'] as const}
          labels={PIPELINE_LABELS_LONG}
        />
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground uppercase tracking-widest">Stage</span>
          <div className="flex gap-1">
            {data.stagesOrder.map((s, i) => (
              <Button key={s} onClick={() => setStageIdx(i)}
                variant={stageIdx === i ? 'default' : 'secondary'} size="sm">
                {data.stageLabels[s] ?? s}
              </Button>
            ))}
          </div>
        </div>
      </StickyControlBar>
      <p className="text-xs text-muted-foreground">{PIPELINE_DESC[pipeline]}</p>
      <div className="flex flex-wrap gap-1.5">
        {F5_ORDER.map(p => (
          <span
            key={p}
            className="px-1.5 py-0.5 rounded text-[10px] font-semibold leading-none chip-text"
            style={{ backgroundColor: PARTY_COLORS[p], color: getContrastText(PARTY_COLORS[p]) }}
          >
            {PARTY_NAMES[p] ?? p}
          </span>
        ))}
      </div>

      {/* Primary Winnowing — bucket composition */}
      {(() => {
        const buckets = pipeline === 'rawMulti' ? pureMultiBuckets : factorDevBuckets;
        return buckets?.stages?.[stageIdx] ? (
          <Card className="p-4">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
              Primary Winnowing
            </h3>
            <p className="text-xs text-muted-foreground mb-3">
              Each bar shows where a survivor&apos;s votes came from. Darkest = own first-choice supporters.
              Other colors = transfers from surplus or eliminated candidates.
            </p>
            <PrimaryBuckets data={buckets} stageIdx={stageIdx} />
          </Card>
        ) : null;
      })()}

      {/* National First-Choice Share */}
      {nationalShares.length > 0 && (
        <Card className="p-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
            National First-Choice Share
          </h3>
          <p className="text-xs text-muted-foreground mb-3">
            Aggregate first-choice vote across states that have voted at this stage.
          </p>
          <div>
            <div className="text-sm mb-2">
              <span className="font-bold" style={{ color: getBlendColor(nationalShares[0].code) }}>
                {nationalShares[0].code}
              </span>
              <span className="text-foreground"> leads with </span>
              <span className="font-bold">{(nationalShares[0].pct * 100).toFixed(1)}%</span>
              <span className="text-muted-foreground"> of the first-choice vote</span>
            </div>
            <div className="flex rounded overflow-hidden h-8 mb-2">
              {nationalShares.map(({ code, pct }) => {
                const w = pct * 100;
                const color = getBlendColor(code);
                return (
                  <div
                    key={code}
                    className="flex items-center justify-center overflow-hidden"
                    style={{ width: `${w}%`, backgroundColor: color, minWidth: w < 2 ? 2 : 0 }}
                    title={`${code}: ${(pct * 100).toFixed(1)}%`}
                  >
                    {w > 5 && (
                      <span className="text-xs font-bold px-0.5 truncate chip-text"
                        style={{ color: getContrastText(color), textShadow: '0 1px 2px rgba(0,0,0,0.5)' }}>
                        {code} {(pct * 100).toFixed(1)}%
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </Card>
      )}

      {/* State Vote Shares */}
      <Card className="p-4">
        <div className="flex items-center gap-2 mb-1">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">
            State Vote Shares
          </h3>
          <span className="text-[10px] font-semibold uppercase tracking-widest text-foreground bg-muted rounded px-1.5 py-0.5">
            {data.stageLabels[stage] ?? stage}
          </span>
        </div>
        <p className="text-xs text-muted-foreground mb-3">
          States light up as their pod votes. Bars show first-choice vote proportions. Hover for breakdown.
        </p>
        <PrimaryStateMap stageShares={stageShares} stage={stage} primaryData={data} />
      </Card>

      {/* Ideological Constellation + Party Profiles */}
      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
          Ideological Constellation
        </h3>
        <p className="text-xs text-muted-foreground mb-4">
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
      </Card>

      <PartyProfileGrid clusters={orderedClusters} />

    </div>
  );
}

import { useMemo } from 'react';
import { useUrlState } from '../hooks/useUrlState';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import type { SenateSeat, VoteModelRow, SenateScenario, ClusterProfile, ConstellationNode, FDSenateSeat, FDHouseSeat, FDCandidateProfile } from '../types';
import { SenateMap } from '../components/senate/SenateMap';
import { VoteModelTable } from '../components/senate/VoteModelTable';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { ParliamentChart } from '../components/shared/ParliamentChart';
import { PartyVariantBar } from '../components/shared/PartyVariantBar';
import { PartyProfileGrid } from '../components/shared/PartyProfileGrid';
import type { ParliamentSegment } from '../components/shared/ParliamentChart';
import { FACTOR_LABELS, DISPLAY_FACTORS, partyOrder } from '../constants/parties';
import { PIPELINE_LABELS, METHOD_LABELS } from '../constants/labels';
import { ToggleGroup } from '../components/shared/ToggleGroup';
import { ParticipationSlider, GAP_STOPS } from '../components/shared/ParticipationSlider';
import { StickyControlBar } from '../components/shared/StickyControlBar';
// Compression stops (5-point steps to 30% of the turnout gap closed); floor comes via props.
import senCondL5 from '../data/pureMultiSenateCondorcetTurnoutL5.json';
import senCondL10 from '../data/pureMultiSenateCondorcetTurnoutL10.json';
import senCondL15 from '../data/pureMultiSenateCondorcetTurnoutL15.json';
import senCondL20 from '../data/pureMultiSenateCondorcetTurnoutL20.json';
import senCondL25 from '../data/pureMultiSenateCondorcetTurnoutL25.json';
import senCondL30 from '../data/pureMultiSenateCondorcetTurnoutL30.json';
import senIrvL5 from '../data/pureMultiSenateIRVTurnoutL5.json';
import senIrvL10 from '../data/pureMultiSenateIRVTurnoutL10.json';
import senIrvL15 from '../data/pureMultiSenateIRVTurnoutL15.json';
import senIrvL20 from '../data/pureMultiSenateIRVTurnoutL20.json';
import senIrvL25 from '../data/pureMultiSenateIRVTurnoutL25.json';
import senIrvL30 from '../data/pureMultiSenateIRVTurnoutL30.json';
// Crossover (FD) senate compression stops.
import fdSenCond0 from '../data/fdSenateCondorcetTurnout.json';
import fdSenCond5 from '../data/fdSenateCondorcetTurnoutL5.json';
import fdSenCond10 from '../data/fdSenateCondorcetTurnoutL10.json';
import fdSenCond15 from '../data/fdSenateCondorcetTurnoutL15.json';
import fdSenCond20 from '../data/fdSenateCondorcetTurnoutL20.json';
import fdSenCond25 from '../data/fdSenateCondorcetTurnoutL25.json';
import fdSenCond30 from '../data/fdSenateCondorcetTurnoutL30.json';
import fdSenIrv0 from '../data/fdSenateIRVTurnout.json';
import fdSenIrv5 from '../data/fdSenateIRVTurnoutL5.json';
import fdSenIrv10 from '../data/fdSenateIRVTurnoutL10.json';
import fdSenIrv15 from '../data/fdSenateIRVTurnoutL15.json';
import fdSenIrv20 from '../data/fdSenateIRVTurnoutL20.json';
import fdSenIrv25 from '../data/fdSenateIRVTurnoutL25.json';
import fdSenIrv30 from '../data/fdSenateIRVTurnoutL30.json';
// Senate bill vote model, tracked across turnout (rank-7 winnow + depth-7 president = app default).
import senVMTurnout from '../data/senateVoteModelTurnout.json';
import senVML5 from '../data/senateVoteModelTurnoutL5.json';
import senVML10 from '../data/senateVoteModelTurnoutL10.json';
import senVML15 from '../data/senateVoteModelTurnoutL15.json';
import senVML20 from '../data/senateVoteModelTurnoutL20.json';
import senVML25 from '../data/senateVoteModelTurnoutL25.json';
import senVML30 from '../data/senateVoteModelTurnoutL30.json';
import SenateBuckets from '../components/senate/SenateBuckets';
import SenateCondorcetView from '../components/senate/SenateCondorcetView';
import { SenateCompositionCard } from '../components/senate/SenateCompositionCard';
import { VariantImpactChart } from '../components/house/VariantImpactChart';
import { VariantAttractionChart } from '../components/house/VariantAttractionChart';
import { AttractionDriverChart } from '../components/house/AttractionDriverChart';

interface Props {
  condorcetFD:       FDSenateSeat[];
  irvFD:             FDSenateSeat[];
  condorcetRawMulti: FDSenateSeat[];
  irvRawMulti:       FDSenateSeat[];
  condorcetRawMultiTurnout: FDSenateSeat[];
  irvRawMultiTurnout:       FDSenateSeat[];
  voteModel:         VoteModelRow[];
  clusters:          ClusterProfile[];
  fdProfiles:        Record<string, FDCandidateProfile>;
  clusterSpreads:    { party: string; n: number; [key: string]: string | number }[];
  houseTransfers: { source: string; totalVoters: number; destinations: { party: string; pct: number }[] }[];
  fdVariantAttraction: { variant: string; party: string; axis: string; direction: string; totalVoters: number; homePct: number; crossPct: number; sources: { party: string; pct: number }[] }[];
  fdAttractionDrivers: { variant: string; party: string; axis: string; direction: string; attracted: string; attractedPct: number; factors: { factor: string; pct: number }[] }[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  senateBuckets: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  senateCondorcet: any;
}

export function SenateTab({ condorcetRawMultiTurnout, irvRawMultiTurnout,
                             clusters, fdProfiles, clusterSpreads,
                             fdVariantAttraction, fdAttractionDrivers,
                             senateBuckets, senateCondorcet }: Props) {
  const [pipeline, setPipeline] = useUrlState<'factorDev' | 'rawMulti'>('pipeline', 'rawMulti', { allowed: ['factorDev', 'rawMulti'], map: { factorDev: 'crossover', rawMulti: 'party-line' } });
  const [method, setMethod] = useUrlState<'condorcet' | 'irv'>('method', 'condorcet', { allowed: ['condorcet', 'irv'] });
  // Participation: gap-compression stop (0 = observed 2024 turnout … 100 = full parity).
  const [part, setPart] = useUrlState<string>('part', '5', { allowed: ['0', '5', '10', '15', '20', '25', '30'] });
  const rawMultiOn = pipeline === 'rawMulti';
  const gi = Math.max(0, GAP_STOPS.indexOf(Number(part) as typeof GAP_STOPS[number]));
  // Bill vote model at the current turnout stop (rank-7 winnow + depth-7 president baked in).
  const vmStops = [senVMTurnout, senVML5, senVML10, senVML15, senVML20, senVML25, senVML30] as unknown as VoteModelRow[][];
  const vmRows = vmStops[gi];
  // Each state elects one senator among 5 finalists via IRV/Condorcet; voters rank all 5 (full
  // ranking), so there is no ballot-depth toggle here.
  // Compression stops [0,5,10,15,20,25,30] for each pipeline; condRM/irvRM are the ACTIVE
  // scenario's Condorcet/IRV senate at the current turnout stop.
  const rmCondStops = [condorcetRawMultiTurnout, senCondL5, senCondL10, senCondL15, senCondL20, senCondL25, senCondL30] as unknown as FDSenateSeat[][];
  const rmIrvStops  = [irvRawMultiTurnout, senIrvL5, senIrvL10, senIrvL15, senIrvL20, senIrvL25, senIrvL30] as unknown as FDSenateSeat[][];
  const fdCondStops = [fdSenCond0, fdSenCond5, fdSenCond10, fdSenCond15, fdSenCond20, fdSenCond25, fdSenCond30] as unknown as FDSenateSeat[][];
  const fdIrvStops  = [fdSenIrv0, fdSenIrv5, fdSenIrv10, fdSenIrv15, fdSenIrv20, fdSenIrv25, fdSenIrv30] as unknown as FDSenateSeat[][];
  const condRM = (rawMultiOn ? rmCondStops : fdCondStops)[gi];
  const irvRM  = (rawMultiOn ? rmIrvStops  : fdIrvStops )[gi];

  const [parliamentFactor, setParliamentFactor] = useUrlState<string>('factor', 'F5', { allowed: [...DISPLAY_FACTORS] });


  const scenario: SenateScenario =
    pipeline === 'factorDev'
      ? (method === 'condorcet' ? 'condFD' : 'irvFD')
      : (method === 'condorcet' ? 'condRawMulti' : 'irvRawMulti');

  // condRM/irvRM already resolve to the active pipeline, so both scenarios map to them.
  const SEAT_MAP: Record<SenateScenario, SenateSeat[]> = {
    condFD:       condRM as unknown as SenateSeat[],
    irvFD:        irvRM  as unknown as SenateSeat[],
    condRawMulti: condRM as unknown as SenateSeat[],
    irvRawMulti:  irvRM  as unknown as SenateSeat[],
  };
  const activeSeats = SEAT_MAP[scenario];

  const seatCounts: Record<string, number> = {};
  for (const s of activeSeats) {
    seatCounts[s.senatorCode] = (seatCounts[s.senatorCode] ?? 0) + 1;
  }

  const clusterByParty = useMemo(
    () => Object.fromEntries(clusters.map(c => [c.party, c])),
    [clusters]
  );
  const orderedClusters = useMemo(() => partyOrder().map(p => clusterByParty[p]).filter(Boolean) as ClusterProfile[], [clusterByParty]);

  function getFactorScore(code: string, factor: string): number {
    const zKey = `z_${factor}`;
    const cl = clusterByParty[code];
    if (cl) { const z = (cl as any)[zKey]; if (z != null) return z; }
    const base = code.split('_')[0];
    const baseCl = clusterByParty[base];
    if (baseCl) { const z = (baseCl as any)[zKey]; if (z != null) return z; }
    const fd = fdProfiles[code];
    if (fd) return (fd as unknown as Record<string, number>)[factor] ?? 0;
    return 0;
  }

  const globalRange = useMemo((): [number, number] => {
    const vals = [
      ...clusters.map(c => (c as unknown as Record<string, number>)[parliamentFactor] ?? 0),
      ...Object.values(fdProfiles).map(p => (p as unknown as Record<string, number>)[parliamentFactor] ?? 0),
    ];
    return vals.length > 0 ? [Math.min(...vals), Math.max(...vals)] : [-2, 2];
  }, [clusters, fdProfiles, parliamentFactor]);

  const parliamentSegments: ParliamentSegment[] = Object.entries(seatCounts)
    .map(([code, seats]) => {
      const base = getFactorScore(code, parliamentFactor);
      const nSuffix = parseInt(code.split('_').pop() ?? '') || 0;
      return { code, seats, fVal: base + (nSuffix > 0 ? (nSuffix - 1) * 0.001 : 0) };
    })
    .sort((a, b) => a.fVal - b.fVal);

  // Variant seat data for PartyVariantBar
  const fdVariantSeats = useMemo((): FDHouseSeat[] => {
    const fdSeats = (method === 'condorcet' ? condRM : irvRM);
    const countByCode: Record<string, FDHouseSeat> = {};
    for (const seat of fdSeats) {
      const key = seat.senatorCode;
      if (!countByCode[key]) {
        countByCode[key] = {
          code: seat.senatorCode, party: seat.senatorParty,
          axis: seat.senatorAxis, direction: seat.senatorDir,
          urban: 0, suburban: 0, rural: 0, national: 0, pctNational: 0,
        };
      }
      countByCode[key].national += 1;
    }
    return Object.values(countByCode);
  }, [condRM, irvRM, method]);

  const constellationNodes: ConstellationNode[] = Object.entries(seatCounts)
    .map(([code, seats]) => ({
      id: code, label: code, seats,
      F1: getFactorScore(code, 'F1'), F2: getFactorScore(code, 'F2'),
      F3: getFactorScore(code, 'F3'), F4: getFactorScore(code, 'F4'),
      F5: getFactorScore(code, 'F5'),
    }));

  const isFD = pipeline === 'factorDev';

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-1">Senate</h2>
        <p className="text-muted-foreground text-sm">
          Each state elects one senator via either Condorcet or IRV. The method choice matters:
          Condorcet finds the most broadly acceptable candidate; IRV amplifies strong-base parties.
        </p>
      </div>

      <StickyControlBar label="Senate settings">
        <ToggleGroup label="Scenario" value={pipeline} onChange={setPipeline}
          options={['rawMulti', 'factorDev'] as const} labels={PIPELINE_LABELS} />
        <ToggleGroup label="Method" value={method} onChange={setMethod}
          options={['condorcet', 'irv'] as const} labels={METHOD_LABELS} />
        <ParticipationSlider value={Number(part)} onChange={v => setPart(String(v))} />
      </StickyControlBar>

      {/* FPTP vs Preferential Senate Comparison (shared with Overview) */}
      <SenateCompositionCard condSeats={condRM} irvSeats={irvRM} />

      {/* Parliament fan chart */}
      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <span className="text-xs text-muted-foreground uppercase tracking-widest">Order by</span>
          {DISPLAY_FACTORS.map(f => (
            <Button key={f} onClick={() => setParliamentFactor(f)} title={FACTOR_LABELS[f]}
              variant={parliamentFactor === f ? 'default' : 'secondary'}
              size="sm">
              {f} · {FACTOR_LABELS[f]}
            </Button>
          ))}
        </div>
        <ParliamentChart segments={parliamentSegments} factor={parliamentFactor} globalRange={globalRange} />
      </Card>

      {/* FD: Variant bar below fan chart */}
      {isFD && fdVariantSeats.length > 0 && (
        <Card className="p-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
            Senate Seats by Variant
          </h3>
          <p className="text-xs text-muted-foreground mb-3">
            Full color = base; lighter = hi axis deviation; darker = lo axis deviation.
          </p>
          <PartyVariantBar seats={fdVariantSeats} totalLabel="51 senate seats" />
        </Card>
      )}

      <Card className="p-4">
        <SenateMap seats={activeSeats} />
      </Card>

      {/* Senate Coalition Composition — how winners fill their quota */}
      {pipeline === 'rawMulti' && senateBuckets && (
        <Card className="p-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
            How Senators Build Their Coalition
          </h3>
          <p className="text-xs text-muted-foreground mb-3">
            Each bar shows where a senator&apos;s votes came from during IRV winnowing.
            Darkest = own first-choice supporters. Other colors = transfers from eliminated parties.
            Select a state to see the full finalist breakdown.
          </p>
          <SenateBuckets data={senateBuckets} method={method} />
        </Card>
      )}

      {/* Senate Condorcet Matrix */}
      {pipeline === 'rawMulti' && senateCondorcet && (
        <Card className="p-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
            Head-to-Head Matrix (Condorcet)
          </h3>
          <p className="text-xs text-muted-foreground mb-3">
            National average shows how often each party beats every other in head-to-head matchups across all 51 state races.
            Select a state to see actual margins for that race&apos;s 5 finalists.
          </p>
          <SenateCondorcetView data={senateCondorcet} />
        </Card>
      )}

      {/* Ideological Constellation */}
      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-3">
          Ideological Constellation
        </h3>
        <IdeologicalConstellation nodes={constellationNodes} clusterSpreads={clusterSpreads} />
      </Card>

      {/* Nine-Party Profiles */}
      <PartyProfileGrid clusters={orderedClusters} />

      {/* Senate Vote Model */}
      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-4">
          Senate Vote Model — 37 Bills
        </h3>
        <p className="text-xs text-muted-foreground mb-4">
          Highlighted rows show bills the senate passes but the president vetoes.
        </p>
        <VoteModelTable rows={vmRows} scenario={scenario} />
      </Card>

      {/* FD Analysis section */}
      {isFD && (
        <>
          <div className="border-t-2 border-violet-200 pt-6">
            <h3 className="text-lg font-bold text-violet-800 mb-1">Crossover Analysis — Senate</h3>
            <p className="text-xs text-muted-foreground mb-6">
              How do ideological deviations affect senate composition under {method === 'condorcet' ? 'Condorcet' : 'IRV'}?
            </p>
          </div>

          <Card className="p-4">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
              Variant Impact by Party
            </h3>
            <p className="text-xs text-muted-foreground mb-4">
              Which ideological deviations win senate seats?
            </p>
            <VariantImpactChart seats={fdVariantSeats} />
          </Card>

          {fdVariantAttraction.length > 0 && (
            <Card className="p-4">
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
                Variant Voter Attraction Sources
              </h3>
              <p className="text-xs text-muted-foreground mb-4">
                Incremental cross-party attraction for each deviation relative to the party base.
              </p>
              <VariantAttractionChart data={fdVariantAttraction} />
            </Card>
          )}

          {fdAttractionDrivers.length > 0 && (
            <Card className="p-4">
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
                Cross-Party Attraction Drivers
              </h3>
              <p className="text-xs text-muted-foreground mb-3">
                Which factors explain each variant&apos;s cross-party pull?
              </p>
              <AttractionDriverChart data={fdAttractionDrivers} />
            </Card>
          )}
        </>
      )}
    </div>
  );
}

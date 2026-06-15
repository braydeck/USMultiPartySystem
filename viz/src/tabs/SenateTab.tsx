import { useState, useMemo } from 'react';
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
import { PARTY_COLORS, FACTOR_LABELS, F5_ORDER } from '../constants/parties';
import { PIPELINE_LABELS, METHOD_LABELS } from '../constants/labels';
import { ToggleGroup } from '../components/shared/ToggleGroup';
import { StickyControlBar } from '../components/shared/StickyControlBar';
import SenateBuckets from '../components/senate/SenateBuckets';
import SenateCondorcetView from '../components/senate/SenateCondorcetView';
import { VariantImpactChart } from '../components/house/VariantImpactChart';
import { VariantAttractionChart } from '../components/house/VariantAttractionChart';
import { AttractionDriverChart } from '../components/house/AttractionDriverChart';

interface Props {
  condorcetFD:       FDSenateSeat[];
  irvFD:             FDSenateSeat[];
  condorcetRawMulti: FDSenateSeat[];
  irvRawMulti:       FDSenateSeat[];
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

function SenateCompBar({ label, seats, segments, total: totalOverride }: {
  label: string;
  seats?: FDSenateSeat[];
  segments?: { party: string; n: number; color: string }[];
  total?: number;
}) {
  const segs = segments ?? (() => {
    const counts: Record<string, number> = {};
    for (const s of seats ?? []) {
      const p = s.senatorParty ?? s.senatorCode.split('_')[0];
      counts[p] = (counts[p] ?? 0) + 1;
    }
    return F5_ORDER.filter(p => counts[p] > 0).map(p => ({
      party: p, n: counts[p], color: PARTY_COLORS[p] ?? '#6b7280',
    }));
  })();
  const total = totalOverride ?? segs.reduce((s, x) => s + x.n, 0);

  return (
    <div className="flex items-center gap-3">
      <div className="shrink-0 text-right" style={{ width: 110 }}>
        <div className="text-xs font-semibold text-foreground">{label}</div>
        <div className="text-xs text-muted-foreground">{total} seats</div>
      </div>
      <div className="flex-1 flex rounded-lg overflow-hidden h-10">
        {segs.map(({ party, n, color }) => {
          const pct = (n / total) * 100;
          return (
            <div key={party} className="flex items-center justify-center"
              style={{ width: `${pct}%`, backgroundColor: color }}>
              {pct >= 6 && (
                <span className="text-white text-[10px] font-bold">{party} {n}</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function SenateTab({ condorcetFD, irvFD, condorcetRawMulti, irvRawMulti,
                             voteModel, clusters, fdProfiles, clusterSpreads,
                             fdVariantAttraction, fdAttractionDrivers,
                             senateBuckets, senateCondorcet }: Props) {
  const [pipeline, setPipeline] = useState<'factorDev' | 'rawMulti'>('rawMulti');
  const [method, setMethod] = useState<'condorcet' | 'irv'>('condorcet');
  const [parliamentFactor, setParliamentFactor] = useState('F5');

  const scenario: SenateScenario =
    pipeline === 'factorDev'
      ? (method === 'condorcet' ? 'condFD' : 'irvFD')
      : (method === 'condorcet' ? 'condRawMulti' : 'irvRawMulti');

  const SEAT_MAP: Record<SenateScenario, SenateSeat[]> = {
    condFD:       condorcetFD        as unknown as SenateSeat[],
    irvFD:        irvFD              as unknown as SenateSeat[],
    condRawMulti: condorcetRawMulti  as unknown as SenateSeat[],
    irvRawMulti:  irvRawMulti        as unknown as SenateSeat[],
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
  const orderedClusters = useMemo(() => F5_ORDER.map(p => clusterByParty[p]).filter(Boolean) as ClusterProfile[], [clusterByParty]);

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
    const fdSeats =
      scenario === 'condFD' ? condorcetFD :
      scenario === 'irvFD' ? irvFD :
      scenario === 'condRawMulti' ? condorcetRawMulti :
      irvRawMulti;
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
  }, [condorcetFD, irvFD, condorcetRawMulti, irvRawMulti, scenario]);

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

      <StickyControlBar>
        <ToggleGroup label="Scenario" value={pipeline} onChange={setPipeline}
          options={['rawMulti', 'factorDev'] as const} labels={PIPELINE_LABELS} />
        <ToggleGroup label="Method" value={method} onChange={setMethod}
          options={['condorcet', 'irv'] as const} labels={METHOD_LABELS} />
      </StickyControlBar>

      {/* FPTP vs STV Senate Comparison */}
      <Card className="p-5 border-2 border-indigo-200 space-y-3">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
          FPTP Today vs STV Senate
        </h3>
        {/* FPTP Today */}
        <SenateCompBar label="FPTP Today" segments={[
          { party: 'DEM', n: 47, color: '#1d4ed8' },
          { party: 'GOP', n: 53, color: '#dc2626' },
        ]} total={100} />
        {/* RM Condorcet */}
        <SenateCompBar label="RM Condorcet" seats={condorcetRawMulti} />
        {/* RM IRV */}
        <SenateCompBar label="RM IRV" seats={irvRawMulti} />
        {/* FD bars */}
        {isFD && <>
          <SenateCompBar label="FD Condorcet" seats={condorcetFD} />
          <SenateCompBar label="FD IRV" seats={irvFD} />
        </>}
      </Card>

      {/* Parliament fan chart */}
      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <span className="text-xs text-muted-foreground uppercase tracking-widest">Order by</span>
          {(['F1','F2','F3','F4','F5'] as const).map(f => (
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
        <VoteModelTable rows={voteModel} scenario={scenario} />
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

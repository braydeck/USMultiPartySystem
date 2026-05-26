import { useState, useMemo } from 'react';
import type { SenateSeat, VoteModelRow, SenateScenario, ClusterProfile, ConstellationNode, FDSenateSeat, FDHouseSeat, FDCandidateProfile } from '../types';
import { SenateMap } from '../components/senate/SenateMap';
import { VoteModelTable } from '../components/senate/VoteModelTable';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { ParliamentChart } from '../components/shared/ParliamentChart';
import { PartyVariantBar } from '../components/shared/PartyVariantBar';
import { PartyProfileGrid } from '../components/shared/PartyProfileGrid';
import type { ParliamentSegment } from '../components/shared/ParliamentChart';
import { PARTY_COLORS, FACTOR_LABELS, PARTY_NAMES, F5_ORDER, getBlendColor } from '../constants/parties';
import { TransferFlowChart } from '../components/house/TransferFlowChart';
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
}

export function SenateTab({ condorcetFD, irvFD, condorcetRawMulti, irvRawMulti,
                             voteModel, clusters, fdProfiles, clusterSpreads,
                             houseTransfers, fdVariantAttraction, fdAttractionDrivers }: Props) {
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

  // Seat comparison: party-level counts for Condorcet vs IRV (+ FD in FD mode)
  const countByParty = (seats: FDSenateSeat[]) => {
    const counts: Record<string, number> = {};
    for (const s of seats) {
      const party = s.senatorParty ?? s.senatorCode.split('_')[0];
      counts[party] = (counts[party] ?? 0) + 1;
    }
    return counts;
  };
  const rmCondCounts = countByParty(condorcetRawMulti);
  const rmIrvCounts  = countByParty(irvRawMulti);
  const fdCondCounts = countByParty(condorcetFD);
  const fdIrvCounts  = countByParty(irvFD);

  const comparisonParties = Array.from(new Set([
    ...Object.keys(rmCondCounts), ...Object.keys(rmIrvCounts),
    ...Object.keys(fdCondCounts), ...Object.keys(fdIrvCounts),
  ])).sort((a, b) => {
    const ai = F5_ORDER.indexOf(a as typeof F5_ORDER[number]);
    const bi = F5_ORDER.indexOf(b as typeof F5_ORDER[number]);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });

  const isFD = pipeline === 'factorDev';
  const condCounts = isFD ? fdCondCounts : rmCondCounts;
  const irvCounts  = isFD ? fdIrvCounts  : rmIrvCounts;

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 mb-1">Senate</h2>
        <p className="text-slate-500 text-sm">
          Each state elects one senator via either Condorcet or IRV. The method choice matters:
          Condorcet finds the most broadly acceptable candidate; IRV amplifies strong-base parties.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex flex-col gap-1">
          <span className="text-xs text-slate-400 uppercase tracking-widest">Scenario</span>
          <div className="flex gap-1">
            {(['rawMulti', 'factorDev'] as const).map(p => (
              <button key={p} onClick={() => setPipeline(p)}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  pipeline === p ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                }`}>
                {p === 'factorDev' ? 'Factor Dev' : 'Raw Multi'}
              </button>
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs text-slate-400 uppercase tracking-widest">Method</span>
          <div className="flex gap-1">
            {(['condorcet', 'irv'] as const).map(m => (
              <button key={m} onClick={() => setMethod(m)}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  method === m ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                }`}>
                {m === 'condorcet' ? 'Condorcet' : 'IRV'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Seat Comparison: Condorcet vs IRV (+ FD in FD mode) */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
          Senate Seat Comparison
        </h3>
        <p className="text-xs text-slate-500 mb-4">
          How does the election method change party representation?
          {isFD && ' Solid = Factor Dev, outlined = Raw Multi for comparison.'}
        </p>
        <div className="space-y-2">
          {comparisonParties.map(party => {
            const cond = condCounts[party] ?? 0;
            const irv  = irvCounts[party] ?? 0;
            const rmCond = rmCondCounts[party] ?? 0;
            const rmIrv  = rmIrvCounts[party] ?? 0;
            const color = PARTY_COLORS[party] ?? '#6b7280';
            const maxSeats = 51;
            if (cond === 0 && irv === 0 && (!isFD || (rmCond === 0 && rmIrv === 0))) return null;

            return (
              <div key={party} className="grid grid-cols-[56px_1fr] gap-2 items-center">
                <span className="text-xs font-bold font-mono text-right" style={{ color }}>{party}</span>
                <div className="space-y-0.5">
                  {/* Condorcet */}
                  <div className="flex items-center gap-2">
                    <div className="h-4 rounded-sm" style={{ width: `${(cond / maxSeats) * 100}%`, minWidth: cond > 0 ? 2 : 0, backgroundColor: color, opacity: 0.75 }} />
                    <span className="text-[10px] text-slate-600">Cond: <b>{cond}</b></span>
                    {isFD && rmCond > 0 && rmCond !== cond && (
                      <span className="text-[10px] text-slate-400">(RM: {rmCond})</span>
                    )}
                  </div>
                  {/* IRV */}
                  <div className="flex items-center gap-2">
                    <div className="h-4 rounded-sm border-2" style={{
                      width: `${(irv / maxSeats) * 100}%`, minWidth: irv > 0 ? 2 : 0,
                      borderColor: color, backgroundColor: color + '33',
                    }} />
                    <span className="text-[10px] text-slate-600">IRV: <b>{irv}</b></span>
                    {isFD && rmIrv > 0 && rmIrv !== irv && (
                      <span className="text-[10px] text-slate-400">(RM: {rmIrv})</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Parliament fan chart */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <span className="text-xs text-slate-600 uppercase tracking-widest">Order by</span>
          {(['F1','F2','F3','F4','F5'] as const).map(f => (
            <button key={f} onClick={() => setParliamentFactor(f)} title={FACTOR_LABELS[f]}
              className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                parliamentFactor === f ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
              }`}>
              {f} · {FACTOR_LABELS[f]}
            </button>
          ))}
        </div>
        <ParliamentChart segments={parliamentSegments} factor={parliamentFactor} globalRange={globalRange} />
      </div>

      {/* FD: Variant bar below fan chart */}
      {isFD && fdVariantSeats.length > 0 && (
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
            Senate Seats by Variant
          </h3>
          <p className="text-xs text-slate-500 mb-3">
            Full color = base; lighter = hi axis deviation; darker = lo axis deviation.
          </p>
          <PartyVariantBar seats={fdVariantSeats} totalLabel="51 senate seats" />
        </div>
      )}

      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <SenateMap seats={activeSeats} />
      </div>

      {/* Nine-Party Profiles */}
      <PartyProfileGrid clusters={orderedClusters} />

      {/* Ideological Constellation */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3">
          Ideological Constellation
        </h3>
        <IdeologicalConstellation nodes={constellationNodes} clusterSpreads={clusterSpreads} />
      </div>

      {/* Vote Transfer Destinations */}
      {houseTransfers.length > 0 && (
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
            Vote Transfer Destinations
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            When a party is eliminated in STV/IRV, where do their voters&apos; ballots flow?
          </p>
          <TransferFlowChart data={houseTransfers} />
        </div>
      )}

      {/* Senate Vote Model */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-4">
          Senate Vote Model — 37 Bills
        </h3>
        <p className="text-xs text-slate-500 mb-4">
          Highlighted rows show bills the senate passes but the president vetoes.
        </p>
        <VoteModelTable rows={voteModel} scenario={scenario} />
      </div>

      {/* FD Analysis section */}
      {isFD && (
        <>
          <div className="border-t-2 border-violet-200 pt-6">
            <h3 className="text-lg font-bold text-violet-800 mb-1">Factor Deviation Analysis — Senate</h3>
            <p className="text-xs text-slate-500 mb-6">
              How do ideological deviations affect senate composition under {method === 'condorcet' ? 'Condorcet' : 'IRV'}?
            </p>
          </div>

          <div className="bg-white rounded-xl p-4 border border-slate-200">
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
              Variant Impact by Party
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Which ideological deviations win senate seats?
            </p>
            <VariantImpactChart seats={fdVariantSeats} />
          </div>

          {fdVariantAttraction.length > 0 && (
            <div className="bg-white rounded-xl p-4 border border-slate-200">
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
                Variant Voter Attraction Sources
              </h3>
              <p className="text-xs text-slate-500 mb-4">
                Incremental cross-party attraction for each deviation relative to the party base.
              </p>
              <VariantAttractionChart data={fdVariantAttraction} />
            </div>
          )}

          {fdAttractionDrivers.length > 0 && (
            <div className="bg-white rounded-xl p-4 border border-slate-200">
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
                Cross-Party Attraction Drivers
              </h3>
              <p className="text-xs text-slate-500 mb-3">
                Which factors explain each variant&apos;s cross-party pull?
              </p>
              <AttractionDriverChart data={fdAttractionDrivers} />
            </div>
          )}
        </>
      )}
    </div>
  );
}

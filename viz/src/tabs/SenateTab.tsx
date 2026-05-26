import { useState, useMemo } from 'react';
import type { SenateSeat, VoteModelRow, SenateScenario, ClusterProfile, ConstellationNode, FDSenateSeat, FDHouseSeat, FDCandidateProfile } from '../types';
import { SenateMap } from '../components/senate/SenateMap';
import { VoteModelTable } from '../components/senate/VoteModelTable';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { ParliamentChart } from '../components/shared/ParliamentChart';
import { PartyVariantBar } from '../components/shared/PartyVariantBar';
import { PartyProfileCard } from '../components/shared/PartyProfileCard';
import type { ParliamentSegment } from '../components/shared/ParliamentChart';
import { FACTOR_LABELS, PARTY_NAMES, F5_ORDER, getBlendColor } from '../constants/parties';

interface Props {
  condorcetFD:       FDSenateSeat[];
  irvFD:             FDSenateSeat[];
  condorcetRawMulti: FDSenateSeat[];
  irvRawMulti:       FDSenateSeat[];
  voteModel:         VoteModelRow[];
  clusters:          ClusterProfile[];
  fdProfiles:        Record<string, FDCandidateProfile>;
  clusterSpreads:    { party: string; n: number; [key: string]: string | number }[];
}

export function SenateTab({ condorcetFD, irvFD,
                             condorcetRawMulti, irvRawMulti,
                             voteModel, clusters, fdProfiles, clusterSpreads }: Props) {
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

  // Derive mini card data
  const seatCounts: Record<string, number> = {};
  for (const s of activeSeats) {
    seatCounts[s.senatorCode] = (seatCounts[s.senatorCode] ?? 0) + 1;
  }
  const miniCardCodes = Object.entries(seatCounts)
    .sort((a, b) => b[1] - a[1])
    .map(([code]) => code);

  // Factor score lookup: FD codes from fdProfiles, party codes from clusters,
  // raw multi codes (e.g. "CTR_1") by stripping the _N suffix to get base party.
  const clusterByParty = useMemo(
    () => Object.fromEntries(clusters.map(c => [c.party, c])),
    [clusters]
  );
  const orderedClusters = useMemo(() => F5_ORDER.map(p => clusterByParty[p]).filter(Boolean) as ClusterProfile[], [clusterByParty]);
  function getFactorScore(code: string, factor: string): number {
    // Return z-score (SDs from population mean, 0 = average voter) for constellation
    const zKey = `z_${factor}`;
    const cl = clusterByParty[code];
    if (cl) { const z = (cl as any)[zKey]; if (z != null) return z; }
    const base = code.split('_')[0];
    const baseCl = clusterByParty[base];
    if (baseCl) { const z = (baseCl as any)[zKey]; if (z != null) return z; }
    // Fallback to raw for FD variants (no percentile available)
    const fd = fdProfiles[code];
    if (fd) return (fd as unknown as Record<string, number>)[factor] ?? 50;
    return 50;
  }

  // Global factor range — union of all clusters + all fdProfiles for stable absolute ordering
  const globalRange = useMemo((): [number, number] => {
    const vals = [
      ...clusters.map(c => (c as unknown as Record<string, number>)[parliamentFactor] ?? 0),
      ...Object.values(fdProfiles).map(p => (p as unknown as Record<string, number>)[parliamentFactor] ?? 0),
    ];
    return vals.length > 0 ? [Math.min(...vals), Math.max(...vals)] : [-2, 2];
  }, [clusters, fdProfiles, parliamentFactor]);

  // Parliament chart segments — absolute factor scores; tiny epsilon offset for _N
  // variants ensures same-party multi-candidates occupy distinct arc positions.
  const parliamentSegments: ParliamentSegment[] = Object.entries(seatCounts)
    .map(([code, seats]) => {
      const base = getFactorScore(code, parliamentFactor);
      const nSuffix = parseInt(code.split('_').pop() ?? '') || 0;
      return { code, seats, fVal: base + (nSuffix > 0 ? (nSuffix - 1) * 0.001 : 0) };
    })
    .sort((a, b) => a.fVal - b.fVal);

  // Variant seat data for PartyVariantBar (FD and Raw Multi scenarios)
  const fdVariantSeats = useMemo((): FDHouseSeat[] => {
    const multiScenarios: SenateScenario[] = ['condFD', 'irvFD', 'condRawMulti', 'irvRawMulti'];
    if (!multiScenarios.includes(scenario)) return [];
    const fdSeats =
      scenario === 'condFD'       ? condorcetFD :
      scenario === 'irvFD'        ? irvFD :
      scenario === 'condRawMulti' ? condorcetRawMulti :
                                    irvRawMulti;
    const countByCode: Record<string, FDHouseSeat> = {};
    for (const seat of fdSeats) {
      const key = seat.senatorCode;
      if (!countByCode[key]) {
        countByCode[key] = {
          code: seat.senatorCode,
          party: seat.senatorParty,
          axis: seat.senatorAxis,
          direction: seat.senatorDir,
          urban: 0, suburban: 0, rural: 0,
          national: 0, pctNational: 0,
        };
      }
      countByCode[key].national += 1;
    }
    return Object.values(countByCode);
  }, [condorcetFD, irvFD, condorcetRawMulti, irvRawMulti, scenario]);

  const constellationNodes: ConstellationNode[] = Object.entries(seatCounts)
    .map(([code, seats]) => ({
      id: code, label: code, seats,
      F1: getFactorScore(code, 'F1'),
      F2: getFactorScore(code, 'F2'),
      F3: getFactorScore(code, 'F3'),
      F4: getFactorScore(code, 'F4'),
      F5: getFactorScore(code, 'F5'),
    }));

  // Method sensitivity: seat counts by party for each method
  const condSeats = pipeline === 'factorDev' ? condorcetFD : condorcetRawMulti;
  const irvSeats  = pipeline === 'factorDev' ? irvFD       : irvRawMulti;

  const countByParty = (seats: FDSenateSeat[]) => {
    const counts: Record<string, number> = {};
    for (const s of seats) {
      const party = s.senatorParty ?? s.senatorCode.split('_')[0];
      counts[party] = (counts[party] ?? 0) + 1;
    }
    return counts;
  };
  const condCounts = countByParty(condSeats);
  const irvCounts  = countByParty(irvSeats);
  const allParties = Array.from(new Set([...Object.keys(condCounts), ...Object.keys(irvCounts)]))
    .sort((a, b) => (condCounts[b] ?? 0) - (condCounts[a] ?? 0));

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
              <button
                key={p}
                onClick={() => setPipeline(p)}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  pipeline === p
                    ? 'bg-indigo-600 text-white'
                    : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                }`}
              >
                {p === 'factorDev' ? 'Factor Dev' : 'Raw Multi'}
              </button>
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-xs text-slate-400 uppercase tracking-widest">Method</span>
          <div className="flex gap-1">
            {(['condorcet', 'irv'] as const).map(m => (
              <button
                key={m}
                onClick={() => setMethod(m)}
                className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                  method === m
                    ? 'bg-indigo-600 text-white'
                    : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                }`}
              >
                {m === 'condorcet' ? 'Condorcet' : 'IRV'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Method sensitivity table */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
          Method Sensitivity
        </h3>
        <p className="text-xs text-slate-500 mb-3">
          Condorcet picks broadly acceptable senators; IRV amplifies strong-base parties.
          Green Δ = party gains seats under Condorcet (preferred method).
        </p>
        <div className="overflow-x-auto">
          <table className="text-sm w-full">
            <thead>
              <tr className="text-xs text-slate-400 uppercase tracking-widest border-b border-slate-100">
                <th className="text-left pb-2 pr-4 font-medium">Party</th>
                <th className="text-right pb-2 px-4 font-medium">Condorcet</th>
                <th className="text-right pb-2 px-4 font-medium">IRV</th>
                <th className="text-right pb-2 pl-4 font-medium">Δ</th>
              </tr>
            </thead>
            <tbody>
              {allParties.map(party => {
                const cond = condCounts[party] ?? 0;
                const irv  = irvCounts[party] ?? 0;
                const delta = cond - irv;
                const color = getBlendColor(party);
                return (
                  <tr key={party} className="border-b border-slate-50">
                    <td className="py-1.5 pr-4">
                      <span className="font-bold font-mono text-xs" style={{ color }}>{party}</span>
                      <span className="ml-2 text-xs text-slate-500">{PARTY_NAMES[party] ?? ''}</span>
                    </td>
                    <td className="text-right px-4 font-mono font-semibold" style={{ color }}>{cond}</td>
                    <td className="text-right px-4 font-mono text-slate-600">{irv}</td>
                    <td className="text-right pl-4 font-mono font-bold" style={{
                      color: delta > 0 ? '#15803d' : delta < 0 ? '#b91c1c' : '#94a3b8'
                    }}>
                      {delta > 0 ? `+${delta}` : delta === 0 ? '—' : delta}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Parliament fan chart replaces SeatSummary */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <span className="text-xs text-slate-600 uppercase tracking-widest">Order by</span>
          {(['F1','F2','F3','F4','F5'] as const).map(f => (
            <button
              key={f}
              onClick={() => setParliamentFactor(f)}
              title={FACTOR_LABELS[f]}
              className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                parliamentFactor === f
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
              }`}
            >
              {f} · {FACTOR_LABELS[f]}
            </button>
          ))}
        </div>
        <ParliamentChart
          segments={parliamentSegments}
          factor={parliamentFactor}
          globalRange={globalRange}
        />
      </div>

      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <SenateMap seats={activeSeats} />
      </div>

      {/* Nine-party profiles below map */}
      <div>
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">Nine-Party Profiles</h3>
        <p className="text-xs text-slate-500 mb-4">
          Ordered left→right by Ideology (F5). Intensity labels show how far each party deviates from the average American voter.
        </p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {orderedClusters.map(cluster => (
            <PartyProfileCard key={cluster.party} cluster={cluster} />
          ))}
        </div>
      </div>

      {/* Factor Dev variant bar — visible for FD scenarios */}
      {fdVariantSeats.length > 0 && (
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
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3">
          Ideological Constellation
        </h3>
        <IdeologicalConstellation nodes={constellationNodes} clusterSpreads={clusterSpreads} />
      </div>

      <div className="bg-white rounded-xl p-4 border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-4">
            Senate Vote Model — 37 Bills
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            Highlighted rows show bills the senate passes but the president vetoes.
          </p>
          <VoteModelTable rows={voteModel} scenario={scenario} />
      </div>
    </div>
  );
}

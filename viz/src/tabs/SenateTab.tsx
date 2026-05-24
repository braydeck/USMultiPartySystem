import { useState, useMemo } from 'react';
import type { SenateSeat, VoteModelRow, SenateScenario, ClusterProfile, ConstellationNode, FDSenateSeat, FDHouseSeat, FDCandidateProfile } from '../types';
import { SenateMap } from '../components/senate/SenateMap';
import { VoteModelTable } from '../components/senate/VoteModelTable';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { MiniPartyCard } from '../components/shared/MiniPartyCard';
import { ParliamentChart } from '../components/shared/ParliamentChart';
import { PartyVariantBar } from '../components/shared/PartyVariantBar';
import type { ParliamentSegment } from '../components/shared/ParliamentChart';
import { FACTOR_LABELS } from '../constants/parties';

interface Props {
  condorcetFD:       FDSenateSeat[];
  irvFD:             FDSenateSeat[];
  condorcetRawMulti: FDSenateSeat[];
  irvRawMulti:       FDSenateSeat[];
  voteModel:         VoteModelRow[];
  clusters:          ClusterProfile[];
  fdProfiles:        Record<string, FDCandidateProfile>;
}

export function SenateTab({ condorcetFD, irvFD,
                             condorcetRawMulti, irvRawMulti,
                             voteModel, clusters, fdProfiles }: Props) {
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
  function getFactorScore(code: string, factor: string): number {
    const fd = fdProfiles[code];
    if (fd) return (fd as unknown as Record<string, number>)[factor] ?? 0;
    const cl = clusterByParty[code];
    if (cl) return (cl as unknown as Record<string, number>)[factor] ?? 0;
    // Raw multi codes: "CTR_1" → base party "CTR"
    const base = code.split('_')[0];
    const baseCl = clusterByParty[base];
    if (baseCl) return (baseCl as unknown as Record<string, number>)[factor] ?? 0;
    return 0;
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

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 mb-1">Senate</h2>
        <p className="text-slate-500 text-sm">
          State-level senate simulation. Factor Dev uses 71 axis-deviation candidates;
          Raw Multi uses 27 intra-party candidates. Condorcet selects the head-to-head
          winner; IRV uses instant runoff elimination.
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

      {/* Mini party cards below map */}
      <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-5 gap-2">
        {miniCardCodes.map(code => {
          const fdKP = fdProfiles[code]?.keyPositions?.slice(0, 2);
          const baseCode = code.split('_')[0];
          const clusterKP = (clusterByParty[code] ?? clusterByParty[baseCode])?.keyPositions?.slice(0, 2);
          const positions = fdKP
            ? fdKP.map(p => ({ question: p.question, pct: p.value, direction: (p.diff > 0 ? 'supports' : 'opposes') as 'supports' | 'opposes', diffPp: p.diff }))
            : clusterKP;
          return (
            <MiniPartyCard
              key={code}
              code={code}
              seats={seatCounts[code]}
              positions={positions}
            />
          );
        })}
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

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3">
            Ideological Constellation
          </h3>
          <IdeologicalConstellation nodes={constellationNodes} />
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
    </div>
  );
}

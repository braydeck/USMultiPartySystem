import { useState, useMemo } from 'react';
import type { SenateSeat, VoteModelRow, SenateScenario, BlendProfile, ConstellationNode } from '../types';
import { SenateMap } from '../components/senate/SenateMap';
import { VoteModelTable } from '../components/senate/VoteModelTable';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { MiniPartyCard } from '../components/shared/MiniPartyCard';
import { ParliamentChart } from '../components/shared/ParliamentChart';
import type { ParliamentSegment } from '../components/shared/ParliamentChart';
import { FACTOR_LABELS } from '../constants/parties';

interface Props {
  condorcetMixed:     SenateSeat[];
  irvMixed:           SenateSeat[];
  condorcetPure:      SenateSeat[];
  irvPure:            SenateSeat[];
  condorcetLightFusion: SenateSeat[];
  irvLightFusion:     SenateSeat[];
  voteModel:          VoteModelRow[];
  blendProfiles:      BlendProfile[];
}

const SCENARIO_GROUPS = [
  { label: 'Blended',      scenarios: ['condMixed', 'irvMixed']  as SenateScenario[] },
  { label: 'Raw',          scenarios: ['condPure',  'irvPure']   as SenateScenario[] },
  { label: 'Light Fusion', scenarios: ['condLF',    'irvLF']     as SenateScenario[] },
];

export function SenateTab({ condorcetMixed, irvMixed, condorcetPure, irvPure,
                             condorcetLightFusion, irvLightFusion,
                             voteModel, blendProfiles }: Props) {
  const [scenario, setScenario] = useState<SenateScenario>('condMixed');
  const [parliamentFactor, setParliamentFactor] = useState('F5');

  const SEAT_MAP: Record<SenateScenario, SenateSeat[]> = {
    condMixed: condorcetMixed,
    irvMixed,
    condPure:  condorcetPure,
    irvPure,
    condLF:    condorcetLightFusion,
    irvLF:     irvLightFusion,
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

  // Global factor range across all blend profiles — stable category labels regardless of scenario
  const globalRange = useMemo((): [number, number] => {
    const vals = blendProfiles.map(p => (p as unknown as Record<string, number>)[parliamentFactor] ?? 0);
    return [Math.min(...vals), Math.max(...vals)];
  }, [blendProfiles, parliamentFactor]);

  // Derive parliament chart segments
  const blendByCode = Object.fromEntries(blendProfiles.map(p => [p.code, p]));
  const parliamentSegments: ParliamentSegment[] = Object.entries(seatCounts)
    .map(([code, seats]) => {
      const bp = blendByCode[code];
      const fVal = (bp as unknown as Record<string, number>)?.[parliamentFactor] ?? 0;
      return { code, seats, fVal };
    })
    .sort((a, b) => a.fVal - b.fVal);
  const constellationNodes: ConstellationNode[] = Object.entries(seatCounts)
    .map(([code, seats]) => {
      const bp = blendByCode[code];
      return {
        id: code, label: code, seats,
        F1: bp?.F1 ?? 0, F2: bp?.F2 ?? 0, F3: bp?.F3 ?? 0,
        F4: bp?.F4 ?? 0, F5: bp?.F5 ?? 0,
      };
    });

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 mb-1">Senate</h2>
        <p className="text-slate-500 text-sm">
          State-level senate simulation. Blended scenarios include coalition candidates;
          raw scenarios use only the 9 core party types. Condorcet selects the head-to-head
          winner; IRV uses instant runoff elimination.
        </p>
      </div>

      <div className="flex flex-wrap gap-4">
        {SCENARIO_GROUPS.map(group => (
          <div key={group.label} className="flex flex-col gap-1">
            <span className="text-xs text-slate-400 uppercase tracking-widest">{group.label}</span>
            <div className="flex gap-1">
              {group.scenarios.map(s => (
                <button
                  key={s}
                  onClick={() => setScenario(s)}
                  className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                    scenario === s
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
                  }`}
                >
                  {s.startsWith('cond') ? 'Condorcet' : 'IRV'}
                </button>
              ))}
            </div>
          </div>
        ))}
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
        {miniCardCodes.map(code => (
          <MiniPartyCard
            key={code}
            code={code}
            seats={seatCounts[code]}
            positions={blendByCode[code]?.keyPositions?.slice(0, 2)}
          />
        ))}
      </div>

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

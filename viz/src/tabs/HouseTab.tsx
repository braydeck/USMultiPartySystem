import { useState } from 'react';
import type { HouseSeat, CoalitionProfile, TransferMatrix, VoteModelRow, HouseStateEntry, ClusterProfile } from '../types';
import { SeatDistributionBar } from '../components/house/SeatDistributionBar';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { BillSimulator } from '../components/house/BillSimulator';
import { HouseMap } from '../components/house/HouseMap';
import { HouseGridChart } from '../components/house/HouseGridChart';
import { MiniPartyCard } from '../components/shared/MiniPartyCard';
import { ParliamentChart } from '../components/shared/ParliamentChart';
import type { ParliamentSegment } from '../components/shared/ParliamentChart';
import { PARTY_NAMES, CLUSTER_TO_PARTY, FACTOR_LABELS } from '../constants/parties';

interface Props {
  seats: HouseSeat[];
  coalitions: CoalitionProfile[];
  transfers: TransferMatrix;
  voteModel: VoteModelRow[];
  stateMap: Record<string, HouseStateEntry>;
  clusters: ClusterProfile[];
}

export function HouseTab({ seats, coalitions, transfers, voteModel, stateMap, clusters }: Props) {
  const clusterByParty = Object.fromEntries(clusters.map(c => [c.party, c]));
  const totalSeats = seats.reduce((s, r) => s + r.national, 0);
  const [houseView, setHouseView] = useState<'map' | 'grid'>('map');
  const [parliamentFactor, setParliamentFactor] = useState('F5');

  // Build parliament segments sorted by chosen factor
  const parliamentSegments: ParliamentSegment[] = seats
    .filter(s => s.national > 0)
    .map(s => {
      const code = CLUSTER_TO_PARTY[String(s.party)] ?? '';
      const fVal = (clusterByParty[code] as unknown as Record<string, number>)?.[parliamentFactor] ?? 0;
      return { code, seats: s.national, fVal };
    })
    .filter(s => s.code)
    .sort((a, b) => a.fVal - b.fVal);

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 mb-1">House of Representatives</h2>
        <p className="text-slate-500 text-sm">
          {totalSeats} seats allocated via STV proportional representation across 3 district types.
        </p>
      </div>

      {/* State view — map or grid */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest">
            State Composition
          </h3>
          <div className="flex gap-1">
            {(['map', 'grid'] as const).map(v => (
              <button
                key={v}
                onClick={() => setHouseView(v)}
                className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                  houseView === v
                    ? 'bg-indigo-600 text-white'
                    : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
                }`}
              >
                {v === 'map' ? 'Map' : 'Grid'}
              </button>
            ))}
          </div>
        </div>
        {houseView === 'map'  && <HouseMap stateMap={stateMap} />}
        {houseView === 'grid' && <HouseGridChart stateMap={stateMap} />}
      </div>

      {/* Parliament chart */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest">Chamber Composition</h3>
          <span className="text-xs text-slate-500">— order by:</span>
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
        />
      </div>

      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3">
          Seat Distribution by District Type
        </h3>
        <p className="text-xs text-slate-500 mb-3">
          Sorted by national seat total. Darker = urban, medium = suburban, lighter = rural.
        </p>
        <SeatDistributionBar seats={seats} />
      </div>

      {/* Mini party cards by house seat count */}
      <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-5 gap-2">
        {[...seats]
          .sort((a, b) => b.national - a.national)
          .map(s => {
            const code = CLUSTER_TO_PARTY[String(s.party)] ?? '';
            const positions = clusterByParty[code]?.keyPositions ?? [];
            return (
              <MiniPartyCard
                key={s.party}
                code={code}
                seats={s.national}
                positions={positions}
              />
            );
          })}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3">
            Ideological Constellation
          </h3>
          <IdeologicalConstellation
            nodes={coalitions
              .filter(c => c.seatsHouse > 0)
              .map(c => ({
                id: c.type, label: PARTY_NAMES[c.type] ?? c.type,
                seats: c.seatsHouse, F1: c.F1, F2: c.F2, F3: c.F3, F4: c.F4, F5: c.F5,
              }))}
            transfers={transfers}
          />
        </div>

        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3">
            Bill Simulator
          </h3>
          <p className="text-xs text-slate-500 mb-3">
            Probability of passage based on the full House seat composition.
          </p>
          <BillSimulator rows={voteModel} />
        </div>
      </div>
    </div>
  );
}

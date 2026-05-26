import { useState, useMemo } from 'react';
import type { HouseSeat, CoalitionProfile, TransferMatrix, VoteModelRow, HouseStateEntry, ClusterProfile, FDHouseSeat, FPTPState, DistrictResult } from '../types';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { BillSimulator } from '../components/house/BillSimulator';
import { HouseMap } from '../components/house/HouseMap';
import { HouseGridChart } from '../components/house/HouseGridChart';
import { ParliamentChart } from '../components/shared/ParliamentChart';
import { PartyVariantBar } from '../components/shared/PartyVariantBar';
import { PartyProfileCard } from '../components/shared/PartyProfileCard';
import { RepresentationGap } from '../components/house/RepresentationGap';
import { FPTPvsSTV } from '../components/house/FPTPvsSTV';
import { UrbSubRurChart } from '../components/house/UrbSubRurChart';
import { FPTPDisproportionality } from '../components/house/FPTPDisproportionality';
import { TransferFlowChart } from '../components/house/TransferFlowChart';
import { StateSeatsTable } from '../components/house/StateSeatsTable';
import type { ParliamentSegment } from '../components/shared/ParliamentChart';
import { PARTY_NAMES, CLUSTER_TO_PARTY, F5_ORDER, FACTOR_LABELS } from '../constants/parties';

interface Props {
  seats: HouseSeat[];
  seatsProbBased: HouseSeat[];
  coalitions: CoalitionProfile[];
  transfers: TransferMatrix;
  voteModel: VoteModelRow[];
  stateMap: Record<string, HouseStateEntry>;
  clusters: ClusterProfile[];
  fdHouseSeats: FDHouseSeat[];
  fptpStates: FPTPState[];
  countyTiers: Record<string, string>;
  districtResults: Record<string, DistrictResult[]>;
  districtCountyMap: Record<string, string[]>;
  houseTransfers: { source: string; totalVoters: number; destinations: { party: string; pct: number }[] }[];
}

export function HouseTab({ seats, seatsProbBased, coalitions, transfers, voteModel, stateMap, clusters, fdHouseSeats, fptpStates, countyTiers, districtResults, districtCountyMap, houseTransfers }: Props) {
  const clusterByParty = useMemo(() => Object.fromEntries(clusters.map(c => [c.party, c])), [clusters]);
  const orderedClusters = useMemo(() => F5_ORDER.map(p => clusterByParty[p]).filter(Boolean) as ClusterProfile[], [clusterByParty]);
  const totalSeats = seats.reduce((s, r) => s + r.national, 0);
  const [scenario, setScenario] = useState<'rawMulti' | 'factorDev'>('rawMulti');
  const [mapView, setMapView] = useState<'map' | 'grid'>('map');
  const [parliamentFactor, setParliamentFactor] = useState('F5');

  const canonicalSegments: ParliamentSegment[] = seats
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
          {totalSeats} seats allocated via STV across geographically-drawn districts sized 4–7 seats.
          The contrast with FPTP is the main story: winner-take-all produces a 2-party monopoly; STV produces proportional representation.
        </p>
      </div>

      {/* Scenario toggle */}
      <div className="flex gap-2">
        {(['rawMulti', 'factorDev'] as const).map(s => (
          <button
            key={s}
            onClick={() => setScenario(s)}
            className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
              scenario === s
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
            }`}
          >
            {s === 'rawMulti' ? 'Raw Multi' : 'Factor Dev'}
          </button>
        ))}
      </div>

      {/* Factor Dev: variant bar only */}
      {scenario === 'factorDev' && (
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
            House Seats by Variant
          </h3>
          <p className="text-xs text-slate-500 mb-3">
            873 FD seats stacked by axis variant. Full color = base; lighter = hi axis; darker = lo axis.
          </p>
          <PartyVariantBar seats={fdHouseSeats} totalLabel="873 house seats" />
        </div>
      )}

      {/* Raw Multi: hero FPTP vs STV */}
      {scenario === 'rawMulti' && (
        <div className="bg-white rounded-xl p-5 border-2 border-indigo-200">
          <FPTPvsSTV seats={seats} />
        </div>
      )}

      {/* Urban / Suburban / Rural breakdown */}
      {scenario === 'rawMulti' && (
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
            Seats by District Type
          </h3>
          <p className="text-xs text-slate-500 mb-3">
            Progressive parties dominate urban seats, conservatives dominate rural, suburbs are contested.
          </p>
          <UrbSubRurChart seats={seats} />
        </div>
      )}

      {/* Representation gap */}
      {scenario === 'rawMulti' && (
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <RepresentationGap seats={seats} />
        </div>
      )}

      {/* Transfer flows */}
      {scenario === 'rawMulti' && houseTransfers.length > 0 && (
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
            Vote Transfer Destinations
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            When a party is eliminated in STV, where do their voters&apos; ballots flow?
            This reveals the ideological neighborhoods — PRG/DSA voters flow left, NAT voters flow right.
          </p>
          <TransferFlowChart data={houseTransfers} />
        </div>
      )}

      {/* FPTP disproportionality */}
      {scenario === 'rawMulti' && fptpStates.length > 0 && (
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
            FPTP Disproportionality by State
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            How far each state&apos;s FPTP outcome diverges from proportional representation.
          </p>
          <FPTPDisproportionality states={fptpStates} stateMap={stateMap} />
        </div>
      )}

      {/* Raw Multi: map/grid sub-view */}
      {scenario === 'rawMulti' && (
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest">
              State Composition
            </h3>
            <div className="flex gap-1">
              {([['map', 'Map'], ['grid', 'Grid']] as const).map(([v, label]) => (
                <button
                  key={v}
                  onClick={() => setMapView(v)}
                  className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                    mapView === v
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          {mapView === 'map'  && <HouseMap districtResults={districtResults} districtCountyMap={districtCountyMap} />}
          {mapView === 'grid' && <HouseGridChart stateMap={stateMap} districtResults={districtResults} />}
        </div>
      )}

      {/* Parliament chart — Raw Multi only */}
      {scenario === 'rawMulti' && (
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
            segments={canonicalSegments}
            factor={parliamentFactor}
          />
        </div>
      )}

      {scenario === 'rawMulti' && (
        <>
          {/* Nine-party profiles */}
          <div>
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">Nine-Party Profiles</h3>
            <p className="text-xs text-slate-500 mb-4">
              Ordered left→right by Ideology (F5). Each party&apos;s position across four discriminating dimensions.
            </p>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {orderedClusters.map(cluster => (
                <PartyProfileCard key={cluster.party} cluster={cluster} />
              ))}
            </div>
          </div>

          <div className="bg-white rounded-xl p-4 border border-slate-200">
            <StateSeatsTable stateMap={stateMap} />
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
                Probability of passage based on the canonical House seat composition.
              </p>
              <BillSimulator rows={voteModel} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

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
import { ScenarioComparison } from '../components/house/ScenarioComparison';
import { VariantImpactChart } from '../components/house/VariantImpactChart';
import { AttractionDriverChart } from '../components/house/AttractionDriverChart';
import { VariantAttractionChart } from '../components/house/VariantAttractionChart';
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
  fdVariantAttraction: { variant: string; party: string; axis: string; direction: string; totalVoters: number; homePct: number; crossPct: number; sources: { party: string; pct: number }[] }[];
  fdCandidatePositions: { code: string; party: string; axis: string; direction: string; F1: number; F2: number; F3: number; F4: number; F5: number }[];
  clusterSpreads: { party: string; n: number; [key: string]: string | number }[];
  fdAttractionDrivers: { variant: string; party: string; axis: string; direction: string; attracted: string; attractedPct: number; factors: { factor: string; pct: number }[] }[];
}

export function HouseTab({ seats, seatsProbBased, coalitions, transfers, voteModel, stateMap, clusters, fdHouseSeats, fptpStates, countyTiers, districtResults, districtCountyMap, houseTransfers, fdVariantAttraction, fdCandidatePositions, clusterSpreads, fdAttractionDrivers }: Props) {
  const clusterByParty = useMemo(() => Object.fromEntries(clusters.map(c => [c.party, c])), [clusters]);
  const orderedClusters = useMemo(() => F5_ORDER.map(p => clusterByParty[p]).filter(Boolean) as ClusterProfile[], [clusterByParty]);
  const totalSeats = seats.reduce((s, r) => s + r.national, 0);
  const [scenario, setScenario] = useState<'rawMulti' | 'factorDev'>('rawMulti');
  const [mapView, setMapView] = useState<'map' | 'grid'>('map');
  const [parliamentFactor, setParliamentFactor] = useState('F5');

  const fdSeatsAggregated: HouseSeat[] = useMemo(() => {
    const byCluster: Record<number, { urban: number; suburban: number; rural: number; national: number }> = {};
    const CODE_TO_CLUSTER: Record<string, number> = { CON: 0, SD: 1, STY: 2, NAT: 3, LIB: 4, REF: 5, CTR: 6, DSA: 8, PRG: 9 };
    const CLUSTER_NAMES: Record<number, string> = { 0:'Conservative',1:'Social Democrat',2:'Solidarity',3:'Nationalist',4:'Liberal',5:'Reform',6:'Center',8:'DSA',9:'Progressive' };
    for (const s of fdHouseSeats) {
      const cluster = CODE_TO_CLUSTER[s.party] ?? -1;
      if (cluster < 0) continue;
      if (!byCluster[cluster]) byCluster[cluster] = { urban: 0, suburban: 0, rural: 0, national: 0 };
      byCluster[cluster].urban += s.urban;
      byCluster[cluster].suburban += s.suburban;
      byCluster[cluster].rural += s.rural;
      byCluster[cluster].national += s.national;
    }
    const fdTotal = Object.values(byCluster).reduce((s, r) => s + r.national, 0) || 1;
    return Object.entries(byCluster).map(([k, v]) => ({
      party: Number(k),
      partyName: CLUSTER_NAMES[Number(k)] ?? '',
      urban: v.urban, suburban: v.suburban, rural: v.rural,
      national: v.national,
      pctNational: v.national / fdTotal * 100,
      pctPopulation: seats.find(s => s.party === Number(k))?.pctPopulation ?? 0,
    }));
  }, [fdHouseSeats, seats]);

  const fdSeatsByCode = useMemo(() => {
    const map: Record<string, number> = {};
    for (const s of fdHouseSeats) map[s.code] = s.national;
    return map;
  }, [fdHouseSeats]);

  const activeSeats = scenario === 'rawMulti' ? seats : fdSeatsAggregated;
  const activeTotalSeats = activeSeats.reduce((s, r) => s + r.national, 0);

  const parliamentSegments: ParliamentSegment[] = activeSeats
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
        </p>
      </div>

      {/* Scenario toggle */}
      <div className="flex gap-2">
        {(['rawMulti', 'factorDev'] as const).map(s => (
          <button key={s} onClick={() => setScenario(s)}
            className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
              scenario === s ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
            }`}>
            {s === 'rawMulti' ? 'Raw Multi' : 'Factor Dev'}
          </button>
        ))}
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          SECTION 1: REPRESENTATION
          ═══════════════════════════════════════════════════════════════════════ */}

      {/* Hero: FPTP vs STV */}
      <div className="bg-white rounded-xl p-5 border-2 border-indigo-200">
        <FPTPvsSTV seats={activeSeats} />
      </div>

      {/* Population vs Seat Share */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
          Population vs Seat Share
        </h3>
        <p className="text-xs text-slate-500 mb-4">
          How close does STV get to proportional representation? Faded bar = population share, solid = seat share.
          {scenario === 'factorDev' && ' Outlined = Factor Dev seat share for comparison.'}
        </p>
        <ScenarioComparison rawMultiSeats={seats} fdSeats={fdSeatsAggregated} scenario={scenario} />
      </div>

      {/* Seats by District Type */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
          Seats by District Type
        </h3>
        <p className="text-xs text-slate-500 mb-3">
          Progressive parties dominate urban seats, conservatives dominate rural, suburbs are contested.
        </p>
        <UrbSubRurChart seats={activeSeats} />
      </div>

      {/* Representation gap detail */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <RepresentationGap seats={activeSeats} />
      </div>

      {/* FPTP disproportionality */}
      {fptpStates.length > 0 && (
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

      {/* ═══════════════════════════════════════════════════════════════════════
          SECTION 2: COMPOSITION & GEOGRAPHY
          ═══════════════════════════════════════════════════════════════════════ */}

      {/* Chamber Composition */}
      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest">Chamber Composition</h3>
          <span className="text-xs text-slate-500">— order by:</span>
          {(['F1','F2','F3','F4','F5'] as const).map(f => (
            <button key={f} onClick={() => setParliamentFactor(f)} title={FACTOR_LABELS[f]}
              className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                parliamentFactor === f ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
              }`}>
              {f} · {FACTOR_LABELS[f]}
            </button>
          ))}
        </div>
        <ParliamentChart segments={parliamentSegments} factor={parliamentFactor} />
      </div>

      {/* State Composition — Raw Multi only */}
      {scenario === 'rawMulti' && (
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest">State Composition</h3>
            <div className="flex gap-1">
              {([['map', 'Map'], ['grid', 'Grid']] as const).map(([v, label]) => (
                <button key={v} onClick={() => setMapView(v)}
                  className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                    mapView === v ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-600 hover:bg-slate-300'
                  }`}>
                  {label}
                </button>
              ))}
            </div>
          </div>
          {mapView === 'map' && <HouseMap districtResults={districtResults} districtCountyMap={districtCountyMap} />}
          {mapView === 'grid' && <HouseGridChart stateMap={stateMap} districtResults={districtResults} />}
        </div>
      )}

      {/* Vote Transfer Destinations — Raw Multi only */}
      {scenario === 'rawMulti' && houseTransfers.length > 0 && (
        <div className="bg-white rounded-xl p-4 border border-slate-200">
          <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
            Vote Transfer Destinations
          </h3>
          <p className="text-xs text-slate-500 mb-4">
            When a party is eliminated in STV, where do their voters&apos; ballots flow?
          </p>
          <TransferFlowChart data={houseTransfers} />
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════════════
          SECTION 3: IDEOLOGICAL LANDSCAPE
          ═══════════════════════════════════════════════════════════════════════ */}

      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3">
          Ideological Constellation
        </h3>
        <IdeologicalConstellation
          nodes={(() => {
            if (scenario === 'factorDev') {
              const fdNodes = fdCandidatePositions
                .filter(c => (fdSeatsByCode[c.code] ?? 0) > 0)
                .map(c => ({
                  id: c.code,
                  label: c.axis === 'base' ? c.party : c.code,
                  seats: fdSeatsByCode[c.code] ?? 1,
                  F1: c.F1, F2: c.F2, F3: c.F3, F4: c.F4, F5: c.F5,
                }));
              return fdNodes.length > 0 ? fdNodes : [];
            }
            return coalitions
              .filter(c => c.seatsHouse > 0)
              .map(c => ({
                id: c.type, label: c.type,
                seats: c.seatsHouse, F1: c.F1, F2: c.F2, F3: c.F3, F4: c.F4, F5: c.F5,
              }));
          })()}
          transfers={scenario === 'rawMulti' ? transfers : undefined}
          clusterSpreads={clusterSpreads}
        />
      </div>

      <div className="bg-white rounded-xl p-4 border border-slate-200">
        <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-3">
          Bill Simulator
        </h3>
        <p className="text-xs text-slate-500 mb-3">
          Probability of passage based on the House seat composition.
        </p>
        <BillSimulator rows={voteModel} />
      </div>

      {/* Nine-Party Profiles */}
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

      {/* ═══════════════════════════════════════════════════════════════════════
          SECTION 4: FACTOR DEV VARIANT ANALYSIS (FD only, at bottom)
          ═══════════════════════════════════════════════════════════════════════ */}

      {scenario === 'factorDev' && (
        <>
          <div className="border-t-2 border-violet-200 pt-6">
            <h3 className="text-lg font-bold text-violet-800 mb-1">Factor Deviation Analysis</h3>
            <p className="text-xs text-slate-500 mb-6">
              How do ideological deviations from party baselines affect seat composition and cross-party attraction?
            </p>
          </div>

          {/* Variant bar */}
          <div className="bg-white rounded-xl p-4 border border-slate-200">
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
              Seats by Variant
            </h3>
            <p className="text-xs text-slate-500 mb-3">
              {activeTotalSeats} seats stacked by axis variant. Full color = base; lighter = hi axis; darker = lo axis.
            </p>
            <PartyVariantBar seats={fdHouseSeats} totalLabel={`${activeTotalSeats} house seats`} />
          </div>

          {/* Variant Impact */}
          <div className="bg-white rounded-xl p-4 border border-slate-200">
            <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
              Variant Impact by Party
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Which ideological deviations win seats? Stacked bars show base vs axis variant contributions.
            </p>
            <VariantImpactChart seats={fdHouseSeats} />
          </div>

          {/* Variant Voter Attraction Sources */}
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

          {/* Cross-Party Attraction Drivers */}
          {fdAttractionDrivers.length > 0 && (
            <div className="bg-white rounded-xl p-4 border border-slate-200">
              <h3 className="text-sm font-semibold text-slate-500 uppercase tracking-widest mb-1">
                Cross-Party Attraction Drivers
              </h3>
              <p className="text-xs text-slate-500 mb-3">
                Which factors explain each variant&apos;s cross-party pull? Bars show per-factor contribution
                to closing the distance between the variant and the attracted party.
              </p>
              <AttractionDriverChart data={fdAttractionDrivers} />
            </div>
          )}
        </>
      )}
    </div>
  );
}

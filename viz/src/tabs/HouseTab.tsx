import { useMemo } from 'react';
import { useUrlState } from '../hooks/useUrlState';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import type { HouseSeat, CoalitionProfile, TransferMatrix, VoteModelRow, HouseStateEntry, ClusterProfile, FDHouseSeat, FPTPState, DistrictResult } from '../types';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { BillSimulator } from '../components/house/BillSimulator';
import { HouseMap } from '../components/house/HouseMap';
import { HouseGridChart } from '../components/house/HouseGridChart';
import { ParliamentChart } from '../components/shared/ParliamentChart';
import { PartyVariantBar } from '../components/shared/PartyVariantBar';
import { PartyProfileGrid } from '../components/shared/PartyProfileGrid';
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
import { CLUSTER_TO_PARTY, partyOrder, FACTOR_LABELS } from '../constants/parties';
import { PIPELINE_LABELS, WYOMING_LABELS } from '../constants/labels';
import { ToggleGroup } from '../components/shared/ToggleGroup';
import { ParticipationSlider, GAP_STOPS } from '../components/shared/ParticipationSlider';
import { StickyControlBar } from '../components/shared/StickyControlBar';
// Gap-compression middle stops (λ=0.25/0.5/0.75); endpoints come via props.
import houseSeatsL25 from '../data/houseSeatsTurnoutL25.json';
import houseSeatsL50 from '../data/houseSeatsTurnoutL50.json';
import houseSeatsL75 from '../data/houseSeatsTurnoutL75.json';
import houseStateMapL25 from '../data/houseStateMapTurnoutL25.json';
import houseStateMapL50 from '../data/houseStateMapTurnoutL50.json';
import houseStateMapL75 from '../data/houseStateMapTurnoutL75.json';
import houseDistL25 from '../data/districtStvResultsTurnoutL25.json';
import houseDistL50 from '../data/districtStvResultsTurnoutL50.json';
import houseDistL75 from '../data/districtStvResultsTurnoutL75.json';

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
  fdDistrictResults: Record<string, DistrictResult[]>;
  seatsTriple: HouseSeat[];
  fdHouseSeatsTriple: FDHouseSeat[];
  stateMapTriple: Record<string, HouseStateEntry>;
  districtResultsTriple: Record<string, DistrictResult[]>;
  fdDistrictResultsTriple: Record<string, DistrictResult[]>;
  districtCountyMapTriple: Record<string, string[]>;
  seatsTurnout: HouseSeat[];
  stateMapTurnout: Record<string, HouseStateEntry>;
  districtResultsTurnout: Record<string, DistrictResult[]>;
}

type WyomingRule = 'double' | 'triple';

export function HouseTab({ seats, transfers, voteModel, stateMap, clusters, fdHouseSeats, fptpStates, districtResults, districtCountyMap, houseTransfers, fdVariantAttraction, fdCandidatePositions, clusterSpreads, fdAttractionDrivers, fdDistrictResults, seatsTriple, fdHouseSeatsTriple, stateMapTriple, districtResultsTriple, fdDistrictResultsTriple, districtCountyMapTriple, seatsTurnout, stateMapTurnout, districtResultsTurnout}: Props) {
  const [scenario, setScenario] = useUrlState<'rawMulti' | 'factorDev'>('scenario', 'rawMulti', { allowed: ['rawMulti', 'factorDev'], map: { factorDev: 'crossover', rawMulti: 'party-line' } });
  const [wyoming, setWyoming] = useUrlState<WyomingRule>('wyoming', 'double', { allowed: ['double', 'triple'] });
  // Participation: gap-compression stop (0 = observed 2024 turnout … 100 = full parity).
  const [part, setPart] = useUrlState<string>('part', '0', { allowed: ['0', '25', '50', '75', '100'] });
  const rmDouble = scenario === 'rawMulti' && wyoming === 'double';
  const gi = Math.max(0, GAP_STOPS.indexOf(Number(part) as typeof GAP_STOPS[number]));
  // Arrays indexed by gap stop [0,25,50,75,100]: floor(Turnout) … ceiling(full/base).
  const seatsStops = [seatsTurnout, houseSeatsL25, houseSeatsL50, houseSeatsL75, seats] as unknown as HouseSeat[][];
  const mapStops   = [stateMapTurnout, houseStateMapL25, houseStateMapL50, houseStateMapL75, stateMap] as unknown as Record<string, HouseStateEntry>[];
  const distStops  = [districtResultsTurnout, houseDistL25, houseDistL50, houseDistL75, districtResults] as unknown as Record<string, DistrictResult[]>[];
  const rmSeats    = rmDouble ? seatsStops[gi] : seats;
  const rmStateMap = rmDouble ? mapStops[gi]   : stateMap;
  const rmDistrict = rmDouble ? distStops[gi]  : districtResults;

  const clusterByParty = useMemo(() => Object.fromEntries(clusters.map(c => [c.party, c])), [clusters]);
  const orderedClusters = useMemo(() => partyOrder().map(p => clusterByParty[p]).filter(Boolean) as ClusterProfile[], [clusterByParty]);
  const [mapView, setMapView] = useUrlState<'map' | 'grid'>('view', 'map', { allowed: ['map', 'grid'] });
  const [parliamentFactor, setParliamentFactor] = useUrlState<string>('factor', 'F5', { allowed: ['F1', 'F2', 'F3', 'F4', 'F5'] });
  const [seatShareState, setSeatShareState] = useUrlState<string>('state', 'national');

  const fdSeatsAggregated: HouseSeat[] = useMemo(() => {
    const byCluster: Record<number, { urban: number; suburban: number; rural: number; national: number }> = {};
    const CODE_TO_CLUSTER: Record<string, number> = { CON: 0, LBR: 1, STY: 2, NAT: 3, LIB: 4, POP: 5, CUP: 6, OAO: 7, DSA: 8, PRG: 9 };
    const CLUSTER_NAMES: Record<number, string> = { 0:'Conservative',1:'Labor',2:'Solidarity',3:'Nationalist',4:'Liberal',5:'Populist',6:'Civic Union Party',7:'Order and Opportunity Party',8:'DSA',9:'Progressive' };
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

  // FD aggregation for triple Wyoming
  const fdSeatsTripleAggregated: HouseSeat[] = useMemo(() => {
    const byCluster: Record<number, { urban: number; suburban: number; rural: number; national: number }> = {};
    const CODE_TO_CLUSTER: Record<string, number> = { CON: 0, LBR: 1, STY: 2, NAT: 3, LIB: 4, POP: 5, CUP: 6, OAO: 7, DSA: 8, PRG: 9 };
    const CLUSTER_NAMES: Record<number, string> = { 0:'Conservative',1:'Labor',2:'Solidarity',3:'Nationalist',4:'Liberal',5:'Populist',6:'Civic Union Party',7:'Order and Opportunity Party',8:'DSA',9:'Progressive' };
    for (const s of fdHouseSeatsTriple) {
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
  }, [fdHouseSeatsTriple, seats]);

  // Helper: convert cluster to percentile-based constellation node
  const clusterToNode = (c: CoalitionProfile | ClusterProfile) => {
    const party = 'type' in c ? (c as CoalitionProfile).type : (c as ClusterProfile).party;
    const cp = clusterByParty[party] ?? clusterByParty[party.split('_')[0]];
    return {
      id: party, label: party,
      seats: 'seatsHouse' in c ? (c as any).seatsHouse : 0,
      F1: ((cp as any)?.z_F1 ?? 0),
      F2: ((cp as any)?.z_F2 ?? 0),
      F3: ((cp as any)?.z_F3 ?? 0),
      F4: ((cp as any)?.z_F4 ?? 0),
      F5: ((cp as any)?.z_F5 ?? 0),
    };
  };

  const activeSeats = useMemo(() => {
    if (wyoming === 'triple') return scenario === 'rawMulti' ? seatsTriple : fdSeatsTripleAggregated;
    return scenario === 'rawMulti' ? rmSeats : fdSeatsAggregated;
  }, [wyoming, scenario, rmSeats, seatsTriple, fdSeatsAggregated, fdSeatsTripleAggregated]);
  const activeTotalSeats = activeSeats.reduce((s, r) => s + r.national, 0);
  const activeDistrictResults = wyoming === 'triple'
    ? (scenario === 'factorDev' ? fdDistrictResultsTriple : districtResultsTriple)
    : (scenario === 'factorDev' ? fdDistrictResults : rmDistrict);
  const activeDistrictCountyMap = wyoming === 'triple' ? districtCountyMapTriple : districtCountyMap;
  const activeStateMap = wyoming === 'triple' ? stateMapTriple : rmStateMap;
  const activeFdHouseSeats = wyoming === 'triple' ? fdHouseSeatsTriple : fdHouseSeats;
  const activeFdSeatsByCode = useMemo(() => {
    const map: Record<string, number> = {};
    for (const s of activeFdHouseSeats) map[s.code] = s.national;
    return map;
  }, [activeFdHouseSeats]);

  const parliamentSegments: ParliamentSegment[] = activeSeats
    .filter(s => s.national > 0)
    .map(s => {
      const code = s.party === 7 ? 'OAO' : (CLUSTER_TO_PARTY[String(s.party)] ?? '');
      const fVal = (clusterByParty[code] as unknown as Record<string, number>)?.[parliamentFactor] ?? 0;
      return { code, seats: s.national, fVal };
    })
    .filter(s => s.code)
    .sort((a, b) => a.fVal - b.fVal);

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-foreground mb-1">House of Representatives</h2>
        <p className="text-muted-foreground text-sm">
          {activeTotalSeats} seats allocated via STV across geographically-drawn multi-member districts.
        </p>
      </div>

      {/* Scenario toggle — sticky */}
      <StickyControlBar>
        <ToggleGroup label="Wyoming" value={wyoming} onChange={setWyoming}
          options={['double', 'triple'] as const} labels={WYOMING_LABELS} />
        <ToggleGroup label="Scenario" value={scenario} onChange={setScenario}
          options={['rawMulti', 'factorDev'] as const} labels={PIPELINE_LABELS} />
        {scenario === 'rawMulti' && wyoming === 'double' && (
          <ParticipationSlider value={Number(part)} onChange={v => setPart(String(v))} />
        )}
      </StickyControlBar>

      {/* ═══════════════════════════════════════════════════════════════════════
          SECTION 1: REPRESENTATION
          ═══════════════════════════════════════════════════════════════════════ */}

      {/* Hero: FPTP vs STV */}
      <Card className="p-5 border-2 border-indigo-200">
        <FPTPvsSTV seats={activeSeats} doubleSeats={rmSeats} wyoming={wyoming} />
      </Card>

      {/* Population vs Seat Share */}
      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
          Population vs Seat Share
        </h3>
        <p className="text-xs text-muted-foreground mb-4">
          How close does STV get to proportional representation? Faded bar = population share, solid = seat share.
          {scenario === 'factorDev' && ' Outlined = Crossover seat share for comparison.'}
        </p>
        <ScenarioComparison
          rawMultiSeats={wyoming === 'triple' ? seatsTriple : rmSeats}
          fdSeats={wyoming === 'triple' ? fdSeatsTripleAggregated : fdSeatsAggregated}
          scenario={scenario}
          wyoming={wyoming}
          doubleSeats={rmSeats}
          doubleFdSeats={fdSeatsAggregated}
          stateMap={activeStateMap}
          doubleStateMap={rmStateMap}
          selectedState={seatShareState}
          onStateChange={setSeatShareState}
        />
      </Card>

      {/* Vote Transfer Destinations — filtered by state/national */}
      {scenario === 'rawMulti' && houseTransfers.length > 0 && (
        <Card className="p-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
            Vote Transfer Destinations{seatShareState !== 'national' ? ` — ${seatShareState}` : ''}
          </h3>
          <p className="text-xs text-muted-foreground mb-4">
            {seatShareState === 'national'
              ? "When a party is eliminated in STV, where do their voters\u2019 ballots flow?"
              : `Showing parties that won seats in ${seatShareState}. Transfer patterns are national averages.`}
          </p>
          <TransferFlowChart
            data={houseTransfers}
            filterParties={seatShareState === 'national' ? undefined : (() => {
              const fips = Object.entries(activeStateMap).find(([, v]) => v.stateAbbr === seatShareState)?.[0];
              const entry = fips ? activeStateMap[fips] : undefined;
              return entry ? Object.keys(entry.seats) : undefined;
            })()}
          />
        </Card>
      )}

      {/* FD: Variant bar right after seat share */}
      {scenario === 'factorDev' && (
        <Card className="p-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
            Seats by Variant
          </h3>
          <p className="text-xs text-muted-foreground mb-3">
            {activeTotalSeats} seats stacked by axis variant. Full color = base; lighter = hi axis; darker = lo axis.
          </p>
          <PartyVariantBar seats={activeFdHouseSeats} totalLabel={`${activeTotalSeats} house seats`} />
        </Card>
      )}

      {/* Seats by District Type */}
      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
          Seats by District Type
        </h3>
        <p className="text-xs text-muted-foreground mb-3">
          Progressive parties dominate urban seats, conservatives dominate rural, suburbs are contested.
        </p>
        <UrbSubRurChart seats={activeSeats} />
      </Card>

      {/* ═══════════════════════════════════════════════════════════════════════
          SECTION 2: PARTIES & GEOGRAPHY
          ═══════════════════════════════════════════════════════════════════════ */}

      {/* Nine-Party Profiles — above the map */}
      <PartyProfileGrid clusters={orderedClusters} />

      {/* Chamber Composition */}
      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-2 mb-3">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">Chamber Composition</h3>
          <span className="text-xs text-muted-foreground">— order by:</span>
          {(['F1','F2','F3','F4','F5'] as const).map(f => (
            <Button key={f} onClick={() => setParliamentFactor(f)} title={FACTOR_LABELS[f]}
              variant={parliamentFactor === f ? 'default' : 'secondary'}
              size="sm">
              {f} · {FACTOR_LABELS[f]}
            </Button>
          ))}
        </div>
        <ParliamentChart segments={parliamentSegments} factor={parliamentFactor} />
      </Card>

      {/* State Composition — both views */}
      <Card className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">State Composition</h3>
          <div className="flex gap-1">
            {([['map', 'Map'], ['grid', 'Grid']] as const).map(([v, label]) => (
              <Button key={v} onClick={() => setMapView(v)}
                variant={mapView === v ? 'default' : 'secondary'}
                size="sm">
                {label}
              </Button>
            ))}
          </div>
        </div>
        {mapView === 'map' && <HouseMap districtResults={activeDistrictResults} districtCountyMap={activeDistrictCountyMap} />}
        {mapView === 'grid' && <HouseGridChart stateMap={activeStateMap} districtResults={activeDistrictResults} />}
      </Card>

      {/* FPTP disproportionality — below maps */}
      {fptpStates.length > 0 && (
        <Card className="p-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
            FPTP Disproportionality by State
          </h3>
          <p className="text-xs text-muted-foreground mb-4">
            How far each state&apos;s FPTP outcome diverges from proportional representation.
          </p>
          <FPTPDisproportionality states={fptpStates} stateMap={activeStateMap} />
        </Card>
      )}

      {/* Vote Transfer Destinations removed — now below Population vs Seat Share */}

      {/* ═══════════════════════════════════════════════════════════════════════
          SECTION 3: IDEOLOGICAL LANDSCAPE
          ═══════════════════════════════════════════════════════════════════════ */}

      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-3">
          Ideological Constellation
        </h3>
        <IdeologicalConstellation
          nodes={(() => {
            if (scenario === 'factorDev') {
              const fdNodes = fdCandidatePositions
                .filter(c => (activeFdSeatsByCode[c.code] ?? 0) > 0)
                .map(c => ({
                  id: c.code,
                  label: c.axis === 'base' ? c.party : c.code,
                  seats: activeFdSeatsByCode[c.code] ?? 1,
                  F1: c.F1, F2: c.F2, F3: c.F3, F4: c.F4, F5: c.F5,
                }));
              return fdNodes.length > 0 ? fdNodes : [];
            }
            return clusters
              .filter(c => (c as any).seatsHouse > 0)
              .map(c => clusterToNode(c));
          })()}
          transfers={scenario === 'rawMulti' ? transfers : undefined}
          clusterSpreads={clusterSpreads}
        />
      </Card>

      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-3">
          Bill Simulator
        </h3>
        <p className="text-xs text-muted-foreground mb-3">
          Probability of passage based on the House seat composition.
        </p>
        <BillSimulator rows={voteModel} probField={
          wyoming === 'triple'
            ? (scenario === 'rawMulti' ? 'houseRawMultiTripleProbPass' : 'houseFDTripleProbPass')
            : (scenario === 'rawMulti' ? 'houseRawMultiProbPass' : 'houseFDProbPass')
        } />
      </Card>

      <Card className="p-4">
        <StateSeatsTable stateMap={activeStateMap} wyoming={wyoming} />
      </Card>

      {/* ═══════════════════════════════════════════════════════════════════════
          SECTION 4: FACTOR DEV VARIANT ANALYSIS (FD only, at bottom)
          ═══════════════════════════════════════════════════════════════════════ */}

      {scenario === 'factorDev' && (
        <>
          <div className="border-t-2 border-violet-200 pt-6">
            <h3 className="text-lg font-bold text-violet-800 mb-1">Crossover Analysis</h3>
            <p className="text-xs text-muted-foreground mb-6">
              How do ideological deviations from party baselines affect seat composition and cross-party attraction?
            </p>
          </div>

          {/* Variant Impact */}
          <Card className="p-4">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
              Variant Impact by Party
            </h3>
            <p className="text-xs text-muted-foreground mb-4">
              Which ideological deviations win seats? Stacked bars show base vs axis variant contributions.
            </p>
            <VariantImpactChart seats={activeFdHouseSeats} />
          </Card>

          {/* Variant Voter Attraction Sources */}
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

          {/* Cross-Party Attraction Drivers */}
          {fdAttractionDrivers.length > 0 && (
            <Card className="p-4">
              <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
                Cross-Party Attraction Drivers
              </h3>
              <p className="text-xs text-muted-foreground mb-3">
                Which factors explain each variant&apos;s cross-party pull? Bars show per-factor contribution
                to closing the distance between the variant and the attracted party.
              </p>
              <AttractionDriverChart data={fdAttractionDrivers} />
            </Card>
          )}
        </>
      )}
    </div>
  );
}

import { useMemo, useState, useEffect } from 'react';
import { useUrlState } from '../hooks/useUrlState';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import type { HouseSeat, TransferMatrix, VoteModelRow, HouseStateEntry, ClusterProfile, FDHouseSeat, FPTPState, DistrictResult } from '../types';
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
import { PartyListView, seatMapToHouseSeats } from '../components/house/PartyListView';
import type { PLConfig } from '../components/house/PartyListView';
import { ScenarioComparison } from '../components/house/ScenarioComparison';
import { VariantImpactChart } from '../components/house/VariantImpactChart';
import { AttractionDriverChart } from '../components/house/AttractionDriverChart';
import { VariantAttractionChart } from '../components/house/VariantAttractionChart';
import type { ParliamentSegment } from '../components/shared/ParliamentChart';
import { CLUSTER_TO_PARTY, F5_ORDER, PARTY_NAMES, partyOrder, FACTOR_LABELS, DISPLAY_FACTORS } from '../constants/parties';
import depthNational from '../data/houseDepthNational.json';
import { PIPELINE_LABELS, WYOMING_LABELS, HOUSE_SYSTEM_LABELS } from '../constants/labels';
import { SHOW_CROSSOVER, PIPELINE_OPTIONS } from '../constants/features';
import { DEPTH_KEYS, DEPTH_LABELS, type DepthKey } from '../constants/depth';
import { ToggleGroup } from '../components/shared/ToggleGroup';
import { ParticipationSlider, GAP_STOPS } from '../components/shared/ParticipationSlider';
import { StickyControlBar } from '../components/shared/StickyControlBar';
import { uncertaintyAt, populationShares } from '../lib/uncertainty';
// Compression stops (5-point steps to 30% of the turnout gap closed); floor comes via props.
import houseSeatsL5 from '../data/houseSeatsTurnoutL5.json';
import houseSeatsL10 from '../data/houseSeatsTurnoutL10.json';
import houseSeatsL15 from '../data/houseSeatsTurnoutL15.json';
import houseSeatsL20 from '../data/houseSeatsTurnoutL20.json';
import houseSeatsL25 from '../data/houseSeatsTurnoutL25.json';
import houseSeatsL30 from '../data/houseSeatsTurnoutL30.json';
import houseStateMapL5 from '../data/houseStateMapTurnoutL5.json';
import houseStateMapL10 from '../data/houseStateMapTurnoutL10.json';
import houseStateMapL15 from '../data/houseStateMapTurnoutL15.json';
import houseStateMapL20 from '../data/houseStateMapTurnoutL20.json';
import houseStateMapL25 from '../data/houseStateMapTurnoutL25.json';
import houseStateMapL30 from '../data/houseStateMapTurnoutL30.json';
import houseDistL5 from '../data/districtStvResultsTurnoutL5.json';
import houseDistL10 from '../data/districtStvResultsTurnoutL10.json';
import houseDistL15 from '../data/districtStvResultsTurnoutL15.json';
import houseDistL20 from '../data/districtStvResultsTurnoutL20.json';
import houseDistL25 from '../data/districtStvResultsTurnoutL25.json';
import houseDistL30 from '../data/districtStvResultsTurnoutL30.json';
// Crossover (FD) + triple-Wyoming compression stops.
import fdSeats0 from '../data/fdHouseSeatsTurnout.json';
import fdSeats5 from '../data/fdHouseSeatsTurnoutL5.json';
import fdSeats10 from '../data/fdHouseSeatsTurnoutL10.json';
import fdSeats15 from '../data/fdHouseSeatsTurnoutL15.json';
import fdSeats20 from '../data/fdHouseSeatsTurnoutL20.json';
import fdSeats25 from '../data/fdHouseSeatsTurnoutL25.json';
import fdSeats30 from '../data/fdHouseSeatsTurnoutL30.json';
import fdDist0 from '../data/fdDistrictStvResultsTurnout.json';
import fdDist5 from '../data/fdDistrictStvResultsTurnoutL5.json';
import fdDist10 from '../data/fdDistrictStvResultsTurnoutL10.json';
import fdDist15 from '../data/fdDistrictStvResultsTurnoutL15.json';
import fdDist20 from '../data/fdDistrictStvResultsTurnoutL20.json';
import fdDist25 from '../data/fdDistrictStvResultsTurnoutL25.json';
import fdDist30 from '../data/fdDistrictStvResultsTurnoutL30.json';
import seatsTri0 from '../data/houseSeatsTripleTurnout.json';
import seatsTri5 from '../data/houseSeatsTripleTurnoutL5.json';
import seatsTri10 from '../data/houseSeatsTripleTurnoutL10.json';
import seatsTri15 from '../data/houseSeatsTripleTurnoutL15.json';
import seatsTri20 from '../data/houseSeatsTripleTurnoutL20.json';
import seatsTri25 from '../data/houseSeatsTripleTurnoutL25.json';
import seatsTri30 from '../data/houseSeatsTripleTurnoutL30.json';
import distTri0 from '../data/districtStvResultsTripleTurnout.json';
import distTri5 from '../data/districtStvResultsTripleTurnoutL5.json';
import distTri10 from '../data/districtStvResultsTripleTurnoutL10.json';
import distTri15 from '../data/districtStvResultsTripleTurnoutL15.json';
import distTri20 from '../data/districtStvResultsTripleTurnoutL20.json';
import distTri25 from '../data/districtStvResultsTripleTurnoutL25.json';
import distTri30 from '../data/districtStvResultsTripleTurnoutL30.json';
import fdSeatsTri0 from '../data/fdHouseSeatsTripleTurnout.json';
import fdSeatsTri5 from '../data/fdHouseSeatsTripleTurnoutL5.json';
import fdSeatsTri10 from '../data/fdHouseSeatsTripleTurnoutL10.json';
import fdSeatsTri15 from '../data/fdHouseSeatsTripleTurnoutL15.json';
import fdSeatsTri20 from '../data/fdHouseSeatsTripleTurnoutL20.json';
import fdSeatsTri25 from '../data/fdHouseSeatsTripleTurnoutL25.json';
import fdSeatsTri30 from '../data/fdHouseSeatsTripleTurnoutL30.json';
import fdDistTri0 from '../data/fdDistrictStvResultsTripleTurnout.json';
import fdDistTri5 from '../data/fdDistrictStvResultsTripleTurnoutL5.json';
import fdDistTri10 from '../data/fdDistrictStvResultsTripleTurnoutL10.json';
import fdDistTri15 from '../data/fdDistrictStvResultsTripleTurnoutL15.json';
import fdDistTri20 from '../data/fdDistrictStvResultsTripleTurnoutL20.json';
import fdDistTri25 from '../data/fdDistrictStvResultsTripleTurnoutL25.json';
import fdDistTri30 from '../data/fdDistrictStvResultsTripleTurnoutL30.json';

interface Props {
  seats: HouseSeat[];
  seatsProbBased: HouseSeat[];
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

// Population share by party code, stop-invariant. The pre-built houseSeats*.json bundles already
// carry these as pctPopulation; the depth bundles carry no population field, so they read it here.
const POP_SHARES = populationShares();

/** National seat counts and their density-tier split, per ballot depth x Wyoming map x turnout
 *  stop. A 71 KB projection of housePartyList.json's national blocks, emitted by the same script
 *  in the same loop, so it cannot disagree with the 4.1 MB file it is drawn from. */
type PartyCounts = Record<string, number>;
const DEPTH_NATIONAL = depthNational as unknown as Record<string, Record<string, Record<string, {
  national: { stvSeats: PartyCounts };
  stvTiers: { urban: PartyCounts; suburban: PartyCounts; rural: PartyCounts };
}>>>;
// Party code to the cluster index HouseSeat.party carries.
const CLUSTER_OF: Record<string, number> = Object.fromEntries(
  Object.entries(CLUSTER_TO_PARTY).map(([k, v]) => [v, Number(k)]));

export function HouseTab({ seats, transfers, voteModel, clusters, fptpStates, districtCountyMap, houseTransfers, fdVariantAttraction, fdCandidatePositions, clusterSpreads, fdAttractionDrivers, stateMapTriple, districtCountyMapTriple, seatsTurnout, stateMapTurnout, districtResultsTurnout}: Props) {
  const [scenario, setScenario] = useUrlState<'rawMulti' | 'factorDev'>('scenario', 'rawMulti', { allowed: PIPELINE_OPTIONS, map: { factorDev: 'crossover', rawMulti: 'party-line' } });
  const [wyoming, setWyoming] = useUrlState<WyomingRule>('wyoming', 'double', { allowed: ['double', 'triple'] });
  // Voting system: STV (default) vs a Hare-quota party list on the same districts.
  const [system, setSystem] = useUrlState<'stv' | 'list'>('system', 'stv', { allowed: ['stv', 'list'] });
  // Ballot depth: how many preferences voters rank (drives STV exhaustion / representation).
  // Default = top 7, a realistic "typical voter" depth; 'full' is the exhaustive-ranking floor.
  const [depth, setDepth] = useUrlState<DepthKey>('depth', 'top7', { allowed: [...DEPTH_KEYS] });
  // Participation: gap-compression stop (0 = observed 2024 turnout … 100 = full parity).
  const [part, setPart] = useUrlState<string>('part', '5', { allowed: ['0', '5', '10', '15', '20', '25', '30'] });
  const gi = Math.max(0, GAP_STOPS.indexOf(Number(part) as typeof GAP_STOPS[number]));
  // Party-list results are lazy-fetched (public static asset) only when the list flip is on.
  const [plData, setPlData] = useState<Record<string, Record<string, Record<string, PLConfig>>> | null>(null);
  useEffect(() => {
    if ((system === 'list' || scenario === 'rawMulti') && !plData) {
      fetch(`${import.meta.env.BASE_URL}data/housePartyList.json`).then(r => r.json()).then(setPlData).catch(() => {});
    }
  }, [system, scenario, plData]);
  // Bill Simulator vote model, tracked across ballot depth × turnout (rank-7 default). Lazy bundle.
  const [hvmDepth, setHvmDepth] = useState<Record<string, Record<string, VoteModelRow[]>> | null>(null);
  useEffect(() => {
    if (!hvmDepth) fetch(`${import.meta.env.BASE_URL}data/houseVoteModelDepth.json`).then(r => r.json()).then(setHvmDepth).catch(() => {});
  }, [hvmDepth]);
  const billRows = hvmDepth?.[depth]?.[part] ?? voteModel;
  const plConfig = plData?.[depth]?.[wyoming]?.[part];
  // Double-Wyoming party-list config, for the party-list view's double-vs-triple comparison rows.
  const plConfigDouble = plData?.[depth]?.['double']?.[part];
  const partyListSeatsForChart = useMemo(
    () => (scenario === 'rawMulti' && plConfig ? seatMapToHouseSeats(plConfig.national.listSeats) : undefined),
    [scenario, plConfig],
  );
  // Compression stops [0,5,10,15,20,25,30] per scenario × Wyoming. Every cell now tracks the
  // slider: RawMulti/Crossover × double/triple.
  const rmSeats    = [seatsTurnout, houseSeatsL5, houseSeatsL10, houseSeatsL15, houseSeatsL20, houseSeatsL25, houseSeatsL30][gi] as unknown as HouseSeat[];
  const rmStateMap = [stateMapTurnout, houseStateMapL5, houseStateMapL10, houseStateMapL15, houseStateMapL20, houseStateMapL25, houseStateMapL30][gi] as unknown as Record<string, HouseStateEntry>;
  const rmDistrict = [districtResultsTurnout, houseDistL5, houseDistL10, houseDistL15, houseDistL20, houseDistL25, houseDistL30][gi] as unknown as Record<string, DistrictResult[]>;
  const fdSeatsGi        = [fdSeats0, fdSeats5, fdSeats10, fdSeats15, fdSeats20, fdSeats25, fdSeats30][gi] as unknown as FDHouseSeat[];
  const fdSeatsTripleGi  = [fdSeatsTri0, fdSeatsTri5, fdSeatsTri10, fdSeatsTri15, fdSeatsTri20, fdSeatsTri25, fdSeatsTri30][gi] as unknown as FDHouseSeat[];
  const seatsTripleGi    = [seatsTri0, seatsTri5, seatsTri10, seatsTri15, seatsTri20, seatsTri25, seatsTri30][gi] as unknown as HouseSeat[];
  const fdDistrictGi       = [fdDist0, fdDist5, fdDist10, fdDist15, fdDist20, fdDist25, fdDist30][gi] as unknown as Record<string, DistrictResult[]>;
  const fdDistrictTripleGi = [fdDistTri0, fdDistTri5, fdDistTri10, fdDistTri15, fdDistTri20, fdDistTri25, fdDistTri30][gi] as unknown as Record<string, DistrictResult[]>;
  const districtTripleGi   = [distTri0, distTri5, distTri10, distTri15, distTri20, distTri25, distTri30][gi] as unknown as Record<string, DistrictResult[]>;
  // Sampling uncertainty at the active stop. The bootstrap ran the party-line pipeline with
  // rank-7 ballots on the 873-seat double-Wyoming map, so its seat counts describe that
  // configuration only; every other combination degrades to plain bars with no ranges.
  // The depth condition is what pairs the bounds with a matching point estimate: at any other
  // depth the chamber differs by up to 6 seats per party, so a range drawn then would describe a
  // different chamber than the number beside it. Since `stvDepthSeats` now comes from a bundled
  // projection rather than the 4.1 MB fetch, this resolves at first paint.
  const houseU = scenario === 'rawMulti' && wyoming === 'double' && depth === 'top7'
    ? uncertaintyAt(gi)?.house.seats
    : undefined;
  // The party-list view has no Scenario control — the list is always allocated from the party-line
  // vote — so it must not inherit a stale `factorDev` from the STV view. Depth still binds: the
  // list is depth-invariant, but its STV comparison row's point estimate is not, and pairing a
  // top-3 point with rank-7 bounds would describe two different chambers.
  const houseUList = wyoming === 'double' && depth === 'top7' ? uncertaintyAt(gi)?.house.seats : undefined;

  const clusterByParty = useMemo(() => Object.fromEntries(clusters.map(c => [c.party, c])), [clusters]);
  const orderedClusters = useMemo(() => partyOrder().map(p => clusterByParty[p]).filter(Boolean) as ClusterProfile[], [clusterByParty]);
  const [mapView, setMapView] = useUrlState<'map' | 'grid'>('view', 'map', { allowed: ['map', 'grid'] });
  const [parliamentFactor, setParliamentFactor] = useUrlState<string>('factor', 'F5', { allowed: [...DISPLAY_FACTORS] });
  const [seatShareState, setSeatShareState] = useUrlState<string>('state', 'national');

  // Below-quota seat share (STV) at the current ballot depth vs the full-ranking floor, for the
  // geography selected in the seat-share chart. Reads the same lazy party-list bundle.
  const belowQuota = useMemo(() => {
    if (scenario !== 'rawMulti' || !plData) return null;
    const pick = (dk: DepthKey): number | null => {
      const cfg = plData?.[dk]?.[wyoming]?.[part];
      if (!cfg) return null;
      if (seatShareState !== 'national') {
        const s = Object.values(cfg.byState).find(v => v.abbr === seatShareState);
        return s?.belowQuota?.stv ?? null;
      }
      return cfg.national.belowQuota?.stv ?? null;
    };
    const current = pick(depth); const floor = pick('full');
    return (current == null || floor == null) ? null : { current, floor };
  }, [scenario, plData, depth, wyoming, part, seatShareState]);

  const fdSeatsAggregated: HouseSeat[] = useMemo(() => {
    const byCluster: Record<number, { urban: number; suburban: number; rural: number; national: number }> = {};
    const CODE_TO_CLUSTER: Record<string, number> = { CON: 0, LBR: 1, STY: 2, NAT: 3, LIB: 4, POP: 5, CUP: 6, OAO: 7, DSA: 8, PRG: 9 };
    const CLUSTER_NAMES: Record<number, string> = { 0:'Conservative',1:'Labor',2:'Solidarity',3:'Nationalist',4:'Liberal',5:'Populist',6:'Civic Union Party',7:'Order and Opportunity Party',8:'DSA',9:'Progressive' };
    for (const s of fdSeatsGi) {
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
  }, [fdSeatsGi, seats]);

  // FD aggregation for triple Wyoming
  const fdSeatsTripleAggregated: HouseSeat[] = useMemo(() => {
    const byCluster: Record<number, { urban: number; suburban: number; rural: number; national: number }> = {};
    const CODE_TO_CLUSTER: Record<string, number> = { CON: 0, LBR: 1, STY: 2, NAT: 3, LIB: 4, POP: 5, CUP: 6, OAO: 7, DSA: 8, PRG: 9 };
    const CLUSTER_NAMES: Record<number, string> = { 0:'Conservative',1:'Labor',2:'Solidarity',3:'Nationalist',4:'Liberal',5:'Populist',6:'Civic Union Party',7:'Order and Opportunity Party',8:'DSA',9:'Progressive' };
    for (const s of fdSeatsTripleGi) {
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
  }, [fdSeatsTripleGi, seats]);

  // Helper: convert cluster to percentile-based constellation node
  const clusterToNode = (c: ClusterProfile) => {
    const party = c.party;
    const cp = clusterByParty[party] ?? clusterByParty[party.split('_')[0]];
    return {
      id: party, label: party,
      seats: c.seatsHouse ?? 0,
      F1: ((cp as any)?.z_F1 ?? 0),
      F2: ((cp as any)?.z_F2 ?? 0),
      F3: ((cp as any)?.z_F3 ?? 0),
      F4: ((cp as any)?.z_F4 ?? 0),
      F5: ((cp as any)?.z_F5 ?? 0),
    };
  };

  // Truncated ballots: the rawMulti STV results come from the depth-limited runs (party-list is
  // depth-invariant). Adapt housePartyList's per-depth STV fields into the STV view's shapes.
  // National seat counts by party for the active depth, from the 71 KB bundled projection of
  // housePartyList.json rather than the 4.1 MB file itself. These drive the headline charts, so
  // sourcing them here is what lets those render at first paint instead of after a fetch.
  const stvDepthSeats = useMemo(() => {
    if (depth === 'full' || scenario !== 'rawMulti') return null;
    const cfg = DEPTH_NATIONAL[depth]?.[wyoming]?.[part];
    if (!cfg) return null;
    const total = Object.values(cfg.national.stvSeats).reduce((a, b) => a + b, 0) || 1;
    return F5_ORDER.map(code => {
      const k = CLUSTER_OF[code];
      const n = cfg.national.stvSeats[code] ?? 0;
      return {
        party: k, partyName: PARTY_NAMES[code],
        urban: cfg.stvTiers.urban[code] ?? 0,
        suburban: cfg.stvTiers.suburban[code] ?? 0,
        rural: cfg.stvTiers.rural[code] ?? 0,
        national: n, pctNational: n / total * 100,
        // True population share, matching the field's name and the "Population" label it renders
        // under. This held vote share until 2026-07-30 — a different quantity (Solidarity showed
        // 9.84 against a real 14.25). Vote share is now its own row in the range view, read from
        // the same populationShareRange payload as this. Do not restore.
        pctPopulation: POP_SHARES[code]?.point ?? 0,
      };
    }).filter(r => r.national > 0) as unknown as HouseSeat[];
  }, [depth, scenario, wyoming, part]);

  // Per-state and per-district detail for the same run. This is the part that genuinely needs the
  // big payload, and it feeds the map and state table further down the page, where arriving a
  // moment late is not visible the way a swapped headline chart is.
  const stvDepthDetail = useMemo(() => {
    if (depth === 'full' || scenario !== 'rawMulti') return null;
    const cfg = plData?.[depth]?.[wyoming]?.[part] as unknown as {
      national: { voteShare: Record<string, number> };
      byState: Record<string, { abbr: string; totalSeats: number; stvSeats: Record<string, number>; voteShare: Record<string, number> }>;
      districts: Record<string, { districtId: string; densityTier: string; seatCount: number; stvElected: string[]; nRespondents: number }[]>;
    } | undefined;
    if (!cfg) return null;
    const districts: Record<string, DistrictResult[]> = {};
    for (const [fips, ds] of Object.entries(cfg.districts)) {
      districts[fips] = ds.map(d => ({ districtId: d.districtId, densityTier: d.densityTier as DistrictResult['densityTier'], seatCount: d.seatCount, elected: d.stvElected, nRespondents: d.nRespondents }));
    }
    const stateMap: Record<string, HouseStateEntry> = {};
    for (const [fips, s] of Object.entries(cfg.byState)) {
      const plur = Object.entries(s.stvSeats).sort((a, b) => b[1] - a[1])[0]?.[0] ?? '';
      // No popShares: this held s.voteShare until 2026-07-30, which the state-level card rendered
      // under a "Population" label (California Conservative 12.8 against a real 12.2). The depth
      // bundle carries no per-state population field, so leaving it out lets the card fall back to
      // the state map's own popShares, which are population and stop-invariant. Do not restore.
      stateMap[fips] = { stateAbbr: s.abbr, pluralityParty: plur, totalSeats: s.totalSeats, seats: s.stvSeats } as unknown as HouseStateEntry;
    }
    return { stateMap, districts };
  }, [depth, scenario, plData, wyoming, part]);

  const activeSeats = useMemo(() => {
    if (stvDepthSeats) return stvDepthSeats;
    if (wyoming === 'triple') return scenario === 'rawMulti' ? seatsTripleGi : fdSeatsTripleAggregated;
    return scenario === 'rawMulti' ? rmSeats : fdSeatsAggregated;
  }, [stvDepthSeats, wyoming, scenario, rmSeats, seatsTripleGi, fdSeatsAggregated, fdSeatsTripleAggregated]);
  const activeTotalSeats = activeSeats.reduce((s, r) => s + r.national, 0);
  const activeDistrictResults = stvDepthDetail ? stvDepthDetail.districts : (wyoming === 'triple'
    ? (scenario === 'factorDev' ? fdDistrictTripleGi : districtTripleGi)
    : (scenario === 'factorDev' ? fdDistrictGi : rmDistrict));
  const activeDistrictCountyMap = wyoming === 'triple' ? districtCountyMapTriple : districtCountyMap;
  const activeStateMap = stvDepthDetail ? stvDepthDetail.stateMap : (wyoming === 'triple' ? stateMapTriple : rmStateMap);
  const activeFdHouseSeats = wyoming === 'triple' ? fdSeatsTripleGi : fdSeatsGi;
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
          {system === 'list'
            ? `${plConfig?.national.totalSeats ?? activeTotalSeats} seats by Hare-quota party list, on the same districts as STV.`
            : `${activeTotalSeats} seats allocated via STV across geographically-drawn multi-member districts.`}
        </p>
      </div>

      {/* Scenario toggle — sticky */}
      <StickyControlBar label="House settings">
        <ToggleGroup label="Wyoming" value={wyoming} onChange={setWyoming}
          options={['double', 'triple'] as const} labels={WYOMING_LABELS} />
        <ToggleGroup label="System" value={system} onChange={setSystem}
          options={['stv', 'list'] as const} labels={HOUSE_SYSTEM_LABELS} />
        {SHOW_CROSSOVER && system === 'stv' && (
          <ToggleGroup label="Scenario" value={scenario} onChange={setScenario}
            options={PIPELINE_OPTIONS} labels={PIPELINE_LABELS} />
        )}
        {(system === 'list' || scenario === 'rawMulti') && (
          <ToggleGroup label="Ballots ranked" value={depth} onChange={setDepth}
            options={[...DEPTH_KEYS]} labels={DEPTH_LABELS} />
        )}
        <ParticipationSlider value={Number(part)} onChange={v => setPart(String(v))} />
      </StickyControlBar>

      {system === 'list' && (plConfig
        ? <PartyListView config={plConfig} wyoming={wyoming} doubleConfig={plConfigDouble}
            districtCountyMap={wyoming === 'triple' ? districtCountyMapTriple : districtCountyMap}
            houseU={houseUList} gi={gi} />
        : <div className="py-24 text-center text-sm text-muted-foreground">Loading party-list results…</div>)}

      {system === 'stv' && (<>
      {/* ═══════════════════════════════════════════════════════════════════════
          SECTION 1: REPRESENTATION
          ═══════════════════════════════════════════════════════════════════════ */}

      {/* Hero: FPTP vs STV vs Party List */}
      <Card className="p-5 border-2 border-indigo-200">
        <FPTPvsSTV
          seats={activeSeats}
          systemLabel="STV"
          otherSystemSeats={partyListSeatsForChart}
          otherSystemLabel="Party List"
          doubleSeats={rmSeats}
          wyoming={wyoming}
        />
      </Card>

      {/* Population vs Seat Share */}
      <Card className="p-4">
        <ScenarioComparison
          rawMultiSeats={stvDepthSeats ?? (wyoming === 'triple' ? seatsTripleGi : rmSeats)}
          fdSeats={wyoming === 'triple' ? fdSeatsTripleAggregated : fdSeatsAggregated}
          scenario={scenario}
          wyoming={wyoming}
          doubleSeats={rmSeats}
          doubleFdSeats={fdSeatsAggregated}
          stateMap={activeStateMap}
          doubleStateMap={rmStateMap}
          selectedState={seatShareState}
          onStateChange={setSeatShareState}
          houseU={houseU}
          gi={gi}
        />
      </Card>

      {/* Seats won below quota — the exhaustion cost of shorter ballots */}
      {scenario === 'rawMulti' && belowQuota && (
        <Card className="p-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
            Seats won below quota{seatShareState !== 'national' ? ` — ${seatShareState}` : ''}
          </h3>
          <div className="grid grid-cols-2 gap-2 max-w-md">
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <div className="text-[11px] text-muted-foreground">Ballots ranked {DEPTH_LABELS[depth].toLowerCase()}</div>
              <div className="text-2xl font-bold tabular-nums text-amber-700">{belowQuota.current.toFixed(1)}%</div>
            </div>
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
              <div className="text-[11px] text-muted-foreground">Rank all · floor</div>
              <div className="text-2xl font-bold tabular-nums text-emerald-700">{belowQuota.floor.toFixed(1)}%</div>
            </div>
          </div>
        </Card>
      )}

      {/* Voters left unrepresented + over-quota surplus (mirrored from party-list view) */}
      {scenario === 'rawMulti' && plConfig && (
        <>
          <Card className="p-4">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
              Voters left unrepresented
            </h3>
            <p className="text-xs text-muted-foreground mb-4">Nobody they voted for won a seat.</p>
            <div className="grid grid-cols-3 gap-2">
              <div className="rounded-lg border border-rose-200 bg-rose-50 p-3">
                <div className="text-[11px] text-muted-foreground">Today's House <span className="opacity-70">· 2024</span></div>
                <div className="text-2xl font-bold tabular-nums text-rose-700">35.8%</div>
              </div>
              <div className="rounded-lg border border-border bg-muted/40 p-3">
                <div className="text-[11px] text-muted-foreground">Party list</div>
                <div className="text-2xl font-bold tabular-nums text-foreground">{plConfig.national.unrepresented.list.toFixed(1)}%</div>
              </div>
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
                <div className="text-[11px] text-muted-foreground">STV</div>
                <div className="text-2xl font-bold tabular-nums text-emerald-700">{plConfig.national.unrepresented.stv.toFixed(1)}%</div>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
              Over-quota surplus
            </h3>
            <p className="text-xs text-muted-foreground mb-4">Votes above what a winner needed.</p>
            <div className="grid grid-cols-3 gap-2">
              <div className="rounded-lg border border-rose-200 bg-rose-50 p-3">
                <div className="text-[11px] text-muted-foreground">Today's House <span className="opacity-70">· 2024</span></div>
                <div className="text-2xl font-bold tabular-nums text-rose-700">14.2%</div>
              </div>
              <div className="rounded-lg border border-border bg-muted/40 p-3">
                <div className="text-[11px] text-muted-foreground">Party list <span className="opacity-70">· stranded</span></div>
                <div className="text-2xl font-bold tabular-nums text-foreground">{plConfig.national.excess.list.toFixed(1)}%</div>
              </div>
              <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
                <div className="text-[11px] text-muted-foreground">STV <span className="opacity-70">· transferred</span></div>
                <div className="text-2xl font-bold tabular-nums text-emerald-700">{plConfig.national.excess.stv.toFixed(1)}%</div>
              </div>
            </div>
          </Card>
        </>
      )}

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
          {DISPLAY_FACTORS.map(f => (
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
        <BillSimulator rows={billRows} probField={
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
      </>)}
    </div>
  );
}

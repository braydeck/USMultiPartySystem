import { useMemo, type ReactNode } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { HouseMap } from './HouseMap';
import { HouseGridChart } from './HouseGridChart';
import { PartyHighlightFilter } from './PartyHighlightFilter';
import { CollapsibleSection } from '../shared/CollapsibleSection';
import { PartyProfileGrid } from '../shared/PartyProfileGrid';
import { VotesVsSeats, type Span } from '../shared/VotesVsSeats';
import { UrbSubRurChart } from './UrbSubRurChart';
import { seatTotals } from '../../lib/seatTotals';
import { StateSeatsTable } from './StateSeatsTable';
import { FPTPvsSTV } from './FPTPvsSTV';
import { useUrlState } from '../../hooks/useUrlState';
import { usePartyHighlight } from '../../hooks/usePartyHighlight';
import { F5_ORDER, PARTY_NAMES } from '../../constants/parties';
import { populationShares, voteSharesAt, partyListSharesAt, partyListSeatsAt, type SeatInterval } from '../../lib/uncertainty';
import type { DistrictResult, HouseStateEntry, HouseSeat, ClusterProfile } from '../../types';
import { CARD_HEADING, MINOR_HEADING, CARD_HINT } from '../../constants/typography';

type SeatMap = Record<string, number>;
interface Metrics { list: number; stv: number; fptp: number }
interface ListStv { list: number; stv: number }

const CURRENT_UNREPRESENTED = 35.8;
const CURRENT_COVERAGE = 100 - CURRENT_UNREPRESENTED;
const CURRENT_SURPLUS = 14.2;

export interface PLConfig {
  national: {
    totalSeats: number;
    voteShare: SeatMap;
    listSeats: SeatMap;
    stvSeats: SeatMap;
    fptpSeats?: SeatMap;
    unrepresented: ListStv;
    nonFirstChoice: ListStv;
    excess: ListStv;
    wasted: Metrics;
    gallagher: Metrics;
    belowQuota: { stv: number };
    softCoverage: { listDistrict: number; stvDistrict: number; listState: number; stvState: number };
  };
  byState: Record<string, {
    abbr: string; totalSeats: number; voteShare: SeatMap; listSeats: SeatMap; stvSeats: SeatMap;
    unrepresented: ListStv; nonFirstChoice: ListStv; wasted: Metrics; belowQuota: { stv: number };
  }>;
  districts: Record<string, {
    districtId: string; densityTier: string; seatCount: number;
    listElected: string[]; stvElected: string[]; nRespondents: number;
  }[]>;
}

interface Props {
  config: PLConfig;
  wyoming: 'double' | 'triple';
  onWyomingChange?: (w: 'double' | 'triple') => void;
  districtCountyMap: Record<string, string[]>;
  doubleConfig?: PLConfig;
  houseU?: Record<string, SeatInterval>;
  gi: number;
  clusters: ClusterProfile[];
  profilesExtra?: ReactNode;
  chamber?: ReactNode;
  fptpDispro?: ReactNode;
  mmpNational?: { seats: SeatMap; totalSeats: number };
}

const CLUSTER_OF: Record<string, number> = { CON: 0, LBR: 1, STY: 2, NAT: 3, LIB: 4, POP: 5, CUP: 6, OAO: 7, DSA: 8, PRG: 9 };

export function seatMapToHouseSeats(seatMap: SeatMap): HouseSeat[] {
  return F5_ORDER.map(p => ({
    party: CLUSTER_OF[p], partyName: PARTY_NAMES[p], national: seatMap[p] ?? 0,
    urban: 0, suburban: 0, rural: 0, pctNational: 0, pctPopulation: 0,
  })).filter(s => s.national > 0) as unknown as HouseSeat[];
}

export function PartyListView({ config, wyoming, onWyomingChange, districtCountyMap, doubleConfig, houseU, gi, clusters, profilesExtra, chamber, fptpDispro, mmpNational }: Props) {
  const [mapView, setMapView] = useUrlState<'map' | 'grid'>('view', 'map', { allowed: ['map', 'grid'] });
  const [selState, setSelState] = useUrlState<string>('plstate', 'national');
  const [mapState, setMapState] = useUrlState<string>('mapstate', 'national');
  const [highlight, setHighlight] = usePartyHighlight();
  const nat = config.national;

  const stateOpts = useMemo(() => [
    { value: 'national', label: 'National' },
    ...Object.entries(config.byState).map(([f, s]) => ({ value: f, label: s.abbr })).sort((a, b) => a.label.localeCompare(b.label)),
  ], [config]);
  const stateSel = selState !== 'national' ? config.byState[selState] : undefined;
  const active = stateSel
    ? { voteShare: stateSel.voteShare, listSeats: stateSel.listSeats, stvSeats: stateSel.stvSeats, totalSeats: stateSel.totalSeats }
    : { voteShare: nat.voteShare, listSeats: nat.listSeats, stvSeats: nat.stvSeats, totalSeats: nat.totalSeats };

  const districtResults = useMemo(() => {
    const out: Record<string, DistrictResult[]> = {};
    for (const [fips, ds] of Object.entries(config.districts)) {
      out[fips] = ds.map(d => ({
        districtId: d.districtId, densityTier: d.densityTier as DistrictResult['densityTier'],
        seatCount: d.seatCount, elected: d.listElected, nRespondents: d.nRespondents,
      }));
    }
    return out;
  }, [config]);

  const mapTotals = useMemo(() => seatTotals(districtResults), [districtResults]);

  const tierSeats = useMemo(() => {
    const per: Record<string, { urban: number; suburban: number; rural: number; national: number }> = {};
    for (const rows of Object.values(config.districts)) {
      for (const d of rows) {
        const key = d.densityTier === 'URBAN' ? 'urban' : d.densityTier === 'SUBURBAN' ? 'suburban' : 'rural';
        for (const p of d.listElected) {
          per[p] ??= { urban: 0, suburban: 0, rural: 0, national: 0 };
          per[p][key]++; per[p].national++;
        }
      }
    }
    return F5_ORDER.filter(p => per[p]).map(p => ({
      party: CLUSTER_OF[p], partyName: PARTY_NAMES[p], national: per[p].national,
      urban: per[p].urban, suburban: per[p].suburban, rural: per[p].rural,
      pctNational: 0, pctPopulation: 0,
    })) as unknown as HouseSeat[];
  }, [config]);

  const stateMap = useMemo(() => {
    const out: Record<string, HouseStateEntry> = {};
    for (const [fips, s] of Object.entries(config.byState)) {
      const plurality = Object.entries(s.listSeats).sort((a, b) => b[1] - a[1])[0]?.[0] ?? '';
      out[fips] = { stateAbbr: s.abbr, pluralityParty: plurality, totalSeats: s.totalSeats,
        seats: s.listSeats, popShares: s.voteShare } as unknown as HouseStateEntry;
    }
    return out;
  }, [config]);

  const partyListSeats = useMemo(() => seatMapToHouseSeats(nat.listSeats), [nat]);
  const doubleListSeats = useMemo(
    () => (wyoming === 'triple' && doubleConfig ? seatMapToHouseSeats(doubleConfig.national.listSeats) : undefined),
    [wyoming, doubleConfig],
  );

  // Bootstrap intervals (only at rank-7 / double-Wyoming)
  const intervals = useMemo(() => {
    if (!houseU || stateSel) return { pop: undefined, vote: undefined, list: undefined, stv: undefined };
    const pop = populationShares();
    const vote = voteSharesAt(gi);
    const listIvs = partyListSharesAt(gi);
    if (!vote || !listIvs) return { pop: undefined, vote: undefined, list: undefined, stv: undefined };
    const stvTotal = Object.values(nat.stvSeats).reduce((a, b) => a + b, 0) || 1;

    const popIvs: Record<string, Span> = {};
    const voteIvs: Record<string, Span> = {};
    const listSpans: Record<string, Span> = {};
    const stvSpans: Record<string, Span> = {};
    for (const code of F5_ORDER) {
      const pv = pop[code]; if (pv) popIvs[code] = pv;
      const vv = vote[code]; if (vv) voteIvs[code] = vv;
      const lv = listIvs[code]; if (lv) listSpans[code] = lv;
      const u = houseU[code];
      if (u) stvSpans[code] = { expected: u.expected / stvTotal * 100, lo: u.lo / stvTotal * 100, hi: u.hi / stvTotal * 100 };
    }
    return { pop: popIvs, vote: voteIvs, list: listSpans, stv: stvSpans };
  }, [houseU, gi, stateSel, nat]);

  // Build system entries for VotesVsSeats
  const vssSystems = useMemo(() => {
    const entries = [
      {
        key: 'list', label: 'Party List', texture: 'primary' as const,
        seats: active.listSeats, totalSeats: active.totalSeats,
        intervals: intervals.list, defaultOn: true,
      },
      {
        key: 'stv', label: 'STV', texture: 'compare' as const,
        seats: active.stvSeats, totalSeats: active.totalSeats,
        intervals: intervals.stv,
      },
    ];
    if (mmpNational && !stateSel) {
      entries.push({
        key: 'mmp', label: 'MMP', texture: 'compare' as const,
        seats: mmpNational.seats, totalSeats: mmpNational.totalSeats,
        intervals: undefined,
      });
    }
    return entries;
  }, [active, intervals, mmpNational, stateSel]);

  return (
    <div className="space-y-8">
      <Card className="p-5">
        <FPTPvsSTV
          seats={partyListSeats}
          systemLabel="Party List"
          doubleSeats={doubleListSeats}
          wyoming={wyoming}
        />
      </Card>

      <CollapsibleSection id="profiles" title="See party profiles" hint="Ten parties, their positions and who they draw from">
        <PartyProfileGrid clusters={clusters} />
        {profilesExtra}
      </CollapsibleSection>

      {chamber}

      <Card className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h4 className={CARD_HEADING}>State Composition</h4>
          <div className="flex gap-1">
            {([['map', 'Map'], ['grid', 'Grid']] as const).map(([v, label]) => (
              <Button key={v} onClick={() => setMapView(v)} variant={mapView === v ? 'default' : 'secondary'} size="sm">{label}</Button>
            ))}
          </div>
        </div>
        <div className="mb-3">
          <PartyHighlightFilter totals={mapTotals} value={highlight} onChange={setHighlight} />
        </div>
        {mapView === 'map'
          ? <HouseMap districtResults={districtResults} districtCountyMap={districtCountyMap}
              wyoming={wyoming} selectedFips={mapState} onSelectFips={setMapState} highlight={highlight} />
          : <HouseGridChart stateMap={stateMap} districtResults={districtResults} highlight={highlight} />}
      </Card>

      <Card className="p-4">
        <h4 className={`${CARD_HEADING} mb-1`}>Seats by District Type</h4>
        <p className={`${CARD_HINT} mb-3`}>
          Progressive parties dominate urban seats, conservatives dominate rural, suburbs are contested.
        </p>
        <UrbSubRurChart seats={tierSeats} />
      </Card>

      <CollapsibleSection id="dispro" title="See disproportionality & method comparison"
        hint="Coverage, Gallagher index, and votes against seats across electoral methods">
        <section className="space-y-6">
          {/* Metric cards */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="p-4">
              <h5 className={`${MINOR_HEADING} mb-1`}>Representational coverage</h5>
              <p className={`${CARD_HINT} mb-3`}>Posterior identity on a seated party.</p>
              <div className="grid grid-cols-3 gap-2">
                <Stat label="Today's House" value={CURRENT_COVERAGE} tone="worst" note="2024 · binary" />
                <Stat label="Party list" value={nat.softCoverage.listState}
                  tone={nat.softCoverage.listState >= nat.softCoverage.stvState ? 'best' : 'mid'} />
                <Stat label="STV" value={nat.softCoverage.stvState}
                  tone={nat.softCoverage.stvState >= nat.softCoverage.listState ? 'best' : 'mid'} />
              </div>
            </Card>
            <Card className="p-4">
              <h5 className={`${MINOR_HEADING} mb-1`}>Voters left unrepresented</h5>
              <p className={`${CARD_HINT} mb-3`}>Nobody they voted for won a seat.</p>
              <div className="grid grid-cols-3 gap-2">
                <Stat label="Today's House" value={CURRENT_UNREPRESENTED} tone="worst" note="2024" />
                <Stat label="Party list" value={nat.unrepresented.list} tone="mid" />
                <Stat label="STV" value={nat.unrepresented.stv} tone="best" />
              </div>
            </Card>
            <Card className="p-4">
              <h5 className={`${MINOR_HEADING} mb-1`}>Over-quota surplus</h5>
              <p className={`${CARD_HINT} mb-3`}>Votes above what a winner needed.</p>
              <div className="grid grid-cols-3 gap-2">
                <Stat label="Today's House" value={CURRENT_SURPLUS} tone="worst" note="2024" />
                <Stat label="Party list" value={nat.excess.list} tone="mid" note="stranded" />
                <Stat label="STV" value={nat.excess.stv} tone="best" note="transferred" />
              </div>
            </Card>
          </div>

          {/* Gallagher */}
          <div>
            <h5 className={`${MINOR_HEADING} mb-1`}>Gallagher index</h5>
            <p className={`${CARD_HINT} mb-3`}>Lower is closer to proportional.</p>
            <div className="grid grid-cols-3 gap-2 max-w-md">
              <Stat label="FPTP (drawn)" value={nat.gallagher.fptp} tone="worst" isCount />
              <Stat label="Party list" value={nat.gallagher.list}
                tone={nat.gallagher.list <= nat.gallagher.stv ? 'best' : 'mid'} isCount />
              <Stat label="STV" value={nat.gallagher.stv}
                tone={nat.gallagher.stv <= nat.gallagher.list ? 'best' : 'mid'} isCount />
            </div>
          </div>

          {/* Unified votes-against-seats */}
          <div>
            <h5 className={`${MINOR_HEADING} mb-1`}>Votes against seats</h5>
            <p className={`${CARD_HINT} mb-3`}>
              {stateSel ? `${stateSel.abbr}. ` : ''}The share of the vote each party wins compared with
              the share of the {active.totalSeats} seats it ends up with.
            </p>
            <VotesVsSeats
              systems={vssSystems}
              voteShare={active.voteShare}
              voteIntervals={intervals.vote}
              populationShare={!stateSel ? populationShares() : undefined}
              populationIntervals={intervals.pop}
              stateOptions={stateOpts}
              selectedState={selState}
              onStateChange={setSelState}
              wyoming={wyoming}
              onWyomingChange={onWyomingChange}
            />
          </div>

          {fptpDispro}
        </section>
      </CollapsibleSection>

      <CollapsibleSection id="perstate" title="See how seats change per state"
        hint="Every state's delegation, the list against today's House">
        <StateSeatsTable stateMap={stateMap} wyoming={wyoming} />
      </CollapsibleSection>
    </div>
  );
}

export function Stat({ label, value, tone, note, isCount }: {
  label: string; value: number; tone: 'worst' | 'mid' | 'best'; note?: string; isCount?: boolean;
}) {
  const cls = tone === 'worst' ? 'border-rose-200 bg-rose-50 text-rose-700'
    : tone === 'best' ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
    : 'border-border bg-muted/40 text-foreground';
  return (
    <div className={`rounded-lg border p-3 ${cls}`}>
      <div className="text-2xs text-muted-foreground">{label}{note && <span className="ml-1 opacity-70">· {note}</span>}</div>
      <div className="text-xl font-bold tabular-nums">
        {isCount ? value.toFixed(0) : `${value.toFixed(value >= 10 ? 1 : 2)}%`}
      </div>
    </div>
  );
}

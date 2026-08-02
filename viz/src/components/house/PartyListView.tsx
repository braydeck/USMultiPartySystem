import { useMemo, type ReactNode } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { HouseMap } from './HouseMap';
import { HouseGridChart } from './HouseGridChart';
import { PartyHighlightFilter } from './PartyHighlightFilter';
import { CollapsibleSection } from '../shared/CollapsibleSection';
import { PartyProfileGrid } from '../shared/PartyProfileGrid';
import { UrbSubRurChart } from './UrbSubRurChart';
import { seatTotals } from '../../lib/seatTotals';
import { StateSeatsTable } from './StateSeatsTable';
import { FPTPvsSTV } from './FPTPvsSTV';
import { useUrlState } from '../../hooks/useUrlState';
import { usePartyHighlight } from '../../hooks/usePartyHighlight';
import { F5_ORDER, getPartyColor, PARTY_NAMES } from '../../constants/parties';
import { SeatShareBar as Bar } from './SeatShareBar';
import { PopSeatRanges, type Quantity, type PartyValues, type Span } from './PopSeatRanges';
import { populationShares, voteSharesAt, partyListSharesAt, partyListSeatsAt, type SeatInterval } from '../../lib/uncertainty';
import type { DistrictResult, HouseStateEntry, HouseSeat, ClusterProfile } from '../../types';

type SeatMap = Record<string, number>;
interface Metrics { list: number; stv: number; fptp: number }
interface ListStv { list: number; stv: number }

// Real 2024 U.S. House (computed from district returns, 435 seats):
//   35.8% of voters backed a losing candidate; 14.2% of votes were surplus above 50% for winners.
const CURRENT_UNREPRESENTED = 35.8;
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
  districtCountyMap: Record<string, string[]>;
  /** Double-Wyoming config, for the triple view's double-vs-triple comparison rows. */
  doubleConfig?: PLConfig;
  /** STV seat spans at this turnout stop, present only when the caller's gate holds (rank-7,
   *  double Wyoming). Its presence is what switches the seat-share card from bars to ranges,
   *  because the STV comparison row has no bounds without it. */
  houseU?: Record<string, SeatInterval>;
  /** Turnout stop, index 0-6. */
  gi: number;
  /** Party profiles, shown in the same collapsed section the STV view uses. */
  clusters: ClusterProfile[];
  /** Ideological constellation, built by the tab which owns its inputs. */
  profilesExtra?: ReactNode;
  /** Chamber composition card, built by the tab which owns the factor selector. */
  chamber?: ReactNode;
  /** FPTP-by-state card, which now carries a party-list bar alongside the STV one. */
  fptpDispro?: ReactNode;
}

/** Mirrors the STV card's row set, with the two counting rules swapped. */
const LIST_QUANTITIES: Quantity[] = [
  { key: 'pop', label: 'Pop', legend: 'Population', texture: 'pop', optional: true },
  { key: 'votes', label: 'Votes', legend: 'Votes', texture: 'context' },
  { key: 'stv', label: 'STV', legend: 'STV', texture: 'compare', optional: true },
  { key: 'seats', label: 'List', legend: 'List seats', texture: 'primary' },
];

const CLUSTER_OF: Record<string, number> = { CON: 0, LBR: 1, STY: 2, NAT: 3, LIB: 4, POP: 5, CUP: 6, OAO: 7, DSA: 8, PRG: 9 };

export function seatMapToHouseSeats(seatMap: SeatMap): HouseSeat[] {
  return F5_ORDER.map(p => ({
    party: CLUSTER_OF[p], partyName: PARTY_NAMES[p], national: seatMap[p] ?? 0,
    urban: 0, suburban: 0, rural: 0, pctNational: 0, pctPopulation: 0,
  })).filter(s => s.national > 0) as unknown as HouseSeat[];
}

export function PartyListView({ config, wyoming, districtCountyMap, doubleConfig, houseU, gi, clusters, profilesExtra, chamber, fptpDispro }: Props) {
  const [mapView, setMapView] = useUrlState<'map' | 'grid'>('view', 'map', { allowed: ['map', 'grid'] });
  const [selState, setSelState] = useUrlState<string>('plstate', 'national');
  const [mapState, setMapState] = useUrlState<string>('mapstate', 'national');
  const [highlight, setHighlight] = usePartyHighlight();
  const nat = config.national;

  const stateOpts = useMemo(() => [
    { v: 'national', label: 'National' },
    ...Object.entries(config.byState).map(([f, s]) => ({ v: f, label: s.abbr })).sort((a, b) => a.label.localeCompare(b.label)),
  ], [config]);
  const stateSel = selState !== 'national' ? config.byState[selState] : undefined;
  // Active geography for the seat-share chart (national or a single state).
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

  // Seats by density tier. The list config carries densityTier per district, so the
  // same chart the STV view shows can be built here rather than left out.
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

  // HouseSeat[] shaped seats for the FPTP/STV/list chart (only party + national are read).
  const partyListSeats = useMemo(() => seatMapToHouseSeats(nat.listSeats), [nat]);
  const stvSeats = useMemo(() => seatMapToHouseSeats(nat.stvSeats), [nat]);
  const doubleListSeats = useMemo(
    () => (wyoming === 'triple' && doubleConfig ? seatMapToHouseSeats(doubleConfig.national.listSeats) : undefined),
    [wyoming, doubleConfig],
  );

  const total = active.totalSeats || 1;
  const parties = F5_ORDER.filter(p => (active.listSeats[p] ?? 0) > 0 || (active.stvSeats[p] ?? 0) > 0 || (active.voteShare[p] ?? 0) > 0);
  // Everything in share terms (%), with the raw seat count annotated. `voteShare` is the electorate's
  // vote, not the population's: the two differ by up to 4.4pp once turnout weighting is applied, and
  // the range view below carries them as separate rows.
  const votePct = (p: string) => active.voteShare[p] ?? 0;
  const listPct = (p: string) => (active.listSeats[p] ?? 0) / total * 100;
  const stvPct = (p: string) => (active.stvSeats[p] ?? 0) / total * 100;
  const maxPct = Math.max(5, ...parties.flatMap(p => [votePct(p), listPct(p), stvPct(p)]));

  // Range rows: list is primary here, STV the opt-in comparison — the mirror image of the STV
  // view, which shares this component. National only, because the bootstrap has no per-state
  // seat spans; a selected state falls back to bars.
  const { rangeParties, rangeMaxPct } = useMemo(() => {
    if (!houseU || stateSel) return { rangeParties: null, rangeMaxPct: 5 };
    const pop = populationShares();
    const votes = voteSharesAt(gi);
    const listIvs = partyListSharesAt(gi);
    const listPts = partyListSeatsAt(gi);
    if (!votes || !listIvs || !listPts) return { rangeParties: null, rangeMaxPct: 5 };
    // STV bounds are seat counts, so they convert on the STV chamber's own total — the same
    // denominator `stvPct` uses — rather than on the list total.
    const stvTotal = Object.values(nat.stvSeats).reduce((a, b) => a + b, 0) || 1;

    const rows: PartyValues[] = [];
    const his: number[] = [];
    for (const code of F5_ORDER) {
      const pv = pop[code], vv = votes[code], lv = listIvs[code], u = houseU[code];
      if (!pv || !vv || !lv) continue;
      const stvIv: Span | undefined = u
        ? { expected: u.expected / stvTotal * 100, lo: u.lo / stvTotal * 100, hi: u.hi / stvTotal * 100 }
        : undefined;
      rows.push({
        code,
        values: {
          pop: { point: pv.point, iv: pv },
          votes: { point: vv.point, iv: vv },
          stv: u ? { point: (nat.stvSeats[code] ?? 0) / stvTotal * 100, iv: stvIv, seats: nat.stvSeats[code] ?? 0 } : undefined,
          seats: { point: (nat.listSeats[code] ?? 0) / (nat.totalSeats || 1) * 100,
            seats: nat.listSeats[code] ?? 0, iv: lv },
        },
      });
      his.push(pv.hi, vv.hi, lv.hi, stvIv?.hi ?? 0);
    }
    if (!rows.length) return { rangeParties: null, rangeMaxPct: 5 };
    // Every quantity counts toward the ceiling whether or not its row is switched on, so toggling
    // a row does not rescale the axis under the reader.
    return { rangeParties: rows, rangeMaxPct: Math.max(5, Math.max(...his) * 1.02) };
  }, [houseU, gi, stateSel, nat]);

  return (
    <div className="space-y-8">
      {/* FPTP vs STV vs Party list — the hero comparison, mirroring the STV view */}
      <Card className="p-5 border-2 border-indigo-200">
        <FPTPvsSTV
          seats={partyListSeats}
          systemLabel="Party List"
          otherSystemSeats={stvSeats}
          otherSystemLabel="STV"
          doubleSeats={doubleListSeats}
          wyoming={wyoming}
        />
      </Card>

      {/* Same slot, id and content as the STV view, so switching system does not
          reshuffle the page or slam an open section shut. */}
      {/* The two wasted-vote numbers are the headline cost of the current system, not a
          drill-down: a vote that elected nobody and a vote piled on a safe winner are the
          same waste from opposite directions. They read beside the seat comparison. */}
      <div className="grid gap-4 lg:grid-cols-2 items-start">
      {/* Headline: voters left unrepresented */}
      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
          Voters left unrepresented
        </h3>
        <p className="text-xs text-muted-foreground mb-4">Nobody they voted for won a seat.</p>
        <div className="grid grid-cols-3 gap-2">
          <Stat label="Today's House" value={CURRENT_UNREPRESENTED} tone="worst" note="2024" />
          <Stat label="Party list" value={nat.unrepresented.list} tone="mid" />
          <Stat label="STV" value={nat.unrepresented.stv} tone="best" />
        </div>
      </Card>

      {/* Over-quota surplus */}
      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
          Over-quota surplus
        </h3>
        <p className="text-xs text-muted-foreground mb-4">
          Votes above what a winner needed.
        </p>
        <div className="grid grid-cols-3 gap-2">
          <Stat label="Today's House" value={CURRENT_SURPLUS} tone="worst" note="2024" />
          <Stat label="Party list" value={nat.excess.list} tone="mid" note="stranded" />
          <Stat label="STV" value={nat.excess.stv} tone="best" note="transferred" />
        </div>
      </Card>
      </div>

      <CollapsibleSection id="profiles" title="See party profiles" hint="Ten parties, their positions and who they draw from">
        <PartyProfileGrid clusters={clusters} />
        {profilesExtra}
      </CollapsibleSection>

      {chamber}

      {/* State composition — reuse STV components with list results */}
      <Card className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">State Composition</h3>
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

      {/* Seats by District Type */}
      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">
          Seats by District Type
        </h3>
        <p className="text-xs text-muted-foreground mb-3">
          Progressive parties dominate urban seats, conservatives dominate rural, suburbs are contested.
        </p>
        <UrbSubRurChart seats={tierSeats} />
      </Card>

      <CollapsibleSection id="dispro" title="See disproportionality"
        hint="Votes against seats, and how it varies by state">
        <section>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">
            Votes against seats
          </h4>
        <div className="flex items-center justify-end gap-2 mb-1">
          <select value={selState} onChange={e => setSelState(e.target.value)}
            className="rounded-md border border-border bg-card px-2 py-1 text-xs">
            {stateOpts.map(o => <option key={o.v} value={o.v}>{o.label}</option>)}
          </select>
        </div>
        <p className="text-xs text-muted-foreground mb-3">
          {stateSel ? `${stateSel.abbr}. ` : ''}The share of the vote each party wins, against
          the share of the {active.totalSeats} seats it ends up with under the list. Add
          population to see how much of the difference is turnout, or STV — it uses the same
          districts, so what separates the two is only what transferring votes changes.
        </p>
        {rangeParties ? (
          <PopSeatRanges max={rangeMaxPct} parties={rangeParties} quantities={LIST_QUANTITIES} />
        ) : (
          <div className="space-y-3">
            {parties.map(p => {
              const c = getPartyColor(p);
              return (
                <div key={p} className="grid grid-cols-[110px_1fr] items-center gap-2">
                  <span className="text-xs font-medium text-foreground truncate">{PARTY_NAMES[p]}</span>
                  <div className="space-y-0.5">
                    <Bar pct={votePct(p)} max={maxPct} color={c} outline label={`Votes ${votePct(p).toFixed(1)}%`} />
                    <Bar pct={listPct(p)} max={maxPct} color={c} label={`List ${listPct(p).toFixed(1)}% (${active.listSeats[p] ?? 0})`} />
                    <Bar pct={stvPct(p)} max={maxPct} color={c} faded label={`STV ${stvPct(p).toFixed(1)}% (${active.stvSeats[p] ?? 0})`} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
        </section>

        {fptpDispro}
      </CollapsibleSection>

      <CollapsibleSection id="perstate" title="See how seats change per state"
        hint="Every state's delegation, the list against today's House">
        <StateSeatsTable stateMap={stateMap} wyoming={wyoming} />
      </CollapsibleSection>
    </div>
  );
}

function Stat({ label, value, tone, note, isCount }: {
  label: string; value: number; tone: 'worst' | 'mid' | 'best'; note?: string; isCount?: boolean;
}) {
  const cls = tone === 'worst' ? 'border-rose-200 bg-rose-50 text-rose-700'
    : tone === 'best' ? 'border-emerald-200 bg-emerald-50 text-emerald-700'
    : 'border-border bg-muted/40 text-foreground';
  return (
    <div className={`rounded-lg border p-3 ${cls}`}>
      <div className="text-[11px] text-muted-foreground">{label}{note && <span className="ml-1 opacity-70">· {note}</span>}</div>
      <div className="text-2xl font-bold tabular-nums">
        {isCount ? value.toFixed(0) : `${value.toFixed(value >= 10 ? 1 : 2)}%`}
      </div>
    </div>
  );
}

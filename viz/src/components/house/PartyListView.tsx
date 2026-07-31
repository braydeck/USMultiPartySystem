import { useMemo, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { HouseMap } from './HouseMap';
import { HouseGridChart } from './HouseGridChart';
import { PartyHighlightFilter } from './PartyHighlightFilter';
import { seatTotals } from '../../lib/seatTotals';
import { StateSeatsTable } from './StateSeatsTable';
import { FPTPvsSTV } from './FPTPvsSTV';
import { useUrlState } from '../../hooks/useUrlState';
import { F5_ORDER, getPartyColor, PARTY_NAMES } from '../../constants/parties';
import { SeatShareBar as Bar } from './SeatShareBar';
import { PopSeatRanges, type PopSeatRangeRow } from './PopSeatRanges';
import { populationShares, voteSharesAt, partyListSharesAt, partyListSeatsAt, type SeatInterval } from '../../lib/uncertainty';
import type { DistrictResult, HouseStateEntry, HouseSeat } from '../../types';

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
}

const CLUSTER_OF: Record<string, number> = { CON: 0, LBR: 1, STY: 2, NAT: 3, LIB: 4, POP: 5, CUP: 6, OAO: 7, DSA: 8, PRG: 9 };

export function seatMapToHouseSeats(seatMap: SeatMap): HouseSeat[] {
  return F5_ORDER.map(p => ({
    party: CLUSTER_OF[p], partyName: PARTY_NAMES[p], national: seatMap[p] ?? 0,
    urban: 0, suburban: 0, rural: 0, pctNational: 0, pctPopulation: 0,
  })).filter(s => s.national > 0) as unknown as HouseSeat[];
}

export function PartyListView({ config, wyoming, districtCountyMap, doubleConfig, houseU, gi }: Props) {
  const [mapView, setMapView] = useUrlState<'map' | 'grid'>('view', 'map', { allowed: ['map', 'grid'] });
  const [selState, setSelState] = useUrlState<string>('plstate', 'national');
  const [mapState, setMapState] = useUrlState<string>('mapstate', 'national');
  // Shared by the map and the grid, so switching views keeps the coalition you built.
  const [highlight, setHighlight] = useState<ReadonlySet<string>>(new Set());
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
  const { rangeRows, rangeMaxPct } = useMemo(() => {
    if (!houseU || stateSel) return { rangeRows: null, rangeMaxPct: 5 };
    const pop = populationShares();
    const votes = voteSharesAt(gi);
    const listIvs = partyListSharesAt(gi);
    const listPts = partyListSeatsAt(gi);
    if (!votes || !listIvs || !listPts) return { rangeRows: null, rangeMaxPct: 5 };
    // STV bounds are seat counts, so they convert on the STV chamber's own total — the same
    // denominator `stvPct` uses — rather than on the list total.
    const stvTotal = Object.values(nat.stvSeats).reduce((a, b) => a + b, 0) || 1;

    const rows: PopSeatRangeRow[] = [];
    for (const code of F5_ORDER) {
      const pv = pop[code], vv = votes[code], lv = listIvs[code], u = houseU[code];
      if (!pv || !vv || !lv) continue;
      rows.push({
        code, popIv: pv, voteIv: vv,
        cmpIv: u
          ? { point: (nat.stvSeats[code] ?? 0) / stvTotal * 100, expected: u.expected / stvTotal * 100,
              lo: u.lo / stvTotal * 100, hi: u.hi / stvTotal * 100 }
          : undefined,
        cmpSeats: u ? (nat.stvSeats[code] ?? 0) : undefined,
        seatPct: (nat.listSeats[code] ?? 0) / (nat.totalSeats || 1) * 100,
        seats: nat.listSeats[code] ?? 0,
        seatIv: lv,
      });
    }
    if (!rows.length) return { rangeRows: null, rangeMaxPct: 5 };
    // Every quantity counts toward the ceiling whether or not its row is switched on, so toggling
    // a row does not rescale the axis under the reader.
    const ceil = Math.max(...rows.flatMap(r =>
      [r.popIv.hi, r.voteIv.hi, r.cmpIv?.hi ?? 0, r.seatIv.hi])) * 1.02;
    return { rangeRows: rows, rangeMaxPct: Math.max(5, ceil) };
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

      {/* Seat share vs population share, party list vs STV */}
      <Card className="p-5 border-2 border-indigo-200">
        <div className="flex items-center justify-between gap-2 mb-1">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">
            {rangeRows ? 'Votes vs seat share' : 'Vote vs seat share'}
          </h3>
          <select value={selState} onChange={e => setSelState(e.target.value)}
            className="rounded-md border border-border bg-card px-2 py-1 text-xs">
            {stateOpts.map(o => <option key={o.v} value={o.v}>{o.label}</option>)}
          </select>
        </div>
        <p className="text-xs text-muted-foreground mb-3">
          {stateSel ? `${stateSel.abbr}. ` : ''}What each party earns against what it wins under the
          list, out of {active.totalSeats} seats. Add population to see the turnout step, or STV to
          see what transferable voting changes on the same districts.
        </p>
        {rangeRows ? (
          <PopSeatRanges rows={rangeRows} max={rangeMaxPct} seatLabel="List" compareLabel="STV" />
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
        <p className="text-[11px] text-muted-foreground mt-3">
          Party-list seats use the Hare quota with largest remainders, within the same multi-member districts as STV. There is no legal threshold: winning a seat takes about one quota, so a party's seats track its vote share times the district's magnitude.
        </p>
      </Card>

      {/* Headline: voters left unrepresented */}
      <Card className="p-5 border-2 border-indigo-200">
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

      {/* State composition — reuse STV components with list results */}
      <Card className="p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">State Composition — party list</h3>
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
        <StateSeatsTable stateMap={stateMap} wyoming={wyoming} />
      </Card>
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

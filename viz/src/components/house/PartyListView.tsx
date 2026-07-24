import { useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { HouseMap } from './HouseMap';
import { HouseGridChart } from './HouseGridChart';
import { StateSeatsTable } from './StateSeatsTable';
import { FPTPvsSTV } from './FPTPvsSTV';
import { useUrlState } from '../../hooks/useUrlState';
import { F5_ORDER, getPartyColor, PARTY_NAMES } from '../../constants/parties';
import { SeatShareBar as Bar } from './SeatShareBar';
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
}

const CLUSTER_OF: Record<string, number> = { CON: 0, LBR: 1, STY: 2, NAT: 3, LIB: 4, POP: 5, CUP: 6, OAO: 7, DSA: 8, PRG: 9 };

export function PartyListView({ config, wyoming, districtCountyMap }: Props) {
  const [mapView, setMapView] = useUrlState<'map' | 'grid'>('view', 'map', { allowed: ['map', 'grid'] });
  const [selState, setSelState] = useUrlState<string>('plstate', 'national');
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

  const stateMap = useMemo(() => {
    const out: Record<string, HouseStateEntry> = {};
    for (const [fips, s] of Object.entries(config.byState)) {
      const plurality = Object.entries(s.listSeats).sort((a, b) => b[1] - a[1])[0]?.[0] ?? '';
      out[fips] = { stateAbbr: s.abbr, pluralityParty: plurality, totalSeats: s.totalSeats,
        seats: s.listSeats, popShares: s.voteShare } as unknown as HouseStateEntry;
    }
    return out;
  }, [config]);

  // HouseSeat[] shaped party-list seats for the FPTP-vs-list chart (only party + national are read).
  const partyListSeats = useMemo<HouseSeat[]>(() =>
    F5_ORDER.map(p => ({
      party: CLUSTER_OF[p], partyName: PARTY_NAMES[p], national: nat.listSeats[p] ?? 0,
      urban: 0, suburban: 0, rural: 0, pctNational: 0, pctPopulation: 0,
    })).filter(s => s.national > 0) as unknown as HouseSeat[],
  [nat]);

  const total = active.totalSeats || 1;
  const parties = F5_ORDER.filter(p => (active.listSeats[p] ?? 0) > 0 || (active.stvSeats[p] ?? 0) > 0 || (active.voteShare[p] ?? 0) > 0);
  // Everything in share terms (%), with the raw seat count annotated.
  const popPct = (p: string) => active.voteShare[p] ?? 0;
  const listPct = (p: string) => (active.listSeats[p] ?? 0) / total * 100;
  const stvPct = (p: string) => (active.stvSeats[p] ?? 0) / total * 100;
  const maxPct = Math.max(5, ...parties.flatMap(p => [popPct(p), listPct(p), stvPct(p)]));

  return (
    <div className="space-y-8">
      {/* Seat share vs population share, party list vs STV */}
      <Card className="p-5 border-2 border-indigo-200">
        <div className="flex items-center justify-between gap-2 mb-1">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">
            Population vs seat share
          </h3>
          <select value={selState} onChange={e => setSelState(e.target.value)}
            className="rounded-md border border-border bg-card px-2 py-1 text-xs">
            {stateOpts.map(o => <option key={o.v} value={o.v}>{o.label}</option>)}
          </select>
        </div>
        <p className="text-xs text-muted-foreground mb-4">
          {stateSel ? `${stateSel.abbr}. ` : ''}Outline: population share. Solid: party list. Hollow: STV. Percent is seat share, parentheses are seats.
        </p>
        <div className="space-y-3">
          {parties.map(p => {
            const c = getPartyColor(p);
            return (
              <div key={p} className="grid grid-cols-[110px_1fr] items-center gap-2">
                <span className="text-xs font-medium text-foreground truncate">{PARTY_NAMES[p]}</span>
                <div className="space-y-0.5">
                  <Bar pct={popPct(p)} max={maxPct} color={c} outline label={`Population ${popPct(p).toFixed(1)}%`} />
                  <Bar pct={listPct(p)} max={maxPct} color={c} label={`List ${listPct(p).toFixed(1)}% (${active.listSeats[p] ?? 0})`} />
                  <Bar pct={stvPct(p)} max={maxPct} color={c} faded label={`STV ${stvPct(p).toFixed(1)}% (${active.stvSeats[p] ?? 0})`} />
                </div>
              </div>
            );
          })}
        </div>
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

      {/* FPTP vs Party list — the hero comparison, mirroring the STV view */}
      <Card className="p-5 border-2 border-indigo-200">
        <FPTPvsSTV seats={partyListSeats} wyoming={wyoming} systemLabel="Party list" />
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
        {mapView === 'map'
          ? <HouseMap districtResults={districtResults} districtCountyMap={districtCountyMap} />
          : <HouseGridChart stateMap={stateMap} districtResults={districtResults} />}
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

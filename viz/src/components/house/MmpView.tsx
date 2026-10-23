import { useMemo, useState, type ReactNode } from 'react';
import { Card } from '@/components/ui/card';
import { FPTPvsSTV } from './FPTPvsSTV';
import { Stat, seatMapToHouseSeats } from './PartyListView';
import type { PLConfig } from './PartyListView';
import type { ReserveNational } from './ReserveView';
import { UrbSubRurChart } from './UrbSubRurChart';
import { MmpMap } from './MmpMap';
import { HouseGridChart } from './HouseGridChart';
import { Button } from '@/components/ui/button';
import { PartyHighlightFilter } from './PartyHighlightFilter';
import { StateDrilldown, StateSelect, US_STATES, type DrilldownGroup } from './StateDrilldown';
import { usePartyHighlight } from '../../hooks/usePartyHighlight';
import { CollapsibleSection } from '../shared/CollapsibleSection';
import { PartyProfileGrid } from '../shared/PartyProfileGrid';
import { VotesVsSeats, type SystemEntry } from '../shared/VotesVsSeats';
import { useUrlState } from '../../hooks/useUrlState';
import { getBlendColor, PARTY_NAMES, CLUSTER_TO_PARTY, F5_ORDER } from '../../constants/parties';
import type { ClusterProfile, DistrictResult, HouseSeat } from '../../types';
import {
  CARD_HEADING, MINOR_HEADING, CARD_HINT, TABLE_HEADER,
} from '../../constants/typography';
import { RepresentedByChoice } from './RepresentedByChoice';

export type SeatMap = Record<string, number>;

export interface MmpNational {
  totalSeats: number;
  districtTotal: number;
  topoffTotal: number;
  voteShare: SeatMap;
  districtSeats: SeatMap;
  topoffSeats: SeatMap;
  mmpSeats: SeatMap;
  overhang: number;
  unrepresented: number;
  gallagher: { mmp: number; districtOnly: number };
  softCoverage: number;
  excess?: number;
  districtTiers?: { urban: SeatMap; suburban: SeatMap; rural: SeatMap };
}

export interface MmpStateRow {
  abbr: string;
  totalSeats: number;
  districtCount: number;
  voteShare: SeatMap;
  districtSeats: SeatMap;
  topoffSeats: SeatMap;
  mmpSeats: SeatMap;
  overhang: number;
  unrepresented: number;
  softCoverage: number;
}

export interface MmpConfig {
  national: MmpNational;
  byState: Record<string, MmpStateRow>;
  districts: Record<string, Record<string, {
    winner: string; densityTier?: string; nRespondents: number; winnerShare: number;
  }>>;
}

interface Props {
  config: MmpConfig;
  national: MmpNational;
  wyoming: 'double' | 'triple';
  onWyomingChange?: (w: 'double' | 'triple') => void;
  doubleConfig?: MmpConfig;
  pl?: PLConfig;
  reserveNat?: ReserveNational;
  clusters: ClusterProfile[];
  profilesExtra?: ReactNode;
  chamber?: ReactNode;
}

const name = (p: string) => PARTY_NAMES[p] ?? p;
const pct1 = (x: number) => x.toFixed(1);
const topoffFill = (party: string) => ({ backgroundColor: getBlendColor(party), opacity: 0.42 });
const CLUSTER_OF: Record<string, number> = Object.fromEntries(
  Object.entries(CLUSTER_TO_PARTY).map(([k, v]) => [v, Number(k)]));

export function MmpView({ config, national, wyoming, onWyomingChange, doubleConfig, pl, reserveNat, clusters, profilesExtra, chamber }: Props) {
  const [sort, setSort] = useState<'size' | 'overhang'>('overhang');
  const [selState, setSelState] = useUrlState<string>('mapstate', 'national');
  const nat = config?.national ?? national;

  // The map needs one winner per real district, and the top-off counts per state.
  const districtWinner = useMemo(() => {
    const out: Record<string, string> = {};
    for (const st of Object.values(config?.districts ?? {})) {
      for (const [did, d] of Object.entries(st)) out[did] = d.winner;
    }
    return out;
  }, [config]);
  const [highlight, setHighlight] = usePartyHighlight();
  const [mapView, setMapView] = useUrlState<'map' | 'grid'>('view', 'map', { allowed: ['map', 'grid'] });

  // The grid wants rows of seats. MMP's districts are one seat each, so a row per district
  // would stack California 52 high; winners are grouped by density tier instead, with the
  // state's top-off seats as a last, statewide row.
  const gridRows = useMemo((): Record<string, DistrictResult[]> => {
    const out: Record<string, DistrictResult[]> = {};
    for (const [fips, st] of Object.entries(config?.byState ?? {})) {
      const byTier: Record<string, string[]> = { URBAN: [], SUBURBAN: [], RURAL: [] };
      for (const d of Object.values(config?.districts?.[fips] ?? {})) {
        (byTier[d.densityTier ?? 'SUBURBAN'] ??= []).push(d.winner);
      }
      const rows: DistrictResult[] = (['URBAN', 'SUBURBAN', 'RURAL'] as const)
        .filter(t => byTier[t].length)
        .map(t => ({ districtId: `${fips}-${t}`, densityTier: t, seatCount: byTier[t].length,
          elected: byTier[t], nRespondents: 0 }));
      const top = F5_ORDER.flatMap(p => Array(st.topoffSeats[p] ?? 0).fill(p) as string[]);
      if (top.length) rows.push({ districtId: `${fips}-TOP`, densityTier: 'STATEWIDE',
        seatCount: top.length, elected: top, nRespondents: 0 });
      out[fips] = rows;
    }
    return out;
  }, [config]);

  // Seat totals for the highlight pills: every district winner plus every top-off seat.
  const mapTotals = useMemo(() => {
    const per: Record<string, number> = {};
    for (const st of Object.values(config?.districts ?? {})) {
      for (const d of Object.values(st)) per[d.winner] = (per[d.winner] ?? 0) + 1;
    }
    for (const st of Object.values(config?.byState ?? {})) {
      for (const [p, n] of Object.entries(st.topoffSeats)) per[p] = (per[p] ?? 0) + n;
    }
    return { per, all: Object.values(per).reduce((s, n) => s + n, 0) };
  }, [config]);

  // The drill-down: one card per real district, then the state's top-off seats as one.
  const drillGroups = useMemo((): DrilldownGroup[] => {
    if (selState === 'national') return [];
    const dists = config?.districts?.[selState] ?? {};
    const out: DrilldownGroup[] = Object.entries(dists).sort(([a], [b]) => a.localeCompare(b))
      .map(([id, d]) => ({ id, densityTier: d.densityTier ?? 'SUBURBAN', seatCount: 1,
        elected: [d.winner], nRespondents: d.nRespondents }));
    const top = config?.byState?.[selState]?.topoffSeats ?? {};
    const elected = F5_ORDER.flatMap(p => Array(top[p] ?? 0).fill(p) as string[]);
    if (elected.length) {
      out.push({ id: `${selState}-TOP`, densityTier: 'STATEWIDE', seatCount: elected.length,
        elected, label: 'Statewide top-off' });
    }
    return out;
  }, [config, selState]);

  const abbrByFips = useMemo(() => Object.fromEntries(US_STATES.map(s => [s.fips, s.abbr])), []);
  const fipsByAbbr = useMemo(() => Object.fromEntries(US_STATES.map(s => [s.abbr, s.fips])), []);

  const topoffByState = useMemo(
    () => Object.fromEntries(Object.entries(config?.byState ?? {})
      .map(([fips, st]) => [fips, st.topoffSeats])),
    [config]);

  const stateSel = selState !== 'national' ? config?.byState?.[selState] : undefined;
  const plSel = stateSel && pl ? pl.byState[selState] : undefined;

  // Memoised on its own inputs: as a bare object literal this was a new reference every render,
  // so the useMemo keyed on it below recomputed every time and memoised nothing.
  const active = useMemo(() => (stateSel
    ? { voteShare: stateSel.voteShare, mmpSeats: stateSel.mmpSeats, districtSeats: stateSel.districtSeats,
        totalSeats: stateSel.totalSeats, listSeats: plSel?.listSeats, stvSeats: plSel?.stvSeats,
        otherTotal: plSel?.totalSeats }
    : { voteShare: nat.voteShare, mmpSeats: nat.mmpSeats, districtSeats: nat.districtSeats,
        totalSeats: nat.totalSeats, listSeats: pl?.national.listSeats, stvSeats: pl?.national.stvSeats,
        otherTotal: pl?.national.totalSeats }), [stateSel, plSel, nat, pl]);

  const mmpSeats = useMemo(() => seatMapToHouseSeats(nat.mmpSeats), [nat]);
  const doubleMmpSeats = useMemo(
    () => (doubleConfig ? seatMapToHouseSeats(doubleConfig.national.mmpSeats) : undefined),
    [doubleConfig]);

  const districtTierSeats = useMemo((): HouseSeat[] | undefined => {
    const dt = nat.districtTiers;
    if (!dt) return undefined;
    return F5_ORDER.map(p => {
      const u = dt.urban[p] ?? 0, s = dt.suburban[p] ?? 0, r = dt.rural[p] ?? 0;
      return { party: CLUSTER_OF[p], partyName: PARTY_NAMES[p], national: u + s + r,
        urban: u, suburban: s, rural: r, pctNational: 0, pctPopulation: 0 };
    }).filter(s => s.national > 0) as unknown as HouseSeat[];
  }, [nat]);

  const parties = useMemo(
    () => F5_ORDER.filter(p => (nat.mmpSeats[p] ?? 0) > 0 || (nat.voteShare[p] ?? 0) > 0)
      .sort((a, b) => (nat.mmpSeats[b] ?? 0) - (nat.mmpSeats[a] ?? 0)),
    [nat]);

  const states = useMemo(() => {
    const rows = Object.entries(config?.byState ?? {}).map(([fips, s]) => ({ fips, ...s }));
    return rows.sort((a, b) => (sort === 'overhang'
      ? b.overhang - a.overhang || b.totalSeats - a.totalSeats
      : b.totalSeats - a.totalSeats));
  }, [config, sort]);

  const overhangStates = states.filter(s => s.overhang > 0).length;
  const maxSeats = Math.max(...parties.map(p => nat.mmpSeats[p] ?? 0), 1);

  // VotesVsSeats state options and system entries
  const stateOpts = useMemo(() => [
    { value: 'national', label: 'National' },
    ...Object.entries(config?.byState ?? {}).map(([f, st]) => ({ value: f, label: st.abbr }))
      .sort((a, b) => a.label.localeCompare(b.label)),
  ], [config]);

  const vssSystems = useMemo((): SystemEntry[] => {
    const entries: SystemEntry[] = [{
      key: 'mmp', label: 'MMP', texture: 'primary',
      seats: active.mmpSeats, totalSeats: active.totalSeats,
      defaultOn: true,
    }];
    if (active.listSeats && active.otherTotal) {
      entries.push({
        key: 'list', label: 'Party List', texture: 'compare',
        seats: active.listSeats, totalSeats: active.otherTotal,
      });
    }
    if (active.stvSeats && active.otherTotal) {
      entries.push({
        key: 'stv', label: 'STV', texture: 'compare',
        seats: active.stvSeats, totalSeats: active.otherTotal,
      });
    }
    return entries;
  }, [active]);

  return (
    <div className="space-y-8">
      {/* Hero — simplified: FPTP, PR 2-party, MMP only */}
      <Card className="p-5">
        <FPTPvsSTV
          seats={mmpSeats}
          systemLabel="MMP"
          doubleSeats={doubleMmpSeats}
          wyoming={wyoming}
        />
      </Card>

      <Card className="p-4">
        <div className="flex items-center justify-between mb-1">
          <h4 className={CARD_HEADING}>Where the seats are</h4>
          <div className="flex gap-1">
            {([['map', 'Map'], ['grid', 'Grid']] as const).map(([v, label]) => (
              <Button key={v} onClick={() => setMapView(v)}
                variant={mapView === v ? 'default' : 'secondary'} size="sm">{label}</Button>
            ))}
          </div>
        </div>
        <p className={`${CARD_HINT} mb-3`}>
          {nat.districtTotal} seats are won in the real congressional districts and
          {' '}{nat.topoffTotal} are added statewide to top each delegation up, so every state
          appears twice.
        </p>
        <div className="mb-3">
          <PartyHighlightFilter totals={mapTotals} value={highlight} onChange={setHighlight} />
        </div>
        {mapView === 'grid' ? (
          <HouseGridChart stateMap={{}} districtResults={gridRows} highlight={highlight}
            footnote={<>Each square is one seat. Rows group district winners by tier, urban to rural; the dashed row is the state's top-off.</>} />
        ) : <MmpMap
          wyoming={wyoming}
          districtWinner={districtWinner}
          topoffByState={topoffByState}
          highlight={highlight}
          selected={selState !== 'national' ? (abbrByFips[selState] ?? null) : null}
          onSelectState={ab => setSelState(
            fipsByAbbr[ab] === selState ? 'national' : (fipsByAbbr[ab] ?? 'national'))}
          toolbar={<StateSelect value={selState} onChange={setSelState} />}
          footnote={
            <>One hexagon cluster is one seat, states sized by population. Each state is drawn twice:
            the solid outline holds the seats it wins in its districts, the dashed outline the
            seats it is given statewide. Click a
            state to zoom, click it again to zoom back out.</>
          }
        />}
        {selState !== 'national' && (
          <div className="mt-3">
            <StateDrilldown fips={selState} groups={drillGroups} />
          </div>
        )}
      </Card>

      <CollapsibleSection id="profiles" title="See party profiles"
        hint="Ten parties, their positions and who they draw from">
        <PartyProfileGrid clusters={clusters} />
        {profilesExtra}
      </CollapsibleSection>

      {chamber}

      {districtTierSeats && districtTierSeats.length > 0 && (
        <Card className="p-4">
          <h4 className={`${CARD_HEADING} mb-1`}>District Seats by Type</h4>
          <p className={`${CARD_HINT} mb-3`}>
            District-tier wins only ({nat.districtTotal} of {nat.totalSeats} seats). Top-off seats are statewide.
          </p>
          <UrbSubRurChart seats={districtTierSeats} />
        </Card>
      )}

      <CollapsibleSection id="tiers" title="See where each party's seats come from"
        hint="District wins against statewide top-off">
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className={`w-28 sm:w-40 shrink-0 ${TABLE_HEADER}`}>party</span>
            <span className={`w-12 shrink-0 text-right ${TABLE_HEADER}`}>vote</span>
            <span className={`flex-1 min-w-0 ${TABLE_HEADER}`}>seats</span>
            <span className={`w-12 shrink-0 text-right ${TABLE_HEADER}`}>seat</span>
          </div>
          <div className="space-y-1">
            {parties.map(p => {
              const d = nat.districtSeats[p] ?? 0;
              const t = nat.topoffSeats[p] ?? 0;
              const total = d + t;
              const seatPct = total / nat.totalSeats * 100;
              const votePct = nat.voteShare[p] ?? 0;
              const title = `${name(p)}: ${total} seats = ${d} district + ${t} top-off; `
                + `${pct1(votePct)}% of the vote, ${pct1(seatPct)}% of the seats`;
              return (
                <div key={p} className="flex items-center gap-2" title={title}>
                  <span className="w-28 sm:w-40 shrink-0 text-xs font-semibold truncate"
                    style={{ color: getBlendColor(p) }}>{name(p)}</span>
                  <span className="w-12 shrink-0 text-right text-3xs tabular-nums text-muted-foreground">
                    {pct1(votePct)}%
                  </span>
                  <div className="flex-1 min-w-0 h-5 flex items-center">
                    <div className="flex h-full items-stretch" style={{ width: `${total / maxSeats * 100}%` }}>
                      {total > 0 && <>
                        <div className="rounded-l-sm" style={{ width: `${d / total * 100}%`, backgroundColor: getBlendColor(p) }} />
                        <div className="rounded-r-sm" style={{ width: `${t / total * 100}%`, ...topoffFill(p) }} />
                      </>}
                    </div>
                    <span className="ml-1.5 text-3xs tabular-nums text-muted-foreground shrink-0">
                      {d} + {t}
                    </span>
                  </div>
                  <span className="w-12 shrink-0 text-right text-xs tabular-nums font-bold">
                    {pct1(seatPct)}%
                  </span>
                </div>
              );
            })}
          </div>
          <p className={`${CARD_HINT} mt-3 leading-relaxed`}>
            Solid is a seat won in a district, translucent is a seat added by the top-off. A party
            that wins many districts on a modest vote share receives little top-off, because its
            district wins already meet its entitlement.
          </p>
        </Card>
      </CollapsibleSection>

      {/* Disproportionality & method comparison */}
      <CollapsibleSection id="dispro" title="See disproportionality & method comparison"
        hint="Coverage, Gallagher index, and votes against seats across electoral methods">
        <section className="space-y-6">
          {/* Metric cards */}
          <div className="grid gap-4 xl:grid-cols-3">
            <Card className="p-4">
              <h5 className={`${MINOR_HEADING} mb-1`}>Representational coverage</h5>
              <p className={`${CARD_HINT} mb-3`}>Posterior identity on a seated party.</p>
              <div className={`grid gap-2 ${pl ? 'grid-cols-3' : 'grid-cols-1'}`}>
                <Stat label="MMP" value={nat.softCoverage} tone="best" note="per state" />
                {pl && <Stat label={reserveNat ? 'Party list + reserve' : 'Party list'}
                  value={reserveNat ? reserveNat.list.softCoverage.state : pl.national.softCoverage.listState} tone="mid" note="per state" />}
                {pl && <Stat label={reserveNat ? 'STV + reserve' : 'STV'}
                  value={reserveNat ? reserveNat.stv.softCoverage.state : pl.national.softCoverage.stvState} tone="mid" note="per state" />}
              </div>
            </Card>
            <Card className="p-4">
              <h5 className={`${MINOR_HEADING} mb-1`}>Voters left unrepresented</h5>
              <p className={`${CARD_HINT} mb-3`}>Nobody they voted for won a seat.</p>
              <div className="grid grid-cols-2 sm:grid-cols-4 xl:grid-cols-2 gap-2">
                <Stat label="Today's House" value={35.8} tone="worst" note="2024" />
                {pl && <Stat label={reserveNat ? 'Party list + reserve' : 'Party list'}
                  value={reserveNat ? reserveNat.list.unrepresented : pl.national.unrepresented.list} tone="mid" note={reserveNat ? 'state' : 'district'} />}
                <Stat label="MMP" value={nat.unrepresented} tone="mid" note="state" />
                {pl && <Stat label={reserveNat ? 'STV + reserve' : 'STV'}
                  value={reserveNat ? (reserveNat.stv.ballotPathUnrep ?? reserveNat.stv.unrepresented) : pl.national.unrepresented.stv} tone="best" note={reserveNat ? 'state' : 'district'} />}
              </div>
              <p className={`${CARD_HINT} mt-3`}>
                {reserveNat
                  ? 'All three systems are compared at the statewide level.'
                  : "MMP's list is statewide; STV and party list are counted per district."}
              </p>
            </Card>
            <Card className="p-4">
              <h5 className={`${MINOR_HEADING} mb-1`}>Overhang absorbed</h5>
              <p className={`${CARD_HINT} mb-3`}>
                Seats beyond what statewide vote justifies, because a party won more
                districts than its entitlement.
              </p>
              <div className="grid grid-cols-3 gap-2">
                <Stat label="Overhang" value={nat.overhang} tone={nat.overhang ? 'mid' : 'best'}
                  note="seats" isCount />
                <Stat label="States affected" value={overhangStates} tone={overhangStates ? 'mid' : 'best'}
                  note={`of ${states.length}`} isCount />
                <Stat label="Top-off pool" value={nat.topoffTotal} tone="best" note="seats" isCount />
              </div>
              <p className={`${CARD_HINT} mt-3`}>
                The chamber is fixed at {nat.totalSeats} seats: {nat.districtTotal} districts plus{' '}
                {nat.topoffTotal} top-off.
              </p>
            </Card>
          </div>

          <RepresentedByChoice />

          {/* Gallagher index */}
          <div>
            <h5 className={`${MINOR_HEADING} mb-1`}>Gallagher index</h5>
            <p className={`${CARD_HINT} mb-3`}>Lower is closer to proportional.</p>
            {pl ? (
              <div className="grid grid-cols-2 lg:grid-cols-5 gap-2">
                <Stat label="Winner-take-all" value={pl.national.gallagher.fptp} tone="worst"
                  note="drawn map" isCount />
                <Stat label="Current districts" value={nat.gallagher.districtOnly} tone="worst"
                  note="MMP tier 1 alone" isCount />
                <Stat label={reserveNat ? 'STV + reserve' : 'STV'}
                  value={reserveNat ? reserveNat.stv.gallagher : pl.national.gallagher.stv} tone="mid" isCount />
                <Stat label={reserveNat ? 'Party list + reserve' : 'Party list'}
                  value={reserveNat ? reserveNat.list.gallagher : pl.national.gallagher.list} tone="mid" isCount />
                <Stat label="MMP" value={nat.gallagher.mmp} tone="best" isCount />
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-2">
                <Stat label="Current districts" value={nat.gallagher.districtOnly} tone="worst"
                  note="MMP tier 1 alone" isCount />
                <Stat label="MMP" value={nat.gallagher.mmp} tone="best" isCount />
              </div>
            )}
            <p className={`${CARD_HINT} mt-3`}>
              The single-member current map scores {nat.gallagher.districtOnly.toFixed(2)} on its
              own. The drop to {nat.gallagher.mmp.toFixed(2)} is what the statewide top-off corrects.
            </p>
          </div>

          {/* Unified votes-against-seats */}
          <div>
            <h5 className={`${MINOR_HEADING} mb-1`}>Votes against seats</h5>
            <p className={`${CARD_HINT} mb-3`}>
              {stateSel ? `${stateSel.abbr}. ` : ''}The share of the vote each party wins compared
              with the share of the {active.totalSeats} seats it ends up with.
            </p>
            <VotesVsSeats
              systems={vssSystems}
              voteShare={active.voteShare}
              stateOptions={stateOpts}
              selectedState={selState}
              onStateChange={setSelState}
              wyoming={wyoming}
              onWyomingChange={onWyomingChange}
            />
          </div>
        </section>
      </CollapsibleSection>

      <CollapsibleSection id="perstate" title="See how seats change per state"
        hint={`${states.length} delegations, district counts fixed by the current map`}>
        <Card className="overflow-hidden">
          <div className="px-4 py-3 border-b border-border/50 bg-muted flex items-center justify-between gap-3">
            <span className={MINOR_HEADING}>State delegations</span>
            <div className="flex gap-1">
              {(['overhang', 'size'] as const).map(k => (
                <button key={k} onClick={() => setSort(k)}
                  className={`text-2xs px-2 py-1 rounded-sm border ${sort === k
                    ? 'bg-foreground text-background border-foreground'
                    : 'border-border text-muted-foreground hover:bg-muted'}`}>
                  by {k}
                </button>
              ))}
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border/50">
                  <th className={`text-left px-3 py-2 sticky left-0 z-10 bg-card ${TABLE_HEADER}`}>state</th>
                  <th className={`text-right px-2 py-2 ${TABLE_HEADER}`}>seats</th>
                  <th className={`text-right px-2 py-2 ${TABLE_HEADER}`}>districts</th>
                  <th className={`text-right px-2 py-2 ${TABLE_HEADER}`}>top-off</th>
                  <th className={`text-right px-2 py-2 ${TABLE_HEADER}`}>overhang</th>
                  <th className={`text-left px-3 py-2 ${TABLE_HEADER}`}>composition</th>
                </tr>
              </thead>
              <tbody>
                {states.map(s => {
                  const topoff = s.totalSeats - s.districtCount;
                  const seats = F5_ORDER.filter(p => (s.mmpSeats[p] ?? 0) > 0);
                  return (
                    <tr key={s.fips} className="border-b border-border/30 last:border-0">
                      <td className="px-3 py-1.5 font-semibold sticky left-0 z-10 bg-card">{s.abbr}</td>
                      <td className="px-2 py-1.5 text-right tabular-nums">{s.totalSeats}</td>
                      <td className="px-2 py-1.5 text-right tabular-nums text-muted-foreground">{s.districtCount}</td>
                      <td className="px-2 py-1.5 text-right tabular-nums text-muted-foreground">{topoff}</td>
                      <td className={`px-2 py-1.5 text-right tabular-nums ${s.overhang ? 'font-bold text-foreground' : 'text-muted-foreground/50'}`}>
                        {s.overhang || '—'}
                      </td>
                      <td className="px-3 py-1.5">
                        <div className="flex h-3.5 rounded-sm overflow-hidden min-w-32">
                          {seats.map(p => {
                            const d = s.districtSeats[p] ?? 0;
                            const t = s.topoffSeats[p] ?? 0;
                            return (
                              <div key={p} className="flex items-stretch"
                                style={{ width: `${(d + t) / s.totalSeats * 100}%` }}
                                title={`${name(p)}: ${d + t} of ${s.totalSeats} (${d} district + ${t} top-off)`}>
                                <div style={{ width: `${d / (d + t) * 100}%`, backgroundColor: getBlendColor(p) }} />
                                <div style={{ width: `${t / (d + t) * 100}%`, ...topoffFill(p) }} />
                              </div>
                            );
                          })}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      </CollapsibleSection>
    </div>
  );
}

import { useMemo } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { FPTPvsSTV } from './FPTPvsSTV';
import { Stat, seatMapToHouseSeats } from './PartyListView';
import type { PLConfig } from './PartyListView';
import { UrbSubRurChart } from './UrbSubRurChart';
import { CollapsibleSection } from '../shared/CollapsibleSection';
import { VotesVsSeats, type SystemEntry } from '../shared/VotesVsSeats';
import { PartyProfileGrid } from '../shared/PartyProfileGrid';
import { useUrlState, resetUrlParams } from '../../hooks/useUrlState';
import { getBlendColor, PARTY_NAMES, F5_ORDER } from '../../constants/parties';
import type { HouseSeat, ClusterProfile } from '../../types';
import { CARD_HEADING, MINOR_HEADING, CARD_HINT, TABLE_HEADER } from '../../constants/typography';
import type { ReactNode } from 'react';

export type SeatMap = Record<string, number>;

interface SystemBlock {
  seats: SeatMap;
  districtSeats: SeatMap;
  reserveSeats: SeatMap;
  elected: string[];
  gallagher: number;
  gallagherDistrictOnly: number;
  unrepresented: number;
  unrepDistrictOnly: number;
  softCoverage: { district: number; state: number };
  ballotPathUnrep?: number | null;
}

export interface ReserveNational {
  totalSeats: number;
  districtSeats: number;
  reserveSeats: number;
  voteShare: SeatMap;
  list: SystemBlock;
  stv: SystemBlock;
}

export interface ReserveConfig {
  national: ReserveNational;
  byState: Record<string, {
    abbr: string; totalSeats: number; districtSeats: number; reserveSeats: number;
    voteShare: SeatMap; listSeats: SeatMap; stvSeats: SeatMap;
    softCoverage: { listState: number; stvState: number };
  }>;
}

interface Props {
  config: ReserveConfig;
  national: ReserveNational;
  system: 'list' | 'stv';
  wyoming: 'double' | 'triple';
  onWyomingChange?: (w: 'double' | 'triple') => void;
  doubleConfig?: ReserveConfig;
  base?: PLConfig;
  mmpGallagher?: number;
  mmpCoverage?: number;
  mmpUnrep?: number;
  mmpExcess?: number;
  mmpNational?: { seats: SeatMap; totalSeats: number };
  baseSeats?: HouseSeat[];
  clusters: ClusterProfile[];
  profilesExtra?: ReactNode;
  chamber?: ReactNode;
}

const CURRENT_UNREPRESENTED = 35.8;
const CURRENT_COVERAGE = 100 - CURRENT_UNREPRESENTED;
const CURRENT_SURPLUS = 14.2;
const name = (p: string) => PARTY_NAMES[p] ?? p;
const topoffFill = (party: string) => ({ backgroundColor: getBlendColor(party), opacity: 0.42 });

export function ReserveView({ config, national, system, wyoming, onWyomingChange, doubleConfig, base, mmpGallagher, mmpCoverage, mmpUnrep, mmpExcess, mmpNational, baseSeats, clusters, profilesExtra, chamber }: Props) {
  const [selState, setSelState] = useUrlState<string>('mmpstate', 'national');
  const nat = config?.national ?? national;
  const sys = nat[system];
  const other = nat[system === 'list' ? 'stv' : 'list'];
  const sysLabel = system === 'list' ? 'Party list' : 'STV';

  const heroSeats = useMemo(() => seatMapToHouseSeats(sys.seats), [sys]);
  const doubleSeats = useMemo(
    () => doubleConfig ? seatMapToHouseSeats(doubleConfig.national[system].seats) : undefined,
    [doubleConfig, system]);

  const parties = useMemo(
    () => F5_ORDER.filter(p => (sys.seats[p] ?? 0) > 0 || (nat.voteShare[p] ?? 0) > 0)
      .sort((a, b) => (sys.seats[b] ?? 0) - (sys.seats[a] ?? 0)),
    [sys, nat]);

  const maxSeats = Math.max(...parties.map(p => sys.seats[p] ?? 0), 1);

  const stateSel = selState !== 'national' ? config?.byState?.[selState] : undefined;

  const active = stateSel
    ? { voteShare: stateSel.voteShare, totalSeats: stateSel.totalSeats,
        listSeats: stateSel.listSeats, stvSeats: stateSel.stvSeats }
    : { voteShare: nat.voteShare, totalSeats: nat.totalSeats,
        listSeats: nat.list.seats, stvSeats: nat.stv.seats };

  // VotesVsSeats system entries
  const stateOpts = useMemo(() => [
    { value: 'national', label: 'National' },
    ...Object.entries(config?.byState ?? {}).map(([f, s]) => ({ value: f, label: s.abbr }))
      .sort((a, b) => a.label.localeCompare(b.label)),
  ], [config]);

  const vssSystems = useMemo((): SystemEntry[] => {
    const entries: SystemEntry[] = [];
    entries.push({
      key: system === 'list' ? 'listRes' : 'stvRes',
      label: system === 'list' ? 'List + reserve' : 'STV + reserve',
      texture: 'primary',
      seats: system === 'list' ? active.listSeats : active.stvSeats,
      totalSeats: active.totalSeats,
      defaultOn: true,
    });
    entries.push({
      key: system === 'list' ? 'stvRes' : 'listRes',
      label: system === 'list' ? 'STV + reserve' : 'List + reserve',
      texture: 'compare',
      seats: system === 'list' ? active.stvSeats : active.listSeats,
      totalSeats: active.totalSeats,
    });
    // Base (no reserve) from plConfig
    if (base && !stateSel) {
      entries.push({
        key: 'listBase', label: 'List (no reserve)', texture: 'compare',
        seats: base.national.listSeats, totalSeats: base.national.totalSeats,
      });
      entries.push({
        key: 'stvBase', label: 'STV (no reserve)', texture: 'compare',
        seats: base.national.stvSeats, totalSeats: base.national.totalSeats,
      });
    }
    // MMP
    if (mmpNational && !stateSel) {
      entries.push({
        key: 'mmp', label: 'MMP', texture: 'compare',
        seats: mmpNational.seats, totalSeats: mmpNational.totalSeats,
      });
    }
    return entries;
  }, [system, active, base, mmpNational, stateSel]);

  const states = useMemo(() => {
    return Object.entries(config?.byState ?? {})
      .map(([fips, s]) => ({ fips, ...s }))
      .sort((a, b) => b.totalSeats - a.totalSeats);
  }, [config]);

  const baseGallagher = base?.national.gallagher[system === 'list' ? 'list' : 'stv'];

  return (
    <div className="space-y-8">
      {/* Hero — simplified: FPTP, PR 2-party, active system only */}
      <Card className="p-5">
        <FPTPvsSTV
          seats={heroSeats}
          systemLabel={sysLabel === 'Party list' ? 'Party List' : 'STV'}
          doubleSeats={doubleSeats}
          wyoming={wyoming}
        />
      </Card>

      <CollapsibleSection id="profiles" title="See party profiles"
        hint="Ten parties, their positions and who they draw from">
        <PartyProfileGrid clusters={clusters} />
        {profilesExtra}
      </CollapsibleSection>

      {chamber}

      {/* Seats by District Type — from the base (non-reserve) districts */}
      {baseSeats && baseSeats.length > 0 && baseSeats.some(s => s.urban > 0 || s.suburban > 0 || s.rural > 0) && (
        <Card className="p-4">
          <h4 className={`${CARD_HEADING} mb-1`}>Seats by District Type</h4>
          <p className={`${CARD_HINT} mb-3`}>
            District-tier results. Reserve seats are statewide and have no density tier.
          </p>
          <UrbSubRurChart seats={baseSeats} />
        </Card>
      )}

      <Card className="p-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h4 className={`${CARD_HEADING} mb-1`}>How this chamber votes on bills</h4>
          <p className={CARD_HINT}>
            The bill simulator lives on the Legislation tab, where the whipping rules and the
            full bill set are.
          </p>
        </div>
        <Button onClick={() => resetUrlParams({ tab: 'legislation' })}>Open Legislation</Button>
      </Card>

      {/* Disproportionality & method comparison — collapsed */}
      <CollapsibleSection id="dispro" title="See disproportionality & method comparison"
        hint="Coverage, Gallagher index, and votes against seats across electoral methods">
        <section className="space-y-6">
          {/* Metric cards */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card className="p-4">
              <h5 className={`${MINOR_HEADING} mb-1`}>Representational coverage</h5>
              <p className={`${CARD_HINT} mb-3`}>Posterior identity on a seated party.</p>
              <div className={`grid gap-2 ${mmpCoverage != null ? 'grid-cols-4' : 'grid-cols-3'}`}>
                <Stat label="Today's House" value={CURRENT_COVERAGE} tone="worst" note="2024 · binary" />
                <Stat label="List + reserve" value={nat.list.softCoverage.state}
                  tone={nat.list.softCoverage.state >= nat.stv.softCoverage.state ? 'best' : 'mid'} />
                <Stat label="STV + reserve" value={nat.stv.softCoverage.state}
                  tone={nat.stv.softCoverage.state >= nat.list.softCoverage.state ? 'best' : 'mid'} />
                {mmpCoverage != null && <Stat label="MMP" value={mmpCoverage} tone="mid" />}
              </div>
            </Card>
            <Card className="p-4">
              <h5 className={`${MINOR_HEADING} mb-1`}>Voters left unrepresented</h5>
              <p className={`${CARD_HINT} mb-3`}>Nobody they voted for won a seat.</p>
              <div className={`grid gap-2 ${mmpUnrep != null ? 'grid-cols-4' : 'grid-cols-3'}`}>
                <Stat label="Today's House" value={CURRENT_UNREPRESENTED} tone="worst" note="2024" />
                <Stat label="List + reserve" value={nat.list.unrepresented} tone="mid" note="1st choice" />
                <Stat label="STV + reserve" value={nat.stv.ballotPathUnrep ?? nat.stv.unrepresented}
                  tone="best" note="ballot path" />
                {mmpUnrep != null && <Stat label="MMP" value={mmpUnrep} tone="mid" note="1st choice" />}
              </div>
              <p className={`${CARD_HINT} mt-3`}>
                List and MMP count first-choice only. STV counts ballot path: did any of your ranked choices win.
              </p>
            </Card>
            <Card className="p-4">
              <h5 className={`${MINOR_HEADING} mb-1`}>Over-quota surplus</h5>
              <p className={`${CARD_HINT} mb-3`}>Votes above what a winner needed.</p>
              <div className={`grid gap-2 ${mmpExcess != null ? 'grid-cols-4' : 'grid-cols-3'}`}>
                <Stat label="Today's House" value={CURRENT_SURPLUS} tone="worst" note="2024" />
                <Stat label="Party list" value={base?.national.excess?.list ?? 0} tone="mid" note="stranded" />
                <Stat label="STV" value={base?.national.excess?.stv ?? 0} tone="best" note="transferred" />
                {mmpExcess != null && <Stat label="MMP" value={mmpExcess} tone="mid" note="stranded" />}
              </div>
            </Card>
          </div>

          {/* Gallagher index */}
          <div>
            <h5 className={`${MINOR_HEADING} mb-1`}>Gallagher index</h5>
            <p className={`${CARD_HINT} mb-3`}>Lower is closer to proportional.</p>
            <div className={`grid gap-2 ${mmpGallagher != null ? 'grid-cols-3' : 'grid-cols-2'}`}>
              <Stat label="List + reserve" value={nat.list.gallagher}
                tone={nat.list.gallagher <= nat.stv.gallagher ? 'best' : 'mid'} isCount />
              <Stat label="STV + reserve" value={nat.stv.gallagher}
                tone={nat.stv.gallagher <= nat.list.gallagher ? 'best' : 'mid'} isCount />
              {mmpGallagher != null && <Stat label="MMP" value={mmpGallagher} tone="mid" isCount />}
            </div>
            {baseGallagher != null && (
              <p className={`${CARD_HINT} mt-2`}>
                Without reserve: {baseGallagher.toFixed(2)}.
                With reserve: {sys.gallagher.toFixed(2)}.
              </p>
            )}
          </div>

          {/* Unified votes-against-seats */}
          <div>
            <h5 className={`${MINOR_HEADING} mb-1`}>Votes against seats</h5>
            <p className={`${CARD_HINT} mb-3`}>
              {stateSel ? `${stateSel.abbr}. ` : ''}Vote share against seat share, {active.totalSeats} seats.
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

      {/* District/reserve split */}
      <CollapsibleSection id="tiers" title="See where each party's seats come from"
        hint="District wins against statewide reserve">
        <Card className="p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className={`w-28 sm:w-40 shrink-0 ${TABLE_HEADER}`}>party</span>
            <span className={`w-12 shrink-0 text-right ${TABLE_HEADER}`}>vote</span>
            <span className={`flex-1 min-w-0 ${TABLE_HEADER}`}>seats</span>
            <span className={`w-12 shrink-0 text-right ${TABLE_HEADER}`}>seat</span>
          </div>
          <div className="space-y-1">
            {parties.map(p => {
              const d = sys.districtSeats[p] ?? 0;
              const r = sys.reserveSeats[p] ?? 0;
              const total = d + r;
              const seatPct = total / nat.totalSeats * 100;
              const votePct = nat.voteShare[p] ?? 0;
              return (
                <div key={p} className="flex items-center gap-2"
                  title={`${name(p)}: ${total} = ${d} district + ${r} reserve`}>
                  <span className="w-28 sm:w-40 shrink-0 text-xs font-semibold truncate"
                    style={{ color: getBlendColor(p) }}>{name(p)}</span>
                  <span className="w-12 shrink-0 text-right text-3xs tabular-nums text-muted-foreground">
                    {votePct.toFixed(1)}%
                  </span>
                  <div className="flex-1 min-w-0 h-5 flex items-center">
                    <div className="flex h-full items-stretch" style={{ width: `${total / maxSeats * 100}%` }}>
                      {total > 0 && <>
                        <div className="rounded-l-sm" style={{ width: `${d / total * 100}%`, backgroundColor: getBlendColor(p) }} />
                        <div className="rounded-r-sm" style={{ width: `${r / total * 100}%`, ...topoffFill(p) }} />
                      </>}
                    </div>
                    <span className="ml-1.5 text-3xs tabular-nums text-muted-foreground shrink-0">
                      {d} + {r}
                    </span>
                  </div>
                  <span className="w-12 shrink-0 text-right text-xs tabular-nums font-bold">
                    {seatPct.toFixed(1)}%
                  </span>
                </div>
              );
            })}
          </div>
          <p className={`${CARD_HINT} mt-3`}>
            Solid is a seat won in a district, translucent is from the statewide reserve.
          </p>
        </Card>
      </CollapsibleSection>

      {/* State delegations */}
      <CollapsibleSection id="perstate" title="See state delegations"
        hint={`${states.length} states, ~${Math.round(nat.reserveSeats / nat.totalSeats * 100)}% reserve in multi-district states`}>
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border/50">
                  <th className={`text-left px-3 py-2 sticky left-0 z-10 bg-card ${TABLE_HEADER}`}>state</th>
                  <th className={`text-right px-2 py-2 ${TABLE_HEADER}`}>seats</th>
                  <th className={`text-right px-2 py-2 ${TABLE_HEADER}`}>dist</th>
                  <th className={`text-right px-2 py-2 ${TABLE_HEADER}`}>rsv</th>
                  <th className={`text-right px-2 py-2 ${TABLE_HEADER}`}>cov%</th>
                  <th className={`text-left px-3 py-2 ${TABLE_HEADER}`}>{sysLabel} composition</th>
                </tr>
              </thead>
              <tbody>
                {states.map(s => {
                  const sysSeats = system === 'list' ? s.listSeats : s.stvSeats;
                  const cov = s.softCoverage[system === 'list' ? 'listState' : 'stvState'];
                  const seated = F5_ORDER.filter(p => (sysSeats[p] ?? 0) > 0);
                  return (
                    <tr key={s.fips} className="border-b border-border/30 last:border-0">
                      <td className="px-3 py-1.5 font-semibold sticky left-0 z-10 bg-card">{s.abbr}</td>
                      <td className="px-2 py-1.5 text-right tabular-nums">{s.totalSeats}</td>
                      <td className="px-2 py-1.5 text-right tabular-nums text-muted-foreground">{s.districtSeats}</td>
                      <td className="px-2 py-1.5 text-right tabular-nums text-muted-foreground">{s.reserveSeats}</td>
                      <td className="px-2 py-1.5 text-right tabular-nums">{cov.toFixed(1)}</td>
                      <td className="px-3 py-1.5">
                        <div className="flex h-3.5 rounded-sm overflow-hidden min-w-32">
                          {seated.map(p => (
                            <div key={p} style={{ width: `${(sysSeats[p] ?? 0) / s.totalSeats * 100}%`, backgroundColor: getBlendColor(p) }}
                              title={`${name(p)}: ${sysSeats[p]}`} />
                          ))}
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

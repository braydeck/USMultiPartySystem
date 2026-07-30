import { useMemo } from 'react';
import type { HouseSeat, HouseStateEntry } from '../../types';
import { getPartyColor, PARTY_NAMES, F5_ORDER, CLUSTER_TO_PARTY } from '../../constants/parties';
import { SeatShareBar as Bar } from './SeatShareBar';
import type { SeatInterval } from '../../lib/uncertainty';

/** One party's row. Interval fields are percent-of-chamber and only populated in the national
 *  view, where the bootstrap's national seat counts share the row's denominator. */
interface Row {
  code: string;
  popPct: number;
  seatPct: number; seats: number;
  fdPct: number; fdSeats: number;
  dblPct: number; dblSeats: number;
  uLo?: number; uHi?: number; uCentre?: number;
}

interface Props {
  rawMultiSeats: HouseSeat[];
  fdSeats: HouseSeat[];
  scenario: 'rawMulti' | 'factorDev';
  doubleSeats?: HouseSeat[];
  doubleFdSeats?: HouseSeat[];
  wyoming?: 'double' | 'triple';
  stateMap: Record<string, HouseStateEntry>;
  doubleStateMap?: Record<string, HouseStateEntry>;
  selectedState: string;
  onStateChange: (state: string) => void;
  houseU?: Record<string, SeatInterval>;
}

export function ScenarioComparison({ rawMultiSeats, fdSeats, scenario, doubleSeats, doubleFdSeats, wyoming = 'double', stateMap, doubleStateMap, selectedState, onStateChange, houseU }: Props) {
  const isNational = selectedState === 'national';

  const stateOpts = useMemo(() => [
    { v: 'national', label: 'National' },
    ...Object.values(stateMap).map(e => ({ v: e.stateAbbr, label: e.stateAbbr }))
      .sort((a, b) => a.label.localeCompare(b.label)),
  ], [stateMap]);

  const { rows, maxPct, showFD, showDouble } = useMemo(() => {
    const showFD = scenario === 'factorDev';
    const showDbl = wyoming === 'triple' && !!doubleSeats && doubleSeats.length > 0;

    if (isNational) {
      const rmTotal = rawMultiSeats.reduce((s, r) => s + r.national, 0) || 1;
      const fdTotal = fdSeats.reduce((s, r) => s + r.national, 0) || 1;
      const dblArr = showDbl ? (showFD && doubleFdSeats ? doubleFdSeats : doubleSeats!) : [];
      const dblTotal = dblArr.reduce((s, r) => s + r.national, 0) || 1;

      const rows: Row[] = F5_ORDER.map(code => {
        const rm = rawMultiSeats.find(s => CLUSTER_TO_PARTY[String(s.party)] === code);
        const fd = fdSeats.find(s => CLUSTER_TO_PARTY[String(s.party)] === code);
        const dbl = dblArr.find(s => CLUSTER_TO_PARTY[String(s.party)] === code);
        // Bootstrap bounds are seat counts, so they convert on rmTotal — the same denominator
        // this row's seatPct came from.
        const u = houseU?.[code];
        return {
          code,
          popPct: rm?.pctPopulation ?? fd?.pctPopulation ?? 0,
          seatPct: rm ? rm.national / rmTotal * 100 : 0, seats: rm?.national ?? 0,
          fdPct: fd ? fd.national / fdTotal * 100 : 0, fdSeats: fd?.national ?? 0,
          dblPct: dbl ? dbl.national / dblTotal * 100 : 0, dblSeats: dbl?.national ?? 0,
          uLo: u ? u.lo / rmTotal * 100 : undefined,
          uHi: u ? u.hi / rmTotal * 100 : undefined,
          uCentre: u ? u.expected / rmTotal * 100 : undefined,
        };
      }).filter(r => r.popPct > 0 || r.seatPct > 0 || r.fdPct > 0);
      // The axis has to clear the widest sampling bound — the leading party's upper bound sits
      // past its own seat share — plus a hair of headroom, or that bound's 1px end cap lands on
      // the track's clipping edge and disappears.
      const uCeil = Math.max(...rows.map(r => r.uHi ?? 0)) * 1.02;
      const maxPct = Math.max(5, uCeil, ...rows.flatMap(r => [r.popPct, r.seatPct, r.fdPct, r.dblPct]));
      return { rows, maxPct, showFD, showDouble: showDbl };
    }

    // State-level view
    const fips = Object.entries(stateMap).find(([, v]) => v.stateAbbr === selectedState)?.[0] ?? '';
    const entry = stateMap[fips];
    const dblEntry = doubleStateMap?.[fips];
    if (!entry) return { rows: [], maxPct: 5, showFD: false, showDouble: showDbl };
    const totalSeats = entry.totalSeats || 1;
    const dblTotalSeats = dblEntry?.totalSeats || 1;
    const popShares = entry.popShares ?? dblEntry?.popShares ?? {};
    // No per-state bootstrap, so state rows carry no interval and the bars render bare.
    const rows: Row[] = F5_ORDER.map(code => {
      const seats = entry.seats[code] ?? 0;
      const dblSeats = dblEntry?.seats?.[code] ?? 0;
      return {
        code,
        popPct: popShares[code] ?? 0,
        seatPct: seats / totalSeats * 100, seats,
        fdPct: 0, fdSeats: 0,
        dblPct: dblSeats / dblTotalSeats * 100, dblSeats,
      };
    }).filter(r => r.popPct > 0 || r.seatPct > 0 || r.dblPct > 0);
    const maxPct = Math.max(5, ...rows.flatMap(r => [r.popPct, r.seatPct, r.dblPct]));
    return { rows, maxPct, showFD: false, showDouble: showDbl };
  }, [selectedState, isNational, rawMultiSeats, fdSeats, scenario, wyoming, doubleSeats, doubleFdSeats, stateMap, doubleStateMap, houseU]);

  const seatLabel = wyoming === 'triple' ? 'Triple' : 'STV';
  const hasWhiskers = rows.some(r => r.uHi != null);

  return (
    <div>
      <div className="flex items-center justify-between gap-2 mb-1">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">
          Population vs seat share
        </h3>
        <select value={isNational ? 'national' : selectedState}
          onChange={e => onStateChange(e.target.value === 'national' ? 'national' : e.target.value)}
          className="rounded-md border border-border bg-card px-2 py-1 text-xs">
          {stateOpts.map(o => <option key={o.v} value={o.v}>{o.label}</option>)}
        </select>
      </div>
      <p className="text-xs text-muted-foreground mb-4">
        {isNational ? '' : `${selectedState}. `}Outline: population share. Solid: {seatLabel} seat share.
        {showDouble && ' Faded: double-Wyoming (873).'}{showFD && ' Dashed: Crossover.'} Percent is seat share, parentheses are seats.
        {hasWhiskers && ' Whisker on the seat bar: the range across 1,000 resamples, dot at the expected share.'}
      </p>
      <div className="space-y-3">
        {rows.map(r => {
          const c = getPartyColor(r.code);
          return (
            <div key={r.code} className="grid grid-cols-[110px_1fr] items-center gap-2">
              <span className="text-xs font-medium text-foreground truncate">{PARTY_NAMES[r.code]}</span>
              <div className="space-y-0.5">
                <Bar pct={r.popPct} max={maxPct} color={c} outline label={`Population ${r.popPct.toFixed(1)}%`} />
                <Bar pct={r.seatPct} max={maxPct} color={c} label={`${seatLabel} ${r.seatPct.toFixed(1)}% (${r.seats})`}
                  lo={r.uLo} hi={r.uHi} centre={r.uCentre} />
                {showDouble && <Bar pct={r.dblPct} max={maxPct} color={c} faded label={`Double ${r.dblPct.toFixed(1)}% (${r.dblSeats})`} />}
                {showFD && <Bar pct={r.fdPct} max={maxPct} color={c} dashed label={`Crossover ${r.fdPct.toFixed(1)}% (${r.fdSeats})`} />}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

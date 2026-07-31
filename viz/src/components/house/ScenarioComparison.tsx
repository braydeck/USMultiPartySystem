import { useMemo } from 'react';
import type { HouseSeat, HouseStateEntry } from '../../types';
import { F5_ORDER, CLUSTER_TO_PARTY } from '../../constants/parties';
import { PopSeatRanges, type Quantity, type PartyValues, type Span } from './PopSeatRanges';
import { populationShares, voteSharesAt, partyListSharesAt, partyListSeatsAt, type SeatInterval, type ShareInterval } from '../../lib/uncertainty';

/** One party's row. Interval fields are only populated in the national view, where the
 *  bootstrap's national seat counts share the row's denominator. */
interface Row {
  code: string;
  popPct: number;
  seatPct: number; seats: number;
  fdPct: number; fdSeats: number;
  dblPct: number; dblSeats: number;
  /** Percent-of-chamber sampling span, converted on the row's own seat denominator. */
  seatIv?: Span;
  /** Percent-of-population span and point. One payload for every turnout stop: population share
   *  is weighted by the survey weight alone, never by turnout, because it describes the
   *  population rather than the electorate. The vote and seat spans are turnout-weighted and do
   *  move — that asymmetry is where the turnout effect comes from, not a bug. */
  popIv?: ShareInterval;
  /** Percent-of-national-vote span and point at this turnout stop. Both come from the same
   *  payload, so tick and band are one computation. The card's district-aggregated vote share
   *  differs from this national figure by at most 0.16pp against 0.6-1.1pp interval widths, and
   *  mixing the two sources is the mistake this row exists to avoid. */
  voteIv?: ShareInterval;
  /** Percent-of-chamber span under party-list PR at this turnout stop, on the STV row's
   *  denominator, plus the seat count for the readout. */
  cmpIv?: ShareInterval;
  cmpSeats?: number;
}

// Static: population share does not vary by turnout stop, so this needs no hook.
const POP_IVS = populationShares();

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
  /** Turnout stop, index 0-6. Only the vote spans need it; population is stop-invariant. */
  gi: number;
}

export function ScenarioComparison({ rawMultiSeats, fdSeats, scenario, doubleSeats, doubleFdSeats, wyoming = 'double', stateMap, doubleStateMap, selectedState, onStateChange, houseU, gi }: Props) {
  const isNational = selectedState === 'national';

  const stateOpts = useMemo(() => [
    { v: 'national', label: 'National' },
    ...Object.values(stateMap).map(e => ({ v: e.stateAbbr, label: e.stateAbbr }))
      .sort((a, b) => a.label.localeCompare(b.label)),
  ], [stateMap]);

  const { rows, maxPct, rangeMaxPct, showFD, showDouble } = useMemo(() => {
    const showFD = scenario === 'factorDev';
    const showDbl = wyoming === 'triple' && !!doubleSeats && doubleSeats.length > 0;

    if (isNational) {
      const rmTotal = rawMultiSeats.reduce((s, r) => s + r.national, 0) || 1;
      const fdTotal = fdSeats.reduce((s, r) => s + r.national, 0) || 1;
      const dblArr = showDbl ? (showFD && doubleFdSeats ? doubleFdSeats : doubleSeats!) : [];
      const dblTotal = dblArr.reduce((s, r) => s + r.national, 0) || 1;

      const voteIvs = houseU ? voteSharesAt(gi) : undefined;
      const listIvs = houseU ? partyListSharesAt(gi) : undefined;
      const listSeats = houseU ? partyListSeatsAt(gi) : undefined;
      const rows: Row[] = F5_ORDER.map(code => {
        const rm = rawMultiSeats.find(s => CLUSTER_TO_PARTY[String(s.party)] === code);
        const fd = fdSeats.find(s => CLUSTER_TO_PARTY[String(s.party)] === code);
        const dbl = dblArr.find(s => CLUSTER_TO_PARTY[String(s.party)] === code);
        // Bootstrap bounds are seat counts, so they convert on rmTotal — the same denominator
        // this row's seatPct came from. Population and vote bounds arrive already in percent.
        const u = houseU?.[code];
        const pop = houseU ? POP_IVS[code] : undefined;
        return {
          code,
          popPct: rm?.pctPopulation ?? fd?.pctPopulation ?? 0,
          seatPct: rm ? rm.national / rmTotal * 100 : 0, seats: rm?.national ?? 0,
          fdPct: fd ? fd.national / fdTotal * 100 : 0, fdSeats: fd?.national ?? 0,
          dblPct: dbl ? dbl.national / dblTotal * 100 : 0, dblSeats: dbl?.national ?? 0,
          seatIv: u
            ? { lo: u.lo / rmTotal * 100, hi: u.hi / rmTotal * 100, expected: u.expected / rmTotal * 100 }
            : undefined,
          popIv: pop,
          voteIv: voteIvs?.[code],
          cmpIv: listIvs?.[code],
          cmpSeats: listSeats?.[code]?.point,
        };
      }).filter(r => r.popPct > 0 || r.seatPct > 0 || r.fdPct > 0);
      // The axis has to clear the widest sampling bound — the leading party's upper bound sits
      // past its own seat share — plus a hair of headroom, or that bound's 1px end cap lands on
      // the track's clipping edge and disappears.
      // Every quantity counts toward the ceiling whether or not its row is switched on, so the
      // axis holds still when a row is toggled rather than rescaling under the reader.
      const uCeil = Math.max(0, ...rows.flatMap(
        r => [r.seatIv?.hi ?? 0, r.popIv?.hi ?? 0, r.voteIv?.hi ?? 0, r.cmpIv?.hi ?? 0])) * 1.02;
      const maxPct = Math.max(5, uCeil, ...rows.flatMap(r => [r.popPct, r.seatPct, r.fdPct, r.dblPct]));
      // The range view never draws Crossover or double-Wyoming, so its axis ignores those two
      // bar-only quantities. Crossover's leading share runs well past any STV bound and would
      // otherwise squeeze every span into the left two-thirds of the track.
      const rangeMaxPct = Math.max(5, uCeil,
        ...rows.flatMap(r => [r.popIv?.point ?? 0, r.voteIv?.point ?? 0, r.cmpIv?.point ?? 0, r.seatPct]));
      return { rows, maxPct, rangeMaxPct, showFD, showDouble: showDbl };
    }

    // State-level view
    const fips = Object.entries(stateMap).find(([, v]) => v.stateAbbr === selectedState)?.[0] ?? '';
    const entry = stateMap[fips];
    const dblEntry = doubleStateMap?.[fips];
    if (!entry) return { rows: [], maxPct: 5, rangeMaxPct: 5, showFD: false, showDouble: showDbl };
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
    return { rows, maxPct, rangeMaxPct: maxPct, showFD: false, showDouble: showDbl };
  }, [selectedState, isNational, rawMultiSeats, fdSeats, scenario, wyoming, doubleSeats, doubleFdSeats, stateMap, doubleStateMap, houseU, gi]);

  const seatLabel = wyoming === 'triple' ? 'Triple' : 'STV';
  // Spans only exist for the national bootstrap, and only when neither optional bar is on
  // (Crossover and double-Wyoming have no resampled counterpart). Everywhere else the
  // same bars render without whiskers rather than falling back to a different chart.
  const hasRanges = !showFD && !showDouble
    && rows.length > 0 && rows.every(r => r.popIv && r.voteIv && r.seatIv);
  const hasList = hasRanges && rows.every(r => !!r.cmpIv);

  const quantities: Quantity[] = hasRanges
    ? [
      { key: 'pop', label: 'Pop', legend: 'Population', texture: 'pop', optional: true },
      { key: 'votes', label: 'Votes', legend: 'Votes', texture: 'context' },
      ...(hasList
        ? [{ key: 'list', label: 'Party list', legend: 'Party list', texture: 'compare' as const, optional: true }]
        : []),
      { key: 'seats', label: seatLabel, legend: `${seatLabel} seats`, texture: 'primary' },
    ]
    : [
      { key: 'pop', label: 'Pop', legend: 'Population', texture: 'pop' },
      { key: 'seats', label: seatLabel, legend: `${seatLabel} seats`, texture: 'primary' },
      ...(showDouble ? [{ key: 'dbl', label: 'Double', legend: 'Double Wyoming', texture: 'context' as const }] : []),
      ...(showFD ? [{ key: 'fd', label: 'Crossover', legend: 'Crossover', texture: 'compare' as const }] : []),
    ];

  const parties: PartyValues[] = rows.map(r => ({
    code: r.code,
    values: {
      pop: hasRanges && r.popIv
        ? { point: r.popIv.point, iv: r.popIv }
        : { point: r.popPct },
      votes: r.voteIv ? { point: r.voteIv.point, iv: r.voteIv } : undefined,
      list: r.cmpIv ? { point: r.cmpIv.point, iv: r.cmpIv, seats: r.cmpSeats } : undefined,
      seats: { point: r.seatPct, seats: r.seats, iv: hasRanges ? r.seatIv : undefined },
      dbl: showDouble ? { point: r.dblPct, seats: r.dblSeats } : undefined,
      fd: showFD ? { point: r.fdPct, seats: r.fdSeats } : undefined,
    },
  }));

  return (
    <div>
      <div className="flex items-center justify-between gap-2 mb-1">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest">
          {hasRanges ? 'Votes vs seat share' : 'Population vs seat share'}
        </h3>
        <select value={isNational ? 'national' : selectedState}
          onChange={e => onStateChange(e.target.value === 'national' ? 'national' : e.target.value)}
          className="rounded-md border border-border bg-card px-2 py-1 text-xs">
          {stateOpts.map(o => <option key={o.v} value={o.v}>{o.label}</option>)}
        </select>
      </div>
      <p className="text-xs text-muted-foreground mb-3">
        {isNational ? '' : `${selectedState}. `}
        {hasRanges ? (
          <>
            The share of the vote each party wins, against the share of the seats it ends up
            with. Add population to see how much of the difference is turnout
            {hasList && `, or party list — it uses the same districts as ${seatLabel}, so what
              separates the two is only what transferring votes changes`}.
          </>
        ) : (
          <>
            The share of the population each party speaks for, against the share of the seats it
            wins.{showDouble && ' Double Wyoming is the 873-seat chamber.'}
            {showFD && ' Crossover lets voters back candidates from other parties.'}
            {' '}No sampling ranges at this setting — the resampling only covers the standard run.
          </>
        )}
      </p>
      <PopSeatRanges quantities={quantities} parties={parties}
        max={hasRanges ? rangeMaxPct : maxPct} />
    </div>
  );
}

// Bootstrap sampling uncertainty, one payload per turnout stop. These are bootstrap
// percentile intervals, not credible intervals — see About → Caveats.
import u0 from '../data/uncertaintyTurnout.json';
import u5 from '../data/uncertaintyTurnoutL5.json';
import u10 from '../data/uncertaintyTurnoutL10.json';
import u15 from '../data/uncertaintyTurnoutL15.json';
import u20 from '../data/uncertaintyTurnoutL20.json';
import u25 from '../data/uncertaintyTurnoutL25.json';
import u30 from '../data/uncertaintyTurnoutL30.json';
import popShares from '../data/populationShareRange.json';
import type { SenateIrvRound } from '../types';

export interface SeatInterval {
  modal: number; expected: number; lo: number; hi: number; observed: number;
}

export interface StateUncertainty {
  observed: string;
  modal: string;
  pModal: number;
  pObserved: number;
  dist: Record<string, number>;
  substituted: boolean;
  repRounds?: SenateIrvRound[];
  repShare?: number;
  decomp?: Record<string, { slate: number; final: number; win: number; winIfFinal: number | null }>;
}

export interface MethodUncertainty {
  seats: Record<string, SeatInterval>;
  states: Record<string, StateUncertainty>;
  nSubstituted: number;
  nBelow50: number;
}

export interface UncertaintyData {
  nDraws: number;
  seed: number;
  senate: { cond: MethodUncertainty; irv: MethodUncertainty };
  house: { seats: Record<string, SeatInterval> };
  primary: { slate: Record<string, number>; observedSlate: string[] };
  // nResolved counts draws that produced a winner at all: a Condorcet cycle yields none, so
  // dist is conditional on resolution and the denominator has to stay visible.
  president: Record<'irv' | 'cond',
    { dist: Record<string, number>; observed: string; modal: string; nResolved: number }>;
}

export const UNCERTAINTY_STOPS = [u0, u5, u10, u15, u20, u25, u30] as unknown as UncertaintyData[];

export function uncertaintyAt(gi: number): UncertaintyData | undefined {
  return UNCERTAINTY_STOPS[gi];
}

/** A party's share of the population across resamples, in percent. `point` is the share of the
 *  observed sample, the same number the seat tables report as `pctPopulation`. */
export interface ShareInterval {
  point: number; expected: number; lo: number; hi: number;
}

export interface PopulationShareData {
  nDraws: number;
  seed: number;
  /** True because population share is weighted by `commonpostweight` alone and never by turnout:
   *  it describes the population, not the electorate. Hence one payload for all seven stops,
   *  unlike the seat intervals above, which move with the turnout slider. */
  stopInvariant: boolean;
  shares: Record<string, ShareInterval>;
}

export const POPULATION_SHARE = popShares as unknown as PopulationShareData;

/** Population share spans, keyed by party code. Takes no stop argument on purpose — see
 *  `PopulationShareData.stopInvariant`. */
export function populationShares(): Record<string, ShareInterval> {
  return POPULATION_SHARE.shares;
}

export function chamberTotal(
  seats: Record<string, SeatInterval>,
  key: 'modal' | 'observed',
): number {
  return Object.values(seats).reduce((s, v) => s + v[key], 0);
}

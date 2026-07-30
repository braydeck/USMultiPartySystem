// Bootstrap sampling uncertainty, one payload per turnout stop. These are bootstrap
// percentile intervals, not credible intervals — see About → Caveats.
import u0 from '../data/uncertaintyTurnout.json';
import u5 from '../data/uncertaintyTurnoutL5.json';
import u10 from '../data/uncertaintyTurnoutL10.json';
import u15 from '../data/uncertaintyTurnoutL15.json';
import u20 from '../data/uncertaintyTurnoutL20.json';
import u25 from '../data/uncertaintyTurnoutL25.json';
import u30 from '../data/uncertaintyTurnoutL30.json';
import shareRanges from '../data/populationShareRange.json';
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

/** A party's share of some total across resamples, in percent. `point` is the share of the
 *  observed sample, `expected` the resample mean. */
export interface ShareInterval {
  point: number; expected: number; lo: number; hi: number;
}

export interface ShareBlock {
  shares: Record<string, ShareInterval>;
}

/** Turnout stops in slider order, index 0-6 — the same seven suffixes every other per-stop
 *  payload in the app is keyed by. */
export const VOTE_STOP_KEYS = [
  'Turnout', 'TurnoutL5', 'TurnoutL10', 'TurnoutL15', 'TurnoutL20', 'TurnoutL25', 'TurnoutL30',
] as const;

export interface ShareRangeData {
  nDraws: number;
  seed: number;
  /** One block, never seven: population share is weighted by `commonpostweight` alone and never
   *  by turnout, so it describes the country and cannot move with the slider. */
  population: ShareBlock & { stopInvariant: boolean };
  /** Seven blocks keyed by `VOTE_STOP_KEYS`: vote share is turnout-weighted, so it describes the
   *  electorate and does move. The gap against `population` is the turnout effect, which is why
   *  the two are deliberately not the same shape. */
  votes: Record<string, ShareBlock>;
}

export const SHARE_RANGES = shareRanges as unknown as ShareRangeData;

/** Population share spans, keyed by party code. Takes no stop argument on purpose — see
 *  `ShareRangeData.population`. */
export function populationShares(): Record<string, ShareInterval> {
  return SHARE_RANGES.population.shares;
}

/** Vote share spans at one turnout stop, keyed by party code. Undefined outside 0-6. */
export function voteSharesAt(gi: number): Record<string, ShareInterval> | undefined {
  const key = VOTE_STOP_KEYS[gi];
  return key ? SHARE_RANGES.votes[key]?.shares : undefined;
}

export function chamberTotal(
  seats: Record<string, SeatInterval>,
  key: 'modal' | 'observed',
): number {
  return Object.values(seats).reduce((s, v) => s + v[key], 0);
}

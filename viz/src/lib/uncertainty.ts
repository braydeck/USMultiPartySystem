// Bootstrap sampling uncertainty, one payload per turnout stop. These are bootstrap
// percentile intervals, not credible intervals — see About → Caveats.
import u0 from '../data/uncertaintyTurnout.json';
import u5 from '../data/uncertaintyTurnoutL5.json';
import u10 from '../data/uncertaintyTurnoutL10.json';
import u15 from '../data/uncertaintyTurnoutL15.json';
import u20 from '../data/uncertaintyTurnoutL20.json';
import u25 from '../data/uncertaintyTurnoutL25.json';
import u30 from '../data/uncertaintyTurnoutL30.json';
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
  president: Record<'irv' | 'cond', { dist: Record<string, number>; observed: string; modal: string }>;
}

export const UNCERTAINTY_STOPS = [u0, u5, u10, u15, u20, u25, u30] as unknown as UncertaintyData[];

export function uncertaintyAt(gi: number): UncertaintyData | undefined {
  return UNCERTAINTY_STOPS[gi];
}

export function chamberTotal(
  seats: Record<string, SeatInterval>,
  key: 'modal' | 'observed',
): number {
  return Object.values(seats).reduce((s, v) => s + v[key], 0);
}

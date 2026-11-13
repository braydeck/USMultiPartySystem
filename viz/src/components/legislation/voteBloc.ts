import type { CandidateVoteRow, VoteModelRow } from '../../types';
import type { HouseSystem, Pipeline, WyomingRule } from '../../constants/labels';
import { F5_ORDER, getPrimaryParty } from '../../constants/parties';

export type SeatMap = Record<string, number>;

const HOUSE_PROB_FIELD: Record<string, keyof VoteModelRow> = {
  'rawMulti+double':  'houseRawMultiProbPass',
  'rawMulti+triple':  'houseRawMultiTripleProbPass',
  'factorDev+double': 'houseFDProbPass',
  'factorDev+triple': 'houseFDTripleProbPass',
};

/** The precomputed pass-probability column for one House configuration, or undefined when the
 *  combination (MMP, reserve, non-rank-7 depth) has no pre-baked column and must be computed
 *  on the fly via passProbability. */
export function houseProbField(
  system: HouseSystem, pipeline: Pipeline, wyoming: WyomingRule,
  opts?: { depth?: string; reserve?: string },
): keyof VoteModelRow | undefined {
  if (system === 'mmp') return undefined;
  if (opts?.reserve === 'on') return undefined;
  if (system === 'list') return wyoming === 'triple' ? 'houseListTripleProbPass' : 'houseListProbPass';
  if (opts?.depth && opts.depth !== 'top7') return undefined;
  return HOUSE_PROB_FIELD[`${pipeline}+${wyoming}`] ?? 'houseRawMultiProbPass';
}

/** Count senators per party from a per-senator scenario array. */
export function senateSeatMap(senators: { senatorParty: string }[]): SeatMap {
  const m: SeatMap = {};
  for (const s of senators) m[s.senatorParty] = (m[s.senatorParty] ?? 0) + 1;
  return m;
}

/** Whipped: a party casts all its seats for the side its majority favors (support > 50%). */
export function blocOutcome(bill: CandidateVoteRow, seats: SeatMap) {
  let yes = 0, total = 0;
  for (const p of F5_ORDER) {
    const s = seats[p] ?? 0;
    if (!s || !bill.parties[p]) continue;
    total += s;
    if ((bill.parties[p].observedPct ?? 0) > 50) yes += s;
  }
  return { yes, total, pass: yes > total / 2, share: total ? yes / total : 0 };
}

// Abramowitz & Stegun 26.2.17, the normal CDF prepare_data.py uses, so a computed column matches
// a published one to the digit.
function normalCdf(x: number): number {
  if (x > 6) return 1;
  if (x < -6) return 0;
  const t = 1 / (1 + 0.2316419 * Math.abs(x));
  const d = 0.3989422803 * Math.exp(-0.5 * x * x);
  const tail = d * t * (0.3193815 + t * (-0.3565638 + t * (1.7814779 + t * (-1.821256 + t * 1.3302744))));
  return x < 0 ? tail : 1 - tail;
}

/** Chamber vote model: the chance a bill clears a majority of `seats`. Every member votes
 *  independently at their party's observed support, so the yes count is a sum of binomials,
 *  taken by its continuity-corrected normal approximation. This is the calculation behind the
 *  published pass-probability columns (prepare_data.py `_lf_prob_pass`), for the House
 *  configurations that have none. `majority` defaults to more than half the seats. */
export function passProbability(bill: CandidateVoteRow, seats: SeatMap, majority?: number): number | undefined {
  let mu = 0, variance = 0, total = 0;
  for (const p of F5_ORDER) {
    const s = seats[p] ?? 0;
    if (!s) continue;
    total += s;
    const q = (bill.parties[p]?.observedPct ?? 0) / 100;
    mu += s * q;
    variance += s * q * (1 - q);
  }
  if (!total) return undefined;
  const need = majority ?? Math.floor(total / 2) + 1;
  const z = (need - 0.5 - mu) / (variance > 0 ? Math.sqrt(variance) : 1e-6);
  return 1 - normalCdf(z);
}

/** A single president signs (whipped) when their party favors the bill. */
export function presSigns(bill: CandidateVoteRow, winnerCode: string): boolean {
  const party = getPrimaryParty(winnerCode);
  return (bill.parties[party]?.observedPct ?? 0) > 50;
}

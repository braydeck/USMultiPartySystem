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
 *  on the fly via freeOutcome. */
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

/** Free vote: each party's seats split by its per-candidate yes-probability. */
export function freeOutcome(bill: CandidateVoteRow, seats: SeatMap) {
  let yes = 0, total = 0;
  for (const p of F5_ORDER) {
    const s = seats[p] ?? 0;
    if (!s || !bill.parties[p]) continue;
    total += s;
    const pYes = bill.parties[p].pYes ?? (bill.parties[p].observedPct ?? 0) / 100;
    yes += s * pYes;
  }
  return { yes, total, pass: yes > total / 2, share: total ? yes / total : 0 };
}

/** A single president signs (whipped) when their party favors the bill. */
export function presSigns(bill: CandidateVoteRow, winnerCode: string): boolean {
  const party = getPrimaryParty(winnerCode);
  return (bill.parties[party]?.observedPct ?? 0) > 50;
}

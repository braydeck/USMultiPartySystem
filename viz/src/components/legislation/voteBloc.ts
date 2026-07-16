import type { CandidateVoteRow } from '../../types';
import { F5_ORDER, getPrimaryParty } from '../../constants/parties';

export type SeatMap = Record<string, number>;

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

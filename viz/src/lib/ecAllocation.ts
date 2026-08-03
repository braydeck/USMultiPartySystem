/**
 * ecAllocation.ts — what the electoral college does to a ten-party field.
 *
 * The presidency is decided nationally on this site: one ballot, counted once, by IRV or
 * Condorcet. That is the national override. This module answers the obvious next question
 * — what if the college kept its state-by-state structure? — and the answer is why the
 * override exists.
 *
 * Four rules, not six. Per state the payload carries a first-choice share vector, an IRV
 * winner and a Condorcet winner. Only a share vector can be apportioned, and it is a
 * first-choice vector, so proportional allocation is FPTP by construction; IRV and
 * Condorcet each yield one winner per state and are therefore winner-take-all by
 * construction. FPTP proportional, FPTP winner-take-all, IRV, Condorcet.
 *
 * Electoral votes use this project's apportionment, not today's 538: a state's
 * multi-member House seats plus two senatorial votes, so 873 + 102 = 975 under double
 * Wyoming. Small states are still over-weighted the way the real college over-weights
 * them — that is the point of counting them this way.
 */

import type { PresidentialStateWinner, HouseStateEntry, IRVRound } from '../types';

export type ECMethod = 'prop' | 'fptp' | 'irv' | 'condorcet';

export const EC_METHODS: readonly ECMethod[] = ['prop', 'fptp', 'irv', 'condorcet'];

export const EC_METHOD_LABELS: Record<ECMethod, string> = {
  prop: 'Proportional',
  fptp: 'Winner-take-all',
  irv: 'IRV per state',
  condorcet: 'Condorcet per state',
};

/** Longer label for the result cards, where the counting rule needs naming too. */
export const EC_METHOD_LONG: Record<ECMethod, string> = {
  prop: 'FPTP · proportional electors',
  fptp: 'FPTP · winner-take-all',
  irv: 'IRV · winner-take-all',
  condorcet: 'Condorcet · winner-take-all',
};

export const EC_METHOD_BLURB: Record<ECMethod, string> = {
  prop: 'Each state splits its electors in proportion to first-choice votes.',
  fptp: 'Each state gives every elector to its first-choice leader.',
  irv: 'Each state runs its own instant runoff, then gives every elector to the winner.',
  condorcet: 'Each state finds its own head-to-head winner, then gives every elector to them.',
};

/**
 * The vote itself, with no allocation rule on top: states sized by population and tiles
 * split by first-choice share. It sits alongside the four elector rules because it is what
 * they are all rules *about* — the thing every one of them distorts.
 */
export type MapView = ECMethod | 'share';

export const MAP_VIEWS: readonly MapView[] = ['share', ...EC_METHODS];

export const MAP_VIEW_LABELS: Record<MapView, string> = {
  share: 'First-choice share',
  ...EC_METHOD_LABELS,
};

export const MAP_VIEW_BLURB: Record<MapView, string> = {
  share: 'States sized by population. Hexes apportioned by first vote share.',
  ...EC_METHOD_BLURB,
};

/** Senatorial electors, the two per state that break proportionality by design. */
export const SENATORIAL_ELECTORS = 2;

/** States casting one vote each when the college fails to produce a majority. */
export const CONTINGENT_STATES = 51;

export interface ECStateAllocation {
  fips: string;
  abbr: string;
  ev: number;
  /** electors by party; one entry under the three winner-take-all rules */
  electors: Record<string, number>;
  /** the party carrying the state, or null under proportional where nobody carries it */
  carries: string | null;
}

export interface ECTally {
  method: ECMethod;
  states: ECStateAllocation[];
  /** parties with at least one elector, most first */
  byParty: { code: string; ev: number }[];
  total: number;
  majority: number;
  /** the party holding a majority of electors, or null when the college deadlocks */
  winner: string | null;
}

export interface ContingentVote {
  /** parties holding at least one state delegation, most first */
  byParty: { code: string; states: number }[];
  total: number;
  majority: number;
  /** the party holding a majority of delegations, or null when the House deadlocks */
  winner: string | null;
}

/** Electoral votes per state: House seats at the current magnitude plus two. */
export function ecWeights(stateMap: Record<string, HouseStateEntry>): Record<string, number> {
  const out: Record<string, number> = {};
  for (const [fips, entry] of Object.entries(stateMap)) {
    out[fips] = entry.totalSeats + SENATORIAL_ELECTORS;
  }
  return out;
}

/**
 * Largest remainder (Hamilton), the same rule the party-list seats use. Ties on the
 * fractional part break on party code so a rerun cannot reorder the result.
 */
export function largestRemainder(shares: Record<string, number>, seats: number): Record<string, number> {
  const total = Object.values(shares).reduce((s, v) => s + v, 0);
  if (total <= 0 || seats <= 0) return {};
  const exact: Record<string, number> = {};
  const out: Record<string, number> = {};
  for (const [code, share] of Object.entries(shares)) {
    exact[code] = (share / total) * seats;
    out[code] = Math.floor(exact[code]);
  }
  let left = seats - Object.values(out).reduce((s, v) => s + v, 0);
  const byRemainder = Object.keys(exact).sort((a, b) => {
    const ra = exact[a] - Math.floor(exact[a]);
    const rb = exact[b] - Math.floor(exact[b]);
    return rb - ra || a.localeCompare(b);
  });
  for (const code of byRemainder) {
    if (left <= 0) break;
    out[code] += 1;
    left -= 1;
  }
  return out;
}

/** First-choice leader of a state. Ties break on party code, as everywhere else here. */
export function pluralityWinner(shares: Record<string, number>): string | null {
  const codes = Object.keys(shares);
  if (codes.length === 0) return null;
  return codes.sort((a, b) => shares[b] - shares[a] || a.localeCompare(b))[0];
}

function stateWinnerFor(method: ECMethod, sw: PresidentialStateWinner): string | null {
  switch (method) {
    case 'fptp': return pluralityWinner(sw.shares);
    case 'irv': return sw.winner;
    case 'condorcet': return sw.condorcetWinner;
    case 'prop': return null;
  }
}

export function allocateEC(
  stateWinners: Record<string, PresidentialStateWinner>,
  weights: Record<string, number>,
  method: ECMethod,
): ECTally {
  const states: ECStateAllocation[] = [];
  const totals: Record<string, number> = {};

  for (const [fips, sw] of Object.entries(stateWinners)) {
    const ev = weights[fips];
    if (!ev) continue;
    let electors: Record<string, number>;
    let carries: string | null = null;
    if (method === 'prop') {
      electors = largestRemainder(sw.shares, ev);
    } else {
      carries = stateWinnerFor(method, sw);
      electors = carries ? { [carries]: ev } : {};
    }
    for (const [code, n] of Object.entries(electors)) {
      totals[code] = (totals[code] ?? 0) + n;
    }
    states.push({ fips, abbr: sw.stateAbbr, ev, electors, carries });
  }

  states.sort((a, b) => a.abbr.localeCompare(b.abbr));
  const byParty = Object.entries(totals)
    .map(([code, ev]) => ({ code, ev }))
    .sort((a, b) => b.ev - a.ev || a.code.localeCompare(b.code));
  const total = byParty.reduce((s, p) => s + p.ev, 0);
  const majority = Math.floor(total / 2) + 1;

  return {
    method,
    states,
    byParty,
    total,
    majority,
    winner: byParty.find(p => p.ev >= majority)?.code ?? null,
  };
}

/**
 * The contingent election, one vote per state delegation.
 *
 * A delegation's vote goes to that state's Condorcet winner: the college has already
 * failed at this point, so what decides the House is which candidate the delegation's
 * own voters would prefer against every alternative — the closest thing in the payload
 * to the coalitional bargaining a real contingent election would be.
 */
export function contingentVote(
  stateWinners: Record<string, PresidentialStateWinner>,
): ContingentVote {
  const counts: Record<string, number> = {};
  let total = 0;
  for (const sw of Object.values(stateWinners)) {
    if (!sw.condorcetWinner) continue;
    counts[sw.condorcetWinner] = (counts[sw.condorcetWinner] ?? 0) + 1;
    total += 1;
  }
  const byParty = Object.entries(counts)
    .map(([code, states]) => ({ code, states }))
    .sort((a, b) => b.states - a.states || a.code.localeCompare(b.code));
  const majority = Math.floor(total / 2) + 1;
  return {
    byParty,
    total,
    majority,
    winner: byParty.find(p => p.states >= majority)?.code ?? null,
  };
}

/**
 * National first-choice shares, which are round one of the instant runoff. FPTP counted
 * nationally is the same ballots stopped after the first preference.
 */
export function nationalFirstChoice(rounds: IRVRound[]): { code: string; pct: number }[] {
  const first = rounds[0];
  if (!first) return [];
  const total = first.candidates.reduce((s, c) => s + c.votes, 0);
  if (total <= 0) return [];
  return first.candidates
    .map(c => ({ code: c.code, pct: c.votes / total }))
    .sort((a, b) => b.pct - a.pct || a.code.localeCompare(b.code));
}

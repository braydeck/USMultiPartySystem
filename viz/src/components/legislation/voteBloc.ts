import type { CandidateVoteRow, VoteModelRow } from '../../types';
import type { HouseSystem, Pipeline, VoteMode, WyomingRule } from '../../constants/labels';
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

/** Who carries one bill, as CoalitionMap draws it. Parties with seats are split into a yes and a
 *  no side and each side is ordered by support. Whipped: every seat goes to the side the party's
 *  majority favors (support > 50%). Free vote: a party's seats split by its yes-probability.
 *  On a pass, the pivotal segment is the yes segment whose seats carry the running total to half
 *  the chamber; a defeat has none. */
export type CoalitionSeg = { party: string; w: number; yes: boolean; key: string };

export function coalitionSegments(bill: CandidateVoteRow, seats: SeatMap, mode: VoteMode) {
  const parties = F5_ORDER.filter((p) => bill.parties[p] && (seats[p] ?? 0) > 0);
  const supp = (p: string) => bill.parties[p].observedPct ?? 0;
  const py = (p: string) => bill.parties[p].pYes ?? supp(p) / 100;
  let total = 0;
  for (const p of parties) total += seats[p] ?? 0;

  const yesSegs: CoalitionSeg[] = [];
  const noSegs: CoalitionSeg[] = [];
  if (mode === 'whipped') {
    for (const p of parties) {
      const s = seats[p] ?? 0;
      (supp(p) > 50 ? yesSegs : noSegs).push({ party: p, w: s, yes: supp(p) > 50, key: p });
    }
    yesSegs.sort((a, b) => supp(b.party) - supp(a.party));
    noSegs.sort((a, b) => supp(b.party) - supp(a.party));
  } else {
    for (const p of parties) {
      const s = seats[p] ?? 0;
      const yesW = s * py(p);
      const noW = s - yesW;
      if (yesW > 0.5) yesSegs.push({ party: p, w: yesW, yes: true, key: p + '-y' });
      if (noW > 0.5) noSegs.push({ party: p, w: noW, yes: false, key: p + '-n' });
    }
    yesSegs.sort((a, b) => py(b.party) - py(a.party));
    noSegs.sort((a, b) => py(b.party) - py(a.party));
  }

  const totalYes = yesSegs.reduce((s, x) => s + x.w, 0);
  const pass = totalYes > total / 2;
  // Pivotal only exists on a pass — the yes-segment whose seats carry the coalition over the line.
  let pivotalKey: string | null = null;
  if (pass) {
    let cum = 0;
    for (const seg of yesSegs) { cum += seg.w; if (cum >= total / 2) { pivotalKey = seg.key; break; } }
  }
  return { segs: [...yesSegs, ...noSegs], total, totalYes, pass, pivotalKey };
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

export type DomainCoalition = {
  domain: string;
  bills: CandidateVoteRow[];
  passed: number;
  /** Per party with seats: share of the domain's bills on which its whipped vote is on the winning side. */
  membership: Record<string, number>;
  /** Per party with seats: share of the domain's items that pass but would fail without its seats. */
  needed: Record<string, number>;
  /** The most common set of parties on the winning side (yes on a pass, no on a defeat), in F5_ORDER. */
  typical: { parties: string[]; pass: boolean; count: number };
  failed: CandidateVoteRow[];
};

/** Which parties end up in the majority across one policy domain, under whipped (party-line)
 *  votes, counted from coalitionSegments so the grid agrees with the per-bill view. A party is
 *  needed on an item when the yes side passes with its seats and falls to half or less without
 *  them. Domains keep their first-appearance order. Typical-coalition ties go to the set covering
 *  more seats, then the one met first. */
export function domainCoalitions(bills: CandidateVoteRow[], seats: SeatMap): DomainCoalition[] {
  const byDomain = new Map<string, CandidateVoteRow[]>();
  for (const b of bills) {
    const rows = byDomain.get(b.domain);
    if (rows) rows.push(b);
    else byDomain.set(b.domain, [b]);
  }
  const seated = F5_ORDER.filter((p) => (seats[p] ?? 0) > 0);
  return [...byDomain].map(([domain, rows]) => {
    const won: Record<string, number> = {}, need: Record<string, number> = {};
    for (const p of seated) { won[p] = 0; need[p] = 0; }
    const sets = new Map<string, { parties: string[]; pass: boolean; count: number; seats: number }>();
    const failed: CandidateVoteRow[] = [];
    let passed = 0;
    for (const b of rows) {
      const { segs, pass, total, totalYes } = coalitionSegments(b, seats, 'whipped');
      if (pass) passed++; else failed.push(b);
      const winners = segs.filter((s) => s.yes === pass).map((s) => s.party);
      for (const p of winners) won[p]++;
      if (pass) for (const p of winners) if (totalYes - (seats[p] ?? 0) <= total / 2) need[p]++;
      const ordered = F5_ORDER.filter((p) => winners.includes(p));
      const key = `${pass ? 'Y' : 'N'}:${ordered.join(',')}`;
      const cur = sets.get(key);
      if (cur) cur.count++;
      else sets.set(key, { parties: ordered, pass, count: 1, seats: ordered.reduce((s, p) => s + (seats[p] ?? 0), 0) });
    }
    let typical = { parties: [] as string[], pass: true, count: 0, seats: -1 };
    for (const v of sets.values()) {
      if (v.count > typical.count || (v.count === typical.count && v.seats > typical.seats)) typical = v;
    }
    const n = rows.length;
    return {
      domain, bills: rows, passed, failed,
      membership: Object.fromEntries(seated.map((p) => [p, won[p] / n])),
      needed: Object.fromEntries(seated.map((p) => [p, need[p] / n])),
      typical: { parties: typical.parties, pass: typical.pass, count: typical.count },
    };
  });
}

/** Parties whose majorities (support > 50%) land on the same side of every item in `rows`. Seats
 *  play no part, as in PartyAgreement. Groups are ordered by their first member in F5_ORDER. */
export function votingGroups(rows: CandidateVoteRow[]): string[][] {
  const groups = new Map<string, string[]>();
  for (const p of F5_ORDER) {
    if (!rows.every((b) => b.parties[p])) continue;
    const sig = rows.map((b) => ((b.parties[p].observedPct ?? 0) > 50 ? '1' : '0')).join('');
    const g = groups.get(sig);
    if (g) g.push(p);
    else groups.set(sig, [p]);
  }
  return [...groups.values()];
}

import { describe, it, expect } from 'vitest';
import {
  ecWeights, largestRemainder, pluralityWinner, allocateEC, contingentVote,
  nationalFirstChoice, SENATORIAL_ELECTORS,
} from './ecAllocation';
import type { PresidentialStateWinner, HouseStateEntry, IRVRound } from '../types';

const state = (
  stateAbbr: string, winner: string, condorcetWinner: string, shares: Record<string, number>,
): PresidentialStateWinner => ({ stateAbbr, winner, condorcetWinner, pod: 'A', nRespondents: 100, shares });

const houseState = (stateAbbr: string, totalSeats: number): HouseStateEntry =>
  ({ stateAbbr, pluralityParty: 'CON', totalSeats, seats: {} });

describe('ecWeights', () => {
  it('adds two senatorial electors to each state', () => {
    const w = ecWeights({ '06': houseState('CA', 104), '56': houseState('WY', 2) });
    expect(w).toEqual({ '06': 106, '56': 4 });
  });

  it('gives the smallest state the largest bonus relative to population', () => {
    const w = ecWeights({ '06': houseState('CA', 104), '56': houseState('WY', 2) });
    // WY doubles, CA gains 2% — the over-weighting the college is built on
    expect(w['56'] / 2).toBe(2);
    expect(w['06'] / 104).toBeCloseTo(1.019, 3);
  });
});

describe('largestRemainder', () => {
  it('allocates every seat', () => {
    const out = largestRemainder({ A: 0.35, B: 0.33, C: 0.32 }, 10);
    expect(Object.values(out).reduce((s, v) => s + v, 0)).toBe(10);
  });

  it('gives the leftover to the largest fractional remainder', () => {
    // exact = A 3.5, B 3.3, C 3.2 → floors 3/3/3, one left, A has the biggest remainder
    expect(largestRemainder({ A: 0.35, B: 0.33, C: 0.32 }, 10)).toEqual({ A: 4, B: 3, C: 3 });
  });

  it('breaks remainder ties on party code so reruns are identical', () => {
    // B and A tie exactly on the remainder; A wins on code
    expect(largestRemainder({ B: 0.5, A: 0.5 }, 3)).toEqual({ A: 2, B: 1 });
  });

  it('rounds a small share to zero rather than inventing an elector', () => {
    const out = largestRemainder({ A: 0.9, B: 0.1 }, 4);
    expect(out).toEqual({ A: 4, B: 0 });
  });

  it('returns nothing for an empty or zero-seat state', () => {
    expect(largestRemainder({}, 5)).toEqual({});
    expect(largestRemainder({ A: 1 }, 0)).toEqual({});
  });
});

describe('pluralityWinner', () => {
  it('picks the highest first-choice share', () => {
    expect(pluralityWinner({ A: 0.2, B: 0.5, C: 0.3 })).toBe('B');
  });

  it('breaks ties on party code', () => {
    expect(pluralityWinner({ B: 0.5, A: 0.5 })).toBe('A');
  });

  it('returns null when there are no shares', () => {
    expect(pluralityWinner({})).toBeNull();
  });
});

describe('allocateEC', () => {
  // Two states. The big one prefers CON on first choice but STY beats everyone
  // head-to-head; the small one is solidly LBR. This is the divergence the four rules exist
  // to show, compressed into the smallest case that produces it.
  const winners: Record<string, PresidentialStateWinner> = {
    '06': state('CA', 'LBR', 'STY', { CON: 0.4, LBR: 0.35, STY: 0.25 }),
    '56': state('WY', 'LBR', 'LBR', { LBR: 0.6, CON: 0.4 }),
  };
  const weights = { '06': 10, '56': 4 };

  it('splits proportionally under prop and carries nobody', () => {
    const t = allocateEC(winners, weights, 'prop');
    expect(t.total).toBe(14);
    expect(t.majority).toBe(8);
    // CA: 4/3.5/2.5 → 4/4/2 after remainders. WY: 2.4/1.6 → 2/2.
    expect(t.states.find(s => s.abbr === 'CA')!.electors).toEqual({ CON: 4, LBR: 4, STY: 2 });
    expect(t.states.every(s => s.carries === null)).toBe(true);
    expect(t.winner).toBeNull();
  });

  it('hands every elector to the first-choice leader under fptp', () => {
    const t = allocateEC(winners, weights, 'fptp');
    expect(t.byParty).toEqual([{ code: 'CON', ev: 10 }, { code: 'LBR', ev: 4 }]);
    expect(t.winner).toBe('CON');
  });

  it('uses the state IRV winner under irv', () => {
    const t = allocateEC(winners, weights, 'irv');
    expect(t.byParty).toEqual([{ code: 'LBR', ev: 14 }]);
    expect(t.winner).toBe('LBR');
  });

  it('uses the state Condorcet winner under condorcet', () => {
    const t = allocateEC(winners, weights, 'condorcet');
    expect(t.byParty).toEqual([{ code: 'STY', ev: 10 }, { code: 'LBR', ev: 4 }]);
    expect(t.winner).toBe('STY');
  });

  it('reports no winner when the leader falls short of a majority', () => {
    const three: Record<string, PresidentialStateWinner> = {
      '01': state('AL', 'A', 'A', { A: 1 }),
      '02': state('AK', 'B', 'B', { B: 1 }),
      '04': state('AZ', 'C', 'C', { C: 1 }),
    };
    const t = allocateEC(three, { '01': 4, '02': 3, '04': 3 }, 'fptp');
    expect(t.total).toBe(10);
    expect(t.majority).toBe(6);
    expect(t.winner).toBeNull();
  });

  it('skips states with no electoral weight rather than counting them as zero', () => {
    const t = allocateEC(winners, { '06': 10 }, 'fptp');
    expect(t.total).toBe(10);
    expect(t.states).toHaveLength(1);
  });

  it('conserves electors: every rule allocates the same total', () => {
    const totals = (['prop', 'fptp', 'irv', 'condorcet'] as const)
      .map(m => allocateEC(winners, weights, m).total);
    expect(new Set(totals)).toEqual(new Set([14]));
  });
});

describe('contingentVote', () => {
  it('gives each state one vote, cast for its Condorcet winner', () => {
    const cv = contingentVote({
      '01': state('AL', 'LBR', 'STY', { STY: 1 }),
      '02': state('AK', 'LBR', 'STY', { STY: 1 }),
      '04': state('AZ', 'LBR', 'LBR', { LBR: 1 }),
    });
    expect(cv.total).toBe(3);
    expect(cv.majority).toBe(2);
    expect(cv.byParty).toEqual([{ code: 'STY', states: 2 }, { code: 'LBR', states: 1 }]);
    expect(cv.winner).toBe('STY');
  });

  it('deadlocks when no party holds a majority of delegations', () => {
    const cv = contingentVote({
      '01': state('AL', 'A', 'A', { A: 1 }),
      '02': state('AK', 'B', 'B', { B: 1 }),
      '04': state('AZ', 'C', 'C', { C: 1 }),
      '05': state('AR', 'D', 'D', { D: 1 }),
    });
    expect(cv.majority).toBe(3);
    expect(cv.winner).toBeNull();
  });

  it('ignores a state with no Condorcet winner instead of crediting one', () => {
    const cv = contingentVote({
      '01': state('AL', 'LBR', '', { LBR: 1 }),
      '02': state('AK', 'LBR', 'LBR', { LBR: 1 }),
    });
    expect(cv.total).toBe(1);
  });
});

describe('nationalFirstChoice', () => {
  const rounds: IRVRound[] = [{
    round: 1,
    candidates: [
      { code: 'LBR', name: 'LBR', pct: 20, votes: 200, eliminated: false, winner: false },
      { code: 'CON', name: 'CON', pct: 50, votes: 500, eliminated: false, winner: false },
      { code: 'STY', name: 'STY', pct: 30, votes: 300, eliminated: false, winner: false },
    ],
  }, {
    round: 2,
    candidates: [
      { code: 'CON', name: 'CON', pct: 55, votes: 550, eliminated: false, winner: false },
      { code: 'STY', name: 'STY', pct: 45, votes: 450, eliminated: false, winner: true },
    ],
  }];

  it('reads round one, not the final round', () => {
    const out = nationalFirstChoice(rounds);
    expect(out.map(o => o.code)).toEqual(['CON', 'STY', 'LBR']);
    expect(out[0].pct).toBeCloseTo(0.5, 6);
  });

  it('returns nothing for an empty round list', () => {
    expect(nationalFirstChoice([])).toEqual([]);
  });
});

describe('SENATORIAL_ELECTORS', () => {
  it('is two, the constant that makes the college disproportional', () => {
    expect(SENATORIAL_ELECTORS).toBe(2);
  });
});

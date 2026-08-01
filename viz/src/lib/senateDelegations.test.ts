import { describe, it, expect } from 'vitest';
import { delegations, delegationSeats, SPLIT_THRESHOLD_PP } from './senateDelegations';
import type { StateUncertainty } from './uncertainty';
import u5 from '../data/uncertaintyTurnoutL5.json';

const st = (dist: Record<string, number>): StateUncertainty => {
  const ranked = Object.entries(dist).sort((a, b) => b[1] - a[1]);
  return {
    observed: `${ranked[0][0]}_1`, modal: ranked[0][0],
    pModal: ranked[0][1], pObserved: ranked[0][1], dist, substituted: false,
  } as StateUncertainty;
};

describe('senate delegations', () => {
  it('gives both seats to a party that wins the state outright', () => {
    const [d] = delegations({ '01': st({ CON: 0.83, STY: 0.11, POP: 0.06 }) });
    expect(d.split).toBe(false);
    expect(d.seats).toEqual(['CON', 'CON']);
  });

  it('splits when the runner-up is inside the threshold', () => {
    const [d] = delegations({ '05': st({ CON: 0.282, POP: 0.243, STY: 0.2 }) });
    expect(d.split).toBe(true);
    expect(d.seats).toEqual(['CON', 'POP']);
  });

  it('is inclusive at the threshold, despite float error', () => {
    const gap = SPLIT_THRESHOLD_PP / 100;
    // 0.428 - 0.328 is Wyoming, and it comes out as 9.999999999999998 points.
    expect(delegations({ '01': st({ A: 0.428, B: 0.328 }) })[0].split).toBe(true);
    expect(delegations({ '01': st({ A: 0.5, B: 0.5 - gap - 0.001 }) })[0].split).toBe(false);
  });

  it('handles a state only one party ever wins', () => {
    const [d] = delegations({ '01': st({ CON: 1 }) });
    expect(d.split).toBe(false);
    expect(d.seats).toEqual(['CON', 'CON']);
  });

  it('keeps the chamber at two seats per state on the real payload', () => {
    for (const method of ['cond', 'irv'] as const) {
      const states = u5.senate[method].states as unknown as Record<string, StateUncertainty>;
      const n = Object.keys(states).length;
      const total = Object.values(delegationSeats(states)).reduce((a, b) => a + b, 0);
      expect(total).toBe(n * 2);
    }
  });

  it('splits the states the Condorcet resampling actually leaves contested', () => {
    const states = u5.senate.cond.states as unknown as Record<string, StateUncertainty>;
    const FIPS_TO_ABBR: Record<string, string> = {
      '05': 'AR', '18': 'IN', '20': 'KS', '31': 'NE', '32': 'NV', '37': 'NC',
      '38': 'ND', '45': 'SC', '51': 'VA', '54': 'WV', '56': 'WY',
    };
    const split = delegations(states).filter(d => d.split).map(d => FIPS_TO_ABBR[d.fips] ?? d.fips);
    expect(split.sort()).toEqual(Object.values(FIPS_TO_ABBR).sort());
  });
});

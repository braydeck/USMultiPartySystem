import { describe, expect, it } from 'vitest';
import { domainPositions } from './domainPosition';
import { DOMAIN_POLES } from '../constants/domains';
import type { CandidateVoteRow } from '../types';
import candidateVotes from '../data/candidateVoteModel.json';
import budget from '../data/budgetPriorities.json';

const items = [...(candidateVotes as unknown as CandidateVoteRow[]), ...(budget as unknown as CandidateVoteRow[])];
const dom = (d: string) => items.filter(b => b.domain === d);
const toward = (d: string, q: string) => {
  const rows = dom(d);
  return domainPositions(rows).toward100[rows.findIndex(r => r.question === q)];
};

describe('domainPositions', () => {
  it('has end labels for every domain', () => {
    for (const d of new Set(items.map(b => b.domain))) expect(DOMAIN_POLES[d]).toBeDefined();
  });
  // Directions come from the data, so check they land where the end labels say.
  it('points each item toward the end its label names', () => {
    expect(toward('Immigration', 'Build a wall between the U.S. and Mexico')).toBe(true);
    expect(toward('Immigration', 'Permanent status/pathway for Dreamers')).toBe(false);
    expect(toward('Abortion', 'Prohibit restrictions on abortion access')).toBe(false);
    expect(toward('Healthcare & Housing', 'Repeal the Affordable Care Act')).toBe(true);
    expect(toward('Environment & Climate', 'Increase fossil fuel production in the U.S.')).toBe(true);
    expect(toward('Taxes & Economy', 'Extend the 2017 tax cuts')).toBe(true);
    expect(toward('Budget', 'Increase state spending on law enforcement')).toBe(true);
    expect(toward('Budget', 'Increase state spending on welfare')).toBe(false);
  });
  it('matches the numpy reference for immigration', () => {
    const { pos } = domainPositions(dom('Immigration'));
    expect(Math.round(pos.DSA)).toBe(1);
    expect(Math.round(pos.NAT)).toBe(90);
    expect(Math.round(pos.CUP)).toBe(51);
  });
});

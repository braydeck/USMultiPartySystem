import { describe, expect, it } from 'vitest';
import { coalitionSegments, domainCoalitions } from './voteBloc';
import type { CandidateVoteRow, ClusterProfile } from '../../types';
import candidateVotes from '../../data/candidateVoteModel.json';
import budget from '../../data/budgetPriorities.json';
import clusterProfiles from '../../data/clusterProfiles.json';
import depthNational from '../../data/houseDepthNational.json';

const bills = candidateVotes as unknown as CandidateVoteRow[];
const budgetRows = budget as unknown as (CandidateVoteRow & { overallPct: number })[];
const seats = (depthNational as unknown as Record<string, Record<string, Record<string, {
  national: { stvSeats: Record<string, number> } }>>>).top7.double['5'].national.stvSeats;

describe('budget priorities payload', () => {
  it('stays out of the 37-bill set', () => {
    const billVars = new Set(bills.map(b => b.variable));
    expect(budgetRows).toHaveLength(5);
    for (const r of budgetRows) expect(billVars.has(r.variable)).toBe(false);
  });
  it('carries the Parties tab shares for every party', () => {
    for (const c of clusterProfiles as unknown as ClusterProfile[]) {
      for (const r of budgetRows) {
        const pct = (c.variables as Record<string, { pct: number }>)[r.variable].pct;
        expect(Math.abs(r.parties[c.party].observedPct! - pct)).toBeLessThan(0.06);
      }
    }
  });
});

describe('domainCoalitions', () => {
  const items = [...bills, ...budgetRows];
  const rows = domainCoalitions(items, seats);
  it('covers every item once, Budget included', () => {
    expect(rows.reduce((s, r) => s + r.bills.length, 0)).toBe(items.length);
    expect(rows.map(r => r.domain)).toContain('Budget');
  });
  it('agrees with the per-bill pivotal party', () => {
    for (const r of rows) {
      const n = r.bills.length;
      const piv: Record<string, number> = {};
      for (const b of r.bills) {
        const k = coalitionSegments(b, seats, 'whipped').pivotalKey;
        if (k) piv[k] = (piv[k] ?? 0) + 1;
      }
      for (const [p, v] of Object.entries(r.pivot)) expect(v * n).toBeCloseTo(piv[p] ?? 0);
      expect(Object.values(r.pivot).reduce((s, v) => s + v * n, 0)).toBeCloseTo(r.passed);
    }
  });
  it('leaves parties without seats out of the grid', () => {
    const r = domainCoalitions(bills, { CON: 10, LBR: 5 })[0];
    expect(Object.keys(r.membership).sort()).toEqual(['CON', 'LBR']);
  });
});

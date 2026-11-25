import { describe, expect, it } from 'vitest';
import partyOrderCsv from '../../../data/processed/party_order.csv?raw';
import { agreementLine } from './agreementLine';
import type { CandidateVoteRow } from '../types';
import candidateVotes from '../data/candidateVoteModel.json';

const bills = candidateVotes as unknown as CandidateVoteRow[];

describe('agreementLine', () => {
  // On all 37 bills the line is the site's party order, so it must reproduce vote_agreement.py.
  it('reproduces party_order.csv on the 37 bills', () => {
    const csv = partyOrderCsv.trim().split('\n').slice(1);
    const { x } = agreementLine(bills, 'whipped');
    for (const line of csv) {
      const [party, , dim1] = line.split(',');
      expect(Math.abs(x[party] - Number(dim1))).toBeLessThan(1e-3);
    }
  });
  it('puts parties that vote identically at the same point', () => {
    const { x } = agreementLine(bills.filter(b => b.domain === 'Abortion'), 'whipped');
    expect(Math.abs(x.CON - x.NAT)).toBeLessThan(1e-9);
  });
});

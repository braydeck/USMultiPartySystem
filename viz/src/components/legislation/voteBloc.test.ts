import { describe, expect, it } from 'vitest';
import { passProbability } from './voteBloc';
import type { CandidateVoteRow } from '../../types';
import candidateVotes from '../../data/candidateVoteModel.json';
import houseVotesL5 from '../../data/houseVoteModelTurnoutL5.json';
import depthNational from '../../data/houseDepthNational.json';

// The computed fallback has to sit on the same scale as the published pass-probability columns,
// or a House configuration without a column (MMP, reserve, other depths) reads on a different one.
const bills = candidateVotes as unknown as CandidateVoteRow[];
const rows = houseVotesL5 as unknown as { variable: string; houseRawMultiProbPass: number; houseListProbPass: number }[];
const byVar = Object.fromEntries(rows.map(r => [r.variable, r]));
const nat = (depthNational as unknown as Record<string, Record<string, Record<string, {
  national: { stvSeats: Record<string, number>; listSeats: Record<string, number> } }>>>)
  .top7.double['5'].national;

describe('passProbability', () => {
  // The House votes as the House tab shows it: the elected chamber, not the bootstrap's modal one.
  it('reproduces the published STV column on the elected chamber', () => {
    for (const b of bills) expect(Math.abs(passProbability(b, nat.stvSeats)! - byVar[b.variable].houseRawMultiProbPass)).toBeLessThan(0.03);
  });
  it('reproduces the published Party List column on the list chamber', () => {
    for (const b of bills) expect(Math.abs(passProbability(b, nat.listSeats)! - byVar[b.variable].houseListProbPass)).toBeLessThan(0.03);
  });
  it('returns undefined for an empty chamber', () => {
    expect(passProbability(bills[0], {})).toBeUndefined();
  });
});

// Ballot depth: how many preferences a voter ranks. Truncating ballots makes them exhaust,
// which weakens STV proportionality (late seats fill below quota). 'full' is the exhaustive floor.
export type DepthKey = 'top3' | 'top5' | 'top7' | 'top10' | 'full';

export const DEPTH_KEYS = ['top3', 'top5', 'top7', 'top10', 'full'] as const;

export const DEPTH_LABELS: Record<DepthKey, string> = {
  top3: '3',
  top5: '5',
  top7: '7',
  top10: '10',
  full: 'Rank all',
};

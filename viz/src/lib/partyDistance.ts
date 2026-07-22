// Distance between a formulated party and a current party, in the typology's own
// coordinate systems. Factor distance is the primary "how different" number; policy
// divergence is the secondary, per-item average.

export const DISTANCE_FACTORS = ['F1', 'F2', 'F4', 'F5'] as const;
export type DistanceFactor = typeof DISTANCE_FACTORS[number];

/** η²-weighted RMS of z-score differences over DISTANCE_FACTORS, in σ.
 *  `a`/`b` carry `z_F1`…`z_F5`; `eta` carries per-factor discriminatory value. */
export function factorDistance(
  a: Record<string, number>,
  b: Record<string, number>,
  eta: Record<string, number>,
): number {
  let wsum = 0, acc = 0;
  for (const f of DISTANCE_FACTORS) {
    const w = eta[f] ?? 0;
    const d = (a[`z_${f}`] ?? 0) - (b[`z_${f}`] ?? 0);
    wsum += w;
    acc += w * d * d;
  }
  return wsum > 0 ? Math.sqrt(acc / wsum) : 0;
}

/** Mean of per-item policy distances (each 0–100); 0 when there are no shared items. */
export function policyDivergence(perItemDistances: number[]): number {
  if (perItemDistances.length === 0) return 0;
  return perItemDistances.reduce((s, d) => s + d, 0) / perItemDistances.length;
}

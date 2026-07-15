// Shared vocabulary for a party's "signature": positions held by strong internal Consensus
// (cohesion) that are either Mainstream (near the U.S. average) or Deviant (far from it).
// Annotations always show, driven purely by the thresholds; the per-axis filter checkboxes
// (held outside this object) only trim which rows are listed.

export interface SignatureFilter {
  consPct: number;        // cohesive if held by ≥consPct% (or the type-specific analog)
  deviantPp: number;      // "D" when distance-from-U.S. ≥ deviantPp
  mainstreamPp: number;   // "M" when distance-from-U.S. ≤ mainstreamPp
}

/** Classify a party's distance-from-national (0–100) as Deviant / Mainstream / neither.
 *  Always on (no enable gate); Deviant wins if the bands somehow overlap. */
export function centralityMark(distance: number, f: SignatureFilter): 'D' | 'M' | null {
  if (distance >= f.deviantPp) return 'D';
  if (distance <= f.mainstreamPp) return 'M';
  return null;
}

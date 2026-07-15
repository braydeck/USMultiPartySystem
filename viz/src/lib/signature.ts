// Shared vocabulary for a party's "signature": positions held by strong internal Consensus
// (cohesion) that are either Mainstream (near the U.S. average) or Deviant (far from it).
// Cohesion and centrality are two independent axes, shown as row annotations (a left cohesion
// dot and a right D/M mark) rather than by hiding rows.

export interface SignatureFilter {
  useConsensus: boolean;
  consPct: number;        // cohesive if held by ≥consPct% (or the type-specific analog)
  useDeviant: boolean;
  deviantPp: number;      // "D" when distance-from-U.S. ≥ deviantPp
  useMainstream: boolean;
  mainstreamPp: number;   // "M" when distance-from-U.S. ≤ mainstreamPp
}

/** True when at least one annotation axis is engaged. */
export function sigActive(f: SignatureFilter): boolean {
  return f.useConsensus || f.useDeviant || f.useMainstream;
}

/** Classify a party's distance-from-national (0–100) as Deviant / Mainstream / neither,
 *  honoring which axes are enabled. Deviant wins if both would somehow apply. */
export function centralityMark(distance: number, f: SignatureFilter): 'D' | 'M' | null {
  if (f.useDeviant && distance >= f.deviantPp) return 'D';
  if (f.useMainstream && distance <= f.mainstreamPp) return 'M';
  return null;
}

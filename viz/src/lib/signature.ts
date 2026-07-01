// Shared vocabulary for a party's "signature": positions it holds by strong
// internal Consensus that are either Mainstream (near the national average) or
// Deviant (far from it). These are two independent axes — "distinctive" is the
// combination, not one of them. Different parties are defined by different mixes:
// some by mainstream consensus (CUP, STY, OAO), others by deviance (NAT, PRG, DSA).

export type AlignMode = 'deviant' | 'mainstream';

export interface SignatureFilter {
  useConsensus: boolean;
  consPct: number; // held by ≥consPct% (or ≤100-consPct% against)
  useAlign: boolean;
  alignMode: AlignMode;
  alignPp: number; // distance from the national average, in points
}

/** True when at least one axis of the signature filter is engaged. */
export function sigActive(f: SignatureFilter): boolean {
  return f.useConsensus || f.useAlign;
}

/**
 * Does one party's position on one item belong to its signature under this filter?
 * pct = the party's share; overall = the national average on the same scale.
 */
export function qualifies(pct: number, overall: number | null, f: SignatureFilter): boolean {
  const consensusOk = pct >= f.consPct || pct <= 100 - f.consPct;
  const absDev = Math.abs(pct - (overall ?? pct));
  const alignOk = f.alignMode === 'deviant' ? absDev >= f.alignPp : absDev <= f.alignPp;
  return (!f.useConsensus || consensusOk) && (!f.useAlign || alignOk);
}

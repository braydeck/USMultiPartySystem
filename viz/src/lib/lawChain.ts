// Enactment chain for a bill: pass both chambers, then the president signs — or,
// on a veto, both chambers override with a 2/3 supermajority.
//
//   P(law) = P(House) · P(Senate) · [ P(sign) + (1 − P(sign)) · P(overrideHouse) · P(overrideSenate) ]
//
// All inputs are probabilities in [0, 1]. P(sign) is the president's party
// candidate's factor-logit P(yes) on the bill; the override terms are the
// 2/3-threshold pass probabilities from the same sum-of-binomials.

export interface LawChainInputs {
  pHouse: number;
  pSenate: number;
  pSign: number;
  pOverrideHouse?: number;
  pOverrideSenate?: number;
}

export function pLaw({
  pHouse,
  pSenate,
  pSign,
  pOverrideHouse = 0,
  pOverrideSenate = 0,
}: LawChainInputs): number {
  const overrides = pOverrideHouse * pOverrideSenate;
  const enacted = pSign + (1 - pSign) * overrides;
  return pHouse * pSenate * enacted;
}

// Verdict bands shared with the existing bill table.
export type Verdict = 'Fails' | 'Tossup' | 'Possibly' | 'Likely' | 'Clearly';

export function verdict(prob: number): Verdict {
  if (prob >= 0.8) return 'Clearly';
  if (prob >= 0.65) return 'Likely';
  if (prob >= 0.55) return 'Possibly';
  if (prob >= 0.45) return 'Tossup';
  return 'Fails';
}

// The pivotal party on a bill: order parties by predicted P(yes) descending and
// find the one whose seats carry the cumulative yes-share across the majority
// line. That party's defection would flip the outcome — the whip target.
export function pivotalParty(
  pYesByParty: Record<string, number>,
  seatShareByParty: Record<string, number>,
): string | null {
  const parties = Object.keys(pYesByParty).filter((p) => (seatShareByParty[p] ?? 0) > 0);
  if (parties.length === 0) return null;
  const total = parties.reduce((s, p) => s + (seatShareByParty[p] ?? 0), 0);
  const majority = total / 2;
  const ordered = parties.sort((a, b) => pYesByParty[b] - pYesByParty[a]);
  let cum = 0;
  for (const p of ordered) {
    cum += seatShareByParty[p] ?? 0;
    if (cum >= majority) return p;
  }
  return ordered[ordered.length - 1] ?? null;
}

import partyPopData from '../data/partyPopulation.json';

type Row = { party: string; popShare: number; voteShare: number; turnoutPresidential: number; turnoutMidterm: number };
const BY_CODE: Record<string, Row> = Object.fromEntries(
  (partyPopData as unknown as Row[]).map(r => [r.party, r]),
);

/** Share of the adult population belonging to a party's cluster (0–100). */
export function popShare(code: string): number {
  return BY_CODE[code.split('_')[0]]?.popShare ?? 0;
}

/** Compact label, e.g. "12% of adults" — the party's population weight. */
export function popShareLabel(code: string): string {
  const p = popShare(code);
  return p ? `${Math.round(p)}% of adults` : '';
}

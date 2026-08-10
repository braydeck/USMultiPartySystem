import { F5_ORDER } from '../constants/parties';
import quotaComposition from '../data/quotaComposition.json';

/** Shared shape for the party→party matrices (transfer destinations, quota composition) and
 *  the controls they share. Kept out of the component file so both can be imported without
 *  tripping the fast-refresh rule. */

export interface FlowRow {
  party: string;
  segments: { party: string; share: number }[];
  /** Own-party share, held separately so the heatmap can scale its body on the off-diagonal:
   *  a 55-90% own share against 2-14% borrowed would flatten every other cell. */
  selfShare?: number;
}

/** A numeric column to the right of the matrix, e.g. coalition breadth or exhausted weight.
 *  Generic so a chart can add one without the matrix growing chart-specific code. */
export interface FlowExtra {
  label: string;
  hint?: string;
  value: (row: FlowRow) => string;
}

export type FlowView = 'heatmap' | 'bars';
export const FLOW_VIEWS: readonly FlowView[] = ['heatmap', 'bars'];
export const FLOW_VIEW_LABELS: Record<FlowView, string> = { heatmap: 'Heatmap', bars: 'Bars' };

export type FlowSort = 'reliance' | 'ideology' | 'breadth';
export const FLOW_SORTS: readonly FlowSort[] = ['reliance', 'ideology', 'breadth'];
export const FLOW_SORT_LABELS: Record<FlowSort, string> = {
  reliance: 'Self-reliance',
  ideology: 'Ideology',
  breadth: 'Breadth',
};

/** Parties by the share of their electing weight that came from their own first-preference
 *  voters, descending. Read off the quota-composition bundle so it cannot drift from the data. */
export const RELIANCE_ORDER: readonly string[] =
  (quotaComposition as { parties: { party: string }[] }).parties.map(p => p.party);

/**
 * Effective number of partners: 1 / Σp², the Laakso-Taagepera formula applied to a party's
 * off-self shares. Reads on an intuitive scale — 2.0 is as concentrated as an even two-way
 * split — and separates a tight coalition partner from a diffuse one. Progressive sends 59%
 * of its transfers to DSA and 38% to Liberal and scores 2.0; Civic Union spreads across five
 * parties and scores 4.7.
 *
 * Preferred over Shannon entropy here because the source data is clipped at 0.5% per
 * destination, and entropy is the more tail-sensitive of the two.
 */
export function effectivePartners(segments: { share: number }[]): number {
  const total = segments.reduce((a, s) => a + s.share, 0);
  if (!total) return 0;
  const hhi = segments.reduce((a, s) => a + (s.share / total) ** 2, 0);
  return 1 / hhi;
}

/** Row and column order for one matrix. Rows and columns always share it, which is what keeps
 *  the self cells on the diagonal. `breadth` is per-matrix, so the two cards can differ. */
export function orderRows(rows: FlowRow[], sort: FlowSort): FlowRow[] {
  if (sort === 'breadth') {
    return [...rows].sort((a, b) => effectivePartners(b.segments) - effectivePartners(a.segments));
  }
  const seq = sort === 'ideology' ? F5_ORDER : RELIANCE_ORDER;
  const rank = (p: string) => {
    const i = seq.indexOf(p);
    return i === -1 ? seq.length : i;
  };
  return [...rows].sort((a, b) => rank(a.party) - rank(b.party));
}

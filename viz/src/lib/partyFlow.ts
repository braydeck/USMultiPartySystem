import { F5_ORDER } from '../constants/parties';
import quotaComposition from '../data/quotaComposition.json';

/** Shared shape for the party→party matrices (transfer destinations, quota composition) and
 *  the view switch they share. Kept out of the component file so both can be imported without
 *  tripping the fast-refresh rule. */

export interface FlowRow {
  party: string;
  segments: { party: string; share: number }[];
  /** Own-party share, held separately so the heatmap can scale its body on the off-diagonal:
   *  a 55-90% own share against 2-14% borrowed would flatten every other cell. */
  selfShare?: number;
}

export type FlowView = 'heatmap' | 'bars';
export const FLOW_VIEWS: readonly FlowView[] = ['bars', 'heatmap'];
export const FLOW_VIEW_LABELS: Record<FlowView, string> = { bars: 'Bars', heatmap: 'Heatmap' };

export type FlowSort = 'reliance' | 'ideology';
export const FLOW_SORTS: readonly FlowSort[] = ['reliance', 'ideology'];
export const FLOW_SORT_LABELS: Record<FlowSort, string> = {
  reliance: 'Self-reliance',
  ideology: 'Ideology',
};

/** Parties by the share of their electing weight that came from their own first-preference
 *  voters, descending. Read off the quota-composition bundle so it cannot drift from the data. */
export const RELIANCE_ORDER: readonly string[] =
  (quotaComposition as { parties: { party: string }[] }).parties.map(p => p.party);

/** One order for both matrices under either sort, applied to rows and columns alike. */
export function flowOrder(sort: FlowSort): readonly string[] {
  return sort === 'ideology' ? F5_ORDER : RELIANCE_ORDER;
}

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

export type FlowView = 'bars' | 'heatmap';
export const FLOW_VIEWS: readonly FlowView[] = ['bars', 'heatmap'];
export const FLOW_VIEW_LABELS: Record<FlowView, string> = { bars: 'Bars', heatmap: 'Heatmap' };

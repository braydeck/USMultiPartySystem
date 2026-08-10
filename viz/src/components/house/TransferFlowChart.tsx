import { PartyFlowBars, PartyFlowHeatmap } from '../shared/PartyFlowMatrix';
import {
  orderRows, spreadIndex,
  type FlowExtra, type FlowRow, type FlowSort, type FlowView,
} from '../../lib/partyFlow';
import type { FlowConfig } from '../../lib/quotaFlows';

/** Real transfer destinations, followed as the count runs: every surplus and every elimination,
 *  with the weight leaving a candidate traced to its next surviving choice. Replaces the earlier
 *  second-preference proxy, which could not see elimination order, intra-slate transfers, or
 *  exhausted ballots. */
const AXES = { row: 'from', col: 'to' };

const EXTRAS: FlowExtra[] = [
  {
    label: 'spread',
    hint: 'Low when a party\'s votes pile into one destination, high when they divide evenly '
      + 'across many. 0 would be every vote to a single party, 100 an even split across all nine '
      + 'others.',
    meter: row => spreadIndex(row.segments),
    value: row => `${Math.round(spreadIndex(row.segments) * 100)}`,
  },
];

export function TransferFlowChart({ config, filterParties, view = 'heatmap', sort = 'spread' }: {
  config: FlowConfig | null;
  filterParties?: string[];
  view?: FlowView;
  sort?: FlowSort;
}) {
  if (!config) return null;
  const rows: FlowRow[] = config.transfersOut
    .filter(r => !filterParties || filterParties.includes(r.party))
    .map(r => ({
      party: r.party,
      segments: Object.entries(r.byDest).map(([party, share]) => ({ party, share })),
      hint: `Of all the weight leaving ${r.party}: ${Math.round(r.crossShare * 100)}% to other `
        + `parties (shown), ${Math.round(r.internalShare * 100)}% to its own other candidates, `
        + `${Math.round(r.exhaustedShare * 100)}% exhausted with no rankings left`,
    }));
  if (!rows.length) return null;
  const ordered = orderRows(rows, sort);

  return view === 'heatmap'
    ? <PartyFlowHeatmap rows={ordered} axes={AXES} extras={EXTRAS} />
    : <PartyFlowBars rows={ordered} axes={AXES} extras={EXTRAS} />;
}

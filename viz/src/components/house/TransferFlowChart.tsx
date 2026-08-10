import { PartyFlowBars, PartyFlowHeatmap } from '../shared/PartyFlowMatrix';
import {
  effectivePartners, orderRows,
  type FlowExtra, type FlowRow, type FlowSort, type FlowView,
} from '../../lib/partyFlow';
import quotaComposition from '../../data/quotaComposition.json';

/** Real transfer destinations, followed as the count runs: every surplus and every elimination,
 *  with the weight leaving a candidate traced to its next surviving choice. Replaces the earlier
 *  second-preference proxy, which could not see elimination order, intra-slate transfers, or
 *  exhausted ballots. */
interface TransferRow {
  party: string;
  byDest: Record<string, number>;
  crossShare: number;
  internalShare: number;
  exhaustedShare: number;
  surplusShare: number;
}

const DATA = (quotaComposition as unknown as { transfersOut: TransferRow[] }).transfersOut;
const AXES = { row: 'transfers out of', col: 'ballots go to' };

const EXTRAS: FlowExtra[] = [
  {
    label: 'reach',
    hint: 'Effective number of destination parties (1 / sum of squared shares). 2.0 is as '
      + 'concentrated as an even two-way split; higher means the votes spread more widely.',
    value: row => effectivePartners(row.segments).toFixed(1),
  },
];

export function TransferFlowChart({ filterParties, view = 'heatmap', sort = 'breadth' }: {
  filterParties?: string[];
  view?: FlowView;
  sort?: FlowSort;
}) {
  const rows: FlowRow[] = DATA
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

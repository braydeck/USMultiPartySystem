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
const META: Record<string, TransferRow> = Object.fromEntries(DATA.map(r => [r.party, r]));

const AXES = { row: 'transfers out of', col: 'ballots go to' };

const EXTRAS: FlowExtra[] = [
  {
    label: 'partners',
    hint: 'Effective number of destination parties (1 / sum of squared shares). 2.0 is as '
      + 'concentrated as an even two-way split; higher means the votes spread more widely.',
    value: row => effectivePartners(row.segments).toFixed(1),
  },
  {
    label: 'stays in',
    hint: 'Share of the weight leaving this party that goes to another of its own candidates. '
      + 'High for parties running multi-candidate slates.',
    value: row => `${Math.round((META[row.party]?.internalShare ?? 0) * 100)}%`,
  },
  {
    label: 'exhausts',
    hint: 'Share of the weight leaving this party that runs out of ranked choices and stops '
      + 'transferring altogether.',
    value: row => `${Math.round((META[row.party]?.exhaustedShare ?? 0) * 100)}%`,
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
    }));
  if (!rows.length) return null;
  const ordered = orderRows(rows, sort);

  return view === 'heatmap'
    ? <PartyFlowHeatmap rows={ordered} axes={AXES} extras={EXTRAS} />
    : <PartyFlowBars rows={ordered} axes={AXES} extras={EXTRAS} />;
}

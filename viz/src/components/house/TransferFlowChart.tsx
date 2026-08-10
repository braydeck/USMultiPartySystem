import { F5_ORDER } from '../../constants/parties';
import { PartyFlowBars, PartyFlowHeatmap } from '../shared/PartyFlowMatrix';
import { orderRows, type FlowRow, type FlowSort, type FlowView } from '../../lib/partyFlow';

interface TransferSource {
  source: string;
  totalVoters: number;
  destinations: { party: string; pct: number }[];
}

interface Props {
  data: TransferSource[];
  filterParties?: string[];
  view?: FlowView;
  sort?: FlowSort;
}

const AXES = { row: 'eliminated', col: 'ballots go to' };

export function TransferFlowChart({ data, filterParties, view = 'heatmap', sort = 'reliance' }: Props) {
  if (!data || data.length === 0) return null;

  const bySource: Record<string, TransferSource> = {};
  for (const row of data) bySource[row.source] = row;

  const seq = filterParties ? F5_ORDER.filter(p => filterParties.includes(p)) : F5_ORDER;
  const rows: FlowRow[] = seq
    .map(party => bySource[party])
    .filter((r): r is TransferSource => !!r && r.destinations.length > 0)
    .map(r => ({
      party: r.source,
      segments: r.destinations.map(d => ({ party: d.party, share: d.pct / 100 })),
    }));

  if (!rows.length) return null;
  const ordered = orderRows(rows, sort);

  return view === 'heatmap'
    ? <PartyFlowHeatmap rows={ordered} axes={AXES} />
    : <PartyFlowBars rows={ordered} axes={AXES} />;
}

import { F5_ORDER } from '../../constants/parties';
import { PartyFlowBars, PartyFlowHeatmap } from '../shared/PartyFlowMatrix';
import type { FlowRow, FlowView } from '../../lib/partyFlow';

interface TransferSource {
  source: string;
  totalVoters: number;
  destinations: { party: string; pct: number }[];
}

interface Props {
  data: TransferSource[];
  filterParties?: string[];
  view?: FlowView;
  /** Row and column order, shared with the quota-composition matrix. */
  order?: readonly string[];
}

export function TransferFlowChart({ data, filterParties, view = 'heatmap', order }: Props) {
  if (!data || data.length === 0) return null;

  const bySource: Record<string, TransferSource> = {};
  for (const row of data) bySource[row.source] = row;

  const seq = order ?? F5_ORDER;
  const rows: FlowRow[] = (filterParties ? seq.filter(p => filterParties.includes(p)) : seq)
    .map(party => bySource[party])
    .filter((r): r is TransferSource => !!r && r.destinations.length > 0)
    .map(r => ({
      party: r.source,
      segments: r.destinations.map(d => ({ party: d.party, share: d.pct / 100 })),
    }));

  if (!rows.length) return null;

  return view === 'heatmap'
    ? <PartyFlowHeatmap rows={rows} />
    : <PartyFlowBars rows={rows} />;
}

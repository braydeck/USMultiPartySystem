import { PartyFlowBars, PartyFlowHeatmap } from '../shared/PartyFlowMatrix';
import { orderRows, type FlowRow, type FlowSort, type FlowView } from '../../lib/partyFlow';
import type { FlowConfig } from '../../lib/quotaFlows';

/** Whose ballots elected each party's seats: own first-preference voters against votes
 *  borrowed from other parties' voters. Origin rather than preference depth, because
 *  ballots are party-contiguous and depth mostly reports slate size. */
const AXES = { row: 'seat won by', col: 'voters from' };

export function QuotaCompositionChart({ config, filterParties, view = 'heatmap', sort = 'reliance' }: {
  config: FlowConfig | null;
  filterParties?: string[];
  view?: FlowView;
  sort?: FlowSort;
}) {
  if (!config) return null;
  const rows: FlowRow[] = config.parties
    .filter(r => !filterParties || filterParties.includes(r.party))
    .map(r => ({
      party: r.party,
      selfShare: r.ownShare,
      segments: Object.entries(r.byOrigin)
        .filter(([p]) => p !== r.party)
        .sort((a, b) => b[1] - a[1])
        .map(([p, share]) => ({ party: p, share })),
    }));
  if (!rows.length) return null;
  const ordered = orderRows(rows, sort);

  return (
    <div className="space-y-3">
      {view === 'heatmap'
        ? <PartyFlowHeatmap rows={ordered} axes={AXES} selfLabel="Own" />
        : <PartyFlowBars rows={ordered} axes={AXES} />}
    </div>
  );
}

import { CARD_HINT } from '../../constants/typography';
import { PartyFlowBars, PartyFlowHeatmap } from '../shared/PartyFlowMatrix';
import type { FlowRow, FlowView } from '../../lib/partyFlow';
import quotaComposition from '../../data/quotaComposition.json';

interface PartyRow {
  party: string;
  seats: number;
  belowQuota: number;
  ownShare: number;
  byOrigin: Record<string, number>;
  ownDepth: Record<string, number>;
  marginalByOrigin: Record<string, number>;
  marginalOwnShare: number;
  perDistrict: {
    districtsWon: number; median: number; max: number;
    hist: Record<string, number>; multiSeatShare: number;
  };
}
interface Bundle {
  config: { apportionment: string; ballotDepth: number; turnoutGap: number };
  parties: PartyRow[];
}

const DATA = quotaComposition as unknown as Bundle;

/** Whose ballots elected each party's seats: own first-preference voters against votes
 *  borrowed from other parties' voters. Origin rather than preference depth, because
 *  ballots are party-contiguous and depth mostly reports slate size. */
export function QuotaCompositionChart({ filterParties, view = 'heatmap', order }: {
  filterParties?: string[];
  view?: FlowView;
  /** Row and column order, shared with the transfer matrix. */
  order?: readonly string[];
}) {
  const rank = (p: string) => (order ? order.indexOf(p) : 0);
  const rows: FlowRow[] = DATA.parties
    .filter(r => !filterParties || filterParties.includes(r.party))
    .sort((a, b) => (order ? rank(a.party) - rank(b.party) : 0))
    .map(r => ({
      party: r.party,
      selfShare: r.ownShare,
      segments: Object.entries(r.byOrigin)
        .filter(([p]) => p !== r.party)
        .sort((a, b) => b[1] - a[1])
        .map(([p, share]) => ({ party: p, share })),
    }));
  if (!rows.length) return null;

  return (
    <div className="space-y-3">
      {view === 'heatmap'
        ? <PartyFlowHeatmap rows={rows} selfLabel="Own" />
        : <PartyFlowBars rows={rows} />}
      <p className={CARD_HINT}>
        Rank-{DATA.config.ballotDepth}
        {' '}ballots at {Math.round(DATA.config.turnoutGap * 100)}% turnout gap closed, fixed.
      </p>
    </div>
  );
}

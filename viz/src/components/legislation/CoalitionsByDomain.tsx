import { useMemo } from 'react';
import type { CandidateVoteRow } from '../../types';
import { F5_ORDER, PARTY_NAMES, getPartyColor } from '../../constants/parties';
import type { VoteMode } from '../../constants/labels';
import { agreementLine } from '../../lib/agreementLine';
import { useElementWidth } from '../../hooks/useElementWidth';
import { domainCoalitions, type SeatMap } from './voteBloc';
import type { Chamber } from './CoalitionMap';
import { PartyAgreement } from './PartyAgreement';
import { FOOTNOTE, MINOR_HEADING } from '../../constants/typography';

// Issue coalitions: one agreement line per policy domain (agreementLine, the method behind the
// site's party order, run on that domain's items). Parties close together vote alike on that kind
// of issue. Every row shares one scale, so a wider spread is a more divided domain. Chips that
// would overlap stack into lanes. Selecting a domain shows its pairwise matrix and filters the
// per-bill view; each chip's hover text gives its closest partners and its winning-side count.

const CHIP_W = 34;
const LANE_H = 22;
const GAP = 3;

type Placed = { party: string; px: number; lane: number };

function place(x: Record<string, number>, toPx: (v: number) => number): { chips: Placed[]; lanes: number } {
  const order = [...F5_ORDER].sort((a, b) => x[a] - x[b]);
  const laneEnd: number[] = [];
  const chips: Placed[] = [];
  for (const p of order) {
    const px = toPx(x[p]);
    let lane = laneEnd.findIndex((end) => px - CHIP_W / 2 >= end + GAP);
    if (lane < 0) { lane = laneEnd.length; laneEnd.push(0); }
    laneEnd[lane] = px + CHIP_W / 2;
    chips.push({ party: p, px, lane });
  }
  return { chips, lanes: laneEnd.length };
}

export function CoalitionsByDomain({ bills, houseSeats, senateSeats, chamber, voteModel, domain, onDomainChange }: {
  bills: CandidateVoteRow[];
  houseSeats: SeatMap;
  senateSeats: SeatMap;
  chamber: Chamber;
  voteModel: VoteMode;
  domain: string | null;
  onDomainChange: (d: string | null) => void;
}) {
  const seats = chamber === 'house' ? houseSeats : senateSeats;
  const chamberName = chamber === 'house' ? 'House' : 'Senate';
  const [trackRef, trackW] = useElementWidth<HTMLDivElement>();

  const rows = useMemo(
    () => domainCoalitions(bills, seats).map((r) => ({ ...r, line: agreementLine(r.bills, voteModel) })),
    [bills, seats, voteModel]);
  const [lo, hi] = useMemo(() => {
    const xs = rows.flatMap((r) => Object.values(r.line.x));
    return [Math.min(...xs), Math.max(...xs)];
  }, [rows]);
  const usable = Math.max(trackW - CHIP_W, 1);
  const toPx = (v: number) => CHIP_W / 2 + (hi > lo ? (v - lo) / (hi - lo) : 0.5) * usable;
  const sel = rows.find((r) => r.domain === domain);
  const alike = (v: number) => `${Math.round(v * 100)}%`;

  return (
    <div>
      <div className="grid grid-cols-1 sm:grid-cols-[150px_1fr] gap-x-3">
        <span className="hidden sm:block" />
        <div ref={trackRef} className="h-0" />
      </div>
      <div className="space-y-0.5">
        {rows.map((r) => {
          const active = r.domain === domain;
          const n = r.bills.length;
          const { chips, lanes } = trackW ? place(r.line.x, toPx) : { chips: [], lanes: 1 };
          return (
            <button key={r.domain} type="button" onClick={() => onDomainChange(active ? null : r.domain)} aria-pressed={active}
              className={`w-full text-left grid grid-cols-1 sm:grid-cols-[150px_1fr] gap-x-3 gap-y-1 items-center rounded-md py-1.5 ${active ? 'ring-2 ring-foreground/70 bg-muted/40' : 'hover:bg-muted/40'}`}>
              <span className="text-2xs font-semibold leading-tight pl-1"
                title={`One line captures ${Math.round(r.line.fit * 100)}% of how these parties agree on ${r.domain.toLowerCase()}`}>
                {r.domain}<span className="text-4xs font-normal text-muted-foreground"> · {n} {n === 1 ? 'item' : 'items'}</span>
              </span>
              <div className="relative" style={{ height: lanes * LANE_H }}>
                <div className="absolute left-0 right-0 border-t border-dashed border-border" style={{ top: LANE_H / 2 }} />
                {chips.map(({ party: p, px, lane }) => {
                  const partners = F5_ORDER.filter((q) => q !== p)
                    .sort((a, b) => r.line.agreement[p][b] - r.line.agreement[p][a]).slice(0, 3)
                    .map((q) => `${q} ${alike(r.line.agreement[p][q])}`).join(', ');
                  const won = r.membership[p];
                  const tally = won == null ? `no ${chamberName} seats` : `${chamberName}: on the winning side of ${Math.round(won * n)} of ${n}`;
                  return (
                    <span key={p} className="absolute text-center py-0.5 rounded text-3xs font-bold text-white chip-text shadow-sm"
                      style={{ left: px - CHIP_W / 2, top: lane * LANE_H + 1, width: CHIP_W, backgroundColor: getPartyColor(p) }}
                      title={`${PARTY_NAMES[p] ?? p}, ${r.domain}. Votes most like ${partners}. ${tally}.`}>
                      {p}
                    </span>
                  );
                })}
              </div>
            </button>
          );
        })}
      </div>
      <p className={`${FOOTNOTE} mt-2`}>
        Parties close together vote alike on that kind of issue; far apart, they split. Stacked parties sit at
        about the same point. Every row uses the same scale. {voteModel === 'whipped' ? 'Whipped: alike means both party majorities take the same side.' : 'Free vote: alike means similar levels of support.'} Hover
        a party for its closest partners.
      </p>

      {sel && (
        <div className="mt-5 pt-4 border-t border-border/60">
          <h5 className={`${MINOR_HEADING} mb-1`}>{sel.domain}: how often each pair votes the same way</h5>
          <PartyAgreement candidateVotes={sel.bills} voteModel={voteModel} />
          <p className={`${FOOTNOTE} mt-2`}>
            {sel.failed.length ? <>Fails in the {chamberName}: {sel.failed.map((b) => b.question).join('; ')}.</> : `Every item passes in the ${chamberName}.`}
          </p>
        </div>
      )}
    </div>
  );
}

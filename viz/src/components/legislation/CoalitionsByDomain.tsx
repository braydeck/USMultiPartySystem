import { useMemo } from 'react';
import type { CandidateVoteRow } from '../../types';
import { F5_ORDER, PARTY_NAMES, getPartyColor } from '../../constants/parties';
import { DOMAIN_POLES } from '../../constants/domains';
import type { VoteMode } from '../../constants/labels';
import { domainPositions } from '../../lib/domainPosition';
import { useElementWidth } from '../../hooks/useElementWidth';
import { domainCoalitions, type SeatMap } from './voteBloc';
import type { Chamber } from './CoalitionMap';
import { PartyAgreement } from './PartyAgreement';
import { FOOTNOTE, MINOR_HEADING } from '../../constants/typography';

// Where each party stands in each policy domain (domainPositions), one strip per domain between
// that domain's end labels. The labels sit above their own strip, beside the domain name, so no
// label sits next to another row's line. Party codes under nearby dots stack into lanes. Selecting
// a domain shows how often each pair votes the same way there and filters the per-bill view; each
// dot's hover text gives the position, the same-side counts and the winning-side count.

const DOT_R = 7;
const LANE_H = 12;
const LABEL_GAP = 30;

function lanes(pos: Record<string, number>, toPx: (v: number) => number) {
  const end: number[] = [];
  const lane: Record<string, number> = {};
  for (const p of [...F5_ORDER].sort((a, b) => pos[a] - pos[b])) {
    const x = toPx(pos[p]);
    let k = end.findIndex((e) => x - e >= LABEL_GAP);
    if (k < 0) { k = end.length; end.push(-Infinity); }
    end[k] = x;
    lane[p] = k;
  }
  return { lane, count: end.length };
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
    () => domainCoalitions(bills, seats).map((r) => ({ ...r, ...domainPositions(r.bills) })),
    [bills, seats]);
  const sel = rows.find((r) => r.domain === domain);
  const toPx = (v: number) => DOT_R + (v / 100) * Math.max(trackW - 2 * DOT_R, 1);

  const sameSide = (rs: CandidateVoteRow[], a: string, b: string) =>
    rs.filter((x) => ((x.parties[a]?.observedPct ?? 0) > 50) === ((x.parties[b]?.observedPct ?? 0) > 50)).length;

  return (
    <div>
      <div ref={trackRef} className="h-0 mx-1 sm:ml-[186px]" />
      {rows.map((r) => {
        const active = r.domain === domain;
        const n = r.bills.length;
        const [low, high] = DOMAIN_POLES[r.domain] ?? ['', ''];
        const { lane, count } = trackW ? lanes(r.pos, toPx) : { lane: {}, count: 1 };
        const axisY = DOT_R + 2;
        const h = axisY + DOT_R + 6 + count * LANE_H;
        return (
          <button key={r.domain} type="button" onClick={() => onDomainChange(active ? null : r.domain)} aria-pressed={active}
            className={`w-full text-left block border-t border-border py-3 px-1 rounded-sm ${active ? 'ring-2 ring-foreground/70 bg-muted/40' : 'hover:bg-muted/30'}`}>
            <div className="grid grid-cols-1 sm:grid-cols-[170px_1fr] gap-x-3 gap-y-1">
              <span className="text-xs font-semibold leading-tight">
                {r.domain}<span className="block text-4xs font-normal text-muted-foreground">{n} {n === 1 ? 'item' : 'items'}</span>
              </span>
              <div>
                <div className="flex justify-between gap-3 text-2xs text-muted-foreground mb-1.5">
                  <span>← {low}</span><span className="text-right">{high} →</span>
                </div>
                {trackW > 0 && (
                  <svg width={trackW} height={h} className="block overflow-visible" role="img"
                    aria-label={`${r.domain}, from ${low} to ${high}: ${[...F5_ORDER].sort((a, b) => r.pos[a] - r.pos[b]).map((p) => `${p} ${Math.round(r.pos[p])}`).join(', ')}`}>
                    <line x1={DOT_R} x2={trackW - DOT_R} y1={axisY} y2={axisY} stroke="hsl(var(--border))" strokeWidth={2} />
                    {[0, 50, 100].map((t) => (
                      <line key={t} x1={toPx(t)} x2={toPx(t)} y1={axisY - 4} y2={axisY + 4} stroke="hsl(var(--border))" strokeWidth={1.5} />
                    ))}
                    {F5_ORDER.map((p) => {
                      const x = toPx(r.pos[p]);
                      const partners = F5_ORDER.filter((q) => q !== p)
                        .sort((a, b) => sameSide(r.bills, p, b) - sameSide(r.bills, p, a)).slice(0, 4)
                        .map((q) => `${q} ${sameSide(r.bills, p, q)}/${n}`).join(', ');
                      const won = r.membership[p];
                      const tally = won == null ? `no ${chamberName} seats` : `${chamberName}: on the winning side of ${Math.round(won * n)} of ${n}`;
                      return (
                        <g key={p}>
                          <circle cx={x} cy={axisY} r={DOT_R} fill={getPartyColor(p)} stroke="hsl(var(--background))" strokeWidth={2}>
                            <title>{`${PARTY_NAMES[p] ?? p}, ${r.domain}: ${Math.round(r.pos[p])} of 100 toward "${high}". Same side as ${partners}. ${tally}.`}</title>
                          </circle>
                          <text x={x} y={axisY + DOT_R + 11 + (lane[p] ?? 0) * LANE_H} textAnchor="middle"
                            className="text-3xs font-bold" style={{ fill: getPartyColor(p) }}>{p}</text>
                        </g>
                      );
                    })}
                  </svg>
                )}
              </div>
            </div>
          </button>
        );
      })}
      <p className={`${FOOTNOTE} mt-2 border-t border-border pt-2`}>
        Position: across the domain's items, the average share of each party's members taking the side at the
        right-hand end. Hover a party for its position and the parties it votes with most.
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

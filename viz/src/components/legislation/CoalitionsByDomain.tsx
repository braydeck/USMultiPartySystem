import { useMemo } from 'react';
import type { CandidateVoteRow } from '../../types';
import { F5_ORDER, PARTY_NAMES, getPartyColor } from '../../constants/parties';
import type { VoteMode } from '../../constants/labels';
import { useElementWidth } from '../../hooks/useElementWidth';
import { domainCoalitions, votingGroups, type SeatMap } from './voteBloc';
import type { Chamber } from './CoalitionMap';
import { PartyAgreement } from './PartyAgreement';
import { FOOTNOTE, MINOR_HEADING } from '../../constants/typography';

// Issue coalitions: every party keeps one column (F5_ORDER) in every domain row, and parties whose
// majorities vote the same way on every item in that domain (votingGroups) are joined. Neighbouring
// members join with a straight bar; a member further along joins with an arc under the parties it
// skips, so a bar never runs through a party outside the bundle. Scanning down a column shows a
// party changing partners from one kind of issue to the next. Selecting a domain shows its pairwise
// matrix and filters the per-bill view.

const DOT_R = 9;
const ROW_H = 30;
const ARC_DROP = 13;
const LINK = 'hsl(var(--foreground))';

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
    () => domainCoalitions(bills, seats).map((r) => ({ ...r, groups: votingGroups(r.bills) })),
    [bills, seats]);
  const sel = rows.find((r) => r.domain === domain);
  const col = (p: string) => F5_ORDER.indexOf(p as typeof F5_ORDER[number]);
  const step = trackW / F5_ORDER.length;
  const cx = (i: number) => step * (i + 0.5);

  const sameSide = (rs: CandidateVoteRow[], a: string, b: string) =>
    rs.filter((x) => ((x.parties[a]?.observedPct ?? 0) > 50) === ((x.parties[b]?.observedPct ?? 0) > 50)).length;

  return (
    <div>
      <div className="grid grid-cols-1 sm:grid-cols-[150px_1fr] gap-x-3">
        <span className="hidden sm:block" />
        <div ref={trackRef} className="grid pb-1 max-w-[640px]" style={{ gridTemplateColumns: `repeat(${F5_ORDER.length}, 1fr)` }}>
          {F5_ORDER.map((p) => (
            <span key={p} className="text-center text-3xs font-bold" style={{ color: getPartyColor(p) }} title={PARTY_NAMES[p] ?? p}>{p}</span>
          ))}
        </div>
      </div>

      <div>
        {rows.map((r) => {
          const active = r.domain === domain;
          const n = r.bills.length;
          const y = ROW_H / 2;
          const hasArc = r.groups.some((g) => g.some((p, k) => k > 0 && col(p) - col(g[k - 1]) > 1));
          const h = ROW_H + (hasArc ? ARC_DROP : 0);
          return (
            <button key={r.domain} type="button" onClick={() => onDomainChange(active ? null : r.domain)} aria-pressed={active}
              className={`w-full text-left grid grid-cols-1 sm:grid-cols-[150px_1fr] gap-x-3 items-center rounded-md border-t border-border/40 ${active ? 'ring-2 ring-foreground/70 bg-muted/40' : 'hover:bg-muted/40'}`}>
              <span className="text-2xs font-semibold leading-tight pl-1 pt-1.5 sm:pt-0">
                {r.domain}<span className="text-4xs font-normal text-muted-foreground"> · {n} {n === 1 ? 'item' : 'items'}</span>
              </span>
              {trackW > 0 && (
                <svg width={trackW} height={h} className="block overflow-visible" role="img"
                  aria-label={`${r.domain}: ${r.groups.map((g) => g.join(' ')).join('; ')}`}>
                  {r.groups.map((g) => g.slice(1).map((p, k) => {
                    const a = col(g[k]), b = col(p);
                    const x1 = cx(a), x2 = cx(b);
                    return b - a === 1
                      ? <line key={`${g[k]}-${p}`} x1={x1} x2={x2} y1={y} y2={y} stroke={LINK} strokeWidth={4} strokeLinecap="round" />
                      : <path key={`${g[k]}-${p}`} d={`M ${x1} ${y + DOT_R - 2} C ${x1} ${y + DOT_R + ARC_DROP}, ${x2} ${y + DOT_R + ARC_DROP}, ${x2} ${y + DOT_R - 2}`}
                          fill="none" stroke={LINK} strokeWidth={2.5} strokeLinecap="round" />;
                  }))}
                  {F5_ORDER.map((p, i) => {
                    const partners = F5_ORDER.filter((q) => q !== p)
                      .sort((a, b) => sameSide(r.bills, p, b) - sameSide(r.bills, p, a)).slice(0, 4)
                      .map((q) => `${q} ${sameSide(r.bills, p, q)}/${n}`).join(', ');
                    const won = r.membership[p];
                    const tally = won == null ? `no ${chamberName} seats` : `${chamberName}: on the winning side of ${Math.round(won * n)} of ${n}`;
                    return (
                      <circle key={p} cx={cx(i)} cy={y} r={DOT_R} fill={getPartyColor(p)} stroke="hsl(var(--background))" strokeWidth={2}>
                        <title>{`${PARTY_NAMES[p] ?? p}, ${r.domain}. Same side as ${partners}. ${tally}.`}</title>
                      </circle>
                    );
                  })}
                </svg>
              )}
            </button>
          );
        })}
      </div>
      <p className={`${FOOTNOTE} mt-2`}>
        Joined parties vote the same way on every item in the domain; a curve joins bundle members across
        the parties between them. Hover a party for how often it sides with each other party.
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

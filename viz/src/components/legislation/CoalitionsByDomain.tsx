import { useMemo } from 'react';
import type { CandidateVoteRow } from '../../types';
import { PARTY_NAMES, getPartyColor } from '../../constants/parties';
import type { VoteMode } from '../../constants/labels';
import { domainCoalitions, votingGroups, type SeatMap } from './voteBloc';
import type { Chamber } from './CoalitionMap';
import { PartyAgreement } from './PartyAgreement';
import { FOOTNOTE, MINOR_HEADING } from '../../constants/typography';

// Issue coalitions: for each policy domain, the parties whose majorities vote the same way on every
// item in it (votingGroups), so the regrouping from one kind of issue to the next is visible at a
// glance. Selecting a domain shows its pairwise agreement (PartyAgreement on that domain's items)
// and filters the per-bill view. Each chip's hover text carries the party's winning-side and
// needed counts in the chamber the per-bill view shows (domainCoalitions).

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
  const rows = useMemo(() => domainCoalitions(bills, seats).map((r) => ({ ...r, groups: votingGroups(r.bills) })), [bills, seats]);
  const sel = rows.find((r) => r.domain === domain);
  const chamberName = chamber === 'house' ? 'House' : 'Senate';

  return (
    <div>
      <div className="space-y-1">
        {rows.map((r) => {
          const active = r.domain === domain;
          const n = r.bills.length;
          return (
            <button key={r.domain} type="button" onClick={() => onDomainChange(active ? null : r.domain)} aria-pressed={active}
              className={`w-full text-left grid grid-cols-1 sm:grid-cols-[150px_1fr] gap-x-3 gap-y-1 items-center rounded-md px-2 py-1.5 ${active ? 'ring-2 ring-foreground/70 bg-muted/40' : 'hover:bg-muted/40'}`}>
              <span className="text-2xs font-semibold leading-tight">
                {r.domain}<span className="text-4xs font-normal text-muted-foreground"> · {n} {n === 1 ? 'item' : 'items'}</span>
              </span>
              <span className="flex flex-wrap gap-1.5">
                {r.groups.map((g) => (
                  <span key={g.join()} className="inline-flex gap-0.5 rounded-md border border-border bg-background p-0.5">
                    {g.map((p) => {
                      const won = r.membership[p], need = r.needed[p];
                      const detail = won == null
                        ? `no ${chamberName} seats`
                        : `${chamberName}: on the winning side of ${Math.round(won * n)} of ${n}, needed to pass ${Math.round((need ?? 0) * n)}`;
                      return (
                        <span key={p} className="px-1.5 py-0.5 rounded text-3xs font-bold text-white chip-text"
                          style={{ backgroundColor: getPartyColor(p) }} title={`${PARTY_NAMES[p] ?? p}, ${r.domain}. ${detail}`}>
                          {p}
                        </span>
                      );
                    })}
                  </span>
                ))}
              </span>
            </button>
          );
        })}
      </div>
      <p className={`${FOOTNOTE} mt-2`}>
        Parties boxed together vote the same way on every item in the domain. Hover a party for how often it
        ends up on the winning side in the {chamberName}.
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

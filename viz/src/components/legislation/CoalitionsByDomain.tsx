import { useMemo } from 'react';
import type { CandidateVoteRow } from '../../types';
import { F5_ORDER, PARTY_NAMES, getPartyColor } from '../../constants/parties';
import { cividisForFrac, cividisText } from '../../lib/cividis';
import { ToggleGroup } from '../shared/ToggleGroup';
import { domainCoalitions, type SeatMap } from './voteBloc';
import type { Chamber } from './CoalitionMap';
import { FOOTNOTE, TABLE_HEADER } from '../../constants/typography';

// The committee-level view of CoalitionMap: per policy domain, how often each party's whipped vote
// lands on the winning side, and how often its seats are the ones that carry a pass. Counted with
// domainCoalitions → coalitionSegments, the function the per-bill rows below draw from.

const PIVOT_RING = 'inset 0 0 0 1.5px #fff, inset 0 0 0 3px rgba(15,23,42,0.85)';
const pct = (v: number) => `${Math.round(v * 100)}`;

function Chips({ parties }: { parties: string[] }) {
  return (
    <span className="inline-flex flex-wrap gap-1 align-middle">
      {parties.map((p) => (
        <span key={p} className="px-1.5 py-px rounded text-4xs font-bold text-white chip-text" style={{ backgroundColor: getPartyColor(p) }}>{p}</span>
      ))}
    </span>
  );
}

export function CoalitionsByDomain({ bills, houseSeats, senateSeats, chamber, onChamberChange, domain, onDomainChange }: {
  bills: CandidateVoteRow[];
  houseSeats: SeatMap;
  senateSeats: SeatMap;
  chamber: Chamber;
  onChamberChange: (c: Chamber) => void;
  domain: string | null;
  onDomainChange: (d: string | null) => void;
}) {
  const seats = chamber === 'house' ? houseSeats : senateSeats;
  const rows = useMemo(() => domainCoalitions(bills, seats), [bills, seats]);
  const total = F5_ORDER.reduce((s, p) => s + (seats[p] ?? 0), 0);
  const majority = Math.floor(total / 2) + 1;
  const sel = rows.find((r) => r.domain === domain);
  const COLS = `minmax(118px,1.4fr) repeat(${F5_ORDER.length}, minmax(30px,1fr)) 44px`;

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <ToggleGroup label="Chamber" value={chamber} onChange={onChamberChange}
          options={['house', 'senate'] as const} labels={{ house: 'House', senate: 'Senate' }} />
        <span className={FOOTNOTE}>{total} seats · majority {majority}</span>
      </div>

      <div className="overflow-x-auto">
        <div className="min-w-[560px]">
          <div className={`grid gap-px items-end mb-1 ${TABLE_HEADER}`} style={{ gridTemplateColumns: COLS }}>
            <span>Domain</span>
            {F5_ORDER.map((p) => (
              <span key={p} className="text-3xs font-bold text-center normal-case tracking-normal" style={{ color: getPartyColor(p) }}
                title={`${PARTY_NAMES[p] ?? p}: ${seats[p] ?? 0} seats`}>
                {p}<span className="block font-normal text-muted-foreground tabular-nums">{seats[p] ?? 0}</span>
              </span>
            ))}
            <span className="text-center">Pass</span>
          </div>
          {rows.map((r) => {
            const active = r.domain === domain;
            return (
              <button key={r.domain} type="button" onClick={() => onDomainChange(active ? null : r.domain)}
                aria-pressed={active}
                className={`grid gap-px items-center mb-px w-full text-left rounded-sm ${active ? 'ring-2 ring-foreground/70' : 'hover:bg-muted/40'}`}
                style={{ gridTemplateColumns: COLS }}>
                <span className="text-2xs font-semibold pr-1.5 leading-tight">
                  {r.domain}<span className="block text-4xs font-normal text-muted-foreground">{r.bills.length} {r.bills.length === 1 ? 'item' : 'items'}</span>
                </span>
                {F5_ORDER.map((p) => {
                  const m = r.membership[p];
                  if (m == null) return <span key={p} className="h-9 rounded-[2px] bg-muted/30 flex items-center justify-center text-4xs text-muted-foreground">–</span>;
                  const pv = r.pivot[p] ?? 0;
                  const bg = cividisForFrac(m);
                  return (
                    <span key={p} className="h-9 rounded-[2px] flex flex-col items-center justify-center tabular-nums leading-none"
                      style={{ backgroundColor: bg, color: cividisText(bg), boxShadow: pv > 0 ? PIVOT_RING : 'none' }}
                      title={`${PARTY_NAMES[p] ?? p}, ${r.domain}: on the winning side of ${Math.round(m * r.bills.length)} of ${r.bills.length}; pivotal on ${Math.round(pv * r.bills.length)}`}>
                      <span className="text-3xs font-semibold">{pct(m)}</span>
                      {pv > 0 && <span className="text-4xs mt-0.5">{pct(pv)}</span>}
                    </span>
                  );
                })}
                <span className="text-2xs text-center tabular-nums">{r.passed}/{r.bills.length}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-3xs text-muted-foreground mt-2 pt-1.5 border-t border-border/40">
        <span className="flex items-center gap-1">
          {[0, .33, .66, 1].map((t) => <span key={t} className="w-3 h-2.5" style={{ backgroundColor: cividisForFrac(t) }} />)}
          % of the domain's items on the winning side
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-4 h-3.5 rounded-sm bg-muted-foreground/30" style={{ boxShadow: PIVOT_RING }} />
          ringed, with a second number: % of items where the party is pivotal
        </span>
      </div>

      <div className="mt-3 text-xs space-y-1.5" aria-live="polite">
        {sel ? (
          <>
            <p>
              <span className="font-semibold">{sel.domain}: </span>
              the most common winning side is <Chips parties={sel.typical.parties} />{' '}
              {sel.typical.pass ? 'voting yes' : 'voting no'}, on {sel.typical.count} of {sel.bills.length}.
            </p>
            <p className="text-muted-foreground">
              {sel.failed.length
                ? <>Fails: {sel.failed.map((b) => b.question).join('; ')}.</>
                : 'Every item in this domain passes.'}
            </p>
          </>
        ) : (
          <p className="text-muted-foreground">Select a domain to see its most common winning side and the items that fail, and to filter the bills below.</p>
        )}
      </div>
    </div>
  );
}

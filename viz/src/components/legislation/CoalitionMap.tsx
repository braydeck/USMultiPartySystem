import { useMemo } from 'react';
import type { CandidateVoteRow } from '../../types';
import { F5_ORDER, PARTY_NAMES, getPartyColor } from '../../constants/parties';

// Who combines to pass each bill. Every bill is a row; parties are stacked left→right in order
// of support (most enthusiastic first), each segment sized by its House seats. The dashed line
// is the majority (same position on every row, since seats are fixed), so every party to its
// left is the coalition that carries the bill and the one straddling it is pivotal. Faded
// segments are parties that oppose the bill (support ≤ 50%). Seat weighting follows the scenario
// controls above.

function pivotalOf(bill: CandidateVoteRow, seats: Record<string, number>, majority: number): string | null {
  const ordered = F5_ORDER
    .filter((p) => bill.parties[p] && (seats[p] ?? 0) > 0)
    .sort((a, b) => (bill.parties[b].observedPct ?? 0) - (bill.parties[a].observedPct ?? 0));
  let cum = 0;
  for (const p of ordered) { cum += seats[p] ?? 0; if (cum >= majority) return p; }
  return null;
}

function CoalitionRow({ bill, seats, total, majority }: {
  bill: CandidateVoteRow; seats: Record<string, number>; total: number; majority: number;
}) {
  const ordered = F5_ORDER
    .filter((p) => bill.parties[p] && (seats[p] ?? 0) > 0)
    .sort((a, b) => (bill.parties[b].observedPct ?? 0) - (bill.parties[a].observedPct ?? 0));
  const pivotal = pivotalOf(bill, seats, majority);
  // Passes the House when parties that actually support it (>50%) hold a strict seat majority.
  const supportingSeats = ordered
    .filter((p) => (bill.parties[p].observedPct ?? 0) > 50)
    .reduce((s, p) => s + (seats[p] ?? 0), 0);
  const passes = supportingSeats > total / 2;

  return (
    <div className="grid grid-cols-[minmax(140px,1.3fr)_2fr] gap-3 items-center py-1.5 border-t border-border/40">
      <div className="text-[11px] leading-tight flex items-start gap-1.5">
        <span className={`shrink-0 font-bold ${passes ? 'text-emerald-600' : 'text-rose-500'}`}
          title={passes ? 'Supporting parties hold a majority — passes the House' : 'Supporters fall short of a majority — fails the House'}>
          {passes ? '✓' : '✗'}
        </span>
        <span>{bill.question}</span>
      </div>
      <div className="relative h-7 rounded flex overflow-hidden bg-muted/30">
        {ordered.map((p) => {
          const s = seats[p] ?? 0;
          const w = (s / total) * 100;
          const pct = Math.round(bill.parties[p].observedPct ?? 0);
          const supports = (bill.parties[p].observedPct ?? 0) > 50;
          // A pivotal party only exists for a bill that passes — the one whose seats carry the
          // winning coalition over the line. On a defeat there is no coalition, so no ring.
          const isPivotal = passes && p === pivotal;
          return (
            <div key={p}
              className="relative flex items-center justify-center overflow-hidden chip-text"
              style={{
                width: `${w}%`,
                backgroundColor: getPartyColor(p),
                opacity: supports ? 1 : 0.4,
                boxShadow: isPivotal ? 'inset 0 0 0 1.5px #fff, inset 0 0 0 3px rgba(15,23,42,0.85)' : 'none',
              }}
              title={`${PARTY_NAMES[p] ?? p}: ${pct}% support, ${s} seats${isPivotal ? ' · pivotal' : ''}${supports ? '' : ' · opposes'}`}>
              {w >= 9 && <span className="text-[9px] font-bold text-white leading-none">{p}</span>}
            </div>
          );
        })}
        {/* majority line — white halo so it reads on any party color */}
        <div className="absolute inset-y-0 z-10" style={{ left: '50%', width: 2, backgroundColor: '#0f172a', boxShadow: '0 0 0 1.5px rgba(255,255,255,0.9)' }} />
      </div>
    </div>
  );
}

export function CoalitionMap({ candidateVotes, seats }: {
  candidateVotes: CandidateVoteRow[];
  seats: Record<string, number>;
}) {
  const total = useMemo(() => F5_ORDER.reduce((s, p) => s + (seats[p] ?? 0), 0), [seats]);
  const majority = total / 2;

  const groups = useMemo(() => {
    const g: { domain: string; rows: CandidateVoteRow[] }[] = [];
    for (const b of candidateVotes) {
      const last = g[g.length - 1];
      if (last && last.domain === b.domain) last.rows.push(b);
      else g.push({ domain: b.domain, rows: [b] });
    }
    return g;
  }, [candidateVotes]);

  return (
    <div>
      {/* party color key */}
      <div className="flex flex-wrap gap-x-2.5 gap-y-1 mb-3">
        {F5_ORDER.map((p) => (
          <span key={p} className="flex items-center gap-1 text-[10px] font-semibold" style={{ color: getPartyColor(p) }}>
            <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: getPartyColor(p) }} />{p}
          </span>
        ))}
      </div>

      <div className="hidden md:grid grid-cols-[minmax(140px,1.3fr)_2fr] gap-3 px-0 pb-1 text-[10px] text-muted-foreground uppercase tracking-widest">
        <div>Bill</div>
        <div>Parties by support · seat-weighted · ◆ = pivotal · dashed = majority</div>
      </div>

      {groups.map((g) => (
        <div key={g.domain}>
          <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/80 mt-3 mb-0.5">{g.domain}</div>
          {g.rows.map((bill) => (
            <CoalitionRow key={bill.variable} bill={bill} seats={seats} total={total} majority={majority} />
          ))}
        </div>
      ))}

      <p className="text-[11px] text-muted-foreground mt-3">
        <span className="text-emerald-600 font-bold">✓</span>/<span className="text-rose-500 font-bold">✗</span> marks
        whether the bill's supporters hold a seat majority — it passes the House. On a pass, the pivotal party
        (white/dark ring) is the one whose seats tip the winning coalition over the line; a defeat has no pivotal party.
        Faded = the party opposes the bill (support ≤ 50%).
      </p>
    </div>
  );
}

import { useMemo, useState } from 'react';
import type { CandidateVoteRow } from '../../types';
import { F5_ORDER, PARTY_NAMES, getPartyColor } from '../../constants/parties';

// Who combines to pass a given bill. Parties are stacked left→right in order of support
// (most enthusiastic first), each segment sized by its House seats. The dashed line is the
// majority; every party to its left is the coalition that carries the bill, and the one
// straddling it is pivotal. A party's segment is tinted by whether it actually backs the bill
// (support > 50%).
export function CoalitionMap({ candidateVotes, seats }: {
  candidateVotes: CandidateVoteRow[];
  seats: Record<string, number>;
}) {
  const [billVar, setBillVar] = useState(candidateVotes[0]?.variable ?? '');
  const bill = candidateVotes.find((b) => b.variable === billVar) ?? candidateVotes[0];

  const { ordered, total, pivotal, passes } = useMemo(() => {
    const total = F5_ORDER.reduce((s, p) => s + (seats[p] ?? 0), 0);
    const majority = total / 2;
    const ordered = F5_ORDER
      .filter((p) => bill?.parties[p] && (seats[p] ?? 0) > 0)
      .sort((a, b) => (bill.parties[b].observedPct ?? 0) - (bill.parties[a].observedPct ?? 0));
    let cum = 0, pivotal: string | null = null, coalitionSupports = true;
    for (const p of ordered) {
      cum += seats[p] ?? 0;
      if (pivotal == null && cum >= majority) { pivotal = p; break; }
    }
    // Does the majority-making coalition consist of parties that actually support the bill?
    let c2 = 0;
    for (const p of ordered) {
      if ((bill.parties[p].observedPct ?? 0) <= 50) coalitionSupports = false;
      c2 += seats[p] ?? 0;
      if (c2 >= majority) break;
    }
    return { ordered, total, pivotal, passes: coalitionSupports };
  }, [bill, seats]);

  const groups = useMemo(() => {
    const g: { domain: string; rows: CandidateVoteRow[] }[] = [];
    for (const b of candidateVotes) {
      const last = g[g.length - 1];
      if (last && last.domain === b.domain) last.rows.push(b);
      else g.push({ domain: b.domain, rows: [b] });
    }
    return g;
  }, [candidateVotes]);

  let cum = 0;

  return (
    <div className="space-y-3">
      <select
        value={billVar}
        onChange={(e) => setBillVar(e.target.value)}
        className="w-full sm:max-w-md text-sm border border-border rounded-md px-2 py-1.5 bg-white"
      >
        {groups.map((g) => (
          <optgroup key={g.domain} label={g.domain}>
            {g.rows.map((b) => <option key={b.variable} value={b.variable}>{b.question}</option>)}
          </optgroup>
        ))}
      </select>

      {/* Seat-weighted stack, parties ordered by support */}
      <div className="relative w-full h-12 rounded-md overflow-hidden bg-muted/30 flex">
        {ordered.map((p) => {
          const s = seats[p] ?? 0;
          const w = (s / total) * 100;
          const pct = Math.round(bill.parties[p].observedPct ?? 0);
          const supports = (bill.parties[p].observedPct ?? 0) > 50;
          const isPivotal = p === pivotal;
          cum += s;
          return (
            <div key={p}
              className="relative flex flex-col items-center justify-center overflow-hidden text-white"
              style={{
                width: `${w}%`,
                backgroundColor: getPartyColor(p),
                opacity: supports ? 1 : 0.45,
                outline: isPivotal ? '2px solid #0f172a' : 'none',
                outlineOffset: '-2px',
              }}
              title={`${PARTY_NAMES[p] ?? p}: ${pct}% support, ${s} seats${isPivotal ? ' · pivotal' : ''}`}>
              {w >= 6 && <span className="text-[10px] font-bold leading-none chip-text">{p}</span>}
              {w >= 6 && <span className="text-[9px] leading-none chip-text opacity-90">{pct}%</span>}
            </div>
          );
        })}
        {/* majority line at 50% of seats */}
        <div className="absolute inset-y-0 z-10" style={{ left: '50%', width: 2, backgroundColor: '#0f172a' }}>
          <span className="absolute -top-0 left-1 text-[9px] font-bold text-slate-900 bg-white/80 px-1 rounded">majority</span>
        </div>
      </div>

      <p className="text-[13px] text-foreground/90 leading-relaxed">
        Ordered by support, {pivotal ? <>the coalition reaches a majority at <span className="font-semibold" style={{ color: getPartyColor(pivotal) }}>{PARTY_NAMES[pivotal] ?? pivotal}</span> (pivotal)</> : 'no coalition reaches a majority'}.{' '}
        {passes
          ? 'Every party in that coalition actually backs the bill, so it passes the House on its merits.'
          : 'The majority-making coalition includes parties that oppose the bill, so passage is not clean.'}{' '}
        Faded segments are parties that oppose it (support ≤ 50%).
      </p>
    </div>
  );
}

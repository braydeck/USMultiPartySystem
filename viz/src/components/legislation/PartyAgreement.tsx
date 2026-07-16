import { useMemo } from 'react';
import type { CandidateVoteRow } from '../../types';
import { F5_ORDER, PARTY_NAMES, getPartyColor } from '../../constants/parties';
import { cividisForFrac, cividisText } from '../../lib/cividis';

// How often two parties land in the same place on policy. Similarity = 100 − the average gap
// in support across all bills, so 100 means identical positions everywhere and 0 means maximal
// disagreement. Position-based (uses each party's observed support), so it doesn't move with the
// seat/turnout controls above.
export function PartyAgreement({ candidateVotes }: { candidateVotes: CandidateVoteRow[] }) {
  const parties = F5_ORDER;

  const sim = useMemo(() => {
    const m: Record<string, Record<string, number>> = {};
    for (const a of parties) {
      m[a] = {};
      for (const c of parties) {
        let tot = 0, n = 0;
        for (const b of candidateVotes) {
          const va = b.parties[a]?.observedPct;
          const vc = b.parties[c]?.observedPct;
          if (va == null || vc == null) continue;
          tot += Math.abs(va - vc);
          n++;
        }
        m[a][c] = n ? 100 - tot / n : NaN;
      }
    }
    return m;
  }, [candidateVotes]);

  const COLS = `44px repeat(${parties.length}, minmax(30px, 1fr))`;

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[560px]">
        {/* header row */}
        <div className="grid gap-px items-end mb-px" style={{ gridTemplateColumns: COLS }}>
          <span />
          {parties.map((p) => (
            <span key={p} className="text-[10px] font-bold text-center truncate px-0.5" style={{ color: getPartyColor(p) }} title={PARTY_NAMES[p] ?? p}>{p}</span>
          ))}
        </div>
        {parties.map((row) => (
          <div key={row} className="grid gap-px items-center mb-px" style={{ gridTemplateColumns: COLS }}>
            <span className="text-[10px] font-bold text-right pr-1.5 truncate" style={{ color: getPartyColor(row) }} title={PARTY_NAMES[row] ?? row}>{row}</span>
            {parties.map((col) => {
              const v = sim[row]?.[col];
              if (v == null || Number.isNaN(v)) return <div key={col} className="h-8 rounded-[2px] bg-muted/30" />;
              if (row === col) {
                // diagonal — self; show the party color block, no number
                return <div key={col} className="h-8 rounded-[2px]" style={{ backgroundColor: getPartyColor(row) + '55' }} />;
              }
              const bg = cividisForFrac(v / 100);
              return (
                <div key={col} className="h-8 rounded-[2px] flex items-center justify-center text-[10px] font-semibold tabular-nums"
                  style={{ backgroundColor: bg, color: cividisText(bg) }}
                  title={`${PARTY_NAMES[row] ?? row} & ${PARTY_NAMES[col] ?? col} agree ${Math.round(v)}% of the time`}>
                  {Math.round(v)}
                </div>
              );
            })}
          </div>
        ))}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-muted-foreground mt-2 pt-1.5 border-t border-border/40">
          <span className="flex items-center gap-1">
            {[0, .33, .66, 1].map((t) => <span key={t} className="w-3 h-2.5" style={{ backgroundColor: cividisForFrac(t) }} />)}
            0% (opposite) → 100% (identical)
          </span>
          <span>cell = 100 − average gap in support across the bills</span>
        </div>
      </div>
    </div>
  );
}

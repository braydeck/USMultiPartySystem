import { useMemo } from 'react';
import type { CandidateVoteRow } from '../../types';
import { F5_ORDER, PARTY_NAMES, getPartyColor } from '../../constants/parties';
import { cividisForFrac, cividisText } from '../../lib/cividis';
import type { VoteMode } from '../../constants/labels';

// How often two parties land in the same place on policy. The global vote model picks the lens:
//  • Free vote → position: 100 − the average gap in support across all bills (degree of agreement).
//  • Whipped   → same-side: % of bills where both parties whip the same yes/no vote (support > 50%).
// Position-based, so it doesn't move with the seat/turnout controls above.

export function PartyAgreement({ candidateVotes, voteModel }: { candidateVotes: CandidateVoteRow[]; voteModel: VoteMode }) {
  const view: 'position' | 'binary' = voteModel === 'whipped' ? 'binary' : 'position';
  const parties = F5_ORDER;

  const { position, binary } = useMemo(() => {
    const position: Record<string, Record<string, number>> = {};
    const binary: Record<string, Record<string, number>> = {};
    for (const a of parties) {
      position[a] = {}; binary[a] = {};
      for (const c of parties) {
        let gap = 0, same = 0, n = 0;
        for (const b of candidateVotes) {
          const va = b.parties[a]?.observedPct;
          const vc = b.parties[c]?.observedPct;
          if (va == null || vc == null) continue;
          gap += Math.abs(va - vc);
          if ((va > 50) === (vc > 50)) same++;
          n++;
        }
        position[a][c] = n ? 100 - gap / n : NaN;
        binary[a][c] = n ? (same / n) * 100 : NaN;
      }
    }
    return { position, binary };
  }, [candidateVotes]);

  const M = view === 'position' ? position : binary;
  const COLS = `44px repeat(${parties.length}, minmax(30px, 1fr))`;

  return (
    <div>
      <div className="overflow-x-auto">
        <div className="min-w-[560px]">
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
                const v = M[row]?.[col];
                if (v == null || Number.isNaN(v)) return <div key={col} className="h-8 rounded-[2px] bg-muted/30" />;
                if (row === col) return <div key={col} className="h-8 rounded-[2px]" style={{ backgroundColor: getPartyColor(row) + '55' }} />;
                const bg = cividisForFrac(v / 100);
                return (
                  <div key={col} className="h-8 rounded-[2px] flex items-center justify-center text-[10px] font-semibold tabular-nums"
                    style={{ backgroundColor: bg, color: cividisText(bg) }}
                    title={`${PARTY_NAMES[row] ?? row} & ${PARTY_NAMES[col] ?? col}: ${view === 'position' ? `${Math.round(v)} similarity` : `agree ${Math.round(v)}% of the time`}`}>
                    {Math.round(v)}
                  </div>
                );
              })}
            </div>
          ))}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-muted-foreground mt-2 pt-1.5 border-t border-border/40">
            <span className="flex items-center gap-1">
              {[0, .33, .66, 1].map((t) => <span key={t} className="w-3 h-2.5" style={{ backgroundColor: cividisForFrac(t) }} />)}
              0 (opposite) → 100 (identical)
            </span>
            <span>{view === 'position' ? 'cell = 100 − average gap in support across the bills' : 'cell = % of bills where both parties predict the same yes/no vote'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

import { useMemo } from 'react';
import type { CandidateVoteRow } from '../../types';
import { PARTY_NAMES, PARTY_TAGLINES, getPartyColor } from '../../constants/parties';
import { cividisForFrac, cividisText } from '../../lib/cividis';

interface Props {
  party: string;
  candidateVotes: CandidateVoteRow[];
  onClose: () => void;
}

/** A single party's predicted votes down every bill; divergences surfaced first. */
export function CandidateColumn({ party, candidateVotes, onClose }: Props) {
  const color = getPartyColor(party);
  const rows = useMemo(() => {
    return candidateVotes
      .map((b) => ({ variable: b.variable, question: b.question, domain: b.domain, v: b.parties[party] }))
      .filter((r) => r.v)
      .sort((a, b) => {
        const da = a.v!.diverges ? 1 : 0;
        const db = b.v!.diverges ? 1 : 0;
        if (da !== db) return db - da;
        return Math.abs(b.v!.delta ?? 0) - Math.abs(a.v!.delta ?? 0);
      });
  }, [party, candidateVotes]);

  const nDiv = rows.filter((r) => r.v!.diverges).length;

  return (
    <div className="rounded-lg border border-border p-4 space-y-3" style={{ borderColor: color + '55' }}>
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded px-2 py-0.5 text-sm font-bold" style={{ backgroundColor: color + '22', color }}>{party}</span>
            <span className="font-semibold text-foreground">{PARTY_NAMES[party]}</span>
          </div>
          <p className="text-xs text-muted-foreground mt-1 max-w-xl">{PARTY_TAGLINES[party]}</p>
        </div>
        <button onClick={onClose} className="text-xs text-muted-foreground hover:text-foreground">✕ close</button>
      </div>

      <p className="text-xs text-muted-foreground">
        How a {PARTY_NAMES[party]} candidate is predicted to vote, from the party's factor position.
        {nDiv > 0 && <> {nDiv} bill{nDiv > 1 ? 's' : ''} where the candidate votes against what that position predicts (⚠, shown first).</>}
      </p>

      <div className="grid sm:grid-cols-2 gap-x-6 gap-y-1">
        {rows.map((r) => {
          const v = r.v!;
          const bg = cividisForFrac(v.pYes);
          const fg = cividisText(bg);
          return (
            <div key={r.variable} className="flex items-center gap-2 text-[11px] py-0.5">
              <span
                className="w-9 shrink-0 text-center rounded font-bold tabular-nums py-0.5"
                style={{ backgroundColor: bg, color: fg }}
              >
                {Math.round(v.pYes * 100)}
              </span>
              <span className="flex-1 leading-tight truncate" title={r.question}>{r.question}</span>
              {v.diverges && (
                <span className="shrink-0 text-[10px] font-semibold text-amber-600" title={`observed ${v.observedPct}% vs predicted ${Math.round(v.pYes * 100)}%`}>
                  ⚠ {v.delta! > 0 ? '+' : ''}{v.delta}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

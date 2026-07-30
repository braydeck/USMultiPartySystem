import { useMemo, useState } from 'react';
import type { VoteModelRow, PresidentialElection } from '../../types';
import { getBlendColor } from '../../constants/parties';
import { Button } from '@/components/ui/button';

interface Props {
  rows: VoteModelRow[];
  factorDev: PresidentialElection;
  rawMulti: PresidentialElection;
}

interface PresidentEntry {
  /** 'rawMulti' resolves by the party of `code`; 'fd' reads its own columns, because Crossover
   *  candidates are blends of two clusters and no party-keyed map covers them. */
  key: 'fd' | 'rawMulti';
  code: string;
  /** Crossover fallbacks. Unused for the party-line entry. */
  signField: keyof VoteModelRow;
  pctField: keyof VoteModelRow;
  label: string;
}

function SignBadge({ sign, pct }: { sign: string; pct?: number }) {
  const signs = sign === 'SIGN';
  return (
    <div className="flex flex-col items-center gap-0.5">
      <span className={`text-xs font-bold px-2 py-0.5 rounded border whitespace-nowrap ${
        signs ? 'bg-green-50 text-green-700 border-green-300' : 'bg-red-50 text-red-700 border-red-300'
      }`}>
        {signs ? 'Signs' : 'Vetoes'}
      </span>
      {pct !== undefined && (
        <span className="text-xs text-muted-foreground font-mono">{Math.round(pct)}%</span>
      )}
    </div>
  );
}

export function PresidentialComparison({ rows, factorDev, rawMulti }: Props) {
  const [domain, setDomain] = useState('All');
  const [showOnly, setShowOnly] = useState<'all' | 'differs'>('differs');
  const [method, setMethod] = useState<'irv' | 'condorcet'>('irv');

  const IRV_PRESIDENTS: PresidentEntry[] = [
    { key: 'fd',       code: factorDev.irvWinner,  signField: 'presFDIRVSigns',       pctField: 'presFDIRVPct',       label: 'Crossover' },
    { key: 'rawMulti', code: rawMulti.irvWinner,   signField: 'presRawMultiIRVSigns', pctField: 'presRawMultiIRVPct', label: 'Party-Line'  },
  ];
  const COND_PRESIDENTS: PresidentEntry[] = [
    { key: 'fd',       code: factorDev.condorcetWinner,  signField: 'presFDCondSigns',       pctField: 'presFDCondPct',       label: 'Crossover' },
    { key: 'rawMulti', code: rawMulti.condorcetWinner,   signField: 'presRawMultiCondSigns', pctField: 'presRawMultiCondPct', label: 'Party-Line'  },
  ];

  const presidents = method === 'irv' ? IRV_PRESIDENTS : COND_PRESIDENTS;

  const domains = useMemo(() => {
    const d = new Set(rows.map(r => r.domain));
    return ['All', ...Array.from(d).sort()];
  }, [rows]);

  // Score each row by disagreement magnitude
  const scored = useMemo(() => {
    const pres = method === 'irv' ? IRV_PRESIDENTS : COND_PRESIDENTS;
    return rows.map(r => {
      const signs = pres.map(p => p.key === 'fd'
        ? (r[p.signField] as string | undefined)
        : r.presSignsByParty?.[p.code.split('_')[0]]);
      const pcts = pres.map(p => p.key === 'fd'
        ? (r[p.pctField] as number | undefined)
        : r.presPctByParty?.[p.code.split('_')[0]]);
      const defined = signs.filter(Boolean);
      const disagreeCount = defined.length > 0
        ? defined.filter(s => s !== defined[0]).length
        : 0;
      const validPcts = pcts.filter(p => p !== undefined) as number[];
      const spread = validPcts.length > 1
        ? Math.max(...validPcts) - Math.min(...validPcts)
        : 0;
      return { row: r, disagreeCount, spread };
    });
  }, [rows, method]);

  const filtered = scored
    .filter(x => domain === 'All' || x.row.domain === domain)
    .filter(x => showOnly === 'all' || x.disagreeCount > 0)
    .sort((a, b) => b.disagreeCount - a.disagreeCount || b.spread - a.spread);

  return (
    <div>
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="flex gap-1">
          {(['irv', 'condorcet'] as const).map(m => (
            <Button
              key={m}
              onClick={() => setMethod(m)}
              variant={method === m ? 'default' : 'secondary'}
              size="sm"
            >
              {m === 'irv' ? 'IRV winners' : 'Condorcet winners'}
            </Button>
          ))}
        </div>
        <div className="flex gap-1">
          {(['all', 'differs'] as const).map(v => (
            <Button
              key={v}
              onClick={() => setShowOnly(v)}
              variant={showOnly === v ? 'default' : 'secondary'}
              size="sm"
            >
              {v === 'all' ? 'All bills' : 'Only where they differ'}
            </Button>
          ))}
        </div>
        <div className="flex flex-wrap gap-1">
          {domains.map(d => (
            <Button
              key={d}
              onClick={() => setDomain(d)}
              variant={domain === d ? 'default' : 'secondary'}
              size="sm"
            >
              {d}
            </Button>
          ))}
        </div>
      </div>

      {/* Header */}
      <div className="hidden md:grid grid-cols-[1fr_repeat(2,130px)] gap-2 px-3 py-2 border-b border-border mb-1">
        <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">Bill</div>
        {presidents.map(p => (
          <div key={p.key} className="text-center">
            <div
              className="text-xs font-bold font-mono px-2 py-0.5 rounded mx-auto inline-block"
              style={{ backgroundColor: getBlendColor(p.code) + '22', color: getBlendColor(p.code) }}
            >
              {p.code}
            </div>
            <div className="text-xs text-muted-foreground mt-0.5">{p.label}</div>
          </div>
        ))}
      </div>

      <div className="space-y-0.5">
        {filtered.map(({ row: r, disagreeCount }) => {
          const isHighlighted = disagreeCount > 0;
          return (
            <div
              key={r.variable}
              className={`flex flex-col md:grid md:grid-cols-[1fr_repeat(2,130px)] gap-2 items-start md:items-center px-3 py-2.5 rounded text-sm ${
                isHighlighted
                  ? 'bg-amber-50 border border-amber-200'
                  : 'bg-white border border-border/50'
              }`}
            >
              <div className="min-w-0">
                <div className="text-foreground text-sm">{r.question}</div>
                <div className="text-xs text-muted-foreground mt-0.5">{r.domain}</div>
              </div>
              {presidents.map(p => {
                const sign = p.key === 'fd'
                  ? (r[p.signField] as string | undefined)
                  : r.presSignsByParty?.[p.code.split('_')[0]];
                const pct = p.key === 'fd'
                  ? (r[p.pctField] as number | undefined)
                  : r.presPctByParty?.[p.code.split('_')[0]];
                return (
                  <div key={p.key} className="flex justify-center mt-1 md:mt-0">
                    {sign ? (
                      <SignBadge sign={sign} pct={pct} />
                    ) : (
                      <span className="text-slate-300 text-xs">—</span>
                    )}
                  </div>
                );
              })}
            </div>
          );
        })}
      </div>

      {filtered.length === 0 && (
        <p className="text-center text-muted-foreground text-sm py-8">
          {showOnly === 'differs' ? 'No bills where presidents disagree in this domain.' : 'No bills in this domain.'}
        </p>
      )}
    </div>
  );
}

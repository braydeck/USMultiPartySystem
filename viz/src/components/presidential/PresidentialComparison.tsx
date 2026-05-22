import { useMemo, useState } from 'react';
import type { VoteModelRow } from '../../types';
import { getBlendColor } from '../../constants/parties';

interface Props {
  rows: VoteModelRow[];
}

const PRESIDENTS = [
  { key: 'irv',       code: 'CON/SD',  signField: 'presMixedSigns',     pctField: 'presMixedPct',     label: 'CON/SD (IRV)'       },
  { key: 'condorcet', code: 'SD/CON',  signField: 'presMixedCondSigns', pctField: 'presMixedCondPct', label: 'SD/CON (Condorcet)' },
  { key: 'pure',      code: 'STY',     signField: 'presPureSigns',       pctField: 'presPurePct',      label: 'STY (Raw)'          },
  { key: 'lfCtr',     code: 'STY_ctr', signField: 'presLFSigns',         pctField: 'presLFPct',        label: 'STY_ctr (LF)'       },
] as const;

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
        <span className="text-xs text-slate-500 font-mono">{Math.round(pct)}%</span>
      )}
    </div>
  );
}

export function PresidentialComparison({ rows }: Props) {
  const [domain, setDomain] = useState('All');
  const [showOnly, setShowOnly] = useState<'all' | 'differs'>('differs');

  const domains = useMemo(() => {
    const d = new Set(rows.map(r => r.domain));
    return ['All', ...Array.from(d).sort()];
  }, [rows]);

  // Score each row by disagreement magnitude
  const scored = useMemo(() => rows.map(r => {
    const signs = PRESIDENTS.map(p => (r as any)[p.signField] as string | undefined);
    const pcts = PRESIDENTS.map(p => (r as any)[p.pctField] as number | undefined);
    const defined = signs.filter(Boolean);
    const disagreeCount = defined.length > 0
      ? defined.filter(s => s !== defined[0]).length
      : 0;
    // Max pct spread as a secondary sort key
    const validPcts = pcts.filter(p => p !== undefined) as number[];
    const spread = validPcts.length > 1
      ? Math.max(...validPcts) - Math.min(...validPcts)
      : 0;
    return { row: r, disagreeCount, spread };
  }), [rows]);

  const filtered = scored
    .filter(x => domain === 'All' || x.row.domain === domain)
    .filter(x => showOnly === 'all' || x.disagreeCount > 0)
    .sort((a, b) => b.disagreeCount - a.disagreeCount || b.spread - a.spread);

  return (
    <div>
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-3 mb-4">
        <div className="flex gap-1">
          {(['all', 'differs'] as const).map(v => (
            <button
              key={v}
              onClick={() => setShowOnly(v)}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                showOnly === v ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
              }`}
            >
              {v === 'all' ? 'All bills' : 'Only where they differ'}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-1">
          {domains.map(d => (
            <button
              key={d}
              onClick={() => setDomain(d)}
              className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                domain === d ? 'bg-slate-700 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* Header */}
      <div className="hidden md:grid grid-cols-[1fr_repeat(4,130px)] gap-2 px-3 py-2 border-b border-slate-200 mb-1">
        <div className="text-xs font-semibold text-slate-600 uppercase tracking-widest">Bill</div>
        {PRESIDENTS.map(p => (
          <div key={p.key} className="text-center">
            <div
              className="text-xs font-bold font-mono px-2 py-0.5 rounded mx-auto inline-block"
              style={{ backgroundColor: getBlendColor(p.code) + '22', color: getBlendColor(p.code) }}
            >
              {p.code}
            </div>
            <div className="text-xs text-slate-500 mt-0.5">{p.key === 'irv' ? 'IRV' : p.key === 'condorcet' ? 'Condorcet' : 'Raw'}</div>
          </div>
        ))}
      </div>

      <div className="space-y-0.5">
        {filtered.map(({ row: r, disagreeCount }) => {
          const isHighlighted = disagreeCount > 0;
          return (
            <div
              key={r.variable}
              className={`flex flex-col md:grid md:grid-cols-[1fr_repeat(4,130px)] gap-2 items-start md:items-center px-3 py-2.5 rounded text-sm ${
                isHighlighted
                  ? 'bg-amber-50 border border-amber-200'
                  : 'bg-white border border-slate-100'
              }`}
            >
              <div className="min-w-0">
                <div className="text-slate-700 text-sm">{r.question}</div>
                <div className="text-xs text-slate-500 mt-0.5">{r.domain}</div>
              </div>
              {PRESIDENTS.map(p => {
                const sign = (r as any)[p.signField] as string | undefined;
                const pct = (r as any)[p.pctField] as number | undefined;
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
        <p className="text-center text-slate-500 text-sm py-8">
          {showOnly === 'differs' ? 'No bills where presidents disagree in this domain.' : 'No bills in this domain.'}
        </p>
      )}
    </div>
  );
}

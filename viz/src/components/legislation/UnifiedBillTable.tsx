import { useState, useMemo } from 'react';
import type { VoteModelRow } from '../../types';
import { getBlendColor, getPrimaryParty } from '../../constants/parties';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface Props {
  houseRows: VoteModelRow[];
  senateRows: VoteModelRow[];
  pipeline: 'rawMulti' | 'factorDev';
  senateMethod: 'condorcet' | 'irv';
  presWinner: string;
  wyoming?: 'double' | 'triple';
}

const SENATE_PROB_FIELD: Record<string, keyof VoteModelRow> = {
  'rawMulti+condorcet':  'condRawMultiProbPass',
  'rawMulti+irv':        'irvRawMultiProbPass',
  'factorDev+condorcet': 'condFDProbPass',
  'factorDev+irv':       'irvFDProbPass',
};

const PRES_SIGN_FIELD: Record<string, keyof VoteModelRow> = {
  'rawMulti+condorcet':  'presRawMultiCondSigns',
  'rawMulti+irv':        'presRawMultiIRVSigns',
  'factorDev+condorcet': 'presFDCondSigns',
  'factorDev+irv':       'presFDIRVSigns',
};

const PRES_PCT_FIELD: Record<string, keyof VoteModelRow> = {
  'rawMulti+condorcet':  'presRawMultiCondPct',
  'rawMulti+irv':        'presRawMultiIRVPct',
  'factorDev+condorcet': 'presFDCondPct',
  'factorDev+irv':       'presFDIRVPct',
};

export type VerdictLabel =
  | 'Clearly Passes' | 'Likely Passes'   | 'Possibly Passes'
  | 'Tossup'
  | 'Possibly Fails' | 'Likely Fails'    | 'Clearly Fails';

export const VERDICT_STYLE: Record<string, { bg: string; text: string; border: string }> = {
  'Clearly Passes': { bg: '#dcfce7', text: '#15803d', border: '#86efac' },
  'Likely Passes':  { bg: '#f0fdf4', text: '#16a34a', border: '#bbf7d0' },
  'Possibly Passes':{ bg: '#ecfdf5', text: '#0f766e', border: '#99f6e4' },
  'Tossup':         { bg: '#fefce8', text: '#a16207', border: '#fde68a' },
  'Possibly Fails': { bg: '#fff7ed', text: '#c2410c', border: '#fed7aa' },
  'Likely Fails':   { bg: '#fef2f2', text: '#dc2626', border: '#fca5a5' },
  'Clearly Fails':  { bg: '#fee2e2', text: '#b91c1c', border: '#f87171' },
};

/** Single-estimate: 45–55% is a tossup zone. Multi-estimate: straddles 50% → tossup. */
export function getBayesianLabel(probs: (number | undefined)[]): VerdictLabel | '' {
  const valid = probs.filter((p): p is number => p !== undefined && p !== null);
  if (valid.length === 0) return '';
  const lo   = Math.min(...valid);
  const hi   = Math.max(...valid);
  const mean = valid.reduce((a, b) => a + b, 0) / valid.length;
  const tossup = (lo < 0.50 && hi > 0.50) ||
                 (valid.length === 1 && mean >= 0.45 && mean <= 0.55);
  if (tossup) return 'Tossup';
  if (mean > 0.50) {
    if (mean >= 0.80) return 'Clearly Passes';
    if (mean >= 0.65) return 'Likely Passes';
    return 'Possibly Passes';
  } else {
    if (mean <= 0.20) return 'Clearly Fails';
    if (mean <= 0.35) return 'Likely Fails';
    return 'Possibly Fails';
  }
}

export function getDirection(label: VerdictLabel | ''): 'pass' | 'fail' | 'uncertain' {
  if (label.includes('Passes')) return 'pass';
  if (label.includes('Fails'))  return 'fail';
  return 'uncertain';
}

export function VerdictBadge({ label }: { label: VerdictLabel | '' }) {
  if (!label) return <span className="text-muted-foreground text-xs">—</span>;
  const s = VERDICT_STYLE[label];
  return (
    <Badge
      variant="outline"
      className="whitespace-nowrap"
      style={{ backgroundColor: s.bg, color: s.text, borderColor: s.border }}
    >
      {label}
    </Badge>
  );
}

/** President sign/veto with the same graded confidence bands as the pass/fail verdicts —
 *  the sign chance is the winning party's support level, so it carries the same uncertainty.
 *  Reuses getBayesianLabel for both the grade and the color, relabeled Signs/Vetoes. */
export function SignBadge({ prob }: { prob: number | undefined }) {
  const base = getBayesianLabel([prob]);
  if (!base) return <span className="text-muted-foreground text-xs">—</span>;
  const label = base.replace('Passes', 'Signs').replace('Fails', 'Vetoes');
  const s = VERDICT_STYLE[base];
  return (
    <Badge
      variant="outline"
      className="whitespace-nowrap"
      style={{ backgroundColor: s.bg, color: s.text, borderColor: s.border }}
    >
      {label}
    </Badge>
  );
}

function ProbBar({ prob }: { prob: number | undefined }) {
  if (prob === undefined || prob === null) return <span className="text-slate-300 text-xs">—</span>;
  const pct   = Math.round(prob * 100);
  const color = prob > 0.65 ? '#22c55e' : prob > 0.50 ? '#84cc16' : prob > 0.35 ? '#f59e0b' : '#ef4444';
  return (
    <div className="flex items-center gap-1.5 min-w-[90px]">
      <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs font-mono w-7 text-right" style={{ color }}>{pct}%</span>
    </div>
  );
}

const HOUSE_PROB_FIELD: Record<string, keyof VoteModelRow> = {
  'rawMulti+double':    'houseRawMultiProbPass',
  'rawMulti+triple':    'houseRawMultiTripleProbPass',
  'factorDev+double':   'houseFDProbPass',
  'factorDev+triple':   'houseFDTripleProbPass',
};

type SortKey = 'bill' | 'house' | 'senate' | 'pres';
const GRID = 'md:grid-cols-[1fr_150px_150px_150px]';

export function UnifiedBillTable({ houseRows, senateRows, pipeline, senateMethod, presWinner, wyoming = 'double' }: Props) {
  const [domain, setDomain] = useState<string>('All');
  const [sort, setSort] = useState<{ key: SortKey; dir: 'asc' | 'desc' }>({ key: 'senate', dir: 'desc' });

  const combo          = `${pipeline}+${senateMethod}`;
  const senateProbField = SENATE_PROB_FIELD[combo];
  const houseProbField  = HOUSE_PROB_FIELD[`${pipeline}+${wyoming}`] ?? 'houseRawMultiProbPass';
  const presSignField   = PRES_SIGN_FIELD[combo];
  const presPctField    = PRES_PCT_FIELD[combo];
  const presColor       = getBlendColor(presWinner);
  const presLabel       = `President: ${getPrimaryParty(presWinner)}`;

  const houseByVar  = useMemo(() => Object.fromEntries(houseRows.map(r => [r.variable, r])),  [houseRows]);
  const senateByVar = useMemo(() => Object.fromEntries(senateRows.map(r => [r.variable, r])), [senateRows]);

  const allVars = useMemo(() => {
    const vars = new Set([...houseRows.map(r => r.variable), ...senateRows.map(r => r.variable)]);
    return Array.from(vars);
  }, [houseRows, senateRows]);

  const domains = useMemo(() => {
    const d = new Set<string>();
    for (const r of [...houseRows, ...senateRows]) d.add(r.domain);
    return ['All', ...Array.from(d).sort()];
  }, [houseRows, senateRows]);

  // Build per-bill row data: House/Senate pass probabilities + the president's sign chance.
  const rows = useMemo(() => {
    return allVars
      .filter(v => domain === 'All' || (houseByVar[v] ?? senateByVar[v])?.domain === domain)
      .map(variable => {
        const hr = houseByVar[variable];
        const sr = senateByVar[variable];
        const ref = hr ?? sr;
        const houseProb  = hr?.[houseProbField] as number | undefined;
        const senateProb = sr?.[senateProbField] as number | undefined;
        const signs      = (sr?.[presSignField] as string | undefined) ?? '';
        const presPct    = sr?.[presPctField] as number | undefined;
        // The president's coalition-support % is the chance they sign (>50% → signs).
        const presProb   = presPct !== undefined ? presPct / 100 : undefined;
        return { variable, ref, houseProb, senateProb, signs, presPct, presProb };
      })
      .filter((r): r is typeof r & { ref: VoteModelRow } => !!r.ref);
  }, [allVars, domain, houseByVar, senateByVar, houseProbField, senateProbField, presSignField, presPctField]);

  const sorted = useMemo(() => {
    const arr = [...rows];
    const dir = sort.dir === 'desc' ? -1 : 1;
    if (sort.key === 'bill') {
      arr.sort((a, b) => dir * a.ref.question.localeCompare(b.ref.question));
      return arr;
    }
    const pick = (r: typeof rows[number]) =>
      sort.key === 'house' ? r.houseProb : sort.key === 'senate' ? r.senateProb : r.presPct;
    arr.sort((a, b) => {
      const av = pick(a), bv = pick(b);
      if (av == null && bv == null) return 0;
      if (av == null) return 1;   // undefined always sorts to the bottom
      if (bv == null) return -1;
      return dir * (av - bv);
    });
    return arr;
  }, [rows, sort]);

  function toggleSort(key: SortKey) {
    setSort(s => s.key === key ? { key, dir: s.dir === 'desc' ? 'asc' : 'desc' } : { key, dir: 'desc' });
  }
  const arrow = (key: SortKey) => sort.key === key ? (sort.dir === 'desc' ? ' ↓' : ' ↑') : '';
  const sortBtn = (key: SortKey, label: string, extra = '') =>
    <button
      type="button"
      onClick={() => toggleSort(key)}
      className={`uppercase tracking-widest hover:text-foreground transition-colors ${sort.key === key ? 'text-foreground font-semibold' : ''} ${extra}`}
    >
      {label}{arrow(key)}
    </button>;

  return (
    <div>
      <div className="flex flex-wrap gap-2 mb-4">
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

      <div className={`hidden md:grid grid-cols-[1fr_150px_150px_150px] gap-x-3 items-center px-3 py-1 text-xs text-muted-foreground border-b border-border mb-1`}>
        {sortBtn('bill', 'Bill', 'text-left')}
        {sortBtn('house', 'House')}
        {sortBtn('senate', 'Senate')}
        <button
          type="button"
          onClick={() => toggleSort('pres')}
          className="uppercase tracking-widest truncate font-bold hover:opacity-80 transition-opacity"
          style={{ color: presColor }}
          title={presWinner}
        >
          {presLabel}{arrow('pres')}
        </button>
      </div>

      <div className="space-y-0.5">
        {sorted.map(({ variable, ref, houseProb, senateProb, presProb }) => {
          const houseLabel   = getBayesianLabel([houseProb]);
          const senateLabel  = getBayesianLabel([senateProb]);

          const chamberSplit = getDirection(houseLabel) !== 'uncertain' &&
                               getDirection(senateLabel) !== 'uncertain' &&
                               getDirection(houseLabel) !== getDirection(senateLabel);

          return (
            <div
              key={variable}
              className={`flex flex-col md:grid ${GRID} gap-x-3 items-start md:items-center py-2 px-3 rounded text-sm ${
                chamberSplit
                  ? 'bg-amber-50 border border-amber-200'
                  : 'bg-white border border-border/50 hover:bg-slate-50'
              }`}
            >
              <div className="min-w-0">
                <span className="text-foreground">{ref.question}</span>
                <span className="text-xs text-muted-foreground ml-2">{ref.domain}</span>
              </div>

              <div className="mt-2 md:mt-0 w-full flex items-center justify-between gap-3 border-t border-border/40 pt-2 md:border-0 md:pt-0 md:block">
                <span className="md:hidden text-xs font-semibold text-muted-foreground uppercase tracking-wide shrink-0">House</span>
                <div className="flex flex-col gap-1 items-end md:items-start">
                  <ProbBar prob={houseProb} />
                  <VerdictBadge label={houseLabel} />
                </div>
              </div>

              <div className="mt-2 md:mt-0 w-full flex items-center justify-between gap-3 border-t border-border/40 pt-2 md:border-0 md:pt-0 md:block">
                <span className="md:hidden text-xs font-semibold text-muted-foreground uppercase tracking-wide shrink-0">Senate</span>
                <div className="flex flex-col gap-1 items-end md:items-start">
                  <ProbBar prob={senateProb} />
                  <VerdictBadge label={senateLabel} />
                </div>
              </div>

              <div className="mt-2 md:mt-0 w-full flex items-center justify-between gap-3 border-t border-border/40 pt-2 md:border-0 md:pt-0 md:block">
                <span className="md:hidden text-xs font-semibold uppercase tracking-wide shrink-0" style={{ color: presColor }}>{presLabel}</span>
                {presProb !== undefined ? (
                  <div className="flex flex-col gap-1 items-end md:items-start">
                    <ProbBar prob={presProb} />
                    <SignBadge prob={presProb} />
                  </div>
                ) : (
                  <span className="text-slate-300 text-xs">—</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

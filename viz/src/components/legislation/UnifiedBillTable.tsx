import { useState, useMemo } from 'react';
import type { VoteModelRow } from '../../types';
import { getBlendColor } from '../../constants/parties';
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

export function UnifiedBillTable({ houseRows, senateRows, pipeline, senateMethod, presWinner, wyoming = 'double' }: Props) {
  const [domain, setDomain] = useState<string>('All');

  const combo          = `${pipeline}+${senateMethod}`;
  const senateProbField = SENATE_PROB_FIELD[combo];
  const houseProbField  = HOUSE_PROB_FIELD[`${pipeline}+${wyoming}`] ?? 'houseRawMultiProbPass';
  const presSignField   = PRES_SIGN_FIELD[combo];
  const presPctField    = PRES_PCT_FIELD[combo];
  const presColor       = getBlendColor(presWinner);

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

  const filtered = domain === 'All'
    ? allVars
    : allVars.filter(v => (houseByVar[v] ?? senateByVar[v])?.domain === domain);

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

      <div className="hidden md:grid grid-cols-[1fr_150px_150px_120px] gap-x-3 items-center px-3 py-1 text-xs text-muted-foreground uppercase tracking-widest border-b border-border mb-1">
        <div>Bill</div>
        <div>House</div>
        <div>Senate</div>
        <div
          className="text-center font-bold truncate"
          style={{ color: presColor }}
          title={presWinner}
        >
          {presWinner}
        </div>
      </div>

      <div className="space-y-0.5">
        {filtered.map(variable => {
          const hr  = houseByVar[variable];
          const sr  = senateByVar[variable];
          const ref = hr ?? sr;
          if (!ref) return null;

          const houseProb    = hr?.[houseProbField] as number | undefined;
          const houseLabel   = getBayesianLabel([houseProb]);
          const senateProb   = sr?.[senateProbField] as number | undefined;
          const senateLabel  = getBayesianLabel([senateProb]);
          const signs        = (sr?.[presSignField] as string | undefined) ?? '';
          const presPct      = sr?.[presPctField] as number | undefined;

          const chamberSplit = getDirection(houseLabel) !== 'uncertain' &&
                               getDirection(senateLabel) !== 'uncertain' &&
                               getDirection(houseLabel) !== getDirection(senateLabel);

          return (
            <div
              key={variable}
              className={`flex flex-col md:grid md:grid-cols-[1fr_150px_150px_120px] gap-x-3 items-start md:items-center py-2 px-3 rounded text-sm ${
                chamberSplit
                  ? 'bg-amber-50 border border-amber-200'
                  : 'bg-white border border-border/50 hover:bg-slate-50'
              }`}
            >
              <div className="min-w-0">
                <span className="text-foreground">{ref.question}</span>
                <span className="text-xs text-muted-foreground ml-2">{ref.domain}</span>
              </div>

              <div className="mt-1 md:mt-0 flex flex-col gap-1">
                <ProbBar prob={houseProb} />
                <VerdictBadge label={houseLabel} />
              </div>

              <div className="mt-1 md:mt-0 flex flex-col gap-1">
                <ProbBar prob={senateProb} />
                <VerdictBadge label={senateLabel} />
              </div>

              <div className="mt-1 md:mt-0 flex flex-col items-center gap-0.5">
                {signs ? (
                  <>
                    <span
                      className="text-xs font-bold px-2 py-0.5 rounded border whitespace-nowrap"
                      style={
                        signs === 'SIGN'
                          ? { backgroundColor: presColor + '18', color: presColor, borderColor: presColor + '55' }
                          : { backgroundColor: '#fef2f2', color: '#b91c1c', borderColor: '#fca5a5' }
                      }
                    >
                      {signs === 'SIGN' ? 'Signs' : 'Vetoes'}
                    </span>
                    {presPct !== undefined && (
                      <span className="text-xs text-muted-foreground font-mono">{Math.round(presPct)}%</span>
                    )}
                  </>
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

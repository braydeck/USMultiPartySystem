import { useState, useMemo } from 'react';
import type { VoteModelRow } from '../../types';

interface Props {
  houseRows: VoteModelRow[];
  senateRows: VoteModelRow[];
  pipeline: 'rawMulti' | 'factorDev';
  senateMethod: 'condorcet' | 'irv';
}

const SENATE_PROB_FIELD: Record<string, keyof VoteModelRow> = {
  'rawMulti+condorcet':  'condRawMultiProbPass',
  'rawMulti+irv':        'irvRawMultiProbPass',
  'factorDev+condorcet': 'condFDProbPass',
  'factorDev+irv':       'irvFDProbPass',
};

const SENATE_VERDICT_FIELD: Record<string, keyof VoteModelRow> = {
  'rawMulti+condorcet':  'condRawMultiVerdict',
  'rawMulti+irv':        'irvRawMultiVerdict',
  'factorDev+condorcet': 'condFDVerdict',
  'factorDev+irv':       'irvFDVerdict',
};

const PRES_SIGNS_FIELD: Record<string, keyof VoteModelRow> = {
  'rawMulti+condorcet':  'presRawMultiCondSigns',
  'rawMulti+irv':        'presRawMultiIRVSigns',
  'factorDev+condorcet': 'presFDCondSigns',
  'factorDev+irv':       'presFDIRVSigns',
};

const PRES_LABEL: Record<string, string> = {
  'rawMulti+condorcet':  'CTR_1',
  'rawMulti+irv':        'SD_1',
  'factorDev+condorcet': 'CTR_lo_pc',
  'factorDev+irv':       'SD_lo_pc',
};

function ProbBar({ prob }: { prob: number }) {
  const pct = Math.round(prob * 100);
  const color = prob > 0.7 ? '#22c55e' : prob > 0.3 ? '#f59e0b' : '#ef4444';
  return (
    <div className="flex items-center gap-2 min-w-[90px]">
      <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-xs font-mono w-7 text-right" style={{ color }}>{pct}%</span>
    </div>
  );
}

function VerdictBadge({ verdict }: { verdict: string }) {
  const cls =
    verdict === 'PASS' ? 'bg-green-50 text-green-700 border-green-300' :
    verdict === 'FAIL' ? 'bg-red-50 text-red-700 border-red-300' :
    'bg-yellow-50 text-yellow-700 border-yellow-300';
  return (
    <span className={`text-xs font-bold px-1.5 py-0.5 rounded border whitespace-nowrap ${cls}`}>
      {verdict}
    </span>
  );
}

export function UnifiedBillTable({ houseRows, senateRows, pipeline, senateMethod }: Props) {
  const [domain, setDomain] = useState<string>('All');

  const combo = `${pipeline}+${senateMethod}` as keyof typeof SENATE_PROB_FIELD;
  const senateProbField = SENATE_PROB_FIELD[combo];
  const senateVerdictField = SENATE_VERDICT_FIELD[combo];
  const presSignsField = PRES_SIGNS_FIELD[combo];
  const presLabel = PRES_LABEL[combo];

  const houseByVar = useMemo(() => Object.fromEntries(houseRows.map(r => [r.variable, r])), [houseRows]);
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
          <button
            key={d}
            onClick={() => setDomain(d)}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              domain === d
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-200 text-slate-700 hover:bg-slate-300'
            }`}
          >
            {d}
          </button>
        ))}
      </div>

      <div className="hidden md:grid grid-cols-[1fr_auto_auto_auto_auto_auto] gap-x-3 items-center px-3 py-1 text-xs text-slate-600 uppercase tracking-widest border-b border-slate-200 mb-1">
        <div>Bill</div>
        <div className="w-24 text-right">House</div>
        <div className="w-14 text-right">Verdict</div>
        <div className="w-24 text-right">Senate</div>
        <div className="w-14 text-right">Verdict</div>
        <div className="w-20 text-center">Pres: {presLabel}</div>
      </div>

      <div className="space-y-0.5">
        {filtered.map(variable => {
          const hr = houseByVar[variable];
          const sr = senateByVar[variable];
          const ref = hr ?? sr;
          if (!ref) return null;

          const hVerdict = hr?.verdict ?? '—';
          const hProb    = hr?.probPass ?? 0;
          const sVerdict = (sr?.[senateVerdictField] as string | undefined) ?? '—';
          const signs = (sr?.[presSignsField] as string | undefined) ?? '—';
          const disagrees = hVerdict !== '—' && sVerdict !== '—' && hVerdict !== sVerdict;

          return (
            <div
              key={variable}
              className={`flex flex-col md:grid md:grid-cols-[1fr_auto_auto_auto_auto_auto] gap-x-3 items-start md:items-center py-2 px-3 rounded text-sm ${
                disagrees ? 'bg-amber-50 border border-amber-300' : 'bg-white border border-slate-100 hover:bg-slate-50'
              }`}
            >
              <div className="min-w-0">
                <span className="text-slate-700">{ref.question}</span>
                <span className="text-xs text-slate-500 ml-2">{ref.domain}</span>
              </div>

              {/* House */}
              <div className="w-24 mt-1 md:mt-0">
                {hr ? <ProbBar prob={hProb} /> : <span className="text-slate-300 text-xs">—</span>}
              </div>
              <div className="w-14">
                {hVerdict !== '—' ? <VerdictBadge verdict={hVerdict} /> : <span className="text-slate-300 text-xs">—</span>}
              </div>

              {/* Senate (scenario-driven) */}
              <div className="w-24 mt-1 md:mt-0">
                {sr && senateProbField ? <ProbBar prob={sr[senateProbField] as number} /> : <span className="text-slate-300 text-xs">—</span>}
              </div>
              <div className="w-14">
                {sVerdict !== '—' ? <VerdictBadge verdict={sVerdict} /> : <span className="text-slate-300 text-xs">—</span>}
              </div>

              {/* Presidency */}
              <div className="w-20 text-center">
                {signs !== '—' ? (
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${
                    signs === 'SIGN'
                      ? 'bg-green-50 text-green-700 border-green-300'
                      : 'bg-red-50 text-red-700 border-red-300'
                  }`}>
                    {signs === 'SIGN' ? 'Signs' : 'Vetoes'}
                  </span>
                ) : <span className="text-slate-300 text-xs">—</span>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

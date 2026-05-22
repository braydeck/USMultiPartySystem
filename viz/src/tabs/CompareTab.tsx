import { useState } from 'react';
import type { ClusterProfile, BlendProfile } from '../types';
import { getBlendColor, PARTY_NAMES, F5_ORDER } from '../constants/parties';

interface Props {
  clusters: ClusterProfile[];
  blendProfiles: BlendProfile[];
}

const DOMAINS = [
  'Taxes & Economy',
  'Immigration',
  'Police & Guns',
  'Abortion',
  'Environment & Climate',
  'Healthcare & Housing',
  'Civil Liberties',
  'Elections & Trust',
  'Racial & Gender',
  'Religion',
  'Demographics',
];

interface VarEntry {
  key: string;
  question: string;
  pcts: Record<string, number>;
  maxGap: number;
}

function getVariables(
  code: string,
  clusters: ClusterProfile[],
  blendProfiles: BlendProfile[],
): Record<string, { pct: number; question: string; domain: string }> {
  const cluster = clusters.find(c => c.party === code);
  if (cluster) return cluster.variables as Record<string, { pct: number; question: string; domain: string }>;
  const bp = blendProfiles.find(p => p.code === code);
  if (bp?.variables) return bp.variables as Record<string, { pct: number; question: string; domain: string }>;
  return {};
}

export function CompareTab({ clusters, blendProfiles }: Props) {
  const [selected, setSelected] = useState<string[]>([]);
  const [activeDomain, setActiveDomain] = useState<string>(DOMAINS[0]);
  const [minGap, setMinGap] = useState(15);

  // Build option list: pure parties in F5_ORDER, then blended codes sorted by seats
  const pureOptions = F5_ORDER
    .filter(code => clusters.some(c => c.party === code))
    .map(code => ({ code, label: PARTY_NAMES[code] ?? code }));

  const blendOptions = blendProfiles
    .filter(p => !p.isPure && (p.seatsCond > 0 || p.seatsIRV > 0))
    .sort((a, b) => (b.seatsCond + b.seatsIRV) - (a.seatsCond + a.seatsIRV))
    .map(p => ({ code: p.code, label: p.code }));

  const addParty = (code: string) => {
    if (selected.length >= 3 || selected.includes(code)) return;
    setSelected(prev => [...prev, code]);
  };

  const removeParty = (code: string) => {
    setSelected(prev => prev.filter(c => c !== code));
  };

  const getVarsForDomain = (domain: string): VarEntry[] => {
    if (selected.length < 2) return [];

    const varMap = new Map<string, { question: string; pcts: Record<string, number> }>();
    for (const code of selected) {
      const vars = getVariables(code, clusters, blendProfiles);
      for (const [key, v] of Object.entries(vars)) {
        if (v.domain !== domain) continue;
        if (!varMap.has(key)) varMap.set(key, { question: v.question, pcts: {} });
        varMap.get(key)!.pcts[code] = v.pct;
      }
    }

    const result: VarEntry[] = [];
    for (const [key, entry] of varMap) {
      const pcts = selected.map(c => entry.pcts[c]).filter(v => v !== undefined) as number[];
      if (pcts.length < 2) continue;
      const maxGap = Math.max(...pcts) - Math.min(...pcts);
      if (maxGap < minGap) continue;
      result.push({ key, question: entry.question, pcts: entry.pcts, maxGap });
    }
    return result.sort((a, b) => b.maxGap - a.maxGap);
  };

  const domainVars = getVarsForDomain(activeDomain);

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 mb-1">Party Comparison</h2>
        <p className="text-slate-500 text-sm">
          Compare up to 3 parties side-by-side across 7 policy domains. Only positions
          where parties diverge are shown — sorted by largest gap first.
        </p>
      </div>

      {/* Party selector */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="text-sm font-semibold text-slate-700 mb-3">Select up to 3 parties to compare</div>
        <div className="flex items-center gap-2 flex-wrap">
          {selected.map(code => {
            const color = getBlendColor(code);
            const label = PARTY_NAMES[code] ?? code;
            return (
              <span
                key={code}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-semibold text-white"
                style={{ backgroundColor: color }}
              >
                {code}
                <span className="font-normal opacity-75 text-xs hidden sm:inline">— {label}</span>
                <button
                  onClick={() => removeParty(code)}
                  className="ml-0.5 opacity-70 hover:opacity-100 leading-none"
                  aria-label={`Remove ${code}`}
                >
                  ×
                </button>
              </span>
            );
          })}
          {selected.length < 3 && (
            <select
              className="text-sm border border-slate-200 rounded px-2 py-1.5 text-slate-700 bg-white"
              value=""
              onChange={e => { if (e.target.value) addParty(e.target.value); }}
            >
              <option value="">+ Add party</option>
              {pureOptions.filter(o => !selected.includes(o.code)).length > 0 && (
                <optgroup label="Pure parties">
                  {pureOptions.filter(o => !selected.includes(o.code)).map(o => (
                    <option key={o.code} value={o.code}>{o.code} — {o.label}</option>
                  ))}
                </optgroup>
              )}
              {blendOptions.filter(o => !selected.includes(o.code)).length > 0 && (
                <optgroup label="Blended (senate)">
                  {blendOptions.filter(o => !selected.includes(o.code)).map(o => (
                    <option key={o.code} value={o.code}>{o.code}</option>
                  ))}
                </optgroup>
              )}
            </select>
          )}
        </div>
        {selected.length === 0 && (
          <p className="text-xs text-slate-400 mt-2">
            Try: PRG + NAT (maximum divergence) · SD + CON (presidential rivals) · CON + REF + NAT (right coalition)
          </p>
        )}
      </div>

      {selected.length >= 2 ? (
        <>
          {/* Domain tabs + gap filter */}
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex gap-1 flex-wrap flex-1">
            {DOMAINS.map(d => {
              const count = getVarsForDomain(d).length;
              return (
                <button
                  key={d}
                  onClick={() => setActiveDomain(d)}
                  className={`px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                    activeDomain === d
                      ? 'bg-indigo-600 text-white'
                      : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'
                  }`}
                >
                  {d}
                  {count > 0 && (
                    <span className={`ml-1.5 text-xs rounded-full px-1.5 py-0.5 ${
                      activeDomain === d ? 'bg-white/20 text-white' : 'bg-slate-100 text-slate-500'
                    }`}>
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
            </div>
            <label className="flex items-center gap-1.5 text-xs text-slate-500 whitespace-nowrap ml-auto">
              Min gap
              <input
                type="number"
                min={0}
                max={100}
                value={minGap}
                onChange={e => setMinGap(Math.max(0, Math.min(100, Number(e.target.value))))}
                className="w-14 border border-slate-200 rounded px-2 py-1 text-center font-mono text-slate-700 bg-white"
              />
              pp
            </label>
          </div>

          {/* Variable table */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            {domainVars.length === 0 ? (
              <div className="px-4 py-8 text-center text-slate-400 text-sm">
                No significant differences in {activeDomain}
                <span className="block text-xs mt-1 text-slate-300">(all parties within {minGap}pp of each other)</span>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50">
                    <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 w-1/2">
                      Policy Question
                    </th>
                    {selected.map(code => {
                      const color = getBlendColor(code);
                      return (
                        <th key={code} className="px-3 py-2.5 text-center text-xs font-bold" style={{ color }}>
                          {code}
                        </th>
                      );
                    })}
                    <th className="px-3 py-2.5 text-center text-xs font-semibold text-slate-400">Gap</th>
                  </tr>
                </thead>
                <tbody>
                  {domainVars.map(v => {
                    const pctsPresent = selected.map(c => v.pcts[c]).filter((p): p is number => p !== undefined);
                    const maxPct = Math.max(...pctsPresent);
                    const minPct = Math.min(...pctsPresent);
                    return (
                      <tr key={v.key} className="border-b border-slate-100 last:border-0 hover:bg-slate-50/60">
                        <td className="px-4 py-2.5 text-slate-700 text-xs leading-snug">{v.question}</td>
                        {selected.map(code => {
                          const pct = v.pcts[code];
                          const color = getBlendColor(code);
                          if (pct === undefined) {
                            return <td key={code} className="px-3 py-2.5 text-center text-slate-300 text-xs">—</td>;
                          }
                          const isMax = pct === maxPct && maxPct !== minPct;
                          const isMin = pct === minPct && maxPct !== minPct;
                          return (
                            <td key={code} className="px-3 py-2.5 text-center">
                              <div
                                className={`font-mono text-sm font-semibold ${isMax ? '' : isMin ? '' : 'text-slate-500'}`}
                                style={{ color: isMax || isMin ? color : undefined }}
                              >
                                {Math.round(pct)}%
                              </div>
                              <div className="h-1 bg-slate-100 rounded-full mt-1 mx-1">
                                <div
                                  className="h-full rounded-full transition-all"
                                  style={{ width: `${pct}%`, backgroundColor: color, opacity: 0.65 }}
                                />
                              </div>
                            </td>
                          );
                        })}
                        <td className="px-3 py-2.5 text-center text-xs text-slate-400 font-mono">
                          {v.maxGap.toFixed(0)}pp
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <div className="text-slate-400 text-sm">Select at least 2 parties above to compare policy positions</div>
          <div className="text-slate-300 text-xs mt-2">
            Positions shown only where parties diverge by ≥{minGap}pp. Sorted by largest gap.
          </div>
        </div>
      )}
    </div>
  );
}

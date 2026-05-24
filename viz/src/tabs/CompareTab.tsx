import { useState, useMemo } from 'react';
import type { ClusterProfile, FDCandidateProfile } from '../types';
import { getBlendColor, PARTY_NAMES, F5_ORDER, VAR_FACTOR, FACTOR_SHORT, FACTOR_LABELS } from '../constants/parties';

interface Props {
  clusters: ClusterProfile[];
  fdProfiles: Record<string, FDCandidateProfile>;
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

const FACTORS = ['F1', 'F2', 'F3', 'F4', 'F5'] as const;
type FactorKey = typeof FACTORS[number];

interface VarEntry {
  key: string;
  question: string;
  pcts: Record<string, number>;
  maxGap: number;
  highlighted: boolean;
  factor: string | null;
}

function getVariables(
  code: string,
  clusters: ClusterProfile[],
  fdProfiles: Record<string, FDCandidateProfile>,
): Record<string, { pct: number; question: string; domain: string }> {
  const cluster = clusters.find(c => c.party === code);
  if (cluster) return cluster.variables as Record<string, { pct: number; question: string; domain: string }>;
  const fdp = fdProfiles[code];
  if (fdp?.variables) return fdp.variables as Record<string, { pct: number; question: string; domain: string }>;
  return {};
}

function getFactorScores(
  code: string,
  clusters: ClusterProfile[],
  fdProfiles: Record<string, FDCandidateProfile>,
): Record<FactorKey, number> | null {
  const cluster = clusters.find(c => c.party === code);
  if (cluster) return { F1: cluster.F1, F2: cluster.F2, F3: cluster.F3, F4: cluster.F4, F5: cluster.F5 };
  const fdp = fdProfiles[code];
  if (fdp) return { F1: fdp.F1, F2: fdp.F2, F3: fdp.F3, F4: fdp.F4, F5: fdp.F5 };
  return null;
}

function factorTier(val: number): string {
  if (val > 0.75)  return 'Very High';
  if (val > 0.25)  return 'High';
  if (val > -0.25) return 'Medium';
  if (val > -0.75) return 'Low';
  return 'Very Low';
}

function getSectionTitle(key: string): string {
  if (key === 'Untagged') return 'Other / Untagged';
  if ((FACTORS as readonly string[]).includes(key)) return `${FACTOR_LABELS[key]} (${FACTOR_SHORT[key]})`;
  return key;
}

export function CompareTab({ clusters, fdProfiles }: Props) {
  const [selected, setSelected] = useState<string[]>([]);
  const [minGap, setMinGap] = useState(15);
  const [activeFactors, setActiveFactors] = useState<Set<string>>(new Set());
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set(['Untagged']));
  const [groupBy, setGroupBy] = useState<'category' | 'factor'>('category');

  // Build option list: pure parties in F5_ORDER, then FD candidates grouped by party
  const pureOptions = F5_ORDER
    .filter(code => clusters.some(c => c.party === code))
    .map(code => ({ code, label: PARTY_NAMES[code] ?? code }));

  const fdOptions = Object.entries(fdProfiles)
    .sort((a, b) => {
      const ai = F5_ORDER.indexOf(a[1].party as typeof F5_ORDER[number]);
      const bi = F5_ORDER.indexOf(b[1].party as typeof F5_ORDER[number]);
      if (ai !== bi) return ai - bi;
      return a[0].localeCompare(b[0]);
    })
    .map(([code]) => ({ code, label: code }));

  const addParty = (code: string) => {
    if (selected.length >= 4 || selected.includes(code)) return;
    setSelected(prev => [...prev, code]);
  };

  const removeParty = (code: string) => {
    setSelected(prev => prev.filter(c => c !== code));
  };

  const toggleFactor = (f: string) => {
    setActiveFactors(prev => {
      const next = new Set(prev);
      if (next.has(f)) next.delete(f); else next.add(f);
      return next;
    });
  };

  const toggleSection = (key: string) => {
    setCollapsedSections(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  };

  // Build vars grouped by category or factor
  const sectionVarMap = useMemo((): Record<string, VarEntry[]> => {
    if (selected.length < 2) return {};

    const varMap = new Map<string, { question: string; domain: string; pcts: Record<string, number> }>();
    for (const code of selected) {
      const vars = getVariables(code, clusters, fdProfiles);
      for (const [key, v] of Object.entries(vars)) {
        if (!varMap.has(key)) varMap.set(key, { question: v.question, domain: v.domain, pcts: {} });
        varMap.get(key)!.pcts[code] = v.pct;
      }
    }

    const grouped: Record<string, VarEntry[]> = {};
    for (const [key, entry] of varMap) {
      const pcts = selected.map(c => entry.pcts[c]).filter((v): v is number => v !== undefined);
      if (pcts.length < 2) continue;
      const maxGap = Math.max(...pcts) - Math.min(...pcts);
      const factor = VAR_FACTOR[key] ?? null;

      const groupKey = groupBy === 'factor'
        ? (factor ?? 'Untagged')
        : entry.domain;

      // Factor filter only applies in category mode
      if (groupBy === 'category' && activeFactors.size > 0 && !activeFactors.has(factor ?? '')) continue;

      if (!grouped[groupKey]) grouped[groupKey] = [];
      grouped[groupKey].push({ key, question: entry.question, pcts: entry.pcts, maxGap, highlighted: maxGap >= minGap, factor });
    }

    for (const key of Object.keys(grouped)) {
      grouped[key].sort((a, b) => {
        if (a.highlighted !== b.highlighted) return a.highlighted ? -1 : 1;
        return b.maxGap - a.maxGap;
      });
    }

    return grouped;
  }, [selected, clusters, fdProfiles, minGap, activeFactors, groupBy]);

  // Ordered section keys
  const sectionKeys = useMemo(() => {
    if (groupBy === 'category') {
      return DOMAINS.filter(d => (sectionVarMap[d]?.length ?? 0) > 0);
    }
    const factorKeys = FACTORS.filter(f => (sectionVarMap[f]?.length ?? 0) > 0);
    const hasUntagged = (sectionVarMap['Untagged']?.length ?? 0) > 0;
    return [...factorKeys, ...(hasUntagged ? ['Untagged'] : [])];
  }, [sectionVarMap, groupBy]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-900 mb-1">Party Comparison</h2>
        <p className="text-slate-500 text-sm">
          Compare up to 3 parties side-by-side across all policy domains. Amber rows highlight where
          parties differ by ≥{minGap}pp and sort to the top of each section.
        </p>
      </div>

      {/* Party selector */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="text-sm font-semibold text-slate-700 mb-3">Select up to 4 parties to compare</div>
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
          {selected.length < 4 && (
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
              {fdOptions.filter(o => !selected.includes(o.code)).length > 0 && (
                <optgroup label="Factor Deviation candidates">
                  {fdOptions.filter(o => !selected.includes(o.code)).map(o => (
                    <option key={o.code} value={o.code}>{o.code}</option>
                  ))}
                </optgroup>
              )}
            </select>
          )}
        </div>
        {selected.length === 0 && (
          <p className="text-xs text-slate-400 mt-2">
            Try: PRG + NAT (maximum divergence) · SD + CON (presidential rivals) · SD_hi_so + SD (factor deviation vs base)
          </p>
        )}
      </div>

      {selected.length >= 2 && (
        <>
          {/* Factor scores */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100 bg-slate-50">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Factor Scores</span>
              <span className="text-xs text-slate-400 ml-3">Tiers: Very High &gt;+0.75 · High +0.25 · Medium ±0.25 · Low −0.25 · Very Low &lt;−0.75</span>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="px-4 py-2 text-left text-xs font-semibold text-slate-400 w-2/5">Factor</th>
                  {selected.map(code => (
                    <th key={code} className="px-3 py-2 text-center text-xs font-bold" style={{ color: getBlendColor(code) }}>
                      {code}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {FACTORS.map(f => (
                  <tr key={f} className="border-t border-slate-50">
                    <td className="px-4 py-2.5">
                      <div className="text-xs font-semibold text-slate-700">{FACTOR_LABELS[f]}</div>
                      <div className="text-[10px] text-slate-400 font-mono">{FACTOR_SHORT[f]}</div>
                    </td>
                    {selected.map(code => {
                      const scores = getFactorScores(code, clusters, fdProfiles);
                      const val = scores?.[f];
                      if (val === undefined) return <td key={code} className="px-3 py-2.5 text-center text-slate-300 text-xs">—</td>;
                      const tier = factorTier(val);
                      const color = getBlendColor(code);
                      // Bar centered at 0, range −2 to +2
                      const pct = ((val + 2) / 4) * 100;
                      const barLeft = val >= 0 ? 50 : pct;
                      const barWidth = Math.abs(pct - 50);
                      return (
                        <td key={code} className="px-3 py-2.5">
                          <div className="text-center text-xs text-slate-700 font-medium">{tier}</div>
                          <div className="text-center text-[10px] font-mono text-slate-400">
                            {val >= 0 ? '+' : ''}{val.toFixed(2)}
                          </div>
                          <div className="h-1.5 bg-slate-100 rounded-full mt-1 mx-2 relative">
                            <div
                              className="absolute h-full rounded-full"
                              style={{ left: `${barLeft}%`, width: `${barWidth}%`, backgroundColor: color, opacity: 0.72 }}
                            />
                            <div className="absolute top-0 bottom-0 left-1/2 w-px bg-slate-300" />
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Controls: group by + factor filter (category mode only) + highlight threshold */}
          <div className="flex flex-wrap items-start gap-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 uppercase tracking-widest">Group by</span>
              {(['category', 'factor'] as const).map(g => (
                <button
                  key={g}
                  onClick={() => setGroupBy(g)}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                    groupBy === g ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {g === 'category' ? 'Category' : 'Factor'}
                </button>
              ))}
            </div>

            {groupBy === 'category' && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-slate-500 uppercase tracking-widest">Filter</span>
                <button
                  onClick={() => setActiveFactors(new Set())}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                    activeFactors.size === 0 ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  All
                </button>
                {FACTORS.map(f => (
                  <button
                    key={f}
                    onClick={() => toggleFactor(f)}
                    className={`px-2.5 py-1 rounded text-xs font-medium transition-colors ${
                      activeFactors.has(f) ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {FACTOR_LABELS[f]} ({FACTOR_SHORT[f]})
                  </button>
                ))}
              </div>
            )}

            <label className="flex items-center gap-1.5 text-xs text-slate-500 whitespace-nowrap ml-auto">
              Highlight gap ≥
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

          {/* Sections */}
          {sectionKeys.length === 0 ? (
            <div className="bg-white rounded-xl border border-slate-200 p-8 text-center text-slate-400 text-sm">
              No variables match the selected filter.
            </div>
          ) : (
            <div className="space-y-3">
              {sectionKeys.map(sectionKey => {
                const vars = sectionVarMap[sectionKey] ?? [];
                const collapsed = collapsedSections.has(sectionKey);
                const highlightCount = vars.filter(v => v.highlighted).length;

                return (
                  <div key={sectionKey} className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                    <button
                      className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 transition-colors text-left"
                      onClick={() => toggleSection(sectionKey)}
                    >
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-semibold text-slate-700">{getSectionTitle(sectionKey)}</span>
                        <span className="text-xs bg-slate-100 text-slate-500 rounded-full px-2 py-0.5">{vars.length}</span>
                        {highlightCount > 0 && (
                          <span className="text-xs bg-amber-100 text-amber-700 font-medium rounded-full px-2 py-0.5">
                            {highlightCount} diverge
                          </span>
                        )}
                      </div>
                      <span className="text-slate-400 text-xs flex-shrink-0 ml-2">{collapsed ? '▶' : '▼'}</span>
                    </button>

                    {!collapsed && (
                      <table className="w-full text-sm border-t border-slate-100">
                        <thead>
                          <tr className="bg-slate-50">
                            <th className="px-4 py-2.5 text-left text-xs font-semibold text-slate-500 w-1/2">
                              Policy Question
                            </th>
                            {selected.map(code => (
                              <th key={code} className="px-3 py-2.5 text-center text-xs font-bold" style={{ color: getBlendColor(code) }}>
                                {code}
                              </th>
                            ))}
                            <th className="px-3 py-2.5 text-center text-xs font-semibold text-slate-400">Gap</th>
                          </tr>
                        </thead>
                        <tbody>
                          {vars.map(v => {
                            const pctsPresent = selected.map(c => v.pcts[c]).filter((p): p is number => p !== undefined);
                            const maxPct = Math.max(...pctsPresent);
                            const minPct = Math.min(...pctsPresent);
                            return (
                              <tr
                                key={v.key}
                                className={`border-t border-slate-100 ${v.highlighted ? 'bg-amber-50' : 'hover:bg-slate-50/60'}`}
                              >
                                <td className="px-4 py-2.5 text-slate-700 text-xs leading-snug">
                                  {v.factor && (
                                    <span className="inline-block text-[10px] font-bold px-1 py-0.5 rounded mr-1.5 bg-slate-100 text-slate-500 align-middle">
                                      {FACTOR_SHORT[v.factor]}
                                    </span>
                                  )}
                                  {v.question}
                                </td>
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
                                        className="font-mono text-sm font-semibold"
                                        style={{ color: isMax || isMin ? color : '#64748b' }}
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
                                <td className={`px-3 py-2.5 text-center text-xs font-mono ${v.highlighted ? 'text-amber-600 font-semibold' : 'text-slate-400'}`}>
                                  {v.maxGap.toFixed(0)}pp
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}

      {selected.length < 2 && (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <div className="text-slate-400 text-sm">Select at least 2 parties above to compare policy positions</div>
          <div className="text-slate-300 text-xs mt-2">
            All variables shown — amber rows highlight where parties diverge by ≥{minGap}pp.
          </div>
        </div>
      )}
    </div>
  );
}

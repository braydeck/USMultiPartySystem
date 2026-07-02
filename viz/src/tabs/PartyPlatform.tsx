import { useMemo, useState } from 'react';
import type { ClusterProfile } from '../types';
import { useUrlState } from '../hooks/useUrlState';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER, getContrastText } from '../constants/parties';
import { useSignatureFilter } from '../hooks/useSignatureFilter';
import { SignatureFilters } from '../components/shared/SignatureFilters';
import { PartySelector } from '../components/shared/PartySelector';
import { IdeologicalConstellation } from '../components/house/IdeologicalConstellation';
import { buildSubgroups, stripPrefix } from '../lib/subgroups';
import { IntensityBar, IntensityLegend, intensityFor, splitShares, passesFilter, BAM_LEFT, BAM_RIGHT } from '../components/shared/IntensityBar';
import { Card } from '@/components/ui/card';

interface Props {
  clusters: ClusterProfile[];
  clusterSpreads: { party: string; n: number; [key: string]: string | number }[];
}

// Domain groups, in display order.
const VIEW_DOMAINS = [
  'Taxes & Economy', 'Government Spending', 'Healthcare & Housing', 'Immigration',
  'Police & Guns', 'Civil Liberties', 'Abortion', 'Racial & Gender',
  'Environment & Climate', 'Foreign Policy & Defense', 'Elections & Trust', 'Religion',
];
const DEMO_DOMAINS = [
  'Race & Ethnicity', 'Gender & Sexuality', 'Education', 'Economics',
  'Household', 'Employment & Labor', 'Other',
];
const VOTING_DOMAINS = ['Voting History'];

type Category = 'views' | 'demographics' | 'voting' | 'all';
const CATEGORY_DOMAINS: Record<Category, string[]> = {
  views: VIEW_DOMAINS,
  demographics: DEMO_DOMAINS,
  voting: VOTING_DOMAINS,
  all: [...VIEW_DOMAINS, ...DEMO_DOMAINS, ...VOTING_DOMAINS],
};
const CATEGORY_LABELS: Record<Category, string> = {
  views: 'Views', demographics: 'Demographics', voting: 'Voting history', all: 'All',
};
const VIEW_SET = new Set(VIEW_DOMAINS);
const NEUTRAL_BAR = '#94a3b8';
const MULTI_ACCENT = '#6366f1';

interface Cell {
  pct: number;
  diffPp: number;
  qualifies: boolean;
}
interface Row {
  key: string;
  question: string;
  domain: string;
  overall: number;
  maxVal: number;              // axis maximum (100 for %, 40 for abortion weeks, etc.)
  unit: string;                // display suffix ('%', 'wks', …)
  cells: Record<string, Cell>; // by party code
  qualifiers: string[];        // parties for whom this is a defining plank
  maxStrength: number;         // max normalized |value-50| among qualifiers, for sorting
  diverges: boolean;           // selected parties don't share an identical defining stance
}

// Normalize a value onto a 0–100 scale so non-percentage items (e.g. abortion
// cutoff in weeks, maxVal 40) share the same consensus/deviation thresholds.
const norm = (val: number, maxVal: number) => (maxVal === 100 ? val : (val / maxVal) * 100);

export function PartyPlatform({ clusters, clusterSpreads }: Props) {
  const parties = F5_ORDER.filter(p => clusters.some(c => c.party === p));
  // Selection is shared with Compare Policies (?cmp=…) so it persists across the two views.
  const [cmp, setCmp] = useUrlState<string>('cmp', '');
  const full = useMemo(() => (cmp ? cmp.split(',').filter(Boolean) : []), [cmp]);
  const selected = useMemo(() => full.filter(p => (parties as readonly string[]).includes(p)), [full, parties]);
  const [category, setCategory] = useState<Category>('views');
  const [divergeOnly, setDivergeOnly] = useState(false);
  const sig = useSignatureFilter();
  const { filter } = sig;

  const multi = selected.length > 1;
  const barColor = multi ? NEUTRAL_BAR : (PARTY_COLORS[selected[0]] ?? '#6b7280');
  const accent = multi ? MULTI_ACCENT : barColor;
  const domainOrder = CATEGORY_DOMAINS[category];
  const domainSet = useMemo(() => new Set(domainOrder), [domainOrder]);

  // Toggle a base party while preserving any crossover codes shared from Compare.
  const toggleParty = (p: string) => {
    setCmp((full.includes(p) ? full.filter(x => x !== p) : [...full, p]).join(','));
  };

  const rowsByDomain = useMemo(() => {
    const byKey = new Map<string, Row>();
    for (const code of selected) {
      const cl = clusters.find(c => c.party === code);
      if (!cl) continue;
      for (const [key, v0] of Object.entries(cl.variables ?? {})) {
        const v = v0 as { pct?: number; overall?: number; diffPp?: number; domain?: string; question?: string; maxVal?: number; unit?: string };
        if (!v || typeof v !== 'object' || v.pct == null || !v.domain || !domainSet.has(v.domain)) continue;
        const maxVal = v.maxVal ?? 100;
        let row = byKey.get(key);
        if (!row) {
          row = { key, question: v.question ?? key, domain: v.domain, overall: v.overall ?? 0, maxVal, unit: v.unit ?? '%', cells: {}, qualifiers: [], maxStrength: 0, diverges: false };
          byKey.set(key, row);
        }
        const q = passesFilter(key, code, v.pct, v.overall ?? v.pct, maxVal, filter);
        row.cells[code] = { pct: v.pct, diffPp: v.diffPp ?? 0, qualifies: q };
        if (q) row.qualifiers.push(code);
      }
    }
    const out: Record<string, Row[]> = {};
    for (const row of byKey.values()) {
      if (row.qualifiers.length === 0) continue;
      row.maxStrength = Math.max(...row.qualifiers.map(c => Math.abs(norm(row.cells[c]!.pct, row.maxVal) - 50)));
      // Divergence: the selected parties don't all share the same defining stance.
      // Token per party: 'none' (not a defining plank), 'high' (strong for), 'low' (strong against).
      const stances = new Set(selected.map(code => {
        const c = row.cells[code];
        if (!c || !c.qualifies) return 'none';
        return norm(c.pct, row.maxVal) >= 50 ? 'high' : 'low';
      }));
      row.diverges = stances.size > 1;
      (out[row.domain] ??= []).push(row);
    }
    // Shared planks first (surfaces overlap), then by strength.
    for (const d of Object.keys(out)) {
      out[d].sort((a, b) => b.qualifiers.length - a.qualifiers.length || b.maxStrength - a.maxStrength);
    }
    return out;
  }, [selected, clusters, sig.consPct, sig.alignPp, sig.useConsensus, sig.useAlign, sig.alignMode, domainSet]);

  // "Divergences only" keeps rows where the parties differ in defining stance (multi only).
  const shownByDomain = useMemo(() => {
    if (!divergeOnly || !multi) return rowsByDomain;
    const out: Record<string, Row[]> = {};
    for (const [d, rows] of Object.entries(rowsByDomain)) {
      const f = rows.filter(r => r.diverges);
      if (f.length) out[d] = f;
    }
    return out;
  }, [rowsByDomain, divergeOnly, multi]);

  const total = Object.values(shownByDomain).reduce((s, a) => s + a.length, 0);
  const noun = category === 'views' ? 'position' : category === 'voting' ? 'pattern' : 'trait';

  return (
    <div className="space-y-6">
      {/* Ideological constellation — the overview map */}
      <Card className="p-4">
        <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">Ideological Constellation</h3>
        <p className="text-[11px] text-muted-foreground mb-3 leading-relaxed">
          Each party is an ellipse spanning its members' range on the two strongest factors. Where ellipses
          {' '}<span className="font-medium text-foreground">overlap</span>, voters sit in shared factor space — cross-pressured between those parties.
        </p>
        <IdeologicalConstellation
          nodes={parties.map(code => {
            const c = clusters.find(x => x.party === code)!;
            return {
              id: code, label: code, seats: c.seatsHouse,
              F1: (c as any).z_F1 ?? 0, F2: (c as any).z_F2 ?? 0, F3: (c as any).z_F3 ?? 0, F4: (c as any).z_F4 ?? 0, F5: (c as any).z_F5 ?? 0,
            };
          })}
          clusterSpreads={clusterSpreads}
        />
      </Card>

      <PartySelector selected={full} onToggle={toggleParty} baseParties={parties} />

      {/* Dials */}
      <Card className="p-4">
        <div className="flex flex-wrap gap-1 mb-4">
          <span className="text-xs text-muted-foreground self-center mr-1 uppercase tracking-widest">Show</span>
          {(['views', 'demographics', 'voting', 'all'] as const).map(c => (
            <button key={c} onClick={() => setCategory(c)}
              className={`text-xs px-2.5 py-1 rounded-md border ${category === c ? 'bg-secondary text-foreground font-semibold' : 'text-muted-foreground'}`}>
              {CATEGORY_LABELS[c]}
            </button>
          ))}
          {multi && (
            <button onClick={() => setDivergeOnly(v => !v)}
              title="Only items where the selected parties differ — one defines it and another doesn't, or they define it in opposite directions."
              className={`text-xs px-2.5 py-1 rounded-md border ml-auto ${divergeOnly ? 'bg-secondary text-foreground font-semibold' : 'text-muted-foreground'}`}>
              {divergeOnly ? '✓ ' : ''}Divergences only
            </button>
          )}
        </div>
        <SignatureFilters s={sig} accent={accent} />
        <p className="text-[11px] text-muted-foreground mt-3 leading-relaxed border-t border-border/40 pt-2">
          A party's <span className="font-semibold text-foreground">signature</span> is the mix of two things:
          how strongly it holds a position (<span className="font-semibold text-foreground">Consensus</span>) and how far
          that position sits from the country (<span className="font-semibold text-foreground">Mainstream</span> vs.
          <span className="font-semibold text-foreground"> Deviant</span>). Some parties are defined by strongly-held
          mainstream positions; others by where they break from the national average.
          {multi && ' Each row is a defining plank for at least one selected party; a column fills only when the plank is part of that party’s signature.'}
        </p>
        <p className="text-xs text-muted-foreground mt-2">
          <span className="font-semibold" style={{ color: accent }}>
            {selected.map(p => PARTY_NAMES[p] ?? p).join(' · ') || 'No party selected'}
          </span>
          {selected.length > 0 && (
            <> — {total} {noun}{total !== 1 ? 's' : ''} where {multi ? 'a selected party' : 'this party'} is
            {' '}{[sig.useConsensus && 'strongly held', sig.useAlign && (sig.alignMode === 'deviant' ? 'deviant from the U.S.' : 'mainstream')].filter(Boolean).join(' + ') || 'shown (no filter)'}{divergeOnly && multi ? ', where they diverge' : ''}.</>
          )}
        </p>
      </Card>

      {selected.length === 0 && (
        <p className="text-sm text-muted-foreground">Select a party above to see its platform.</p>
      )}
      {selected.length > 0 && total === 0 && (
        <p className="text-sm text-muted-foreground">Nothing meets these thresholds — try loosening the dials.</p>
      )}

      {total > 0 && (
        <div>
          <div className="space-y-6">
            {/* Column headers + national-average legend — floats on scroll so you remember who's compared */}
            <div className="flex gap-4 items-end px-4 sticky top-[80px] z-10 bg-background/95 backdrop-blur-sm py-2 rounded-b-md">
              <div className="flex-[2] min-w-[160px] text-right">
                {multi && <div className="text-[10px] uppercase tracking-widest text-muted-foreground">Position</div>}
                <div className="flex items-center justify-end gap-1 text-[10px] text-muted-foreground mt-0.5">
                  <span className="relative inline-block w-1.5 h-3">
                    <span className="absolute left-1/2 top-0 bottom-0 w-[2px] -translate-x-1/2 bg-slate-800 rounded" />
                  </span>
                  U.S. average
                </div>
              </div>
              {multi && selected.map(code => {
                const c = PARTY_COLORS[code] ?? '#6b7280';
                return (
                  <div key={code} className="flex-1 min-w-[110px] pl-3 border-l border-border/40">
                    <span className="text-xs font-semibold px-2 py-0.5 rounded-full chip-text-soft"
                      style={{ backgroundColor: c, color: getContrastText(c) }}>
                      {code}
                    </span>
                  </div>
                );
              })}
            </div>

            {domainOrder.filter(d => shownByDomain[d]?.length).map(domain => {
              const isView = VIEW_SET.has(domain);
              const legendItem = shownByDomain[domain].map(r => intensityFor(r.key)).find(Boolean);
              return (
                <Card key={domain} className="p-4">
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-2">{domain}</h3>
                  {legendItem && <div className="mb-2"><IntensityLegend item={legendItem} /></div>}
                  <div>
                    {buildSubgroups(domain, shownByDomain[domain]).map(grp => (
                    <div key={grp.header ?? 'main'}>
                    {grp.header && (
                      <div className="mt-3 mb-1">
                        <div className="text-xs font-semibold text-foreground">{grp.label}</div>
                        {grp.multi && (
                          <div className="text-[11px] text-muted-foreground">Multiple selections allowed — shares can exceed 100%.</div>
                        )}
                      </div>
                    )}
                    {grp.items.map((row, ri) => (
                      <div key={row.key}
                        className={`flex gap-4 items-start rounded transition-colors hover:bg-muted/60 ${ri % 2 === 1 ? 'bg-muted/25' : ''}`}>
                        <div className="flex-[2] min-w-[160px] text-right text-sm text-foreground leading-snug py-2 pl-2">
                          {intensityFor(row.key)?.question ?? (grp.header ? stripPrefix(row.question) : row.question)}
                        </div>
                        {selected.map(code => {
                          const cell = row.cells[code];
                          const base = 'flex-1 min-w-[110px] py-2 pl-3 border-l border-border/40';
                          if (!cell || !cell.qualifies) {
                            return <div key={code} className={`${base} text-center text-slate-300 text-xs`} aria-hidden="true">·</div>;
                          }
                          const iv = intensityFor(row.key);
                          const ivShares = iv?.parties[code];
                          if (iv && ivShares) {
                            const sp = splitShares(iv, ivShares);
                            return (
                              <div key={code} className={base}>
                                <div className="py-1"><IntensityBar item={iv} shares={ivShares} /></div>
                                {sp && (
                                  <>
                                    {sp.neutral != null && (
                                      <div className="relative h-1.5 rounded-sm bg-muted overflow-hidden mt-0.5" title={`Neither ${Math.round(sp.neutral)}%`}>
                                        <div className="absolute inset-y-0 left-0 bg-slate-400" style={{ width: `${sp.neutral}%` }} />
                                      </div>
                                    )}
                                    <div className="mt-0.5 text-[10px] tabular-nums flex items-center justify-between">
                                      <span className="font-semibold" style={{ color: BAM_LEFT }}>{Math.round(sp.leftTotal)}%</span>
                                      {sp.neutral != null && <span className="text-muted-foreground">{Math.round(sp.neutral)}% neither</span>}
                                      <span className="font-semibold" style={{ color: BAM_RIGHT }}>{Math.round(sp.rightTotal)}%</span>
                                    </div>
                                  </>
                                )}
                              </div>
                            );
                          }
                          const isPct = row.unit === '%';
                          const high = norm(cell.pct, row.maxVal) >= 50;
                          const arrowColor = isView && isPct ? (high ? '#16a34a' : '#dc2626') : NEUTRAL_BAR;
                          const cellColor = PARTY_COLORS[code] ?? '#6b7280';
                          const diff = cell.pct - row.overall;
                          const suffix = isPct ? '' : ` ${row.unit}`;
                          return (
                            <div key={code} className={base}>
                              {/* padded wrapper lets the national marker poke above/below the bar */}
                              <div className="relative py-1">
                                <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                                  <div className="absolute top-0 left-0 h-full rounded-full"
                                    style={{ width: `${norm(cell.pct, row.maxVal)}%`, backgroundColor: cellColor }} />
                                </div>
                                <div className="absolute top-0 bottom-0 w-[2px] bg-slate-800 rounded"
                                  style={{ left: `${norm(row.overall, row.maxVal)}%`, transform: 'translateX(-1px)' }}
                                  title={`National avg ${Math.round(row.overall)}${isPct ? '%' : suffix}`} />
                              </div>
                              <div className="flex items-center gap-1 mt-1 text-[11px] tabular-nums">
                                <span style={{ color: arrowColor }} aria-hidden="true">{high ? '▲' : '▼'}</span>
                                <span className="font-semibold text-foreground">{Math.round(cell.pct)}{isPct ? '%' : suffix}</span>
                                <span className="text-muted-foreground">
                                  {diff >= 0 ? '+' : ''}{Math.round(diff)}{suffix}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ))}
                    </div>
                    ))}
                  </div>
                </Card>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

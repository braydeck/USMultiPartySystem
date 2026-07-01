import { Fragment, useMemo, useState } from 'react';
import type { ClusterProfile } from '../types';
import { useUrlState } from '../hooks/useUrlState';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER, getContrastText } from '../constants/parties';
import { qualifies, type AlignMode, type SignatureFilter } from '../lib/signature';
import { Card } from '@/components/ui/card';

interface Props {
  clusters: ClusterProfile[];
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
  cells: Record<string, Cell>; // by party code
  qualifiers: string[];        // parties for whom this is a defining plank
  maxStrength: number;         // max |pct-50| among qualifiers, for sorting
}

export function PartyPlatform({ clusters }: Props) {
  const parties = F5_ORDER.filter(p => clusters.some(c => c.party === p));
  // Selection is a comma list so it is deep-linkable and supports side-by-side comparison.
  const [platform, setPlatform] = useUrlState<string>('platform', parties[0] ?? 'CON');
  const selected = useMemo(
    () => (platform ? platform.split(',').filter(p => (parties as readonly string[]).includes(p)) : []),
    [platform, parties],
  );
  const [category, setCategory] = useState<Category>('views');
  // Two independent axes of a party's signature — enable either or both.
  // Consensus = how unified the party is; Alignment = how far from the country
  // (mainstream = close, deviant = far).
  const [useConsensus, setUseConsensus] = useState(true);
  const [useAlign, setUseAlign] = useState(true);
  const [alignMode, setAlignMode] = useState<AlignMode>('deviant');
  const [minStrength, setMinStrength] = useState(75);
  const [minDev, setMinDev] = useState(25);

  const multi = selected.length > 1;
  const barColor = multi ? NEUTRAL_BAR : (PARTY_COLORS[selected[0]] ?? '#6b7280');
  const accent = multi ? MULTI_ACCENT : barColor;
  const domainOrder = CATEGORY_DOMAINS[category];
  const domainSet = useMemo(() => new Set(domainOrder), [domainOrder]);

  const toggleParty = (p: string) => {
    if (selected.includes(p)) {
      if (selected.length === 1) return; // keep at least one selected
      setPlatform(selected.filter(x => x !== p).join(','));
    } else {
      setPlatform([...selected, p].join(','));
    }
  };

  const filter: SignatureFilter = { useConsensus, consPct: minStrength, useAlign, alignMode, alignPp: minDev };

  const rowsByDomain = useMemo(() => {
    const byKey = new Map<string, Row>();
    for (const code of selected) {
      const cl = clusters.find(c => c.party === code);
      if (!cl) continue;
      for (const [key, v0] of Object.entries(cl.variables ?? {})) {
        const v = v0 as { pct?: number; overall?: number; diffPp?: number; domain?: string; question?: string };
        if (!v || typeof v !== 'object' || v.pct == null || !v.domain || !domainSet.has(v.domain)) continue;
        let row = byKey.get(key);
        if (!row) {
          row = { key, question: v.question ?? key, domain: v.domain, overall: v.overall ?? 0, cells: {}, qualifiers: [], maxStrength: 0 };
          byKey.set(key, row);
        }
        const q = qualifies(v.pct, v.overall ?? v.pct, filter);
        row.cells[code] = { pct: v.pct, diffPp: v.diffPp ?? 0, qualifies: q };
        if (q) row.qualifiers.push(code);
      }
    }
    const out: Record<string, Row[]> = {};
    for (const row of byKey.values()) {
      if (row.qualifiers.length === 0) continue;
      row.maxStrength = Math.max(...row.qualifiers.map(c => Math.abs(row.cells[c]!.pct - 50)));
      (out[row.domain] ??= []).push(row);
    }
    // Shared planks first (surfaces overlap), then by strength.
    for (const d of Object.keys(out)) {
      out[d].sort((a, b) => b.qualifiers.length - a.qualifiers.length || b.maxStrength - a.maxStrength);
    }
    return out;
  }, [selected, clusters, minStrength, minDev, useConsensus, useAlign, alignMode, domainSet]);

  const total = Object.values(rowsByDomain).reduce((s, a) => s + a.length, 0);
  const noun = category === 'views' ? 'position' : category === 'voting' ? 'pattern' : 'trait';
  const gridStyle = {
    display: 'grid',
    gridTemplateColumns: `minmax(180px, 2fr) repeat(${Math.max(selected.length, 1)}, minmax(120px, 1fr))`,
    columnGap: '1rem',
  } as const;

  return (
    <div className="space-y-6">
      {/* Party selector — click to toggle; up to ~3 reads best */}
      <div className="flex flex-wrap gap-1.5">
        {parties.map(p => {
          const on = selected.includes(p);
          const c = PARTY_COLORS[p] ?? '#6b7280';
          return (
            <button key={p} onClick={() => toggleParty(p)}
              className="text-xs font-semibold px-2.5 py-1 rounded-full border transition-all"
              style={{ borderColor: c, color: on ? getContrastText(c) : c, backgroundColor: on ? c : 'transparent' }}>
              {PARTY_NAMES[p] ?? p}
            </button>
          );
        })}
      </div>

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
        </div>
        <div className="grid sm:grid-cols-2 gap-5 items-end">
          <div style={{ opacity: useConsensus ? 1 : 0.45 }}>
            <label className="flex items-center gap-2 text-xs mb-1 cursor-pointer">
              <input type="checkbox" checked={useConsensus} onChange={e => setUseConsensus(e.target.checked)}
                style={{ accentColor: accent }} />
              <span className="font-semibold text-foreground">Consensus</span>
              <span className="text-muted-foreground">— held by</span>
              <span className="font-mono font-semibold ml-auto" style={{ color: accent }}>≥{minStrength}% or ≤{100 - minStrength}%</span>
            </label>
            <input type="range" min={50} max={100} step={5} value={minStrength} disabled={!useConsensus}
              onChange={e => setMinStrength(Number(e.target.value))} className="w-full" style={{ accentColor: accent }} />
          </div>
          <div style={{ opacity: useAlign ? 1 : 0.45 }}>
            <label className="flex items-center gap-2 text-xs mb-1 cursor-pointer">
              <input type="checkbox" checked={useAlign} onChange={e => setUseAlign(e.target.checked)}
                style={{ accentColor: accent }} />
              <span className="font-semibold text-foreground">{alignMode === 'deviant' ? 'Deviant' : 'Mainstream'}</span>
              <span className="text-muted-foreground">— {alignMode === 'deviant' ? 'far from' : 'close to'} the U.S. average</span>
              <span className="font-mono font-semibold ml-auto" style={{ color: accent }}>
                {alignMode === 'deviant' ? '≥' : '≤'}{minDev} pts
              </span>
            </label>
            <div className="flex items-center gap-2">
              <div className="flex gap-1 shrink-0">
                {(['mainstream', 'deviant'] as const).map(m => (
                  <button key={m} onClick={() => setAlignMode(m)} disabled={!useAlign}
                    className={`text-[10px] px-1.5 py-0.5 rounded border ${alignMode === m ? 'bg-secondary text-foreground font-semibold' : 'text-muted-foreground'}`}>
                    {m === 'mainstream' ? '≤ mainstream' : '≥ deviant'}
                  </button>
                ))}
              </div>
              <input type="range" min={0} max={50} step={5} value={minDev} disabled={!useAlign}
                onChange={e => setMinDev(Number(e.target.value))} className="flex-1" style={{ accentColor: accent }} />
            </div>
          </div>
        </div>
        <p className="text-[11px] text-muted-foreground mt-3 leading-relaxed border-t border-border/40 pt-2">
          A party's <span className="font-semibold text-foreground">signature</span> is the mix of two things:
          how strongly it holds a position (<span className="font-semibold text-foreground">Consensus</span>) and how far
          that position sits from the country (<span className="font-semibold text-foreground">Mainstream</span> vs.
          <span className="font-semibold text-foreground"> Deviant</span>). Some parties are defined by strongly-held
          mainstream positions; others by where they break from the national average.
          {multi && ' Select up to ~3 parties — each row is a defining plank for at least one; a column fills only when it is a defining plank for that party.'}
        </p>
        <p className="text-xs text-muted-foreground mt-2">
          <span className="font-semibold" style={{ color: accent }}>
            {selected.map(p => PARTY_NAMES[p] ?? p).join(' · ') || 'No party selected'}
          </span>
          {selected.length > 0 && (
            <> — {total} {noun}{total !== 1 ? 's' : ''} where {multi ? 'a selected party' : 'this party'} is
            {' '}{[useConsensus && 'strongly held', useAlign && (alignMode === 'deviant' ? 'deviant from the U.S.' : 'mainstream')].filter(Boolean).join(' + ') || 'shown (no filter)'}.</>
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
        <div className="overflow-x-auto">
          <div style={{ minWidth: multi ? 180 + selected.length * 140 : undefined }} className="space-y-6">
            {multi && (
              <div style={gridStyle} className="items-end">
                <div className="text-[10px] uppercase tracking-widest text-muted-foreground pb-1">Position</div>
                {selected.map(code => {
                  const c = PARTY_COLORS[code] ?? '#6b7280';
                  return (
                    <div key={code} className="pl-3 border-l border-border/40">
                      <span className="text-xs font-semibold px-2 py-0.5 rounded-full chip-text-soft"
                        style={{ backgroundColor: c, color: getContrastText(c) }}>
                        {code}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}

            {domainOrder.filter(d => rowsByDomain[d]?.length).map(domain => {
              const isView = VIEW_SET.has(domain);
              return (
                <div key={domain}>
                  <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-2">{domain}</h3>
                  <div style={gridStyle}>
                    {rowsByDomain[domain].map((row, ri) => (
                      <Fragment key={row.key}>
                        <div className={`text-sm text-foreground leading-snug py-2 pr-2 ${ri > 0 ? 'border-t border-border/40' : ''}`}>
                          {row.question}
                        </div>
                        {selected.map(code => {
                          const cell = row.cells[code];
                          const base = `py-2 pl-3 border-l border-border/40 ${ri > 0 ? 'border-t' : ''}`;
                          if (!cell || !cell.qualifies) {
                            return <div key={code} className={`${base} text-center text-slate-300 text-xs`} aria-hidden="true">·</div>;
                          }
                          const high = cell.pct >= 50;
                          const arrowColor = isView ? (high ? '#16a34a' : '#dc2626') : NEUTRAL_BAR;
                          const cellColor = PARTY_COLORS[code] ?? '#6b7280';
                          return (
                            <div key={code} className={base}>
                              <div className="relative h-2 bg-muted rounded-full overflow-hidden">
                                <div className="absolute top-0 left-0 h-full rounded-full"
                                  style={{ width: `${cell.pct}%`, backgroundColor: cellColor }} />
                                <div className="absolute top-0 h-full w-0.5 bg-slate-500"
                                  style={{ left: `${row.overall}%` }} title={`National avg ${Math.round(row.overall)}%`} />
                              </div>
                              <div className="flex items-center gap-1 mt-1 text-[11px] tabular-nums">
                                <span style={{ color: arrowColor }} aria-hidden="true">{high ? '▲' : '▼'}</span>
                                <span className="font-semibold text-foreground">{Math.round(cell.pct)}%</span>
                                <span className="text-muted-foreground">
                                  {cell.diffPp >= 0 ? '+' : ''}{Math.round(cell.diffPp)}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </Fragment>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

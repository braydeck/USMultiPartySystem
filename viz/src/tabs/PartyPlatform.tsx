import { useMemo, useState } from 'react';
import type { ClusterProfile } from '../types';
import { useUrlState } from '../hooks/useUrlState';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER, getContrastText } from '../constants/parties';
import { qualifies, type AlignMode } from '../lib/signature';
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

interface Plank {
  question: string;
  domain: string;
  pct: number;      // % of the party's (core) members
  overall: number;  // national average
  diffPp: number;   // deviation from national
}

export function PartyPlatform({ clusters }: Props) {
  const parties = F5_ORDER.filter(p => clusters.some(c => c.party === p));
  const [party, setParty] = useUrlState<string>('platform', parties[0] ?? 'CON', { allowed: [...parties] });
  const [category, setCategory] = useState<Category>('views');
  // Two independent axes of a party's signature — enable either or both.
  // Consensus = how unified the party is; Alignment = how far from the country
  // (mainstream = close, deviant = far).
  const [useConsensus, setUseConsensus] = useState(true);
  const [useAlign, setUseAlign] = useState(true);
  const [alignMode, setAlignMode] = useState<AlignMode>('deviant');
  const [minStrength, setMinStrength] = useState(75);
  const [minDev, setMinDev] = useState(25);

  const cluster = clusters.find(c => c.party === party);
  const color = PARTY_COLORS[party] ?? '#6b7280';
  const domainOrder = CATEGORY_DOMAINS[category];
  const domainSet = useMemo(() => new Set(domainOrder), [domainOrder]);

  const planksByDomain = useMemo(() => {
    const out: Record<string, Plank[]> = {};
    if (!cluster) return out;
    for (const v of Object.values(cluster.variables ?? {})) {
      if (!v || typeof v !== 'object') continue;
      const { pct, overall, diffPp, domain, question } = v as Plank & { question: string; domain: string };
      if (pct == null || !domainSet.has(domain)) continue;
      const pass = qualifies(pct, overall ?? pct, {
        useConsensus, consPct: minStrength, useAlign, alignMode, alignPp: minDev,
      });
      if (!pass) continue;
      (out[domain] ??= []).push({ question, domain, pct, overall: overall ?? 0, diffPp: diffPp ?? 0 });
    }
    for (const d of Object.keys(out)) out[d].sort((a, b) => Math.abs(b.pct - 50) - Math.abs(a.pct - 50));
    return out;
  }, [cluster, minStrength, minDev, useConsensus, useAlign, alignMode, domainSet]);

  const total = Object.values(planksByDomain).reduce((s, a) => s + a.length, 0);
  const noun = category === 'views' ? 'position' : category === 'voting' ? 'pattern' : 'trait';

  return (
    <div className="space-y-6">
      {/* Party selector */}
      <div className="flex flex-wrap gap-1.5">
        {parties.map(p => {
          const on = p === party;
          const c = PARTY_COLORS[p] ?? '#6b7280';
          return (
            <button key={p} onClick={() => setParty(p)}
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
                style={{ accentColor: color }} />
              <span className="font-semibold text-foreground">Consensus</span>
              <span className="text-muted-foreground">— held by</span>
              <span className="font-mono font-semibold ml-auto" style={{ color }}>≥{minStrength}% or ≤{100 - minStrength}%</span>
            </label>
            <input type="range" min={50} max={100} step={5} value={minStrength} disabled={!useConsensus}
              onChange={e => setMinStrength(Number(e.target.value))} className="w-full" style={{ accentColor: color }} />
          </div>
          <div style={{ opacity: useAlign ? 1 : 0.45 }}>
            <label className="flex items-center gap-2 text-xs mb-1 cursor-pointer">
              <input type="checkbox" checked={useAlign} onChange={e => setUseAlign(e.target.checked)}
                style={{ accentColor: color }} />
              <span className="font-semibold text-foreground">{alignMode === 'deviant' ? 'Deviant' : 'Mainstream'}</span>
              <span className="text-muted-foreground">— {alignMode === 'deviant' ? 'far from' : 'close to'} the U.S. average</span>
              <span className="font-mono font-semibold ml-auto" style={{ color }}>
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
                onChange={e => setMinDev(Number(e.target.value))} className="flex-1" style={{ accentColor: color }} />
            </div>
          </div>
        </div>
        <p className="text-[11px] text-muted-foreground mt-3 leading-relaxed border-t border-border/40 pt-2">
          A party's <span className="font-semibold text-foreground">signature</span> is the mix of two things:
          how strongly it holds a position (<span className="font-semibold text-foreground">Consensus</span>) and how far
          that position sits from the country (<span className="font-semibold text-foreground">Mainstream</span> vs.
          <span className="font-semibold text-foreground"> Deviant</span>). Some parties are defined by strongly-held
          mainstream positions; others by where they break from the national average.
        </p>
        <p className="text-xs text-muted-foreground mt-2">
          <span className="font-semibold" style={{ color }}>{PARTY_NAMES[party] ?? party}</span> —
          {' '}{category === 'views' ? 'positions' : category === 'voting' ? 'voting patterns' : category === 'demographics' ? 'demographics' : 'positions & traits'} its
          core members, filtered by the criteria above
          ({[useConsensus && 'strongly held', useAlign && (alignMode === 'deviant' ? 'deviant from the U.S.' : 'mainstream')].filter(Boolean).join(' + ') || 'no filter'}).
          {' '}{total} {noun}{total !== 1 ? 's' : ''} shown.
        </p>
      </Card>

      {total === 0 && (
        <p className="text-sm text-muted-foreground">Nothing meets these thresholds — try loosening the dials.</p>
      )}
      {domainOrder.filter(d => planksByDomain[d]?.length).map(domain => {
        const isView = VIEW_SET.has(domain);
        return (
          <div key={domain}>
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-2">{domain}</h3>
            <div className="space-y-2">
              {planksByDomain[domain].map((p, i) => {
                const high = p.pct >= 50;                      // majority holds / above 50%
                // Views: green ▲ supports / red ▼ opposes. Other categories: neutral majority/minority.
                const arrowColor = isView ? (high ? '#16a34a' : '#dc2626') : (high ? color : '#94a3b8');
                return (
                  <div key={i} className="flex items-center gap-3">
                    <span className="shrink-0 w-5 text-center font-bold" style={{ color: arrowColor }} aria-hidden="true">
                      {high ? '▲' : '▼'}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-foreground leading-snug">{p.question}</div>
                      <div className="relative h-2 bg-muted rounded-full overflow-hidden mt-1">
                        <div className="absolute top-0 left-0 h-full rounded-full"
                          style={{ width: `${p.pct}%`, backgroundColor: color }} />
                        <div className="absolute top-0 h-full w-0.5 bg-slate-500"
                          style={{ left: `${p.overall}%` }} title={`National avg ${Math.round(p.overall)}%`} />
                      </div>
                    </div>
                    <div className="shrink-0 text-right tabular-nums" style={{ width: 96 }}>
                      <div className="text-sm font-semibold" style={{ color }}>{Math.round(p.pct)}%</div>
                      <div className="text-[10px] text-muted-foreground">
                        nat {Math.round(p.overall)}% · {p.diffPp >= 0 ? '+' : ''}{Math.round(p.diffPp)}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

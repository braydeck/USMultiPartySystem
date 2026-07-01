import { useMemo } from 'react';
import type { ClusterProfile } from '../types';
import { useUrlState } from '../hooks/useUrlState';
import { PARTY_COLORS, PARTY_NAMES, F5_ORDER, getContrastText } from '../constants/parties';
import { Card } from '@/components/ui/card';
import intensityData from '../data/clusterIntensity.json';

interface Item {
  variable: string;
  question: string;
  domain: string;
  kind: 'diverging' | 'freq';
  labels: string[];
  middleIndex: number | null;
  national: number[];
  parties: Record<string, number[]>;
}
const ITEMS = (intensityData as { items: Item[] }).items;

interface Props {
  clusters: ClusterProfile[];
}

// agree/increase (strong→somewhat) · neutral · somewhat→strong disagree/decrease
const DIVERGE5 = ['#1d4ed8', '#93c5fd', '#e2e8f0', '#fca5a5', '#dc2626'];
// sequential ramp for frequency scales (church: most→least)
const SEQ = ['#1e3a8a', '#2563eb', '#60a5fa', '#93c5fd', '#c7d7f5', '#eef2ff'];

interface Seg { left: number; width: number; color: string; label: string }

// Diverging: neutral centered at 50%; each side scaled so 100% share = 50% of track.
function divergingSegs(shares: number[], labels: string[], m: number, colors: string[]): Seg[] {
  const S = 0.5;
  const nW = shares[m] * S;
  const cLeft = 50 - nW / 2;
  const seg = (i: number, left: number, width: number): Seg => ({ left, width, color: colors[i], label: `${labels[i]}: ${shares[i]}%` });
  const segs: Seg[] = [seg(m, cLeft, nW)];
  let x = cLeft;
  for (let i = m - 1; i >= 0; i--) { const w = shares[i] * S; segs.push(seg(i, x - w, w)); x -= w; }
  let y = cLeft + nW;
  for (let i = m + 1; i < shares.length; i++) { const w = shares[i] * S; segs.push(seg(i, y, w)); y += w; }
  return segs;
}

// Sequential: simple left→right stack over the full track.
function seqSegs(shares: number[], labels: string[], colors: string[]): Seg[] {
  const segs: Seg[] = [];
  let x = 0;
  for (let i = 0; i < shares.length; i++) { segs.push({ left: x, width: shares[i], color: colors[i], label: `${labels[i]}: ${shares[i]}%` }); x += shares[i]; }
  return segs;
}

function Bar({ item, shares }: { item: Item; shares: number[] }) {
  const colors = item.kind === 'diverging' ? DIVERGE5 : SEQ;
  const segs = item.kind === 'diverging' && item.middleIndex != null
    ? divergingSegs(shares, item.labels, item.middleIndex, colors)
    : seqSegs(shares, item.labels, colors);
  return (
    <div className="relative h-4 w-full rounded-sm overflow-hidden bg-muted">
      {segs.map((s, i) => (
        <div key={i} className="absolute top-0 h-full" style={{ left: `${s.left}%`, width: `${s.width}%`, backgroundColor: s.color }}
          title={s.label} />
      ))}
      {item.kind === 'diverging' && <div className="absolute top-0 h-full w-px bg-slate-500/60" style={{ left: '50%' }} />}
    </div>
  );
}

function Legend({ item }: { item: Item }) {
  const colors = item.kind === 'diverging' ? DIVERGE5 : SEQ;
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-muted-foreground mb-2">
      {item.labels.map((l, i) => (
        <span key={i} className="inline-flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: colors[i] }} />
          {l}
        </span>
      ))}
    </div>
  );
}

export function IntensityView({ clusters }: Props) {
  const parties = F5_ORDER.filter(p => clusters.some(c => c.party === p) && ITEMS[0]?.parties[p]);
  const [platform, setPlatform] = useUrlState<string>('platform', '');
  const selected = useMemo(
    () => (platform ? platform.split(',').filter(p => (parties as readonly string[]).includes(p)) : []),
    [platform, parties],
  );
  const toggle = (p: string) => {
    const next = selected.includes(p) ? selected.filter(x => x !== p) : [...selected, p];
    setPlatform(next.join(','));
  };

  // group items by domain, preserving file order
  const byDomain = useMemo(() => {
    const out: { domain: string; items: Item[] }[] = [];
    for (const it of ITEMS) {
      let g = out.find(x => x.domain === it.domain);
      if (!g) { g = { domain: it.domain, items: [] }; out.push(g); }
      g.items.push(it);
    }
    return out;
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap gap-1.5">
        {parties.map(p => {
          const on = selected.includes(p);
          const c = PARTY_COLORS[p] ?? '#6b7280';
          return (
            <button key={p} onClick={() => toggle(p)}
              className="text-xs font-semibold px-2.5 py-1 rounded-full border transition-all"
              style={{ borderColor: c, color: on ? getContrastText(c) : c, backgroundColor: on ? c : 'transparent' }}>
              {PARTY_NAMES[p] ?? p}
            </button>
          );
        })}
      </div>

      <p className="text-xs text-muted-foreground">
        Full response distributions for the multi-point items that Compare/Platform otherwise collapse to a
        single number. The <span className="font-medium text-foreground">middle</span> category (Maintain / Neither)
        is centered so you can read the compromise share and the strong-vs-somewhat intensity directly.
      </p>

      {selected.length === 0 && (
        <p className="text-sm text-muted-foreground">Select one or more parties above.</p>
      )}

      {selected.length > 0 && byDomain.map(g => (
        <div key={g.domain}>
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-widest mb-1">{g.domain}</h3>
          <Legend item={g.items[0]} />
          <Card className="p-4 space-y-4">
            {g.items.map(item => (
              <div key={item.variable}>
                <div className="text-sm text-foreground leading-snug mb-1.5">{item.question}</div>
                <div className="space-y-1">
                  {(['__NAT__', ...selected]).map(code => {
                    const shares = code === '__NAT__' ? item.national : item.parties[code];
                    if (!shares) return null;
                    const isNat = code === '__NAT__';
                    const c = isNat ? '#64748b' : (PARTY_COLORS[code] ?? '#6b7280');
                    const midVal = item.middleIndex != null ? shares[item.middleIndex] : null;
                    return (
                      <div key={code} className="flex items-center gap-2">
                        <span className="w-14 shrink-0 text-[10px] font-semibold text-right" style={{ color: c }}>
                          {isNat ? 'U.S.' : code}
                        </span>
                        <div className="flex-1 min-w-0"><Bar item={item} shares={shares} /></div>
                        <span className="w-10 shrink-0 text-[10px] tabular-nums text-muted-foreground text-right">
                          {midVal != null ? `${Math.round(midVal)}%` : ''}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </Card>
        </div>
      ))}
    </div>
  );
}

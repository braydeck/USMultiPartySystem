import { bamForFrac } from '../../lib/bam';
import { flareForFrac } from '../../lib/flare';
import type { SignatureFilter } from '../../lib/signature';
import clusterIntensityData from '../../data/clusterIntensity.json';

// Legible pole colors for the disagree(left)/agree(right) total labels.
export const BAM_LEFT = bamForFrac(0.12);   // magenta
export const BAM_RIGHT = bamForFrac(0.88);  // green

export interface IntensityItem {
  variable: string;
  question: string;
  domain: string;
  kind: 'diverging' | 'freq';
  battery: string;           // comparable group (agree / spending / trust / …) for per-battery percentiles
  labels: string[];          // ordered liberal(index 0) → conservative(last); neutral in middle
  middleIndex: number | null;
  national: number[];
  parties: Record<string, number[]>;
}

export const INTENSITY_ITEMS = (clusterIntensityData as { items: IntensityItem[] }).items;
const BY_VAR: Record<string, IntensityItem> = Object.fromEntries(INTENSITY_ITEMS.map(i => [i.variable, i]));
// Profile keys append "_agree" for the agree scales — strip it to join to intensity data.
export const intensityFor = (key: string): IntensityItem | undefined => BY_VAR[key.replace(/_agree$/, '')];

// Bipolar agree/disagree scales use bam (magenta → neutral → green) so the color does
// not read as the political red/blue used for left–right elsewhere. Sequential frequency
// scales (church/prayer: most → least frequent) use the seaborn "flare" ramp, dark = high
// frequency → light salmon = low; its hue rotation separates adjacent buckets better than
// the old flat RdPu magenta.
export function catColors(kind: 'diverging' | 'freq', n: number): string[] {
  if (kind === 'diverging') return Array.from({ length: n }, (_, i) => bamForFrac(i / (n - 1)));
  return Array.from({ length: n }, (_, i) => flareForFrac(n <= 1 ? 1 : 1 - i / (n - 1)));
}

const sum = (a: number[]) => a.reduce((x, y) => x + y, 0);
const poleWord = (label: string) => label.split(/[ /]/).pop()!.toLowerCase(); // "Strongly disagree" → "disagree"

export interface Split {
  neutral: number | null; // null for even scales (no neutral category, e.g. 4-point trust)
  leftTotal: number;
  rightTotal: number;
  leftWord: string;
  rightWord: string;
}

/** Split a diverging item's shares into neutral / left / right totals. Even scales
 *  (no neutral) split down the middle with neutral = null. */
export function splitShares(item: IntensityItem, shares: number[]): Split | null {
  if (item.kind !== 'diverging') return null;
  const m = item.middleIndex;
  const n = shares.length;
  const leftEnd = m != null ? m : n / 2;      // slice(0, leftEnd)
  const rightStart = m != null ? m + 1 : n / 2;
  return {
    neutral: m != null ? shares[m] : null,
    leftTotal: sum(shares.slice(0, leftEnd)),
    rightTotal: sum(shares.slice(rightStart)),
    leftWord: poleWord(item.labels[0]),
    rightWord: poleWord(item.labels[n - 1]),
  };
}

const norm01 = (val: number, maxVal: number) => (maxVal === 100 ? val : (val / maxVal) * 100);

// Empirical distribution of each bucket's share, pooled PER BATTERY (agree / spending /
// trust / …) since neutral baselines differ sharply between batteries (spending "Maintain"
// runs far higher than an agree scale's "Neither"). Consensus is then applied as a
// within-battery percentile: a stance is "defining" if it's unusually high in agree,
// neutral, OR disagree relative to other ordinal stances in the same battery.
type Buckets = { left: number[]; neutral: number[]; right: number[] };
const POOL: Record<string, Buckets> = {};
for (const it of INTENSITY_ITEMS) {
  if (it.kind !== 'diverging') continue;
  const b = (POOL[it.battery] ??= { left: [], neutral: [], right: [] });
  for (const code of Object.keys(it.parties)) {
    const sp = splitShares(it, it.parties[code]);
    if (!sp) continue;
    b.left.push(sp.leftTotal);
    b.right.push(sp.rightTotal);
    if (sp.neutral != null) b.neutral.push(sp.neutral);
  }
}
for (const b of Object.values(POOL)) (['left', 'neutral', 'right'] as const).forEach(k => b[k].sort((x, y) => x - y));
function bucketPercentile(battery: string, bucket: 'left' | 'neutral' | 'right', p: number): number {
  const a = POOL[battery]?.[bucket];
  if (!a || !a.length) return 101;
  return a[Math.min(a.length - 1, Math.floor((p / 100) * a.length))];
}

/**
 * Does a party's stance on one item pass the signature filter? Consensus is judged
 * percentile-relative for ordinal (diverging) items — the slider value P means "top
 * (100−P)% of that bucket's distribution" in agree, neutral, or disagree — and by the
 * plain ≥P% / ≤(100−P)% rule for binary items. Alignment (deviance) is always the
 * collapsed-pct deviation from the national average.
 */
export function passesFilter(key: string, code: string, pct: number, overall: number, maxVal: number, f: SignatureFilter): boolean {
  const iv = intensityFor(key);
  const shares = iv?.parties[code];
  let consensusOk: boolean;
  if (iv && iv.kind === 'diverging' && shares) {
    const sp = splitShares(iv, shares)!;
    consensusOk =
      sp.leftTotal >= bucketPercentile(iv.battery, 'left', f.consPct) ||
      sp.rightTotal >= bucketPercentile(iv.battery, 'right', f.consPct) ||
      (sp.neutral != null && sp.neutral >= bucketPercentile(iv.battery, 'neutral', f.consPct));
  } else {
    const p = norm01(pct, maxVal);
    consensusOk = p >= f.consPct || p <= 100 - f.consPct;
  }
  const dev = Math.abs(norm01(pct, maxVal) - norm01(overall ?? pct, maxVal));
  const alignOk = f.alignMode === 'deviant' ? dev >= f.alignPp : dev <= f.alignPp;
  return (!f.useConsensus || consensusOk) && (!f.useAlign || alignOk);
}

interface Seg { left: number; width: number; color: string; label: string }

// Diverging bar of the NON-neutral categories, centered on the boundary (50%). Left side
// extends left, right side right; 100% per side = half the track. A neutral middle (odd
// scales) is excluded from the bar; even scales split contiguously at the center.
function centeredSegs(shares: number[], labels: string[], m: number | null, colors: string[]): Seg[] {
  const S = 0.5;
  const n = shares.length;
  const leftEnd = m != null ? m - 1 : n / 2 - 1;
  const rightStart = m != null ? m + 1 : n / 2;
  const seg = (i: number, left: number, width: number): Seg => ({ left, width, color: colors[i], label: `${labels[i]}: ${Math.round(shares[i])}%` });
  const segs: Seg[] = [];
  let x = 50;
  for (let i = leftEnd; i >= 0; i--) { const w = shares[i] * S; segs.push(seg(i, x - w, w)); x -= w; }
  let y = 50;
  for (let i = rightStart; i < n; i++) { const w = shares[i] * S; segs.push(seg(i, y, w)); y += w; }
  return segs;
}

function seqSegs(shares: number[], labels: string[], colors: string[]): Seg[] {
  const segs: Seg[] = [];
  let x = 0;
  for (let i = 0; i < shares.length; i++) { segs.push({ left: x, width: shares[i], color: colors[i], label: `${labels[i]}: ${Math.round(shares[i])}%` }); x += shares[i]; }
  return segs;
}

/** Distribution bar. Diverging items exclude the neutral category (shown separately) and
 *  center the agree/disagree split on zero; frequency scales stack left→right. */
export function IntensityBar({ item, shares, height = 14 }: { item: IntensityItem; shares: number[]; height?: number }) {
  const colors = catColors(item.kind, item.labels.length);
  const diverging = item.kind === 'diverging';
  const segs = diverging
    ? centeredSegs(shares, item.labels, item.middleIndex, colors)
    : seqSegs(shares, item.labels, colors);
  return (
    <div className="relative w-full rounded-sm overflow-hidden bg-muted" style={{ height }}>
      {segs.map((s, i) => (
        <div key={i} className="absolute top-0 h-full" style={{ left: `${s.left}%`, width: `${s.width}%`, backgroundColor: s.color }} title={s.label} />
      ))}
      {diverging && <div className="absolute top-0 h-full w-px bg-slate-500/70" style={{ left: '50%' }} />}
    </div>
  );
}

/** Legend showing the pole labels + colors (diverging), or the category ramp (freq). */
export function IntensityLegend({ item }: { item: IntensityItem }) {
  const colors = catColors(item.kind, item.labels.length);
  if (item.kind === 'diverging') {
    const last = item.labels.length - 1;
    return (
      <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: colors[0] }} />◀ {item.labels[0]}
        </span>
        <span className="inline-flex items-center gap-1">
          {item.labels[last]} ▶<span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: colors[last] }} />
        </span>
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
      {item.labels.map((l, i) => (
        <span key={i} className="inline-flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: colors[i] }} />{l}
        </span>
      ))}
    </div>
  );
}

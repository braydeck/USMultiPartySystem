import { vikForPctile } from '../../lib/vik';
import clusterIntensityData from '../../data/clusterIntensity.json';

export interface IntensityItem {
  variable: string;
  question: string;
  domain: string;
  kind: 'diverging' | 'freq';
  labels: string[];
  middleIndex: number | null;
  national: number[];
  parties: Record<string, number[]>;
}

export const INTENSITY_ITEMS = (clusterIntensityData as { items: IntensityItem[] }).items;
const BY_VAR: Record<string, IntensityItem> = Object.fromEntries(INTENSITY_ITEMS.map(i => [i.variable, i]));
// Profile keys append "_agree" for the agree scales — strip it to join to intensity data.
export const intensityFor = (key: string): IntensityItem | undefined => BY_VAR[key.replace(/_agree$/, '')];

// Sequential ramp for non-bipolar frequency scales (church: most → least attendance).
const SEQ = ['#0b3d91', '#2563eb', '#60a5fa', '#93c5fd', '#c7d7f5', '#eef2ff'];

// Bipolar scales use vik (blue pole → neutral center → red pole); frequency uses SEQ.
export function catColors(kind: 'diverging' | 'freq', n: number): string[] {
  if (kind === 'diverging') return Array.from({ length: n }, (_, i) => vikForPctile((i / (n - 1)) * 100));
  return Array.from({ length: n }, (_, i) => SEQ[Math.min(i, SEQ.length - 1)]);
}

interface Seg { left: number; width: number; color: string; label: string }

// Diverging: middle category centered at 50%; each side scaled so 100% share = 50% of track.
function divergingSegs(shares: number[], labels: string[], m: number, colors: string[]): Seg[] {
  const S = 0.5;
  const nW = shares[m] * S;
  const cLeft = 50 - nW / 2;
  const seg = (i: number, left: number, width: number): Seg => ({ left, width, color: colors[i], label: `${labels[i]}: ${Math.round(shares[i])}%` });
  const segs: Seg[] = [seg(m, cLeft, nW)];
  let x = cLeft;
  for (let i = m - 1; i >= 0; i--) { const w = shares[i] * S; segs.push(seg(i, x - w, w)); x -= w; }
  let y = cLeft + nW;
  for (let i = m + 1; i < shares.length; i++) { const w = shares[i] * S; segs.push(seg(i, y, w)); y += w; }
  return segs;
}

// Sequential: simple left → right stack over the full track.
function seqSegs(shares: number[], labels: string[], colors: string[]): Seg[] {
  const segs: Seg[] = [];
  let x = 0;
  for (let i = 0; i < shares.length; i++) { segs.push({ left: x, width: shares[i], color: colors[i], label: `${labels[i]}: ${Math.round(shares[i])}%` }); x += shares[i]; }
  return segs;
}

/** A stacked distribution bar for a multi-point item. Diverging (bipolar) scales
 *  center the neutral category and color via vik; frequency scales stack left→right. */
export function IntensityBar({ item, shares, height = 14 }: { item: IntensityItem; shares: number[]; height?: number }) {
  const colors = catColors(item.kind, item.labels.length);
  const segs = item.kind === 'diverging' && item.middleIndex != null
    ? divergingSegs(shares, item.labels, item.middleIndex, colors)
    : seqSegs(shares, item.labels, colors);
  return (
    <div className="relative w-full rounded-sm overflow-hidden bg-muted" style={{ height }}>
      {segs.map((s, i) => (
        <div key={i} className="absolute top-0 h-full" style={{ left: `${s.left}%`, width: `${s.width}%`, backgroundColor: s.color }} title={s.label} />
      ))}
      {item.kind === 'diverging' && <div className="absolute top-0 h-full w-px bg-slate-500/50" style={{ left: '50%' }} />}
    </div>
  );
}

/** Compact legend for an item's categories. */
export function IntensityLegend({ item }: { item: IntensityItem }) {
  const colors = catColors(item.kind, item.labels.length);
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-muted-foreground">
      {item.labels.map((l, i) => (
        <span key={i} className="inline-flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: colors[i] }} />
          {l}
        </span>
      ))}
    </div>
  );
}

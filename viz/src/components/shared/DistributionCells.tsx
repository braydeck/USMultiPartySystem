import { getBlendColor } from '../../constants/parties';
import { PartyRowLabel, type RowMark } from './PartyRowLabel';
import { cividisForFrac, cividisText } from '../../lib/cividis';

// Shared row language with StackedBarCell/IntensityCell: `U.S.` + each selected party code,
// a w-11 label, a flex-1 track, and a value column. National uses slate.
const NAT = '#64748b';

type RangeVals = { p10: number; q25: number; median: number; q75: number; p90: number };
type CompVals = { pcts: number[]; value?: number };

export interface RangeMeta { question: string; unit: string }
export interface CompMeta { question: string; segLabels: string[]; colors?: string[]; pivot?: number; valueUnit?: string; viz?: string }

function niceTicks(min: number, max: number, count = 5): number[] {
  const span = (max - min) || 1;
  const mag = Math.pow(10, Math.floor(Math.log10(span / count)));
  const norm = (span / count) / mag;
  const step = (norm < 1.5 ? 1 : norm < 3 ? 2 : norm < 7 ? 5 : 10) * mag;
  const ticks: number[] = [];
  for (let t = Math.ceil(min / step) * step; t <= max + 1e-9; t += step) ticks.push(Math.round(t * 100) / 100);
  return ticks;
}

/** Continuous distribution as a plain-language box plot with an axis scale: box = middle 50%,
 *  tick = median, whiskers = 10th–90th percentile. Value column shows median + IQR. */
export function RangeBarCell({ meta, national, byCode, codes, marks }: {
  meta: RangeMeta; national: RangeVals; byCode: Record<string, RangeVals>; codes: string[];
  marks?: Record<string, RowMark>;
}) {
  const shown = codes.filter(c => byCode[c]);
  const all = [national, ...shown.map(c => byCode[c])];
  const lo = Math.min(...all.map(v => v.p10)), hi = Math.max(...all.map(v => v.p90));
  const pad = Math.max((hi - lo) * 0.06, 1);
  const AMIN = lo - pad, AMAX = hi + pad;
  const pos = (x: number) => ((x - AMIN) / (AMAX - AMIN)) * 100;
  const ticks = niceTicks(AMIN, AMAX);
  const u = (n: number) => meta.unit === '$k' ? `$${Math.round(n)}k` : `${Math.round(n)}`;

  return (
    <div className="px-3 py-3">
      <div className="text-xs text-foreground leading-snug font-medium mb-2">
        {meta.question} <span className="text-[10px] text-muted-foreground font-normal">
          ({meta.unit === 'wks' ? 'weeks' : meta.unit === '$k' ? '$ thousands' : 'years'})</span>
      </div>
      {/* axis */}
      <div className="flex items-end gap-2 mb-1">
        <span className="w-11 shrink-0" />
        <div className="flex-1 relative h-3 text-[9px] text-muted-foreground">
          {ticks.map(t => (
            <span key={t} className="absolute -translate-x-1/2 tabular-nums" style={{ left: `${pos(t)}%` }}>{u(t)}</span>
          ))}
        </div>
        <span className="w-16 shrink-0" />
      </div>
      <div className="space-y-1">
        {['__NAT__', ...shown].map(code => {
          const isNat = code === '__NAT__';
          const v = isNat ? national : byCode[code];
          const color = isNat ? NAT : getBlendColor(code);
          return (
            <div key={code} className="flex items-center gap-2 text-[10px] tabular-nums">
              <PartyRowLabel code={code} signature={marks?.[code]?.dot} mark={marks?.[code]?.mark} />
              <div className="flex-1 relative h-4">
                {/* faint gridlines at ticks */}
                {ticks.map(t => (
                  <div key={t} className="absolute inset-y-0" style={{ left: `${pos(t)}%`, width: 1, backgroundColor: '#f1f5f9' }} />
                ))}
                {/* whisker 10th–90th */}
                <div className="absolute top-1/2 -translate-y-1/2" style={{ left: `${pos(v.p10)}%`, width: `${pos(v.p90) - pos(v.p10)}%`, height: 1.5, backgroundColor: color, opacity: 0.5 }} />
                {[v.p10, v.p90].map((x, i) => (
                  <div key={i} className="absolute top-1/2 -translate-y-1/2" style={{ left: `${pos(x)}%`, width: 1.5, height: 7, backgroundColor: color, opacity: 0.55 }} />
                ))}
                {/* box: middle 50% */}
                <div className="absolute top-1/2 -translate-y-1/2 rounded-sm" style={{ left: `${pos(v.q25)}%`, width: `${pos(v.q75) - pos(v.q25)}%`, height: 11, backgroundColor: isNat ? '#cbd5e1' : color, opacity: isNat ? 1 : 0.8 }} />
                {/* median: solid dark tick, protruding above and below the box */}
                <div className="absolute top-1/2 -translate-y-1/2 rounded-full" style={{ left: `calc(${pos(v.median)}% - 1px)`, width: 2, height: 19, backgroundColor: '#0f172a' }} />
              </div>
              <span className="w-16 shrink-0 text-right leading-tight">
                <span className="font-semibold text-foreground">{u(v.median)}</span>
                <span className="block text-[9px] text-muted-foreground">{u(v.q25)}–{u(v.q75)}</span>
              </span>
            </div>
          );
        })}
      </div>
      <div className="text-[9px] text-muted-foreground mt-1.5 pl-[52px]">
        box = middle 50% (25th–75th pct) · tick = median · whisker = 10th–90th pct
      </div>
    </div>
  );
}

/** Mutually-exclusive battery as a 100% composition bar (nominal) or a diverging bar aligned on
 *  a pivot category (bipolar ordinal). Optional value column (e.g. median income). */
export function CompositionStackCell({ meta, national, byCode, codes, marks }: {
  meta: CompMeta; national: CompVals; byCode: Record<string, CompVals>; codes: string[];
  marks?: Record<string, RowMark>;
}) {
  const shown = codes.filter(c => byCode[c]);
  const colors = meta.colors ?? [];
  const pivot = meta.pivot ?? -1;
  const diverging = pivot >= 0;
  const last = meta.segLabels.length - 1;
  const norm = (p: number[]) => { const s = p.reduce((a, b) => a + b, 0) || 1; return p.map(x => x / s * 100); };
  const fmtVal = (v?: number) => v == null ? '' : meta.valueUnit === '$k' ? `$${Math.round(v)}k` : `${Math.round(v)}`;
  const hasVal = meta.valueUnit != null;

  const rowsData = ['__NAT__', ...shown].map(code => {
    const d = code === '__NAT__' ? national : byCode[code];
    return { code, raw: d.pcts, p: norm(d.pcts), value: d.value };
  });

  return (
    <div className="px-3 py-3">
      <div className="text-xs text-foreground leading-snug font-medium mb-1.5">{meta.question}</div>
      <div className="flex flex-wrap gap-x-2.5 gap-y-0.5 mb-1.5">
        {meta.segLabels.map((l, i) => (
          <span key={l} className="inline-flex items-center gap-1 text-[9px] text-muted-foreground">
            <span className="w-2 h-2 rounded-sm" style={{ backgroundColor: colors[i] }} />{l}
          </span>
        ))}
      </div>
      {/* Diverging: the middle category is pulled into its own column (like the "neither" agree
          layout) so the two poles diverge from a clean center and stay easy to compare. */}
      {diverging && (
        <div className="flex items-center gap-2 text-[9px] text-muted-foreground uppercase tracking-wide mb-0.5">
          <span className="w-11 shrink-0" />
          <span className="w-24 shrink-0 text-center">{meta.segLabels[pivot]}</span>
          <span className="w-7 shrink-0" />
          <span className="flex-1 text-center">distribution</span>
          <span className="w-7 shrink-0" />
        </div>
      )}
      <div className="space-y-1">
        {rowsData.map(({ code, raw, p, value }) => {
          if (diverging) {
            const neutral = p[pivot];
            const leftTot = p.slice(0, pivot).reduce((a, b) => a + b, 0);
            const rightTot = p.slice(pivot + 1).reduce((a, b) => a + b, 0);
            const segs: { left: number; width: number; color: string; title: string }[] = [];
            let lx = 50;
            for (let i = pivot - 1; i >= 0; i--) { const w = p[i] * 0.5; segs.push({ left: lx - w, width: w, color: colors[i], title: `${meta.segLabels[i]}: ${Math.round(raw[i])}%` }); lx -= w; }
            let rx = 50;
            for (let i = pivot + 1; i < p.length; i++) { const w = p[i] * 0.5; segs.push({ left: rx, width: w, color: colors[i], title: `${meta.segLabels[i]}: ${Math.round(raw[i])}%` }); rx += w; }
            return (
              <div key={code} className="flex items-center gap-2 text-[10px] tabular-nums">
                <PartyRowLabel code={code} signature={marks?.[code]?.dot} mark={marks?.[code]?.mark} />
                <div className="w-24 shrink-0 flex items-center gap-1" title={`${meta.segLabels[pivot]}: ${Math.round(neutral)}%`}>
                  <div className="relative h-3 flex-1 rounded-sm bg-muted overflow-hidden">
                    <div className="absolute inset-y-0 left-0" style={{ width: `${neutral}%`, backgroundColor: colors[pivot] }} />
                  </div>
                  <span className="w-6 text-right font-semibold text-foreground">{Math.round(neutral)}%</span>
                </div>
                <span className="w-7 shrink-0 text-right font-semibold" style={{ color: colors[0] }}>{Math.round(leftTot)}</span>
                <div className="flex-1 relative h-3.5 rounded-sm overflow-hidden bg-muted">
                  <div className="absolute inset-y-0 z-10" style={{ left: '50%', width: 1, backgroundColor: 'rgba(15,23,42,0.3)' }} />
                  {segs.map((s, i) => (
                    <div key={i} className="absolute inset-y-0" title={s.title}
                      style={{ left: `${s.left}%`, width: `${s.width}%`, backgroundColor: s.color }} />
                  ))}
                </div>
                <span className="w-7 shrink-0 font-semibold" style={{ color: colors[last] }}>{Math.round(rightTot)}</span>
              </div>
            );
          }
          let cum = 0;
          return (
            <div key={code} className="flex items-center gap-2 text-[10px] tabular-nums">
              <PartyRowLabel code={code} signature={marks?.[code]?.dot} mark={marks?.[code]?.mark} />
              <div className="flex-1 relative h-3.5 rounded-sm overflow-hidden bg-muted">
                {p.map((seg, i) => {
                  const left = cum; cum += seg;
                  return (
                    <div key={i} className="absolute inset-y-0" title={`${meta.segLabels[i]}: ${Math.round(raw[i])}%`}
                      style={{ left: `${left}%`, width: `${seg}%`, backgroundColor: colors[i] }} />
                  );
                })}
              </div>
              {hasVal && <span className="w-11 shrink-0 text-right font-semibold text-foreground">{fmtVal(value)}</span>}
            </div>
          );
        })}
      </div>
      {hasVal && <div className="text-[9px] text-muted-foreground mt-1 pl-[52px]">value column = median</div>}
    </div>
  );
}

/** Many-category nominal battery as a party × category heatmap — every real category shown
 *  (no "Other" merge), cell shaded by share with the exact % in the cell. */
export function HeatmapCell({ meta, national, byCode, codes, marks }: {
  meta: CompMeta; national: CompVals; byCode: Record<string, CompVals>; codes: string[];
  marks?: Record<string, RowMark>;
}) {
  const shown = codes.filter(c => byCode[c]);
  const rows = [{ code: '__NAT__', isNat: true, pcts: national.pcts },
    ...shown.map(c => ({ code: c, isNat: false, pcts: byCode[c].pcts }))];
  const scaleMax = Math.max(1, ...rows.flatMap(r => r.pcts));
  const cols = meta.segLabels.length;

  return (
    <div className="px-3 py-3">
      <div className="text-xs text-foreground leading-snug font-medium mb-2">{meta.question}</div>
      <div className="grid gap-px" style={{ gridTemplateColumns: `44px repeat(${cols}, minmax(0, 1fr))` }}>
        <span />
        {meta.segLabels.map(l => (
          <span key={l} className="text-[8.5px] text-muted-foreground text-center leading-tight px-0.5 pb-0.5" title={l}>{l}</span>
        ))}
        {rows.map(({ code, pcts }) => (
          <div key={code} className="contents">
            <PartyRowLabel code={code} className="self-center text-[10px]" signature={marks?.[code]?.dot} mark={marks?.[code]?.mark} />
            {pcts.map((v, i) => {
              // Cividis by within-grid share: dark navy = low → yellow = high. Perceptually
              // uniform and colorblind-safe; exact % is printed in the cell either way.
              const a = Math.min(1, v / scaleMax);
              const bg = cividisForFrac(a);
              return (
                <div key={i} className="h-6 flex items-center justify-center text-[9px] tabular-nums rounded-[2px]"
                  title={`${meta.segLabels[i]}: ${v.toFixed(1)}%`}
                  style={{ backgroundColor: bg, color: cividisText(bg) }}>
                  {v >= 0.5 ? Math.round(v) : ''}
                </div>
              );
            })}
          </div>
        ))}
      </div>
      <div className="text-[9px] text-muted-foreground mt-1.5">% of each party (row) in each category · darker = higher share</div>
    </div>
  );
}

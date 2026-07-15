import { getBlendColor } from '../../constants/parties';

// Shared row language with StackedBarCell/IntensityCell: `U.S.` + each selected party code,
// a w-11 label, a flex-1 track, and (range only) a w-11 value. National uses slate.
const NAT = '#64748b';

type RangeVals = { p10: number; q25: number; median: number; q75: number; p90: number };
type CompVals = { pcts: number[] };

export interface RangeMeta { question: string; unit: string }
export interface CompMeta { question: string; segLabels: string[]; colors: string[]; pivot?: number }

/** Continuous distribution as a plain-language box plot: box = middle 50%, tick = median,
 *  whiskers = 10th–90th percentile. One row per selected party + national, shared axis. */
export function RangeBarCell({ meta, national, byCode, codes }: {
  meta: RangeMeta; national: RangeVals; byCode: Record<string, RangeVals>; codes: string[];
}) {
  const shown = codes.filter(c => byCode[c]);
  const all = [national, ...shown.map(c => byCode[c])];
  const lo = Math.min(...all.map(v => v.p10)), hi = Math.max(...all.map(v => v.p90));
  const pad = Math.max((hi - lo) * 0.06, 1);
  const AMIN = lo - pad, AMAX = hi + pad;
  const pos = (x: number) => ((x - AMIN) / (AMAX - AMIN)) * 100;
  const fmt = (v: number) => meta.unit === '$k' ? `$${Math.round(v)}k`
    : meta.unit === 'wks' ? `${Math.round(v)}w` : `${Math.round(v)}`;

  return (
    <div className="px-3 py-3">
      <div className="text-xs text-foreground leading-snug font-medium mb-2">{meta.question}</div>
      <div className="space-y-1">
        {['__NAT__', ...shown].map(code => {
          const isNat = code === '__NAT__';
          const v = isNat ? national : byCode[code];
          const color = isNat ? NAT : getBlendColor(code);
          return (
            <div key={code} className="flex items-center gap-2 text-[10px] tabular-nums">
              <span className="w-11 shrink-0 font-bold text-right" style={{ color }}>{isNat ? 'U.S.' : code}</span>
              <div className="flex-1 relative h-4"
                title={`${isNat ? 'U.S.' : code}: median ${v.median} · middle 50% ${v.q25}–${v.q75} · 10–90% ${v.p10}–${v.p90}`}>
                <div className="absolute top-1/2 -translate-y-1/2" style={{ left: `${pos(v.p10)}%`, width: `${pos(v.p90) - pos(v.p10)}%`, height: 1.5, backgroundColor: color, opacity: 0.5 }} />
                {[v.p10, v.p90].map((x, i) => (
                  <div key={i} className="absolute top-1/2 -translate-y-1/2" style={{ left: `${pos(x)}%`, width: 1.5, height: 8, backgroundColor: color, opacity: 0.55 }} />
                ))}
                <div className="absolute top-1/2 -translate-y-1/2 rounded-sm" style={{ left: `${pos(v.q25)}%`, width: `${pos(v.q75) - pos(v.q25)}%`, height: 12, backgroundColor: isNat ? '#cbd5e1' : color, opacity: isNat ? 1 : 0.85 }} />
                <div className="absolute top-1/2 -translate-y-1/2" style={{ left: `${pos(v.median)}%`, width: 2, height: 15, backgroundColor: '#0f172a', boxShadow: '0 0 0 1px rgba(255,255,255,0.9)' }} />
              </div>
              <span className="w-11 shrink-0 text-right" style={{ color: isNat ? NAT : 'inherit' }}>{fmt(v.median)}</span>
            </div>
          );
        })}
      </div>
      <div className="text-[9px] text-muted-foreground mt-1.5 pl-[52px]">
        box = middle 50% · tick = median · whisker = 10th–90th percentile{meta.unit === 'wks' ? ' · weeks' : meta.unit === '$k' ? ' · $ thousands' : ' · years'}
      </div>
    </div>
  );
}

/** Mutually-exclusive battery as a 100% composition bar (nominal) or a diverging bar aligned on
 *  a pivot category (bipolar ordinal). One row per selected party + national. */
export function CompositionStackCell({ meta, national, byCode, codes }: {
  meta: CompMeta; national: CompVals; byCode: Record<string, CompVals>; codes: string[];
}) {
  const shown = codes.filter(c => byCode[c]);
  const diverging = meta.pivot != null;
  const norm = (p: number[]) => { const s = p.reduce((a, b) => a + b, 0) || 1; return p.map(x => x / s * 100); };

  const rowsData = ['__NAT__', ...shown].map(code => {
    const isNat = code === '__NAT__';
    const raw = (isNat ? national : byCode[code]).pcts;
    return { code, isNat, raw, p: norm(raw) };
  });

  // Diverging: common half-width H so the pivot-segment center sits at 50% on every row and
  // nothing clips (H bounds the largest left/right extent across shown rows).
  let H = 1;
  if (diverging) {
    for (const rd of rowsData) {
      const before = rd.p.slice(0, meta.pivot!).reduce((a, b) => a + b, 0);
      const center = before + rd.p[meta.pivot!] / 2;
      H = Math.max(H, center, 100 - center);
    }
  }

  return (
    <div className="px-3 py-3">
      <div className="text-xs text-foreground leading-snug font-medium mb-1.5">{meta.question}</div>
      <div className="flex flex-wrap gap-x-2.5 gap-y-0.5 mb-1.5">
        {meta.segLabels.map((l, i) => (
          <span key={l} className="inline-flex items-center gap-1 text-[9px] text-muted-foreground">
            <span className="w-2 h-2 rounded-sm" style={{ backgroundColor: meta.colors[i] }} />{l}
          </span>
        ))}
      </div>
      <div className="space-y-1">
        {rowsData.map(({ code, isNat, raw, p }) => {
          const center = diverging ? p.slice(0, meta.pivot!).reduce((a, b) => a + b, 0) + p[meta.pivot!] / 2 : 0;
          let cum = 0;
          return (
            <div key={code} className="flex items-center gap-2 text-[10px] tabular-nums">
              <span className="w-11 shrink-0 font-bold text-right" style={{ color: isNat ? NAT : getBlendColor(code) }}>{isNat ? 'U.S.' : code}</span>
              <div className="flex-1 relative h-3.5 rounded-sm overflow-hidden bg-muted">
                {diverging && <div className="absolute inset-y-0 z-10" style={{ left: '50%', width: 1, backgroundColor: 'rgba(15,23,42,0.28)' }} />}
                {p.map((seg, i) => {
                  const left = diverging ? 50 + (cum - center) * 50 / H : cum;
                  const width = diverging ? seg * 50 / H : seg;
                  cum += seg;
                  return (
                    <div key={i} className="absolute inset-y-0" title={`${meta.segLabels[i]}: ${Math.round(raw[i])}%`}
                      style={{ left: `${left}%`, width: `${width}%`, backgroundColor: meta.colors[i] }} />
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

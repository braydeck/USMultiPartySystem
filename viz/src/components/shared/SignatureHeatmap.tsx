import { F5_ORDER, PARTY_NAMES, getPartyColor } from '../../constants/parties';
import { cividisForFrac, cividisText } from '../../lib/cividis';
import type { RowMark } from './PartyRowLabel';
import { FactorTags } from './DistributionCells';

// A single-number-per-party heatmap: items on rows, parties on fixed F5 columns + a US
// baseline column. Shade = value (cividis). Each cell carries the signature tags —
// C (internally cohesive), M/D (mainstream/deviant vs the U.S.). Divergent rows (parties
// far apart) are marked on the row label. Toggled-off parties leave a blank slot so every
// column holds its horizontal position.

export interface HeatRow {
  key: string;
  question: string;
  pcts: Record<string, number>;
  overall: number | null;
  maxVal: number;
  unit: string;
  marks: Record<string, RowMark>;
  highlighted: boolean;     // divergent: parties far apart (maxGap ≥ minGap)
  factorShorts?: string[];
}

function tagOf(m?: RowMark): string {
  if (!m) return '';
  const parts: string[] = [];
  if (m.dot) parts.push('C');
  if (m.mark) parts.push(m.mark);
  return parts.join('·');
}

function Cell({ row, code }: { row: HeatRow; code: string }) {
  const v = row.pcts[code];
  if (v == null) return <div className="h-9 rounded-sm bg-transparent" />;  // toggled-off → blank slot
  const frac = row.maxVal ? v / row.maxVal : 0;
  const bg = cividisForFrac(frac);
  const fg = cividisText(bg);
  const tag = tagOf(row.marks[code]);
  const disp = row.unit === '%' ? Math.round(v) : (v % 1 === 0 ? v : v.toFixed(1));
  return (
    <div
      className="h-9 rounded-sm flex flex-col items-center justify-center leading-none"
      style={{ backgroundColor: bg, color: fg }}
      title={`${PARTY_NAMES[code] ?? code}: ${disp}${row.unit === '%' ? '%' : ' ' + row.unit}${tag ? ` · ${tag}` : ''}`}
    >
      <span className="text-[11px] font-semibold tabular-nums">{disp}</span>
      {tag && <span className="text-[8px] font-bold opacity-80 tracking-tight mt-0.5">{tag}</span>}
    </div>
  );
}

export function SignatureHeatmap({ rows, selected }: { rows: HeatRow[]; selected: string[] }) {
  const sel = new Set(selected);
  const COLS = `grid-cols-[minmax(160px,1.5fr)_44px_repeat(10,minmax(26px,1fr))]`;
  return (
    <div className="px-3 py-2 overflow-x-auto">
      <div className="min-w-[720px]">
        {/* header */}
        <div className={`grid ${COLS} gap-1 items-end pb-1 sticky top-0 z-10 bg-slate-50/95`}>
          <div className="text-[9px] uppercase tracking-widest text-muted-foreground">Position</div>
          <div className="text-[9px] font-bold text-center text-slate-500">US</div>
          {F5_ORDER.map((p) => (
            <div
              key={p}
              className="text-[9px] font-bold text-center rounded px-0.5 py-0.5"
              style={{
                backgroundColor: sel.has(p) ? getPartyColor(p) + '33' : 'transparent',
                color: sel.has(p) ? getPartyColor(p) : '#cbd5e1',
              }}
              title={PARTY_NAMES[p]}
            >
              {p}
            </div>
          ))}
        </div>

        {rows.map((r) => (
          <div key={r.key} className={`grid ${COLS} gap-1 items-center py-0.5`}>
            <div className={`text-[10px] leading-tight pr-1 flex items-center gap-1 ${r.highlighted ? 'font-medium' : ''}`}>
              {r.highlighted && <span className="text-amber-500 text-[10px]" title="Parties diverge on this item">◆</span>}
              {r.factorShorts && r.factorShorts.length > 0 && <FactorTags shorts={r.factorShorts} />}
              <span className="truncate" title={r.question}>{r.question}</span>
            </div>
            {/* US baseline */}
            {r.overall != null ? (
              <div className="h-9 rounded-sm flex items-center justify-center bg-slate-200 text-slate-700 text-[11px] font-semibold tabular-nums"
                title={`U.S. average: ${Math.round(r.overall)}${r.unit === '%' ? '%' : ' ' + r.unit}`}>
                {r.unit === '%' ? Math.round(r.overall) : r.overall}
              </div>
            ) : <div className="h-9" />}
            {F5_ORDER.map((p) => <Cell key={p} row={r} code={p} />)}
          </div>
        ))}

        {/* legend */}
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-[9px] text-muted-foreground mt-2 pt-1 border-t border-border/40">
          <span className="flex items-center gap-1">
            {[0, .33, .66, 1].map((t) => <span key={t} className="w-3 h-2.5" style={{ backgroundColor: cividisForFrac(t) }} />)}
            shade = % support
          </span>
          <span><b>C</b> cohesive (party united)</span>
          <span><b>M</b> mainstream (near US)</span>
          <span><b>D</b> deviant (far from US)</span>
          <span className="text-amber-500">◆ parties diverge</span>
        </div>
      </div>
    </div>
  );
}

import { PARTY_NAMES, getBlendColor } from '../../constants/parties';
import { cividisForFrac, cividisText } from '../../lib/cividis';
import { type RowMark, SigTag } from './PartyRowLabel';
import { FactorTags } from './DistributionCells';

// A single-number-per-party heatmap: items on rows, parties on columns + a US baseline column.
// Shade = value (cividis). Each cell carries the signature tags — C (internally cohesive, lower
// left) and M/D (mainstream/deviant vs the U.S., lower right). Divergent rows (parties far apart)
// are marked on the row label. Columns collapse to the selected parties (kept in the PC order the
// caller passes); it shares the cividis grid language with the race/ethnicity HeatmapCell.

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

function Cell({ row, code }: { row: HeatRow; code: string }) {
  const v = row.pcts[code];
  if (v == null) return <div className="h-9 rounded-[2px] bg-muted/40" />;  // selected but no data for this item
  const frac = row.maxVal ? v / row.maxVal : 0;
  const bg = cividisForFrac(frac);
  const fg = cividisText(bg);
  const m = row.marks[code];
  const cohesive = !!m?.dot;
  const mark = m?.mark ?? null;
  const disp = row.unit === '%' ? Math.round(v) : (v % 1 === 0 ? v : v.toFixed(1));
  const tags = [cohesive ? 'C' : null, mark].filter(Boolean).join('·');
  return (
    <div
      className="relative h-9 rounded-[2px] flex items-start justify-center pt-1"
      style={{ backgroundColor: bg, color: fg }}
      title={`${PARTY_NAMES[code] ?? code}: ${disp}${row.unit === '%' ? '%' : ' ' + row.unit}${tags ? ` · ${tags}` : ''}`}
    >
      <span className="text-[10px] font-semibold tabular-nums">{disp}</span>
      {/* C lower-left, M/D lower-right — boxed tags, matching the distribution-row labels */}
      {cohesive && <span className="absolute left-0.5 bottom-0.5"><SigTag kind="C" /></span>}
      {mark && <span className="absolute right-0.5 bottom-0.5"><SigTag kind={mark} /></span>}
    </div>
  );
}

export function SignatureHeatmap({ rows, selected }: { rows: HeatRow[]; selected: string[] }) {
  // Columns collapse to the selected parties (already PC-ordered by the caller). Widths are
  // capped so cells stay compact with few parties instead of ballooning to fill the card.
  const COLS = `minmax(200px,360px) 40px repeat(${selected.length}, minmax(44px,64px))`;
  return (
    <div className="px-3 py-2 overflow-x-auto">
      <div className="min-w-fit">
        {/* header */}
        <div className="grid gap-px items-end pb-1 sticky top-0 z-10 bg-slate-50/95" style={{ gridTemplateColumns: COLS }}>
          <span className="text-[9px] uppercase tracking-widest text-muted-foreground">Position</span>
          <span className="text-[9px] font-bold text-center text-slate-500">US</span>
          {selected.map((p) => (
            <span key={p} className="text-[9px] font-bold text-center truncate px-0.5" style={{ color: getBlendColor(p) }} title={PARTY_NAMES[p] ?? p}>{p}</span>
          ))}
        </div>

        {rows.map((r) => (
          <div key={r.key} className="grid gap-px items-center py-1 border-t border-border/30" style={{ gridTemplateColumns: COLS }}>
            <div className={`text-[10px] leading-snug pr-2 ${r.highlighted ? 'font-medium' : ''}`}>
              {r.highlighted && <span className="text-amber-500 mr-1" title="Parties diverge on this item">◆</span>}
              {r.factorShorts && r.factorShorts.length > 0 && <FactorTags shorts={r.factorShorts} />}
              <span className="break-words">{r.question}</span>
            </div>
            {/* US baseline — shaded on the same cividis scale so its contrast with the
                parties is visible; a subtle inset ring marks it as the reference column. */}
            {r.overall != null ? (() => {
              const bg = cividisForFrac(r.maxVal ? r.overall / r.maxVal : 0);
              return (
                <div className="h-9 rounded-[2px] flex items-center justify-center text-[10px] font-semibold tabular-nums ring-1 ring-inset ring-slate-500/50"
                  style={{ backgroundColor: bg, color: cividisText(bg) }}
                  title={`U.S. average: ${Math.round(r.overall)}${r.unit === '%' ? '%' : ' ' + r.unit}`}>
                  {r.unit === '%' ? Math.round(r.overall) : r.overall}
                </div>
              );
            })() : <div className="h-9" />}
            {selected.map((p) => <Cell key={p} row={r} code={p} />)}
          </div>
        ))}

        {/* legend */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[10px] text-muted-foreground mt-2 pt-1.5 border-t border-border/40">
          <span className="flex items-center gap-1">
            {[0, .33, .66, 1].map((t) => <span key={t} className="w-3 h-2.5" style={{ backgroundColor: cividisForFrac(t) }} />)}
            shade = % support
          </span>
          <span className="flex items-center gap-1"><SigTag kind="C" /> cohesive (party united)</span>
          <span className="flex items-center gap-1"><SigTag kind="M" /> mainstream (near US)</span>
          <span className="flex items-center gap-1"><SigTag kind="D" /> deviance (far from US)</span>
          <span className="flex items-center gap-1 text-amber-600"><span className="text-amber-500">◆</span> parties diverge</span>
        </div>
      </div>
    </div>
  );
}

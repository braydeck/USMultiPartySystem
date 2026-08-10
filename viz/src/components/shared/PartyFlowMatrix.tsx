import { PARTY_COLORS, PARTY_NAMES, getContrastText } from '../../constants/parties';
import { TABLE_HEADER } from '../../constants/typography';
import { CIVIDIS_COLORS, cividisForFrac, cividisText } from '../../lib/cividis';
import { PartyCode } from './PartyRowLabel';
import { effectivePartners, type FlowRow } from '../../lib/partyFlow';

const name = (p: string) => PARTY_NAMES[p] ?? p;
const color = (p: string) => PARTY_COLORS[p] ?? '#6b7280';
const pct = (x: number) => Math.round(x * 100);

const LABEL_COL = 'w-28 shrink-0';
const PARTNER_COL = 'w-10 shrink-0';
const PARTNER_HINT =
  'Effective number of partners (1 / sum of squared shares). 2.0 is as concentrated as an even '
  + 'two-way split; higher means the votes spread across more parties.';

/** What a row is and what a column is, rendered on the matrix itself rather than in prose. */
export interface FlowAxes { row: string; col: string }

/** Stacked bars, one row per party. Full party name to the left, and the wide segments
 *  carry their own label so the bar reads without the legend. */
export function PartyFlowBars({ rows, axes }: { rows: FlowRow[]; axes: FlowAxes }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-end gap-2">
        <span className={`${LABEL_COL} ${TABLE_HEADER}`}>↓ {axes.row}</span>
        <span className={`flex-1 ${TABLE_HEADER}`}>→ {axes.col}</span>
        <span className={`${PARTNER_COL} text-right ${TABLE_HEADER}`} title={PARTNER_HINT}>partners</span>
      </div>
      {rows.map(row => {
        const segs = row.selfShare != null
          ? [{ party: row.party, share: row.selfShare }, ...row.segments]
          : row.segments;
        return (
          <div key={row.party} className="flex items-center gap-2">
            <span className={`${LABEL_COL} text-xs font-medium truncate`} style={{ color: color(row.party) }}>
              {name(row.party)}
            </span>
            <div className="flex h-7 flex-1 rounded overflow-hidden border border-border">
              {segs.map(s => {
                const c = color(s.party);
                const isSelf = s.party === row.party;
                return (
                  <div
                    key={s.party}
                    className="relative flex items-center justify-center overflow-hidden"
                    style={{
                      width: `${s.share * 100}%`,
                      backgroundColor: c,
                      opacity: isSelf ? 1 : 0.8,
                      minWidth: s.share > 0.03 ? undefined : 2,
                    }}
                    title={`${name(s.party)}: ${pct(s.share)}%`}
                  >
                    {s.share >= 0.10 && (
                      <span className="text-3xs font-bold whitespace-nowrap px-1 chip-text"
                        style={{ color: getContrastText(c) }}>
                        {s.party} {pct(s.share)}%
                      </span>
                    )}
                    {s.share >= 0.05 && s.share < 0.10 && (
                      <span className="text-4xs font-semibold chip-text" style={{ color: getContrastText(c) }}>
                        {pct(s.share)}%
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
            <span className={`${PARTNER_COL} text-right text-xs tabular-nums text-foreground`}
              title={PARTNER_HINT}>
              {effectivePartners(row.segments).toFixed(1)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/** The same matrix as a grid. Rows read across, and the shared cividis scale makes cells
 *  comparable between rows, which stacked bars cannot do: a 14% segment looks identical in
 *  every bar regardless of what it sits beside.
 *
 *  Columns follow the row order, so the self cells fall on the diagonal and leave it empty.
 *  Any party that lends votes without holding a row of its own is appended after them. */
export function PartyFlowHeatmap({ rows, axes, selfLabel }: {
  rows: FlowRow[];
  axes: FlowAxes;
  /** Header for the separated own-share column. Omit when rows carry no `selfShare`. */
  selfLabel?: string;
}) {
  const rowOrder = rows.map(r => r.party);
  const extras = [...new Set(rows.flatMap(r => r.segments.filter(s => s.share > 0).map(s => s.party)))]
    .filter(p => !rowOrder.includes(p));
  const cols = [...rowOrder, ...extras];
  const max = Math.max(...rows.flatMap(r => r.segments.map(s => s.share)), 0.0001);
  const hasSelf = rows.some(r => r.selfShare != null);

  return (
    <div className="overflow-x-auto">
      <div className="inline-block min-w-full">
        <div className="flex items-end gap-px mb-1">
          <span className={`${LABEL_COL} ${TABLE_HEADER} leading-tight pr-2`}>
            ↓ {axes.row}<br />→ {axes.col}
          </span>
          {hasSelf && <span className={`w-11 shrink-0 text-center ${TABLE_HEADER}`}>{selfLabel ?? 'Own'}</span>}
          {hasSelf && <span className="w-2 shrink-0" />}
          {cols.map(c => (
            <span key={c} className="flex-1 min-w-8 flex justify-center text-3xs font-bold" title={name(c)}>
              <PartyCode code={c} />
            </span>
          ))}
          <span className={`${PARTNER_COL} text-right ${TABLE_HEADER}`} title={PARTNER_HINT}>partners</span>
        </div>

        {rows.map(row => {
          const byParty: Record<string, number> = {};
          for (const s of row.segments) byParty[s.party] = s.share;
          return (
            <div key={row.party} className="flex items-stretch gap-px mb-px">
              <span className={`${LABEL_COL} text-xs font-medium truncate self-center`} style={{ color: color(row.party) }}>
                {name(row.party)}
              </span>
              {hasSelf && (
                <span
                  className="w-11 shrink-0 h-7 flex items-center justify-center rounded-sm text-3xs font-bold tabular-nums"
                  style={{ backgroundColor: color(row.party), color: getContrastText(color(row.party)) }}
                  title={`${name(row.party)}: ${pct(row.selfShare ?? 0)}% own`}
                >
                  {pct(row.selfShare ?? 0)}%
                </span>
              )}
              {hasSelf && <span className="w-2 shrink-0" />}
              {cols.map(c => {
                if (c === row.party) {
                  return (
                    <span key={c} className="flex-1 min-w-8 h-7 rounded-sm bg-muted/40"
                      title={`${name(row.party)} — own votes are in the ${selfLabel ?? 'Own'} column`} />
                  );
                }
                const share = byParty[c];
                const bg = share ? cividisForFrac(share / max) : undefined;
                return (
                  <span
                    key={c}
                    className="flex-1 min-w-8 h-7 flex items-center justify-center rounded-sm text-3xs font-semibold tabular-nums"
                    style={bg
                      ? { backgroundColor: bg, color: cividisText(bg) }
                      : { backgroundColor: 'var(--muted)' }}
                    title={`${name(row.party)} ← ${name(c)}: ${pct(share ?? 0)}%`}
                  >
                    {share && share >= 0.02 ? pct(share) : ''}
                  </span>
                );
              })}
              <span className={`${PARTNER_COL} h-7 flex items-center justify-end text-xs tabular-nums text-foreground`}
                title={PARTNER_HINT}>
                {effectivePartners(row.segments).toFixed(1)}
              </span>
            </div>
          );
        })}

        <div className={`flex items-center gap-2 mt-2 ${TABLE_HEADER}`}>
          <span>0%</span>
          <span className="h-2 w-24 rounded-sm"
            style={{ backgroundImage: `linear-gradient(90deg, ${CIVIDIS_COLORS.join(', ')})` }} />
          <span>{pct(max)}%</span>
          {hasSelf && <span className="normal-case tracking-normal">own share on its own scale</span>}
        </div>
      </div>
    </div>
  );
}

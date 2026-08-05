import { useCallback, useMemo, type ReactNode } from 'react';
import { PARTY_NAMES, getContrastText } from '../../constants/parties';
import { HexStateCartogram, type StateFill } from '../shared/HexStateCartogram';
import { dealTiles, f5FillOrder, partyOf, tileColor } from '../../lib/stateTiles';
import type { Cartogram } from '../../lib/hexCartogram';
import { largestRemainder } from '../../lib/ecAllocation';
import { BAR_HEIGHT, LABEL_MIN_WIDTH } from '../house/FPTPvsSTV';
import { useElementWidth } from '../../hooks/useElementWidth';
import { CARD_HINT } from '../../constants/typography';

/**
 * The presidency cartogram's rendering, shared by every view of it.
 *
 * Two sections draw the same map from different numbers — the elector rules without the
 * instructive ballot, and the top-two allocations with it — and both need the identical hex
 * tiling, sidebar, tooltip and legend order. Only the counts and the controls differ, so
 * those are the caller's job and everything below the controls lives here once.
 *
 * Callers pass a single `view` object rather than a dozen props: adding a fourteenth
 * parameter to a component is how a shared renderer stops being worth sharing.
 *
 * What changes between views is the denominator, and each denominator gets its own tiling,
 * because making the denominator visible is a cartogram's whole job:
 *
 * - the **population basis** gives 4,365 tiles, states sized by their people, the smallest
 *   still holding ten — enough to read a five-way split off a state the size of Wyoming.
 * - the **electoral basis** gives 975 tiles, one per elector, states scaled to electoral
 *   weight, so the two senatorial electors every state gets are part of the shape and
 *   Wyoming is drawn a third larger than its people alone would make it.
 *
 * Switching between the two redraws the country, and the difference between the two
 * silhouettes is the college's thumb on the scale.
 */
export interface CartogramView {
  basis: 'pop' | 'ec';
  /** Per-state party counts, keyed by state abbreviation. */
  countsByAbbr: Record<string, Record<string, number>>;
  /**
   * Whether `countsByAbbr` holds shares to spread across the state's tiles (true) or
   * counts that already correspond one-to-one with tiles (false).
   */
  apportion: boolean;
  /** Electors per state; null on the population basis, where a tile is not an elector. */
  evByAbbr: Record<string, number> | null;
  /** National totals, driving both the legend order and its values. */
  totals: { code: string; value: number }[];
  /**
   * Electors needed to win, marked on the national bar. Omitted on the population basis, where
   * there is no threshold to cross — a share view has no majority elector point.
   */
  majority?: number;
  format: (n: number) => string;
  /** Right of the state abbreviation in the sidebar header, e.g. " · 106 electors". */
  perStateSuffix: (abbr: string) => string;
  /** Shown in place of a state name before the reader hovers anything. */
  nationalLabel: string;
  /** The one-line reading of the view, under the legend. */
  summary: string;
  /** Above the map: what this view is showing. */
  blurb: string;
  /** Below the map: what a tile and a state's size mean here. */
  footnote: string;
  ariaLabel: string;
  subject: string;
}

const nameOf = (code: string) => PARTY_NAMES[partyOf(code)] ?? partyOf(code);

export function CartogramPanel({ view, children }: { view: CartogramView; children?: ReactNode }) {
  const { basis, countsByAbbr, apportion, evByAbbr, totals, format } = view;
  // Measured on the bar itself, not the viewport: the sidebar is a 176px column on desktop and
  // full width on mobile, so which segments can carry a label depends on the bar, not the screen.
  const [barRef, barWidth] = useElementWidth<HTMLDivElement>();

  const order = useMemo(() => f5FillOrder(totals.map(t => t.code)), [totals]);

  const fills = useCallback((cg: Cartogram): StateFill[] => cg.states.map(st => {
    const raw = countsByAbbr[st.abbr];
    const counts = apportion
      ? (raw ? largestRemainder(raw, st.seatCount) : {})
      : raw ?? {};
    return { abbr: st.abbr, groups: dealTiles(counts, st.seatPaths) };
  }), [countsByAbbr, apportion]);

  const splitFor = (abbr: string): string[] => {
    const counts = countsByAbbr[abbr];
    if (!counts) return [];
    return f5FillOrder(Object.keys(counts)).filter(c => (counts[c] ?? 0) > 0);
  };

  const rawValue = (code: string, abbr: string | null): number => {
    const local = abbr ? countsByAbbr[abbr] : undefined;
    return local ? local[code] ?? 0 : totals.find(t => t.code === code)?.value ?? 0;
  };
  const valueFor = (code: string, abbr: string | null) => format(rawValue(code, abbr));

  /**
   * Share as a stacked bar, not a column of numbers: the reader's question is how the state
   * divides, and a bar answers it before any figure is read.
   *
   * Same grammar as the seat-share cards, legend included: it lists ONLY the slivers too narrow
   * to carry their own inline label, and disappears entirely when every segment labels itself. A
   * legend that restates a bar the reader can already read is noise.
   */
  const sidebar = (abbr: string | null) => {
    const codes = abbr ? splitFor(abbr) : order;
    const rows = codes.map(code => ({ code, value: rawValue(code, abbr) })).filter(r => r.value > 0);
    // On the electoral basis the bar's question is "does anyone clear the line", so it sorts by
    // electors descending: the leader starts at the left edge and the majority marker reads
    // directly as how far short it falls. The F5 left-right spectrum is the wrong ordering for
    // that, and is kept only on the population basis, where the spectrum IS the information.
    if (basis === 'ec') rows.sort((x, y) => y.value - x.value || x.code.localeCompare(y.code));
    const sum = rows.reduce((s, r) => s + r.value, 0) || 1;
    const narrow = new Set(
      rows.filter(r => !barWidth || (r.value / sum) * barWidth < LABEL_MIN_WIDTH).map(r => r.code),
    );
    return (
      <>
        <div className="text-xs font-semibold text-foreground mb-2">
          {abbr ? (
            <>
              {abbr}
              <span className="font-normal text-muted-foreground">{view.perStateSuffix(abbr)}</span>
            </>
          ) : (
            <span className="text-muted-foreground">{view.nationalLabel} · hover a state</span>
          )}
        </div>

        <div ref={barRef} className="relative flex rounded-lg overflow-hidden" style={{ height: BAR_HEIGHT }}>
          {rows.map(({ code, value }) => {
            const w = (value / sum) * 100;
            const color = tileColor(code);
            return (
              <div key={code}
                title={`${nameOf(code)}: ${valueFor(code, abbr)}`}
                className="seat-segment flex min-w-0 items-center justify-center overflow-hidden"
                style={{ width: `${w}%`, backgroundColor: color, minWidth: w < 3 ? 2 : 0 }}>
                <span className="seat-segment-label text-2xs font-bold leading-tight text-center px-0.5 chip-text"
                  style={{ color: getContrastText(color) }}>
                  {partyOf(code)}<br />{valueFor(code, abbr)}
                </span>
              </div>
            );
          })}
          {/* Where the majority sits, same dashed marker the elector cards use. Only on the
              national bar: a hovered state's bar sums to that state's electors, so a national
              threshold drawn on it would land far off the right edge. */}
          {!abbr && view.majority != null && view.majority <= sum && (
            <div className="absolute top-0 bottom-0 border-l-2 border-dashed border-slate-900 pointer-events-none"
              style={{
                left: `${(view.majority / sum) * 100}%`,
                // A white halo, because the marker can land mid-label and the inline labels carry
                // their own dark text-shadow: without it the line and the digits merge into each
                // other and "200" reads as "20 0".
                filter: 'drop-shadow(0 0 1.5px rgba(255,255,255,0.95))',
              }}
              title={`${view.majority} electors to win`} />
          )}
        </div>
        {!abbr && view.majority != null && view.majority <= sum && (
          <div className="text-3xs tabular-nums text-muted-foreground mt-0.5 text-right">
            {view.majority} to win
          </div>
        )}

        {rows.some(r => narrow.has(r.code)) && (
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1">
            {rows.filter(r => narrow.has(r.code)).map(({ code }) => (
              <span key={code} className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm shrink-0" style={{ backgroundColor: tileColor(code) }} />
                <span className="text-xs text-foreground font-semibold">{nameOf(code)}</span>
                <span className="text-xs tabular-nums text-muted-foreground">{valueFor(code, abbr)}</span>
              </span>
            ))}
          </div>
        )}

        <div className="mt-3 pt-2 border-t border-border text-3xs text-muted-foreground leading-snug">
          {view.summary}
        </div>
      </>
    );
  };

  const tooltip = (abbr: string) => (
    <>
      <span className="font-semibold">{abbr}</span>
      {evByAbbr && ` — ${evByAbbr[abbr] ?? 0} elector${evByAbbr[abbr] === 1 ? '' : 's'}`}
      <div className="flex flex-wrap gap-1 mt-1">
        {splitFor(abbr).map(c => (
          <span key={c} className="px-1 rounded text-3xs font-bold text-white"
            style={{ backgroundColor: tileColor(c) }} title={nameOf(c)}>
            {partyOf(c)} {valueFor(c, abbr)}
          </span>
        ))}
      </div>
    </>
  );

  return (
    <div className="space-y-2">
      {children}
      <p className={CARD_HINT}>{view.blurb}</p>
      <HexStateCartogram
        basis={basis}
        fills={fills}
        sidebar={sidebar}
        tooltip={tooltip}
        ariaLabel={view.ariaLabel}
        subject={view.subject}
        footnote={view.footnote}
      />
    </div>
  );
}

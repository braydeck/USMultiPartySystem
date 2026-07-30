import { whiskerGeometry } from '../../lib/whisker';

/** A whisker overlay for an existing bar: a horizontal span from lo to hi with a
 *  centre tick at the expected value. Absolutely positioned, so the parent must be
 *  `relative`. Renders nothing when there is no interval, so consumers degrade
 *  gracefully at stops without uncertainty data. */
export function SeatWhisker({ lo, hi, centre, max, title }: {
  lo: number; hi: number; centre: number; max: number; title?: string;
}) {
  const g = whiskerGeometry(lo, hi, centre, max);
  if (!g) return null;
  return (
    // inset-0 (not inset-y-0): children are positioned with left:X%, so this container
    // must span the parent's full width or those percentages resolve against 0px.
    <div className="absolute inset-0 pointer-events-none" aria-hidden="true" title={title}>
      <div className="absolute top-1/2 -translate-y-1/2 h-px bg-foreground/70"
        style={{ left: `${g.leftPct}%`, width: `${g.widthPct}%` }} />
      {[g.leftPct, g.leftPct + g.widthPct].map((x, i) => (
        <div key={i} className="absolute top-1/2 -translate-y-1/2 w-px h-2 bg-foreground/70"
          style={{ left: `${x}%` }} />
      ))}
      <div className="absolute top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-foreground/85 -ml-[3px]"
        style={{ left: `${g.centrePct}%` }} />
    </div>
  );
}

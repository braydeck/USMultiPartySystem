// A small caret above a 100% stacked bar at the 50% point, where a majority starts. It sits in the
// gap between the bar's label row and the bar, so it adds no height. The parent must be
// `relative` and must not clip (the bar itself usually does, so wrap it).
export function MajorityMark() {
  return (
    <span aria-hidden
      className="pointer-events-none absolute left-1/2 bottom-full -translate-x-1/2 text-muted-foreground"
      style={{
        width: 0, height: 0,
        borderLeft: '4px solid transparent', borderRight: '4px solid transparent',
        borderTop: '4px solid currentColor',
      }} />
  );
}

/** A dashed line at 50% down through a seat bar (and any strip above it), under the caret. Same
 *  parent rules as MajorityMark. */
export function MajorityLine() {
  return <span aria-hidden className="pointer-events-none absolute left-1/2 top-0 bottom-0 z-10 border-l border-dashed border-foreground/50" />;
}

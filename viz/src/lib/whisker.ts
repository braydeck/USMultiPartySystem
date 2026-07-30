/** Geometry for a whisker overlay, in percentages of an axis running 0…max.
 *  Clamped so a wide interval can never overflow its track. Null when there is
 *  nothing meaningful to draw. */
export function whiskerGeometry(
  lo: number, hi: number, centre: number, max: number,
): { leftPct: number; widthPct: number; centrePct: number } | null {
  if (!(max > 0) || !(hi > lo)) return null;
  const pct = (v: number) => Math.min(100, Math.max(0, (v / max) * 100));
  const leftPct = pct(lo);
  return { leftPct, widthPct: pct(hi) - leftPct, centrePct: pct(centre) };
}

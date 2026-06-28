import * as d3 from 'd3';

// vik (Fabio Crameri's Scientific Colour Maps): diverging blue (low) → red (high),
// with a true neutral center so the midpoint reads as "no signal" rather than warm.
// 11 symmetric control points; index 5 (#ece8de) is the neutral center.
export const VIK_COLORS = [
  '#001261', '#1c3f7a', '#3f6c96', '#79a3c0', '#bcd5e3',
  '#ece8de',
  '#e7bda2', '#cf8a6a', '#b25640', '#7f2418', '#59121b',
];

// piecewise (not basis-spline) so the interpolator passes through every control point —
// t = 0.5 lands exactly on the neutral center, keeping the scale centered.
export const interpolateVik = d3.piecewise(d3.interpolateRgb, VIK_COLORS);

/** Map a signed z-score to a vik color (blue at low pole, red at high pole), centered on 0, clamped to ±clamp. */
export function vikForZ(z: number, clamp = 2.5): string {
  const c = Math.max(-clamp, Math.min(clamp, z));
  return interpolateVik((c + clamp) / (2 * clamp));
}

/** Map a 0–100 percentile to a vik color, centered on 50% (distance from the median sets the hue). */
export function vikForPctile(pctile: number): string {
  return interpolateVik(Math.max(0, Math.min(100, pctile)) / 100);
}

import * as d3 from 'd3';

// Diverging magenta (low) → neutral → teal (high). Used for agree/disagree intensity so it
// does NOT read as the political red/blue (left–right) or the party greens (PRG/DSA). Teal
// replaced the former green pole, which collided with the Progressive/DSA party colors.
// 11 symmetric control points; index 5 is the near-white neutral center.
export const BAM_COLORS = [
  '#4d0d33', '#7a1f58', '#a5477f', '#c884ab', '#e7c8db',
  '#f4eef1',
  '#c8e6e0', '#8fccc2', '#4fa89b', '#2b7a70', '#134e4a',
];

// piecewise (not basis-spline) so the interpolator passes through every control point —
// t = 0.5 lands exactly on the neutral center, keeping the diverging scale centered.
export const interpolateBam = d3.piecewise(d3.interpolateRgb, BAM_COLORS);

/** Map a 0–1 fraction to a bam color (magenta at 0, neutral at 0.5, teal at 1). */
export function bamForFrac(t: number): string {
  return interpolateBam(Math.max(0, Math.min(1, t)));
}

/** Map a signed z-score to a bam color (magenta at low pole, teal at high pole), centered on 0, clamped to ±clamp. */
export function bamForZ(z: number, clamp = 2.5): string {
  const c = Math.max(-clamp, Math.min(clamp, z));
  return interpolateBam((c + clamp) / (2 * clamp));
}

/** Map a 0–100 percentile to a bam color, centered on 50% (distance from the median sets the hue). */
export function bamForPctile(pctile: number): string {
  return interpolateBam(Math.max(0, Math.min(100, pctile)) / 100);
}

// Legible dark ends of the bam poles for label text on white (both clear AA at ~7:1+):
// magenta for the low pole, teal for the high pole. These match the scale's hue at each end.
export const BAM_TEXT_LOW = '#7a1f58';  // magenta (low / progressive pole)
export const BAM_TEXT_HIGH = '#134e4a'; // teal (high / conservative pole)

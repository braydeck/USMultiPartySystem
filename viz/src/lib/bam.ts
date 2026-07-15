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

export const interpolateBam = d3.piecewise(d3.interpolateRgb, BAM_COLORS);

/** Map a 0–1 fraction to a bam color (magenta at 0, neutral at 0.5, teal at 1). */
export function bamForFrac(t: number): string {
  return interpolateBam(Math.max(0, Math.min(1, t)));
}

import * as d3 from 'd3';

// bam (Fabio Crameri's Scientific Colour Maps): diverging magenta (low) → neutral →
// green (high). Used for agree/disagree intensity so it does NOT read as the political
// red/blue used for left–right elsewhere (party cards, factor bars).
// 11 symmetric control points; index 5 is the near-white neutral center.
export const BAM_COLORS = [
  '#4d0d33', '#7a1f58', '#a5477f', '#c884ab', '#e7c8db',
  '#f4eef1',
  '#cfe0b1', '#98c06a', '#5f9038', '#356a1d', '#1a3f0d',
];

export const interpolateBam = d3.piecewise(d3.interpolateRgb, BAM_COLORS);

/** Map a 0–1 fraction to a bam color (magenta at 0, neutral at 0.5, green at 1). */
export function bamForFrac(t: number): string {
  return interpolateBam(Math.max(0, Math.min(1, t)));
}

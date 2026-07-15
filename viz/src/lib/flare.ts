import * as d3 from 'd3';

// Seaborn "flare" — a perceptually-uniform sequential ramp running from a light warm salmon
// at 0 to a dark magenta-purple at 1. Replaces flat single-hue ramps (alpha-faded magenta,
// RdPu) whose adjacent steps blurred together; flare rotates hue (salmon → coral → red →
// magenta → purple) as it darkens, so neighbouring buckets stay distinguishable.
// Anchors sampled at 0.0, 0.1, … 1.0 from seaborn's flare cmap.
export const FLARE_COLORS = [
  '#edb081', '#eb9872', '#e77e63', '#e2655c', '#d64f5f',
  '#c14168', '#aa3a6e', '#923371', '#7a2e70', '#62296a', '#4b2362',
];

const interpolateFlare = d3.piecewise(d3.interpolateRgb, FLARE_COLORS);

/** Map a 0–1 fraction to a flare hex color (light at 0, dark at 1). Clamped. */
export function flareForFrac(t: number): string {
  return d3.color(interpolateFlare(Math.max(0, Math.min(1, t))))!.formatHex();
}

/** Readable text color (dark slate or white) over a given flare hex, by WCAG luminance. */
export function flareText(hex: string): string {
  const c = d3.color(hex)!.rgb();
  const lin = (v: number) => { const s = v / 255; return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); };
  const L = 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
  return L > 0.32 ? '#334155' : '#ffffff';
}

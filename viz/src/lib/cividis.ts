import * as d3 from 'd3';

// Cividis — perceptually-uniform, colorblind-safe sequential ramp (dark navy at 0 → gray-tan
// → yellow at 1). Used for the demographic heatmaps, where each cell is read against a shared
// scale (its monotone luminance survives grayscale and colorblindness).
export const CIVIDIS_COLORS = [
  '#00204d', '#00336f', '#39486b', '#575d6d', '#707173',
  '#8a8779', '#a69d75', '#c4b56c', '#e4cf5b', '#ffea46',
];

const interpolateCividis = d3.piecewise(d3.interpolateRgb, CIVIDIS_COLORS);

/** Map a 0–1 fraction to a cividis hex color (dark navy at 0, yellow at 1). Clamped. */
export function cividisForFrac(t: number): string {
  return d3.color(interpolateCividis(Math.max(0, Math.min(1, t))))!.formatHex();
}

/** Readable text color (dark slate or white) over a given cividis hex, by WCAG luminance. */
export function cividisText(hex: string): string {
  const c = d3.color(hex)!.rgb();
  const lin = (v: number) => { const s = v / 255; return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4); };
  const L = 0.2126 * lin(c.r) + 0.7152 * lin(c.g) + 0.0722 * lin(c.b);
  return L > 0.4 ? '#334155' : '#ffffff';
}

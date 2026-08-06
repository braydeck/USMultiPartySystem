// Seat-dot layout for the hemicycle (parliament) chart, kept out of the component so it
// can be tested directly.

export interface ParliamentSegment {
  code: string;
  seats: number;
  fVal: number;
}

export interface SeatDot { cx: number; cy: number }

export const INNER_R = 60;
export const RING_GAP = 15;

/** Split `total` seats across concentric rings in proportion to each ring's arc length. */
export function computeRings(total: number, innerR: number, ringGap: number): number[] {
  const nRings = Math.max(3, Math.ceil(Math.sqrt(total / 5)));
  const perims = Array.from({ length: nRings }, (_, i) => Math.PI * (innerR + ringGap * i));
  const totalPerim = perims.reduce((s, p) => s + p, 0);
  const raw = perims.map(p => (p / totalPerim) * total);
  const floored = raw.map(Math.floor);
  const rem = total - floored.reduce((s, n) => s + n, 0);
  const fracs = raw.map((v, i) => ({ i, f: v - floored[i] })).sort((a, b) => b.f - a.f);
  for (let k = 0; k < rem; k++) floored[fracs[k].i]++;
  return floored;
}

/** Lay every seat out as one dot, grouped by party.
 *
 *  Each party receives exactly `seats` dots. Slots are assigned by cumulative seat
 *  count, not by the angle a dot happens to land at: because every ring places a dot at
 *  frac 0 and at frac 1, an angle-based lookup handed the first and last parties one dot
 *  per ring regardless of their seat counts and left the rest to per-ring rounding — a
 *  102-seat senate drew 11 and 5 dots for parties holding 8 and 2 seats. Wedges stay
 *  contiguous because the slots are walked in angular order.
 *
 *  `segments` must be pre-sorted by `fVal` ascending; that order becomes left-to-right.
 */
export function layoutSeatDots(segments: ParliamentSegment[]): {
  groupedDots: Record<string, SeatDot[]>;
  nRings: number;
  dotSize: number;
  slotFracs: number[];
} {
  const totalSeats = segments.reduce((s, seg) => s + seg.seats, 0);
  if (totalSeats === 0) return { groupedDots: {}, nRings: 3, dotSize: 4, slotFracs: [] };

  const rings = computeRings(totalSeats, INNER_R, RING_GAP);
  const nRings = rings.length;

  const sumR = rings.reduce((s, _, i) => s + INNER_R + RING_GAP * i, 0);
  const spacing = Math.PI * sumR / totalSeats;
  const dotSize = Math.max(2.5, Math.min(10, spacing * 0.68));

  // Every seat position across every ring, ordered left→right by angle. Ties at the arc
  // ends break inner ring first.
  const slots: { frac: number; r: number }[] = [];
  for (let ring = 0; ring < nRings; ring++) {
    const n = rings[ring];
    const r = INNER_R + RING_GAP * ring;
    for (let i = 0; i < n; i++) {
      slots.push({ frac: n === 1 ? 0.5 : i / (n - 1), r });
    }
  }
  slots.sort((a, b) => a.frac - b.frac || a.r - b.r);

  const groupedDots: Record<string, SeatDot[]> = {};
  let si = 0;
  for (const seg of segments) {
    const positions: SeatDot[] = groupedDots[seg.code] ?? [];
    groupedDots[seg.code] = positions;
    for (let k = 0; k < seg.seats && si < slots.length; k++, si++) {
      const { frac, r } = slots[si];
      const angle = Math.PI - frac * Math.PI;
      positions.push({ cx: r * Math.cos(angle), cy: -r * Math.sin(angle) });
    }
  }

  return { groupedDots, nRings, dotSize, slotFracs: slots.map(s => s.frac) };
}

import affinity from '../data/crossPartyAffinity.json';
import ellipses from '../data/partyFactorEllipses.json';
import { F5_ORDER } from '../constants/parties';
import type { FlowRow } from './partyFlow';

/** matrix[j][k]: share of the electorate's posterior mass on party k held by voters whose first
 *  choice is party j, in points. Written by pipeline/build_cross_party_affinity.py. */
const MATRIX = (affinity as { matrix: Record<string, Record<string, number>> }).matrix;

/** One row per party: the average membership a party's own first-choice voters give each party.
 *  Dividing a row by its sum turns electorate points into that party's voters' average posterior,
 *  so the row reads "a typical Progressive voter is 76% Progressive, 13% Liberal, 8% DSA". */
export function overlapRows(): FlowRow[] {
  return F5_ORDER.filter(p => MATRIX[p]).map(p => {
    const row = MATRIX[p];
    const total = Object.values(row).reduce((a, b) => a + b, 0) || 1;
    return {
      party: p,
      selfShare: (row[p] ?? 0) / total,
      segments: Object.entries(row).filter(([k]) => k !== p).map(([k, v]) => ({ party: k, share: v / total })),
    };
  });
}

/** Leaf order of an average-linkage tree on the symmetrised overlap, so parties that share
 *  voters sit next to each other and the strong cells fall in blocks along the diagonal. When
 *  two clusters merge, the pair of ends that overlap most is joined. */
export function similarityOrder(rows: FlowRow[]): string[] {
  const share = (a: string, b: string) => {
    const ra = rows.find(r => r.party === a), rb = rows.find(r => r.party === b);
    const ab = ra?.segments.find(s => s.party === b)?.share ?? 0;
    const ba = rb?.segments.find(s => s.party === a)?.share ?? 0;
    return (ab + ba) / 2;
  };
  let clusters: string[][] = rows.map(r => [r.party]);
  const link = (x: string[], y: string[]) =>
    x.reduce((acc, a) => acc + y.reduce((s, b) => s + share(a, b), 0), 0) / (x.length * y.length);
  while (clusters.length > 1) {
    let best = { i: 0, j: 1, v: -1 };
    for (let i = 0; i < clusters.length; i++) {
      for (let j = i + 1; j < clusters.length; j++) {
        const v = link(clusters[i], clusters[j]);
        if (v > best.v) best = { i, j, v };
      }
    }
    const a = clusters[best.i], b = clusters[best.j];
    const joins: [string[], string[]][] = [
      [a, b], [a, [...b].reverse()], [[...a].reverse(), b], [[...a].reverse(), [...b].reverse()],
    ];
    const [l, r] = joins.reduce((m, j) =>
      share(j[0][j[0].length - 1], j[1][0]) > share(m[0][m[0].length - 1], m[1][0]) ? j : m);
    clusters = clusters.filter((_, k) => k !== best.i && k !== best.j).concat([[...l, ...r]]);
  }
  return clusters[0];
}

export interface PartyEllipse {
  n: number;
  weightShare: number;
  /** Centroid in electorate SDs, in `ELLIPSE_FACTORS` order. */
  mean: number[];
  cov: number[][];
  /** Weighted share of members inside each pair's nominal 50% ellipse, keyed "F1-F2". */
  coverage50: Record<string, number>;
}

const ELLIPSE_DATA = ellipses as unknown as { factors: string[]; parties: Record<string, PartyEllipse> };
export const ELLIPSE_FACTORS = ELLIPSE_DATA.factors;
export const PARTY_ELLIPSES = ELLIPSE_DATA.parties;

/** Squared Mahalanobis radius that holds half of a 2-D Gaussian: −2 ln(0.5). */
const R2_HALF = 2 * Math.LN2;

/** The 50% ellipse of one party on two factors, from the 2×2 block of its covariance (the exact
 *  marginal of a Gaussian). Returns centre, semi-axes and rotation in degrees. */
export function pairEllipse(p: PartyEllipse, fx: string, fy: string) {
  const i = ELLIPSE_FACTORS.indexOf(fx), j = ELLIPSE_FACTORS.indexOf(fy);
  return { cx: p.mean[i], cy: p.mean[j], ...ellipseFromCov2(p.cov[i][i], p.cov[i][j], p.cov[j][j]) };
}

/** Semi-axes and rotation (degrees, counter-clockwise in data space) of the 50% ellipse of a
 *  2-D Gaussian with covariance [[a, b], [b, d]]. Also the exact outline of a 3-D ellipsoid seen
 *  under orthographic projection, given the projected covariance. */
export function ellipseFromCov2(a: number, b: number, d: number) {
  const mid = (a + d) / 2, half = Math.sqrt(((a - d) / 2) ** 2 + b * b);
  const l1 = mid + half, l2 = Math.max(mid - half, 0);
  const angle = Math.atan2(l1 - a, b || 1e-12) * 180 / Math.PI;
  return {
    rx: Math.sqrt(R2_HALF * l1), ry: Math.sqrt(R2_HALF * l2),
    angle: b === 0 ? (a >= d ? 0 : 90) : angle,
  };
}

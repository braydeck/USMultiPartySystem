import type { CandidateVoteRow } from '../types';
import { F5_ORDER } from '../constants/parties';

// Where each party stands within one policy domain, on a 0-100 scale between the domain's two end
// labels (constants/domains.ts). Each item's direction comes from the data: the sign of its
// loading on the first principal axis of the parties' support across the domain's items, signed
// so the axis rises with the site's left-right order. A party's position is the mean, over the
// items, of the share of its members taking the side at the 100 end (support, or 100 - support
// for an item pointing the other way). Parties count equally, whatever their size.

/** Eigenvalues and eigenvectors (columns of V) of a symmetric matrix, by cyclic Jacobi rotation. */
function jacobiEigen(M: number[][]): { values: number[]; V: number[][] } {
  const n = M.length;
  const A = M.map((r) => [...r]);
  const V: number[][] = Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => (i === j ? 1 : 0)));
  for (let sweep = 0; sweep < 100; sweep++) {
    let off = 0;
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) off += A[i][j] * A[i][j];
    if (off < 1e-20) break;
    for (let p = 0; p < n; p++) for (let q = p + 1; q < n; q++) {
      if (Math.abs(A[p][q]) < 1e-15) continue;
      const theta = (A[q][q] - A[p][p]) / (2 * A[p][q]);
      const t = Math.sign(theta || 1) / (Math.abs(theta) + Math.sqrt(theta * theta + 1));
      const c = 1 / Math.sqrt(t * t + 1), s = t * c;
      for (let k = 0; k < n; k++) {
        const akp = A[k][p], akq = A[k][q];
        A[k][p] = c * akp - s * akq; A[k][q] = s * akp + c * akq;
      }
      for (let k = 0; k < n; k++) {
        const apk = A[p][k], aqk = A[q][k];
        A[p][k] = c * apk - s * aqk; A[q][k] = s * apk + c * aqk;
      }
      for (let k = 0; k < n; k++) {
        const vkp = V[k][p], vkq = V[k][q];
        V[k][p] = c * vkp - s * vkq; V[k][q] = s * vkp + c * vkq;
      }
    }
  }
  return { values: A.map((r, i) => r[i]), V };
}

export function domainPositions(rows: CandidateVoteRow[], parties: readonly string[] = F5_ORDER) {
  const k = rows.length, n = parties.length;
  const X = parties.map((p) => rows.map((r) => r.parties[p]?.observedPct ?? 0));
  const mean = rows.map((_, j) => X.reduce((s, row) => s + row[j], 0) / n);
  const Xc = X.map((row) => row.map((v, j) => v - mean[j]));
  const cov = rows.map((_, a) => rows.map((_, b) => Xc.reduce((s, row) => s + row[a] * row[b], 0)));
  const { values, V } = jacobiEigen(cov);
  const top = values.indexOf(Math.max(...values));
  let load = rows.map((_, j) => V[j][top]);
  const score = Xc.map((row) => row.reduce((s, v, j) => s + v * load[j], 0));
  const mi = (n - 1) / 2, ms = score.reduce((s, v) => s + v, 0) / n;
  const idx = parties.map((p) => F5_ORDER.indexOf(p as typeof F5_ORDER[number]));
  if (score.reduce((s, v, i) => s + (v - ms) * (idx[i] - mi), 0) < 0) load = load.map((v) => -v);
  const toward100 = load.map((v) => v > 0);
  const pos = Object.fromEntries(parties.map((p, i) => [p,
    X[i].reduce((s, v, j) => s + (toward100[j] ? v : 100 - v), 0) / k])) as Record<string, number>;
  return { pos, toward100 };
}

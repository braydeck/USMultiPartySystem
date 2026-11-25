import type { CandidateVoteRow } from '../types';
import { F5_ORDER } from '../constants/parties';

// How alike each pair of parties votes on a set of items, and those parties laid on one line so
// the distance between two of them is how differently they vote. This is the computation
// analysis/coalitions/vote_agreement.py uses for the site's left-right order (classical MDS on
// 1 − agreement, first dimension), run here on any subset of items, such as one domain.
//   whipped  share of items where both party majorities (support > 50%) land on the same side
//   free     1 − average gap in support, as PartyAgreement shows it

export type AgreementMode = 'whipped' | 'free';

export function agreementMatrix(rows: CandidateVoteRow[], parties: readonly string[], mode: AgreementMode): number[][] {
  return parties.map((a) => parties.map((b) => {
    let s = 0;
    for (const r of rows) {
      const va = r.parties[a]?.observedPct ?? 0, vb = r.parties[b]?.observedPct ?? 0;
      s += mode === 'whipped' ? ((va > 50) === (vb > 50) ? 1 : 0) : 1 - Math.abs(va - vb) / 100;
    }
    return rows.length ? s / rows.length : 1;
  }));
}

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

/** Each party's position on the agreement line for `rows`, and the share of the agreement pattern
 *  the line captures (its eigenvalue over the sum of the positive ones). Signed so positions rise
 *  with the site's left-right order, which keeps rows for different domains comparable. */
export function agreementLine(rows: CandidateVoteRow[], mode: AgreementMode, parties: readonly string[] = F5_ORDER) {
  const n = parties.length;
  const A = agreementMatrix(rows, parties, mode);
  const D2 = A.map((r) => r.map((a) => (1 - a) ** 2));
  const rowMean = D2.map((r) => r.reduce((s, v) => s + v, 0) / n);
  const all = rowMean.reduce((s, v) => s + v, 0) / n;
  const B = D2.map((r, i) => r.map((v, j) => -0.5 * (v - rowMean[i] - rowMean[j] + all)));
  const { values, V } = jacobiEigen(B);
  const top = values.indexOf(Math.max(...values));
  const lam = Math.max(values[top], 0);
  let x = parties.map((_, i) => V[i][top] * Math.sqrt(lam));
  const idx = parties.map((p) => F5_ORDER.indexOf(p as typeof F5_ORDER[number]));
  const mi = idx.reduce((s, v) => s + v, 0) / n, mx = x.reduce((s, v) => s + v, 0) / n;
  if (x.reduce((s, v, i) => s + (v - mx) * (idx[i] - mi), 0) < 0) x = x.map((v) => -v);
  const pos = values.filter((v) => v > 0).reduce((s, v) => s + v, 0);
  return {
    x: Object.fromEntries(parties.map((p, i) => [p, x[i]])) as Record<string, number>,
    fit: pos > 0 ? lam / pos : 1,
    agreement: Object.fromEntries(parties.map((a, i) => [a, Object.fromEntries(parties.map((b, j) => [b, A[i][j]]))])) as Record<string, Record<string, number>>,
  };
}

import type { QuizQuestion } from '../types';
import { CLUSTER_TO_PARTY } from '../constants/parties';

export type SpreadRow = { party: string; n: number; [key: string]: string | number };
interface ScoreResult { clusterId: string; prob: number }

const ACTIVE = ['0', '1', '2', '3', '4', '5', '6', '8', '9'];
// F3 (Government Distrust) is omitted — non-differentiating (every party scores Medium).
const FACTORS = ['F1', 'F2', 'F4', 'F5'];
// Temperature softens the 5-D Gaussian posterior into honest match-strengths rather than
// snapping to ~100% one party (tuned so a clear archetype lands ~55-70%).
const TEMP = 3;

const mean = (a: number[]) => a.reduce((x, y) => x + y, 0) / a.length;

/**
 * Method A — probabilistic classification mirroring the model's soft assignment.
 * 1. Estimate the respondent's factor-space position from their answers, weighting each
 *    item by its EFA loading. Each item is calibrated to the factor by regressing the
 *    9 clusters' factor-means on their support, so item orientation is learned from data.
 * 2. Score each party by a diagonal-Gaussian log-likelihood (mean + sd from clusterSpreads)
 *    plus its population prior, then softmax → P(party | answers).
 */
export function classifyQuiz(
  questions: QuizQuestion[],
  answers: Record<number, number>,
  spreads: SpreadRow[],
): ScoreResult[] {
  const byParty: Record<string, SpreadRow> = {};
  for (const s of spreads) byParty[s.party] = s;
  const spreadFor = (id: string) => byParty[CLUSTER_TO_PARTY[id]];
  const num = (id: string, key: string) => Number(spreadFor(id)[key]);

  // Per-item calibration: support → factor-mean across the 9 clusters (1-D least squares).
  const coef = questions.map(q => {
    const xs = ACTIVE.map(id => q.clusterSupport[id] ?? 0.5);
    const ys = ACTIVE.map(id => num(id, `mean_${q.factor}`));
    const xb = mean(xs), yb = mean(ys);
    let sxx = 0, sxy = 0;
    for (let k = 0; k < xs.length; k++) { sxx += (xs[k] - xb) ** 2; sxy += (xs[k] - xb) * (ys[k] - yb); }
    const b = sxx > 1e-9 ? sxy / sxx : 0;
    return { a: yb - b * xb, b };
  });

  // Respondent's estimated position per factor (loading-weighted mean of calibrated items).
  const userF: Record<string, number> = {};
  for (const f of FACTORS) {
    let n = 0, d = 0;
    questions.forEach((q, i) => {
      if (q.factor !== f) return;
      const a = answers[i] ?? 0.5;
      const w = Math.abs(q.loading ?? 1);
      n += w * (coef[i].a + coef[i].b * a);
      d += w;
    });
    userF[f] = d ? n / d : 0;
  }

  const nTot = spreads.reduce((s, r) => s + r.n, 0);
  const logits = ACTIVE.map(id => {
    let ll = 0;
    for (const f of FACTORS) {
      const sd = num(id, `sd_${f}`);
      ll += -0.5 * ((userF[f] - num(id, `mean_${f}`)) / sd) ** 2 - Math.log(sd);
    }
    return { id, logit: ll / TEMP + Math.log(spreadFor(id).n / nTot) };
  });

  const mx = Math.max(...logits.map(l => l.logit));
  const exps = logits.map(l => ({ id: l.id, e: Math.exp(l.logit - mx) }));
  const z = exps.reduce((a, b) => a + b.e, 0);
  return exps
    .map(x => ({ clusterId: x.id, prob: x.e / z }))
    .sort((a, b) => b.prob - a.prob);
}

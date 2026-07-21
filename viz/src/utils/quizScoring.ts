import type { QuizQuestion, ClusterProfile } from '../types';
import { CLUSTER_TO_PARTY } from '../constants/parties';

export type SpreadRow = { party: string; n: number; [key: string]: string | number };
interface ScoreResult { clusterId: string; prob: number }

const ACTIVE = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'];
// F3 (Government Distrust) is omitted — non-differentiating (every party scores Medium).
const FACTORS = ['F1', 'F2', 'F4', 'F5'];
// Temperature softens the 5-D Gaussian posterior into honest match-strengths rather than
// snapping to ~100% one party (tuned so a clear archetype lands ~55-70%).
const TEMP = 3;

const mean = (a: number[]) => a.reduce((x, y) => x + y, 0) / a.length;

/**
 * Estimate the respondent's factor-space position from their answers. Each item is
 * calibrated to its factor by regressing the 9-10 clusters' target value on their
 * support (1-D least squares), so item orientation is learned from data; the
 * respondent's position is the loading-weighted mean of the calibrated items.
 *
 * `target(clusterId, factor)` supplies the per-cluster anchor: the raw factor mean
 * for scoring, or the z-scored factor value for display (so a UI marker lands on the
 * same axis the party bars use).
 */
function estimateFactors(
  questions: QuizQuestion[],
  answers: Record<number, number>,
  target: (clusterId: string, factor: string) => number,
): Record<string, number> {
  const coef = questions.map(q => {
    const xs = ACTIVE.map(id => q.clusterSupport[id] ?? 0.5);
    const ys = ACTIVE.map(id => target(id, q.factor));
    const xb = mean(xs), yb = mean(ys);
    let sxx = 0, sxy = 0;
    for (let k = 0; k < xs.length; k++) { sxx += (xs[k] - xb) ** 2; sxy += (xs[k] - xb) * (ys[k] - yb); }
    const b = sxx > 1e-9 ? sxy / sxx : 0;
    return { a: yb - b * xb, b };
  });

  const out: Record<string, number> = {};
  for (const f of FACTORS) {
    let n = 0, d = 0;
    questions.forEach((q, i) => {
      if (q.factor !== f) return;
      const a = answers[i] ?? 0.5;
      const w = Math.abs(q.loading ?? 1);
      n += w * (coef[i].a + coef[i].b * a);
      d += w;
    });
    out[f] = d ? n / d : 0;
  }
  return out;
}

/**
 * Method A — probabilistic classification mirroring the model's soft assignment.
 * 1. Estimate the respondent's factor-space position (calibrated against cluster means).
 * 2. Score each party by a diagonal-Gaussian log-likelihood (mean + sd from clusterSpreads),
 *    then softmax → P(party | answers).
 *
 * Flat prior: no population base-rate term. This is a self-placement tool ("which party
 * are you"), so ranking is by ideological proximity — otherwise large clusters (CON, LBR)
 * absorb every close call between neighbours.
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

  const userF = estimateFactors(questions, answers, (id, f) => num(id, `mean_${f}`));

  const logits = ACTIVE.map(id => {
    let ll = 0;
    for (const f of FACTORS) {
      const sd = num(id, `sd_${f}`);
      ll += -0.5 * ((userF[f] - num(id, `mean_${f}`)) / sd) ** 2 - Math.log(sd);
    }
    return { id, logit: ll / TEMP };
  });

  const mx = Math.max(...logits.map(l => l.logit));
  const exps = logits.map(l => ({ id: l.id, e: Math.exp(l.logit - mx) }));
  const z = exps.reduce((a, b) => a + b.e, 0);
  return exps
    .map(x => ({ clusterId: x.id, prob: x.e / z }))
    .sort((a, b) => b.prob - a.prob);
}

/**
 * The respondent's factor position expressed in the z-score units the FactorBar renders,
 * so a marker dot lands on the same axis as each party's bar. Calibrated against the
 * clusters' z_F exactly as classifyQuiz calibrates against mean_F.
 */
export function estimateFactorZScores(
  questions: QuizQuestion[],
  answers: Record<number, number>,
  clusters: ClusterProfile[],
): Record<string, number> {
  const byId: Record<string, Record<string, number>> = {};
  for (const c of clusters) byId[c.id] = c as unknown as Record<string, number>;
  return estimateFactors(questions, answers, (id, f) => byId[id]?.[`z_${f}`] ?? 0);
}

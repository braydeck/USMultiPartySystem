import type { QuizQuestion } from '../types';
import shortform from '../data/quizShortform.json';

interface ScoreResult { clusterId: string; prob: number }

interface Shortform {
  variables: string[];
  weights: Record<string, Record<string, number>>;      // factor -> {intercept, <var>: coef}
  popSd: Record<string, number>;                          // displayed factor -> population sd
  classify: {
    factors: string[];
    temp: number;
    clusters: Record<string, { party: string; mean: number[]; invCov: number[][]; logDet: number }>;
  };
}

const SF = shortform as unknown as Shortform;
const DISPLAY_FACTORS = Object.keys(SF.popSd);            // ['F1','F2','F4','F5']

/**
 * Estimate the respondent's position on each requested factor (raw EFA score units)
 * from their 21 answers, via the validated short-form scoring key: a linear predictor
 * (intercept + per-item weight) fit to the full-model factor scores. Bounded and
 * calibrated to the electorate — no per-item extrapolation.
 */
function userFactors(
  questions: QuizQuestion[],
  answers: Record<number, number>,
  factors: string[],
): Record<string, number> {
  const out: Record<string, number> = {};
  for (const f of factors) {
    const wf = SF.weights[f];
    let v = wf.intercept;
    questions.forEach((q, i) => { v += (wf[q.variable] ?? 0) * (answers[i] ?? 0.5); });
    out[f] = v;
  }
  return out;
}

/**
 * Classify the respondent against each party cluster with a full-covariance Gaussian
 * (Mahalanobis) in the model's 5-factor space {F1,F2,F3,F4,F5} — the same space the
 * DPGMM defined the parties in (F3 is a hidden classification dimension; full covariance
 * makes this equivalent to the residualized F4/F5 space). Flat prior: ranking is by
 * ideological proximity, so large clusters don't absorb close calls.
 */
export function classifyQuiz(
  questions: QuizQuestion[],
  answers: Record<number, number>,
): ScoreResult[] {
  const uf = userFactors(questions, answers, SF.classify.factors);
  const x = SF.classify.factors.map(f => uf[f]);
  const logits = Object.entries(SF.classify.clusters).map(([id, c]) => {
    const d = x.map((xi, i) => xi - c.mean[i]);
    let maha = 0;
    for (let i = 0; i < d.length; i++) {
      let row = 0;
      for (let j = 0; j < d.length; j++) row += c.invCov[i][j] * d[j];
      maha += d[i] * row;
    }
    return { id, logit: (-0.5 * maha - 0.5 * c.logDet) / SF.classify.temp };
  });
  const mx = Math.max(...logits.map(l => l.logit));
  const exps = logits.map(l => ({ id: l.id, e: Math.exp(l.logit - mx) }));
  const z = exps.reduce((a, b) => a + b.e, 0);
  return exps
    .map(e => ({ clusterId: e.id, prob: e.e / z }))
    .sort((a, b) => b.prob - a.prob);
}

/**
 * The respondent's displayed factors in z-score units (raw score / population sd), so a
 * marker dot lands on the same axis as each party's FactorBar.
 */
export function estimateFactorZScores(
  questions: QuizQuestion[],
  answers: Record<number, number>,
): Record<string, number> {
  const uf = userFactors(questions, answers, DISPLAY_FACTORS);
  const out: Record<string, number> = {};
  for (const f of DISPLAY_FACTORS) out[f] = uf[f] / SF.popSd[f];
  return out;
}

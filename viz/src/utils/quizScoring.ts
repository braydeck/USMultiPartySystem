import type { QuizQuestion } from '../types';
import keys from '../data/quizShortform.json';

interface ScoreResult { clusterId: string; prob: number }

export type QuizVersion = 'short' | 'long';

interface VersionKey {
  variables: string[];
  itemMean: Record<string, number>;                       // weighted mean answer, used for a skipped item
  weights: Record<string, Record<string, number>>;      // factor -> {intercept, <var>: coef}
  classify: {
    factors: string[];
    clusters: Record<string, { party: string; mean: number[]; invCov: number[][]; logDet: number; logWeight: number }>;
  };
  placement: number;
}

interface QuizKeys {
  popSd: Record<string, number>;                          // displayed factor -> population sd
  versions: Record<QuizVersion, VersionKey>;
}

const K = keys as unknown as QuizKeys;
const DISPLAY_FACTORS = Object.keys(K.popSd);             // ['F1','F2','F4','F5']

/** Item count of each quiz version, for the arrival chooser. */
export const QUIZ_VERSION_SIZE: Record<QuizVersion, number> = {
  short: K.versions.short.variables.length,
  long: K.versions.long.variables.length,
};

/** Share of survey respondents each version places in their own party (in-sample, weighted). */
export const QUIZ_PLACEMENT: Record<QuizVersion, number> = {
  short: K.versions.short.placement,
  long: K.versions.long.placement,
};

/** The questions of one version, in the order they are asked. */
export function questionsFor(questions: QuizQuestion[], version: QuizVersion): QuizQuestion[] {
  const keep = new Set(K.versions[version].variables);
  return questions.filter(q => keep.has(q.variable));
}

/**
 * The respondent's position on each app factor (raw score units) from their answers, via the
 * version's scoring key: intercept + per-item weight, fit by weighted least squares to the
 * full-model factor scores. A skipped item counts at its electorate mean.
 */
function userFactors(
  questions: QuizQuestion[],
  answers: Record<number, number>,
  version: QuizVersion,
): Record<string, number> {
  const key = K.versions[version];
  const out: Record<string, number> = {};
  for (const f of key.classify.factors) {
    const wf = key.weights[f];
    let v = wf.intercept;
    questions.forEach((q, i) => { v += (wf[q.variable] ?? 0) * (answers[i] ?? key.itemMean[q.variable] ?? 0.5); });
    out[f] = v;
  }
  return out;
}

/**
 * Party probabilities from the clustering model itself: each party is one DPGMM component (its
 * mean, covariance and mixing weight), with the covariance widened by the scoring key's own error
 * so a shorter quiz is matched less confidently. The probabilities are the component posteriors.
 */
export function classifyQuiz(
  questions: QuizQuestion[],
  answers: Record<number, number>,
  version: QuizVersion = 'short',
): ScoreResult[] {
  const key = K.versions[version];
  const uf = userFactors(questions, answers, version);
  const x = key.classify.factors.map(f => uf[f]);
  const logits = Object.entries(key.classify.clusters).map(([id, c]) => {
    const d = x.map((xi, i) => xi - c.mean[i]);
    let maha = 0;
    for (let i = 0; i < d.length; i++) {
      let row = 0;
      for (let j = 0; j < d.length; j++) row += c.invCov[i][j] * d[j];
      maha += d[i] * row;
    }
    return { id, logit: c.logWeight - 0.5 * maha - 0.5 * c.logDet };
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
  version: QuizVersion = 'short',
): Record<string, number> {
  const uf = userFactors(questions, answers, version);
  const out: Record<string, number> = {};
  for (const f of DISPLAY_FACTORS) out[f] = uf[f] / K.popSd[f];
  return out;
}

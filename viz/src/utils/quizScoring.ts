import type { QuizQuestion } from '../types';

const ACTIVE_CLUSTERS = ['0','1','2','3','4','5','6','8','9'];

// Weight each factor by its discriminating power (EFA η²). F3 (Government
// Distrust) is omitted — it is non-differentiating (every party scores Medium),
// so it would only add noise. F2 (Electoral Skepticism) is cross-cutting and
// down-weighted accordingly; F1 and F5 are the strong partisan sorters.
const FACTOR_WEIGHTS: Record<string, number> = { F1: 0.701, F2: 0.375, F4: 0.305, F5: 0.736 };

interface ScoreResult {
  clusterId: string;
  score: number;
}

export function scoreQuiz(
  questions: QuizQuestion[],
  answers: Record<number, number>
): ScoreResult[] {
  // Group questions by factor (ignoring factors without a weight, e.g. F3)
  const byFactor: Record<string, QuizQuestion[]> = {};
  for (const q of questions) {
    if (!(q.factor in FACTOR_WEIGHTS)) continue;
    (byFactor[q.factor] ??= []).push(q);
  }

  const results = ACTIVE_CLUSTERS.map(cid => {
    let weighted = 0;
    let weightSum = 0;
    for (const [factor, qs] of Object.entries(byFactor)) {
      if (qs.length === 0) continue;
      let factorAlignment = 0;
      for (const q of qs) {
        const qIdx = questions.indexOf(q);
        const userScore = answers[qIdx] ?? 0.5;
        const clusterMean = q.clusterSupport[cid] ?? 0.5;
        factorAlignment += 1 - Math.abs(userScore - clusterMean);
      }
      const w = FACTOR_WEIGHTS[factor];
      weighted += w * (factorAlignment / qs.length);
      weightSum += w;
    }
    return { clusterId: cid, score: weightSum > 0 ? weighted / weightSum : 0 };
  });

  return results.sort((a, b) => b.score - a.score);
}

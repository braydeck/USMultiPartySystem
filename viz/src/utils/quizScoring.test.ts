import { describe, it, expect } from 'vitest'
import { classifyQuiz, estimateFactorZScores } from './quizScoring'
import questions from '../data/quizQuestions.json'

// A strongly-conservative, institution-distrusting respondent (the "dad" case):
// law-and-order, opposes taxing high earners + infrastructure, election-skeptic.
const dadByVar: Record<string, number> = {
  CC24_321d: 1, CC24_321e: 0, CC24_321b: 0.75, CC24_323b: 1, CC24_340f: 1,
  CC24_323a: 0.25, CC24_323d: 0.75, CC24_340e: 0, CC24_341a: 0.75, CC24_341c: 0,
  CC24_341d: 0.25, CC24_340c: 1, CC24_340b: 0.25, CC24_421_1_agree: 0.25,
  CC24_421_2_agree: 0.25, CC24_440b_agree: 0.75, CC24_440c_agree: 0.75,
  CC24_423: 0.67, CC24_424: 0.67, pew_churatd: 0.5, CC24_325_median: 0.15,
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const qs = questions as any[]
const answers: Record<number, number> = Object.fromEntries(
  qs.map((q, i) => [i, dadByVar[q.variable]]),
)

describe('classifyQuiz (short-form, full-covariance, flat prior)', () => {
  it('places a distrustful, strongly-conservative respondent as Populist', () => {
    const scores = classifyQuiz(qs, answers)
    // '5' = POP (see quizShortform.json cluster ids)
    expect(scores[0].clusterId).toBe('5')
    expect(scores[0].prob).toBeGreaterThan(0.6) // a confident match, not a 3-way tie
    // CON no longer wins on a size prior
    expect(scores.find(s => s.clusterId === '0')!.prob).toBeLessThan(0.2)
    // probabilities are a normalized distribution
    expect(scores.reduce((a, s) => a + s.prob, 0)).toBeCloseTo(1, 5)
  })
})

describe('estimateFactorZScores', () => {
  it('returns the respondent position in z-units for the displayed factors', () => {
    const z = estimateFactorZScores(qs, answers)
    expect(Object.keys(z).sort()).toEqual(['F1', 'F2', 'F4', 'F5'])
    expect(z.F5).toBeGreaterThan(1) // strongly conservative
    expect(z.F2).toBeGreaterThan(0.5) // distrusts institutions
  })
})

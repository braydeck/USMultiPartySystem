import { describe, it, expect } from 'vitest'
import { classifyQuiz, estimateFactorZScores } from './quizScoring'
import questions from '../data/quizQuestions.json'
import spreads from '../data/clusterSpreads.json'
import clusters from '../data/clusterProfiles.json'

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

describe('classifyQuiz (flat prior)', () => {
  it('ranks by ideological proximity, not party base rate', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const scores = classifyQuiz(qs, answers, spreads as any)
    // '5' = POP, '3' = NAT, '0' = CON (see CLUSTER_TO_PARTY)
    expect(scores[0].clusterId).toBe('5') // Populist wins under a flat prior
    expect(scores[0].prob).toBeGreaterThan(0.4)
    const prob = (id: string) => scores.find(s => s.clusterId === id)!.prob
    // CON no longer floats up on its large population prior
    expect(prob('3')).toBeGreaterThan(prob('0')) // NAT > CON
  })
})

describe('estimateFactorZScores', () => {
  it('returns the respondent position in z-units for the displayed factors', () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const z = estimateFactorZScores(qs, answers, clusters as any)
    expect(z.F5).toBeGreaterThan(1) // strongly conservative
    expect(z.F2).toBeGreaterThan(0.5) // distrusts institutions
    expect(Object.keys(z).sort()).toEqual(['F1', 'F2', 'F4', 'F5'])
  })
})

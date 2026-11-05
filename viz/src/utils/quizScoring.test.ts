import { describe, it, expect } from 'vitest'
import { classifyQuiz, estimateFactorZScores, questionsFor, QUIZ_VERSION_SIZE, type QuizVersion } from './quizScoring'
import questions from '../data/quizQuestions.json'
import type { QuizQuestion } from '../types'

const all = questions as unknown as QuizQuestion[]
const VERSIONS: QuizVersion[] = ['short', 'long']
const PARTY_IDS = Object.keys(all[0].clusterSupport)

/** A respondent who gives a party's own weighted-mean answer to every item. */
function answersOf(qs: QuizQuestion[], clusterId: string): Record<number, number> {
  return Object.fromEntries(qs.map((q, i) => [i, q.clusterSupport[clusterId]]))
}

describe('quiz versions', () => {
  it('asks 25 items short and all 41 long', () => {
    expect(QUIZ_VERSION_SIZE).toEqual({ short: 25, long: 41 })
    expect(questionsFor(all, 'short')).toHaveLength(25)
    expect(questionsFor(all, 'long')).toHaveLength(41)
  })
})

describe('classifyQuiz (DPGMM components + key error)', () => {
  for (const version of VERSIONS) {
    it(`places each party's mean answers in that party (${version})`, () => {
      const qs = questionsFor(all, version)
      for (const id of PARTY_IDS) {
        const scores = classifyQuiz(qs, answersOf(qs, id), version)
        expect(scores[0].clusterId).toBe(id)
        expect(scores[0].prob).toBeGreaterThan(0.6)
        expect(scores.reduce((a, s) => a + s.prob, 0)).toBeCloseTo(1, 5)
      }
    })
  }
})

describe('estimateFactorZScores', () => {
  it('puts the Nationalist mean answers high on cultural and economic conservatism', () => {
    const qs = questionsFor(all, 'long')
    const z = estimateFactorZScores(qs, answersOf(qs, '3'), 'long') // '3' = NAT
    expect(Object.keys(z).sort()).toEqual(['F1', 'F2', 'F4', 'F5'])
    expect(z.F4).toBeGreaterThan(0.8)
    expect(z.F5).toBeGreaterThan(0.8)
  })
})

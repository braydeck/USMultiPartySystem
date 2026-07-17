import { describe, it, expect, vi } from 'vitest'
import { answersToVariableMap, debounce } from './analytics'
import type { QuizQuestion } from '../types'

const questions = [
  { variable: 'CC24_321d', factor: 'F1', loading: 0.7, question: 'q0', domain: 'd', clusterSupport: {} },
  { variable: 'CC24_999z', factor: 'F2', loading: 0.5, question: 'q1', domain: 'd', clusterSupport: {} },
] as unknown as QuizQuestion[]

describe('answersToVariableMap', () => {
  it('keys answers by the question CES variable', () => {
    expect(answersToVariableMap(questions, { 0: 1, 1: 0.5 })).toEqual({ CC24_321d: 1, CC24_999z: 0.5 })
  })
  it('ignores answer indices with no matching question', () => {
    expect(answersToVariableMap(questions, { 5: 1 })).toEqual({})
  })
})

describe('debounce', () => {
  it('calls once after the delay with the latest args', () => {
    vi.useFakeTimers()
    const fn = vi.fn()
    const d = debounce(fn, 500)
    d('a')
    d('b')
    expect(fn).not.toHaveBeenCalled()
    vi.advanceTimersByTime(500)
    expect(fn).toHaveBeenCalledTimes(1)
    expect(fn).toHaveBeenCalledWith('b')
    vi.useRealTimers()
  })
})

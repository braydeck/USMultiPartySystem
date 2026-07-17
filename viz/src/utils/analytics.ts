import type { QuizQuestion } from '../types'

export const QUIZ_VERSION = 'v1-2026-07'

export function debounce<A extends unknown[]>(fn: (...a: A) => void, ms: number): (...a: A) => void {
  let t: ReturnType<typeof setTimeout> | undefined
  return (...a: A) => {
    if (t) clearTimeout(t)
    t = setTimeout(() => fn(...a), ms)
  }
}

export function answersToVariableMap(
  questions: QuizQuestion[],
  answers: Record<number, number>,
): Record<string, number> {
  const out: Record<string, number> = {}
  for (const [idx, val] of Object.entries(answers)) {
    const q = questions[Number(idx)]
    if (q?.variable) out[q.variable] = val
  }
  return out
}

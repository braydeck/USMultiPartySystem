import posthog from 'posthog-js'
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

const KEY = import.meta.env.VITE_POSTHOG_KEY
const HOST = import.meta.env.VITE_POSTHOG_HOST ?? 'https://us.i.posthog.com'
const OPTOUT_KEY = 'stv_analytics_optout'

let ready = false
let disabled = false

/** Whether this browser has opted out (persists across sessions, unlike PostHog's memory mode). */
function isOptedOut(): boolean {
  // ?analytics=off sets a persistent opt-out on this browser; ?analytics=on clears it.
  try {
    const flag = new URLSearchParams(window.location.search).get('analytics')
    if (flag === 'off') localStorage.setItem(OPTOUT_KEY, '1')
    else if (flag === 'on') localStorage.removeItem(OPTOUT_KEY)
    return localStorage.getItem(OPTOUT_KEY) === '1'
  } catch {
    return false // localStorage blocked — behave normally
  }
}

export function initAnalytics(): void {
  disabled = isOptedOut()
  if (disabled) {
    console.info('[analytics] disabled on this browser (opted out)')
    return
  }
  if (ready || !KEY) return
  posthog.init(KEY, {
    api_host: HOST,
    person_profiles: 'identified_only',
    persistence: 'memory',
    autocapture: false,
    capture_pageview: 'history_change',
  })
  ready = true
}

export function track(event: string, props?: Record<string, unknown>): void {
  if (disabled || !ready) return
  try {
    posthog.capture(event, props)
  } catch {
    // analytics must never throw into the UI
  }
}

function currentParams(): Record<string, string> {
  return Object.fromEntries(new URLSearchParams(window.location.search))
}

export function mountViewStateTracking(): () => void {
  track('view_state', currentParams())
  const emit = debounce(() => track('view_state', currentParams()), 500)
  window.addEventListener('urlstatechange', emit)
  window.addEventListener('popstate', emit)
  return () => {
    window.removeEventListener('urlstatechange', emit)
    window.removeEventListener('popstate', emit)
  }
}

/**
 * Fire once at load if the visitor arrived via a shared party-result link — the /r/<party>
 * redirect tags those with utm_source=result_share, so this counts organic share-sourced
 * visits (copied links, DMs) that carry no referrer, not just clicks from known domains.
 */
export function trackShareLanding(): void {
  const p = Object.fromEntries(new URLSearchParams(window.location.search))
  if (p.utm_source === 'result_share') {
    track('shared_result_opened', { party: p.utm_content ?? p.result ?? null })
  }
}

export function submitQuizResult(input: {
  id: string
  result_party: string
  answers: Record<string, number>
  scores: { party: string; prob: number }[]
}): void {
  if (disabled) return
  try {
    fetch('/api/quiz', {
      method: 'POST',
      keepalive: true,
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        ...input,
        referrer: document.referrer || null,
        quiz_version: QUIZ_VERSION,
      }),
    }).catch(() => {
      /* fire-and-forget */
    })
  } catch {
    /* never throw into the UI */
  }
  track('quiz_completed', { party: input.result_party })
}

export function submitVibe(id: string, vibe: 'fit' | 'miss', party: string): void {
  if (disabled) return
  try {
    fetch('/api/quiz', {
      method: 'PATCH',
      keepalive: true,
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ id, vibe }),
    }).catch(() => {
      /* fire-and-forget */
    })
  } catch {
    /* never throw into the UI */
  }
  track('quiz_vibe', { party, vibe })
}

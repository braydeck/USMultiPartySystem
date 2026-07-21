/**
 * The tab a visitor lands on when the URL has no `?tab=` param: Quiz on mobile (the shareable
 * hook), Overview on desktop. Shared by App (its landing default) and analytics (so `view_state`
 * always emits an explicit tab instead of a blank bucket for default landings).
 */
export function resolveDefaultTab(): 'quiz' | 'overview' {
  return typeof window !== 'undefined' && window.matchMedia('(max-width: 639px)').matches
    ? 'quiz'
    : 'overview'
}

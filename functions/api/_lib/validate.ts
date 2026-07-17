export const PARTY_CODES = ['PRG', 'DSA', 'LIB', 'LBR', 'OAO', 'STY', 'CUP', 'CON', 'POP', 'NAT'] as const
export const VIBE_VALUES = ['fit', 'miss'] as const
export const MAX_ANSWERS = 50
export const MAX_BODY_BYTES = 8192

export interface CreatePayload {
  id: string
  result_party: string
  answers: Record<string, number>
  scores: { party: string; prob: number }[]
  referrer: string | null
  quiz_version: string
}
export interface VibePayload {
  id: string
  vibe: string
}

type Result<T> = { ok: true; value: T } | { ok: false; error: string }

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

export function validateCreate(body: unknown): Result<CreatePayload> {
  if (!isRecord(body)) return { ok: false, error: 'body must be an object' }
  if (typeof body.id !== 'string' || !UUID_RE.test(body.id)) return { ok: false, error: 'invalid id' }
  if (typeof body.result_party !== 'string' || !(PARTY_CODES as readonly string[]).includes(body.result_party))
    return { ok: false, error: 'invalid result_party' }
  if (!isRecord(body.answers)) return { ok: false, error: 'invalid answers' }
  const keys = Object.keys(body.answers)
  if (keys.length === 0 || keys.length > MAX_ANSWERS) return { ok: false, error: 'invalid answers size' }
  for (const k of keys) {
    const val = (body.answers as Record<string, unknown>)[k]
    if (typeof val !== 'number' || !Number.isFinite(val)) return { ok: false, error: 'invalid answer value' }
  }
  if (!Array.isArray(body.scores)) return { ok: false, error: 'invalid scores' }
  for (const s of body.scores) {
    if (!isRecord(s) || typeof s.party !== 'string' || typeof s.prob !== 'number')
      return { ok: false, error: 'invalid score entry' }
  }
  if (typeof body.quiz_version !== 'string' || body.quiz_version.length === 0 || body.quiz_version.length > 32)
    return { ok: false, error: 'invalid quiz_version' }
  const referrer = typeof body.referrer === 'string' ? body.referrer.slice(0, 512) : null
  return {
    ok: true,
    value: {
      id: body.id,
      result_party: body.result_party,
      answers: body.answers as Record<string, number>,
      scores: body.scores as { party: string; prob: number }[],
      referrer,
      quiz_version: body.quiz_version,
    },
  }
}

export function validateVibe(body: unknown): Result<VibePayload> {
  if (!isRecord(body)) return { ok: false, error: 'body must be an object' }
  if (typeof body.id !== 'string' || !UUID_RE.test(body.id)) return { ok: false, error: 'invalid id' }
  if (typeof body.vibe !== 'string' || !(VIBE_VALUES as readonly string[]).includes(body.vibe))
    return { ok: false, error: 'invalid vibe' }
  return { ok: true, value: { id: body.id, vibe: body.vibe } }
}

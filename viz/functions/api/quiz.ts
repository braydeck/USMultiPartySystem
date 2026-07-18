/// <reference types="@cloudflare/workers-types" />
import { validateCreate, validateVibe, MAX_BODY_BYTES } from './_lib/validate'

interface Env {
  DB: D1Database
}

async function readJson(request: Request): Promise<unknown | null> {
  const len = Number(request.headers.get('content-length') ?? '0')
  if (len > MAX_BODY_BYTES) return null
  try {
    return await request.json()
  } catch {
    return null
  }
}

export const onRequestPost: PagesFunction<Env> = async ({ request, env }) => {
  const body = await readJson(request)
  if (body === null) return new Response('bad request', { status: 400 })
  const v = validateCreate(body)
  if (!v.ok) return new Response(v.error, { status: 400 })
  const p = v.value
  const created_at = new Date().toISOString()
  const country = (request as Request & { cf?: { country?: string } }).cf?.country ?? null
  try {
    await env.DB.prepare(
      `INSERT INTO quiz_response
         (id, created_at, result_party, answers, scores, vibe, referrer, country, quiz_version)
       VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?)`,
    )
      .bind(
        p.id,
        created_at,
        p.result_party,
        JSON.stringify(p.answers),
        JSON.stringify(p.scores),
        p.referrer,
        country,
        p.quiz_version,
      )
      .run()
  } catch {
    // duplicate id or transient DB error — safe to swallow, capture is best-effort
    return new Response('conflict', { status: 409 })
  }
  return new Response(null, { status: 204 })
}

export const onRequestPatch: PagesFunction<Env> = async ({ request, env }) => {
  const body = await readJson(request)
  if (body === null) return new Response('bad request', { status: 400 })
  const v = validateVibe(body)
  if (!v.ok) return new Response(v.error, { status: 400 })
  await env.DB.prepare(`UPDATE quiz_response SET vibe = ? WHERE id = ?`).bind(v.value.vibe, v.value.id).run()
  return new Response(null, { status: 204 })
}

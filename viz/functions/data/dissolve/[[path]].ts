/// <reference types="@cloudflare/workers-types" />
// Dissolve-a-party scenarios (pipeline/build_dissolve_scenarios.py): ~600 MB of gzip-encoded
// JSON, too big for the repo, held in the R2 bucket bound as DISSOLVE. Objects are stored
// compressed, so the body passes through untouched with its encoding declared.

interface Env {
  DISSOLVE?: R2Bucket
}

const SAFE = /^[A-Z-]+\/[A-Za-z0-9.]+\.json$/

export const onRequestGet: PagesFunction<Env> = async ({ params, env }) => {
  const key = (Array.isArray(params.path) ? params.path : [params.path]).join('/')
  if (!env.DISSOLVE || !SAFE.test(key)) return new Response('not found', { status: 404 })
  const obj = await env.DISSOLVE.get(key)
  if (!obj) return new Response('not found', { status: 404 })
  return new Response(obj.body, {
    headers: {
      'Content-Type': 'application/json',
      'Content-Encoding': 'gzip',
      'Cache-Control': 'public, max-age=86400',
      ETag: obj.httpEtag,
    },
    encodeBody: 'manual',
  })
}

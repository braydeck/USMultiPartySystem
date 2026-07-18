import { describe, it, expect } from 'vitest'
import { onRequestPost, onRequestPatch } from '../api/quiz'

function mockDB() {
  const calls: { sql: string; args: unknown[] }[] = []
  const db = {
    prepare(sql: string) {
      return {
        bind(...args: unknown[]) {
          return {
            run: async () => {
              calls.push({ sql, args })
              return { success: true }
            },
          }
        },
      }
    },
  }
  return { db, calls }
}

function req(body: unknown, cfCountry = 'US') {
  return {
    headers: { get: (_k: string) => null },
    json: async () => body,
    cf: { country: cfCountry },
  } as unknown as Request
}

const goodCreate = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  result_party: 'LBR',
  answers: { CC24_321d: 1 },
  scores: [{ party: 'LBR', prob: 0.6 }],
  referrer: 'https://braydendecker.substack.com/',
  quiz_version: 'v1-2026-07',
}

describe('onRequestPost', () => {
  it('inserts a valid submission and returns 204', async () => {
    const { db, calls } = mockDB()
    const res = await onRequestPost({ request: req(goodCreate), env: { DB: db } } as any)
    expect(res.status).toBe(204)
    expect(calls).toHaveLength(1)
    expect(calls[0].sql).toContain('INSERT INTO quiz_response')
    // 8 bound params (vibe is a literal NULL in the SQL)
    expect(calls[0].args).toHaveLength(8)
    // country comes from request.cf, and no arg is an IP address
    expect(calls[0].args).toContain('US')
    for (const a of calls[0].args) {
      expect(String(a)).not.toMatch(/\b\d{1,3}(\.\d{1,3}){3}\b/)
    }
  })
  it('rejects an invalid payload with 400 and never touches the DB', async () => {
    const { db, calls } = mockDB()
    const res = await onRequestPost({ request: req({ ...goodCreate, result_party: 'ZZZ' }), env: { DB: db } } as any)
    expect(res.status).toBe(400)
    expect(calls).toHaveLength(0)
  })
})

describe('onRequestPatch', () => {
  it('updates vibe and returns 204', async () => {
    const { db, calls } = mockDB()
    const res = await onRequestPatch({ request: req({ id: goodCreate.id, vibe: 'fit' }), env: { DB: db } } as any)
    expect(res.status).toBe(204)
    expect(calls[0].sql).toContain('UPDATE quiz_response SET vibe')
    expect(calls[0].args).toEqual(['fit', goodCreate.id])
  })
  it('rejects a bad vibe with 400', async () => {
    const { db, calls } = mockDB()
    const res = await onRequestPatch({ request: req({ id: goodCreate.id, vibe: 'nope' }), env: { DB: db } } as any)
    expect(res.status).toBe(400)
    expect(calls).toHaveLength(0)
  })
})

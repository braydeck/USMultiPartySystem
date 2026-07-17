# Analytics + Quiz Result Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add PostHog interaction analytics, Cloudflare Web Analytics, and anonymous quiz-result capture to Cloudflare D1, with a result "vibe check", storing zero PII.

**Architecture:** A repo-root Cloudflare Pages Function (`functions/api/quiz.ts`) persists anonymous quiz submissions to D1 (SQLite), with validation extracted to a pure, unit-tested module. Client-side, a single debounced listener on the existing `urlstatechange` event drives PostHog `view_state` events (covering every tab + filter), and explicit events cover the quiz funnel. All capture is fire-and-forget and can never break the UI.

**Tech Stack:** React + TypeScript + Vite (in `viz/`), Cloudflare Pages Functions + D1 (repo root), `posthog-js`, `vitest` (new test runner).

## Global Constraints

- **Pages root directory is the repo root** — the Function MUST live at repo-root `functions/api/quiz.ts`, NOT inside `viz/`.
- **Install deps with `--legacy-peer-deps`** to match the project's build command: `npm i <pkg> --legacy-peer-deps`.
- **No PII, ever.** Never write IP address, name, email, login, or any persistent device/cookie identifier to D1 or PostHog. The Function receives the client IP but must never store it.
- **Consent copy, verbatim:** `Your answers are anonymous. I store the response and result to study which parties resonate, with no names, accounts, or IP addresses attached.`
- **PostHog key/host, verbatim:** key `phc_vRxUStnjzxWPrLb449r4VvnjFUjYmxi2C7jxXHzHDhmo`, host `https://us.i.posthog.com`.
- **Allowed party codes, verbatim:** `PRG, DSA, LIB, LBR, OAO, STY, CUP, CON, POP, NAT`.
- **PostHog config:** `person_profiles: 'identified_only'`, `persistence: 'memory'`, `autocapture: false`, `capture_pageview: 'history_change'`.
- **Copy style:** public-writing voice; no em-dashes with spaces around them.
- **Commit after every task.** This is a personal project on `main`; commit locally, do not push unless asked.

## File Structure

**New (repo root):**
- `functions/api/quiz.ts` — Pages Function: `onRequestPost` (create) + `onRequestPatch` (vibe).
- `functions/api/_lib/validate.ts` — pure validation + shared constants/types (no Workers runtime deps).
- `functions/api/_lib/validate.test.ts` — unit tests for validation.
- `functions/api/quiz.test.ts` — handler tests with a mocked D1.
- `schema.sql` — D1 table DDL.

**New (viz/):**
- `viz/.env` — PostHog key/host (committed; publishable key).
- `viz/src/vite-env.d.ts` — vite client types + typed env vars.
- `viz/src/utils/analytics.ts` — PostHog init, tracking helpers, capture functions, pure helpers.
- `viz/src/utils/analytics.test.ts` — unit tests for the pure helpers.

**Modified (viz/):**
- `viz/package.json` — add `posthog-js`, `vitest`, `@cloudflare/workers-types`; add `test` scripts.
- `viz/vite.config.ts` — add vitest `test` config (includes repo-root functions tests).
- `viz/src/main.tsx` — init PostHog + mount view-state tracking.
- `viz/src/tabs/QuizTab.tsx` — capture on completion, `quiz_started`, consent note, pass `submissionId`/`onVibe`.
- `viz/src/components/quiz/QuizResult.tsx` — vibe-check UI (own result only), `result_shared` event.

---

### Task 1: Test runner + dependencies

**Files:**
- Modify: `viz/package.json`
- Modify: `viz/vite.config.ts`
- Create: `viz/src/smoke.test.ts` (temporary; deleted in Step 6)

**Interfaces:**
- Produces: a working `npm test` (vitest) that also discovers tests under repo-root `functions/`.

- [ ] **Step 1: Install dependencies**

Run (from `viz/`):
```bash
npm i posthog-js --legacy-peer-deps
npm i -D vitest @cloudflare/workers-types --legacy-peer-deps
```
Expected: installs succeed; `posthog-js` in `dependencies`, `vitest` + `@cloudflare/workers-types` in `devDependencies`.

- [ ] **Step 2: Add test scripts to `viz/package.json`**

In the `"scripts"` block, add:
```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 3: Configure vitest in `viz/vite.config.ts`**

Replace the file contents with:
```ts
/// <reference types="vitest/config" />
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: './',
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts', '../functions/**/*.test.ts'],
  },
})
```

- [ ] **Step 4: Write a smoke test**

Create `viz/src/smoke.test.ts`:
```ts
import { describe, it, expect } from 'vitest'

describe('smoke', () => {
  it('runs', () => {
    expect(1 + 1).toBe(2)
  })
})
```

- [ ] **Step 5: Run tests to verify the runner works**

Run (from `viz/`): `npm test`
Expected: PASS, 1 test passed.

- [ ] **Step 6: Delete the smoke test and commit**

```bash
rm viz/src/smoke.test.ts
cd "$(git rev-parse --show-toplevel)"
git add viz/package.json viz/package-lock.json viz/vite.config.ts
git commit -m "chore: add vitest + posthog-js; discover functions/ tests"
```

---

### Task 2: Server-side validation module

**Files:**
- Create: `functions/api/_lib/validate.ts`
- Test: `functions/api/_lib/validate.test.ts`

**Interfaces:**
- Produces:
  - `PARTY_CODES: readonly string[]`, `VIBE_VALUES: readonly ['fit','miss']`, `MAX_BODY_BYTES: number`
  - `interface CreatePayload { id: string; result_party: string; answers: Record<string, number>; scores: {party:string;prob:number}[]; referrer: string | null; quiz_version: string }`
  - `interface VibePayload { id: string; vibe: string }`
  - `validateCreate(body: unknown): { ok: true; value: CreatePayload } | { ok: false; error: string }`
  - `validateVibe(body: unknown): { ok: true; value: VibePayload } | { ok: false; error: string }`

- [ ] **Step 1: Write the failing tests**

Create `functions/api/_lib/validate.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import { validateCreate, validateVibe } from './validate'

const goodCreate = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  result_party: 'LBR',
  answers: { CC24_321d: 1 },
  scores: [{ party: 'LBR', prob: 0.6 }],
  referrer: 'https://braydendecker.substack.com/',
  quiz_version: 'v1-2026-07',
}

describe('validateCreate', () => {
  it('accepts a well-formed payload', () => {
    const r = validateCreate(goodCreate)
    expect(r.ok).toBe(true)
  })
  it('rejects an unknown party', () => {
    expect(validateCreate({ ...goodCreate, result_party: 'ZZZ' }).ok).toBe(false)
  })
  it('rejects a non-uuid id', () => {
    expect(validateCreate({ ...goodCreate, id: 'nope' }).ok).toBe(false)
  })
  it('rejects empty answers', () => {
    expect(validateCreate({ ...goodCreate, answers: {} }).ok).toBe(false)
  })
  it('rejects a non-numeric answer value', () => {
    expect(validateCreate({ ...goodCreate, answers: { CC24_321d: 'x' } }).ok).toBe(false)
  })
  it('rejects too many answers', () => {
    const answers: Record<string, number> = {}
    for (let i = 0; i < 51; i++) answers['q' + i] = 1
    expect(validateCreate({ ...goodCreate, answers }).ok).toBe(false)
  })
  it('rejects a missing quiz_version', () => {
    const { quiz_version, ...rest } = goodCreate
    expect(validateCreate(rest).ok).toBe(false)
  })
  it('defaults a missing referrer to null', () => {
    const { referrer, ...rest } = goodCreate
    const r = validateCreate(rest)
    expect(r.ok && r.value.referrer).toBe(null)
  })
})

describe('validateVibe', () => {
  it('accepts fit', () => {
    expect(validateVibe({ id: goodCreate.id, vibe: 'fit' }).ok).toBe(true)
  })
  it('accepts miss', () => {
    expect(validateVibe({ id: goodCreate.id, vibe: 'miss' }).ok).toBe(true)
  })
  it('rejects any other vibe', () => {
    expect(validateVibe({ id: goodCreate.id, vibe: 'maybe' }).ok).toBe(false)
  })
  it('rejects a bad id', () => {
    expect(validateVibe({ id: 'nope', vibe: 'fit' }).ok).toBe(false)
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `viz/`): `npm test -- validate`
Expected: FAIL — cannot resolve `./validate`.

- [ ] **Step 3: Write the implementation**

Create `functions/api/_lib/validate.ts`:
```ts
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run (from `viz/`): `npm test -- validate`
Expected: PASS, all validate tests green.

- [ ] **Step 5: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add functions/api/_lib/validate.ts functions/api/_lib/validate.test.ts
git commit -m "feat: add pure validation for quiz capture endpoint"
```

---

### Task 3: D1 schema + Pages Function

**Files:**
- Create: `schema.sql` (repo root)
- Create: `functions/api/quiz.ts`
- Test: `functions/api/quiz.test.ts`

**Interfaces:**
- Consumes: `validateCreate`, `validateVibe`, `MAX_BODY_BYTES` from `./_lib/validate`.
- Produces: HTTP endpoint `/api/quiz` — `POST` (create, 204) and `PATCH` (vibe, 204); binding `env.DB` (D1). Exports `onRequestPost`, `onRequestPatch`.

- [ ] **Step 1: Write the schema**

Create `schema.sql` (repo root):
```sql
CREATE TABLE IF NOT EXISTS quiz_response (
  id            TEXT PRIMARY KEY,
  created_at    TEXT NOT NULL,
  result_party  TEXT NOT NULL,
  answers       TEXT NOT NULL,
  scores        TEXT NOT NULL,
  vibe          TEXT,
  referrer      TEXT,
  country       TEXT,
  quiz_version  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_quiz_response_party ON quiz_response (result_party);
CREATE INDEX IF NOT EXISTS idx_quiz_response_created ON quiz_response (created_at);
```

- [ ] **Step 2: Write the failing handler tests**

Create `functions/api/quiz.test.ts`:
```ts
import { describe, it, expect, vi } from 'vitest'
import { onRequestPost, onRequestPatch } from './quiz'

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
```

- [ ] **Step 3: Run tests to verify they fail**

Run (from `viz/`): `npm test -- quiz`
Expected: FAIL — cannot resolve `./quiz`.

- [ ] **Step 4: Write the Function**

Create `functions/api/quiz.ts`:
```ts
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run (from `viz/`): `npm test -- quiz`
Expected: PASS, all quiz handler tests green.

- [ ] **Step 6: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add schema.sql functions/api/quiz.ts functions/api/quiz.test.ts
git commit -m "feat: add /api/quiz Pages Function + D1 schema"
```

---

### Task 4: Client analytics — pure helpers

**Files:**
- Create: `viz/src/utils/analytics.ts` (helpers portion only in this task)
- Test: `viz/src/utils/analytics.test.ts`

**Interfaces:**
- Produces:
  - `answersToVariableMap(questions: QuizQuestion[], answers: Record<number, number>): Record<string, number>`
  - `debounce<A extends unknown[]>(fn: (...a: A) => void, ms: number): (...a: A) => void`
  - `QUIZ_VERSION: string` (value `'v1-2026-07'`)

- [ ] **Step 1: Write the failing tests**

Create `viz/src/utils/analytics.test.ts`:
```ts
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `viz/`): `npm test -- analytics`
Expected: FAIL — cannot resolve `./analytics`.

- [ ] **Step 3: Write the helpers**

Create `viz/src/utils/analytics.ts`:
```ts
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run (from `viz/`): `npm test -- analytics`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add viz/src/utils/analytics.ts viz/src/utils/analytics.test.ts
git commit -m "feat: add pure analytics helpers (answersToVariableMap, debounce)"
```

---

### Task 5: Client analytics — PostHog init, tracking, capture

**Files:**
- Create: `viz/.env`
- Create: `viz/src/vite-env.d.ts`
- Modify: `viz/src/utils/analytics.ts` (append side-effecting functions)

**Interfaces:**
- Consumes: `posthog-js`, `QUIZ_VERSION`, `debounce`.
- Produces:
  - `initAnalytics(): void`
  - `track(event: string, props?: Record<string, unknown>): void`
  - `mountViewStateTracking(): () => void`
  - `submitQuizResult(input: { id: string; result_party: string; answers: Record<string, number>; scores: { party: string; prob: number }[] }): void`
  - `submitVibe(id: string, vibe: 'fit' | 'miss', party: string): void`

- [ ] **Step 1: Create `viz/.env`**

```
VITE_POSTHOG_KEY=phc_vRxUStnjzxWPrLb449r4VvnjFUjYmxi2C7jxXHzHDhmo
VITE_POSTHOG_HOST=https://us.i.posthog.com
```

- [ ] **Step 2: Create `viz/src/vite-env.d.ts`**

```ts
/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_POSTHOG_KEY?: string
  readonly VITE_POSTHOG_HOST?: string
}
interface ImportMeta {
  readonly env: ImportMetaEnv
}
```

- [ ] **Step 3: Append the side-effecting functions to `viz/src/utils/analytics.ts`**

Add these imports at the top (below the existing `import type` line):
```ts
import posthog from 'posthog-js'
```
Append at the end of the file:
```ts
const KEY = import.meta.env.VITE_POSTHOG_KEY
const HOST = import.meta.env.VITE_POSTHOG_HOST ?? 'https://us.i.posthog.com'

let ready = false

export function initAnalytics(): void {
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
  if (!ready) return
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

export function submitQuizResult(input: {
  id: string
  result_party: string
  answers: Record<string, number>
  scores: { party: string; prob: number }[]
}): void {
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
```

- [ ] **Step 4: Verify the pure-helper tests still pass and typecheck is clean**

Run (from `viz/`): `npm test -- analytics && npx tsc -b`
Expected: analytics tests PASS; `tsc` reports no errors.

- [ ] **Step 5: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add viz/.env viz/src/vite-env.d.ts viz/src/utils/analytics.ts
git commit -m "feat: add PostHog init, view-state tracking, and quiz capture"
```

---

### Task 6: Wire analytics into `main.tsx`

**Files:**
- Modify: `viz/src/main.tsx`

**Interfaces:**
- Consumes: `initAnalytics`, `mountViewStateTracking` from `./utils/analytics`.

- [ ] **Step 1: Read the current file**

Run: open `viz/src/main.tsx` and note the import block and the render call.

- [ ] **Step 2: Add the analytics import**

Add near the other imports:
```ts
import { initAnalytics, mountViewStateTracking } from './utils/analytics'
```

- [ ] **Step 3: Initialize before render**

Immediately before the `createRoot(...).render(...)` call, add:
```ts
initAnalytics()
mountViewStateTracking()
```

- [ ] **Step 4: Verify build**

Run (from `viz/`): `npx tsc -b && npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add viz/src/main.tsx
git commit -m "feat: initialize PostHog + view-state tracking at app entry"
```

---

### Task 7: QuizTab — capture, quiz_started, consent note, pass id/onVibe

**Files:**
- Modify: `viz/src/tabs/QuizTab.tsx`

**Interfaces:**
- Consumes: `submitQuizResult`, `submitVibe`, `answersToVariableMap`, `track` from `../utils/analytics`.
- Produces: passes `submissionId?: string` and `onVibe?: (v: 'fit' | 'miss') => void` to `<QuizResult>` (consumed in Task 8).

- [ ] **Step 1: Add imports**

Add to the import block:
```ts
import { submitQuizResult, submitVibe, answersToVariableMap, track } from '../utils/analytics'
```

- [ ] **Step 2: Add submission-id state**

After the existing `const [resultParty, setResultParty] = useUrlState...` block, add:
```ts
  const [submissionId, setSubmissionId] = useState<string>('')
```

- [ ] **Step 3: Fire `quiz_started` on the first answer**

Replace `handleSelect` with:
```ts
  function handleSelect(value: number) {
    if (Object.keys(answers).length === 0) track('quiz_started')
    setAnswers(prev => ({ ...prev, [current]: value }))
  }
```

- [ ] **Step 4: Capture the result on completion**

In `handleNext`, replace the `else` branch body with:
```ts
    } else {
      const scores = classifyQuiz(questions, answers, spreads);
      const top: RankEntry[] = scores.slice(0, 4).map(s => {
        const cl = clusters.find(c => c.id === s.clusterId);
        return { party: cl?.party ?? '', partyName: cl?.partyName ?? '', prob: s.prob };
      });
      setRanking(top);
      if (top[0].party) {
        setResultParty(top[0].party);
        const id = crypto.randomUUID();
        setSubmissionId(id);
        submitQuizResult({
          id,
          result_party: top[0].party,
          answers: answersToVariableMap(questions, answers),
          scores: top.map(t => ({ party: t.party, prob: t.prob })),
        });
      }
    }
```

- [ ] **Step 5: Reset submission id on retake**

In `handleRetake`, add after `setResultParty('');`:
```ts
    setSubmissionId('');
```

- [ ] **Step 6: Add the consent note element**

Directly before the `// Result view` comment, add:
```tsx
  const consentNote = (
    <p className="text-xs text-muted-foreground text-center pt-2">
      Your answers are anonymous. I store the response and result to study which parties resonate, with no names, accounts, or IP addresses attached.
    </p>
  );
```

- [ ] **Step 7: Render the note + pass props in the result branch**

In the result-view `return`, change the `<QuizResult .../>` usage to include the new props and add the note after it, inside the outer `<div className="space-y-8">`:
```tsx
          <QuizResult
            cluster={cluster}
            seats={seatsById[cluster.id] ?? 0}
            shared={isShared}
            ranking={ranking ?? undefined}
            onRetake={handleRetake}
            submissionId={isShared ? undefined : submissionId}
            onVibe={isShared ? undefined : (v => { if (submissionId) submitVibe(submissionId, v, cluster.party); })}
          />
          {consentNote}
```

- [ ] **Step 8: Render the note in the question branch**

At the end of the question-view `return`, add `{consentNote}` as the last child inside the outer `<div className="space-y-8 max-w-xl mx-auto">` (after the Back/Next `<div className="flex justify-between">`).

- [ ] **Step 9: Verify build**

Run (from `viz/`): `npx tsc -b && npm run build`
Expected: build succeeds. (Type errors on `submissionId`/`onVibe` props are expected here and fixed in Task 8 — if `tsc` fails only on those two unknown props, proceed to Task 8, then re-run.)

- [ ] **Step 10: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add viz/src/tabs/QuizTab.tsx
git commit -m "feat: capture quiz results, quiz_started event, and consent note"
```

---

### Task 8: QuizResult — vibe-check UI + result_shared event

**Files:**
- Modify: `viz/src/components/quiz/QuizResult.tsx`

**Interfaces:**
- Consumes: `submissionId`, `onVibe` props from QuizTab (Task 7); `track` from `../../utils/analytics`.

- [ ] **Step 1: Add the import**

Add:
```ts
import { track } from '../../utils/analytics'
```

- [ ] **Step 2: Extend the Props interface**

In `interface Props`, add:
```ts
  submissionId?: string;
  onVibe?: (v: 'fit' | 'miss') => void;
```

- [ ] **Step 3: Destructure the new props and add voted state**

Change the component signature to include the new props:
```ts
export function QuizResult({ cluster, seats, shared, ranking, onRetake, submissionId, onVibe }: Props) {
```
And add near the `const [copied, setCopied] = useState(false)` line:
```ts
  const [voted, setVoted] = useState<'fit' | 'miss' | null>(null);
```

- [ ] **Step 4: Fire `result_shared` in handleShare**

At the very top of `handleShare` (before the `if (navigator.share)`), add:
```ts
    track('result_shared', { party: cluster.party });
```

- [ ] **Step 5: Add the vibe-check block**

Immediately after the closing `</Card>` of the match card (the one with `style={{ borderColor: color }}`), add:
```tsx
      {!shared && onVibe && submissionId && (
        <div className="mb-6 rounded-lg border border-border p-4">
          {voted ? (
            <div className="text-sm text-muted-foreground">Thanks, noted.</div>
          ) : (
            <>
              <div className="text-sm font-semibold text-foreground mb-2">Does this match how you see yourself?</div>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  className="flex-1"
                  onClick={() => { setVoted('fit'); onVibe('fit'); }}
                >
                  That sounds right
                </Button>
                <Button
                  variant="secondary"
                  className="flex-1"
                  onClick={() => { setVoted('miss'); onVibe('miss'); }}
                >
                  Not really me
                </Button>
              </div>
            </>
          )}
        </div>
      )}
```

- [ ] **Step 6: Verify build (QuizTab + QuizResult together)**

Run (from `viz/`): `npx tsc -b && npm run build`
Expected: build succeeds with no errors (Task 7's prop types now resolve).

- [ ] **Step 7: Commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add viz/src/components/quiz/QuizResult.tsx
git commit -m "feat: add quiz result vibe-check + result_shared event"
```

---

### Task 9: Full verification + deploy checklist

**Files:**
- None (verification + docs only)

- [ ] **Step 1: Run the full test suite and build**

Run (from `viz/`): `npm test && npx tsc -b && npm run build && npm run lint`
Expected: all tests PASS; typecheck clean; build succeeds; lint clean.

- [ ] **Step 2: Local integration test of the Function against a local D1**

From the repo root:
```bash
npx wrangler d1 execute stv-quiz --local --file=./schema.sql
npx wrangler pages dev viz/dist --d1=DB=stv-quiz --port 8788
```
In a second terminal:
```bash
curl -i -X POST http://localhost:8788/api/quiz \
  -H 'content-type: application/json' \
  -d '{"id":"123e4567-e89b-12d3-a456-426614174000","result_party":"LBR","answers":{"CC24_321d":1},"scores":[{"party":"LBR","prob":0.6}],"referrer":null,"quiz_version":"v1-2026-07"}'
# expect: HTTP/1.1 204

curl -i -X PATCH http://localhost:8788/api/quiz \
  -H 'content-type: application/json' \
  -d '{"id":"123e4567-e89b-12d3-a456-426614174000","vibe":"fit"}'
# expect: HTTP/1.1 204
```
Confirm the row landed and stored no IP:
```bash
npx wrangler d1 execute stv-quiz --local --command "SELECT id, result_party, vibe, country FROM quiz_response;"
```
Expected: one row, `vibe=fit`; no IP column exists.

- [ ] **Step 3: Document the one-time production setup**

Append to the design spec's "What the user must do" section, or hand the user this checklist (production D1 cannot be created by a git push):
```
1. npx wrangler login
2. npx wrangler d1 create stv-quiz            # note the DB name
3. npx wrangler d1 execute stv-quiz --remote --file=./schema.sql
4. Cloudflare dashboard → Pages project → Settings → Functions → D1 database bindings:
   add binding name "DB" → database "stv-quiz", for BOTH Production and Preview.
5. PostHog → project Settings → toggle "Discard client IP data".
6. Push to main → auto-deploy. Verify:
   - PostHog "Waiting for events" flips to received after loading the site
   - a completed quiz writes one row: npx wrangler d1 execute stv-quiz --remote --command "SELECT count(*) FROM quiz_response;"
   - Cloudflare Web Analytics starts recording (already enabled)
```

- [ ] **Step 4: Final commit**

```bash
cd "$(git rev-parse --show-toplevel)"
git add -A
git commit -m "docs: production D1 + PostHog setup checklist" --allow-empty
```

---

## Self-Review

**Spec coverage:**
- Component A (D1 capture): Tasks 2, 3, 5 (client), 7 (wiring), 9 (integration). ✅
- Component B (vibe-check): Tasks 7 (id/onVibe plumbing) + 8 (UI). ✅
- Component C (consent note): Task 7, verbatim copy. ✅
- Component D (PostHog init + choke point + events): Tasks 5, 6; events `view_state`, `quiz_started` (Task 7), `quiz_completed` (Task 5/7), `quiz_vibe` (Task 5/7), `result_shared` (Task 8). ✅
- Privacy (no IP/PII): enforced in Task 3 (country-only, IP never bound), asserted by Task 3 tests and Task 9 Step 2. ✅
- Cloudflare Web Analytics: already enabled; verified in Task 9 Step 3. ✅
- Dashboard D1 binding (no wrangler.toml): Task 9 Step 3. ✅

**Placeholder scan:** No TBD/TODO; all code blocks are complete; commands have expected output. ✅

**Type consistency:** `submissionId`/`onVibe` produced by Task 7 match Props added in Task 8. `validateCreate`/`validateVibe` signatures used identically in Tasks 2 and 3. `submitQuizResult`/`submitVibe`/`answersToVariableMap`/`track`/`initAnalytics`/`mountViewStateTracking` signatures defined in Tasks 4–5 match call sites in Tasks 6–8. INSERT binds 8 params (vibe literal NULL), asserted in Task 3 test. ✅

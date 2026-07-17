# Analytics + Quiz Result Capture — Design

**Date:** 2026-07-17
**Status:** Approved for planning
**Surface:** `viz/` (React + TS + Vite SPA on Cloudflare Pages) + a new repo-root `functions/` Pages Function

## Intent

Add three capabilities to the deployed site, all on free tiers:

1. **Traffic baseline** — Cloudflare Web Analytics (already enabled in the dashboard; effective next deploy).
2. **Interaction analytics** — PostHog (free tier) for which tabs/filters get used, quiz funnels, and referrer attribution (most traffic arrives from Substack).
3. **Quiz result capture** — persist each anonymous quiz submission to Cloudflare D1 (SQLite) as a raw, analyzable dataset, plus a directional "vibe check" (does the result feel right to the respondent?).

Privacy is a first-class constraint: **no PII.** No accounts, names, emails, IP addresses, or persistent device identifiers are stored anywhere.

## Context (as-built)

- Deploy: Git-integration auto-deploy on push to `main`. Build command `cd viz && npm install --legacy-peer-deps && npm run build`, output `viz/dist`, **root directory = repo root** (blank). Therefore Pages Functions live at **repo-root `functions/`**, not inside `viz/`.
- Quiz completes in `viz/src/tabs/QuizTab.tsx` `handleNext()` (~L41-47): `classifyQuiz()` returns `{clusterId, prob}[]`, top-4 mapped to `RankEntry[]`, and the top party is written to the URL as `?result=CODE`.
- Answers are held as `Record<questionIndex, optionValue>`. Questions carry a stable **`variable`** field (CES code, e.g. `CC24_321d`); 21 questions total.
- Result card is `viz/src/components/quiz/QuizResult.tsx`. It renders for both a fresh completion (`ranking` set) and a shared `?result=` link (`shared` / `isShared`).
- URL state is centralized in `viz/src/hooks/useUrlState.ts`. Every tab and filter change dispatches a single `urlstatechange` event (L32, L47). Tab navigation uses `pushState` (real navigations, distinct URLs); filters use `replaceState` (no history entry, so pageview-only trackers miss them).
- Share/OG pages are pre-baked static HTML under `viz/public/r/<PARTY>/index.html`.
- No `functions/` dir, no `wrangler.toml` yet. `viz/.env` is not gitignored.

## Non-goals (YAGNI)

- No self-hosted analytics, no Workers Analytics Engine (PostHog chosen).
- No per-visitor identity, no session replay, no feature flags.
- No CAPTCHA/Turnstile in v1 (add later only if the endpoint is abused).
- No geographic modeling; `country` is stored only as coarse context.

---

## Component A — Quiz capture to Cloudflare D1

### Pages Function: `functions/api/quiz.ts` (repo root)

- `onRequestPost` — create a submission row.
- `onRequestPatch` — attach the vibe-check to an existing row by `id`.
- Binding: `env.DB` (D1). Server sets `created_at` and reads `request.cf.country`. The client IP is received but **never written**.
- Validation (reject with 400 on failure): `result_party` ∈ allowed party list; `answers` is an object within a size cap; `vibe` ∈ {`fit`, `miss`}; body size cap to blunt spam. Malformed input is rejected, not stored.
- CORS: same-origin only (the SPA and the Function share the Pages domain), so no permissive CORS headers.

### Schema: `schema.sql` (repo root)

```sql
CREATE TABLE IF NOT EXISTS quiz_response (
  id            TEXT PRIMARY KEY,   -- client crypto.randomUUID(); memory-only, never persisted client-side
  created_at    TEXT NOT NULL,      -- server ISO timestamp
  result_party  TEXT NOT NULL,      -- top party code, validated
  answers       TEXT NOT NULL,      -- JSON {variable: value}, keyed by CES code
  scores        TEXT NOT NULL,      -- JSON [{party, prob}] top 4
  vibe          TEXT,               -- 'fit' | 'miss' | NULL
  referrer      TEXT,               -- document.referrer (Substack attribution), nullable
  country       TEXT,               -- request.cf.country, coarse geo
  quiz_version  TEXT NOT NULL       -- bumped when the question set changes
);
CREATE INDEX IF NOT EXISTS idx_quiz_response_party ON quiz_response (result_party);
CREATE INDEX IF NOT EXISTS idx_quiz_response_created ON quiz_response (created_at);
```

`id` exists solely so the vibe PATCH can find its row. It lives in React memory between result render and the vibe click; it is **not** written to `localStorage`/cookies, so it is not a cross-session tracking identifier.

### Client capture: `viz/src/utils/analytics.ts` (new) + wiring in `QuizTab.tsx`

- On a genuine completion (ranking set, not a shared link), generate `id = crypto.randomUUID()`, transform answers to `{variable: value}` via `questions[i].variable`, and `fetch('/api/quiz', { method:'POST', keepalive:true, ... })` fire-and-forget inside `try/catch`. Capture must never block or break the UI; failures are swallowed.
- The `id` is passed to `QuizResult` so the vibe-check can PATCH the same row.

### D1 binding config

- Bind `DB` via the **dashboard** (Settings → Functions → D1 database bindings) for both Production and Preview. We deliberately do **not** add a `wrangler.toml`: this Pages project is configured through the dashboard (custom root directory, `cd viz`, `--legacy-peer-deps`), and a `wrangler.toml` would take over as the source of truth and can override/break those build settings. The DB is created and migrated with the CLI by name (below), which needs no config file.

---

## Component B — Vibe-check buttons

- Location: `QuizResult.tsx`, **your-own-result only** (`!shared`). Not shown on shared `?result=` links.
- UI: a compact block under the match card:
  > **Does this match how you see yourself?**  [ That sounds right ]  [ Not really me ]
- On click: call `onVibe('fit' | 'miss')` (prop from `QuizTab`), which PATCHes `/api/quiz` with `{id, vibe}` and fires a PostHog `quiz_vibe` event, then the component swaps to a "Thanks, noted" state and disables both buttons. One vote per submission.
- `QuizTab` owns the submission `id` and capture calls; `QuizResult` owns only its local voted state.

---

## Component C — Consent note

- A muted footnote at the bottom of the quiz, shown on both the question and result views (rendered at the `QuizTab` level).
- Copy (approved, public-writing voice, no spaced em-dashes):
  > Your answers are anonymous. I store the response and result to study which parties resonate, with no names, accounts, or IP addresses attached.

---

## Component D — PostHog analytics layer

### Install + init

- `npm i posthog-js`. Init in `viz/src/main.tsx`.
- Config from `viz/.env` (committed; the `phc_...` key is a publishable client-side key, not a secret):
  - `VITE_POSTHOG_KEY=phc_vRxUStnjzxWPrLb449r4VvnjFUjYmxi2C7jxXHzHDhmo`
  - `VITE_POSTHOG_HOST=https://us.i.posthog.com`
- Init options (privacy-forward):
  - `person_profiles: 'identified_only'`
  - `persistence: 'memory'` (cookieless → no cookie banner, consistent with the consent note)
  - `autocapture: false` (deliberate events → clean, low-volume dataset)
  - `capture_pageview: 'history_change'` (tab `pushState` navigations become pageviews automatically)
- Manual dashboard step (documented, not code): enable **"Discard client IP data"** in PostHog project settings.

### The single instrumentation choke point

- One listener on the existing `urlstatechange` event (dispatched in `useUrlState.ts`), debounced ~500ms, fires `capture('view_state', {…all current query params})`. This covers **every tab and filter** with zero per-component instrumentation. Debounce collapses slider drags (e.g. `part=10`) into one event.
- Mounted once (in `main.tsx` or a top-level effect in `App.tsx`), torn down on unload.

### Explicit events

- `quiz_started` (first answer), `quiz_completed` `{party}`, `quiz_vibe` `{party, vibe}`, `result_shared` (in `QuizResult.handleShare`).

---

## What the user must do (one-time)

Everything except D1 needs nothing beyond what is already done (Web Analytics enabled; PostHog key provided). D1 requires a one-time setup:

```bash
npx wrangler login                  # once, opens browser
npx wrangler d1 create stv-quiz     # prints the database name/id
npx wrangler d1 execute stv-quiz --remote --file=./schema.sql   # loads the table by name
```

Then bind `DB` → the `stv-quiz` database in the Pages project: dashboard Settings → Functions → D1 database bindings, for **both Production and Preview**. PostHog: toggle "Discard client IP data".

## Privacy summary

- Stored: anonymous answers (keyed by CES code), result, top-4 scores, coarse country, referrer, timestamp, quiz version, optional vibe.
- Never stored: IP, name, email, login, persistent device/cookie identifier.
- PostHog runs cookieless (`persistence: 'memory'`) with IP discarded server-side and profiles only for identified users (there are none). Political-opinion responses are not linked to any identifiable person, so they are not "personal data" under GDPR special-category rules.

## Testing

- Function: unit-test validation (reject bad `result_party`, oversized body, bad `vibe`); POST-then-PATCH happy path against a local D1 (`wrangler d1 execute --local`).
- Client: capture is fire-and-forget and must not throw into the UI; a failed/blocked `fetch` leaves the result view fully functional (test with network offline).
- Vibe-check: renders only on own result, hidden on shared links, single-vote lockout after click.
- Manual: after deploy, confirm PostHog "Waiting for events" flips to verified, `view_state` events carry tab+filter params, and a completed quiz writes one D1 row.

## Files touched

- New: `functions/api/quiz.ts`, `schema.sql`, `viz/.env`, `viz/src/utils/analytics.ts`
- Edit: `viz/src/main.tsx` (PostHog init + choke-point listener), `viz/src/tabs/QuizTab.tsx` (capture + consent note + pass `id`/`onVibe`), `viz/src/components/quiz/QuizResult.tsx` (vibe-check UI + `result_shared` event), `viz/package.json` (`posthog-js`)

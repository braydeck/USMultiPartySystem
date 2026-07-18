# Analytics + Quiz Capture — one-time production setup

The code is deployed by pushing to `main` (Cloudflare Pages auto-builds). A few
things cannot be done by a git push and must be set up once.

## 0. Point the Pages root directory at `viz` (required for the Function)

Cloudflare only detects the `functions/` directory when it sits inside the
project's **root directory**. This app lives in `viz/`, and the Function is at
`viz/functions/api/quiz.ts`, so the Pages build settings must use `viz` as the
root (instead of the old blank root + `cd viz` build command).

Cloudflare dashboard → Pages → **usmultipartysystem** → Settings → Build →
**Build configuration** → Edit:

- **Root directory:** `viz`
- **Build command:** `npm install --legacy-peer-deps && npm run build`
- **Build output directory:** `dist`

(Previously: blank root, `cd viz && npm install --legacy-peer-deps && npm run build`,
output `viz/dist`. The new settings produce identical static output and also let
Pages find `viz/functions/`.)

## 1. Create + bind the D1 database (required for quiz capture)

From the repo root:

```bash
npx wrangler login                                          # once, opens browser
npx wrangler d1 create stv-quiz                             # note the database name/id it prints
npx wrangler d1 execute stv-quiz --remote --file=./schema.sql   # creates the table
```

Then bind it to the Pages project in the dashboard:

- Cloudflare dashboard → Pages → **usmultipartysystem** → Settings → Functions →
  **D1 database bindings** → Add binding
- Variable name: `DB`  →  Database: `stv-quiz`
- Add it for **both Production and Preview**.

> We intentionally do **not** commit a `wrangler.toml`. This Pages project is
> configured through the dashboard. A committed `wrangler.toml` would become the
> source of truth and could override/break those build settings.

## 2. PostHog privacy toggle

- PostHog → project Settings → toggle **"Discard client IP data"** on.
- (The client already runs cookieless: `persistence: 'memory'`, `autocapture: false`,
  `person_profiles: 'identified_only'`.)

## 3. Cloudflare Web Analytics

Already enabled in the Pages dashboard; it takes effect on the next deploy. Nothing to do.

## Post-deploy verification

After the next push to `main` deploys:

```bash
# a completed quiz should add rows:
npx wrangler d1 execute stv-quiz --remote --command "SELECT count(*) AS n, vibe FROM quiz_response GROUP BY vibe;"
```

- PostHog "Waiting for events" flips to received once the site loads.
- `view_state` events carry the current tab + filter params.
- Events: `quiz_started`, `quiz_completed`, `quiz_vibe`, `result_shared`.

## What is (and isn't) stored

Stored per quiz submission: a random submission id, server timestamp, result
party, answers keyed by CES `variable`, top-4 scores, coarse `country`,
`referrer`, `quiz_version`, and an optional `vibe` (`fit`/`miss`).

Never stored: IP address, name, email, login, or any persistent device/cookie
identifier.

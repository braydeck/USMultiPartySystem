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
- (The client runs `persistence: 'localStorage'` — a random anonymous id, no cookie/PII, so unique visitors are counted accurately — plus `autocapture: false`,
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
- `view_state` events carry the current tab + filter params (tab always explicit).
- Events: `quiz_started`, `quiz_completed`, `quiz_vibe`, `result_shared`,
  `shared_result_opened`, `filter_changed`, `view_state`.

## Querying the quiz results (Cloudflare D1)

Dashboard → **Storage & Databases → D1 SQL Database → `stv-quiz` → Console**; paste
one query, Execute. Columns: `id, created_at, result_party, answers, scores, vibe,
referrer, country, quiz_version`. `answers`/`scores` are JSON text; `created_at` is
UTC (subtract 6h for MDT in summer).

```sql
-- how many responses
SELECT count(*) AS total FROM quiz_response;

-- party distribution
SELECT result_party, count(*) AS n
FROM quiz_response GROUP BY result_party ORDER BY n DESC;

-- vibe check: does the result feel right?  (fit/miss/no-vote per party)
SELECT result_party,
       SUM(vibe='fit')   AS fit,
       SUM(vibe='miss')  AS miss,
       SUM(vibe IS NULL) AS no_vote,
       count(*)          AS total
FROM quiz_response GROUP BY result_party ORDER BY total DESC;

-- overall vibe hit-rate among voters
SELECT SUM(vibe='fit') AS fit, SUM(vibe='miss') AS miss,
       ROUND(SUM(vibe='fit')*100.0/SUM(vibe IS NOT NULL),1) AS fit_pct
FROM quiz_response;

-- traffic sources
SELECT COALESCE(referrer,'(direct)') AS source, count(*) AS n
FROM quiz_response GROUP BY source ORDER BY n DESC;

-- responses per day
SELECT substr(created_at,1,10) AS day, count(*) AS n
FROM quiz_response GROUP BY day ORDER BY day;

-- newest responses
SELECT created_at, result_party, vibe, referrer
FROM quiz_response ORDER BY created_at DESC LIMIT 25;

-- pull a specific answer out of the JSON (keyed by CES variable)
SELECT result_party,
       json_extract(answers,'$.CC24_321d')        AS police,
       json_extract(answers,'$.CC24_421_1_agree')  AS elections_fair,
       vibe
FROM quiz_response;
```

For analysis (join answers to the EFA/CES work), export the whole table and flatten:

```bash
npx wrangler d1 execute stv-quiz --remote --json \
  --command "SELECT * FROM quiz_response;" > quiz_data.json
```
```python
import json, pandas as pd
rows = json.load(open("quiz_data.json"))[0]["results"]
df = pd.json_normalize(rows)
answers = pd.json_normalize(df["answers"].map(json.loads))   # one column per CES variable
df = pd.concat([df.drop(columns=["answers","scores"]), answers], axis=1)
```

## PostHog report recipes

The site is a single path (`/`) with the tab/filters in the query string, so
PostHog's path-based "top pages" collapses to `/`. Use the custom events instead
(Product Analytics → Trends). All are forward-looking (data accrues from when each
event shipped).

- **Top areas:** event `view_state` → break down by `tab` → *Unique users*.
- **Within an area:** filter `view_state` where `tab = house` → break down by a filter
  param (`scenario`, `part`, `wyoming`, `section`, `cmp`, `result`).
- **Most-used filters:** event `filter_changed` → break down by `filter`; filter to one
  `filter` and break down by `value` for popular settings.
- **Traffic sources:** break down by `$channel_type` (buckets) or `$referring_domain`
  (raw domains). Exclude both hosts' self-referrals (share redirects): `usmultiparty.com`, the
  canonical domain, and `usmultipartysystem.pages.dev`, which still resolves.
- **Shares:** filter `utm_source = result_share` (survives the /r redirect even with no
  referrer), or the `shared_result_opened` event; break down by `party`/`utm_content`.

Self-exclusion: visit `?analytics=off` on a browser to stop it sending any data
(PostHog + D1); `?analytics=on` re-enables. Persists per browser in localStorage.

## What is (and isn't) stored

Stored per quiz submission: a random submission id, server timestamp, result
party, answers keyed by CES `variable`, top-4 scores, coarse `country`,
`referrer`, `quiz_version`, and an optional `vibe` (`fit`/`miss`).

Never stored: IP address, name, email, login, or any persistent device/cookie
identifier.

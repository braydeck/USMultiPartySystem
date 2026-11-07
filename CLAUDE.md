# START HERE

Repo: `/Users/bdecker/Local Projects/Personal/STV`. Direct push to `main`, no PR workflow.
This file auto-loads every session for this project only. Keep it short and current; when
something here goes stale, fix it here rather than adding a second note elsewhere.

Supporting docs: `docs/METHODOLOGY.md` (how the pipeline works), `docs/EFA_FACTORS.md` (full
factor loadings), `docs/DATA_SOURCES.md` (which file is authoritative for a given number).
`docs/AGENTS.md`, `AGENT_CONTEXT.md` and `PROJECT_GUIDE.md` were deleted 2026-09-12; they
described a two-worktree layout that no longer exists and held nothing the three above lack.

## What this is

A simulation of American elections under proportional representation, built from 2024 CES
survey data. A polychoric EFA reduces 41 policy items to 4 ideological factors; a Dirichlet
Process Gaussian Mixture Model clusters respondents into 9 voter types, and each cluster
becomes a party. Those parties then contest a House, a Senate, a presidency, and a legislative
agenda under several counting rules. The point is that the counting rule changes the answer.

The deliverable is a React + TypeScript + Vite + Tailwind + shadcn app in `viz/`, deployed to
Cloudflare.

## Invariants

| Fact | Value |
|---|---|
| Respondents | **49,431**: every post-weighted respondent who answered at least half of each factor's primary items (available-item scoring, nine-party typology of 2026-11-04). Not 45,214, the old listwise count. |
| Parties | **9**, the cap-9 modal solution of the revised §3c rule on the four plain factor scores (ruled 2026-11-04, `analysis/efa/exploration/listwise_check/DECISIONS.md`): 17 of 20 seeds reach it, 8 of 9 clusters stable under resampling (POP at 0.75). The DPGMM fills every component it is given, so the count is a cap. Borders between neighboring parties are approximate; the re-clustering bootstrap carries that into every interval. No party is protected: a new typology may add, merge or drop parties on the evidence. |
| House chamber | **873 seats** (double magnitude), 1,726 (triple). **Not 435.** |
| House districts | 150 double, 243 triple. MMP and Single Race instead use the 436 real 119th-Congress districts. |
| Senate | 51 seats, one per state plus DC |
| Electoral college | 975 electors |
| Cluster to party | 0 CON, 1 LBR (Labor), 2 STY, 3 NAT, 5 POP, 6 CUP (Civic Union), 7 OAO (Order and Opportunity), 8 DSA, 9 PRG. Slot 4 (DAL) holds no voters. Left-right order is how often the parties vote together (first MDS dimension of party-majority agreement on the 37 Legislation bills, ruled 2026-11-06): DSA PRG LBR CUP STY OAO CON POP NAT (`analysis/coalitions/vote_agreement.py` → `data/processed/party_order.csv` → `party_codes.LEFT_RIGHT`, and it rewrites `F5_ORDER`). IDs stay stable across typologies; scripts get the live parties from `pipeline/party_codes.py`, which reads them off the typology, and keep length-10 arrays only where `prob_cluster_0..9` is positional. |
| App defaults | ballot depth `top7`, turnout gap `5%`, magnitude `double`, field `rawMulti` |

Before quoting any chamber-level count, sum it out of the JSON. Do not reach for 435.

## The four factors

App keys (`pipeline/factor_keys.py`): F1 Security & Order (= −FS_SO), F2 Government Distrust
(= FS_TR), F4 Cultural Conservatism (= FS_RT), F5 Economic Conservatism (= −FS_PC). F3 retired.
The raw FS_SO and FS_PC scores run high = liberal (r −0.58 with ideo5), so anything that shows
or describes a position uses the keyed `FS_F*` columns of `efa_factor_scores.csv`; clustering,
ballots and the bootstrap use the raw `FS_RT/TR/SO/PC`, which are sign-invariant there.
Parties separate most on F4 (η² 0.75), then F1 and F5 (0.69), least on F2 (0.23).

Scores come from `analysis/efa/pipeline/efa_revised.py` (41 items, pairwise polychoric, PAF +
oblimin, available-item scoring, no residualization). Party IDs are pinned through
`data/processed/party_id_reference.csv`; `dpgmm_clustering.py` keeps seed 52, the best lower
bound in the modal solution. A new typology is rebuilt with `pipeline/rebuild_from_typology.py`:
`check_stale.py --regenerate` covers only the house trees and the payloads.

The quiz has a short (25-item) and long (40-item) version (the 41 factor items less the out-of-date
TikTok item, `QUIZ_EXCLUDE`), keys and classifier built by
`viz/scripts/make_quiz_questions.py` then `analysis/efa/build_quiz_shortform.py`.

## How a voter becomes a ballot

The DPGMM gives each respondent a membership probability across the nine clusters. Candidate
scores come from that posterior, and `argsort` on the scores is the ranked ballot. Ranks 1
through 3 carry 98.6% of a voter's probability mass. Slate order within a party is fixed and
identical for every voter, so the model represents slate voting at the strong-discipline limit.

Two candidate fields exist. **`rawMulti` (pure_multi) is the only one displayed**: pure party
candidates, 1 to 3 per party by local strength. The **crossover** (`factor_deviation`) field
adds ideologically shifted variant candidates and is reachable only via `?lab=crossover`.

## The ten tabs

| Tab | What it simulates |
|---|---|
| **Overview** | Headline results, turnout robustness, the case for the whole thing |
| **Party Quiz** | Answer real CES items, get scored on the 5 factors, land in a party |
| **Parties** | Party platforms, factor positions, comparison against today's DEM/IND/REP |
| **Presidency** | *Primary:* 27 candidates (9 parties × 3) through a 4-stage rolling-electorate STV winnow (Retail 27→12, Pod A 12→9, Pod C 9→7, Pod B/D 7→5). *General:* national IRV, per-state IRV, and Ranked Pairs Condorcet over the 5 finalists, plus an electoral-college cartogram and a top-two reduction |
| **Senate** | Two stages per state: a rank-7 STV winnow of ~20 candidates to 5 finalists, then IRV or Condorcet over those 5 **fully ranked**. No depth toggle |
| **House** | Four systems on the same ballots: **STV** (multi-member, Droop quota, weighted inclusive Gregory), **Party List** (Sainte-Laguë), **MMP** (compensatory, real 119th districts + per-state top-off), and a **~20% per-state reserve** tier layered on STV or List. Toggles: system, magnitude, depth, turnout, reserve |
| **Single Race** | FPTP head-to-head in a real 119th district, with opinion and turnout sliders |
| **Legislation** | Bill-by-bill floor-vote probabilities for House and Senate, baked at rank-7 chambers and depth-7 president. Two models: **chamber vote model** (sum of independent binomials over observed per-party support) and **candidate vote model** (per-bill logistic regression on the 5 factors, predicting from party centroids). Their disagreement is the "divergence" finding |
| **IRV Case Studies** | Real Alaska and Maine cast vote records, not simulation |
| **What Is This?** | Methodology, the nine parties, voting systems, turnout, caveats |

`polarization/` is a separate cross-national study (V-Dem / QoG) with its own README and
FINDINGS; it does not feed the app.

## Turnout and depth

**Turnout** weights each respondent by their cluster's validated 2024 turnout (CES `TS_g2024`,
Spec 1, roughly 59% weighted national). The `part` URL param picks a gap stop: 0, 5, 10, 15,
20, 25, 30. Default 5%. Every stop is a parallel `_turnout` / `_lNN` output tree.

**Ballot depth** is 3 / 5 / 7 / 10 / rank-all, default 7, exposed on House STV and the Primary.
Senate, presidential general, and Legislation are baked at rank-7.

## Where numbers come from

Displayed numbers live in `viz/src/data/*.json` (bundled) and `viz/public/data/*.json`
(fetched lazily). `viz/scripts/prepare_data.py` converts pipeline CSVs into most of them;
`pipeline/build_*.py` writes the rest.

**Trace a number to its JSON, then to the script that writes that JSON, before explaining it.**
Reading a script in `pipeline/` is not evidence the app uses it. Use
`grep -rln <module> pipeline/` to check for a live importer.

## The traps

0. **Approval of actors never enters an item pool.** Presidential, Congress, SCOTUS, governor and
   legislator approval (`CC24_312*`, and ANES equivalents) measure who holds power and how they are
   doing, not ideology. Don't propose them back, including Congress approval on the grounds that its
   party-ID R² is low or that available-item scoring removes its missingness cost. Institutional
   *trust* items are a different category and stay in (`docs/EFA_ITEM_SELECTION_ROBUSTNESS.md` Stage A).

1. **Ballot depth counts CANDIDATES, not parties.** Every party fields at least one candidate
   per district and strong parties field 2 to 4, so a depth-7 ballot reaches roughly **3
   parties**, never 7. Sizing is `n_candidates_for_district()` in
   `run_pure_multi_house_stv.py`; the Senate uses share thresholds (≥12% → 3, ≥5% → 2, ≥1% → 1).

2. **`pipeline/party_stv.py` is dead code**, but `party_ballots.csv` is NOT. Only
   `run_party_*.py` import the module and nothing displayed reads its output. The ballots file
   is separate: `prepare_data.py` reads `pure_multi/party_ballots.csv` to build
   `houseTransfers.json`, which the House tab imports.

3. **Party List counts each voter's top party on purpose.** `run_pure_multi_house_stv.py`
   scores candidates with `prob_cluster_k`, so STV's rank-1 already *is* the argmax. Matching
   the vote definition makes a list-versus-STV gap purely about the counting rule. Settled.

4. **Join respondent files by `caseid`, never by a re-derived mask.** `efa_factor_scores.csv` and
   `typology_cluster_assignments.csv` are row-aligned and both carry `caseid`; join the DTA with
   `.set_index('caseid').loc[typ.caseid]`. The old `ITEMS_24` `notna()` mask selects 45,214 rows,
   not the 49,431 of the four-factor typology, so a positional join on it is silently wrong.

5. **A below-quota floor is ordinary STV; ballot depth drives the variation above it.** When
   the continuing candidates run down to the seats remaining, the engine elects them regardless
   of quota (`run_pure_multi_house_stv.py:241`). That is the normal end-game and needs no
   exhaustion. Depth explains the movement: 34.2% of seats below quota at top-3, 18.8 / 13.2 /
   9.6, and a 7.9% floor at full ranking. Benchmark the floor before calling it high — one such
   seat in each of the 150 districts would be 17.2%, so 7.9% (69 seats, 46% of districts) sits
   well under the ordinary rate. Concentration is a plausible story for *which* districts sit at
   the floor, untested as of 2026-09-12. These figures predate the 2026-10 rescore; re-measure
   before quoting.

6. **`id` is the correct FD axis label.** Do not re-run `rename_ae_to_es.py`.

7. **`prepare_data.py` alone is not the whole build.** It writes the pre-rank-7 Legislation and
   Senate files, so it must be followed by `build_legislation_rank7.py` and
   `build_senate_rank7.py` or those tabs silently revert. Full sequence:
   ```
   python3 viz/scripts/prepare_data.py
   python3 pipeline/build_legislation_rank7.py
   python3 pipeline/build_senate_rank7.py
   ```
   **Then run `npm test` in `viz/`, not just `tsc` and `npm run build`.** Several tests assert
   against the real payloads in `viz/src/data/` (the contested-state set in
   `senateDelegations.test.ts`, for one), so a data regeneration can turn the suite red while
   the type check and the build both stay green. That is how a broken test rode along in
   56db6d5 for four commits.

8. **The senate bootstrap and `build_senate_rank7.py` must run at the same depth.**
   `analysis/bootstrap/contests.py` resamples the senate, and `viz/src/data/uncertainty*.json`
   is what the Senate map, the modal winner, and the two-winner split actually render.
   `pureMultiSenate*.json` only supplies the fallback fill. If the two are built at different
   depths the page shows one model and the observed files hold another, which is invisible
   because the map colors by `u.modal`. Note `sen.main(ballot_depth=N)` reassigns its global
   `OUTPUT_DIR` to `<parent>_topN/senate`, so read back where it wrote, not where you pointed it.

   **Every bootstrap draw re-clusters** (`analysis/bootstrap/recluster.py`): the parties are
   refit on the draw's resample, then the draw's elections run on that same resample, so the
   intervals carry party uncertainty as well as vote noise. Fits are cached in
   `data/bootstrap_cache/` (gitignored); delete it after a new typology. `analysis/bootstrap_house.py` reruns only the
   House on those fits for every other map and depth (`viz/public/data/houseSeatRanges.json`);
   `bootstrap_partylist.py` covers all four maps. `--fixed-parties` on
   the three bootstrap scripts restores the old fixed-party harness. The Senate split cutoff
   (`SPLIT_THRESHOLD_PP` in `viz/src/lib/senateDelegations.ts`) was chosen on these draws'
   per-state gaps and must be re-measured whenever the parties change.

9. **Committed outputs drift silently when an input changes and nothing re-runs.** Run
   `python3 pipeline/check_stale.py` (1s) — it hashes every declared input against
   `data/outputs/.verified.json` and names the groups that need rebuilding. `--regenerate`
   (~3 min) rebuilds everything, diffs, and rewrites the stamp; commit the stamp with the
   outputs. This is what caught nothing in July, when `county_split_overrides.csv` changed and
   73 of 74 house trees sat stale for six weeks.

   When verifying a pipeline **edit**, still never diff against HEAD: the runners rewrite their
   own committed output on a no-op re-run. Run the unedited code, snapshot, apply the edit,
   re-run, diff those two. The runners are deterministic (byte-identical across runs and across
   `PYTHONHASHSEED`); it is the committed baseline that lags.

## Voice for app copy

Claim-first and mechanism-named. No editorial commentary ("surprisingly", "unlike X", "more
moderate than"). Party labels, never candidate codes (RH, MW, MRJ). Sparse em-dashes, never a
spaced one. Propose moving UI elements rather than removing them. See the user's global
`CLAUDE.md` and the `public-writing` skill.

## Deeper notes

Session memory is at
`~/.claude/projects/-Users-bdecker-Local-Projects-Personal-STV/memory/`, indexed by
`MEMORY.md`. **Open the linked file, not just the index line**, before reasoning about ballots,
depth, EFA factors, or which pipeline is live.

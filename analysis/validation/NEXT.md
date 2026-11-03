# NEXT: validation (ANES / GSS / CES team modules)   (written 2026-11-02 after the ANES available-item segmentation ruling)

## Where it stands
- Matched EFA, PSU bootstrap of φ and the nine-party matched clustering benchmark stand (`anes/outputs/`, c73f4d8). On 18 matched items no CES party survives a majority of ANES-sized subsamples, which is the case for the classifier.
- Independent ANES EFA: 99 items, 10 factors, no party-ID cap (`anes/independent_efa.py`, 6394b0f; DECISIONS 2026-10-31).
- Independent segmentation, now primary: available-item scoring, no cull (`anes/independent_clustering.py --available`, output `anes/outputs/clustering/independent_available/`; DECISIONS 2026-11-02). It covers 4,673 respondents and fits 10 factors (φ 0.97–0.99 vs the 99-item fit). Cap 4 gives 4 clusters, 20 of 20 seeds reach one solution, and resample ARI is 0.68. Committed with this handoff.
- Profiles and portraits now read the available output (`describe_clusters.py`, `describe_segments.py`, `segment_portraits_page.py`, `cluster_profiles_page.py`). The four segments rematched by profile: 2 secular progressives, 0 center-left moderates (renamed from "moderate Democrats": 56% Harris, 20% Trump, 30% Republican ID), 3 young disaffected working class, 1 religious conservatives. Portrait claims and superlatives re-derived from the new CSVs. The Israel and Ukraine aid factor runs high = opposes aid in this fit; `STANCE` was flipped and Trust in institutions added.
- The culled segmentation (3777ff7) is archived to `_ARCHIVE (superseded, do not cite)/anes/outputs/clustering/independent/`. `AGENTS.md` here holds the sources-of-truth table.
- Why ANES stops at 4 clusters (`anes/n_check.py`, `anes/dims_check.py`): sample size, not factor count. CES's five production factors cut to ANES's 4,673 keep caps 5, 6 and 9 across three draws, 8 at 2x and 9 at 4x. ANES's own 99 items refit at 3, 5, 7 and 10 factors keep caps 4, 5, 4 and 4. All 10 resamples of the production ANES scores keep cap 4.
- Without the 10 foreign-policy items (`anes/nofp_check.py`): parallel analysis still picks 10 factors, the cap rule still keeps 4 (all 4 stable, resample ARI 0.74 vs 0.68), ARI 0.61 vs production. Religious conservatives 98%, secular progressives 88% and young disaffected 85% land in one new cluster; center-left moderates split 63/19/17. Trust items: CSES institutional trust and efficacy items have party-ID R2 <= 0.01; media and scientists 0.13-0.17.
- CES side: the listwise-deletion check moved to its own workstream, `analysis/efa/exploration/listwise_check/NEXT.md`.

## Waiting on the researcher
- Merge: `bd-corrected-scoring` and `bd-nine-parties` are pushed, not merged to `main`. Merging deploys the nine-party site.
- Party copy rewrite (main app): drafts in `analysis/efa/exploration/k9_profiles/proposed_copy.json`.

## Next steps
1. Classifier, **on hold until the eight-party CES rebuild lands** (researcher, 2026-11-02; `analysis/efa/rebuild_eight_parties/`). Don't ask again; start it when the rebuild is committed. (Workstream 2 of `UNTRACKED/plans/ces_anes_gss_validation_plan.md`): CES→ANES on `exact`/`close` crosswalk items, party posterior target (eight parties after the rebuild), recall gate 0.5, shrinkage on held-out CES. Writes `classifier_report_anes.md`. Re-measure which parties fail recall.

## Handed off in parallel
- `analysis/efa/exploration/listwise_check/` (CES): tests whether CES loadings and parties survive re-estimation on all 49,432 post-weight respondents. This workstream waits on nothing from it. Same tree and branch: commit with explicit paths.

## Running
- Viz dev server: port 5199, `cd viz && npm run dev -- --port 5199 --strictPort` (not needed here).

## Don't redo
- Don't reintroduce a cull or a per-factor item count; available-item scoring replaced them (DECISIONS 2026-11-02). Keep the anchor rule, the cap rule (largest cap 2–10 with no dissolving cluster) and the ≥ half-items-per-factor threshold.
- Don't rerun the matched or independent EFA for the rescore; the CES inputs didn't change beyond the Populist Conservatism sign.
- Don't edit the matched crosswalk; it is frozen (DECISIONS 2026-10-27).
- Describe segments by factor profile and descriptors, not by D/R lean (memory `describe-on-factors-not-party`).
- ANES data: `UNTRACKED/anes_timeseries_2024_csv_20250808/` (not committed). Weights/PSU/strata `V240108a/c/d`. Use `.venv/bin/python`.

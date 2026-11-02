# NEXT: validation (ANES / GSS / CES team modules)   (written 2026-11-02 after the ANES available-item segmentation ruling)

## Where it stands
- Matched EFA, PSU bootstrap of φ and the nine-party matched clustering benchmark stand (`anes/outputs/`, c73f4d8). On 18 matched items no CES party survives a majority of ANES-sized subsamples, which is the case for the classifier.
- Independent ANES EFA: 99 items, 10 factors, no party-ID cap (`anes/independent_efa.py`, 6394b0f; DECISIONS 2026-10-31).
- Independent segmentation, now primary: available-item scoring, no cull (`anes/independent_clustering.py --available`, output `anes/outputs/clustering/independent_available/`; DECISIONS 2026-11-02). It covers 4,673 respondents and fits 10 factors (φ 0.97–0.99 vs the 99-item fit). Cap 4 gives 4 clusters, 20 of 20 seeds reach one solution, and resample ARI is 0.68. Committed with this handoff.
- The culled segmentation (`anes/outputs/clustering/independent/`, 3777ff7) is superseded. The descriptors and portraits were built on it: `describe_segments.py`, `segment_portraits_page.py` and `describe_clusters.py` still read `independent/`. Against the available version the culled one has ARI 0.64 and 84–90% per-segment correspondence, but only 63% for the young disaffected segment. Unverified: whether the four portrait names still fit.
- CES side: the listwise-deletion check moved to its own workstream, `analysis/efa/exploration/listwise_check/NEXT.md`.

## Waiting on the researcher
- Merge: `bd-corrected-scoring` and `bd-nine-parties` are pushed, not merged to `main`. Merging deploys the nine-party site.
- Party copy rewrite (main app): drafts in `analysis/efa/exploration/k9_profiles/proposed_copy.json`.

## Next steps
1. Repoint the profile scripts at the available output. Change `SRC` in `anes/describe_segments.py:29` and `anes/segment_portraits_page.py:17`, and `independent()` in `anes/describe_clusters.py`, to `clustering/independent_available`. Then archive `outputs/clustering/independent/` to `_ARCHIVE (superseded, do not cite)/` with the research-project-setup `archive.py`.
2. Rerun `describe_clusters.py`, `describe_segments.py` and `segment_portraits_page.py`. Segment ids will differ from the culled run. Rematch the segments by profile, then re-derive the names, `ORDER`, the `STANCE` map and every portrait claim from the new CSVs. Don't carry text over. Check each superlative against the data. Open the page locally with `open` (memory `artifacts-local-only`) and commit.
3. Classifier (workstream 2 of `UNTRACKED/plans/ces_anes_gss_validation_plan.md`): CES→ANES on `exact`/`close` crosswalk items, nine-party posterior target, recall gate 0.5, shrinkage on held-out CES. Writes `classifier_report_anes.md`. Re-measure which parties fail recall.

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

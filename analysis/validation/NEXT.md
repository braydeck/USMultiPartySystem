# NEXT: validation (ANES / GSS / CES team modules)   (written 2026-10-30 by the session that rebuilt the CES typology at nine parties)

## Where it stands
- Matched crosswalk frozen (`anes/config/anes_matched_crosswalk.csv`, af017de); independent pool in `anes/config/anes_independent_pool.csv`.
- Matched EFA, PSU bootstrap of φ, and independent EFA ran 2026-10-27 (2aa5c6c): Institutional Distrust φ 0.96, Religious Traditionalism 0.90, Populist Conservatism splits, Security & Order mostly a spending-format factor, parallel analysis k=3 in both surveys. Outputs in `anes/outputs/`.
- Clustering benchmark (cd1d300, `anes/outputs/clustering/`): at ANES n=3,796 on CES's 24 items only NAT survives a majority of subsamples (57%).
- Team-module scan done: `ces_team_modules_scan.md` (all 46 modules released 2026-10-05).
- **All of the above predates the rescore (69a6eeb) and the nine-party typology.** `analysis/efa/efa_loadings_k5_final.csv` changed in 69a6eeb, and `matched_clustering.py` reads `data/processed/typology_cluster_assignments.csv`, now nine parties. None of the ANES numbers above are current.
- Unverified: `data/processed/polychoric_matrix.csv` (read by `matched_efa.py`, docstring says n=45,707) has not changed since May. Confirm which matrix the rescored loadings came from (candidate: `analysis/efa/exploration/church_dk/outputs/polychoric_B_45214.csv`) before rerunning.

## Waiting on the researcher
- Party copy rewrite (main app, not this workstream): rewrite in the researcher's voice with numbers in a separate review column, for `viz/src/constants/parties.ts` and `viz/src/components/shared/PartyProfileCard.tsx`. Drafts: `analysis/efa/exploration/k9_profiles/proposed_copy.json`. The researcher reviews before anything lands.
- Merge: `bd-corrected-scoring` and `bd-nine-parties` (e8ac89a) are pushed, not merged to `main`. Merging deploys the nine-party site.

## Next steps
1. Settle the CES polychoric input (above), then rerun on the rescored CES: `python3 analysis/validation/anes/matched_efa.py`, `bootstrap_phi.py`, `independent_efa.py` (bridge correlations use CES factor scores). Diff against the committed `anes/outputs/*` and report which findings moved.
2. Rerun `python3 analysis/validation/anes/matched_clustering.py` against the nine-party typology (writes `anes/outputs/clustering/`). Party labels come from `pipeline/party_codes.py`, not a hard-coded ten-party map.
3. Then Workstream 2 of `UNTRACKED/plans/ces_anes_gss_validation_plan.md`: CES→ANES classifier on `exact`/`close` crosswalk items, recall gate 0.5, shrinkage on held-out CES; writes `analysis/validation/classifier_report_anes.md`.

## Running
- Viz dev server: port 5199, `cd viz && npm run dev -- --port 5199 --strictPort` (not needed for ANES work).

## Don't redo
- Don't edit the matched crosswalk; it is frozen by design (DECISIONS 2026-10-27). Items without a clean analog stay omitted, including `CC24_424`.
- Trust and election-fairness items stay in the independent pool; spending battery and thermometers stay out (DECISIONS 2026-10-27).
- ANES data is `UNTRACKED/anes_timeseries_2024_csv_20250808/` (not committed). Splice `V241382`+`V241383` and `V241439`+`V241440`; weights/PSU/strata `V240108a/c/d`.
- `data/bootstrap_cache/` holds the nine-party re-clustering fits (gitignored); don't delete it unless the typology changes again.

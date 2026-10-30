# NEXT: validation (ANES / GSS / CES team modules)   (written 2026-10-30 by the session that rebuilt the CES typology at nine parties)

## Where it stands
- Matched crosswalk frozen (`anes/config/anes_matched_crosswalk.csv`, af017de); independent pool in `anes/config/anes_independent_pool.csv`.
- Matched EFA, PSU bootstrap of φ, and independent EFA (2aa5c6c, `anes/outputs/`): Institutional Distrust φ 0.96, Religious Traditionalism 0.92, Populist Conservatism splits, Security & Order mostly a spending-format factor, parallel analysis k=3 in both surveys. **These still stand after the rescore** (checked 2026-10-30):
  - The production loadings come from `data/processed/polychoric_matrix.csv` (`analysis/efa/pipeline/efa_update.py:172`), unchanged since May. That matrix is label-coded with church "Don't know" as missing (`efa_pipeline_v4.py:55`), so the scoring bug never reached it.
  - The rescore changed `efa_loadings_k5_final.csv` only by flipping Populist Conservatism's sign; every magnitude matches the old file to 6 decimals.
  - Rerunning `matched_efa.py` moves each φ by 0.003 or less and changes no replication label. Populist Conservatism prints −0.766 instead of 0.768 (the sign flip). `bootstrap_phi.py` takes |φ|; `independent_efa.py` reads only ANES.
- Clustering benchmark (cd1d300, `anes/outputs/clustering/`) is **stale**: it labels CES respondents with the ten-party typology. Its finding (only NAT survives a majority of n=3,796 subsamples, 57%) needs a nine-party rerun.
- **The ANES polychoric is not reproducible run to run.** `weighted_polychoric` in `analysis/efa/previous_years/common/efa_math.py` calls `scipy.stats.multivariate_normal(...).cdf` without a seed, and that CDF is a randomized quasi-Monte Carlo integral. Two back-to-back `matched_efa.py` runs differ in 144 of 153 pairs, by up to 0.0125 (Dreamers × same-sex marriage). The committed outputs were restored; nothing on disk changed.
- Team-module scan done: `ces_team_modules_scan.md` (all 46 modules released 2026-10-05).

## Waiting on the researcher
- Party copy rewrite (main app, not this workstream): researcher's voice, numbers in a separate review column, for `viz/src/constants/parties.ts` and `viz/src/components/shared/PartyProfileCard.tsx`. Drafts: `analysis/efa/exploration/k9_profiles/proposed_copy.json`.
- Merge: `bd-corrected-scoring` and `bd-nine-parties` are pushed, not merged to `main`. Merging deploys the nine-party site.

## Next steps
1. Make the polychoric deterministic: pass `seed=42` to `multivariate_normal` in `efa_math.py:weighted_polychoric` (or use an exact bivariate-normal CDF). The module is shared with `analysis/efa/previous_years/`, so rerun those outputs too and report what moves. Then rerun `matched_efa.py` and `bootstrap_phi.py` once and commit.
2. Rerun `python3 analysis/validation/anes/matched_clustering.py` against the nine-party typology (writes `anes/outputs/clustering/`). Take party labels from `pipeline/party_codes.py`, not a ten-party map.
3. Workstream 2 of `UNTRACKED/plans/ces_anes_gss_validation_plan.md`: CES→ANES classifier on `exact`/`close` crosswalk items, recall gate 0.5, shrinkage on held-out CES; writes `analysis/validation/classifier_report_anes.md`.

## Running
- Viz dev server: port 5199, `cd viz && npm run dev -- --port 5199 --strictPort` (not needed for ANES work).

## Don't redo
- Don't rerun the matched or independent EFA to "update for the rescore"; the check above shows the CES inputs didn't change beyond the Populist Conservatism sign.
- Don't edit the matched crosswalk; it is frozen by design (DECISIONS 2026-10-27). Items without a clean analog stay omitted, including `CC24_424`.
- Trust and election-fairness items stay in the independent pool; spending battery and thermometers stay out (DECISIONS 2026-10-27).
- ANES data is `UNTRACKED/anes_timeseries_2024_csv_20250808/` (not committed). Splice `V241382`+`V241383` and `V241439`+`V241440`; weights/PSU/strata `V240108a/c/d`.
- `data/bootstrap_cache/` holds the nine-party re-clustering fits (gitignored); don't delete it unless the typology changes again.

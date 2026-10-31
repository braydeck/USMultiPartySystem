# NEXT: validation (ANES / GSS / CES team modules)   (updated 2026-10-30 after the exact polychoric and nine-party clustering benchmark)

## Where it stands
- Matched crosswalk frozen (`anes/config/anes_matched_crosswalk.csv`, af017de); independent pool in `anes/config/anes_independent_pool.csv`.
- Matched EFA, PSU bootstrap of φ, and independent EFA (2aa5c6c, `anes/outputs/`): Institutional Distrust φ 0.96, Religious Traditionalism 0.92, Populist Conservatism splits, Security & Order mostly a spending-format factor, parallel analysis k=3 in both surveys. **These still stand after the rescore** (checked 2026-10-30):
  - The production loadings come from `data/processed/polychoric_matrix.csv` (`analysis/efa/pipeline/efa_update.py:172`), unchanged since May. That matrix is label-coded with church "Don't know" as missing (`efa_pipeline_v4.py:55`), so the scoring bug never reached it.
  - The rescore changed `efa_loadings_k5_final.csv` only by flipping Populist Conservatism's sign; every magnitude matches the old file to 6 decimals.
  - Rerunning `matched_efa.py` moves each φ by 0.003 or less and changes no replication label. Populist Conservatism prints −0.766 instead of 0.768 (the sign flip). `bootstrap_phi.py` takes |φ|; `independent_efa.py` reads only ANES.
- Polychoric is now exact and deterministic (`efa_math.bvn_cdf`, Owen's T). The earlier "not reproducible" finding held only under the system Python's scipy 1.16; the `.venv` (scipy 1.17) was already exact, so `matched_efa.py` and `bootstrap_phi.py` reproduce their committed outputs except Populist Conservatism's sign. `previous_years/` was not rerun: under the `.venv` its numbers cannot move.
- Clustering benchmark rerun at nine parties (`anes/outputs/clustering/`, log in `matched_clustering.log`). On the 18 matched items at ANES's n = 3,796, no party survives a majority of 100 CES subsamples; NAT is highest at 31%. With all 24 items NAT reaches 46%. At full CES n a fresh 24-item fit recovers 8 of 9 (DAL splits); on 18 items only NAT survives. So ANES clusters cannot be read as CES parties, which is the case for the classifier.
- Team-module scan done: `ces_team_modules_scan.md` (all 46 modules released 2026-10-05).

## Waiting on the researcher
- Party copy rewrite (main app, not this workstream): researcher's voice, numbers in a separate review column, for `viz/src/constants/parties.ts` and `viz/src/components/shared/PartyProfileCard.tsx`. Drafts: `analysis/efa/exploration/k9_profiles/proposed_copy.json`.
- Merge: `bd-corrected-scoring` and `bd-nine-parties` are pushed, not merged to `main`. Merging deploys the nine-party site.

## Next steps
1. Workstream 2 of `UNTRACKED/plans/ces_anes_gss_validation_plan.md`: CES→ANES classifier on `exact`/`close` crosswalk items, nine-party posterior target (the plan's "10-cluster" predates the rebuild), recall gate 0.5, shrinkage on held-out CES; writes `analysis/validation/classifier_report_anes.md`. Re-measure which parties fail recall rather than assuming STY and LBR, a ten-party expectation.

## Running
- Viz dev server: port 5199, `cd viz && npm run dev -- --port 5199 --strictPort` (not needed for ANES work).

## Don't redo
- Don't rerun the matched or independent EFA to "update for the rescore"; the check above shows the CES inputs didn't change beyond the Populist Conservatism sign.
- Don't edit the matched crosswalk; it is frozen by design (DECISIONS 2026-10-27). Items without a clean analog stay omitted, including `CC24_424`.
- Trust and election-fairness items stay in the independent pool; spending battery and thermometers stay out (DECISIONS 2026-10-27).
- ANES data is `UNTRACKED/anes_timeseries_2024_csv_20250808/` (not committed). Splice `V241382`+`V241383` and `V241439`+`V241440`; weights/PSU/strata `V240108a/c/d`.
- `data/bootstrap_cache/` holds the nine-party re-clustering fits (gitignored); don't delete it unless the typology changes again.

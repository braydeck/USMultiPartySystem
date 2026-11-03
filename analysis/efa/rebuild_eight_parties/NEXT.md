# NEXT: Rebuild production on the rescored cap-8 typology   (brief written 2026-11-02 by the listwise_check session)

## Goal
Replace the nine-party production typology with the eight-party one the listwise check found more stable: same
24 items, loadings re-estimated on all 49,432 post-weighted respondents, each respondent scored on the items
they answered, DPGMM cap 8. Everything downstream (elections, bootstraps, app payloads, copy) rebuilds on it.

## Why now (what the spawning session found)
- Ruling: `analysis/efa/exploration/listwise_check/DECISIONS.md` 2026-11-02. Evidence: `listwise_check/findings.md`.
- Cap 8 on the rescored scores: 19 of 20 seeds reach one solution, resample ARI 0.77, worst party PRG dissolves in 28% of resamples (`listwise_check/outputs/kscan/`). Its eight parties are production minus CUP; CON absorbs most of CUP.
- Reference code (exploration, not production): `listwise_check/rescore_refit.py` (pairwise matrix, `available_scores()`, residual lines over all eligible), `listwise_check/reestimate_loadings.py` (`align()` to production factor order and sign). Cached pairwise matrix: `listwise_check/outputs/polychoric_pairwise.csv`.

## Owns and returns
- Writes `analysis/efa/pipeline/efa_update.py`, `analysis/efa/pipeline/dpgmm_clustering.py`, `pipeline/`, `data/processed/`, `data/outputs/`, `viz/`, CLAUDE.md invariants, docs. Must not write `analysis/validation/` (ANES session) or `listwise_check/` (closed except its NEXT.md pointer).
- Branch `bd-nine-parties` is shared with the ANES session: `git add` explicit paths. Consider a new branch for the rebuild.

## Waiting on the researcher
- Party names and codes after CUP's slot empties (slot 6 stays reserved, as slot 7 did for OAO).
- Whether DAL and LBR keep their names: at cap 8 LBR's cluster is 72% LBR / 17% DAL and DAL's is 94% DAL.

## Next steps
1. `efa_update.py`: build the 24-item matrix pairwise on all post-weighted respondents (`efa_math.polychoric_matrix` handles NaN pairwise), keep the sign/anchor logic, score by available items (per-item available mean/SD, Thomson per missing-data pattern), residual lines over all scored. Output 49,428 rows with `caseid`.
2. `dpgmm_clustering.py`: cap 8, same seed/modal-solution selection. Party IDs via `party_id_reference.csv` match on the 45,214 who have one; the 4,214 new respondents have no reference row.
3. **Trap 4 breaks.** `typology_cluster_assignments.csv` joins the DTA positionally behind the `ITEMS_24` notna mask. Under available scoring that mask is wrong. Consumers applying it: `pipeline/candidate_vote_model.py`, `build_current_party_profiles.py`, `build_single_race_data.py`, `make_voter_counties.py`, `add_compare_items.py`, `compute_intensity.py`, `pure_only/compute_turnout_propensity.py`. Add `caseid` to the typology file and switch every consumer to a caseid join, with an assert, before rebuilding.
4. `python3 pipeline/rebuild_from_typology.py` (plan), then `--run`; delete `data/bootstrap_cache/` first. Then `check_stale.py`, the three build scripts (CLAUDE.md trap 7) and `npm test` in `viz/`.
5. Re-measure the Senate split cutoff (`SPLIT_THRESHOLD_PP`, CLAUDE.md trap 8). Update CLAUDE.md invariants (45,214 → 49,428; 9 → 8 parties), `docs/EFA_FACTORS.md`, `docs/METHODOLOGY.md`, app copy that says nine.

## Don't redo
- The cap choice and the no-new-items call are ruled. Don't rescan caps unless the production code's scores differ from `listwise_check/outputs/rescore_scores.csv` (regenerate it with `rescore_refit.py`; correlation with it should be ~1).
- Use `.venv/bin/python` for anything building a polychoric (scipy 1.17 exact CDF).

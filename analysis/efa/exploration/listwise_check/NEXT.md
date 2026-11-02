# NEXT: CES listwise check   (written 2026-11-02 by the ANES session that scored the CES listwise-dropped respondents)

## Goal
Decide whether the CES typology should score respondents on the items they answered (as ANES now does) at the next production rebuild. The question for the researcher: do the factor loadings, and then the nine parties, survive re-estimation on everyone with a post-election weight instead of the listwise sample?

## Why now (what the spawning session found)
- 49,432 respondents have `commonpostweight`; production keeps the 45,214 who answered all 24 items and drops 4,218. 3,786 of those 4,218 skip exactly one item: abortion weeks `CC24_325` (38% of the dropped), `CC24_440b` (14%), church attendance `pew_churatd` (14%) (`outputs/run.log`).
- Scored with the frozen production loadings on the items they answered, the dropped are more religious (Religious Traditionalism +0.48 SD [0.43–0.53]) and higher on Populist Conservatism (+0.25), Security & Order (+0.22) and Institutional Distrust (+0.15). They don't differ on Government Distrust (−0.02). They are more religious inside every party, by +0.09 (PRG) to +0.43 (CUP) (`outputs/factor_gap.csv`).
- Adding them moves no party's share by more than 0.8 pp. The four least religious parties (LBR, DAL, DSA, PRG) shrink (`outputs/party_shares.csv`).
- A DPGMM refit on all 49,432, run with the production procedure but frozen loadings, matches production at ARI 0.97 (other seed solutions differ from production at 0.65–0.75). Each party keeps 96–100% of its members and centers move ≤ 0.04 SD (`outputs/refit_parties.csv`, `outputs/refit_run.log`).
- Not yet tested: re-estimating the loadings themselves. That is this workstream's step 1.
- ANES precedent: `analysis/validation/DECISIONS.md` 2026-11-02 (available-item scoring replaces the cull; items define factors, missingness never removes an item). ANES code that does this: `available_scores()` and the `--available` branch of `analysis/validation/anes/independent_clustering.py:80,155`.

## Owns and returns
- Writes only `analysis/efa/exploration/listwise_check/` (scripts, `outputs/`, this NEXT.md, a new `DECISIONS.md` here for CES rulings).
- Must not write `data/processed/`, `pipeline/`, `viz/`, or anything under `analysis/validation/` (the ANES session owns it). Adopting the change is a typology rebuild (`pipeline/rebuild_from_typology.py`), and the researcher decides that. This session doesn't run it.
- Same working tree and branch (`bd-nine-parties`) as the ANES session: commit with explicit `git add <your paths>`, never `git add -A`.
- Result lands in `outputs/` plus a short `findings.md` here, read back by the researcher.

## Waiting on the researcher
- After step 3: adopt available-item scoring for CES at the next rebuild, or record listwise deletion as a known limitation. Log the ruling in this folder's `DECISIONS.md` and in memory.

## Next steps
1. Loadings: write `reestimate_loadings.py`. Production's matrix (`data/processed/polychoric_matrix.csv`) was built by `analysis/efa/pipeline/efa_pipeline_v4.py` on its own listwise sample (26 vars, line 159), then cut to 24 by `efa_update.py:172`. First reproduce that matrix with `analysis/efa/previous_years/common/efa_math.polychoric_matrix` on the listwise sample, so any later difference comes from the sample and not the code. Then build it pairwise on all 49,432, fit 5 factors with `efa_update.paf` + `oblimin`, and compare to `efa_loadings_k5_final.csv`: one-to-one Tucker φ (`common/clustering.match_factors`), largest loading changes, and parallel analysis k.
2. Rescore everyone on their answered items with the new loadings (Thomson per missing-data pattern, as `available_scoring.py` does, but with B from the new R and loadings). Refit the residual lines on FS_F1. Rerun the 20-seed DPGMM procedure (`refit_with_dropped.py` `fit()`).
3. Compare to production on factor φ, party membership (ARI, per-party Jaccard, kept share), party shares, and factor centers. Describe parties by factor profile, not party ID (memory `describe-on-factors-not-party`). Write `findings.md`.

## Don't redo
- The frozen-loadings check (steps above under Why now) is done and committed. Don't rerun it except to confirm code changes reproduce `outputs/party_shares.csv`.
- Use `.venv/bin/python` (scipy 1.17, exact polychoric). System Python's scipy 1.16 makes the polychoric random.
- `typology_cluster_assignments.csv` joins positionally (CLAUDE.md trap 4). `available_scoring.score()` already asserts the join.

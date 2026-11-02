# NEXT: CES listwise check   (written 2026-11-02 by the session that re-estimated the loadings and refit the parties)

## Where it stands
- Frozen-loadings check (done earlier): the 4,218 listwise-dropped respondents are more religious (+0.48 SD), but adding them moves no party's share by more than 0.8 pp; refit ARI 0.97 against production (`outputs/party_shares.csv`, `outputs/refit_parties.csv`).
- Loadings re-estimated on all 49,432 (`reestimate_loadings.py`, `outputs/reestimate_run.log`): all five factors φ ≥ 0.964 against production; loadings move up to 0.15, the same size as a 50-draw listwise bootstrap moves them (`outputs/loadings_bootstrap.csv`). Parallel analysis k = 4 on every matrix.
- Rescored on answered items and refit (`rescore_refit.py`, `outputs/rescore_parties.csv`): ARI 0.61 against production. CUP keeps 13% of its members; the other eight keep 64–99%.
- Decomposition (`rescore_refit.py --complete-only`, `outputs/rescore_parties_complete.csv`): the same loadings on only the 45,214 complete respondents give the same result (ARI 0.62, CUP keeps 13%). The loadings change, not the added respondents, dissolves CUP.
- Write-up: `findings.md`. Not yet read by the researcher.
- `outputs/rescore_scores[_complete].csv` (17 MB) are uncommitted; `rescore_refit.py` rebuilds them in seconds from the cached matrix and labels.

## Waiting on the researcher
- Read `findings.md`. Then rule: adopt available-item scoring for CES at the next rebuild, or record listwise deletion as a known limitation. The finding bears on a second question the original ask didn't: CUP depends on one draw of the loadings, and the production bootstrap (`analysis/bootstrap/recluster.py`) holds loadings fixed. Log rulings in a new `DECISIONS.md` in this folder and in memory.

- Cap for the rescored typology: 8 (most reproducible) or 9 (largest with no dissolved party). The two criteria agreed on production data and split here (`findings.md`).

## Next steps
1. If the researcher wants it: CUP survival across bootstrap loading draws. For each of the 50 draws in `outputs/loadings_bootstrap.csv` (rebuild the draw's loadings with the same seed-42 resampling in `reestimate_loadings.py`), score the 45,214 complete respondents, run the 20-seed DPGMM (`refit_with_dropped.fit`), and record each party's kept share against production. About 3 minutes per draw; run in the background.
2. Cap scan done (`k_scan.py`, `outputs/kscan/`, `findings.md` "How many parties"): cap 8 is the most reproducible (19 of 20 seeds, resample ARI 0.77, no CUP); cap 9 is the largest with no dissolved party (ninth party Jaccard 0.61). Researcher to pick the criterion. Run the loading-draw test (step 1) at both 8 and 9.
3. Larger CES item pool, as its own check after step 1 (proposed by the ANES session in conversation; not yet in any DECISIONS.md). Rule it proposed for both surveys: curate the item pool for construct reasons, never cull for missingness, handle missing answers at scoring. An earlier uncurated CES pool gave an unstable factor solution, so ANES's clean 99-item fit doesn't predict CES. With available-item scoring, extra items no longer cost respondents, so the 24-item set rests only on construct choices (party proxies out, domains balanced). Judge party changes against the loading-draw noise floor from step 1, and report per-party kept share and Jaccard, not just factor φ: a larger pool moves border voters even when the factors replicate.
4. After the ruling, adopting the change is a typology rebuild (`pipeline/rebuild_from_typology.py`). That is the researcher's call and outside this workstream.

## Don't redo
- The frozen-loadings check, the three polychoric matrices and the 50 bootstrap draws are cached in `outputs/`; delete a cache file only to rebuild it on purpose.
- Use `.venv/bin/python` (scipy 1.17, exact polychoric). System Python's scipy 1.16 makes the polychoric random.
- Writes only this folder. Must not write `data/processed/`, `pipeline/`, `viz/`, or `analysis/validation/` (the ANES session owns it). Same branch as the ANES session (`bd-nine-parties`): `git add` explicit paths, never `-A`.
- `typology_cluster_assignments.csv` joins positionally (CLAUDE.md trap 4); `rescore_refit.py` asserts the caseid order.

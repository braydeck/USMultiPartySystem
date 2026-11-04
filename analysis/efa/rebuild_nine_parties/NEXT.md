# NEXT: Rebuild production on the nine-party typology   (written 2026-11-04 by the listwise_check session, stage 1 done)

## Goal
Replace production's nine parties (24 items, 5 factors) with the nine of the revised §3c rule (41 items, 4 factors)
everywhere downstream: elections, bootstraps, quiz, app payloads, copy. Supersedes `../rebuild_eight_parties/`.

## Where it stands
- Rulings: `../exploration/listwise_check/DECISIONS.md` 2026-11-04 (nine adopted; residualization dropped; names;
  LBR = Labor; factor names; party order; short and long quiz).
- `data/processed/efa_factor_scores.csv` is new: 49,431 rows, columns pid3, ideo5, inputstate, commonpostweight,
  FS_RT, FS_TR, FS_SO, FS_PC, caseid (`analysis/efa/pipeline/efa_revised.py`; asserts r = 1 vs stage_c_v2).
- `data/processed/party_id_reference.csv` pins slots (`pin_party_ids.py`): CON 0, LBR 1, STY 2, NAT 3, (4 DAL empty),
  POP 5, CUP 6, OAO 7, DSA 8, PRG 9.
- `data/processed/typology_cluster_assignments.csv` is new (`dpgmm_clustering.py` on the 4 columns; fixed the
  zero-column crash for the empty slot). Same party as the reference for 100% of respondents. Written from `--seed 52`
  (the seed the full run chose); a full detached rerun refreshes `dpgmm_seed_selection.csv`
  (log `dpgmm_production_run.log`). Check its output equals the seed-52 file before relying on the table.
- Trap 4 fixed: `candidate_vote_model`, `build_current_party_profiles`, `make_voter_counties`,
  `build_single_race_data`, `compute_intensity`, `add_compare_items`, `pure_only/compute_turnout_propensity` join by
  caseid. Compiled, not yet run.
- Four factors in: `ballot_utils`, `run_house_stv`, `run_house_canonical`, `build_single_race_data`, `pure_only/`
  `{generate_pure_multi_ballots, run_pure_multi_house_stv, run_pure_multi_senate, generate_presidential_ballots_pure,
  run_senate_simulation_pure, run_senate_irv_pure}`. Compiled, not yet run.
- Quiz item ranking: `quiz_items.py` -> `quiz_items.csv` (greedy by mean factor R2, held-out half): 10 items R2 0.86
  / party agreement 0.67; 15: 0.92 / 0.72; 20: 0.95 / 0.78; 25: 0.97 / 0.83; all 41: 0.997 / 0.91.

- Rebuild run attempt (`rebuild_steps_4_11.log`, `data/outputs/rebuild_from_typology.log`): steps 4 (geography,
  turnout) and 6 (ballots) ran on 49,431 rows; step 7 stopped on the positional density-tier checkpoint, now fixed by
  `carry_density_tiers.py` (old tiers carried by caseid, 4,217 new respondents tiered the stv_step2 way). Not rerun.
- Blocker found: OAO gets no candidates. ~20 scripts hold static party lists that name DAL but not OAO (candidate
  lists, orders, colors): `pure_only/generate_pure_multi_ballots.py` (CANDIDATES), `run_house_stv`,
  `build_house_{partylist,reserve,mmp}`, `build_hex_{seat,mmp}_cartogram`, `build_single_race_data`,
  `build_cross_party_affinity`, `pure_only/{run_senate_simulation_pure, run_senate_irv_pure,
  generate_presidential_ballots_pure, run_presidential_primary_pure, run_party_*}`,
  `generate_factor_deviation_candidates`, `viz/scripts/{prepare_data, make_share_assets, make_og_image}`. Add OAO
  (slot 7) everywhere DAL appears, or read the live set from `party_codes`, then rerun from step 6.
- Quiz classifier (`quiz_classifier.py` -> `quiz_classifier.csv`): the DPGMM's own components with their weights
  place 96.6% at 41 items (current per-party Gaussians 91.3%), 79.5% at 20, 73.3% at 15. Adding the key's error to
  each component's covariance keeps placement and lowers the overconfident top-party probability (15 items: 0.64 vs
  0.83 with the current classifier, at 72-73% placement). Use components + key error in the quiz export.

## App key mapping (decided, keeps app churn low)
App keys F1 = FS_SO Security & Order, F2 = FS_TR Government Distrust, F4 = FS_RT Cultural Conservatism, F5 = FS_PC
Economic Conservatism; F3 retires (the app already hides it). Party order = Economic Conservatism, low to high:
DSA, PRG, OAO, LBR, CUP, STY, CON, NAT, POP (replaces `F5_ORDER` in `viz/src/constants/parties.ts`).

## Waiting on the researcher
- Descriptions: `party_descriptions.md` (being edited). OAO's color (the review
  page borrows DAL's azure). Overlap floor for `analysis/bootstrap/recluster.py` (proposed, not ruled).

## Next steps
1. Centroid chain: `pipeline/archive/generate_candidate_profiles.py` writes `candidate_factor_centroids.csv` with
   five `F*_...` columns; switch to F1/F2/F4/F5 per the mapping and update its readers (`candidate_vote_model`,
   `generate_factor_deviation_*`, `run_fd_*`, `senate_voting_blocs`, `build_cluster_spreads`, `prepare_data`).
2. App-facing builders: `build_current_party_profiles` (z_F*), `build_party_factor_ellipses`, `build_cluster_spreads`,
   `stv_affinity`, `viz/scripts/prepare_data.py`, `analysis/bootstrap/recluster.py` (cap 9 on the 4 columns).
3. Quiz (ruled, listwise_check `DECISIONS.md` "Quiz: short = 25 items"): short = first 25 items of `quiz_items.csv`,
   long = all 41. `viz/scripts/make_quiz_questions.py` writes `quizQuestions.json` / `quizShortform.json`: fit a linear
   key per version (intercept + item weights, WLS on FS_RT/TR/SO/PC, answers 0-1, skipped = neutral), and replace the
   per-party Gaussians in the `classify` block with the DPGMM's nine components (means, covariances, log mixing
   weights; refit seed 52 as `quiz_classifier.py` does, ARI 1 with production), each covariance + that key's
   residual covariance. `quizScoring.ts` then adds the log weight to each logit (it already does the Gaussian math).
   Expected placement 85.1% short / 96.6% long. Add an arrival chooser showing each version's item count.
4. `python3 pipeline/rebuild_from_typology.py --run` (delete `data/bootstrap_cache/` first), `check_stale.py`, the
   trap-7 builds, `npm test`, re-measure `SPLIT_THRESHOLD_PP`.
5. App: factor labels/poles/domains/`VAR_FACTOR`/`FACTOR_ITEMS`, party order, names (DAL gone, OAO back), colors,
   descriptions; CLAUDE.md invariants (49,431; 4 factors; the nine).

## Running (detached, survive restarts)
- Full `dpgmm_clustering.py` rerun to refresh `dpgmm_seed_selection.csv`: log `dpgmm_production_run.log`; its
  typology output must equal the seed-52 file (copy in this session's scratchpad was temporary; compare cluster
  columns by caseid with `party_id_reference.csv`, 100% same).
- Factor-redraw test on the nine (listwise_check `v2_draws.py 9`, `outputs/v2_draws_k9_run.log`); 34 of 50 draws:
  median ARI 0.84, no party under half in any draw. Report only; it gates nothing here.
- Review pages: `python -m http.server 8765` in `listwise_check/outputs/`, index `review_index.html`.

## Don't redo
- Cap, items, factors, names and the key mapping are ruled. Don't rescan caps or reselect items.
- `.venv/bin/python` for anything building a polychoric. Don't write `analysis/validation/` (ANES reads the old
  production files from git if it needs them; the researcher handles ANES).

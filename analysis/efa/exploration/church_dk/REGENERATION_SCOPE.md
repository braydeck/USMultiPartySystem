# Regeneration scope: dropping the 493 church-attendance "Don't know" rows

Scoped read-only on 2026-10-27 at commit 2aa5c6c. Nothing was regenerated. `python3 pipeline/check_stale.py`
(no flags) reports all 12 groups current, verified 2026-10-27T15:07:58Z at cfd5291.

Rebuilding the typology on 45,214 rows takes 19 ordered steps. About 3.5 hours of that is the
bootstrap. The two EFA scripts need path edits. Nine positional DTA readers need the same new mask
condition. Three inputs have no live writer. `check_stale.py --regenerate` covers only part of the
chain, and the stamp it writes would still mark every group verified.

## 0. Facts the plan rests on (measured, read-only)

- The 45,707-row sample holds 493 rows with `pew_churatd == 7` ("Don't know"). The value labels are
  1 = More than once a week ... 6 = Never, 7 = Don't know, 98/99 = skipped/not asked. These come from
  the DTA via `pyreadstat`, with the `ITEMS_24 + commonpostweight` notna mask from `pipeline/stv_config.py:67-76`.
- `efa_update.py` reads raw numeric codes (`convert_categoricals=False`, `analysis/efa/pipeline/efa_update.py:224`)
  and never recodes `pew_churatd`. Its listwise mask is notna only (`efa_update.py:291-293`), so code 7
  scores as one step past "Never".
- The polychoric matrix already excludes these rows. `efa_pipeline_v4.py:55-58` maps "Don't know" to NaN
  before the listwise mask at `:159`. Steps 1–2 of the EFA (`efa_pipeline_v4.py`, `run_efa.py`) therefore
  do not need to run. `efa_update.py` recomputes PAF + oblimin from that unchanged matrix (`:150-176`),
  so `efa_loadings_k5_final.csv` and `efa_phi_k5_final.csv` should come out identical. The factor scores
  still change for every row, because the weighted item means and SDs are recomputed on the new sample
  (`efa_update.py:303-312`).
- **Docs misattribute the gap.** `docs/EFA_FACTORS.md:303` says the exploration rerun's N = 45,214 comes from
  mapping "Not sure" on the government-trust items to the midpoint. That mapping affects 9,736 rows in the
  sample. The 493-row gap is the church "Don't know". The exploration scripts map it to NaN
  (`analysis/efa/exploration/compare_k4_vs_k5_clustering.py:46`) and map "Not sure" to 2, the same as production (`:43`).
- **Unclear, worth checking before the rebuild:** item direction for `pew_churatd`. The polychoric was
  built with Never = 1 (`efa_pipeline_v4.py:55-57`). `efa_update.py` scores the raw codes, where Never = 6.
  It checks direction empirically for CC24_303 (`:250-262`) but not for church attendance. I did not establish
  whether this flips the item's contribution to the scores.

## 1. The steps, in order

Paths are relative to the repo root. The env knobs are `TURNOUT_WEIGHT=1`, `TURNOUT_LAMBDA=0.05…0.30`
(`pipeline/pure_only/turnout_weights.py:27-31`) and `BALLOT_DEPTH=N` or `--depth=N`.

**Step 1. Edit before running anything (code changes, no outputs).**
- `analysis/efa/pipeline/efa_update.py:18-19`: `DATA_DIR`/`CES_PATH` point at `/Users/bdecker/Documents/STV/...`,
  which does not exist. A single `DATA_DIR` cannot serve this script, because its reads and writes live in
  four places:
  - reads `polychoric_matrix.csv` from `data/processed/` (`:150`)
  - reads `efa_loadings_k5.csv` from `analysis/efa/exploration/` (`:194`, `:489`; used only for printed comparisons)
  - reads the DTA at `data/raw/2024 CES Base/CCES24_Common_OUTPUT_vv_topost_final.dta` (`:19`)
  - writes `efa_factor_scores.csv` to `data/processed/` (`:596`)
  - writes `efa_loadings_k5_final.csv` and `efa_phi_k5_final.csv` to `analysis/efa/` (`:582`, `:587`)
  - writes `efa_cramersv_actual.csv` to `analysis/efa/exploration/` (`:611`)
  - The fix itself goes here: set `pew_churatd == 7` to NaN before `mask_complete` (`:291`).
- `analysis/efa/pipeline/dpgmm_clustering.py:29`: point `DATA_DIR` at `data/processed/`. It reads (`:40`) and
  writes (`:213`) only there.
- `analysis/efa/pipeline/cluster_profiles.py:25` (optional): same old path. Its outputs have no live consumer.
  The only copies are under `archive/clustering_old/`.
- The same `pew_churatd != 7` condition has to go into every script that rebuilds the row set from the DTA by
  position (Section 3, table A). `pipeline/stv_config.py:66-76` already holds the shared deletion items and is
  the natural single home for the condition. Today each of those scripts writes out its own mask.

**Step 2. `python3 analysis/efa/pipeline/efa_update.py`.** Writes `data/processed/efa_factor_scores.csv` (45,214 rows).

**Step 3. `python3 analysis/efa/pipeline/dpgmm_clustering.py`.** Writes `data/processed/typology_cluster_assignments.csv`.
Gate this before going on (Section 3, risks 1–2). Confirm 10 effective components and match the new clusters to
the old parties. `analysis/efa/exploration/cluster_survival_k4_k5.py` already does this matching for variants.

**Step 4. Per-respondent geography and turnout.**
- `python3 pipeline/make_voter_counties.py` writes `data/processed/voter_county_fips.csv`. Edit `EXPECTED_N`
  (`:22`) and the mask (`:39`) first.
- `python3 pipeline/pure_only/compute_turnout_propensity.py` writes `data/processed/turnout_propensity.csv`.
  Edit the mask at `:54` first.

**Step 5. Party centroid file: no live writer.** `data/outputs/candidate_factor_centroids.csv` is read by
`pipeline/candidate_vote_model.py:48`, `pipeline/build_single_race_data.py`, the crossover chain, and
`viz/scripts/prepare_data.py:1879`. Its only writer is `pipeline/archive/generate_candidate_profiles.py:244`.
That script's `BASE_DIR = Path(__file__).parent.parent` (`:26`) now resolves to `pipeline/` because the file
moved into `archive/`. `candidate_vote_model.py:154` asserts the centroids reconstruct within 0.05, so a stale
file fails loudly.

**Step 6. Ballots (base tree `pure_multi`).**
- `python3 pipeline/pure_only/generate_pure_multi_ballots.py` writes `pure_multi/presidential_ballots.csv` and
  `state_candidate_profiles.csv` (`:268-275`).
- `python3 pipeline/pure_only/generate_party_ballots.py` writes `pure_multi/party_ballots.csv`. That file feeds
  `houseTransfers.json` (`prepare_data.py:219`; CLAUDE.md trap 2).
- `state_pod_assignments.csv` is a fixed state-to-pod table (`run_presidential_primary_pure.py:85-104`). No
  rebuild is needed.

**Step 7. Canonical checkpoints: blocked as written.** `python3 pipeline/run_house_canonical.py` and `--triple`.
Each run reads `density_tier` from its own prior `ballots_checkpoint.parquet` and asserts that file has as
many rows as `efa` (`run_house_canonical.py:532-535`). Under the fix that is 45,707 vs 45,214, so the assert
fails. One of two things has to happen first:
- Subset the old checkpoints by the 493-row keep mask, in DTA order.
- Change the script to derive the tier without its own output.

Which one is a decision. `district_apportionment.csv` comes from state population alone (`:545`), so it should
not change.

**Step 8. Reserve checkpoints.** `python3 pipeline/build_reserve_checkpoints.py`. It reads `density_tier` from
the canonical checkpoint (`:57-60`) and the voter FIPS file, with no length assert. `draw_reserve_districts.py`
and `build_reserve_apportionment.py` read geography and apportionment only, so they need no rerun.

**Step 9. House STV trees.**
- `python3 pipeline/resync_district_map.py --run --stage 3 --jobs 10` runs all `pure_multi*` house trees,
  derived from the tree names on disk (`resync_district_map.py:88-110`).
- `python3 pipeline/run_reserve_stv.py` runs the 70 reserve trees.

**Step 10. Senate trees: no orchestrator.** Run `pipeline/pure_only/run_pure_multi_senate.py [--depth=N]`
(`:735-740`) under each turnout env. There are 24 `pure_multi*` senate trees on disk:
- the base tree
- 7 stops × {full, top3, top7}
- `_l50` and `_l75`

`build_senate_rank7.py` only reformats the `_top7` trees (`:19-23`). It does not simulate.

**Step 11. Primary, then presidential, then stage shares, per tree.** There are 38 `pure_multi*` trees with
`primary_results_2028.csv`: the base tree, 7 stops × {full, 3, 5, 7, 10}, and `_l50`/`_l75`. For each tree, run:
1. `pipeline/pure_only/run_pure_multi_primary.py`
2. `pipeline/pure_only/run_pure_multi_presidential.py`
3. `pipeline/compute_primary_state_shares.py`

Each takes `BALLOT_DEPTH` (`run_pure_multi_primary.py:294`, `run_pure_multi_presidential.py:199`,
`compute_primary_state_shares.py:140`). Presidential reads the primary's output.

**Step 12. Crossover chain (`?lab=crossover` only).** Run in this order:
1. `pipeline/generate_factor_deviation_candidates.py`, which reads the Step 5 file
2. `generate_factor_deviation_ballots.py`
3. `run_fd_house_stv.py` (16 trees), `run_fd_senate_simulation.py`, `run_fd_primary_2028.py`, `run_fd_irv_2028.py`

**Step 13. Profile tables.**
- `data/outputs/profiles/cluster_stats.csv` has no live base writer. Its writer is
  `pipeline/archive/cluster_profile_viz.py:1655-1658`, which has the same broken `BASE_DIR` (`:38`) and asserts
  `45_707` (`:681`).
- After that, run in this order:
  1. `pipeline/add_compare_items.py`, which appends to `cluster_stats.csv` (`:229-232`)
  2. `pipeline/build_current_party_profiles.py`
  3. `pipeline/compute_intensity.py`
  4. `pipeline/candidate_vote_model.py`

**Step 14. House payloads.** Run `pipeline/build_house_partylist.py`, then `pipeline/build_house_reserve.py`.

**Step 15. Bootstraps (about 2.9 h).** Run:
- `python3 analysis/bootstrap_uncertainty.py --draws 1000 --procs 12`
- `python3 analysis/bootstrap_partylist.py --draws 1000`
- `python3 analysis/bootstrap_population.py --draws 1000`

Trap 8 is satisfied as the code stands: `analysis/bootstrap/contests.py:27` uses `DEPTH = 7`, and
`build_senate_rank7.py` reads the `_top7` trees. `bootstrap_uncertainty.py:99-101` refuses to overwrite a
payload holding more draws unless given `--force`.

**Step 16. `python3 viz/scripts/prepare_data.py`.** It now chains `build_legislation_rank7.py` and
`build_senate_rank7.py` itself (`prepare_data.py:3640-3658`). CLAUDE.md trap 7 still says to run them after
it, which is now redundant but harmless. Read its log for `SKIP` lines (Section 3, risk 3).

**Step 17. Payloads downstream of prepare_data.** Order, following `check_stale.py:120-137` and
`resync_district_map.py:136-141`:
1. `pipeline/build_house_mmp.py`
2. `pipeline/build_house_rep_by_rank.py`
3. `pipeline/build_house_votemodel_depth.py`, `build_general_depth_bundle.py`, `build_primary_depth_bundle.py`
4. `pipeline/build_top_two_bundle.py`, which reads `houseStateMapTurnoutL5.json`
5. `pipeline/build_party_factor_ellipses.py`. Edit the `== 45707` assert at `:46` first.
6. `pipeline/build_cross_party_affinity.py`
7. `pipeline/build_single_race_data.py`. Edit `EXPECTED_N` (`:65`) and the mask (`:158`) first.
8. `analysis/quota_flows.py` and `analysis/quota_composition.py`, which read `housePartyList.json`
9. `viz/scripts/make_quiz_questions.py`, which reads `clusterProfiles.json` and `cluster_stats.csv`
10. `analysis/efa/build_quiz_shortform.py`. Its input `CCES24_Common_OUTPUT_vv_topost_final.csv` at the repo
    root (`:22`) is not on disk.
11. The hex cartograms: `build_hex_seat_cartogram.py` with no flag, `--triple`, `--reserve`, and
    `--reserve --triple`, then `build_hex_mmp_cartogram.py` with no flag and `--triple`.

**Step 18. Verify.** Run `npm test` in `viz/`, then `python3 pipeline/check_stale.py`, then the hand checks in Section 5.

**Step 19. Update reader-facing copy and docs** (Section 3, table C) and rewrite the CLAUDE.md invariants.

## 2. Dependents, grouped as `check_stale.py` groups them

The typology files are `SURVEY` (`pipeline/check_stale.py:47`). All 12 groups go stale. Ten list `SURVEY`
directly. The other two inherit it through viz JSON inputs:
- `hex cartograms` through `districtStvResults*.json` and `houseReserve.json` (`:89-100`)
- `mmp cartogram` through `houseMmp.json` (`:112-115`)

| Group (`check_stale.py`) | Script that rebuilds it | In `REGEN`? |
|---|---|---|
| house (party-line) `:59` | `run_pure_multi_house_stv.py` via resync stage 3 | yes `:121` |
| house (crossover) `:60-62` | `run_fd_house_stv.py` + FD ballots/candidates | **no** |
| house (reserve) `:63-69` | `run_reserve_stv.py` | yes `:123` (but not `build_reserve_checkpoints.py`) |
| senate `:70-72` | `run_pure_multi_senate.py` × 24 trees | **no** |
| primary `:73-76` | `run_pure_multi_primary.py` × 38 trees | **no** |
| presidential `:77-79` | `run_pure_multi_presidential.py` × 38 trees | **no** |
| ballots `:80` | `generate_pure_multi_ballots.py` | **no** |
| viz payloads `:81-84` | `prepare_data.py`, partylist, reserve, mmp, rank-7 builders | yes `:124-127` |
| hex cartograms `:89-100` | `build_hex_seat_cartogram.py` × 4 | yes `:129-133` |
| party factor ellipses `:101` | `build_party_factor_ellipses.py` | yes `:134` |
| representation by choice `:102-111` | `build_house_rep_by_rank.py` | yes `:128` |
| mmp cartogram `:112-115` | `build_hex_mmp_cartogram.py` × 2 | yes `:135-136` |

Direct readers of either typology file, from a grep of live `.py` files. The full list also includes
`pipeline/archive/`, `exploration/` and `previous_years/`.
- **Per-respondent intermediates:**
  - `pipeline/make_voter_counties.py`
  - `pipeline/pure_only/compute_turnout_propensity.py`
  - `pipeline/run_house_canonical.py`
  - `pipeline/build_reserve_checkpoints.py`
  - `pipeline/pure_only/generate_pure_multi_ballots.py`
  - `pipeline/pure_only/generate_party_ballots.py`
  - `pipeline/generate_factor_deviation_ballots.py`
- **Runners:**
  - `pipeline/pure_only/run_pure_multi_{house_stv,senate,primary,presidential}.py`
  - `pipeline/run_fd_{house_stv,senate_simulation,primary_2028,irv_2028}.py`
  - `pipeline/compute_primary_state_shares.py`
- **Payload builders:**
  - `viz/scripts/prepare_data.py`, which reads the files in 8 functions, among them `build_house_transfers` `:228`,
    `build_cluster_profiles` `:1018`, `build_current_party_profiles` `:1078` and `build_party_population` `:3293`
  - `pipeline/build_house_{partylist,reserve,mmp,rep_by_rank}.py`
  - `pipeline/build_party_factor_ellipses.py`
  - `pipeline/build_cross_party_affinity.py`
  - `pipeline/build_single_race_data.py`
  - `pipeline/candidate_vote_model.py`
  - `pipeline/compute_intensity.py`
  - `pipeline/build_current_party_profiles.py`
  - `pipeline/add_compare_items.py`
- **Analysis:**
  - `analysis/bootstrap/{contests,inject,selftest}.py`
  - `analysis/bootstrap_partylist.py`
  - `analysis/bootstrap_population.py`
  - `analysis/efa/build_quiz_shortform.py`
  - `analysis/ballot_model_diagnostic.py`
  - `analysis/instructive_ballot_wta_vs_prop.py`
- **Dead code, not displayed** (trap 2): `pipeline/pure_only/run_party_*.py`, `run_senate_*_pure.py`,
  `run_presidential_*_pure.py`.

## 3. Silent-breakage risks

The good news first: most positional joins are guarded by asserts. Each script in table A asserts its masked
DTA rows equal the typology rows, so a missed mask edit stops the build:
- `turnout_weights.py:50`
- `run_pure_multi_house_stv.py:365, :404`
- `run_fd_house_stv.py:191, :196`
- `build_house_partylist.py:173, :185`
- `build_house_reserve.py:135, :146`
- `build_house_mmp.py:147, :151`
- `build_house_rep_by_rank.py:118, :121`
- `analysis/bootstrap/inject.py:52`

The risks below are the ones that do not stop the build.

**Risk 1. Cluster IDs are reassigned by size, and party names are hard-coded by ID.** `dpgmm_clustering.py:115-116`
numbers clusters by descending weighted N. Today's weighted shares:

| Cluster | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|
| Share | 9.75% | 9.21% | 9.00% | 8.58% | 6.17% | 5.99% | 5.60% |

Neighbours sit 0.2–0.6 pp apart, so a refit can swap their order. 23 live files hard-code the ID-to-party map,
for example:
- `stv_config.py:18-29`
- `prepare_data.py`
- `build_house_partylist.py:59`
- `analysis/bootstrap/contests.py`
- `analysis/efa/build_quiz_shortform.py:33`
- `viz/src/tabs/LegislationTab.tsx:85`
- `viz/src/tabs/HouseTab.tsx:333, :358`

A swap would put party names on the wrong voters, and every build would still pass. CLAUDE.md's invariant
"OAO (cluster 7) and STY (cluster 2)" depends on the IDs too.

**Risk 2. Fewer than 10 effective clusters.** Only components with weight > 0.01 get `prob_cluster_k` columns
(`dpgmm_clustering.py:92, :106, :209-211`). Downstream code assumes 10 (`generate_pure_multi_ballots.py:46`,
`stv_config.py:30`). A lost component fails loudly with a KeyError. A changed component set that still totals
10 does not fail.

**Risk 3. `prepare_data.py` swallows every builder error.** `_run` catches all exceptions, prints `SKIP`, and
keeps the committed JSON (`prepare_data.py:3593-3600`). A builder that hits a row-count assert, or an input
pruned from this checkout, leaves the old 45,707-based payload in place, and the script still exits 0. It
already documents one such case: the native chamber-vote-model chain is pruned, so committed vote-model columns
are kept (`:3602-3605`). Those cannot be rebuilt from this checkout.

**Risk 4. `check_stale.py --regenerate` would stamp unrebuilt groups as verified.** `REGEN` (`:120-137`) runs
none of the following:
- the ballots, senate, primary, presidential or crossover runners
- `run_house_canonical.py` or `build_reserve_checkpoints.py`
- `make_voter_counties.py` or `compute_turnout_propensity.py`

But `regenerate()` writes the digests of all inputs into the stamp (`:199-207`). After the typology changes,
that marks the ballots, senate, primary, presidential and crossover groups `ok` while their trees still hold
45,707-row results.

**Risk 5. A stale `voter_county_fips.csv` would be silently truncated.** `assign_voters_to_districts_geo`
zips counties against `inputstates` (`run_house_canonical.py:395`). With 45,707 counties and 45,214 states,
the zip quietly drops the extra rows and every county lands on a shifted voter. `build_reserve_checkpoints.py`
has no length assert (`:45-80`), so a stale FIPS file plus a stale base checkpoint writes a 45,707-row
checkpoint without complaint. The runner's assert at `run_pure_multi_house_stv.py:365` catches it later.
Step 4 has to precede Steps 7–8.

**Table A: DTA readers that must get the new mask condition.** Each one reapplies the
`ITEMS_24 + commonpostweight` notna mask and joins by position (trap 4):

| Script | Mask | Guard |
|---|---|---|
| `pipeline/make_voter_counties.py` | `:39` | `EXPECTED_N = 45_707` `:22`, assert `:42` |
| `pipeline/build_single_race_data.py` | `:158` | `EXPECTED_N = 45_707` `:65`, asserts `:146`, `:160` |
| `pipeline/pure_only/compute_turnout_propensity.py` | `:54` | asserts `:60-66` |
| `pipeline/add_compare_items.py` | `:112` | assert `:115` |
| `pipeline/build_current_party_profiles.py` | `:188` | assert `:191` |
| `pipeline/candidate_vote_model.py` | `:111` | assert `:116` |
| `pipeline/compute_intensity.py` | `:60` | assert `:63` |
| `pipeline/archive/cluster_profile_viz.py` | `:678` | assert `== 45_707` `:681` |
| `analysis/efa/pipeline/efa_update.py` | `:292` | none (this is the fix) |

**Table B: other hard-coded 45,707 values.**
- `pipeline/build_party_factor_ellipses.py:46`: `assert ... == 45707`, which fails loudly.
- `analysis/bootstrap/inject.py:19`: `N_RESPONDENTS = 45707`. Nothing reads this constant. Its docstring (`:3`) is now stale.
- Comments only: `turnout_weights.py:43`, `run_presidential_primary_pure.py:672`, `generate_presidential_ballots_pure.py:11`,
  `dpgmm_clustering.py:6`, `cluster_profiles.py:6`, `add_compare_items.py:7`.
- Analysis-only:
  - `analysis/efa/previous_years/wave_2024/reproduce_gate.py:63`
  - `analysis/validation/anes/matched_clustering.py` (three places; untracked and in progress)
  - `analysis/validation/anes/matched_efa.py`
  - `analysis/validation/anes/bootstrap_phi.py`

**Table C: reader-facing copy and docs that would go stale without any error.**
- `viz/src/components/about/CaveatsSection.tsx:183` says "~45,700 respondents".
- `CLAUDE.md:27` says 45,707. The derived figures in trap 5 (34.2 / 18.8 / 13.2 / 9.6 / 7.9%, 69 seats) and the
  98.6% rank-1-to-3 mass would also move.
- `README.md` has 5 occurrences.
- `docs/METHODOLOGY.md:3, :10`
- `docs/EFA_FACTORS.md:6`, and `:303` with the wrong attribution noted in Section 0
- `comms/party_profiles.md:3, :646, :715`
- Generated JSON (`partyFactorEllipses.json` `nVoters`) refreshes itself on rebuild.

**Table D: `viz` tests pinned to the real payloads.** These fail loudly but will need rewriting:
- `viz/src/utils/quizScoring.test.ts:24` expects cluster `'5'` = POP. It reads `quizQuestions.json`.
- `viz/src/lib/senateDelegations.test.ts:56-65` pins the 10 contested states from `uncertaintyTurnoutL5.json`.

## 4. Typology-dependent outputs that `check_stale.py` does not cover

There are 23 of these. Inputs in `GROUPS` are listed below even when only the downstream result appears there.
"Not in REGEN" means no `--regenerate` step rebuilds the file.

| Output | Writer | Declared in GROUPS? |
|---|---|---|
| `data/processed/voter_county_fips.csv` | `make_voter_counties.py` | as input only (`:48`), not in REGEN |
| `data/processed/turnout_propensity.csv` | `compute_turnout_propensity.py` | as input only (`:50`), not in REGEN |
| `canonical{,_triple}/ballots_checkpoint.parquet` | `run_house_canonical.py` | as input only (`:51-54`), not in REGEN |
| `canonical{,_triple}_reserve/ballots_checkpoint.parquet` | `build_reserve_checkpoints.py` | as input only, not in REGEN |
| `pure_multi/party_ballots.csv` → `houseTransfers.json` | `generate_party_ballots.py` | no |
| `data/outputs/candidate_factor_centroids.csv` | archived only | no |
| `data/outputs/profiles/cluster_stats.csv` → `clusterProfiles.json`, `quizQuestions.json` | archived base + `add_compare_items.py` | no |
| `profiles/current_party_stats.csv`, `currentPartySpreads.json` | `build_current_party_profiles.py` | no |
| `clusterIntensity.json` | `compute_intensity.py` | no |
| `candidate_vote_model.csv` → `candidateVoteModel.json` | `candidate_vote_model.py` | no |
| `crossPartyAffinity.json` | `build_cross_party_affinity.py` | no |
| `singleRaceMeta.json`, `public/data/singleRaceVoters.json` | `build_single_race_data.py` | no |
| `uncertaintyTurnout{,L5…L30}.json` (7) | `analysis/bootstrap_uncertainty.py` | no |
| `partyListSeatRange.json` | `analysis/bootstrap_partylist.py` | no |
| `populationShareRange.json` | `analysis/bootstrap_population.py` | no |
| `public/data/quotaFlows.json`, `quotaComposition.json` | `analysis/quota_flows.py`, `quota_composition.py` | no |
| `public/data/topTwo.json` | `build_top_two_bundle.py` | no |
| `public/data/{houseVoteModelDepth,generalDepth,primaryDepth}.json` | the three depth builders | no |
| `quizShortform.json` | `analysis/efa/build_quiz_shortform.py` (input CSV missing) | no |
| `quizQuestions.json` | `viz/scripts/make_quiz_questions.py` | no |
| `houseVoteModel*`/`senateVoteModel*` native columns | pruned chain (`prepare_data.py:3602-3605`) | no; cannot rebuild |
| Senate / primary / presidential / crossover trees | per-office runners | as groups, not in REGEN |
| Analysis-only: `analysis/efa/exploration/*` explorers, `previous_years/`, `validation/anes/` | various | no; does not feed the app |

`clusterProfiles.json` is written by `prepare_data.py:1018`, which sits inside the declared "viz payloads"
group. It reads `cluster_stats.csv`, which nothing in REGEN rebuilds, so a rebuild would reformat stale
profile statistics.

## 5. Runtime and verification

The measured figures come from repo docstrings. The rest are not measured.
- `check_stale.py` fast check: ~1 s, measured today.
- House trees: ~4 s each. Stage 3 takes ~45 s at 10-way, ~5 min serial (`resync_district_map.py:61`).
- `--regenerate` subset: ~3–4 min (`check_stale.py:12`, `:230`).
- Bootstraps: 7 stops × 1,001 draws ≈ 2.9 h at 10 procs, ~2.6 h at 12 (`resync_district_map.py:59-63`).
  Per-draw cost is senate 3.3 s, primary 3.3 s, house 1.8 s (`:65`). On that basis the 24 senate and
  38 × 2 primary/presidential tree runs should take minutes in total. That is inferred, not measured.
- `efa_update.py`, `dpgmm_clustering.py` (`n_init=5`, `max_iter=500` on 45k × 5, `:55-62`), and the 9 DTA
  reads (each ~1 GB file): not measured.
- **Budget: about 3.5 h end to end**, dominated by Step 15, plus the manual work in Steps 1, 5, 7 and 13.

Verification, per CLAUDE.md traps 7–9:
1. `npm test` in `viz/`. Table D tests will fail by design and need new expected values.
2. `python3 pipeline/check_stale.py`. After a manual rebuild every `SURVEY` group reads STALE until a stamp is
   rewritten. Because of Risk 4, run `--regenerate` only as a reproducibility diff after Steps 1–17, never as
   the rebuild itself.
3. Grep the `prepare_data.py` log for `SKIP` (Risk 3).
4. Sum chamber totals out of the JSON: House 873 / 1,726, Senate 51, electors 975 (CLAUDE.md invariants).
5. Spot-check the party labels against old centroids in factor space (Risk 1).

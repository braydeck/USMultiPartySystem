# Spec: faster bootstrap draws

Status: proposed 2026-10-28, not started. Branch from whatever branch holds the nine-party
rebuild (`bd-nine-parties` at the time of writing).

## Goal

Cut the time of a re-clustering bootstrap run (1,000 draws × 7 turnout stops, plus 1,000 party
refits) from about 4 hours on the M4 Pro to about 1.5 hours, with every output unchanged byte for
byte.

## Where the time goes (measured)

One re-clustering draw at the default stop, profiled with cProfile on 2026-10-28
(`analysis.bootstrap.contests.run_draw(seed=43, lam=0.05, recluster=True)`), 12.5 s on one
core, measured while the full bootstrap was also running:

| Part | Seconds | What it is |
|---|---|---|
| Ballot generation, Senate | 1.8 | `run_pure_multi_senate.generate_ballots`, 102 calls (one per state per method), a Python loop over voters |
| Ballot generation, House | 1.0 | `run_pure_multi_house_stv.generate_ballots`, 300 calls, same per-voter loop |
| Ballot generation, presidential | ~1.5 | `generate_pure_multi_ballots.generate_ballots` inside `_recluster_inputs`, same loop over all 45,214 voters |
| CSV write + read of stand-in files | ~2.0 | `to_csv` 1.06 s and `read_csv` 0.91 s: the draw's typology, turnout, ballots and profiles go to temp CSVs and are read back through the patched `pd.read_csv` |
| STV counting, House | 1.1 | `run_stv`, 300 districts |
| Senate winnow + IRV + Ranked Pairs | ~1.5 | `winnow_stv`, `irv_rounds`, `build_matchups` |
| Primary | 1.85 | `run_pure_multi_primary.main`, four STV stages |
| Module import | 1.65 | once per worker process, not per draw |

Ballot generation and file round-trips take about 6 s of each draw. Counting takes about 4 s.
So the first win is not compiling the counting engine. It is removing the per-voter Python loops
and the temp files. (This corrects what the session that wrote this spec first said: that STV
counting dominated.)

The 1,000 party refits (DPGMM, n_init 5, about 65 s each on one core) run once per run and are
cached in `data/bootstrap_cache/recluster_k9/`. They are not part of this spec.

## Work, in order

Each phase ends with the full verification below before the next starts.

### Phase 1: vectorize ballot generation (expected: about 3.5 s off each draw)

All three `generate_ballots` functions do, per voter, `np.argsort(-scores[i])`, then reorder
each party's candidates into slate order inside the positions that party holds. Replace the loop
with array operations over all voters at once:

- `order = np.argsort(-scores, axis=1, kind="stable")`. Check the current tie-breaking first:
  `np.argsort` with the default quicksort is not stable, and same-party candidates have
  identical scores, so the per-voter loop's output for ties is whatever quicksort returned. The
  slate reorder that follows makes within-party order deterministic, but ties *across* parties
  (two parties with equal posterior, rare but possible) must reproduce exactly. If quicksort
  order differs from stable order on any real tie, keep quicksort.
- The within-party reorder becomes: for each multi-candidate party, take the positions its
  candidates occupy (a boolean mask over `order`), and write the party's candidate indices back
  into those positions in slate order. That is a per-party operation over the whole matrix, with
  one loop over at most ten parties instead of 45,214 voters.
- Keep the old function as `_generate_ballots_reference` in each module for one release, and
  assert equality on the real data in the verification step.

Files: `pipeline/pure_only/generate_pure_multi_ballots.py`, `run_pure_multi_senate.py`,
`run_pure_multi_house_stv.py`; check `generate_party_ballots.py` and the crossover
`generate_factor_deviation_ballots.py` for the same loop.

### Phase 2: pass draw inputs in memory, and build them once per draw (expected: about 2 s off each draw, plus 6/7 of the input prep)

- `inject.resampled_inputs` accepts file stand-ins today (`substitutes`). Add in-memory
  stand-ins: a dict of real path to DataFrame, returned (resampled where row-aligned) by the
  patched `read_csv` without touching disk. The draw's typology, turnout, ballots and state
  profiles never get written.
- The four inputs depend on the draw, not on the turnout stop. Today each of the 7 stops rebuilds
  them. Either (a) cache them per draw as compressed parquet in `data/bootstrap_cache/`, about
  5 MB per draw, 5 GB for 1,000, deleted after the run; or (b) restructure so one worker runs
  all 7 stops for a draw. (b) is blocked by `turnout_weights` reading `TURNOUT_LAMBDA` at import,
  one lambda per process (CLAUDE.md trap 8 area). Prefer (a) unless `turnout_weights` is
  refactored to take lambda as an argument, which would also remove the
  one-Pool-per-stop rule.

Files: `analysis/bootstrap/inject.py`, `analysis/bootstrap/contests.py`,
`analysis/bootstrap/recluster.py`, `analysis/bootstrap_uncertainty.py`.

### Phase 3 (only if still too slow): compile the counting loops with Numba

Targets, in order of measured cost: the primary's four STV stages, Senate `winnow_stv` +
`irv_rounds` + `build_matchups`, House `run_stv`. Each takes a ballot matrix (int8 candidate
indices), weights and an active set, and loops rounds of first-surviving-choice, tally, elect or
eliminate, transfer. Port the inner functions (`first_surviving_choice`, the tally, the
weighted-inclusive Gregory transfer) to `@njit` functions over plain arrays. Keep the Python
orchestration, the round logging the viz reads (`senate_irv_rounds.json`, House transfer
records) and the tie-break rules exactly as they are. Numba is a new dependency, so add it to
the requirements and confirm it installs on the deploy and CI machines first.

Floating point: the Gregory transfer sums weighted fractions. A compiled loop that sums in a
different order can change the last bits and flip a tie. Require byte-identical outputs; if a
port cannot reach that, keep the Python version for that function.

## Verification (every phase)

1. `python3 pipeline/check_stale.py --regenerate` reproduces every committed output byte for
   byte. CLAUDE.md trap 9 says verify an edit by running the unedited code, snapshotting, applying
   the edit, re-running and diffing the two. Do that rather than diffing against HEAD.
2. `python3 analysis/bootstrap/selftest.py` passes.
3. A 50-draw re-clustering bootstrap at stops 0 and 5, before and after, produces identical
   `uncertainty*.json` (same seeds, same cached fits).
4. `npm test` in `viz/` passes on the regenerated payloads.
5. Time a 100-draw run at one stop before and after, on an otherwise idle machine, and record the
   numbers in this file.

## Not in scope

- GPU (MPS/MLX). The counting is round-by-round branching logic and the clustering matrices are
  45,214 × 5; neither benefits, and scikit-learn has no Apple GPU support.
- Changing any modeling choice: ballot depth, slate rules, quota, tie-breaks, turnout model.
- The DPGMM refits. If they become the bottleneck, the lever is fewer `n_init` restarts per
  draw, which is a modeling choice for the user, not a speedup.

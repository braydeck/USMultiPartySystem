# Positional scoring + pure-only variant — session notes

Branch: `bd-positional-senate-scoring`

## Problem

The senate simulation was producing senators that looked too conservative
relative to the political makeup of their states. Two states that surfaced the
issue cleanly:

- **AZ** — Condorcet winner `POP/STY`, IRV winner `CON/NAT`. AZ has been
  a competitive state, and `CON/NAT` is the most conservative coalition the
  pipeline can generate.
- **CO** — Condorcet `POP/STY`, IRV `CON/POP`. CO went Harris +11 in 2024;
  a center-right senator does not match the state's political center of
  gravity.

The smoking gun was the IRV transfer behavior in CO: when `POP/STY` was
eliminated, **80% of its voters cascaded to `CON/POP`**, not to `SD` or `LIB`.
The "centrist" candidate's voter base was actually right-pole-displaced POP
voters whose first choice (pure POP) had been eliminated upstream in the STV
primary.

## Root cause

The scoring function for ballot generation was cluster-membership-based:

```python
score = w_primary * p(cluster_primary | voter) + w_secondary * p(cluster_secondary | voter)
```

Three structural pathologies fall out of this formulation:

1. **Pure candidates monopolize their cluster's first preferences.** With
   `w_primary = 1.0`, a pure-STY voter scores STY at 1.0 and every coalition
   candidate (SD/STY, POP/STY) at strictly lower than 0.5. Coalition candidates
   can never accumulate first-preference votes from their natural cluster
   base.
2. **Coalition candidates' bases are asymmetric.** A `POP/STY` candidate at
   `w_primary = 0.7` pulls POP voters' rankings about 2× harder than STY
   voters'. The candidate appears centrist but its support is 70%
   POP-aligned. When eliminated, transfers go right.
3. **Coalition candidates die early in STV.** They get crowded out of first
   preferences before they can absorb other clusters' transfers. SD/STY (CO),
   SD/LIB (CO), STY/SD (AZ) all eliminated at 0% first preferences in the
   senate STV primary.

## Fix: positional scoring

Replaced the cluster-membership formula with **Gaussian proximity in 5-D
factor space**:

```python
candidate_position = w_primary * centroid_primary + w_secondary * centroid_secondary
score              = exp(-‖voter_factor_scores - candidate_position‖² / (2 σ²))
```

with `σ = 1.5`. The candidate's `w_primary` now controls a literal *position*
in factor space (POP/STY at `w = 0.7` is 30% of the way from POP toward STY in
F1-F5 space) rather than a discount factor on cluster-membership probability.

Implications:
- Voter scores depend on factor-space distance, not cluster-membership
  affinity. Coalition candidates can compete for first preferences on
  proximity.
- Moving `w_primary` for a coalition candidate now literally moves the
  candidate's position. Moderation = moving toward the centroid of the voter
  mass. This matches the political-economy interpretation of "candidate
  moderates positions to win votes."

### Files modified

- `pipeline/run_senate_simulation.py` — replaced `score_candidates`;
  added `candidate_position`; added `POSITIONAL_SIGMA = 1.5` and
  `FACTOR_COLS`; threaded `voter_factors` through `run_state_election`.
- `pipeline/run_senate_irv.py` — same set of changes.
- `pipeline/generate_presidential_ballots.py` — replaced
  `compute_candidate_scores`; added `compute_cluster_centroids` and
  `candidate_position` (the presidential variant didn't previously compute
  centroids); threaded `voter_factors` through `main()`.

### Result deltas (mixed-candidate scenarios with positional scoring)

| State | Old Condorcet | New Condorcet | Old IRV | New IRV |
|---|---|---|---|---|
| AZ | POP/STY | STY | CON/NAT | STY/SD |
| CO | POP/STY | CON/SD (wildcard) | CON/POP | CON/SD |

National senate Condorcet: 16 different parties win seats. SD/STY 8, CON/SD 6,
CON/POP 6, SD 6, STY 5, CON/CUP 5, CON/STY 4 are the top tiers. Pure
candidates win 16 seats nationally; coalition candidates win 25; cross-aisle
wildcards win 10.

National presidential general (IRV): `CON/SD` 50.43% beat `CON/STY` 49.57%.
Winner flipped from prior `SD/CON` (51%) to `CON/SD` (50.4%). Both finalists
are now CON-led blends — voter median in CES factor space sits slightly right
of the SD–CON midpoint.

## Pure-only variant

Created a parallel pipeline that uses **only the 9 pure-cluster candidates**
(no co-occurrence straddlers, no cross-aisle wildcards). Same positional
scoring; just restricts the candidate field.

### New files

- `pipeline/pure_only/run_senate_simulation_pure.py`
- `pipeline/pure_only/run_senate_irv_pure.py`
- `pipeline/pure_only/generate_presidential_ballots_pure.py`
- `pipeline/pure_only/run_presidential_primary_pure.py`
- `pipeline/pure_only/run_presidential_irv_pure.py`

All outputs land in `data/outputs/pure_only/` (separate from the mixed-pipeline
outputs so neither overwrites the other). The senate scripts gate
`generate_state_candidates` to return after Step A (pure candidates only) and
drop the pure-threshold from 5% to 2% so every cluster with meaningful state
share competes. The presidential ballot generator keeps only the 9 pure
entries in `CANDIDATES`. The primary pod survivor targets were lowered from
12 → 10 → 8 → 5 to **8 → 7 → 6 → 5** to fit the 9-candidate field.

### Pure-only results

**Senate national composition (Condorcet):** SD 16, CUP 15, STY 10, CON 9,
POP 1. Five parties win seats; NAT, LIB, DSA, PRG win zero. **AZ:** CUP.
**CO:** STY. Both methods (Condorcet, IRV) agree on AZ and CO.

**Presidential general:** STY 50.54% beat CUP 49.46% in the final IRV round.
Round-by-round: LIB out first, then CON, then SD. STY wins as the spatial-
median pure cluster.

**Primary Ranked Pairs winner:** STY (same as general). Both election methods
converge on STY as the moderate compromise.

## Consolidation script

`pipeline/consolidate_results.py` aggregates the four senate scenarios + two
presidential scenarios + house STV results into two files in `results/`:

- **`results/state_results.csv`** — one row per state. Columns:
  `state_abbr`, `state_fips`, `senate_cond_mixed`, `senate_irv_mixed`,
  `senate_cond_pure`, `senate_irv_pure`, `pres_irv_mixed`, `pres_irv_pure`,
  and `house_<PARTY>` columns for each of the 9 cluster parties plus a
  `house_total_seats` count.
- **`results/national_composition.csv`** — long format
  (`office`, `scenario`, `party`, `value`, `metric`) covering:
  - senate seat counts under all 4 scenarios
  - house STV national seat counts
  - presidential general final-round percentages (winner + runner-up)
  - presidential primary Ranked Pairs finalist percentages

Run with `python3 pipeline/consolidate_results.py`.

## Things to watch

- **σ is a free parameter.** At `σ = 1.5`, pure presidential candidates cannot
  win nationally in the mixed pipeline — the spatial-median blend candidates
  dominate. Lowering σ would sharpen voter preferences and let polar
  candidates compete. The pure-only pipeline sidesteps this by removing the
  blends entirely.
- **The CES typology under-represents CO's partisan left-lean.** CO's
  cluster-share distribution reads as ~40R/40L/20moderate with `ideo_avg`
  3.00, even though CO votes ~55D/43R. Partisan attachment isn't captured in
  the factor space. Simulation results reflect ideological position, not
  partisan voting. This is a typology calibration issue, not a mechanics
  issue.
- **The wildcard candidate at `w = 0.55` is the spatial median.** When mixed-
  candidate scenarios produce a `CON/SD` or `SD/CON` winner, that's the
  candidate type designed to sit at the cross-aisle midpoint. Under
  proximity scoring it's a powerful Condorcet finalist.

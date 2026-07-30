# Sampling Uncertainty on Seat Counts — Design

## Intent

Every seat count in the app is reported as an exact number. They aren't. Bootstrapping
the senate showed the reported winner is reproduced in a median of only ~68% of resamples,
and in 14 of 51 Condorcet races the reported winner isn't even the modal outcome. Wyoming's
Populist seat — the case that started this — comes from the smallest sample of all 51 states
(N=70) and holds in just 27% of draws.

Put that uncertainty on the page: whiskers on the seat bars, the numbers behind an expander,
per-state stability on the senate map. Keep the methodology out of the simulation tabs and
in About → Caveats.

## Findings this is built on

From `analysis/ballot_model_diagnostic.py` work and the bootstrap probes on 2026-07-29/30
(200 draws, senate only):

- Condorcet: 20/51 states ≥90% stable, 13 at 50–70%, **14 below 50%**. Median 69%.
- IRV: 10/51 ≥90%, 19 at 50–70%, **8 below 50%**. Median 68%.
- Correlation with log(N) is only +0.29 (Condorcet) / +0.37 (IRV), so sample size explains
  part of it, not most.
- **IRV is markedly less stable than Condorcet, including in large states.** WA (N=1112):
  Condorcet LBR 100%, IRV LIB 39%. NJ (N=1241): Condorcet 98%, IRV 51%. MN (N=811): 99.5%
  vs 51%. CT (N=465): 93% vs 30%. This is IRV's sequential elimination amplifying small
  vote differences into different elimination paths; Condorcet compares all pairs at once
  and avoids it. This is a *finding* about method choice, not only a caveat.

## Decisions (locked)

- **Headline stays the point estimate.** The deterministic run is one coherent chamber that
  sums correctly by construction (51 state winners ×2 = 102; 873 house seats). Bootstrap
  medians would not sum to chamber size and no state on the map would reconcile with the
  headline. Intervals annotate the headline; they never replace it.
- **Presentation: whiskers inline + expandable detail.** Whiskers on the existing seat and
  population-vs-seat bars so the range is visible without interaction; a one-line summary;
  the per-party interval table and per-state stability list behind an expander.
- **Scope: all four contests × all 7 turnout stops.** Senate (Condorcet + IRV), House STV,
  STV primary, President IRV. Intervals must stay correct as the participation slider moves.
- **Uncertainty source: respondent sampling only.** Candidate pools held fixed. Understates
  total uncertainty; stated as a limitation in Caveats.
- **1000 draws.** 200 gives usable stability probabilities but noisy 95% endpoints.
- **Methodology lives in About → Caveats.** Simulation tabs carry numbers and at most one
  short line. No bootstrap explanation, no percentile-vs-credible discussion, no
  non-summing explanation in the sim cards.
- **Call it a bootstrap percentile interval, not a credible interval.** The estimand is an
  election outcome — a complex nonlinear function of the data — so resampling is the right
  tool rather than a Beta-Binomial. Naming it accurately matters because the rest of
  Brayden's work uses "credible interval" for Bayesian intervals specifically.

## Resampling design

**Stratified within state**, preserving each state's N exactly. State is the practical
stratum: every contest here is state-based, and holding N fixed means `MIN_RESPONDENTS`
can never be violated mid-draw, so no draw can fail by dropping a state.

House districts nest within states via county FIPS, so district-level N varies across draws
as a consequence. That is correct: district composition is itself a sampled quantity.

Five per-respondent files are row-aligned at 45,707 rows and must be resampled with one
shared index vector:

| file | note |
| --- | --- |
| `data/processed/efa_factor_scores.csv` | factor scores, state, weights |
| `data/processed/typology_cluster_assignments.csv` | cluster posteriors |
| `data/processed/turnout_propensity.csv` | validated turnout |
| `data/processed/voter_county_fips.csv` | county → house district |
| `data/outputs/<tree>/presidential_ballots.csv` | `index_col=0`, one row per respondent |

Because the ballots file is row-aligned, resampling it is equivalent to regenerating ballots
from the resampled respondents, and far cheaper. The pipelines' own `len(efa) == len(typology)`
asserts become the safety net for alignment.

Draw `d` uses seed `42 + d`; the seed is recorded in the output so any draw is reproducible.
The pipelines' internal `default_rng(42)` is unrelated (and `generate_ballots` is
deterministic given scores), so there is no interaction.

## Harness — `analysis/bootstrap_uncertainty.py`

Per draw, in dependency order (president reads the primary's finalists):

| stage | cost |
| --- | --- |
| senate (Condorcet + IRV) | 4.4s |
| house STV, depth 7 | 1.0s |
| STV primary | 2.8s |
| president IRV | 0.5s |
| **total** | **~8.7s** |

1000 draws × 7 stops ÷ 12 cores ≈ 85 min wall clock.

Mechanism, reusing the pattern proven in `ballot_model_diagnostic.py`: patch `pd.read_csv`
to return the resampled frame for the five files above, redirect each pipeline's
`OUTPUT_DIR` to a per-worker temp dir, call the real `main()`, read the output CSVs. Nothing
canonical is written.

**Multiprocessing gotcha.** `turnout_weights` reads `TURNOUT_WEIGHT` / `TURNOUT_LAMBDA` at
*import* time, and macOS Python defaults to the `spawn` start method, so each worker
re-imports from scratch. The worker function must set `os.environ` and *then* import the
pipeline modules inside itself. Threads will not work: the pipelines carry module-level
`OUTPUT_DIR` globals, so isolation must be by process.

### Recorded per draw

- senate: `{fips: cond_winner}`, `{fips: irv_winner}`
- house: `{party: national_seats}`
- primary: the final surviving slate. The primary is a staged winnow
  (`Initial_Slate` → `After_Retail` → `After_Pod_A` → `After_Pod_C` → `After_Pod_BD`)
  ending in the 5 candidates who contest the general, not a nominee per party. Record the
  set of `candidate_code` with `status == 'surviving'` at the last winnowing point.
- president: `irv_winner`, `cond_winner`

## Output — `viz/src/data/uncertainty{Suffix}.json`

Suffixes match the existing `_build_turnout_variant` convention: `Turnout`,
`TurnoutL5` … `TurnoutL30`.

```json
{
  "nDraws": 1000,
  "seed": 42,
  "senate": {
    "cond": {
      "seats":   { "LBR": { "point": 22, "p50": 21, "lo": 15, "hi": 27 } },
      "states":  { "56": { "winner": "CON_1", "stability": 0.43 } },
      "coinFlips": 14
    },
    "irv": { "…": "same shape" }
  },
  "house":     { "seats": { "CON": { "point": 206, "p50": 203, "lo": 178, "hi": 228 } } },
  "primary":   { "slate": { "CON_1": 0.99, "STY_1": 0.86, "LIB_1": 0.61 },
                 "pointSlate": ["CON_1", "CUP_1", "LBR_1", "LIB_1", "STY_1"] },
  "president": { "irv": { "LBR": 0.87, "STY": 0.09 }, "cond": { "STY": 0.62 } }
}
```

`primary.slate` gives each candidate's probability of reaching the general-election slate;
`pointSlate` is the deterministic run's five, so the UI can mark which of them are shaky.

`point` is the deterministic run's value, carried alongside so components never have to
join across files. `coinFlips` counts states whose reported winner falls below 50%
stability. Summary statistics only — a few KB per stop, 7 files.

## prepare_data integration

The bootstrap is expensive and does not belong in the normal `prepare_data.py` flow. The
harness writes `uncertainty*.json` into `viz/src/data/` directly and `prepare_data.py`
leaves those files untouched, matching the existing "committed JSON we keep" pattern its
`_run` wrapper already relies on. Re-run the harness only when the pipeline's ballot or
turnout model changes.

## Components

### New: `components/shared/SeatWhisker.tsx`

A primitive, not a chart. Given `point`, `lo`, `hi` and the axis scale, renders a whisker
overlay positioned over an existing bar segment or row. Used by the senate composition card,
the house seat bars, and the population-vs-seat comparison. It draws nothing when the
interval is absent, so every consumer degrades gracefully if a stop lacks data.

### New: `components/shared/UncertaintyDetail.tsx`

Collapsed by default. Contains the per-party interval table (point, 95% interval) and the
per-state stability list sorted least-stable first, with the party pill for each. One short
header line only; the explanation lives in About.

### Modified

| file | change |
| --- | --- |
| `components/senate/SenateCompositionCard.tsx` | whiskers on the Condorcet/IRV bars; `UncertaintyDetail` below |
| `components/senate/SenateMap.tsx` | states below 50% stability get a diagonal-hatch overlay, keeping the winner's party colour readable underneath; the 50% threshold is named in the legend as "could flip on sampling" |
| `tabs/SenateTab.tsx` | import the stop-indexed uncertainty JSONs, pass to the cards |
| `tabs/HouseTab.tsx` | whiskers on seat bars and the population-vs-seat comparison |
| `tabs/PresidencyTab.tsx` / `PrimaryTab.tsx` | winner probability as a compact line |
| `tabs/AboutTab.tsx` | the methodology, in Caveats |

### Copy discipline in the simulation tabs

One short line per card maximum. For example, on the senate composition card: *"14 of 51
seats are close enough to flip on sampling alone."* Numbers and whiskers carry the rest.
No bootstrap explanation, no interval-arithmetic explanation.

### About → Caveats

A new card, "How precise are the seat counts?", extending the existing thread in the
"Stress-tested, not hand-picked" card (which already says which voter lands in which party
is a statistical estimate). It covers: what the resampling does; why it's a bootstrap
percentile interval rather than a credible interval; why per-party intervals don't sum to
chamber size; the IRV-vs-Condorcet stability difference as a substantive finding about
method choice; and the limitation that pools are held fixed so total uncertainty is
understated.

## Verification

Automated:

- Harness asserts every resampled frame is 45,707 rows and that per-state N matches the
  original exactly.
- `point` in each output JSON equals the committed deterministic seat counts. This is the
  key regression: if it drifts, the harness is resampling something it shouldn't.
- Failed-draw count is reported and must be 0 (stratified resampling guarantees it).
- `pnpm typecheck`, `pnpm lint`, `vitest` clean. Unit test `SeatWhisker` positioning and
  the absent-interval no-op path.

Manual, in the browser:

- Senate whiskers bracket the point estimate; the headline still sums to 102.
- Moving the participation slider updates intervals along with the seat counts.
- Wyoming reads as unstable on the map, and appears at the top of the stability list.
- House headline still sums to 873; population-vs-seat whiskers render at all depths.
- Crossover pipeline degrades gracefully (no intervals, no layout break), since the
  bootstrap covers the party-line path only.

## Out of scope

- Bootstrapping the Crossover (FD) pipeline.
- Candidate-pool resampling.
- CES replicate weights (not used; post-weights are applied to resampled rows).
- Re-running the ballot-model question — settled, see
  `2026-07-29-senate-coalition-irv-condorcet-design.md` and the ballot-model memory.

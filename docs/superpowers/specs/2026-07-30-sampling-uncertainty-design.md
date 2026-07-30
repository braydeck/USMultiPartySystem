# Sampling Uncertainty and Probabilistic Seat Counts — Design

## Intent

Every seat count in the app is reported as an exact number produced by one simulation run
on the observed CES sample. Those numbers are less certain than they look, and in a handful
of states the reported winner is not the likely one.

Wyoming is the case that surfaced it. The observed sample gives POP by 2.8pp. Resampling its
70 respondents 1000 times gives **CON 54%, POP 28%**. The reason is clean: POP and CON are
evenly matched head-to-head — each wins 59% of the time once they meet — but CON reaches the
final round 93% of the time and POP only 48%. POP won our sample because it survived to the
final round, which happens less than half the time.

This change moves the app from "here is the run" to "here is the likely outcome, with its
range," while keeping every drill-down internally consistent with the headline.

## Findings this rests on

Bootstrap probes, 2026-07-29/30, senate, at the app default stop (λ=0.05):

- Reported winner reproduced in a median of **68–69%** of resamples.
- Condorcet: 20/51 states ≥90% stable, **14 below 50%**. IRV: 10/51 ≥90%, **8 below 50%**.
- Correlation with log(N) only +0.29 (Condorcet) / +0.37 (IRV) — sample size explains part
  of it, not most.
- **IRV is markedly less stable than Condorcet, including at large N.** WA (N=1112):
  Condorcet LBR 100% vs IRV LIB 39%. NJ (1241): 98% vs 51%. MN (811): 99.5% vs 51%.
  CT (465): 93% vs 30%. Sequential elimination amplifies small vote differences into
  different elimination paths; Condorcet compares all pairs at once and avoids it. This is a
  substantive finding about method choice, not only a caveat.
- Deterministic and modal chambers differ in only **3 of 51 states (IRV)** and **6 (Condorcet)**:

```
IRV        observed:  CON 48  LBR 42  LIB 8  STY 2  POP 2
           modal:     CON 48  LBR 46  LIB 6  STY 2  POP 0
Condorcet  observed:  LBR 44  STY 26  CON 22  POP 8  CUP 2
           modal:     LBR 42  STY 28  CON 20  POP 8  CUP 4
```

So the probabilistic reading does not overturn the project's findings. It moves a few
marginal seats — exactly the ones that should never have read as certain.

## Decisions (locked)

- **Headline is the modal chamber.** Most likely winner in each state, doubled. Integers,
  sums to 102 by construction since it is still one winner per state. Ties broken toward the
  observed winner, so real data wins where the bootstrap is indifferent.
- **Expected seats is the whisker centre.** The mean of a party's seat count across draws.
  Sums to exactly the chamber size automatically, by linearity of expectation. In the
  single-winner senate this equals summing the party's win probabilities across states;
  for multi-seat house STV it is the mean seat count, which is the general form.
  Non-integer; reads as an estimate ("45.2 expected") alongside the modal integer.
- **Whisker ends are the 2.5th/97.5th percentiles** of that party's seat count across draws.
- **Bootstrap percentile interval, named as such.** Not a credible interval. The estimand is
  an election outcome — a nonlinear, discontinuous function of the data — so resampling is
  the right tool rather than a Beta-Binomial. Naming matters because the rest of Brayden's
  work reserves "credible interval" for Bayesian intervals. The Bayesian-bootstrap
  equivalence (Rubin 1981) is what licenses reading these frequencies as probabilities.
- **Detail views stay on the observed run wherever it agrees with the modal winner** (48/51
  states IRV, 45/51 Condorcet). Only disagreeing states get a substituted representative
  run, labelled as an example count.
- **Scope: all four contests × all 7 turnout stops.** Senate (Condorcet + IRV), House STV,
  STV primary, President IRV. 1000 draws.
- **Uncertainty source: respondent sampling only**, candidate pools fixed. Understates total
  uncertainty; stated in Caveats.
- **Methodology lives in About → Caveats.** Simulation tabs carry numbers, whiskers, and at
  most one short line each. No bootstrap explanation in the sim cards.

## Resampling design

**Stratified within state**, preserving each state's N exactly. State is the practical
stratum — every contest is state-based — and holding N fixed means `MIN_RESPONDENTS` can
never be violated, so no draw can fail by dropping a state. House district sizes vary across
draws as a consequence, which is correct: district composition is itself sampled.

Five per-respondent files are row-aligned at 45,707 rows and must share one resampled index:

| file | note |
| --- | --- |
| `data/processed/efa_factor_scores.csv` | factor scores, state, weights |
| `data/processed/typology_cluster_assignments.csv` | cluster posteriors |
| `data/processed/turnout_propensity.csv` | validated turnout |
| `data/processed/voter_county_fips.csv` | county → house district |
| `data/outputs/<tree>/presidential_ballots.csv` | `index_col=0`, one row per respondent |

Because the ballots file is row-aligned, resampling it is equivalent to regenerating ballots
and far cheaper. The pipelines' own `len(efa) == len(typology)` asserts are the safety net.

Draw `d` uses seed `42 + d`, recorded in the output. The pipelines' internal
`default_rng(42)` is unrelated — `generate_ballots` is deterministic given scores.

## Harness — `analysis/bootstrap_uncertainty.py`

Per draw, in dependency order (president reads the primary's finalists):
senate 4.4s → house STV depth-7 1.0s → primary 2.8s → president 0.5s ≈ **8.7s**.
1000 draws × 7 stops ÷ 12 cores ≈ **85 min**.

Mechanism, reusing the pattern proven in `ballot_model_diagnostic.py`: patch `pd.read_csv`
to return resampled frames for the five files, redirect each pipeline's `OUTPUT_DIR` to a
per-worker temp dir, call the real `main()`, read the output CSVs. Nothing canonical written.

**Multiprocessing gotcha.** `turnout_weights` reads `TURNOUT_WEIGHT`/`TURNOUT_LAMBDA` at
*import* time and macOS defaults to `spawn`, so each worker must set `os.environ` and *then*
import the pipeline modules inside itself. Threads will not work — the pipelines carry
module-level `OUTPUT_DIR` globals, so isolation must be by process.

### Recorded per draw

- senate: `{fips: cond_winner}`, `{fips: irv_winner}`, and per state the finalist slate and
  ordered elimination sequence (needed to pick representative runs)
- house: `{party: national_seats}`
- primary: the surviving slate at the final winnowing point (`After_Pod_BD`). The primary is
  a staged winnow, not a nominee-per-party contest.
- president: `irv_winner`, `cond_winner`

## Representative-run selection

For a state where the observed winner differs from the modal winner, pick one real draw that
produces the modal winner and is typical of such draws:

1. Among draws the modal winner wins, take the **most common finalist slate**.
2. Within that slate, take the **most common elimination order**.
3. Within that bucket, take the **medoid** — the draw whose round-1 vote vector is closest to
   the bucket mean.

Verified on Wyoming: slate `CON_1/CON_2/LBR_1/LIB_1/POP_1` covers 23% of CON wins; the order
`CON_2→LBR_1→POP_1` covers 35% of that slate; the resulting bucket is 8% of CON wins. The
medoid run:

```
R1: CON_1 42.7  LIB_1 25.4  POP_1 19.1  LBR_1 12.8  CON_2 0.0 ✕   (100.0)
R2: CON_1 42.7  LIB_1 25.4  POP_1 19.1  LBR_1 12.8 ✕              (100.0)
R3: CON_1 43.4  LIB_1 34.6  POP_1 22.0 ✕                           (100.0)
R4: CON_1 64.1  LIB_1 35.9                                          (100.0)
```

Every round sums to 100 — it is a real coherent count, not an average of incompatible paths.
Averaging across draws is **not** an option: round 3 cannot be averaged across draws that
eliminated different candidates in round 2, because the active sets differ, so tallies aren't
commensurable and transfers wouldn't sum.

It is also narratively consistent with the prediction: POP is eliminated in R3, which is what
happens 52% of the time. The observed run, where POP survives R3 and wins, is the minority
path.

The same substituted draw supplies that state's winnow card and head-to-head matrix, so a
switch state is internally consistent across all three of its views.

## Output — `viz/src/data/uncertainty{Suffix}.json`

Suffixes match `_build_turnout_variant`: `Turnout`, `TurnoutL5` … `TurnoutL30`.

```json
{
  "nDraws": 1000,
  "seed": 42,
  "senate": {
    "irv": {
      "seats": { "LBR": { "modal": 23, "expected": 22.6, "lo": 18, "hi": 27, "observed": 21 } },
      "states": {
        "56": {
          "observed": "POP_1", "modal": "CON_1", "pModal": 0.54, "substituted": true,
          "dist": { "CON": 0.54, "POP": 0.28, "LBR": 0.12, "CUP": 0.05 },
          "decomp": { "CON": { "slate": 1.00, "final": 0.93, "win": 0.54, "winIfFinal": 0.59 },
                      "POP": { "slate": 0.92, "final": 0.48, "win": 0.28, "winIfFinal": 0.59 } }
        }
      },
      "nSubstituted": 3, "nBelow50": 8
    },
    "cond": { "…": "same shape" }
  },
  "house":     { "seats": { "CON": { "modal": 203, "expected": 201.4, "lo": 178, "hi": 228, "observed": 206 } } },
  "primary":   { "slate": { "CON_1": 0.99, "STY_1": 0.86 }, "observedSlate": ["CON_1","CUP_1","LBR_1","LIB_1","STY_1"] },
  "president": { "irv": { "LBR": 0.87, "STY": 0.09 }, "cond": { "STY": 0.62 } }
}
```

`observed` is carried alongside so components never join across files, and so a regression
test can assert it still equals the committed deterministic counts. Summary statistics only —
a few KB per stop, 7 files.

Substituted runs are written into the existing `senateIrvRounds{Suffix}.json`,
`senateBuckets{Suffix}.json` and `senateCondorcet{Suffix}.json` for the affected states, with
a `"substituted": true` flag on those state entries so the UI can label them.

## Vote model

`build_senate_vote_model_wfp` (`prepare_data.py:3194`) derives per-party seat counts by
counting the composition CSVs and passes them to `_lf_prob_pass`. It needs only the seat
dict plus the presidential winner for veto logic — no re-simulation. So recomputing from the
modal chamber means substituting the modal seat counts and the modal president. Same for
`build_house_vote_model_wfp`. Cheap.

## Components

### New: `components/shared/SeatWhisker.tsx`

A primitive, not a chart. Given `modal`, `expected`, `lo`, `hi` and the axis scale, overlays
a whisker with a centre mark on an existing bar segment. Renders nothing when the interval is
absent, so consumers degrade gracefully if a stop lacks data.

### New: `components/shared/UncertaintyDetail.tsx`

Collapsed by default. Per-party table (modal, expected, 95% interval) and the per-state list
sorted by ascending confidence, with the decomposition table inline for states below 70%.

### Modified

| file | change |
| --- | --- |
| `components/senate/SenateCompositionCard.tsx` | headline becomes modal; whiskers on both bars; `UncertaintyDetail` below |
| `components/senate/SenateMap.tsx` | SVG diagonal-hatch `<pattern>` overlay on states below 50%, party colour readable underneath; win probability added to the existing hover tooltip; legend names the threshold. **No numeric label per state** — this is a geographic `geoAlbersUsa` projection, and the least stable states (WY, ND, VT, DC, RI) are exactly the ones with no room to draw text in |
| `components/senate/SenateCoalitionCard.tsx` | "example count producing the most likely winner" label on substituted states; decomposition table for states below 70% |
| `components/senate/SenateWinnowCard.tsx`, `SenateCondorcetView.tsx` | same substituted-state label |
| `tabs/SenateTab.tsx` | import stop-indexed uncertainty JSONs, thread to cards |
| `tabs/HouseTab.tsx` | modal headline; whiskers on seat bars and the population-vs-seat comparison |
| `tabs/PresidencyTab.tsx`, `PrimaryTab.tsx` | winner / slate probability as a compact line |
| `tabs/LegislationTab.tsx` | reads the modal-chamber vote model |
| `tabs/AboutTab.tsx` | methodology, in Caveats |

### Copy discipline

One short line per card. On the senate composition card: *"8 of 51 seats are close enough to
flip on sampling alone."* Numbers and whiskers carry the rest.

### About → Caveats

New card, "How precise are the seat counts?", extending the existing thread in
"Stress-tested, not hand-picked" (which already notes that which voter lands in which party
is a statistical estimate). Covers: what the resampling does; modal vs expected vs observed
and why the headline is modal; why it's a percentile not a credible interval; why per-party
intervals don't sum but modal and expected do; what a substituted example run is and where
it appears; the IRV-vs-Condorcet stability gap as a finding about method choice; and the
limitation that pools are fixed so total uncertainty is understated.

## Verification

Automated:

- Every resampled frame is 45,707 rows; per-state N matches the original exactly.
- `observed` in each output JSON equals the committed deterministic counts. Key regression:
  drift means the harness is resampling something it shouldn't.
- Modal chamber sums to 102 (senate) and 873 (house). Expected sums to the same within
  floating-point tolerance.
- Failed-draw count is 0 (guaranteed by stratified resampling).
- Every substituted state's stored rounds sum to 100% per round, and its final-round winner
  equals that state's modal winner.
- `pnpm typecheck`, `pnpm lint`, `vitest`. Unit tests for `SeatWhisker` positioning, the
  absent-interval no-op, and the expected-seats sum property.

Manual, in the browser:

- Wyoming shows CON, labelled as an example count, with the decomposition table.
- Senate headline sums to 102; whiskers bracket the modal value.
- Moving the participation slider updates intervals with the seat counts.
- House headline sums to 873; population-vs-seat whiskers render at all depths.
- Legislation tab's pass/veto outcomes reflect the modal chamber.
- Crossover pipeline degrades gracefully — no intervals, no layout break.

## Noted, not adopted

The geographic map is a poor fit for this particular signal: the low-confidence states are
the physically smallest, so hatching them is barely visible and a numeric label is
impossible. A grid cartogram (Brayden's stated preference elsewhere) would show it far
better. Left alone here because swapping the map is a separate change with its own design
questions, and quietly replacing it inside an uncertainty feature would be the wrong way to
make that call.

## Out of scope

- Bootstrapping the Crossover (FD) pipeline.
- Replacing `SenateMap` with a grid cartogram (see above).
- Candidate-pool resampling.
- CES replicate weights (post-weights applied to resampled rows).
- The ballot-model question — settled; see the ballot-model memory and
  `2026-07-29-senate-coalition-irv-condorcet-design.md`.

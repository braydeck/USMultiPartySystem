# EFA redundancy re-check — corrected polychoric screen

The earlier `redundant_pairs.csv` was produced by a buggy polychoric pass: it
inflated magnitudes (several pairs pushed above 0.70 that are really in the
0.50–0.66 range) and, at least in the racial-attitudes block, mixed reverse-coding
so one relationship carried the wrong sign. Those wrong numbers were cited as the
r-based justification for four DROP decisions, and they also hid four
retained-vs-retained pairs that genuinely exceed the stated 0.70 redundancy rule.

This note re-derives every screened pair from the **correct weighted polychoric
MLE** used in the production pipeline (`analysis/efa/pipeline/efa_pipeline_v4.py`,
lines ~217–255), cross-checked against the same function in
`archive/old_scripts/efa_pipeline_step4.py` (lines ~714–793). The two
implementations agree to four decimals on every spot-checked pair.

## Method

- **Correlation:** weighted polychoric / tetrachoric MLE (bivariate-normal
  cell-probability likelihood, weighted contingency table, probit thresholds).
- **Weight:** `commonpostweight`.
- **Sample:** listwise **per pair** — each `r` uses respondents complete on both
  items of that pair *and* with a non-missing `commonpostweight`. The last
  condition matters: `commonpostweight` is NaN for the 10,568 pre-survey-only
  respondents, so a pre-survey pair must drop them too, otherwise the weighted
  contingency table degenerates. (The v4 pipeline never hits this because it
  listwise-deletes the full all-post item set up front.)
- **Item universe:** the attitudinal/policy items plus government-trust and
  religion items in `efa_variable_list.csv` (36 items). Excludes the approval
  battery (`CC24_312*`), ideology self-placement (`CC24_330*`),
  multi-select/compositional items (`CC24_309d*`, `CC24_420*`), and vote items —
  none of those are screened for redundancy.
- **Recoding:** follows `efa_pipeline_v4.py` conventions (Support/Oppose →
  polarity, 5-point agree scales oriented so higher = more conservative). Items
  dropped before v4 (e.g. `pew_religimp`, `CC24_440a`, `CC24_441b`) use the
  identical direction rules from the archive recode block, so signs are on the
  common "higher = conservative" scale.
- Artifacts: corrected pairs in `redundant_pairs.csv` (|r| ≥ 0.60); full matrix
  in `polychoric_matrix_redundancy_screen.csv`; regeneration script
  `recompute_redundant_pairs.py`.

A note on the two hand spot-checks that were circulated earlier:
`CC24_341a×341b` was quoted as 0.49 and reproduces here as **0.538** (both
correct implementations agree); `CC24_440a×440b` was quoted as **−0.67** and
reproduces here as **+0.658** — same magnitude, opposite sign, because
`CC24_440a` ("white people have advantages") is reverse-coded so that
higher = conservative, matching `440b`. The pipeline's consistent-direction
convention makes this pair positive.

---

## (a) Every pair that previously justified a DROP — corrected |r| and verdict

For each item dropped on a **redundancy** basis, the table gives the number the
old justification stated, the corrected `r` against that same reference item, the
corrected **maximum |r| against any RETAINED item** (the number that actually
matters for a keep/drop call), and a verdict.

| Dropped item | Stated basis | Corrected r vs stated ref | Corrected max \|r\| vs any RETAINED item | Verdict |
|---|---|---|---|---|
| `pew_religimp` | churatd r = 0.82 | **0.80** (vs `pew_churatd`) | 0.80 (`pew_churatd`) | **CONFIRM** — stated number essentially correct; genuinely redundant with retained churatd. |
| `pew_bornagain` | religimp r = 0.77 | **0.77** (vs `pew_religimp`, itself dropped) | **0.615** (`pew_churatd`) | **FLAG-UNJUSTIFIED** — the 0.77 was measured against another *dropped* item. Its |r| with the RETAINED religion anchor (churatd) is 0.61, below 0.70. Real basis below. |
| `CC24_341b` | 341a r > 0.70 | **0.538** (vs `CC24_341a`) | **0.797** (`CC24_341c`) | **FLAG-UNJUSTIFIED (as stated), but drop defensible** — not redundant with 341a (0.54), but strongly redundant with the RETAINED item 341c (0.80). Correct the reference item, keep the drop. |
| `CC24_440a` | 440b r = 0.71 | **0.658** (vs `CC24_440b`) | **0.658** (`CC24_440b`) | **FLAG-UNJUSTIFIED** — real |r| is 0.66, below the 0.70 rule. Close, but the r > 0.70 claim is false. Real basis below. |
| `CC24_440d` | 440c r = 0.77 | **0.748** (vs `CC24_440c`) | 0.748 (`CC24_440c`) | **CONFIRM** — 0.75 vs the retained gender item 440c; genuinely redundant. |
| `CC24_324d` | "r > 0.79 with 6 items" | max **0.707** (vs `CC24_325`) | 0.707 (`CC24_325`) | **FLAG-UNJUSTIFIED** — no retained pair reaches 0.79; only one (abortion-weeks `CC24_325`) reaches 0.70, the rest sit 0.60–0.70. The "0.79 with 6 items" claim is a buggy-pass artifact. Drop is still defensible as a redundant abortion-direction item, but on true numbers. |
| `CC24_441a` | "collinearity vs Factor 1" (no numeric r) | — | **0.644** (`CC24_340f`) | **FLAG (never a redundancy claim)** — max |r| vs any retained item is 0.64; not a >0.70 redundancy case. Real basis below. |
| `CC24_441b` | "collinearity vs Factor 1" (no numeric r) | — | **0.637** (`CC24_340f`) | **FLAG (never a redundancy claim)** — max |r| vs any retained item is 0.64. Real basis below. |

---

## (b) RETAINED pairs that exceed the 0.70 redundancy rule

These four pairs are both-items-retained and have corrected |r| ≥ 0.70, i.e. they
violate the stated "drop one of any pair with r > 0.70" rule. They are kept
deliberately as **multiple indicators / factor anchors**, not oversights. Keeping
paired indicators inside a domain stabilises that factor's loading against
single-item measurement error; the redundancy rule is a screen against
*accidental* duplication, and these are intentional.

| Retained pair | Corrected r | Why kept |
|---|---|---|
| `CC24_323a` × `CC24_323d` | **+0.81** | Two immigration-legalization items (working-immigrant legal status; Dreamer pathway). Both anchor the immigration factor; dropping one thins the strongest cross-cutting domain. |
| `CC24_321d` × `CC24_321e` | **+0.76** | Increase-police vs decrease-police — the two poles of the policing item pair. Retained together as the policing anchor. |
| `CC24_421_1` × `CC24_421_2` | **+0.74** | National vs state/local election-fairness. Both define the election-legitimacy factor, which has no other indicators; dropping either would leave it single-item. |
| `CC24_323b` × `CC24_340f` | **+0.70** | Increase border patrols × deny asylum. Border-enforcement pair; retained as immigration-enforcement indicators. |

These violate the stated rule but are defensible as the intended
multiple-indicator design. If a stricter one-item-per-domain reading is wanted,
the lower-PID-R² member of each pair is the natural drop candidate — but that is
a human call, not made here.

---

## (c) The four flagged drops — corrected number and the real defensible reason

The verdicts above show the *stated* r-justification was wrong or referred to a
dropped item for these four. Each can still stay out, but the documentation must
rest on the true number and the true reason:

- **`CC24_341b`** (oppose raising the corporate tax) — corrected |r| vs `CC24_341a`
  is **0.54**, so the "redundant with 341a" line is false. But its |r| with the
  **retained** top-rate item `CC24_341c` is **0.80**. Real reason: it is redundant
  with a retained fiscal item (341c), so the fiscal factor keeps 341a + 341c + 341d
  and loses nothing by dropping 341b. Fix the cited reference from 341a to 341c.

- **`CC24_440a`** (disagree that white people have advantages) — corrected |r| vs
  the retained racial item `CC24_440b` is **0.66**, not > 0.70. Real reason: it is
  not a clean redundancy drop. If it stays out, the honest basis is (i) it is the
  most partisan item in the racial block (PID R² = 0.37, the highest of the 440/441
  set) and (ii) the racial-resentment content is already carried by the retained
  `CC24_440b`/`440c` at |r| = 0.66/lower. Frame it as "retain the lower-PID-R²
  racial indicators (440b, 440c); 440a adds partisan signal without new content,"
  not as "r > 0.70."

- **`CC24_441a` / `CC24_441b`** (the two racial-resentment items) — corrected max
  |r| against any *retained* item is only **0.64** (both peak against `CC24_340f`,
  deny-asylum), and they correlate **0.77** with *each other*. They were never a
  redundancy drop (the pipeline reason is "collinearity concern vs Factor 1," not
  an r > 0.70 pair). Real reason: they **thin the racial-resentment cluster** —
  keeping all of `440a/440b/440c/440d/441a/441b` would load a single
  racial-resentment sub-dimension so heavily it would dominate Factor 1 and crowd
  out the cross-cutting structure the EFA is designed to surface. The design keeps
  two racial indicators (`440b`, `440c`) as the anchor and drops `440a/440d/441a/441b`
  to prevent that over-weighting. That is a factor-balance decision on the retained
  pair 440b/440c, defensible on the true 0.60–0.77 within-cluster correlations, and
  it does not depend on any r > 0.70-vs-retained claim.

- **`pew_bornagain`** (born-again identity) — corrected |r| vs the **retained**
  religion anchor `pew_churatd` is **0.61**, below 0.70; the stated 0.77 was against
  `pew_religimp`, which is itself dropped. Real reason: the religion domain is
  represented in the final set by a single anchor, `pew_churatd` (church
  attendance), chosen for its low PID R² (0.066) and ordinal 6-point scale.
  `pew_bornagain` is a binary with a 67% modal category and correlates 0.61 with
  churatd, so it adds a coarse, partly redundant indicator to a domain that is
  intentionally represented by one clean item. Frame as "religion reduced to a
  single low-partisan anchor (churatd); bornagain is a coarser binary correlated
  0.61 with it," not "redundant with religimp at 0.77."

---

## Summary of what changed

- **Confirmed on true numbers:** `pew_religimp` (0.80 vs churatd), `CC24_440d`
  (0.75 vs 440c). These drops were correctly justified.
- **Justification was wrong, drop still defensible on corrected numbers:**
  `CC24_341b` (redundant with 341c at 0.80, not 341a), `CC24_324d` (max 0.71 vs
  325, not "0.79 with 6 items").
- **Justification was wrong, drop rests on a non-redundancy reason:**
  `CC24_440a` (0.66, kept out as most-partisan racial item), `pew_bornagain`
  (0.61 vs retained churatd), `CC24_441a`/`441b` (0.64 vs retained; racial-cluster
  balance).
- **Rule violations that are intentional and documented:** the four retained
  pairs above (0.70–0.81).

The KEEP/DROP columns in `efa_variable_list.csv` / `_v3.csv` were **not** changed;
this note and the corrected `redundant_pairs.csv` are the inputs for a human
keep/drop review.

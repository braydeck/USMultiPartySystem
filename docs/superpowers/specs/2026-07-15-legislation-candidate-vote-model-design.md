# Legislation Tab v2 — Candidate Vote Model

**Date:** 2026-07-15
**Status:** Design approved, pending spec review

## Goal

Make the Legislation tab show *who votes, who signs, and what becomes law*, so the parties
feel like tangible actors rather than abstract passage percentages. Four capabilities, all
in one view:

1. **Candidate vote depiction** — for each bill, how a representative candidate of each party
   would likely vote.
2. **Ideology-vs-stated divergence** — surface bills where a party's factor-predicted stance
   disagrees with its observed support (the non-circular "surprising vote" signal).
3. **Presidential sign/veto** — model what the winning party's president would sign or veto.
4. **Coalition / whip view** — which parties form the yes-coalition per bill, and which party
   is pivotal.

## What exists today (and what it is NOT)

The current Legislation tab does **pure observed-support aggregation**, with no factor space:

- For each bill, take each party's raw `% support` (empirical fraction of that cluster's
  constituents who answered yes), from `cluster_stats.csv` via `house_chamber_profile.csv`.
- Each seat is a Bernoulli trial with `p = party % support`.
- Sum over seats → Normal approximation → `P(pass) = P(yes ≥ majority)`
  (`pipeline/chamber_vote_model.py:94-114`).

It answers only: *given the seat composition and each party's observed support, how likely is
a floor majority?* No candidates, no president, no divergence.

`candidate_factor_centroids.csv` exists but is consumed by the primary/candidate-generation
pipeline, not by legislation.

## The circularity question (why this is not a relabel)

The candidate factor position is **the party's constituency mean** — a summary of the same
people whose bill answers produce the raw `% support`. Therefore:

- **Circular (excluded):** taking a party's `% support` on bill P and relabeling it as the
  candidate's vote probability. Same number, new costume.
- **Not circular (this design):** fit a logistic model of the vote on the 5 factors, then
  evaluate it at the party centroid. This uses only the variance the bill shares with the 5
  ideological dimensions and **discards the item-specific residual**. Because communality
  (`h2`) runs ≈ 0.15–0.72, much of each item's variance is *not* factor-explained, so the
  factor prediction genuinely disagrees with raw support on low-communality bills.

The **value is the contrast**: where factor-predicted diverges from observed = bills where a
party votes against what its own latent ideology predicts (cross-pressure, single-issue
quirks). That gap is new information.

## Modeling decisions (locked)

| Decision | Choice |
|---|---|
| Calibration | **Pure factor logit** — predict from the fitted 5-factor logit at the party centroid; divergence from observed is unforced. |
| Candidate per party | **Single representative candidate**, labeled by **party** (see naming rule below). |
| Within-party shakiness | **Spread band** from measured within-party factor dispersion (STY wide, PRG tight). Candidate-identity uncertainty only. |
| Enactment | Full chain: pass both chambers, then **sign OR 2/3 override**. |
| Layout | **Party × bill matrix** + president column + law verdict. |
| Columns | **10 pure parties only**: CON, LBR, STY, NAT, LIB, POP, CUP, OAO, DSA, PRG. |

### Naming rule (hard constraint)

**Never display candidate initials/codes** (`RH`, `MW`, `MRJ`, …) or the deprecated
**fusion labels** (`CON/CTR`, `CON_STY`, `SD_CON`, …) anywhere in the UI. All candidate
references use the **party label**. The `candidate_code` column stays an internal join key
only.

### Deprecated concepts — do not revive

- **Fusion candidates** (light-fusion rows in the centroids file): ignored completely.
- **FD (factor-deviation) candidates** (discrete hi/lo variant *people*): parked for the
  future. This design uses none of the FD candidate rows/files/labels.
- The spread band uses only the **raw within-party dispersion statistic** (how internally
  spread a cluster's members are). That statistic is a measured cousin of FD but is not the
  parked FD candidate concept.

## Data pipeline — `pipeline/candidate_vote_model.py` (new)

**Step 1 (implementation prerequisite):** resolve the respondent-level join. Assemble
`(F1–F5, cluster, CC24 yes/no, survey weight)` per respondent by reusing the existing
CC24→cluster merge that already builds `cluster_stats.csv`. The raw CES `.dta`
(`data/raw/2024 CES Base/CCES24_Common_OUTPUT_vv_topost_final.dta`) has every `CC24_` item
plus `caseid`; the 45,708-row factor/cluster table is `typology_cluster_assignments.csv`
(has `FS_F1..F5`, `cluster`, but no `caseid`). The exact key that links them must be
confirmed before fitting — this is the first task in the plan.

**Per bill:**

1. Fit `logit(P(yes)) = β0 + Σ βk·Fk` across all respondents, survey-weighted.
2. Evaluate at each party centroid (from `candidate_factor_centroids.csv`, pure parties) →
   party candidate `P(yes)`.
3. **Spread band:** propagate each party's within-party factor SD through the fitted logit
   (Monte-Carlo draws of the candidate's factor position, or delta method) → `[lo, hi]`.
4. **Divergence:** `Δ = observed_party_pct − factor_predicted_pct`; flag when `|Δ| ≥ 15` pts
   (tunable constant).
5. **President:** evaluate the logit at the winning party's centroid → `P(sign)`.

**Output:** `viz/src/data/candidateVoteModel*.json`, keyed by party label, one file per
turnout/scenario stop to match the existing `houseVoteModelTurnoutL*` pattern. Each bill
record carries, per party: `pYes`, `bandLo`, `bandHi`, `observedPct`, `delta`, `diverges`.

**Correctness guard:** within-party spread lives in the candidate depiction only. Chamber
passage math (`chamber_vote_model.py`) already integrates within-party spread empirically via
observed `% support` and is **unchanged** — no double-count.

## Enactment chain (computed in-app)

- `P(House)`, `P(Senate)` = existing sum-of-binomials at simple-majority threshold. Unchanged.
- `P(override)` = same binomials at a **2/3** threshold in **both** chambers.
- `P(sign)` = president logit (above).
- `P(law) = P(House) × P(Senate) × [P(sign) + (1 − P(sign)) × P(override)]`.

## UI — party × bill matrix (`viz/src/components/legislation/`)

- **Rows:** bills grouped by domain (~36 items). **Columns:** 10 party-label pills.
- **Cell:** center dot shaded by `P(yes)` + spread band; `⚠` mark where `diverges`.
- **Right side:** President column (sign/veto lean for winning party) + Law verdict (`P(law)`
  with existing Tossup 45–55 / Possibly 55–65 / Likely 65–80 / Clearly 80%+ bands).
- **Coalition / whip:** per row the yes-side parties are the visible coalition; mark the
  **pivotal party** (the one whose flip changes the majority). Emerges from the matrix; no
  separate panel.
- **Drill-in:** click a column → that party's predicted votes down all bills with divergences
  highlighted; click a row → the bill's floor + law chain.
- **Retained:** existing controls (Wyoming / Scenario / Senate method / participation slider)
  and the Condorcet-vs-IRV divergences panel.

## Copy

All labels/explanations in the user's public-writing voice (claim-first, mechanism-named,
sparse em-dashes). Divergence framed plainly — never "surprisingly" / "unlike X".

## Out of scope (explicit)

- Discrete FD variant candidates and fusion candidates.
- Item-residual uncertainty folded into the band (band = candidate-identity spread only).
- Blend/shrink calibration and item-intercept calibration (rejected in favor of pure logit).
- Changing the chamber passage math.

## Open constants to tune

- Divergence threshold: start `|Δ| ≥ 15` points.
- Band definition: candidate factor position drawn as `Normal(centroid, within-party SD)` per
  factor; number of MC draws (or delta-method) chosen for stable `[lo, hi]` at fit time.

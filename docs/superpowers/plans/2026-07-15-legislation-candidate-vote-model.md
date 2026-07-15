# Legislation Candidate Vote Model — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans to implement task-by-task. Steps use checkbox (`- [ ]`) syntax.
> **Testing note:** this repo has no pytest. Its convention is *assertion + spot-check validation inside the script itself* (see `pipeline/add_compare_items.py`, `pipeline/chamber_vote_model.py`). Frontend "tests" = `tsc --noEmit` + `vite build`. The plan follows that convention rather than inventing a pytest suite.

**Goal:** Turn the Legislation tab into a party × bill matrix showing each party's predicted candidate vote (from a per-bill 5-factor logit), the ideology-vs-observed divergence, the president's sign/veto, coalition/pivotal marking, and the full pass-both-chambers-then-sign-or-override law chain.

**Architecture:** A new Python script fits one weighted logistic regression per bill (yes/no on the 5 EFA factor scores), evaluates it at each pure-party centroid to get a candidate vote probability + within-party spread band, and records divergence from observed support. `prepare_data.py` emits this as JSON and adds a 2/3-threshold override probability alongside the existing pass probabilities. A new React matrix renders it; the law chain is computed in a TS helper.

**Tech stack:** Python (pandas, numpy, statsmodels GLM), React + TypeScript + Vite + Tailwind + shadcn/ui, existing project data pipeline.

---

## Key facts (verified during design)

- **Join:** load CES `.dta` with the 24 EFA-anchor items + `commonpostweight`, mask `notna().all()` on those, `reset_index(drop=True)` → row-aligned with `typology_cluster_assignments.csv` (N=45,707; `assert len(dc)==len(typo)`). Pattern proven in `pipeline/add_compare_items.py:104-110`.
- **Factor scores:** `data/processed/efa_factor_scores.csv` has raw `FS_F1..FS_F5` (same listwise order). Centroids in `candidate_factor_centroids.csv` are weighted cluster means of `FS_F1..F5`.
- **Binary recode:** standard CES support items → `1→1.0, 2→0.0, else NaN`. Non-standard items (spending 5-pt, categorical) follow `add_compare_items.py`. **Every recode is validated** against `cluster_stats.csv` `% Supporting` `c0..c9`.
- **Bills:** 36 rows in `data/outputs/house_vote_model.csv` (`variable, domain, question`).
- **Parties (columns):** CON, LBR, STY, NAT, LIB, POP, CUP, OAO, DSA, PRG. Cluster map `{0:CON,1:LBR,2:STY,3:NAT,4:LIB,5:POP,6:CUP,7:OAO,8:DSA,9:PRG}`.
- **Naming:** never surface candidate initials or fusion labels; party labels only.
- **Override:** reuse the Normal-approx sum-of-binomials at a 2/3 threshold (mirror `_lf_prob_pass`).

---

## File structure

- **Create** `pipeline/candidate_vote_model.py` — fit per-bill logit, evaluate at centroids, emit `data/outputs/candidate_vote_model.csv` (+ `candidate_vote_params.csv`).
- **Modify** `viz/scripts/prepare_data.py` — new `build_candidate_vote_model()` → `candidateVoteModel.json`; extend house/senate vote-model builders with `probOverride` (2/3 threshold).
- **Modify** `viz/src/types.ts` (or wherever types live) — add `CandidateVoteRow`, `PartyVote`.
- **Create** `viz/src/lib/lawChain.ts` — pure functions for P(law).
- **Create** `viz/src/components/legislation/VoteMatrix.tsx` — the party × bill matrix.
- **Create** `viz/src/components/legislation/BillFloor.tsx` — row drill-in (floor + law chain).
- **Create** `viz/src/components/legislation/CandidateColumn.tsx` — column drill-in (a party's votes down all bills).
- **Modify** `viz/src/tabs/LegislationTab.tsx` — mount the matrix; keep controls + divergences panel.

---

## Task 1: Python — per-bill factor logit + validation

**Files:** Create `pipeline/candidate_vote_model.py`; outputs `data/outputs/candidate_vote_model.csv`, `data/outputs/candidate_vote_params.csv`.

- [ ] **Step 1: Assemble the aligned respondent frame.**
  - Load bills from `house_vote_model.csv`.
  - Load `.dta` columns = bills' raw variables + 24 anchors + `commonpostweight`; apply anchor NA mask; `reset_index`.
  - Load `efa_factor_scores.csv` (`FS_F1..F5`) and `typology_cluster_assignments.csv` (`cluster`); `assert` all three lengths equal.
- [ ] **Step 2: Recode each bill to binary y** using `1→1, 2→0, else NaN` (special-case any non-standard var exactly as `add_compare_items.py` does).
- [ ] **Step 3: Validation gate A — recode matches observed.** For each bill, weighted mean of y within each cluster must equal `cluster_stats.csv` `c0..c9` within ±0.6pp. `assert`, print any mismatch (variable + cluster + both values).
- [ ] **Step 4: Validation gate B — centroid reconstruction.** Weighted mean of `FS_F1..F5` per cluster must match `candidate_factor_centroids.csv` pure-party rows within ±0.02. `assert`.
- [ ] **Step 5: Fit weighted logit per bill.** `statsmodels.GLM(y, add_constant(F1..F5), family=Binomial(), freq_weights=w)` on rows with non-NaN y. Store coefficients in `candidate_vote_params.csv` (variable, intercept, b_F1..b_F5, n, pseudo_r2).
- [ ] **Step 6: Predict per party.** For each bill × party: `pYes = logistic(intercept + Σ b_k·centroid_k)`. `observedPct = cluster_stats c_k`. `delta = observedPct − pYes*100`. `diverges = abs(delta) >= 15`.
- [ ] **Step 7: Spread band.** Per party, per factor within-cluster weighted SD (`sqrt(Σ w (F-μ)² / Σ w)`). Draw 500 candidate positions `Normal(centroid_k, sd_k)` (seed fixed via `np.random.default_rng(20260715)`), push through the bill's logit, take p10/p90 → `bandLo/bandHi`.
- [ ] **Step 8: Emit** long CSV `candidate_vote_model.csv` (columns: `variable, domain, question, party, pYes, bandLo, bandHi, observedPct, delta, diverges`).
- [ ] **Step 9: Spot-check print.** For CC24_341a (tax cuts) and CC24_321c (background checks), print each party's `pYes` vs `observedPct` and flag divergences; sanity-check that near-universal items (321c) predict high everywhere.
- [ ] **Step 10: Run + commit.** `.venv/bin/python pipeline/candidate_vote_model.py` — expect both validation gates to pass and spot-checks to look sane. Commit.

## Task 2: prepare_data — JSON export + override probability

**Files:** Modify `viz/scripts/prepare_data.py`.

- [ ] **Step 1:** Add `build_candidate_vote_model()` reading `candidate_vote_model.csv`, grouping to one record per bill: `{variable, domain, question, parties: {CON:{pYes,bandLo,bandHi,observedPct,delta,diverges}, ...}}`. `write_json(..., "candidateVoteModel.json")`.
- [ ] **Step 2:** Add `_lf_prob_override(seat_counts, cluster_by_var, total_seats)` = `_lf_prob_pass` with `majority = ceil(2/3 * total_seats)`.
- [ ] **Step 3:** Extend `build_house_vote_model` / senate builder to also emit per-scenario `...ProbOverride` fields (same seat sets already computed there).
- [ ] **Step 4:** Register `build_candidate_vote_model` in the main run sequence.
- [ ] **Step 5: Run + verify.** `cd viz && python scripts/prepare_data.py` (or the documented invocation); confirm `viz/src/data/candidateVoteModel.json` exists with 36 bills × 10 parties and override fields present. Commit.

## Task 3: Types + law-chain helper

**Files:** Modify types file; create `viz/src/lib/lawChain.ts`.

- [ ] **Step 1:** Add `PartyVote { pYes; bandLo; bandHi; observedPct; delta; diverges }` and `CandidateVoteRow { variable; domain; question; parties: Record<string, PartyVote> }`.
- [ ] **Step 2:** `lawChain.ts`: `pLaw({pHouse, pSenate, pSign, pOverrideHouse, pOverrideSenate})` = `pHouse * pSenate * (pSign + (1-pSign) * pOverrideHouse * pOverrideSenate)`; plus `pivotalParty(parties, seatShares)` returning the party at which cumulative seat-weighted yes crosses the majority when parties are ordered by `pYes` descending.
- [ ] **Step 3:** `tsc --noEmit` passes. Commit.

## Task 4: VoteMatrix component

**Files:** Create `viz/src/components/legislation/VoteMatrix.tsx`.

- [ ] **Step 1:** Render rows = bills grouped by domain, columns = 10 party pills (reuse `PartyBadge`). Cell = center dot shaded by `pYes` (existing sequential scale, e.g. cividis) + a thin band from `bandLo..bandHi`; `⚠` when `diverges`.
- [ ] **Step 2:** Right side: President column = `pYes` of `presWinner` party rendered as sign/veto lean; Law column = `pLaw(...)` with existing verdict bands (Tossup/Possibly/Likely/Clearly).
- [ ] **Step 3:** Coalition/pivotal: mark the pivotal party's cell per row (outline) via `pivotalParty`.
- [ ] **Step 4:** Sidebar legend (vertical) explaining shade = P(yes), band = within-party spread, ⚠ = ideology-vs-stated divergence. Self-explanatory without tooltips.
- [ ] **Step 5:** `tsc --noEmit` + `vite build` pass. Commit.

## Task 5: Drill-ins + tab integration

**Files:** Create `BillFloor.tsx`, `CandidateColumn.tsx`; modify `LegislationTab.tsx`.

- [ ] **Step 1:** Row click → `BillFloor`: all parties as yes/no pills, the president's sign/veto, the four-factor law chain laid out (`P(House) × P(Senate) × [sign or override]`), divergence note.
- [ ] **Step 2:** Column click → `CandidateColumn`: that party's `pYes` down every bill, divergences highlighted, sorted by |delta|.
- [ ] **Step 3:** Mount `VoteMatrix` in `LegislationTab` above/below the existing `UnifiedBillTable`; keep controls + `LegislationDivergences`. Wire `presWinner` through.
- [ ] **Step 4:** `tsc --noEmit` + `vite build` pass. Commit.

## Task 6: Copy + polish

**Files:** `LegislationTab.tsx`, `VoteMatrix.tsx` strings.

- [ ] **Step 1:** Rewrite headings/explanations in the public-writing voice (claim-first, mechanism-named). State the divergence framing plainly — no "surprisingly"/"unlike X".
- [ ] **Step 2:** Final `vite build`; visual self-check of shading, bands, pivotal outline, law chain. Commit + push.

---

## Out of scope
Discrete FD variant candidates, fusion candidates, item-residual noise in the band, blend/intercept calibration, changing chamber passage math.

## Tunable constants
Divergence threshold `|Δ| ≥ 15`; band draws = 500, band = p10..p90; RNG seed `20260715`.

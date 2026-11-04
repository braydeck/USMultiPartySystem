# DECISIONS: CES listwise check

## 2026-11-02

- **Replace the production typology with the rescored cap-8 typology.** Pairwise polychoric loadings on
  all 49,432 post-weighted respondents, available-item scoring (49,428 eligible), DPGMM cap 8. Same 24
  items. Basis: at cap 8 every party reproduces in 19 of 20 seeds and the worst party (PRG) dissolves in
  28% of resamples; production cap 9 reproduces CUP, DAL and LBR in 11 of 20 seeds and PRG, DAL and CUP
  dissolve in 45%, 41% and 31% of resamples (`findings.md`). The rescored cap 9's ninth party dissolves in
  52% of resamples. Adoption is a production rebuild, handed to `analysis/efa/rebuild_eight_parties/`.
- **No items added.** The 24-item curation rests on construct reasons (`docs/EFA_ITEM_SELECTION_ROBUSTNESS.md`
  Stages A/B, `analysis/efa/efa_variable_list.csv`). A larger-pool test stays a separate later check (`NEXT.md`).
- **Congress approval (`CC24_312b`) is never eligible** (researcher). It is a horse-race measure of who
  holds power, not ideology. Its old drop reason in `efa_variable_list.csv` ("drag down N") was wrong and
  now gives the category reason; the rule is CLAUDE.md trap 0.
- **Loading-draw test is not a gate.** Production was never tested against loading draws either; cap 8
  beats production on the stability measures both were tested on.
- **The larger-pool test re-tests every hand drop; only Stage A category exclusions stay out** (researcher).
  Out by category: approvals (`CC24_312*`), ideology self-placement (`CC24_330a`), the economy
  retrospective (`CC24_301`, a Biden-approval proxy), multi-selects (`CC24_309d_8`; `CC24_420_*` stays out of the main test and enters the foreign-policy
  arm below). Back in,
  because they were dropped by judgment below the Stage B thresholds: `CC24_440a` (r 0.66 with a retained
  item, under the 0.70 redundancy cut), `CC24_441a` and `CC24_441b` (racial-resentment thinning),
  `pew_bornagain` (r 0.61, modal share 67%, under the 85% cut). Mechanical Stage B drops are re-decided by
  the rule as it runs.
- **Foreign policy gets its own arm of the larger-pool test, with and without the other re-tested items**
  (researcher). Multi-select batteries enter as individual binaries with the exclusive "none" box dropped,
  not as count scores: the intervention reasons split left/right among the 45,214 (oil supply NAT 30% vs
  PRG 4%; UN law PRG 78% vs NAT 11%). Ukraine and Gaza included even though partisan-coded. Financial
  fragility (`CC24_309d_8`) stays out as non-attitudinal.
- **Stage C picks the clustering dimensions** (`docs/EFA_ITEM_SELECTION_ROBUSTNESS.md` §3c, shared with ANES). Item
  choice (Stages A/B) and clustering-dimension choice are separate decisions; every threshold is fixed before results.
- **Entry-test minimum lowered from 3 clean items to 2** (researcher, after the first CES run). The two-battery
  requirement stays, so a two-item factor needs its items from different batteries. Two-item factors that pass are
  labeled as such. On production's 24, trust kept `CC24_421_1` and `CC24_424`; `421_2` left as a Heywood case
  (λ 1.02, near-duplicate of `421_1`) and `423` as a cross-loader (0.48 / 0.43).
- **Stage C tie rule: when parallel analysis and MAP disagree, fit the lower k** (researcher, after the first CES run).
  Replaces "fit both; a factor must pass in both at φ ≥ 0.85". At the higher (parallel-analysis) k, Populist
  Conservatism and Religious Traditionalism split into single-battery fragments that fail the entry test, so the
  both-fits rule left only Security & Order and Trust in the 69-item pool. CES results were seen first; ANES is the
  clean test. Under the lower-k rule: 69 pool, k 5 → S&O, RT, PC, Trust pass (contraception pair fails); 69 + checkbox,
  k 7 → the same four pass. The rerun after cross-loader removal gives PA 6 / MAP 3 (69 pool), disclosed.
- **State-trust sensitivity check, not a rule change** (researcher, 2026-11-03, after results were seen). The
  distrust dimension's clean items include state-government trust (`CC24_424`) and state election fairness
  (`CC24_421_2`), whose answers flip with which party carried the state (Trump voters distrusting their state
  government: 30% where Harris lost by 10+, 75% where she won by 10+; federal distrust 70% / 67%). C9 inherits that
  geography (state index 0.38 vs 0.11 by chance). These are the only CES trust or fairness items besides approvals.
  Two disclosed checks in `trust_sensitivity.py`: (a) Stage C without the two state items (`stage_c.py --pool
  pool69nat`): at MAP's k = 5 no distrust factor forms; it appears only at PA's k = 7 (`421_1` + `423`), so under the
  lower-k rule the space is S&O, RT, PC; (b) the reference space with distrust adjusted for alignment with the
  governor's party (pid3 kept as a control, only the alignment terms removed). The production typology stays the
  reference either way until the researcher rules.
- **State-control check through the whole chain** (researcher, 2026-11-03, after results were seen; not a rule
  change). `state_control.py`: respondents stratified by alignment with their 2024 state government (governor and
  both chambers, `analysis/efa/state_control_2024.csv`, 23 R / 17 D + DC / 10 divided, verified against Ballotpedia's
  pre-election count; governors match CES `CurrentGovParty`). Pooled within-stratum polychorics feed Stages B and C,
  only the alignment contrasts (opposed and split vs aligned, among partisans) are removed from the clustering
  scores, with nonpartisans' own difference kept (a first version removed it too: nonpartisans average +0.37 on
  distrust vs aligned partisans -0.34, 3.3 of the strata's 12.0 points of distrust variance; rerun), and the cap
  scan 2-10 reruns. The governor-only arm of `trust_sensitivity.py` is superseded: its pid3 and alignment terms are
  collinear among partisans, so it also removed part of the partisan-vs-independent difference. Party ID is not a stratum, so the
  left-right covariance stays; the control removes only being in or out of power in one's state.
- **Alignment-only adjustment on the unchanged four-dimension space** (researcher, 2026-11-03, after results were
  seen; not a rule change). `four_dim_aligned.py` separates the two changes mixed in `state_control.py` (pooled
  correlations reshaped RT and PC; ARI vs the reference ten 0.38): the reference scores stay as they are and only the
  opposed and split contrasts are subtracted from distrust (nonpartisan difference kept), then the cap scan 2-10
  reruns under the unchanged §3c cap rule.
- **Economic sentiment out of every item pool** (researcher, 2026-11-03). Household income change (`CC24_302`) and
  price change (`CC24_303`) report the respondent's circumstances, not a policy or cultural view, and never enter a
  CES or ANES pool (ANES equivalents: personal and national economy retrospectives). Same category logic as approvals
  (CLAUDE.md trap 0). In the 69-item pool both were already dropped as weak at k = 5, so the current space is
  unaffected; the rule matters for any rerun.
- **Cross-loaders stay in** (researcher, 2026-11-03, after results were seen). §3c step 3's worst-first
  cross-loader removal is dropped: it removed 10 items at k = 5 (student debt, marriage recognition, "work their way
  up", infrastructure spending, ACA repeal, concealed carry, Roe, fossil fuel, pronoun consent, age verification),
  and its one-at-a-time order made 8 items flip on correlation changes under 0.06 (`state_control.py` vs
  `pool69`; same 30 items give Tucker phi >= 0.996 on both matrices). Production kept its cross-loaders. Cross-loading
  now matters only for the entry test's clean-item count. Item retention to be made robust to resampling; full
  re-evaluation of every item under the revised rule, both surveys. §3c rewrite pending the researcher's ruling on
  the remaining Stage C criticisms.
- **Why the lower factor count** (researcher, 2026-11-03). The researcher's prior, held independent of any cluster
  result: political attitude structure has a few broad dimensions (roughly 3-7), and at higher k the extra factors
  describe item sets (one battery, one wording family) rather than general attitudes. This is the substantive
  rationale for the lower-k tie rule and matches the two-battery entry test's purpose; it goes into the §3c rewrite.
  Outcome tests are still reported at both counts.
- **CES 2022 held back** (researcher, 2026-11-03). CES 2022 is reserved as the untouched confirmation run: no
  item-pool, Stage C or clustering work on 2022 until the 2024 rule is settled, then the fixed rule runs once.
- **§3c rewritten** (researcher, 2026-11-03). `docs/EFA_ITEM_SELECTION_ROBUSTNESS.md` §3c now has: economic
  sentiment out at Stage A; a party-blind redundancy tie-break (keep the member with the higher mean |r| with the
  pool); factor count = the lower of parallel analysis (uncapped) and MAP, bounded to 3-7 (added after ANES fit 17:
  past about 7 the factors restate item sets rather than measure general attitudes); cross-loaders kept; weak-item
  and redundancy steps resampled (50 draws, seed 42, retained if they survive in more than half); entry test
  resampled the same way (Tucker phi >= 0.85 matching); three declared outcome tests (held-out eta-squared, resample
  stability, CES-ANES phi). Stage B list item 4 and §3b updated to match. ANES session (stv-e5) told.
- **In-power effects in §3c** (researcher, 2026-11-03). New §3c step 7: items about a specific government stay in;
  every clustering score is adjusted for alignment with the respondent's 2024 state government (governor + both
  chambers; opposed and split contrasts removed among partisans, nonpartisan difference kept). Federal alignment is
  not adjustable in one cross-section (collinear with party ID) and is stated as a limit. `four_dim_aligned.py` is
  the CES test of the adjustment on the current space.
- **Redundancy tie-break direction reversed** (2026-11-03, before any result past Stage B). As first written the
  party-blind tie-break kept the member with the higher mean |r| with the pool. On CES that chained: the border wall
  (`CC24_323c`) absorbed 11 items across topics at |r| 0.71-0.74 (abortion access, white advantage, fossil fuels,
  Dreamers, ACA repeal, EPA, "work their way up", student debt, Roe), and religious importance absorbed the other
  three religion items, leaving 35 items. Keeping the lower-mean member (the one adding information the pool lacks)
  drops 17 items, as the old party-ID tie-break did, leaving 44; it differs from the old rule on three swaps (keeps
  legal status over Dreamers, national over state election fairness, "slavery and discrimination" over "work their
  way up"). §3c updated; the aborted run's outputs deleted.
- **Held-out test: domestic items primary** (researcher, 2026-11-03). The primary held-out measure is the domestic
  policy items outside every compared typology's inputs (7 under the revised rule); the foreign-policy checkboxes are
  reported separately, each question (troop use, Ukraine, Israel-Gaza) averaged as one so 21 boxes don't outweigh
  the domestic items 3:1. `heldout_domestic.py`, outputs `outputs/heldout_v2/domestic_*.csv`.
- **Revised ten adopted as the parties** (researcher, 2026-11-04). The cap-10 modal solution of the revised §3c rule
  (`outputs/stage_c_v2/labels.npz`, names in `outputs/profile_v2/names.csv`) replaces both production's nine and the
  ruled-but-unbuilt cap-8 rebuild. Evidence: held-out domestic eta-squared 0.170 vs 0.133 current ten, 0.130
  production (`heldout_domestic.py`); 19 of 20 seeds reach it; factor redraws median ARI 0.78, 13 of 50 draws with
  a cluster under half, 9 of them A.2 folding into A.1 (`v2_draws.py`). Alternatives ruled out: merging A.1 + A.2
  costs 0.016 held-out (`heldout_merge_a.py`); caps 7-9 each have 3-5 competing seed solutions and cap 9 does not
  converge even at 100 seeds (`cap9_seeds.py`). Unstable clusters (A.1, A.2, B.2, C.1) stay as parties; no separate
  A-family totals (researcher: revisit for coalition visualization). Rebuild pending; `analysis/bootstrap/recluster.py`
  is still cap 9 on the five production factors and its forced Hungarian match would relabel a party that fails to
  form in a draw.
- **Residualization check on CES** (2026-11-04, after ANES found it decides its cap 4 vs 5). Residualized scores are
  exact affine functions of plain scores (R2 = 1.0), so the full-covariance DPGMM with data-derived priors fits the
  same models and only the k-means starts differ. CES plain-score caps 5 and 10 reproduce the residualized ones (ARI
  0.989 at both; 19 of 20 seeds at cap 10; held-out domestic 0.1694 vs 0.1695; unstable 5 vs 4 at the 0.75 line).
  One plain-score seed (48) found a cap-10 solution with a better lower bound (-22,356 vs -22,455) that scores lower
  held-out (-0.0065) and has 3 dissolving clusters. `resid_check_ces.py`. Whether to drop residualization from §3c
  for both surveys is open.
- **Residualization dropped for CES** (researcher, 2026-11-04; ANES handled separately by the researcher).
  `stage_c_v2.py` and `v2_draws.py` no longer residualize RT and PC on SO; §3c updated with the disclosure line; the
  residualized run is kept in `outputs/stage_c_v2_residualized/`. Rerun: same 41 items and four factors; cap rule
  still 10; the ten match the residualized ten at ARI 0.989 and keep their names (98-100% overlap each). Unstable
  at the 0.75 line: A.1, A.2, B.2, C.1, C.2.
- **Correction: cap 9 converges on plain scores** (2026-11-04). The earlier finding that cap 9 has 4-5 competing
  solutions even at 100 seeds (`cap9_seeds.py`) came from the residualized scores' k-means starts. On plain scores
  17 of 20 seeds reach one cap-9 solution, the best-fitting one found (lower bound -22,676.5; ARI 0.959 with the
  best of the 100 residualized seeds); 8 of 9 clusters stable (B.2 at 0.75), resample ARI 0.749 vs 0.632 at cap 10.
  Held-out domestic: ten 0.1694, nine 0.1620, ten - nine +0.0074 [+0.0035, +0.0115]. The nine merge A.2 with the
  more conservative part of A.1 and A.1's remainder with C.1. Whether this changes the adoption of the ten is open.
- **Nine adopted as the parties** (researcher, 2026-11-04; replaces the same-day adoption of the ten). The cap-9
  modal solution on plain scores (`outputs/stage_c_v2/labels.npz`; 17 of 20 seeds; 8 of 9 clusters stable, B.2 at
  0.749) over the ten (5 of 10 unstable), accepting the ten's +0.0074 held-out domestic edge. Names in
  `outputs/profile_v2_k9/names.csv` (A-E families from the cap-5 solution, numbered by size), profile at
  `outputs/profile_nine/index.html`. Against the ten: nine A.1 = ten A.2 53% + A.1 46%; nine A.2 = ten C.1 59% +
  A.1 41%; nine C.1 = ten C.2 76% + C.1 17%; nine C.2 = ten C.3; B.1, B.2, D.1, D.2, E.1 carry over. Not yet run on
  the nine: the factor-redraw test.
- **Working names A-I for the nine** (researcher, 2026-11-04). Lettered in production order of each cluster's largest
  source party (`compare_typologies.py v2 9`, `outputs/compare_typologies_k9/letters.csv`): A CON-like, B NAT, C POP
  (B.2), D STY, E LBR, F and G mixed LBR/DAL/CUP/STY, H PRG, I DSA. Replace the A.1-E.1 labels on the nine's pages.
- **Names for the nine** (researcher, 2026-11-04). A = CON, B = NAT, C = POP, D = STY, E = Liberal, F = CUP (Civic
  Union; the name fits F's institutionalism, the old "religious, centrist on culture" description does not: F sits
  -0.79 on cultural conservatism), G = Order and Opportunity (OAO), H = PRG, I = DSA. LBR and DAL have no successor
  (E is closest to LBR, 0.62 SD on the four dimensions; DAL's members split across F, E, G, H). E's code and the ID
  slot assignments are for the rebuild (`analysis/efa/rebuild_nine_parties/NEXT.md`).
- **Liberal's code is LIB** (researcher, 2026-11-04). Every party description needs rewriting for the nine, CUP's first (it is not religious or centrist on culture).
- **Liberal's code is LBR, not LIB** (researcher, 2026-11-04, replacing the LIB entry above): avoids the pejorative; production's Labor party retires, so the code is free.
- **E is Labor (LBR); the Liberal label retires** (researcher, 2026-11-04, replacing the Liberal/LIB entries above). Draft descriptions for the nine: `analysis/efa/rebuild_nine_parties/party_descriptions.md` (researcher edits it; the rebuild copies it into `viz/src/constants/parties.ts`).
- **Factor names and party order for the app** (researcher, 2026-11-04). RT = Cultural Conservatism, TR = Government
  Distrust, SO = Security & Order, PC = Economic Conservatism. Parties are ordered left to right by Economic
  Conservatism (replaces production's F5_ORDER). Quiz: a short and a long version, the visitor chooses on arrival and
  sees each version's item count; short = the items that best explain the four factors, long = the most accurate.
- **Quiz: short = 25 items, model components** (researcher, 2026-11-04). Short version = the first 25 items of
  `analysis/efa/rebuild_nine_parties/quiz_items.csv` (held-out factor R2 0.97); long = all 41. Both classify with the
  DPGMM's own components and mixing weights, covariances widened by each key's residual covariance
  (`quiz_classifier.py`: 25 items place 85.1%, 41 items 96.6%, vs 83.4% / 91.3% with the old per-party Gaussians).

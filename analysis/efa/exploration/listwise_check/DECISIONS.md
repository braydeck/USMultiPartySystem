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

# Validation workstream decisions (ANES / GSS / CES team modules)

Plan: `UNTRACKED/plans/anes_replication_plan.md` (ANES design), `UNTRACKED/plans/ces_anes_gss_validation_plan.md` (full scope).

## 2026-10-27

- **ANES runs two EFAs: a matched one-to-one replication and an independent native EFA.** The matched
  crosswalk (one ANES item per CES typology item, recode rules, state-trust stand-in) is frozen and
  committed before any ANES correlation is computed. The independent pool uses the CES screening rules
  (partisan-proxy, modal-share, multi-select, r>0.7 redundancy) and parallel analysis picks k. The two
  solutions are bridged by correlating factor scores on the same ANES respondents, not by Tucker φ.
- **The independent pool includes the trust and election-fairness items** (`V241229`–`V241233`,
  `V241314`, `V241315`, `V242207`, `V242430`, CSES `V242417`–`V242423`). Institutional distrust is a
  core concept in the CES typology and in Echelon Insights' segmentation, so leaving out the domain ANES
  covers best would bias the exploratory test.
- **The independent pool excludes the federal spending battery and the feeling thermometers.** The
  cross-wave work showed that same-format spending items form a method factor
  (`previous_years` `EXCLUDE_FROM_COMMON`). Thermometers are mostly partisan proxies and share one format.
- **No stand-ins in the matched crosswalk.** A CES item without a clean ANES analog is omitted, including
  `CC24_424` (state-government trust). Preserving F3's two-institution shape is not a goal, because F3
  is a suppressor. The distrust dimension that matters is F2, and the independent fit lets ANES's richer
  trust items define it.
- **The CES police items (`CC24_321d`/`321e`) match to `V241397` (urban unrest, 1–7) and `V241270`
  (federal crime spending).** If the spending-format items (`V241270`, `V241267`, `V241276`) load together
  in ANES, treat that as a format factor, not Security & Order.
- **The independent pool uses the CES Stage A/B item screen unchanged** (`docs/EFA_ITEM_SELECTION_ROBUSTNESS.md`).
- **This round uses 2024 surveys only.** Workstream 7 (STY life-stage, the ANES 2016–2020–2024 panel, and
  the GSS cohort analysis) is deferred. Goals 1–3 need nothing before 2024.
- **All eight critique fixes are adopted** in `ces_anes_gss_validation_plan.md`:
  - a native-cluster route for parties that fail the recall gate;
  - a shrinkage factor measured on held-out CES respondents;
  - cut-points that match the CES answer splits;
  - a CES subsample benchmark for merges;
  - the `caseid` positional join for team modules;
  - the new workstream order: team modules → ANES EFAs → classifiers → profiles → GSS;
  - corrected paths and context;
  - a stated denominator for party shares.
- **The multi-item conceptual-domain version is a sensitivity check only.** Item density reshapes the
  factors (ANES's 4 racial-resentment items tend to form their own factor).

## 2026-10-28 (upstream changes this workstream depends on)

- **The CES typology is now nine parties on label-coded scores** (rescore 69a6eeb, nine-party rebuild
  on branch `bd-nine-parties`). Slot 7 (formerly OAO) holds no voters; LIB is renamed DAL (Democratic
  Alliance). Rulings live in the project `CLAUDE.md` and memory `typology-defensibility.md`. ANES
  clustering outputs committed before 69a6eeb use the ten-party labels and must be rerun before they
  are cited. The matched and independent EFAs stand: their CES inputs changed only by Populist
  Conservatism's sign (checked 2026-10-30, see NEXT.md).

## 2026-10-30

- **The polychoric uses an exact bivariate-normal CDF** (Owen's T, `efa_math.bvn_cdf`) instead of
  `scipy.stats.multivariate_normal.cdf`. Under the project `.venv` (scipy 1.17) the old call was already
  exact, so no committed output moves (largest CDF difference 2e-16). Under the system Python (scipy
  1.16) it was a randomized integral that changed on every run. The fix makes results independent of
  which interpreter runs them.
- **The ANES clustering benchmark caps the DPGMM at the live party count (9)** and takes party codes
  from `pipeline/party_codes.py`, matching the nine-party typology.

## 2026-10-31

- **The ANES independent screen has no party-ID cap.** The CES curation excluded direct party items
  (approvals, ideology placements) by category and never dropped a policy item for party-ID R² alone,
  so the 0.34 cap overstated the CES rule. Its only ANES casualty was the border-wall item
  (`V241395x`, R² 0.40), which now loads on the immigration factor. All 10 independent factors match
  the capped fit (Tucker φ 0.99–1.00). The redundancy tie-break (keep the less partisan twin) stays,
  as in CES.

# Outputs index

What each current figure/table shows, and which script produces it. Run order is in
`../FINDINGS.md` §7. Superseded outputs live in `archive/` (see bottom).

## Primary essay figures (all from `src/viz_essay_panels.py`)

| File | Claim it makes |
|---|---|
| `fig_essay_panel_a.png` | Among English-speaking democracies only the US is polarized (V-Dem 2025; US +2.30, nearest neighbors Afghanistan/South Sudan/Venezuela). |
| `fig_essay_panel_b.png` | Duopoly concentration tracks V-Dem polarization **within** the anglosphere (r=0.88) but **not** across all democracies (r=0.08) — the scope-conditional core. |
| `fig_essay_panels.png` | Both panels side by side (combined version). |

For the essay, place Panel A at the "company it keeps" sentence and Panel B at the mechanism
paragraph; see the `<!-- CLAUDE ... -->` markers in `../post.md`.

## Expert-measure (V-Dem) analysis

| File | Script | Claim |
|---|---|---|
| `bayes_coefficients.csv` | `analyze_bayes.py` | adjusted FPTP effect on V-Dem polarization +0.22 (P=0.93, established); **presidential +0.337 (P=0.775, inconclusive)**; anglophone-only FPTP +0.263 (P=0.96). |
| `bayes_prior_sensitivity.csv` | `analyze_bayes.py` | FPTP effect stable across skeptical/weak/diffuse priors (+0.16 to +0.22). |
| `fig_bayes_forest.png` | `analyze_bayes.py` | M_primary coefficients (democracy dominates; FPTP +, size +). |
| `fig_bayes_ridge.png` | `analyze_bayes.py` | FPTP×anglophone joint posterior (collinearity rendered honestly; corr ≈ −0.2). |
| `fig_bayes_prior_sensitivity.png` | `analyze_bayes.py` | prior-sensitivity of the FPTP coefficient. |

## Citizen-measure (CSES) analysis

| File | Script | Claim |
|---|---|---|
| `fig_anglophone_compare.png` | `viz_anglophone.py` | anglophone ranking flips between expert (V-Dem) and citizen (out-group coldness). |
| `fig_fptp_across_measures.png` | `viz_fptp_forest.py` | FPTP effect (SD units) across all measures/universes. **Uncontrolled** (no heritage covariate); the controlled estimate is +0.30–0.44, see `analyze_coldness_robustness.py`. |
| `fig_polarization_quadrants.png` | `viz_quadrants.py` | two-layer typology (expert × citizen), absolute anchors. |
| `fig_affpol_vs_elite.png` | `analyze_affpol.py` | affective (CSES) vs elite (V-Dem) scatter. |
| `affpol_country_merged.csv` | `analyze_affpol.py` | country-level affective + elite merge. |
| `fptp_forest_results.csv` | `viz_fptp_forest.py` | cached forest coefficients (SD units). |

Key intermediate tables live in `../data/`: `coldness_election.csv`, `affective_fractionalization.csv`
(top-2 concentration, ENP, AF), `enp_by_election.csv`, `cses_extras_election.csv`,
`dyadic_party_ratings.csv`.

## Corrections carried since the first pass (see FINDINGS §3c/§4)

- The citizen coldness headline is **+0.30–0.44 (directional)** after a common-law control and a clean
  single-member-plurality FPTP definition — not the uncontrolled +0.56. `fig_fptp_across_measures.png`
  shows the uncontrolled version.
- The operative channel is **balanced-duopoly concentration**, not effective number of parties.
- India is not in the citizen regressions; the US is 24th of 59 on the in/out gap (not "highest").

## archive/ — superseded

Early frequentist tiered exploration (`analyze.py`), superseded by the Bayesian + corrected analysis:
`fig1_anglophone_by_system.png`, `fig2_fptp_across_tiers.png`, `fig3_polarization_vs_democracy.png`,
`tier1_*.csv`, `tier2_*.csv`, `tier3_*.csv`, `tier3_regression_tables.txt`,
`primary_established_nonmicro.csv`, `collinearity_corr.csv`. Kept for provenance; do not cite.

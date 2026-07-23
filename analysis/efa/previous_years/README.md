# Cross-wave CES typology comparison (2018 / 2020 / 2022 vs 2024)

Does the 2024 ten-party typology hold up in earlier CES waves? This module re-runs
the proven 2024 EFA + DPGMM chain on 2018, 2020, and 2022 and compares factor
structure and clusters across years.

**Headline result:** the Populist-Conservatism spine (racial resentment + immigration
+ guns) is near-identical across all waves (Tucker φ 0.94→0.998); a religious/social
axis matches 2024 from 2020; Government Distrust matches 2024 from 2022 (φ 0.86, when
its trust items first exist). Only Security & Order (police/asylum/surveillance) and
Institutional Distrust (election-fairness) are strictly 2024-only. The 2024 typology
has no economic factor (fiscal loads on Populist), so the state-spending battery is
excluded from the common comparison. Full writeup: [`outputs/findings.md`](outputs/findings.md).

## The gating constraint

CES renumbers common content each cycle. After an exhaustive per-wave item search,
**10 typology items have a clean equivalent in all four waves** and form the common
comparison set: church, income, immigration legal-status + border, concealed carry,
abortion rape/incest, and the racial-attitude battery (`440a/b`, `441a/b`; 2018
`422a/b/e/f`). The all-wave state-spending battery (`443`/`426`) is available but
EXCLUDED from the common set (`crosswalk.EXCLUDE_FROM_COMMON`) because its same-format
items form a method factor absent from the 2024 typology; it stays in native fits.
Government trust exists only in 2022+2024; the election-fairness battery (F2's
signature), same-sex marriage, and surveillance are verified 2024-only. See
[`config/item_crosswalk.csv`](config/item_crosswalk.csv) (45 constructs) and
[`outputs/crosswalk_coverage.csv`](outputs/crosswalk_coverage.csv).

## Layout

```
common/            shared math extracted verbatim from the frozen 2024 pipeline
  efa_math.py        PAF, oblimin, parallel analysis, weighted polychoric, Thomson scores, wresid
  clustering.py      DPGMM (10-comp DP prior), remap-by-weighted-N, Hungarian centroid match, ARI
  congruence.py      Tucker's phi + factor matching
  crosswalk.py       load item_crosswalk.csv; label-based recode (whitespace-normalized)
  io_paths.py        wave -> dta path / weight column / output dir (repo-relative)
  wave_pipeline.py   end-to-end per-wave fit (recode -> polychoric -> EFA -> scores -> DPGMM)
config/
  item_crosswalk.csv  31 constructs x 4 waves: variable, recode token, coverage flag
wave_2024/
  reproduce_gate.py   asserts the shared math reproduces the frozen 2024 artifacts
run_wave.py           native (k=5) + common (k=4) fits for one wave -> outputs/<wave>/
compare/
  refit_common.py         (utility) refit the common set at a chosen k from stored matrices
  structural_congruence.py Tucker phi across waves (k=1 dominant + k=2 rotated per-factor)
  cluster_comparison.py    independent DPGMM + 2024 prior-lens projection
  compare_2022_2024.py     dedicated 2022-vs-2024 fit on 14 shared items (incl govt trust)
  compare_pair.py <wave>   adjacent-wave vs-2024 fit + cluster partisan makeup
                           (2020 adds the police battery; 2022 adds govt trust)
  middle_clusters.py       clusters sorted on conservatism axis w/ policy+partisan
                           profiles; isolates the moderate middle + its trend
  enrich_trends.py         partisan spread on the dominant conservatism axis
outputs/
  <wave>/            loadings_*, phi_*, parallel_*, cluster_shares_*, diagnostics_*, fit_results.pkl
  congruence_matrix.csv, cluster_drift.csv, priorlens_shares.csv, backbone_trends.csv
  crosswalk_coverage.csv, findings.md
```

## Reproduce

```bash
# 0. validate the shared math reproduces canonical 2024 (loadings, 10 clusters) — the gate
.venv/bin/python analysis/efa/previous_years/wave_2024/reproduce_gate.py

# 1. per-wave native + common fits
for y in 2018 2020 2022 2024; do
  .venv/bin/python analysis/efa/previous_years/run_wave.py $y
done

# 2. refit the common set on the 10 typology items (excl. spending battery) at k=2
.venv/bin/python analysis/efa/previous_years/compare/refit_common.py

# 3. comparisons
.venv/bin/python analysis/efa/previous_years/compare/structural_congruence.py
.venv/bin/python analysis/efa/previous_years/compare/cluster_comparison.py
.venv/bin/python analysis/efa/previous_years/compare/enrich_trends.py
.venv/bin/python analysis/efa/previous_years/compare/compare_2022_2024.py   # dedicated 2-wave (incl govt trust)
```

## Method notes

- Recode is **label-based** (`convert_categoricals=True`), oriented so higher = more
  conservative/right, matching the 2024 recode direction validated against
  `efa_loadings_k5_final.csv`. Skip / not-asked / don't-know labels map to NaN.
- Every wave uses `commonpostweight` (the racial/gender items are post-survey).
- The 2024 gate reproduces the frozen polychoric (max diff 0.014), loadings
  (max diff 0.018), and recovers 10 effective clusters (sorted shares within 2.6pp;
  the DPGMM fit is unweighted and stochastic per the production pipeline).
- Nothing here modifies the viz or the frozen 2024 pipeline scripts. Raw `.dta` are
  read-only from `UNTRACKED/CES Data/`.

## Not in this deliverable (next phase)

Turnout and the midterm-vs-presidential composition question. Validated turnout is
present in every wave (`CL_2018gvm`/`CL_2020gvm`, `TS_g2022`/`TS_g2024`) but unused
here; share/score differences currently confound attitude change with turnout
composition.

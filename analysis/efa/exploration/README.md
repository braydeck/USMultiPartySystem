# EFA exploration & robustness

Everything here is **exploratory / audit** work — not part of the canonical production pipeline (that lives in `../pipeline/` and the canonical artifacts in `../`). These files document *what was tested* on the way to the 5-factor / 10-party typology. The narrative write-up is [`docs/EFA_ITEM_SELECTION_ROBUSTNESS.md`](../../../docs/EFA_ITEM_SELECTION_ROBUSTNESS.md).

> **Path caveat:** these scripts were written to run from the **repo root** with hardcoded relative paths (e.g. `analysis/efa/cluster_labels_variants.csv`). After moving them into `exploration/`, those paths point one level up from their new location — re-running requires repointing them into `analysis/efa/exploration/`. They are kept as a record of methodology, not as turnkey re-runs.

## What's here

**k-sweep (dimensionality choice)**
- `efa_loadings_k{3,4,5,6,7}.csv`, `efa_phi_k{3,4,5,6,7}.csv` — the extraction at each factor count (the production k=5 *final* solution is `../efa_loadings_k5_final.csv`).

**k4/k5 × residualization robustness**
- `compare_k4_vs_k5_clustering.py`, `cluster_survival_k4_k5.py`, `cluster_confidence_k5.py`, `eta2_resid_compare.py`, `profile_variant_clusters.py`, `cluster_labels_variants.csv`, `variant_cluster_profiles.txt`.

**Two-paradigm cluster explorer** (resid vs no-resid)
- `build_cluster_explorer_data.py`, `build_cluster_explorer_html.py`, `cluster_explorer_data.json`, `cluster_explorer.html`.

**Six-dimension (foreign-policy) variant**
- `sixdim_cluster.py`, `build_sixdim_{data,html}.py`, `sixdim_data.json`, `sixdim_explorer.html`, `sixdim_labels.csv`.

**Coalition-fracture view**
- `coalition_fracture.py`, `build_coalition_fracture_html.py`, `coalition_fracture.{json,html}`.

**Excluded-domain / proxy explorations**
- `explore_foreign_policy.py`, `explore_extra_dims.py`, `rerun_efa_with_proxies.py`, `polychoric_matrix_with_proxies.csv`.

**Audit artifacts (July 2026)**
- `verify_f3_inversion.py` — shows F3 ("Government Distrust") runs opposite to real distrust.
- `recompute_redundant_pairs.py`, `redundancy_recheck_notes.md`, `polychoric_matrix_redundancy_screen.csv` — corrected redundancy screening (the canonical `../redundant_pairs.csv` was regenerated from this).

**Supporting diagnostics / figures**
- `efa_recommendation_table.csv`, `efa_cramersv_actual.csv`, `efa_factor_partisan_summary.csv`, `polychoric_heatmap.png`, `polychoric_heatmap_v4.png`.

# EFA → Typology pipeline

How the ten-party political typology is derived from the 2024 CES, plus the
robustness analysis behind the modeling choices. Narrative reference:
[`docs/EFA_FACTORS.md`](../../docs/EFA_FACTORS.md).

> **Heads-up on paths:** the canonical pipeline scripts in `pipeline/` were written
> against an earlier working directory (`/Users/bdecker/Documents/STV/Claude`) and
> have **hardcoded `DATA_DIR` paths**. They document the methodology that produced
> the committed artifacts; to re-run them, repoint `DATA_DIR` at the repo's
> `data/processed/` and `analysis/efa/`. The raw CES `.dta` is git-ignored (≈1 GB).

## Directory layout
- **Root (this folder) — canonical artifacts only:** `pipeline/` (the ordered production pipeline), `efa_loadings_k5_final.csv` / `efa_phi_k5_final.csv` (the k=5 solution), `efa_variable_list.csv` + `_v3.csv` (item screening), `efa_parallel_analysis.csv`, `efa_variance_summary.csv`, `efa_checkpoint_summary.txt`, `redundant_pairs.csv`.
- **`exploration/` — all robustness, comparison, and audit work:** the k-sweep loadings (k3/k4/k6/k7 + non-final k5), the k4/k5 × resid comparison and survival/confidence scripts, the cluster explorer + six-dim variant, the redundancy recompute + F3-inversion audit, and their data/HTML/PNG outputs. These document *what was tested*; the write-up is [`docs/EFA_ITEM_SELECTION_ROBUSTNESS.md`](../../docs/EFA_ITEM_SELECTION_ROBUSTNESS.md). (These scripts were written to run from the repo root with relative paths; after the move, re-running them requires repointing those paths into `exploration/`.)

## Canonical pipeline (`pipeline/`), in order

| Step | Script | Reads | Writes |
|---|---|---|---|
| 1. Preprocess + polychoric | `efa_pipeline_v4.py` | raw CES `.dta` | `polychoric_matrix.csv`, `efa_variable_list.csv`, `efa_checkpoint_summary.txt` |
| 2. Extract + rotate | `run_efa.py` | `polychoric_matrix.csv` | `efa_loadings_k{3..7}.csv`, `efa_phi_k*.csv`, `efa_parallel_analysis.csv`, `efa_variance_summary.csv` |
| 3. Factor scores + residualize | `efa_update.py` | polychoric + k5 loadings + raw `.dta` | `efa_factor_scores.csv` (FS_F1–F5, FS_F4_resid, FS_F5_resid); `efa_loadings_k5_final.csv`, `efa_phi_k5_final.csv` |
| 4. Cluster | `dpgmm_clustering.py` | `efa_factor_scores.csv` | `typology_cluster_assignments.csv` (cluster + posteriors) |
| 5. Profile clusters | `cluster_profiles.py` | `typology_cluster_assignments.csv` | `cluster_profiles_raw.csv` |

Method: 24-item polychoric EFA (one item dropped for a near-Heywood loading) →
PAF + oblimin, k=5 → Thomson regression factor scores → sign-flips →
F4/F5 residualized on F1 → DPGMM (`n_components=10`, Dirichlet process) → C7
kept as OAO (Order & Opportunity Party), for **10 parties**.

### k=4 alternative (explored, not adopted)
`run_efa_k4.py`, `run_dpgmm_k4.py` — the 4-factor variant. Rejected because the
4th factor is an uninterpretable junk dimension (see `docs/EFA_FACTORS.md` →
Robustness). k=5's only weakness (Government Distrust, η²≈0.06) is benign by
comparison.

## Robustness analysis (`exploration/`)

Built to test whether the parties are real structure or artifacts of the k /
residualization choices. Scripts (now under `exploration/`) were written to run
from the **repo root** with relative paths.

| Script | Purpose |
|---|---|
| `compare_k4_vs_k5_clustering.py` | Re-runs EFA+DPGMM for k=4/k=5 × resid/no-resid; cluster profiles + ARI |
| `cluster_survival_k4_k5.py` | Matches each variant's clusters back to the production parties → preserved/split/absorbed; writes `cluster_labels_variants.csv` |
| `cluster_confidence_k5.py` | Re-fits k=5 (resid & no-resid) to recover DPGMM assignment confidence (cluster strength) |
| `build_cluster_explorer_data.py` | Assembles the comparison JSON (policy, demographics, factors, correspondence, strength) |
| `build_cluster_explorer_html.py` | Renders `cluster_explorer.html` — the standalone two-paradigm infographic |
| `profile_variant_clusters.py` | Plain-text per-cluster profiles for every variant |
| `eta2_resid_compare.py` | η² of each factor under resid vs no-resid clustering |
| `rerun_efa_with_proxies.py` | Re-runs EFA with the dropped partisan proxies added back (cross-cutting robustness) |

**Deliverable:** open [`exploration/cluster_explorer.html`](exploration/cluster_explorer.html) in a browser.

## Committed artifacts
- Loadings / rotation: `efa_loadings_k5_final.csv`, `efa_phi_k5_final.csv`, `efa_parallel_analysis.csv`, `efa_variance_summary.csv` (this directory)
- Scores / clusters: `data/processed/{polychoric_matrix,efa_factor_scores,typology_cluster_assignments}.csv`

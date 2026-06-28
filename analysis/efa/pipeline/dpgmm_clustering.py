"""
dpgmm_clustering.py
-------------------
Dirichlet Process Gaussian Mixture Model clustering of CES 2024 factor scores.

Input:  efa_factor_scores.csv  (N=45,707; five factor scores + weights)
Output: typology_cluster_assignments.csv  (hard + soft cluster assignments)

Factor inputs:
  FS_F1         - Enforcement Orientation (HIGH = enforcement-conservative)
  FS_F2         - Election Distrust (HIGH = distrusts elections)
  FS_F3         - Government Trust (HIGH = distrusts government)
  FS_F4_resid   - Repro Rights / Religion, F1-residualized
  FS_F5_resid   - Values Conservatism, F1-residualized

DPGMM params:
  n_components=10  (upper bound; effective k determined by data)
  covariance_type='full'
  weight_concentration_prior_type='dirichlet_process'
  n_init=5
  max_iter=500
  random_state=42
"""

import numpy as np
import pandas as pd
from sklearn.mixture import BayesianGaussianMixture

DATA_DIR = "/Users/bdecker/Documents/STV/Claude"
CLUSTER_COLS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4_resid", "FS_F5_resid"]
COL_LABELS = ["F1(Enf)", "F2(ElDis)", "F3(GovTru)", "F4r(RepRel)", "F5r(ValCon)"]

# ---------------------------------------------------------------------------
# 1. SETUP
# ---------------------------------------------------------------------------
print("=" * 70)
print("SETUP")
print("=" * 70)

fs = pd.read_csv(f"{DATA_DIR}/efa_factor_scores.csv")
print(f"Loaded efa_factor_scores.csv: {fs.shape[0]:,} rows x {fs.shape[1]} cols")
print(f"NaN count in clustering columns: {fs[CLUSTER_COLS].isna().sum().sum()}")
print(f"Total commonpostweight sum: {fs['commonpostweight'].sum():,.1f}")

X = fs[CLUSTER_COLS].values
w = fs["commonpostweight"].values

# ---------------------------------------------------------------------------
# 2. FIT DPGMM
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("FIT DPGMM")
print("=" * 70)

dpgmm = BayesianGaussianMixture(
    n_components=10,
    covariance_type='full',
    weight_concentration_prior_type='dirichlet_process',
    n_init=5,
    random_state=42,
    max_iter=500,
)

# Note: BayesianGaussianMixture.fit() does not accept sample_weight in sklearn.
# Fitting is done unweighted on the standardized factor scores; those scores were
# themselves derived from the weighted Thomson regression (weighted polychoric R).
# Survey weights (commonpostweight) are applied to ALL post-fit reporting:
# cluster sizes, factor score means, and validation cross-tabs.
print("Fitting BayesianGaussianMixture (n_components=10, n_init=5, max_iter=500)...")
print("Note: fit() is unweighted (sklearn limitation); commonpostweight applied to all reporting.")
dpgmm.fit(X)
print(f"Converged: {dpgmm.converged_}")
print(f"Lower bound (final): {dpgmm.lower_bound_:.4f}")

# ---------------------------------------------------------------------------
# 3. EFFECTIVE CLUSTER COUNT
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("EFFECTIVE CLUSTER COUNT  (weight > 0.01 threshold)")
print("=" * 70)

sorted_idx = np.argsort(dpgmm.weights_)[::-1]
sorted_weights = dpgmm.weights_[sorted_idx]

print("\nAll component weights (sorted descending):")
print(f"  {'Comp':>4}  {'Weight':>8}  {'Active':>6}")
print(f"  {'-'*4}  {'-'*8}  {'-'*6}")
for rank, (orig_idx, wt) in enumerate(zip(sorted_idx, sorted_weights)):
    active = "YES" if wt > 0.01 else "---"
    print(f"  {orig_idx:>4}  {wt:>8.5f}  {active:>6}")

n_eff = (dpgmm.weights_ > 0.01).sum()
print(f"\nEffective clusters (weight > 0.01): {n_eff}")

# ---------------------------------------------------------------------------
# 4. HARD ASSIGNMENTS AND CLUSTER SIZES
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("CLUSTER SIZES")
print("=" * 70)

# Raw cluster labels from predict()
raw_labels = dpgmm.predict(X)

# Keep only effective components; remap by descending weighted N
eff_components = sorted_idx[:n_eff]  # original component indices, largest weight first

# Build mapping: original component index -> new cluster id (0 = largest)
raw_weighted_n = {}
for orig_k in eff_components:
    mask = raw_labels == orig_k
    raw_weighted_n[orig_k] = w[mask].sum()

# Sort by weighted N descending to assign final cluster IDs
size_sorted = sorted(eff_components, key=lambda k: raw_weighted_n[k], reverse=True)
remap = {orig_k: new_k for new_k, orig_k in enumerate(size_sorted)}

# Apply remap to labels; rows in non-effective components get label -1 (shouldn't happen
# in practice since predict() assigns to argmax, but guard anyway)
cluster = np.full(len(raw_labels), -1, dtype=int)
for orig_k, new_k in remap.items():
    cluster[raw_labels == orig_k] = new_k

print(f"\n  {'Cluster':>7}  {'Unweighted N':>13}  {'Weighted N':>11}  {'Weighted %':>11}")
print(f"  {'-'*7}  {'-'*13}  {'-'*11}  {'-'*11}")
total_w = w.sum()
for new_k in range(n_eff):
    mask = cluster == new_k
    uw_n = mask.sum()
    wt_n = w[mask].sum()
    pct = 100.0 * wt_n / total_w
    print(f"  {new_k:>7}  {uw_n:>13,}  {wt_n:>11,.1f}  {pct:>10.1f}%")

unassigned = (cluster == -1).sum()
if unassigned > 0:
    print(f"\n  WARNING: {unassigned} respondents not assigned to any effective cluster")

print(f"\n  Total weighted N assigned: {w[cluster >= 0].sum():,.1f}  (should be ~{total_w:,.1f})")

# ---------------------------------------------------------------------------
# 5. CLUSTER MEANS (FACTOR SCORE PROFILES)
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("CLUSTER MEANS — FACTOR SCORE PROFILES")
print("=" * 70)

col_width = 11

header_parts = [f"{'Cluster':>7}", f"{'Wtd N':>8}"]
for lbl in COL_LABELS:
    header_parts.append(f"{lbl:>{col_width}}")
print("\n  " + "  ".join(header_parts))

sep_parts = ["-" * 7, "-" * 8] + ["-" * col_width] * len(COL_LABELS)
print("  " + "  ".join(sep_parts))

cluster_means = {}
for new_k in range(n_eff):
    mask = cluster == new_k
    wt_n = w[mask].sum()
    means = []
    for col_idx in range(len(CLUSTER_COLS)):
        m = np.average(X[mask, col_idx], weights=w[mask])
        means.append(m)
    cluster_means[new_k] = means
    row_parts = [f"{new_k:>7}", f"{wt_n:>8,.0f}"]
    for m in means:
        row_parts.append(f"{m:>{col_width}.4f}")
    print("  " + "  ".join(row_parts))

# ---------------------------------------------------------------------------
# 6. ASSIGNMENT CONFIDENCE (mean max-probability per cluster)
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("ASSIGNMENT CONFIDENCE  (mean max-probability per cluster)")
print("=" * 70)

probs = dpgmm.predict_proba(X)
max_probs = probs.max(axis=1)

print(f"\n  Overall mean max-probability: {max_probs.mean():.4f}")
print(f"  Overall median max-probability: {np.median(max_probs):.4f}")
print(f"  Fraction with max-prob > 0.90: {(max_probs > 0.90).mean():.3f}")
print(f"  Fraction with max-prob > 0.70: {(max_probs > 0.70).mean():.3f}")
print(f"  Fraction with max-prob > 0.50: {(max_probs > 0.50).mean():.3f}")

print(f"\n  {'Cluster':>7}  {'Mean max-prob':>13}  {'Median max-prob':>15}  {'N > 0.90':>9}")
print(f"  {'-'*7}  {'-'*13}  {'-'*15}  {'-'*9}")
for new_k in range(n_eff):
    mask = cluster == new_k
    mp = max_probs[mask]
    print(f"  {new_k:>7}  {mp.mean():>13.4f}  {np.median(mp):>15.4f}  {(mp > 0.90).mean():>9.3f}")

# ---------------------------------------------------------------------------
# 7. SAVE CLUSTER ASSIGNMENTS
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("SAVE CLUSTER ASSIGNMENTS")
print("=" * 70)

save_cols = ["pid3", "ideo5", "inputstate", "commonpostweight",
             "govt_trust_imputed"] + CLUSTER_COLS

out = fs[save_cols].copy()
out["cluster"] = cluster

# Save soft assignment probabilities for effective clusters only
# Use remapped indices: column prob_cluster_k corresponds to new cluster k
for new_k in range(n_eff):
    orig_k = size_sorted[new_k]
    out[f"prob_cluster_{new_k}"] = probs[:, orig_k]

out_path = f"{DATA_DIR}/typology_cluster_assignments.csv"
out.to_csv(out_path, index=False)
print(f"Saved: {out_path}")
print(f"  Shape: {out.shape[0]:,} rows x {out.shape[1]} columns")
print(f"  Columns: {list(out.columns)}")

# ---------------------------------------------------------------------------
# 8. VALIDATION CROSS-TABS
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("VALIDATION CROSS-TABS")
print("=" * 70)

def weighted_pct_crosstab(series, cluster_arr, weights, val_labels):
    """Weighted % breakdown of `series` categories within each cluster."""
    cats = sorted(series.dropna().unique())
    results = {}
    for new_k in range(n_eff):
        mask = cluster_arr == new_k
        total_w = weights[mask].sum()
        row = {}
        for cat in cats:
            cat_mask = mask & (series.values == cat)
            row[cat] = 100.0 * weights[cat_mask].sum() / total_w
        results[new_k] = row
    # Print
    col_w = 9
    cat_labels_display = [val_labels.get(c, str(c)) for c in cats]
    header = f"  {'Cluster':>7}  {'Wtd N':>8}  " + "  ".join(f"{l:>{col_w}}" for l in cat_labels_display)
    print(f"\n{header}")
    print("  " + "-" * (len(header) - 2))
    for new_k in range(n_eff):
        mask = cluster_arr == new_k
        wt_n = weights[mask].sum()
        row_str = "  ".join(f"{results[new_k][c]:>{col_w}.1f}%" for c in cats)
        print(f"  {new_k:>7}  {wt_n:>8,.0f}  {row_str}")

# --- 8a. Party ID (pid3) ---
print("\n--- Party ID (pid3: 1=Dem, 2=Rep, 3=Indep/Other) ---")
pid_labels = {1.0: "Dem%", 2.0: "Rep%", 3.0: "Ind%"}
# pid3 can be float in the csv
pid3_series = fs["pid3"].round(0)
weighted_pct_crosstab(pid3_series, cluster, w, pid_labels)

# --- 8b. Ideology (ideo5) ---
print("\n--- Ideology (ideo5: 1=VLib ... 5=VCon) ---")
ideo_labels = {1.0: "VLib%", 2.0: "Lib%", 3.0: "Mod%", 4.0: "Con%", 5.0: "VCon%"}
ideo5_series = fs["ideo5"].round(0)
weighted_pct_crosstab(ideo5_series, cluster, w, ideo_labels)

# --- 8c. govt_trust_imputed ---
print("\n--- Govt Trust Imputed Flag (0=non-imputed, 1=imputed/'Not sure') ---")
flag_labels = {0: "NotImputed%", 1: "Imputed%"}
weighted_pct_crosstab(fs["govt_trust_imputed"], cluster, w, flag_labels)

# --- 8d. Mean FS_F2 and FS_F3 per cluster ---
print("\n--- Mean FS_F2 (Election Distrust) and FS_F3 (Govt Trust) per cluster ---")
f2_vals = fs["FS_F2"].values
f3_vals = fs["FS_F3"].values
print(f"\n  {'Cluster':>7}  {'Wtd N':>8}  {'Mean F2(ElDis)':>15}  {'Mean F3(GovTru)':>16}")
print(f"  {'-'*7}  {'-'*8}  {'-'*15}  {'-'*16}")
for new_k in range(n_eff):
    mask = cluster == new_k
    wt_n = w[mask].sum()
    mean_f2 = np.average(f2_vals[mask], weights=w[mask])
    mean_f3 = np.average(f3_vals[mask], weights=w[mask])
    print(f"  {new_k:>7}  {wt_n:>8,.0f}  {mean_f2:>15.4f}  {mean_f3:>16.4f}")

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)

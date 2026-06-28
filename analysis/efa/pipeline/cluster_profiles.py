"""
cluster_profiles.py
-------------------
Produces a comprehensive cluster comparison table from the DPGMM output.

Input:  typology_cluster_assignments.csv  (N=45,707; cluster labels, factor
        scores, pid3, ideo5, commonpostweight, prob_cluster_0..9)
Output: cluster_profiles_raw.csv  (one row per cluster; all metrics)

Columns in output:
  cluster, weighted_n, weighted_pct
  f1_mean, f2_mean, f3_mean, f4r_mean, f5r_mean
  pid3_dem_pct, pid3_rep_pct, pid3_ind_pct, pid3_other_pct
  ideo_vlib_pct, ideo_lib_pct, ideo_mod_pct, ideo_con_pct, ideo_vcon_pct
  mean_max_prob

Also prints the 10x10 Mahalanobis distance matrix between cluster centroids
(using the overall sample covariance of the five factor score inputs).
"""

import numpy as np
import pandas as pd
from scipy.linalg import solve

DATA_DIR = "/Users/bdecker/Documents/STV/Claude"
CLUSTER_COLS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4_resid", "FS_F5_resid"]
COL_LABELS   = ["F1(Enf)", "F2(ElDis)", "F3(GovTru)", "F4r(RepRel)", "F5r(ValCon)"]

# ---------------------------------------------------------------------------
# 1. LOAD DATA
# ---------------------------------------------------------------------------
print("=" * 70)
print("LOAD DATA")
print("=" * 70)

df = pd.read_csv(f"{DATA_DIR}/typology_cluster_assignments.csv")
print(f"Loaded typology_cluster_assignments.csv: {df.shape[0]:,} rows x {df.shape[1]} cols")

n_clusters = 10
X  = df[CLUSTER_COLS].values
w  = df["commonpostweight"].values
cl = df["cluster"].values

prob_cols = [f"prob_cluster_{k}" for k in range(n_clusters)]
probs = df[prob_cols].values   # shape (N, 10)
max_probs = probs.max(axis=1)

total_w = w.sum()
print(f"Total commonpostweight: {total_w:,.1f}")
print(f"Clusters present: {sorted(df['cluster'].unique())}")

# ---------------------------------------------------------------------------
# 2. CLUSTER CENTROIDS AND WEIGHTED STATS
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("COMPUTING CLUSTER METRICS")
print("=" * 70)

records = []

for k in range(n_clusters):
    mask = cl == k
    wk   = w[mask]
    wk_sum = wk.sum()

    # --- factor score means ---
    means = {col: np.average(X[mask, i], weights=wk)
             for i, col in enumerate(CLUSTER_COLS)}

    # --- pid3 breakdown ---
    pid3 = df.loc[mask, "pid3"].values
    pid_cats = {1: "dem", 2: "rep", 3: "ind"}
    pid_pct  = {}
    for code, label in pid_cats.items():
        pid_pct[f"pid3_{label}_pct"] = 100.0 * wk[pid3 == code].sum() / wk_sum
    # category 4 + 5 combined → "other"
    other_mask = np.isin(pid3, [4, 5])
    pid_pct["pid3_other_pct"] = 100.0 * wk[other_mask].sum() / wk_sum

    # --- ideo5 breakdown ---
    ideo5 = df.loc[mask, "ideo5"].values
    ideo_cats = {1: "vlib", 2: "lib", 3: "mod", 4: "con", 5: "vcon"}
    ideo_pct  = {}
    for code, label in ideo_cats.items():
        ideo_pct[f"ideo_{label}_pct"] = 100.0 * wk[ideo5 == code].sum() / wk_sum

    # --- mean max-probability ---
    mean_max_p = max_probs[mask].mean()

    row = {
        "cluster":      k,
        "weighted_n":   round(wk_sum, 1),
        "weighted_pct": round(100.0 * wk_sum / total_w, 2),
        "f1_mean":      round(means["FS_F1"], 4),
        "f2_mean":      round(means["FS_F2"], 4),
        "f3_mean":      round(means["FS_F3"], 4),
        "f4r_mean":     round(means["FS_F4_resid"], 4),
        "f5r_mean":     round(means["FS_F5_resid"], 4),
        **{k2: round(v, 2) for k2, v in pid_pct.items()},
        **{k2: round(v, 2) for k2, v in ideo_pct.items()},
        "mean_max_prob": round(mean_max_p, 4),
    }
    records.append(row)

profiles = pd.DataFrame(records)

# ---------------------------------------------------------------------------
# 3. PRINT FULL COMPARISON TABLE
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("CLUSTER COMPARISON TABLE")
print("=" * 70)

# -- Factor score means --
print("\n--- Factor Score Means ---")
print(f"\n  {'Cl':>3}  {'WtdN':>7}  {'Wt%':>5}  "
      + "  ".join(f"{l:>11}" for l in COL_LABELS))
print("  " + "-" * (3 + 2 + 7 + 2 + 5 + 2 + 11*5 + 2*4))
for _, r in profiles.iterrows():
    k = int(r["cluster"])
    print(f"  {k:>3}  {r['weighted_n']:>7,.0f}  {r['weighted_pct']:>4.1f}%  "
          + "  ".join(f"{r[f]:>11.4f}" for f in
                      ["f1_mean","f2_mean","f3_mean","f4r_mean","f5r_mean"]))

# -- Party ID --
print("\n--- Weighted % Party ID (pid3) ---")
print(f"\n  {'Cl':>3}  {'WtdN':>7}  {'Dem%':>7}  {'Rep%':>7}  {'Ind%':>7}  {'Other%':>7}")
print("  " + "-" * 48)
for _, r in profiles.iterrows():
    k = int(r["cluster"])
    print(f"  {k:>3}  {r['weighted_n']:>7,.0f}  "
          f"{r['pid3_dem_pct']:>7.1f}  {r['pid3_rep_pct']:>7.1f}  "
          f"{r['pid3_ind_pct']:>7.1f}  {r['pid3_other_pct']:>7.1f}")

# -- Ideology --
print("\n--- Weighted % Ideology (ideo5) ---")
print(f"\n  {'Cl':>3}  {'WtdN':>7}  {'VLib%':>7}  {'Lib%':>7}  {'Mod%':>7}  {'Con%':>7}  {'VCon%':>7}")
print("  " + "-" * 58)
for _, r in profiles.iterrows():
    k = int(r["cluster"])
    print(f"  {k:>3}  {r['weighted_n']:>7,.0f}  "
          f"{r['ideo_vlib_pct']:>7.1f}  {r['ideo_lib_pct']:>7.1f}  "
          f"{r['ideo_mod_pct']:>7.1f}  {r['ideo_con_pct']:>7.1f}  "
          f"{r['ideo_vcon_pct']:>7.1f}")

# -- Mean max-probability --
print("\n--- Mean Max-Probability (Assignment Confidence) ---")
print(f"\n  {'Cl':>3}  {'WtdN':>7}  {'MeanMaxP':>10}")
print("  " + "-" * 26)
for _, r in profiles.iterrows():
    k = int(r["cluster"])
    print(f"  {k:>3}  {r['weighted_n']:>7,.0f}  {r['mean_max_prob']:>10.4f}")

# ---------------------------------------------------------------------------
# 4. MAHALANOBIS DISTANCE MATRIX
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("MAHALANOBIS DISTANCE MATRIX  (cluster centroid pairs)")
print("Using overall sample covariance of the 5 factor score inputs.")
print("=" * 70)

# Overall (unweighted) sample covariance matrix on the 5 cluster inputs
# Using unweighted cov because the factor score space itself was not
# weighted at fit time; this gives a consistent metric for centroid separation.
S     = np.cov(X.T)          # shape (5, 5)
S_inv = np.linalg.inv(S)

# Cluster centroids (weighted means)
centroids = np.array([
    np.average(X[cl == k], axis=0, weights=w[cl == k])
    for k in range(n_clusters)
])

# Pairwise Mahalanobis distances
D = np.zeros((n_clusters, n_clusters))
for i in range(n_clusters):
    for j in range(n_clusters):
        diff = centroids[i] - centroids[j]
        D[i, j] = np.sqrt(diff @ S_inv @ diff)

# Print distance matrix
print(f"\n  {'':>3}", end="")
for j in range(n_clusters):
    print(f"  {'C'+str(j):>7}", end="")
print()
print("  " + "-" * (3 + 9 * n_clusters))

for i in range(n_clusters):
    print(f"  {'C'+str(i):>3}", end="")
    for j in range(n_clusters):
        if i == j:
            print(f"  {'---':>7}", end="")
        else:
            print(f"  {D[i,j]:>7.3f}", end="")
    print()

# Summary: nearest and farthest neighbor for each cluster
print("\n--- Nearest / Farthest Neighbor per Cluster ---")
print(f"\n  {'Cl':>3}  {'Nearest':>8}  {'Dist':>7}  {'Farthest':>9}  {'Dist':>7}")
print("  " + "-" * 44)
for i in range(n_clusters):
    row = D[i].copy()
    row[i] = np.inf
    nearest = int(np.argmin(row))
    row[i] = 0.0
    farthest = int(np.argmax(row))
    print(f"  {i:>3}  {'C'+str(nearest):>8}  {D[i, nearest]:>7.3f}  "
          f"{'C'+str(farthest):>9}  {D[i, farthest]:>7.3f}")

# Smallest off-diagonal distances (candidates for aggregation)
print("\n--- 10 Smallest Pairwise Distances (closest cluster pairs) ---")
pairs = []
for i in range(n_clusters):
    for j in range(i+1, n_clusters):
        pairs.append((D[i,j], i, j))
pairs.sort()
print(f"\n  {'Rank':>4}  {'Pair':>8}  {'Mahal. Dist':>12}")
print("  " + "-" * 28)
for rank, (dist, i, j) in enumerate(pairs[:10], 1):
    print(f"  {rank:>4}  {'C'+str(i)+'-C'+str(j):>8}  {dist:>12.4f}")

# ---------------------------------------------------------------------------
# 5. SAVE cluster_profiles_raw.csv
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("SAVE")
print("=" * 70)

out_path = f"{DATA_DIR}/cluster_profiles_raw.csv"
profiles.to_csv(out_path, index=False)
print(f"Saved: {out_path}")
print(f"  Rows: {len(profiles)}  |  Columns: {list(profiles.columns)}")

# Also save distance matrix as CSV
dist_df = pd.DataFrame(
    D,
    index=[f"C{k}" for k in range(n_clusters)],
    columns=[f"C{k}" for k in range(n_clusters)]
).round(4)
dist_path = f"{DATA_DIR}/cluster_mahal_distances.csv"
dist_df.to_csv(dist_path)
print(f"Saved: {dist_path}")

print("\n" + "=" * 70)
print("DONE  — do not aggregate yet")
print("=" * 70)

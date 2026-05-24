#!/usr/bin/env python3
"""
run_dpgmm_k4.py
---------------
DPGMM clustering on k=4 factor scores.

Input:  data/processed/k4/efa_factor_scores_k4.csv
Output: data/processed/k4/typology_cluster_assignments_k4.csv

Uses the same DPGMM settings as the k=5 baseline:
  n_components=10, covariance_type='full', n_init=5, max_iter=500
"""

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.mixture import BayesianGaussianMixture

BASE_DIR = Path(__file__).parent.parent
FS_PATH  = BASE_DIR / "data" / "processed" / "k4" / "efa_factor_scores_k4.csv"
OUT_PATH = BASE_DIR / "data" / "processed" / "k4" / "typology_cluster_assignments_k4.csv"


def main():
    sep  = "=" * 70
    thin = "─" * 70

    print(sep)
    print("DPGMM CLUSTERING  |  k=4 factor scores")
    print(sep)

    # ── 1. Load factor scores ─────────────────────────────────────────────────
    fs = pd.read_csv(FS_PATH)
    print(f"\nLoaded {FS_PATH.name}: {fs.shape[0]:,} rows × {fs.shape[1]} cols")
    print(f"Columns: {list(fs.columns)}")

    # Select clustering columns: prefer residualized where available
    # Raw factor score columns
    raw_cols   = [c for c in fs.columns if c.startswith("FS_F") and "_resid" not in c]
    resid_cols = [c for c in fs.columns if c.endswith("_resid")]

    # Build final feature set: residualized version of a factor if it exists,
    # otherwise raw. Always use raw for F1 (enforcement anchor).
    f1_col = raw_cols[0]   # FS_F1 is always F1 (enforcement); never residualized against itself
    resid_bases = {c.replace("_resid", ""): c for c in resid_cols}

    cluster_cols = [f1_col]
    for rc in raw_cols[1:]:
        cluster_cols.append(resid_bases.get(rc, rc))

    print(f"\nClustering features ({len(cluster_cols)}):")
    for col in cluster_cols:
        print(f"  {col}")

    X = fs[cluster_cols].values
    w = fs["commonpostweight"].values
    print(f"\nNaN in features: {np.isnan(X).sum()}")
    print(f"Total commonpostweight: {w.sum():,.1f}")

    # ── 2. Fit DPGMM ─────────────────────────────────────────────────────────
    print(f"\n{thin}")
    print("FIT DPGMM  (n_components=10, full covariance, n_init=5)")
    print(thin)

    dpgmm = BayesianGaussianMixture(
        n_components=10,
        covariance_type="full",
        weight_concentration_prior_type="dirichlet_process",
        n_init=5,
        random_state=42,
        max_iter=500,
    )
    print("Fitting… (unweighted; survey weights applied to all post-fit reporting)")
    dpgmm.fit(X)
    print(f"Converged: {dpgmm.converged_}")
    print(f"Lower bound: {dpgmm.lower_bound_:.4f}")

    # ── 3. Effective cluster count ────────────────────────────────────────────
    print(f"\n{thin}")
    print("EFFECTIVE CLUSTER COUNT  (weight > 0.01)")
    print(thin)

    sorted_idx    = np.argsort(dpgmm.weights_)[::-1]
    sorted_weights = dpgmm.weights_[sorted_idx]

    print(f"\n  {'Comp':>4}  {'Weight':>8}  {'Active':>6}")
    print(f"  {'-'*4}  {'-'*8}  {'-'*6}")
    for orig_idx, wt in zip(sorted_idx, sorted_weights):
        active = "YES" if wt > 0.01 else "---"
        print(f"  {orig_idx:>4}  {wt:>8.5f}  {active:>6}")

    n_eff = (dpgmm.weights_ > 0.01).sum()
    print(f"\nEffective clusters: {n_eff}")

    # ── 4. Hard assignments & remapping ──────────────────────────────────────
    raw_labels = dpgmm.predict(X)
    eff_components = sorted_idx[:n_eff]

    # Remap by descending weighted N
    raw_wn = {k: w[raw_labels == k].sum() for k in eff_components}
    size_sorted = sorted(eff_components, key=lambda k: raw_wn[k], reverse=True)
    remap = {orig_k: new_k for new_k, orig_k in enumerate(size_sorted)}

    cluster = np.full(len(raw_labels), -1, dtype=int)
    for orig_k, new_k in remap.items():
        cluster[raw_labels == orig_k] = new_k

    unassigned = (cluster == -1).sum()
    if unassigned:
        print(f"  WARNING: {unassigned} respondents unassigned")

    # ── 5. Cluster sizes & factor means ──────────────────────────────────────
    print(f"\n{thin}")
    print("CLUSTER SIZES & FACTOR SCORE PROFILES")
    print(thin)

    col_w = 10
    header = (f"\n  {'Cluster':>7}  {'Wtd N':>8}  {'Wtd%':>6}  "
              + "  ".join(f"{c:>{col_w}}" for c in cluster_cols))
    print(header)
    print("  " + "-" * (len(header) - 3))

    total_w = w.sum()
    cluster_means = {}
    for new_k in range(n_eff):
        mask = cluster == new_k
        wt_n = w[mask].sum()
        pct  = 100.0 * wt_n / total_w
        means = [np.average(X[mask, j], weights=w[mask]) for j in range(len(cluster_cols))]
        cluster_means[new_k] = means
        row = (f"  {new_k:>7}  {wt_n:>8,.0f}  {pct:>5.1f}%  "
               + "  ".join(f"{m:>{col_w}.4f}" for m in means))
        print(row)

    # ── 6. Assignment confidence ──────────────────────────────────────────────
    probs = dpgmm.predict_proba(X)
    max_probs = probs.max(axis=1)
    print(f"\n  Overall mean max-probability:   {max_probs.mean():.4f}")
    print(f"  Fraction with max-prob > 0.90:  {(max_probs > 0.90).mean():.3f}")
    print(f"  Fraction with max-prob > 0.70:  {(max_probs > 0.70).mean():.3f}")

    print(f"\n  {'Cluster':>7}  {'Mean max-prob':>13}  {'Median max-prob':>15}  {'N>0.90':>7}")
    print(f"  {'-'*7}  {'-'*13}  {'-'*15}  {'-'*7}")
    for new_k in range(n_eff):
        mask = cluster == new_k
        mp = max_probs[mask]
        print(f"  {new_k:>7}  {mp.mean():>13.4f}  {np.median(mp):>15.4f}  "
              f"{(mp > 0.90).mean():>7.3f}")

    # ── 7. Validation cross-tabs ──────────────────────────────────────────────
    print(f"\n{thin}")
    print("VALIDATION CROSS-TABS")
    print(thin)

    def wtd_pct(series, labels):
        cats = sorted(series.dropna().unique())
        col_w = 9
        hdr = f"  {'Cluster':>7}  {'Wtd N':>8}  " + "  ".join(f"{labels.get(c,str(c)):>{col_w}}" for c in cats)
        print(f"\n{hdr}")
        print("  " + "-" * len(hdr))
        for new_k in range(n_eff):
            mask_k = cluster == new_k
            total  = w[mask_k].sum()
            vals   = "  ".join(
                f"{100.0 * w[mask_k & (series.values == c)].sum() / total:>{col_w}.1f}%"
                for c in cats
            )
            print(f"  {new_k:>7}  {total:>8,.0f}  {vals}")

    print("\n--- Party ID (pid3: 1=Dem, 2=Rep, 3=Indep) ---")
    wtd_pct(fs["pid3"].round(0), {1.0: "Dem%", 2.0: "Rep%", 3.0: "Ind%"})

    print("\n--- Ideology (ideo5: 1=VLib … 5=VCon) ---")
    wtd_pct(fs["ideo5"].round(0),
            {1.0:"VLib%", 2.0:"Lib%", 3.0:"Mod%", 4.0:"Con%", 5.0:"VCon%"})

    # ── 8. Save ───────────────────────────────────────────────────────────────
    print(f"\n{thin}")
    print("SAVE")
    print(thin)

    out = fs[["pid3", "ideo5", "inputstate", "commonpostweight",
              "govt_trust_imputed"] + cluster_cols].copy()
    out["cluster"] = cluster

    for new_k in range(n_eff):
        orig_k = size_sorted[new_k]
        out[f"prob_cluster_{new_k}"] = probs[:, orig_k]

    out.to_csv(OUT_PATH, index=False)
    print(f"\n  Saved: {OUT_PATH.relative_to(BASE_DIR)}")
    print(f"  Shape: {out.shape[0]:,} rows × {out.shape[1]} columns")
    print(f"  Columns: {list(out.columns)}")

    print(f"\n{'=' * 70}")
    print("DONE")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()

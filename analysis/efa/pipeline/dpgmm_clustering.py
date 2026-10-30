"""
dpgmm_clustering.py
-------------------
Dirichlet Process Gaussian Mixture Model clustering of CES 2024 factor scores.

Input:  efa_factor_scores.csv  (N=45,214; five factor scores + weights + caseid)
        party_id_reference.csv  (caseid -> party id from the ten-party seed-61 typology of
                                 the 2026-10 rescore, so CON = 0 ... PRG = 9 keep their meaning)
Output: typology_cluster_assignments.csv  (hard + soft cluster assignments)
        dpgmm_seed_selection.csv  (per-seed fit diagnostics and agreement)

Factor inputs:
  FS_F1         - Enforcement Orientation (HIGH = enforcement-conservative)
  FS_F2         - Election Distrust (HIGH = distrusts elections)
  FS_F3         - Government Trust (HIGH = distrusts government)
  FS_F4_resid   - Repro Rights / Religion, F1-residualized
  FS_F5_resid   - Values Conservatism, F1-residualized

DPGMM params:
  n_components=9  (a cap, not a discovery: the Dirichlet process fills every component it is
                   given, all 15 at a cap of 15. Nine is the cap whose solution is stable:
                   every seed reaches the same clusters and none dissolves under resampling.
                   analysis/efa/exploration/k_stability/)
  covariance_type='full'
  weight_concentration_prior_type='dirichlet_process'
  n_init=5
  max_iter=2000
  random_state=42..61 (20 seeds)

Seed selection: every seed is fit; seeds that converge with K effective components are
eligible. At K = 9 the 20 seeds land on three solutions (groups of seeds agreeing at ARI >=
0.9): 11 seeds reach the most common one, 6 a better-fitting one, 3 a third. The default
(--select modal) keeps the most common solution, and within it the best lower bound.
The bootstrap re-clusters every draw, so the other solutions are carried in the published
intervals (analysis/bootstrap/recluster.py). --select bound keeps the best lower bound
overall; --select ari keeps the most typical seed by mean ARI. max_iter is 2000 because at 500 most seeds stopped
before converging.

Exploration options (analysis/efa/exploration/seed_sweep/, k9_bootstrap/). Any of them leaves
dpgmm_seed_selection.csv untouched:
  --seed N            fit only seed N and keep it
  --seeds A B ...     fit these seeds; --select bound keeps the best lower bound instead of the ARI medoid
  --n-components K    cap K. Party IDs stay 0-9; with K < 10 the unmatched IDs are empty, their
                      prob_cluster columns all zero
  --reference CSV     caseid -> party_id file to match against (default party_id_reference.csv)
  --resample B        fit on a with-replacement resample of respondents (rng seed 42 + B), then
                      predict labels and posteriors for all respondents
  --out CSV           write the assignments here instead of typology_cluster_assignments.csv

Cluster IDs are party identities, not size ranks. Each new cluster takes the ID of the
previous-typology party it retains most of (Hungarian match on the weighted crosstab via
caseid), so CON = 0 ... PRG = 9 stays valid in the code that hard-codes party IDs.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score
from sklearn.mixture import BayesianGaussianMixture

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "processed"
ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, help="fit only this seed; skip seed selection")
ap.add_argument("--seeds", type=int, nargs="+")
ap.add_argument("--select", choices=["modal", "ari", "bound"], default="modal")
ap.add_argument("--n-components", type=int, default=9)
ap.add_argument("--reference", type=Path, default=DATA_DIR / "party_id_reference.csv")
ap.add_argument("--resample", type=int)
ap.add_argument("--out", type=Path, default=DATA_DIR / "typology_cluster_assignments.csv")
ARGS = ap.parse_args()
SEEDS = [ARGS.seed] if ARGS.seed is not None else ARGS.seeds or range(42, 62)
PRODUCTION_RUN = (ARGS.seed is None and ARGS.seeds is None and ARGS.n_components == ap.get_default("n_components") and ARGS.select == ap.get_default("select") and ARGS.resample is None
                  and ARGS.reference == ap.get_default("reference") and ARGS.out == ap.get_default("out"))
N_PARTIES = 10
K = ARGS.n_components
CLUSTER_COLS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4_resid", "FS_F5_resid"]
COL_LABELS = ["F1(Enf)", "F2(ElDis)", "F3(GovTru)", "F4r(RepRel)", "F5r(ValCon)"]

# ---------------------------------------------------------------------------
# 1. SETUP
# ---------------------------------------------------------------------------
print("=" * 70)
print("SETUP")
print("=" * 70)

fs = pd.read_csv(DATA_DIR / "efa_factor_scores.csv")
print(f"Loaded efa_factor_scores.csv: {fs.shape[0]:,} rows x {fs.shape[1]} cols")
print(f"NaN count in clustering columns: {fs[CLUSTER_COLS].isna().sum().sum()}")
print(f"Total commonpostweight sum: {fs['commonpostweight'].sum():,.1f}")

X = fs[CLUSTER_COLS].values
w = fs["commonpostweight"].values
X_fit = X
if ARGS.resample is not None:
    X_fit = X[np.random.default_rng(42 + ARGS.resample).integers(0, len(X), len(X))]
    print(f"Fitting on resample {ARGS.resample} (rng seed {42 + ARGS.resample}); predicting all {len(X):,}")

# ---------------------------------------------------------------------------
# 2. FIT DPGMM
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("FIT DPGMM")
print("=" * 70)

def fit(seed):
    return BayesianGaussianMixture(
        n_components=K,
        covariance_type='full',
        weight_concentration_prior_type='dirichlet_process',
        n_init=5,
        random_state=seed,
        max_iter=2000,
    ).fit(X_fit)


# Note: BayesianGaussianMixture.fit() does not accept sample_weight in sklearn.
# Fitting is done unweighted on the standardized factor scores; those scores were
# themselves derived from the weighted Thomson regression (weighted polychoric R).
# Survey weights (commonpostweight) are applied to ALL post-fit reporting:
# cluster sizes, factor score means, and validation cross-tabs.
fits = {}
for seed in SEEDS:
    m = fit(seed)
    n_eff_s = int((m.weights_ > 0.01).sum())
    fits[seed] = (m, m.predict(X), n_eff_s)
    print(f"  seed {seed}: converged={m.converged_}  lower bound={m.lower_bound_:.4f}  effective={n_eff_s}")

eligible = [sd for sd, (m, _, ne) in fits.items() if ne == K and m.converged_]


def select_seed():
    """Most typical eligible seed by mean ARI; writes dpgmm_seed_selection.csv."""
    if len(eligible) < 2:
        raise SystemExit(f"Only {len(eligible)} seeds produced {K} effective clusters; stopping.")
    ari = pd.DataFrame([[adjusted_rand_score(fits[a][1], fits[b][1]) for b in eligible] for a in eligible],
                       index=eligible, columns=eligible)
    mean_ari = (ari.sum(axis=1) - 1) / (len(eligible) - 1)
    chosen = int(mean_ari.idxmax())
    if ARGS.select == "bound":
        chosen = max(eligible, key=lambda sd: fits[sd][0].lower_bound_)
    elif ARGS.select == "modal":
        from scipy.sparse.csgraph import connected_components
        _, comp = connected_components((ari.values >= 0.9).astype(int), directed=False)
        modal = [sd for sd, c in zip(eligible, comp) if c == np.bincount(comp).argmax()]
        chosen = max(modal, key=lambda sd: fits[sd][0].lower_bound_)
        print(f"  solutions among eligible seeds: {len(set(comp))}; most common reached by "
              f"{len(modal)} of {len(eligible)} seeds: {modal}")
    table = pd.DataFrame({
        "seed": list(SEEDS),
        "effective_clusters": [fits[sd][2] for sd in SEEDS],
        "converged": [fits[sd][0].converged_ for sd in SEEDS],
        "lower_bound": [fits[sd][0].lower_bound_ for sd in SEEDS],
        "mean_ari_vs_other_seeds": [mean_ari.get(sd, np.nan) for sd in SEEDS],
        "chosen": [sd == chosen for sd in SEEDS],
    }).round(4)
    if PRODUCTION_RUN:
        table.to_csv(DATA_DIR / "dpgmm_seed_selection.csv", index=False)
    else:
        print(table.to_string(index=False))
    print(f"\nEligible seeds: {len(eligible)} of {len(SEEDS)}; mean ARI range "
          f"{mean_ari.min():.3f}-{mean_ari.max():.3f}; chosen seed {chosen} by {ARGS.select} "
          f"(mean ARI {mean_ari[chosen]:.3f})")
    return chosen


if ARGS.seed is None:
    chosen = select_seed()
elif eligible == [ARGS.seed]:
    chosen = ARGS.seed
    print(f"\n--seed {chosen}: seed selection skipped, dpgmm_seed_selection.csv not written")
else:
    raise SystemExit(f"Seed {ARGS.seed} did not converge to {K} effective clusters; stopping.")
dpgmm, raw_labels, n_eff = fits[chosen]

# ---------------------------------------------------------------------------
# 3. PARTY IDS (match to the previous typology by caseid)
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("PARTY IDS")
print("=" * 70)

ref = pd.read_csv(ARGS.reference)
prev = fs[["caseid"]].merge(ref, on="caseid", how="left")["party_id"].values
assert not np.isnan(prev).any(), f"respondents missing from {ARGS.reference.name}"
eff_components = [k for k in np.argsort(dpgmm.weights_)[::-1] if dpgmm.weights_[k] > 0.01]
ct = pd.crosstab(raw_labels, prev, values=w, aggfunc="sum").reindex(
    index=eff_components, columns=range(N_PARTIES)).fillna(0)
retention = ct.values / ct.values.sum(axis=0, keepdims=True)
ri, ci = linear_sum_assignment(-retention)
remap = {int(ct.index[r]): int(c) for r, c in zip(ri, ci)}
id_to_component = {v: k for k, v in remap.items()}
present = sorted(id_to_component)  # party IDs that hold a cluster; all ten unless K < 10
for pid in sorted(set(range(N_PARTIES)) - set(present)):
    print(f"  party id {pid}: no cluster (K = {K}); prob_cluster_{pid} written as zeros")
for comp, pid in sorted(remap.items(), key=lambda kv: kv[1]):
    print(f"  component {comp:>2} -> party id {pid}: retains {retention[list(ct.index).index(comp), pid]:.1%} "
          f"of that party's previous weight")

cluster = np.full(len(raw_labels), -1, dtype=int)
for orig_k, new_k in remap.items():
    cluster[raw_labels == orig_k] = new_k

print(f"\n  {'Cluster':>7}  {'Unweighted N':>13}  {'Weighted N':>11}  {'Weighted %':>11}")
print(f"  {'-'*7}  {'-'*13}  {'-'*11}  {'-'*11}")
total_w = w.sum()
for new_k in present:
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
for new_k in present:
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
for new_k in present:
    mask = cluster == new_k
    mp = max_probs[mask]
    print(f"  {new_k:>7}  {mp.mean():>13.4f}  {np.median(mp):>15.4f}  {(mp > 0.90).mean():>9.3f}")

# ---------------------------------------------------------------------------
# 7. SAVE CLUSTER ASSIGNMENTS
# ---------------------------------------------------------------------------
print("\n" + "=" * 70)
print("SAVE CLUSTER ASSIGNMENTS")
print("=" * 70)

save_cols = ["pid3", "ideo5", "inputstate", "commonpostweight"] + CLUSTER_COLS

out = fs[save_cols].copy()
out["cluster"] = cluster

# Save soft assignment probabilities for effective clusters only
# Use remapped indices: column prob_cluster_k corresponds to new cluster k
for new_k in range(N_PARTIES):
    out[f"prob_cluster_{new_k}"] = probs[:, id_to_component[new_k]] if new_k in present else 0.0

out["caseid"] = fs["caseid"].values
out_path = ARGS.out
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
    for new_k in present:
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
    for new_k in present:
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

# --- 8d. Mean FS_F2 and FS_F3 per cluster ---
print("\n--- Mean FS_F2 (Election Distrust) and FS_F3 (Govt Trust) per cluster ---")
f2_vals = fs["FS_F2"].values
f3_vals = fs["FS_F3"].values
print(f"\n  {'Cluster':>7}  {'Wtd N':>8}  {'Mean F2(ElDis)':>15}  {'Mean F3(GovTru)':>16}")
print(f"  {'-'*7}  {'-'*8}  {'-'*15}  {'-'*16}")
for new_k in present:
    mask = cluster == new_k
    wt_n = w[mask].sum()
    mean_f2 = np.average(f2_vals[mask], weights=w[mask])
    mean_f3 = np.average(f3_vals[mask], weights=w[mask])
    print(f"  {new_k:>7}  {wt_n:>8,.0f}  {mean_f2:>15.4f}  {mean_f3:>16.4f}")

print("\n" + "=" * 70)
print("DONE")
print("=" * 70)

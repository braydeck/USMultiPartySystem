"""DPGMM clustering + cross-set matching — extracted from the frozen 2024 pipeline.

Sources:
  - DPGMM config + remap-by-weighted-N   ← analysis/efa/pipeline/dpgmm_clustering.py
  - Hungarian centroid matching (zc)     ← analysis/efa/exploration/cluster_survival_k4_k5.py
  - cramers_v_weighted                   ← analysis/efa/pipeline/efa_update.py
"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
from sklearn.mixture import BayesianGaussianMixture
from sklearn.metrics import adjusted_rand_score
from scipy.optimize import linear_sum_assignment

# Production party codes in cluster-id order (add_compare_items.py CODES).
PARTY_CODES = ["CON", "LBR", "STY", "NAT", "LIB", "POP", "CUP", "OAO", "DSA", "PRG"]


def dpgmm_fit(X, n_components=10, seed=42):
    """Fit the production DPGMM (unweighted, per sklearn limitation). Returns the
    fitted model plus raw predict labels and probabilities."""
    m = BayesianGaussianMixture(
        n_components=n_components, covariance_type="full",
        weight_concentration_prior_type="dirichlet_process",
        n_init=5, max_iter=500, random_state=seed,
    ).fit(X)
    return m, m.predict(X), m.predict_proba(X)


def remap_by_weighted_n(raw_labels, w, weights_, thresh=0.01):
    """Keep effective components (mixture weight > thresh), relabel 0..n-1 by
    descending weighted N. Matches dpgmm_clustering.py. Returns (cluster, size_sorted)."""
    sorted_idx = np.argsort(weights_)[::-1]
    n_eff = int((weights_ > thresh).sum())
    eff = sorted_idx[:n_eff]
    wn = {k: w[raw_labels == k].sum() for k in eff}
    size_sorted = sorted(eff, key=lambda k: wn[k], reverse=True)
    remap = {orig: new for new, orig in enumerate(size_sorted)}
    cluster = np.full(len(raw_labels), -1, dtype=int)
    for orig, new in remap.items():
        cluster[raw_labels == orig] = new
    return cluster, size_sorted


def weighted_centroids(X, cluster, w, n):
    """Weighted mean of each column of X within clusters 0..n-1."""
    C = np.zeros((n, X.shape[1]))
    for k in range(n):
        mask = cluster == k
        if mask.sum() == 0:
            C[k] = np.nan
            continue
        ww = w[mask] / w[mask].sum()
        C[k] = (ww[:, None] * X[mask]).sum(0)
    return C


def _zc(M):
    return (M - np.nanmean(M, 0)) / (np.nanstd(M, 0) + 1e-9)


def hungarian_match(centroids_from, centroids_to):
    """Optimal 1:1 assignment of `from` rows to `to` rows by Euclidean distance in
    z-scored centroid space. Returns (mapping dict from_idx->to_idx, distances)."""
    fz, tz = _zc(centroids_from), _zc(centroids_to)
    cost = np.linalg.norm(fz[:, None, :] - tz[None, :, :], axis=2)
    ri, ci = linear_sum_assignment(cost)
    mapping = {int(ri[i]): int(ci[i]) for i in range(len(ri))}
    dists = {int(ri[i]): float(cost[ri[i], ci[i]]) for i in range(len(ri))}
    return mapping, dists


def cramers_v_weighted(group_labels, cat_labels, weights):
    """Weighted Cramér's V between a grouping and a categorical (e.g. quartile × pid3)."""
    groups = sorted(np.unique(group_labels))
    cats = sorted(np.unique(cat_labels))
    table = np.zeros((len(groups), len(cats)))
    for gi, g in enumerate(groups):
        for ci, c in enumerate(cats):
            mask = (group_labels == g) & (cat_labels == c)
            table[gi, ci] = weights[mask].sum()
    N = table.sum()
    row = table.sum(axis=1, keepdims=True)
    col = table.sum(axis=0, keepdims=True)
    expected = row @ col / N
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2 = np.sum((table - expected) ** 2 / np.where(expected > 0, expected, np.inf))
    k = min(table.shape[0] - 1, table.shape[1] - 1)
    V = np.sqrt(chi2 / (N * k)) if k > 0 and N > 0 else 0.0
    return float(V), float(chi2), float(N)


def ari(a, b):
    return float(adjusted_rand_score(a, b))

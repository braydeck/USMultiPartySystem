"""Do more parties describe voters better on the questions they were not clustered on?

Data: CES 2024 DTA via pipeline/archive/cluster_profile_viz.load_data() (n = 45,214, same mask
and positional join as production), factor scores from data/processed/efa_factor_scores.csv.
Outcomes: every scalar profile item in that script's ITEM_META except the 24 clustering items
(binary items as % choosing option 1; ordinal, Likert and trust items on their own scale,
missing codes dropped).

For each party cap K = 6..14: 5-fold cross-validation (fold assignment rng 42). The DPGMM
(production settings, n_init 3, random_state 42) is fit on four folds; held-out respondents are
assigned to clusters and predicted as their cluster's training-fold weighted mean. Score per
item = weighted held-out R^2, 1 - SSE / SST around the training mean. Reference ceiling: a
weighted linear regression on the five continuous factor scores, same folds.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.mixture import BayesianGaussianMixture

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "pipeline" / "archive"))
import cluster_profile_viz as cpv  # noqa: E402

OUT = Path(__file__).parent / "outputs"
COLS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4_resid", "FS_F5_resid"]
KS = range(6, 15)
FOLDS = 5


def outcomes(df):
    Y = {}
    for v, m in cpv.ITEM_META.items():
        if v in cpv.ITEMS_24 or v not in df.columns or m.get("heatmap_stat") is None:
            continue
        s = df[v].where(~df[v].isin(m.get("missing", cpv.MISSING_STD)))
        Y[v] = (s == 1).astype(float).where(s.notna()) if m["heatmap_stat"] == "pct1" else s.astype(float)
    return pd.DataFrame(Y)


def r2_items(pred, Y, w, test, ybar):
    out = {}
    for j, c in enumerate(Y.columns):
        y = Y[c].values[test]
        ok = ~np.isnan(y)
        if ok.sum() < 100:
            continue
        sse = np.sum(w[test][ok] * (y[ok] - pred[ok, j]) ** 2)
        sst = np.sum(w[test][ok] * (y[ok] - ybar[j]) ** 2)
        out[c] = 1 - sse / sst
    return out


def wmeans(Y, w, idx):
    M = Y.values[idx]
    W = np.where(np.isnan(M), 0, w[idx][:, None])
    return np.nansum(np.nan_to_num(M) * W, axis=0) / np.maximum(W.sum(axis=0), 1e-12)


def cluster_fold(X, Y, w, folds, K, f):
    train, test = folds != f, folds == f
    m = BayesianGaussianMixture(n_components=K, covariance_type="full", weight_concentration_prior_type="dirichlet_process",
                                n_init=3, random_state=42, max_iter=2000).fit(X[train])
    lt, ls = m.predict(X[train]), m.predict(X[test])
    ybar = wmeans(Y, w, np.where(train)[0])
    means = {k: wmeans(Y, w, np.where(train)[0][lt == k]) for k in np.unique(lt)}
    pred = np.array([means.get(k, ybar) for k in ls])
    return {"K": K, "fold": f, **r2_items(pred, Y, w, test, ybar)}


def linear_fold(X, Y, w, folds, f):
    train, test = folds != f, folds == f
    ybar = wmeans(Y, w, np.where(train)[0])
    A = np.column_stack([np.ones(len(X)), X])
    pred = np.empty((test.sum(), Y.shape[1]))
    for j, c in enumerate(Y.columns):
        y = Y[c].values
        ok = train & ~np.isnan(y)
        sw = np.sqrt(w[ok])
        beta = np.linalg.lstsq(A[ok] * sw[:, None], y[ok] * sw, rcond=None)[0]
        pred[:, j] = A[test] @ beta
    return {"K": "linear", "fold": f, **r2_items(pred, Y, w, test, ybar)}


def main():
    OUT.mkdir(exist_ok=True)
    df = cpv.load_data()
    fs = pd.read_csv(ROOT / "data/processed/efa_factor_scores.csv")
    assert len(fs) == len(df)
    X, w = fs[COLS].values, fs["commonpostweight"].values
    Y = outcomes(df)
    print(f"{Y.shape[1]} outcome items", flush=True)
    folds = np.random.default_rng(42).integers(0, FOLDS, len(X))
    jobs = [delayed(cluster_fold)(X, Y, w, folds, K, f) for K in KS for f in range(FOLDS)]
    rows = Parallel(n_jobs=6, verbose=5)(jobs) + [linear_fold(X, Y, w, folds, f) for f in range(FOLDS)]
    long = pd.DataFrame(rows).melt(id_vars=["K", "fold"], var_name="item", value_name="r2").dropna()
    long.to_csv(OUT / "k_validity_by_item.csv", index=False)
    per_item = long.groupby(["K", "item"]).r2.mean().reset_index()
    s = per_item.groupby("K").r2.agg(mean_r2="mean", median_r2="median").round(4)
    s["items"] = per_item.groupby("K").size()
    s.to_csv(OUT / "k_validity_summary.csv")
    print(s.to_string())


if __name__ == "__main__":
    main()

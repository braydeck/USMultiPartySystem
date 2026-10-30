"""Fair stability comparison of party counts and clustering methods.

Data: data/processed/efa_factor_scores.csv (rescored 2026-10, n = 45,214), clustering inputs
FS_F1, FS_F2, FS_F3, FS_F4_resid, FS_F5_resid. Party labels for interpretation:
data/processed/party_id_reference.csv (the ten-party seed-61 typology), joined by caseid.

Why: the first scan (k_stability.py) scored each cap against the best of 5 full-data seeds.
At cap 9 that reference was the most common solution; at cap 10 it was not, so the comparison
was tilted. This one uses no external reference.

For each method in {dpgmm, gmm, kmeans} and K = 8..11:
  - 20 full-data fits, seeds 42-61. Seed agreement = mean pairwise ARI. Solutions = connected
    groups of seeds whose labels agree at ARI >= 0.9; reported as the number of solutions and
    the share of seeds in the most common one.
  - 30 resample fits (rng 42 + b, with replacement), each predicted back onto all respondents.
    Resample agreement = mean pairwise ARI among the 30. The medoid resample fit (highest mean
    ARI to the others) is the reference for per-party stability: each of its clusters scores
    its mean best Jaccard overlap across the other 29 (>= 0.75 stable, < 0.5 dissolved,
    Hennig's convention). Each medoid cluster is labeled by its largest seed-61 party.
dpgmm = production settings (full covariance, Dirichlet process prior, n_init 5, max_iter 2000).
gmm = finite GaussianMixture, same covariance and n_init. kmeans = n_init 10.
HDBSCAN (density-based, chooses its own number of clusters, leaves low-density points as noise)
runs on full data at three minimum cluster sizes, to see which groups stand out as separate
dense regions at all.
Unweighted fits, as in production. Rerunnable end to end; seeds fixed.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.sparse.csgraph import connected_components
from sklearn.cluster import HDBSCAN, KMeans
from sklearn.metrics import adjusted_rand_score as ari
from sklearn.mixture import BayesianGaussianMixture, GaussianMixture

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).parent / "outputs" / "fair"
COLS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4_resid", "FS_F5_resid"]
PARTY = {0: "CON", 1: "LBR", 2: "STY", 3: "NAT", 4: "LIB", 5: "POP", 6: "CUP", 7: "OAO", 8: "DSA", 9: "PRG"}
METHODS = ("dpgmm", "gmm", "kmeans")
KS = (8, 9, 10, 11)
SEEDS = range(42, 62)
N_BOOT = 30


def model(method, K, seed):
    if method == "dpgmm":
        return BayesianGaussianMixture(n_components=K, covariance_type="full",
                                       weight_concentration_prior_type="dirichlet_process",
                                       n_init=5, random_state=seed, max_iter=2000)
    if method == "gmm":
        return GaussianMixture(n_components=K, covariance_type="full", n_init=5, random_state=seed, max_iter=2000)
    return KMeans(n_clusters=K, n_init=10, random_state=seed)


def job(X, method, K, kind, i):
    if kind == "seed":
        m = model(method, K, i).fit(X)
    else:
        idx = np.random.default_rng(42 + i).integers(0, len(X), len(X))
        m = model(method, K, 1000 + i).fit(X[idx])
    labels = m.predict(X).astype(np.int8)
    bound = getattr(m, "lower_bound_", None)
    if method == "kmeans":
        bound = -m.inertia_
    return method, K, kind, i, labels, float(bound)


def pairwise_ari(L):
    n = len(L)
    M = np.eye(n)
    for a in range(n):
        for b in range(a + 1, n):
            M[a, b] = M[b, a] = ari(L[a], L[b])
    return M


def best_jaccard(ref, other):
    out = []
    for c in np.unique(ref):
        a = ref == c
        out.append(max((a & (other == d)).sum() / (a | (other == d)).sum() for d in np.unique(other)))
    return np.array(out)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fs = pd.read_csv(ROOT / "data/processed/efa_factor_scores.csv")
    ref = pd.read_csv(ROOT / "data/processed/party_id_reference.csv")
    party = fs[["caseid"]].merge(ref, on="caseid", how="left")["party_id"].map(PARTY).values
    X, w = fs[COLS].values, fs["commonpostweight"].values

    jobs = [delayed(job)(X, m, K, kind, i) for m in METHODS for K in KS
            for kind, rng in (("seed", SEEDS), ("boot", range(N_BOOT))) for i in rng]
    res = Parallel(n_jobs=11, verbose=2)(jobs)
    store = {}
    for method, K, kind, i, labels, bound in res:
        store.setdefault((method, K, kind), []).append((i, labels, bound))
    np.savez_compressed(OUT / "labels.npz", **{f"{m}_{K}_{k}": np.stack([l for _, l, _ in sorted(v, key=lambda t: t[0])])
                                               for (m, K, k), v in store.items()})

    summary, clusters = [], []
    for method in METHODS:
        for K in KS:
            seeds = sorted(store[(method, K, "seed")], key=lambda t: t[0])
            S = pairwise_ari([l for _, l, _ in seeds])
            n_sol, comp = connected_components(S >= 0.9, directed=False)
            sizes = np.bincount(comp)
            best_seed = max(seeds, key=lambda t: t[2])
            best_family_share = sizes[comp[seeds.index(best_seed)]] / len(seeds)

            boots = [l for _, l, _ in sorted(store[(method, K, "boot")], key=lambda t: t[0])]
            B = pairwise_ari(boots)
            off = B[~np.eye(len(B), dtype=bool)]
            med = int(np.argmax((B.sum(axis=1) - 1) / (len(B) - 1)))
            J = np.array([best_jaccard(boots[med], boots[j]) for j in range(len(boots)) if j != med])
            mj = J.mean(axis=0)
            for c, cl in enumerate(np.unique(boots[med])):
                m = boots[med] == cl
                comp_ = pd.Series(w[m]).groupby(party[m]).sum().sort_values(ascending=False) / w[m].sum()
                clusters.append({"method": method, "K": K, "share": round(w[m].sum() / w.sum() * 100, 1),
                                 "largest_party": comp_.index[0], "largest_party_pct": round(comp_.iloc[0] * 100, 0),
                                 "second": f"{comp_.index[1]} {comp_.iloc[1] * 100:.0f}" if len(comp_) > 1 else "",
                                 "mean_jaccard": round(float(mj[c]), 3)})
            summary.append({"method": method, "K": K,
                            "seed_ari_mean": round(float(S[~np.eye(len(S), dtype=bool)].mean()), 3),
                            "n_solutions": int(n_sol), "modal_solution_share": round(sizes.max() / len(seeds), 2),
                            "best_fit_solution_share": round(float(best_family_share), 2),
                            "resample_ari_mean": round(float(off.mean()), 3),
                            "resample_ari_q10": round(float(np.quantile(off, 0.1)), 3),
                            "n_stable": int((mj >= 0.75).sum()), "n_dissolved": int((mj < 0.5).sum())})
    s = pd.DataFrame(summary)
    s.to_csv(OUT / "summary.csv", index=False)
    pd.DataFrame(clusters).to_csv(OUT / "clusters.csv", index=False)
    print(s.to_string(index=False), flush=True)

    rows = []
    for mcs in (250, 500, 1000):
        lab = HDBSCAN(min_cluster_size=mcs, min_samples=25).fit_predict(X)
        for c in sorted(set(lab)):
            m = lab == c
            comp_ = pd.Series(w[m]).groupby(party[m]).sum().sort_values(ascending=False) / w[m].sum()
            rows.append({"min_cluster_size": mcs, "cluster": int(c), "share": round(w[m].sum() / w.sum() * 100, 1),
                         "composition": ", ".join(f"{p} {v * 100:.0f}" for p, v in comp_.items() if v >= 0.08)})
        print(f"HDBSCAN min_cluster_size {mcs}: {len(set(lab)) - (-1 in lab)} clusters, "
              f"noise {w[lab == -1].sum() / w.sum() * 100:.1f}%", flush=True)
    pd.DataFrame(rows).to_csv(OUT / "hdbscan.csv", index=False)


if __name__ == "__main__":
    main()

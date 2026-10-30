"""How many parties does the rescored factor space support, and how stable is each solution?

Data: data/processed/efa_factor_scores.csv (rescored 2026-10, n = 45,214), the five clustering
inputs FS_F1, FS_F2, FS_F3, FS_F4_resid, FS_F5_resid. Model: the production DPGMM
(full covariance, Dirichlet process prior, max_iter 2000).

Why: at n_components = 10 and 15 every component carries > 1% of weight, so the number of
parties is set by the cap, not found by the Dirichlet process. This script scores each cap
K = 6..14 on stability rather than fit (the evidence lower bound keeps rising with K):
  - seed agreement: ARI among 5 full-data fits (seeds 42-46, n_init 5); reference = best bound
  - bootstrap stability: 30 respondent resamples (rng 42+b), each fit with n_init 3 and
    predicted back onto all 45,214; ARI vs the reference, and per reference cluster the best
    Jaccard overlap (Hennig's clusterboot convention: >= 0.75 stable, < 0.5 dissolved)
Unweighted fit, as in production. Rerunnable end to end; ~1 h on 11 cores.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import adjusted_rand_score
from sklearn.mixture import BayesianGaussianMixture

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).parent / "outputs"
COLS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4_resid", "FS_F5_resid"]
KS = range(6, 15)
REF_SEEDS = range(42, 47)
N_BOOT = 30


def fit(X, K, seed, n_init):
    return BayesianGaussianMixture(n_components=K, covariance_type="full",
                                   weight_concentration_prior_type="dirichlet_process",
                                   n_init=n_init, random_state=seed, max_iter=2000).fit(X)


def ref_job(X, K, seed):
    m = fit(X, K, seed, 5)
    return {"K": K, "seed": seed, "bound": m.lower_bound_, "converged": m.converged_,
            "eff": int((m.weights_ > 0.01).sum()), "labels": m.predict(X)}


def boot_job(X, K, b):
    idx = np.random.default_rng(42 + b).integers(0, len(X), len(X))
    m = fit(X[idx], K, b, 3)
    return {"K": K, "b": b, "converged": m.converged_, "labels": m.predict(X)}


def best_jaccard(ref, other):
    out = []
    for c in np.unique(ref):
        a = ref == c
        out.append(max((a & (other == d)).sum() / (a | (other == d)).sum() for d in np.unique(other)))
    return np.array(out)


def main():
    OUT.mkdir(exist_ok=True)
    X = pd.read_csv(ROOT / "data/processed/efa_factor_scores.csv")[COLS].values
    jobs = [delayed(ref_job)(X, K, s) for K in KS for s in REF_SEEDS] + \
           [delayed(boot_job)(X, K, b) for K in KS for b in range(N_BOOT)]
    res = Parallel(n_jobs=11, verbose=5)(jobs)
    refs = [r for r in res if "seed" in r]
    boots = [r for r in res if "b" in r]

    summary, clusters = [], []
    for K in KS:
        rk = [r for r in refs if r["K"] == K]
        best = max(rk, key=lambda r: r["bound"])
        seed_ari = [adjusted_rand_score(a["labels"], b["labels"]) for i, a in enumerate(rk) for b in rk[i + 1:]]
        bk = [r for r in boots if r["K"] == K]
        ari = [adjusted_rand_score(best["labels"], r["labels"]) for r in bk]
        J = np.array([best_jaccard(best["labels"], r["labels"]) for r in bk])
        sizes = np.bincount(best["labels"], minlength=K) / len(X)
        for c in range(J.shape[1]):
            clusters.append({"K": K, "cluster": c, "share": round(float(sizes[np.unique(best["labels"])[c]]), 4),
                             "mean_jaccard": round(float(J[:, c].mean()), 3),
                             "share_draws_ge_075": round(float((J[:, c] >= 0.75).mean()), 3)})
        summary.append({"K": K, "best_bound": round(best["bound"], 1), "best_seed": best["seed"],
                        "eff_clusters": best["eff"], "seed_ari_mean": round(float(np.mean(seed_ari)), 3),
                        "seed_ari_min": round(float(np.min(seed_ari)), 3),
                        "boot_ari_median": round(float(np.median(ari)), 3),
                        "boot_ari_q10": round(float(np.quantile(ari, 0.1)), 3),
                        "n_stable_clusters": int((J.mean(axis=0) >= 0.75).sum()),
                        "n_dissolved_clusters": int((J.mean(axis=0) < 0.5).sum()),
                        "boot_converged": int(sum(r["converged"] for r in bk))})
        np.save(OUT / f"ref_labels_K{K}.npy", best["labels"])
    s = pd.DataFrame(summary)
    s.to_csv(OUT / "k_summary.csv", index=False)
    pd.DataFrame(clusters).to_csv(OUT / "k_cluster_stability.csv", index=False)
    print(s.to_string(index=False))


if __name__ == "__main__":
    main()

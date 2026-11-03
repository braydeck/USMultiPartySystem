"""Does the ANES cluster count depend on the DPGMM? Run k-means and a finite Gaussian mixture through the same rule.

Data: outputs/clustering/independent_available/independent_clusters.csv (n = 4,673, ten factors), clustering inputs
after the anchor rule (dims_check.residualize).

Methods, as in analysis/efa/exploration/k_stability/fair_compare.py (CES): gmm = finite GaussianMixture, full
covariance, n_init 5; kmeans = n_init 10. For each K = 2..10: 20 full-data seeds (42-61) and 30 resample fits
(rng 42 + b, predicted back onto every respondent). A cluster dissolves when its mean best Jaccard across resamples
is < 0.5; the kept K is the largest with none dissolved, the rule that kept DPGMM cap 4. GMM also reports BIC
(lower = better fit), the usual fit-based choice of K, from the best of the 20 seeds.
Each method's kept solution is compared with the production four segments.

Writes outputs/clustering/methods_check/{caps.csv, crosswalk_<method>.csv, run.log}.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import itertools

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.sparse.csgraph import connected_components
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture

import dims_check as dk
import independent_clustering as ic
import matched_efa as me
import recode_matched as rm
from common import clustering as cl

SRC = me.OUT / "clustering" / "independent_available"
OUT = me.OUT / "clustering" / "methods_check"
SEGMENTS = {0: "center-left moderates", 1: "religious conservatives", 2: "secular progressives", 3: "young disaffected"}


def model(method, K, seed):
    if method == "gmm":
        return GaussianMixture(n_components=K, covariance_type="full", n_init=5, random_state=seed, max_iter=2000)
    return KMeans(n_clusters=K, n_init=10, random_state=seed)


def job(X, method, K, kind, i):
    if kind == "seed":
        m = model(method, K, i).fit(X)
    else:
        m = model(method, K, 1000 + i).fit(X[np.random.default_rng(42 + i).integers(0, len(X), len(X))])
    bic = m.bic(X) if method == "gmm" else np.nan
    return method, K, kind, i, m.predict(X).astype(np.int8), bic


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lab = pd.read_csv(SRC / "independent_clusters.csv")
    raw = pd.read_csv(rm.ANES_CSV, usecols=["V240001", rm.WEIGHT], low_memory=False).apply(pd.to_numeric, errors="coerce")
    w = lab[["caseid"]].merge(raw.rename(columns={"V240001": "caseid"}), on="caseid")[rm.WEIGHT].values
    X = dk.residualize(lab[[c for c in lab.columns if c.startswith("F_")]].values, w)

    jobs = [delayed(job)(X, mth, K, kind, i) for mth in ("kmeans", "gmm") for K in ic.KS
            for kind, rng in (("seed", ic.SEEDS), ("boot", range(ic.N_BOOT))) for i in rng]
    store = {}
    for mth, K, kind, i, l, bic in Parallel(n_jobs=11)(jobs):
        store.setdefault((mth, K, kind), []).append((i, l, bic))

    rows, kept_lab = [], {}
    for mth in ("kmeans", "gmm"):
        for K in ic.KS:
            seeds = sorted(store[(mth, K, "seed")], key=lambda t: t[0])
            S = ic.pairwise([l for _, l, _ in seeds])
            n_sol, comp = connected_components(S >= 0.9, directed=False)
            boots = [l for _, l, _ in sorted(store[(mth, K, "boot")], key=lambda t: t[0])]
            B = ic.pairwise(boots)
            med = int(np.argmax(B.sum(axis=1)))
            mj = np.array([ic.best_jaccard(boots[med], boots[j]) for j in range(len(boots)) if j != med]).mean(axis=0)
            modal = np.bincount(comp).argmax()
            rows.append({"method": mth, "K": K, "n_solutions": int(n_sol),
                         "modal_solution_share": round(np.bincount(comp).max() / len(seeds), 2),
                         "resample_ari_mean": round(float(B[~np.eye(len(B), dtype=bool)].mean()), 3),
                         "n_stable": int((mj >= 0.75).sum()), "n_dissolved": int((mj < 0.5).sum()),
                         "bic": round(min(b for _, _, b in seeds)) if mth == "gmm" else None})
            kept_lab[(mth, K)] = [l for (_, l, _), c in zip(seeds, comp) if c == modal][0]
    caps = pd.DataFrame(rows)
    caps.to_csv(OUT / "caps.csv", index=False)
    print(caps.to_string(index=False), flush=True)

    old = lab.cluster.map(SEGMENTS).values
    for mth in ("kmeans", "gmm"):
        s = caps[caps.method == mth]
        K = dk.kept(s)
        if K is None:
            print(f"\n{mth}: no K free of dissolving clusters")
            continue
        new = kept_lab[(mth, K)]
        print(f"\n{mth}: kept K {K}; ARI vs production four segments {cl.ari(lab.cluster.values, new):.2f}")
        ct = pd.crosstab(pd.Series(old, name="production"), pd.Series(new, name=mth), values=w, aggfunc="sum",
                         normalize="index").round(2)
        ct.to_csv(OUT / f"crosswalk_{mth}.csv")
        print(ct.to_string())
    g = caps[caps.method == "gmm"]
    print(f"\ngmm BIC is lowest at K = {int(g.loc[g.bic.idxmin(), 'K'])} (range searched 2-10)")


if __name__ == "__main__":
    main()

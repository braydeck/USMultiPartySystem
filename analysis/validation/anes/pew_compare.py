"""ANES under a Pew-style typology choice: k-means at K = 4..10 on the Stage C clustering space, with how reliably
each group comes back under resampling.

Pew (2021 typology) and More in Common (Hidden Tribes) chose their group counts by judgment from k-means or
hierarchical solutions, with no test that each group survives a resample. This script lays out what that judgment
would see in ANES, and adds the per-group resample check our cap rule uses.

Data: outputs/stage_c/independent_clusters.csv (n = 4,634; stage_c_export.py). Clustering inputs are the eight
factors that pass the §3c entry test (outputs/stage_c/factors.csv), anchor-residualized (dims_check.residualize),
as the Stage C DPGMM used. Groups are described on all ten factors standardized to the weighted sample (high = the
end that goes with conservative self-placement), plus vote and ideology (describe_clusters.descriptors).

For each K: k-means n_init 10. Reference solution = seed 42 on the full data. Seeds 42-61 count distinct solutions
(ARI >= 0.9 = same). 30 resample fits (rng 42 + b) are predicted back onto every respondent; each reference group's
stability is its mean best Jaccard across them (>= 0.75 stable, < 0.5 dissolves; the cap rule's thresholds).
Variance explained on the full data; mean silhouette on a seeded 2,000-respondent sample.

Writes outputs/clustering/pew_compare/{summary.csv, groups.csv, crosswalk_k<K>.csv, run.log}.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.sparse.csgraph import connected_components
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

import describe_clusters as dc
import dims_check as dk
import independent_clustering as ic
import matched_efa as me

SRC = me.OUT / "stage_c"
OUT = me.OUT / "clustering" / "pew_compare"
KS = range(4, 11)
DPGMM = {0: "religious conservatives", 1: "young disaffected", 2: "center-left moderates", 3: "secular progressives"}
SHORT = {"Immigration and diversity": "immig", "Democratic norms": "norms_discount",
         "Trust in institutions (CSES)": "inst_trust*", "Leave decisions to experts or business (CSES)": "experts_biz*",
         "Foreign threats": "threats", "Religion and social traditionalism": "religion", "Rural resentment": "rural",
         "Government role in the economy": "small_govt", "Gun policy": "anti_gunctl", "Ukraine and Israel aid": "oppose_aid"}


def job(X, K, kind, i):
    if kind == "seed":
        return K, kind, i, KMeans(n_clusters=K, n_init=10, random_state=i).fit(X).labels_.astype(np.int8)
    idx = np.random.default_rng(42 + i).integers(0, len(X), len(X))
    return K, kind, i, KMeans(n_clusters=K, n_init=10, random_state=1000 + i).fit(X[idx]).predict(X).astype(np.int8)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lab = pd.read_csv(SRC / "independent_clusters.csv")
    fac = pd.read_csv(SRC / "factors.csv")
    names = list(fac.factor)
    d = lab[["caseid"]].merge(dc.descriptors()[0], on="caseid", how="left")
    w = d.w.values
    F = lab[[f"F_{n}" for n in names]].values
    X = dk.residualize(F[:, fac.clusters.values], w)
    mu = np.average(F, axis=0, weights=w)
    Fz = (F - mu) / np.sqrt(np.average((F - mu) ** 2, axis=0, weights=w))

    jobs = [delayed(job)(X, K, kind, i) for K in KS
            for kind, rng in (("seed", ic.SEEDS), ("boot", range(ic.N_BOOT))) for i in rng]
    store = {}
    for K, kind, i, l in Parallel(n_jobs=11)(jobs):
        store.setdefault((K, kind), {})[i] = l

    sub = np.random.default_rng(42).choice(len(X), 2000, replace=False)
    total = ((X - X.mean(axis=0)) ** 2).sum()
    summ, groups = [], []
    for K in KS:
        seeds = [store[(K, "seed")][i] for i in ic.SEEDS]
        n_sol, _ = connected_components(ic.pairwise(seeds) >= 0.9, directed=False)
        ref = seeds[0]
        boots = [store[(K, "boot")][i] for i in range(ic.N_BOOT)]
        stab = np.array([ic.best_jaccard(ref, b) for b in boots]).mean(axis=0)
        inertia = sum(((X[ref == c] - X[ref == c].mean(axis=0)) ** 2).sum() for c in range(K))
        ideo = [np.average(d.ideo.values[(ref == c) & d.ideo.notna().values],
                           weights=w[(ref == c) & d.ideo.notna().values]) for c in range(K)]
        order = np.argsort(ideo)
        g = np.empty_like(ref)
        for new, old in enumerate(order):
            g[ref == old] = new
        stab = stab[order]
        summ.append({"K": K, "n_solutions_20_seeds": int(n_sol), "variance_explained": round(1 - inertia / total, 3),
                     "silhouette": round(float(silhouette_score(X[sub], ref[sub])), 3),
                     "n_stable": int((stab >= 0.75).sum()), "n_dissolved": int((stab < 0.5).sum()),
                     "min_group_stability": round(float(stab.min()), 2)})
        for c in range(K):
            m = g == c
            v = d.vote.values[m]
            oki = ~np.isnan(d.ideo.values[m])
            groups.append({"K": K, "group": c + 1, "share": round(w[m].sum() / w.sum(), 3), "n": int(m.sum()),
                           "stability": round(float(stab[c]), 2),
                           "harris": round(float(np.average(v == "Harris", weights=w[m])), 2),
                           "trump": round(float(np.average(v == "Trump", weights=w[m])), 2),
                           "no_vote": round(float(np.average(np.isin(v, ["Did not vote / missing", "No post interview"]),
                                                             weights=w[m])), 2),
                           "ideology": round(float(np.average(d.ideo.values[m][oki], weights=w[m][oki])), 1),
                           **{SHORT[n]: round(float(np.average(Fz[m, j], weights=w[m])), 2) for j, n in enumerate(names)}})
        ct = pd.crosstab(pd.Series(lab.cluster.map(DPGMM).values, name="dpgmm_segment"),
                         pd.Series(g + 1, name=f"kmeans{K}_group"), values=w, aggfunc="sum",
                         normalize="columns").round(2)
        ct.to_csv(OUT / f"crosswalk_k{K}.csv")

    s, gr = pd.DataFrame(summ), pd.DataFrame(groups)
    s.to_csv(OUT / "summary.csv", index=False)
    gr.to_csv(OUT / "groups.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(f"n = {len(X):,}, {X.shape[1]} clustering factors (* = profile-only factor)\n")
        print(s.to_string(index=False))
        for K in KS:
            print(f"\nK = {K}, groups ordered by mean ideology (factor columns in SD):")
            print(gr[gr.K == K].drop(columns="K").to_string(index=False))
            print(pd.read_csv(OUT / f"crosswalk_k{K}.csv", index_col=0).to_string())


if __name__ == "__main__":
    main()

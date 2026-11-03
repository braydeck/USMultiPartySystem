"""Does the ANES segmentation depend on its foreign-policy items? Refit without them and compare.

Data: ANES 2024 Time Series CSV (2025-08-08 release), weight V240108a; the 99 screened items in
outputs/independent_loadings.csv; the 4,673 respondents of outputs/clustering/independent_available/.

Drops the 10 items in the foreign_policy_nation domain (six threat ratings, Israel and Ukraine aid, Palestinian aid,
"better off if we stayed home"). Defense spending stays: it is in the economy domain. The remaining 89 items keep the
same respondents and the same pairwise polychoric (a pairwise matrix's submatrix is the matrix of the subset).
Parallel analysis picks k; PAF + oblimin; available-item scores; the anchor rule; the stability sweep picks the cap
(dims_check / n_check). The kept solution is the modal one across 20 seeds, best lower bound within it, and is
compared with the production four segments by ARI and by where each production segment's members land.

Writes outputs/clustering/nofp_check/{caps.csv, crosswalk.csv, run.log}.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import sys

import numpy as np
import pandas as pd
from scipy.sparse.csgraph import connected_components

import describe_clusters as dc
import dims_check as dk
import independent_clustering as ic
import independent_efa as ie
import matched_efa as me
import n_check as nc
from common import clustering as cl
from common import efa_math as em

OUT = me.OUT / "clustering" / "nofp_check"
NAMES = {0: "center-left moderates", 1: "religious conservatives", 2: "secular progressives", 3: "young disaffected"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    items, w, _, _ = ie.load_pool()
    load = pd.read_csv(me.OUT / "independent_loadings.csv", index_col=0)
    ids = [c for c in load.index if load.domain[c] != "foreign_policy_nation"]
    lab = pd.read_csv(me.OUT / "clustering" / "independent_available" / "independent_clusters.csv")
    desc_all, keep_w = dc.descriptors()
    items.index = desc_all.caseid[keep_w].values
    D = items.loc[lab.caseid.values, ids]
    wD = pd.Series(w, index=items.index).loc[lab.caseid.values].values
    R = em.regularize_corr(em.polychoric_matrix(D.reset_index(drop=True), ids, wD, progress=False))
    k, _, _ = em.parallel_analysis(R, n_obs=len(D))
    L, Phi, _ = me.fit(R, k)
    full = load.loc[ids, [c for c in load.columns if c.startswith("N") and c[1:].isdigit()]].values
    matches = {dc.INDEPENDENT_NAMES[f"N{m['factor_1'] + 1}"]: round(abs(m["phi"]), 2) for m in me.cg.match_factors(full, L)}
    print(f"n = {len(D):,}, {len(ids)} items (10 foreign-policy items dropped); parallel analysis k = {k}")
    print(f"production factors matched (Tucker phi): {matches}", flush=True)

    F, _ = ic.available_scores(D, wD, R, L, Phi)
    X = dk.residualize(F, wD)
    s = nc.sweep(X)
    s.to_csv(OUT / "caps.csv", index=False)
    K = dk.kept(s)
    print(f"\nkept cap {K}\n{s.to_string(index=False)}", flush=True)

    fits = [ic.job(X, K, "seed", i) for i in ic.SEEDS]
    S = ic.pairwise([f[3] for f in fits])
    _, comp = connected_components(S >= 0.9, directed=False)
    modal = np.bincount(comp).argmax()
    new = max((f for f, c in zip(fits, comp) if c == modal), key=lambda f: f[4])[3]
    old = lab.cluster.values
    print(f"\nARI vs production four segments: {cl.ari(old, new):.2f}")
    ct = pd.crosstab(pd.Series(old, name="production").map(NAMES), pd.Series(new, name="no_foreign_policy"),
                     values=wD, aggfunc="sum", normalize="index").round(2)
    ct.to_csv(OUT / "crosswalk.csv")
    print("share of each production segment landing in each new cluster:\n", ct.to_string())


if __name__ == "__main__":
    sys.exit(main())

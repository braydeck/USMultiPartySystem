"""Two checks on ANES's four-segment ceiling: does it rise with fewer factors, and how firmly does the rule land on 4?

Data: ANES 2024 Time Series CSV (2025-08-08 release), weight V240108a; the 99 screened items in
outputs/independent_loadings.csv; the 4,673 respondents of outputs/clustering/independent_available/.

1. Factor count. The 99 items' pairwise polychoric is refit at k = 3, 5, 7 and 10 factors (PAF + oblimin, as in
   independent_efa.py), every respondent is scored on the items they answered (available-item Thomson scores), the
   anchor rule residualizes, and the stability sweep picks the cap. Respondents and items are held fixed, so only the
   number of dimensions changes. k = 10 reproduces the production run and should keep cap 4.
2. Rule uncertainty. The production 10-factor scores are resampled with replacement (10 draws, rng 42 + b) and the
   full sweep reruns on each draw. Factors are not refit per draw, so this measures the clustering step only.

The sweep is n_check.sweep (the independent_clustering.py rule: caps 2-10, 20 seeds, 30 resamples, kept cap = largest
with no cluster under 0.5 mean Jaccard). Factor sign does not affect the clustering, so factors are not oriented.

Writes outputs/clustering/dims_check/{by_factors.csv, by_factors_caps.csv, rule_bootstrap.csv, run.log}.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import sys

import numpy as np
import pandas as pd

import describe_clusters as dc
import independent_clustering as ic
import independent_efa as ie
import matched_efa as me
import n_check as nc
from common import efa_math as em

OUT = me.OUT / "clustering" / "dims_check"
K_FACTORS = (3, 5, 7, 10)
N_DRAWS = 10


def residualize(F, w):
    k = F.shape[1]
    C = np.corrcoef(F.T)
    anchor = int(np.argmax((np.abs(C).sum(axis=1) - 1) / (k - 1)))
    X = F.copy()
    for j in range(k):
        if j != anchor and abs(C[anchor, j]) >= ic.ANCHOR_R:
            X[:, j] = em.wresid(F[:, j], F[:, anchor], w)
    mu = np.average(X, axis=0, weights=w)
    return (X - mu) / np.sqrt(np.average((X - mu) ** 2, axis=0, weights=w))


def kept(s):
    ok = s[s.n_dissolved == 0]
    return int(ok.K.max()) if not ok.empty else None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    items, w, _, _ = ie.load_pool()
    load = pd.read_csv(me.OUT / "independent_loadings.csv", index_col=0)
    ids = list(load.index)
    lab = pd.read_csv(me.OUT / "clustering" / "independent_available" / "independent_clusters.csv")
    desc_all, keep_w = dc.descriptors()
    items.index = desc_all.caseid[keep_w].values
    D = items.loc[lab.caseid.values, ids]
    wD = pd.Series(w, index=items.index).loc[lab.caseid.values].values
    R = em.regularize_corr(em.polychoric_matrix(D.reset_index(drop=True), ids, wD, progress=False))
    print(f"n = {len(D):,}, {len(ids)} items", flush=True)

    rows, caps = [], []
    for k in K_FACTORS:
        L, Phi, _ = me.fit(R, k)
        F, _ = ic.available_scores(D, wD, R, L, Phi)
        s = nc.sweep(residualize(F, wD))
        s.insert(0, "factors", k)
        caps.append(s)
        kc = kept(s)
        rows.append({"factors": k, "kept_cap": kc,
                     "resample_ari_at_kept": float(s.loc[s.K == kc, "resample_ari_mean"].iloc[0]) if kc else None})
        print(f"\n== {k} factors: kept cap {kc}\n{s.drop(columns='factors').to_string(index=False)}", flush=True)
    pd.concat(caps).to_csv(OUT / "by_factors_caps.csv", index=False)
    pd.DataFrame(rows).to_csv(OUT / "by_factors.csv", index=False)
    print("\n", pd.DataFrame(rows).to_string(index=False), flush=True)

    X = residualize(lab[[c for c in lab.columns if c.startswith("F_")]].values, wD)
    boot = []
    for b in range(N_DRAWS):
        idx = np.random.default_rng(42 + b).integers(0, len(X), len(X))
        s = nc.sweep(X[idx])
        boot.append({"draw": b + 1, "kept_cap": kept(s), "n_dissolved_by_cap": s.n_dissolved.tolist()})
        print(f"draw {b + 1}: kept cap {kept(s)}; dissolved by cap 2-10 {s.n_dissolved.tolist()}", flush=True)
    bt = pd.DataFrame(boot)
    bt.to_csv(OUT / "rule_bootstrap.csv", index=False)
    print("\nkept cap across draws:", bt.kept_cap.value_counts().sort_index().to_dict())


if __name__ == "__main__":
    sys.exit(main())

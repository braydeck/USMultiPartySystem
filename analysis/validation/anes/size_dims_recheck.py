"""n_check.py and dims_check.py rerun on the current spaces: is ANES's lower cap a sample-size or a dimension-count effect?

Data:
  CES   analysis/efa/exploration/listwise_check/outputs/four_dim/scores.csv (CES 2024, the Stage C four-dimension
        space of the 69-item pool, n = 49,431; clustering columns SO, TR, RT_resid, PC_resid; full-sample kept cap 10).
  ANES  ANES 2024 Time Series (2025-08-08 release), weight V240108a; the 86 items of outputs/stage_c/loadings_k17.csv
        and the 4,596 respondents of outputs/stage_c/clusters.csv (11 clustering factors, kept cap 6).

1. Sample size. Three CES subsamples at ANES's n (4,596), one at 2x and one at 4x, drawn without replacement
   (rng 42 + r), each through the ANES sweep. Dimensions held at CES's four.
2. Dimension count. The 86 ANES items' pairwise polychoric on the 4,596 respondents is refit at k = 4, 5, 8 and 11
   (PAF + oblimin), every factor is scored (available-item Thomson scores), the anchor rule residualizes, and the
   sweep picks the cap. Respondents and items are held fixed, so only the number of dimensions changes. These fits
   cluster every factor at fixed k; they are a diagnostic, not the §3c rule.

The sweep is n_check.sweep (caps 2-10, 20 seeds, 30 resamples, kept cap = largest with no cluster under 0.5 mean
Jaccard), unweighted as in both production chains.

Writes outputs/clustering/size_dims_recheck/{summary.csv, by_cap.csv}; log via tee.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import sys

import numpy as np
import pandas as pd

import describe_clusters as dc
import dims_check as dk
import independent_clustering as ic
import independent_efa as ie
import matched_efa as me
import n_check as nc
from common import efa_math as em

OUT = me.OUT / "clustering" / "size_dims_recheck"
CES_SCORES = me.HERE.parents[1] / "efa" / "exploration" / "listwise_check" / "outputs" / "four_dim" / "scores.csv"
CES_COLS = ["SO", "TR", "RT_resid", "PC_resid"]
K_FACTORS = (4, 5, 8, 11)


def record(rows, caps, arm, n, dims, s):
    kc = dk.kept(s)
    s = s.copy()
    s.insert(0, "arm", arm)
    caps.append(s)
    rows.append({"arm": arm, "n": n, "dims": dims, "kept_cap": kc,
                 "n_stable_at_kept": int(s.loc[s.K == kc, "n_stable"].iloc[0]) if kc else None,
                 "resample_ari_at_kept": float(s.loc[s.K == kc, "resample_ari_mean"].iloc[0]) if kc else None})
    print(f"\n== {arm} (n = {n:,}, {dims} dims): kept cap {kc}\n{s.drop(columns='arm').to_string(index=False)}", flush=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows, caps = [], []

    anes = pd.read_csv(me.OUT / "stage_c" / "clusters.csv")
    n_anes = len(anes)
    ces = pd.read_csv(CES_SCORES, usecols=CES_COLS).dropna().values
    print(f"CES n = {len(ces):,}; ANES n = {n_anes:,}", flush=True)
    for arm, n, r in [("CES at ANES n #1", n_anes, 0), ("CES at ANES n #2", n_anes, 1), ("CES at ANES n #3", n_anes, 2),
                      ("CES at 2x ANES n", 2 * n_anes, 0), ("CES at 4x ANES n", 4 * n_anes, 0)]:
        idx = np.random.default_rng(42 + r).choice(len(ces), n, replace=False)
        record(rows, caps, arm, n, 4, nc.sweep(ces[idx]))

    items, w, _, _ = ie.load_pool()
    ids = list(pd.read_csv(me.OUT / "stage_c" / "loadings_k17.csv", index_col=0).index)
    desc_all, keep_w = dc.descriptors()
    items.index = desc_all.caseid[keep_w].values
    D = items.loc[anes.caseid.values, ids]
    wD = pd.Series(w, index=items.index).loc[anes.caseid.values].values
    R = em.regularize_corr(em.polychoric_matrix(D.reset_index(drop=True), ids, wD, progress=False))
    print(f"\nANES: n = {len(D):,}, {len(ids)} items", flush=True)
    for k in K_FACTORS:
        L, Phi, _ = me.fit(R, k)
        F, _ = ic.available_scores(D, wD, R, L, Phi)
        record(rows, caps, f"ANES refit at k = {k}", len(D), k, nc.sweep(dk.residualize(F, wD)))

    pd.concat(caps).to_csv(OUT / "by_cap.csv", index=False)
    summ = pd.DataFrame(rows)
    summ.to_csv(OUT / "summary.csv", index=False)
    print("\n", summ.to_string(index=False), flush=True)


if __name__ == "__main__":
    sys.exit(main())

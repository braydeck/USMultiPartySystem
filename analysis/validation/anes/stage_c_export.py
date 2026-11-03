"""Name, orient and export the Stage C segmentation in the format the profile scripts read.

Inputs: outputs/stage_c/{clusters.csv, loadings_k10.csv, entry_test.csv} (stage_c.py). Ideology V241177 and weight
from describe_clusters.descriptors().

Names are given after the entry test, from each factor's top items (naming is not a criterion, §3c step 4).
Orientation follows describe_clusters.orient: high = the end that goes with conservative self-placement; factors whose
|r| with ideology is under 0.10 keep their top item positive. Clusters are relabeled 0..3 by descending weighted size.
The anchor and residualized columns repeat dims_check.residualize's rule over the clustering factors.

Writes outputs/stage_c/{independent_clusters.csv, factors.csv}.
"""
import numpy as np
import pandas as pd

import describe_clusters as dc
import matched_efa as me
from common import clustering as cl

SRC = me.OUT / "stage_c"
ANCHOR_R = 0.40
NAMES = ["Immigration and diversity", "Democratic norms", "Trust in institutions (CSES)",
         "Leave decisions to experts or business (CSES)", "Foreign threats", "Religion and social traditionalism",
         "Rural resentment", "Government role in the economy", "Gun policy", "Ukraine and Israel aid"]


def main():
    lab = pd.read_csv(SRC / "clusters.csv")
    load = pd.read_csv(SRC / "loadings_k10.csv", index_col=0)
    et = pd.read_csv(SRC / "entry_test.csv")
    k = len(NAMES)
    d = lab[["caseid"]].merge(dc.descriptors()[0], on="caseid", how="left")
    w = d.w.values
    F = lab[[f"F{j}" for j in range(k)]].values
    L = load[[f"N{j + 1}" for j in range(k)]].values
    F, L, r_ideo = dc.orient(F, NAMES, d.ideo.values, w, L)

    raw = lab.cluster.values
    shares = np.bincount(raw, weights=w) / w.sum()
    cluster, _ = cl.remap_by_weighted_n(raw, w, shares, thresh=0.0)

    use = list(et.factor[et.clusters])
    C = np.corrcoef(F[:, use].T)
    a = int(np.argmax((np.abs(C).sum(axis=1) - 1) / (len(use) - 1)))
    resid = [use[j] for j in range(len(use)) if j != a and abs(C[a, j]) >= ANCHOR_R]
    pd.DataFrame({"caseid": lab.caseid, "cluster": cluster, **{f"F_{n}": F[:, j] for j, n in enumerate(NAMES)}}).to_csv(
        SRC / "independent_clusters.csv", index=False)
    top = ["; ".join(f"{load.label.iloc[t][:70]} ({L[t, j]:+.2f})" for t in np.argsort(-np.abs(L[:, j]))[:3]) for j in range(k)]
    fac = pd.DataFrame({"factor": NAMES, "r_ideology": r_ideo, "clusters": et.clusters.values,
                        "anchor": [j == use[a] for j in range(k)], "residualized": [j in resid for j in range(k)],
                        "n_clean": et.n_clean.values, "n_batteries": et.n_batteries.values, "top_items": top})
    fac.to_csv(SRC / "factors.csv", index=False)
    print(fac.drop(columns="top_items").to_string(index=False))
    print("segment shares:", np.round(np.bincount(cluster, weights=w) / w.sum(), 3))


if __name__ == "__main__":
    main()

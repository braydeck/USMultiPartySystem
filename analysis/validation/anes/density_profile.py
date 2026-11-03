"""Where are ANES respondents dense, on the ten independent factors? The ANES twin of
analysis/efa/exploration/k_stability/density_profile.py (CES).

Data: outputs/clustering/independent_available/independent_clusters.csv (n = 4,673, ten factors), the clustering
inputs after the anchor rule (dims_check.residualize); weight V240108a.

1. HDBSCAN with the CES settings scaled to ANES's n: CES used min_cluster_size 500 of 45,214 (1.1%) and min_samples
   25, so ANES uses 50 and 5 (also 25 and 100 as a check). Weighted factor means of each dense region, in SD units,
   and the production segment mix of each region.
2. One factor at a time: Sarle's bimodality coefficient (> 0.555 suggests more than one peak).

Writes outputs/clustering/density/{dense_regions.csv, factor_shape.csv, run.log}.
"""
import numpy as np
import pandas as pd
from scipy.stats import kurtosis, skew
from sklearn.cluster import HDBSCAN

import dims_check as dk
import matched_efa as me
import recode_matched as rm

SRC = me.OUT / "clustering" / "independent_available"
OUT = me.OUT / "clustering" / "density"
SEGMENTS = {0: "center-left moderates", 1: "religious conservatives", 2: "secular progressives", 3: "young disaffected"}
SETTINGS = [(25, 5), (50, 5), (100, 10)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lab = pd.read_csv(SRC / "independent_clusters.csv")
    names = [c[2:] for c in lab.columns if c.startswith("F_")]
    raw = pd.read_csv(rm.ANES_CSV, usecols=["V240001", rm.WEIGHT], low_memory=False).apply(pd.to_numeric, errors="coerce")
    w = lab[["caseid"]].merge(raw.rename(columns={"V240001": "caseid"}), on="caseid")[rm.WEIGHT].values
    X = dk.residualize(lab[[f"F_{n}" for n in names]].values, w)
    seg = lab.cluster.map(SEGMENTS).values

    rows = []
    for mcs, ms in SETTINGS:
        h = HDBSCAN(min_cluster_size=mcs, min_samples=ms).fit_predict(X)
        print(f"HDBSCAN min_cluster_size {mcs}, min_samples {ms}: {len(set(h)) - (-1 in h)} dense regions, "
              f"{w[h == -1].sum() / w.sum() * 100:.1f}% in none", flush=True)
        for c in sorted(set(h)):
            m = h == c
            mix = pd.Series(w[m]).groupby(seg[m]).sum().sort_values(ascending=False) / w[m].sum()
            rows.append({"min_cluster_size": mcs, "region": "none" if c < 0 else c,
                         "share_pct": round(w[m].sum() / w.sum() * 100, 1),
                         "segments": ", ".join(f"{s} {v * 100:.0f}" for s, v in mix.items() if v >= 0.08),
                         **{n: round(float(np.average(X[m, j], weights=w[m])), 2) for j, n in enumerate(names)}})
    reg = pd.DataFrame(rows)
    reg.to_csv(OUT / "dense_regions.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 20):
        print(reg.to_string(index=False))

    shape = []
    for j, n in enumerate(names):
        x = X[:, j]
        g, k, N = skew(x), kurtosis(x), len(x)
        shape.append({"factor": n, "skew": round(float(g), 2), "excess_kurtosis": round(float(k), 2),
                      "bimodality_coef": round(float((g ** 2 + 1) / (k + 3 * (N - 1) ** 2 / ((N - 2) * (N - 3)))), 3)})
    sh = pd.DataFrame(shape)
    sh.to_csv(OUT / "factor_shape.csv", index=False)
    print("\n", sh.to_string(index=False))


if __name__ == "__main__":
    main()

"""Where are CES respondents dense, described on the five factors rather than on party labels?

Data: data/processed/efa_factor_scores.csv (rescored 2026-10, n = 45,214), clustering inputs FS_F1, FS_F2, FS_F3,
FS_F4_resid, FS_F5_resid; weight commonpostweight.

1. HDBSCAN at fair_compare.py's middle setting (min_cluster_size 500, min_samples 25): the weighted factor means
   of each dense region and of the respondents in no dense region, in SD units of the full sample.
2. One factor at a time: Sarle's bimodality coefficient (> 0.555 suggests more than one peak) and a 20-bin
   weighted histogram, to show whether any single factor has two humps or one.

Writes outputs/density/{dense_region_means.csv, factor_shape.csv, histograms.csv}.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kurtosis, skew
from sklearn.cluster import HDBSCAN

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).parent / "outputs" / "density"
COLS = {"FS_F1": "F1 Security & Order", "FS_F2": "F2 Institutional Distrust", "FS_F3": "F3 Government Distrust",
        "FS_F4_resid": "F4 Religious Traditionalism (resid)", "FS_F5_resid": "F5 Populist Conservatism (resid)"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fs = pd.read_csv(ROOT / "data/processed/efa_factor_scores.csv")
    X, w = fs[list(COLS)].values, fs["commonpostweight"].values
    mu = np.average(X, axis=0, weights=w)
    Z = (X - mu) / np.sqrt(np.average((X - mu) ** 2, axis=0, weights=w))

    lab = HDBSCAN(min_cluster_size=500, min_samples=25).fit_predict(X)
    rows = []
    for c in sorted(set(lab)):
        m = lab == c
        rows.append({"region": "no dense region" if c < 0 else f"dense region {c}",
                     "share_pct": round(w[m].sum() / w.sum() * 100, 1),
                     **{nm: round(float(np.average(Z[m, j], weights=w[m])), 2) for j, nm in enumerate(COLS.values())}})
    reg = pd.DataFrame(rows)
    reg.to_csv(OUT / "dense_region_means.csv", index=False)
    print("factor means (SD) by HDBSCAN region:\n", reg.to_string(index=False))

    shape, hist = [], []
    for j, nm in enumerate(COLS.values()):
        x = Z[:, j]
        g, k = skew(x), kurtosis(x)
        n = len(x)
        bc = (g ** 2 + 1) / (k + 3 * (n - 1) ** 2 / ((n - 2) * (n - 3)))
        shape.append({"factor": nm, "skew": round(float(g), 2), "excess_kurtosis": round(float(k), 2),
                      "bimodality_coef": round(float(bc), 3)})
        h, edges = np.histogram(x, bins=20, range=(-3, 3), weights=w)
        hist += [{"factor": nm, "bin_mid": round((a + b) / 2, 2), "share_pct": round(v / w.sum() * 100, 1)}
                 for a, b, v in zip(edges[:-1], edges[1:], h)]
    sh = pd.DataFrame(shape)
    sh.to_csv(OUT / "factor_shape.csv", index=False)
    pd.DataFrame(hist).to_csv(OUT / "histograms.csv", index=False)
    print("\nshape of each factor (bimodality coefficient > 0.555 suggests two peaks):\n", sh.to_string(index=False))
    H = pd.DataFrame(hist).pivot(index="bin_mid", columns="factor", values="share_pct")
    print("\nweighted % of respondents per 0.3-SD bin:\n", H.to_string())


if __name__ == "__main__":
    main()

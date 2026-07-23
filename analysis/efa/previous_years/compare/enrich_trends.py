#!/usr/bin/env python3
"""Cross-wave trend signals on the dominant conservatism axis (k=1 backbone).

Validity + mass-polarization proxy: weighted mean of the dominant-dimension score
for Dem vs Rep (z-standardized within wave), and the standardized partisan gap.
Emits outputs/backbone_trends.csv.
"""
import sys, pickle, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import io_paths as io, efa_math as em


def main():
    rows = []
    for w in io.WAVES:
        with open(io.out_dir(w) / "fit_results.pkl", "rb") as f:
            c = pickle.load(f)["common"]
        R = em.regularize_corr(c["R"].copy())
        L1, _, _ = em.paf(R, 1)
        # orient positive
        L1 = L1[:, 0] * (1 if L1[np.argmax(np.abs(L1[:, 0])), 0] >= 0 else -1)
        X = c["_Xitems"]
        Z, mu, sig = em.weighted_standardize(X, c["w"])
        score = Z @ (np.linalg.inv(R) @ L1)     # Thomson score, single factor
        ww = c["w"]; pid = c["pid3"]
        # z-standardize the score within wave (weighted)
        m = np.average(score, weights=ww); s = np.sqrt(np.average((score - m) ** 2, weights=ww))
        z = (score - m) / s
        dem = pid == 1; rep = pid == 2; ind = pid == 3
        md = np.average(z[dem], weights=ww[dem]); mr = np.average(z[rep], weights=ww[rep])
        mi = np.average(z[ind], weights=ww[ind])
        rows.append({"wave": w, "kind": io.KIND[w],
                     "dem_mean_z": round(md, 3), "ind_mean_z": round(mi, 3),
                     "rep_mean_z": round(mr, 3), "rep_minus_dem_sd": round(mr - md, 3)})
        print(f"{w} ({io.KIND[w]:12}): Dem {md:+.2f}  Ind {mi:+.2f}  Rep {mr:+.2f}  "
              f"| partisan gap {mr-md:.2f} SD")
    pd.DataFrame(rows).to_csv(io.compare_dir() / "backbone_trends.csv", index=False)
    print("saved outputs/backbone_trends.csv")


if __name__ == "__main__":
    main()

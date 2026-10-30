#!/usr/bin/env python3
"""
build_party_factor_ellipses.py
------------------------------
Each party's spread across the four interpretable factors, for the Parties tab's factor-pair
grid. Source: data/processed/efa_factor_scores.csv (raw FS_F1/F2/F4/F5 + commonpostweight)
joined positionally to data/processed/typology_cluster_assignments.csv (hard `cluster`).
Both files are 45,214 rows on the same listwise-deletion mask, asserted below. Raw F4/F5,
not the resid columns, so the space matches the constellation's centroids.

F3 is left out: it is a suppressor kept only to isolate CUP and runs opposite to real distrust.

Units are standard deviations of the weighted electorate, the same scale as clusterProfiles
z_F*. Per party: weighted mean vector and weighted 4x4 covariance of its first-choice members.
The viz draws each pair's ellipse from the 2x2 sub-block, which is the exact marginal of a
Gaussian. `coverage50` records the weighted share of members actually inside each pair's
nominal 50% ellipse, so a party whose cloud is far from Gaussian is visible in the payload.

Output: viz/src/data/partyFactorEllipses.json (bundled).
"""

import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from party_codes import CLUSTER_TO_PARTY  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
PROCESSED = BASE / "data" / "processed"
OUT = BASE / "viz" / "src" / "data" / "partyFactorEllipses.json"

FACTORS = ["F1", "F2", "F4", "F5"]
CHI2_2DF_50 = 2 * np.log(2)  # squared Mahalanobis radius holding 50% of a 2-D Gaussian


def wmean(x, w):
    return float(np.average(x, weights=w))


def main():
    scores = pd.read_csv(PROCESSED / "efa_factor_scores.csv")
    typ = pd.read_csv(PROCESSED / "typology_cluster_assignments.csv")
    assert len(scores) == len(typ) == 45214
    assert np.allclose(scores.FS_F1, typ.FS_F1) and np.allclose(scores.commonpostweight, typ.commonpostweight)

    w = scores.commonpostweight.to_numpy()
    X = scores[[f"FS_{f}" for f in FACTORS]].to_numpy()
    mu = np.average(X, axis=0, weights=w)
    sd = np.sqrt(np.average((X - mu) ** 2, axis=0, weights=w))
    Z = (X - mu) / sd

    parties = {}
    for k, code in CLUSTER_TO_PARTY.items():
        m = typ.cluster.to_numpy() == k
        zk, wk = Z[m], w[m]
        mean = np.average(zk, axis=0, weights=wk)
        cov = np.cov(zk, rowvar=False, aweights=wk)
        coverage = {}
        for i, j in combinations(range(len(FACTORS)), 2):
            sub = cov[np.ix_([i, j], [i, j])]
            d = zk[:, [i, j]] - mean[[i, j]]
            r2 = np.einsum("ni,ij,nj->n", d, np.linalg.inv(sub), d)
            coverage[f"{FACTORS[i]}-{FACTORS[j]}"] = round(wmean(r2 <= CHI2_2DF_50, wk) * 100, 1)
        parties[code] = {
            "n": int(m.sum()),
            "weightShare": round(float(wk.sum() / w.sum() * 100), 2),
            "mean": [round(float(v), 4) for v in mean],
            "cov": [[round(float(v), 4) for v in row] for row in cov],
            "coverage50": coverage,
        }

    out = {"factors": FACTORS, "units": "SD of the weighted electorate",
           "nVoters": int(len(Z)), "parties": parties}
    OUT.write_text(json.dumps(out, separators=(",", ":")))
    print(f"wrote {OUT.relative_to(BASE)}")
    for code, p in parties.items():
        cov = p["coverage50"].values()
        print(f"  {code}: n={p['n']:>5}  50% ellipse holds {min(cov):.0f}-{max(cov):.0f}%")


if __name__ == "__main__":
    main()

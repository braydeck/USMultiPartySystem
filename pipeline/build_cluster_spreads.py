#!/usr/bin/env python3
"""
build_cluster_spreads.py
------------------------
Each party's spread in raw factor units, for the constellation penumbras and the Parties-tab
z-scores. Source: data/processed/efa_factor_scores.csv (raw FS_F1..F5 + commonpostweight)
joined positionally to data/processed/typology_cluster_assignments.csv (hard `cluster`), both
45,214 rows on the same listwise-deletion mask. Raw, not resid, F4/F5, so the means match
candidate_factor_centroids.csv, which places the constellation's nodes.

Per party: weighted mean, weighted SD and weighted pairwise covariance of its first-choice
members; `n` is the unweighted member count.

Output: viz/src/data/clusterSpreads.json, plus viz/src/data/factorPopulationSd.json, the
weighted SD of each raw factor across the whole electorate, which the viz divides by to put
raw scores on a z scale.
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
OUT = BASE / "viz" / "src" / "data"

FACTORS = ["F1", "F2", "F3", "F4", "F5"]


def wsd(x, w):
    mu = np.average(x, weights=w)
    return float(np.sqrt(np.average((x - mu) ** 2, weights=w)))


def main():
    scores = pd.read_csv(PROCESSED / "efa_factor_scores.csv")
    typ = pd.read_csv(PROCESSED / "typology_cluster_assignments.csv")
    assert len(scores) == len(typ) == 45214
    assert np.allclose(scores.FS_F1, typ.FS_F1) and np.allclose(scores.commonpostweight, typ.commonpostweight)

    w = scores.commonpostweight.to_numpy()
    X = scores[[f"FS_{f}" for f in FACTORS]].to_numpy()
    cl = typ.cluster.to_numpy()

    rows = []
    for k, code in CLUSTER_TO_PARTY.items():
        m = cl == k
        xk, wk = X[m], w[m]
        cov = np.cov(xk, rowvar=False, aweights=wk, bias=True)
        row = {"party": code, "n": int(m.sum())}
        for i, f in enumerate(FACTORS):
            row[f"mean_{f}"] = round(float(np.average(xk[:, i], weights=wk)), 4)
            row[f"sd_{f}"] = round(float(np.sqrt(cov[i, i])), 4)
        for i, j in combinations(range(len(FACTORS)), 2):
            row[f"cov_{FACTORS[i]}_{FACTORS[j]}"] = round(float(cov[i, j]), 4)
        rows.append(row)

    pop_sd = {f: round(wsd(X[:, i], w), 3) for i, f in enumerate(FACTORS)}
    (OUT / "clusterSpreads.json").write_text(json.dumps(rows))
    (OUT / "factorPopulationSd.json").write_text(json.dumps(pop_sd))
    print(f"wrote clusterSpreads.json ({len(rows)} parties), factorPopulationSd.json {pop_sd}")


if __name__ == "__main__":
    main()

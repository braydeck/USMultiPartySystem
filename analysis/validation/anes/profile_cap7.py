"""Profile the primary ANES segmentation (no-foreign-policy Stage C) at cap 7, for comparison with caps 4 and 5.

Data: ANES 2024 Time Series CSV (2025-08-08 release), post weight V240108a; outputs/stage_c_nofp/clusters.csv (scores of
4,712 respondents). Labels at caps 4, 5 and 7: stage_c.py's selection (20 seeds, modal solution, best lower bound) on
the residualized clustering factors, as in heldout_test.py; the cap-5 labels must reproduce clusters.csv.
Per cap-7 segment: weighted share; mean best-match Jaccard against 30 bootstrap refits (independent_clustering.job,
labels predicted on the full sample), stable >= 0.75, dissolves < 0.5; factor means in weighted z units; weighted
shares on descriptor items (codes from the ANES codebook); where the cap-4 and cap-5 segments go at cap 7.
Factor directions (loadings_k7.csv and codebook codes): left-right high = left; democratic norms high = checks and
balances rated important; religion high = religious; government trust high = trusts government; the three-item factor
high = rejects political violence, rejects "women demanding equality seek special favors", and rejects leaving
decisions to business leaders.
Writes outputs/stage_c_nofp/cap7/{profile.csv, from_cap4.csv, from_cap5.csv}.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

import describe_clusters as dc
import dims_check as dk
import heldout_test as ht
import independent_clustering as ic
import independent_efa as ie
import matched_efa as me
from common import clustering as cl

PRIMARY = me.OUT / "stage_c_nofp"
OUT = PRIMARY / "cap7"
FACTORS = {0: "left-right (high = left)", 1: "democratic norms", 4: "religion", 5: "government trust",
           6: "rejects violence / gender / business rule"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    items, w_all, _, cw = ie.load_pool()
    desc, keep_w = dc.descriptors()
    items.index = desc.caseid[keep_w].values
    prim = pd.read_csv(PRIMARY / "clusters.csv")
    w = pd.Series(w_all, index=items.index).loc[prim.caseid].values
    D = items.loc[prim.caseid]
    passing = sorted(FACTORS)
    F = prim[[f"F{j}" for j in passing]].values
    X = dk.residualize(F, w)
    lab = dict(Parallel(n_jobs=3)(delayed(ht.modal_labels)(X, K) for K in (4, 5, 7)))
    assert cl.ari(lab[5], prim.cluster.values) > 0.999
    boots = Parallel(n_jobs=6)(delayed(ic.job)(X, 7, "boot", i) for i in range(ic.N_BOOT))
    jac = np.mean([ic.best_jaccard(lab[7], b[3]) for b in boots], axis=0)

    Fz = (F - np.average(F, axis=0, weights=w)) / np.sqrt(np.average((F - np.average(F, axis=0, weights=w)) ** 2, axis=0, weights=w))
    church_top = D.church.max()
    desc_items = {
        "Bible literal word of God": (D.V241421 == 1),
        "church almost every week": (D.church == church_top),
        "abortion never or only rape/incest/life": (D.V241302 <= 2),
        "checks and balances very/extremely important": (D.V241325 >= 4),
        "violence to achieve goals justified at least moderately": (D.V241579 >= 3),
        "trust federal government always/most of the time": (D.V241229 <= 2),
        "favor DEI": (D.V241290x <= 3),
        "make all unauthorized immigrants felons and deport": (D.V241386 == 1),
        "make buying a gun more difficult": (D.V242325 == 1),
        "favor weapons to Ukraine": (D.V241400x <= 3),
        "favor military aid to Israel": (D.V241403x <= 3),
    }
    src = {"Bible literal word of God": "V241421", "church almost every week": "church",
           "abortion never or only rape/incest/life": "V241302", "checks and balances very/extremely important": "V241325",
           "violence to achieve goals justified at least moderately": "V241579",
           "trust federal government always/most of the time": "V241229", "favor DEI": "V241290x",
           "make all unauthorized immigrants felons and deport": "V241386", "make buying a gun more difficult": "V242325",
           "favor weapons to Ukraine": "V241400x", "favor military aid to Israel": "V241403x"}
    rows = []
    order = np.argsort(-np.bincount(lab[7], weights=w))
    for s in order:
        m = lab[7] == s
        row = {"segment": int(s), "share": round(100 * w[m].sum() / w.sum(), 1), "jaccard": round(float(jac[s]), 2),
               "status": "stable" if jac[s] >= 0.75 else ("dissolves" if jac[s] < 0.5 else "middling")}
        row.update({FACTORS[j]: round(float(np.average(Fz[m, i], weights=w[m])), 2) for i, j in enumerate(passing)})
        for name, hit in desc_items.items():
            ok = m & D[src[name]].notna().values
            row[name] = round(100 * float(np.average(hit.values[ok], weights=w[ok])), 0)
        rows.append(row)
    prof = pd.DataFrame(rows)
    prof.to_csv(OUT / "profile.csv", index=False)
    for K in (4, 5):
        ct = pd.crosstab(lab[K], lab[7], values=w, aggfunc="sum", normalize="index").round(2)
        ct.to_csv(OUT / f"from_cap{K}.csv")
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(prof.T.to_string())
        for K in (4, 5):
            sh = (pd.Series(w).groupby(lab[K]).sum() / w.sum()).round(3)
            prof_k = pd.DataFrame({FACTORS[j]: pd.Series(Fz[:, i]).groupby(lab[K]).apply(
                lambda s: np.average(s, weights=w[s.index])).round(2) for i, j in enumerate(passing)})
            print(f"\ncap {K} segments (share, factor means):\n{prof_k.assign(share=sh).to_string()}")
            print(f"cap {K} -> cap 7 (row shares):\n{pd.read_csv(OUT / f'from_cap{K}.csv', index_col=0).to_string()}")


if __name__ == "__main__":
    sys.exit(main())

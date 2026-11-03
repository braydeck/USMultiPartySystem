"""k-means on the ANES segmentation inputs: the elbow curve, and what the six-group solution looks like.

Data: outputs/clustering/independent_available/independent_clusters.csv (n = 4,673, ten factors). Clustering inputs
are the anchor-residualized factors (dims_check.residualize), as in methods_check.py; groups are described on the
unresidualized factors standardized to the weighted sample (high = the end that goes with conservative
self-placement; see segment_portraits_page.STANCE), plus vote, party ID and ideology (describe_clusters.descriptors).

1. Elbow: within-cluster sum of squares for K = 1..12 (seed 42, n_init 10), with the share of variance explained
   and the gain from each added cluster. Mean silhouette on a seeded 2,000-respondent sample.
2. K = 6, seed 42 (all 20 seeds reach one solution, methods_check.py): weighted size, factor means, vote, party ID,
   ideology, and where each production segment's members land.

Writes outputs/clustering/kmeans_six/{elbow.csv, groups.csv, crosswalk.csv, run.log}.
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

import describe_clusters as dc
import dims_check as dk
import matched_efa as me

SRC = me.OUT / "clustering" / "independent_available"
OUT = me.OUT / "clustering" / "kmeans_six"
SEGMENTS = {0: "center-left moderates", 1: "religious conservatives", 2: "secular progressives", 3: "young disaffected"}
SHORT = {"Immigration and diversity": "immigration", "Trust in institutions (CSES)": "inst. distrust",
         "Democratic norms": "norms discount", "Iran, Russia, China as threats": "threats",
         "No say in government; gender attitudes": "no say/gender", "Religion and social traditionalism": "religion",
         "Israel and Ukraine aid": "oppose aid", "Government waste and big interests": "govt waste",
         "Government role in the economy": "small govt", "Gun policy": "anti gun control"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lab = pd.read_csv(SRC / "independent_clusters.csv")
    names = [c[2:] for c in lab.columns if c.startswith("F_")]
    desc_all, _ = dc.descriptors()
    d = lab[["caseid"]].merge(desc_all, on="caseid", how="left")
    w = d.w.values
    F = lab[[f"F_{n}" for n in names]].values
    X = dk.residualize(F, w)
    mu = np.average(F, axis=0, weights=w)
    Fz = (F - mu) / np.sqrt(np.average((F - mu) ** 2, axis=0, weights=w))

    rng = np.random.default_rng(42)
    sub = rng.choice(len(X), 2000, replace=False)
    total = ((X - X.mean(axis=0)) ** 2).sum()
    rows = []
    for K in range(1, 13):
        m = KMeans(n_clusters=K, n_init=10, random_state=42).fit(X)
        rows.append({"K": K, "wss": round(m.inertia_, 1), "variance_explained": round(1 - m.inertia_ / total, 3),
                     "silhouette": round(float(silhouette_score(X[sub], m.labels_[sub])), 3) if K > 1 else None})
    el = pd.DataFrame(rows)
    el["gain_from_this_K"] = el.variance_explained.diff().round(3)
    el.to_csv(OUT / "elbow.csv", index=False)
    print("elbow:\n", el.to_string(index=False))

    g = KMeans(n_clusters=6, n_init=10, random_state=42).fit_predict(X)
    order = np.argsort([np.average(d.ideo.values[(g == k) & d.ideo.notna().values], weights=w[(g == k) & d.ideo.notna().values])
                        for k in range(6)])
    remap = {old: new for new, old in enumerate(order)}
    g = np.array([remap[k] for k in g])
    out = []
    for k in range(6):
        m = g == k
        v = d.vote.values[m]
        p = d.pid7.values[m]
        okp = ~np.isnan(p)
        oki = ~np.isnan(d.ideo.values[m])
        out.append({"group": k + 1, "share": round(w[m].sum() / w.sum(), 3), "n": int(m.sum()),
                    "harris": round(float(np.average(v == "Harris", weights=w[m])), 2),
                    "trump": round(float(np.average(v == "Trump", weights=w[m])), 2),
                    "no_vote": round(float(np.average(np.isin(v, ["Did not vote / missing", "No post interview"]), weights=w[m])), 2),
                    "pid_dem": round(float(np.average(p[okp] <= 3, weights=w[m][okp])), 2),
                    "pid_rep": round(float(np.average(p[okp] >= 5, weights=w[m][okp])), 2),
                    "ideology_1to7": round(float(np.average(d.ideo.values[m][oki], weights=w[m][oki])), 1),
                    **{SHORT[n]: round(float(np.average(Fz[m, j], weights=w[m])), 2) for j, n in enumerate(names)}})
    gr = pd.DataFrame(out)
    gr.to_csv(OUT / "groups.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print("\nsix k-means groups, ordered by mean ideology (factor columns in SD):\n", gr.to_string(index=False))
    ct = pd.crosstab(pd.Series(lab.cluster.map(SEGMENTS).values, name="production"), pd.Series(g + 1, name="kmeans6"),
                     values=w, aggfunc="sum", normalize="columns").round(2)
    ct.to_csv(OUT / "crosswalk.csv")
    print("\nmakeup of each k-means group by production segment:\n", ct.to_string())


if __name__ == "__main__":
    main()

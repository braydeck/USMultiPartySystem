"""Profile the two sets of ANES 2024 clusters: matched (18 CES items) and independent (ANES's own factors).

Data: ANES 2024 Time Series CSV (2025-08-08 release), post weight V240108a.
  - Matched clusters: the production chain on the 18 crosswalk items (matched_clustering.run_chain,
    DPGMM cap 9, seed 42), n = 3,796. Party labels come from outputs/clustering/anes_clusters.csv,
    which matched_clustering.py writes; this script asserts it reproduces those cluster shares.
  - Independent clusters: read from outputs/clustering/independent/ (independent_clustering.py:
    culled to 4 items per factor, residualized on one anchor, DPGMM cap chosen on stability).
Factors in both sets are oriented so that high = the end that correlates with conservative
self-placement (V241177); factors whose |r| with ideology is under 0.10 keep their top item's sign.
Descriptors: party ID V241227x, 2024 presidential vote V242096x, ideology V241177, and the count of
"haven't thought much" answers (code 99) on the six 7-point scales in SCALES_7PT.

Writes outputs/clustering/cluster_profiles.json; cluster_profiles_page.py renders it.
"""
import json
import sys

import numpy as np
import pandas as pd

import independent_efa as ie
import matched_clustering as mc
import matched_efa as me
import recode_matched as rm
from common import clustering as cl
from common import efa_math as em

OUT = me.OUT / "clustering"
K = mc.K
CANON = me.ROOT / "analysis" / "efa" / "efa_loadings_k5_final.csv"
CANON_NAMES = {"F1": "Security & Order", "F2": "Institutional Distrust", "F3": "Government Distrust",
               "F4": "Religious Traditionalism", "F5": "Populist Conservatism"}
INDEPENDENT_NAMES = {
    "N1": "Immigration and diversity", "N2": "Trust in institutions (CSES)", "N3": "Democratic norms",
    "N4": "Iran, Russia, China as threats", "N5": "Religion and social traditionalism",
    "N6": "No say in government; gender attitudes", "N7": "Government waste and big interests",
    "N8": "Israel and Ukraine aid", "N9": "Government role in the economy", "N10": "Gun policy",
}
# 7-point self-placement scales that offer "haven't thought much about this" (code 99)
SCALES_7PT = ["V241239", "V241242", "V241245", "V241252", "V241255", "V241397"]
VOTE = {1: "Harris", 2: "Trump", 3: "Other", 4: "Other", 5: "Other", 6: "Other"}


def descriptors():
    d = pd.read_csv(rm.ANES_CSV, usecols=["V240001", rm.WEIGHT, "V241227x", "V242096x", "V241177"] + SCALES_7PT, low_memory=False)
    w = pd.to_numeric(d[rm.WEIGHT], errors="coerce").values
    keep = ~np.isnan(w) & (w > 0)
    pid7 = d.V241227x.where(d.V241227x.between(1, 7))
    vote = d.V242096x.map(VOTE).fillna(pd.Series(np.where(d.V242096x == -6, "No post interview", "Did not vote / missing"), index=d.index))
    ideo = d.V241177.where(d.V241177.between(1, 7))
    not_thought = (d[SCALES_7PT].apply(pd.to_numeric, errors="coerce") == 99).sum(axis=1)
    return pd.DataFrame({"caseid": d.V240001, "w": w, "pid7": pid7, "vote": vote, "ideo": ideo,
                         "not_thought": not_thought}), keep


def orient(F, names, ideo, w, L):
    """Flip each factor so high = conservative end; weak-ideology factors keep their top item positive."""
    F, L = F.copy(), L.copy()
    r_ideo = []
    for j in range(F.shape[1]):
        ok = ~np.isnan(ideo)
        r = np.corrcoef(F[ok, j], ideo[ok])[0, 1]
        flip = r < 0 if abs(r) >= 0.10 else L[np.argmax(np.abs(L[:, j])), j] < 0
        if flip:
            F[:, j] *= -1
            L[:, j] *= -1
            r = -r
        r_ideo.append(round(float(r), 2))
    return F, L, r_ideo


def profile(cluster, desc, F, fnames, w):
    rows = []
    Fz = (F - np.average(F, axis=0, weights=w)) / np.sqrt(np.average((F - np.average(F, axis=0, weights=w)) ** 2, axis=0, weights=w))
    for k in range(cluster.max() + 1):
        m = cluster == k
        ww = w[m]
        g = desc[m]
        pid = g.pid7.values
        okp = ~np.isnan(pid)
        ideo = g.ideo.values
        oki = ~np.isnan(ideo)
        vote = pd.Series(ww).groupby(g.vote.values).sum() / ww.sum()
        rows.append({
            "cluster": k, "n": int(m.sum()), "share": float(ww.sum() / w.sum()),
            "pid_dem": float(np.average(pid[okp] <= 3, weights=ww[okp])),
            "pid_ind": float(np.average(pid[okp] == 4, weights=ww[okp])),
            "pid_rep": float(np.average(pid[okp] >= 5, weights=ww[okp])),
            "pid7_mean": float(np.average(pid[okp], weights=ww[okp])),
            "ideo_mean": float(np.average(ideo[oki], weights=ww[oki])) if oki.any() else None,
            "not_thought_any": float(np.average(g.not_thought.values > 0, weights=ww)),
            "not_thought_mean": float(np.average(g.not_thought.values, weights=ww)),
            "vote": {v: float(vote.get(v, 0.0)) for v in ["Harris", "Trump", "Other", "Did not vote / missing", "No post interview"]},
            "factors": {f: float(np.average(Fz[m, j], weights=ww)) for j, f in enumerate(fnames)},
        })
    return rows


def matched(desc_all, keep_w):
    raw, items, cw = rm.load_matched()
    wa = raw[rm.WEIGHT].values.astype(float)
    pid_raw = pd.read_csv(rm.ANES_CSV, usecols=["V241221"]).V241221.values
    pa = np.where(pid_raw == 1, 1, np.where(pid_raw == 2, 2, 3))
    ids18 = list(cw.ces_var)
    keep = items.notna().all(axis=1).values & ~np.isnan(wa) & (wa > 0)
    A = items[keep].reset_index(drop=True)
    L, X, clu = mc.run_chain(A, wa[keep], pa[keep], ids18)
    w = wa[keep]
    ref = pd.read_csv(OUT / "anes_clusters.csv")
    shares = np.array([w[clu == k].sum() / w.sum() for k in range(clu.max() + 1)])
    assert np.allclose(shares.round(3), ref.share.values), "matched clusters do not reproduce anes_clusters.csv"

    canon = pd.read_csv(CANON, index_col=0).loc[ids18, list(CANON_NAMES)].values
    fnames = [None] * 5
    for m in me.cg.match_factors(canon, L):
        fnames[m["factor_2"]] = CANON_NAMES[f"F{m['factor_1'] + 1}"]
    desc = desc_all[keep].reset_index(drop=True)
    X, L, r_ideo = orient(X, fnames, desc.ideo.values, w, L)
    rows = profile(clu, desc, X, fnames, w)
    Z, _, _ = em.weighted_standardize(A[ids18].values.astype(float), w)
    labels = dict(zip(cw.ces_var, cw.ces_label))
    top = {f: [f"{labels[ids18[i]]} ({L[i, j]:+.2f})" for i in np.argsort(-np.abs(L[:, j]))[:3]]
           for j, f in enumerate(fnames)}
    for r, lab in zip(rows, ref.itertuples()):
        m = clu == r["cluster"]
        r["nearest_party"], r["hungarian_party"] = lab.nearest_party, lab.hungarian_party
        r["items"] = {labels[c]: float(np.average(Z[m, i], weights=w[m])) for i, c in enumerate(ids18)}
    return {"fnames": fnames, "r_ideo": r_ideo, "top_items": top, "clusters": rows,
            "caseid": desc.caseid.values, "cluster": clu}


def independent(desc_all, keep_w):
    """Read the stable independent clustering written by independent_clustering.py."""
    src = OUT / "independent"
    lab = pd.read_csv(src / "independent_clusters.csv")
    fac = pd.read_csv(src / "factors.csv")
    fnames = list(fac.factor)
    desc = lab[["caseid"]].merge(desc_all, on="caseid", how="left")
    F = lab[[f"F_{f}" for f in fnames]].values
    clu = lab.cluster.values
    top = {f: t.split("; ") for f, t in zip(fnames, fac.top_items)}
    rows = profile(clu, desc, F, fnames, desc.w.values)
    print(f"independent: n = {len(lab):,}, {len(fnames)} factors, clusters = {clu.max() + 1}")
    return {"fnames": fnames, "r_ideo": list(fac.r_ideology), "top_items": top, "clusters": rows,
            "anchor": fac.factor[fac.anchor].tolist(), "residualized": fac.factor[fac.residualized].tolist(),
            "caseid": lab.caseid.values, "cluster": clu}


def main():
    desc_all, keep_w = descriptors()
    M = matched(desc_all, keep_w)
    I = independent(desc_all, keep_w)
    a = pd.DataFrame({"caseid": M.pop("caseid"), "matched": M.pop("cluster")})
    b = pd.DataFrame({"caseid": I.pop("caseid"), "independent": I.pop("cluster")})
    both = a.merge(b, on="caseid").merge(desc_all[["caseid", "w"]], on="caseid")
    unassigned = {"matched": int((a.matched < 0).sum()), "independent": int((b.independent < 0).sum())}
    both = both[(both.matched >= 0) & (both.independent >= 0)]
    ct = both.pivot_table(index="matched", columns="independent", values="w", aggfunc="sum", fill_value=0)
    ct = ct.div(ct.sum(axis=1), axis=0)
    out = {"matched": M, "independent": I, "crosstab": {"n": len(both), "row_share": ct.round(3).values.tolist(),
                                                          "cols": [int(c) for c in ct.columns], "rows": [int(r) for r in ct.index]},
           "ari": float(cl.ari(both.matched.values, both.independent.values)), "unassigned": unassigned}
    (OUT / "cluster_profiles.json").write_text(json.dumps(out, indent=1))
    print(f"matched x independent overlap n = {len(both):,}, ARI = {out['ari']:.2f}")


if __name__ == "__main__":
    sys.exit(main())

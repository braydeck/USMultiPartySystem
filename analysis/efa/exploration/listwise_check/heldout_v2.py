"""Held-out items for the revised-rule clusters (§3c step 6), every cap 2-10, against the current ten and production.

Data: CES 2024 Common Content; weight commonpostweight. Respondents: those assigned in all compared typologies.
Groupings: revised rule (outputs/stage_c_v2/labels.npz, modal seed solution at each cap 2-10); current ten
(outputs/four_dim cap 10); production's nine (data/processed/typology_cluster_assignments.csv, row order of
efa_factor_scores.csv).
Measure: weighted eta-squared per item (share of the item's variance between groups), numeric recode of
item_pool.recode, averaged over an item set. Ceiling: weighted R^2 of each item on the four revised scores (linear),
the share the continuous space explains with no clustering.
Item sets, fixed before running:
  strict, all inputs   pool + foreign-policy items in none of the three typologies' clustering inputs, minus any item
                with |polychoric r| > 0.70 with any input (cross-typology comparison)
  strict, revised      same but relative to the revised 41 inputs only (the cap curve)
  behavior and identity   validated 2024 turnout, Harris vs Trump, pid7, ideo5 (as heldout_test.py)
Uncertainty: 200 respondent bootstrap resamples (seed 42) for the differences reported.
Also: weighted composition of each revised cap-5 cluster by production party.
Writes outputs/heldout_v2/{curve.csv, compare.csv, items.csv, cap5_composition.csv}.
"""
import numpy as np
import pandas as pd

import heldout_test as ht
import item_pool as ip
import loading_draws as ld
import reestimate_loadings as rl
import rescore_refit as rr

OUT = rl.OUT / "heldout_v2"
N_BOOT = 200


def wr2(y, X, w):
    ok = ~np.isnan(y)
    y, X, w = y[ok], X[ok], w[ok]
    A = np.column_stack([np.ones(len(y)), X])
    sw = np.sqrt(w)
    beta = np.linalg.lstsq(A * sw[:, None], y * sw, rcond=None)[0]
    res = y - A @ beta
    m = np.average(y, weights=w)
    return float(1 - (w * res ** 2).sum() / (w * (y - m) ** 2).sum())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    S = pd.read_csv(rl.OUT / "stage_c_v2/scores.csv")
    z = np.load(rl.OUT / "stage_c_v2/labels.npz")
    rev = {K: pd.Series(ld.modal_solution(list(zip(range(42, 62), z[f"{K}_seed"], z[f"{K}_seed_bounds"])))[0], index=S.caseid.values)
           for K in range(2, 11)}
    S0 = pd.read_csv(rl.OUT / "four_dim/scores.csv", usecols=["caseid"])
    z0 = np.load(rl.OUT / "four_dim/labels.npz")
    cur = pd.Series(ld.modal_solution(list(zip(range(42, 62), z0["10_seed"], z0["10_seed_bounds"])))[0], index=S0.caseid.values)
    fs = pd.read_csv(rl.ROOT / "data/processed/efa_factor_scores.csv", usecols=["caseid"])
    typ = pd.read_csv(rl.ROOT / "data/processed/typology_cluster_assignments.csv", usecols=["cluster"])
    prod = pd.Series(typ.cluster.values, index=fs.caseid.values)

    X, w, pid, caseid = ip.load()
    extra = pd.read_stata(rl.eu.CES_PATH, columns=["caseid", "commonpostweight", "TS_g2024", "CC24_410", "ideo5"], convert_categoricals=True)
    extra = extra[pd.to_numeric(extra.commonpostweight, errors="coerce") > 0].reset_index(drop=True)
    assert np.array_equal(extra.caseid.values, caseid)
    both = np.isin(caseid, prod.index) & np.isin(caseid, cur.index) & np.isin(caseid, S.caseid.values)
    ids = caseid[both]
    X, w, pid, extra = X[both].reset_index(drop=True), w[both], pid[both], extra[both].reset_index(drop=True)
    F = S.set_index("caseid").loc[ids, ["RT", "TR", "SO", "PC"]].values
    G = {f"revised {K}": pd.factorize(rev[K].loc[ids].values)[0] for K in rev}
    G["current ten"] = pd.factorize(cur.loc[ids].values)[0]
    G["production nine"] = pd.factorize(prod.loc[ids].values)[0]
    K_ = {k: g.max() + 1 for k, g in G.items()}
    print(f"n = {len(ids):,}", flush=True)

    rev41 = set(pd.read_csv(rl.OUT / "stage_c_v2/loadings.csv", index_col=0).index)
    cur30 = set(pd.read_csv(rl.OUT / "stage_c/pool69_loadings_k5.csv", index_col=0).index)
    prod24 = set(rl.eu.ITEMS_24)
    R = ip.poly_all(X, w)

    def strict(inputs):
        held = [c for c in ip.POOL + ip.FP if c not in inputs and c not in ("CC24_302", "CC24_303")]
        return [c for c in held if R.loc[c, sorted(inputs)].abs().max() <= 0.70]
    s_all, s_rev = strict(rev41 | cur30 | prod24), strict(rev41)
    turnout = extra.TS_g2024.isin([1, 2, 3, 4, 5, 6]).astype(float).values
    vote = extra.CC24_410.astype(str).map({"Kamala Harris": 1.0, "Donald Trump": 0.0}).astype(float).values
    ideo = extra.ideo5.astype(str).map({"Very liberal": 1, "Liberal": 2, "Moderate": 3, "Conservative": 4, "Very conservative": 5}).astype(float).values
    V = {c: X[c].values.astype(float) for c in sorted(set(s_all) | set(s_rev))}
    V.update({"validated 2024 turnout": turnout, "Harris vs Trump": vote, "pid7": pid, "ideo5": ideo})
    beh = ["validated 2024 turnout", "Harris vs Trump", "pid7", "ideo5"]
    print({"strict, all inputs": len(s_all), "strict, revised": len(s_rev)}, "\nstrict all:", s_all, "\nstrict revised:", s_rev, flush=True)

    items = pd.DataFrame([{"item": c, **{k: ht.eta2(V[c], g, w, K_[k]) for k, g in G.items()},
                           "continuous R2": wr2(V[c], F, w)} for c in V]).set_index("item")
    items.round(4).to_csv(OUT / "items.csv")

    curve = []
    for name, cols in (("strict, revised", s_rev), ("behavior and identity", beh)):
        ceil = items.loc[cols, "continuous R2"].mean()
        for K in range(2, 11):
            e = items.loc[cols, f"revised {K}"].mean()
            curve.append({"set": name, "K": K, "mean_eta2": round(e, 4), "share_of_continuous": round(e / ceil, 3),
                          "continuous_R2": round(ceil, 4)})
    curve = pd.DataFrame(curve)
    curve.to_csv(OUT / "curve.csv", index=False)
    print("\ncap curve:\n", curve.to_string(index=False), flush=True)

    pairs = [("revised 10", "current ten"), ("revised 9", "production nine"), ("revised 10", "production nine"),
             ("current ten", "production nine"), ("revised 10", "revised 5"), ("revised 5", "revised 4")]
    sets = {"strict, all inputs": s_all, "behavior and identity": beh}
    rng = np.random.default_rng(42)
    boots = {(s, a, b): [] for s in sets for a, b in pairs}
    for _ in range(N_BOOT):
        i = rng.integers(0, len(w), len(w))
        for s, cols in sets.items():
            e = {k: np.mean([ht.eta2(V[c][i], G[k][i], w[i], K_[k]) for c in cols]) for k in {x for p in pairs for x in p}}
            for a, b in pairs:
                boots[(s, a, b)].append(e[a] - e[b])
    rows = []
    for s, cols in sets.items():
        for a, b in pairs:
            d = items.loc[cols, a].mean() - items.loc[cols, b].mean()
            bb = np.array(boots[(s, a, b)])
            rows.append({"set": s, "n_items": len(cols), "a": a, "b": b, "a_eta2": round(items.loc[cols, a].mean(), 4),
                         "b_eta2": round(items.loc[cols, b].mean(), 4), "diff": round(d, 4),
                         "lo": round(np.quantile(bb, .025), 4), "hi": round(np.quantile(bb, .975), 4)})
    cmp_ = pd.DataFrame(rows)
    cmp_.to_csv(OUT / "compare.csv", index=False)
    print("\ncomparisons:\n", cmp_.to_string(index=False), flush=True)

    g5, gp = rev[5].loc[ids].values, prod.loc[ids].values
    comp = []
    for c in np.unique(g5):
        m = g5 == c
        sh = pd.Series(w[m]).groupby(gp[m]).sum() / w[m].sum()
        row = {"cluster": int(c), "share": round(100 * w[m].sum() / w.sum(), 1)}
        row.update({rr.pc.CLUSTER_TO_PARTY[k]: round(100 * v) for k, v in sh.items()})
        comp.append(row)
    comp = pd.DataFrame(comp)
    sty = gp == [k for k, v in rr.pc.CLUSTER_TO_PARTY.items() if v == "STY"][0]
    where = pd.Series(w[sty]).groupby(g5[sty]).sum() / w[sty].sum()
    comp["share_of_STY_here"] = comp.cluster.map((100 * where).round())
    comp.to_csv(OUT / "cap5_composition.csv", index=False)
    print("\ncap-5 clusters by production party (% of cluster):\n", comp.to_string(index=False))


if __name__ == "__main__":
    main()

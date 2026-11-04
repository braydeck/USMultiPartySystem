"""Which typology describes answers it was not built from? Production's nine parties vs the ten four-dimension clusters.

Data: CES 2024 Common Content, the 45,214 respondents assigned in both typologies, weight commonpostweight.
  Production: data/processed/typology_cluster_assignments.csv (row order of efa_factor_scores.csv).
  New: outputs/four_dim/labels.npz, cap-10 modal seed solution (and cap 9, for an equal group count).
Measure: weighted eta-squared per item (share of the item's variance lying between groups), on the numeric recode
of item_pool.recode; mean across an item set.
Item sets, fixed before running:
  held-out      every pool or foreign-policy item in neither clustering set (production's 24, the new 30)
  held-out, strict   held-out minus any item whose pairwise polychoric with a clustering item of either typology
                exceeds |0.70| (the Stage B redundancy bar), so near-copies of an input don't count as held out
  foreign policy   the 21 troop / Ukraine / Israel-Gaza checkboxes (in no pool either typology was built from)
  behavior and identity   validated 2024 turnout (TS_g2024 1-6 = voted, else 0), Harris vs Trump among
                voters (CC24_410), pid7, ideo5; reported separately
Uncertainty: 200 respondent bootstrap resamples (seed 42) of each set's mean eta-squared difference.
Writes outputs/heldout/{items.csv, summary.csv}.
"""
import numpy as np
import pandas as pd

import item_pool as ip
import loading_draws as ld
import reestimate_loadings as rl
import rescore_refit as rr

OUT = rl.OUT / "heldout"
N_BOOT = 200


def eta2(x, g, w, k):
    ok = ~np.isnan(x)
    x, g, w = x[ok], g[ok], w[ok]
    W = np.bincount(g, w, k)
    S = np.bincount(g, w * x, k)
    grand = S.sum() / W.sum()
    m = np.divide(S, W, out=np.full(k, grand), where=W > 0)
    return float((W * (m - grand) ** 2).sum() / (w * (x - grand) ** 2).sum())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    S = pd.read_csv(rl.OUT / "four_dim" / "scores.csv", usecols=["caseid"])
    z = np.load(rl.OUT / "four_dim" / "labels.npz")
    new10 = pd.Series(ld.modal_solution(list(zip(range(42, 62), z["10_seed"], z["10_seed_bounds"])))[0], index=S.caseid.values)
    new9 = pd.Series(ld.modal_solution(list(zip(range(42, 62), z["9_seed"], z["9_seed_bounds"])))[0], index=S.caseid.values)
    fs = pd.read_csv(rl.ROOT / "data/processed/efa_factor_scores.csv", usecols=["caseid"])
    typ = pd.read_csv(rl.ROOT / "data/processed/typology_cluster_assignments.csv", usecols=["cluster"])
    prod = pd.Series(typ.cluster.values, index=fs.caseid.values)

    X, w, pid, caseid = ip.load()
    extra = pd.read_stata(rl.eu.CES_PATH, columns=["caseid", "commonpostweight", "TS_g2024", "CC24_410", "ideo5"],
                          convert_categoricals=True)
    extra = extra[pd.to_numeric(extra.commonpostweight, errors="coerce") > 0].reset_index(drop=True)
    assert np.array_equal(extra.caseid.values, caseid)
    both = np.isin(caseid, prod.index) & np.isin(caseid, new10.index)
    ids = caseid[both]
    X, w, pid, extra = X[both].reset_index(drop=True), w[both], pid[both], extra[both].reset_index(drop=True)
    G = {"production 9": pd.factorize(prod.loc[ids].values)[0], "new 10": pd.factorize(new10.loc[ids].values)[0],
         "new at cap 9": pd.factorize(new9.loc[ids].values)[0]}
    print(f"n = {len(ids):,}; groups: " + ", ".join(f"{k} {g.max() + 1}" for k, g in G.items()))

    prod24 = set(rl.eu.ITEMS_24)
    new30 = set(pd.read_csv(rl.OUT / "stage_c" / "pool69_loadings_k5.csv", index_col=0).index)
    inputs = prod24 | new30
    held = [c for c in ip.POOL + ip.FP if c not in inputs]
    R = ip.poly_all(X, w)
    strict = [c for c in held if R.loc[c, sorted(inputs)].abs().max() <= 0.70]
    turnout = extra.TS_g2024.isin([1, 2, 3, 4, 5, 6]).astype(float).values
    vote = extra.CC24_410.astype(str).map({"Kamala Harris": 1.0, "Donald Trump": 0.0}).astype(float).values
    ideo = extra.ideo5.astype(str).map({"Very liberal": 1, "Liberal": 2, "Moderate": 3, "Conservative": 4,
                                        "Very conservative": 5}).astype(float).values
    V = {c: X[c].values.astype(float) for c in held}
    V.update({"validated 2024 turnout": turnout, "Harris vs Trump": vote, "pid7": pid, "ideo5": ideo})
    sets = {"held-out": held, "held-out, strict": strict, "foreign policy": list(ip.FP),
            "behavior and identity": ["validated 2024 turnout", "Harris vs Trump", "pid7", "ideo5"]}
    print({k: len(v) for k, v in sets.items()})
    print("dropped from strict (near-copy of an input):", [c for c in held if c not in strict])

    K = {k: g.max() + 1 for k, g in G.items()}
    items = pd.DataFrame([{"item": c, **{k: eta2(V[c], g, w, K[k]) for k, g in G.items()}} for c in V]).set_index("item")
    items["new 10 minus production"] = items["new 10"] - items["production 9"]
    items.round(4).to_csv(OUT / "items.csv")

    rng = np.random.default_rng(42)
    boots = {s: [] for s in sets}
    for _ in range(N_BOOT):
        i = rng.integers(0, len(w), len(w))
        for s, cols in sets.items():
            e = {k: np.mean([eta2(V[c][i], g[i], w[i], K[k]) for c in cols]) for k, g in G.items()}
            boots[s].append((e["new 10"] - e["production 9"], e["new at cap 9"] - e["production 9"]))
    rows = []
    for s, cols in sets.items():
        b = np.array(boots[s])
        rows.append({"set": s, "n_items": len(cols), **{k: round(items.loc[cols, k].mean(), 4) for k in G},
                     "new10_minus_prod": round(items.loc[cols, "new 10"].mean() - items.loc[cols, "production 9"].mean(), 4),
                     "diff_lo": round(np.quantile(b[:, 0], 0.025), 4), "diff_hi": round(np.quantile(b[:, 0], 0.975), 4),
                     "p_new10_higher": round((b[:, 0] > 0).mean(), 3),
                     "new9_minus_prod": round(items.loc[cols, "new at cap 9"].mean() - items.loc[cols, "production 9"].mean(), 4),
                     "new9_lo": round(np.quantile(b[:, 1], 0.025), 4), "new9_hi": round(np.quantile(b[:, 1], 0.975), 4),
                     "items_new10_higher": int((items.loc[cols, "new 10 minus production"] > 0).sum())})
    summ = pd.DataFrame(rows)
    summ.to_csv(OUT / "summary.csv", index=False)
    print(summ.to_string(index=False))
    print("\nper item:\n", items.sort_values("new 10 minus production").round(3).to_string())


if __name__ == "__main__":
    main()

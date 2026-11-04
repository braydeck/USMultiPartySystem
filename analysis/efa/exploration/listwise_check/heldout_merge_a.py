"""What does the A.1 / A.2 split add on the held-out domestic items? (2026-11-03, after the factor-redraw test showed
A.2 folding into A.1 in 8 of 50 draws.)

Data and groupings: as heldout_domestic.py (n = 45,214; the 7 held-out domestic items). Revised ten = the cap-10
modal solution of outputs/stage_c_v2/, names from outputs/profile_v2/names.csv. "Revised ten, A merged" relabels
A.2 as A.1 (nine groups, no refit). Benchmarks: the cost of merging every other pair of the ten (45 pairs), the
revised cap-9 fit, and the current ten. Merging always lowers eta2, so the pair benchmark is what reads the A.1/A.2
cost as large or small.
Uncertainty: 200 respondent bootstrap resamples (seed 42).
Writes outputs/heldout_v2/{merge_a_compare.csv, merge_pairs.csv, merge_a_items.csv}.
"""
import itertools

import numpy as np
import pandas as pd

import heldout_domestic as hd
import heldout_test as ht
import item_pool as ip
import loading_draws as ld
import reestimate_loadings as rl

OUT = rl.OUT / "heldout_v2"


def main():
    S = pd.read_csv(rl.OUT / "stage_c_v2/scores.csv")
    z = np.load(rl.OUT / "stage_c_v2/labels.npz")
    rev = {K: pd.Series(ld.modal_solution(list(zip(range(42, 62), z[f"{K}_seed"], z[f"{K}_seed_bounds"])))[0], index=S.caseid.values) for K in (9, 10)}
    S0 = pd.read_csv(rl.OUT / "four_dim/scores.csv", usecols=["caseid"])
    z0 = np.load(rl.OUT / "four_dim/labels.npz")
    cur = pd.Series(ld.modal_solution(list(zip(range(42, 62), z0["10_seed"], z0["10_seed_bounds"])))[0], index=S0.caseid.values)
    fs = pd.read_csv(rl.ROOT / "data/processed/efa_factor_scores.csv", usecols=["caseid"])
    typ = pd.read_csv(rl.ROOT / "data/processed/typology_cluster_assignments.csv", usecols=["cluster"])
    prod = pd.Series(typ.cluster.values, index=fs.caseid.values)
    X, w, _, caseid = ip.load()
    both = np.isin(caseid, prod.index) & np.isin(caseid, cur.index) & np.isin(caseid, S.caseid.values)
    ids, X, w = caseid[both], X[both].reset_index(drop=True), w[both]

    nm = pd.read_csv(rl.OUT / "profile_v2/names.csv")
    nm = nm[nm.cap == 10]
    name = dict(zip(nm.cluster, nm.name))
    code = {v: k for k, v in name.items()}
    ten = rev[10].loc[ids].values
    merged = np.where(ten == code["A.2"], code["A.1"], ten)
    G = {"revised 10": ten, "revised 10, A merged": merged, "revised 9": rev[9].loc[ids].values, "current ten": cur.loc[ids].values}
    G = {k: pd.factorize(g)[0] for k, g in G.items()}
    V = {c: X[c].values.astype(float) for c in hd.DOM}

    def dom(g, idx, k):
        return np.mean([ht.eta2(V[c][idx], g[idx], w[idx], k) for c in hd.DOM])

    allidx = np.arange(len(w))
    full = {k: dom(g, allidx, g.max() + 1) for k, g in G.items()}

    # every pairwise merge of the ten, full sample
    pairs = []
    for a, b in itertools.combinations(sorted(name), 2):
        g = pd.factorize(np.where(ten == b, a, ten))[0]
        pairs.append({"merge": f"{name[a]} + {name[b]}", "domestic": round(dom(g, allidx, 9), 4),
                      "cost": round(full["revised 10"] - dom(g, allidx, 9), 4)})
    pairs = pd.DataFrame(pairs).sort_values("cost").reset_index(drop=True)
    pairs["rank_of_45"] = np.arange(1, len(pairs) + 1)
    pairs.to_csv(OUT / "merge_pairs.csv", index=False)

    rng = np.random.default_rng(42)
    boots = []
    for _ in range(200):
        idx = rng.integers(0, len(w), len(w))
        boots.append({k: dom(g, idx, g.max() + 1) for k, g in G.items()})
    rows = []
    for a, b in [("revised 10", "revised 10, A merged"), ("revised 10, A merged", "revised 9"), ("revised 10, A merged", "current ten")]:
        d = np.array([bb[a] - bb[b] for bb in boots])
        rows.append({"a": a, "b": b, "a_eta2": round(full[a], 4), "b_eta2": round(full[b], 4), "diff": round(full[a] - full[b], 4),
                     "lo": round(np.quantile(d, .025), 4), "hi": round(np.quantile(d, .975), 4), "p_a_higher": round((d > 0).mean(), 3)})
    cmp_ = pd.DataFrame(rows)
    cmp_.to_csv(OUT / "merge_a_compare.csv", index=False)

    items = pd.DataFrame([{"item": c, "revised 10": ht.eta2(V[c], G["revised 10"], w, 10),
                           "A merged": ht.eta2(V[c], G["revised 10, A merged"], w, 9)} for c in hd.DOM]).set_index("item")
    items["cost"] = items["revised 10"] - items["A merged"]
    items.round(4).to_csv(OUT / "merge_a_items.csv")

    print(f"n = {len(w):,}; 7 held-out domestic items\n")
    print(cmp_.to_string(index=False))
    print("\nper item:\n", items.round(4).to_string())
    print("\npairwise merges of the ten (cost = drop in mean domestic eta2):\n", pairs.to_string(index=False))


if __name__ == "__main__":
    main()

"""Held-out domestic policy items as the primary held-out measure (researcher, 2026-11-03); foreign policy reported
separately, each of its three questions averaged as one.

Data and groupings: as heldout_v2.py (n = 45,214 assigned in all compared typologies; revised rule caps 2-10, current
ten, production nine). Items: the strict held-out set of heldout_v2.py (in no typology's clustering input, |r| <= 0.70
with every input). Domestic = the non-checkbox items (7). Foreign policy = troop use (CC24_420_*), Ukraine
(CC24_308a_*), Israel-Gaza (CC24_308b_*), each question's boxes averaged first, then the three questions averaged.
Uncertainty: 200 respondent bootstrap resamples (seed 42).
Writes outputs/heldout_v2/{domestic_curve.csv, domestic_compare.csv}.
"""
import numpy as np
import pandas as pd

import heldout_test as ht
import item_pool as ip
import loading_draws as ld
import reestimate_loadings as rl

OUT = rl.OUT / "heldout_v2"
DOM = ["CC24_321c", "CC24_321f", "CC24_324c", "CC24_328a", "CC24_328c", "CC24_441e", "CC24_441g"]
FPQ = {"troop use": "CC24_420", "Ukraine": "CC24_308a", "Israel-Gaza": "CC24_308b"}


def main():
    S = pd.read_csv(rl.OUT / "stage_c_v2/scores.csv")
    z = np.load(rl.OUT / "stage_c_v2/labels.npz")
    rev = {K: pd.Series(ld.modal_solution(list(zip(range(42, 62), z[f"{K}_seed"], z[f"{K}_seed_bounds"])))[0], index=S.caseid.values) for K in range(2, 11)}
    S0 = pd.read_csv(rl.OUT / "four_dim/scores.csv", usecols=["caseid"])
    z0 = np.load(rl.OUT / "four_dim/labels.npz")
    cur = pd.Series(ld.modal_solution(list(zip(range(42, 62), z0["10_seed"], z0["10_seed_bounds"])))[0], index=S0.caseid.values)
    fs = pd.read_csv(rl.ROOT / "data/processed/efa_factor_scores.csv", usecols=["caseid"])
    typ = pd.read_csv(rl.ROOT / "data/processed/typology_cluster_assignments.csv", usecols=["cluster"])
    prod = pd.Series(typ.cluster.values, index=fs.caseid.values)
    X, w, _, caseid = ip.load()
    both = np.isin(caseid, prod.index) & np.isin(caseid, cur.index) & np.isin(caseid, S.caseid.values)
    ids, X, w = caseid[both], X[both].reset_index(drop=True), w[both]
    G = {f"revised {K}": pd.factorize(rev[K].loc[ids].values)[0] for K in rev}
    G["current ten"] = pd.factorize(cur.loc[ids].values)[0]
    G["production nine"] = pd.factorize(prod.loc[ids].values)[0]
    K_ = {k: g.max() + 1 for k, g in G.items()}
    held = pd.read_csv(OUT / "items.csv", index_col=0).index
    fpq = {q: [c for c in held if c.startswith(p + "_")] for q, p in FPQ.items()}
    V = {c: X[c].values.astype(float) for c in DOM + sum(fpq.values(), [])}

    def measures(idx):
        out = {}
        for k, g in G.items():
            e = lambda c: ht.eta2(V[c][idx], g[idx], w[idx], K_[k])
            out[k] = (np.mean([e(c) for c in DOM]), np.mean([np.mean([e(c) for c in cs]) for cs in fpq.values()]))
        return out
    full = measures(np.arange(len(w)))
    rng = np.random.default_rng(42)
    boots = [measures(rng.integers(0, len(w), len(w))) for _ in range(200)]

    curve = pd.DataFrame([{"grouping": k, "domestic": round(v[0], 4), "foreign_policy_by_question": round(v[1], 4)} for k, v in full.items()])
    curve.to_csv(OUT / "domestic_curve.csv", index=False)
    print(f"n = {len(w):,}; foreign-policy boxes per question: {[len(v) for v in fpq.values()]}\n", curve.to_string(index=False))
    pairs = [("revised 10", "current ten"), ("revised 10", "production nine"), ("revised 9", "production nine"),
             ("current ten", "production nine"), ("revised 10", "revised 5"), ("revised 5", "revised 4")]
    rows = []
    for j, setname in ((0, "domestic"), (1, "foreign policy by question")):
        for a, b in pairs:
            d = np.array([bb[a][j] - bb[b][j] for bb in boots])
            rows.append({"set": setname, "a": a, "b": b, "diff": round(full[a][j] - full[b][j], 4),
                         "lo": round(np.quantile(d, .025), 4), "hi": round(np.quantile(d, .975), 4), "p_a_higher": round((d > 0).mean(), 3)})
    cmp_ = pd.DataFrame(rows)
    cmp_.to_csv(OUT / "domestic_compare.csv", index=False)
    print("\n", cmp_.to_string(index=False))


if __name__ == "__main__":
    main()

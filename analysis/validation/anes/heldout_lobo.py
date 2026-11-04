"""Leave-one-battery-out held-out test for the primary ANES segmentation (no-foreign-policy Stage C), caps 2-10.

Data: ANES 2024 Time Series CSV (2025-08-08 release), post weight V240108a; pool config/anes_independent_pool.csv;
primary run outputs/stage_c_nofp/ (109 retained items, k = 7, five clustering factors, 4,712 respondents scored).
Question: at each cap, how much of each domestic item's variance lies between segments built without that item's
battery? Every retained item is scored exactly once, by a typology that never saw its battery.

Per battery b of the retained pool (80 batteries), fixed before running:
  1. Drop b's items from the 109; fit PAF + oblimin at k = 7 on the full-sample matrix (stage_c.py's: regularized
     pairwise polychoric over the Stage B univariate pool, subset). No resampled screens and no new entry test: k,
     the retained items and the five clustering factors are held fixed, so the typology stays the primary one.
  2. Match the refit factors to the primary fit's factors one-to-one (Hungarian on |Tucker phi| over the shared
     items), sign-align, and take the five clustering factors' matches. A match under phi 0.85 is flagged: that
     battery's refit is a different factor space and is reported separately.
  3. Available-item scores for the same 4,712 respondents, the anchor residualization, then DPGMM at caps 2-10
     with stage_c.py's selection (20 seeds, modal solution, best lower bound).
  4. Weighted eta-squared of each of b's items at each cap; ARI of the refit labels with the primary labels.
The no-battery fit is run the same way and must reproduce the primary loadings and cap-5 labels.
Items on the same topic in other batteries stay in the fit; there is no |r| screen. Comparisons across caps read the
step sizes: eta-squared rises with any finer partition.
Uncertainty: 200 respondent bootstrap resamples (seed 42) of each cap-to-cap step, labels fixed.
Writes outputs/heldout_lobo/{items.csv, batteries.csv, curve.csv, steps.csv}; per-battery results cached in
outputs/heldout_lobo/cache/ (not committed). Log via tee.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import pickle
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.optimize import linear_sum_assignment

import describe_clusters as dc
import dims_check as dk
import heldout_test as ht
import independent_clustering as ic
import independent_efa as ie
import matched_efa as me
import stage_c as sc
from common import clustering as cl
from common import efa_math as em

OUT = me.OUT / "heldout_lobo"
CACHE = OUT / "cache"
PRIMARY = me.OUT / "stage_c_nofp"
K, PHI, N_BOOT = 7, 0.85, 200


def tucker(A, B):
    return (A.T @ B) / np.sqrt(np.outer((A ** 2).sum(0), (B ** 2).sum(0)))


def run_battery(b, items_b, R_ret, retained, L0, passing, D, w):
    path = CACHE / f"{b or 'none'}.pkl".replace("/", "_")
    if path.exists():
        return pickle.loads(path.read_bytes())
    use = [i for i, c in enumerate(retained) if c not in items_b]
    ids = [retained[i] for i in use]
    R = R_ret[np.ix_(use, use)]
    L, Phi, _ = me.fit(R, K)
    P = tucker(L0[use], L)
    r, c = linear_sum_assignment(-np.abs(P))
    match = dict(zip(r, c))
    cols = [match[j] for j in passing]
    phis = np.array([P[j, match[j]] for j in passing])
    sign = np.sign(phis)
    F, _ = ic.available_scores(D[ids], w, R, L, Phi)
    X = dk.residualize(F[:, cols] * sign, w)
    labels = dict(ht.modal_labels(X, cap) for cap in ic.KS)
    res = {"battery": b, "items": items_b, "min_phi": float(np.abs(phis).min()), "phis": np.abs(phis).round(3).tolist(),
           "labels": labels}
    path.write_bytes(pickle.dumps(res))
    return res


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(exist_ok=True)
    (OUT / ".gitignore").write_text("cache/\n")
    items, w_all, _, cw = ie.load_pool()
    desc, keep_w = dc.descriptors()
    items.index = desc.caseid[keep_w].values

    ids_full = sc.stage_b_univariate(items, w_all, [])
    raw = pd.DataFrame(np.load(ht.CACHE / f"R_pool{items.shape[1]}.npy"), index=items.columns, columns=items.columns)
    R_full = em.regularize_corr(raw.loc[ids_full, ids_full].values)
    load0 = pd.read_csv(PRIMARY / "loadings_k7.csv", index_col=0)
    retained = list(load0.index)
    pos = [ids_full.index(c) for c in retained]
    R_ret = R_full[np.ix_(pos, pos)]
    L0 = load0[[f"N{j + 1}" for j in range(K)]].values
    et = pd.read_csv(PRIMARY / "entry_test.csv")
    passing = sorted(et.factor[et.clusters])
    prim = pd.read_csv(PRIMARY / "clusters.csv")
    D = items.loc[prim.caseid]
    w = pd.Series(w_all, index=items.index).loc[prim.caseid].values
    batteries = sorted(cw.battery_id[retained].unique())
    print(f"{len(retained)} retained items in {len(batteries)} batteries; {len(prim):,} respondents; "
          f"clustering factors {passing}", flush=True)

    base = run_battery(None, [], R_ret, retained, L0, passing, D, w)
    print(f"no-battery refit: min phi vs primary {base['min_phi']:.3f}; cap-5 ARI vs clusters.csv "
          f"{cl.ari(base['labels'][5], prim.cluster.values):.3f}", flush=True)
    assert base["min_phi"] > 0.999 and cl.ari(base["labels"][5], prim.cluster.values) > 0.999

    todo = [(b, [c for c in retained if cw.battery_id[c] == b]) for b in batteries]
    res = Parallel(n_jobs=8, verbose=5)(delayed(run_battery)(b, ib, R_ret, retained, L0, passing, D, w)
                                        for b, ib in todo)

    V = {c: D[c].values.astype(float) for c in retained}
    rows, brows = [], []
    for r in res:
        brows.append({"battery": r["battery"], "n_items": len(r["items"]), "min_phi": round(r["min_phi"], 3),
                      "phis": r["phis"], "same_space": r["min_phi"] >= PHI,
                      **{f"ari_cap{cap}": round(cl.ari(r["labels"][cap], base["labels"][cap]), 3) for cap in ic.KS}})
        for c in r["items"]:
            rows.append({"item": c, "battery": r["battery"], "domain": cw.domain[c], "label": cw.label[c][:80],
                         "same_space": r["min_phi"] >= PHI,
                         **{f"heldout {cap}": round(ht.eta2(V[c], pd.factorize(r["labels"][cap])[0], w), 4) for cap in ic.KS},
                         **{f"in-sample {cap}": round(ht.eta2(V[c], pd.factorize(base["labels"][cap])[0], w), 4) for cap in ic.KS}})
    it, bt = pd.DataFrame(rows), pd.DataFrame(brows)
    it.to_csv(OUT / "items.csv", index=False)
    bt.to_csv(OUT / "batteries.csv", index=False)
    print(f"\nbatteries whose refit stays in the primary space (all five matches phi >= {PHI}): "
          f"{int(bt.same_space.sum())} of {len(bt)}; items {int(it.same_space.sum())} of {len(it)}", flush=True)
    flagged = bt[~bt.same_space]
    if len(flagged):
        print("flagged:\n" + flagged[["battery", "n_items", "min_phi", "phis"]].to_string(index=False), flush=True)

    curve = []
    for name, sub in (("all retained items", it), ("same-space batteries only", it[it.same_space])):
        for cap in ic.KS:
            curve.append({"set": name, "n_items": len(sub), "K": cap, "heldout_eta2": round(sub[f"heldout {cap}"].mean(), 4),
                          "in_sample_eta2": round(sub[f"in-sample {cap}"].mean(), 4),
                          "mean_ari_vs_primary": round(bt[f"ari_cap{cap}"].mean(), 3)})
    curve = pd.DataFrame(curve)
    curve.to_csv(OUT / "curve.csv", index=False)
    with pd.option_context("display.width", 200):
        print("\n" + curve.to_string(index=False), flush=True)

    lab = {r["battery"]: {cap: pd.factorize(r["labels"][cap])[0] for cap in ic.KS} for r in res}
    rng = np.random.default_rng(42)
    boot = {cap: [] for cap in ic.KS}
    for _ in range(N_BOOT):
        i = rng.integers(0, len(w), len(w))
        for cap in ic.KS:
            boot[cap].append(np.mean([ht.eta2(V[c][i], lab[b][cap][i], w[i]) for c, b in zip(it.item, it.battery)]))
    steps = []
    for cap in range(3, 11):
        bb = np.array(boot[cap]) - np.array(boot[cap - 1])
        steps.append({"from": cap - 1, "to": cap, "gain": round(it[f"heldout {cap}"].mean() - it[f"heldout {cap - 1}"].mean(), 4),
                      "lo": round(np.quantile(bb, .025), 4), "hi": round(np.quantile(bb, .975), 4),
                      "p_gain": round(float((bb > 0).mean()), 3)})
    steps = pd.DataFrame(steps)
    steps.to_csv(OUT / "steps.csv", index=False)
    print("\ncap-to-cap steps, all retained items:\n" + steps.to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())

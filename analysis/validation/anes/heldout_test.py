"""Held-out items for the ANES Stage C segmentations (§3c step 6, docs/EFA_ITEM_SELECTION_ROBUSTNESS.md).

Data: ANES 2024 Time Series CSV (2025-08-08 release), post weight V240108a; pool config/anes_independent_pool.csv.
Groupings, on respondents assigned in all three:
  no-foreign-policy   outputs/stage_c_nofp/ (primary since 2026-11-03), cap 5; caps 2-10 refit here on the same scores
                      (residualized clustering factors from clusters.csv) with stage_c.py's selection: 20 seeds,
                      modal solution, best lower bound. The cap-5 refit must reproduce clusters.csv.
  with foreign policy outputs/stage_c/, cap 5
  production four     outputs/clustering/independent_available/independent_clusters.csv
Clustering inputs: every item retained in each fit (loadings_k7.csv; outputs/independent_loadings.csv for production).
Measure: weighted eta-squared per item (between-group share of the item's variance, answered respondents only), on
the pool's numeric recodes, averaged over an item set. Ceiling: weighted linear R^2 of each item on the five
no-foreign-policy clustering scores, the share the continuous space explains with no clustering. Chance: mean eta^2
over 20 label permutations (seed 42) at each cap.
Item sets, fixed before running:
  strict, all inputs     pool items in none of the three fits' inputs, minus any with full-sample weighted polychoric
                         |r| > 0.70 with any input (cross-typology comparison)
  strict, no-FP          same relative to the no-foreign-policy inputs only (cap curve); includes foreign policy
  foreign policy         the 14 foreign_policy_nation items (none is a no-foreign-policy input)
Policy items only: vote, turnout, party ID and ideology are not a measure of cluster quality (§3c; researcher).
Uncertainty: 200 respondent bootstrap resamples (seed 42) for each reported difference.
Writes outputs/heldout/{curve.csv, compare.csv, items.csv, sets.csv}; the full-pool polychoric is cached in
outputs/heldout/cache/ (not committed). Log via tee.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.sparse.csgraph import connected_components

import describe_clusters as dc
import dims_check as dk
import independent_clustering as ic
import independent_efa as ie
import matched_efa as me
from common import clustering as cl
from common import efa_math as em

OUT = me.OUT / "heldout"
CACHE = OUT / "cache"
N_BOOT, N_PERM, R_MAX = 200, 20, 0.70
FP_DOMAIN = "foreign_policy_nation"


def eta2(y, g, w):
    ok = ~np.isnan(y)
    y, g, w = y[ok], g[ok], w[ok]
    m = np.average(y, weights=w)
    tot = (w * (y - m) ** 2).sum()
    W = np.bincount(g, weights=w)
    M = np.bincount(g, weights=w * y)
    nz = W > 0
    return float((W[nz] * (M[nz] / W[nz] - m) ** 2).sum() / tot)


def wr2(y, X, w):
    ok = ~np.isnan(y)
    y, X, w = y[ok], X[ok], w[ok]
    A = np.column_stack([np.ones(len(y)), X]) * np.sqrt(w)[:, None]
    beta = np.linalg.lstsq(A, y * np.sqrt(w), rcond=None)[0]
    res = y - np.column_stack([np.ones(len(y)), X]) @ beta
    m = np.average(y, weights=w)
    return float(1 - (w * res ** 2).sum() / (w * (y - m) ** 2).sum())


def modal_labels(X, K):
    seeds = [ic.job(X, K, "seed", i) for i in ic.SEEDS]
    _, comp = connected_components(ic.pairwise([f[3] for f in seeds]) >= 0.9, directed=False)
    modal = np.bincount(comp).argmax()
    return K, max((f for f, c in zip(seeds, comp) if c == modal), key=lambda f: f[4])[3]


def full_poly(items, w):
    ids = list(items.columns)
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"R_pool{len(ids)}.npy"
    if path.exists():
        R = np.load(path)
    else:
        R = em.polychoric_matrix(items, ids, w, progress=False)
        np.save(path, R)
    return pd.DataFrame(R, index=ids, columns=ids)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / ".gitignore").write_text("cache/\n")
    items, w_all, _, cw = ie.load_pool()
    desc, keep_w = dc.descriptors()
    caseid_all = desc.caseid[keep_w].values
    items.index = caseid_all
    w_by_id = pd.Series(w_all, index=caseid_all)

    nofp = pd.read_csv(me.OUT / "stage_c_nofp" / "clusters.csv")
    et = pd.read_csv(me.OUT / "stage_c_nofp" / "entry_test.csv")
    passing = sorted(et.factor[et.clusters])
    F = nofp[[f"F{j}" for j in range(len(et))]].values
    Xs = dk.residualize(F[:, passing], w_by_id.loc[nofp.caseid].values)
    curve_labels = dict(Parallel(n_jobs=5)(delayed(modal_labels)(Xs, K) for K in ic.KS))
    check = cl.ari(curve_labels[5], nofp.cluster.values)
    print(f"no-foreign-policy cap-5 refit vs clusters.csv: ARI {check:.3f}", flush=True)
    assert check > 0.999

    main_run = pd.read_csv(me.OUT / "stage_c" / "clusters.csv")[["caseid", "cluster"]]
    prod = pd.read_csv(me.OUT / "clustering" / "independent_available" / "independent_clusters.csv")[["caseid", "cluster"]]
    ids = np.array(sorted(set(nofp.caseid) & set(main_run.caseid) & set(prod.caseid)))
    pos = pd.Series(range(len(nofp)), index=nofp.caseid).loc[ids].values
    w = w_by_id.loc[ids].values
    X = Xs[pos]
    G = {f"no-FP {K}": pd.factorize(curve_labels[K][pos])[0] for K in ic.KS}
    G["with FP 5"] = pd.factorize(main_run.set_index("caseid").cluster.loc[ids].values)[0]
    G["production 4"] = pd.factorize(prod.set_index("caseid").cluster.loc[ids].values)[0]
    print(f"respondents in all three: {len(ids):,} (no-FP {len(nofp):,}, with FP {len(main_run):,}, production "
          f"{len(prod):,})", flush=True)

    inputs = {"no-FP": set(pd.read_csv(me.OUT / "stage_c_nofp" / "loadings_k7.csv", index_col=0).index),
              "with FP": set(pd.read_csv(me.OUT / "stage_c" / "loadings_k7.csv", index_col=0).index),
              "production": set(pd.read_csv(me.OUT / "independent_loadings.csv", index_col=0).index) & set(cw.index)}
    print({k: len(v) for k, v in inputs.items()}, flush=True)
    R = full_poly(items, w_all)

    def strict(inp):
        held = [c for c in cw.index if c not in inp]
        return [c for c in held if R.loc[c, sorted(inp)].abs().max() <= R_MAX]
    all_inp = set().union(*inputs.values())
    sets = {"strict, all inputs": strict(all_inp), "strict, no-FP": strict(inputs["no-FP"]),
            "foreign policy": [c for c in cw.index if cw.domain[c] == FP_DOMAIN]}

    V = {c: items.loc[ids, c].values.astype(float) for c in cw.index}

    rows = []
    for s, cols in sets.items():
        for c in cols:
            rows.append({"set": s, "item": c, "label": cw.label[c][:80], "domain": cw.domain[c], "answered": round(float(np.average(~np.isnan(V[c]), weights=w)), 3),
                         **{k: round(eta2(V[c], g, w), 4) for k, g in G.items()}, "continuous R2": round(wr2(V[c], X, w), 4)})
    items_out = pd.DataFrame(rows)
    items_out.to_csv(OUT / "items.csv", index=False)
    pd.DataFrame([{"set": s, "n_items": len(c), "items": "; ".join(c)} for s, c in sets.items()]).to_csv(
        OUT / "sets.csv", index=False)
    print({s: len(c) for s, c in sets.items()}, flush=True)

    rng = np.random.default_rng(42)
    perms = [rng.permutation(len(ids)) for _ in range(N_PERM)]
    curve = []
    for s in ("strict, no-FP", "foreign policy"):
        sub = items_out[items_out.set == s]
        ceil = sub["continuous R2"].mean()
        for K in ic.KS:
            g = G[f"no-FP {K}"]
            e = sub[f"no-FP {K}"].mean()
            chance = np.mean([np.mean([eta2(V[c], g[p], w) for c in sub.item]) for p in perms])
            curve.append({"set": s, "n_items": len(sub), "K": K, "mean_eta2": round(e, 4), "chance_eta2": round(chance, 4),
                          "share_of_continuous": round(e / ceil, 3), "continuous_R2": round(ceil, 4)})
    curve = pd.DataFrame(curve)
    curve.to_csv(OUT / "curve.csv", index=False)
    with pd.option_context("display.width", 200):
        print("\ncap curve (no-foreign-policy space):\n" + curve.to_string(index=False), flush=True)

    pairs = [("no-FP 5", "with FP 5"), ("no-FP 5", "production 4"), ("with FP 5", "production 4")] + \
            [(f"no-FP {K}", f"no-FP {K - 1}") for K in range(3, 11)]
    cmp_sets = {s: sets[s] for s in ("strict, all inputs",)}
    need = {x for p in pairs for x in p}
    boots = {(s, a, b): [] for s in cmp_sets for a, b in pairs}
    for _ in range(N_BOOT):
        i = rng.integers(0, len(ids), len(ids))
        for s, cols in cmp_sets.items():
            e = {k: np.mean([eta2(V[c][i], G[k][i], w[i]) for c in cols]) for k in need}
            for a, b in pairs:
                boots[(s, a, b)].append(e[a] - e[b])
    out = []
    for s, cols in cmp_sets.items():
        sub = items_out[items_out.set == s]
        for a, b in pairs:
            bb = np.array(boots[(s, a, b)])
            out.append({"set": s, "n_items": len(cols), "a": a, "b": b, "a_eta2": round(sub[a].mean(), 4),
                        "b_eta2": round(sub[b].mean(), 4), "diff": round(sub[a].mean() - sub[b].mean(), 4),
                        "lo": round(np.quantile(bb, .025), 4), "hi": round(np.quantile(bb, .975), 4),
                        "p_a_higher": round(float((bb > 0).mean()), 3)})
    out = pd.DataFrame(out)
    out.to_csv(OUT / "compare.csv", index=False)
    with pd.option_context("display.width", 200):
        print("\ncomparisons:\n" + out.to_string(index=False))
        fp = items_out[items_out.set == "foreign policy"][["item", "label", "answered", "no-FP 5", "with FP 5",
                                                            "production 4", "continuous R2"]]
        print("\nforeign-policy items:\n" + fp.to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())

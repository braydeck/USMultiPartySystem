"""Stable clusters on ANES's own factors: cull to 4 items per factor, residualize, pick the cap on stability.

Data: ANES 2024 Time Series CSV (2025-08-08 release), post weight V240108a. Items and loadings from
outputs/independent_loadings.csv (independent_efa.py, 99 items, 10 factors, no party-ID cap).
Rulings: analysis/validation/DECISIONS.md 2026-10-31.

  1. Cull. For each factor, eligible items have it as primary, no other |loading| >= 0.30, and at most
     5% of post-weighted respondents missing. Keep the 4 highest |loading|; if fewer than 4 are
     eligible, fill from the factor's remaining items by |loading|.
  2. Refit on the culled items, listwise. Parallel analysis re-picks k. Factors are named by Tucker
     match to the 99-item solution (a factor drawing 2+ items from several of them is named for all) and oriented so high = the end that correlates with conservative
     self-placement (V241177).
  3. Residualize, CES-style (efa_update.py residualizes religion and values on enforcement). The
     anchor is the factor with the highest mean |r| with the others; every factor with |r| >= 0.40
     with the anchor is replaced by its weighted-OLS residual on the anchor.
  4. Stability, the fair_compare.py procedure: for DPGMM caps K = 5..10, 20 full-data seeds (42-61)
     and 30 resamples. Seed agreement = mean pairwise ARI; solutions = groups of seeds agreeing at
     ARI >= 0.9; per-cluster stability = mean best Jaccard of the medoid resample's clusters across
     the other 29 (>= 0.75 stable, < 0.5 dissolved). Rule: among caps where no cluster dissolves,
     keep the fewest solutions, ties to the larger modal share. The kept fit is the best lower bound
     within the modal solution, as in dpgmm_clustering.py. Unweighted fits, as in production.
  5. Drop-one-factor test at the kept cap, against that cap's own seed-to-seed agreement.

Writes outputs/clustering/independent/ (culled_items.csv, stability_summary.csv,
stability_clusters.csv, drop_one.csv, independent_clusters.csv, run.log via stdout).
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import itertools

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.sparse.csgraph import connected_components
from sklearn.mixture import BayesianGaussianMixture

import describe_clusters as dc
import independent_efa as ie
import matched_efa as me
import recode_matched as rm
from common import clustering as cl
from common import efa_math as em

OUT = me.OUT / "clustering" / "independent"
PER_FACTOR, MAX_CROSS, MAX_MISS, ANCHOR_R = 4, 0.30, 0.05, 0.40
KS, SEEDS, N_BOOT = range(5, 11), range(42, 62), 30
SHORT = {"Immigration and diversity": "immigration", "Trust in institutions (CSES)": "institutional trust",
         "Democratic norms": "democratic norms", "Iran, Russia, China as threats": "foreign threats",
         "Religion and social traditionalism": "religion", "No say in government; gender attitudes": "no say",
         "Government waste and big interests": "government waste", "Israel and Ukraine aid": "Israel and Ukraine",
         "Government role in the economy": "economy", "Gun policy": "guns"}


def cull(load, items, w):
    fc = [c for c in load.columns if c.startswith("N") and c[1:].isdigit()]
    miss = {c: 1 - np.average(items[c].notna(), weights=w) for c in load.index}
    rows = []
    for f in fc:
        sub = load[load.primary == f]
        cross = sub[[g for g in fc if g != f]].abs().max(axis=1)
        order = sub[f].abs().sort_values(ascending=False).index
        eligible = [c for c in order if cross[c] < MAX_CROSS and miss[c] <= MAX_MISS]
        keep = eligible[:PER_FACTOR]
        keep += [c for c in order if c not in keep][:PER_FACTOR - len(keep)]
        for c in keep:
            rows.append({"item": c, "label": load.label[c], "factor": dc.INDEPENDENT_NAMES[f], "loading": load.loc[c, f],
                         "max_cross": round(float(cross[c]), 3), "missing": round(float(miss[c]), 3),
                         "filled": c not in eligible})
    return pd.DataFrame(rows)


def dpgmm(K, seed):
    return BayesianGaussianMixture(n_components=K, covariance_type="full",
                                   weight_concentration_prior_type="dirichlet_process",
                                   n_init=5, random_state=seed, max_iter=2000)


def job(X, K, kind, i):
    if kind == "seed":
        m = dpgmm(K, i).fit(X)
    else:
        m = dpgmm(K, 1000 + i).fit(X[np.random.default_rng(42 + i).integers(0, len(X), len(X))])
    return K, kind, i, m.predict(X).astype(np.int8), float(m.lower_bound_)


def pairwise(L):
    M = np.eye(len(L))
    for a, b in itertools.combinations(range(len(L)), 2):
        M[a, b] = M[b, a] = cl.ari(L[a], L[b])
    return M


def best_jaccard(ref, other):
    return np.array([max(((ref == c) & (other == d)).sum() / ((ref == c) | (other == d)).sum() for d in np.unique(other))
                     for c in np.unique(ref)])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    items, w, pid, cw = ie.load_pool()
    load = pd.read_csv(me.OUT / "independent_loadings.csv", index_col=0)
    fc = [c for c in load.columns if c.startswith("N") and c[1:].isdigit()]
    kept = cull(load, items, w)
    kept.to_csv(OUT / "culled_items.csv", index=False)
    print(f"[1] culled to {len(kept)} items ({int(kept.filled.sum())} filled past the coverage/cross-loading screen)")

    ids = list(kept.item)
    D = items[ids].dropna()
    wD = w[D.index.values]
    print(f"    listwise n = {len(D):,} (99 items: 2,697; post-weighted respondents: {len(items):,})")
    R = em.regularize_corr(em.polychoric_matrix(D.reset_index(drop=True), ids, wD, progress=False))
    k, ev, thr = em.parallel_analysis(R, n_obs=len(D))
    L, Phi, h2 = me.fit(R, k)
    Z, _, _ = em.weighted_standardize(D.values.astype(float), wD)
    F, _ = em.thomson_scores(Z, R, L, Phi)
    full = load.loc[ids, fc].values
    names, phis = [None] * k, {}
    for m in me.cg.match_factors(full, L):
        nm = dc.INDEPENDENT_NAMES[fc[m["factor_1"]]]
        names[m["factor_2"]] = nm
        phis[nm] = round(abs(m["phi"]), 2)
    # A culled factor that absorbs items from several 99-item factors is named for all of them
    primary = np.abs(L).argmax(axis=1)
    for j in range(k):
        src = kept.factor[primary == j].value_counts()
        src = list(src[src >= 2].index)
        if len(src) > 1:
            names[j] = " + ".join(SHORT[s] for s in src)
    print(f"[2] parallel analysis k = {k}; similarity to the 99-item factors: {phis}; named {names}")

    desc_all, keep_w = dc.descriptors()
    desc = desc_all[keep_w].reset_index(drop=True).iloc[D.index.values].reset_index(drop=True)
    F, L, r_ideo = dc.orient(F, names, desc.ideo.values, wD, L)
    C = np.corrcoef(F.T)
    anchor = int(np.argmax((np.abs(C).sum(axis=1) - 1) / (k - 1)))
    resid = [j for j in range(k) if j != anchor and abs(C[anchor, j]) >= ANCHOR_R]
    X = F.copy()
    for j in resid:
        X[:, j] = em.wresid(F[:, j], F[:, anchor], wD)
    mu = np.average(X, axis=0, weights=wD)
    X = (X - mu) / np.sqrt(np.average((X - mu) ** 2, axis=0, weights=wD))
    print(f"[3] anchor {names[anchor]}; residualized on it: {[f'{names[j]} (r {C[anchor, j]:+.2f})' for j in resid]}")
    print("    largest |r| after residualizing:",
          round(float(np.abs(np.corrcoef(X.T) - np.eye(k)).max()), 2))

    jobs = [delayed(job)(X, K, kind, i) for K in KS for kind, rng in (("seed", SEEDS), ("boot", range(N_BOOT))) for i in rng]
    res = Parallel(n_jobs=11)(jobs)
    store = {}
    for K, kind, i, lab, bound in res:
        store.setdefault((K, kind), []).append((i, lab, bound))
    summary, clusters = [], []
    for K in KS:
        seeds = sorted(store[(K, "seed")], key=lambda t: t[0])
        S = pairwise([l for _, l, _ in seeds])
        n_sol, comp = connected_components(S >= 0.9, directed=False)
        sizes = np.bincount(comp)
        boots = [l for _, l, _ in sorted(store[(K, "boot")], key=lambda t: t[0])]
        B = pairwise(boots)
        med = int(np.argmax(B.sum(axis=1)))
        mj = np.array([best_jaccard(boots[med], boots[j]) for j in range(len(boots)) if j != med]).mean(axis=0)
        for c, lab in enumerate(np.unique(boots[med])):
            m = boots[med] == lab
            clusters.append({"K": K, "cluster": int(lab), "share": round(float(wD[m].sum() / wD.sum()), 3),
                             "harris": round(float(np.average(desc.vote.values[m] == "Harris", weights=wD[m])), 2),
                             "trump": round(float(np.average(desc.vote.values[m] == "Trump", weights=wD[m])), 2),
                             "mean_jaccard": round(float(mj[c]), 3)})
        summary.append({"K": K, "effective_clusters_median": int(np.median([len(np.unique(l)) for _, l, _ in seeds])),
                        "seed_ari_mean": round(float(S[~np.eye(len(S), dtype=bool)].mean()), 3),
                        "n_solutions": int(n_sol), "modal_solution_share": round(sizes.max() / len(seeds), 2),
                        "resample_ari_mean": round(float(B[~np.eye(len(B), dtype=bool)].mean()), 3),
                        "n_stable": int((mj >= 0.75).sum()), "n_dissolved": int((mj < 0.5).sum())})
    summ = pd.DataFrame(summary)
    summ.to_csv(OUT / "stability_summary.csv", index=False)
    pd.DataFrame(clusters).to_csv(OUT / "stability_clusters.csv", index=False)
    print("[4] stability by cap:\n", summ.to_string(index=False))

    ok = summ[summ.n_dissolved == 0]
    if ok.empty:
        print("    no cap is free of dissolving clusters; keeping the fewest dissolved")
        ok = summ[summ.n_dissolved == summ.n_dissolved.min()]
    K = int(ok.sort_values(["n_solutions", "modal_solution_share"], ascending=[True, False]).iloc[0].K)
    seeds = sorted(store[(K, "seed")], key=lambda t: t[0])
    S = pairwise([l for _, l, _ in seeds])
    _, comp = connected_components(S >= 0.9, directed=False)
    modal = np.bincount(comp).argmax()
    i, lab, bound = max((s for s, c in zip(seeds, comp) if c == modal), key=lambda t: t[2])
    cluster, _ = cl.remap_by_weighted_n(lab, wD, np.bincount(lab, minlength=K) / len(lab), thresh=0.0)
    print(f"    kept cap {K}: seed {i}, {cluster.max() + 1} clusters, modal solution reached by {int((comp == modal).sum())} of 20 seeds")

    base = S[np.ix_(comp == modal, comp == modal)]
    base = base[~np.eye(len(base), dtype=bool)].mean() if (comp == modal).sum() > 1 else 1.0
    seed_mean = S[~np.eye(len(S), dtype=bool)].mean()
    drop = Parallel(n_jobs=11)(delayed(lambda j, s: (j, s, dpgmm(K, s).fit(np.delete(X, j, 1)).predict(np.delete(X, j, 1))))(j, s)
                               for j in range(k) for s in range(42, 52))
    full_by_seed = {s: l for s, l, _ in seeds}
    dd = pd.DataFrame([{"factor": names[j], "seed": s, "ari": cl.ari(l, full_by_seed[s])} for j, s, l in drop])
    dd = dd.groupby("factor").ari.mean().round(3).sort_values().reset_index()
    dd.to_csv(OUT / "drop_one.csv", index=False)
    print(f"[5] drop one factor at cap {K} (mean ARI vs the full fit, seeds 42-51); seed-to-seed baseline {seed_mean:.2f}:\n",
          dd.to_string(index=False))

    pd.DataFrame({"caseid": desc.caseid.values, "cluster": cluster,
                  **{f"F_{nm}": F[:, j] for j, nm in enumerate(names)}}).to_csv(OUT / "independent_clusters.csv", index=False)
    pd.DataFrame({"factor": names, "r_ideology": r_ideo, "anchor": [j == anchor for j in range(k)],
                  "residualized": [j in resid for j in range(k)],
                  "top_items": ["; ".join(f"{cw.label[ids[t]][:70]} ({L[t, j]:+.2f})" for t in np.argsort(-np.abs(L[:, j]))[:3])
                                for j in range(k)]}).to_csv(OUT / "factors.csv", index=False)


if __name__ == "__main__":
    main()

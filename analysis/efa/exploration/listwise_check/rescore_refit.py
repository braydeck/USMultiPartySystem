"""Rescore everyone on the items they answered with re-estimated loadings, refit the parties, compare to production.

Data: as reestimate_loadings.py. Pairwise polychoric on the 49,432 respondents with a post weight
(outputs/polychoric_pairwise.csv), PAF k=5 + oblimin, factors aligned (order and sign) to
analysis/efa/efa_loadings_k5_final.csv. Production scores data/processed/efa_factor_scores.csv and parties
data/processed/typology_cluster_assignments.csv (same row order, n = 45,214).

Method, following the ANES available-item precedent (analysis/validation/DECISIONS.md 2026-11-02,
anes/independent_clustering.available_scores):
  1. Eligible: answered at least half of each factor's primary items (primary = largest |production loading|).
  2. Items standardized by their weighted mean and SD over everyone who answered them; Thomson regression
     scores per missing-data pattern, F = z_s R_ss^-1 S_s, with R the pairwise matrix and S = L Phi.
  3. FS_F4_resid, FS_F5_resid: weighted-OLS residuals on FS_F1 over all eligible respondents.
  4. Production DPGMM procedure (cap 9, seeds 42-61, n_init 5, max_iter 2000; solutions grouped at pairwise
     ARI >= 0.9; modal solution, best lower bound within it).
  5. Refit clusters matched one-to-one to production parties on weighted overlap among the 45,214; compared
     on ARI, Jaccard, kept share, weighted share, and factor centroids. Every production seed solution is
     also scored against production as the benchmark for ordinary seed-to-seed variation.
Writes outputs/rescore_scores.csv, outputs/rescore_parties.csv, outputs/rescore_profiles.csv,
outputs/rescore_labels.npz (cached; delete to refit), outputs/rescore_run.log (via tee).
--complete-only scores just the 45,214 production respondents (one missing-data pattern, so complete-case
standardization) with the same re-estimated loadings: it separates the loadings change from adding respondents.
Its outputs carry a _complete suffix.
"""
import os
import sys
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.optimize import linear_sum_assignment
from scipy.sparse.csgraph import connected_components
from sklearn.metrics import adjusted_rand_score as ari

import reestimate_loadings as rl
import refit_with_dropped as rw

ROOT, OUT, ITEMS, NAMES = rl.ROOT, rl.OUT, rl.ITEMS, rl.NAMES
pc = rw.pc
FS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]
CLUSTER_COLS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4_resid", "FS_F5_resid"]
MIN_SHARE_PER_FACTOR = 0.5
COMPLETE_ONLY = "--complete-only" in sys.argv
TAG = "_complete" if COMPLETE_ONLY else ""


def available_scores(X, w, R, L, Phi):
    ok = ~np.isnan(X)
    mu = np.array([np.average(X[ok[:, j], j], weights=w[ok[:, j]]) for j in range(X.shape[1])])
    sd = np.array([np.sqrt(np.average((X[ok[:, j], j] - mu[j]) ** 2, weights=w[ok[:, j]])) for j in range(X.shape[1])])
    Z = (X - mu) / sd
    S = L @ Phi
    F = np.zeros((len(X), L.shape[1]))
    pats, inv = np.unique(ok, axis=0, return_inverse=True)
    for p, m in enumerate(pats):
        rows = np.where(inv.ravel() == p)[0]
        F[rows] = Z[np.ix_(rows, np.where(m)[0])] @ np.linalg.solve(R[np.ix_(m, m)], S[m])
    return F, len(pats)


def main():
    X, w, post, complete, _ = rl.load()
    caseid = pd.read_stata(rl.eu.CES_PATH, columns=["caseid"], convert_categoricals=False).caseid.values
    L_final = pd.read_csv(ROOT / "analysis/efa/efa_loadings_k5_final.csv", index_col=0).loc[ITEMS, ["F1", "F2", "F3", "F4", "F5"]].values
    R = rl.em.regularize_corr(rl.poly(None, None, OUT / "polychoric_pairwise.csv"))
    L, Phi, phi = rl.align(L_final, *rl.fit(R))

    primary = np.abs(L_final).argmax(axis=1)
    answered = np.column_stack([(~np.isnan(X.values[:, primary == f])).mean(axis=1) for f in range(5)])
    elig = complete.copy() if COMPLETE_ONLY else post & (answered >= MIN_SHARE_PER_FACTOR).all(axis=1)
    print(f"eligible: {elig.sum():,} of {post.sum():,} post-weighted ({post.sum() - elig.sum():,} answer < half of some factor's items); "
          f"production complete cases {complete.sum():,}")

    Xe, we = X.values[elig].astype(float), w[elig]
    F, n_pat = available_scores(Xe, we, R, L, Phi)
    comp_e = complete[elig]
    fs = pd.read_csv(ROOT / "data/processed/efa_factor_scores.csv")
    typ = pd.read_csv(ROOT / "data/processed/typology_cluster_assignments.csv", usecols=["cluster", "commonpostweight"])
    assert np.array_equal(caseid[complete], fs.caseid.values), "production rows not reproduced"
    r = [np.corrcoef(F[comp_e, j], fs[FS[j]].values)[0, 1] for j in range(5)]
    assert min(r) > 0, "a rescored factor runs opposite to production"
    print(f"{n_pat} missing-data patterns; correlation with production scores on the {comp_e.sum():,} complete respondents:",
          dict(zip(NAMES, [round(float(x), 4) for x in r])))

    Fc = np.column_stack([F[:, :3]] + [rl.em.wresid(F[:, j], F[:, 0], we) for j in (3, 4)])
    pd.DataFrame({"caseid": caseid[elig], "complete": comp_e, "commonpostweight": we,
                  **{c: F[:, j] for j, c in enumerate(FS)}, "FS_F4_resid": Fc[:, 3], "FS_F5_resid": Fc[:, 4]}
                 ).to_csv(OUT / f"rescore_scores{TAG}.csv", index=False)

    lab_path = OUT / f"rescore_labels{TAG}.npz"
    if lab_path.exists():
        z = np.load(lab_path)
        res = list(zip(z["seeds"].tolist(), list(z["labels"]), z["bounds"].tolist()))
    else:
        res = sorted(Parallel(n_jobs=11)(delayed(rw.fit)(Fc, s) for s in rw.SEEDS))
        np.savez_compressed(lab_path, labels=np.stack([l for _, l, _ in res]), seeds=np.array([s for s, *_ in res]),
                            bounds=np.array([b for *_, b in res]))
    Ls = [l for _, l, _ in res]
    S = np.array([[ari(a, b) for b in Ls] for a in Ls])
    n_sol, comp = connected_components(S >= 0.9, directed=False)
    modal = np.bincount(comp).argmax()
    best = max((r_ for r_, c in zip(res, comp) if c == modal), key=lambda r_: r_[2])
    lab = best[1]
    print(f"\nRefit on {len(Fc):,}: {n_sol} solutions across 20 seeds, modal {np.bincount(comp).max()} of 20 (seed {best[0]}); "
          f"solution sizes {sorted(np.bincount(comp).tolist(), reverse=True)}")

    prod = typ.cluster.values
    wc = typ.commonpostweight.values
    lc = lab[comp_e]
    print(f"ARI, refit vs production on the {len(prod):,} complete respondents: {ari(prod, lc):.3f}")
    by_sol = pd.DataFrame({"solution": comp, "ari_vs_production": [ari(prod, l[comp_e]) for l in Ls]})
    print("ARI vs production by refit solution (seeds per solution, mean ARI):",
          by_sol.groupby("solution").ari_vs_production.agg(["size", "mean"]).round(3).to_dict("index"))
    prod_seed = np.load(OUT / "refit_labels.npz")["labels"][:, :len(prod)]
    print("benchmark, frozen-loadings refit seeds vs production (refit_with_dropped.py): ARI range "
          f"{min(ari(prod, l) for l in prod_seed):.2f}-{max(ari(prod, l) for l in prod_seed):.2f}")

    pids = sorted(np.unique(prod))
    ov = np.array([[wc[(prod == p) & (lc == k)].sum() for k in range(9)] for p in pids])
    ri, ci = linear_sum_assignment(-ov)
    to_party = {k: pc.CLUSTER_TO_PARTY[pids[i]] for i, k in zip(ri, ci)}
    new_party = np.array([to_party.get(k, "unmatched") for k in lab])
    party_c = typ.cluster.map(pc.CLUSTER_TO_PARTY).values
    np_c = new_party[comp_e]

    sd_prod = np.sqrt(rw.wmean((fs[FS].values - rw.wmean(fs[FS].values, wc)) ** 2, wc))
    sd_new = np.sqrt(rw.wmean((F - rw.wmean(F, we)) ** 2, we))
    rows, prof = [], []
    for p in pc.PARTIES:
        a, b = party_c == p, np_c == p
        cp = rw.wmean(fs[FS].values[a], wc[a]) / sd_prod
        cn = rw.wmean(F[new_party == p], we[new_party == p]) / sd_new
        rows.append({"party": p, "production_share": wc[a].sum() / wc.sum(), "refit_share": we[new_party == p].sum() / we.sum(),
                     "jaccard": wc[a & b].sum() / wc[a | b].sum(), "kept_in_party": wc[a & b].sum() / wc[a].sum(),
                     "centroid_shift_sd": float(np.linalg.norm(cn - cp))})
        for j, nm in enumerate(NAMES):
            prof.append({"party": p, "factor": nm, "production_sd": cp[j], "refit_sd": cn[j]})
    out = pd.DataFrame(rows)
    out["shift_pp"] = (out.refit_share - out.production_share) * 100
    out.to_csv(OUT / f"rescore_parties{TAG}.csv", index=False)
    prof = pd.DataFrame(prof)
    prof.to_csv(OUT / f"rescore_profiles{TAG}.csv", index=False)
    print("\n", out.round(3).to_string(index=False))
    print("\nFactor centers in SD units, production / refit:\n",
          prof.assign(v=prof.production_sd.round(2).astype(str) + " / " + prof.refit_sd.round(2).astype(str))
          .pivot(index="party", columns="factor", values="v").loc[list(pc.PARTIES), NAMES].to_string())
    ct = pd.crosstab(pd.Series(party_c, name="production"), pd.Series(np_c, name="refit"), values=wc, aggfunc="sum", normalize="index")
    print("\nProduction party (rows) across refit parties, complete respondents:\n", ct.round(3).to_string())


if __name__ == "__main__":
    main()

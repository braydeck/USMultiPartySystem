"""Parties on the Stage C clustering space from the 69-item pool: how many does it support, and how do they compare?

Data: CES 2024 Common Content, 49,432 post-weighted respondents (item_pool.load). Item set and factor identities: the
§3c Stage C fit of the 69-item pool at k = 5 (MAP's k; parallel analysis gave 8; lower-k tie rule), after cross-loader
removal: outputs/stage_c/pool69_loadings_k5.csv and pool69_factors.csv. Four factors pass the entry test (Security &
Order, Religious Traditionalism, Populist Conservatism, Trust); the contraception pair fails and is not a clustering input.
Checkbox items are out (Stage A as written). Reference parties: the rescored cap-8 typology (loading_draws.reference).

Procedure, production's on the new space:
  1. Loadings from the pairwise polychoric on all post-weighted respondents (item_pool cache), PAF k = 5 + oblimin,
     aligned by Tucker phi to the Stage C listwise solution.
  2. Available-item scoring (rescore_refit.available_scores); eligible = answered at least half of each passing
     factor's primary items.
  3. Anchor residualization as production: Religious Traditionalism and Populist Conservatism residualized on
     Security & Order (weighted OLS).
  4. Cap scan 2-10, DPGMM, the k_scan.py / fair_compare.py procedure: 20 seeds (42-61) grouped at ARI >= 0.9; 30
     resample fits predicted back onto everyone; medoid resample clusters scored by mean best Jaccard across the other 29
     (>= 0.75 stable, < 0.5 dissolved). Cap rule (§3c, unchanged): the largest cap with no dissolved cluster.
  5. At the kept cap and at cap 8: the modal seed solution (best lower bound) against the reference eight parties
     (weighted one-to-one overlap: kept share, Jaccard, ARI), with factor centroids.
Writes outputs/four_dim/{scores.csv, summary.csv, clusters.csv, labels.npz, compare_cap<K>.csv}; log via tee.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.sparse.csgraph import connected_components
from sklearn.metrics import adjusted_rand_score as ari

import item_pool as ip
import loading_draws as ld
import reestimate_loadings as rl
import rescore_refit as rr

sys.path.insert(0, str(rl.ROOT / "analysis/efa/exploration/k_stability"))
import fair_compare as fc  # noqa: E402

em = rl.em
OUT = rl.OUT / "four_dim"
SC = rl.OUT / "stage_c"
CAPS = range(2, 11)
NAMES = {"Security & Order": "SO", "Religious Traditionalism": "RT", "Populist Conservatism": "PC", "Institutional Distrust": "TR"}


def fit_space():
    """Items, aligned pairwise loadings and the passing-factor names of the Stage C k = 5 solution."""
    ld_k5 = pd.read_csv(SC / "pool69_loadings_k5.csv", index_col=0)
    items = list(ld_k5.index)
    fn = [c for c in ld_k5.columns if c.startswith("k5_F")]
    f = pd.read_csv(SC / "pool69_factors.csv")
    f = f[f.fit == "k5"].reset_index(drop=True)
    names = {}
    for j, row in f.iterrows():
        if row.passes:
            names[j] = NAMES[row["name"].split(" (")[0]]
    X, w, pid, caseid = ip.load()
    Rpw = ip.poly_all(X, w)
    R = em.regularize_corr(Rpw.loc[items, items].values.copy())
    L_un, _, _ = em.paf(R, len(fn))
    L, Phi = em.oblimin(L_un)
    L, Phi, phi = rl.align(ld_k5[fn].values, L, Phi)
    print(f"{len(items)} items; pairwise vs Stage C listwise loadings, Tucker phi per factor: {np.round(phi, 3).tolist()}")
    return items, L, Phi, R, names, X, w, caseid


def score(items, L, Phi, R, names, X, w, caseid):
    keep = sorted(names)
    primary = np.abs(L).argmax(axis=1)
    Xv = X[items].values.astype(float)
    answered = np.column_stack([(~np.isnan(Xv[:, primary == j])).mean(axis=1) for j in keep])
    elig = (answered >= rr.MIN_SHARE_PER_FACTOR).all(axis=1)
    F, n_pat = rr.available_scores(Xv[elig], w[elig], R, L, Phi)
    we = w[elig]
    S = pd.DataFrame({names[j]: F[:, j] for j in keep})
    for c in ("RT", "PC"):
        S[c + "_resid"] = em.wresid(S[c].values, S["SO"].values, we)
    S.insert(0, "caseid", caseid[elig])
    S.insert(1, "commonpostweight", we)
    return S, elig, n_pat


def space():
    items, L, Phi, R, names, X, w, caseid = fit_space()
    S, elig, n_pat = score(items, L, Phi, R, names, X, w, caseid)
    print(f"eligible {elig.sum():,} of {len(X):,} ({n_pat} missing-data patterns); clustering columns SO, TR, RT_resid, PC_resid")
    return S


def summarize(X, w, party, seeds, boots, K, cols):
    S = fc.pairwise_ari([l for _, l, _ in seeds])
    n_sol, comp = connected_components(S >= 0.9, directed=False)
    sizes = np.bincount(comp)
    B = fc.pairwise_ari(boots)
    off = B[~np.eye(len(B), dtype=bool)]
    med = int(np.argmax((B.sum(axis=1) - 1) / (len(B) - 1)))
    mj = np.array([fc.best_jaccard(boots[med], boots[j]) for j in range(len(boots)) if j != med]).mean(axis=0)
    clusters = []
    for c, cl in enumerate(np.unique(boots[med])):
        m = boots[med] == cl
        comp_ = pd.Series(w[m]).groupby(party[m]).sum().sort_values(ascending=False) / w[m].sum()
        means = (X[m] * w[m, None]).sum(0) / w[m].sum()
        clusters.append({"K": K, "share": round(w[m].sum() / w.sum() * 100, 1),
                         "composition": ", ".join(f"{p} {v * 100:.0f}" for p, v in comp_.items() if v >= 0.08),
                         "mean_jaccard": round(float(mj[c]), 3), **{col: round(float(v), 2) for col, v in zip(cols, means)}})
    return {"K": K, "n_solutions": int(n_sol), "modal_solution_share": round(sizes.max() / len(seeds), 2),
            "resample_ari_mean": round(float(off.mean()), 3), "n_clusters": len(np.unique(boots[med])),
            "n_stable": int((mj >= 0.75).sum()), "n_dissolved": int((mj < 0.5).sum())}, clusters


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    S = space()
    S.to_csv(OUT / "scores.csv", index=False)
    cols = ["SO", "TR", "RT_resid", "PC_resid"]
    X, w = S[cols].values, S.commonpostweight.values

    s_ref, ref, names = ld.reference()
    ref_by_case = pd.Series([names[k] for k in ref], index=s_ref.caseid.values)
    party = S.caseid.map(ref_by_case).fillna("none").values

    lab_path = OUT / "labels.npz"
    if lab_path.exists():
        z = np.load(lab_path)
        store = {k: z[k] for k in z.files}
        bounds = {k: z[k] for k in z.files if k.endswith("_bounds")}
    else:
        jobs = [delayed(fc.job)(X, "dpgmm", K, kind, i) for K in CAPS
                for kind, rng in (("seed", fc.SEEDS), ("boot", range(fc.N_BOOT))) for i in rng]
        res = Parallel(n_jobs=11, verbose=2)(jobs)
        acc = {}
        for _, K, kind, i, labels, bound in res:
            acc.setdefault((K, kind), []).append((i, labels, bound))
        store = {}
        for (K, kind), v in acc.items():
            v = sorted(v, key=lambda t: t[0])
            store[f"{K}_{kind}"] = np.stack([l for _, l, _ in v])
            store[f"{K}_{kind}_bounds"] = np.array([b for *_, b in v])
        np.savez_compressed(lab_path, **store)

    summary, clusters = [], []
    for K in CAPS:
        seeds = list(zip(fc.SEEDS, store[f"{K}_seed"], store[f"{K}_seed_bounds"]))
        s, c = summarize(X, w, party, seeds, list(store[f"{K}_boot"]), K, cols)
        summary.append(s)
        clusters += c
    summ = pd.DataFrame(summary)
    summ.to_csv(OUT / "summary.csv", index=False)
    pd.DataFrame(clusters).to_csv(OUT / "clusters.csv", index=False)
    kept = int(summ[summ.n_dissolved == 0].K.max())
    print("\nCap scan on the four-dimension space:\n", summ.to_string(index=False))
    print(f"\nCap rule (largest cap with no dissolved cluster): {kept}")

    known = party != "none"
    for K in sorted({kept, 8}):
        seeds = list(zip(fc.SEEDS, store[f"{K}_seed"], store[f"{K}_seed_bounds"]))
        lab, n_sol, share = ld.modal_solution(seeds)
        rows = pd.DataFrame(ld.match(np.array([{v: k for k, v in names.items()}[p] for p in party[known]]),
                                     lab[known], w[known], names)).set_index("party")
        cent = []
        for cl in np.unique(lab):
            m = lab == cl
            comp_ = pd.Series(w[m & known]).groupby(party[m & known]).sum().sort_values(ascending=False) / w[m & known].sum()
            cent.append({"cluster": int(cl), "share": round(w[m].sum() / w.sum() * 100, 1),
                         "composition": ", ".join(f"{p} {v * 100:.0f}" for p, v in comp_.items() if v >= 0.08),
                         **{c_: round(float(np.average(X[m, j], weights=w[m])), 2) for j, c_ in enumerate(cols)}})
        cent = pd.DataFrame(cent).sort_values("share", ascending=False)
        cent.to_csv(OUT / f"compare_cap{K}.csv", index=False)
        print(f"\ncap {K}: {n_sol} seed solutions, modal share {share:.2f}; ARI vs the reference eight parties "
              f"{ari(party[known], lab[known]):.3f}")
        print("reference parties' kept share / Jaccard:\n", rows.round(3).to_string())
        print("clusters (composition = reference party):\n", cent.to_string(index=False))


if __name__ == "__main__":
    main()

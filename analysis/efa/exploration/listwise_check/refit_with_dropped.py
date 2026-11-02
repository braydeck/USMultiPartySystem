"""Do the listwise-dropped CES respondents differ on the factors, and does adding them change the parties themselves?

Data: as available_scoring.py (frozen production loadings, standardization and residual lines; the 4,218
dropped respondents scored on the items they answered). Parties from data/processed/typology_cluster_assignments.csv.

1. Factor profile: weighted mean of each factor among the dropped minus among complete respondents, in
   complete-case SD units, overall and within each party. 1,000-draw bootstrap of the dropped group (seed 42).
2. Refit: the production procedure on all 49,432 (DPGMM cap 9, seeds 42-61, n_init 5, max_iter 2000; seeds
   grouped into solutions at pairwise ARI >= 0.9; modal solution, best lower bound within it). Refit clusters
   are matched one-to-one to production parties on the complete rows, then compared on membership (ARI,
   Jaccard), share, and centroid.
Writes outputs/factor_gap.csv, outputs/refit_parties.csv, outputs/refit_labels.npz.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.optimize import linear_sum_assignment
from scipy.sparse.csgraph import connected_components
from sklearn.metrics import adjusted_rand_score as ari
from sklearn.mixture import BayesianGaussianMixture

import available_scoring as av

pc = av.pc
SEEDS = range(42, 62)
FACTORS = {"FS_F1": "Security & Order", "FS_F2": "Institutional Distrust", "FS_F3": "Government Distrust",
           "FS_F4": "Religious Traditionalism", "FS_F5": "Populist Conservatism"}


def wmean(x, w):
    return (x * w[:, None]).sum(0) / w.sum()


def factor_gap(Fc, wc, Fd, wd, party_c, party_d, rng):
    sd = np.sqrt(wmean((Fc - wmean(Fc, wc)) ** 2, wc))
    rows = []
    for group in ["All"] + list(pc.PARTIES):
        mc, md = (party_c == group, party_d == group) if group != "All" else (slice(None), slice(None))
        fc, w1, fd, w2 = Fc[mc], wc[mc], Fd[md], wd[md]
        gap = (wmean(fd, w2) - wmean(fc, w1)) / sd
        boot = np.array([(wmean(fd[i], w2[i]) - wmean(fc, w1)) / sd
                         for i in (rng.integers(0, len(fd), len(fd)) for _ in range(1000))])
        for j, f in enumerate(FACTORS):
            rows.append({"group": group, "n_dropped": len(fd), "factor": FACTORS[f], "complete_mean_sd": wmean(fc, w1)[j] / sd[j],
                         "gap_sd": gap[j], "lo": np.quantile(boot[:, j], 0.025), "hi": np.quantile(boot[:, j], 0.975),
                         "p_dropped_higher": float((boot[:, j] > 0).mean())})
    return pd.DataFrame(rows)


def fit(X, seed):
    m = BayesianGaussianMixture(n_components=9, covariance_type="full", weight_concentration_prior_type="dirichlet_process",
                                n_init=5, random_state=seed, max_iter=2000).fit(X)
    return seed, m.predict(X).astype(np.int8), float(m.lower_bound_)


def main():
    d = av.score()
    complete, dropped, w_all, fs, typ, wc, Fd, Xd_cl = (d[k] for k in
        ("complete", "dropped", "w_all", "fs", "typ", "wc", "Fd", "Xd_cl"))
    wd = w_all[dropped].values
    party_c = typ.cluster.map(pc.CLUSTER_TO_PARTY).values
    party_d = pd.read_csv(av.OUT / "dropped_respondents.csv").party.values

    gap = factor_gap(fs[av.FS].values, wc, Fd, wd, party_c, party_d, np.random.default_rng(42))
    gap.to_csv(av.OUT / "factor_gap.csv", index=False)
    print(gap[gap.group == "All"].round(3).to_string(index=False))
    wide = gap.pivot(index="group", columns="factor", values="gap_sd").loc[list(pc.PARTIES)]
    print("\nWithin-party gap (dropped minus complete, SD units):\n", wide.round(2).to_string())
    print("\nParty centroids, complete respondents (SD units):\n",
          gap[gap.group != "All"].pivot(index="group", columns="factor", values="complete_mean_sd").loc[list(pc.PARTIES)].round(2).to_string())

    X = np.vstack([fs[av.CLUSTER_COLS].values, Xd_cl])
    w = np.concatenate([wc, wd])
    nc = len(fs)
    res = sorted(Parallel(n_jobs=11)(delayed(fit)(X, s) for s in SEEDS))
    L = [l for _, l, _ in res]
    S = np.array([[ari(a, b) for b in L] for a in L])
    n_sol, comp = connected_components(S >= 0.9, directed=False)
    modal = np.bincount(comp).argmax()
    best = max((r for r, c in zip(res, comp) if c == modal), key=lambda r: r[2])
    lab = best[1]
    np.savez_compressed(av.OUT / "refit_labels.npz", labels=np.stack(L), seeds=np.array(list(SEEDS)), bounds=np.array([b for *_, b in res]))
    print(f"\nRefit on {len(X):,}: {n_sol} solutions across 20 seeds, modal {np.bincount(comp).max()} of 20 (seed {best[0]}); "
          f"seed ARI mean {S[~np.eye(20, dtype=bool)].mean():.3f}")

    prod = typ.cluster.values
    pids = sorted(np.unique(prod))
    ov = np.array([[w[:nc][(prod == p) & (lab[:nc] == k)].sum() for k in range(9)] for p in pids])
    r, c = linear_sum_assignment(-ov)
    to_party = {k: pc.CLUSTER_TO_PARTY[pids[i]] for i, k in zip(r, c)}
    refit_party = np.array([to_party.get(k, "unmatched") for k in lab])
    print(f"ARI, refit vs production on the {nc:,} complete respondents: {ari(prod, lab[:nc]):.3f}")
    fam_ari = [ari(prod, l[:nc]) for l in L]
    print("ARI vs production, each seed:", dict(zip(SEEDS, np.round(fam_ari, 2))))

    rows = []
    for p in pc.PARTIES:
        a, b = party_c == p, refit_party[:nc] == p
        cent_p = wmean(fs[av.CLUSTER_COLS].values[a], wc[a])
        cent_r = wmean(X[refit_party == p], w[refit_party == p]) if (refit_party == p).any() else np.full(5, np.nan)
        rows.append({"party": p, "production_share": wc[a].sum() / wc.sum(),
                     "refit_share": w[refit_party == p].sum() / w.sum(),
                     "jaccard": (wc[a & b].sum()) / wc[a | b].sum(),
                     "kept_in_party": wc[a & b].sum() / wc[a].sum(),
                     "centroid_shift": float(np.linalg.norm(cent_r - cent_p))})
    out = pd.DataFrame(rows)
    out.to_csv(av.OUT / "refit_parties.csv", index=False)
    print(out.round(3).to_string(index=False))
    ct = pd.crosstab(pd.Series(party_c, name="production"), pd.Series(refit_party[:nc], name="refit"),
                     values=wc, aggfunc="sum", normalize="index")
    print("\nProduction party (rows) across refit parties, complete respondents:\n", ct.round(3).to_string())


if __name__ == "__main__":
    main()

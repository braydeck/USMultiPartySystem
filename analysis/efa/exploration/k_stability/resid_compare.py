"""Is the nine-party typology's residualization the more stable choice? Raw vs residualized scores at cap 9.

Data: data/processed/efa_factor_scores.csv (rescored 2026-10, n = 45,214) and the production parties in
data/processed/typology_cluster_assignments.csv (same row order; asserted on the weights), codes from
pipeline/party_codes.py.
  resid = FS_F1, FS_F2, FS_F3, FS_F4_resid, FS_F5_resid (production clustering inputs)
  raw   = FS_F1 .. FS_F5

Why: a full-covariance mixture is indifferent to residualizing in principle, but each fit starts from
k-means, and on these scores the same seeds reach different partitions (ARI ~0.67). This asks which
partition the data return to more reliably.

Procedure, the fair_compare.py one restricted to production DPGMM settings at K = 9 (n_init 5,
max_iter 2000, unweighted): per input, 20 full-data seeds (42-61) and 30 resamples (rng 42 + b, with
replacement, each predicted back onto all respondents). Seed agreement = mean pairwise ARI; solutions
= groups of seeds agreeing at ARI >= 0.9. Per-cluster stability = mean best Jaccard of the medoid
resample's clusters across the other 29 (>= 0.75 stable, < 0.5 dissolved). Each medoid cluster is
labeled by its largest production party. The modal raw solution is cross-tabbed against production.

Writes outputs/resid/ (summary.csv, clusters.csv, raw_vs_production.csv). Rerunnable; seeds fixed.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.sparse.csgraph import connected_components
from sklearn.mixture import BayesianGaussianMixture

from fair_compare import best_jaccard, pairwise_ari

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "pipeline"))
import party_codes as pc  # noqa: E402

OUT = Path(__file__).parent / "outputs" / "resid"
INPUTS = {"resid": ["FS_F1", "FS_F2", "FS_F3", "FS_F4_resid", "FS_F5_resid"],
          "raw": ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]}
K, SEEDS, N_BOOT = 9, range(42, 62), 30


def job(X, name, kind, i):
    m = BayesianGaussianMixture(n_components=K, covariance_type="full",
                                weight_concentration_prior_type="dirichlet_process",
                                n_init=5, random_state=i if kind == "seed" else 1000 + i, max_iter=2000)
    if kind == "seed":
        m.fit(X)
    else:
        m.fit(X[np.random.default_rng(42 + i).integers(0, len(X), len(X))])
    return name, kind, i, m.predict(X).astype(np.int8), float(m.lower_bound_)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fs = pd.read_csv(ROOT / "data/processed/efa_factor_scores.csv")
    typ = pd.read_csv(ROOT / "data/processed/typology_cluster_assignments.csv", usecols=["cluster", "commonpostweight"])
    assert np.allclose(fs.commonpostweight.values, typ.commonpostweight.values), "row order differs"
    w = fs.commonpostweight.values
    party = typ.cluster.map(pc.CLUSTER_TO_PARTY).values

    jobs = [delayed(job)(fs[cols].values, name, kind, i) for name, cols in INPUTS.items()
            for kind, rng in (("seed", SEEDS), ("boot", range(N_BOOT))) for i in rng]
    res = Parallel(n_jobs=11, verbose=2)(jobs)
    store = {}
    for name, kind, i, labels, bound in res:
        store.setdefault((name, kind), []).append((i, labels, bound))

    summary, clusters, modal_labels = [], [], {}
    for name in INPUTS:
        seeds = sorted(store[(name, "seed")], key=lambda t: t[0])
        S = pairwise_ari([l for _, l, _ in seeds])
        n_sol, comp = connected_components(S >= 0.9, directed=False)
        modal = np.bincount(comp).argmax()
        modal_labels[name] = max((s for s, c in zip(seeds, comp) if c == modal), key=lambda t: t[2])[1]
        boots = [l for _, l, _ in sorted(store[(name, "boot")], key=lambda t: t[0])]
        B = pairwise_ari(boots)
        med = int(np.argmax(B.sum(axis=1)))
        mj = np.array([best_jaccard(boots[med], boots[j]) for j in range(len(boots)) if j != med]).mean(axis=0)
        for c, lab in enumerate(np.unique(boots[med])):
            m = boots[med] == lab
            comp_ = pd.Series(w[m]).groupby(party[m]).sum().sort_values(ascending=False) / w[m].sum()
            clusters.append({"input": name, "share": round(w[m].sum() / w.sum() * 100, 1),
                             "largest_party": comp_.index[0], "largest_party_pct": round(comp_.iloc[0] * 100),
                             "second": f"{comp_.index[1]} {comp_.iloc[1] * 100:.0f}" if len(comp_) > 1 else "",
                             "mean_jaccard": round(float(mj[c]), 3)})
        off = B[~np.eye(len(B), dtype=bool)]
        summary.append({"input": name, "seed_ari_mean": round(float(S[~np.eye(len(S), dtype=bool)].mean()), 3),
                        "n_solutions": int(n_sol), "modal_solution_share": round(np.bincount(comp).max() / len(seeds), 2),
                        "resample_ari_mean": round(float(off.mean()), 3), "resample_ari_q10": round(float(np.quantile(off, 0.1)), 3),
                        "n_stable": int((mj >= 0.75).sum()), "n_dissolved": int((mj < 0.5).sum())})
    s = pd.DataFrame(summary)
    s.to_csv(OUT / "summary.csv", index=False)
    c = pd.DataFrame(clusters).sort_values(["input", "share"], ascending=[True, False])
    c.to_csv(OUT / "clusters.csv", index=False)
    print(s.to_string(index=False))
    print(c.to_string(index=False))

    raw = modal_labels["raw"]
    ct = pd.crosstab(party, raw, values=w, aggfunc="sum", normalize="index").round(3)
    ct.to_csv(OUT / "raw_vs_production.csv")
    print("\nProduction party (rows) across the modal raw solution's clusters (share of each party's weight):")
    print(ct.to_string())


if __name__ == "__main__":
    main()

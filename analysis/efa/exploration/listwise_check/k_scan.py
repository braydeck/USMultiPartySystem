"""How many parties does the rescored CES support? The fair stability scan, rerun on the re-estimated scores.

Data: outputs/rescore_scores.csv (rescore_refit.py: pairwise loadings, available-item scores, n = 49,428).
Party labels for interpretation: data/processed/typology_cluster_assignments.csv mapped by pipeline/party_codes.py,
known only for the 45,214 complete respondents (joined by caseid through data/processed/efa_factor_scores.csv).

Procedure: analysis/efa/exploration/k_stability/fair_compare.py, DPGMM only (it beat finite GMM and k-means
at every cap there), caps 7-11. Per cap: 20 full-data seeds (42-61) grouped into solutions at ARI >= 0.9;
30 resample fits (rng 42 + b) predicted back onto everyone; the medoid resample fit's clusters scored by mean
best Jaccard across the other 29 (>= 0.75 stable, < 0.5 dissolved). Cap 7 is also run on the production
scores, since the earlier scan stopped at 8; production caps 8-11 come from k_stability/outputs/fair/.
Writes outputs/kscan/{summary,clusters}.csv and labels.npz; outputs/kscan_run.log via tee.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.sparse.csgraph import connected_components

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(HERE.parent / "k_stability"))
sys.path.insert(0, str(ROOT / "pipeline"))
import fair_compare as fc  # noqa: E402
import party_codes as pc  # noqa: E402

OUT = HERE / "outputs" / "kscan"
KS = (7, 8, 9, 10, 11)


def inputs():
    new = pd.read_csv(HERE / "outputs" / "rescore_scores.csv")
    fs = pd.read_csv(ROOT / "data/processed/efa_factor_scores.csv")
    typ = pd.read_csv(ROOT / "data/processed/typology_cluster_assignments.csv", usecols=["cluster"])
    prod_party = pd.Series(typ.cluster.map(pc.CLUSTER_TO_PARTY).values, index=fs.caseid.values)
    party_new = new.caseid.map(prod_party).fillna("dropped").values
    return {"rescored": (new[fc.COLS].values, new.commonpostweight.values, party_new),
            "production": (fs[fc.COLS].values, fs.commonpostweight.values, prod_party.values)}


def summarize(X, w, party, seeds, boots, data, K):
    S = fc.pairwise_ari([l for _, l, _ in seeds])
    n_sol, comp = connected_components(S >= 0.9, directed=False)
    sizes = np.bincount(comp)
    best = max(seeds, key=lambda t: t[2])
    B = fc.pairwise_ari(boots)
    off = B[~np.eye(len(B), dtype=bool)]
    med = int(np.argmax((B.sum(axis=1) - 1) / (len(B) - 1)))
    J = np.array([fc.best_jaccard(boots[med], boots[j]) for j in range(len(boots)) if j != med])
    mj = J.mean(axis=0)
    known = party != "dropped"
    clusters = []
    for c, cl in enumerate(np.unique(boots[med])):
        m = boots[med] == cl
        mk = m & known
        comp_ = pd.Series(w[mk]).groupby(party[mk]).sum().sort_values(ascending=False) / w[mk].sum()
        means = (X[m] * w[m, None]).sum(0) / w[m].sum()
        clusters.append({"data": data, "K": K, "share": round(w[m].sum() / w.sum() * 100, 1),
                         "composition": ", ".join(f"{p} {v * 100:.0f}" for p, v in comp_.items() if v >= 0.08),
                         "mean_jaccard": round(float(mj[c]), 3),
                         **{col: round(float(v), 2) for col, v in zip(fc.COLS, means)}})
    summ = {"data": data, "K": K, "seed_ari_mean": round(float(S[~np.eye(len(S), dtype=bool)].mean()), 3),
            "n_solutions": int(n_sol), "modal_solution_share": round(sizes.max() / len(seeds), 2),
            "best_fit_solution_share": round(sizes[comp[seeds.index(best)]] / len(seeds), 2),
            "resample_ari_mean": round(float(off.mean()), 3), "resample_ari_q10": round(float(np.quantile(off, 0.1)), 3),
            "n_stable": int((mj >= 0.75).sum()), "n_dissolved": int((mj < 0.5).sum())}
    return summ, clusters


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    data = inputs()
    plan = [("rescored", K) for K in KS] + [("production", 7)]
    jobs = [delayed(lambda d, *a: (d, fc.job(*a)))(d, data[d][0], "dpgmm", K, kind, i)
            for d, K in plan for kind, rng in (("seed", fc.SEEDS), ("boot", range(fc.N_BOOT))) for i in rng]
    res = Parallel(n_jobs=11, verbose=2)(jobs)
    store = {}
    for d, (_, K, kind, i, labels, bound) in res:
        store.setdefault((d, K, kind), []).append((i, labels, bound))
    np.savez_compressed(OUT / "labels.npz", **{f"{d}_{K}_{k}": np.stack([l for _, l, _ in sorted(v, key=lambda t: t[0])])
                                               for (d, K, k), v in store.items()})

    summary, clusters = [], []
    for d, K in plan:
        X, w, party = data[d]
        seeds = sorted(store[(d, K, "seed")], key=lambda t: t[0])
        boots = [l for _, l, _ in sorted(store[(d, K, "boot")], key=lambda t: t[0])]
        s, c = summarize(X, w, party, seeds, boots, d, K)
        summary.append(s)
        clusters += c
    prior = pd.read_csv(HERE.parent / "k_stability/outputs/fair/summary.csv")
    prior = prior[prior.method == "dpgmm"].drop(columns="method").assign(data="production")
    s = pd.concat([pd.DataFrame(summary), prior], ignore_index=True).sort_values(["data", "K"])
    s.to_csv(OUT / "summary.csv", index=False)
    cl = pd.DataFrame(clusters)
    cl.to_csv(OUT / "clusters.csv", index=False)
    print(s.to_string(index=False))
    print("\nRescored medoid clusters by cap (composition = production party among complete respondents):")
    for K in KS:
        print(f"\nK = {K}\n" + cl[(cl.data == "rescored") & (cl.K == K)].sort_values("share", ascending=False)
              .drop(columns=["data", "K"]).to_string(index=False))


if __name__ == "__main__":
    main()

"""Is ANES's four-segment ceiling a sample-size effect? Run the ANES cap rule on CES cut to ANES's size.

Data: data/processed/efa_factor_scores.csv (CES 2024, rescored 2026-10, n = 45,214), the production clustering
inputs FS_F1, FS_F2, FS_F3, FS_F4_resid, FS_F5_resid. ANES comparison: outputs/clustering/independent_available/
(n = 4,673, 10 factors, cap 4).

The sweep is the one independent_clustering.py runs on ANES: DPGMM caps 2-10, 20 full-data seeds (42-61) and 30
resample fits per cap, a cluster counts as dissolved when its mean best Jaccard across resamples is < 0.5, and the
kept cap is the largest with no dissolved cluster. Fits are unweighted, as in both production chains.

Arms: three independent CES subsamples at the ANES n (4,673), then one each at 2x and 4x that n, to see whether the
kept cap climbs with n toward the full-sample 9 (fair_compare.py). Subsamples drawn without replacement, rng 42 + r.

Writes outputs/clustering/n_check/{summary.csv, by_cap.csv, run.log}.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.sparse.csgraph import connected_components

import independent_clustering as ic
import matched_efa as me

ROOT = me.HERE.parents[2]
OUT = me.OUT / "clustering" / "n_check"
COLS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4_resid", "FS_F5_resid"]
N_ANES = 4673
ARMS = [("ANES n", N_ANES, 0), ("ANES n", N_ANES, 1), ("ANES n", N_ANES, 2), ("2x ANES n", 2 * N_ANES, 0),
        ("4x ANES n", 4 * N_ANES, 0)]


def sweep(X):
    jobs = [delayed(ic.job)(X, K, kind, i) for K in ic.KS for kind, rng in (("seed", ic.SEEDS), ("boot", range(ic.N_BOOT)))
            for i in rng]
    store = {}
    for K, kind, i, lab, _ in Parallel(n_jobs=11)(jobs):
        store.setdefault((K, kind), []).append((i, lab))
    rows = []
    for K in ic.KS:
        seeds = [l for _, l in sorted(store[(K, "seed")], key=lambda t: t[0])]
        S = ic.pairwise(seeds)
        n_sol, comp = connected_components(S >= 0.9, directed=False)
        boots = [l for _, l in sorted(store[(K, "boot")], key=lambda t: t[0])]
        B = ic.pairwise(boots)
        med = int(np.argmax(B.sum(axis=1)))
        mj = np.array([ic.best_jaccard(boots[med], boots[j]) for j in range(len(boots)) if j != med]).mean(axis=0)
        rows.append({"K": K, "effective_clusters_median": int(np.median([len(np.unique(l)) for l in seeds])),
                     "n_solutions": int(n_sol), "modal_solution_share": round(np.bincount(comp).max() / len(seeds), 2),
                     "resample_ari_mean": round(float(B[~np.eye(len(B), dtype=bool)].mean()), 3),
                     "n_stable": int((mj >= 0.75).sum()), "n_dissolved": int((mj < 0.5).sum())})
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ces = pd.read_csv(ROOT / "data" / "processed" / "efa_factor_scores.csv", usecols=COLS).dropna()
    print(f"CES n = {len(ces):,}", flush=True)
    summary, by_cap = [], []
    for arm, n, r in ARMS:
        idx = np.random.default_rng(42 + r).choice(len(ces), n, replace=False)
        s = sweep(ces.values[idx])
        ok = s[s.n_dissolved == 0]
        kept = int(ok.K.max()) if not ok.empty else None
        s.insert(0, "arm", f"{arm} #{r + 1}" if arm == "ANES n" else arm)
        s.insert(1, "n", n)
        by_cap.append(s)
        summary.append({"arm": s.arm.iloc[0], "n": n, "kept_cap": kept,
                        "resample_ari_at_kept": float(s.loc[s.K == kept, "resample_ari_mean"].iloc[0]) if kept else None})
        print(f"\n== {s.arm.iloc[0]} (n = {n:,}) kept cap {kept}\n{s.drop(columns=['arm', 'n']).to_string(index=False)}", flush=True)
    pd.concat(by_cap).to_csv(OUT / "by_cap.csv", index=False)
    pd.DataFrame(summary).to_csv(OUT / "summary.csv", index=False)
    print("\n", pd.DataFrame(summary).to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())

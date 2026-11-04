"""Does the best-fitting cap-9 solution dominate once more starting points are tried? (2026-11-04)

The cap scan (stage_c_v2.py) fit cap 9 from 20 seeds (42-61) and found 4 solutions; the most common (7 seeds) is not
the best-fitting (5 seeds). This adds seeds 62-141, for 100 in all, same model (fair_compare.job, DPGMM, n_init 5)
on the same clustering scores (outputs/stage_c_v2/scores.csv: RT, TR, SO, PC as clustered). Seed 42 is refit as a
reproducibility check against the stored labels.
Solutions are grouped at ARI >= 0.9 (loading_draws.modal_solution's rule). Per solution: seed count, best lower bound,
ARI vs the 20-seed most common and best-fitting cap-9 solutions, and vs the revised ten.
Writes outputs/cap9_seeds/{labels.npz, solutions.csv}.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.sparse.csgraph import connected_components
from sklearn.metrics import adjusted_rand_score as ari

import four_dim_space as fd
import loading_draws as ld
import reestimate_loadings as rl

fc = fd.fc
OUT = rl.OUT / "cap9_seeds"
V2 = rl.OUT / "stage_c_v2"
CAP, NEW = 9, range(62, 142)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    S = pd.read_csv(V2 / "scores.csv")
    X = S[["RT", "TR", "SO", "PC"]].values
    z = np.load(V2 / "labels.npz")
    old_L, old_B = z[f"{CAP}_seed"], z[f"{CAP}_seed_bounds"]
    path = OUT / "labels.npz"
    if path.exists():
        st = np.load(path)
        new_L, new_B, chk = st["labels"], st["bounds"], st["check"]
    else:
        res = Parallel(n_jobs=11, verbose=2)(delayed(fc.job)(X, "dpgmm", CAP, "seed", i) for i in [42, *NEW])
        res = sorted(res, key=lambda r: r[3])
        chk = res[0][4]
        new_L = np.stack([r[4] for r in res[1:]])
        new_B = np.array([r[5] for r in res[1:]])
        np.savez_compressed(path, labels=new_L, bounds=new_B, check=chk)
    print(f"seed 42 refit vs stored: ARI {ari(chk, old_L[0]):.4f}")

    L = np.concatenate([old_L, new_L])
    B = np.concatenate([old_B, new_B])
    seeds = np.array([*range(42, 62), *NEW])
    A = np.array([[ari(a, b) for b in L] for a in L])
    n, comp = connected_components(A >= 0.9, directed=False)
    # reference points from the 20-seed scan
    c20 = comp[:20]
    modal20 = np.bincount(c20).argmax()
    best20 = c20[old_B.argmax()]
    ten = ld.modal_solution(list(zip(range(42, 62), z["10_seed"], z["10_seed_bounds"])))[0]
    rows = []
    for c in np.argsort(-np.bincount(comp)):
        m = np.where(comp == c)[0]
        rep = m[B[m].argmax()]
        rows.append({"solution": len(rows) + 1, "seeds": len(m), "seeds_in_first_20": int((m < 20).sum()),
                     "best_bound": round(float(B[m].max()), 1), "mean_bound": round(float(B[m].mean()), 1),
                     "is_20seed_most_common": c == modal20, "is_20seed_best_fit": c == best20,
                     "ari_vs_ten": round(ari(L[rep], ten), 3)})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "solutions.csv", index=False)
    print(f"{len(L)} seeds, {n} solutions; best bound overall {B.max():.1f} (seed {seeds[B.argmax()]})\n", out.to_string(index=False))


if __name__ == "__main__":
    main()

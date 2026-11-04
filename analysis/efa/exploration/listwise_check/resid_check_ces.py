"""Does anchor residualization change the CES revised-rule clusters? (2026-11-04, prompted by the ANES finding that
it decides cap 4 vs 5 there.)

Residualizing RT and PC on SO is an affine map of the clustering columns with determinant 1 (the in-power adjustment
after it is linear and maps a constant to itself, so the composite stays affine). A full-covariance DPGMM with
sklearn's data-derived default priors is equivariant under such a map, so the two inputs should differ only through
the k-means initialization (Euclidean, not affine-invariant) and reg_covar. This script checks that and reruns the
cap scan on plain scores.

Data: CES 2024; the stage_c_v2.py space (41 items, k = 5, entering RT, TR, SO, PC), rescored with v2_draws.py's
procedure on the 49,431 eligible respondents, with and without the residualization step.
Fits: fair_compare.job (DPGMM, n_init 5), caps 5 and 10, 20 seeds (42-61) and 30 resample fits, as the cap scan.
Compared with the residualized labels in outputs/stage_c_v2/labels.npz.
Writes outputs/resid_check_ces/{labels.npz, summary.csv}.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import adjusted_rand_score as ari

import four_dim_space as fd
import item_pool as ip
import loading_draws as ld
import profile_v2 as pv
import reestimate_loadings as rl
import rescore_refit as rr
import stage_c_v2 as v2
import state_control as stc

em, fc = rl.em, fd.fc
OUT = rl.OUT / "resid_check_ces"
V2 = rl.OUT / "stage_c_v2"
CAPS = (5, 10)


def score(X, w, items, R, L, Phi, enter, sn, elig, strata, resid):
    F, _ = rr.available_scores(X[items].values.astype(float)[elig], w[elig], R, L, Phi)
    we = w[elig]
    S = pd.DataFrame({sn[j]: F[:, j] for j in enter})
    if resid:
        for c in ("RT", "PC"):
            S[c] = em.wresid(S[c].values, S["SO"].values, we)
    Xd = np.column_stack([np.ones(len(S))] + [(strata == g).astype(float) for g in ("nonpartisan", "opposed", "split")])
    sw = np.sqrt(we / we.mean())
    for c in S.columns:
        y = S[c].values
        beta = np.linalg.lstsq(Xd * sw[:, None], y * sw, rcond=None)[0]
        S[c] = y - Xd[:, 2:] @ beta[2:]
    return S


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    X, w, pid, caseid = ip.load()
    S0 = pd.read_csv(V2 / "scores.csv")
    cols = ["RT", "TR", "SO", "PC"]
    fac = pd.read_csv(V2 / "factors.csv")
    enter = [int(j) for j in fac.factor[fac.enters]]
    sn = v2.roles(dict(zip(fac.factor, fac.name)), enter)
    retained = list(pd.read_csv(V2 / "loadings.csv", index_col=0).index)
    L_lw = pd.read_csv(V2 / "loadings.csv", index_col=0)[[f"F{j}" for j in range(len(fac))]].values
    Rp = v2.reg(ip.poly_all(X, w).loc[retained, retained].values, retained)
    Lp, Pp = em.oblimin(em.paf(Rp.values.copy(), len(fac))[0])
    Lp, Pp, _ = rl.align(L_lw, Lp, Pp)
    elig = np.isin(caseid, S0.caseid.values)
    strata = stc.strata(caseid, pid)[0][elig]
    Sr = score(X, w, retained, Rp.values, Lp, Pp, enter, sn, elig, strata, True)
    Sp = score(X, w, retained, Rp.values, Lp, Pp, enter, sn, elig, strata, False)
    print("residualized rescoring vs stored, r:", [round(float(np.corrcoef(Sr[c], S0[c])[0, 1]), 4) for c in cols])
    print("plain vs residualized, r:", [round(float(np.corrcoef(Sr[c], Sp[c])[0, 1]), 3) for c in cols])
    # affine check: each residualized column from the four plain columns plus a constant
    A = np.column_stack([Sp[cols].values, np.ones(len(Sp))])
    r2 = [1 - np.var(Sr[c].values - A @ np.linalg.lstsq(A, Sr[c].values, rcond=None)[0]) / np.var(Sr[c].values) for c in cols]
    print("residualized columns as affine functions of plain columns, R2:", [round(float(x), 8) for x in r2])
    Xp = Sp[cols].values

    path = OUT / "labels.npz"
    if path.exists():
        st = dict(np.load(path))
    else:
        res = Parallel(n_jobs=11, verbose=2)(delayed(fc.job)(Xp, "dpgmm", K, kind, i) for K in CAPS
                                             for kind, rng in (("seed", fc.SEEDS), ("boot", range(fc.N_BOOT))) for i in rng)
        st = {}
        for K in CAPS:
            for kind in ("seed", "boot"):
                v = sorted([(i, l, b) for _, k, kd, i, l, b in res if k == K and kd == kind], key=lambda t: t[0])
                st[f"{K}_{kind}"] = np.stack([l for _, l, _ in v])
                st[f"{K}_{kind}_bounds"] = np.array([b for *_, b in v])
        np.savez_compressed(path, **st)

    z = np.load(V2 / "labels.npz")
    rows = []
    for K in CAPS:
        ref, rn, rs = ld.modal_solution(list(zip(range(42, 62), z[f"{K}_seed"], z[f"{K}_seed_bounds"])))
        lab, n_sol, share = ld.modal_solution(list(zip(range(42, 62), st[f"{K}_seed"], st[f"{K}_seed_bounds"])))
        jr = pv.jaccard_mean(ref, list(z[f"{K}_boot"]))
        jp = pv.jaccard_mean(lab, list(st[f"{K}_boot"]))
        # same-seed pairs landing on the same partition: lower bounds should agree if the model is equivariant
        same = [(a, b) for a, b, la, lb in zip(z[f"{K}_seed_bounds"], st[f"{K}_seed_bounds"], z[f"{K}_seed"], st[f"{K}_seed"]) if ari(la, lb) > 0.999]
        rows.append({"cap": K, "plain_vs_resid_ari": round(ari(ref, lab), 3),
                     "resid_n_solutions": rn, "resid_modal_share": rs, "plain_n_solutions": n_sol, "plain_modal_share": share,
                     "resid_unstable": int((jr < .75).sum()), "resid_dissolved": int((jr < .5).sum()),
                     "plain_unstable": int((jp < .75).sum()), "plain_dissolved": int((jp < .5).sum()),
                     "resid_best_bound": round(float(z[f"{K}_seed_bounds"].max()), 1), "plain_best_bound": round(float(st[f"{K}_seed_bounds"].max()), 1),
                     "same_partition_seed_pairs": len(same),
                     "max_bound_gap_same_partition": round(max((abs(a - b) for a, b in same), default=np.nan), 3)})
        print(f"cap {K}: plain jaccard {np.round(np.sort(jp), 2).tolist()}; residualized {np.round(np.sort(jr), 2).tolist()}")
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "summary.csv", index=False)
    print(out.T.to_string())


if __name__ == "__main__":
    main()

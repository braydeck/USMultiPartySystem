"""Do the revised-rule ten clusters survive redrawn factor estimates? The four_dim_draws.py test on the revised space.

Data: CES 2024 Common Content; the revised §3c space of stage_c_v2.py (41 retained items, k = 5, four entering
factors: RT, TR, SO, PC). Reference: the cap-10 modal seed solution in outputs/stage_c_v2/labels.npz, cluster names
from outputs/profile_v2/names.csv.
Draws: the 50 respondent bootstrap draws (seed 42) whose weighted pairwise polychorics stage_c_v2.py cached
(outputs/stage_c_v2/draw_poly.npz), restricted to the 41 items. Per draw: PAF k = 5 + oblimin aligned by Tucker phi
to the full-sample pairwise loadings; the same 49,431 eligible respondents scored on the items they answered with the
draw's matrix and loadings (available-item scoring); no residualization (dropped 2026-11-04); in-power adjustment re-estimated
(opposed and split contrasts removed, nonpartisan kept); cap-10 DPGMM, 20 seeds, modal solution. Draw clusters matched
one-to-one to the reference on weighted overlap; each reference cluster's kept share and Jaccard recorded.
Comparable to outputs/four_dim_draws/ (current ten) and outputs/production_draws/ (production nine, 14 draws).
Differences from those: draws resample all post-weighted respondents (pairwise matrices), not the listwise sample.
Writes outputs/v2_draws/{draws,parties,summary}.csv, draw_labels.npz (cache); log via tee.
"""
import os
import sys
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import adjusted_rand_score as ari

import item_pool as ip
import loading_draws as ld
import reestimate_loadings as rl
import rescore_refit as rr
import stage_c_v2 as v2
import state_control as stc

em = rl.em
CAP, N_DRAWS = (int(sys.argv[1]) if len(sys.argv) > 1 else 10), 50
# outputs/v2_draws/ holds the 2026-11-03 run on the ten with residualized scores; plain-score runs go to v2_draws_k{CAP}
OUT = rl.OUT / f"v2_draws_k{CAP}"
V2 = rl.OUT / "stage_c_v2"


def score(X, w, items, R, L, Phi, enter, sn, elig, strata):
    Xv = X[items].values.astype(float)[elig]
    we = w[elig]
    F, _ = rr.available_scores(Xv, we, R, L, Phi)
    S = pd.DataFrame({sn[j]: F[:, j] for j in enter})
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
    cols = [c for c in S0.columns if c not in ("caseid", "commonpostweight")]
    fac = pd.read_csv(V2 / "factors.csv")
    enter = [int(j) for j in fac.factor[fac.enters]]
    sn = v2.roles(dict(zip(fac.factor, fac.name)), enter)
    assert [sn[j] for j in enter] == cols, (sn, cols)
    retained = list(pd.read_csv(V2 / "loadings.csv", index_col=0).index)
    L_lw = pd.read_csv(V2 / "loadings.csv", index_col=0)[[f"F{j}" for j in range(len(fac))]].values
    Rpw = ip.poly_all(X, w)
    Rp = v2.reg(Rpw.loc[retained, retained].values, retained)
    Lp, Pp = em.oblimin(em.paf(Rp.values.copy(), len(fac))[0])
    Lp, Pp, _ = rl.align(L_lw, Lp, Pp)
    elig = np.isin(caseid, S0.caseid.values)
    assert np.array_equal(caseid[elig], S0.caseid.values)
    strata = stc.strata(caseid, pid)[0][elig]
    check = score(X, w, retained, Rp.values, Lp, Pp, enter, sn, elig, strata)
    print("full-sample rescoring vs stage_c_v2 scores, r per factor:",
          [round(float(np.corrcoef(check[c], S0[c])[0, 1]), 4) for c in cols], flush=True)

    z = np.load(V2 / "labels.npz")
    ref, n_sol, share = ld.modal_solution(list(zip(range(42, 62), z[f"{CAP}_seed"], z[f"{CAP}_seed_bounds"])))
    nm = pd.read_csv(rl.OUT / ("profile_v2" if CAP == 10 else f"profile_v2_k{CAP}") / "names.csv")
    rnames = dict(zip(nm[nm.cap == CAP].cluster, nm[nm.cap == CAP].name))
    we = S0.commonpostweight.values
    print(f"reference: {n_sol} seed solutions (modal {share:.2f}); " + ", ".join(f"{rnames[k]} {we[ref == k].sum() / we.sum() * 100:.1f}%" for k in np.unique(ref)), flush=True)

    store = np.load(V2 / "draw_poly.npz")
    b1 = [c for c in ip.POOL if c not in v2.SENTIMENT]
    lab_path = OUT / "draw_labels.npz"
    cached = dict(np.load(lab_path)) if lab_path.exists() else {}
    draws, parties = [], []
    for b in range(N_DRAWS):
        key = f"d{b}"
        if key not in cached:
            full = pd.DataFrame(store[key], index=_b1(X, w, b1), columns=_b1(X, w, b1))
            Rb = v2.reg(full.loc[retained, retained].values, retained)
            Lb, Pb = em.oblimin(em.paf(Rb.values.copy(), len(fac))[0])
            Lb, Pb, phi = rl.align(Lp, Lb, Pb)
            Sb = score(X, w, retained, Rb.values, Lb, Pb, enter, sn, elig, strata)
            res = sorted(Parallel(n_jobs=11)(delayed(ld.fit)(Sb[cols].values, s, CAP) for s in ld.SEEDS))
            lab, ns, sh = ld.modal_solution(res)
            cached.update({key: lab, f"{key}_nsol": ns, f"{key}_share": sh, f"{key}_phi": phi})
            np.savez_compressed(lab_path, **cached)
        lab, ns, sh, phi = cached[key], int(cached[f"{key}_nsol"]), float(cached[f"{key}_share"]), cached[f"{key}_phi"]
        rows = ld.match(ref, lab, we, rnames)
        parties += [{"draw": b, **r} for r in rows]
        draws.append({"draw": b, "ari_vs_reference": ari(ref, lab), "n_solutions": ns, "modal_share": sh,
                      "min_phi": float(np.min(phi)), "min_kept": min(r["kept"] for r in rows)})
        print(f"draw {b + 1}/{N_DRAWS}: ARI {draws[-1]['ari_vs_reference']:.3f}, {ns} solutions, modal {sh:.2f}, "
              f"worst factor phi {np.min(phi):.3f}, worst kept {draws[-1]['min_kept']:.2f}", flush=True)

    dr, pa = pd.DataFrame(draws), pd.DataFrame(parties)
    dr.to_csv(OUT / "draws.csv", index=False)
    pa.to_csv(OUT / "parties.csv", index=False)
    summ = pa.groupby("party").agg(kept_median=("kept", "median"), kept_q05=("kept", lambda x: x.quantile(0.05)),
                                   jaccard_median=("jaccard", "median"),
                                   share_draws_kept_below_half=("kept", lambda x: (x < 0.5).mean()))
    summ["reference_share"] = pd.Series({rnames[k]: we[ref == k].sum() / we.sum() for k in np.unique(ref)})
    summ = summ.sort_values("reference_share", ascending=False)
    summ.to_csv(OUT / "summary.csv")
    for name, p in [("current ten", "four_dim_draws"), ("production nine", "production_draws"), ("eight-party rebuild", "loading_draws")]:
        f = rl.OUT / p / "draws.csv"
        if f.exists():
            d = pd.read_csv(f)
            print(f"{name}: {len(d)} draws, ARI median {d.ari_vs_reference.median():.3f}; draws with a cluster under half {(d.min_kept < 0.5).mean():.2f}")
    print(f"revised ten: {len(dr)} draws, ARI median {dr.ari_vs_reference.median():.3f}, 5th pct {dr.ari_vs_reference.quantile(0.05):.3f}; "
          f"draws with a cluster under half {(dr.min_kept < 0.5).mean():.2f}")
    print("\nPer reference cluster across draws:\n", summ.round(3).to_string())


_B1 = None


def _b1(X, w, b1):
    """The items stage_c_v2 cached per draw: the pool after the missing / modal screen."""
    global _B1
    if _B1 is None:
        _B1 = v2.basic_screen(X, w, b1, [])
    return _B1


if __name__ == "__main__":
    main()

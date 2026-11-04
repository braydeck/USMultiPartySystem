"""Sensitivity check (2026-11-03, after results were seen): how much of the ten-cluster typology rests on distrust of
the respondent's own state government? Not a rule change; disclosed in DECISIONS.md.

Data: CES 2024 Common Content; as four_dim_space.py. Reference: the cap-10 modal seed solution of outputs/four_dim/.
Arms, each clustered at cap 10 with the four_dim_space procedure (20 seeds 42-61 modal solution; 30 resample fits):
  national  Stage C on the 69-item pool without CC24_424 (state-government trust) and CC24_421_2 (state election
            fair): outputs/stage_c/pool69nat_{loadings_k5,factors}.csv (MAP's k = 5, the lower-k rule). Loadings from
            the pairwise polychoric, aligned to the listwise fit; available-item scores; Religious Traditionalism and
            Populist Conservatism residualized on Security & Order; passing factors only.
  governor  the reference space with the distrust score adjusted for alignment with the governor's party: weighted
            OLS of distrust on pid3 (Democrat, Republican, other) plus two indicators, respondent's party holds the
            governorship / the other major party does (CurrentGovParty); only the two alignment terms are removed,
            so party ID's own association with distrust stays in the score.
Outputs per arm: ARI vs the reference, each reference cluster's kept share and Jaccard (one-to-one weighted
overlap), resample stability, and the state concentration of the cluster matched to C9.
Writes outputs/trust_sensitivity/{summary.csv, clusters.csv, labels.npz}.
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
import reestimate_loadings as rl
import rescore_refit as rr

em, fc = rl.em, fd.fc
OUT = rl.OUT / "trust_sensitivity"
SC = rl.OUT / "stage_c"
CAP = 10


def national_space():
    ld5 = pd.read_csv(SC / "pool69nat_loadings_k5.csv", index_col=0)
    items = list(ld5.index)
    fn = [c for c in ld5.columns if c.startswith("k5_F")]
    f = pd.read_csv(SC / "pool69nat_factors.csv")
    f = f[f.fit == "k5"].reset_index(drop=True)
    names = {j: fd.NAMES[r["name"].split(" (")[0]] for j, r in f.iterrows() if r.passes}
    X, w, _, caseid = ip.load()
    R = em.regularize_corr(ip.poly_all(X, w).loc[items, items].values.copy())
    L, Phi = em.oblimin(em.paf(R, len(fn))[0])
    L, Phi, phi = rl.align(ld5[fn].values, L, Phi)
    print(f"national: {len(items)} items, passing factors {sorted(names.values())}, phi vs listwise {np.round(phi, 3).tolist()}")
    keep = sorted(names)
    primary = np.abs(L).argmax(axis=1)
    Xv = X[items].values.astype(float)
    elig = (np.column_stack([(~np.isnan(Xv[:, primary == j])).mean(axis=1) for j in keep]) >= rr.MIN_SHARE_PER_FACTOR).all(axis=1)
    F, _ = rr.available_scores(Xv[elig], w[elig], R, L, Phi)
    S = pd.DataFrame({names[j]: F[:, j] for j in keep})
    for c in ("RT", "PC"):
        S[c + "_resid"] = em.wresid(S[c].values, S["SO"].values, w[elig])
    S.insert(0, "caseid", caseid[elig])
    S.insert(1, "commonpostweight", w[elig])
    return S, ["SO", "RT_resid", "PC_resid"]


def governor_space():
    S = pd.read_csv(fd.OUT / "scores.csv")
    m = pd.read_stata(rl.eu.CES_PATH, columns=["caseid", "pid3", "CurrentGovParty"], convert_categoricals=True).set_index("caseid").loc[S.caseid]
    pid, gov = m.pid3.astype(str).values, m.CurrentGovParty.astype(str).values
    dem, rep = pid == "Democrat", pid == "Republican"
    aligned = (dem & (gov == "Democratic")) | (rep & (gov == "Republican"))
    opposed = (dem & (gov == "Republican")) | (rep & (gov == "Democratic"))
    Xd = np.column_stack([np.ones(len(S)), dem, rep, aligned, opposed]).astype(float)
    w = S.commonpostweight.values
    sw = np.sqrt(w / w.mean())
    beta = np.linalg.lstsq(Xd * sw[:, None], S.TR.values * sw, rcond=None)[0]
    print(f"governor: distrust on pid3 + alignment, betas aligned {beta[3]:+.3f}, opposed {beta[4]:+.3f} "
          f"(distrust SD {np.sqrt(np.cov(S.TR, aweights=w)):.3f})")
    S["TR_gov"] = S.TR.values - Xd[:, 3:] @ beta[3:]
    return S, ["SO", "TR_gov", "RT_resid", "PC_resid"]


def state_index(mask, st, w):
    a = pd.Series(w * mask).groupby(st).sum()
    b = pd.Series(w).groupby(st).sum()
    return 0.5 * (a / a.sum() - b / b.sum()).abs().sum()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    S0 = pd.read_csv(fd.OUT / "scores.csv")
    z = np.load(fd.OUT / "labels.npz")
    ref = pd.Series(ld.modal_solution(list(zip(range(42, 62), z[f"{CAP}_seed"], z[f"{CAP}_seed_bounds"])))[0], index=S0.caseid.values)
    geo = pd.read_stata(rl.eu.CES_PATH, columns=["caseid", "inputstate", "CC24_410"], convert_categoricals=True).set_index("caseid")
    lab_path = OUT / "labels.npz"
    store = dict(np.load(lab_path)) if lab_path.exists() else {}
    summary, clusters = [], []
    for arm, build in [("national", national_space), ("governor", governor_space)]:
        S, cols = build()
        X = S[cols].values
        if f"{arm}_seed" not in store:
            jobs = [delayed(fc.job)(X, "dpgmm", CAP, kind, i) for kind, rng in (("seed", fc.SEEDS), ("boot", range(fc.N_BOOT))) for i in rng]
            res = Parallel(n_jobs=11)(jobs)
            for kind in ("seed", "boot"):
                v = sorted([(i, l, b) for _, _, k, i, l, b in res if k == kind], key=lambda t: t[0])
                store[f"{arm}_{kind}"] = np.stack([l for _, l, _ in v])
                store[f"{arm}_{kind}_bounds"] = np.array([b for *_, b in v])
            store[f"{arm}_caseid"] = S.caseid.values
            np.savez_compressed(lab_path, **store)
        seeds = list(zip(fc.SEEDS, store[f"{arm}_seed"], store[f"{arm}_seed_bounds"]))
        lab, n_sol, share = ld.modal_solution(seeds)
        s, _ = fd.summarize(X, S.commonpostweight.values, np.array(["x"] * len(S)), seeds, list(store[f"{arm}_boot"]), CAP, cols)
        common = np.intersect1d(S.caseid.values, ref.index.values)
        r_ = ref.loc[common].values
        l_ = pd.Series(lab, index=S.caseid.values).loc[common].values
        w_ = S.set_index("caseid").commonpostweight.loc[common].values
        rows = pd.DataFrame(ld.match(r_, l_, w_, {k: f"C{k}" for k in np.unique(r_)})).set_index("party")
        # the arm's cluster that best matches C9, and its geography
        ov = pd.Series(w_[r_ == 9]).groupby(l_[r_ == 9]).sum()
        c9 = ov.idxmax()
        st = geo.inputstate.astype(str).loc[common].values
        idx = state_index(l_ == c9, st, w_)
        idx_ref = state_index(r_ == 9, st, w_)
        summary.append({"arm": arm, "n": len(S), "dims": " ".join(cols), "ari_vs_reference": round(ari(r_, l_), 3),
                        "n_solutions": n_sol, "modal_share": round(share, 2), "resample_ari": s["resample_ari_mean"],
                        "n_stable": s["n_stable"], "n_dissolved": s["n_dissolved"],
                        "c9_best_match_share": round(float(w_[l_ == c9].sum() / w_.sum() * 100), 1),
                        "c9_state_index": round(idx, 3), "c9_state_index_reference": round(idx_ref, 3)})
        for p, r in rows.iterrows():
            clusters.append({"arm": arm, "party": p, "kept": round(r.kept, 3), "jaccard": round(r.jaccard, 3)})
        print(f"\n== {arm}: ARI vs reference {summary[-1]['ari_vs_reference']}, {n_sol} seed solutions (modal {share:.2f}), "
              f"resample ARI {s['resample_ari_mean']}, stable {s['n_stable']}, dissolved {s['n_dissolved']}")
        print(rows.round(3).T.to_string())
        print(f"C9's best match: {summary[-1]['c9_best_match_share']}% of respondents; state index {idx:.3f} (reference C9 {idx_ref:.3f})")
    pd.DataFrame(summary).to_csv(OUT / "summary.csv", index=False)
    pd.DataFrame(clusters).to_csv(OUT / "clusters.csv", index=False)


if __name__ == "__main__":
    main()

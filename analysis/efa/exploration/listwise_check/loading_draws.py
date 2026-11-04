"""How much do the cap-8 parties move when only the factor loadings are redrawn? The noise floor for item-pool tests.

Data: as reestimate_loadings.py (CES 2024, 49,432 post-weighted; 45,214 complete on the 24 items).
Reference: the rescored cap-8 typology, refit here from outputs/rescore_scores.csv (rescore_refit.py) with the
production DPGMM procedure at cap 8 (seeds 42-61, n_init 5, max_iter 2000; solutions grouped at ARI >= 0.9;
modal solution, best lower bound within it). Its clusters are named by one-to-one weighted overlap with the
production parties among the 45,214 (pipeline/party_codes.py), as the rebuild will name them.

Draws: the 50 respondent bootstrap draws of the listwise sample behind outputs/loadings_bootstrap.csv, rebuilt
with the same seed-42 generator sequence (each draw's Tucker phi is checked against that file). Per draw: PAF k=5 +
oblimin on the draw's polychoric, aligned to production's factor order and sign; every eligible respondent
(the 49,428 of rescore_refit.py) scored on the items they answered with the draw's matrix and loadings; F4/F5
residualized on F1; the same cap-8 DPGMM procedure. Draw clusters are matched one-to-one to reference parties
on weighted overlap; each reference party's kept share (weighted share of its members in the matched cluster)
and Jaccard are recorded.
Writes outputs/loading_draws/{reference_labels.npz, draws.csv, parties.csv, summary.csv}; per-draw labels cached in
outputs/loading_draws/draw_labels.npz (delete to refit). Log: outputs/loading_draws_run.log via tee.
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

import reestimate_loadings as rl
import rescore_refit as rr

OUT = rl.OUT / "loading_draws"
CAP = 8
SEEDS = range(42, 62)
ITEMS = rl.ITEMS


def fit(X, seed, cap=CAP):
    m = BayesianGaussianMixture(n_components=cap, covariance_type="full", weight_concentration_prior_type="dirichlet_process",
                                n_init=5, random_state=seed, max_iter=2000).fit(X)
    return seed, m.predict(X).astype(np.int8), float(m.lower_bound_)


def modal_solution(res):
    """res: list of (seed, labels, bound). Returns chosen labels, n solutions, modal share."""
    Ls = [l for _, l, _ in res]
    S = np.array([[ari(a, b) for b in Ls] for a in Ls])
    n_sol, comp = connected_components(S >= 0.9, directed=False)
    modal = np.bincount(comp).argmax()
    best = max((r for r, c in zip(res, comp) if c == modal), key=lambda r: r[2])
    return best[1], int(n_sol), np.bincount(comp).max() / len(res)


def cluster(F, w, seeds=SEEDS, n_jobs=11):
    """F: raw factor scores (F1..F5). Residualizes F4/F5 on F1 and runs the cap-8 procedure."""
    Fc = np.column_stack([F[:, :3]] + [rl.em.wresid(F[:, j], F[:, 0], w) for j in (3, 4)])
    res = sorted(Parallel(n_jobs=n_jobs)(delayed(fit)(Fc, s) for s in seeds))
    return modal_solution(res)


def match(ref, lab, w, names):
    """One-to-one match of lab's clusters to ref's (weighted overlap). Returns per-reference-party rows."""
    rk, lk = np.unique(ref), np.unique(lab)
    ov = np.array([[w[(ref == a) & (lab == b)].sum() for b in lk] for a in rk])
    ri, ci = linear_sum_assignment(-ov)
    pairs = dict(zip(rk[ri], lk[ci]))
    rows = []
    for a in rk:
        A = ref == a
        if a in pairs:
            B = lab == pairs[a]
            kept, jac = w[A & B].sum() / w[A].sum(), w[A & B].sum() / w[A | B].sum()
        else:
            kept = jac = 0.0
        rows.append({"party": names[a], "kept": kept, "jaccard": jac})
    return rows


def reference():
    OUT.mkdir(parents=True, exist_ok=True)
    s = pd.read_csv(rl.OUT / "rescore_scores.csv")
    F, w = s[rr.FS].values, s.commonpostweight.values
    path = OUT / "reference_labels.npz"
    if path.exists():
        lab = np.load(path)["labels"]
    else:
        lab, n_sol, share = cluster(F, w)
        print(f"reference cap {CAP}: {n_sol} solutions, modal share {share:.2f}")
        np.savez_compressed(path, labels=lab, caseid=s.caseid.values)
    fs = pd.read_csv(rl.ROOT / "data/processed/efa_factor_scores.csv", usecols=["caseid"])
    typ = pd.read_csv(rl.ROOT / "data/processed/typology_cluster_assignments.csv", usecols=["cluster"])
    prod = s.caseid.map(pd.Series(typ.cluster.values, index=fs.caseid.values))
    known = prod.notna().values
    pids = sorted(prod[known].unique().astype(int))
    ov = np.array([[w[known & (prod.values == p) & (lab == k)].sum() for k in range(CAP)] for p in pids])
    ri, ci = linear_sum_assignment(-ov)
    names = {k: rr.pc.CLUSTER_TO_PARTY[pids[i]] for i, k in zip(ri, ci)}
    for k in np.unique(lab):
        names.setdefault(k, f"new{k}")
    return s, lab, names


def main():
    s, ref, names = reference()
    shares = {names[k]: s.commonpostweight.values[ref == k].sum() / s.commonpostweight.sum() for k in np.unique(ref)}
    print("reference parties (weighted share):", {k: round(v, 3) for k, v in sorted(shares.items(), key=lambda t: -t[1])})

    X, w, post, complete, _ = rl.load()
    caseid = pd.read_stata(rl.eu.CES_PATH, columns=["caseid"], convert_categoricals=False).caseid.values
    elig = np.isin(caseid, s.caseid.values)
    assert np.array_equal(caseid[elig], s.caseid.values)
    Xe, we = X.values[elig].astype(float), w[elig]
    L_final = pd.read_csv(rl.ROOT / "analysis/efa/efa_loadings_k5_final.csv", index_col=0).loc[ITEMS, ["F1", "F2", "F3", "F4", "F5"]].values
    R_lw = rl.poly(None, None, rl.OUT / "polychoric_listwise.csv")
    La_lw, _, _ = rl.align(L_final, *rl.fit(R_lw))
    boot_ref = pd.read_csv(rl.OUT / "loadings_bootstrap.csv")

    D, wl = X[complete].reset_index(drop=True), w[complete]
    rng = np.random.default_rng(42)
    lab_path = OUT / "draw_labels.npz"
    cached = dict(np.load(lab_path)) if lab_path.exists() else {}
    draws, parties = [], []
    for b in range(rl.N_BOOT):
        i = rng.integers(0, len(D), len(D))
        key = f"d{b}"
        if key in cached:
            lab, n_sol, share = cached[key], int(cached[f"{key}_nsol"]), float(cached[f"{key}_share"])
        else:
            Rb = rl.poly(D.iloc[i].reset_index(drop=True), wl[i], None)
            _, _, phb = rl.align(La_lw, *rl.fit(Rb))
            want = boot_ref[boot_ref.draw == b].phi_pattern.values
            assert np.allclose(phb, want, atol=1e-6), f"draw {b} does not reproduce loadings_bootstrap.csv"
            Rr = rl.em.regularize_corr(Rb)
            Lb, Pb, _ = rl.align(L_final, *rl.fit(Rb))
            F, _ = rr.available_scores(Xe, we, Rr, Lb, Pb)
            lab, n_sol, share = cluster(F, we)
            cached.update({key: lab, f"{key}_nsol": n_sol, f"{key}_share": share})
            np.savez_compressed(lab_path, **cached)
        rows = match(ref, lab, we, names)
        for r in rows:
            parties.append({"draw": b, **r})
        draws.append({"draw": b, "ari_vs_reference": ari(ref, lab), "n_solutions": n_sol, "modal_share": share,
                      "min_kept": min(r["kept"] for r in rows)})
        print(f"draw {b + 1}/{rl.N_BOOT}: ARI {draws[-1]['ari_vs_reference']:.3f}, {n_sol} solutions, "
              f"modal {share:.2f}, worst kept {draws[-1]['min_kept']:.2f}", flush=True)

    dr, pa = pd.DataFrame(draws), pd.DataFrame(parties)
    dr.to_csv(OUT / "draws.csv", index=False)
    pa.to_csv(OUT / "parties.csv", index=False)
    summ = pa.groupby("party").agg(kept_median=("kept", "median"), kept_q05=("kept", lambda x: x.quantile(0.05)),
                                   kept_min=("kept", "min"), jaccard_median=("jaccard", "median"),
                                   jaccard_q05=("jaccard", lambda x: x.quantile(0.05)),
                                   share_draws_kept_below_half=("kept", lambda x: (x < 0.5).mean()))
    summ["reference_share"] = pd.Series(shares)
    summ = summ.sort_values("reference_share", ascending=False)
    summ.to_csv(OUT / "summary.csv")
    print(f"\nARI vs reference across {len(dr)} draws: median {dr.ari_vs_reference.median():.3f}, "
          f"5th pct {dr.ari_vs_reference.quantile(0.05):.3f}, min {dr.ari_vs_reference.min():.3f}")
    print(f"solutions per draw: {dr.n_solutions.value_counts().sort_index().to_dict()}; "
          f"modal share median {dr.modal_share.median():.2f}")
    print("\nPer reference party across draws:\n", summ.round(3).to_string())


if __name__ == "__main__":
    main()

"""Do production's nine parties survive redrawn factor estimates? The loading_draws.py / four_dim_draws.py test, run on
production's own procedure.

Data: CES 2024 Common Content; the 45,214 respondents complete on the 24 production items (reestimate_loadings.load).
Reference: production's parties, data/processed/typology_cluster_assignments.csv (row order of efa_factor_scores.csv).
Production procedure (analysis/efa/pipeline/efa_update.py, k_stability/fair_compare.py): weighted-standardized items,
Thomson scores F = Z R^-1 L Phi on the listwise sample, F4/F5 residualized on F1 (weighted OLS), unweighted cap-9
DPGMM, 20 seeds (42-61), modal solution, best lower bound within it.
Draws: the same 50 seed-42 respondent bootstrap draws as loading_draws.py (each checked against
outputs/loadings_bootstrap.csv). Per draw: the draw's polychoric, PAF k = 5 + oblimin aligned to production's loadings,
everyone rescored with production's formula, the cap-9 procedure. Draw clusters matched one-to-one to production's
parties on weighted overlap. Directly comparable to outputs/loading_draws/ (8-party rebuild) and
outputs/four_dim_draws/ (ten four-dimension clusters).
Writes outputs/production_draws/{draws,parties,summary}.csv, draw_labels.npz (cache); log via tee.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import adjusted_rand_score as ari

import loading_draws as ld
import reestimate_loadings as rl
import rescore_refit as rr

em = rl.em
OUT = rl.OUT / "production_draws"
CAP = 9


def thomson(Z, R, L, Phi):
    return Z @ np.linalg.solve(R, L @ Phi)


def resid(F, w):
    return np.column_stack([F[:, :3]] + [em.wresid(F[:, j], F[:, 0], w) for j in (3, 4)])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    X, w, post, complete, _ = rl.load()
    D, wl = X[complete].reset_index(drop=True), w[complete]
    fs = pd.read_csv(rl.ROOT / "data/processed/efa_factor_scores.csv")
    typ = pd.read_csv(rl.ROOT / "data/processed/typology_cluster_assignments.csv", usecols=["cluster"])
    assert len(fs) == len(D) == len(typ)
    ref = typ.cluster.values
    names = {k: rr.pc.CLUSTER_TO_PARTY[k] for k in np.unique(ref)}

    Xv = D.values.astype(float)
    wn = wl / wl.sum()
    mu = (wn[:, None] * Xv).sum(0)
    Z = (Xv - mu) / np.sqrt((wn[:, None] * (Xv - mu) ** 2).sum(0))
    L_final = pd.read_csv(rl.ROOT / "analysis/efa/efa_loadings_k5_final.csv", index_col=0).loc[rl.ITEMS, ["F1", "F2", "F3", "F4", "F5"]].values
    R_lw = rl.poly(None, None, rl.OUT / "polychoric_listwise.csv")
    La_lw, _, _ = rl.align(L_final, *rl.fit(R_lw))
    L0, P0, _ = rl.align(L_final, *rl.fit(R_lw))
    F0 = thomson(Z, em.regularize_corr(R_lw.copy()), L0, P0)
    prod_F = fs[["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]].values
    print("full-sample rescoring vs production FS_F1..F5, r per factor:",
          [round(float(np.corrcoef(F0[:, j], prod_F[:, j])[0, 1]), 3) for j in range(5)], flush=True)

    boot_ref = pd.read_csv(rl.OUT / "loadings_bootstrap.csv")
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
            assert np.allclose(phb, boot_ref[boot_ref.draw == b].phi_pattern.values, atol=1e-6), f"draw {b} mismatch"
            Lb, Pb, _ = rl.align(L_final, *rl.fit(Rb))
            Fb = resid(thomson(Z, em.regularize_corr(Rb.copy()), Lb, Pb), wl)
            res = sorted(Parallel(n_jobs=11)(delayed(ld.fit)(Fb, s, CAP) for s in ld.SEEDS))
            lab, n_sol, share = ld.modal_solution(res)
            cached.update({key: lab, f"{key}_nsol": n_sol, f"{key}_share": share})
            np.savez_compressed(lab_path, **cached)
        rows = ld.match(ref, lab, wl, names)
        for r in rows:
            parties.append({"draw": b, **r})
        draws.append({"draw": b, "ari_vs_reference": ari(ref, lab), "n_solutions": n_sol, "modal_share": share,
                      "min_kept": min(r["kept"] for r in rows)})
        print(f"draw {b + 1}/{rl.N_BOOT}: ARI {draws[-1]['ari_vs_reference']:.3f}, {n_sol} solutions, modal {share:.2f}, "
              f"worst kept {draws[-1]['min_kept']:.2f}", flush=True)

    dr, pa = pd.DataFrame(draws), pd.DataFrame(parties)
    dr.to_csv(OUT / "draws.csv", index=False)
    pa.to_csv(OUT / "parties.csv", index=False)
    shares = {names[k]: wl[ref == k].sum() / wl.sum() for k in np.unique(ref)}
    summ = pa.groupby("party").agg(kept_median=("kept", "median"), kept_q05=("kept", lambda x: x.quantile(0.05)),
                                   jaccard_median=("jaccard", "median"),
                                   share_draws_kept_below_half=("kept", lambda x: (x < 0.5).mean()))
    summ["reference_share"] = pd.Series(shares)
    summ = summ.sort_values("reference_share", ascending=False)
    summ.to_csv(OUT / "summary.csv")
    four = pd.read_csv(rl.OUT / "four_dim_draws/draws.csv")
    eight = pd.read_csv(rl.OUT / "loading_draws/draws.csv")
    for name, d in [("production nine", dr), ("eight-party rebuild", eight), ("ten four-dimension clusters", four)]:
        print(f"{name}: ARI median {d.ari_vs_reference.median():.3f}, 5th pct {d.ari_vs_reference.quantile(0.05):.3f}, "
              f"min {d.ari_vs_reference.min():.3f}; draws with a cluster under half {(d.min_kept < 0.5).mean():.2f}")
    print("\nPer production party across draws:\n", summ.round(3).to_string())


if __name__ == "__main__":
    main()

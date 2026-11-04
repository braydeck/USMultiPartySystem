"""Do the ten parties of the four-dimension space survive redrawn factor estimates? The loading_draws.py test, rerun.

Data: as four_dim_space.py (69-item pool, Stage C k = 5 item set of 30 items, four passing factors). Reference: the
cap-10 modal seed solution from outputs/four_dim/labels.npz (best lower bound within the modal solution).

Draws: 50 respondent bootstrap draws (seed 42) of the respondents complete on the 30 items. Per draw: the draw's
weighted polychoric, PAF k = 5 + oblimin aligned by Tucker phi to the full-sample pairwise solution; everyone eligible
scored on the items they answered with the draw's matrix and loadings; Religious Traditionalism and Populist
Conservatism residualized on Security & Order; cap-10 DPGMM, 20 seeds, modal solution. Draw clusters matched one-to-one
to the reference clusters on weighted overlap; each reference cluster's kept share and Jaccard recorded. Directly
comparable to outputs/loading_draws/ (the eight-party typology under the same test).
Writes outputs/four_dim_draws/{draws,parties,summary}.csv, draw_labels.npz (cache); log via tee.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import adjusted_rand_score as ari

import four_dim_space as fd
import loading_draws as ld
import reestimate_loadings as rl

em = rl.em
OUT = rl.OUT / "four_dim_draws"
CAP = 10
N_DRAWS = 50
COLS = ["SO", "TR", "RT_resid", "PC_resid"]


def polychoric(D, items, w):
    pairs = [(i, j) for i in range(len(items)) for j in range(i + 1, len(items))]
    vals = Parallel(n_jobs=11)(delayed(em.weighted_polychoric)(D[:, i], D[:, j], w) for i, j in pairs)
    M = np.eye(len(items))
    for (i, j), r in zip(pairs, vals):
        M[i, j] = M[j, i] = r
    return em.regularize_corr(M)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    items, L0, Phi0, R0, names, X, w, caseid = fd.fit_space()
    S0, elig0, _ = fd.score(items, L0, Phi0, R0, names, X, w, caseid)
    z = np.load(fd.OUT / "labels.npz")
    ref, n_sol, share = ld.modal_solution(list(zip(range(42, 62), z[f"{CAP}_seed"], z[f"{CAP}_seed_bounds"])))
    we = S0.commonpostweight.values
    rnames = {k: f"C{k}" for k in np.unique(ref)}
    print(f"reference cap {CAP}: {n_sol} seed solutions, modal share {share:.2f}; cluster shares "
          + ", ".join(f"C{k} {we[ref == k].sum() / we.sum() * 100:.1f}%" for k in np.unique(ref)))

    Xv = X[items].values.astype(float)
    comp = ~np.isnan(Xv).any(axis=1)
    D, wc = Xv[comp], w[comp]
    print(f"bootstrap base: {comp.sum():,} respondents complete on the {len(items)} items")
    rng = np.random.default_rng(42)
    lab_path = OUT / "draw_labels.npz"
    cached = dict(np.load(lab_path)) if lab_path.exists() else {}
    draws, parties = [], []
    for b in range(N_DRAWS):
        i = rng.integers(0, len(D), len(D))
        key = f"d{b}"
        if key in cached:
            lab, n_sol_b, share_b, phi_b = cached[key], int(cached[f"{key}_nsol"]), float(cached[f"{key}_share"]), cached[f"{key}_phi"]
        else:
            Rb = polychoric(D[i], items, wc[i])
            L_un, _, _ = em.paf(Rb.copy(), L0.shape[1])
            Lb, Pb = em.oblimin(L_un)
            Lb, Pb, phi_b = rl.align(L0, Lb, Pb)
            Sb, elig_b, _ = fd.score(items, Lb, Pb, Rb, names, X, w, caseid)
            res = sorted(Parallel(n_jobs=11)(delayed(ld.fit)(Sb[COLS].values, s, CAP) for s in ld.SEEDS))
            lab_b, n_sol_b, share_b = ld.modal_solution(res)
            # eligibility can shift by a respondent or two if an item's primary factor moves; align on caseid
            lab = pd.Series(lab_b, index=Sb.caseid.values).reindex(S0.caseid.values).fillna(-1).astype(int).values
            cached.update({key: lab, f"{key}_nsol": n_sol_b, f"{key}_share": share_b, f"{key}_phi": phi_b})
            np.savez_compressed(lab_path, **cached)
        rows = ld.match(ref, lab, we, rnames)
        for r in rows:
            parties.append({"draw": b, **r})
        draws.append({"draw": b, "ari_vs_reference": ari(ref, lab), "n_solutions": n_sol_b, "modal_share": share_b,
                      "min_phi": float(np.min(phi_b)), "min_kept": min(r["kept"] for r in rows)})
        print(f"draw {b + 1}/{N_DRAWS}: ARI {draws[-1]['ari_vs_reference']:.3f}, {n_sol_b} solutions, modal {share_b:.2f}, "
              f"worst factor phi {np.min(phi_b):.3f}, worst kept {draws[-1]['min_kept']:.2f}", flush=True)

    dr, pa = pd.DataFrame(draws), pd.DataFrame(parties)
    dr.to_csv(OUT / "draws.csv", index=False)
    pa.to_csv(OUT / "parties.csv", index=False)
    summ = pa.groupby("party").agg(kept_median=("kept", "median"), kept_q05=("kept", lambda x: x.quantile(0.05)),
                                   jaccard_median=("jaccard", "median"),
                                   share_draws_kept_below_half=("kept", lambda x: (x < 0.5).mean()))
    summ["reference_share"] = pd.Series({rnames[k]: we[ref == k].sum() / we.sum() for k in np.unique(ref)})
    summ = summ.sort_values("reference_share", ascending=False)
    summ.to_csv(OUT / "summary.csv")
    eight = pd.read_csv(rl.OUT / "loading_draws/draws.csv")
    print(f"\nARI vs reference across {len(dr)} draws: median {dr.ari_vs_reference.median():.3f}, "
          f"5th pct {dr.ari_vs_reference.quantile(0.05):.3f}, min {dr.ari_vs_reference.min():.3f} "
          f"(eight-party typology under the same test: median {eight.ari_vs_reference.median():.3f}, "
          f"5th pct {eight.ari_vs_reference.quantile(0.05):.3f})")
    print(f"draws where some cluster keeps under half its members: {(dr.min_kept < 0.5).mean():.2f} "
          f"(eight-party: {(eight.min_kept < 0.5).mean():.2f})")
    print("\nPer reference cluster across draws:\n", summ.round(3).to_string())


if __name__ == "__main__":
    main()

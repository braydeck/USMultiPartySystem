"""Do the five factor loadings survive re-estimation on everyone with a post-election weight?

Data: CES 2024 Common Content (efa_update.CES_PATH), production recode (efa_update.recode_items; CC24_340a
recoded as efa_pipeline_v4.py did, for the reproduction sample only). Production references:
data/processed/polychoric_matrix.csv (built by efa_pipeline_v4.py with scipy's randomized bivariate-normal
CDF) and analysis/efa/efa_loadings_k5_final.csv.

Three weighted polychoric matrices on the 24 items, all with the exact code (common/efa_math, Owen's T):
  repro     production's own sample: complete on the 25 v4 items (24 + CC24_340a). Separates code noise
            from sample change; compared cell by cell to polychoric_matrix.csv.
  listwise  the 45,214 production respondents (complete on 24 items, post weight > 0).
  pairwise  all 49,432 with a post weight; each pair uses everyone who answered both items.
Each is regularized, fit with PAF k=5 + oblimin (as efa_update.py), and matched to the production
loadings by Hungarian on |Tucker phi| (common/congruence). Parallel analysis at n capped at 20,000, as
production does. The listwise-vs-pairwise comparison is the sample effect; production-vs-repro is the
floor set by the code change. A 50-draw respondent bootstrap of the listwise sample (seed 42) gives the
loading movement expected from resampling alone, as the benchmark for the listwise-vs-pairwise change.
Writes outputs/polychoric_{repro,listwise,pairwise}.csv and outputs/loadings_bootstrap.csv (cached; delete to rebuild),
outputs/loadings_compare.csv, outputs/loadings_pairwise.csv, outputs/reestimate_run.log (via tee).
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "analysis" / "efa" / "pipeline"))
sys.path.insert(0, str(ROOT / "analysis" / "efa" / "previous_years"))
import efa_update as eu  # noqa: E402
from common import efa_math as em  # noqa: E402
from common import congruence as cg  # noqa: E402

OUT = Path(__file__).parent / "outputs"
ITEMS = eu.ITEMS_24
NAMES = ["Security & Order", "Institutional Distrust", "Government Distrust",
         "Religious Traditionalism", "Populist Conservatism"]
PA_CAP = 20000
N_BOOT = 50


def load():
    lab = pd.read_stata(eu.CES_PATH, columns=ITEMS + [eu.DROP_ITEM], convert_categoricals=True,
                        convert_missing=False, convert_dates=False)
    w = pd.to_numeric(pd.read_stata(eu.CES_PATH, columns=["commonpostweight"], convert_categoricals=False)
                      .commonpostweight, errors="coerce").values
    X = eu.recode_items(lab)
    x340a = lab[eu.DROP_ITEM].map(eu.OPPOSE_HI).astype(float)
    post = w > 0
    complete = X.notna().all(axis=1).values & post
    repro = complete & x340a.notna().values
    return X, w, post, complete, repro


def poly(D, w, path):
    if path is not None and path.exists():
        return pd.read_csv(path, index_col=0).loc[ITEMS, ITEMS].values
    pairs = [(i, j) for i in range(len(ITEMS)) for j in range(i + 1, len(ITEMS))]
    vals = Parallel(n_jobs=11)(delayed(em.weighted_polychoric)(D[ITEMS[i]].values, D[ITEMS[j]].values, w)
                               for i, j in pairs)
    M = np.eye(len(ITEMS))
    for (i, j), r in zip(pairs, vals):
        M[i, j] = M[j, i] = r
    if path is not None:
        pd.DataFrame(M, index=ITEMS, columns=ITEMS).to_csv(path)
    return M


def fit(R):
    L_un, _, _ = em.paf(em.regularize_corr(R.copy()), 5)
    L, Phi = em.oblimin(L_un)
    return L, Phi


def align(L_ref, L, Phi):
    """Permute and sign-flip L (and Phi) onto L_ref's factor order; return aligned L, Phi, signed phis."""
    m = sorted(cg.match_factors(L_ref, L), key=lambda d: d["factor_1"])
    order = [d["factor_2"] for d in m]
    sign = np.array([1.0 if d["phi"] >= 0 else -1.0 for d in m])
    La = L[:, order] * sign
    Pa = Phi[np.ix_(order, order)] * np.outer(sign, sign)
    return La, Pa, np.array([abs(d["phi"]) for d in m])


def main():
    OUT.mkdir(exist_ok=True)
    X, w, post, complete, repro = load()
    n = {"repro": repro.sum(), "listwise": complete.sum(), "pairwise": post.sum()}
    print(f"samples: repro {n['repro']:,}, listwise {n['listwise']:,}, pairwise {n['pairwise']:,}")
    pair_n = np.array([[(X[a].notna() & X[b].notna() & post).sum() for b in ITEMS] for a in ITEMS])
    print(f"pairwise n per item pair: min {pair_n[np.triu_indices(24, 1)].min():,}, "
          f"median {int(np.median(pair_n[np.triu_indices(24, 1)])):,}")

    R = {"production": pd.read_csv(ROOT / "data/processed/polychoric_matrix.csv", index_col=0).loc[ITEMS, ITEMS].values}
    for name, mask in (("repro", repro), ("listwise", complete), ("pairwise", post)):
        R[name] = poly(X[mask].reset_index(drop=True), w[mask], OUT / f"polychoric_{name}.csv")

    off = np.triu_indices(24, 1)
    def cell_diff(a, b):
        d = np.abs(R[a] - R[b])[off]
        return f"{a} vs {b}: max |dr| {d.max():.4f}, mean {d.mean():.4f}, cells > 0.02: {(d > 0.02).sum()} of 276"
    for a, b in (("production", "repro"), ("repro", "listwise"), ("listwise", "pairwise")):
        print(cell_diff(a, b))
    d = R["pairwise"] - R["listwise"]
    i, j = np.unravel_index(np.argsort(-np.abs(np.triu(d, 1)), axis=None)[:5], d.shape)
    print("largest pairwise-minus-listwise cells:", [(ITEMS[a], ITEMS[b], round(float(d[a, b]), 3)) for a, b in zip(i, j)])

    L_final = pd.read_csv(ROOT / "analysis/efa/efa_loadings_k5_final.csv", index_col=0).loc[ITEMS, ["F1", "F2", "F3", "F4", "F5"]].values
    fits = {k: fit(v) for k, v in R.items()}
    La_prod, _, phi_prod = align(L_final, *fits["production"])
    assert np.abs(La_prod - L_final).max() < 1e-6, "production loadings not reproduced from polychoric_matrix.csv"
    print("production matrix refit reproduces efa_loadings_k5_final.csv exactly")

    aligned = {k: align(L_final, *fits[k]) for k in ("repro", "listwise", "pairwise")}
    La_lw, Phi_lw, _ = aligned["listwise"]
    La_pw, Phi_pw, _ = aligned["pairwise"]
    rows = []
    for k, (La, Pa, ph) in aligned.items():
        for f in range(5):
            rows.append({"matrix": k, "factor": NAMES[f], "phi_vs_production": ph[f],
                         "phi_vs_listwise": cg.tucker_phi(La_lw[:, f], La[:, f]),
                         "max_abs_dloading_vs_production": np.abs(La[:, f] - L_final[:, f]).max(),
                         "max_abs_dloading_vs_listwise": np.abs(La[:, f] - La_lw[:, f]).max()})
    cmp_ = pd.DataFrame(rows)
    cmp_.to_csv(OUT / "loadings_compare.csv", index=False)
    print("\nFactor congruence (Tucker phi) and largest loading change:\n", cmp_.round(4).to_string(index=False))

    dl = pd.DataFrame(La_pw - La_lw, index=ITEMS, columns=NAMES)
    top = dl.stack().abs().sort_values(ascending=False).head(8)
    print("\nLargest loading changes, pairwise minus listwise (same code):")
    for (item, f), v in top.items():
        print(f"  {item:<11} {f:<25} listwise {La_lw[ITEMS.index(item), NAMES.index(f)]:+.3f} -> "
              f"pairwise {La_pw[ITEMS.index(item), NAMES.index(f)]:+.3f}")
    print("\nFactor correlations, listwise (lower) / pairwise (upper):")
    both = np.tril(Phi_lw, -1) + np.triu(Phi_pw, 1) + np.eye(5)
    print(pd.DataFrame(both, index=[x[:12] for x in NAMES], columns=[x[:12] for x in NAMES]).round(3).to_string())

    pd.DataFrame(La_pw, index=ITEMS, columns=NAMES).assign(
        **{f"{c}_listwise": La_lw[:, j] for j, c in enumerate(NAMES)}).to_csv(OUT / "loadings_pairwise.csv")

    S_lw, S_pw = La_lw @ Phi_lw, La_pw @ Phi_pw
    print("\nStructure-matrix phi, pairwise vs listwise (rotation-frame free):",
          dict(zip(NAMES, [round(cg.tucker_phi(S_lw[:, f], S_pw[:, f]), 4) for f in range(5)])))

    boot_path = OUT / "loadings_bootstrap.csv"
    if boot_path.exists():
        boot = pd.read_csv(boot_path)
    else:
        rng = np.random.default_rng(42)
        D, wl = X[complete].reset_index(drop=True), w[complete]
        brows = []
        for b in range(N_BOOT):
            i = rng.integers(0, len(D), len(D))
            Rb = poly(D.iloc[i].reset_index(drop=True), wl[i], None)
            Lb, Pb, phb = align(La_lw, *fit(Rb))
            Sb = Lb @ Pb
            for f in range(5):
                brows.append({"draw": b, "factor": NAMES[f], "phi_pattern": phb[f],
                              "phi_structure": cg.tucker_phi(S_lw[:, f], Sb[:, f]),
                              "max_abs_dloading": np.abs(Lb[:, f] - La_lw[:, f]).max()})
            print(f"  bootstrap draw {b + 1}/{N_BOOT}", flush=True)
        boot = pd.DataFrame(brows)
        boot.to_csv(boot_path, index=False)
    summ = boot.groupby("factor", sort=False).agg(phi_pattern_min=("phi_pattern", "min"), phi_pattern_med=("phi_pattern", "median"),
                                                   dload_med=("max_abs_dloading", "median"), dload_max=("max_abs_dloading", "max"),
                                                   phi_structure_min=("phi_structure", "min"))
    pw = cmp_[cmp_.matrix == "pairwise"].set_index("factor")
    summ["pairwise_phi"] = pw.phi_vs_listwise
    summ["pairwise_dload"] = pw.max_abs_dloading_vs_listwise
    summ["share_draws_phi_below_pairwise"] = boot.groupby("factor", sort=False).apply(
        lambda g: (g.phi_pattern <= pw.phi_vs_listwise[g.name]).mean())
    print(f"\nListwise resampling noise ({N_BOOT} respondent bootstrap draws, seed 42) vs the pairwise change:\n",
          summ.loc[NAMES].round(4).to_string())

    print("\nParallel analysis k (n capped at 20,000):")
    for k in ("production", "listwise", "pairwise"):
        nf, ev, thr = em.parallel_analysis(em.regularize_corr(R[k].copy()), min(n.get(k, 45707), PA_CAP))
        print(f"  {k:<10} k = {nf}; first six eigenvalues {np.round(ev[:6], 3).tolist()}")


if __name__ == "__main__":
    main()

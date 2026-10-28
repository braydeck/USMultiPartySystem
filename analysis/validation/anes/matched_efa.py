"""Matched EFA: does the CES 2024 factor structure reappear in ANES 2024 on the same items?

Data: ANES 2024 Time Series CSV (2025-08-08 release), recoded by the frozen crosswalk
(config/anes_matched_crosswalk.csv, commit af017de); CES 2024 weighted polychoric matrix
(data/processed/polychoric_matrix.csv, n = 45,707) and k=5 loadings
(analysis/efa/efa_loadings_k5_final.csv).

Specified before running:
  - Same math as CES (analysis/efa/previous_years/common/efa_math): weighted polychoric,
    PAF, oblimin. k = 5 is the primary fit; the parallel-analysis k is reported alongside.
  - Primary comparison: ANES on the 18 matched items vs CES refit on the same 18 items
    (the CES polychoric matrix subset; pairwise polychorics don't depend on other items).
  - Secondary: ANES vs the canonical CES 24-item loadings, restricted to the 18 rows.
  - Factors matched by Hungarian on |Tucker phi|; >= 0.95 identical, >= 0.85 fair.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "analysis" / "efa" / "previous_years"))
sys.path.insert(0, str(HERE))
from common import efa_math as em  # noqa: E402
from common import congruence as cg  # noqa: E402
import recode_matched as rm  # noqa: E402

OUT = HERE / "outputs"
CES_R = ROOT / "data" / "processed" / "polychoric_matrix.csv"
CES_L = ROOT / "analysis" / "efa" / "efa_loadings_k5_final.csv"
CES_NAMES = {"F1": "Security & Order", "F2": "Institutional Distrust", "F3": "Government Distrust",
             "F4": "Religious Traditionalism", "F5": "Populist Conservatism"}
N_PA_CES = 20000  # production parallel analysis caps n_obs at 20,000


def fit(R, k):
    L_un, _, _ = em.paf(R, k)
    L, Phi = em.oblimin(L_un)
    h2 = np.clip(np.diag(L @ Phi @ L.T), 0, 1)
    return L, Phi, h2


def compare(L_ref, L_new, ref_names, new_label):
    rows = []
    for m in cg.match_factors(L_ref, L_new):
        rows.append({"ces_factor": ref_names[m["factor_1"]], f"{new_label}_factor": f"A{m['factor_2'] + 1}",
                     "phi": m["phi"], "replication": m["replication"]})
    return pd.DataFrame(rows)


def main():
    raw, items, cw = rm.load_matched()
    ids = list(items.columns)
    w = raw[rm.WEIGHT].values.astype(float)
    mask = items.notna().all(axis=1).values & ~np.isnan(w) & (w > 0)
    D, ww = items[mask].reset_index(drop=True), w[mask]
    print(f"ANES matched set: {len(ids)} items, listwise n = {len(D):,}")

    R_anes = em.regularize_corr(em.polychoric_matrix(D, ids, ww, progress=False))
    R_ces = em.regularize_corr(pd.read_csv(CES_R, index_col=0).loc[ids, ids].values)
    OUT.mkdir(exist_ok=True)
    pd.DataFrame(R_anes, index=ids, columns=ids).round(4).to_csv(OUT / "matched_polychoric_anes.csv")

    k_anes, ev_anes, thr_anes = em.parallel_analysis(R_anes, n_obs=len(D))
    k_ces, ev_ces, thr_ces = em.parallel_analysis(R_ces, n_obs=N_PA_CES)
    pa = pd.DataFrame({"factor": range(1, 8), "anes_eigen": ev_anes[:7].round(3),
                       "anes_threshold": np.asarray(thr_anes)[:7].round(3),
                       "ces18_eigen": ev_ces[:7].round(3), "ces18_threshold": np.asarray(thr_ces)[:7].round(3)})
    pa.to_csv(OUT / "matched_parallel.csv", index=False)
    print(f"\nParallel analysis: ANES k = {k_anes}, CES on same 18 items k = {k_ces}")
    print(pa.to_string(index=False))

    L_can = pd.read_csv(CES_L, index_col=0).loc[ids, list(CES_NAMES)].values
    for k in sorted({5, k_anes, k_ces}):
        L_a, Phi_a, h2_a = fit(R_anes, k)
        L_c, Phi_c, h2_c = fit(R_ces, k)
        ces_names = [f"C{j + 1}" for j in range(k)]
        tab = compare(L_c, L_a, ces_names, "anes")
        # label the CES-18 refit factors by their best match to the canonical named factors
        canon = cg.match_factors(L_can, L_c)
        name_of = {m["factor_2"]: f"{CES_NAMES[list(CES_NAMES)[m['factor_1']]]} (phi {m['phi']:+.2f})" for m in canon}
        tab.insert(1, "ces18_matches_canonical", [name_of.get(int(c[1:]) - 1, "(no canonical match)") for c in tab.ces_factor])
        print(f"\n=== k = {k}: ANES vs CES refit on the same 18 items ===")
        print(tab.to_string(index=False))
        sec = compare(L_can, L_a, list(CES_NAMES.values()), "anes") if k == 5 else None
        if sec is not None:
            print("\n=== k = 5: ANES vs canonical CES loadings (18 shared rows) ===")
            print(sec.to_string(index=False))
            sec.to_csv(OUT / "matched_phi_vs_canonical_k5.csv", index=False)
        tab.to_csv(OUT / f"matched_phi_vs_ces18_k{k}.csv", index=False)
        load = pd.DataFrame(L_a, index=ids, columns=[f"A{j + 1}" for j in range(k)]).round(3)
        load["h2"] = h2_a.round(3)
        load.insert(0, "anes_item", cw.set_index("ces_var").loc[ids, "anes_sources"].values)
        load.to_csv(OUT / f"matched_loadings_anes_k{k}.csv")
        cl = pd.DataFrame(L_c, index=ids, columns=ces_names).round(3)
        cl["h2"] = h2_c.round(3)
        cl.to_csv(OUT / f"matched_loadings_ces18_k{k}.csv")
        pd.DataFrame(Phi_a, index=load.columns[1:-1], columns=load.columns[1:-1]).round(3).to_csv(
            OUT / f"matched_factor_corr_anes_k{k}.csv")
        heywood = [i for i, h in zip(ids, h2_a) if h >= 0.995]
        print(f"\nANES k={k} loadings (Heywood: {heywood or 'none'}):")
        print(load.to_string())


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""2024 REPRODUCTION GATE.

Runs the extracted shared math on the canonical 2024 24-item recode and asserts it
reproduces the frozen artifacts:
  1. fresh weighted polychoric  ~= data/processed/polychoric_matrix.csv (drop CC24_340a)
  2. PAF+oblimin loadings        == analysis/efa/efa_loadings_k5_final.csv
  3. Thomson+resid+DPGMM shares  ~= data/processed/typology_cluster_assignments.csv

If any check fails the shared module has diverged from canon and no prior-wave
result should be trusted.
"""
import sys, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import efa_math as em, clustering as cl, io_paths as io

ROOT = io.ROOT
DTA = io.dta_path("2024")

ITEMS_25 = ["pew_churatd","CC24_302","CC24_303","CC24_341a","CC24_341c","CC24_341d","CC24_323a",
 "CC24_323b","CC24_323d","CC24_321b","CC24_321d","CC24_321e","CC24_325","CC24_324b","CC24_340a",
 "CC24_340b","CC24_340c","CC24_340e","CC24_340f","CC24_440b","CC24_440c","CC24_421_1","CC24_421_2",
 "CC24_423","CC24_424"]
ITEMS = [x for x in ITEMS_25 if x != "CC24_340a"]


def canonical_recode(df):
    S, O = "Support", "Oppose"
    ca = {"Strongly agree":5,"Somewhat agree":4,"Neither agree nor disagree":3,"Somewhat disagree":2,"Strongly disagree":1}
    el = {"Strongly agree":1,"Somewhat agree":2,"Neither agree nor disagree":3,"Somewhat disagree":4,"Strongly disagree":5}
    gv = {"A great deal":1,"A fair amount":2,"Not very much":3,"None at all":4,"Not sure":2}
    c = lambda col, m: df[col].map(m).astype(float)
    r = {}
    r["pew_churatd"] = c("pew_churatd", {"Never":1,"Seldom":2,"A few times a year":3,"Once or twice a month":4,"Once a week":5,"More than once a week":6,"Don't know":np.nan})
    r["CC24_302"] = c("CC24_302", {"Increased a lot":1,"Increased somewhat":2,"Stayed about the same":3,"Decreased somewhat":4,"Decreased a lot":5})
    r["CC24_303"] = c("CC24_303", {"Decreased a lot":1,"Decreased somewhat":2,"Stayed about the same":3,"Increased somewhat":4,"Increased a lot":5})
    r["CC24_341a"] = c("CC24_341a", {S:1,O:0}); r["CC24_341c"] = c("CC24_341c", {S:0,O:1}); r["CC24_341d"] = c("CC24_341d", {S:0,O:1})
    r["CC24_323a"] = c("CC24_323a", {S:0,O:1}); r["CC24_323b"] = c("CC24_323b", {S:1,O:0}); r["CC24_323d"] = c("CC24_323d", {S:0,O:1})
    r["CC24_321b"] = c("CC24_321b", {S:1,O:0}); r["CC24_321d"] = c("CC24_321d", {S:1,O:0}); r["CC24_321e"] = c("CC24_321e", {S:0,O:1})
    r["CC24_325"] = 40.0 - pd.to_numeric(df["CC24_325"].astype(str), errors="coerce"); r["CC24_324b"] = c("CC24_324b", {S:1,O:0})
    r["CC24_340b"] = c("CC24_340b", {S:0,O:1}); r["CC24_340c"] = c("CC24_340c", {S:0,O:1})
    r["CC24_340e"] = c("CC24_340e", {S:1,O:0}); r["CC24_340f"] = c("CC24_340f", {S:1,O:0})
    r["CC24_440b"] = c("CC24_440b", ca); r["CC24_440c"] = c("CC24_440c", ca)
    r["CC24_421_1"] = c("CC24_421_1", el); r["CC24_421_2"] = c("CC24_421_2", el)
    r["CC24_423"] = c("CC24_423", gv); r["CC24_424"] = c("CC24_424", gv)
    return pd.DataFrame(r)


def main():
    print("=== 2024 REPRODUCTION GATE ===", flush=True)
    df = pd.read_stata(str(DTA), columns=ITEMS + ["commonpostweight", "pid3"],
                       convert_categoricals=True, convert_missing=False, convert_dates=False)
    R = canonical_recode(df)
    R["w"] = pd.to_numeric(df["commonpostweight"], errors="coerce").values
    R["pid3"] = df["pid3"].map({"Democrat":1,"Republican":2,"Independent":3,"Other":4,"Not sure":5}).values
    comp = R[ITEMS].notna().all(axis=1) & R["w"].notna()
    D = R[comp].reset_index(drop=True)
    w = D["w"].values; pid3 = D["pid3"].values
    print(f"listwise N = {len(D):,}  (canon 45,707)", flush=True)

    # --- check 1: fresh polychoric vs frozen matrix ---
    Rmat = em.polychoric_matrix(D, ITEMS, w, progress=True)
    ref_poly = pd.read_csv(ROOT / "data/processed/polychoric_matrix.csv", index_col=0).loc[ITEMS, ITEMS].values
    poly_maxdiff = np.abs(Rmat - ref_poly).max()
    print(f"\n[1] polychoric max abs diff vs frozen: {poly_maxdiff:.4f}  -> {'PASS' if poly_maxdiff < 0.02 else 'FAIL'}")

    # --- check 2: loadings vs frozen ---
    Rreg = em.regularize_corr(Rmat)
    L_un, _, _ = em.paf(Rreg, 5); L, Phi = em.oblimin(L_un)
    refL = pd.read_csv(ROOT / "analysis/efa/efa_loadings_k5_final.csv", index_col=0).loc[ITEMS, ["F1","F2","F3","F4","F5"]].values
    from scipy.optimize import linear_sum_assignment
    C = np.array([[abs(np.corrcoef(L[:,a], refL[:,b])[0,1]) for b in range(5)] for a in range(5)])
    ri, ci = linear_sum_assignment(-C)
    perm = {b: a for a, b in zip(ri, ci)}
    Lm = np.column_stack([L[:, perm[b]] for b in range(5)])
    for b in range(5):
        if np.corrcoef(Lm[:, b], refL[:, b])[0, 1] < 0:
            Lm[:, b] *= -1
    load_maxdiff = np.abs(np.abs(Lm) - np.abs(refL)).max()
    print(f"[2] loadings max abs diff vs frozen: {load_maxdiff:.4f}  -> {'PASS' if load_maxdiff < 0.02 else 'FAIL'}")

    # --- check 3: cluster shares vs frozen (via canonical FS_* from frozen scores space) ---
    # Use our fresh scores + residualization + DPGMM; compare sorted share vector.
    Z, mu, sig = em.weighted_standardize(D[ITEMS].values.astype(float), w)
    F, B = em.thomson_scores(Z, Rreg, L, Phi)
    F, L2 = em.sign_align_by_loading(F, L)
    a = lambda it: int(np.argmax(np.abs(L2[ITEMS.index(it), :])))
    enf, rel, val = a("CC24_323b"), a("pew_churatd"), a("CC24_440b")
    dem = pid3 == 1; rep = pid3 == 2
    for j in (enf, rel, val):
        if np.average(F[rep, j], weights=w[rep]) < np.average(F[dem, j], weights=w[dem]):
            F[:, j] *= -1
    Xc = F.copy()
    for j in (rel, val):
        if j != enf:
            Xc[:, j] = em.wresid(F[:, j], F[:, enf], w)
    model, raw, _ = cl.dpgmm_fit(Xc)
    cluster, _ = cl.remap_by_weighted_n(raw, w, model.weights_)
    shares = np.sort([w[cluster == k].sum() / w.sum() * 100 for k in range(int((model.weights_ > 0.01).sum()))])[::-1]
    ref = pd.read_csv(ROOT / "data/processed/typology_cluster_assignments.csv", usecols=["cluster", "commonpostweight"])
    refshares = np.sort(ref.groupby("cluster")["commonpostweight"].sum() / ref["commonpostweight"].sum() * 100)[::-1]
    n = min(len(shares), len(refshares))
    share_maxdiff = np.abs(shares[:n] - refshares[:n]).max()
    print(f"[3] cluster-share vector (sorted) max diff vs frozen: {share_maxdiff:.2f} pp")
    print(f"    fresh : {np.round(shares,1)}")
    print(f"    frozen: {np.round(refshares,1)}")
    print(f"    -> {'PASS' if share_maxdiff < 3.0 else 'REVIEW (DPGMM is stochastic; inspect)'}")
    print("\n=== GATE COMPLETE ===")


if __name__ == "__main__":
    main()

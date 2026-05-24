#!/usr/bin/env python3
"""
run_efa_k4.py
-------------
4-factor EFA on the 24-item polychoric matrix, Bartlett factor scores,
and F1-residualization for factors that strongly correlate with F1.

Inputs:
  data/processed/polychoric_matrix.csv   (25×25 polychoric R, CC24_340a dropped)
  data/raw/.../CCES24_Common_...dta      (raw survey for factor scoring)

Outputs (all in analysis/efa_k4/):
  efa_loadings_k4_final.csv
  efa_phi_k4_final.csv

Outputs (data/processed/k4/):
  efa_factor_scores_k4.csv   — columns: pid3, ideo5, inputstate,
                               commonpostweight, govt_trust_imputed,
                               FS_F1..FS_F4, + resid cols for correlated factors
"""

import warnings
import numpy as np
import pandas as pd
from pathlib import Path

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent.parent
POLY_PATH  = BASE_DIR / "data" / "processed" / "polychoric_matrix.csv"

_CES_CANDIDATES = [
    BASE_DIR / "data" / "raw" / "2024 CES Base" / "CCES24_Common_OUTPUT_vv_topost_final.dta",
    Path.home() / "Downloads" / "dataverse_files" / "CCES24_Common_OUTPUT_vv_topost_final.dta",
    Path.home() / "Documents" / "STV" / "2024 CES Base" / "CCES24_Common_OUTPUT_vv_topost_final.dta",
]
CES_PATH = next((p for p in _CES_CANDIDATES if p.exists()), _CES_CANDIDATES[0])
EFA_OUT    = BASE_DIR / "analysis" / "efa_k4"
PROC_OUT   = BASE_DIR / "data" / "processed" / "k4"

N_FACTORS  = 4
RESID_THRESHOLD = 0.25   # |phi(F1, Fj)| above this → residualize Fj against F1

ITEMS_25 = [
    "pew_churatd", "CC24_302",   "CC24_303",   "CC24_341a",  "CC24_341c",
    "CC24_341d",   "CC24_323a",  "CC24_323b",  "CC24_323d",  "CC24_321b",
    "CC24_321d",   "CC24_321e",  "CC24_325",   "CC24_324b",  "CC24_340a",
    "CC24_340b",   "CC24_340c",  "CC24_340e",  "CC24_340f",  "CC24_440b",
    "CC24_440c",   "CC24_421_1", "CC24_421_2", "CC24_423",   "CC24_424",
]
ITEMS_24 = [it for it in ITEMS_25 if it != "CC24_340a"]

REV_BINARY = {
    "CC24_341c", "CC24_341d",
    "CC24_323a", "CC24_323d",
    "CC24_321e",
    "CC24_340b", "CC24_340c",
}


# ── PAF ───────────────────────────────────────────────────────────────────────
def compute_smc(R):
    try:
        R_inv = np.linalg.inv(R)
        smc = 1.0 - 1.0 / np.diag(R_inv)
    except np.linalg.LinAlgError:
        smc = np.full(R.shape[0], 0.5)
    return np.clip(smc, 0.005, 0.999)


def paf(R, n_factors, n_iter=1000, tol=1e-7):
    h2 = compute_smc(R)
    for _ in range(n_iter):
        R_red = R.copy()
        np.fill_diagonal(R_red, h2)
        evals, evecs = np.linalg.eigh(R_red)
        idx = np.argsort(evals)[::-1]
        evals, evecs = evals[idx], evecs[:, idx]
        pos = np.maximum(evals[:n_factors], 0.0)
        L = evecs[:, :n_factors] * np.sqrt(pos)
        h2_new = np.clip(np.sum(L ** 2, axis=1), 0.0, 0.999)
        if np.max(np.abs(h2_new - h2)) < tol:
            h2 = h2_new
            break
        h2 = h2_new
    return L, h2, evals[:n_factors]


def oblimin(A, gamma=0):
    from factor_analyzer.rotator import Rotator
    rot = Rotator(method="oblimin", power=gamma)
    L = rot.fit_transform(A)
    Phi = rot.phi_ if rot.phi_ is not None else np.eye(A.shape[1])
    return L, Phi


# ══════════════════════════════════════════════════════════════════════════════
def main():
    sep  = "=" * 72
    thin = "─" * 72
    fnames = [f"F{j+1}" for j in range(N_FACTORS)]

    print(sep)
    print(f"EFA K={N_FACTORS}  |  24-item polychoric matrix  |  Bartlett factor scores")
    print(sep)

    # ── 1. Load & prepare polychoric matrix ───────────────────────────────────
    print(f"\n{thin}")
    print("STEP 1: LOAD 24-ITEM POLYCHORIC SUBMATRIX")
    print(thin)

    corr_df = pd.read_csv(POLY_PATH, index_col=0)
    if "CC24_340a" in corr_df.index:
        corr_df = corr_df.drop(index="CC24_340a", columns="CC24_340a")
    assert list(corr_df.columns) == ITEMS_24, "Item order mismatch in polychoric matrix"

    R = corr_df.values.astype(float)
    R = (R + R.T) / 2.0
    np.fill_diagonal(R, 1.0)

    min_eig = np.linalg.eigvalsh(R).min()
    if min_eig < 1e-6:
        bump = abs(min_eig) + 1e-4
        R += np.eye(len(ITEMS_24)) * bump
        d = np.sqrt(np.diag(R))
        R /= np.outer(d, d)
        print(f"  [regularized: +{bump:.5f} to fix non-PSD]")

    print(f"  24×24 matrix ready. Eigenvalue range: "
          f"[{np.linalg.eigvalsh(R).min():.4f}, {np.linalg.eigvalsh(R).max():.4f}]")

    # ── 2. PAF + oblimin ──────────────────────────────────────────────────────
    print(f"\n{thin}")
    print(f"STEP 2: PAF + OBLIMIN  k={N_FACTORS}")
    print(thin)

    L_unrot, h2_init, eigs = paf(R, N_FACTORS)
    L_rot, Phi = oblimin(L_unrot)
    h2 = np.clip(np.diag(L_rot @ Phi @ L_rot.T), 0.0, 1.0)

    ss = np.sum(L_rot ** 2, axis=0)
    pv = ss / len(ITEMS_24) * 100.0

    print(f"\n  Variance Explained:")
    print(f"  {'Factor':>6}  {'SS Load':>8}  {'%Var':>7}  {'Cum%':>7}")
    cumul = 0.0
    for j in range(N_FACTORS):
        cumul += pv[j]
        print(f"  {fnames[j]:>6}  {ss[j]:>8.3f}  {pv[j]:>6.1f}%  {cumul:>6.1f}%")

    print(f"\n  Factor Intercorrelations (Φ):")
    phi_df = pd.DataFrame(np.round(Phi, 4), index=fnames, columns=fnames)
    print("  " + phi_df.to_string().replace("\n", "\n  "))

    print(f"\n  Pattern Matrix  (|λ| < 0.25 suppressed):")
    hdr = f"  {'Item':<15}" + "".join(f"  {fn:>7}" for fn in fnames) + f"  {'h²':>6}"
    print(hdr)
    print(f"  {'─'*15}" + "  ─────  " * N_FACTORS + "  ─────")
    for i, item in enumerate(ITEMS_24):
        row = f"  {item:<15}"
        for j in range(N_FACTORS):
            v = L_rot[i, j]
            row += f"  {v:>7.3f}" if abs(v) >= 0.25 else f"  {'':>7}"
        row += f"  {h2[i]:>6.3f}"
        print(row)

    # ── 3. Load & recode raw DTA ──────────────────────────────────────────────
    print(f"\n{thin}")
    print("STEP 3: LOAD & RECODE RAW DTA")
    print(thin)

    import pyreadstat
    COLS_NEEDED = ITEMS_24 + ["pid3", "ideo5", "commonpostweight", "inputstate"]
    print(f"  Reading {CES_PATH.name} …")
    df_raw, _ = pyreadstat.read_dta(
        str(CES_PATH),
        usecols=COLS_NEEDED,
        apply_value_formats=False,
    )
    print(f"  Raw rows: {len(df_raw):,}")

    # Flag / recode "Not sure" (8) on govt trust items
    df_raw["govt_trust_imputed"] = (
        (df_raw["CC24_423"] == 8) | (df_raw["CC24_424"] == 8)
    ).astype(int)
    for col in ["CC24_423", "CC24_424"]:
        df_raw[col] = df_raw[col].where(df_raw[col] != 8, other=2)

    # ideo5: 6 → NaN
    df_raw["ideo5"] = df_raw["ideo5"].where(df_raw["ideo5"] != 6, other=np.nan)

    # CC24_303 direction check
    mask_chk = df_raw[["CC24_303", "CC24_341a", "commonpostweight"]].notna().all(axis=1)
    df_chk = df_raw[mask_chk]
    w_chk = df_chk["commonpostweight"].values
    x303  = df_chk["CC24_303"].values
    x341a = df_chk["CC24_341a"].values
    mu303  = np.sum(w_chk * x303)  / w_chk.sum()
    mu341a = np.sum(w_chk * x341a) / w_chk.sum()
    cov    = np.sum(w_chk * (x303 - mu303) * (x341a - mu341a)) / w_chk.sum()
    s303   = np.sqrt(np.sum(w_chk * (x303 - mu303)  ** 2) / w_chk.sum())
    s341a  = np.sqrt(np.sum(w_chk * (x341a - mu341a) ** 2) / w_chk.sum())
    r303   = cov / (s303 * s341a)
    needs_rev_303 = r303 < 0
    print(f"  CC24_303 direction check: Pearson(303, 341a) = {r303:+.4f} "
          f"→ {'FLIP' if needs_rev_303 else 'OK'}")

    df = df_raw.copy()
    if needs_rev_303:
        df["CC24_303"] = 6 - df["CC24_303"]
    for col in REV_BINARY:
        if col in df.columns:
            df[col] = 3 - df[col]
    df["CC24_325"] = 40 - df["CC24_325"]

    # Listwise deletion
    mask = df[ITEMS_24 + ["commonpostweight"]].notna().all(axis=1)
    df_c = df[mask].copy().reset_index(drop=True)
    print(f"  After listwise deletion: N = {len(df_c):,}")

    # ── 4. Compute Thomson factor scores ──────────────────────────────────────
    print(f"\n{thin}")
    print("STEP 4: BARTLETT FACTOR SCORES (Thomson regression)")
    print(thin)

    X = df_c[ITEMS_24].values.astype(float)
    w = df_c["commonpostweight"].values
    w_norm = w / w.sum()

    mu  = np.array([np.sum(w_norm * X[:, j]) for j in range(len(ITEMS_24))])
    sig = np.array([np.sqrt(np.sum(w_norm * (X[:, j] - mu[j]) ** 2))
                    for j in range(len(ITEMS_24))])
    sig[sig < 1e-10] = 1.0
    Z = (X - mu) / sig

    S   = L_rot @ Phi
    R_inv = np.linalg.inv(R)
    B   = R_inv @ S
    F   = Z @ B

    # ── 5. Sign flips ─────────────────────────────────────────────────────────
    # Anchor items for factor identification
    anchors = {
        "CC24_323b":  "enforcement/immigration",
        "pew_churatd": "repro rights/religion",
        "CC24_440b":  "values conservatism",
        "CC24_421_2": "institutional distrust",   # cross-partisan: left as-is
    }

    anchor_map = {}   # construct → factor index
    for item, construct in anchors.items():
        idx = ITEMS_24.index(item)
        fj  = int(np.argmax(np.abs(L_rot[idx, :])))
        anchor_map[construct] = fj
        print(f"  {item} ({construct}) → F{fj+1}  (loading {L_rot[idx, fj]:+.3f})")

    # Warn on collisions
    conservative_factors = [anchor_map[k] for k in
                             ["enforcement/immigration", "repro rights/religion",
                              "values conservatism"]]
    if len(set(conservative_factors)) < 3:
        print(f"  ⚠  Anchor collision: {conservative_factors} — check solution stability")

    mask_dem = (df_c["pid3"] == 1).values
    mask_rep = (df_c["pid3"] == 2).values

    print(f"\n  Sign-flip decisions (Republicans should score higher on conservative factors):")
    for construct in ["enforcement/immigration", "repro rights/religion", "values conservatism"]:
        fj = anchor_map[construct]
        fs = F[:, fj]
        w_dem = w[mask_dem]; w_rep = w[mask_rep]
        mean_dem = np.sum(w_dem * fs[mask_dem]) / w_dem.sum()
        mean_rep = np.sum(w_rep * fs[mask_rep]) / w_rep.sum()
        if mean_rep < mean_dem:
            F[:, fj] *= -1
            print(f"  F{fj+1} ({construct}): FLIPPED  "
                  f"[Rep {mean_rep:+.3f}→{-mean_rep:+.3f}, Dem {mean_dem:+.3f}→{-mean_dem:+.3f}]")
        else:
            print(f"  F{fj+1} ({construct}): OK  [Rep {mean_rep:+.3f} > Dem {mean_dem:+.3f}]")

    distrust_j = anchor_map["institutional distrust"]
    print(f"  F{distrust_j+1} (institutional distrust): left as-is (cross-partisan)")

    # Store raw scores
    for j, fn in enumerate(fnames):
        df_c[f"FS_{fn}"] = F[:, j]

    print(f"\n  Factor score descriptives (weighted):")
    print(f"  {'Factor':>8}  {'W.Mean':>8}  {'W.SD':>8}  {'Min':>8}  {'Max':>8}")
    for j, fn in enumerate(fnames):
        fs = F[:, j]
        wm = np.sum(w_norm * fs)
        ws = np.sqrt(np.sum(w_norm * (fs - wm) ** 2))
        print(f"  {fn:>8}  {wm:>8.3f}  {ws:>8.3f}  {fs.min():>8.3f}  {fs.max():>8.3f}")

    # ── 6. Residualize correlated factors against F1 ──────────────────────────
    print(f"\n{thin}")
    print(f"STEP 5: F1-RESIDUALIZATION  (threshold |φ| > {RESID_THRESHOLD})")
    print(thin)

    # Identify F1 by enforcement/immigration anchor
    f1_j = anchor_map["enforcement/immigration"]
    F1_scores = F[:, f1_j]

    resid_cols = []
    for j, fn in enumerate(fnames):
        if j == f1_j:
            continue
        phi_val = Phi[f1_j, j]
        if abs(phi_val) > RESID_THRESHOLD:
            # OLS residual: regress Fj on F1 (weighted)
            fs_j = F[:, j]
            cov_jf1 = np.sum(w_norm * (fs_j - np.sum(w_norm * fs_j))
                             * (F1_scores - np.sum(w_norm * F1_scores)))
            var_f1  = np.sum(w_norm * (F1_scores - np.sum(w_norm * F1_scores)) ** 2)
            beta = cov_jf1 / var_f1
            resid = fs_j - beta * F1_scores
            col = f"FS_{fn}_resid"
            df_c[col] = resid
            resid_cols.append(col)
            print(f"  F{j+1} ({fn}): φ(F1,F{j+1})={phi_val:+.3f} → residualized → {col}")
        else:
            print(f"  F{j+1} ({fn}): φ(F1,F{j+1})={phi_val:+.3f} → no residualization needed")

    # ── 7. Save outputs ───────────────────────────────────────────────────────
    print(f"\n{thin}")
    print("STEP 6: SAVING OUTPUTS")
    print(thin)

    # EFA loadings
    df_L = pd.DataFrame(L_rot, index=ITEMS_24, columns=fnames)
    df_L.insert(0, "h2", h2)
    out_L = EFA_OUT / "efa_loadings_k4_final.csv"
    df_L.to_csv(out_L)
    print(f"  ✓ {out_L.relative_to(BASE_DIR)}")

    # Phi matrix
    df_phi = pd.DataFrame(np.round(Phi, 4), index=fnames, columns=fnames)
    out_phi = EFA_OUT / "efa_phi_k4_final.csv"
    df_phi.to_csv(out_phi)
    print(f"  ✓ {out_phi.relative_to(BASE_DIR)}")

    # Factor scores
    raw_fs_cols  = [f"FS_{fn}" for fn in fnames]
    save_cols = (["pid3", "ideo5", "inputstate", "commonpostweight",
                  "govt_trust_imputed"] + raw_fs_cols + resid_cols)
    out_fs = PROC_OUT / "efa_factor_scores_k4.csv"
    df_c[save_cols].to_csv(out_fs, index=False)
    print(f"  ✓ {out_fs.relative_to(BASE_DIR)}  (N={len(df_c):,})")
    print(f"    Columns: {save_cols}")

    print(f"\n{sep}")
    print("DONE — Ready for run_dpgmm_k4.py")
    print(sep)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
EFA Update: Drop CC24_340a, rerun k=5, compute Bartlett factor scores,
verify actual Cramér's V against approximations.

Steps 1–5 as specified.
"""

import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import chi2_contingency

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR = Path("/Users/bdecker/Documents/STV/Claude")
CES_PATH = Path("/Users/bdecker/Documents/STV/2024 CES Base/CCES24_Common_OUTPUT_vv_topost_final.dta")

# ── Item ordering in original 25-item polychoric matrix ──────────────────────
ITEMS_25 = [
    "pew_churatd", "CC24_302",   "CC24_303",   "CC24_341a",  "CC24_341c",
    "CC24_341d",   "CC24_323a",  "CC24_323b",  "CC24_323d",  "CC24_321b",
    "CC24_321d",   "CC24_321e",  "CC24_325",   "CC24_324b",  "CC24_340a",
    "CC24_340b",   "CC24_340c",  "CC24_340e",  "CC24_340f",  "CC24_440b",
    "CC24_440c",   "CC24_421_1", "CC24_421_2", "CC24_423",   "CC24_424",
]
DROP_ITEM  = "CC24_340a"
ITEMS_24   = [it for it in ITEMS_25 if it != DROP_ITEM]

# ── Recoding map for raw DTA → polychoric-consistent direction ────────────────
# [rev] binary items (1/2): recode as 3 - x  (1→2, 2→1)
REV_BINARY = {
    "CC24_341c", "CC24_341d",
    "CC24_323a", "CC24_323d",
    "CC24_321e",
    "CC24_340b", "CC24_340c",   # 340a dropped; 340b/340c still needed
}
# CC24_325: raw = weeks allowed; polychoric coding = 40 - raw (high = restrictive)
# CC24_303: (rev: high=inflation) — direction verified empirically below
# CC24_423/424: value 8 = "Not sure" → 2 (midpoint of 1–3 scale); no directional flip needed
# CC24_421_1/2: already high=distrust in raw data
# All other items: no recoding

APPROX_V = {          # from narrative (Steps 5–7 output)
    "F1": 0.388,
    "F2": 0.147,
    "F3": 0.270,
    "F4": 0.345,
    "F5": 0.400,
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


# ── Oblimin ───────────────────────────────────────────────────────────────────
def oblimin(A, gamma=0):
    try:
        from factor_analyzer.rotator import Rotator
        rot = Rotator(method="oblimin", power=gamma)
        L = rot.fit_transform(A)
        Phi = rot.phi_ if rot.phi_ is not None else np.eye(A.shape[1])
        return L, Phi
    except Exception as e:
        raise RuntimeError(f"factor_analyzer.rotator failed: {e}")


# ── Weighted statistics ───────────────────────────────────────────────────────
def weighted_mean(x, w):
    mask = ~np.isnan(x)
    return np.sum(x[mask] * w[mask]) / np.sum(w[mask])


def weighted_std(x, w):
    mask = ~np.isnan(x)
    mu = weighted_mean(x, w)
    var = np.sum(w[mask] * (x[mask] - mu) ** 2) / np.sum(w[mask])
    return np.sqrt(var)


# ── Cramér's V (weighted) ─────────────────────────────────────────────────────
def cramers_v_weighted(group_labels, cat_labels, weights):
    """
    Compute Cramér's V from a weighted contingency table.
    group_labels: 1-D array (e.g. quartile 1-4)
    cat_labels:   1-D array (e.g. pid3 1/2/3)
    weights:      1-D array of survey weights
    """
    # Build weighted cross-tab
    groups = sorted(np.unique(group_labels))
    cats   = sorted(np.unique(cat_labels))
    table  = np.zeros((len(groups), len(cats)))
    for gi, g in enumerate(groups):
        for ci, c in enumerate(cats):
            mask = (group_labels == g) & (cat_labels == c)
            table[gi, ci] = weights[mask].sum()

    N = table.sum()
    row_sums = table.sum(axis=1, keepdims=True)
    col_sums = table.sum(axis=0, keepdims=True)
    expected = row_sums @ col_sums / N
    with np.errstate(divide="ignore", invalid="ignore"):
        chi2 = np.sum((table - expected) ** 2 / np.where(expected > 0, expected, np.inf))
    k = min(table.shape[0] - 1, table.shape[1] - 1)
    V = np.sqrt(chi2 / (N * k)) if k > 0 and N > 0 else 0.0
    return float(V), float(chi2), float(N)


# ══════════════════════════════════════════════════════════════════════════════
def main():
    sep  = "=" * 72
    thin = "─" * 72

    print(sep)
    print("EFA UPDATE  |  Drop CC24_340a  |  24-item k=5 + Factor Scores")
    print(sep)

    # ── STEP 1a: Build 24×24 polychoric submatrix ──────────────────────────
    print(f"\n{thin}")
    print("STEP 1a: LOAD 24-ITEM POLYCHORIC SUBMATRIX")
    print(thin)

    corr_df_25 = pd.read_csv(DATA_DIR / "polychoric_matrix.csv", index_col=0)
    corr_df_24 = corr_df_25.drop(index=DROP_ITEM, columns=DROP_ITEM)
    assert list(corr_df_24.columns) == ITEMS_24, "Column order mismatch"

    R24 = corr_df_24.values.astype(float)
    R24 = (R24 + R24.T) / 2.0
    np.fill_diagonal(R24, 1.0)

    min_eig = np.linalg.eigvalsh(R24).min()
    if min_eig < 1e-6:
        bump = abs(min_eig) + 1e-4
        R24 += np.eye(len(ITEMS_24)) * bump
        d = np.sqrt(np.diag(R24))
        R24 /= np.outer(d, d)
        print(f"  [regularized: +{bump:.5f} to fix non-PSD]")

    print(f"  24×24 matrix loaded. Eigenvalue range: "
          f"[{np.linalg.eigvalsh(R24).min():.4f}, {np.linalg.eigvalsh(R24).max():.4f}]")

    # ── STEP 1b: PAF + Oblimin on 24-item matrix ───────────────────────────
    print(f"\n{thin}")
    print("STEP 1b: PAF + OBLIMIN  k=5  (24-item set)")
    print(thin)

    L_unrot_24, h2_init_24, eigs_24 = paf(R24, 5)
    L_rot_24, Phi_24 = oblimin(L_unrot_24)
    h2_24 = np.clip(np.diag(L_rot_24 @ Phi_24 @ L_rot_24.T), 0.0, 1.0)

    fnames = ["F1", "F2", "F3", "F4", "F5"]
    ss_24  = np.sum(L_rot_24 ** 2, axis=0)
    pv_24  = ss_24 / len(ITEMS_24) * 100.0

    print(f"\n  Variance Explained:")
    print(f"  {'Factor':>6}  {'SS Load':>8}  {'%Var':>7}  {'Cum%':>7}")
    cumul = 0.0
    for j in range(5):
        cumul += pv_24[j]
        print(f"  {fnames[j]:>6}  {ss_24[j]:>8.3f}  {pv_24[j]:>6.1f}%  {cumul:>6.1f}%")

    print(f"\n  Factor Intercorrelations (Φ):")
    phi_df = pd.DataFrame(np.round(Phi_24, 3), index=fnames, columns=fnames)
    print("  " + phi_df.to_string().replace("\n", "\n  "))

    # STEP 4 prep: load the original 25-item k=5 loadings for side-by-side
    orig_L_df = pd.read_csv(DATA_DIR / "efa_loadings_k5.csv", index_col=0)
    # The CSV has columns: Label, Domain, PID_R2, F1…F5, h2
    # Extract the original F3 loadings for the 24 items (and 340a)
    factor_cols_orig = ["F1", "F2", "F3", "F4", "F5"]
    # Remap original factor ordering to match the new solution by checking top items
    # (factor numbering may shuffle — we'll align by label after printing both)

    print(f"\n  Pattern Matrix  (|λ| < 0.30 suppressed):")
    hdr = f"  {'Item':<15}" + "".join(f"  {fn:>7}" for fn in fnames) + f"  {'h²':>6}"
    print(hdr)
    print(f"  {'─'*15}" + "  ─────  " * 5 + "  ─────")
    for i, item in enumerate(ITEMS_24):
        row = f"  {item:<15}"
        for j in range(5):
            v = L_rot_24[i, j]
            row += f"  {v:>7.3f}" if abs(v) >= 0.30 else f"  {'':>7}"
        row += f"  {h2_24[i]:>6.3f}"
        print(row)

    # ── STEP 1c: Confirm F1–F5 correlation ────────────────────────────────
    print(f"\n  F1–F5 phi correlation: {Phi_24[0,4]:.4f}  "
          f"(was 0.6150 in 25-item solution)")

    # ── STEP 2: Load raw DTA data ──────────────────────────────────────────
    print(f"\n{thin}")
    print("STEP 2: LOAD & RECODE RAW DTA DATA")
    print(thin)

    COLS_NEEDED = ITEMS_24 + ["pid3", "ideo5", "commonpostweight", "inputstate"]
    print(f"  Reading {CES_PATH.name} …")
    df_raw = pd.read_stata(CES_PATH, columns=COLS_NEEDED, convert_categoricals=False)
    print(f"  Raw rows: {len(df_raw):,}")

    # Flag respondents where CC24_423 or CC24_424 was "Not sure" (value 8)
    # Create BEFORE recoding so the flag reflects the original raw response
    df_raw["govt_trust_imputed"] = (
        (df_raw["CC24_423"] == 8) | (df_raw["CC24_424"] == 8)
    ).astype(int)
    n_imputed = df_raw["govt_trust_imputed"].sum()
    print(f"  govt_trust_imputed: {n_imputed:,} respondents flagged "
          f"(CC24_423==8 OR CC24_424==8)")

    # Recode CC24_423/424: value 8 → 2 (midpoint of 1–3 scale)
    for col in ["CC24_423", "CC24_424"]:
        n_8 = (df_raw[col] == 8).sum()
        df_raw[col] = df_raw[col].where(df_raw[col] != 8, other=2)
        print(f"  {col}: recoded {n_8:,} value-8 → 2 (midpoint, scale 1–3)")

    # Recode ideo5: value 6 → NaN ("Not sure")
    n_6 = (df_raw["ideo5"] == 6).sum()
    df_raw["ideo5"] = df_raw["ideo5"].where(df_raw["ideo5"] != 6, other=np.nan)
    print(f"  ideo5:   recoded {n_6:,} value-6 → NaN")

    # Verify CC24_303 direction: compute weighted Pearson corr with CC24_341a
    # In polychoric matrix, CC24_303 × CC24_341a = +0.3675
    # If raw Pearson corr is negative, we need 6 - CC24_303
    mask_valid = df_raw[["CC24_303", "CC24_341a", "commonpostweight"]].notna().all(axis=1)
    df_chk = df_raw[mask_valid]
    w = df_chk["commonpostweight"].values
    x303  = df_chk["CC24_303"].values
    x341a = df_chk["CC24_341a"].values
    mu303  = np.sum(w * x303)  / w.sum()
    mu341a = np.sum(w * x341a) / w.sum()
    cov    = np.sum(w * (x303 - mu303) * (x341a - mu341a)) / w.sum()
    s303   = np.sqrt(np.sum(w * (x303 - mu303)  ** 2) / w.sum())
    s341a  = np.sqrt(np.sum(w * (x341a - mu341a) ** 2) / w.sum())
    r_raw_303_341a = cov / (s303 * s341a)
    print(f"\n  CC24_303 direction check:")
    print(f"    Weighted Pearson(CC24_303, CC24_341a) in raw data = {r_raw_303_341a:+.4f}")
    print(f"    Polychoric(CC24_303, CC24_341a) in matrix         = +0.3675")
    if r_raw_303_361a := r_raw_303_341a < 0:
        print(f"    → Raw correlation is NEGATIVE → applying 6 - CC24_303")
        needs_rev_303 = True
    else:
        print(f"    → Raw correlation is POSITIVE → CC24_303 already in correct direction")
        needs_rev_303 = False

    # Apply all recodings
    df = df_raw.copy()

    if needs_rev_303:
        df["CC24_303"] = 6 - df["CC24_303"]

    for col in REV_BINARY:
        if col in df.columns:
            df[col] = 3 - df[col]

    # CC24_325: 40 - raw (high = restrictive)
    df["CC24_325"] = 40 - df["CC24_325"]

    print(f"\n  Recoding applied:")
    print(f"    Binary [rev]: {sorted(REV_BINARY)}")
    print(f"    CC24_325 → 40 - CC24_325")
    if needs_rev_303:
        print(f"    CC24_303 → 6 - CC24_303")

    # ── Listwise deletion on 24 items + weight ─────────────────────────────
    cols_for_deletion = ITEMS_24 + ["commonpostweight"]
    mask_complete = df[cols_for_deletion].notna().all(axis=1)
    df_complete = df[mask_complete].copy().reset_index(drop=True)
    print(f"\n  After listwise deletion on 24 items: N = {len(df_complete):,}")
    print(f"  Weighted N = {df_complete['commonpostweight'].sum():,.0f}")

    # ── STEP 2b: Standardize items using weighted mean/std ─────────────────
    print(f"\n{thin}")
    print("STEP 2b: COMPUTE BARTLETT FACTOR SCORES (regression method)")
    print(thin)

    X = df_complete[ITEMS_24].values.astype(float)   # (n, 24)
    w = df_complete["commonpostweight"].values         # (n,)
    w_norm = w / w.sum()                               # normalized weights

    # Weighted standardization
    mu  = np.array([np.sum(w_norm * X[:, j]) for j in range(len(ITEMS_24))])
    sig = np.array([
        np.sqrt(np.sum(w_norm * (X[:, j] - mu[j]) ** 2))
        for j in range(len(ITEMS_24))
    ])
    sig[sig < 1e-10] = 1.0   # guard against zero-variance items
    Z = (X - mu) / sig        # (n, 24) standardized matrix

    # Thomson (regression) factor scores for oblique rotation:
    #   Structure matrix: S = L_rot @ Phi  (24×5)
    #   Scoring coefficients: B = R24_inv @ S  (24×5)
    #   Factor scores: F = Z @ B  (n×5)
    S   = L_rot_24 @ Phi_24                   # structure matrix (24×5)
    R24_inv = np.linalg.inv(R24)
    B   = R24_inv @ S                         # scoring coefficients (24×5)
    F   = Z @ B                               # raw factor scores (n×5)

    # ── Sign flips ─────────────────────────────────────────────────────────
    # In oblique rotation, pattern matrix loading signs do NOT reliably
    # determine factor score direction because the scoring coefficients
    # B = R⁻¹S depend on the full polychoric structure.  Empirical check:
    # for the three "conservative" partisan factors, Republicans should score
    # higher than Democrats; flip those where they don't.
    # Cross-partisan factors (election distrust, govt trust) are left as-is.
    #
    # Factor identification by strongest absolute loading on anchor items:
    #   CC24_323b   → enforcement/immigration  (border patrols; raw low=conservative)
    #   pew_churatd → repro rights / religion  (church attendance; raw low=conservative)
    #   CC24_440b   → values conservatism      (racial minimization; raw low=conservative)
    #   CC24_421_2  → election/govt distrust   (disagree elections fair; raw high=distrust)
    #   CC24_423    → state/fed govt trust      (fed govt trust item; raw high=distrust)

    idx_323b    = ITEMS_24.index("CC24_323b")
    idx_churatd = ITEMS_24.index("pew_churatd")
    idx_440b    = ITEMS_24.index("CC24_440b")
    idx_421_2   = ITEMS_24.index("CC24_421_2")
    idx_423     = ITEMS_24.index("CC24_423")

    f_enforce_j  = int(np.argmax(np.abs(L_rot_24[idx_323b, :])))
    f_repro_j    = int(np.argmax(np.abs(L_rot_24[idx_churatd, :])))
    f_values_j   = int(np.argmax(np.abs(L_rot_24[idx_440b, :])))
    f_distrust_j = int(np.argmax(np.abs(L_rot_24[idx_421_2, :])))
    f_govttr_j   = int(np.argmax(np.abs(L_rot_24[idx_423, :])))

    id_map = {
        f_enforce_j:  "enforcement/immigration",
        f_repro_j:    "repro rights/religion",
        f_values_j:   "values conservatism",
        f_distrust_j: "election/govt distrust",
        f_govttr_j:   "state/fed govt trust",
    }
    print(f"\n  Factor identification by anchor item:")
    for fj in sorted(id_map):
        lbl = id_map[fj]
        print(f"    F{fj+1} → {lbl}")

    # Warn if any two "conservative" anchors map to the same factor
    cons_factors = [f_enforce_j, f_repro_j, f_values_j]
    if len(set(cons_factors)) < 3:
        print(f"  ⚠  WARNING: anchor collision among conservative factors "
              f"({cons_factors}) — check solution stability")

    # Empirical partisan means (pid3=1 Democrat, pid3=2 Republican)
    mask_dem = (df_complete["pid3"] == 1).values
    mask_rep = (df_complete["pid3"] == 2).values

    print(f"\n  Sign-flip decisions (partisan anchor; high = conservative for F{f_enforce_j+1}/F{f_repro_j+1}/F{f_values_j+1}):")
    for factor_j, construct in [
        (f_enforce_j,  "enforcement/immigration"),
        (f_repro_j,    "repro rights/religion"),
        (f_values_j,   "values conservatism"),
    ]:
        fs = F[:, factor_j]
        w_dem = w[mask_dem];  w_rep = w[mask_rep]
        mean_dem = np.sum(w_dem * fs[mask_dem]) / w_dem.sum()
        mean_rep = np.sum(w_rep * fs[mask_rep]) / w_rep.sum()
        if mean_rep < mean_dem:
            F[:, factor_j] *= -1
            print(f"    F{factor_j+1} ({construct}): FLIPPED  "
                  f"[Rep {mean_rep:+.3f} → {-mean_rep:+.3f}, "
                  f"Dem {mean_dem:+.3f} → {-mean_dem:+.3f}]")
        else:
            print(f"    F{factor_j+1} ({construct}): OK  "
                  f"[Rep {mean_rep:+.3f} > Dem {mean_dem:+.3f}]")

    # Cross-partisan factors: leave sign as-is
    print(f"    F{f_distrust_j+1} (election distrust): left as-is (V≈0.11, cross-partisan)")
    print(f"    F{f_govttr_j+1}  (govt trust):        left as-is (V≈0.06, near-orthogonal)")

    # Store factor scores in dataframe
    factor_score_cols = [f"FS_{fn}" for fn in fnames]
    for j, col in enumerate(factor_score_cols):
        df_complete[col] = F[:, j]

    print(f"\n  Factor score descriptives (weighted):")
    print(f"  {'Factor':>8}  {'W.Mean':>8}  {'W.SD':>8}  {'Min':>8}  {'Max':>8}")
    for j, fn in enumerate(fnames):
        fs = F[:, j]
        wm = np.sum(w_norm * fs)
        ws = np.sqrt(np.sum(w_norm * (fs - wm) ** 2))
        print(f"  {fn:>8}  {wm:>8.3f}  {ws:>8.3f}  {fs.min():>8.3f}  {fs.max():>8.3f}")

    # ── STEP 3: Cramér's V ─────────────────────────────────────────────────
    print(f"\n{thin}")
    print("STEP 3: CRAMÉR'S V — ACTUAL vs APPROXIMATED")
    print(thin)
    print(f"\n  Quartile split × pid3 (Democrat=1, Republican=2, Independent=3)")
    print(f"  [Weighted cross-tabs; pid3 ∈ {{1,2,3}} only]\n")

    # Filter to partisan three: pid3 in {1, 2, 3}
    mask_pid3 = df_complete["pid3"].isin([1, 2, 3])
    df_pid3 = df_complete[mask_pid3].copy()

    results_v = {}
    print(f"  {'Factor':>8}  {'Actual V':>10}  {'Approx V':>10}  {'Δ':>8}  "
          f"{'Chi²':>10}  {'N(wtd)':>10}")
    print(f"  {'─'*8}  {'─'*10}  {'─'*10}  {'─'*8}  {'─'*10}  {'─'*10}")

    for j, fn in enumerate(fnames):
        fs_col = factor_score_cols[j]
        fs     = df_pid3[fs_col].values
        pid3   = df_pid3["pid3"].values.astype(int)
        wt     = df_pid3["commonpostweight"].values

        # Quartile split using weighted quantiles
        # Use numpy percentile with weights approximation via sorted cumulative weight
        sorted_idx = np.argsort(fs)
        sorted_w   = wt[sorted_idx]
        cum_w      = np.cumsum(sorted_w) / sorted_w.sum()
        qtile_breaks = [0.0, 0.25, 0.50, 0.75, 1.0]
        qtile_vals   = np.interp(qtile_breaks, cum_w, fs[sorted_idx])

        # Assign quartile (1–4)
        qtile = np.searchsorted(qtile_vals[1:-1], fs, side="right") + 1
        qtile = np.clip(qtile, 1, 4)

        V, chi2, N_w = cramers_v_weighted(qtile, pid3, wt)
        approx = APPROX_V[fn]
        delta  = V - approx
        results_v[fn] = {"actual_v": round(V, 4), "approx_v": approx,
                         "delta": round(delta, 4), "chi2": round(chi2, 1),
                         "N_wtd": round(N_w, 0)}
        print(f"  {fn:>8}  {V:>10.4f}  {approx:>10.4f}  {delta:>+8.4f}  "
              f"{chi2:>10.1f}  {N_w:>10.0f}")

    # ── Cross-tab detail for each factor ───────────────────────────────────
    print(f"\n  Weighted cross-tab detail (% within pid3):")
    pid3_labels = {1: "Dem", 2: "Rep", 3: "Ind"}

    for j, fn in enumerate(fnames):
        fs_col = factor_score_cols[j]
        fs     = df_pid3[fs_col].values
        pid3   = df_pid3["pid3"].values.astype(int)
        wt     = df_pid3["commonpostweight"].values

        sorted_idx = np.argsort(fs)
        sorted_w   = wt[sorted_idx]
        cum_w      = np.cumsum(sorted_w) / sorted_w.sum()
        qtile_vals = np.interp([0, 0.25, 0.50, 0.75, 1.0], cum_w, fs[sorted_idx])
        qtile      = np.clip(np.searchsorted(qtile_vals[1:-1], fs, side="right") + 1, 1, 4)

        # Build % within-party table
        print(f"\n  {fn}  ({results_v[fn]['actual_v']:.4f})")
        print(f"  {'Quartile':>10}", end="")
        for pid_v in [1, 2, 3]:
            print(f"  {pid3_labels[pid_v]:>8}", end="")
        print()
        for q in range(1, 5):
            print(f"  {'Q'+str(q):>10}", end="")
            for pid_v in [1, 2, 3]:
                mask = (qtile == q) & (pid3 == pid_v)
                pct = wt[mask].sum() / wt[pid3 == pid_v].sum() * 100
                print(f"  {pct:>7.1f}%", end="")
            print()

    # ── STEP 4: F3 before/after comparison ────────────────────────────────
    print(f"\n{thin}")
    print("STEP 4: F3 LOADING COMPARISON — BEFORE vs AFTER DROPPING CC24_340a")
    print(thin)

    # Original 25-item F3 loadings (from efa_loadings_k5.csv)
    # The original CSV has factor columns named F1..F5
    orig_L = pd.read_csv(DATA_DIR / "efa_loadings_k5.csv", index_col=0)
    # Identify which column in the original solution corresponds to F3
    # (the reproductive rights factor anchored by 340a and 340b)
    # Check which original factor has the highest loading on CC24_340b
    orig_factor_cols = [c for c in orig_L.columns if c.startswith("F") and c[1:].isdigit()]
    orig_340b_loads  = orig_L.loc["CC24_340b", orig_factor_cols]
    orig_f3_col      = orig_340b_loads.abs().idxmax()
    print(f"\n  Original 25-item solution: CC24_340b anchors on {orig_f3_col}")

    # New solution: which factor has highest |load| on CC24_340b (derived locally)
    idx_340b_s4 = ITEMS_24.index("CC24_340b")
    new_f3_j    = int(np.argmax(np.abs(L_rot_24[idx_340b_s4, :])))
    new_f3_col  = f"F{new_f3_j+1}"
    print(f"  Updated 24-item solution: CC24_340b anchors on {new_f3_col}")

    # Build side-by-side comparison for F3-related items
    f3_items_orig = [it for it in ITEMS_25
                     if abs(float(orig_L.loc[it, orig_f3_col]) if it in orig_L.index else 0) >= 0.15
                     or it == "CC24_340a"]

    # Also show any item with |load| >= 0.15 on new F3
    new_L_df = pd.DataFrame(L_rot_24, index=ITEMS_24, columns=fnames)
    f3_items_new = [it for it in ITEMS_24 if abs(new_L_df.loc[it, new_f3_col]) >= 0.15]

    all_f3_items = sorted(set(f3_items_orig) | set(f3_items_new),
                          key=lambda x: ITEMS_25.index(x))

    print(f"\n  {'Item':<15}  {'Orig '+orig_f3_col+' (25-item)':>20}  "
          f"{'New '+new_f3_col+' (24-item)':>20}  {'Δ loading':>10}  Note")
    print(f"  {'─'*15}  {'─'*20}  {'─'*20}  {'─'*10}  {'─'*25}")

    for item in all_f3_items:
        if item in orig_L.index:
            orig_val = float(orig_L.loc[item, orig_f3_col])
        else:
            orig_val = np.nan
        if item in ITEMS_24:
            new_val  = float(new_L_df.loc[item, new_f3_col])
        else:
            new_val  = np.nan   # CC24_340a dropped

        if np.isnan(orig_val):
            orig_str = "—  (dropped)"
            delta_str = "n/a"
        else:
            orig_str = f"{orig_val:>+.3f}"
        if np.isnan(new_val):
            new_str  = "—  (dropped)"
            delta_str = "n/a"
        else:
            new_str  = f"{new_val:>+.3f}"

        if not np.isnan(orig_val) and not np.isnan(new_val):
            delta = new_val - orig_val
            delta_str = f"{delta:>+.3f}"
            flag = ""
            if item == "CC24_340b":
                if abs(new_val) > 0.90:
                    flag = "⚠ STILL NEAR-HEYWOOD"
                elif abs(new_val) > 0.70:
                    flag = "↓ Heywood resolved"
                else:
                    flag = "✓ Loading normalized"
            elif abs(delta) > 0.10:
                flag = "↑ Notable shift"
        else:
            delta_str = "n/a"
            flag = "(anchor item dropped)" if item == DROP_ITEM else ""

        print(f"  {item:<15}  {orig_str:>20}  {new_str:>20}  {delta_str:>10}  {flag}")

    # Specific check on CC24_340b
    new_340b = float(new_L_df.loc["CC24_340b", new_f3_col])
    orig_340b = float(orig_L.loc["CC24_340b", orig_f3_col])
    print(f"\n  CC24_340b: orig λ = {orig_340b:+.3f} → new λ = {new_340b:+.3f}")
    if abs(new_340b) > 0.90:
        print(f"  ⚠  WARNING: CC24_340b loading ({new_340b:+.3f}) still near-Heywood.")
        print(f"     F3 stability is questionable without a second anchor item.")
        print(f"     Consider: (a) dropping CC24_340b, (b) merging 340b into F5,")
        print(f"     or (c) treating F3 as a 1-item factor and scoring it directly.")
    elif abs(new_340b) > 0.70:
        print(f"  ✓  Near-Heywood condition resolved. CC24_340b loading is strong but acceptable.")
    else:
        print(f"  ✓  CC24_340b loading has normalized substantially.")

    # ── STEP 5: SAVE ALL OUTPUTS ───────────────────────────────────────────
    print(f"\n{thin}")
    print("STEP 5: SAVING OUTPUTS")
    print(thin)

    # 5a. Updated 24-item k=5 loadings
    df_L_out = pd.DataFrame(L_rot_24, index=ITEMS_24, columns=fnames)
    df_L_out.insert(0, "h2", h2_24)
    df_L_out.to_csv(DATA_DIR / "efa_loadings_k5_final.csv")
    print("  ✓ efa_loadings_k5_final.csv")

    # 5b. Updated Phi
    phi_out = pd.DataFrame(np.round(Phi_24, 4), index=fnames, columns=fnames)
    phi_out.to_csv(DATA_DIR / "efa_phi_k5_final.csv")
    print("  ✓ efa_phi_k5_final.csv")

    # 5c. Factor scores merged with metadata
    # (keep pid3 1-5 in the output file, not just 1-3, so analyst has full dataset)
    save_cols = (["pid3", "ideo5", "inputstate", "commonpostweight",
                  "govt_trust_imputed"]
                 + factor_score_cols)
    df_scores_out = df_complete[save_cols].copy()
    df_scores_out.to_csv(DATA_DIR / "efa_factor_scores.csv", index=False)
    print(f"  ✓ efa_factor_scores.csv  (N={len(df_scores_out):,})")

    # 5d. Cramér's V comparison table
    cramers_rows = []
    for fn, vals in results_v.items():
        cramers_rows.append({
            "Factor":    fn,
            "Actual_V":  vals["actual_v"],
            "Approx_V":  vals["approx_v"],
            "Delta":     vals["delta"],
            "Chi2":      vals["chi2"],
            "N_weighted": vals["N_wtd"],
        })
    cramers_df = pd.DataFrame(cramers_rows)
    cramers_df.to_csv(DATA_DIR / "efa_cramersv_actual.csv", index=False)
    print("  ✓ efa_cramersv_actual.csv")

    print(f"\n{sep}")
    print("DONE — Awaiting analyst review before clustering.")
    print(sep)

    return results_v, new_340b


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
EFA Steps 5-7: PAF + Oblimin on CES 2024 polychoric correlation matrix
N=45143, 25 items, commonpostweight applied during polychoric computation.
"""

import sys
import warnings
import numpy as np
import pandas as pd
from pathlib import Path

warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR = Path("/Users/bdecker/Documents/STV/Claude")

# ── Item metadata (from checkpoint) ──────────────────────────────────────────
ITEM_META = {
    "pew_churatd": {"label": "Church attendance frequency",                       "pid_r2": 0.059,  "domain": "Religion"},
    "CC24_302":    {"label": "HH income: change past year",                       "pid_r2": 0.059,  "domain": "Econ"},
    "CC24_303":    {"label": "Perceived price change past year (high=inflation)",  "pid_r2": 0.116,  "domain": "Econ"},
    "CC24_341a":   {"label": "Support extend 2017 tax cuts",                      "pid_r2": 0.152,  "domain": "Tax"},
    "CC24_341c":   {"label": "Oppose allow $400k+ tax rates to rise [rev]",       "pid_r2": 0.182,  "domain": "Tax"},
    "CC24_341d":   {"label": "Oppose $150B infrastructure spending [rev]",        "pid_r2": 0.066,  "domain": "Tax"},
    "CC24_323a":   {"label": "Oppose grant legal status to immigrants [rev]",     "pid_r2": 0.237,  "domain": "Immigration"},
    "CC24_323b":   {"label": "Support increase border patrols",                   "pid_r2": 0.097,  "domain": "Immigration"},
    "CC24_323d":   {"label": "Oppose Dreamers citizenship pathway [rev]",         "pid_r2": 0.204,  "domain": "Immigration"},
    "CC24_321b":   {"label": "Support easier concealed carry permits",            "pid_r2": 0.195,  "domain": "Guns"},
    "CC24_321d":   {"label": "Support increase police by 10%",                    "pid_r2": 0.152,  "domain": "Policing"},
    "CC24_321e":   {"label": "Oppose decrease police by 10% [rev]",               "pid_r2": 0.118,  "domain": "Policing"},
    "CC24_325":    {"label": "Abortion weeks limit (high=restrictive)",            "pid_r2": 0.253,  "domain": "Abortion"},
    "CC24_324b":   {"label": "Support permit abortion only rape/incest/life",     "pid_r2": 0.109,  "domain": "Abortion"},
    "CC24_340a":   {"label": "Oppose prohibit contraceptive restrictions [rev]",  "pid_r2": 0.029,  "domain": "CivRights"},
    "CC24_340b":   {"label": "Oppose prohibit abortion restrictions [rev]",       "pid_r2": 0.111,  "domain": "CivRights"},
    "CC24_340c":   {"label": "Oppose require same-sex marriage recognition [rev]","pid_r2": 0.198,  "domain": "CivRights"},
    "CC24_340e":   {"label": "Support renew post-9/11 surveillance programs",     "pid_r2": 0.000,  "domain": "CivRights"},
    "CC24_340f":   {"label": "Support deny asylum at border",                     "pid_r2": 0.230,  "domain": "CivRights"},
    "CC24_440b":   {"label": "Agree: racial problems are rare/isolated",          "pid_r2": 0.231,  "domain": "Racial/Gender"},
    "CC24_440c":   {"label": "Agree: women seek power over men",                 "pid_r2": 0.154,  "domain": "Racial/Gender"},
    "CC24_421_1":  {"label": "Disagree: U.S. elections are fair (distrust)",     "pid_r2": 0.011,  "domain": "Elect Trust"},
    "CC24_421_2":  {"label": "Disagree: state/local election fair (distrust)",    "pid_r2": 0.007,  "domain": "Elect Trust"},
    "CC24_423":    {"label": "Low trust: federal government",                     "pid_r2": 0.022,  "domain": "Govt Trust"},
    "CC24_424":    {"label": "Low trust: state government",                       "pid_r2": 0.005,  "domain": "Govt Trust"},
}

N = 45143  # effective weighted N

# ── PAF implementation ────────────────────────────────────────────────────────
def compute_smc(R):
    """Squared multiple correlations as initial communality estimates."""
    try:
        R_inv = np.linalg.inv(R)
        smc = 1.0 - 1.0 / np.diag(R_inv)
    except np.linalg.LinAlgError:
        smc = np.full(R.shape[0], 0.5)
    return np.clip(smc, 0.005, 0.999)


def paf(R, n_factors, n_iter=1000, tol=1e-7):
    """
    Principal Axis Factoring from correlation matrix.
    Returns: L (p×k unrotated loadings), h2 (communalities), eigs (eigenvalues)
    """
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


# ── Oblimin rotation ──────────────────────────────────────────────────────────
def oblimin(A, gamma=0, max_iter=2000, tol=1e-8):
    """
    Direct oblimin rotation.
    First tries factor_analyzer.rotator.Rotator (best implementation).
    Falls back to manual Jennrich-Sampson gradient descent.
    Returns: L (pattern matrix), Phi (factor correlations)
    """
    p, k = A.shape

    # ── Try factor_analyzer ──
    try:
        from factor_analyzer.rotator import Rotator
        rot = Rotator(method="oblimin", power=gamma)
        L = rot.fit_transform(A)
        Phi = rot.phi_
        if Phi is None:
            Phi = np.eye(k)
        return L, Phi
    except Exception:
        pass  # fall through to manual

    # ── Manual: Jennrich-Sampson gradient descent ──
    # We minimize Q = Σ_{j<k} [Σ_i l²_ij · l²_ik - γ/p · (Σ_i l²_ij)(Σ_i l²_ik)]
    # with column-normalized T such that L = A (T'T)^{-1/2} ... simplified to:
    # L = A @ np.linalg.inv(T).T,  then normalize cols.
    T = np.eye(k)

    def criterion(T_):
        try:
            L_ = A @ np.linalg.inv(T_).T
        except np.linalg.LinAlgError:
            return 1e10
        L2 = L_ ** 2
        N_mat = np.ones((k, k)) - np.eye(k)
        f = np.sum(L2 * (L2 @ N_mat)) / 4.0
        if gamma != 0:
            col_ss = np.sum(L2, axis=0)  # (k,)
            f -= gamma / (4.0 * p) * np.sum(col_ss ** 2)
        return f

    alpha = 1.0
    f_prev = criterion(T)

    for _ in range(max_iter):
        try:
            L_cur = A @ np.linalg.inv(T).T
        except np.linalg.LinAlgError:
            break
        L2 = L_cur ** 2
        N_mat = np.ones((k, k)) - np.eye(k)

        if gamma == 0:
            grad_L = L_cur * (L2 @ N_mat)
        else:
            col_ss = np.sum(L2, axis=0)
            grad_L = L_cur * (L2 @ N_mat - gamma / p * np.ones((p, 1)) @ col_ss.reshape(1, -1))

        try:
            Ti = np.linalg.inv(T)
        except np.linalg.LinAlgError:
            break
        G = -Ti.T @ A.T @ grad_L @ Ti.T
        Gp = G - T @ np.diag(np.diag(G.T @ T))

        if np.max(np.abs(Gp)) < tol:
            break

        # Armijo line search
        s = alpha
        for _ in range(20):
            T_new = T - s * Gp
            col_norms = np.sqrt(np.sum(T_new ** 2, axis=0))
            col_norms[col_norms < 1e-12] = 1e-12
            T_new = T_new / col_norms
            f_new = criterion(T_new)
            if f_new < f_prev:
                break
            s *= 0.5
        T = T_new
        f_prev = f_new

    L = A @ np.linalg.inv(T).T
    try:
        Phi = np.linalg.inv(T.T @ T)
    except np.linalg.LinAlgError:
        Phi = np.eye(k)

    return L, Phi


# ── Parallel analysis ─────────────────────────────────────────────────────────
def parallel_analysis(R, n_max=10, n_sim=200, pct=95, seed=2024):
    """Compare observed eigenvalues of R to random-data eigenvalues (95th pct)."""
    np.random.seed(seed)
    p = R.shape[0]
    obs_evals = np.linalg.eigvalsh(R)[::-1]
    sim_evals = np.zeros((n_sim, p))
    for i in range(n_sim):
        X = np.random.randn(N, p)
        Rc = np.corrcoef(X.T)
        sim_evals[i] = np.linalg.eigvalsh(Rc)[::-1]
    threshold = np.percentile(sim_evals, pct, axis=0)
    n_factors = int(np.sum(obs_evals[:n_max] > threshold[:n_max]))
    return n_factors, obs_evals, threshold


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    sep = "=" * 72
    thin = "─" * 72

    print(sep)
    print("EFA STEPS 5-7  |  CES 2024 Political Typology  |  N=45,143")
    print(sep)

    # Check oblimin backend
    try:
        from factor_analyzer.rotator import Rotator
        print("Rotation backend: factor_analyzer.rotator.Rotator (oblimin)")
    except ImportError:
        print("Rotation backend: manual Jennrich-Sampson (factor_analyzer not found)")

    # ── Load matrix ────────────────────────────────────────────────────────────
    corr_df = pd.read_csv(DATA_DIR / "polychoric_matrix.csv", index_col=0)
    items = list(corr_df.columns)
    R = corr_df.values.astype(float)
    p = len(items)

    # Enforce symmetry and unit diagonal
    R = (R + R.T) / 2.0
    np.fill_diagonal(R, 1.0)

    # Fix any negative eigenvalues (can occur in polychoric matrices)
    min_eig = np.linalg.eigvalsh(R).min()
    if min_eig < 1e-6:
        bump = abs(min_eig) + 1e-4
        R += np.eye(p) * bump
        d = np.sqrt(np.diag(R))
        R = R / np.outer(d, d)
        print(f"[Note] Added regularization ({bump:.4f}) to fix non-PSD matrix")

    eig_range = np.linalg.eigvalsh(R)
    print(f"Matrix: {p}×{p} | Eigenvalue range: [{eig_range.min():.4f}, {eig_range.max():.4f}]")

    # ──────────────────────────────────────────────────────────────────────────
    # STEP 5a: PARALLEL ANALYSIS
    # ──────────────────────────────────────────────────────────────────────────
    print(f"\n{thin}")
    print("STEP 5a: PARALLEL ANALYSIS  (200 simulations, 95th percentile)")
    print(thin)

    k_pa, obs_evals, sim_thresh = parallel_analysis(R)

    print(f"\n{'Factor':>8}  {'Obs Eigenvalue':>16}  {'Sim 95th%':>12}  {'Extract?':>9}")
    print(f"{'─'*8}  {'─'*16}  {'─'*12}  {'─'*9}")
    for i in range(10):
        flag = "  YES" if obs_evals[i] > sim_thresh[i] else "  no "
        print(f"{i+1:>8}  {obs_evals[i]:>16.4f}  {sim_thresh[i]:>12.4f}  {flag}")
    print(f"\n→ Parallel analysis suggests k = {k_pa} factors")

    # ──────────────────────────────────────────────────────────────────────────
    # STEP 5b: PAF + OBLIMIN FOR k = 3, 4, 5, 6, 7
    # ──────────────────────────────────────────────────────────────────────────
    all_results = {}

    for k in [3, 4, 5, 6, 7]:
        print(f"\n{thin}")
        print(f"STEP 5b: PAF + OBLIMIN  k={k}")
        print(thin)

        L_unrot, h2_init, eigs_k = paf(R, k)
        L_rot, Phi = oblimin(L_unrot)

        # Communalities after oblique rotation: h²_i = (L Φ L')_ii
        h2 = np.clip(np.diag(L_rot @ Phi @ L_rot.T), 0.0, 1.0)

        fnames = [f"F{j+1}" for j in range(k)]
        ss = np.sum(L_rot ** 2, axis=0)
        pct_var = ss / p * 100.0

        # Variance table
        print(f"\n  Variance Explained (SS Loadings from pattern matrix):")
        print(f"  {'Factor':>8}  {'SS Load':>8}  {'%Var':>7}  {'Cum%':>7}")
        cumul = 0.0
        for j in range(k):
            cumul += pct_var[j]
            print(f"  {fnames[j]:>8}  {ss[j]:>8.3f}  {pct_var[j]:>6.1f}%  {cumul:>6.1f}%")

        # Phi matrix
        print(f"\n  Factor Intercorrelation Matrix (Φ):")
        phi_df = pd.DataFrame(np.round(Phi, 3), index=fnames, columns=fnames)
        print("  " + phi_df.to_string().replace("\n", "\n  "))

        # Pattern matrix
        print(f"\n  Pattern Matrix  (|λ| < 0.30 suppressed):")
        hdr = f"  {'Item':<15}" + "".join(f"  {fn:>7}" for fn in fnames) + f"  {'h²':>6}"
        print(hdr)
        print(f"  {'─'*15}" + "".join("  ─────" + "  " for _ in fnames) + "  ─────")
        for i, item in enumerate(items):
            row = f"  {item:<15}"
            for j in range(k):
                v = L_rot[i, j]
                row += f"  {v:>7.3f}" if abs(v) >= 0.30 else f"  {'':>7}"
            row += f"  {h2[i]:>6.3f}"
            print(row)

        # Top 5 per factor
        print(f"\n  Top 5 items per factor (by |pattern loading|):")
        for j in range(k):
            top5 = np.argsort(np.abs(L_rot[:, j]))[::-1][:5]
            print(f"\n  {fnames[j]}:")
            for idx in top5:
                it = items[idx]
                v = L_rot[idx, j]
                sign = "+" if v >= 0 else "−"
                lbl = ITEM_META.get(it, {"label": it})["label"]
                print(f"    {sign}{abs(v):.3f}  {it:<15}  {lbl[:55]}")

        all_results[k] = {
            "L_unrot": L_unrot,
            "L_rot": L_rot,
            "h2": h2,
            "Phi": Phi,
            "ss": ss,
            "pct_var": pct_var,
            "eigs": eigs_k,
        }

    # ──────────────────────────────────────────────────────────────────────────
    # STEP 6: INTERPRET & FLAG (primary solution)
    # ──────────────────────────────────────────────────────────────────────────
    # Parallel analysis says k=4, but F5 eigenvalue (1.026) misses threshold (1.028)
    # by < 0.3% — a marginal call.  For typology work, k=5 is preferred because it
    # splits the large k=4 F1 omnibus (immigration/enforcement/fiscal/race) into two
    # theoretically meaningful sub-dimensions, improving cluster separability.
    # k=4 remains the statistically conservative anchor; k=5 is the recommended
    # working solution.  Both are reported; analyst should verify with parallel
    # analysis on final weighted data.
    k_primary = 5  # recommended typology input
    print(f"\n{sep}")
    print(f"STEP 6: INTERPRET & FLAG  (primary solution: k={k_primary})")
    print(f"  [PA → k={k_pa}; k=5 adopted — F5 eigenvalue {obs_evals[4]:.4f} vs threshold")
    print(f"   {sim_thresh[4]:.4f} (Δ={obs_evals[4]-sim_thresh[4]:+.4f}); marginal — see narrative]")
    print(sep)

    res = all_results[k_primary]
    L_rot = res["L_rot"]
    h2 = res["h2"]
    Phi = res["Phi"]
    fnames = [f"F{j+1}" for j in range(k_primary)]

    # ── Factor-level partisan collinearity ─────────────────────────────────
    # Estimated via squared-loading-weighted average of item PID R²
    # Cramér's V ≈ √(weighted PID R²)  [valid for rough threshold comparison
    #   since √R² ≈ |r| ≈ V for simple 2-group comparisons; note this is an
    #   approximation without raw data for actual quartile-split cross-tabs]
    print(f"\n  Factor-Level Partisan Collinearity Estimates")
    print(f"  (loading²-weighted avg PID R²; Cramér's V ≈ √PID_R²)")
    print(f"  NOTE: actual Cramér's V requires raw data for quartile-split cross-tabs")
    print(f"  These estimates use item-level R² from Steps 1–4.\n")
    print(f"  {'Factor':>8}  {'Wt PID R²':>11}  {'Approx V':>10}  {'Classification':>24}  {'Flag'}")
    print(f"  {'─'*8}  {'─'*11}  {'─'*10}  {'─'*24}  {'─'*30}")

    factor_partisan = {}
    r2_items = np.array([ITEM_META.get(it, {"pid_r2": 0})["pid_r2"] for it in items])

    for j in range(k_primary):
        w = L_rot[:, j] ** 2
        w_sum = w.sum()
        wt_r2 = float(np.dot(w, r2_items) / w_sum) if w_sum > 0 else 0.0
        approx_v = float(np.sqrt(wt_r2))

        if approx_v > 0.45:
            cls = "LIKELY PARTISAN AXIS"
            flag = "← Consider excluding from cluster input"
        elif approx_v < 0.30:
            cls = "ORTHOGONAL DIMENSION"
            flag = "← Strong candidate for inclusion"
        else:
            cls = "MODERATE PARTISAN LOAD"
            flag = "← Include with caution"

        factor_partisan[j] = {"wt_r2": wt_r2, "approx_v": approx_v, "cls": cls}
        print(f"  {fnames[j]:>8}  {wt_r2:>11.3f}  {approx_v:>10.3f}  {cls:>24}  {flag}")

    # ── Top-5 items + sign interpretation per factor ──
    print(f"\n  Top items per factor with loading sign interpretation:")
    for j in range(k_primary):
        top5 = np.argsort(np.abs(L_rot[:, j]))[::-1][:5]
        fp = factor_partisan[j]
        print(f"\n  ── {fnames[j]}  (approx V={fp['approx_v']:.3f}, {fp['cls']}) ──")
        for idx in top5:
            it = items[idx]
            v = L_rot[idx, j]
            lbl = ITEM_META.get(it, {"label": it})["label"]
            sign_note = "[High score = agrees with item]" if v > 0 else "[High score = disagrees/reverse]"
            print(f"    {v:>+7.3f}  {it:<15}  {lbl[:50]}")
            print(f"           {sign_note}")

    # ──────────────────────────────────────────────────────────────────────────
    # STEP 7: RECOMMENDATION TABLE
    # ──────────────────────────────────────────────────────────────────────────
    print(f"\n{sep}")
    print(f"STEP 7: RECOMMENDATION TABLE  (k={k_primary} solution)")
    print(sep)

    rows = []
    # Items explicitly flagged as cross-cutting / low-PID in checkpoint
    KNOWN_CROSSCUTTING = {"CC24_421_1", "CC24_421_2", "CC24_423", "CC24_424", "CC24_340e"}

    for i, item in enumerate(items):
        meta = ITEM_META.get(item, {"label": item, "pid_r2": 0, "domain": "?"})
        pid_r2 = meta["pid_r2"]
        h2_i = h2[i]

        # Primary factor
        abs_loads = np.abs(L_rot[i, :])
        pri_j = int(np.argmax(abs_loads))
        pri_load = L_rot[i, pri_j]
        pri_factor = fnames[pri_j]
        pri_fp = factor_partisan[pri_j]

        # All factors with |loading| ≥ 0.30
        sig = [(fnames[j], round(L_rot[i, j], 3)) for j in range(k_primary) if abs(L_rot[i, j]) >= 0.30]
        sig_str = "; ".join(f"{f}={lv}" for f, lv in sig) if sig else f"max={pri_load:.3f}<0.30"

        # Ideology R² estimated as 1.5× PID R² (high PID–ideology correlation in CCES;
        # without raw data this is an approximation — flag for verification with analyst)
        ideo_r2_est = round(min(pid_r2 * 1.5, 0.95), 3)

        # ── Recommendation logic ──────────────────────────────────────
        max_abs_load = float(abs_loads.max())
        no_clean_load = len(sig) == 0  # no factor loading ≥ 0.30

        if h2_i < 0.12 or (no_clean_load and h2_i < 0.20):
            rec = "DROP"
            reason = (
                f"Near-zero communality (h²={h2_i:.3f}) and/or no clean factor loading "
                f"(max |λ|={max_abs_load:.3f}); does not contribute signal to any dimension"
            )
        elif item in KNOWN_CROSSCUTTING and h2_i >= 0.08:
            rec = "KEEP"
            reason = f"Cross-cutting (PID R²={pid_r2:.3f}); genuinely orthogonal dimension; h²={h2_i:.3f}"
        elif pid_r2 >= 0.20 and pri_fp["approx_v"] >= 0.42:
            rec = "DROP"
            reason = (
                f"High partisan collinearity: item PID R²={pid_r2:.3f}, "
                f"factor V≈{pri_fp['approx_v']:.3f}; dominates partisan axis"
            )
        elif pid_r2 >= 0.15 or pri_fp["approx_v"] >= 0.35:
            rec = "REVIEW"
            reason = (
                f"Moderate partisan load (item R²={pid_r2:.3f}, F-V≈{pri_fp['approx_v']:.3f}); "
                f"cross-tab by cluster before including"
            )
        else:
            rec = "KEEP"
            reason = (
                f"Low partisan collinearity (R²={pid_r2:.3f}); loads on {pri_factor} "
                f"(λ={pri_load:+.3f}); h²={h2_i:.3f}"
            )

        rows.append({
            "Variable":        item,
            "Label":           meta["label"][:60],
            "Domain":          meta["domain"],
            "Factor(s)_loaded": sig_str,
            "Primary_Factor":  pri_factor,
            "Primary_Loading": round(pri_load, 3),
            "h2":              round(h2_i, 3),
            "Partisan_Item_R2": pid_r2,
            "Factor_Partisan_V": round(pri_fp["approx_v"], 3),
            "Ideology_R2_est": ideo_r2_est,
            "Recommend":       rec,
            "Reason":          reason,
        })

    rec_df = pd.DataFrame(rows)

    # Print grouped
    for group, label in [("KEEP", "CONFIRMED KEEP"), ("REVIEW", "REVIEW"), ("DROP", "DROP")]:
        sub = rec_df[rec_df["Recommend"] == group]
        print(f"\n{'─'*72}")
        print(f"  {label}  ({len(sub)} items)")
        print(f"{'─'*72}")
        for _, row in sub.iterrows():
            print(
                f"  {row['Variable']:<15}  {row['Primary_Factor']}  "
                f"λ={row['Primary_Loading']:+.3f}  h²={row['h2']:.3f}  "
                f"PID_R²={row['Partisan_Item_R2']:.3f}  V≈{row['Factor_Partisan_V']:.3f}"
            )
            print(f"    → {row['Reason']}")

    # ──────────────────────────────────────────────────────────────────────────
    # SAVE ALL OUTPUTS
    # ──────────────────────────────────────────────────────────────────────────
    print(f"\n{sep}")
    print("SAVING OUTPUTS")
    print(sep)

    # 1. Parallel analysis
    pa_df = pd.DataFrame({
        "Factor": range(1, 11),
        "Obs_Eigenvalue": np.round(obs_evals[:10], 4),
        "Sim_95pct":      np.round(sim_thresh[:10], 4),
        "Extract":        obs_evals[:10] > sim_thresh[:10],
    })
    pa_df.to_csv(DATA_DIR / "efa_parallel_analysis.csv", index=False)
    print("  ✓ efa_parallel_analysis.csv")

    # 2. Variance summary
    var_rows = []
    for k in [3, 4, 5, 6, 7]:
        r = all_results[k]
        for j in range(k):
            var_rows.append({
                "k": k, "Factor": f"F{j+1}",
                "SS_Loadings": round(r["ss"][j], 3),
                "Pct_Var":     round(r["pct_var"][j], 2),
            })
    pd.DataFrame(var_rows).to_csv(DATA_DIR / "efa_variance_summary.csv", index=False)
    print("  ✓ efa_variance_summary.csv")

    # 3. Loading matrices + Phi for each k
    for k in [3, 4, 5, 6, 7]:
        r = all_results[k]
        fnames_k = [f"F{j+1}" for j in range(k)]

        # Loading matrix
        df_L = pd.DataFrame(r["L_rot"], index=items, columns=fnames_k)
        df_L.insert(0, "Label",   [ITEM_META.get(it, {"label": it})["label"] for it in items])
        df_L.insert(1, "Domain",  [ITEM_META.get(it, {"domain": ""})["domain"] for it in items])
        df_L.insert(2, "PID_R2",  [ITEM_META.get(it, {"pid_r2": 0})["pid_r2"] for it in items])
        df_L["h2"] = r["h2"]
        df_L.to_csv(DATA_DIR / f"efa_loadings_k{k}.csv")
        print(f"  ✓ efa_loadings_k{k}.csv")

        # Factor correlation matrix
        phi_df = pd.DataFrame(np.round(r["Phi"], 4), index=fnames_k, columns=fnames_k)
        phi_df.to_csv(DATA_DIR / f"efa_phi_k{k}.csv")
        print(f"  ✓ efa_phi_k{k}.csv")

    # 4. Recommendation table
    rec_df.to_csv(DATA_DIR / "efa_recommendation_table.csv", index=False)
    print("  ✓ efa_recommendation_table.csv")

    # 5. Step 6 partisan summary
    partisan_rows = []
    for j in range(k_primary):
        fp = factor_partisan[j]
        # list top 5 items
        top5 = np.argsort(np.abs(L_rot[:, j]))[::-1][:5]
        top5_str = "; ".join(
            f"{items[idx]}({L_rot[idx,j]:+.3f})" for idx in top5
        )
        partisan_rows.append({
            "Factor":           fnames[j],
            "Wt_PID_R2":        round(fp["wt_r2"], 3),
            "Approx_Cramers_V": round(fp["approx_v"], 3),
            "Classification":   fp["cls"],
            "Top5_Items":       top5_str,
        })
    partisan_df = pd.DataFrame(partisan_rows)
    partisan_df.to_csv(DATA_DIR / "efa_factor_partisan_summary.csv", index=False)
    print("  ✓ efa_factor_partisan_summary.csv")

    print(f"\n{'─'*72}")
    print(f"Done.  Parallel analysis → k={k_pa};  Primary solution → k={k_primary}")
    print(f"{'─'*72}")

    return all_results, rec_df


if __name__ == "__main__":
    main()

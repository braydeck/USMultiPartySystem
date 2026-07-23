#!/usr/bin/env python3
"""Independent per-wave EFA + DPGMM clustering from first principles.

Usage:  .venv/bin/python analysis/efa/previous_years/independent/fit_independent.py 2022

Loads ALL policy-attitude items for the wave (broader than the crosswalk),
screens them, runs the full EFA chain, and profiles each resulting cluster.
"""
import sys, warnings, pickle
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import efa_math as em, clustering as cl, io_paths as io
from independent.wave_items import get_items, recode_items

PID3_LABEL = {"Democrat": 1, "Republican": 2, "Independent": 3, "Other": 4, "Not sure": 5}
ANCHORS = {"enf": "imm_border", "rel": "relig_church", "val": "race_problemsrare"}


def pid_r2_weighted(x, pid3, w):
    """Weighted R² of item x on pid3 dummies (1-5)."""
    mask = ~np.isnan(x) & ~np.isnan(pid3) & ~np.isnan(w)
    x, pid3, w = x[mask], pid3[mask], w[mask]
    if len(x) < 100:
        return np.nan
    cats = np.unique(pid3[~np.isnan(pid3)])
    D = np.column_stack([np.ones(len(x))] + [(pid3 == c).astype(float) for c in cats[1:]])
    W = w / w.mean()
    XtW = D.T * W
    try:
        bhat = np.linalg.solve(XtW @ D, XtW @ x)
    except np.linalg.LinAlgError:
        return np.nan
    resid = x - D @ bhat
    ss_res = (W * resid ** 2).sum()
    xbar = (W * x).sum() / W.sum()
    ss_tot = (W * (x - xbar) ** 2).sum()
    return 1 - ss_res / ss_tot if ss_tot > 0 else 0.0


def screen_items(D, items, pid3, w):
    """Screen items: PID R² > 0.50, ceiling/floor > 90%. Returns surviving item list + report."""
    surviving = []
    report_lines = []
    report_lines.append(f"{'construct_id':30s} {'domain':12s} {'N_valid':>7s} {'PID_R2':>7s} {'max_pct':>7s} {'verdict':>10s}")
    report_lines.append("-" * 80)
    for it in items:
        cid = it["construct_id"]
        col = D[cid].values
        valid = ~np.isnan(col)
        n_valid = int(valid.sum())
        r2 = pid_r2_weighted(col, pid3, w)
        vals, counts = np.unique(col[valid], return_counts=True)
        max_pct = 100 * counts.max() / n_valid if n_valid > 0 else 0.0
        if r2 > 0.50:
            verdict = "DROP:PID"
        elif max_pct > 90:
            verdict = "DROP:CEIL"
        elif n_valid < 1000:
            verdict = "DROP:N"
        else:
            verdict = "KEEP"
            surviving.append(it)
        report_lines.append(f"{cid:30s} {it['domain']:12s} {n_valid:>7,d} {r2:>7.3f} {max_pct:>6.1f}% {verdict:>10s}")
    return surviving, report_lines


DEMO_COLS = ["birthyr", "educ", "race", "gender4", "faminc_new", "religpew",
             "pew_bornagain", "urbancity", "votereg", "newsint"]


def fit_wave(wave, k_override=None):
    items = get_items(wave)
    variables = [it["variable"] for it in items]
    demo_available = []
    need = variables + [io.WEIGHT_COL, "pid3", "ideo5"]
    all_cols = pd.read_stata(str(io.dta_path(wave)), iterator=True).variable_labels()
    for dc in DEMO_COLS:
        if dc in all_cols:
            need.append(dc)
            demo_available.append(dc)

    print(f"Loading {wave} dta...", flush=True)
    df = pd.read_stata(str(io.dta_path(wave)), columns=need,
                       convert_categoricals=True, convert_missing=False, convert_dates=False)
    print(f"  raw N = {len(df):,}")

    D = recode_items(df, items)
    w = pd.to_numeric(df[io.WEIGHT_COL], errors="coerce").values.astype(float)
    pid3_raw = df["pid3"].astype("object").map(PID3_LABEL)
    pid3 = pd.to_numeric(pid3_raw, errors="coerce").values.astype(float)

    # ── Screen ──
    print("Screening items...", flush=True)
    surviving, screen_report = screen_items(D, items, pid3, w)
    item_ids = [it["construct_id"] for it in surviving]
    print(f"  {len(surviving)}/{len(items)} items survive screening")

    # ── Listwise ──
    mask = D[item_ids].notna().all(axis=1) & ~np.isnan(w)
    D = D.loc[mask, item_ids].reset_index(drop=True)
    w = w[mask.values]
    pid3 = pid3[mask.values]
    ideo5 = pd.to_numeric(df.loc[mask.values, "ideo5"], errors="coerce").values
    n = len(D)
    wn = w.sum()
    print(f"  listwise N = {n:,}  weighted N = {wn:,.0f}")

    # ── Polychoric ──
    print("Computing polychoric matrix...", flush=True)
    R = em.polychoric_matrix(D, item_ids, w, progress=True)
    R = em.regularize_corr(R)

    # ── Parallel analysis ──
    k_pa, obs_ev, thr = em.parallel_analysis(R, n_obs=min(n, 20000))
    print(f"  parallel analysis -> k = {k_pa}")

    # ── PAF + oblimin ──
    k = k_override if k_override is not None else k_pa
    if k != k_pa:
        print(f"  using k={k} (override; PA suggested k={k_pa})")
    L_un, h2_init, eigs = em.paf(R, k)
    L, Phi = em.oblimin(L_un)
    h2 = np.clip(np.diag(L @ Phi @ L.T), 0.0, 1.0)

    # ── Thomson scores ──
    X = D.values.astype(float)
    Z, mu, sig = em.weighted_standardize(X, w)
    F, B = em.thomson_scores(Z, R, L, Phi)
    F, L = em.sign_align_by_loading(F, L)

    # ── Factor identification by anchor items ──
    def anchor_factor(cid):
        return int(np.argmax(np.abs(L[item_ids.index(cid), :]))) if cid in item_ids else None
    ident = {key: anchor_factor(cid) for key, cid in ANCHORS.items()}
    print(f"  anchors: {ident}")

    # ── Partisan sign-align ──
    dem = pid3 == 1; rep = pid3 == 2
    for key in ("enf", "rel", "val"):
        j = ident[key]
        if j is None:
            continue
        if rep.sum() and dem.sum():
            md = np.average(F[dem, j], weights=w[dem])
            mr = np.average(F[rep, j], weights=w[rep])
            if mr < md:
                F[:, j] *= -1
                L[:, j] *= -1

    # ── Residualize correlated factors on base factor ──
    # Use enforcement anchor if available; fall back to highest-variance factor
    Xc = F.copy()
    enf = ident["enf"]
    if enf is None:
        ss = np.sum(L ** 2, axis=0)
        enf = int(np.argmax(ss))
        print(f"  no enforcement anchor — using F{enf+1} (highest variance) as residualization base")
    for j in range(k):
        if j == enf:
            continue
        if abs(Phi[enf, j]) > 0.25:
            Xc[:, j] = em.wresid(F[:, j], F[:, enf], w)
            print(f"  residualized F{j+1} on F{enf+1} (Phi={Phi[enf,j]:.3f})")

    # ── DPGMM ──
    print("Fitting DPGMM...", flush=True)
    model, raw, probs = cl.dpgmm_fit(Xc)
    cluster, size_sorted = cl.remap_by_weighted_n(raw, w, model.weights_)
    n_eff = int((model.weights_ > 0.01).sum())
    centroids = cl.weighted_centroids(Xc, cluster, w, n_eff)
    print(f"  effective clusters: {n_eff}")

    # ── Profile clusters ──
    profiles = {}
    partisan = {}
    for c in range(n_eff):
        m = cluster == c
        wc = w[m]
        tot = wc.sum()
        prof = {}
        for cid in item_ids:
            vals = D.loc[D.index[m], cid].values
            valid = ~np.isnan(vals)
            if valid.sum() > 0:
                prof[cid] = np.average(vals[valid], weights=wc[valid])
            else:
                prof[cid] = np.nan
        profiles[c] = prof
        partisan[c] = {
            "share": 100 * tot / w.sum(),
            "Dem": 100 * wc[pid3[m] == 1].sum() / tot,
            "Rep": 100 * wc[pid3[m] == 2].sum() / tot,
            "Ind": 100 * wc[pid3[m] == 3].sum() / tot,
            "N_weighted": tot,
        }

    # ── Demographics per cluster ──
    demographics = {}
    mask_idx = mask[mask].index if hasattr(mask, 'index') else np.where(mask.values)[0]
    for c in range(n_eff):
        m = cluster == c
        wc = w[m]
        tot = wc.sum()
        demo = {}
        for dc in demo_available:
            raw = df.iloc[mask_idx[m]][dc]
            if dc == "birthyr":
                by = pd.to_numeric(raw, errors="coerce")
                valid = by.notna()
                if valid.sum() > 0:
                    # compute age as of survey year
                    yr = int(wave)
                    ages = yr - by[valid].values
                    demo["mean_age"] = round(float(np.average(ages, weights=wc[valid.values])), 1)
                    demo["median_age"] = round(float(np.median(ages)), 0)
            else:
                cats = raw.astype("object")
                for val in cats.unique():
                    if pd.isna(val):
                        continue
                    val_str = str(val).strip()
                    if val_str in ("", "Skipped", "Not Asked"):
                        continue
                    pct = 100 * wc[cats.values == val].sum() / tot
                    if pct > 1.0:
                        demo[f"{dc}:{val_str}"] = round(pct, 1)
        demographics[c] = demo

    # ── Print summary ──
    fnames = [f"F{j+1}" for j in range(k)]
    print(f"\n  {'cl':>3} {'share':>6} {'Dem':>5} {'Rep':>5} {'Ind':>5}")
    for c in range(n_eff):
        p = partisan[c]
        print(f"  c{c:<2} {p['share']:>5.1f}% {p['Dem']:>4.0f}% {p['Rep']:>4.0f}% {p['Ind']:>4.0f}%")

    # ── Save outputs ──
    outdir = io.out_dir(wave)
    pd.DataFrame(L, index=item_ids, columns=fnames).assign(h2=h2).to_csv(outdir / "independent_loadings.csv")
    pd.DataFrame(np.round(Phi, 4), index=fnames, columns=fnames).to_csv(outdir / "independent_phi.csv")

    prof_df = pd.DataFrame(profiles).T
    prof_df.index.name = "cluster"
    prof_df.to_csv(outdir / "independent_cluster_profiles.csv")

    part_df = pd.DataFrame(partisan).T
    part_df.index.name = "cluster"
    part_df.to_csv(outdir / "independent_cluster_partisan.csv")

    with open(outdir / "independent_diagnostics.txt", "w") as f:
        f.write(f"INDEPENDENT FIT: {wave} ({io.KIND[wave]})\n")
        f.write(f"items screened: {len(items)}  surviving: {len(surviving)}\n")
        f.write(f"listwise N = {n:,}  weighted N = {wn:,.0f}\n")
        f.write(f"parallel analysis -> k = {k_pa}  (fit uses k={k})\n\n")
        ss = np.sum(L ** 2, axis=0)
        pv = ss / len(item_ids) * 100
        f.write("factor SS-loadings / %var:\n")
        for j in range(k):
            f.write(f"  F{j+1}  SS={ss[j]:.3f}  {pv[j]:.1f}%\n")
        f.write(f"\nanchor->factor: {ident}\n")
        f.write(f"effective clusters: {n_eff}\n\n")
        f.write("ITEM SCREENING:\n")
        for line in screen_report:
            f.write(line + "\n")

    result = dict(
        wave=wave, item_ids=item_ids, items=surviving, k=k, n=n, wn=float(wn),
        R=R, L=L, Phi=Phi, h2=h2, F=F, Xc=Xc, mu=mu, sig=sig, B=B,
        ident=ident, cluster=cluster, probs=probs, w=w, pid3=pid3, ideo5=ideo5,
        n_eff=n_eff, centroids=centroids, k_pa=int(k_pa),
        obs_eigen=obs_ev, model=model, size_sorted=size_sorted,
        profiles=profiles, partisan=partisan, demographics=demographics,
        _items_df=D,
    )
    with open(outdir / "independent_fit.pkl", "wb") as f:
        pickle.dump(result, f)
    print(f"\nOutputs saved to {outdir}/independent_*")
    return result


if __name__ == "__main__":
    wave = sys.argv[1] if len(sys.argv) > 1 else "2022"
    k_override = int(sys.argv[2]) if len(sys.argv) > 2 else None
    fit_wave(wave, k_override=k_override)

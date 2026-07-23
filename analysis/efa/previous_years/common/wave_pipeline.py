"""End-to-end per-wave EFA + clustering, parameterized by item set.

For a given wave and item list it runs the validated 2024 chain:
  recode (crosswalk) -> listwise -> weighted polychoric -> PAF+oblimin
  -> Thomson factor scores -> partisan sign-align -> F4/F5 residualize on F1
  -> DPGMM (10-comp DP prior).

Anchors (present in every wave) identify factors for sign/residualization:
  enforcement = imm_border, religion = relig_church, values/populism = race_problemsrare.
"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd

from . import efa_math as em
from . import clustering as cl
from . import crosswalk as cwmod
from . import io_paths as io

PID3_LABEL = {"Democrat": 1, "Republican": 2, "Independent": 3, "Other": 4, "Not sure": 5}
ANCHORS = {"enf": "imm_border", "rel": "relig_church", "val": "race_problemsrare"}


def load_wave_items(wave, levels=cwmod.USABLE, extra_cols=None):
    """Load a wave's dta (label-decoded), recode crosswalk items, attach weight/pid3.

    Returns (D numeric-item DataFrame keyed by construct_id, w, pid3, meta_dict)."""
    cw = cwmod.load()
    rows = cwmod.constructs_for_wave(wave, levels=levels, cw=cw)
    varcol = f"var_{wave}"
    raw_vars = list(rows[varcol])
    need = raw_vars + [io.WEIGHT_COL, "pid3"] + (extra_cols or [])
    df = pd.read_stata(str(io.dta_path(wave)), columns=need,
                       convert_categoricals=True, convert_missing=False, convert_dates=False)
    items = cwmod.recode_wave(df, wave, levels=levels, cw=cw)
    w = pd.to_numeric(df[io.WEIGHT_COL], errors="coerce").values.astype(float)
    pid3 = df["pid3"].map(PID3_LABEL).values
    meta = {"wave": wave, "n_raw": len(df), "constructs": list(items.columns)}
    return items, w, pid3, meta


def fit_efa(items_df, w, pid3, item_ids, k, wave, label, save=True):
    """Fit EFA (+ scores + DPGMM) on `item_ids` columns of items_df. Returns dict."""
    D = items_df[item_ids].copy()
    mask = D.notna().all(axis=1) & ~np.isnan(w)
    D = D[mask].reset_index(drop=True)
    ww = w[mask.values]
    pp = pid3[mask.values]
    n = len(D)
    wn = ww.sum()
    print(f"  [{wave}/{label}] items={len(item_ids)}  listwise N={n:,}  weighted N={wn:,.0f}", flush=True)

    # polychoric + regularize
    R = em.polychoric_matrix(D, item_ids, ww, progress=True)
    R = em.regularize_corr(R)

    # parallel analysis (for reporting k)
    k_pa, obs_ev, thr = em.parallel_analysis(R, n_obs=min(n, 20000))

    # PAF + oblimin
    L_un, h2_init, eigs = em.paf(R, k)
    L, Phi = em.oblimin(L_un)
    h2 = np.clip(np.diag(L @ Phi @ L.T), 0.0, 1.0)

    # Thomson factor scores
    X = D.values.astype(float)
    Z, mu, sig = em.weighted_standardize(X, ww)
    F, B = em.thomson_scores(Z, R, L, Phi)
    F, L = em.sign_align_by_loading(F, L)   # base convention: strongest item positive

    # identify factors by anchor items (max |loading|)
    def anchor_factor(cid):
        return int(np.argmax(np.abs(L[item_ids.index(cid), :]))) if cid in item_ids else None
    ident = {key: anchor_factor(cid) for key, cid in ANCHORS.items()}

    # partisan sign-align conservative factors (Rep should exceed Dem)
    dem = pp == 1; rep = pp == 2
    for key in ("enf", "rel", "val"):
        j = ident[key]
        if j is None:
            continue
        if rep.sum() and dem.sum():
            md = np.average(F[dem, j], weights=ww[dem])
            mr = np.average(F[rep, j], weights=ww[rep])
            if mr < md:
                F[:, j] *= -1
                L[:, j] *= -1

    # residualize religion & values factors on enforcement factor (production convention)
    Xc = F.copy()
    enf = ident["enf"]
    if enf is not None:
        for key in ("rel", "val"):
            j = ident[key]
            if j is not None and j != enf:
                Xc[:, j] = em.wresid(F[:, j], F[:, enf], ww)

    # DPGMM on residualized factor space
    model, raw, probs = cl.dpgmm_fit(Xc)
    cluster, size_sorted = cl.remap_by_weighted_n(raw, ww, model.weights_)
    n_eff = int((model.weights_ > 0.01).sum())
    centroids = cl.weighted_centroids(Xc, cluster, ww, n_eff)

    fnames = [f"F{j+1}" for j in range(k)]
    result = dict(wave=wave, label=label, item_ids=item_ids, k=k, n=n, wn=float(wn),
                  R=R, L=L, Phi=Phi, h2=h2, F=F, Xc=Xc, mu=mu, sig=sig, B=B,
                  ident=ident, cluster=cluster, probs=probs, w=ww, pid3=pp,
                  n_eff=n_eff, centroids=centroids, k_pa=int(k_pa),
                  obs_eigen=obs_ev, model=model, size_sorted=size_sorted, fnames=fnames,
                  _Xitems=X)

    if save:
        d = io.out_dir(wave)
        pd.DataFrame(L, index=item_ids, columns=fnames).assign(h2=h2).to_csv(d / f"loadings_{label}.csv")
        pd.DataFrame(np.round(Phi, 4), index=fnames, columns=fnames).to_csv(d / f"phi_{label}.csv")
        pd.DataFrame({"factor": range(1, len(obs_ev) + 1), "obs_eigen": np.round(obs_ev, 4)}).to_csv(
            d / f"parallel_{label}.csv", index=False)
        cluster_shares = (pd.Series(cluster[cluster >= 0])
                          .to_frame("cl").assign(w=ww[cluster >= 0])
                          .groupby("cl")["w"].sum())
        cluster_shares = (cluster_shares / cluster_shares.sum() * 100).round(2)
        cluster_shares.to_csv(d / f"cluster_shares_{label}.csv", header=["weighted_pct"])
        _write_diagnostics(d / f"diagnostics_{label}.txt", result)
    return result


def _write_diagnostics(path, r):
    ss = np.sum(r["L"] ** 2, axis=0)
    pv = ss / len(r["item_ids"]) * 100
    with open(path, "w") as f:
        f.write(f"WAVE {r['wave']}  fit={r['label']}  ({io.KIND[r['wave']]})\n")
        f.write(f"items={len(r['item_ids'])}  listwise N={r['n']:,}  weighted N={r['wn']:,.0f}\n")
        f.write(f"parallel analysis -> k={r['k_pa']}   (fit uses k={r['k']})\n\n")
        f.write("factor SS-loadings / %var:\n")
        for j, fn in enumerate(r["fnames"]):
            f.write(f"  {fn}  SS={ss[j]:.3f}  {pv[j]:.1f}%\n")
        f.write(f"\nanchor->factor: {r['ident']}\n")
        f.write(f"effective clusters: {r['n_eff']}\n")

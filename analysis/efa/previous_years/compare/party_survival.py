#!/usr/bin/env python3
"""Do the 2024 parties survive in earlier years?

Approach: for each prior wave, load its items via the crosswalk, keep only items
that exist in the canonical 2024 24-item set, standardize in the 2024 metric, score
with the canonical 2024 scoring coefficients (subset to shared items), sign-align,
residualize (canonical betas), and assign to 2024 parties via a reference DPGMM
(refit on 2024's canonical residualized factor space, seed=42).

Reports — by party name — size, partisan makeup, and change vs 2024.
"""
import sys, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import io_paths as io, efa_math as em, clustering as cl, crosswalk as cwmod

ROOT = io.ROOT
CODES = ["CON", "LBR", "STY", "NAT", "LIB", "POP", "CUP", "OAO", "DSA", "PRG"]
NAMES = {"CON": "Conservative", "LBR": "Labor", "STY": "Solidarity", "NAT": "Nationalist",
         "LIB": "Liberal", "POP": "Populist", "CUP": "Civic Union", "OAO": "Order & Opp.",
         "DSA": "Dem. Socialist", "PRG": "Progressive"}
FCOLS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4_resid", "FS_F5_resid"]

PID3_LABEL = {"Democrat": 1, "Republican": 2, "Independent": 3, "Other": 4, "Not sure": 5}

ITEMS_24 = [
    "pew_churatd", "CC24_302", "CC24_303", "CC24_341a", "CC24_341c", "CC24_341d",
    "CC24_323a", "CC24_323b", "CC24_323d", "CC24_321b", "CC24_321d", "CC24_321e",
    "CC24_325", "CC24_324b", "CC24_340b", "CC24_340c", "CC24_340e", "CC24_340f",
    "CC24_440b", "CC24_440c", "CC24_421_1", "CC24_421_2", "CC24_423", "CC24_424",
]

# ── Load canonical 2024 reference ──
tp = pd.read_csv(ROOT / "data/processed/typology_cluster_assignments.csv")
w24_all = tp["commonpostweight"].values
Xc_24 = tp[FCOLS].values

# canonical per-party reference
REF = {}
for cid in range(10):
    g = tp[tp["cluster"] == cid]; ww = g["commonpostweight"].values; tot = ww.sum()
    REF[CODES[cid]] = {
        "share": 100 * tot / w24_all.sum(),
        "Dem": 100 * ww[g["pid3"].values == 1].sum() / tot,
        "Rep": 100 * ww[g["pid3"].values == 2].sum() / tot,
    }

# fit reference DPGMM on canonical 2024 residualized space
ref_model, ref_raw, _ = cl.dpgmm_fit(Xc_24)
ref_cluster, ref_size = cl.remap_by_weighted_n(ref_raw, w24_all, ref_model.weights_)
n_eff_ref = int((ref_model.weights_ > 0.01).sum())
comp_to_id = {orig: new for new, orig in enumerate(ref_size)}

# verify self-assignment reproduces canonical shares
self_shares = np.array([w24_all[ref_cluster == k].sum() / w24_all.sum() * 100 for k in range(n_eff_ref)])
print("Self-check — ref DPGMM reproduces 2024 shares:")
for k in range(min(10, n_eff_ref)):
    print(f"  {CODES[k]}: canonical {REF[CODES[k]]['share']:.1f}%  ref {self_shares[k]:.1f}%")

# canonical 2024 scoring setup: load polychoric, compute B
R24_full = pd.read_csv(ROOT / "data/processed/polychoric_matrix.csv", index_col=0)
R24 = em.regularize_corr(R24_full.loc[ITEMS_24, ITEMS_24].values.astype(float))
L_un24, _, _ = em.paf(R24, 5); L24, Phi24 = em.oblimin(L_un24)
B24 = np.linalg.inv(R24) @ (L24 @ Phi24)

# 2024 standardization: mu/sig of the 24 items (from the canonical factor-scores sample)
# re-derive from stored scores + items is complex; load 2024 dta once
df24_raw = pd.read_stata(str(io.dta_path("2024")), columns=ITEMS_24 + [io.WEIGHT_COL],
                         convert_categoricals=True, convert_missing=False, convert_dates=False)
cw = cwmod.load()
cw24 = cw[cw["var_2024"].isin(ITEMS_24) & (cw["cov_2024"] == "exact")]
items24_df = cwmod.recode_wave(df24_raw, "2024", levels={"exact"}, cw=cw24)
# reorder to ITEMS_24 order via construct→var mapping
cid_to_var24 = dict(zip(cw24["construct_id"], cw24["var_2024"]))
var24_to_cid = {v: k for k, v in cid_to_var24.items()}
# only constructs whose var_2024 is in ITEMS_24
cids_in_order = [var24_to_cid[v] for v in ITEMS_24 if v in var24_to_cid]
items_in_order = [v for v in ITEMS_24 if v in var24_to_cid]
w24_raw = pd.to_numeric(df24_raw[io.WEIGHT_COL], errors="coerce").values
mask24 = items24_df[cids_in_order].notna().all(axis=1) & ~np.isnan(w24_raw)
X24 = items24_df.loc[mask24, cids_in_order].values
w24_m = w24_raw[mask24]
wn24 = w24_m / w24_m.sum()
mu24 = (wn24[:, None] * X24).sum(0)
sig24 = np.sqrt((wn24[:, None] * (X24 - mu24) ** 2).sum(0))
sig24[sig24 < 1e-10] = 1.0
n_canon = len(cids_in_order)

# sign-alignment: derive from the canonical Xc_24 factor scores vs the raw B24 loadings
# For each factor j, the sign convention is set by the anchor item's loading direction.
# anchor items: F1=CC24_323b(border), F2=CC24_421_2(elec), F3=CC24_423(trust),
#               F4=pew_churatd(church), F5=CC24_440b(race)
# In the canonical pipeline, Republicans score higher on F1/F4/F5 → those are positive.
# Derive empirically: which sign of B24 column makes the canonical Xc_24 means positive
# for the party with the highest centroid on each factor.
signs = np.ones(5)
for j in range(5):
    best_party = int(np.argmax([REF[CODES[k]].get("share", 0) *
                                abs(tp[tp["cluster"] == k][FCOLS[j]].mean())
                                for k in range(10)]))
    canon_sign = np.sign(tp[tp["cluster"] == best_party][FCOLS[j]].mean())
    # test: does B24 col j, applied to the 2024 data subset, produce same sign?
    Z24_test = (X24[:1000] - mu24) / sig24
    B_test = B24[[ITEMS_24.index(cid_to_var24[c]) for c in cids_in_order], :]
    test_mean = (Z24_test @ B_test)[:, j].mean()
    if np.sign(test_mean) != canon_sign and canon_sign != 0:
        signs[j] = -1

# residualization betas from canonical space
W = w24_all / w24_all.mean()
Xd = np.column_stack([np.ones(len(Xc_24)), Xc_24[:, 0]])
XtW = Xd.T * W
betas = {j: np.linalg.solve(XtW @ Xd, XtW @ Xc_24[:, j]) for j in (3, 4)}
print(f"\nCanonical setup: {n_canon}/{len(ITEMS_24)} items recoded, sign flips: {signs.tolist()}")


def project_wave(wave):
    """Project a prior wave into 2024 party space."""
    cw_all = cwmod.load()
    # find constructs shared with canonical 2024
    shared = cw_all[(cw_all["var_2024"].isin(ITEMS_24)) &
                    (cw_all[f"cov_{wave}"].isin({"exact", "equivalent"})) &
                    (cw_all[f"var_{wave}"].notna())]
    shared_cids = list(shared["construct_id"])
    shared_vars_wave = list(shared[f"var_{wave}"])
    shared_vars_24 = list(shared["var_2024"])
    n_shared = len(shared_cids)

    df = pd.read_stata(str(io.dta_path(wave)), columns=shared_vars_wave + [io.WEIGHT_COL, "pid3"],
                       convert_categoricals=True, convert_missing=False, convert_dates=False)
    items_df = cwmod.recode_wave(df, wave, levels={"exact", "equivalent"}, cw=shared)
    w = pd.to_numeric(df[io.WEIGHT_COL], errors="coerce").values
    pid3 = df["pid3"].map(PID3_LABEL).values
    mask = items_df[shared_cids].notna().all(axis=1) & ~np.isnan(w)
    items_df = items_df.loc[mask, shared_cids].reset_index(drop=True)
    w = w[mask]; pid3 = pid3[mask]

    # map shared constructs to their ITEMS_24 indices for B subsetting
    cid_to_24v = dict(zip(shared_cids, shared_vars_24))
    idx_in_items24 = [ITEMS_24.index(cid_to_24v[c]) for c in shared_cids]
    # map shared constructs to their position in the mu24/sig24 arrays (which use cids_in_order)
    idx_in_canon = [cids_in_order.index(c) for c in shared_cids if c in cids_in_order]
    cids_in_both = [c for c in shared_cids if c in cids_in_order]

    X = items_df[cids_in_both].values
    mu_sub = mu24[[cids_in_order.index(c) for c in cids_in_both]]
    sig_sub = sig24[[cids_in_order.index(c) for c in cids_in_both]]
    Z = (X - mu_sub) / sig_sub

    B_sub = B24[[ITEMS_24.index(cid_to_var24[c]) for c in cids_in_both], :]
    F = (Z @ B_sub) * signs

    Xc = F.copy()
    for j in (3, 4):
        a, b = betas[j]
        Xc[:, j] = F[:, j] - (a + b * F[:, 0])

    proba = ref_model.predict_proba(Xc)
    raw = proba.argmax(1)
    cluster = np.array([comp_to_id.get(c, -1) for c in raw])
    return cluster, w, pid3, n_shared


def report(wave, cluster, w, pid3, n_shared):
    total_w = w[cluster >= 0].sum()
    print(f"\n{'='*80}")
    print(f"  {wave} ({io.KIND[wave]}) — {n_shared}/24 items shared with 2024")
    print(f"{'='*80}")
    print(f"  {'':>5} {'name':>14} {'2024':>6} {wave:>6} {'Δpp':>5} | {'Dem':>4} {'Rep':>4} {'Ind':>4} | 2024 mix")
    print(f"  {'-'*5} {'-'*14} {'-'*6} {'-'*6} {'-'*5} | {'-'*4} {'-'*4} {'-'*4} | {'-'*9}")
    for k in range(min(10, n_eff_ref)):
        code = CODES[k]; name = NAMES[code]
        mk = cluster == k; wk = w[mk]; tot = wk.sum()
        sh = 100 * tot / total_w if total_w > 0 else 0
        dem = 100 * wk[pid3[mk] == 1].sum() / tot if tot > 0 else 0
        rep = 100 * wk[pid3[mk] == 2].sum() / tot if tot > 0 else 0
        ind = 100 - dem - rep
        r = REF[code]; delta = sh - r["share"]
        flag = "✓" if abs(delta) < 5 else ("↑" if delta > 0 else "↓")
        print(f"  {code:>5} {name:>14} {r['share']:>5.1f}% {sh:>5.1f}% {delta:>+4.1f}{flag} | "
              f"{dem:>3.0f}% {rep:>3.0f}% {ind:>3.0f}% | {r['Dem']:.0f}D/{r['Rep']:.0f}R")
    missing = [ITEMS_24[i] for i in range(len(ITEMS_24))
               if ITEMS_24[i] not in [cid_to_var24.get(c) for c in
                                      cwmod.load()[(cwmod.load()[f"cov_{wave}"].isin({"exact","equivalent"})) &
                                                   (cwmod.load()["var_2024"].isin(ITEMS_24))]["construct_id"]]]
    if missing:
        print(f"  missing items ({len(missing)}): {', '.join(missing)}")


def main():
    print("PARTY SURVIVAL: projecting each wave into the canonical 2024 party space\n")
    for wave in io.WAVES:
        cluster, w, pid3, n_sh = project_wave(wave)
        report(wave, cluster, w, pid3, n_sh)
    print()


if __name__ == "__main__":
    main()

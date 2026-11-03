"""Forced to CES's factor count, do ANES's topic factors merge into CES's four broad ones?

Data: ANES 2024 Time Series (2025-08-08 release), weight V240108a; the 136 items that pass Stage B of stage_c.py
(config/anes_independent_pool.csv minus the B drops in outputs/stage_c/screen_log.csv). CES reference: the Stage C
fit of the 69-item pool at k = 5, analysis/efa/exploration/listwise_check/outputs/stage_c/pool69_loadings_k5.csv and
pool69_factors.csv (four passing factors plus the contraception pair).

Procedure:
  1. One pairwise weighted polychoric over the 136 items on every post-weighted respondent, regularized (stage_c.py's
     matrix). PAF + oblimin at k = 4 and k = 5, no item reduction, so every screened item is placed.
  2. Merging: each item that is clean on a k = 17 factor (outputs/stage_c/entry_test.csv) is assigned to its highest-
     loading factor in the forced fit; the table counts where each k = 17 factor's clean items land.
  3. Replication: CES and ANES items paired through config/anes_matched_crosswalk.csv (same ANES source variable).
     Each ANES pool item is sign-aligned to its crosswalk coding by the sign of their weighted correlation in ANES.
     Tucker phi between every forced ANES factor and every CES factor over the paired items, counted only when each
     side has at least 2 paired items loading |l| >= 0.30 (the stage_c_resample.py rule); 0.85 is the match line.

This is a diagnostic at fixed k, not the §3c rule.
Writes outputs/consolidation/{loadings_k4.csv, loadings_k5.csv, merging_k4.csv, merging_k5.csv, phi_k4.csv,
phi_k5.csv, pairs.csv}; log via tee.
"""
import sys

import numpy as np
import pandas as pd

import independent_efa as ie
import matched_efa as me
import recode_matched as rm
from common import efa_math as em

OUT = me.OUT / "consolidation"
CES_DIR = me.HERE.parents[1] / "efa" / "exploration" / "listwise_check" / "outputs" / "stage_c"
K_FORCED = (4, 5)
PHI = 0.85


def phi(x, y):
    if (np.abs(x) >= 0.30).sum() < 2 or (np.abs(y) >= 0.30).sum() < 2:
        return np.nan
    return float(x @ y / np.sqrt((x @ x) * (y @ y)))


def wcorr(a, b, w):
    da, db = a - np.average(a, weights=w), b - np.average(b, weights=w)
    return float(np.average(da * db, weights=w) / np.sqrt(np.average(da ** 2, weights=w) * np.average(db ** 2, weights=w)))


def pairs(items, w, cw_pool, pool):
    xw = pd.read_csv(rm.CROSSWALK)
    xw = xw[xw.fidelity != "none"]
    ces = pd.read_csv(CES_DIR / "pool69_loadings_k5.csv", index_col=0)
    raw = pd.read_csv(rm.ANES_CSV, usecols=sorted({s for x in xw.anes_sources for s in x.split("|")} | {rm.WEIGHT}),
                      low_memory=False)
    wr = pd.to_numeric(raw[rm.WEIGHT], errors="coerce").values
    raw = raw[~np.isnan(wr) & (wr > 0)].reset_index(drop=True)
    rows = []
    for r in xw[xw.ces_var.isin(ces.index)].itertuples():
        src = set(r.anes_sources.split("|"))
        for item in pool:
            if src & set(cw_pool.anes_sources[item].split("|")):
                a, b = items[item].values, rm.recode_row(raw, r.anes_sources, r.anes_map).values
                ok = ~np.isnan(a) & ~np.isnan(b)
                c = wcorr(a[ok], b[ok], w[ok]) if ok.sum() > 50 else np.nan
                rows.append({"ces_var": r.ces_var, "anes_item": item, "fidelity": r.fidelity,
                             "sign": int(np.sign(c)), "r": round(float(c), 2), "label": cw_pool.label[item][:60]})
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    items, w, _, cw = ie.load_pool()
    dropped_b = pd.read_csv(me.OUT / "stage_c" / "screen_log.csv").query("dropped_at.str.startswith('B')").item_id
    pool = [c for c in items.columns if c not in set(dropped_b)]
    R = em.regularize_corr(em.polychoric_matrix(items[pool], pool, w, progress=False))
    print(f"{len(pool)} items after Stage B", flush=True)

    et = pd.read_csv(me.OUT / "stage_c" / "entry_test.csv")
    k17 = pd.read_csv(me.OUT / "stage_c" / "loadings_k17.csv", index_col=0)
    k17_name = {r.factor: " / ".join(cw.label[c][:22] for c in k17[f"N{r.factor + 1}"].abs().nlargest(2).index)
                for r in et.itertuples()}

    ces = pd.read_csv(CES_DIR / "pool69_loadings_k5.csv", index_col=0)
    cf = pd.read_csv(CES_DIR / "pool69_factors.csv").query("fit == 'k5'").reset_index(drop=True)
    ces_names = {f"k5_F{j}": ("" if r.passes else "[fails entry] ") + r["name"].split(" (")[0] for j, r in cf.iterrows()}
    pr = pairs(items, w, cw, pool)
    pr.to_csv(OUT / "pairs.csv", index=False)
    with pd.option_context("display.width", 200):
        print(f"\nCES-ANES item pairs in both fits: {len(pr)}\n{pr.to_string(index=False)}", flush=True)

    for k in K_FORCED:
        L, Phi, h2 = me.fit(R, k)
        cols = [f"A{j + 1}" for j in range(k)]
        ld = pd.DataFrame(L, index=pool, columns=cols)
        out = ld.round(3).assign(h2=h2.round(3), label=[cw.label[c][:70] for c in pool])
        out.to_csv(OUT / f"loadings_k{k}.csv")
        print(f"\n===== k = {k} =====\nfactor correlations:\n{pd.DataFrame(Phi, index=cols, columns=cols).round(2)}")
        for c in cols:
            top = ld[c].abs().nlargest(8).index
            print(f"\n{c} top items: " + "; ".join(f"{cw.label[t][:38]} ({ld[c][t]:+.2f})" for t in top))

        prim = ld.abs().idxmax(axis=1)
        merge = []
        for r in et.itertuples():
            clean = [c for c in str(r.clean_items).split("; ") if c in ld.index]
            counts = prim[clean].value_counts()
            merge.append({"k17_factor": f"F{r.factor}", "name": k17_name[r.factor], "clusters_at_k17": r.passes,
                          "n_clean": len(clean), **{c: int(counts.get(c, 0)) for c in cols}})
        mg = pd.DataFrame(merge)
        mg.to_csv(OUT / f"merging_k{k}.csv", index=False)
        with pd.option_context("display.width", 200, "display.max_colwidth", 50):
            print(f"\nwhere each k = 17 factor's clean items land at k = {k}:\n{mg.to_string(index=False)}")

        P = pd.DataFrame(index=[ces_names[c] for c in ces_names], columns=cols, dtype=float)
        for c_ces in ces_names:
            x = ces.loc[pr.ces_var, c_ces].values
            for c in cols:
                y = ld.loc[pr.anes_item, c].values * pr.sign.values
                P.loc[ces_names[c_ces], c] = phi(x, y)
        P.to_csv(OUT / f"phi_k{k}.csv")
        print(f"\nTucker phi, CES factor x forced ANES factor, over the {len(pr)} paired items "
              f"(blank = fewer than 2 loading items on a side):\n{P.abs().round(2).to_string()}", flush=True)


if __name__ == "__main__":
    sys.exit(main())

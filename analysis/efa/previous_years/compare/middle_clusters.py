#!/usr/bin/env python3
"""Concrete cluster-level view: place every common-fit cluster on the (stable)
dominant conservatism axis, with size, partisan makeup, and raw policy positions.
Then isolate the moderate middle and track it across waves.

Uses the stored 10-item common fits (k=2, full sample every wave) — no dta reload.
"""
import sys, pickle, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import io_paths as io, efa_math as em

# raw policy items to profile (recoded: higher = more conservative). church is 1-6, race 1-5, rest 0/1.
PROFILE = ["imm_border", "imm_legalstatus", "gun_concealcarry", "abortion_rapeincest",
           "race_problemsrare", "race_slavery", "relig_church"]
MOD = 0.5  # |conservatism z| < MOD = "moderate"


def wave_table(wave):
    c = pickle.load(open(io.out_dir(wave) / "fit_results.pkl", "rb"))["common"]
    items = c["item_ids"]; X = c["_Xitems"]; w = c["w"]; pid = c["pid3"]; cl = c["cluster"]
    # dominant conservatism score (k=1), z-standardized within wave
    R = em.regularize_corr(c["R"].copy())
    L1, _, _ = em.paf(R, 1); L1 = L1[:, 0] * (1 if L1[np.argmax(np.abs(L1[:, 0])), 0] >= 0 else -1)
    Z, _, _ = em.weighted_standardize(X, w)
    score = Z @ (np.linalg.inv(R) @ L1)
    m = np.average(score, weights=w); s = np.sqrt(np.average((score - m) ** 2, weights=w))
    z = (score - m) / s
    rows = []
    for k in range(c["n_eff"]):
        mk = cl == k
        if mk.sum() == 0:
            continue
        ww = w[mk]; tot = ww.sum()
        row = {"wave": wave, "cluster": k,
               "share": 100 * tot / w[cl >= 0].sum(),
               "cons_z": np.average(z[mk], weights=ww),
               "Dem": 100 * ww[pid[mk] == 1].sum() / tot,
               "Rep": 100 * ww[pid[mk] == 2].sum() / tot,
               "Ind": 100 * ww[pid[mk] == 3].sum() / tot}
        for it in PROFILE:
            row[it] = np.average(X[mk, items.index(it)], weights=ww)
        rows.append(row)
    return pd.DataFrame(rows).sort_values("cons_z").reset_index(drop=True)


def voter_band(wave):
    """Robust (partition-free) moderate band: fraction of VOTERS with |cons z|<MOD."""
    c = pickle.load(open(io.out_dir(wave) / "fit_results.pkl", "rb"))["common"]
    X = c["_Xitems"]; w = c["w"]; pid = c["pid3"]
    R = em.regularize_corr(c["R"].copy())
    L1, _, _ = em.paf(R, 1); L1 = L1[:, 0] * (1 if L1[np.argmax(np.abs(L1[:, 0])), 0] >= 0 else -1)
    Z, _, _ = em.weighted_standardize(X, w)
    score = Z @ (np.linalg.inv(R) @ L1)
    m = np.average(score, weights=w); s = np.sqrt(np.average((score - m) ** 2, weights=w))
    z = (score - m) / s
    mod = np.abs(z) < MOD
    tot = w[mod].sum()
    return dict(wave=wave, kind=io.KIND[wave], moderate_pct=100 * tot / w.sum(),
                Dem=100 * w[mod & (pid == 1)].sum() / tot, Rep=100 * w[mod & (pid == 2)].sum() / tot,
                Ind=100 * w[mod & (pid == 3)].sum() / tot)


def main():
    print("VOTER-LEVEL moderate band (|conservatism z|<%.1f) — partition-free, measures polarization:" % MOD)
    print(f"  {'wave':>14} {'moderate%':>10} {'Dem':>5} {'Rep':>5} {'Ind':>5}")
    for wave in io.WAVES:
        b = voter_band(wave)
        print(f"  {wave+' '+io.KIND[wave]:>14} {b['moderate_pct']:>9.1f}% {b['Dem']:>4.0f} {b['Rep']:>4.0f} {b['Ind']:>4.0f}")

    for wave in io.WAVES:
        t = wave_table(wave)
        print(f"\n===== {wave} ({io.KIND[wave]}) — clusters sorted by conservatism (z) =====")
        print(f"  {'cl':>3} {'sh%':>5} {'consZ':>6} {'D/R/I':>12} | "
              f"{'brdr':>4} {'lgl':>4} {'gun':>4} {'abrt':>4} {'racRare':>7} {'slav':>4} {'chrch':>5}")
        for _, r in t.iterrows():
            tag = " <MID" if abs(r["cons_z"]) < MOD else ""
            print(f"  c{int(r['cluster']):>2} {r['share']:>5.1f} {r['cons_z']:>+6.2f} "
                  f"{r['Dem']:>3.0f}/{r['Rep']:>3.0f}/{r['Ind']:>3.0f} | "
                  f"{r['imm_border']:>4.2f} {r['imm_legalstatus']:>4.2f} {r['gun_concealcarry']:>4.2f} "
                  f"{r['abortion_rapeincest']:>4.2f} {r['race_problemsrare']:>7.2f} {r['race_slavery']:>4.2f} "
                  f"{r['relig_church']:>5.2f}{tag}")
        mid = t[t["cons_z"].abs() < MOD]
        msh = mid["share"].sum()
        if len(mid):
            wd = np.average(mid["Dem"], weights=mid["share"]); wr = np.average(mid["Rep"], weights=mid["share"])
            print(f"  MODERATE MIDDLE (|z|<{MOD}): {msh:.1f}% of electorate, "
                  f"makeup ~{wd:.0f}D/{wr:.0f}R, mean consZ={np.average(mid['cons_z'], weights=mid['share']):+.2f}")


if __name__ == "__main__":
    main()

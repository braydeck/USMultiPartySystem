"""Hierarchical Bayesian analysis of OUT-GROUP COLDNESS (not the in/out gap) vs electoral system.

Out-group coldness = 10 - (vote-share-weighted mean like/dislike a partisan gives to OTHER
parties). Higher = colder = more hostile to opponents. This matches the 'do I dislike people
for being on the other side' framing better than the in/out gap.

Two versions:
  coldness_all    coldness toward ALL out-parties
  coldness_mid    coldness among the MIDDLE clusters only: rater and targets both left-right
                  in [2,8] (excludes far-left <2 and far-right >8), so shared dislike of fringe
                  parties doesn't drive it.

Model: coldness ~ fptp + democracy_z + logpop_z + year_z + (1|region) + (1|country), on
established non-micro democracies and all democracies. Positive FPTP = FPTP systems colder.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import bambi as bmb

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_affpol import parse_dct, DAT, DCT, PARTIES as PP, CODE_SENTINEL

DATA = Path(__file__).resolve().parent.parent / "data"
MID_LO, MID_HI = 2.0, 8.0
MIN_ALL, MIN_MID = 100, 40
FIT = dict(draws=1000, tune=1500, chains=4, cores=4, random_seed=42, target_accept=0.95)


def val(s, lo, hi):
    x = pd.to_numeric(s, errors="coerce"); return x.where(x.between(lo, hi))


def wmean(v, w):
    m = ~np.isnan(v) & ~np.isnan(w)
    return np.average(v[m], weights=w[m]) if m.sum() else np.nan


def build_election_coldness():
    sp = parse_dct(DCT)
    cols = (["IMD1006_UNALPHA3", "IMD1008_YEAR", "IMD1010_2", "IMD3005_3"]
            + [f"IMD3008_{p}" for p in PP] + [f"IMD3007_{p}" for p in PP]
            + [f"IMD5000_{p}" for p in PP] + [f"IMD5001_{p}" for p in PP])
    df = pd.read_fwf(DAT, colspecs=[sp[c] for c in cols], names=cols, dtype=str)
    df = df.rename(columns={"IMD1006_UNALPHA3": "code", "IMD1008_YEAR": "year", "IMD1010_2": "w"})
    df = df[df.code.str.fullmatch(r"[A-Z]{3}", na=False)].copy()
    df["year"] = pd.to_numeric(df.year, errors="coerce")
    df["w"] = pd.to_numeric(df.w, errors="coerce"); df.loc[(df.w <= 0) | df.w.isna(), "w"] = 1.0
    like = np.column_stack([val(df[f"IMD3008_{p}"], 0, 10) for p in PP])
    lr = np.column_stack([val(df[f"IMD3007_{p}"], 0, 10) for p in PP])
    pid = np.column_stack([val(df[f"IMD5000_{p}"], 1, CODE_SENTINEL - 1) for p in PP])
    vs = np.column_stack([val(df[f"IMD5001_{p}"], 0, 100) for p in PP])
    inc = pd.to_numeric(df["IMD3005_3"], errors="coerce")
    incode = inc.where((inc > 0) & (inc < CODE_SENTINEL)).to_numpy(float)[:, None]

    # election-level perceived party LR (weighted mean of IMD3007 per letter)
    key = df["code"] + "_" + df["year"].astype("Int64").astype(str)
    lr_elec = np.full_like(lr, np.nan)
    for j in range(9):
        s = pd.DataFrame({"k": key, "lr": lr[:, j], "w": df.w.values}).dropna(subset=["lr"])
        m = s.groupby("k").apply(lambda x: np.average(x.lr, weights=x.w), include_groups=False)
        lr_elec[:, j] = key.map(m).values
    mid_party = (lr_elec >= MID_LO) & (lr_elec <= MID_HI)

    valid = ~np.isnan(like)
    inmask = valid & ~np.isnan(pid) & (pid == incode) & ~np.isnan(incode)
    has_in = inmask.sum(1) == 1
    in_lr = np.where(inmask, np.nan_to_num(lr_elec), 0).sum(1)
    outmask = valid & ~inmask

    def out_like(mask):
        ow = np.where(mask & ~np.isnan(vs), np.nan_to_num(vs), 0.0)
        no = (ow.sum(1) == 0) & mask.any(1)
        ow[no] = mask[no].astype(float)
        s = ow.sum(1, keepdims=True)
        return np.where(s.ravel() > 0, ((ow / np.where(s > 0, s, 1)) * np.nan_to_num(like)).sum(1), np.nan)

    df["ol_all"] = out_like(outmask)
    df["ol_mid"] = out_like(outmask & mid_party)
    df["has_in"] = has_in
    df["rater_mid"] = (in_lr >= MID_LO) & (in_lr <= MID_HI) & has_in

    def agg(g):
        a = g[g.has_in]; m = g[g.rater_mid & g.ol_mid.notna()]
        return pd.Series({"coldness_all": 10 - wmean(a.ol_all.values, a.w.values) if len(a) >= MIN_ALL else np.nan,
                          "coldness_mid": 10 - wmean(m.ol_mid.values, m.w.values) if len(m) >= MIN_MID else np.nan})
    return df.groupby(["code", "year"]).apply(agg, include_groups=False).reset_index()


def zc(s):
    return (s - s.mean()) / s.std()


def main():
    ce = build_election_coldness()
    pan = pd.read_parquet(DATA / "analysis_panel.parquet")[
        ["code", "year", "majoritarian_fptp", "democracy_score", "log_pop", "region",
         "microstate", "tier_established", "tier_all_democracies"]]
    d = ce.merge(pan, on=["code", "year"], how="inner")
    d["fptp"] = d.majoritarian_fptp
    for c in ["democracy_score", "log_pop", "year"]:
        d[c + "_z"] = zc(d[c])
    ce.to_csv(DATA / "coldness_election.csv", index=False)

    print("=== anglophone latest-wave coldness (higher = colder to opponents) ===")
    core = ["USA", "GBR", "CAN", "AUS", "NZL", "IRL", "ZAF", "IND"]
    for c in core:
        g = d[d.code == c].dropna(subset=["coldness_all"])
        if len(g):
            r = g.loc[g.year.idxmax()]
            print(f"  {c}: all={r.coldness_all:.2f}  middle={r.coldness_mid:.2f}")

    print("\n=== BAYESIAN: FPTP effect on out-group coldness (positive = FPTP colder) ===")
    for outcome in ["coldness_all", "coldness_mid"]:
        for uname, u in [("established non-micro", d[d.tier_established & (d.microstate == 0)]),
                         ("all democracies", d[d.tier_all_democracies])]:
            sub = u.dropna(subset=[outcome, "fptp", "democracy_score", "log_pop", "region", "code"]).copy()
            pr = {k: bmb.Prior("Normal", mu=0, sigma=1)
                  for k in ["fptp", "democracy_score_z", "log_pop_z", "year_z"]}
            f = f"{outcome} ~ fptp + democracy_score_z + log_pop_z + year_z + (1|region) + (1|code)"
            idata = bmb.Model(f, sub, priors=pr).fit(**FIT)
            v = idata.posterior["fptp"].values.reshape(-1)
            lo, hi = np.percentile(v, [3, 97]); p = (v > 0).mean()
            sig = ("Clearly" if max(p, 1 - p) >= .95 else "Likely" if max(p, 1 - p) >= .90
                   else "Possibly" if max(p, 1 - p) >= .80 else "Inconclusive")
            print(f"  {outcome:12s} {uname:22s}: FPTP {v.mean():+.3f} [{lo:+.2f},{hi:+.2f}] "
                  f"P(colder)={p:.2f} {sig} (elections={len(sub)}, FPTP ctys={sub[sub.fptp==1].code.nunique()})")


if __name__ == "__main__":
    main()

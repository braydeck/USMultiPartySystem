"""Additional CSES measures beyond the party affect gap, computed from IMD microdata:

  swd                 mean satisfaction with democracy (IMD3010, reversed: higher = more satisfied)
  wl_gap              winner-loser SWD gap = mean SWD(voted a governing party) - mean SWD(losers).
                      Winners = voted (IMD3002_LH_PL) for a party with >0 cabinet portfolios after
                      the election (IMD5031). Consensus-democracy theory (Anderson & Guillory)
                      predicts a SMALLER gap under PR/consensus institutions -- the mechanism
                      Bernaerts et al. invoke but don't test.
  leader_api          leader-based affective polarization: in-leader minus vote-share-weighted
                      out-leader like/dislike (IMD3009), in-party from IMD3005_3 (Garzia et al.).
  pid_strength        mean partisan-closeness strength (IMD3005_4, reversed; non-close = 0)
  efficacy            mean external efficacy (IMD3011, IMD3012, reversed: higher = more efficacy)

All aggregated to country-election (survey-weighted), then to country (mean across waves).
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_affpol import parse_dct, DAT, DCT  # reuse fixed-width parser + paths

DATA = Path(__file__).resolve().parent.parent / "data"
P = list("ABCDEFGHI")
CODE_SENTINEL = 9_000_000
MIN_RESP = 100
MIN_GROUP = 30

COLS = (["IMD1006_UNALPHA3", "IMD1008_YEAR", "IMD1010_2",
         "IMD3010", "IMD3011", "IMD3012", "IMD3005_3", "IMD3005_4",
         "IMD3002_LH_PL", "IMD3002_LH_DC"]
        + [f"IMD3009_{p}" for p in P] + [f"IMD5000_{p}" for p in P]
        + [f"IMD5001_{p}" for p in P] + [f"IMD5031_{p}" for p in P])


def val(s, lo, hi):
    x = pd.to_numeric(s, errors="coerce")
    return x.where(x.between(lo, hi))


def load():
    spans = parse_dct(DCT)
    cols = [c for c in COLS if c in spans]
    df = pd.read_fwf(DAT, colspecs=[spans[c] for c in cols], names=cols, dtype=str)
    df = df.rename(columns={"IMD1006_UNALPHA3": "code", "IMD1008_YEAR": "year",
                            "IMD1010_2": "w"})
    df = df[df.code.str.fullmatch(r"[A-Z]{3}", na=False)].copy()
    df["year"] = pd.to_numeric(df.year, errors="coerce")
    df["w"] = pd.to_numeric(df.w, errors="coerce")
    df.loc[(df.w <= 0) | (df.w > 100) | df.w.isna(), "w"] = 1.0
    df["swd"] = 5 - val(df["IMD3010"], 1, 4)                 # 1..4, higher = more satisfied
    df["eff1"] = 6 - val(df["IMD3011"], 1, 5)                # higher = more efficacy
    df["eff2"] = 6 - val(df["IMD3012"], 1, 5)
    df["efficacy"] = df[["eff1", "eff2"]].mean(axis=1)
    df["pid_str"] = (4 - val(df["IMD3005_4"], 1, 3)).fillna(0)  # 3=very..1=not; non-close -> 0
    inp = pd.to_numeric(df["IMD3005_3"], errors="coerce")
    df["inparty"] = inp.where((inp > 0) & (inp < CODE_SENTINEL))
    # FPTP/single-member systems record the vote as a district candidate (LH_DC), PR-list
    # systems as a party list (LH_PL); use whichever carries a real party code.
    pl = val(df["IMD3002_LH_PL"], 1, CODE_SENTINEL - 1)
    dc = val(df["IMD3002_LH_DC"], 1, CODE_SENTINEL - 1)
    df["voted"] = pl.fillna(dc)
    for p in P:
        df[f"ld_{p}"] = val(df[f"IMD3009_{p}"], 0, 10)
        df[f"pid_{p}"] = val(df[f"IMD5000_{p}"], 1, CODE_SENTINEL - 1)
        df[f"vs_{p}"] = val(df[f"IMD5001_{p}"], 0, 100)
        df[f"port_{p}"] = val(df[f"IMD5031_{p}"], 0, 899)    # cabinet portfolios after election
    return df


def _norm(w):
    s = w.sum(axis=1, keepdims=True)
    return np.divide(w, s, out=np.zeros_like(w), where=s > 0)


def compute(df):
    n = len(df)
    ld = df[[f"ld_{p}" for p in P]].to_numpy(float)
    pid = df[[f"pid_{p}" for p in P]].to_numpy(float)
    vs = df[[f"vs_{p}" for p in P]].to_numpy(float)
    port = df[[f"port_{p}" for p in P]].to_numpy(float)
    incode = df["inparty"].to_numpy(float)[:, None]
    voted = df["voted"].to_numpy(float)[:, None]

    # leader in/out affect gap
    valid = ~np.isnan(ld)
    inmask = valid & ~np.isnan(pid) & (pid == incode) & ~np.isnan(incode)
    has_in = inmask.sum(axis=1) == 1
    in_like = np.where(inmask, np.nan_to_num(ld), 0).sum(axis=1)
    outmask = valid & ~inmask
    ow = np.where(outmask & ~np.isnan(vs), np.nan_to_num(vs), 0.0)
    no_os = (ow.sum(axis=1) == 0) & outmask.any(axis=1)
    ow[no_os] = outmask[no_os].astype(float)
    out_like = (_norm(ow) * np.nan_to_num(ld)).sum(axis=1)
    df["leader_api"] = np.where(has_in & (ow.sum(axis=1) > 0), in_like - out_like, np.nan)

    # winner/loser: portfolios of the voted party
    votematch = ~np.isnan(pid) & (pid == voted) & ~np.isnan(voted)
    vport = np.where(votematch, np.nan_to_num(port), np.nan)
    vport = np.nanmax(np.where(votematch, port, np.nan), axis=1)  # portfolios of voted party
    df["winner"] = np.where(vport > 0, 1, np.where(vport == 0, 0, np.nan))
    return df


def wmean(v, w):
    m = v.notna() & w.notna()
    return np.average(v[m], weights=w[m]) if m.sum() >= MIN_GROUP else np.nan


def aggregate(df):
    def agg(g):
        win = g[g.winner == 1]; los = g[g.winner == 0]
        swd_w = wmean(win.swd, win.w); swd_l = wmean(los.swd, los.w)
        return pd.Series({
            "swd": wmean(g.swd, g.w),
            "wl_gap": (swd_w - swd_l) if (not np.isnan(swd_w) and not np.isnan(swd_l)) else np.nan,
            "leader_api": wmean(g.leader_api, g.w),
            "pid_strength": wmean(g.pid_str, g.w),
            "efficacy": wmean(g.efficacy, g.w),
            "n": len(g)})
    elec = df.groupby(["code", "year"]).apply(agg, include_groups=False).reset_index()
    elec = elec[elec.n >= MIN_RESP]
    elec.round(3).to_csv(DATA / "cses_extras_election.csv", index=False)
    country = elec.groupby("code").agg(
        swd=("swd", "mean"), wl_gap=("wl_gap", "mean"), leader_api=("leader_api", "mean"),
        pid_strength=("pid_strength", "mean"), efficacy=("efficacy", "mean"),
        n_elections=("n", "size")).reset_index().round(3)
    return elec, country


def main():
    df = compute(load())
    print(f"[winner/loser] classified {df.winner.notna().mean():.0%} of respondents; "
          f"leader API for {df.leader_api.notna().mean():.0%}")
    elec, country = aggregate(df)
    country.to_csv(DATA / "cses_extras.csv", index=False)
    print(f"[saved] cses_extras.csv: {len(country)} countries, {len(elec)} elections\n")

    pan = pd.read_parquet(DATA / "analysis_panel.parquet")
    snap = pan[pan.year.between(2015, 2024)].groupby("code").agg(
        fptp=("majoritarian_fptp", "last"), tier=("tier_established", "last"),
        micro=("microstate", "last")).reset_index()
    m = country.merge(snap, on="code")
    U = m[(m.tier) & (m.micro == 0)]

    print("=== Consensus-democracy mechanism: winner-loser satisfaction gap, PR vs FPTP ===")
    print("(theory: PR/consensus democracies keep LOSERS satisfied -> SMALLER gap)")
    for name, d in [("all matched democracies", m), ("established non-micro", U)]:
        for col, lab in [("wl_gap", "winner-loser SWD gap"), ("swd", "overall satisfaction"),
                         ("leader_api", "leader affective polariz."),
                         ("pid_strength", "partisan-ID strength"), ("efficacy", "external efficacy")]:
            dd = d.dropna(subset=[col, "fptp"])
            maj, prop = dd[dd.fptp == 1][col], dd[dd.fptp == 0][col]
            if len(maj) and len(prop):
                print(f"  [{name:24s}] {lab:26s} FPTP={maj.mean():+.3f} (n={len(maj)}) "
                      f"PR={prop.mean():+.3f} (n={len(prop)}) diff={maj.mean()-prop.mean():+.3f}")
        print()


if __name__ == "__main__":
    main()

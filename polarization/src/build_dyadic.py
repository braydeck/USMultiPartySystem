"""Dyadic decomposition of out-group sentiment: who is the hostility aimed at?

For every ordered pair (rater party i -> target party j) within a country-election, compute
how i's supporters rate j (0-10). Then test whether negative out-group sentiment is:
  - diffuse across all opponents, or
  - concentrated on ideologically EXTREME target parties (far-left / far-right),
which would mean our country/party 'polarization' partly captures shared dislike of a few
fringe parties rather than mutual mainstream hostility.

Separates two things that both make a target disliked:
  distance      |rater_LR - target_LR|  (you dislike parties far from you)
  target_extr   |target_LR - 5|         (fringe parties disliked regardless of the rater)
A negative target-extremeness effect NET of distance = a 'pariah' effect on extreme parties.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import bambi as bmb

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_affpol import parse_dct, DAT, DCT

DATA = Path(__file__).resolve().parent.parent / "data"
P = list("ABCDEFGHI")
SENT = 9_000_000
MIN_SUP = 30
FIT = dict(draws=1000, tune=1500, chains=4, cores=4, random_seed=42, target_accept=0.95)


def val(s, lo, hi):
    x = pd.to_numeric(s, errors="coerce")
    return x.where(x.between(lo, hi))


def build_dyads():
    sp = parse_dct(DCT)
    cols = (["IMD1006_UNALPHA3", "IMD1008_YEAR", "IMD1010_2", "IMD3005_3"]
            + [f"IMD3008_{p}" for p in P] + [f"IMD3007_{p}" for p in P]
            + [f"IMD5000_{p}" for p in P] + [f"IMD5001_{p}" for p in P])
    df = pd.read_fwf(DAT, colspecs=[sp[c] for c in cols], names=cols, dtype=str)
    df = df.rename(columns={"IMD1006_UNALPHA3": "code", "IMD1008_YEAR": "year", "IMD1010_2": "w"})
    df = df[df.code.str.fullmatch(r"[A-Z]{3}", na=False)].copy()
    df["year"] = pd.to_numeric(df.year, errors="coerce")
    df["w"] = pd.to_numeric(df.w, errors="coerce")
    df.loc[(df.w <= 0) | (df.w > 100) | df.w.isna(), "w"] = 1.0
    inc = pd.to_numeric(df["IMD3005_3"], errors="coerce"); df["incode"] = inc.where((inc > 0) & (inc < SENT))
    like = np.column_stack([val(df[f"IMD3008_{p}"], 0, 10) for p in P])
    pid = np.column_stack([val(df[f"IMD5000_{p}"], 1, SENT - 1) for p in P])
    incode = df["incode"].to_numpy(float)[:, None]
    inmask = ~np.isnan(like) & ~np.isnan(pid) & (pid == incode) & ~np.isnan(incode)
    has_in = inmask.sum(axis=1) == 1
    df["in_letter"] = np.where(has_in, inmask.argmax(axis=1), -1)
    df = df[has_in].copy()
    for j, p in enumerate(P):
        df[f"like_{j}"] = like[has_in][:, j]

    # rater i -> target j: weighted mean rating of j among supporters of i
    def wm(g):
        w = g.w.to_numpy()
        return pd.Series({j: np.average(g[f"like_{j}"], weights=w)
                          if g[f"like_{j}"].notna().sum() >= MIN_SUP else np.nan for j in range(9)}
                         | {"n_sup": len(g)})
    grp = df.groupby(["code", "year", "in_letter"]).apply(wm, include_groups=False).reset_index()
    grp = grp[grp.n_sup >= MIN_SUP]
    dy = grp.melt(id_vars=["code", "year", "in_letter", "n_sup"], value_vars=list(range(9)),
                  var_name="target", value_name="rating").dropna(subset=["rating"])
    dy = dy[dy.in_letter != dy.target]   # out-group only

    # party positions (LR, vote share) per election-letter
    lr = np.column_stack([val(df[f"IMD3007_{p}"], 0, 10) for p in P])  # note: df already in-party filtered
    # recompute LR/vs over ALL respondents (reload minimal to avoid the has_in filter bias)
    full = pd.read_fwf(DAT, colspecs=[sp[c] for c in cols], names=cols, dtype=str)
    full = full.rename(columns={"IMD1006_UNALPHA3": "code", "IMD1008_YEAR": "year", "IMD1010_2": "w"})
    full = full[full.code.str.fullmatch(r"[A-Z]{3}", na=False)].copy()
    full["year"] = pd.to_numeric(full.year, errors="coerce")
    full["w"] = pd.to_numeric(full.w, errors="coerce"); full.loc[(full.w <= 0) | full.w.isna(), "w"] = 1.0
    recs = []
    for j, p in enumerate(P):
        lrj = val(full[f"IMD3007_{p}"], 0, 10); vsj = val(full[f"IMD5001_{p}"], 0, 100)
        t = pd.DataFrame({"code": full.code.values, "year": full.year.values, "lr": lrj, "vs": vsj, "w": full.w})
        g = (t.dropna(subset=["lr"]).groupby(["code", "year"])
             .apply(lambda x: pd.Series({"lr": np.average(x.lr, weights=x.w), "vs": x.vs.mean()}),
                    include_groups=False).reset_index())
        g["letter"] = j; recs.append(g)
    pos = pd.concat(recs)
    dy = dy.merge(pos.rename(columns={"letter": "in_letter", "lr": "rater_lr"})[["code", "year", "in_letter", "rater_lr"]],
                  on=["code", "year", "in_letter"], how="left")
    dy = dy.merge(pos.rename(columns={"letter": "target", "lr": "target_lr", "vs": "target_vs"}),
                  on=["code", "year", "target"], how="left")
    dy = dy.dropna(subset=["rater_lr", "target_lr"])
    dy["distance"] = (dy.rater_lr - dy.target_lr).abs()
    dy["target_extr"] = (dy.target_lr - 5).abs()
    dy["target_bloc"] = pd.cut(dy.target_lr, [-.1, 2, 4, 6, 8, 10.1],
                               labels=["far-left", "left", "center", "right", "far-right"])
    return dy


def main():
    dy = build_dyads()
    pan = pd.read_parquet(DATA / "analysis_panel.parquet")
    snap = pan[pan.year.between(2010, 2024)].groupby("code").agg(
        fptp=("majoritarian_fptp", "last"), tier=("tier_established", "last"),
        micro=("microstate", "last")).reset_index()
    dy = dy.merge(snap, on="code", how="left")
    dy.to_csv(DATA / "dyadic_party_ratings.csv", index=False)
    U = dy[(dy.tier == True) & (dy.micro == 0)]
    print(f"[dyadic] {len(dy)} directed party pairs; established non-micro = {len(U)}\n")

    print("=== 1. How warmly is each TARGET bloc rated by out-groups? (0-10) ===")
    for bloc in ["far-left", "left", "center", "right", "far-right"]:
        s = U[U.target_bloc == bloc].rating
        print(f"  target = {bloc:9s}: mean received rating = {s.mean():.2f} (n_dyads={len(s)})")

    print("\n=== 2. Is out-group coldness concentrated on EXTREME targets? ===")
    ext = U[U.target_extr >= 2.5].rating; mod = U[U.target_extr < 2.5].rating
    print(f"  ratings GIVEN to extreme targets (|LR-5|>=2.5): {ext.mean():.2f} (n={len(ext)})")
    print(f"  ratings GIVEN to moderate targets           : {mod.mean():.2f} (n={len(mod)})")
    print(f"  gap = {mod.mean()-ext.mean():+.2f}  (positive => extreme parties are rated much colder)")

    print("\n=== 3. Distance vs target-extremeness (Bayesian; do extremes get a 'pariah' penalty?) ===")
    d = U.dropna(subset=["rating", "distance", "target_extr", "code"]).copy()
    d["dist_z"] = (d.distance - d.distance.mean()) / d.distance.std()
    d["ext_z"] = (d.target_extr - d.target_extr.mean()) / d.target_extr.std()
    pr = {k: bmb.Prior("Normal", mu=0, sigma=1) for k in ["dist_z", "ext_z"]}
    idata = bmb.Model("rating ~ dist_z + ext_z + (1|code)", d, priors=pr).fit(**FIT)
    for t, lab in [("dist_z", "ideological distance"), ("ext_z", "target extremeness")]:
        v = idata.posterior[t].values.reshape(-1)
        print(f"  {lab:22s}: {v.mean():+.3f}  94% CI [{np.percentile(v,3):+.2f}, {np.percentile(v,97):+.2f}]")
    print("  (both negative = colder; ext_z<0 NET of distance = extreme parties disliked as pariahs)")

    print("\n=== 4. Re-derive party out-group warmth EXCLUDING extreme targets ===")
    def party_warmth(sub):
        return sub.groupby(["code", "year", "in_letter", "fptp"]).apply(
            lambda g: np.average(g.rating, weights=g.target_vs.fillna(g.target_vs.mean()) + .01),
            include_groups=False).reset_index(name="warmth")
    allw = party_warmth(U); mainw = party_warmth(U[U.target_extr < 2.5])
    for name, w in [("all out-targets", allw), ("mainstream targets only", mainw)]:
        for f, lab in [(1, "FPTP"), (0, "PR")]:
            s = w[w.fptp == f].warmth
            if len(s): print(f"  [{name:24s}] {lab}: mean warmth={s.mean():.2f} (n={len(s)})")
    print("  (if excluding extremes raises warmth a lot, 'polarization' is partly anti-fringe sentiment)")


if __name__ == "__main__":
    main()

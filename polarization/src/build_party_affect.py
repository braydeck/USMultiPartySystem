"""Party-level out-group sentiment from CSES, and its relation to ideology and electoral system.

For each party (within a country-election), take its supporters (respondents whose in-party is
that party, via IMD3005_3) and compute how warmly they rate the OTHER parties (vote-share-
weighted mean like/dislike of out-parties, 0-10; LOWER = more negative out-group sentiment).
Attach the party's perceived left-right position (mean IMD3007, 0=left..10=right) and vote share.

Questions:
  1. Do parties in FPTP democracies show more out-group hostility than parties in PR democracies?
  2. How does out-group hostility relate to a party's leftness/rightness/centerness?
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
MIN_SUP = 30       # min supporters to estimate a party's out-group sentiment
FIT = dict(draws=1000, tune=1500, chains=4, cores=4, random_seed=42, target_accept=0.95)


def val(s, lo, hi):
    x = pd.to_numeric(s, errors="coerce")
    return x.where(x.between(lo, hi))


def build_party_level():
    spans = parse_dct(DCT)
    cols = (["IMD1006_UNALPHA3", "IMD1008_YEAR", "IMD1010_2", "IMD3005_3"]
            + [f"IMD3008_{p}" for p in P] + [f"IMD3007_{p}" for p in P]
            + [f"IMD5000_{p}" for p in P] + [f"IMD5001_{p}" for p in P])
    df = pd.read_fwf(DAT, colspecs=[spans[c] for c in cols], names=cols, dtype=str)
    df = df.rename(columns={"IMD1006_UNALPHA3": "code", "IMD1008_YEAR": "year", "IMD1010_2": "w"})
    df = df[df.code.str.fullmatch(r"[A-Z]{3}", na=False)].copy()
    df["year"] = pd.to_numeric(df.year, errors="coerce")
    df["w"] = pd.to_numeric(df.w, errors="coerce")
    df.loc[(df.w <= 0) | (df.w > 100) | df.w.isna(), "w"] = 1.0
    inc = pd.to_numeric(df["IMD3005_3"], errors="coerce")
    df["incode"] = inc.where((inc > 0) & (inc < SENT))
    like = np.column_stack([val(df[f"IMD3008_{p}"], 0, 10) for p in P])
    lr = np.column_stack([val(df[f"IMD3007_{p}"], 0, 10) for p in P])
    pid = np.column_stack([val(df[f"IMD5000_{p}"], 1, SENT - 1) for p in P])
    vs = np.column_stack([val(df[f"IMD5001_{p}"], 0, 100) for p in P])
    incode = df["incode"].to_numpy(float)[:, None]

    valid = ~np.isnan(like)
    inmask = valid & ~np.isnan(pid) & (pid == incode) & ~np.isnan(incode)
    has_in = inmask.sum(axis=1) == 1
    in_letter = np.where(has_in, inmask.argmax(axis=1), -1)
    outmask = valid & ~inmask
    ow = np.where(outmask & ~np.isnan(vs), np.nan_to_num(vs), 0.0)
    no_os = (ow.sum(axis=1) == 0) & outmask.any(axis=1)
    ow[no_os] = outmask[no_os].astype(float)
    s = ow.sum(axis=1, keepdims=True)
    own = np.divide(ow, s, out=np.zeros_like(ow), where=s > 0)
    out_warmth = (own * np.nan_to_num(like)).sum(axis=1)
    keep = has_in & (ow.sum(axis=1) > 0)

    sup = pd.DataFrame({"code": df.code.values, "year": df.year.values, "w": df.w.values,
                        "in_letter": in_letter, "out_warmth": out_warmth})[keep]
    # party out-group warmth = weighted mean over that party's supporters
    def wm(g):
        return pd.Series({"out_warmth": np.average(g.out_warmth, weights=g.w), "n_sup": len(g)})
    party = sup.groupby(["code", "year", "in_letter"]).apply(wm, include_groups=False).reset_index()
    party = party[party.n_sup >= MIN_SUP]

    # party LR position and vote share (weighted mean across ALL respondents, per letter)
    recs = []
    for j, p in enumerate(P):
        lrj = lr[:, j]; vsj = vs[:, j]; wj = df.w.to_numpy()
        tmp = pd.DataFrame({"code": df.code.values, "year": df.year.values,
                            "lr": lrj, "vs": vsj, "w": wj})
        g = (tmp.dropna(subset=["lr"]).groupby(["code", "year"])
             .apply(lambda x: pd.Series({"party_lr": np.average(x.lr, weights=x.w),
                                         "vote_share": x.vs.mean()}), include_groups=False)
             .reset_index())
        g["in_letter"] = j
        recs.append(g)
    pos = pd.concat(recs)
    party = party.merge(pos, on=["code", "year", "in_letter"], how="left")
    party = party.dropna(subset=["party_lr"])
    party["extremeness"] = (party.party_lr - 5).abs()
    party["bloc"] = np.where(party.party_lr < 4, "left",
                             np.where(party.party_lr > 6, "right", "center"))
    return party


def main():
    party = build_party_level()
    pan = pd.read_parquet(DATA / "analysis_panel.parquet")
    snap = pan[pan.year.between(2010, 2024)].groupby("code").agg(
        fptp=("majoritarian_fptp", "last"), tier=("tier_established", "last"),
        micro=("microstate", "last")).reset_index()
    party = party.merge(snap, on="code", how="left")
    party.to_csv(DATA / "party_outgroup_affect.csv", index=False)
    print(f"[saved] party_outgroup_affect.csv: {len(party)} parties across "
          f"{party.groupby(['code','year']).ngroups} elections, {party.code.nunique()} countries")
    print("out_warmth = supporters' mean rating of OTHER parties (0-10); LOWER = more hostile\n")

    U = party[(party.tier) & (party.micro == 0)].copy()
    print(f"[established non-micro: {len(U)} parties, {U.code.nunique()} countries, "
          f"FPTP countries={U[U.fptp==1].code.nunique()}]\n")

    print("=== 1. Out-group warmth by electoral system (party level) ===")
    for f, lab in [(1, "FPTP"), (0, "PR/other")]:
        s = U[U.fptp == f].out_warmth
        print(f"  {lab:9s}: mean out-group warmth = {s.mean():.2f}  (n_parties={len(s)}) "
              f"-> {'more hostile' if f==1 else ''}")

    print("\n=== 2. Out-group warmth by ideological bloc ===")
    for bloc in ["left", "center", "right"]:
        for f, lab in [(1, "FPTP"), (0, "PR")]:
            s = U[(U.bloc == bloc) & (U.fptp == f)].out_warmth
            if len(s) >= 5:
                print(f"  {bloc:7s} x {lab:4s}: warmth={s.mean():.2f} (n={len(s)})")
    print("\n  overall by bloc (all parties):")
    for bloc in ["left", "center", "right"]:
        s = U[U.bloc == bloc].out_warmth
        print(f"    {bloc:7s}: warmth={s.mean():.2f} (n={len(s)})")

    print("\n=== 3. Correlations (party level, established non-micro) ===")
    for a, b in [("out_warmth", "extremeness"), ("out_warmth", "party_lr"),
                 ("out_warmth", "vote_share")]:
        d = U.dropna(subset=[a, b])
        r = np.corrcoef(d[a], d[b])[0, 1]
        print(f"  corr({a}, {b}) = {r:+.3f} (n={len(d)})")
    print("  (negative corr with extremeness => extreme parties are COLDER to out-groups)")

    print("\n=== 4. Bayesian: party out-group warmth ~ FPTP + extremeness + LR, (1|country) ===")
    d = U.dropna(subset=["out_warmth", "fptp", "extremeness", "party_lr", "code"]).copy()
    d["ext_z"] = (d.extremeness - d.extremeness.mean()) / d.extremeness.std()
    d["lr_z"] = (d.party_lr - d.party_lr.mean()) / d.party_lr.std()
    d["fptp"] = d.fptp.astype(int)
    pr = {k: bmb.Prior("Normal", mu=0, sigma=1) for k in ["fptp", "ext_z", "lr_z"]}
    idata = bmb.Model("out_warmth ~ fptp + ext_z + lr_z + (1|code)", d, priors=pr).fit(**FIT)
    for t in ["fptp", "ext_z", "lr_z"]:
        v = idata.posterior[t].values.reshape(-1)
        lo, hi = np.percentile(v, [3, 97])
        print(f"  {t:7s}: {v.mean():+.3f}  94% CI [{lo:+.2f}, {hi:+.2f}]  P(>0)={(v>0).mean():.2f}")
    print("  (fptp<0 => FPTP parties colder; ext_z<0 => extreme parties colder)")


if __name__ == "__main__":
    main()

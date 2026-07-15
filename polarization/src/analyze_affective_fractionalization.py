"""Hudde, Horne, Adams & Gidron (2024)-style AFFECTIVE FRACTIONALIZATION.

Expected out-group coldness experienced in a random cross-party encounter, weighting each
directed party pair (i->j) by the probability two random citizens belong to parties i and j:

    AF_raw  = sum_{i != j} p_i p_j (10 - warmth(i->j))     (encounter-weighted; embeds both the
              probability of meeting an out-partisan AND how cold that meeting is)
    AF_norm = AF_raw / sum_{i != j} p_i p_j                 (coldness per cross-party encounter)

This is the structural claim behind the essay: a strict two-party system concentrates all
cross-party contact onto the single most-hostile dyad. Party shares from CSES IMD5001 vote
shares (reliable, incl. the US); dyadic warmth from dyadic_party_ratings.csv.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
import sys; sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_affpol import parse_dct, DAT, DCT, PARTIES
DATA = Path(__file__).resolve().parent.parent / "data"


def build_shares():
    sp = parse_dct(DCT)
    cols = ["IMD1006_UNALPHA3", "IMD1008_YEAR"] + [f"IMD5001_{p}" for p in PARTIES]
    df = pd.read_fwf(DAT, colspecs=[sp[c] for c in cols], names=cols, dtype=str)
    df = df.rename(columns={"IMD1006_UNALPHA3": "code", "IMD1008_YEAR": "year"})
    df = df[df.code.str.fullmatch(r"[A-Z]{3}", na=False)].copy()
    df["year"] = pd.to_numeric(df.year, errors="coerce")
    recs = []
    for (c, y), g in df.groupby(["code", "year"]):
        for pos, p in enumerate(PARTIES):
            v = pd.to_numeric(g[f"IMD5001_{p}"], errors="coerce").where(lambda x: x.between(0, 100)).dropna()
            if len(v):
                recs.append({"code": c, "year": int(y), "pos": pos, "vs": v.iloc[0]})
    s = pd.DataFrame(recs)
    s["p"] = s.vs / s.groupby(["code", "year"]).vs.transform("sum")
    return s


def main():
    sh = build_shares()
    dy = pd.read_csv(DATA / "dyadic_party_ratings.csv").dropna(subset=["rating", "fptp"])
    pi = sh.rename(columns={"pos": "in_letter", "p": "pi"})[["code", "year", "in_letter", "pi"]]
    pj = sh.rename(columns={"pos": "target", "p": "pj"})[["code", "year", "target", "pj"]]
    d = dy.merge(pi, on=["code", "year", "in_letter"], how="left").merge(pj, on=["code", "year", "target"], how="left")
    d = d.dropna(subset=["pi", "pj"])
    d["cold"] = 10 - d.rating; d["w"] = d.pi * d.pj
    el = d.groupby(["code", "year"]).apply(
        lambda g: pd.Series({"AF_raw": (g.w * g.cold).sum(), "cross_prob": g.w.sum(),
                             "AF_norm": (g.w * g.cold).sum() / g.w.sum(),
                             "fptp": g.fptp.iloc[0]}), include_groups=False).reset_index()
    # ENP + top-2 concentration from shares
    enp = sh.groupby(["code", "year"]).p.apply(lambda p: 1 / (p ** 2).sum()).reset_index(name="ENP")
    top2 = sh.groupby(["code", "year"]).p.apply(lambda p: np.sort(p)[::-1][:2].sum()).reset_index(name="top2")
    el = el.merge(enp, on=["code", "year"]).merge(top2, on=["code", "year"])
    el.loc[el.code.isin(["AUS", "FRA", "MLI", "CIV"]), "fptp"] = 0  # strict plurality
    el.to_csv(DATA / "affective_fractionalization.csv", index=False)
    cty = el.sort_values("year").groupby("code").tail(1)

    print("=== AFFECTIVE FRACTIONALIZATION ranking (latest election, higher = colder interactions) ===")
    r = cty.sort_values("AF_raw", ascending=False).reset_index(drop=True); r["rk"] = r.index + 1
    print(r[["rk", "code", "year", "AF_raw", "cross_prob", "AF_norm", "ENP", "top2", "fptp"]].round(2).head(12).to_string(index=False))
    print(f"  ... total ranked: {len(r)}")
    us = r[r.code == "USA"]
    print("  USA:", us[["rk", "AF_raw", "cross_prob", "AF_norm", "ENP", "top2"]].round(2).to_string(index=False, header=False))

    print("\n=== Decompose the US: high AF via (a) high encounter prob or (b) high per-encounter coldness? ===")
    u = cty[cty.code == "USA"].iloc[0]
    print(f"  US cross_prob={u.cross_prob:.2f} (rank {int((cty.cross_prob>u.cross_prob).sum()+1)} of {len(cty)}), "
          f"AF_norm={u.AF_norm:.2f} (rank {int((cty.AF_norm>u.AF_norm).sum()+1)}), "
          f"AF_raw rank {int((cty.AF_raw>u.AF_raw).sum()+1)}")
    print(f"  corr(AF_raw, top2 concentration) = {cty.AF_raw.corr(cty.top2):+.2f}")
    print(f"  corr(AF_raw, ENP)                = {cty.AF_raw.corr(cty.ENP):+.2f}")
    print(f"  AF_raw: FPTP={cty[cty.fptp==1].AF_raw.mean():.2f} vs PR={cty[cty.fptp==0].AF_raw.mean():.2f}")

    print("\n=== Anglophone ===")
    a = cty[cty.code.isin(["USA","GBR","CAN","IRL","AUS","NZL","ZAF"])].sort_values("AF_raw",ascending=False)
    print(a[["code","year","AF_raw","cross_prob","AF_norm","ENP","top2","fptp"]].round(2).to_string(index=False))


if __name__ == "__main__":
    main()

"""FPTP -> effective number of parties (ENP) -> polarization mediation.

Tests the 'duopoly completeness' mechanism directly: does FPTP raise polarization by
compressing the party system into few (ultimately two) parties? ENP (Laakso-Taagepera,
1/sum p_i^2) is computed from CSES lower-house vote shares (IMD5001). Outcomes: V-Dem
expert polarization (v2cacamps) and citizen out-group coldness.

  a  : FPTP -> ENP            (expect negative: FPTP -> fewer parties)
  b  : ENP -> polarization    (expect negative: fewer parties -> more polarized)
  a*b: indirect effect        (expect positive: FPTP more polarized via few parties)
  c' : direct FPTP effect with ENP held constant
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd, bambi as bmb
import sys; sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_affpol import parse_dct, DAT, DCT, PARTIES

DATA = Path(__file__).resolve().parent.parent / "data"
FIT = dict(draws=800, tune=1200, chains=4, cores=4, random_seed=42, target_accept=0.97, progressbar=False)


def z(s): return (s - s.mean()) / s.std()


def build_enp():
    sp = parse_dct(DCT)
    cols = ["IMD1006_UNALPHA3", "IMD1008_YEAR"] + [f"IMD5001_{p}" for p in PARTIES]
    df = pd.read_fwf(DAT, colspecs=[sp[c] for c in cols], names=cols, dtype=str)
    df = df.rename(columns={"IMD1006_UNALPHA3": "code", "IMD1008_YEAR": "year"})
    df = df[df.code.str.fullmatch(r"[A-Z]{3}", na=False)].copy()
    df["year"] = pd.to_numeric(df.year, errors="coerce")
    rows = []
    for (c, y), g in df.groupby(["code", "year"]):
        vs = [pd.to_numeric(g[f"IMD5001_{p}"], errors="coerce").where(lambda x: x.between(0, 100)).dropna()
              for p in PARTIES]
        shares = np.array([v.iloc[0] for v in vs if len(v)])
        if shares.sum() <= 0 or len(shares) < 1:
            continue
        p = shares / shares.sum()
        rows.append({"code": c, "year": int(y), "ENP": 1 / (p ** 2).sum(), "n_parties_vs": len(shares)})
    return pd.DataFrame(rows)


def med(d, outcome, treat="fptp"):
    d = d.dropna(subset=[outcome, treat, "ENP", "code", "region"]).copy()
    d["y"] = z(d[outcome]); d["enp_z"] = z(d["ENP"]); d[treat] = d[treat].astype(int)
    P = {k: bmb.Prior("Normal", mu=0, sigma=1) for k in [treat, "enp_z"]}
    mA = bmb.Model(f"enp_z ~ {treat} + (1|region) + (1|code)", d, priors={treat: P[treat]}).fit(**FIT)
    mC = bmb.Model(f"y ~ {treat} + (1|region) + (1|code)", d, priors={treat: P[treat]}).fit(**FIT)
    mY = bmb.Model(f"y ~ {treat} + enp_z + (1|region) + (1|code)", d, priors=P).fit(**FIT)
    a = mA.posterior[treat].values.reshape(-1)
    c = mC.posterior[treat].values.reshape(-1)
    cp = mY.posterior[treat].values.reshape(-1)
    b = mY.posterior["enp_z"].values.reshape(-1)
    ind = a * b
    def r(v): return f"{v.mean():+.3f} [{np.percentile(v,3):+.2f}, {np.percentile(v,97):+.2f}]"
    print(f"\n  outcome = {outcome}  (n={len(d)}, countries={d.code.nunique()}, "
          f"FPTP={d[d[treat]==1].code.nunique()})")
    print(f"    a  FPTP -> ENP (z)              : {r(a)}  P(<0)={(a<0).mean():.2f}")
    print(f"    b  ENP -> {outcome[:14]:14s}: {r(b)}  P(<0)={(b<0).mean():.2f}")
    print(f"    c  total FPTP -> outcome        : {r(c)}  P(>0)={(c>0).mean():.2f}")
    print(f"    c' direct FPTP (ENP held)       : {r(cp)}  P(>0)={(cp>0).mean():.2f}")
    print(f"    a*b indirect (via ENP)          : {r(ind)}  P(>0)={(ind>0).mean():.2f}")
    if abs(c.mean()) > 1e-6:
        print(f"    proportion mediated by ENP      : {ind.mean()/c.mean():.0%}")


def main():
    enp = build_enp()
    enp.to_csv(DATA / "enp_by_election.csv", index=False)
    pan = pd.read_parquet(DATA / "analysis_panel.parquet")
    d = enp.merge(pan[["code", "year", "polarization", "majoritarian_fptp", "region",
                       "microstate", "tier_established", "tier_all_democracies", "anglophone"]],
                  on=["code", "year"], how="left")
    for t in ["tier_established","tier_all_democracies"]:
        d[t]=d[t].fillna(False).astype(bool)
    d["fptp"] = d.majoritarian_fptp
    d.loc[d.code.isin(["AUS", "FRA", "MLI", "CIV"]), "fptp"] = 0   # strict plurality FPTP

    print("=== ENP sanity check (lowest = most two-party) ===")
    cty = d.sort_values("year").groupby("code").tail(1)
    print("  lowest-ENP:", list(cty.nsmallest(6, "ENP")[["code", "ENP"]].round(2).itertuples(index=False, name=None)))
    print(f"  US ENP = {cty[cty.code=='USA'].ENP.iloc[0]:.2f}")
    print(f"  ENP: strict-FPTP mean={cty[cty.fptp==1].ENP.mean():.2f} vs PR mean={cty[cty.fptp==0].ENP.mean():.2f}")
    print(f"  corr(ENP, polarization) = {cty.ENP.corr(cty.polarization):+.3f} (neg = fewer parties, more polarized)")

    print("\n=== MEDIATION: established liberal democracies (expert measure) ===")
    U = d[d.tier_established & (d.microstate == 0)]
    med(U, "polarization")

    print("\n=== MEDIATION: all democracies (expert measure) ===")
    med(d[d.tier_all_democracies], "polarization")

    # citizen coldness outcome
    cold = pd.read_csv(DATA / "coldness_election.csv")
    dc = d.merge(cold, on=["code", "year"], how="inner")
    print("\n=== MEDIATION: citizen out-group coldness (all democracies) ===")
    med(dc[dc.tier_all_democracies], "coldness_all")


if __name__ == "__main__":
    main()

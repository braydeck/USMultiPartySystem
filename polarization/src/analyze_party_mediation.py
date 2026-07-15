"""(a) Broaden the party-level FPTP estimate to all democracies (more FPTP countries), and
(b) test the mediation FPTP -> bigger/fewer parties -> colder out-group sentiment.

Party-level out-group warmth (0-10; lower = more hostile) from party_outgroup_affect.csv.
Mediator = party vote share (FPTP concentrates support into fewer, bigger parties). Bayesian
throughout (partial pooling by country) given the small number of FPTP countries.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import bambi as bmb

DATA = Path(__file__).resolve().parent.parent / "data"
FIT = dict(draws=1000, tune=1500, chains=4, cores=4, random_seed=42, target_accept=0.95)


def z(s):
    return (s - s.mean()) / s.std()


def fptp_coef(idata):
    v = idata.posterior["fptp"].values.reshape(-1)
    return v.mean(), np.percentile(v, 3), np.percentile(v, 97), (v > 0).mean(), v


def load():
    p = pd.read_csv(DATA / "party_outgroup_affect.csv")
    pan = pd.read_parquet(DATA / "analysis_panel.parquet")
    snap = pan[pan.year.between(2010, 2024)].groupby("code").agg(
        alldem=("tier_all_democracies", "last")).reset_index()
    p = p.merge(snap, on="code", how="left")
    p = p.dropna(subset=["out_warmth", "fptp", "extremeness", "party_lr", "vote_share", "code"]).copy()
    p["fptp"] = p.fptp.astype(int)
    p["ext_z"] = z(p.extremeness); p["lr_z"] = z(p.party_lr); p["vs_z"] = z(p.vote_share)
    return p


def main():
    p = load()
    est = p[(p.tier == True) & (p.micro == 0)]
    alld = p[p.alldem == True]

    print("=== (a) BROADEN: party-level FPTP effect on out-group warmth, by universe ===")
    print("(negative = FPTP parties colder to out-groups)\n")
    for name, d in [("established non-micro", est), ("ALL democracies", alld)]:
        pr = {k: bmb.Prior("Normal", mu=0, sigma=1) for k in ["fptp", "ext_z", "lr_z"]}
        idata = bmb.Model("out_warmth ~ fptp + ext_z + lr_z + (1|code)", d, priors=pr).fit(**FIT)
        m, lo, hi, pg, _ = fptp_coef(idata)
        print(f"  {name:22s}: FPTP {m:+.3f}  94% CI [{lo:+.2f},{hi:+.2f}]  P(colder)={1-pg:.2f}  "
              f"(parties={len(d)}, countries={d.code.nunique()}, FPTP countries={d[d.fptp==1].code.nunique()})")

    print("\n=== (b) MEDIATION: FPTP -> party size (vote share) -> out-group coldness ===")
    d = alld  # use the broader set for more FPTP countries
    print(f"(all democracies: {len(d)} parties, {d.code.nunique()} countries, "
          f"{d[d.fptp==1].code.nunique()} FPTP)\n")
    pr = {k: bmb.Prior("Normal", mu=0, sigma=1) for k in ["fptp", "vs_z", "ext_z", "lr_z"]}

    # a-path: FPTP -> party vote share
    mA = bmb.Model("vs_z ~ fptp + (1|code)", d, priors={"fptp": bmb.Prior("Normal", mu=0, sigma=1)}).fit(**FIT)
    a = mA.posterior["fptp"].values.reshape(-1)
    # total effect c: FPTP -> warmth (no mediator)
    mC = bmb.Model("out_warmth ~ fptp + ext_z + lr_z + (1|code)", d,
                   priors={k: bmb.Prior("Normal", mu=0, sigma=1) for k in ["fptp", "ext_z", "lr_z"]}).fit(**FIT)
    c = mC.posterior["fptp"].values.reshape(-1)
    # outcome model with mediator: direct c' and mediator slope b
    mY = bmb.Model("out_warmth ~ fptp + vs_z + ext_z + lr_z + (1|code)", d, priors=pr).fit(**FIT)
    cp = mY.posterior["fptp"].values.reshape(-1)
    b = mY.posterior["vs_z"].values.reshape(-1)

    indirect = a * b                       # FPTP -> size -> warmth
    prop = indirect.mean() / c.mean()

    def rep(name, v):
        print(f"  {name:38s} {v.mean():+.3f}  94% CI [{np.percentile(v,3):+.2f}, {np.percentile(v,97):+.2f}]")
    rep("a  FPTP -> vote share (z)", a)
    rep("b  vote share -> warmth", b)
    rep("c  total FPTP -> warmth", c)
    rep("c' direct FPTP -> warmth (size held)", cp)
    rep("a*b indirect (via party size)", indirect)
    print(f"\n  Proportion of the FPTP effect mediated by party size: {prop:.0%}")
    print("  Interpretation: a>0 (FPTP parties bigger), b<0 (bigger parties colder) => "
          "indirect<0 (FPTP colder via size).")
    print(f"  Direct effect shrinks {c.mean():+.2f} -> {cp.mean():+.2f} when size is held constant.")


if __name__ == "__main__":
    main()

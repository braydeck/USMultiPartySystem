"""Primary out-group measure: hostility AMONG the middle clusters.

The dyadic decomposition showed out-group coldness is distance-driven, and the fringe blocs
(far-left, far-right) absorb disproportionate hostility that is partly cordon-sanitaire consensus
rather than polarization. So the cleaner measure of genuine polarization is out-group sentiment
*within the broad middle* -- both rater and target among the left/center/right clusters
(left-right position in [2,8]), excluding the far-left (<2) and far-right (>8) blocs entirely.

Recomputes party-level and country-level out-group warmth on the middle clusters and re-runs the
FPTP comparison (Bayesian, partial pooling), against the all-targets version for contrast.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import bambi as bmb

DATA = Path(__file__).resolve().parent.parent / "data"
FIT = dict(draws=1000, tune=1500, chains=4, cores=4, random_seed=42, target_accept=0.95)
MID_LO, MID_HI = 2.0, 8.0     # middle clusters: left/center/right, excluding the two fringes


def z(s):
    return (s - s.mean()) / s.std()


def fptp(idata):
    v = idata.posterior["fptp"].values.reshape(-1)
    return v.mean(), np.percentile(v, 3), np.percentile(v, 97), (v < 0).mean()


def load():
    dy = pd.read_csv(DATA / "dyadic_party_ratings.csv")
    pan = pd.read_parquet(DATA / "analysis_panel.parquet")
    snap = pan[pan.year.between(2010, 2024)].groupby("code").agg(
        alldem=("tier_all_democracies", "last")).reset_index()
    dy = dy.merge(snap, on="code", how="left")
    dy["tw"] = dy.target_vs.fillna(dy.target_vs.median()) + 0.01   # target weight
    return dy


def party_warmth(dy):
    """weighted mean rating a party's supporters give to out-parties in the set."""
    def wm(g):
        return pd.Series({"warmth": np.average(g.rating, weights=g.tw), "rater_lr": g.rater_lr.iloc[0],
                          "n": len(g)})
    p = dy.groupby(["code", "year", "in_letter", "fptp", "tier", "micro", "alldem"]).apply(
        wm, include_groups=False).reset_index()
    p["ext"] = (p.rater_lr - 5).abs()
    return p


def run_party(p, label):
    for name, d in [("established non-micro", p[(p.tier == True) & (p.micro == 0)]),
                    ("all democracies", p[p.alldem == True])]:
        d = d.dropna(subset=["warmth", "fptp", "ext", "rater_lr", "code"]).copy()
        d["fptp"] = d.fptp.astype(int); d["ext_z"] = z(d.ext); d["lr_z"] = z(d.rater_lr)
        pr = {k: bmb.Prior("Normal", mu=0, sigma=1) for k in ["fptp", "ext_z", "lr_z"]}
        idata = bmb.Model("warmth ~ fptp + ext_z + lr_z + (1|code)", d, priors=pr).fit(**FIT)
        m, lo, hi, pc = fptp(idata)
        print(f"  {label:18s} {name:22s}: FPTP {m:+.3f} [{lo:+.2f},{hi:+.2f}] "
              f"P(FPTP colder)={pc:.2f} (parties={len(d)}, FPTP ctys={d[d.fptp==1].code.nunique()})")


def main():
    dy = load()
    mid = dy[(dy.rater_lr.between(MID_LO, MID_HI)) & (dy.target_lr.between(MID_LO, MID_HI))]
    print(f"[middle clusters] {len(mid)} of {len(dy)} dyads are middle->middle "
          f"({len(mid)/len(dy):.0%})\n")

    # descriptive: FPTP vs PR warmth, all-targets vs middle-only
    print("=== FPTP vs PR out-group warmth (party level, established non-micro) ===")
    for lab, d in [("all targets", dy), ("middle clusters only", mid)]:
        p = party_warmth(d); U = p[(p.tier == True) & (p.micro == 0)]
        maj, pro = U[U.fptp == 1].warmth, U[U.fptp == 0].warmth
        print(f"  {lab:22s}: FPTP={maj.mean():.2f} PR={pro.mean():.2f} gap={maj.mean()-pro.mean():+.2f}")

    print("\n=== Bayesian FPTP effect on out-group warmth (negative = FPTP colder) ===")
    run_party(party_warmth(dy), "ALL TARGETS")
    run_party(party_warmth(mid), "MIDDLE CLUSTERS")

    # country-level middle-cluster out-group warmth
    print("\n=== Country-election middle-cluster warmth, FPTP effect (Bayesian) ===")
    ce = mid.groupby(["code", "year", "fptp", "tier", "micro", "alldem"]).apply(
        lambda g: np.average(g.rating, weights=g.tw), include_groups=False).reset_index(name="warmth")
    for name, d in [("established non-micro", ce[(ce.tier == True) & (ce.micro == 0)]),
                    ("all democracies", ce[ce.alldem == True])]:
        d = d.dropna(subset=["warmth", "fptp", "code"]).copy(); d["fptp"] = d.fptp.astype(int)
        idata = bmb.Model("warmth ~ fptp + (1|code)", d,
                          priors={"fptp": bmb.Prior("Normal", mu=0, sigma=1)}).fit(**FIT)
        m, lo, hi, pc = fptp(idata)
        print(f"  {name:22s}: FPTP {m:+.3f} [{lo:+.2f},{hi:+.2f}] P(colder)={pc:.2f} "
              f"(elections={len(d)}, FPTP ctys={d[d.fptp==1].code.nunique()})")


if __name__ == "__main__":
    main()

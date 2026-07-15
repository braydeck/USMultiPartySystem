"""Hierarchical Bayesian analysis of all CSES polarization-relevant outcomes vs electoral system.

At the CSES country level there are only ~6-9 FPTP democracies, so frequentist cluster-robust
SEs are unreliable. This uses election-level observations with partial pooling by country and
region (the low-N-appropriate method matching analyze_bayes.py), and reports posterior mean,
94% credible interval, and P(effect>0) for the FPTP coefficient on each outcome.

Outcomes:
  affect_gap    party in/out affective polarization  (affective_polarization_election.csv)
  leader_api    leader in/out affective polarization  (cses_extras_election.csv)
  wl_gap        winner-loser satisfaction gap
  swd           overall satisfaction with democracy
  pid_strength  partisan-ID strength
  efficacy      external efficacy

Positive FPTP coefficient = higher on that outcome under first-past-the-post.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import bambi as bmb

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
SEED = 42
CRED = 0.94
_LO, _HI = (1 - CRED) / 2 * 100, (1 + CRED) / 2 * 100
FIT = dict(draws=1000, tune=1500, chains=4, cores=4, random_seed=SEED, target_accept=0.95)


def zscore(s):
    return (s - s.mean()) / s.std()


def signal(p):
    q = max(p, 1 - p)
    d = "higher" if p >= 0.5 else "lower"
    return (f"Clearly {d}" if q >= 0.95 else f"Likely {d}" if q >= 0.90
            else f"Possibly {d}" if q >= 0.80 else "Inconclusive")


def load():
    ex = pd.read_csv(DATA / "cses_extras_election.csv")
    ap = pd.read_csv(DATA / "affective_polarization_election.csv")[["code", "year", "affpol_api"]]
    d = ex.merge(ap, on=["code", "year"], how="outer").rename(columns={"affpol_api": "affect_gap"})
    pan = pd.read_parquet(DATA / "analysis_panel.parquet")[
        ["code", "year", "majoritarian_fptp", "democracy_score", "log_pop", "region",
         "microstate", "tier_established", "tier_all_democracies"]]
    d = d.merge(pan, on=["code", "year"], how="inner")
    d["fptp"] = d["majoritarian_fptp"]
    for c in ["democracy_score", "log_pop", "year"]:
        d[c + "_z"] = zscore(d[c])
    return d


def run(d, outcome, label):
    sub = d.dropna(subset=[outcome, "fptp", "democracy_score", "log_pop", "region", "code"]).copy()
    n_fptp = sub[sub.fptp == 1].code.nunique()
    n_cty = sub.code.nunique()
    if sub[outcome].nunique() < 5 or n_cty < 8 or n_fptp < 2:
        print(f"  {label:14s} {outcome:13s}: skipped (n_countries={n_cty}, FPTP={n_fptp})")
        return
    priors = {k: bmb.Prior("Normal", mu=0, sigma=1)
              for k in ["fptp", "democracy_score_z", "log_pop_z", "year_z"]}
    f = f"{outcome} ~ fptp + democracy_score_z + log_pop_z + year_z + (1|region) + (1|code)"
    idata = bmb.Model(f, sub, priors=priors).fit(**FIT)
    fp = idata.posterior["fptp"].values.reshape(-1)
    lo, hi = np.percentile(fp, [_LO, _HI])
    print(f"  {label:14s} {outcome:13s}: FPTP {fp.mean():+.3f}  94% CI [{lo:+.2f},{hi:+.2f}]  "
          f"P(>0)={(fp>0).mean():.2f}  {signal(float((fp>0).mean()))}  "
          f"(elections={len(sub)}, countries={n_cty}, FPTP={n_fptp})")


def main():
    d = load()
    outcomes = ["affect_gap", "leader_api", "wl_gap", "swd", "pid_strength", "efficacy"]
    print("=== Hierarchical Bayesian: FPTP effect on CSES outcomes (partial pooling) ===")
    print("positive = higher under FPTP; wl_gap>0 under FPTP = consensus-mechanism direction\n")
    print("[established non-micro democracies]")
    U = d[d.tier_established & (d.microstate == 0)]
    for o in outcomes:
        run(U, o, "established")
    print("\n[all democracies]")
    D = d[d.tier_all_democracies]
    for o in outcomes:
        run(D, o, "all-dem")


if __name__ == "__main__":
    main()

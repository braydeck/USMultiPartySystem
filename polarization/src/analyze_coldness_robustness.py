"""Robustness re-analysis of the out-group COLDNESS result, addressing three problems:

  1. Treatment definition. The original `majoritarian_fptp` = V-Dem v2elparlel==0, which lumps
     genuine single-member plurality (FPTP: USA, UK, Canada, Kenya, India) together with the
     Alternative Vote (Australia) and two-round runoff (France) -- neither of which is FPTP, and
     both of which sustain multiparty competition. `fptp_strict` keeps only plurality systems.
  2. Anglophone / common-law confound. FPTP is heavily British-common-law. We add `common_law`
     (La Porta legal origin) as a covariate so the FPTP coefficient is net of legal heritage.
     Identifying variation = anglophone/common-law PR cases (Ireland STV, NZ MMP, South Africa
     PR-list, Australia AV) vs FPTP US/UK/Canada.
  3. We report the within-anglophone descriptive comparison directly (the cleanest test), and
     Canada as the internal control (same FPTP system as US/UK, same heritage).

Outcome = out-group coldness (10 - vote-share-weighted out-party warmth), all targets and middle
clusters. Positive FPTP coefficient = FPTP colder to opponents.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import bambi as bmb

DATA = Path(__file__).resolve().parent.parent / "data"
FIT = dict(draws=1000, tune=1500, chains=4, cores=4, random_seed=42, target_accept=0.9)
# Non-plurality majoritarian systems mis-coded as FPTP by v2elparlel==0:
TWO_ROUND = ["FRA", "MLI", "CIV"]   # two-round runoff (multiparty, not plurality)
AV = ["AUS"]                         # Alternative Vote + STV senate (not plurality)


def z(s):
    return (s - s.mean()) / s.std()


def signal(p):
    q = max(p, 1 - p)
    return ("Clearly" if q >= 0.95 else "Likely" if q >= 0.90
            else "Possibly" if q >= 0.80 else "Inconclusive")


def load():
    cold = pd.read_csv(DATA / "coldness_election.csv")
    pan = pd.read_parquet(DATA / "analysis_panel.parquet")
    cov = pan[["code", "year", "majoritarian_fptp", "anglophone", "common_law",
               "democracy_score", "log_pop", "region", "microstate",
               "tier_established", "tier_all_democracies"]]
    d = cold.merge(cov, on=["code", "year"])
    d["fptp_maj"] = d["majoritarian_fptp"]
    d["fptp_strict"] = d["majoritarian_fptp"].where(~d.code.isin(TWO_ROUND + AV), 0)
    d["common_law"] = d["common_law"].astype(float)
    d["anglophone"] = d["anglophone"].astype(float)
    return d


def fit(d, outcome, treat, controls, universe):
    if universe == "established":
        u = d[d.tier_established & (d.microstate == 0)]
    else:
        u = d[d.tier_all_democracies]
    sub = u.dropna(subset=[outcome, treat, "democracy_score", "log_pop", "region", "code"]).copy()
    sub["fptp"] = sub[treat].astype(int)
    for c in ["democracy_score", "log_pop", "year"]:
        sub[c + "_z"] = z(sub[c])
    terms = ["fptp", "democracy_score_z", "log_pop_z", "year_z"] + controls
    pr = {t: bmb.Prior("Normal", mu=0, sigma=1) for t in terms}
    formula = f"{outcome} ~ " + " + ".join(terms) + " + (1|region) + (1|code)"
    idata = bmb.Model(formula, sub, priors=pr).fit(**FIT)
    v = idata.posterior["fptp"].values.reshape(-1)
    lo, hi = np.percentile(v, [3, 97]); p = (v > 0).mean()
    nf = sub[sub.fptp == 1].code.nunique()
    return dict(mean=v.mean(), lo=lo, hi=hi, p=p, nf=nf, n=len(sub),
                fptp_ctys=sorted(sub[sub.fptp == 1].code.unique()))


def main():
    d = load()

    print("=" * 78)
    print("A. WITHIN-ANGLOPHONE descriptive comparison (all common-law, English-speaking)")
    print("=" * 78)
    ang = (d[d.anglophone == 1].sort_values(["code", "year"])
           .groupby("code").agg(year=("year", "last"),
                                cold_all=("coldness_all", "mean"),
                                cold_mid=("coldness_mid", "mean"),
                                fptp_strict=("fptp_strict", "last"),
                                indem=("tier_all_democracies", "last")).reset_index())
    print(ang.to_string(index=False))
    reg = ang[ang.indem == True]   # regression-eligible (India excluded: electoral autocracy)
    for col in ["cold_all", "cold_mid"]:
        f = reg[reg.fptp_strict == 1][col]; p = reg[reg.fptp_strict == 0][col]
        print(f"  [democracy-eligible] {col}: FPTP={f.mean():.2f} ({sorted(reg[reg.fptp_strict==1].code)}) "
              f"vs PR/other={p.mean():.2f} ({sorted(reg[reg.fptp_strict==0].code)}) gap={f.mean()-p.mean():+.2f}")

    print("\n" + "=" * 78)
    print("B. BAYESIAN: FPTP effect on coldness, WITH common_law control (positive = FPTP colder)")
    print("=" * 78)
    specs = [
        ("coldness_all", "fptp_maj", [], "all", "majoritarian (orig), NO heritage control"),
        ("coldness_all", "fptp_maj", ["common_law"], "all", "majoritarian (orig) + common_law"),
        ("coldness_all", "fptp_strict", [], "all", "strict FPTP, NO heritage control"),
        ("coldness_all", "fptp_strict", ["common_law"], "all", "strict FPTP + common_law"),
        ("coldness_mid", "fptp_strict", ["common_law"], "all", "strict FPTP + common_law [MID]"),
        ("coldness_all", "fptp_strict", ["common_law"], "established", "strict FPTP + common_law [EST]"),
        ("coldness_mid", "fptp_strict", ["common_law"], "established", "strict FPTP + common_law [EST,MID]"),
    ]
    rows = []
    for outcome, treat, controls, uni, label in specs:
        r = fit(d, outcome, treat, controls, uni)
        rows.append((label, r))
        print(f"\n  {label}")
        print(f"    FPTP {r['mean']:+.3f}  94% CI [{r['lo']:+.2f}, {r['hi']:+.2f}]  "
              f"P(colder)={r['p']:.2f}  {signal(r['p'])}")
        print(f"    (elections={r['n']}, FPTP countries={r['nf']}: {r['fptp_ctys']})")

    print("\n" + "=" * 78)
    print("SUMMARY: does the FPTP coldness effect survive the heritage control + clean treatment?")
    print("=" * 78)
    for label, r in rows:
        print(f"  {label:42s}: {r['mean']:+.2f} [{r['lo']:+.2f},{r['hi']:+.2f}] P={r['p']:.2f} {signal(r['p'])}")


if __name__ == "__main__":
    main()

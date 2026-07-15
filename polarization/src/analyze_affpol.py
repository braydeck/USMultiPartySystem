"""Test the electoral-system thesis against affective polarization from CSES.

Primary measure: the in-party/out-party affect gap (Reiljan 2020 / Gidron-Adams-Horne) --
how much a partisan likes their own party minus the (vote-share-weighted) mean of the other
parties. This operationalizes "do I dislike people because they support the other side?" and
is the measure used in the electoral-systems literature. The Wagner "spread" (SD of all party
ratings) is kept as a labeled robustness measure; the two can diverge because spread rewards
dispersion across many parties while the in/out gap rewards a single clear opponent.

Cross-sectional: affective polarization is measured only in election years, so each country's
latest CSES wave is compared with a recent (2015-2024) panel snapshot; the hierarchical
Bayesian models use all election-level observations with partial pooling.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import bambi as bmb

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
OUT = BASE / "outputs"

SEED = 42
CRED = 0.94
_LO, _HI = (1 - CRED) / 2 * 100, (1 + CRED) / 2 * 100
FIT = dict(draws=1000, tune=1500, chains=4, cores=4, random_seed=SEED, target_accept=0.95)


def zscore(s):
    return (s - s.mean()) / s.std()


def cred_int(d):
    return np.percentile(d, _LO), np.percentile(d, _HI)


def signal(p):
    q = max(p, 1 - p)
    d = "higher" if p >= 0.5 else "lower"
    return (f"Clearly {d} (strong)" if q >= 0.95 else f"Likely {d} (moderate)" if q >= 0.90
            else f"Possibly {d} (directional)" if q >= 0.80 else "Inconclusive")


def corr(a, b):
    m = a.notna() & b.notna()
    return float(np.corrcoef(a[m], b[m])[0, 1]), int(m.sum())


def group_diff(d, col):
    maj, prop = d.loc[d.fptp == 1, col].dropna(), d.loc[d.fptp == 0, col].dropna()
    rng = np.random.default_rng(SEED)
    boot = np.array([rng.choice(maj, len(maj)).mean() - rng.choice(prop, len(prop)).mean()
                     for _ in range(10000)])
    return maj.mean(), prop.mean(), maj.mean() - prop.mean(), np.percentile(boot, [2.5, 97.5])


def country_snapshot() -> pd.DataFrame:
    df = pd.read_parquet(DATA / "analysis_panel.parquet")
    df = df[df.year.between(2015, 2024)]
    return (df.groupby("code")
            .agg(elite_pol=("polarization", "mean"), fptp=("majoritarian_fptp", "last"),
                 elec_family=("elec_family", "last"), democracy=("democracy_score", "mean"),
                 anglophone=("anglophone", "last"), tier_established=("tier_established", "last"),
                 tier_all_dem=("tier_all_democracies", "last"), microstate=("microstate", "last"))
            .reset_index())


def bayes_affpol():
    """Hierarchical Bayesian model on election-level in/out API (partial pooling by
    country/region) -- the small-N-appropriate method, matching analyze_bayes.py."""
    elec = pd.read_csv(DATA / "affective_polarization_election.csv")
    panel = pd.read_parquet(DATA / "analysis_panel.parquet")[
        ["code", "year", "majoritarian_fptp", "democracy_score", "log_pop", "anglophone",
         "region", "microstate", "tier_established", "tier_all_democracies"]]
    d = elec.merge(panel, on=["code", "year"], how="inner").dropna(
        subset=["affpol_api", "majoritarian_fptp", "democracy_score", "log_pop", "region"])
    d["fptp"] = d["majoritarian_fptp"].astype(int)
    for c in ["democracy_score", "log_pop", "n_parties", "year"]:
        d[c + "_z"] = zscore(d[c])
    pr = {k: bmb.Prior("Normal", mu=0, sigma=1) for k in
          ["fptp", "democracy_score_z", "log_pop_z", "n_parties_z", "year_z"]}

    def run(sub, formula, tag, keys):
        idata = bmb.Model(formula, sub, priors={k: pr[k] for k in keys}).fit(**FIT)
        fp = idata.posterior["fptp"].values.reshape(-1)
        lo, hi = cred_int(fp)
        print(f"  [{tag}] elections={len(sub)}, countries={sub.code.nunique()}: "
              f"FPTP {fp.mean():+.3f}  94% CI [{lo:+.2f}, {hi:+.2f}]  "
              f"P(>0)={ (fp>0).mean():.3f}  -> {signal(float((fp>0).mean()))}")

    print("\n=== BAYESIAN in/out affective polarization (hierarchical) ===")
    full = "affpol_api ~ fptp + democracy_score_z + log_pop_z + n_parties_z + year_z + (1|region) + (1|code)"
    keys = ["fptp", "democracy_score_z", "log_pop_z", "n_parties_z", "year_z"]
    run(d[d.tier_established & (d.microstate == 0)], full, "established non-micro", keys)
    run(d[d.tier_all_democracies], full, "all democracies", keys)
    run(d[d.anglophone == 1], "affpol_api ~ fptp + year_z + (1|code)", "anglophone only",
        ["fptp", "year_z"])


def main():
    ap = pd.read_csv(DATA / "affective_polarization.csv")
    snap = country_snapshot().merge(ap, on="code", how="inner")
    snap["affpol"] = snap["api_latest"]                 # primary measure = in/out API
    print(f"Matched {len(snap)} countries (CSES + panel).")

    U = snap[snap.tier_established & (snap.microstate == 0)]
    D = snap[snap.tier_all_dem]

    print("\n=== 1. Measure agreement ===")
    r_ae, n = corr(snap.api_latest, snap.elite_pol)
    r_se, _ = corr(snap.spread_latest, snap.elite_pol)
    r_as, _ = corr(snap.api_latest, snap.spread_latest)
    print(f"  in/out API vs elite (v2cacamps): r={r_ae:+.3f} (n={n})")
    print(f"  spread     vs elite            : r={r_se:+.3f}")
    print(f"  in/out API vs spread           : r={r_as:+.3f}  (the two affective measures)")

    print("\n=== 2. In/out affective polarization vs electoral system ===")
    for name, d in [("all democracies", D), ("established non-micro (primary)", U)]:
        r, n = corr(d.api_latest, d.fptp.astype(float))
        maj, prop, diff, ci = group_diff(d, "api_latest")
        print(f"  [{name}] n={n}: corr(API,FPTP)={r:+.3f}")
        print(f"    mean API: FPTP={maj:.2f} vs proportional={prop:.2f}  "
              f"diff={diff:+.2f}  bootstrap 95% CI [{ci[0]:+.2f}, {ci[1]:+.2f}]")

    print("\n=== 3. Anglophone core (the thesis's focus) ===")
    core = ["USA", "GBR", "CAN", "AUS", "NZL", "IRL", "ZAF", "IND"]
    a = snap[snap.code.isin(core) & (snap.microstate == 0)].sort_values("api_latest",
                                                                        ascending=False)
    print(a[["code", "elec_family", "fptp", "api_latest", "spread_latest", "elite_pol"]]
          .to_string(index=False))
    maj, prop, diff, ci = group_diff(a, "api_latest")
    print(f"  anglophone FPTP API={maj:.2f} vs proportional={prop:.2f}  diff={diff:+.2f} "
          f"CI [{ci[0]:+.2f}, {ci[1]:+.2f}]")

    print("\n=== 4. Party-count confound + controls (primary universe) ===")
    r_np, _ = corr(U.api_latest, U.n_parties)
    print(f"  corr(API, n_parties) = {r_np:+.3f}")
    reg = U.dropna(subset=["api_latest", "fptp", "n_parties", "democracy", "anglophone"]).copy()
    reg["fptp"] = reg["fptp"].astype(float)
    m = smf.ols("api_latest ~ fptp + n_parties + democracy + anglophone", reg).fit()
    for t in ["fptp", "n_parties", "democracy", "anglophone"]:
        lo, hi = m.conf_int().loc[t]
        print(f"    {t:12s} {m.params[t]:+.3f}  95% CI [{lo:+.2f}, {hi:+.2f}]  p={m.pvalues[t]:.3f}")
    print(f"    (n={int(m.nobs)}, R2={m.rsquared:.2f})")

    snap.to_csv(OUT / "affpol_country_merged.csv", index=False)
    fig, ax = plt.subplots(figsize=(7, 5.5))
    for f, c, lab in [(1, "#c0392b", "majoritarian/FPTP"), (0, "#2980b9", "proportional")]:
        s = D[D.fptp == f]
        ax.scatter(s.elite_pol, s.api_latest, c=c, label=lab, alpha=.7, edgecolor="w")
    for _, r in D.iterrows():
        if r.code in ["USA", "GBR", "CAN", "AUS", "NZL", "IRL", "DEU", "SWE", "FRA", "ZAF"]:
            ax.annotate(r.code, (r.elite_pol, r.api_latest), fontsize=7, weight="bold")
    ax.set_xlabel("Elite/society polarization (V-Dem v2cacamps, 2015-24)")
    ax.set_ylabel("Affective polarization — in/out affect gap (CSES)")
    ax.set_title("In/out affective vs elite polarization, by electoral system")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "fig_affpol_vs_elite.png", dpi=140); plt.close(fig)
    print(f"\n[saved] affpol_country_merged.csv + fig_affpol_vs_elite.png -> {OUT}")

    bayes_affpol()


if __name__ == "__main__":
    main()

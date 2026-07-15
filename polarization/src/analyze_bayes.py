"""Hierarchical Bayesian analysis of the FPTP -> polarization question.

Why Bayesian here (see FINDINGS.md 'Bayesian' section): the country-level N is small (43 in
the primary universe, 9 anglophone), predictors are near time-invariant, and frequentist
cluster-robust SEs are unreliable below ~30-40 clusters (invalid at N=9). A multilevel model
with partial pooling is the correct structure for country-year data, gives valid posterior
uncertainty at any N, yields direct P(effect>0) statements, and renders the FPTP/anglophone
collinearity honestly as a joint-posterior ridge instead of unstable opposing point estimates.

It does NOT create separating information: the substantive verdict is unchanged. This adds
better-quantified, more communicable uncertainty and an explicit prior-sensitivity check.

Models (primary universe = established liberal democracies, population >= 1M, 1990-2025):
  M_primary   polarization ~ fptp + presidential + democracy_z + logpop_z + year_z
                            + (1|region) + (1|country)
  M_joint     + anglophone  (to extract the (fptp, anglophone) joint posterior / ridge)
  M_anglo     anglophone-9 only: polarization ~ fptp + democracy_z + year_z + (1|country)
Plus prior sensitivity on the fptp coefficient (skeptical / weakly-informative / diffuse).

Conventions from the research-statistics skill: 94% HDI, draws=1000/tune=1500/4 chains,
random_seed=42, and the P(effect>0) -> signal-strength mapping.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import bambi as bmb
import arviz as az

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
OUT = BASE / "outputs"
OUT.mkdir(exist_ok=True)

SEED = 42
CRED = 0.94  # equal-tailed credible interval width (matches skill's 94% convention)
_LO, _HI = (1 - CRED) / 2 * 100, (1 + CRED) / 2 * 100
FIT = dict(draws=1000, tune=1500, chains=4, cores=4, random_seed=SEED, target_accept=0.95)


def fit(model: bmb.Model):
    return model.fit(**FIT)


def zscore(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std()


def ci(draws: np.ndarray):
    """Equal-tailed 94% credible interval (robust across arviz versions)."""
    return np.percentile(draws, _LO), np.percentile(draws, _HI)


def rhat(post) -> float:
    """Basic split-free R-hat from a (chain, draw) array — convergence sanity check."""
    x = np.asarray(post)               # shape (chains, draws)
    m, n = x.shape
    W = x.var(axis=1, ddof=1).mean()
    B = n * x.mean(axis=1).var(ddof=1)
    var_hat = (n - 1) / n * W + B / n
    return float(np.sqrt(var_hat / W)) if W > 0 else float("nan")


def signal(p_gt0: float) -> str:
    """P(effect>0) -> signal-strength label (research-statistics Part 2)."""
    p = max(p_gt0, 1 - p_gt0)
    direction = "higher" if p_gt0 >= 0.5 else "lower"
    if p >= 0.95:
        return f"Clearly {direction} (strong)"
    if p >= 0.90:
        return f"Likely {direction} (moderate)"
    if p >= 0.80:
        return f"Possibly {direction} (directional)"
    return "Inconclusive"


def load_universe() -> pd.DataFrame:
    df = pd.read_parquet(DATA / "analysis_panel.parquet")
    df = df[(df.year >= 1990) & df.tier_established & (df.microstate == 0)].copy()
    df = df.dropna(subset=["polarization", "majoritarian_fptp", "presidential",
                           "democracy_score", "log_pop", "region", "code"])
    df["fptp"] = df["majoritarian_fptp"].astype(int)
    df["democracy_z"] = zscore(df["democracy_score"])
    df["logpop_z"] = zscore(df["log_pop"])
    df["year_z"] = zscore(df["year"])
    return df


def coef_table(idata, terms, label) -> pd.DataFrame:
    rows = []
    for t in terms:
        post = idata.posterior[t].values          # (chain, draw)
        draws = post.reshape(-1)
        lo, hi = ci(draws)
        p_gt0 = float((draws > 0).mean())
        rows.append({"model": label, "term": t, "mean": round(float(draws.mean()), 3),
                     "ci_lo": round(float(lo), 3), "ci_hi": round(float(hi), 3),
                     "P(>0)": round(p_gt0, 3), "signal": signal(p_gt0),
                     "r_hat": round(rhat(post), 3)})
    return pd.DataFrame(rows)


def main():
    df = load_universe()
    print(f"Primary universe: {df.code.nunique()} countries, {len(df)} country-years, "
          f"{df.region.nunique()} regions")

    priors = {  # weakly-informative on standardized/binary predictors (outcome SD ~1.3)
        "Intercept": bmb.Prior("Normal", mu=0, sigma=2),
        "fptp": bmb.Prior("Normal", mu=0, sigma=1),
        "presidential": bmb.Prior("Normal", mu=0, sigma=1),
        "democracy_z": bmb.Prior("Normal", mu=0, sigma=1),
        "logpop_z": bmb.Prior("Normal", mu=0, sigma=1),
        "year_z": bmb.Prior("Normal", mu=0, sigma=1),
        "anglophone": bmb.Prior("Normal", mu=0, sigma=1),
    }

    # ---- M_primary ---------------------------------------------------------
    print("\n[M_primary] hierarchical, (1|region)+(1|country) ...")
    f_primary = ("polarization ~ fptp + presidential + democracy_z + logpop_z + year_z "
                 "+ (1|region) + (1|code)")
    m1 = bmb.Model(f_primary, df, priors=priors)
    idata1 = fit(m1)
    terms = ["fptp", "presidential", "democracy_z", "logpop_z", "year_z"]
    t1 = coef_table(idata1, terms, "M_primary")
    print(t1.to_string(index=False))
    print(f"max R-hat (fixed effects) = {t1['r_hat'].max():.3f}  (want < 1.01)")

    # ---- M_joint: FPTP + anglophone, extract the ridge ---------------------
    print("\n[M_joint] adding anglophone to expose the collinearity ...")
    f_joint = ("polarization ~ fptp + anglophone + presidential + democracy_z + logpop_z "
               "+ year_z + (1|region) + (1|code)")
    m2 = bmb.Model(f_joint, df, priors=priors)
    idata2 = fit(m2)
    t2 = coef_table(idata2, ["fptp", "anglophone"], "M_joint")
    fptp_d = idata2.posterior["fptp"].values.reshape(-1)
    angl_d = idata2.posterior["anglophone"].values.reshape(-1)
    ridge_r = float(np.corrcoef(fptp_d, angl_d)[0, 1])
    print(t2.to_string(index=False))
    _tone = ("weak -> the varying intercepts absorb the shared between-country variance, so "
             "fptp stays identified" if abs(ridge_r) < 0.4 else
             "strong -> the two coefficients trade off and are not separately identified")
    print(f"posterior corr(fptp, anglophone) = {ridge_r:+.2f}  ({_tone})")

    # ---- M_anglo: anglophone-9, where frequentist inference is invalid -----
    print("\n[M_anglo] anglophone core only (N=9), partial pooling ...")
    da = pd.read_parquet(DATA / "analysis_panel.parquet")
    da = da[(da.year >= 1990) & da.tier_anglo].dropna(
        subset=["polarization", "majoritarian_fptp", "democracy_score", "code"]).copy()
    da["fptp"] = da["majoritarian_fptp"].astype(int)
    da["democracy_z"] = zscore(da["democracy_score"])
    da["year_z"] = zscore(da["year"])
    m3 = bmb.Model("polarization ~ fptp + democracy_z + year_z + (1|code)", da,
                   priors={k: priors[k] for k in ["Intercept", "fptp", "democracy_z", "year_z"]})
    idata3 = fit(m3)
    t3 = coef_table(idata3, ["fptp"], "M_anglo(N=9)")
    print(t3.to_string(index=False))

    # ---- prior sensitivity on the fptp coefficient -------------------------
    print("\n[prior sensitivity] refitting M_primary under 3 priors on fptp ...")
    sens_rows = []
    for name, sigma in [("skeptical N(0,0.25)", 0.25), ("weakly-info N(0,1)", 1.0),
                        ("diffuse N(0,5)", 5.0)]:
        p = dict(priors); p["fptp"] = bmb.Prior("Normal", mu=0, sigma=sigma)
        mi = bmb.Model(f_primary, df, priors=p)
        ii = fit(mi)
        d = ii.posterior["fptp"].values.reshape(-1)
        lo, hi = ci(d)
        sens_rows.append({"prior": name, "fptp_mean": round(float(d.mean()), 3),
                          "ci_lo": round(float(lo), 3), "ci_hi": round(float(hi), 3),
                          "P(>0)": round(float((d > 0).mean()), 3),
                          "signal": signal(float((d > 0).mean()))})
    sens = pd.DataFrame(sens_rows)
    print(sens.to_string(index=False))

    # ---- save tables -------------------------------------------------------
    allcoef = pd.concat([t1, t2, t3], ignore_index=True)
    allcoef.to_csv(OUT / "bayes_coefficients.csv", index=False)
    sens.to_csv(OUT / "bayes_prior_sensitivity.csv", index=False)

    # ---- figures -----------------------------------------------------------
    fig, ax = plt.subplots(figsize=(7, 3.6))
    yy = range(len(t1))
    ax.errorbar(t1["mean"], yy,
                xerr=[t1["mean"] - t1["ci_lo"], t1["ci_hi"] - t1["mean"]],
                fmt="o", color="#8e44ad", capsize=4)
    ax.axvline(0, color="k", lw=.8, ls="--")
    ax.set_yticks(list(yy)); ax.set_yticklabels(t1["term"])
    ax.set_xlabel("posterior coefficient on polarization (94% credible interval)")
    ax.set_title("M_primary: hierarchical Bayesian coefficients")
    fig.tight_layout(); fig.savefig(OUT / "fig_bayes_forest.png", dpi=140); plt.close(fig)

    fig, ax = plt.subplots(figsize=(5.5, 5))
    idx = np.random.default_rng(SEED).choice(len(fptp_d), 3000, replace=False)
    ax.scatter(fptp_d[idx], angl_d[idx], s=6, alpha=.25, color="#8e44ad")
    ax.axhline(0, color="k", lw=.6); ax.axvline(0, color="k", lw=.6)
    ax.set_xlabel("FPTP coefficient"); ax.set_ylabel("anglophone coefficient")
    ax.set_title(f"Joint posterior of FPTP & anglophone coefficients (r={ridge_r:+.2f})")
    fig.tight_layout(); fig.savefig(OUT / "fig_bayes_ridge.png", dpi=140); plt.close(fig)

    fig, ax = plt.subplots(figsize=(7, 4))
    for name, sigma, col in [("skeptical N(0,0.25)", 0.25, "#c0392b"),
                             ("weakly-info N(0,1)", 1.0, "#2980b9"),
                             ("diffuse N(0,5)", 5.0, "#16a085")]:
        p = dict(priors); p["fptp"] = bmb.Prior("Normal", mu=0, sigma=sigma)
        ii = fit(bmb.Model(f_primary, df, priors=p))
        d = ii.posterior["fptp"].values.reshape(-1)
        ax.hist(d, bins=60, density=True, histtype="step", lw=2, color=col,
                label=f"{name}: mean {d.mean():+.2f}, P(>0)={ (d>0).mean():.2f}")
    ax.axvline(0, color="k", lw=.8, ls="--")
    ax.set_xlabel("FPTP coefficient on polarization"); ax.set_ylabel("posterior density")
    ax.set_title("Prior sensitivity of the FPTP effect (primary universe)")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "fig_bayes_prior_sensitivity.png", dpi=140); plt.close(fig)

    print(f"\n[saved] bayes_coefficients.csv, bayes_prior_sensitivity.csv + 3 figures -> {OUT}")
    print("Done.")


if __name__ == "__main__":
    main()

"""Tiered analysis: does FPTP predict higher polarization, and does the pattern survive
as the sample broadens beyond the anglophone world?

Structure
---------
Tier 1  Anglophone core, descriptive. Recent-period means by electoral family; a
        majoritarian-vs-proportional group difference with a bootstrap CI. Explicitly
        descriptive (N=9), not inferential.
Tier 2  Broaden and re-estimate. polarization ~ majoritarian_fptp with country-clustered
        SEs and year effects, on anglophone -> established democracies -> all democracies.
        The headline "does it muddle?" table.
Tier 3  Controls and confounds. Add democracy score, presidentialism, bicameralism, legal
        origin, language family; an FPTP x anglophone interaction (is the effect specific to
        the shared-media anglophone world?); and collinearity diagnostics that quantify how
        separable "FPTP", "anglophone", and "common-law" even are.

Outputs land in polarization/outputs/ (tables + figures). All modern-era (year >= 1990).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from linearmodels.panel import BetweenOLS, RandomEffects

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data"
OUT = BASE / "outputs"
OUT.mkdir(exist_ok=True)

YEAR_MIN = 1990
RECENT = (2015, 2024)
CORE_ORDER = ["USA", "IND", "GBR", "CAN", "AUS", "ZAF", "MLT", "NZL", "IRL"]
FAMILY_COLOR = {"FPTP": "#c0392b", "AV": "#e67e22", "PR-list": "#2980b9",
                "MMP": "#16a085", "STV": "#27ae60"}

# Bicameral-aware classification: the binary majoritarian_fptp reflects only the lower house
# (V-Dem v2elparlel). Several anglophone systems are hybrids across chambers. "mixed" = a
# directly-elected proportional chamber sits alongside a majoritarian one. Australia's Senate
# is directly-elected STV (proportional) atop an AV lower house. India's Rajya Sabha is STV but
# INDIRECTLY elected by state legislatures (a weak/indirect proportional element) -> kept
# majoritarian, with the ambiguity noted. The US Senate is statewide plurality (malapportioned,
# not proportional) -> majoritarian.
CHAMBER_CLASS = {
    "USA": "majoritarian", "GBR": "majoritarian", "CAN": "majoritarian",
    "IND": "majoritarian",                 # ambiguous: indirect STV upper chamber
    "AUS": "mixed",                        # AV lower + directly-elected STV Senate
    "NZL": "proportional", "IRL": "proportional",
    "MLT": "proportional", "ZAF": "proportional",
}


def load() -> pd.DataFrame:
    df = pd.read_parquet(DATA / "analysis_panel.parquet")
    return df[df["year"] >= YEAR_MIN].copy()


# --------------------------------------------------------------------------- Tier 1
def tier1_anglo_descriptive(df: pd.DataFrame) -> pd.DataFrame:
    lo, hi = RECENT
    core = df[(df.tier_anglo) & (df.year.between(lo, hi))]
    g = (core.groupby("code")
         .agg(polarization=("polarization", "mean"),
              elec_family=("elec_family", "last"),
              majoritarian_fptp=("majoritarian_fptp", "last"),
              presidential=("presidential", "last"),
              legal_origin=("legal_origin", "last"),
              democracy_score=("democracy_score", "mean"))
         .reindex(CORE_ORDER))
    g["polarization"] = g["polarization"].round(3)
    g.to_csv(OUT / "tier1_anglophone_recent.csv")
    print(f"\n=== TIER 1: anglophone core, mean polarization {lo}-{hi} (descriptive, N=9) ===")
    print(g.to_string())

    g["chamber_class"] = g.index.map(CHAMBER_CLASS)

    def _grp_diff(maj, prop, seed):
        rng = np.random.default_rng(seed)
        boot = np.array([rng.choice(maj, len(maj)).mean() - rng.choice(prop, len(prop)).mean()
                         for _ in range(10000)])
        return maj.mean() - prop.mean(), np.percentile(boot, [2.5, 97.5])

    # (a) lower-house binary (as used in the regressions)
    maj = g.loc[g.majoritarian_fptp == 1, "polarization"]
    prop = g.loc[g.majoritarian_fptp == 0, "polarization"]
    diff, ci = _grp_diff(maj, prop, 20240714)
    print(f"\n[lower-house binary] majoritarian={maj.mean():+.2f} (n={len(maj)}: {list(maj.index)})")
    print(f"                     proportional={prop.mean():+.2f} (n={len(prop)}: {list(prop.index)})")
    print(f"                     diff={diff:+.2f}  bootstrap 95% CI [{ci[0]:+.2f}, {ci[1]:+.2f}]")

    # (b) bicameral-aware: Australia's proportional Senate moves it out of the majoritarian group
    print("\n[bicameral-aware] mean polarization by chamber class:")
    for cls in ["majoritarian", "mixed", "proportional"]:
        s = g.loc[g.chamber_class == cls, "polarization"]
        print(f"    {cls:13s} {s.mean():+.2f}  (n={len(s)}: {list(s.index)})")
    maj2 = g.loc[g.chamber_class == "majoritarian", "polarization"]
    prop2 = g.loc[g.chamber_class.isin(["mixed", "proportional"]), "polarization"]
    diff2, ci2 = _grp_diff(maj2, prop2, 20240715)
    print(f"    majoritarian vs (mixed+proportional) diff={diff2:+.2f} "
          f"bootstrap 95% CI [{ci2[0]:+.2f}, {ci2[1]:+.2f}]")

    # (c) Malta is a micro-state (~0.5M) whose small-magnitude STV yields a rigid two-party
    # system -> proportional in form, two-party in practice. Show the split without it.
    gx = g.drop(index="MLT")
    maj3 = gx.loc[gx.majoritarian_fptp == 1, "polarization"]
    prop3 = gx.loc[gx.majoritarian_fptp == 0, "polarization"]
    diff3, ci3 = _grp_diff(maj3, prop3, 20240716)
    print(f"\n[excluding Malta, micro-state] lower-house binary:")
    print(f"    majoritarian={maj3.mean():+.2f} (n={len(maj3)}); "
          f"proportional={prop3.mean():+.2f} (n={len(prop3)}: {list(prop3.index)})")
    print(f"    diff={diff3:+.2f}  bootstrap 95% CI [{ci3[0]:+.2f}, {ci3[1]:+.2f}]")
    print("NOTE: N=9 -> descriptive. Reclassifying Australia by its STV Senate widens the gap "
          f"(+0.99 -> {diff2:+.2f}); dropping micro-state Malta widens it further "
          f"({diff3:+.2f}). India's upper-chamber STV is indirect (weak) so it stays majoritarian.")
    return g


def cluster_ols(data: pd.DataFrame, formula: str):
    d = data.dropna(subset=["polarization", "code"]).copy()
    model = smf.ols(formula, data=d)             # drops rows with NaN in any term
    groups = d.loc[model.data.row_labels, "code"]  # align clusters to retained rows
    return model.fit(cov_type="cluster", cov_kwds={"groups": groups.values})


def _fmt(r, terms):
    out = {}
    for t in terms:
        if t in r.params.index:
            p = r.pvalues[t]
            out[t] = f"{r.params[t]:+.3f}{_stars(p)}"
    return out


# ------------------------------------------------ PRIMARY: established, non-microstate
def primary_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """Headline universe: established (V-Dem liberal) democracies with population >= 1M.
    This drops both developing/backsliding democracies and micro-states, leaving a
    comparable set where the electoral-system contrast is meaningful."""
    U = df[df.tier_established & (df.microstate == 0)].copy()
    print("\n" + "=" * 78)
    print("PRIMARY UNIVERSE: established liberal democracies, population >= 1M, 1990-2025")
    print("=" * 78)
    print(f"{U['code'].nunique()} countries, {len(U)} country-years")
    print("  " + ", ".join(sorted(U["code"].unique())))
    recent_class = U.sort_values("year").groupby("code")["majoritarian_fptp"].last()
    maj_members = sorted(recent_class[recent_class == 1].index)
    print(f"  majoritarian/FPTP members, current classification ({len(maj_members)}): "
          f"{', '.join(maj_members)}")

    specs = {
        "M1 bivariate": "polarization ~ majoritarian_fptp + C(year)",
        "M2 +gov/dem/bicam": "polarization ~ majoritarian_fptp + presidential "
                             "+ democracy_score + bicameral + C(year)",
        "M3 +legal_origin": "polarization ~ majoritarian_fptp + presidential + democracy_score "
                            "+ bicameral + C(legal_origin) + C(year)",
        "M4 +log_pop": "polarization ~ majoritarian_fptp + presidential + democracy_score "
                       "+ bicameral + log_pop + C(legal_origin) + C(year)",
        "M5 FPTP x anglophone": "polarization ~ majoritarian_fptp * anglophone + presidential "
                                "+ democracy_score + bicameral + C(year)",
    }
    terms = ["majoritarian_fptp", "majoritarian_fptp:anglophone", "anglophone",
             "presidential", "democracy_score", "bicameral", "log_pop"]
    rows = []
    for name, f in specs.items():
        r = cluster_ols(U, f)
        row = {"model": name, "n_obs": int(r.nobs), "r2": round(r.rsquared, 3)}
        row.update(_fmt(r, terms))
        # keep the FPTP CI for the headline model
        if "majoritarian_fptp" in r.params.index:
            lo, hi = r.conf_int().loc["majoritarian_fptp"]
            row["fptp_ci"] = f"[{lo:+.2f}, {hi:+.2f}]"
        rows.append(row)
    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "primary_established_nonmicro.csv", index=False)
    print("\nRegressions (polarization; country-clustered SEs; "
          "* p<.05 ** p<.01 *** p<.001):")
    print(tab.to_string(index=False))

    # descriptive group means, recent
    lo, hi = RECENT
    rec = (U[U.year.between(lo, hi)].groupby("code")
           .agg(pol=("polarization", "mean"), fptp=("majoritarian_fptp", "last"),
                anglo=("anglophone", "last"), cl=("common_law", "last")))
    maj, prop = rec[rec.fptp == 1].pol, rec[rec.fptp == 0].pol
    print(f"\nDescriptive means {lo}-{hi}: majoritarian={maj.mean():+.2f} (n={len(maj)}), "
          f"proportional={prop.mean():+.2f} (n={len(prop)}), diff={maj.mean()-prop.mean():+.2f}")
    corr = rec[["fptp", "anglo", "cl"]].astype(float).corr()
    print("Collinearity within this universe (FPTP / anglophone / common-law):")
    print("  FPTP-anglophone r={:.2f}, FPTP-commonlaw r={:.2f}, anglo-commonlaw r={:.2f}"
          .format(corr.loc["fptp", "anglo"], corr.loc["fptp", "cl"], corr.loc["anglo", "cl"]))
    print("  -> restricting to established democracies TIGHTENS the FPTP/anglophone confound "
          "(few non-anglophone FPTP cases survive), so M5's opposing FPTP/anglophone "
          "coefficients are unstable and should not be read as separable effects.")
    return tab


# --------------------------------------------------------------------------- Tier 2


def tier2_across_tiers(df: pd.DataFrame) -> pd.DataFrame:
    tiers = [("anglophone", df[df.tier_anglo]),
             ("established_dem", df[df.tier_established]),
             ("all_democracies", df[df.tier_all_democracies])]
    rows = []
    for name, d in tiers:
        d = d.dropna(subset=["polarization", "majoritarian_fptp"])
        m = cluster_ols(d, "polarization ~ majoritarian_fptp + C(year)")
        b = m.params["majoritarian_fptp"]
        lo, hi = m.conf_int().loc["majoritarian_fptp"]
        nclust = d["code"].nunique()
        rows.append({"tier": name, "n_obs": int(m.nobs), "n_countries": nclust,
                     "fptp_coef": round(b, 3),
                     "ci_low": round(lo, 3), "ci_high": round(hi, 3),
                     "p_value": round(m.pvalues["majoritarian_fptp"], 4),
                     "r2": round(m.rsquared, 3),
                     "clusters_reliable": "no (few clusters)" if nclust < 15 else "yes"})
    tab = pd.DataFrame(rows)
    tab.to_csv(OUT / "tier2_fptp_across_tiers.csv", index=False)
    print("\n=== TIER 2: FPTP coefficient as the sample broadens "
          "(polarization ~ FPTP + year FE, country-clustered) ===")
    print(tab.to_string(index=False))
    print("Positive coef => FPTP associated with HIGHER polarization.")
    return tab


# --------------------------------------------------------------------------- Tier 3
def tier3_controls(df: pd.DataFrame):
    est = df[df.tier_established].dropna(
        subset=["polarization", "majoritarian_fptp", "presidential",
                "democracy_score", "bicameral"])
    alld = df[df.tier_all_democracies].dropna(
        subset=["polarization", "majoritarian_fptp", "presidential",
                "democracy_score", "bicameral"])

    models = {}
    models["established_bivariate"] = cluster_ols(
        est, "polarization ~ majoritarian_fptp + C(year)")
    models["established_controls"] = cluster_ols(
        est, "polarization ~ majoritarian_fptp + presidential + democracy_score "
             "+ bicameral + C(legal_origin) + C(year)")
    models["alldem_controls"] = cluster_ols(
        alld, "polarization ~ majoritarian_fptp + presidential + democracy_score "
              "+ bicameral + C(legal_origin) + C(year)")
    # The thesis: is FPTP's effect specific to the shared-media anglophone world?
    models["alldem_interaction"] = cluster_ols(
        alld, "polarization ~ majoritarian_fptp * anglophone + presidential "
              "+ democracy_score + bicameral + C(year)")
    # Robustness to country size: control for population, and exclude micro-states (<1M),
    # since small states (e.g. Malta) can behave atypically.
    est_pop = est.dropna(subset=["log_pop"])
    models["established_controls_pop"] = cluster_ols(
        est_pop, "polarization ~ majoritarian_fptp + presidential + democracy_score "
                 "+ bicameral + log_pop + C(legal_origin) + C(year)")
    est_big = est_pop[est_pop["microstate"] == 0]
    models["established_no_microstates"] = cluster_ols(
        est_big, "polarization ~ majoritarian_fptp + presidential + democracy_score "
                 "+ bicameral + C(legal_origin) + C(year)")

    with open(OUT / "tier3_regression_tables.txt", "w") as fh:
        for name, m in models.items():
            fh.write(f"\n{'='*78}\nMODEL: {name}\n{'='*78}\n")
            fh.write(str(m.summary()))
            fh.write("\n")
    print("\n=== TIER 3: controlled models (full summaries -> tier3_regression_tables.txt) ===")
    key = ["majoritarian_fptp", "majoritarian_fptp:anglophone", "anglophone",
           "presidential", "democracy_score", "bicameral", "log_pop"]
    summ = []
    for name, m in models.items():
        row = {"model": name, "n_obs": int(m.nobs), "r2": round(m.rsquared, 3)}
        for k in key:
            if k in m.params.index:
                row[k] = f"{m.params[k]:+.3f}{_stars(m.pvalues[k])}"
        summ.append(row)
    stab = pd.DataFrame(summ)
    stab.to_csv(OUT / "tier3_coefficients.csv", index=False)
    print(stab.to_string(index=False))
    print("stars: * p<.05  ** p<.01  *** p<.001 (country-clustered)")

    # cross-check estimators (simple model, all democracies)
    _panel_crosschecks(df)
    return models


def _stars(p: float) -> str:
    return "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else ""


def _panel_crosschecks(df: pd.DataFrame):
    d = (df[df.tier_all_democracies]
         .dropna(subset=["polarization", "majoritarian_fptp"])
         .set_index(["code", "year"]))
    print("\n--- estimator cross-checks (all democracies, polarization ~ FPTP) ---")
    for label, Model in [("BetweenOLS", BetweenOLS), ("RandomEffects", RandomEffects)]:
        try:
            res = Model.from_formula("polarization ~ 1 + majoritarian_fptp", d).fit()
            b = res.params["majoritarian_fptp"]
            ci = res.conf_int().loc["majoritarian_fptp"].values
            print(f"  {label:14s} FPTP coef={b:+.3f}  95% CI [{ci[0]:+.3f}, {ci[1]:+.3f}]")
        except Exception as exc:  # noqa: BLE001
            print(f"  {label}: {exc}")


def collinearity(df: pd.DataFrame):
    d = df[df.tier_all_democracies].dropna(subset=["majoritarian_fptp"])
    # recent snapshot, one row per country, to describe the confound structure
    lo, hi = RECENT
    snap = (d[d.year.between(lo, hi)]
            .groupby("code")
            .agg(fptp=("majoritarian_fptp", "last"),
                 anglophone=("anglophone", "last"),
                 common_law=("common_law", "last")))
    print("\n=== COLLINEARITY: how separable are FPTP / anglophone / common-law? ===")
    print(f"(one row per democracy, {RECENT[0]}-{RECENT[1]}; N={len(snap)})")
    print("\nanglophone x FPTP:")
    print(pd.crosstab(snap.anglophone, snap.fptp, rownames=["anglophone"],
                      colnames=["FPTP"]))
    print("\ncommon_law x FPTP:")
    print(pd.crosstab(snap.common_law.astype(float), snap.fptp, rownames=["common_law"],
                      colnames=["FPTP"]))
    print("\nanglophone x common_law:")
    print(pd.crosstab(snap.anglophone, snap.common_law.astype(float),
                      rownames=["anglophone"], colnames=["common_law"]))
    corr = snap[["fptp", "anglophone", "common_law"]].astype(float).corr()
    corr.round(3).to_csv(OUT / "collinearity_corr.csv")
    print("\nPairwise correlation (country level):")
    print(corr.round(3).to_string())
    n_anglo = int((snap.anglophone == 1).sum())
    n_anglo_cl = int(((snap.anglophone == 1) & (snap.common_law == 1)).sum())
    n_anglo_fptp = int(((snap.anglophone == 1) & (snap.fptp == 1)).sum())
    print(f"\nOf {n_anglo} anglophone democracies, {n_anglo_cl} are common-law and "
          f"{n_anglo_fptp} are FPTP.")
    return snap


# --------------------------------------------------------------------------- figures
def figures(df: pd.DataFrame, t1: pd.DataFrame, t2: pd.DataFrame):
    # Fig 1: anglophone core recent polarization by electoral family
    fig, ax = plt.subplots(figsize=(8, 4.5))
    g = t1.sort_values("polarization")
    colors = [FAMILY_COLOR.get(f, "#888") for f in g["elec_family"]]
    ax.barh(g.index, g["polarization"], color=colors)
    ax.axvline(0, color="k", lw=.8)
    ax.set_xlabel("Mean political polarization, 2015–2024 (V-Dem)")
    ax.set_title("Anglophone democracies by electoral family")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in FAMILY_COLOR.values()]
    ax.legend(handles, FAMILY_COLOR.keys(), title="Electoral family",
              fontsize=8, loc="lower right")
    fig.tight_layout(); fig.savefig(OUT / "fig1_anglophone_by_system.png", dpi=140)
    plt.close(fig)

    # Fig 2: FPTP coefficient across tiers (forest plot)
    fig, ax = plt.subplots(figsize=(7, 3.2))
    y = range(len(t2))
    ax.errorbar(t2["fptp_coef"], y,
                xerr=[t2["fptp_coef"] - t2["ci_low"], t2["ci_high"] - t2["fptp_coef"]],
                fmt="o", color="#c0392b", capsize=4)
    ax.axvline(0, color="k", lw=.8, ls="--")
    ax.set_yticks(list(y)); ax.set_yticklabels(
        [f"{t}\n(N={n} countries)" for t, n in zip(t2.tier, t2.n_countries)])
    ax.set_xlabel("FPTP coefficient on polarization (country-clustered 95% CI)")
    ax.set_title("Does the FPTP effect survive broadening the sample?")
    fig.tight_layout(); fig.savefig(OUT / "fig2_fptp_across_tiers.png", dpi=140)
    plt.close(fig)

    # Fig 3: polarization vs democracy score, colored by system, recent snapshot
    lo, hi = RECENT
    snap = (df[df.tier_all_democracies & df.year.between(lo, hi)]
            .groupby("code")
            .agg(pol=("polarization", "mean"), dem=("democracy_score", "mean"),
                 fptp=("majoritarian_fptp", "last"), anglo=("anglophone", "last")))
    fig, ax = plt.subplots(figsize=(7.5, 5))
    for fptp, col, lab in [(1, "#c0392b", "majoritarian/FPTP"), (0, "#2980b9", "proportional")]:
        s = snap[snap.fptp == fptp]
        ax.scatter(s.dem, s.pol, c=col, label=lab, alpha=.6, edgecolor="w")
    for code in CORE_ORDER:
        if code in snap.index:
            ax.annotate(code, (snap.loc[code, "dem"], snap.loc[code, "pol"]),
                        fontsize=7, weight="bold")
    ax.set_xlabel("Electoral democracy index (V-Dem polyarchy)")
    ax.set_ylabel("Mean polarization 2015–2024")
    ax.set_title("Polarization vs democracy quality, by electoral system")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / "fig3_polarization_vs_democracy.png", dpi=140)
    plt.close(fig)
    print(f"\n[figures] wrote fig1/fig2/fig3 to {OUT}")


def main():
    df = load()
    t1 = tier1_anglo_descriptive(df)
    primary_analysis(df)          # headline: established, non-microstate democracies
    t2 = tier2_across_tiers(df)   # secondary: how the effect changes as the sample broadens
    tier3_controls(df)
    collinearity(df)
    figures(df, t1, t2)
    print("\nDone. See polarization/outputs/ and write-up in polarization/FINDINGS.md")


if __name__ == "__main__":
    main()

"""Forest plot: the FPTP effect across every polarization measure, in comparable (SD) units.

Each outcome is z-scored within its estimation sample, so the FPTP coefficient is in
outcome-standard-deviation units and comparable across measures. Two estimates per measure:
established non-micro democracies vs all democracies. Positive = FPTP more polarized.
Hierarchical Bayesian: outcome_z ~ fptp + democracy_z + logpop_z + year_z + (1|region)+(1|code).
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import bambi as bmb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent.parent
DATA, OUT = BASE / "data", BASE / "outputs"
FIT = dict(draws=1000, tune=1500, chains=4, cores=4, random_seed=42, target_accept=0.95)
COV = ["code", "year", "majoritarian_fptp", "democracy_score", "log_pop", "region",
       "microstate", "tier_established", "tier_all_democracies"]


def z(s):
    return (s - s.mean()) / s.std()


def datasets():
    pan = pd.read_parquet(DATA / "analysis_panel.parquet")
    cov = pan[COV]
    vdem = pan[(pan.year >= 1990)][COV + ["polarization"]].dropna(subset=["polarization"])
    gap = (pd.read_csv(DATA / "affective_polarization_election.csv")[["code", "year", "affpol_api"]]
           .merge(cov, on=["code", "year"]))
    cold = pd.read_csv(DATA / "coldness_election.csv").merge(cov, on=["code", "year"])
    return [("Expert: V-Dem hostile camps", vdem, "polarization"),
            ("Citizen: in/out affect gap", gap, "affpol_api"),
            ("Citizen: out-group coldness", cold, "coldness_all"),
            ("Citizen: coldness, middle clusters", cold, "coldness_mid")]


def fit_fptp(df, outcome, universe):
    d = df[df[universe]].dropna(subset=[outcome, "majoritarian_fptp", "democracy_score",
                                        "log_pop", "region", "code"]).copy()
    d["fptp"] = d.majoritarian_fptp
    d["y"] = z(d[outcome])
    for c in ["democracy_score", "log_pop", "year"]:
        d[c + "_z"] = z(d[c])
    pr = {k: bmb.Prior("Normal", mu=0, sigma=1)
          for k in ["fptp", "democracy_score_z", "log_pop_z", "year_z"]}
    idata = bmb.Model("y ~ fptp + democracy_score_z + log_pop_z + year_z + (1|region) + (1|code)",
                      d, priors=pr).fit(**FIT)
    v = idata.posterior["fptp"].values.reshape(-1)
    return v.mean(), np.percentile(v, 3), np.percentile(v, 97), d[d.fptp == 1].code.nunique()


def main():
    cache = OUT / "fptp_forest_results.csv"
    if cache.exists():
        r = pd.read_csv(cache)
    else:
        rows = []
        for label, df, outcome in datasets():
            for uni, ulab, off, col in [("tier_established", "established non-micro", +0.16, "#c0392b"),
                                        ("tier_all_democracies", "all democracies", -0.16, "#2980b9")]:
                m, lo, hi, nf = fit_fptp(df, outcome, uni)
                rows.append(dict(label=label, ulab=ulab, off=off, col=col, m=m, lo=lo, hi=hi, nf=nf))
                print(f"{label:38s} {ulab:22s}: {m:+.2f} [{lo:+.2f},{hi:+.2f}] (FPTP n={nf})")
        r = pd.DataFrame(rows)
        r.to_csv(cache, index=False)
    labels = list(dict.fromkeys(r.label))
    ypos = {lab: i for i, lab in enumerate(reversed(labels))}

    fig, ax = plt.subplots(figsize=(9, 4.4))
    for _, row in r.iterrows():
        y = ypos[row.label] + row.off
        ax.plot([row.lo, row.hi], [y, y], color=row.col, lw=2.4, solid_capstyle="round", zorder=3)
        ax.scatter(row.m, y, color=row.col, s=45, zorder=4, edgecolor="w", linewidth=.8)
    ax.axvline(0, color="#333", lw=1, ls="--", zorder=1)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(list(reversed(labels)), fontsize=10)
    ax.set_ylim(-0.6, len(labels) - 0.4)
    ax.set_xlabel("FPTP effect on polarization (standard-deviation units, 94% credible interval)")
    ax.set_title("The FPTP effect depends entirely on which polarization you measure",
                 fontsize=13, weight="bold", loc="left", pad=26)
    ax.text(0, 1.02, "Positive = first-past-the-post more polarized. Red = established democracies; "
            "blue = all democracies.", transform=ax.transAxes, fontsize=9, color="#666")
    ax.spines[["top", "right"]].set_visible(False); ax.tick_params(length=0)
    ax.grid(axis="x", color="#eee")
    from matplotlib.lines import Line2D
    ax.legend(handles=[Line2D([0], [0], color="#c0392b", lw=2.4, label="established non-micro"),
                       Line2D([0], [0], color="#2980b9", lw=2.4, label="all democracies")],
              fontsize=8.5, loc="upper right", frameon=False)
    fig.tight_layout()
    fig.savefig(OUT / "fig_fptp_across_measures.png", dpi=150, bbox_inches="tight")
    print(f"\n[saved] {OUT / 'fig_fptp_across_measures.png'}")


if __name__ == "__main__":
    main()

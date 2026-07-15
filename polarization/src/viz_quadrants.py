"""Two-layer polarization typology: expert behavioral vs citizen affective polarization.

x = V-Dem expert measure (v2cacamps): does the divide spill into everyday social life?
y = CSES citizen out-group coldness: how coldly do voters rate opposing parties?
Split at medians into four shaded, labeled quadrants; points colored by electoral family.
Micro-states excluded.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent.parent
DATA, OUT = BASE / "data", BASE / "outputs"
FAMILY = {"FPTP": "FPTP", "AV": "Mixed", "MMP": "MMP", "STV": "STV", "PR-list": "PR-list"}
FAM_COLOR = {"FPTP": "#c0392b", "Mixed": "#e67e22", "MMP": "#16a085", "STV": "#27ae60",
             "PR-list": "#2980b9", "other": "#95a5a6"}
LABEL = {"USA": "United States", "GBR": "UK", "CAN": "Canada", "AUS": "Australia",
         "NZL": "New Zealand", "IRL": "Ireland", "ZAF": "South Africa", "IND": "India*",
         "SWE": "Sweden", "DEU": "Germany", "NOR": "Norway", "POL": "Poland", "GRC": "Greece",
         "HUN": "Hungary", "JPN": "Japan", "FRA": "France", "ESP": "Spain", "NLD": "Netherlands"}
ANGLO = {"USA", "GBR", "CAN", "AUS", "NZL", "IRL", "ZAF", "IND"}


def load():
    pan = pd.read_parquet(DATA / "analysis_panel.parquet")
    v = (pan[pan.year.between(2015, 2024)].groupby("code")
         .agg(vdem=("polarization", "mean"), fam=("elec_family", "last"),
              micro=("microstate", "last"), alldem=("tier_all_democracies", "last")).reset_index())
    cold = pd.read_csv(DATA / "coldness_election.csv").dropna(subset=["coldness_all"])
    cold = cold.loc[cold.groupby("code").year.idxmax()][["code", "coldness_all"]]
    d = v.merge(cold, on="code")
    # all democracies + anglophone core (keeps India, which V-Dem reclassified as an
    # electoral autocracy in 2017 and would otherwise drop); micro-states excluded
    d = d[(d.micro == 0) & ((d.alldem == True) | (d.code.isin(ANGLO)))].copy()
    d["famD"] = d.fam.map(FAMILY).fillna("other")
    return d


def main():
    d = load()
    mx, my = 0.0, 7.0     # absolute anchors: V-Dem global average; coldness 7 = rate opponents <=3/10
    xlo, xhi = d.vdem.min() - .4, d.vdem.max() + .4
    ylo, yhi = d.coldness_all.min() - .4, d.coldness_all.max() + .4

    fig, ax = plt.subplots(figsize=(11.5, 8))
    quad = [  # (x0,x1,y0,y1, color, title, desc, corner)
        (mx, xhi, my, yhi, "#fdecea", "PERNICIOUS", "socially sorted + voter hostility", "tr"),
        (xlo, mx, my, yhi, "#fef5e7", "CONTAINED RIVALRY", "voters dislike, no social spillover", "tl"),
        (mx, xhi, ylo, my, "#eee8f6", "EXPERT-PERCEIVED", "experts rate division, voters not cold", "br"),
        (xlo, mx, ylo, my, "#e8f6ef", "DEPOLARIZED", "calm on both measures", "bl")]
    for x0, x1, y0, y1, c, t, desc, corner in quad:
        ax.add_patch(plt.Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=c, zorder=0))
        pad = 0.12
        x = (x1 - pad, "right") if corner[1] == "r" else (x0 + pad, "left")
        y = (y1 - pad, "top") if corner[0] == "t" else (y0 + pad, "bottom")
        ax.text(x[0], y[0], t, ha=x[1], va=y[1], fontsize=13.5, weight="bold",
                color="#7f8c8d", alpha=.8, zorder=1)
        ax.annotate(desc, (x[0], y[0]), xytext=(0, -15 if y[1] == "top" else 15),
                    textcoords="offset points", ha=x[1], va=y[1], fontsize=8.5,
                    color="#aab2b8", style="italic", zorder=1)
    ax.axvline(mx, color="#555", lw=1.4, zorder=2)
    ax.axhline(my, color="#555", lw=1.4, zorder=2)

    for _, r in d.iterrows():
        anglo = r.code in ANGLO
        ax.scatter(r.vdem, r.coldness_all, s=110 if anglo else 44,
                   c=FAM_COLOR[r.famD], edgecolor="white" if anglo else "none",
                   linewidth=1.2, alpha=.95 if anglo else .5, zorder=5 if anglo else 3)
        if r.code in LABEL and (anglo or r.code in {"SWE", "DEU", "POL", "GRC", "HUN", "JPN", "FRA"}):
            ax.annotate(LABEL[r.code], (r.vdem, r.coldness_all),
                        xytext=(6, 5), textcoords="offset points",
                        fontsize=8.5 if anglo else 7.5, weight="bold" if anglo else "normal",
                        color="#2c3e50" if anglo else "#7f8c8d", zorder=6)

    ax.set_xlim(xlo, xhi); ax.set_ylim(ylo, yhi)
    ax.set_xlabel("Expert behavioral polarization  →  divide spills into everyday social life\n"
                  "(V-Dem, society split into hostile camps)", fontsize=10.5)
    ax.set_ylabel("Citizen affective polarization  →  coldness toward opposing parties\n"
                  "(CSES, 0–10)", fontsize=10.5)
    ax.set_title("Two layers of polarization: what experts see vs what voters feel",
                 fontsize=15, weight="bold", loc="left", pad=26)
    ax.text(0, 1.03, "Split at V-Dem = 0 (global-average polarization) and coldness = 7 (voters "
            "rate opponents ≤3/10). Every democracy is net-cold to opponents (all ≥5).",
            transform=ax.transAxes, fontsize=9, color="#666")
    ax.spines[["top", "right"]].set_visible(False); ax.tick_params(length=0)

    handles = [plt.Line2D([0], [0], marker="o", ls="", mfc=FAM_COLOR[f], mec="w", ms=9, label=f)
               for f in ["FPTP", "Mixed", "MMP", "STV", "PR-list"]]
    ax.legend(handles=handles, title="Electoral family\n(anglophone = large dots)",
              loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=9, title_fontsize=9,
              frameon=False)
    fig.text(0.01, -0.02, "*India shown for reference; V-Dem reclassified it as an electoral "
             "autocracy in 2017, so it is outside the democracy sample.", fontsize=8, color="#999")
    fig.tight_layout()
    fig.savefig(OUT / "fig_polarization_quadrants.png", dpi=150, bbox_inches="tight")
    print(f"[saved] {OUT / 'fig_polarization_quadrants.png'}  (absolute anchors x={mx}, y={my})")


if __name__ == "__main__":
    main()

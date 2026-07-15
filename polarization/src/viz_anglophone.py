"""Anglophone comparison chart: same (non-micro) countries, two measures of polarization.

Left  = V-Dem expert measure (v2cacamps): society split into hostile camps in everyday life.
Right = Citizen out-group COLDNESS (10 - warmth toward opposing parties, CSES).
Both: higher = more polarized. Bars colored by electoral family. Micro-states excluded.
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

NAME = {"USA": "United States", "GBR": "United Kingdom", "CAN": "Canada", "AUS": "Australia",
        "NZL": "New Zealand", "IRL": "Ireland", "ZAF": "South Africa", "IND": "India"}
# Australia = Alternative Vote (majoritarian) lower house + STV (proportional) Senate -> "Mixed"
FAMILY = {"FPTP": "FPTP", "AV": "Mixed", "MMP": "MMP", "STV": "STV", "PR-list": "PR-list"}
FAM_COLOR = {"FPTP": "#c0392b", "Mixed": "#e67e22", "MMP": "#16a085", "STV": "#27ae60",
             "PR-list": "#2980b9"}
CORE = list(NAME)


def load():
    pan = pd.read_parquet(DATA / "analysis_panel.parquet")
    v = (pan[pan.year.between(2015, 2024)].groupby("code")
         .agg(vdem=("polarization", "mean"), fam=("elec_family", "last"),
              micro=("microstate", "last")).reset_index())
    cold = pd.read_csv(DATA / "coldness_election.csv").dropna(subset=["coldness_all"])
    cold = cold.loc[cold.groupby("code").year.idxmax()][["code", "coldness_all"]]
    d = v[v.code.isin(CORE)].merge(cold, on="code", how="left")
    d = d[d.micro == 0]                        # exclude micro-states (Malta already out via CSES)
    d["fam"] = d.fam.map(FAMILY)
    return d


def panel(ax, d, col, title, subtitle, zero_ref, fmt):
    d = d.dropna(subset=[col]).sort_values(col)
    ax.barh(np.arange(len(d)), d[col], color=[FAM_COLOR[f] for f in d.fam], height=0.62, zorder=3)
    ax.set_yticks(np.arange(len(d))); ax.set_yticklabels([NAME[c] for c in d.code], fontsize=10)
    if zero_ref:
        ax.axvline(0, color="#333", lw=1, zorder=2)
    for yi, v_ in enumerate(d[col]):
        ax.text(v_ + (0.06 if v_ >= 0 else -0.06), yi, fmt(v_), va="center",
                ha="left" if v_ >= 0 else "right", fontsize=8.5, color="#444")
    ax.set_title(title, fontsize=12.5, weight="bold", pad=20, loc="left")
    ax.text(0, 1.015, subtitle, transform=ax.transAxes, fontsize=9, color="#666", va="bottom")
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=0); ax.set_axisbelow(True)
    ax.grid(axis="x", color="#eee", zorder=0)


def main():
    d = load()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.5, 4.4))
    panel(a1, d, "vdem", "Expert-coded polarization",
          "V-Dem: society split into hostile camps (2015–24)", True, lambda v: f"{v:+.1f}")
    panel(a2, d, "coldness_all", "Citizen out-group coldness",
          "CSES: coldness toward opposing parties, 0–10 (latest wave)", False, lambda v: f"{v:.1f}")

    handles = [plt.Rectangle((0, 0), 1, 1, color=FAM_COLOR[f]) for f in FAM_COLOR]
    fig.legend(handles, FAM_COLOR.keys(), title="Electoral family", ncol=5, fontsize=9,
               title_fontsize=9, loc="lower center", frameon=False, bbox_to_anchor=(0.5, -0.03))
    fig.suptitle("Anglophone democracies: the polarization ranking depends on how you measure it",
                 fontsize=14, weight="bold", y=1.10)
    fig.text(0.5, 1.03, "Ireland & New Zealand look calmest to experts; among their own voters they "
             "are middling. The US is high on both. Australia = mixed chambers (AV / STV Senate).",
             ha="center", fontsize=9.5, color="#555")
    fig.tight_layout(rect=[0, 0.05, 1, 0.88])
    fig.savefig(OUT / "fig_anglophone_compare.png", dpi=150, bbox_inches="tight")
    print(f"[saved] {OUT / 'fig_anglophone_compare.png'}")


if __name__ == "__main__":
    main()

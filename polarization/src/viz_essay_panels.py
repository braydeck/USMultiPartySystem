"""Essay figures (V-Dem expert-polarization spine). Renders each panel standalone AND combined:
  fig_essay_panel_a.png  English-speaking democracies on V-Dem; the US is the lone outlier.
  fig_essay_panel_b.png  Duopoly concentration vs V-Dem polarization: r=0.88 within the anglosphere,
                         r=0.08 across all democracies (the scope-conditional core).
  fig_essay_panels.png   both, side by side.
Claim-first titles; self-contained for screenshot/email; mobile-legible label sizes.
"""
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(__file__).resolve().parent.parent
DATA, OUT = BASE / "data", BASE / "outputs"
RED, NAVY, GREY = "#c0392b", "#2c3e50", "#c3ccd4"
NAME = {"USA": "United States", "GBR": "United Kingdom", "CAN": "Canada", "IRL": "Ireland",
        "AUS": "Australia", "NZL": "New Zealand", "ZAF": "South Africa"}
ANG = list(NAME)

pol = pd.read_csv(BASE / "political-polarization-score.csv").rename(
    columns={"Code": "code", "Year": "year", "Political polarization score": "pol"})
latest = pol.sort_values("year").groupby("code").tail(1).set_index("code")
ref = {"Venezuela": latest.loc["VEN", "pol"], "South Sudan": latest.loc["SSD", "pol"],
       "Afghanistan": latest.loc["AFG", "pol"]}
af = pd.read_csv(DATA / "affective_fractionalization.csv")
top2 = af.sort_values("year").groupby("code").tail(1)[["code", "top2"]]
d = top2.merge(latest["pol"], left_on="code", right_index=True).dropna()
r_all = np.corrcoef(d.top2, d.pol)[0, 1]
ang = d[d.code.isin(ANG)]
r_ang = np.corrcoef(ang.top2, ang.pol)[0, 1]
mfit, bfit = np.polyfit(ang.top2, ang.pol, 1)


def panel_a(ax):
    a = latest.loc[[c for c in ANG if c in latest.index], "pol"].sort_values()
    y = np.arange(len(a))
    for yi, (code, v) in zip(y, a.items()):
        c = RED if code == "USA" else NAVY
        ax.plot([0, v], [yi, yi], color=c, lw=2.4, zorder=2, solid_capstyle="round")
        ax.scatter(v, yi, s=95, color=c, zorder=3, edgecolor="w", linewidth=1.1)
        ax.text(v + (0.14 if v >= 0 else -0.14), yi, f"{v:+.2f}", va="center",
                ha="left" if v >= 0 else "right", fontsize=9.5, color=c, weight="bold")
    ax.set_yticks(y); ax.set_yticklabels([NAME[c] for c in a.index], fontsize=10.5)
    ax.axvline(0, color="#888", lw=1, ls="--", zorder=1)
    for xv in ref.values():                      # 3 near-identical scores -> one dotted band
        ax.axvline(xv, color="#b0b8bf", lw=1, ls=":", zorder=1)
    ax.text(2.42, 3.0, "US's nearest neighbors:\nVenezuela, South Sudan,\nAfghanistan",
            va="center", ha="left", fontsize=8, color="#7f8c8d", linespacing=1.35)
    ax.set_xlim(-3.2, 3.35); ax.set_ylim(-0.75, len(a) - 0.15)
    ax.set_xlabel("V-Dem political-polarization score, 2025  (higher = more polarized)", fontsize=10)
    ax.set_title("Among English-speaking democracies, only the US is polarized",
                 fontsize=12.5, weight="bold", loc="left", color="#222", pad=10)
    ax.spines[["top", "right"]].set_visible(False); ax.tick_params(length=0)
    ax.grid(axis="x", color="#eee", zorder=0)


def panel_b(ax):
    ax.scatter(d.top2, d.pol, s=30, color=GREY, alpha=0.85, zorder=2, label="all democracies")
    xs = np.array([ang.top2.min() - 0.02, ang.top2.max() + 0.02])
    ax.plot(xs, mfit * xs + bfit, color=NAVY, lw=1.7, ls="--", zorder=3)
    offs = {"USA": (-0.014, 0.10, "right"), "GBR": (0.014, 0.17, "left"),
            "ZAF": (0.016, 0.22, "left"), "CAN": (0.014, -0.34, "left"),
            "AUS": (0.015, 0.14, "left"), "NZL": (0.015, -0.36, "left"),
            "IRL": (0.016, 0.10, "left")}
    for _, r in ang.iterrows():
        c = RED if r.code == "USA" else NAVY
        ax.scatter(r.top2, r.pol, s=100, color=c, zorder=4, edgecolor="w", linewidth=1.1)
        dx, dy, ha = offs.get(r.code, (0.014, 0.1, "left"))
        ax.annotate(NAME[r.code], (r.top2, r.pol), (r.top2 + dx, r.pol + dy),
                    fontsize=9, color=c, weight="bold", zorder=5, ha=ha)
    ax.text(0.565, 2.78, f"English-speaking: r = {r_ang:.2f}", color=NAVY, fontsize=10, weight="bold")
    ax.text(0.565, 2.30, f"all democracies: r = {r_all:.2f}  (flat)", color="#7f8c8d", fontsize=9.5)
    ax.set_xlim(0.55, 1.05); ax.set_ylim(-3.0, 3.0)
    ax.set_xlabel("Two-party (top-2) vote-share concentration  →  complete duopoly", fontsize=10)
    ax.set_ylabel("V-Dem political-polarization score, 2025", fontsize=10)
    ax.set_title("Within the English-speaking world, duopoly tracks polarization",
                 fontsize=12.5, weight="bold", loc="left", color="#222", pad=10)
    ax.spines[["top", "right"]].set_visible(False); ax.tick_params(length=0)
    ax.grid(color="#eee", zorder=0); ax.legend(fontsize=8.5, loc="lower right", frameon=False)


# standalone A
figA, axA = plt.subplots(figsize=(7.8, 5.2)); panel_a(axA)
figA.tight_layout(); figA.savefig(OUT / "fig_essay_panel_a.png", dpi=150, bbox_inches="tight"); plt.close(figA)
# standalone B
figB, axB = plt.subplots(figsize=(7.8, 6.4)); panel_b(axB)
figB.text(0.5, 0.005, "Canada and the UK use FPTP but stay multiparty and unpolarized.",
          ha="center", fontsize=8.5, color="#7f8c8d")
figB.tight_layout(rect=[0, 0.03, 1, 1]); figB.savefig(OUT / "fig_essay_panel_b.png", dpi=150, bbox_inches="tight"); plt.close(figB)
# combined
figC, (cA, cB) = plt.subplots(1, 2, figsize=(15.2, 6.4)); panel_a(cA); panel_b(cB)
figC.tight_layout(w_pad=4); figC.savefig(OUT / "fig_essay_panels.png", dpi=150, bbox_inches="tight"); plt.close(figC)
print(f"[saved] fig_essay_panel_a.png, fig_essay_panel_b.png, fig_essay_panels.png  (r_ang={r_ang:.2f}, r_all={r_all:.2f})")

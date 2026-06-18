#!/usr/bin/env python3
"""Render the social-preview / README hero image: the nine-party House as an
ideological-spectrum seat bar. Outputs viz/public/og-image.png (1200x630)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path

W, H, TOTAL = 1200, 630, 873
ORDER = ["PRG", "LIB", "DSA", "SD", "STY", "CUP", "CON", "POP", "NAT"]  # F5 left -> right
SEATS = {"CON": 202, "SD": 164, "STY": 130, "CUP": 103, "POP": 99, "LIB": 93, "NAT": 46, "DSA": 22, "PRG": 14}
COLORS = {"PRG": "#1e3a8a", "LIB": "#1d4ed8", "DSA": "#60a5fa", "SD": "#06b6d4", "STY": "#16a34a",
          "CUP": "#a16207", "CON": "#ea580c", "POP": "#dc2626", "NAT": "#7f1d1d"}

fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
fig.patch.set_facecolor("#ffffff")
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

ax.text(60, H - 78, "If America Had Nine Parties", fontsize=42, fontweight="bold", color="#1c1b1a")
ax.text(60, H - 120, "Simulated U.S. House under proportional representation   ·   873 seats   ·   no majority",
        fontsize=16, color="#6b6a67")

x0, x1 = 60, W - 60
bw = x1 - x0
by, bh = 250, 150
x = x0
seg = {}
for code in ORDER:
    w = SEATS[code] / TOTAL * bw
    ax.add_patch(Rectangle((x, by), w, bh, facecolor=COLORS[code], edgecolor="white", linewidth=2))
    seg[code] = (x, w)
    if w > 34:  # label inside wide segments
        ax.text(x + w / 2, by + bh / 2 + 10, code, ha="center", va="center", color="white", fontsize=15, fontweight="bold")
        ax.text(x + w / 2, by + bh / 2 - 16, str(SEATS[code]), ha="center", va="center", color="white", fontsize=13)
    x += w

# narrow segments get a label below, in party color
for code in ORDER:
    xs, w = seg[code]
    if w <= 34:
        ax.text(xs + w / 2, by - 18, f"{code} {SEATS[code]}", ha="center", va="top",
                color=COLORS[code], fontsize=12.5, fontweight="bold")

# spectrum cue + footer
ax.text(x0, by + bh + 30, "◀  progressive left", ha="left", va="center", color="#94a3b8", fontsize=13)
ax.text(x1, by + bh + 30, "populist right  ▶", ha="right", va="center", color="#94a3b8", fontsize=13)
ax.text(W / 2, 52, "usmultipartysystem.pages.dev", ha="center", color="#4338ca", fontsize=19, fontweight="bold")

out = Path(__file__).resolve().parent.parent / "public" / "og-image.png"
fig.savefig(out, dpi=100, facecolor="#ffffff")
print("wrote", out)

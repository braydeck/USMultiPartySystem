#!/usr/bin/env python3
"""Render the social-preview / README hero image: the ten-party House as an
ideological-spectrum seat bar. Outputs viz/public/og-image.png (1200x630).

Seat totals are read from the default site view (src/data/houseSeatsTurnout.json,
the validated-turnout-weighted result) so this image can't drift out of sync with
what visitors actually see. Colors and left->right order mirror
src/constants/parties.ts — keep them in sync if either changes there.
"""
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from pathlib import Path

W, H = 1200, 630

# F5 left -> right (matches parties.ts F5_ORDER)
ORDER = ["PRG", "DSA", "LIB", "LBR", "OAO", "STY", "CUP", "CON", "POP", "NAT"]
# Party colors (mirror src/constants/parties.ts PARTY_COLORS)
COLORS = {
    "PRG": "#15803d", "DSA": "#22c55e", "LIB": "#0284c7", "LBR": "#38bdf8",
    "OAO": "#0d9488", "STY": "#8a70b8", "CUP": "#825a27", "CON": "#e68c2c",
    "POP": "#d34812", "NAT": "#a01d2a",
}
# houseSeats party integer codes -> party code (parties.ts CLUSTER_TO_PARTY)
CODE = {0: "CON", 1: "LBR", 2: "STY", 3: "NAT", 4: "LIB",
        5: "POP", 6: "CUP", 7: "OAO", 8: "DSA", 9: "PRG"}

ROOT = Path(__file__).resolve().parent.parent
rows = json.loads((ROOT / "src" / "data" / "houseSeatsTurnout.json").read_text())
SEATS = {CODE[r["party"]]: r["national"] for r in rows}
TOTAL = sum(SEATS.values())

fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
fig.patch.set_facecolor("#ffffff")
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")

ax.text(60, H - 78, "If America Had Ten Parties", fontsize=42, fontweight="bold", color="#1c1b1a")
ax.text(60, H - 120, f"Simulated U.S. House under proportional representation   ·   {TOTAL} seats   ·   no majority",
        fontsize=16, color="#6b6a67")

x0, x1 = 60, W - 60
bw = x1 - x0
by, bh = 250, 150
NARROW = 48  # segments this wide or less can't fit a code+count inside; label below instead
x = x0
seg = {}
for code in ORDER:
    w = SEATS[code] / TOTAL * bw
    ax.add_patch(Rectangle((x, by), w, bh, facecolor=COLORS[code], edgecolor="white", linewidth=2))
    seg[code] = (x, w)
    if w > NARROW:  # label inside wide segments
        ax.text(x + w / 2, by + bh / 2 + 10, code, ha="center", va="center", color="white", fontsize=15, fontweight="bold")
        ax.text(x + w / 2, by + bh / 2 - 16, str(SEATS[code]), ha="center", va="center", color="white", fontsize=13)
    x += w

# Narrow segments get a label below in party color, with a short connector line.
# Stagger adjacent labels onto a second row so tight neighbors (e.g. PRG + DSA) don't collide.
below = sorted((seg[c][0] + seg[c][1] / 2, c) for c in ORDER if seg[c][1] <= NARROW)
last_x, row = -1e9, 0
for cx, code in below:
    row = 1 - row if (cx - last_x) < 56 else 0
    y = by - 14 - row * 20
    ax.plot([cx, cx], [by, y + 12], color=COLORS[code], linewidth=1.2)
    ax.text(cx, y, f"{code} {SEATS[code]}", ha="center", va="top",
            color=COLORS[code], fontsize=12.5, fontweight="bold")
    last_x = cx

# spectrum cue + footer
ax.text(x0, by + bh + 30, "◀  progressive left", ha="left", va="center", color="#94a3b8", fontsize=13)
ax.text(x1, by + bh + 30, "populist right  ▶", ha="right", va="center", color="#94a3b8", fontsize=13)
ax.text(W / 2, 52, "usmultipartysystem.pages.dev", ha="center", color="#4338ca", fontsize=19, fontweight="bold")

out = ROOT / "public" / "og-image.png"
fig.savefig(out, dpi=100, facecolor="#ffffff")
print("wrote", out)

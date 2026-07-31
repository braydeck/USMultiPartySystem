#!/usr/bin/env python3
"""
render_hex_seat_cartogram.py
----------------------------
PROTOTYPE renderer for the one-hexagon-per-seat House cartogram.

Party colour is the fill, so district and state separation is carried entirely by line
weight: hairline between seats inside a district, heavy between districts, heaviest
between states. Boundary edges are found from hex adjacency — the two vertices nearest
a neighbouring cell's centre are the shared edge — so no polygon dissolve is needed.

Colours are read from viz/src/constants/parties.ts so the prototype cannot drift from
the app's palette.

Usage
  python pipeline/render_hex_seat_cartogram.py [--triple] [--out FILE] [--px-per-deg N]
"""

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection

sys.path.insert(0, str(Path(__file__).parent))
from build_hex_seat_cartogram import (SQRT3, hex_center, hex_vertices, neighbors)

BASE_DIR = Path(__file__).parent.parent
PARTIES_TS = BASE_DIR / "viz" / "src" / "constants" / "parties.ts"

# Line weights in points at the reference scale, scaled by px-per-deg so the hierarchy
# looks the same zoomed in as it does on the full map.
REF_PX_PER_DEG = 58.0
W_SEAT, W_DISTRICT, W_STATE = 0.5, 1.9, 3.6
C_SEAT, C_DISTRICT, C_STATE = "#ffffff", "#111827", "#0b1220"


def load_palette():
    """Party code → hex colour, plus display names, parsed from the app's constants."""
    src = PARTIES_TS.read_text()

    def block(name):
        m = re.search(name + r"\s*:\s*Record<string, string>\s*=\s*\{(.*?)\n\};", src, re.S)
        return dict(re.findall(r"(\w+)\s*:\s*'([^']*)'", m.group(1))) if m else {}

    colors, names = block("PARTY_COLORS"), block("PARTY_NAMES")
    order = re.search(r"F5_ORDER\s*=\s*\[(.*?)\]", src, re.S)
    left_right = re.findall(r"'(\w+)'", order.group(1)) if order else sorted(colors)
    return colors, names, left_right


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--triple", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--px-per-deg", type=float, default=58.0)
    ap.add_argument("--no-labels", action="store_true", help="omit state abbreviations")
    ap.add_argument("--style", choices=["cased", "gap"], default="cased",
                    help="district separation: dark line cased in white, or white gap")
    ap.add_argument("--focus", default=None,
                    help="comma-separated state abbreviations to zoom to")
    args = ap.parse_args()

    suffix = "_triple" if args.triple else ""
    data = json.loads((BASE_DIR / "data" / "processed"
                       / f"hex_seat_cartogram{suffix}.json").read_text())
    meta = data["meta"]
    R, x0, y0 = meta["R"], meta["x0"], meta["y0"]
    colors, names, left_right = load_palette()

    cells = {(c["col"], c["row"]): c for c in data["cells"]}
    centers = {k: hex_center(k[0], k[1], R, x0, y0) for k in cells}
    verts = {k: hex_vertices(*centers[k], R) for k in cells}

    # Hex fills
    polys, facecolors = [], []
    for k, c in cells.items():
        polys.append(verts[k])
        facecolors.append(colors.get(c["party"], "#9aa3af"))

    # Boundary edges by class. The shared edge with a neighbour is the two hexagon
    # vertices closest to that neighbour's centre.
    seat_edges, dist_edges, state_edges = [], [], []
    for k, c in cells.items():
        cx, cy = centers[k]
        for nb in neighbors(*k):
            ncell = cells.get(nb)
            if ncell is None:
                nx, ny = hex_center(nb[0], nb[1], R, x0, y0)
                bucket = state_edges
            else:
                nx, ny = centers[nb]
                if ncell["state"] != c["state"]:
                    bucket = state_edges
                elif ncell["district"] != c["district"]:
                    bucket = dist_edges
                else:
                    bucket = seat_edges
            pair = sorted(verts[k], key=lambda v: (v[0] - nx) ** 2 + (v[1] - ny) ** 2)[:2]
            bucket.append(pair)

    if args.focus:
        keep = {a.strip().upper() for a in args.focus.split(",")}
        focus_verts = [verts[k] for k, c in cells.items() if c["state"] in keep]
        if not focus_verts:
            sys.exit(f"--focus {args.focus}: no cells match")
        xs = [v[0] for vv in focus_verts for v in vv]
        ys = [v[1] for vv in focus_verts for v in vv]
    else:
        xs = [v[0] for vv in verts.values() for v in vv]
        ys = [v[1] for vv in verts.values() for v in vv]
    pad = 2 * R
    w = (max(xs) - min(xs) + 2 * pad)
    h = (max(ys) - min(ys) + 2 * pad)
    legend_h = 0.0 if args.focus else 0.16 * h

    fig, ax = plt.subplots(figsize=(w * args.px_per_deg / 100,
                                    (h + legend_h) * args.px_per_deg / 100))
    lw = args.px_per_deg / REF_PX_PER_DEG   # line-weight scale
    ax.add_collection(PolyCollection(polys, facecolors=facecolors,
                                     edgecolors="none", zorder=1))
    ax.add_collection(LineCollection(seat_edges, colors=C_SEAT,
                                     linewidths=W_SEAT * lw, zorder=2, alpha=0.85))
    if args.style == "gap":
        # Districts separated by a wider white channel: white always reads against the
        # saturated party fills, and gap width alone carries the hierarchy.
        ax.add_collection(LineCollection(dist_edges, colors="#ffffff",
                                         linewidths=W_DISTRICT * 1.9 * lw, zorder=3,
                                         capstyle="round", joinstyle="round"))
    else:
        # Dark district line cased in white so it survives both the dark fills
        # (Nationalist, Progressive) and the light ones (Labor).
        ax.add_collection(LineCollection(dist_edges, colors="#ffffff",
                                         linewidths=(W_DISTRICT + 1.5) * lw, zorder=3,
                                         capstyle="round", joinstyle="round"))
        ax.add_collection(LineCollection(dist_edges, colors=C_DISTRICT,
                                         linewidths=W_DISTRICT * lw, zorder=4,
                                         capstyle="round", joinstyle="round"))
    ax.add_collection(LineCollection(state_edges, colors=C_STATE,
                                     linewidths=W_STATE * lw, zorder=5,
                                     capstyle="round", joinstyle="round"))

    if not args.no_labels:
        by_state = defaultdict(list)
        for k, c in cells.items():
            by_state[c["state"]].append(centers[k])
        for ab, pts in by_state.items():
            mx = sum(p[0] for p in pts) / len(pts)
            my = sum(p[1] for p in pts) / len(pts)
            ax.text(mx, my, ab, ha="center", va="center", zorder=6,
                    fontsize=7.5 * lw, fontweight="bold", color="#0b1220",
                    path_effects=[matplotlib.patheffects.withStroke(
                        linewidth=2.4 * lw, foreground="white")])

    # Legend: one swatch per party, left→right ideological order, with seat totals.
    tally = defaultdict(int)
    for c in cells.values():
        tally[c["party"]] += 1
    total = sum(tally.values())
    present = [p for p in left_right if tally.get(p)]
    y_leg = min(ys) - pad - 0.45 * legend_h
    if args.focus:
        present = []
    sw = (max(xs) - min(xs)) / max(len(present), 1)
    for i, p in enumerate(present):
        lx = min(xs) + i * sw
        ax.add_collection(PolyCollection(
            [hex_vertices(lx + 0.35 * R, y_leg, R * 0.62)],
            facecolors=[colors[p]], edgecolors="white", linewidths=0.6, zorder=5))
        ax.text(lx + 1.35 * R, y_leg, f"{names.get(p, p)}\n{tally[p]} seats",
                ha="left", va="center", fontsize=7.2, color="#1e2939", zorder=5)

    ax.text(min(xs), max(ys) + pad * 0.4,
            f"{'Triple' if args.triple else 'Standard'} multi-member House — "
            f"one hexagon = one seat  ({total} seats, "
            f"{len({c['district'] for c in cells.values()})} districts)",
            ha="left", va="bottom", fontsize=11, fontweight="bold", color="#0b1220")
    ax.text(max(xs), min(ys) - pad - 0.95 * legend_h,
            "Cartogram concept and state outlines: Congressional District Hexmap by "
            "Daniel Donner for The Downballot (the-db.co/maps), CC BY 4.0",
            ha="right", va="center", fontsize=6.2, color="#6b7280")

    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad - legend_h, max(ys) + pad)
    ax.set_aspect("equal")
    ax.axis("off")
    out = Path(args.out) if args.out else BASE_DIR / f"hex_seat_cartogram{suffix}.png"
    # 'tight' grows the frame to fit every artist, which would undo a --focus crop.
    plt.savefig(out, dpi=100, facecolor="white",
                bbox_inches=None if args.focus else "tight")
    print(f"wrote {out}  ({total} seats, {len(present)} parties)")


if __name__ == "__main__":
    import matplotlib.patheffects  # noqa: F401  (imported for the label stroke)
    main()

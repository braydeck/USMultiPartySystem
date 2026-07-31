#!/usr/bin/env python3
"""
render_hex_seat_cartogram.py
----------------------------
PROTOTYPE renderer for the one-hexagon-per-seat House cartogram.

Each state's hexagons are clipped to that state's cartogram outline, so the silhouette
stays the real (population-scaled) state shape rather than a castellated hex edge, while
seat boundaries inside the state stay hexagonal. That is how The Downballot's map reads:
smooth state outline, tiled interior.

Party colour is the fill, so district and state separation is carried by line weight:
hairline between seats, heavier between districts, heaviest around the state. Boundary
edges come from hex adjacency — the two vertices nearest a neighbouring cell's centre
are the shared edge — so no polygon boolean operations are needed.

Colours are read from viz/src/constants/parties.ts so the prototype cannot drift from
the app's palette.

Usage
  python pipeline/render_hex_seat_cartogram.py [--triple] [--style cased|gap]
                                               [--focus CA,NV] [--px-per-deg N]
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.patheffects
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.path import Path as MplPath

sys.path.insert(0, str(Path(__file__).parent))
from build_hex_seat_cartogram import hex_center, hex_vertices, neighbors

BASE_DIR = Path(__file__).parent.parent
PARTIES_TS = BASE_DIR / "viz" / "src" / "constants" / "parties.ts"

# Line weights in points at the reference scale, scaled by px-per-deg so the hierarchy
# looks the same zoomed in as it does on the full map.
REF_PX_PER_DEG = 58.0
W_SEAT, W_DISTRICT, W_STATE = 0.5, 1.9, 2.8
C_SEAT, C_DISTRICT, C_STATE = "#ffffff", "#111827", "#0b1220"


def state_stroke(n_seats):
    """State outline weight, thinned for small states.

    A fixed heavy stroke is wider than the narrow features of a 2-seat state — it eats
    Alaska's panhandle and Hawaii's smaller islands entirely — so taper it with size.
    """
    return W_STATE * min(1.0, max(0.4, (n_seats / 10.0) ** 0.5))


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


def compound_path(rings):
    """One closed matplotlib Path covering every ring of a state."""
    return MplPath.make_compound_path(*[
        MplPath(np.array(r + [r[0]]),
                [MplPath.MOVETO] + [MplPath.LINETO] * (len(r) - 1) + [MplPath.CLOSEPOLY])
        for r in rings])


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
    lw = args.px_per_deg / REF_PX_PER_DEG

    # Extent: the state outline for clipped states, the hexagons for unclipped ones.
    keep = ({a.strip().upper() for a in args.focus.split(",")} if args.focus
            else set(data["states"]))
    xs, ys = [], []
    for ab, st in data["states"].items():
        if ab not in keep:
            continue
        if st["clip"]:
            xs += [p[0] for r in st["rings"] for p in r]
            ys += [p[1] for r in st["rings"] for p in r]
        else:
            for c in st["cells"]:
                cx, cy = hex_center(c["col"], c["row"], R, x0, y0)
                for vx, vy in hex_vertices(cx, cy, R):
                    xs.append(vx)
                    ys.append(vy)
    if not xs:
        sys.exit(f"--focus {args.focus}: no states match")

    pad = 2 * R
    w = max(xs) - min(xs) + 2 * pad
    h = max(ys) - min(ys) + 2 * pad
    legend_h = 0.0 if args.focus else 0.16 * h
    fig, ax = plt.subplots(figsize=(w * args.px_per_deg / 100,
                                    (h + legend_h) * args.px_per_deg / 100))

    tally = defaultdict(int)
    districts_seen = set()
    for ab, st in sorted(data["states"].items()):
        cells = {(c["col"], c["row"]): c for c in st["cells"]}
        n_seats = sum(c["isCore"] for c in st["cells"])
        w_state = state_stroke(n_seats)
        for c in st["cells"]:
            districts_seen.add(c["district"])
            if c["isCore"]:
                tally[c["party"]] += 1

        verts = {k: hex_vertices(*hex_center(k[0], k[1], R, x0, y0), R) for k in cells}
        polys = [verts[k] for k in cells]
        facecolors = [colors.get(cells[k]["party"], "#9aa3af") for k in cells]

        seat_edges, dist_edges, hex_rim = [], [], []
        for k, c in cells.items():
            for nb in neighbors(*k):
                ncell = cells.get(nb)
                nx, ny = hex_center(nb[0], nb[1], R, x0, y0)
                if ncell is None:
                    bucket = hex_rim                       # unclipped states only
                elif ncell["district"] != c["district"]:
                    bucket = dist_edges
                elif ncell["core"] != c["core"]:
                    bucket = seat_edges
                else:
                    continue      # same seat — a merged boundary cell, no line
                pair = sorted(verts[k],
                              key=lambda v: (v[0] - nx) ** 2 + (v[1] - ny) ** 2)[:2]
                bucket.append(pair)

        layers = [PolyCollection(polys, facecolors=facecolors, edgecolors="none",
                                 zorder=1),
                  LineCollection(seat_edges, colors=C_SEAT, linewidths=W_SEAT * lw,
                                 zorder=2, alpha=0.85)]
        if args.style == "gap":
            # Districts separated by a wider white channel: white always reads against
            # the saturated party fills, and gap width alone carries the hierarchy.
            layers.append(LineCollection(dist_edges, colors="#ffffff",
                                         linewidths=W_DISTRICT * 1.9 * lw, zorder=3,
                                         capstyle="round", joinstyle="round"))
        else:
            # Dark district line cased in white so it survives both the dark fills
            # (Nationalist, Progressive) and the light ones (Labor).
            layers.append(LineCollection(dist_edges, colors="#ffffff",
                                         linewidths=(W_DISTRICT + 1.5) * lw, zorder=3,
                                         capstyle="round", joinstyle="round"))
            layers.append(LineCollection(dist_edges, colors=C_DISTRICT,
                                         linewidths=W_DISTRICT * lw, zorder=4,
                                         capstyle="round", joinstyle="round"))
        if not st["clip"]:
            layers.append(LineCollection(hex_rim, colors=C_STATE,
                                         linewidths=w_state * lw, zorder=5,
                                         capstyle="round", joinstyle="round"))

        clip = compound_path(st["rings"]) if st["clip"] else None
        for layer in layers:
            ax.add_collection(layer)
            if clip is not None:
                layer.set_clip_path(clip, transform=ax.transData)

        # The state's own outline, over the clipped tiles.
        if st["clip"]:
            for ring in st["rings"]:
                ax.plot([p[0] for p in ring] + [ring[0][0]],
                        [p[1] for p in ring] + [ring[0][1]],
                        color=C_STATE, lw=w_state * lw, zorder=5,
                        solid_capstyle="round", solid_joinstyle="round")

    if not args.no_labels:
        for ab, st in data["states"].items():
            pts = [hex_center(c["col"], c["row"], R, x0, y0)
                   for c in st["cells"] if c["isCore"]]
            mx = sum(p[0] for p in pts) / len(pts)
            my = sum(p[1] for p in pts) / len(pts)
            ax.text(mx, my, ab, ha="center", va="center", zorder=6,
                    fontsize=7.5 * lw, fontweight="bold", color="#0b1220",
                    path_effects=[matplotlib.patheffects.withStroke(
                        linewidth=2.4 * lw, foreground="white")])

    # Legend: one swatch per party, left→right ideological order, with seat totals.
    total = sum(tally.values())
    present = [] if args.focus else [p for p in left_right if tally.get(p)]
    y_leg = min(ys) - pad - 0.45 * legend_h
    sw = (max(xs) - min(xs)) / max(len(present), 1)
    for i, p in enumerate(present):
        lx = min(xs) + i * sw
        ax.add_collection(PolyCollection([hex_vertices(lx + 0.35 * R, y_leg, R * 0.62)],
                                         facecolors=[colors[p]], edgecolors="white",
                                         linewidths=0.6, zorder=5))
        ax.text(lx + 1.35 * R, y_leg, f"{names.get(p, p)}\n{tally[p]} seats",
                ha="left", va="center", fontsize=7.2, color="#1e2939", zorder=5)

    if not args.focus:
        ax.text(min(xs), max(ys) + pad * 0.4,
                f"{'Triple' if args.triple else 'Standard'} multi-member House — "
                f"one hexagon = one seat  ({total} seats, "
                f"{len(districts_seen)} districts)",
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
    print(f"wrote {out}  ({total} seats, {len(tally)} parties)")


if __name__ == "__main__":
    main()

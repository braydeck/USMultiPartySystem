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
import math
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
W_SEAT, W_STATE = 0.5, 3.4
# 'cased' leans on a heavy dark district line; 'gap' on a wide white channel.
W_DISTRICT_CASED, W_CASING = 3.0, 4.8
W_DISTRICT_GAP = 3.6
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
    ap.add_argument("--data", default=None, help="explicit cartogram JSON path")
    ap.add_argument("--no-clip", action="store_true",
                    help="let hexagons extend past the state border instead of being "
                         "clipped to it")
    ap.add_argument("--label-size", type=float, default=17.0,
                    help="state label point size at the reference scale")
    ap.add_argument("--explode", type=float, default=1.0,
                    help="push states apart from the map centre by this factor "
                         "(1.0 = touching as drawn, 1.08 = a visible gap)")
    ap.add_argument("--focus", default=None,
                    help="comma-separated state abbreviations to zoom to")
    args = ap.parse_args()

    suffix = "_triple" if args.triple else ""
    src = (Path(args.data) if args.data else
           BASE_DIR / "data" / "processed" / f"hex_seat_cartogram{suffix}.json")
    data = json.loads(src.read_text())
    meta = data["meta"]
    R, x0, y0 = meta["R"], meta["x0"], meta["y0"]
    colors, names, left_right = load_palette()
    lw = args.px_per_deg / REF_PX_PER_DEG

    def core_centres(st):
        return [hex_center(c["col"], c["row"], R, x0, y0)
                for c in st["cells"] if c["isCore"]]

    # Exploding the map: shift each state away from the centre as a rigid body, which
    # widens the gaps between states without disturbing the hex packing inside any of
    # them. Unclipped, neighbouring states share a hex edge and visually merge, so this
    # is what makes each state readable as a separate shape.
    all_pts = [p for st in data["states"].values() for p in core_centres(st)]
    map_cx = sum(p[0] for p in all_pts) / len(all_pts)
    map_cy = sum(p[1] for p in all_pts) / len(all_pts)
    offsets, centroids = {}, {}
    for ab, st in data["states"].items():
        pts = core_centres(st)
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        centroids[ab] = (cx, cy)
        k = args.explode - 1.0
        offsets[ab] = (k * (cx - map_cx), k * (cy - map_cy))

    def shift(ab, pt):
        ox, oy = offsets[ab]
        return (pt[0] + ox, pt[1] + oy)

    # Extent: the state outline for clipped states, the hexagons for unclipped ones.
    keep = ({a.strip().upper() for a in args.focus.split(",")} if args.focus
            else set(data["states"]))
    xs, ys = [], []
    for ab, st in data["states"].items():
        if ab not in keep:
            continue
        if st["clip"] and not args.no_clip:
            for r in st["rings"]:
                for p in r:
                    px, py = shift(ab, p)
                    xs.append(px)
                    ys.append(py)
        else:
            for c in st["cells"]:
                if not c["isCore"]:
                    continue
                cx, cy = shift(ab, hex_center(c["col"], c["row"], R, x0, y0))
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
        n_seats = len({c["core"] for c in st["cells"] if c["isCore"]})
        clipped = st["clip"] and not args.no_clip
        # Unclipped, a seat is one whole hexagon. The boundary cells exist only to fill
        # the outline for the clip, so drawing them here would inflate every state past
        # its real size and let neighbours collide.
        cells = {(c["col"], c["row"]): c for c in st["cells"]
                 if clipped or c["isCore"]}
        w_state = state_stroke(n_seats)
        seen_seats = set()
        for c in st["cells"]:
            districts_seen.add(c["district"])
            if c["isCore"] and c["core"] not in seen_seats:
                seen_seats.add(c["core"])
                tally[c["party"]] += 1

        verts = {k: hex_vertices(*shift(ab, hex_center(k[0], k[1], R, x0, y0)), R)
                 for k in cells}
        polys = [verts[k] for k in cells]
        facecolors = [colors.get(cells[k]["party"], "#9aa3af") for k in cells]

        seat_edges, dist_edges, hex_rim = [], [], []
        for k, c in cells.items():
            for nb in neighbors(*k):
                ncell = cells.get(nb)
                nx, ny = shift(ab, hex_center(nb[0], nb[1], R, x0, y0))
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
            # Districts separated by a wide white channel: white always reads against
            # the saturated party fills, and gap width alone carries the hierarchy.
            layers.append(LineCollection(dist_edges, colors="#ffffff",
                                         linewidths=W_DISTRICT_GAP * lw, zorder=3,
                                         capstyle="round", joinstyle="round"))
        else:
            # Dark district line cased in white so it survives both the dark fills
            # (Nationalist, Progressive) and the light ones (Labor).
            layers.append(LineCollection(dist_edges, colors="#ffffff",
                                         linewidths=W_CASING * lw, zorder=3,
                                         capstyle="round", joinstyle="round"))
            layers.append(LineCollection(dist_edges, colors=C_DISTRICT,
                                         linewidths=W_DISTRICT_CASED * lw, zorder=4,
                                         capstyle="round", joinstyle="round"))
        if not clipped:
            layers.append(LineCollection(hex_rim, colors=C_STATE,
                                         linewidths=w_state * lw, zorder=5,
                                         capstyle="round", joinstyle="round"))

        rings = [[shift(ab, p) for p in r] for r in st["rings"]]
        clip = compound_path(rings) if clipped else None
        for layer in layers:
            ax.add_collection(layer)
            if clip is not None:
                layer.set_clip_path(clip, transform=ax.transData)

        # The state's own outline, over the clipped tiles.
        if clipped:
            for ring in rings:
                ax.plot([p[0] for p in ring] + [ring[0][0]],
                        [p[1] for p in ring] + [ring[0][1]],
                        color=C_STATE, lw=w_state * lw, zorder=5,
                        solid_capstyle="round", solid_joinstyle="round")

    if not args.no_labels:
        # Labels outside the state, as the published hexmap does: a label on top of the
        # tiles competes with ten party fills, and a two-hex state has nowhere legible to
        # put one. Placement is by fixed preference — bottom-right for every state that
        # can take it, so the eye learns where to look — falling back through the other
        # corners only where a neighbour is in the way.
        DIRECTIONS = [(0.71, -0.71), (-0.71, -0.71), (0.71, 0.71), (-0.71, 0.71),
                      (0.0, -1.0), (1.0, 0.0), (0.0, 1.0), (-1.0, 0.0)]
        occupied = np.array([shift(ab2, hex_center(c["col"], c["row"], R, x0, y0))
                             for ab2, st2 in data["states"].items()
                             for c in st2["cells"]])

        # Point size → degrees, so the clearance test knows how big the text really is.
        deg_per_pt = 100.0 / (72.0 * args.px_per_deg)
        fs = args.label_size * lw
        lab_h = fs * deg_per_pt
        # Big states first, so they get the preferred bottom-right slot and the small
        # ones adapt around them.
        by_size = sorted(data["states"].items(),
                         key=lambda kv: (-len({c["core"] for c in kv[1]["cells"]
                                               if c["isCore"]}), kv[0]))
        placements, taken_boxes = {}, []
        for ab, st in by_size:
            cx, cy = shift(ab, centroids[ab])
            pts = [shift(ab, p) for p in core_centres(st)]
            lab_w = 0.68 * lab_h * len(ab)
            chosen = None
            for dx, dy in DIRECTIONS:
                reach = max((p[0] - cx) * dx + (p[1] - cy) * dy for p in pts)
                for extra in (0.9, 1.6, 2.4):
                    ax_, ay_ = (cx + dx * (reach + extra * R), cy + dy * (reach + extra * R))
                    ha = "left" if dx > 0.3 else "right" if dx < -0.3 else "center"
                    va = "bottom" if dy > 0.3 else "top" if dy < -0.3 else "center"
                    lx0 = ax_ if ha == "left" else ax_ - lab_w if ha == "right" else ax_ - lab_w / 2
                    ly0 = ay_ if va == "bottom" else ay_ - lab_h if va == "top" else ay_ - lab_h / 2
                    # Clear if no hexagon centre falls inside the text box, grown by a
                    # hexagon's reach plus a little breathing room.
                    m = 0.95 * R
                    hit = ((occupied[:, 0] > lx0 - m) & (occupied[:, 0] < lx0 + lab_w + m)
                           & (occupied[:, 1] > ly0 - m) & (occupied[:, 1] < ly0 + lab_h + m))
                    if hit.any():
                        continue
                    box = (lx0 - m / 2, ly0 - m / 2,
                           lx0 + lab_w + m / 2, ly0 + lab_h + m / 2)
                    # Labels must clear each other too, not just the tiles.
                    if any(box[0] < b[2] and b[0] < box[2]
                           and box[1] < b[3] and b[1] < box[3] for b in taken_boxes):
                        continue
                    chosen = (ax_, ay_, ha, va, box)
                    break
                if chosen:
                    break
            if chosen is None:
                chosen = (cx, cy, "center", "center", None)
            if chosen[4]:
                taken_boxes.append(chosen[4])
            placements[ab] = chosen[:4]

        for ab, (lx, ly, ha, va) in placements.items():
            ax.text(lx, ly, ab, ha=ha, va=va, zorder=6,
                    fontsize=fs, fontweight="bold", color="#0b1220",
                    path_effects=[matplotlib.patheffects.withStroke(
                        linewidth=0.30 * fs, foreground="white")])

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

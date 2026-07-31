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
# 'cased' leans on a heavy dark district line; 'gap' on a wide white channel. The base
# weights are calibrated at R_CALIB; a coarser lattice needs a heavier line because the
# border staircases along hex edges, and a stroke thinner than a step reads as sawteeth.
W_DISTRICT_CASED, W_CASING = 3.0, 4.8
W_DISTRICT_GAP = 3.6
R_CALIB = 0.1886        # the 5-cells-per-seat lattice, where these weights look right


def district_weights(R, scale):
    """Dark line and casing widths for a lattice of circumradius R."""
    k = min(1.8, max(1.0, (R / R_CALIB) ** 0.55)) * scale
    return W_DISTRICT_CASED * k, W_CASING * k, W_DISTRICT_GAP * k
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


def chain_edges(edges, tol=6):
    """Join loose boundary segments into continuous polylines.

    Emitting each hex edge as its own two-point segment means matplotlib has no path to
    join or smooth, so every corner of a district border stays a hard angle however heavy
    the stroke — which is what makes the border read as sawteeth at a coarse lattice.
    Walking the segments into chains gives one stroke per border, and something to round.

    At a junction where three districts meet, the continuation that turns least is taken,
    which keeps a border from doubling back on itself.
    """
    def key(pt):
        return (round(pt[0], tol), round(pt[1], tol))

    at = defaultdict(list)
    for i, (a, b) in enumerate(edges):
        at[key(a)].append(i)
        at[key(b)].append(i)
    used = [False] * len(edges)
    chains = []
    for start in range(len(edges)):
        if used[start]:
            continue
        used[start] = True
        a, b = edges[start]
        chain = [a, b]
        # Extend from the tail, then from the head.
        for _ in range(2):
            while True:
                tail, prev = chain[-1], chain[-2]
                vx, vy = tail[0] - prev[0], tail[1] - prev[1]
                best, best_turn = None, None
                for j in at[key(tail)]:
                    if used[j]:
                        continue
                    c, d = edges[j]
                    nxt = d if key(c) == key(tail) else c
                    wx, wy = nxt[0] - tail[0], nxt[1] - tail[1]
                    dot = (vx * wx + vy * wy) / (math.hypot(vx, vy) * math.hypot(wx, wy)
                                                 or 1)
                    if best_turn is None or dot > best_turn:
                        best, best_turn = (j, nxt), dot
                if best is None:
                    break
                j, nxt = best
                used[j] = True
                chain.append(nxt)
                if key(nxt) == key(chain[0]):
                    break
            chain.reverse()
        chains.append(chain)
    return chains


def round_corners(pts, frac=0.28, iters=2):
    """Cut each corner back along its two edges, twice — a fillet, not a re-spline.

    Deliberately local: the line stays on the lattice along straight runs and only
    softens at the turns, so it does not drift away from the hexagon fills underneath.
    """
    closed = abs(pts[0][0] - pts[-1][0]) < 1e-9 and abs(pts[0][1] - pts[-1][1]) < 1e-9
    out = [tuple(p) for p in pts]
    for _ in range(iters):
        if len(out) < 3:
            break
        new = [] if closed else [out[0]]
        rng = range(len(out) - 1) if closed else range(1, len(out) - 1)
        seq = out[:-1] if closed else out
        n = len(seq)
        for i in (range(n) if closed else range(1, n - 1)):
            prv, cur, nxt = seq[(i - 1) % n], seq[i], seq[(i + 1) % n]
            new.append((cur[0] + frac * (prv[0] - cur[0]),
                        cur[1] + frac * (prv[1] - cur[1])))
            new.append((cur[0] + frac * (nxt[0] - cur[0]),
                        cur[1] + frac * (nxt[1] - cur[1])))
        if closed:
            new.append(new[0])
        else:
            new.append(out[-1])
        out = new
    return out


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
    ap.add_argument("--district-scale", type=float, default=1.0,
                    help="multiply the auto district line weight")
    ap.add_argument("--fixed-weight", action="store_true",
                    help="do not scale the district line weight with hex size")
    ap.add_argument("--sharp", action="store_true",
                    help="skip corner rounding on district borders")
    ap.add_argument("--report-labels", action="store_true",
                    help="print which side each state label landed on")
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
    w_dist, w_casing, w_gap = district_weights(
        R_CALIB if args.fixed_weight else R, args.district_scale)

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
        # One continuous stroke per border, corners filleted, so the staircase reads as
        # a line rather than a row of notches.
        dist_paths = [c if args.sharp else round_corners(c)
                      for c in chain_edges(dist_edges)]
        if args.style == "gap":
            # Districts separated by a wide white channel: white always reads against
            # the saturated party fills, and gap width alone carries the hierarchy.
            layers.append(LineCollection(dist_paths, colors="#ffffff",
                                         linewidths=w_gap * lw, zorder=3,
                                         capstyle="round", joinstyle="round"))
        else:
            # Dark district line cased in white so it survives both the dark fills
            # (Nationalist, Progressive) and the light ones (Labor).
            layers.append(LineCollection(dist_paths, colors="#ffffff",
                                         linewidths=w_casing * lw, zorder=3,
                                         capstyle="round", joinstyle="round"))
            layers.append(LineCollection(dist_paths, colors=C_DISTRICT,
                                         linewidths=w_dist * lw, zorder=4,
                                         capstyle="round", joinstyle="round"))
        if not clipped:
            rim = [c if args.sharp else round_corners(c) for c in chain_edges(hex_rim)]
            layers.append(LineCollection(rim, colors=C_STATE,
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
        # Labels sit outside the state, hugging its silhouette. Each candidate is a side
        # plus a bias along that side — "below, toward the right", "right, toward the
        # top" — rather than a diagonal ray from the centre, which on an irregular shape
        # strands the label out in space. Preference leans bottom-then-right so the eye
        # learns one place to look; a state only moves elsewhere when that slot is taken.
        # Hand-set sides where the state's own geometry has an obviously better slot
        # than the default order finds. Each is still validated for clearance and falls
        # back to the ordered search if something else has taken the space.
        PREFERRED = {
            "MA": ("bottom", "right"), "NV": ("top", "right"), "MN": ("top", "right"),
            "MI": ("right", "top"),    "CA": ("bottom", "right"),
            "NM": ("top", "right"),    "TX": ("bottom", "right"),
            "MS": ("bottom", "right"), "LA": ("bottom", "right"),
            "GA": ("right", "bottom"), "VA": ("bottom", "right"),
            "FL": ("right", "center"), "PA": ("right", "top"),
        }
        CANDIDATES = [("bottom", "right"), ("right", "bottom"), ("right", "center"),
                      ("bottom", "center"), ("right", "top"), ("top", "right"),
                      ("bottom", "left"), ("top", "center"), ("left", "bottom"),
                      ("left", "center"), ("top", "left"), ("left", "top")]
        occupied = np.array([shift(ab2, hex_center(c["col"], c["row"], R, x0, y0))
                             for ab2, st2 in data["states"].items()
                             for c in st2["cells"]])
        by_state_pts = {ab2: np.array([shift(ab2, hex_center(c["col"], c["row"],
                                                            R, x0, y0))
                                       for c in st2["cells"]])
                        for ab2, st2 in data["states"].items()}

        def nearest_state(pt):
            best, bd = None, None
            for ab2, arr in by_state_pts.items():
                dd = float(np.min((arr[:, 0] - pt[0]) ** 2 + (arr[:, 1] - pt[1]) ** 2))
                if bd is None or dd < bd:
                    best, bd = ab2, dd
            return best

        def silhouette(ab, st):
            """Points tracing what is actually drawn for this state."""
            if st["clip"] and not args.no_clip:
                return [shift(ab, p) for r in st["rings"] for p in r]
            out = []
            for c in st["cells"]:
                if c["isCore"]:
                    out += hex_vertices(*shift(ab, hex_center(c["col"], c["row"],
                                                              R, x0, y0)), R)
            return out

        deg_per_pt = 100.0 / (72.0 * args.px_per_deg)
        fs = args.label_size * lw
        lab_h = fs * deg_per_pt

        def anchor_for(pts, side, bias, gap):
            xs_ = [p[0] for p in pts]; ys_ = [p[1] for p in pts]
            xlo, xhi, ylo, yhi = min(xs_), max(xs_), min(ys_), max(ys_)
            band = 0.30
            if side in ("bottom", "top"):
                keep = ([p for p in pts if p[1] <= ylo + band * (yhi - ylo)]
                        if side == "bottom" else
                        [p for p in pts if p[1] >= yhi - band * (yhi - ylo)])
                px = (max(p[0] for p in keep) if bias == "right" else
                      min(p[0] for p in keep) if bias == "left" else
                      (xlo + xhi) / 2)
                near = [p for p in keep if abs(p[0] - px) < 1.2 * R] or keep
                py = min(p[1] for p in near) if side == "bottom" else max(p[1] for p in near)
                if side == "bottom":
                    return px, py - gap, ("left" if bias == "right" else
                                          "right" if bias == "left" else "center"), "top"
                return px, py + gap, ("left" if bias == "right" else
                                      "right" if bias == "left" else "center"), "bottom"
            keep = ([p for p in pts if p[0] >= xhi - band * (xhi - xlo)]
                    if side == "right" else
                    [p for p in pts if p[0] <= xlo + band * (xhi - xlo)])
            py = (min(p[1] for p in keep) if bias == "bottom" else
                  max(p[1] for p in keep) if bias == "top" else (ylo + yhi) / 2)
            near = [p for p in keep if abs(p[1] - py) < 1.2 * R] or keep
            px = max(p[0] for p in near) if side == "right" else min(p[0] for p in near)
            va = ("top" if bias == "bottom" else "bottom" if bias == "top" else "center")
            if side == "right":
                return px + gap, py, "left", va
            return px - gap, py, "right", va

        by_size = sorted(data["states"].items(),
                         key=lambda kv: (-len({c["core"] for c in kv[1]["cells"]
                                               if c["isCore"]}), kv[0]))
        placements, taken = {}, []
        for ab, st in by_size:
            pts = silhouette(ab, st)
            lab_w = 0.70 * lab_h * len(ab)
            chosen = None
            order_here = CANDIDATES
            if ab in PREFERRED:
                order_here = [PREFERRED[ab]] + [c for c in CANDIDATES
                                                if c != PREFERRED[ab]]
            # Gap outermost: exhaust every side at the tightest offset before moving the
            # label further out, so a label only drifts (and earns a leader line) when
            # the state is genuinely boxed in on all sides.
            for gap in (0.55 * R, 1.1 * R, 1.8 * R, 2.8 * R, 4.2 * R, 6.0 * R, 8.5 * R):
                for side, bias in order_here:
                    ax_, ay_, ha, va = anchor_for(pts, side, bias, gap)
                    lx0 = (ax_ if ha == "left" else ax_ - lab_w if ha == "right"
                           else ax_ - lab_w / 2)
                    ly0 = (ay_ if va == "bottom" else ay_ - lab_h if va == "top"
                           else ay_ - lab_h / 2)
                    m = 0.95 * R
                    if ((occupied[:, 0] > lx0 - m) & (occupied[:, 0] < lx0 + lab_w + m)
                            & (occupied[:, 1] > ly0 - m)
                            & (occupied[:, 1] < ly0 + lab_h + m)).any():
                        continue        # would sit on some state's tiles
                    box = (lx0 - 0.85 * lab_h, ly0 - 0.5 * lab_h,
                           lx0 + lab_w + 0.85 * lab_h, ly0 + lab_h + 0.5 * lab_h)
                    if any(box[0] < b[2] and b[0] < box[2]
                           and box[1] < b[3] and b[1] < box[3] for b in taken):
                        continue        # would sit on another label
                    # A label nearer some other state than its own is worse than no
                    # label — that is what made the IL/IN/OH/KY/WV cluster unreadable.
                    # Only enforced for labels sitting against their state; once a label
                    # is far enough out to earn a leader line, the line says which state
                    # it belongs to.
                    if gap <= 2.0 * R and nearest_state((ax_, ay_)) != ab:
                        continue
                    chosen = (ax_, ay_, ha, va, box, side, bias, gap, pts)
                    break
                if chosen:
                    break
            if chosen is None:
                # Ringed in on every side (West Virginia). Sweep outward in all
                # directions for the first clear spot; a leader line will connect it.
                cx, cy = shift(ab, centroids[ab])
                reach0 = max(math.hypot(q[0] - cx, q[1] - cy) for q in pts)
                for mult in (1.4, 1.9, 2.5, 3.2, 4.0):
                    for k in range(24):
                        ang = 2 * math.pi * k / 24
                        dx, dy = math.cos(ang), math.sin(ang)
                        ax_, ay_ = cx + dx * reach0 * mult, cy + dy * reach0 * mult
                        ha = "left" if dx > 0.3 else "right" if dx < -0.3 else "center"
                        va = "bottom" if dy > 0.3 else "top" if dy < -0.3 else "center"
                        lx0 = (ax_ if ha == "left" else ax_ - lab_w if ha == "right"
                               else ax_ - lab_w / 2)
                        ly0 = (ay_ if va == "bottom" else ay_ - lab_h if va == "top"
                               else ay_ - lab_h / 2)
                        m = 0.95 * R
                        if ((occupied[:, 0] > lx0 - m) & (occupied[:, 0] < lx0 + lab_w + m)
                                & (occupied[:, 1] > ly0 - m)
                                & (occupied[:, 1] < ly0 + lab_h + m)).any():
                            continue
                        box = (lx0 - 0.85 * lab_h, ly0 - 0.5 * lab_h,
                               lx0 + lab_w + 0.85 * lab_h, ly0 + lab_h + 0.5 * lab_h)
                        if any(box[0] < b[2] and b[0] < box[2]
                               and box[1] < b[3] and b[1] < box[3] for b in taken):
                            continue
                        chosen = (ax_, ay_, ha, va, box, "far", "sweep", 9.9 * R, pts)
                        break
                    if chosen:
                        break
            if chosen is None:
                cx, cy = shift(ab, centroids[ab])
                chosen = (cx, cy, "center", "center", None, "none", "none", 0.0, pts)
            if chosen[4]:
                taken.append(chosen[4])
            placements[ab] = chosen

        for ab, pl in placements.items():
            # A state wedged between neighbours has no room beside it, so its label goes
            # out into open space with a leader line back — standard practice for
            # Delaware and Rhode Island on any printed map.
            if pl[7] > 2.0 * R:
                near = min(pl[8], key=lambda q: (q[0] - pl[0]) ** 2 + (q[1] - pl[1]) ** 2)
                ax.plot([near[0], pl[0]], [near[1], pl[1]], color="#0b1220",
                        lw=0.7 * lw, zorder=5, solid_capstyle="round")
            ax.text(pl[0], pl[1], ab, ha=pl[2], va=pl[3], zorder=6,
                    fontsize=fs, fontweight="bold", color="#0b1220",
                    path_effects=[matplotlib.patheffects.withStroke(
                        linewidth=0.30 * fs, foreground="white")])
        if args.report_labels:
            for ab, pl in sorted(placements.items()):
                print(f"   {ab}: {pl[5]}/{pl[6]}")

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

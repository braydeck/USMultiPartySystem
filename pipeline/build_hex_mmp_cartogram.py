#!/usr/bin/env python3
"""
build_hex_mmp_cartogram.py
--------------------------
Paired cartogram for MMP: every state drawn twice, once per tier.

MMP splits a state's delegation almost in half — 436 district seats and 437 top-off
seats nationally — so neither tier is a companion to the other the way the reserve tier
is. Each state therefore gets two copies of itself side by side: one holding the seats it
elects in its real congressional districts, one holding the seats it elects statewide.

One hexagon is one seat at the same size as everywhere else on the map, so a copy's area
is its seat count: a copy holding half a state's seats is sqrt(0.5) = 0.707 of its width.
The two copies together cover exactly the area the single state covers on the base map,
which is what keeps the country the same size.

Inputs
  data/raw/hexmap/HexStv30/              state outlines (population-scaled)
  viz/public/data/houseMmp.json          districts per state, and the top-off count
  data/processed/voter_county_fips.csv    county → cd119, for seeding district regions
  viz/public/topojson/counties-10m.json   real county positions

Output
  data/processed/hex_mmp_cartogram{,_triple}.json   prototype, with parties
  viz/public/hexmap/hex_mmp_cartogram{,_triple}.json   geometry only, for the app

Usage
  python pipeline/build_hex_mmp_cartogram.py
  python pipeline/build_hex_mmp_cartogram.py --triple
"""

import argparse
import json
import math
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

sys.path.insert(0, str(__file__.rsplit("/", 1)[0]))
from build_hex_seat_cartogram import (  # noqa: E402
    EXPLODE, HEX_AREA_PER_R2, SQRT3, SUB_DIV, TOPO_PATH, OUT_DIR, VIZ_HEX_DIR,
    StateShape, _bbox_gap, _clear, _hull, _poly_parts, hex_center, lattice_R, map_seed,
    neighbors, partition_equal, polygon_area, rings_centroid, sample_offsets,
    spread_coincident,
)


def _bbox(rings):
    xs = [q[0] for r in rings for q in r]
    ys = [q[1] for r in rings for q in r]
    return (min(xs), min(ys), max(xs), max(ys))


def _far(box, blockers, min_gap):
    """True when nothing is close enough to need the exact clearance test."""
    probe = {"bbox": box}
    return all(_bbox_gap(probe, b) >= min_gap for b in blockers)


def clear_fast(rings, blockers, min_gap):
    """Clearance, skipping the exact test when bounding boxes are already far apart."""
    box = _bbox(rings)
    if _far(box, blockers, min_gap):
        return True
    near = [b for b in blockers if _bbox_gap({"bbox": box}, b) < min_gap]
    return _clear(rings, near, min_gap)
from hexmap_io import load_layer, county_centroids  # noqa: E402

MMP_PATH = lambda: None  # replaced below
BASE = OUT_DIR.parent.parent
MMP_JSON = BASE / "viz" / "public" / "data" / "houseMmp.json"
CD_PATH = BASE / "data" / "processed" / "voter_county_fips.csv"

F5_FALLBACK = ["PRG", "DSA", "LIB", "LBR", "OAO", "STY", "CUP", "CON", "POP", "NAT"]

# The paired map draws 102 shapes where the House map draws 51, so the states need
# pushing further apart before their pairs have room to sit together.
MMP_EXPLODE = 1.7


def load_mmp(triple):
    """Per state: its real districts, its top-off count, and each district's winner."""
    raw = json.loads(MMP_JSON.read_text())
    block = raw["triple" if triple else "double"]["5"]
    per_state = {}
    for fips, st in block["byState"].items():
        dists = sorted(block["districts"].get(fips, {}))
        per_state[fips] = {
            "abbr": st["abbr"],
            "districts": dists,
            "topoff": st["totalSeats"] - st["districtCount"],
            "total": st["totalSeats"],
            "winner": {d: v["winner"] for d, v in block["districts"].get(fips, {}).items()},
            "topoffSeats": st["topoffSeats"],
        }
    return per_state


def cd_centroids():
    """Mean county position per real district, from the respondents' own counties."""
    cds = pd.read_csv(CD_PATH).dropna(subset=["countyfips", "cd119"])
    cds["countyfips"] = cds["countyfips"].astype(np.int64)
    cds["cd119"] = cds["cd119"].astype(np.int64)
    state = cds["countyfips"] // 1000
    key = [f"{s:02d}-{d:02d}" for s, d in zip(state, cds["cd119"])]
    cds = cds.assign(cd_key=key)
    # The district most of a county's respondents sit in.
    maj = (cds.groupby(["countyfips", "cd_key"]).size().reset_index(name="n")
           .sort_values(["countyfips", "n"], ascending=[True, False])
           .drop_duplicates("countyfips"))
    cents = county_centroids(TOPO_PATH)
    acc = defaultdict(list)
    for fips, cd in zip(maj["countyfips"], maj["cd_key"]):
        c = cents.get(f"{fips:05d}")
        if c:
            acc[cd].append(c)
    return {cd: (sum(p[0] for p in v) / len(v), sum(p[1] for p in v) / len(v))
            for cd, v in acc.items()}


def real_bboxes():
    """Real lon/lat bbox per state, from its counties."""
    cents = county_centroids(TOPO_PATH)
    acc = defaultdict(list)
    for fips, c in cents.items():
        acc[fips[:2]].append(c)
    return {s: (min(p[0] for p in v), min(p[1] for p in v),
                max(p[0] for p in v), max(p[1] for p in v)) for s, v in acc.items()}


def scaled(rings, at, k, c):
    return [[(at[0] + (x - c[0]) * k, at[1] + (y - c[1]) * k) for x, y in ring]
            for ring in rings]


def place_pair(rings, kd, kx, blockers, min_gap, R, away_from):
    """Two copies of a state, side by side, clear of everything already placed.

    The pair is swept through orientations and separations rather than fixed left-right:
    a state hemmed in by its neighbours may only have room on the diagonal, and the two
    copies cover the same area the single state did, so the room is there to find.
    """
    c = rings_centroid(rings)
    pts = [q for ring in rings for q in ring]
    ext = max(max(q[0] for q in pts) - min(q[0] for q in pts),
              max(q[1] for q in pts) - min(q[1] for q in pts))
    # The pair may also shift as a whole when the state's own spot is boxed in by
    # neighbours already placed. The shift is searched in every direction, not just
    # outward from the map centre: outward-only sent Nevada west, straight over the top
    # of California, when the room it needed was in the empty Great Basin to the east.
    # Among the directions that clear at the smallest shift, the one that stays closest
    # to the middle of the country wins, which keeps a state from leapfrogging a
    # neighbour into the ocean.
    dirs = [math.radians(a) for a in range(0, 360, 30)]
    for shift in (0.0, 0.2, 0.4, 0.65, 0.95, 1.3, 1.7, 2.2, 2.8, 3.5, 4.4, 5.5, 7.0):
        found = []
        for ang_move in ([math.atan2(0, 1)] if shift == 0 else dirs):
            base = (c[0] + math.cos(ang_move) * shift * ext,
                    c[1] + math.sin(ang_move) * shift * ext)
            for sep in (0.5, 0.55, 0.61, 0.68, 0.76, 0.86):
                hit = None
                for turn in (0, 30, -30, 60, -60, 90, -90, 120, -120, 150, -150, 180):
                    a = math.radians(turn)
                    d = sep * ext
                    p1 = (base[0] - math.cos(a) * d / 2, base[1] - math.sin(a) * d / 2)
                    p2 = (base[0] + math.cos(a) * d / 2, base[1] + math.sin(a) * d / 2)
                    A = scaled(rings, p1, kd, c)
                    B = scaled(rings, p2, kx, c) if kx else A
                    if not clear_fast(A, blockers, min_gap):
                        continue
                    if kx and not clear_fast(B, blockers, min_gap):
                        continue
                    if kx and not _clear(A, [_poly_parts(B)], min_gap):
                        continue
                    hit = (A, B, p1, p2)
                    break
                if hit:
                    pull = math.hypot(base[0] - away_from[0], base[1] - away_from[1])
                    found.append((pull, hit))
                    break
            if shift == 0 and found:
                break
        if found:
            found.sort(key=lambda t: t[0])
            A, B, p1, p2 = found[0][1]
            return A, B, p1, p2, c, True
    d = 1.5 * ext
    return (scaled(rings, (c[0] - d / 2, c[1]), kd, c),
            scaled(rings, (c[0] + d / 2, c[1]), kx, c),
            (c[0] - d / 2, c[1]), (c[0] + d / 2, c[1]), c, False)


def tile_copy(rings, seats, seeds, R, x0, y0):
    """Cut a copy into one equal-area region per seat, on the sub-lattice.

    Regions are grown rather than assigned by nearest seed, so each seat is one piece.
    """
    shape = StateShape("copy", rings)
    sub = R / SUB_DIV
    bx0, by0, bx1, by1 = shape.bbox
    c0 = int(math.floor((bx0 - x0) / (SQRT3 * sub))) - 1
    c1 = int(math.ceil((bx1 - x0) / (SQRT3 * sub))) + 1
    r0 = int(math.floor((by0 - y0) / (1.5 * sub))) - 1
    r1 = int(math.ceil((by1 - y0) / (1.5 * sub))) + 1
    grid = [(c, r) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)]
    pts = np.array([hex_center(c, r, sub, x0, y0) for c, r in grid])
    keep = shape.contains(pts)
    pos = {cr: (float(p[0]), float(p[1])) for cr, p, ok in zip(grid, pts, keep) if ok}
    if len(pos) < len(seats):
        return {}

    # Settle the seeds before growing. The 59 real districts carved inside a single
    # county share one centroid, so raw they land within a hex of each other and most get
    # walled in by their neighbours the moment growth starts — which left seats holding a
    # single cell next to seats holding a hundred. A capacity-capped pass pulls them
    # apart: each seed has to own its own share, so it is dragged to the middle of it.
    cells = list(pos)
    n = len(seats)
    seeds = list(seeds)
    quota = [len(cells) // n + (1 if i < len(cells) % n else 0) for i in range(n)]
    for _ in range(10):
        pairs = sorted(((pos[c][0] - sx) ** 2 + (pos[c][1] - sy) ** 2, c, i)
                       for c in cells for i, (sx, sy) in enumerate(seeds))
        left = list(quota)
        take = {}
        for _, c, i in pairs:
            if c in take or left[i] <= 0:
                continue
            take[c] = i
            left[i] -= 1
        for c in cells:
            if c not in take:
                i = max(range(n), key=lambda j: left[j])
                take[c] = i
                left[i] -= 1
        moved = 0.0
        for i in range(n):
            mine = [pos[c] for c, j in take.items() if j == i]
            if not mine:
                continue
            nx = sum(q[0] for q in mine) / len(mine)
            ny = sum(q[1] for q in mine) / len(mine)
            moved = max(moved, math.hypot(nx - seeds[i][0], ny - seeds[i][1]))
            seeds[i] = (nx, ny)
        if moved < 0.02 * sub:
            break

    owner = partition_equal(cells, pos, list(range(n)), seeds)
    return {cr: seats[i] for cr, i in owner.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--triple", action="store_true")
    ap.add_argument("--explode", type=float, default=None,
                    help="override the map explode; the paired map needs more than the "
                         "House map because it draws twice as many shapes")
    ap.add_argument("--out", default=None)
    ap.add_argument("--viz-out", default=None)
    args = ap.parse_args()
    suffix = "_triple" if args.triple else ""

    mmp = load_mmp(args.triple)
    st_layer = load_layer("HexStv30", "HexSTv30")
    ab_by_fips = {a["GEOID"][:2]: a["STATEAB"] for a, _ in load_layer("HexCDv32")}
    fips_by_ab = {v: k for k, v in ab_by_fips.items()}
    states = {a["STATEAB"]: StateShape(a["STATEAB"], r) for a, r in st_layer}


    total_seats = sum(v["total"] for v in mmp.values())
    # Both copies together cover the state's own area, so the lattice is the base map's:
    # sized over the outlines that exist, then reused for the states added by hand.
    have = {ab: st for ab, st in states.items() if fips_by_ab.get(ab) in mmp}
    R_EST = lattice_R(have, sum(mmp[fips_by_ab[ab]]["total"] for ab in have))
    R = R_EST
    # DC has no population-scaled outline in the states file, so it borrows its delegate
    # hexagon, scaled up to hold its own delegation at the map's hex size. Without this
    # it drops off the map and the chamber comes up two seats short.
    if "DC" not in states and "11" in mmp:
        dd = {a["ABBREV"]: r for a, r in load_layer("HexDDv20")}
        hexring = dd["DC"]
        hcx, hcy = rings_centroid(hexring)
        want = mmp["11"]["total"] * HEX_AREA_PER_R2 * R_EST * R_EST
        grow = math.sqrt(want / max(polygon_area(hexring), 1e-9))
        states["DC"] = StateShape("DC", [[(hcx + (x - hcx) * grow, hcy + (y - hcy) * grow)
                                          for x, y in ring] for ring in hexring])
        fips_by_ab["DC"] = "11"
        ab_by_fips["11"] = "DC"
    x0, y0 = 0.0, 0.0
    print(f"{total_seats} seats, R={R:.4f} deg, sub-lattice 1/{SUB_DIV}")

    cdc = cd_centroids()
    rbox = real_bboxes()

    # Explode offsets, as the app applies them, so placement is searched where the
    # copies will actually be drawn.
    weight = {ab: mmp[fips_by_ab[ab]]["total"] for ab in states if fips_by_ab.get(ab) in mmp}
    cent = {ab: rings_centroid(states[ab].rings) for ab in weight}
    mcx = sum(cent[ab][0] * weight[ab] for ab in weight) / sum(weight.values())
    mcy = sum(cent[ab][1] * weight[ab] for ab in weight) / sum(weight.values())
    k = (args.explode or MMP_EXPLODE) - 1
    off = {ab: (k * (cent[ab][0] - mcx), k * (cent[ab][1] - mcy)) for ab in weight}

    min_gap = 0.55 * R
    blockers, out_states, crowded = [], {}, []
    order = sorted(weight, key=lambda ab: -weight[ab])
    for ab in order:
        fips = fips_by_ab[ab]
        info = mmp[fips]
        D, X, T = len(info["districts"]), info["topoff"], info["total"]
        dx, dy = off[ab]
        rings = [[(x + dx, y + dy) for x, y in r] for r in states[ab].rings]
        kd = math.sqrt(D / T)
        kx = math.sqrt(X / T) if X else 0.0
        A, B, p1, p2, c, ok = place_pair(rings, kd, kx, blockers, min_gap, R, (mcx, mcy))
        if not ok:
            crowded.append(ab)
        blockers.append(_poly_parts(A))
        if X:
            blockers.append(_poly_parts(B))
            # Reserve the gap between the two copies too, so a neighbouring state cannot
            # settle in the middle of this state's pair and break the reading.
            blockers.append(_poly_parts([_hull([q for r in A + B for q in r])]))

        # District copy: one region per real district, seeded from its counties.
        abox = StateShape("a", A).bbox
        seeds = {}
        for d in info["districts"]:
            rp = cdc.get(d)
            seeds[d] = (map_seed(rp, rbox.get(fips, abox), abox) if rp
                        else ((abox[0] + abox[2]) / 2, (abox[1] + abox[3]) / 2))
        seeds = spread_coincident(seeds, R * kd)
        dcells = tile_copy(A, info["districts"], [seeds[d] for d in info["districts"]], R, x0, y0)

        # Top-off copy: its seats have no district, so they are spread west to east and
        # the app fills them in F5 order, the same as a district's own seats.
        tcells = {}
        if X:
            bbox = StateShape("b", B).bbox
            tseats = [f"{fips}-TOP-{i:02d}" for i in range(X)]
            tseeds = [(bbox[0] + (bbox[2] - bbox[0]) * (i + 0.5) / X,
                       (bbox[1] + bbox[3]) / 2) for i in range(X)]
            tcells = tile_copy(B, tseats, tseeds, R, x0, y0)

        out_states[ab] = {
            "district": {"rings": A, "cells": dcells, "seats": info["districts"]},
            "topoff": ({"rings": B, "cells": tcells, "seats": [f"{fips}-TOP-{i:02d}" for i in range(X)]}
                       if X else None),
            "fips": fips,
            "offset": [dx, dy],
        }
        short = [s for s in info["districts"] if s not in set(dcells.values())]
        if short:
            print(f"   {ab}: WARNING {len(short)} district seat(s) got no cells")

    proto = {
        "meta": {"R": R, "x0": x0, "y0": y0, "orientation": "pointy-top",
                 "seats": total_seats, "subDiv": SUB_DIV, "triple": args.triple,
                 "explode": args.explode or MMP_EXPLODE,
                 "source": "Congressional District Hexmap v3.2 by Daniel Donner for "
                           "The Downballot (https://the-db.co/maps), CC BY 4.0"},
        "states": {},
    }
    for ab, v in sorted(out_states.items()):
        entry = {"fips": v["fips"], "offset": [round(q, 6) for q in v["offset"]], "tiers": {}}
        for kind in ("district", "topoff"):
            t = v[kind]
            if not t:
                continue
            seat_ix = {s: i for i, s in enumerate(t["seats"])}
            flat = []
            for cr, seat in sorted(t["cells"].items()):
                flat += [cr[0], cr[1], seat_ix[seat]]
            entry["tiers"][kind] = {
                "rings": [[[round(x, 5), round(y, 5)] for x, y in ring] for ring in t["rings"]],
                "seats": t["seats"],
                "cells": flat,
            }
        proto["states"][ab] = entry

    print(f"   pairs placed without a clear spot: {crowded if crowded else 'none'}")
    n = sum(len(t["cells"]) // 3 for s in proto["states"].values() for t in s["tiers"].values())
    seats = sum(len(t["seats"]) for s in proto["states"].values() for t in s["tiers"].values())
    print(f"   {seats} seats across {len(proto['states'])} states, {n} sub-cells")

    path = args.out or OUT_DIR / f"hex_mmp_cartogram{suffix}.json"
    with open(path, "w") as f:
        json.dump(proto, f)
    print(f"wrote {path}")
    vpath = args.viz_out or VIZ_HEX_DIR / f"hex_mmp_cartogram{suffix}.json"
    with open(vpath, "w") as f:
        json.dump(proto, f)
    print(f"wrote {vpath} ({round(len(open(vpath).read())/1024)} KB)")


if __name__ == "__main__":
    main()

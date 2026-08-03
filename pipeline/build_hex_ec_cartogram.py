#!/usr/bin/env python3
"""
build_hex_ec_cartogram.py
-------------------------
State-level hexagon cartograms for the presidency, on the same lattice and the same state
outlines as the House seat map. Two bases:

  --basis electoral   one hexagon per electoral vote (975). State area is scaled to
                      electoral weight, so the two senatorial electors every state gets
                      are visible in the shape rather than buried in a footnote.
  --basis population  one hexagon per 1/N of the population, at a lattice fine enough that
                      the smallest state holds --min-hexes of them. State area is
                      population, unscaled, which is what the source outlines already are.
                      This is the basis for reading a vote share off the map: the electoral
                      college is not involved, so nothing should be re-weighted for it.

Why these are separate maps rather than recolourings of the seat cartogram: the seat map
gives Wyoming 2 hexagons. Its electoral weight is 4, and 2 hexagons cannot show a
five-way vote split at all. Each basis therefore needs its own tiling.

Two simplifications against `build_hex_seat_cartogram.py`, both because a presidential
race has no districts:

  * one district per state, so there is no seed placement, no capacity-constrained blob
    growth and no seat grouping — every cell is its own elector;
  * cells are apportioned across a state's separate rings by area alone (Michigan's
    peninsulas, Hawaii's islands), the same guard the seat map applies, so an island
    cannot take electors the mainland needs.

On the electoral basis, outlines are scaled about each state's own centroid by
sqrt(electoral share / population share), which runs from 1.34x for the 4-elector states
down to 0.96x for California. The cells a state keeps then sit inside its own outline, so
clipping stays faithful. Adjacent small states can overlap after scaling; a cell is owned
by whichever state covers it most, so the tiling stays exclusive, and the report at the end
names any state whose outline crosses a neighbour's.

Inputs
  data/raw/hexmap/HexStv30/                 state outlines (population-scaled)
  data/raw/hexmap/HexDDv20/                 delegate districts, used only to place DC
  viz/src/data/houseStateMap.json           House seats per state, the 873-seat basis

Reproducibility: no randomness, all ties broken on explicit sort keys, so repeated runs
are byte-identical.

Usage
  python pipeline/build_hex_ec_cartogram.py                                  # 975 electors
  python pipeline/build_hex_ec_cartogram.py --basis population --min-hexes 10  # 4,365 tiles
"""

import argparse
import json
import math
import sys
from collections import defaultdict, deque
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from build_hex_seat_cartogram import (  # noqa: E402
    SQRT3, HEX_AREA_PER_R2, StateShape, connect_selection, fill_holes, hex_center,
    largest_component, largest_remainder, nearest_cell, neighbors, polygon_area,
    ring_area_of, rings_centroid, sample_offsets, viz_payload,
)
from hexmap_io import load_layer  # noqa: E402

BASE_DIR = Path(__file__).parent.parent
OUT_DIR = BASE_DIR / "data" / "processed"
VIZ_HEX_DIR = BASE_DIR / "viz" / "public" / "hexmap"

SENATORIAL = 2


def scale_rings(rings, factor):
    """Scale a state's rings about their own centroid, so it keeps its position."""
    cx, cy = rings_centroid(rings)
    return [[[cx + (x - cx) * factor, cy + (y - cy) * factor] for x, y in ring]
            for ring in rings]


def load_house_seats():
    """{state abbr: House seats} on the double-Wyoming apportionment — the population basis."""
    path = BASE_DIR / "viz" / "src" / "data" / "houseStateMap.json"
    hs = json.loads(path.read_text())
    return {v["stateAbbr"]: v["totalSeats"] for v in hs.values()}


def population_targets(seats, min_hexes):
    """Apportion tiles by population so the smallest state holds at least `min_hexes`.

    The total follows from the floor rather than the other way round: at 873 seats the
    smallest states hold 2, so a floor of 10 needs 10 x 873 / 2 = 4,365 tiles. Largest
    remainder from there, so every state's tile count is its population share.
    """
    total_seats = sum(seats.values())
    smallest = min(seats.values())
    n = math.ceil(min_hexes * total_seats / smallest)
    return largest_remainder(n, seats)


def lattice_R(states, total_cells):
    total_area = sum(s.area for s in states.values())
    return math.sqrt(total_area / total_cells / HEX_AREA_PER_R2)


def build(states, targets, verbose=True):
    """Pick each state's cells: the best-covered cells it owns, exactly `target` of them.

    Returns (cells, pools, R, x0, y0). `cells` maps (col, row) -> state; `pools` maps a
    state to every cell touching it, so the boundary fill can cover the outline.
    """
    R = lattice_R(states, sum(targets.values()))
    xmin = min(s.bbox[0] for s in states.values())
    ymin = min(s.bbox[1] for s in states.values())
    xmax = max(s.bbox[2] for s in states.values())
    ymax = max(s.bbox[3] for s in states.values())
    offs = sample_offsets(R)
    x0, y0 = xmin - 2 * SQRT3 * R, ymin - 3 * R
    n_cols = int((xmax - x0) / (SQRT3 * R)) + 3
    n_rows = int((ymax - y0) / (1.5 * R)) + 3

    cover = defaultdict(dict)      # (ab, ring_idx) -> {cell: sample hits}
    best = {}                      # cell -> (hits, ab)
    for row in range(n_rows):
        for col in range(n_cols):
            cx, cy = hex_center(col, row, R, x0, y0)
            pts = offs + np.array([cx, cy])
            for ab, st in states.items():
                bx0, by0, bx1, by1 = st.bbox
                if cx < bx0 - R or cx > bx1 + R or cy < by0 - R or cy > by1 + R:
                    continue
                tot = 0
                for i, path in enumerate(st.paths):
                    s = int(path.contains_points(pts).sum())
                    if s:
                        cover[(ab, i)][(col, row)] = s
                        tot += s
                if tot:
                    prev = best.get((col, row))
                    if prev is None or (tot, ab) > prev:
                        best[(col, row)] = (tot, ab)
    owner = {c: v[1] for c, v in best.items()}

    pools = defaultdict(set)
    for (ab, _i), d in cover.items():
        pools[ab] |= set(d)
    for ab, st in states.items():
        for ring in st.rings:
            for x, y in ring:
                pools[ab].add(nearest_cell(x, y, R, x0, y0))

    cells = {}
    shortfalls = []
    for ab, st in sorted(states.items()):
        target = targets[ab]
        areas = {i: ring_area_of(st.rings[i]) for i in range(len(st.rings))}
        hex_area = HEX_AREA_PER_R2 * R * R
        eligible = {i: a for i, a in areas.items()
                    if a >= 0.35 * hex_area and cover.get((ab, i))}
        if not eligible:
            eligible = {max(areas, key=lambda i: (areas[i], -i)): 1.0}
        alloc = largest_remainder(target, eligible)

        picked = set()
        for i in sorted(eligible):
            want = alloc[i]
            if want <= 0:
                continue
            pool = {c: s for c, s in cover.get((ab, i), {}).items()
                    if owner.get(c) == ab and c not in picked}
            ranked = sorted(pool, key=lambda c: (-pool[c], c))[:want]
            picked |= fill_holes(connect_selection(ranked, pool, want), pool)
        if len(picked) < target:
            rest = {c: s for (a, i), d in cover.items() if a == ab
                    for c, s in d.items() if owner.get(c) == ab and c not in picked}
            for c in sorted(rest, key=lambda c: (-rest[c], c))[:target - len(picked)]:
                picked.add(c)
        if len(picked) != target:
            shortfalls.append((ab, target, len(picked)))
        for c in picked:
            cells[c] = ab
        if verbose:
            print(f"   {ab}: target={target:4d} rings={len(st.rings)} kept={len(picked):4d}")

    if shortfalls:
        print("   WARNING shortfalls:", shortfalls)
    return cells, pools, R, x0, y0


def overlapping_pairs(states):
    """States whose scaled outlines cross a neighbour's, for the report."""
    out = []
    abbrs = sorted(states)
    for i, a in enumerate(abbrs):
        for b in abbrs[i + 1:]:
            sa, sb = states[a], states[b]
            if (sa.bbox[2] < sb.bbox[0] or sb.bbox[2] < sa.bbox[0]
                    or sa.bbox[3] < sb.bbox[1] or sb.bbox[3] < sa.bbox[1]):
                continue
            pts = np.array([p for ring in sb.rings for p in ring])
            if sa.contains(pts).any():
                out.append((a, b))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--basis", choices=["electoral", "population"], default="electoral",
                    help="one hexagon per elector, or per 1/N of the population")
    ap.add_argument("--min-hexes", type=int, default=10,
                    help="population basis only: tiles the smallest state must hold")
    ap.add_argument("--out", default=None, help="prototype JSON path")
    ap.add_argument("--viz-out", default=None,
                    help="geometry-only JSON for the app (default viz/public/hexmap/)")
    args = ap.parse_args()

    electoral = args.basis == "electoral"
    seats = load_house_seats()
    targets = ({ab: s + SENATORIAL for ab, s in seats.items()} if electoral
               else population_targets(seats, args.min_hexes))
    unit = "electors" if electoral else "tiles"
    print(f"{args.basis} basis: {sum(targets.values())} {unit} across {len(targets)} states"
          + ("" if electoral else f", smallest state holds {min(targets.values())}"))

    st_layer = load_layer("HexStv30", "HexSTv30")
    raw = {a["STATEAB"]: r for a, r in st_layer if a["STATEAB"] in targets}
    dd = {a["ABBREV"]: r for a, r in load_layer("HexDDv20")}
    if "DC" in targets and "DC" not in raw:
        raw["DC"] = dd["DC"]

    # Re-scale so outline area tracks electoral weight rather than population. Only the
    # electoral basis needs this: the source outlines are already population-scaled, which
    # is exactly what the population basis wants.
    print("\nstep 0 — outline scaling")
    if not electoral:
        scaled = raw
        print("   population basis — outlines used as they are")
    else:
        pop_area = {ab: polygon_area(r) for ab, r in raw.items()}
        total_area = sum(pop_area.values())
        total_ev = sum(targets.values())
        scaled = {}
        factors = {}
        for ab, rings in raw.items():
            want = targets[ab] / total_ev
            have = pop_area[ab] / total_area
            f = math.sqrt(want / have) if have > 0 else 1.0
            factors[ab] = f
            scaled[ab] = scale_rings(rings, f)
        biggest = sorted(factors.items(), key=lambda kv: -kv[1])[:5]
        smallest = sorted(factors.items(), key=lambda kv: kv[1])[:3]
        print(f"   grown most: {[(a, round(f, 3)) for a, f in biggest]}")
        print(f"   shrunk most: {[(a, round(f, 3)) for a, f in smallest]}")

    states = {ab: StateShape(ab, r) for ab, r in scaled.items()}
    crossings = overlapping_pairs(states)
    print(f"   outlines crossing a neighbour: {len(crossings)}"
          + (f" {crossings[:10]}" if crossings else ""))

    print("\nstep 1 — hex lattice")
    cells, pools, R, x0, y0 = build(states, targets)
    print(f"   R={R:.4f} deg  cells={len(cells)}  (target {sum(targets.values())})")

    by_state = defaultdict(set)
    for c, ab in cells.items():
        by_state[ab].add(c)
    frag = {ab: len(v) - len(largest_component(v)) for ab, v in by_state.items()}
    frag = {k: v for k, v in frag.items() if v}
    print(f"   states with detached cells: {frag if frag else 'none'}")

    # Every cell is its own elector, and the state is the only district.
    print("\nstep 2 — fill to the state outline")
    filled = {}
    for ab, pool in sorted(pools.items()):
        cores = {c for c in pool if cells.get(c) == ab}
        if not cores:
            continue
        seat_of = {c: c for c in cores}
        queue = deque(sorted(cores))
        while queue:
            c = queue.popleft()
            for nb in neighbors(*c):
                if nb in pool and nb not in seat_of:
                    seat_of[nb] = seat_of[c]
                    queue.append(nb)
        for c in sorted(pool - set(seat_of)):
            cx, cy = hex_center(c[0], c[1], R, x0, y0)
            near = min(sorted(cores), key=lambda k: (
                (hex_center(k[0], k[1], R, x0, y0)[0] - cx) ** 2
                + (hex_center(k[0], k[1], R, x0, y0)[1] - cy) ** 2))
            seat_of[c] = seat_of[near]
        filled[ab] = seat_of
    print(f"   boundary cells merged into a neighbouring elector: "
          f"{sum(len(v) for v in filled.values()) - len(cells)}")

    out = {
        "meta": {
            "R": R, "x0": x0, "y0": y0, "orientation": "pointy-top",
            "seats": sum(targets.values()), "cellsPerSeat": 1,
            "triple": False, "basis": args.basis,
            "source": "Congressional District Hexmap v3.2 by Daniel Donner for "
                      "The Downballot (https://the-db.co/maps), CC BY 4.0",
        },
        "states": {
            ab: {
                # DC's outline is a delegate hexagon, not a population-scaled shape.
                "clip": ab != "DC",
                "rings": [[[round(x, 5), round(y, 5)] for x, y in ring]
                          for ring in states[ab].rings],
                "cells": [
                    {"col": c[0], "row": c[1], "core": f"{seat[0]},{seat[1]}",
                     "district": ab, "party": None,
                     "isCore": cells.get(c) == ab}
                    for c, seat in sorted(seat_of.items())
                ],
            }
            for ab, seat_of in sorted(filled.items())
        },
    }

    name = "hex_ec_cartogram" if electoral else "hex_pop_cartogram"
    path = Path(args.out) if args.out else OUT_DIR / f"{name}.json"
    path.write_text(json.dumps(out))
    n_cells = sum(len(s["cells"]) for s in out["states"].values())
    print(f"\nwrote {path} ({n_cells} cells across {len(out['states'])} states)")

    vpath = Path(args.viz_out) if args.viz_out else VIZ_HEX_DIR / f"{name}.json"
    vpath.parent.mkdir(parents=True, exist_ok=True)
    vpath.write_text(json.dumps(viz_payload(out, R, x0, y0)))
    print(f"wrote {vpath} ({vpath.stat().st_size // 1024} KB, geometry only)")

    kept = {ab: sum(1 for c in s["cells"] if c["isCore"]) for ab, s in out["states"].items()}
    bad = {ab: (n, targets[ab]) for ab, n in kept.items() if n != targets[ab]}
    print(f"{unit} per state match target: {'yes' if not bad else f'NO {bad}'}")


if __name__ == "__main__":
    main()

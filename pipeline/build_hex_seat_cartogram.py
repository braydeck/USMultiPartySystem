#!/usr/bin/env python3
"""
build_hex_seat_cartogram.py
---------------------------
PROTOTYPE. Build a one-hexagon-per-seat cartogram of the multi-member House.

Concept borrowed from the Congressional District Hexmap by Daniel Donner for The
Downballot (https://the-db.co/maps, CC BY 4.0): states keep a recognizable outline but
are scaled so area is proportional to population, and districts are drawn as blobs of
equal-area tiles rather than real geography. Their tiling is finer than one tile per
district; here the tile IS the unit of representation — one hexagon = one seat — because
each of our districts elects 2-10 members from 10 parties, so party colour has to live
below the district level.

Inputs
  data/raw/hexmap/HexStv30/       state outlines (population-scaled) — the container
  data/raw/hexmap/HexDDv20/       delegate districts, used only to place DC
  viz/src/data/districtStvResults{,Triple}.json   districts, seatCount, elected members
  data/processed/county_to_district{,_triple}.csv county → district
  viz/public/topojson/counties-10m.json           real county positions, for seeding

Method
  1. Size a pointy-top hex lattice so the cell count over the state outlines equals the
     seat total, then keep the N cells per state with the greatest overlap with that
     state. State area is population-proportional, so this lands within ~1 cell/state.
     Seats are apportioned across a state's separate rings by area, so Michigan's
     peninsulas and Hawaii's islands each get their own share.
     Cells per ring are sized to the districts assigned to that ring, not to its area,
     because only districts sharing a ring can trade cells.
  2. Assign each ring's cells to districts by capacity-constrained nearest-seed, seeded
     at each district's real county centroid mapped into the state's distorted frame.
     Sizes are exact by construction; contiguity is then improved by size-preserving
     swaps. Sizes win when the two conflict — they are seat counts.
  3. Group cells into seats (--cells-per-seat: 1 hexagon, or 2 conjoined) and give each
     seat one elected member, dealt in F5_ORDER west→east so a district reads as a
     left-to-right ideological gradient.
  4. Merge every remaining cell that touches the state into its nearest seat. The
     renderer clips each state's cells to that state's outline, so the silhouette stays
     the real state shape instead of a castellated hex edge — this step guarantees there
     is no uncovered sliver left inside the outline for the clip to expose.

The seat hexagons in a state's interior are therefore whole hexagons, while the ones on
its border are trimmed to the state's edge. That is the same trade Donner's map makes.

District placement inside a state is approximate by construction — the state shape is
distorted, so a blob can only sit in roughly the right corner. That matches Donner's
own approach and costs little here: within-party geographic variation is ~6pp.

Reproducibility: no randomness. Ties break on explicit sort keys (cell id, district id),
so repeated runs are byte-identical.

Usage
  python pipeline/build_hex_seat_cartogram.py                    # 873 seats, 1 hex each
  python pipeline/build_hex_seat_cartogram.py --cells-per-seat 2 # conjoined dominoes
  python pipeline/build_hex_seat_cartogram.py --triple           # 1,726-seat map
"""

import argparse
import csv
import json
import math
import re
import sys
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
from matplotlib.path import Path as MplPath

sys.path.insert(0, str(Path(__file__).parent))
from hexmap_io import load_layer, county_centroids

BASE_DIR = Path(__file__).parent.parent
TOPO_PATH = BASE_DIR / "viz" / "public" / "topojson" / "counties-10m.json"
OUT_DIR = BASE_DIR / "data" / "processed"
VIZ_HEX_DIR = BASE_DIR / "viz" / "public" / "hexmap"

# Pointy-top hexagon: vertex at the top. width = sqrt(3)*R, height = 2*R.
SQRT3 = math.sqrt(3.0)
HEX_AREA_PER_R2 = 1.5 * SQRT3  # area of a regular hexagon with circumradius 1

# Must match EXPLODE in viz/src/lib/hexCartogram.ts. The app pushes every state away
# from the map centre by this factor before drawing, so a miniature's placement has to be
# searched in that space rather than in the lattice's.
EXPLODE = 1.24

# The statewide miniatures are cut on a lattice this many times finer than a seat, so a
# region can deform to fill the outline while still holding an exact share of its area.
SUB_DIV = 6

# Axial neighbour steps for a pointy-top "odd-r" offset lattice, as (dcol, drow)
# pairs for even and odd rows.
NEIGHBORS_EVEN_ROW = [(+1, 0), (0, -1), (-1, -1), (-1, 0), (-1, +1), (0, +1)]
NEIGHBORS_ODD_ROW = [(+1, 0), (+1, -1), (0, -1), (-1, 0), (0, +1), (+1, +1)]


# ── geometry helpers ─────────────────────────────────────────────────────────

def ring_area(pts):
    a = 0.0
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        a += x0 * y1 - x1 * y0
    return abs(a / 2)


def polygon_area(rings):
    return sum(ring_area(r) for r in rings)


def rings_centroid(rings):
    tot = polygon_area(rings)
    if tot == 0:
        pts = rings[0]
        return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)
    cx = cy = 0.0
    for pts in rings:
        w = ring_area(pts)
        cx += w * sum(p[0] for p in pts) / len(pts)
        cy += w * sum(p[1] for p in pts) / len(pts)
    return cx / tot, cy / tot


def hex_vertices(cx, cy, R):
    """Pointy-top hexagon vertices, starting at the top and going clockwise."""
    return [(cx + R * math.sin(math.pi / 3 * k), cy + R * math.cos(math.pi / 3 * k))
            for k in range(6)]


def hex_center(col, row, R, x0, y0):
    """Centre of odd-r offset cell (col, row). Odd rows shift right by half a width."""
    w = SQRT3 * R
    return (x0 + w * (col + 0.5 * (row & 1)), y0 + 1.5 * R * row)


def axial(col, row):
    """Odd-r offset coords -> axial (q, r), where lattice arithmetic is linear."""
    return col - (row - (row & 1)) // 2, row


def nearest_cell(x, y, R, x0, y0):
    """The lattice cell whose hexagon contains (x, y).

    Searches the neighbourhood of the approximate row/col and takes the nearest centre,
    which is exact: the Voronoi diagram of a triangular lattice is its hexagonal tiling.
    """
    row_f = (y - y0) / (1.5 * R)
    best, best_d = None, None
    for row in (int(math.floor(row_f)) - 1, int(math.floor(row_f)),
                int(math.floor(row_f)) + 1, int(math.floor(row_f)) + 2):
        col_f = (x - x0) / (SQRT3 * R) - 0.5 * (row & 1)
        for col in (int(math.floor(col_f)), int(math.floor(col_f)) + 1):
            cx, cy = hex_center(col, row, R, x0, y0)
            d = (cx - x) ** 2 + (cy - y) ** 2
            if best_d is None or d < best_d:
                best, best_d = (col, row), d
    return best


def sample_offsets(R, rings_of_circles=2, dense=False):
    """Points inside a unit hexagon, used to estimate what fraction of a cell is
    inside a state polygon. Centre plus two rings — enough to rank edge cells.

    `dense` adds two more rings and more points per ring, for the miniatures, where the
    fraction is used as an area rather than only to rank one cell against another.
    """
    pts = [(0.0, 0.0)]
    if dense:
        for frac in (0.25, 0.45, 0.62, 0.78, 0.92):
            n = 12
            for k in range(n):
                ang = 2 * math.pi * k / n + (math.pi / n if int(frac * 100) % 2 else 0.0)
                pts.append((frac * R * math.sin(ang), frac * R * math.cos(ang)))
        return np.array(pts)
    for frac in (0.45, 0.8):
        for k in range(6):
            ang = math.pi / 3 * k + (math.pi / 6 if frac == 0.8 else 0.0)
            pts.append((frac * R * math.sin(ang), frac * R * math.cos(ang)))
    return np.array(pts)


class StateShape:
    """A state's cartogram outline: matplotlib Paths for containment tests."""

    def __init__(self, ab, rings):
        self.ab = ab
        self.rings = rings
        self.paths = [MplPath(np.array(r)) for r in rings]
        self.area = polygon_area(rings)
        xs = [p[0] for r in rings for p in r]
        ys = [p[1] for r in rings for p in r]
        self.bbox = (min(xs), min(ys), max(xs), max(ys))

    def contains(self, pts):
        """Boolean mask: which of pts fall inside any ring."""
        inside = np.zeros(len(pts), dtype=bool)
        for p in self.paths:
            inside |= p.contains_points(pts)
        return inside


# ── inputs ───────────────────────────────────────────────────────────────────

def load_districts(triple):
    """Return {district_id: {state, seats, elected}} and {state_fips: total_seats}."""
    name = "districtStvResultsTriple" if triple else "districtStvResults"
    raw = json.loads((BASE_DIR / "viz" / "src" / "data" / f"{name}.json").read_text())
    districts, per_state = {}, {}
    for state, rows in raw.items():
        per_state[state] = sum(r["seatCount"] for r in rows)
        for r in rows:
            districts[r["districtId"]] = {
                "state": state,
                "seats": r["seatCount"],
                "elected": list(r["elected"]),
                "tier": r.get("densityTier", ""),
            }
    return districts, per_state


def load_reserve_districts(triple):
    """Districts, per-state totals and the statewide count for the reserve map.

    The reserve map is its own redraw — 128 districts against the base map's 149 — and
    about a fifth of each state's seats are elected statewide instead of in a district.
    `per_state` carries district seats only. The statewide seats are drawn as a border
    around the state rather than as cells inside it, and the state's outline is shrunk to
    match its district seats, so the hex size is unchanged and the state plus its border
    still covers the same area as the base map's state.
    """
    tree = "canonical_triple_reserve" if triple else "canonical_reserve"
    path = BASE_DIR / "data" / "outputs" / tree / "district_apportionment.csv"
    districts, per_state, reserve = {}, defaultdict(int), {}
    with open(path) as f:
        for row in csv.DictReader(f):
            fips = row["state_fips"].zfill(2)
            districts[row["district_id"]] = {
                "state": fips,
                "seats": int(row["seat_count"]),
                "elected": [],
                "tier": row["density_tier"],
            }
            per_state[fips] += int(row["seat_count"])
            reserve[fips] = int(row["reserve"])
    return districts, dict(per_state), reserve


SPLIT_OVERRIDES = Path(__file__).parent / "county_split_overrides.csv"


def load_split_overrides():
    """(county, district) → share of that county, from the cd119 split overrides.

    A county listed here is divided between districts by real 119th-Congress district,
    so it seeds every district it feeds rather than only the one the whole-county file
    names. Maricopa is the case this exists for: it alone backs both AZ 04-01 and 04-03,
    and without it 04-03 has no geography at all and falls back to the state centre.
    """
    if not SPLIT_OVERRIDES.exists():
        return {}
    per_county = defaultdict(list)
    with open(SPLIT_OVERRIDES) as f:
        for row in csv.DictReader(f):
            per_county[row["county_fips5"]].append(row["district_id"])
    shares = {}
    for fips, dids in per_county.items():
        for did in set(dids):
            shares[(fips, did)] = dids.count(did) / len(dids)
    return shares


def district_real_centroids(suffix, districts):
    """Population-free centroid per district in real lon/lat, weighted by county share.

    Whole counties count once; a county split across districts by cd119 contributes to
    each in proportion to how many of its cd119 pieces that district takes.
    """
    path = OUT_DIR / f"county_to_district{suffix}.csv"
    cents = county_centroids(TOPO_PATH)
    overrides = load_split_overrides()
    split_counties = {fips for fips, _ in overrides}

    acc = defaultdict(list)          # district -> [(lon, lat, weight)]
    missing = 0
    with open(path) as f:
        for row in csv.DictReader(f):
            fips = row["county_fips5"]
            c = cents.get(fips)
            if c is None:
                missing += 1
                continue
            if fips in split_counties:
                continue             # handled from the override table below
            acc[row["district_id"]].append((c[0], c[1], 1.0))
    for (fips, did), share in sorted(overrides.items()):
        c = cents.get(fips)
        if c is not None:
            acc[did].append((c[0], c[1], share))

    out = {}
    for did in districts:
        pts = acc.get(did)
        if pts:
            wsum = sum(p[2] for p in pts)
            out[did] = (sum(p[0] * p[2] for p in pts) / wsum,
                        sum(p[1] * p[2] for p in pts) / wsum)
    return out, missing, {d: len(acc.get(d, [])) for d in districts}


def spread_coincident(seeds, R):
    """Nudge apart districts that share a seed point.

    Two districts carved out of the same county (AZ 04-01 and 04-03 both come from
    Maricopa) land on the identical centroid, which leaves the growth with nothing to
    tell them apart. Spacing them on a small ring keeps both in the right place while
    giving each its own side to grow from.
    """
    groups = defaultdict(list)
    for did, (x, y) in seeds.items():
        groups[(round(x, 4), round(y, 4))].append(did)
    out = dict(seeds)
    for (x, y), dids in sorted(groups.items()):
        if len(dids) < 2:
            continue
        for i, did in enumerate(sorted(dids)):
            ang = 2 * math.pi * i / len(dids)
            out[did] = (x + 0.7 * R * math.cos(ang), y + 0.7 * R * math.sin(ang))
    return out


def real_state_bboxes(suffix):
    """Real lon/lat bbox per state, from the counties assigned to it."""
    cents = county_centroids(TOPO_PATH)
    acc = defaultdict(list)
    with open(OUT_DIR / f"county_to_district{suffix}.csv") as f:
        for row in csv.DictReader(f):
            c = cents.get(row["county_fips5"])
            if c:
                acc[row["state_fips"]].append(c)
    return {s: (min(p[0] for p in v), min(p[1] for p in v),
                max(p[0] for p in v), max(p[1] for p in v))
            for s, v in acc.items()}


# ── step 1: lattice ──────────────────────────────────────────────────────────

def largest_remainder(total, weights):
    """Apportion `total` whole units across weights (Hamilton / largest remainder)."""
    keys = sorted(weights)
    w_sum = sum(weights.values())
    if w_sum <= 0:
        return {k: 0 for k in keys}
    quotas = {k: total * weights[k] / w_sum for k in keys}
    alloc = {k: int(quotas[k]) for k in keys}
    left = total - sum(alloc.values())
    for k in sorted(keys, key=lambda k: (-(quotas[k] - alloc[k]), k))[:left]:
        alloc[k] += 1
    return alloc


def connect_selection(chosen, pool, want):
    """Swap detached cells for cells touching the main body, keeping the count fixed.

    Small or thin states can otherwise pick a cell separated from the rest by a lattice
    gap, which renders as a stray hexagon floating beside the state.
    """
    chosen = set(chosen)
    for _ in range(len(chosen)):
        if len(chosen) < 2:
            break
        main = largest_component(chosen)
        stray = chosen - main
        if not stray:
            break
        # Best unused candidate that touches the main body.
        options = [(s, c) for c, s in pool.items()
                   if c not in chosen and any(nb in main for nb in neighbors(*c))]
        if not options:
            break
        options.sort(key=lambda t: (-t[0], t[1]))
        drop = min(stray, key=lambda c: (pool.get(c, 0), c))
        add = options[0][1]
        if pool.get(add, 0) <= 0:
            break
        chosen.discard(drop)
        chosen.add(add)
    return chosen


def lattice_R(states, total_cells):
    """Hex circumradius that fits exactly total_cells cells across the state outlines."""
    total_area = sum(s.area for s in states.values())
    return math.sqrt(total_area / total_cells / HEX_AREA_PER_R2)


def assign_districts_to_rings(st, dists, seeds, R):
    """Split a state's districts across its separate rings, then size each ring to fit.

    A ring's cell count has to equal the sum of the district sizes assigned to it, not
    its area share, or the districts stranded on it can never reach their target: only
    districts in the same ring can trade cells, since growth follows adjacency and rings
    do not touch. Michigan is the case that forces this — an area-proportional split gave
    the Upper Peninsula 16 cells, but its district sizes are 14/14/14/12 and no subset
    sums to 16, so its lone district could never balance.

    Returns (ring_of_district, ring_targets).
    """
    hex_area = HEX_AREA_PER_R2 * R * R
    areas = {i: ring_area(st.rings[i]) for i in range(len(st.rings))}
    eligible = {i: a for i, a in areas.items() if a >= 0.35 * hex_area}
    if not eligible:
        eligible = {max(areas, key=lambda i: (areas[i], -i)): 1.0}

    total_cells = sum(d["size"] for d in dists.values())
    quota = largest_remainder(total_cells, eligible)
    centroids = {i: rings_centroid([st.rings[i]]) for i in eligible}

    remaining = dict(quota)
    ring_of = {}
    # Largest districts first: they are the hardest to place once quotas fill up.
    for did in sorted(dists, key=lambda d: (-dists[d]["size"], d)):
        size = dists[did]["size"]
        sx, sy = seeds[did]

        def dist_to(i):
            cx, cy = centroids[i]
            return (cx - sx) ** 2 + (cy - sy) ** 2, i

        room = [i for i in eligible if remaining[i] >= size]
        pick = (min(room, key=dist_to) if room
                else max(sorted(eligible), key=lambda i: (remaining[i], -i)))
        ring_of[did] = pick
        remaining[pick] -= size

    ring_targets = defaultdict(int)
    for did, i in ring_of.items():
        ring_targets[i] += dists[did]["size"]
    return ring_of, dict(ring_targets)


def fill_holes(chosen, pool):
    """Trade interior gaps for the least-covered edge cell, keeping the count fixed.

    Ranking cells purely by how much of them falls inside the state can drop an interior
    cell in favour of a border one, which leaves a visible hole in the middle of the
    state once the hexagons are drawn unclipped. Swapping the hole for the most-outside
    cell we hold fixes it without changing how many cells the state has.
    """
    chosen = set(chosen)
    for _ in range(len(chosen)):
        # A gap ringed on five of six sides still reads as a hole once drawn.
        holes = [c for c in pool if c not in chosen
                 and sum(1 for nb in neighbors(*c) if nb in chosen) >= 5]
        if not holes:
            break
        hole = min(holes, key=lambda c: (-pool.get(c, 0), c))
        # Drop the cell we hold with the least of itself inside the state, never one
        # whose removal would open a fresh hole next to the one being filled.
        drop = [c for c in chosen if c not in neighbors(*hole)]
        if not drop:
            break
        # Give up the cell with least of itself inside the state, and only if it is on
        # the edge of the selection — dropping an interior cell would just move the hole.
        edge = [c for c in drop
                if any(nb not in chosen for nb in neighbors(*c))] or drop
        out = min(edge, key=lambda c: (pool.get(c, 0), c))
        if out == hole:
            break
        chosen.discard(out)
        chosen.add(hole)
    return chosen


def build_lattice(states, targets, ring_targets=None, verbose=True):
    """Choose R so in-state cell count == seat total, then pick the best cells.

    Cells are claimed by whichever state covers them most, so no cell is double-used.
    Within a state, cells are apportioned across the state's separate rings (Michigan's
    peninsulas, Hawaii's islands) so islands cannot steal seats from the mainland. When
    ring_targets is given — {(state, ring_index): cells} from assign_districts_to_rings —
    it overrides the area-proportional split so each ring holds exactly the districts
    assigned to it.

    Returns (cores, pools, picked_by_ring, R, x0, y0): `cores` maps (col, row) -> state
    abbreviation; `pools` maps a state to every cell touching it, including the boundary
    cells merged into a neighbouring seat so clipping leaves the silhouette intact.
    """
    total_seats = sum(targets.values())
    R = lattice_R(states, total_seats)

    xmin = min(s.bbox[0] for s in states.values())
    ymin = min(s.bbox[1] for s in states.values())
    xmax = max(s.bbox[2] for s in states.values())
    ymax = max(s.bbox[3] for s in states.values())

    offs = sample_offsets(R)
    x0, y0 = xmin - 2 * SQRT3 * R, ymin - 3 * R
    n_cols = int((xmax - x0) / (SQRT3 * R)) + 3
    n_rows = int((ymax - y0) / (1.5 * R)) + 3

    # Coverage of every cell against every ring it touches.
    cover = defaultdict(dict)          # (ab, ring_idx) -> {cell: score}
    best_state = {}                    # cell -> (score, ab)
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
                    prev = best_state.get((col, row))
                    if prev is None or (tot, ab) > prev:
                        best_state[(col, row)] = (tot, ab)

    owner = {c: v[1] for c, v in best_state.items()}

    # Every cell that touches a state, so the union of cells covers the state
    # completely and clipping to the outline leaves no uncovered sliver. Sampling
    # alone misses cells the border only grazes, so also take the cell nearest each
    # outline vertex — the Voronoi cell of a triangular lattice IS its hexagon, so
    # the nearest centre is the containing hexagon.
    pools = defaultdict(set)
    for (ab, _i), d in cover.items():
        pools[ab] |= set(d)
    for ab, st in states.items():
        for ring in st.rings:
            for x, y in ring:
                pools[ab].add(nearest_cell(x, y, R, x0, y0))

    cells = {}
    picked_by_ring = {}
    shortfalls = []
    for ab, st in sorted(states.items()):
        target = targets[ab]
        areas = {i: ring_area_of(st.rings[i]) for i in range(len(st.rings))}
        if ring_targets is not None:
            alloc = {i: n for i, n in
                     ((j, ring_targets.get((ab, j), 0)) for j in areas) if n}
            eligible = dict(alloc)
        else:
            # A ring too small to hold a whole cell should not be handed a seat.
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
            chosen = fill_holes(connect_selection(ranked, pool, want), pool)
            picked_by_ring[(ab, i)] = chosen
            picked |= chosen
        # Any shortfall (ring quota larger than the cells available) falls back to the
        # state's remaining unclaimed cells.
        if len(picked) < target:
            rest = {c: s for (a, i), d in cover.items() if a == ab
                    for c, s in d.items() if owner.get(c) == ab and c not in picked}
            biggest = max(alloc, key=lambda i: (alloc[i], -i)) if alloc else 0
            for c in sorted(rest, key=lambda c: (-rest[c], c))[:target - len(picked)]:
                picked.add(c)
                picked_by_ring.setdefault((ab, biggest), set()).add(c)
        if len(picked) != target:
            shortfalls.append((ab, target, len(picked)))
        for c in picked:
            cells[c] = ab
        if verbose:
            print(f"   {ab}: target={target:4d} rings={len(st.rings)} "
                  f"alloc={ {i: alloc[i] for i in sorted(alloc) if alloc[i]} } "
                  f"kept={len(picked):4d}")

    if shortfalls:
        print("   WARNING shortfalls:", shortfalls)
    return cells, pools, picked_by_ring, R, x0, y0


def ring_area_of(pts):
    return ring_area(pts)


def neighbors(col, row):
    steps = NEIGHBORS_ODD_ROW if (row & 1) else NEIGHBORS_EVEN_ROW
    return [(col + dc, row + dr) for dc, dr in steps]


def n_components(cell_set):
    """Number of adjacency-connected pieces in cell_set."""
    seen, n = set(), 0
    for start in sorted(cell_set):
        if start in seen:
            continue
        n += 1
        stack = [start]
        seen.add(start)
        while stack:
            for nb in neighbors(*stack.pop()):
                if nb in cell_set and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        # the inner loop above already marked the whole component
    return n


def components(cell_set):
    """All adjacency-connected pieces of cell_set, largest first."""
    seen, out = set(), []
    for start in sorted(cell_set):
        if start in seen:
            continue
        comp, stack = set(), [start]
        seen.add(start)
        while stack:
            c = stack.pop()
            comp.add(c)
            for nb in neighbors(*c):
                if nb in cell_set and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        out.append(comp)
    return sorted(out, key=lambda s: (-len(s), sorted(s)[0]))


def largest_component(cell_set):
    """Return the biggest adjacency-connected subset of cell_set."""
    seen, best = set(), set()
    for start in sorted(cell_set):
        if start in seen:
            continue
        comp, stack = set(), [start]
        seen.add(start)
        while stack:
            c = stack.pop()
            comp.add(c)
            for nb in neighbors(*c):
                if nb in cell_set and nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        if len(comp) > len(best):
            best = comp
    return best


# ── step 2: districts ────────────────────────────────────────────────────────

def shrink_rings(rings, k):
    """Scale a state's outline about its own centroid by k."""
    cx, cy = rings_centroid(rings)
    return [[(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in ring] for ring in rings]


def _arc_table(ring):
    """Closed polyline plus a cumulative arc-length table."""
    pts = list(ring)
    if pts[0] != pts[-1]:
        pts.append(pts[0])
    segs, total = [], 0.0
    for p, q in zip(pts, pts[1:]):
        d = math.hypot(q[0] - p[0], q[1] - p[1])
        if d > 0:
            segs.append((total, p, q, d))
            total += d
    return segs, total


def _at(segs, total, s):
    """Point and unit tangent at arc length s along the closed polyline."""
    s %= total
    for s0, p, q, d in segs:
        if s <= s0 + d:
            t = (s - s0) / d
            return ((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t),
                    ((q[0] - p[0]) / d, (q[1] - p[1]) / d))
    s0, p, q, d = segs[-1]
    return (q, ((q[0] - p[0]) / d, (q[1] - p[1]) / d))


def _walk(segs, total, s0, s1, step):
    """Points from arc s0 to s1, including the polyline's own vertices between them."""
    out = [_at(segs, total, s0)[0]]
    n = max(2, int(abs(s1 - s0) / step) + 1)
    for i in range(1, n):
        out.append(_at(segs, total, s0 + (s1 - s0) * i / n)[0])
    out.append(_at(segs, total, s1)[0])
    return out


def _hull(pts):
    """Convex hull, counter-clockwise (Andrew's monotone chain)."""
    pts = sorted(set((round(x, 9), round(y, 9)) for x, y in pts))
    if len(pts) < 3:
        return list(pts)

    def half(seq):
        out = []
        for p in seq:
            while len(out) >= 2:
                (ax, ay), (bx, by) = out[-2], out[-1]
                if (bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax) <= 0:
                    out.pop()
                else:
                    break
            out.append(p)
        return out

    return half(pts)[:-1] + half(pts[::-1])[:-1]


def mini_state(rings, count, R, x0, y0, at):
    """A miniature of the state holding `count` hexagons at full size.

    Statewide seats belong to no district and sit nowhere inside the state, so they get a
    small copy of the state of their own, parked beside it. The copy is scaled so its
    area holds exactly `count` cells at the same circumradius as every other seat on the
    map — one hexagon is still one seat, here as everywhere else — which for a fifth of a
    delegation comes to a little under half the state's width.

    Returns (rings, cells) with the copy already centred on `at`.
    """
    area = polygon_area(rings)
    k = math.sqrt(count * HEX_AREA_PER_R2 * R * R / area) if area > 0 else 1.0
    cx, cy = rings_centroid(rings)
    placed = [[(at[0] + (x - cx) * k, at[1] + (y - cy) * k) for x, y in ring]
              for ring in rings]

    # Equal area per seat, by construction. The miniature is cut into `count` regions of
    # the same area rather than tiled with whole hexagons: the outline was scaled to hold
    # exactly `count` hexagons' worth of area, but hexagons cannot tile an arbitrary
    # shape, and sharing the leftover fringe out by nearest seat gave two-seat Louisiana
    # three quarters one party and a quarter the other. Regions are grown on a lattice
    # four times finer than a seat, so each one holds the same number of sub-cells and
    # deforms to fill the outline the way a district does inside a state.
    shape = StateShape("mini", placed)
    sub = R / SUB_DIV
    x0m, y0m, x1m, y1m = shape.bbox
    col0 = int(math.floor((x0m - x0) / (SQRT3 * sub))) - 1
    col1 = int(math.ceil((x1m - x0) / (SQRT3 * sub))) + 1
    row0 = int(math.floor((y0m - y0) / (1.5 * sub))) - 1
    row1 = int(math.ceil((y1m - y0) / (1.5 * sub))) + 1

    cells, pos = [], {}
    grid = [(col, row) for row in range(row0, row1 + 1) for col in range(col0, col1 + 1)]
    pts = np.array([hex_center(c, r, sub, x0, y0) for c, r in grid])
    keep = shape.contains(pts)
    for (cr, p, ok) in zip(grid, pts, keep):
        if ok:
            cells.append(cr)
            pos[cr] = (float(p[0]), float(p[1]))
    if len(cells) < count:
        return placed, []

    # Seeds spread across the shape, ordered west to east so the app's F5 fill reads left
    # to right across the miniature the way it does across a district.
    xs = sorted(cells, key=lambda c: (pos[c][0], pos[c][1]))
    seeds = [pos[xs[min(len(xs) - 1, int((i + 0.5) * len(xs) / count))]] for i in range(count)]

    quota = [len(cells) // count + (1 if i < len(cells) % count else 0) for i in range(count)]
    for _ in range(6):
        pairs = []
        for c in cells:
            px, py = pos[c]
            for i, (sx, sy) in enumerate(seeds):
                pairs.append(((px - sx) ** 2 + (py - sy) ** 2, c, i))
        pairs.sort()
        left = list(quota)
        owner = {}
        for _, c, i in pairs:
            if c in owner or left[i] <= 0:
                continue
            owner[c] = i
            left[i] -= 1
        for c in cells:
            if c not in owner:
                i = max(range(count), key=lambda j: left[j])
                owner[c] = i
                left[i] -= 1
        moved = 0.0
        for i in range(count):
            mine = [pos[c] for c, o in owner.items() if o == i]
            if not mine:
                continue
            nx = sum(q[0] for q in mine) / len(mine)
            ny = sum(q[1] for q in mine) / len(mine)
            moved = max(moved, math.hypot(nx - seeds[i][0], ny - seeds[i][1]))
            seeds[i] = (nx, ny)
        if moved < 0.02 * sub:
            break
    # Grow from the settled seeds so each seat is one piece, not a scatter.
    owner = partition_equal(cells, pos, list(range(count)), seeds)

    order = sorted(range(count), key=lambda i: (seeds[i][0], -seeds[i][1]))
    rank = {i: k for k, i in enumerate(order)}
    flat = []
    for c in sorted(cells):
        flat += [c[0], c[1], rank[owner[c]]]
    return placed, flat


# Directions hand-set where the geometric search picks a spot that reads worse than an
# obvious neighbouring gap. Degrees, 0 = east, counter-clockwise, tried before the search.
MINI_PREFERRED = {
    "MI": (0,),          # straight east, into the lake
    "MN": (225,),        # into the notch south-west of the state
    "FL": (225,),        # tucked into the curve of the peninsula
    "NY": (180, 135),    # west, else north-west
}


def _poly_parts(rings):
    pts = np.array([q for ring in rings for q in ring], dtype=float)
    segs = np.array([(u, v) for ring in rings
                     for u, v in zip(ring, list(ring[1:]) + [ring[0]])], dtype=float)
    path = MplPath(np.array(list(rings[0]) + [rings[0][0]]))
    bbox = (pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max())
    return {"pts": pts, "segs": segs, "path": path, "bbox": bbox}


def _pt_seg_dist(pts, segs):
    """Smallest distance from any point to any segment."""
    a = segs[:, 0, :]
    b = segs[:, 1, :]
    ab = b - a
    denom = (ab * ab).sum(1)
    denom[denom == 0] = 1e-12
    ap = pts[:, None, :] - a[None, :, :]
    t = np.clip((ap * ab[None, :, :]).sum(2) / denom[None, :], 0.0, 1.0)
    closest = a[None, :, :] + t[:, :, None] * ab[None, :, :]
    return float(np.sqrt(((pts[:, None, :] - closest) ** 2).sum(2)).min())


def _bbox_gap(x, y):
    """Distance between two bounding boxes; 0 if they overlap. Cheap rejection test."""
    dx = max(x["bbox"][0] - y["bbox"][2], y["bbox"][0] - x["bbox"][2], 0.0)
    dy = max(x["bbox"][1] - y["bbox"][3], y["bbox"][1] - x["bbox"][3], 0.0)
    return math.hypot(dx, dy)


def _gap_between(x, y):
    """Distance between two polygons; 0 if they overlap."""
    if x["path"].contains_points(y["pts"]).any() or y["path"].contains_points(x["pts"]).any():
        return 0.0
    return min(_pt_seg_dist(x["pts"], y["segs"]), _pt_seg_dist(y["pts"], x["segs"]))


def _clear(cand_rings, blockers, min_gap):
    """True if the candidate keeps at least `min_gap` from every other shape.

    Bare non-overlap is not enough: New York's copy cleared Connecticut by a third of a
    hex radius and read as touching it once both outlines were stroked.
    """
    cand = _poly_parts(cand_rings)
    for b in blockers:
        if _bbox_gap(cand, b) < min_gap and _gap_between(cand, b) < min_gap:
            return False
    return True


def place_mini(ab, rings, count, R, away_from, blockers, min_gap):
    """Find a spot for a state's miniature: as close as it can sit and still stay clear.

    It wants to sit straight out from the map centre, which keeps the copies in the
    margin rather than in the middle of the country, and a handful of states name their
    own direction in MINI_PREFERRED where an obvious gap beats what the search finds.
    The distance is scanned outward from near-contact rather than derived from the
    state's reach along the direction, because the reach of a shape as long as California
    overshoots by most of the state and parked its copy four hex radii away.
    """
    cx, cy = rings_centroid(rings)
    area = polygon_area(rings)
    k = math.sqrt(count * HEX_AREA_PER_R2 * R * R / area) if area > 0 else 1.0
    base = math.degrees(math.atan2(cy - away_from[1], cx - away_from[0]))
    if math.hypot(cx - away_from[0], cy - away_from[1]) < 1e-9:
        base = 90.0
    pts = [q for ring in rings for q in ring]

    def shape_at(at):
        return [[(at[0] + (x - cx) * k, at[1] + (y - cy) * k) for x, y in ring]
                for ring in rings]

    def reach(ang):
        ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        far = max((q[0] - cx) * ux + (q[1] - cy) * uy for q in pts)
        near = -min((q[0] - cx) * ux + (q[1] - cy) * uy for q in pts)
        return far + near * k

    def at_dist(ang, d):
        return (cx + math.cos(math.radians(ang)) * d, cy + math.sin(math.radians(ang)) * d)

    def scan(ang):
        """Closest clear distance along `ang`, or None. Coarse pass, then refine."""
        span = reach(ang)
        lo, hi = 0.3 * span, span + 6 * R
        coarse = 0.5 * R
        found = None
        d = lo
        while d <= hi:
            if _clear(shape_at(at_dist(ang, d)), blockers, min_gap):
                found = d
                break
            d += coarse
        if found is None:
            return None
        back = found - coarse
        while back > lo and _clear(shape_at(at_dist(ang, back)), blockers, min_gap):
            found, back = back, back - coarse
        step = 0.12 * R
        d = found - coarse + step
        while d < found:
            if _clear(shape_at(at_dist(ang, d)), blockers, min_gap):
                found = d
                break
            d += step
        return found, at_dist(ang, found)

    for ang in MINI_PREFERRED.get(ab, ()):
        got = scan(ang)
        if got:
            return got[1]

    best = None
    for turn in (0, 20, -20, 40, -40, 60, -60, 80, -80, 100, -100,
                 120, -120, 140, -140, 160, -160, 180):
        got = scan(base + turn)
        if got and (best is None or (got[0], abs(turn)) < best[0]):
            best = ((got[0], abs(turn)), got[1])
    if best:
        return best[1]
    span = reach(base)
    return (cx + math.cos(math.radians(base)) * (span + 6 * R),
            cy + math.sin(math.radians(base)) * (span + 6 * R))


def outward_sign(rings):
    """+1 if (-dy, dx) points out of the polygon, -1 if it points in."""
    ring = max(rings, key=ring_area)
    a = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        a += x0 * y1 - x1 * y0
    return 1.0 if a < 0 else -1.0


def _components(cellset):
    """Adjacency-connected pieces of a cell set, largest first."""
    left = set(cellset)
    out = []
    while left:
        start = min(left)
        seen = {start}
        queue = deque([start])
        left.discard(start)
        while queue:
            c = queue.popleft()
            for nb in neighbors(*c):
                if nb in left:
                    left.discard(nb)
                    seen.add(nb)
                    queue.append(nb)
        out.append(seen)
    out.sort(key=len, reverse=True)
    return out


def partition_equal(group, pos, seats, seeds):
    """Assign every cell in `group` to one of `seats`, contiguously and evenly.

    Seats are shared out between the group's connected pieces in proportion to their
    size, then grown inside each piece. Growing across the whole group at once left
    single cells of one seat stranded inside another's blob, because a state broken up by
    water — Alaska's islands, Virginia's Eastern Shore, the Florida keys — cannot be
    covered by contiguous regions of arbitrary size. A piece too small to hold a seat
    joins whichever seat is nearest, which is the one disconnection there is no way
    around.

    Returns {cell: index into seats}.
    """
    comps = _components(group)
    n = len(seats)
    if len(comps) == 1:
        quota = [len(group) // n + (1 if i < len(group) % n else 0) for i in range(n)]
        return grow_equal_regions(set(group), pos, seeds, quota)

    # How many seats each piece can hold, by size.
    share = {i: len(c) * n / len(group) for i, c in enumerate(comps)}
    alloc = {i: int(share[i]) for i in share}
    spare = n - sum(alloc.values())
    for i in sorted(share, key=lambda k: (-(share[k] - alloc[k]), k))[:spare]:
        alloc[i] += 1

    def centre(cells):
        pts = [pos[c] for c in cells]
        return (sum(q[0] for q in pts) / len(pts), sum(q[1] for q in pts) / len(pts))

    # Hand each piece the seats whose seeds sit nearest it.
    free = set(range(n))
    picked = {}
    for i in sorted(alloc, key=lambda k: -alloc[k]):
        if alloc[i] == 0:
            continue
        cx, cy = centre(comps[i])
        take = sorted(free, key=lambda j: ((seeds[j][0] - cx) ** 2 + (seeds[j][1] - cy) ** 2, j))
        picked[i] = take[:alloc[i]]
        free -= set(picked[i])

    owner = {}
    for i, mine in picked.items():
        cells = comps[i]
        q = [len(cells) // len(mine) + (1 if k < len(cells) % len(mine) else 0)
             for k in range(len(mine))]
        got = grow_equal_regions(set(cells), pos, [seeds[j] for j in mine], q)
        for c, k in got.items():
            owner[c] = mine[k]

    # Pieces too small for a seat of their own.
    for i, cells in enumerate(comps):
        if i in picked:
            continue
        cx, cy = centre(cells)
        j = min(range(n), key=lambda k: ((seeds[k][0] - cx) ** 2 + (seeds[k][1] - cy) ** 2, k))
        for c in cells:
            owner[c] = j
    return owner


def grow_equal_regions(cellset, pos, seeds, quota):
    """One contiguous region per seed, each of exactly `quota[i]` cells.

    Assigning cells to their nearest seed under a capacity cap gets the areas right but
    not the shapes: once a seat fills up, later cells fall to whichever seat still has
    room, which stranded single cells of one party several cells inside another party's
    blob. Growing each region outward from its seed instead keeps it in one piece by
    construction, and feeding whichever region is furthest below its quota keeps the
    areas equal. Seeds are expected to be settled centroids, so the regions still land
    where the seats are.
    """
    n = len(seeds)
    owner, got = {}, [0] * n
    frontier = [set() for _ in range(n)]

    def near(i, c):
        return (pos[c][0] - seeds[i][0]) ** 2 + (pos[c][1] - seeds[i][1]) ** 2

    for i in sorted(range(n), key=lambda j: (-quota[j], j)):
        free = [c for c in cellset if c not in owner]
        if not free:
            break
        c0 = min(free, key=lambda c: (near(i, c), c))
        owner[c0] = i
        got[i] = 1
        frontier[i] = {nb for nb in neighbors(*c0) if nb in cellset and nb not in owner}

    left = set(cellset) - set(owner)

    def claim(i, c):
        owner[c] = i
        got[i] += 1
        left.discard(c)
        frontier[i] |= {nb for nb in neighbors(*c) if nb in cellset and nb not in owner}

    while left:
        # First choice: the region furthest below its quota that can reach a free cell.
        order = sorted(range(n), key=lambda j: (got[j] / max(1, quota[j]), got[j], j))
        took = False
        for i in order:
            if got[i] >= quota[i]:
                continue
            opts = [c for c in frontier[i] if c in left]
            if not opts:
                frontier[i] = {c for c in frontier[i] if c in left}
                continue
            claim(i, min(opts, key=lambda c: (near(i, c), c)))
            took = True
            break
        if took:
            continue
        # Every region that still wants cells is walled in. Let a region already at its
        # quota take the cell rather than leave it stranded: a seat one cell over its
        # share is invisible, a seat with a detached fragment several cells away is not.
        for i in order:
            opts = [c for c in frontier[i] if c in left]
            if not opts:
                frontier[i] = {c for c in frontier[i] if c in left}
                continue
            claim(i, min(opts, key=lambda c: (near(i, c), c)))
            took = True
            break
        if took:
            continue
        # Nothing touches anything — the piece really is disconnected. Nearest region.
        c = min(left)
        claim(min(range(n), key=lambda j: (near(j, c), j)), c)
    return owner


def grow_districts(state_cells, dists, seeds, R, x0, y0, max_swaps=4000,
                   lloyd_passes=6):
    """Partition a ring's cells into district blobs of exactly the right size.

    Capacity-respecting growth: at each step the proportionally most under-filled
    district claims its nearest unclaimed neighbour, so no district can be starved and
    every one lands on its exact target. If a district's frontier is walled in before it
    is full it jumps to the nearest unclaimed cell instead — sizes are the hard
    constraint (they are seat counts) and contiguity is cosmetic.

    Those jumps are then unpicked by swapping cells between districts, which keeps every
    size fixed while reducing the number of disconnected pieces.
    """
    centers = {c: hex_center(c[0], c[1], R, x0, y0) for c in state_cells}
    order = sorted(dists, key=lambda d: (-dists[d]["size"], d))
    target = {d: dists[d]["size"] for d in dists}

    def d2(cell, did):
        sx, sy = seeds[did]
        return (centers[cell][0] - sx) ** 2 + (centers[cell][1] - sy) ** 2

    # Capacity-constrained assignment, then a few Lloyd passes. Walking every
    # (cell, district) pair in order of distance and taking it if the cell is free and
    # the district has room makes sizes exact by construction — a district cannot be
    # starved the way a plain nearest-seed split starves one whose seed sits beside
    # another's. Re-centring on the region actually won and reassigning then compacts
    # the blobs, which is what keeps them contiguous as the lattice gets finer; without
    # it, cells that lost every nearby district land far from home as islands.
    def capacity_assign(refs):
        members = {d: set() for d in dists}
        assign = {}
        pairs = sorted(((ref_d2(c, d, refs), d, c) for c in state_cells for d in order),
                       key=lambda t: (t[0], t[1], t[2]))
        for _, did, cell in pairs:
            if cell in assign or len(members[did]) >= target[did]:
                continue
            members[did].add(cell)
            assign[cell] = did
        for cell in sorted(set(state_cells) - set(assign)):
            did = min((d for d in order if len(members[d]) < target[d]),
                      key=lambda d: (ref_d2(cell, d, refs), d))
            members[did].add(cell)
            assign[cell] = did
        return members, assign

    def ref_d2(cell, did, refs):
        rx, ry = refs[did]
        return (centers[cell][0] - rx) ** 2 + (centers[cell][1] - ry) ** 2

    refs = dict(seeds)
    members, assign = capacity_assign(refs)
    for _ in range(lloyd_passes):
        moved = {}
        for did in order:
            pts = [centers[c] for c in members[did]]
            if pts:
                moved[did] = (sum(p[0] for p in pts) / len(pts),
                              sum(p[1] for p in pts) / len(pts))
            else:
                moved[did] = refs[did]
        if all(abs(moved[d][0] - refs[d][0]) < 1e-9 and abs(moved[d][1] - refs[d][1]) < 1e-9
               for d in order):
            break
        refs = moved
        members, assign = capacity_assign(refs)

    # Contiguity cleanup: swap a whole stray piece for an equal number of cells that
    # touch the district's main blob. Equal counts both ways, so no seat count moves.
    give_up = set()
    for _ in range(max_swaps):
        stray = None
        for did in order:
            comps = components(members[did])
            if len(comps) < 2:
                continue
            home = max(comps, key=lambda cp: (len(cp), -min(d2(c, did) for c in cp)))
            for comp in comps:
                key = (did, min(comp))
                if comp is not home and key not in give_up:
                    stray = (did, frozenset(comp), key)
                    break
            if stray:
                break
        if stray is None:
            break
        did, piece, key = stray

        # Which neighbouring district surrounds this piece?
        touching = defaultdict(int)
        for c in piece:
            for nb in neighbors(*c):
                od = assign.get(nb)
                if od is not None and od != did:
                    touching[od] += 1
        best = None
        for other in sorted(touching, key=lambda o: (-touching[o], o)):
            # Cells of `other` that touch our home blob, to hand back in exchange.
            home_cells = members[did] - piece
            cands = [c for c in sorted(members[other])
                     if any(nb in home_cells for nb in neighbors(*c))]
            if len(cands) < len(piece):
                continue
            # Prefer give-back cells whose loss does not break `other` apart.
            base = n_components(members[other])
            cands.sort(key=lambda c: (
                n_components(members[other] - {c}) > base, d2(c, did), c))
            take = set(cands[:len(piece)])
            new_did = home_cells | take
            new_other = (members[other] - take) | set(piece)
            before = n_components(members[did]) + n_components(members[other])
            after = n_components(new_did) + n_components(new_other)
            # Accept a break-even trade too, so long as this district actually sheds a
            # piece — otherwise strays that merely move around never get absorbed.
            if (after <= before and n_components(new_did) < n_components(members[did])
                    and (best is None or after < best[0])):
                best = (after, other, take, new_did, new_other)
        if best is None:
            give_up.add(key)
            continue
        _, other, take, new_did, new_other = best
        members[did] = new_did
        members[other] = new_other
        for c in new_did:
            assign[c] = did
        for c in new_other:
            assign[c] = other

    counts = {d: len(members[d]) for d in dists}
    return assign, counts


def map_seed(real_pt, real_bbox, hex_bbox):
    """Map a real lon/lat into the state's distorted cartogram bbox, proportionally."""
    rx0, ry0, rx1, ry1 = real_bbox
    hx0, hy0, hx1, hy1 = hex_bbox
    fx = 0.5 if rx1 == rx0 else (real_pt[0] - rx0) / (rx1 - rx0)
    fy = 0.5 if ry1 == ry0 else (real_pt[1] - ry0) / (ry1 - ry0)
    return hx0 + fx * (hx1 - hx0), hy0 + fy * (hy1 - hy0)


# ── step 3: parties ──────────────────────────────────────────────────────────

PARTIES_TS = BASE_DIR / "viz" / "src" / "constants" / "parties.ts"

# Fallback only; the live order is F5_ORDER in the app's constants.
LEFT_RIGHT_FALLBACK = ["PRG", "DSA", "LIB", "LBR", "OAO", "STY", "CUP", "CON", "POP", "NAT"]


def left_right_order():
    """Parties left→right, read from the app's F5_ORDER so the two cannot diverge."""
    m = re.search(r"F5_ORDER\s*=\s*\[(.*?)\]", PARTIES_TS.read_text(), re.S)
    order = re.findall(r"'(\w+)'", m.group(1)) if m else []
    return order or LEFT_RIGHT_FALLBACK


def group_into_seats(cellset, size, R, x0, y0, strict=False):
    """Partition a district's cells into connected groups of `size` — one per seat.

    size=1 is the plain one-hexagon-per-seat map. size=2 makes each seat a domino of two
    conjoined hexagons. A greedy pass leaves stragglers that cannot be paired, and a
    short group would invent a seat with no member to put in it, so this searches
    exhaustively: always extend from the most constrained free cell (fewest free
    neighbours) and backtrack when a branch dead-ends. District blobs top out around
    twenty cells, so the search is cheap and always finds a partition when one exists.

    Returns {cell: seat_id}, seat_id being the smallest cell in the group.
    """
    if size == 1:
        return {c: c for c in cellset}

    free = set(cellset)
    groups = []

    def free_degree(c):
        return sum(1 for nb in neighbors(*c) if nb in free)

    def extend(group):
        """Ways to grow `group` by one adjacent free cell, most compact first.

        Ordering by how many cells of the group a candidate already touches is what keeps
        seats readable: a seat is a countable unit, so five hexes in a line and five in a
        clump must not both occur, or the reader cannot tell one seat from two. Filling
        concavities first drives every group toward the roundest available shape, with
        the most-constrained cell as the tie-break so nothing gets stranded.
        """
        opts = {nb for c in group for nb in neighbors(*c) if nb in free}
        gset = set(group)

        def touching(c):
            return sum(1 for nb in neighbors(*c) if nb in gset)

        if strict:
            # Only shapes where the new cell touches every cell already in the group.
            # For size 3 that admits the triangle and nothing else — no strings, no Ls.
            opts = {c for c in opts if touching(c) == len(gset)}

        def straightens(c):
            """True if adding c to a 2-cell group makes three cells in a row.

            A bent trio still reads as a clump; a straight one reads as a bar and is the
            shape that makes a seat hard to tell from its neighbour. Prefer the bend
            whenever a full triangle is not available.
            """
            if len(group) != 2:
                return False
            a, b = group
            if c in neighbors(*a) and c in neighbors(*b):
                return False                     # triangle, not a line
            mid, end = (b, a) if c in neighbors(*b) else (a, b)
            qm, rm = axial(*mid)
            return (axial(*c)[0] - qm, axial(*c)[1] - rm) == (qm - axial(*end)[0],
                                                              rm - axial(*end)[1])

        return sorted(opts, key=lambda c: (-touching(c), straightens(c),
                                           free_degree(c), c))

    def solve():
        if not free:
            return True
        start = min(free, key=lambda c: (free_degree(c), c))

        def build(group):
            if len(group) == size:
                groups.append(list(group))
                if solve():
                    return True
                groups.pop()
                return False
            for nxt in extend(group):
                free.discard(nxt)
                if build(group + [nxt]):
                    return True
                free.add(nxt)
            return False

        free.discard(start)
        if build([start]):
            return True
        free.add(start)
        return False

    if not solve() and strict:
        return None          # this blob admits no all-strict partition
    if not free and not groups:
        pass
    if groups and sum(len(g) for g in groups) < len(cellset):
        pass
    if not groups or sum(len(g) for g in groups) != len(cellset):
        # No exact partition exists for this blob (an odd or pinched shape). Fall back to
        # greedy so the map still renders, and let the caller warn about the seat count.
        free = set(cellset)
        groups = []
        while free:
            start = min(free, key=lambda c: (free_degree(c), c))
            group = [start]
            free.discard(start)
            while len(group) < size and (opts := extend(group)):
                nxt = opts[0]
                group.append(nxt)
                free.discard(nxt)
            groups.append(group)

    # The fallback can leave more groups than the district has seats (a stray cell with
    # no neighbour becomes a group of one), which would invent a seat with no member to
    # fill it. Merge the smallest groups until the count matches, nearest pair first: a
    # seat drawn as two hexagons that do not touch is a much smaller wrong than a seat
    # that does not exist.
    n_seats = len(cellset) // size
    while len(groups) > n_seats and len(groups) > 1:
        def centroid(g):
            pts = [hex_center(c[0], c[1], R, x0, y0) for c in g]
            return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

        groups.sort(key=lambda g: (len(g), min(g)))
        g = groups[0]
        gx, gy = centroid(g)
        other = min(groups[1:], key=lambda h: (len(h),
                                               (centroid(h)[0] - gx) ** 2
                                               + (centroid(h)[1] - gy) ** 2,
                                               min(h)))
        other.extend(g)
        groups.remove(g)

    # Local polish: trade single cells between neighbouring seats when it makes both
    # rounder. The search above takes the first valid partition it finds, which leaves
    # some seats strung out; swapping fills their concavities without changing any seat's
    # size. Compactness is what makes a seat countable, so it is worth the extra pass.
    def contacts(g):
        gs = set(g)
        return sum(1 for c in gs for nb in neighbors(*c) if nb in gs) // 2

    def is_line(g):
        """A trio in a straight row — the one 3-cell shape that reads as a bar."""
        if len(g) != 3:
            return False
        gs = set(g)
        deg = {c: sum(1 for nb in neighbors(*c) if nb in gs) for c in gs}
        if sorted(deg.values()) != [1, 1, 2]:
            return False
        mid = max(deg, key=lambda c: deg[c])
        a, b = [c for c in gs if c != mid]
        qm, rm = axial(*mid)
        return (axial(*a)[0] - qm, axial(*a)[1] - rm) == (qm - axial(*b)[0],
                                                          rm - axial(*b)[1])

    def score(g):
        # Contacts dominate; straightness breaks ties, so the polish never trades a bend
        # for a bar of equal compactness.
        return contacts(g) * 10 - (3 if is_line(g) else 0)

    owner = {}
    for gi, g in enumerate(groups):
        for c in g:
            owner[c] = gi
    for _ in range(6):
        improved = False
        for gi, g in enumerate(groups):
            for cell in list(g):
                for nb in neighbors(*cell):
                    gj = owner.get(nb)
                    if gj is None or gj == gi:
                        continue
                    h = groups[gj]
                    for back in list(h):
                        if not any(n in g for n in neighbors(*back)) or back == nb:
                            continue
                        ng = [c for c in g if c != cell] + [back]
                        nh = [c for c in h if c != back] + [cell]
                        if len(largest_component(set(ng))) != len(ng):
                            continue
                        if len(largest_component(set(nh))) != len(nh):
                            continue
                        if score(ng) + score(nh) > score(g) + score(h):
                            groups[gi], groups[gj] = ng, nh
                            g, h = ng, nh
                            owner[back] = gi
                            owner[cell] = gj
                            improved = True
                            break
                    else:
                        continue
                    break
                else:
                    continue
                break
        if not improved:
            break

    out = {}
    for g in groups:
        seat_id = min(g)
        for c in g:
            out[c] = seat_id
    return out


def assign_parties(seat_cells, elected, R, x0, y0, order):
    """Give each seat one elected member, laid out left→right by ideology.

    Seats are dealt in F5_ORDER across the district sorted west→east by seat centroid,
    so every district reads as a left-to-right ideological gradient and same-party seats
    sit together. Returns {seat_id: party}.
    """
    pos = {}
    for seat, cells in seat_cells.items():
        pts = [hex_center(c[0], c[1], R, x0, y0) for c in cells]
        pos[seat] = (sum(p[0] for p in pts) / len(pts),
                     sum(p[1] for p in pts) / len(pts))
    ordered = sorted(seat_cells, key=lambda s: (pos[s][0], pos[s][1], s))
    by_party = defaultdict(int)
    for p in elected:
        by_party[p] += 1
    rank = {p: i for i, p in enumerate(order)}
    seq = []
    for party in sorted(by_party, key=lambda p: (rank.get(p, len(rank)), p)):
        seq.extend([party] * by_party[party])
    return dict(zip(ordered, seq))


# ── viz payload ──────────────────────────────────────────────────────────────

def by_district_cores(by_district):
    """Every core cell of a state, flattened, for the state centroid."""
    return [c for cores in by_district.values() for c in cores]


def viz_payload(out, R, x0, y0):
    """Re-shape the build output into the geometry-only file the app fetches.

    Two differences from the prototype JSON, both deliberate:

    - **No party.** The app recolours the same geometry for STV vs party list, for every
      ballot depth and turnout stop. Baking one scenario's winners in would freeze the
      map on whichever run happened to build it.
    - **Seats are pre-sorted west→east within their district**, so the app fills them by
      zipping F5_ORDER against `seats` and never has to redo the centroid sort. The
      left→right ideological gradient is defined once, here.

    Cells become a flat `[col, row, seatIdx, isCore]` run rather than objects: the same
    information at about a third of the bytes, which matters for a file that ships to
    the browser on every House-tab visit.
    """
    states = {}
    for ab, s in out["states"].items():
        # One entry per seat, from the sub-cells that carry it.
        by_district = defaultdict(set)
        for cell in s["cells"]:
            by_district[cell["district"]].add(cell["core"])

        seat_ids, seat_district = [], []
        district_ids = sorted(d for d in by_district if d)

        def centre(core):
            col, row = (int(v) for v in core.split(","))
            return hex_center(col, row, R, x0, y0)

        for di, did in enumerate(district_ids):
            def west_east(core):
                cx, cy = centre(core)
                return (cx, cy, core)

            for core in sorted(by_district[did], key=west_east):
                seat_ids.append(core)
                seat_district.append(di)

        index_of = {core: i for i, core in enumerate(seat_ids)}
        flat = []
        for cell in s["cells"]:
            idx = index_of.get(cell["core"])
            if idx is None:
                continue
            flat += [cell["col"], cell["row"], idx]

        states[ab] = {
            "clip": s["clip"],
            "rings": [[[round(x, 4), round(y, 4)] for x, y in ring] for ring in s["rings"]],
            "districts": district_ids,
            "seats": seat_district,
            # flat [col, row, seatIdx] on the sub-lattice; meta.subDiv is the divisor
            "cells": flat,
            "seatCentres": s.get("seatCentres", []),
            # The statewide miniature, if the state has one: its own outline plus one
            # cell per statewide seat, in reading order.
            "mini": (None if not s.get("mini") else {
                "rings": [[[round(x, 4), round(y, 4)] for x, y in ring]
                          for ring in s["mini"]["rings"]],
                # flat [col, row, seatIdx] on a lattice `div` times finer than a seat
                "cells": s["mini"]["cells"],
                "div": s["mini"]["div"],
                "district": s["mini"]["district"],
            }),
        }
    return {"meta": out["meta"], "states": states}


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--triple", action="store_true", help="1,726-seat map")
    ap.add_argument("--reserve", action="store_true",
                    help="reserve map: its own districts, plus a statewide band per state")
    ap.add_argument("--out", default=None, help="output JSON path")
    ap.add_argument("--cells-per-seat", type=int, default=1,
                    choices=[1, 2, 3, 4, 5, 6],
                    help="hexagons per seat: 1 = single hex, 2+ = conjoined cluster")
    ap.add_argument("--viz-out", default=None,
                    help="geometry-only JSON for the app (default viz/public/hexmap/)")
    ap.add_argument("--no-viz", action="store_true",
                    help="skip the app payload; write only the prototype JSON")
    args = ap.parse_args()

    cpp = args.cells_per_seat
    suffix = ("_triple" if args.triple else "") + ("_reserve" if args.reserve else "")
    if args.reserve:
        districts, per_state, reserve_by_state = load_reserve_districts(args.triple)
    else:
        districts, per_state = load_districts(args.triple)
        reserve_by_state = {}

    for v in districts.values():
        v["size"] = v["seats"] * cpp          # district size in cells, not seats
    per_state = {k: v * cpp for k, v in per_state.items()}
    print(f"districts={len(districts)} seats={sum(v['seats'] for v in districts.values())}"
          f" cells-per-seat={cpp} lattice cells={sum(per_state.values())}")

    st_layer = load_layer("HexStv30", "HexSTv30")
    ab_by_fips = {a["GEOID"][:2]: a["STATEAB"] for a, _ in load_layer("HexCDv32")}
    fips_by_ab = {v: k for k, v in ab_by_fips.items()}
    states = {a["STATEAB"]: StateShape(a["STATEAB"], r) for a, r in st_layer}

    # A state with statewide seats gives up the matching share of its outline so the
    # border has somewhere to sit. Area per cell is unchanged, so R is too.
    hat_of = {}
    for ab, st in list(states.items()):
        fips = fips_by_ab.get(ab)
        n = reserve_by_state.get(fips, 0)
        if not n:
            continue
        d = per_state.get(fips, 0)
        if d <= 0:
            continue
        full = states[ab].rings
        states[ab] = StateShape(ab, shrink_rings(full, math.sqrt(d / (d + n))))
        hat_of[ab] = n

    dc_seats = per_state.get("11", 0)
    targets = {ab: per_state[fips_by_ab[ab]] for ab in states if fips_by_ab[ab] in per_state}

    # Seeds first: the ring split below needs to know where each district wants to sit,
    # and seeding off the state polygon rather than the chosen cells makes it independent
    # of the lattice.
    real_bboxes = real_state_bboxes(suffix)
    real_cents, missing, county_counts = district_real_centroids(suffix, districts)
    print(f"counties without a centroid: {missing}")
    no_cent = [d for d in districts if d not in real_cents]
    if no_cent:
        print(f"WARNING districts with no county centroid: {no_cent}")

    R_est = lattice_R(states, sum(targets.values()))

    def seeds_for(st, dists, fips, R_ref):
        rbbox = real_bboxes.get(fips, st.bbox)
        out = {}
        for d in dists:
            rp = real_cents.get(d)
            out[d] = map_seed(rp, rbbox, st.bbox) if rp else (
                (st.bbox[0] + st.bbox[2]) / 2, (st.bbox[1] + st.bbox[3]) / 2)
        return spread_coincident(out, R_ref)

    seeds_by_state, ring_targets, ring_of = {}, {}, {}
    for ab, st in sorted(states.items()):
        fips = fips_by_ab.get(ab)
        dists = {d: v for d, v in districts.items() if v["state"] == fips}
        if not dists:
            continue
        seeds = seeds_for(st, dists, fips, R_est)
        seeds_by_state[ab] = seeds
        r_of, r_targets = assign_districts_to_rings(st, dists, seeds, R_est)
        ring_of.update(r_of)
        for i, n in r_targets.items():
            ring_targets[(ab, i)] = n

    print("\nstep 1 — hex lattice")
    cells, pools, picked_by_ring, R, x0, y0 = build_lattice(states, targets, ring_targets)
    print(f"   R={R:.4f} deg  cells={len(cells)}  (target {sum(targets.values())})")

    # DC: no population-scaled outline in the states file, so borrow the delegate
    # hexagon's position and drop its seats onto free lattice cells nearby.
    if dc_seats:
        dd = {a["ABBREV"]: r for a, r in load_layer("HexDDv20")}
        dcx, dcy = rings_centroid(dd["DC"])
        # Search a window around DC's delegate hexagon for unused lattice cells.
        free = []
        c0 = int((dcx - x0) / (SQRT3 * R))
        r0 = int((dcy - y0) / (1.5 * R))
        for row in range(r0 - 4, r0 + 5):
            for col in range(c0 - 4, c0 + 5):
                if (col, row) in cells:
                    continue
                cx, cy = hex_center(col, row, R, x0, y0)
                free.append((math.hypot(cx - dcx, cy - dcy), col, row))
        free.sort()
        for _, col, row in free[:dc_seats]:
            cells[(col, row)] = "DC"
            pools["DC"].add((col, row))
        states["DC"] = StateShape("DC", dd["DC"])
        targets["DC"] = dc_seats
        fips_by_ab["DC"] = "11"
        # DC's outline is a delegate hexagon, far smaller than its share of seats, so
        # its cells sit on the lattice instead of being clipped to that outline.
        for ring in dd["DC"]:
            for x, y in ring:
                pools["DC"].add(nearest_cell(x, y, R, x0, y0))
        # DC's delegate hexagon does not contain the cells placed for it, so its outline
        # becomes the hull of those cells. Every state then has an outline its own seats
        # sit inside, and nothing downstream needs a DC branch.
        dc_verts = [q for c in sorted(pools["DC"]) if cells.get(c) == "DC"
                    for q in hex_vertices(*hex_center(c[0], c[1], R, x0, y0), R)]
        if dc_verts:
            states["DC"] = StateShape("DC", [_hull(dc_verts)])
        print(f"   DC: placed {dc_seats} cells near ({dcx:.2f}, {dcy:.2f})")

    # connectivity check
    by_state = defaultdict(set)
    for c, ab in cells.items():
        by_state[ab].add(c)
    frag = {ab: len(v) - len(largest_component(v)) for ab, v in by_state.items()}
    frag = {k: v for k, v in frag.items() if v}
    print(f"   states with detached cells: {frag if frag else 'none'}")

    print("\nstep 2 — district blobs")
    # Grow per ring, not per state: only districts sharing a ring can trade cells, since
    # growth follows adjacency and a state's rings do not touch.
    assignment = {}
    for ab in sorted(by_state):
        fips = fips_by_ab[ab]
        all_dists = {d: v for d, v in districts.items() if v["state"] == fips}
        if not all_dists:
            continue
        # DC joins `states` after the seed pass above, so seed it here.
        seeds = seeds_by_state.get(ab) or seeds_for(states[ab], all_dists, fips, R)
        if ab == "DC":            # DC's cells are placed by hand, not by ring
            groups = [(by_state[ab], all_dists)]
        else:
            groups = []
            for i in sorted({ring_of[d] for d in all_dists}):
                grp = {d: v for d, v in all_dists.items() if ring_of[d] == i}
                cellset = picked_by_ring.get((ab, i), set()) & by_state[ab]
                groups.append((cellset, grp))
        for cellset, dists in groups:
            if not cellset or not dists:
                if dists:
                    print(f"   {ab}: WARNING no cells for {sorted(dists)}")
                continue
            got, counts = grow_districts(cellset, dists, seeds, R, x0, y0)
            bad = {d: (counts[d], dists[d]["size"]) for d in dists
                   if counts[d] != dists[d]["size"]}
            if bad:
                print(f"   {ab}: SIZE MISMATCH {bad}")
            assignment.update(got)

    # contiguity of each district blob
    cells_by_dist = defaultdict(set)
    for c, d in assignment.items():
        cells_by_dist[d].add(c)
    broken = {d: len(v) - len(largest_component(v)) for d, v in cells_by_dist.items()}
    broken = {k: v for k, v in broken.items() if v}
    print(f"   non-contiguous district blobs: {len(broken)}"
          + (f" {dict(list(broken.items())[:8])}" if broken else ""))

    print("\nstep 3 — seats and parties")
    order = left_right_order()
    seat_of_cell, party_of_seat = {}, {}
    short = strict_fail = 0
    for d, cellset in cells_by_dist.items():
        grouped = group_into_seats(cellset, cpp, R, x0, y0, strict=True)
        if grouped is None:
            grouped = group_into_seats(cellset, cpp, R, x0, y0)
            strict_fail += 1
        seat_cells = defaultdict(list)
        for c, seat in grouped.items():
            seat_cells[seat].append(c)
        short += sum(1 for g in seat_cells.values() if len(g) != cpp)
        seat_of_cell.update(grouped)
        party_of_seat.update(
            assign_parties(seat_cells, districts[d]["elected"], R, x0, y0, order))
    print(f"   districts needing a non-strict shape: {strict_fail} of {len(cells_by_dist)}")
    print(f"   seats: {len(party_of_seat)} from {len(seat_of_cell)} cells"
          f"  (left\u2192right order: {' '.join(order)})")
    if short:
        print(f"   WARNING seats not made of exactly {cpp} cells: {short}")

    print("\nstep 4 — equal-area seat regions")
    # A seat is a region of its district holding an equal share of the district's area,
    # grown on a lattice SUB_DIV times finer than a seat. One seat used to be one whole
    # hexagon with the leftover along the border handed to its nearest neighbour, which
    # left a seat clipped by the outline showing a quarter of a hexagon while the seat
    # beside it showed two and a half. Districts are untouched: a sub-cell joins the
    # district of the coarse cell it falls in, so district borders stay where step 2 put
    # them and keep their own heavier line.
    sub = R / SUB_DIV
    filled = {}          # ab -> {sub-cell: seat}
    seat_centre = {}     # ab -> {seat: coarse centre, for labels}
    spread = []
    for ab, pool in sorted(pools.items()):
        cores = {c for c in pool if cells.get(c) == ab}
        if not cores:
            continue

        # Which core each boundary cell belongs to, by adjacency then by distance. This
        # is what decides the district a boundary cell joins.
        near_core = {c: c for c in cores}
        queue = deque(sorted(cores))
        while queue:
            c = queue.popleft()
            for nb in neighbors(*c):
                if nb in pool and nb not in near_core:
                    near_core[nb] = near_core[c]
                    queue.append(nb)
        for c in sorted(pool - set(near_core)):
            cx, cy = hex_center(c[0], c[1], R, x0, y0)
            near_core[c] = min(sorted(cores), key=lambda k: (
                (hex_center(k[0], k[1], R, x0, y0)[0] - cx) ** 2
                + (hex_center(k[0], k[1], R, x0, y0)[1] - cy) ** 2))

        st = states[ab]
        coarse_pos = {c: hex_center(c[0], c[1], R, x0, y0) for c in pool}
        seat_centre[ab] = {seat_of_cell.get(c, c): coarse_pos[c] for c in cores}

        # Sub-cells inside the state.
        bx0, by0, bx1, by1 = st.bbox
        c0 = int(math.floor((bx0 - x0) / (SQRT3 * sub))) - 1
        c1 = int(math.ceil((bx1 - x0) / (SQRT3 * sub))) + 1
        r0 = int(math.floor((by0 - y0) / (1.5 * sub))) - 1
        r1 = int(math.ceil((by1 - y0) / (1.5 * sub))) + 1
        grid = [(c, r) for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)]
        pts = np.array([hex_center(c, r, sub, x0, y0) for c, r in grid])
        keep = st.contains(pts)
        spos = {cr: (float(p[0]), float(p[1])) for cr, p, ok in zip(grid, pts, keep) if ok}

        # Each sub-cell joins the district of the nearest coarse cell of this state.
        by_district = defaultdict(list)
        for cr, p in spos.items():
            best = min(pool, key=lambda k: (coarse_pos[k][0] - p[0]) ** 2
                                           + (coarse_pos[k][1] - p[1]) ** 2)
            by_district[assignment.get(near_core[best])].append(cr)

        # A sub-cell joins the district of the nearest coarse cell, which across a narrow
        # neck can be a coarse cell of the district next door. That left two- and
        # three-cell islands of one district inside another, and a seat grown into one of
        # them showed up as a stray blob of its party several cells from home. Any
        # fragment that is not its district's main piece joins the district most of its
        # neighbours belong to.
        of_district = {cr: did for did, grp in by_district.items() for cr in grp}
        for _ in range(6):
            moved = 0
            for did in list(by_district):
                pieces = _components(set(by_district[did]))
                for frag in pieces[1:]:
                    votes = defaultdict(int)
                    for c in frag:
                        for nb in neighbors(*c):
                            d2 = of_district.get(nb)
                            if d2 is not None and d2 != did:
                                votes[d2] += 1
                    if not votes:
                        continue
                    winner = max(sorted(votes), key=lambda d: votes[d])
                    for c in frag:
                        of_district[c] = winner
                    moved += len(frag)
            if not moved:
                break
            by_district = defaultdict(list)
            for cr, did in of_district.items():
                by_district[did].append(cr)

        seat_of = {}
        for did, group in sorted(by_district.items(), key=lambda kv: (kv[0] or "",)):
            seats = sorted({seat_of_cell.get(c, c) for c in cores
                            if assignment.get(near_core[c]) == did})
            if not seats or not group:
                continue
            seeds = [seat_centre[ab][sd] for sd in seats]
            quota = [len(group) // len(seats) + (1 if i < len(group) % len(seats) else 0)
                     for i in range(len(seats))]
            # Settle the seeds first, then grow. The relaxation puts each seed at its
            # region's centre of mass; the growth is what keeps the region in one piece.
            take = {}
            for _ in range(8):
                pairs = sorted(((spos[cr][0] - sx) ** 2 + (spos[cr][1] - sy) ** 2, cr, i)
                               for cr in group for i, (sx, sy) in enumerate(seeds))
                left = list(quota)
                take = {}
                for _, cr, i in pairs:
                    if cr in take or left[i] <= 0:
                        continue
                    take[cr] = i
                    left[i] -= 1
                for cr in group:
                    if cr not in take:
                        i = max(range(len(seats)), key=lambda j: left[j])
                        take[cr] = i
                        left[i] -= 1
                moved = 0.0
                for i in range(len(seats)):
                    mine = [spos[cr] for cr, j in take.items() if j == i]
                    if not mine:
                        continue
                    nx = sum(q[0] for q in mine) / len(mine)
                    ny = sum(q[1] for q in mine) / len(mine)
                    moved = max(moved, math.hypot(nx - seeds[i][0], ny - seeds[i][1]))
                    seeds[i] = (nx, ny)
                if moved < 0.02 * sub:
                    break
            take = partition_equal(group, spos, seats, seeds)
            for cr, i in take.items():
                seat_of[cr] = seats[i]
            counts = [sum(1 for v in take.values() if v == i) for i in range(len(seats))]
            if min(counts) > 0:
                spread.append((max(counts) / min(counts), ab, did))
        filled[ab] = seat_of
    print(f"   sub-cells: {sum(len(v) for v in filled.values())} at 1/{SUB_DIV} of a seat")
    if spread:
        spread.sort(reverse=True)
        mid = spread[len(spread) // 2]
        print(f"   seat area within a district, largest/smallest: median {mid[0]:.3f}, "
              f"worst {spread[0][0]:.3f} ({spread[0][1]} {spread[0][2]})")

    # Map centre, from the states that actually carry cells, so the miniatures push
    # outward rather than into the middle of the country.
    all_pts = [hex_center(c[0], c[1], R, x0, y0) for c in cells]
    map_c = (sum(q[0] for q in all_pts) / len(all_pts),
             sum(q[1] for q in all_pts) / len(all_pts))

    # The app pushes each state away from the map centre before drawing, so placement is
    # searched in that same exploded space and the result is shifted back, or a miniature
    # would be tested against a state that is not where it will be drawn.
    core_centre = {}
    for ab, cs in by_state.items():
        pts = [hex_center(c[0], c[1], R, x0, y0) for c in cs]
        core_centre[ab] = (sum(q[0] for q in pts) / len(pts),
                           sum(q[1] for q in pts) / len(pts))
    ex = EXPLODE - 1
    off = {ab: (ex * (c[0] - map_c[0]), ex * (c[1] - map_c[1]))
           for ab, c in core_centre.items()}

    def shifted(ab, rings):
        dx, dy = off.get(ab, (0.0, 0.0))
        return [[(x + dx, y + dy) for x, y in ring] for ring in rings]

    blockers = [_poly_parts(shifted(ab, states[ab].rings)) for ab in sorted(states)]
    min_gap = 0.55 * R
    minis = {}
    for ab, n in sorted(hat_of.items(), key=lambda kv: (-kv[1], kv[0])):
        dx, dy = off.get(ab, (0.0, 0.0))
        at_ex = place_mini(ab, shifted(ab, states[ab].rings), n, R, map_c, blockers, min_gap)
        at = (at_ex[0] - dx, at_ex[1] - dy)
        rings_m, cells_m = mini_state(states[ab].rings, n, R, x0, y0, at)
        minis[ab] = {"rings": rings_m, "cells": cells_m}
        blockers.append(_poly_parts(shifted(ab, rings_m)))
    def n_core(flat):
        return (max((flat[i + 2] for i in range(0, len(flat), 3)), default=-1) + 1)
    short = [(ab, n_core(v["cells"]), hat_of[ab]) for ab, v in minis.items()
             if n_core(v["cells"]) != hat_of[ab]]
    print(f"\nstep 5 — statewide miniatures: {sum(n_core(v['cells']) for v in minis.values())} "
          f"seats across {len(minis)} states")
    print(f"   miniatures short of their seat count: {short if short else 'none'}")

    out = {
        "meta": {
            "R": R, "x0": x0, "y0": y0, "orientation": "pointy-top",
            "seats": sum(targets.values()) // cpp, "cellsPerSeat": cpp,
            "subDiv": SUB_DIV,
            "triple": args.triple,
            "source": "Congressional District Hexmap v3.2 by Daniel Donner for "
                      "The Downballot (https://the-db.co/maps), CC BY 4.0",
        },
        "states": {
            ab: {
                # DC's outline is a delegate hexagon, not a population-scaled shape, so
                # its cells are drawn as raw hexagons rather than clipped to it.
                "clip": True,
                "rings": [[[round(x, 5), round(y, 5)] for x, y in ring]
                          for ring in states[ab].rings],
                # Statewide seats: a miniature of the state, one hexagon per seat, dealt
                # in reading order. Absent for a state that elects at large.
                "mini": ({
                    "rings": [[[round(x, 5), round(y, 5)] for x, y in ring]
                              for ring in minis[ab]["rings"]],
                    "cells": minis[ab]["cells"],
                    "div": SUB_DIV,
                    "district": f"{fips_by_ab[ab]}-RES",
                } if ab in minis else None),
                # Sub-cells, on a lattice SUB_DIV times finer than a seat.
                "cells": [
                    {"col": c[0], "row": c[1],
                     "core": f"{seat[0]},{seat[1]}",
                     "district": assignment.get(seat),
                     "party": party_of_seat.get(seat)}
                    for c, seat in sorted(seat_of.items())
                ],
                # One point per seat on the coarse lattice, for label placement.
                "seatCentres": [[round(q[0], 5), round(q[1], 5)]
                                for _, q in sorted(seat_centre.get(ab, {}).items())],
            }
            for ab, seat_of in sorted(filled.items())
        },
    }
    path = Path(args.out) if args.out else OUT_DIR / f"hex_seat_cartogram{suffix}.json"
    path.write_text(json.dumps(out))
    n_cells = sum(len(s["cells"]) for s in out["states"].values())
    print(f"\nwrote {path} ({n_cells} cells across {len(out['states'])} states)")

    if not args.no_viz:
        vpath = (Path(args.viz_out) if args.viz_out
                 else VIZ_HEX_DIR / f"hex_seat_cartogram{suffix}.json")
        vpath.parent.mkdir(parents=True, exist_ok=True)
        vpath.write_text(json.dumps(viz_payload(out, R, x0, y0)))
        print(f"wrote {vpath} ({vpath.stat().st_size // 1024} KB, geometry only)")


if __name__ == "__main__":
    main()

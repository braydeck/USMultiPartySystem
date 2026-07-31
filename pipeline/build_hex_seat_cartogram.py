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
  2. Grow each state's cells into district blobs of exactly seatCount cells, seeded at
     each district's real county centroid mapped into the state's distorted frame.
     Growth is adjacency-only, so blobs stay contiguous.
  3. Give each hexagon one elected member's party.
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
  python pipeline/build_hex_seat_cartogram.py            # 873-seat standard map
  python pipeline/build_hex_seat_cartogram.py --triple   # 1,726-seat map
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

# Pointy-top hexagon: vertex at the top. width = sqrt(3)*R, height = 2*R.
SQRT3 = math.sqrt(3.0)
HEX_AREA_PER_R2 = 1.5 * SQRT3  # area of a regular hexagon with circumradius 1

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


def sample_offsets(R, rings_of_circles=2):
    """Points inside a unit hexagon, used to estimate what fraction of a cell is
    inside a state polygon. Centre plus two rings — enough to rank edge cells."""
    pts = [(0.0, 0.0)]
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


def district_real_centroids(triple, districts):
    """Mean county centroid per district, in real lon/lat."""
    suffix = "_triple" if triple else ""
    path = OUT_DIR / f"county_to_district{suffix}.csv"
    cents = county_centroids(TOPO_PATH)
    acc = defaultdict(list)
    missing = 0
    with open(path) as f:
        for row in csv.DictReader(f):
            c = cents.get(row["county_fips5"])
            if c is None:
                missing += 1
                continue
            acc[row["district_id"]].append(c)
    out = {}
    for did in districts:
        pts = acc.get(did)
        if pts:
            out[did] = (sum(p[0] for p in pts) / len(pts),
                        sum(p[1] for p in pts) / len(pts))
    return out, missing, {d: len(acc.get(d, [])) for d in districts}


def real_state_bboxes(triple):
    """Real lon/lat bbox per state, from the counties assigned to it."""
    suffix = "_triple" if triple else ""
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


def build_lattice(states, targets, verbose=True):
    """Choose R so in-state cell count == seat total, then pick the best cells.

    Cells are claimed by whichever state covers them most, so no cell is double-used.
    Within a state, seats are apportioned across the state's separate rings by area
    (Michigan's peninsulas, Hawaii's islands) and each ring picks its own best cells,
    which keeps islands from stealing seats from the mainland or vice versa.

    Returns (cores, pools, R, x0, y0): `cores` maps (col, row) -> state abbreviation,
    one core cell per seat; `pools` maps a state to every cell touching it, including
    the boundary cells that get merged into a neighbouring seat so that clipping the
    result to the state outline leaves the silhouette intact.
    """
    total_seats = sum(targets.values())
    total_area = sum(s.area for s in states.values())
    R = math.sqrt(total_area / total_seats / HEX_AREA_PER_R2)

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
    shortfalls = []
    for ab, st in sorted(states.items()):
        target = targets[ab]
        ring_area = {i: ring_area_of(st.rings[i]) for i in range(len(st.rings))}
        # A ring too small to hold a whole cell should not be handed a seat.
        hex_area = HEX_AREA_PER_R2 * R * R
        eligible = {i: a for i, a in ring_area.items()
                    if a >= 0.35 * hex_area and cover.get((ab, i))}
        if not eligible:
            eligible = {max(ring_area, key=lambda i: (ring_area[i], -i)): 1.0}
        alloc = largest_remainder(target, eligible)

        picked = set()
        for i in sorted(eligible):
            want = alloc[i]
            if want <= 0:
                continue
            pool = {c: s for c, s in cover[(ab, i)].items()
                    if owner.get(c) == ab and c not in picked}
            ranked = sorted(pool, key=lambda c: (-pool[c], c))[:want]
            picked |= connect_selection(ranked, pool, want)
        # Any shortfall (ring quota larger than the cells available) falls back to the
        # state's remaining unclaimed cells.
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
            print(f"   {ab}: target={target:4d} rings={len(st.rings)} "
                  f"alloc={ {i: alloc[i] for i in sorted(alloc) if alloc[i]} } "
                  f"kept={len(picked):4d}")

    if shortfalls:
        print("   WARNING shortfalls:", shortfalls)
    return cells, pools, R, x0, y0


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

def grow_districts(state_cells, dists, seeds, R, x0, y0, max_moves=20000):
    """Partition a state's cells into district blobs of exactly seatCount cells.

    Capacity-limited growth strands cells (a cell ringed by districts that are already
    full has nowhere to go), so instead: assign every cell to its nearest seed, then
    repair the sizes by moving boundary cells. Each repair walks a path through the
    district-adjacency graph from an over-full district to an under-full one and shifts
    one cell across every edge on the path, which changes only the endpoints' counts.
    A move is rejected if it would disconnect the donor, so blobs stay contiguous, and
    total imbalance strictly decreases, so the loop terminates.
    """
    centers = {c: hex_center(c[0], c[1], R, x0, y0) for c in state_cells}
    order = sorted(dists, key=lambda d: (-dists[d]["seats"], d))
    target = {d: dists[d]["seats"] for d in dists}

    def d2(cell, did):
        sx, sy = seeds[did]
        return (centers[cell][0] - sx) ** 2 + (centers[cell][1] - sy) ** 2

    # Reserve one distinct cell per district so none starts empty, largest first.
    assign = {}
    taken = set()
    for did in order:
        best = min((c for c in state_cells if c not in taken), key=lambda c: (d2(c, did), c))
        assign[best] = did
        taken.add(best)
    # Everything else goes to its nearest seed.
    for c in sorted(state_cells):
        if c not in assign:
            assign[c] = min(order, key=lambda d: (d2(c, d), d))

    members = defaultdict(set)
    for c, d in assign.items():
        members[d].add(c)

    # Nearest-seed assignment can leave a district holding a detached lobe. Hand each
    # stray piece to an adjacent district before fixing sizes, since the size repair
    # below preserves component counts but never reduces them. A piece with no
    # neighbouring district stays put — that is a genuinely islanded state (Hawaii).
    for _ in range(len(state_cells)):
        moved = False
        for did in order:
            comps = components(members[did])
            if len(comps) < 2:
                continue
            home = min(comps, key=lambda cp: (min(d2(c, did) for c in cp),
                                              sorted(cp)[0]))
            for comp in comps:
                if comp is home:
                    continue
                touching = {assign[nb] for c in comp for nb in neighbors(*c)
                            if nb in assign and assign[nb] != did}
                if not touching:
                    continue
                cx = sum(centers[c][0] for c in comp) / len(comp)
                cy = sum(centers[c][1] for c in comp) / len(comp)

                def seed_dist(d, cx=cx, cy=cy):
                    sx, sy = seeds[d]
                    return (sx - cx) ** 2 + (sy - cy) ** 2, d

                new = min(sorted(touching), key=seed_dist)
                for c in comp:
                    members[did].discard(c)
                    members[new].add(c)
                    assign[c] = new
                moved = True
        if not moved:
            break

    def shift(donor, recip):
        """Move the most recipient-leaning boundary cell from donor to recip.

        Rejected if it would break the donor into more pieces than it already has —
        'more pieces than before' rather than 'more than one', because a state whose
        lattice cells are themselves disconnected (Hawaii's islands, thin states that
        pick up a detached cell) can hand a district a legitimately split blob.
        """
        before = n_components(members[donor])
        cands = sorted((c for c in members[donor]
                        if any(assign.get(nb) == recip for nb in neighbors(*c))),
                       key=lambda c: (d2(c, recip) - d2(c, donor), c))
        for cell in cands:
            rest = members[donor] - {cell}
            if rest and n_components(rest) > before:
                continue
            members[donor].discard(cell)
            members[recip].add(cell)
            assign[cell] = recip
            return cell
        return None

    moves = 0
    blocked = set()
    while moves < max_moves:
        over = sorted(d for d in order if len(members[d]) > target[d])
        under = {d for d in order if len(members[d]) < target[d]}
        if not over or not under:
            break

        # District adjacency, rebuilt each pass since blobs move.
        adj = defaultdict(set)
        for c, d in assign.items():
            for nb in neighbors(*c):
                nd = assign.get(nb)
                if nd is not None and nd != d and (d, nd) not in blocked:
                    adj[d].add(nd)

        # Shortest path from any over-full district to any under-full one.
        path = None
        for src in over:
            prev, queue, seen = {src: None}, [src], {src}
            while queue and path is None:
                nxt = []
                for d in queue:
                    if d in under and d != src:
                        node, chain = d, []
                        while node is not None:
                            chain.append(node)
                            node = prev[node]
                        path = chain[::-1]
                        break
                    for nd in sorted(adj[d]):
                        if nd not in seen:
                            seen.add(nd)
                            prev[nd] = d
                            nxt.append(nd)
                queue = nxt
            if path:
                break
        if not path or len(path) < 2:
            break

        # Apply the whole path or none of it, so imbalance always drops by one.
        applied = []
        for donor, recip in zip(path, path[1:]):
            cell = shift(donor, recip)
            if cell is None:
                for c, dn, rc in reversed(applied):   # roll back
                    members[rc].discard(c)
                    members[dn].add(c)
                    assign[c] = dn
                blocked.add((donor, recip))
                break
            applied.append((cell, donor, recip))
        else:
            moves += len(applied)
            blocked.clear()   # geometry changed; previously blocked edges may work now

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


def assign_parties(cells_of_district, elected, R, x0, y0, order):
    """Give each hexagon one elected member, laid out left→right by ideology.

    Seats are dealt in F5_ORDER across the blob sorted west→east, so every district
    reads as a left-to-right ideological gradient and same-party seats sit together.
    """
    centers = {c: hex_center(c[0], c[1], R, x0, y0) for c in cells_of_district}
    ordered = sorted(cells_of_district, key=lambda c: (centers[c][0], centers[c][1], c))
    by_party = defaultdict(int)
    for p in elected:
        by_party[p] += 1
    rank = {p: i for i, p in enumerate(order)}
    seq = []
    for party in sorted(by_party, key=lambda p: (rank.get(p, len(rank)), p)):
        seq.extend([party] * by_party[party])
    return dict(zip(ordered, seq))


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--triple", action="store_true", help="1,726-seat map")
    ap.add_argument("--out", default=None, help="output JSON path")
    args = ap.parse_args()

    districts, per_state = load_districts(args.triple)
    print(f"districts={len(districts)} seats={sum(per_state.values())}")

    st_layer = load_layer("HexStv30", "HexSTv30")
    ab_by_fips = {a["GEOID"][:2]: a["STATEAB"] for a, _ in load_layer("HexCDv32")}
    fips_by_ab = {v: k for k, v in ab_by_fips.items()}
    states = {a["STATEAB"]: StateShape(a["STATEAB"], r) for a, r in st_layer}

    dc_seats = per_state.get("11", 0)
    targets = {ab: per_state[fips_by_ab[ab]] for ab in states if fips_by_ab[ab] in per_state}

    print("\nstep 1 — hex lattice")
    cells, pools, R, x0, y0 = build_lattice(states, targets)
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
        print(f"   DC: placed {dc_seats} cells near ({dcx:.2f}, {dcy:.2f})")

    # connectivity check
    by_state = defaultdict(set)
    for c, ab in cells.items():
        by_state[ab].add(c)
    frag = {ab: len(v) - len(largest_component(v)) for ab, v in by_state.items()}
    frag = {k: v for k, v in frag.items() if v}
    print(f"   states with detached cells: {frag if frag else 'none'}")

    print("\nstep 2 — district blobs")
    real_bboxes = real_state_bboxes(args.triple)
    real_cents, missing, county_counts = district_real_centroids(args.triple, districts)
    print(f"   counties without a centroid: {missing}")
    no_cent = [d for d in districts if d not in real_cents]
    if no_cent:
        print(f"   WARNING districts with no county centroid: {no_cent}")

    assignment = {}
    for ab, cellset in sorted(by_state.items()):
        fips = fips_by_ab[ab]
        dists = {d: v for d, v in districts.items() if v["state"] == fips}
        if not dists:
            continue
        hbbox = (min(hex_center(*c, R, x0, y0)[0] for c in cellset),
                 min(hex_center(*c, R, x0, y0)[1] for c in cellset),
                 max(hex_center(*c, R, x0, y0)[0] for c in cellset),
                 max(hex_center(*c, R, x0, y0)[1] for c in cellset))
        rbbox = real_bboxes.get(fips, hbbox)
        seeds = {}
        for d in dists:
            rp = real_cents.get(d)
            seeds[d] = map_seed(rp, rbbox, hbbox) if rp else (
                (hbbox[0] + hbbox[2]) / 2, (hbbox[1] + hbbox[3]) / 2)
        got, counts = grow_districts(cellset, dists, seeds, R, x0, y0)
        bad = {d: (counts[d], dists[d]["seats"]) for d in dists
               if counts[d] != dists[d]["seats"]}
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

    print("\nstep 3 — parties")
    order = left_right_order()
    party_of = {}
    for d, cellset in cells_by_dist.items():
        party_of.update(assign_parties(cellset, districts[d]["elected"], R, x0, y0, order))
    print(f"   hexagons coloured: {len(party_of)}  (left\u2192right order: {' '.join(order)})")

    print("\nstep 4 — fill to the state outline")
    filled = {}          # ab -> {cell: core cell it belongs to}
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
        # Anything adjacency can't reach goes to the nearest core.
        for c in sorted(pool - set(seat_of)):
            cx, cy = hex_center(c[0], c[1], R, x0, y0)
            seat_of[c] = min(sorted(cores), key=lambda k: (
                (hex_center(k[0], k[1], R, x0, y0)[0] - cx) ** 2
                + (hex_center(k[0], k[1], R, x0, y0)[1] - cy) ** 2))
        filled[ab] = seat_of
    extra = sum(len(v) for v in filled.values()) - len(cells)
    print(f"   boundary cells merged into a neighbouring seat: {extra}")

    out = {
        "meta": {
            "R": R, "x0": x0, "y0": y0, "orientation": "pointy-top",
            "seats": sum(targets.values()), "triple": args.triple,
            "source": "Congressional District Hexmap v3.2 by Daniel Donner for "
                      "The Downballot (https://the-db.co/maps), CC BY 4.0",
        },
        "states": {
            ab: {
                # DC's outline is a delegate hexagon, not a population-scaled shape, so
                # its cells are drawn as raw hexagons rather than clipped to it.
                "clip": ab != "DC",
                "rings": [[[round(x, 5), round(y, 5)] for x, y in ring]
                          for ring in states[ab].rings],
                "cells": [
                    {"col": c[0], "row": c[1],
                     "core": f"{core[0]},{core[1]}",
                     "district": assignment.get(core),
                     "party": party_of.get(core),
                     "isCore": c == core}
                    for c, core in sorted(seat_of.items())
                ],
            }
            for ab, seat_of in sorted(filled.items())
        },
    }
    suffix = "_triple" if args.triple else ""
    path = Path(args.out) if args.out else OUT_DIR / f"hex_seat_cartogram{suffix}.json"
    path.write_text(json.dumps(out))
    n_cells = sum(len(s["cells"]) for s in out["states"].values())
    print(f"\nwrote {path} ({n_cells} cells across {len(out['states'])} states)")


if __name__ == "__main__":
    main()

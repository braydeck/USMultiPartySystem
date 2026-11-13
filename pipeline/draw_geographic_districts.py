#!/usr/bin/env python3
"""
draw_geographic_districts.py
----------------------------
Draw the four multi-member House maps (double, triple, and their reserve versions) from counties,
with Census ZIP areas splitting any county too big for one district.

Each state's seat total is its population over the map's population per seat. Each district's seat
count follows the people it holds (redrawn 2026-11-11). Per state:
  1. A county worth 4 or more seats is a district of its own. One worth more than the map's
     largest district (9 seats double, 10 triple) is cut into the fewest ZIP-area districts of at
     most that size, by recursive straight cuts on ZIP centres, each piece holding its share of
     the county's people. Respondents there are placed by ZIP (district_assign.py).
  2. The other counties are cut into contiguous districts by recursive two-way cuts sized by the
     base map's rule (4-7 seats). A pocket too small for a district (an island, or counties cut
     off by a big county) joins a touching district, never past the size cap.
  3. Seats go to every district by largest remainder on its people.
A state small enough for one district elects at large, as before.

Inputs: county adjacency and centres (viz/public/topojson/counties-10m.json), county populations
(NCHS 2013 file, 2012 estimates), county tiers (viz/src/data/countyTiers.json), and the Census 2010
ZCTA-to-county relationship and ZCTA gazetteer files (data/raw/census_zcta/, from
www2.census.gov/geo/docs/maps-data/data/rel/ and .../gazetteer/).

Outputs, per map (suffix "", _triple, _reserve, _triple_reserve):
  data/outputs/canonical{suffix}/district_apportionment.csv   district seats and tiers
  data/processed/county_to_district{suffix}.csv               county -> district (split=1 marks
                                                              a county cut into ZIP pieces)
  data/processed/county_split_zcta{suffix}.csv                ZIP piece -> district, people, centre

Deterministic: every choice breaks ties on FIPS or ZIP, so the same inputs draw the same maps.
The district assignment feeds every House figure, so run the full rebuild after redrawing
(pipeline/rebuild_from_typology.py from step 4).

  python3 pipeline/draw_geographic_districts.py                  # all four maps
  python3 pipeline/draw_geographic_districts.py double triple    # some of them
"""

import csv
import csv
import json
import sys
import openpyxl
from collections import defaultdict
from pathlib import Path

BASE_DIR      = Path(__file__).parent.parent
TOPO_PATH     = BASE_DIR / "viz" / "public" / "topojson" / "counties-10m.json"
TIERS_PATH    = BASE_DIR / "viz" / "src" / "data" / "countyTiers.json"
XLSX_PATH     = BASE_DIR / "data" / "raw" / "NCHSURCodes2013.xlsx"
OUTPUT_PATH        = BASE_DIR / "data" / "processed" / "county_to_district.csv"
OUTPUT_PATH_TRIPLE = BASE_DIR / "data" / "processed" / "county_to_district_triple.csv"

sys.path.insert(0, str(Path(__file__).parent))
import math
from run_house_canonical import partition_seats, partition_seats_triple, _partition_standard
from stv_config import (LP_PER_SEAT, LP_PER_SEAT_TRIPLE, STATE_POPS, FIPS_TO_ABBR,
                        STATE_URBAN_PCT)
from hexmap_io import county_centroids

TIER_SORT_ORDER = {"URBAN": 0, "SUBURBAN": 1, "RURAL": 2}


# ── TopoJSON helpers ─────────────────────────────────────────────────────────

def _iter_arc_rings(arc_structure):
    """Yield flat arc-index lists from a Polygon or MultiPolygon arc structure."""
    if not arc_structure:
        return
    first = arc_structure[0]
    if isinstance(first, list):
        if first and isinstance(first[0], list):
            # MultiPolygon: [[ring, ...], ...]
            for polygon in arc_structure:
                for ring in polygon:
                    yield ring
        else:
            # Polygon: [ring, ...]
            for ring in arc_structure:
                yield ring
    else:
        # Bare ring (list of arc indices)
        yield arc_structure


def build_county_adjacency(topo_path: Path) -> tuple:
    """
    Returns:
        adj            — {fips5: set(fips5)} adjacency map
        state_counties — {state_fips2: set(fips5)} counties per state
    """
    with open(topo_path) as f:
        topo = json.load(f)

    arc_to_counties: dict = defaultdict(set)
    state_counties:  dict = defaultdict(set)

    for geom in topo["objects"]["counties"]["geometries"]:
        fips5 = str(geom.get("id", "")).zfill(5)
        sf    = fips5[:2]
        state_counties[sf].add(fips5)
        for ring in _iter_arc_rings(geom.get("arcs", [])):
            for arc_idx in ring:
                arc_to_counties[abs(arc_idx)].add(fips5)

    adj: dict = defaultdict(set)
    for counties in arc_to_counties.values():
        for a in counties:
            for b in counties:
                if a != b:
                    adj[a].add(b)

    # Augment: same-state counties sharing an out-of-state neighbor become adjacent.
    # Handles topology gaps in simplified meshes (e.g. Washington UT has no direct arc
    # to Iron UT, but both border Lincoln NV — so they should be considered adjacent).
    for external, neighbors in list(adj.items()):
        by_state: dict = defaultdict(set)
        for n in neighbors:
            by_state[n[:2]].add(n)
        for state, same_state in by_state.items():
            if state == external[:2]:
                continue  # skip c's own state
            if len(same_state) >= 2:
                for a in same_state:
                    for b in same_state:
                        if a != b:
                            adj[a].add(b)

    return dict(adj), {k: set(v) for k, v in state_counties.items()}


# ── County population loader ─────────────────────────────────────────────────

def load_county_pops(xlsx_path: Path) -> dict:
    """Load 2012 county populations from NCHS xlsx. Returns {fips5: int}."""
    if not xlsx_path.exists():
        print(f"  Warning: {xlsx_path.name} not found — using uniform population weights")
        return {}

    pops: dict = {}
    wb   = openpyxl.load_workbook(xlsx_path, read_only=True)
    ws   = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return pops

    # Detect county population column from header row
    header  = [str(c).lower() if c else "" for c in rows[0]]
    pop_col = None
    for i, h in enumerate(header):
        if "county" in h and "pop" in h:
            pop_col = i
            break
    if pop_col is None:
        for i, h in enumerate(header):
            if "pop" in h and i > 2:
                pop_col = i
                break
    if pop_col is None:
        pop_col = 5  # fallback: column F (0-indexed), typical for NCHS xlsx

    for row in rows[1:]:
        fips_raw = row[0]
        if fips_raw is None:
            continue
        try:
            fips5 = str(int(fips_raw)).zfill(5)
            pop   = int(row[pop_col] or 0)
        except (TypeError, ValueError):
            continue
        pops[fips5] = pop

    return pops


# ── Map definitions ──────────────────────────────────────────────────────────

MAPS = {
    "double": dict(pps=LP_PER_SEAT, triple=False, reserve=False, suffix="", outdir="canonical",
                   big_max=9),
    "triple": dict(pps=LP_PER_SEAT_TRIPLE, triple=True, reserve=False, suffix="_triple",
                   outdir="canonical_triple", big_max=10),
    "reserve": dict(pps=LP_PER_SEAT, triple=False, reserve=True, suffix="_reserve",
                    outdir="canonical_reserve", big_max=9),
    "triple_reserve": dict(pps=LP_PER_SEAT_TRIPLE, triple=True, reserve=True,
                           suffix="_triple_reserve", outdir="canonical_triple_reserve", big_max=10),
}
# Reserve maps: a state with at least MIN_RESERVE_TOTAL seats carves RESERVE_FRAC of them as a
# statewide compensatory tier and districts the rest (rules from build_reserve_apportionment.py).
RESERVE_FRAC = 0.20
MIN_RESERVE_TOTAL = 10

ZCTA_REL = BASE_DIR / "data" / "raw" / "census_zcta" / "zcta_county_rel_10.txt"
ZCTA_GAZ = BASE_DIR / "data" / "raw" / "census_zcta" / "Gaz_zcta_national.txt"
PROCESSED = BASE_DIR / "data" / "processed"
OUTPUTS = BASE_DIR / "data" / "outputs"


def largest_remainder(weights: dict, total: int) -> dict:
    """Integer shares of `total` proportional to `weights`; leftovers by largest fraction, then key."""
    w = sum(weights.values())
    if total <= 0 or w <= 0:
        return {k: 0 for k in weights}
    exact = {k: total * v / w for k, v in weights.items()}
    out = {k: int(math.floor(x)) for k, x in exact.items()}
    for k in sorted(weights, key=lambda k: (-(exact[k] - out[k]), k))[:total - sum(out.values())]:
        out[k] += 1
    return out


def even_sizes(seats: int, big_max: int) -> list:
    """Split a big county's seats into the fewest districts of at most big_max, sizes within one."""
    k = max(1, math.ceil(seats / big_max))
    base, extra = divmod(seats, k)
    return [base + 1] * extra + [base] * (k - extra)


def load_zcta_pieces() -> dict:
    """{county fips5: [(zcta5, pop, lon, lat)]} for every ZCTA's part inside each county (2010)."""
    gaz = {}
    with open(ZCTA_GAZ) as f:
        rdr = csv.reader(f, delimiter="\t")
        hdr = [h.strip() for h in next(rdr)]
        gi, la, lo = hdr.index("GEOID"), hdr.index("INTPTLAT"), hdr.index("INTPTLONG")
        for row in rdr:
            gaz[row[gi].strip()] = (float(row[lo]), float(row[la]))
    pieces = defaultdict(list)
    with open(ZCTA_REL) as f:
        for row in csv.DictReader(f):
            z = row["ZCTA5"]
            if z in gaz:
                lon, lat = gaz[z]
                pieces[row["GEOID"]].append((z, int(row["POPPT"]), lon, lat))
    return pieces


def bisect_pieces(items: list, sizes: list, ids: list) -> dict:
    """Cut ZIP pieces into len(sizes) groups whose populations follow `sizes`, by recursive
    straight cuts along the longer side of the group's extent. Returns {zcta: district id}."""
    if len(sizes) == 1:
        return {z: ids[0] for z, *_ in items}
    order = sorted(range(len(sizes)), key=lambda i: (-sizes[i], i))
    left, right, sl, sr = [], [], 0, 0
    for i in order:                      # balance the two halves' seat totals
        if sl <= sr:
            left.append(i); sl += sizes[i]
        else:
            right.append(i); sr += sizes[i]
    lat0 = sum(it[3] for it in items) / len(items)
    xs = [it[2] * math.cos(math.radians(lat0)) for it in items]
    ys = [it[3] for it in items]
    axis = 0 if (max(xs) - min(xs)) >= (max(ys) - min(ys)) else 1
    key = (lambda it: (it[2] * math.cos(math.radians(lat0)), it[3], it[0])) if axis == 0 \
        else (lambda it: (it[3], it[2], it[0]))
    srt = sorted(items, key=key)
    total = sum(it[1] for it in srt) or 1
    want = total * sl / (sl + sr)
    acc, cut, best = 0, 1, None
    for j, it in enumerate(srt[:-1], start=1):
        acc += it[1]
        if best is None or abs(acc - want) < best:
            best, cut = abs(acc - want), j
    out = bisect_pieces(srt[:cut], [sizes[i] for i in left], [ids[i] for i in left])
    out.update(bisect_pieces(srt[cut:], [sizes[i] for i in right], [ids[i] for i in right]))
    return out


def _connected(nodes: set, adjacency: dict) -> bool:
    if not nodes:
        return True
    start = min(nodes)
    seen, todo = {start}, [start]
    while todo:
        c = todo.pop()
        for n in adjacency.get(c, ()):
            if n in nodes and n not in seen:
                seen.add(n); todo.append(n)
    return len(seen) == len(nodes)


def _components(nodes: set, adjacency: dict) -> list:
    left, out = set(nodes), []
    while left:
        start = min(left)
        seen, todo = {start}, [start]
        while todo:
            c = todo.pop()
            for n in adjacency.get(c, ()):
                if n in left and n not in seen:
                    seen.add(n); todo.append(n)
        out.append(seen)
        left -= seen
    return out


def _carve(region: set, seed, target: float, pops: dict, adjacency: dict):
    """Grow a part from `seed` toward `target` people inside `region`. A step that would cut what
    is left of the region in two also takes the smaller cut-off pieces, so the remainder always
    stays one connected piece. Returns (part, people)."""
    def take(part, c):
        rest = region - part - {c}
        comps = _components(rest, adjacency)
        if len(comps) <= 1:
            return {c}
        keep = max(comps, key=lambda g: (sum(pops.get(x, 0) for x in g), min(g)))
        return {c} | (rest - keep)

    part, cur = set(), 0.0
    add = take(part, seed)
    part |= add; cur += sum(pops.get(x, 0) for x in add)
    while cur < target and len(part) < len(region):
        frontier = {n for c in part for n in adjacency.get(c, ()) if n in region} - part
        best = None
        # Most ties into the part first (compact), then whichever lands nearest the target.
        for c in sorted(frontier, key=lambda c: (-sum(n in part for n in adjacency.get(c, ())), c)):
            add = take(part, c)
            new = cur + sum(pops.get(x, 0) for x in add)
            if abs(new - target) < abs(cur - target) and len(part | add) < len(region):
                if best is None or abs(new - target) < best[0] - 1e-9 and len(add) < len(best[1]) + 3:
                    best = (abs(new - target), add, new)
                    if len(add) == 1:
                        break
        if best is None:
            break
        part |= best[1]; cur = best[2]
    return part, cur


def split_region(region: set, sizes: list, pops: dict, adjacency: dict, centroids: dict) -> list:
    """Cut a connected set of whole counties into len(sizes) contiguous parts whose populations
    follow `sizes`, by recursive two-way cuts. Each cut tries many starting counties (the region's
    outer ones) and keeps the one that lands closest to the wanted split."""
    if len(sizes) <= 1 or len(region) <= 1:
        return [set(region)]
    order = sorted(range(len(sizes)), key=lambda i: (-sizes[i], i))
    left, right, sl, sr = [], [], 0, 0
    for i in order:
        if sl <= sr:
            left.append(sizes[i]); sl += sizes[i]
        else:
            right.append(sizes[i]); sr += sizes[i]
    total = sum(pops.get(c, 0) for c in region)
    target = total * sl / (sl + sr)
    pts = {c: centroids.get(c, (0.0, 0.0)) for c in region}
    mx = sum(p[0] for p in pts.values()) / len(pts)
    my = sum(p[1] for p in pts.values()) / len(pts)
    seeds = sorted(region, key=lambda c: (-((pts[c][0] - mx) ** 2 + (pts[c][1] - my) ** 2), c))[:48]
    if not _connected(region, adjacency):
        return [set(region)]
    best = None
    for seed in seeds:
        part, cur = _carve(region, seed, target, pops, adjacency)
        if part is None or len(part) == len(region):
            continue
        err = abs(cur - target)
        if best is None or err < best[0]:
            best = (err, part)
    if best is None:
        return [set(region)]
    a = best[1]
    return (split_region(a, left, pops, adjacency, centroids)
            + split_region(region - a, right, pops, adjacency, centroids))


def grow_rest(counties: set, pops: dict, adjacency: dict, centroids: dict, sizes: list,
              pps: float, partition=None) -> list:
    """Districts from whole counties: each connected piece of the region gets seats in proportion
    to its people and is cut into contiguous parts of those sizes. Counties with no neighbour in
    the region (islands, or pockets cut off by a big county) join the nearest part."""
    region = {c for c in counties if any(n in counties for n in adjacency.get(c, ()))}
    loose = set(counties) - region
    comps = _components(region, adjacency)
    total_seats = sum(sizes)
    comp_seats = largest_remainder({i: sum(pops.get(c, 0) for c in g) for i, g in enumerate(comps)},
                                   total_seats)
    groups = []
    for i, g in enumerate(comps):
        if comp_seats[i] == 0:
            loose |= g
            continue
        plan = sorted((partition or partition_seats)(comp_seats[i]), reverse=True) \
            if comp_seats[i] > 3 else [comp_seats[i]]
        groups += split_region(g, plan, pops, adjacency, centroids)
    if not groups:
        return [set(counties)]
    for c in sorted(loose):
        cx, cy = centroids.get(c, (0.0, 0.0))
        def dist(g):
            return min(((centroids[n][0] - cx) ** 2 + (centroids[n][1] - cy) ** 2
                        for n in g if n in centroids), default=1e18)
        min(groups, key=lambda g: (dist(g), min(g))).add(c)
    return groups


MIN_WORTH, MAX_WORTH = 3.6, 7.45   # a grown district must round to 4-7 seats


def settle_rest(groups: list, pops: dict, adjacency: dict, centroids: dict, spp: float,
                partition=None) -> list:
    """Merge any part worth under MIN_WORTH seats into its smallest touching neighbour (a
    component too small for a district of its own produces one), then re-cut any part worth
    over MAX_WORTH."""
    groups = [set(g) for g in groups if g]

    def worth(g):
        return sum(pops.get(c, 0) for c in g) / spp

    for _ in range(50):
        small = sorted((g for g in groups if worth(g) < MIN_WORTH), key=lambda g: (worth(g), min(g)))
        if not small or len(groups) == 1:
            break
        g = small[0]
        others = [h for h in groups if h is not g]
        touching = [h for h in others if any(n in h for c in g for n in adjacency.get(c, ()))]
        pool = touching or others
        cx = sum(centroids.get(c, (0, 0))[0] for c in g) / len(g)
        cy = sum(centroids.get(c, (0, 0))[1] for c in g) / len(g)
        into = min(pool, key=lambda h: (worth(h), min(((centroids[c][0] - cx) ** 2 + (centroids[c][1] - cy) ** 2
                                                       for c in h if c in centroids), default=1e18), min(h)))
        into |= g
        groups = others
    out = []
    for g in groups:
        w = worth(g)
        if w > MAX_WORTH and _connected(g, adjacency):
            seats = round(w)
            out += split_region(g, sorted((partition or partition_seats)(seats), reverse=True),
                                pops, adjacency, centroids)
        else:
            out.append(g)
    return out


def dominant_tier(members: list, county_tiers: dict) -> str:
    """Population-weighted majority tier of a district's (county, people) members."""
    acc = defaultdict(float)
    for fips, people in members:
        acc[county_tiers.get(fips, "RURAL")] += people
    return max(acc, key=lambda t: (acc[t], -TIER_SORT_ORDER.get(t, 9))) if acc else "RURAL"


BLOCK_AT = 4.0       # a county worth this many seats is a district of its own


def draw_state(counties: list, D: int, spp: float, big_max: int, rest_partition, county_pops,
               adjacency, centroids, zpieces) -> list:
    """Districts for one state with D district seats and spp people per seat.

    A county worth BLOCK_AT to big_max seats is one district on its own; a bigger one is cut into
    the fewest ZIP-area districts of at most big_max seats. The remaining counties are cut into
    contiguous districts, and a pocket too small for a district joins a touching one (a county
    block included). Seats then go to every district by largest remainder on its people."""
    worth = {c: county_pops.get(c, 0) / spp for c in counties}
    blocks = sorted((c for c in counties if worth[c] >= BLOCK_AT), key=lambda c: (-worth[c], c))
    districts = []
    for c in blocks:
        if worth[c] <= big_max + 0.5:
            districts.append({"members": [(c, county_pops[c])], "counties": {c}, "split": None})
            continue
        sizes = even_sizes(round(worth[c]), big_max)
        ids = [f"{c}#{i}" for i in range(len(sizes))]
        items = zpieces.get(c) or [(c, county_pops[c], *centroids.get(c, (0.0, 0.0)))]
        assign = bisect_pieces(items, sizes, ids)
        scale = county_pops[c] / (sum(it[1] for it in items) or 1)
        for i in range(len(sizes)):
            mine = [it for it in items if assign[it[0]] == ids[i]]
            districts.append({"members": [(c, sum(it[1] for it in mine) * scale)], "counties": {c},
                              "split": (c, ids[i], mine, scale)})
    rest = [c for c in counties if c not in set(blocks)]
    rest_pop = sum(county_pops.get(c, 0) for c in rest)
    rest_seats = round(rest_pop / spp)
    groups = []
    if rest and rest_seats >= 1:
        plan = sorted(rest_partition(rest_seats), reverse=True) if rest_seats > 3 else [rest_seats]
        groups = grow_rest(set(rest), county_pops, adjacency, centroids, plan, spp,
                           partition=rest_partition)
        groups = settle_rest(groups, county_pops, adjacency, centroids, spp,
                             partition=rest_partition)
    else:
        groups = [{c} for c in rest]          # absorbed below
    for g in groups:
        districts.append({"members": [(c, county_pops.get(c, 0)) for c in g], "counties": set(g),
                          "split": None})

    def people(d):
        return sum(p for _, p in d["members"])

    def centre(d):
        if d["split"]:
            its = d["split"][2] or [(None, 1, 0.0, 0.0)]
            return (sum(it[2] for it in its) / len(its), sum(it[3] for it in its) / len(its))
        pts = [centroids[c] for c in d["counties"] if c in centroids] or [(0.0, 0.0)]
        return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)

    kept: set = set()     # small groups with nowhere to go under the size cap; they stay small

    def merge_small():
        nonlocal districts
        cap = (big_max + 0.5) * spp
        while len(districts) > 1:
            small = [d for d in districts if not d["split"] and people(d) / spp < MIN_WORTH
                     and frozenset(d["counties"]) not in kept
                     and not (len(d["counties"]) == 1 and next(iter(d["counties"])) in blocks)]
            if not small:
                break
            g = min(small, key=lambda d: (people(d), min(d["counties"])))
            others = [d for d in districts if d is not g and people(d) + people(g) <= cap]
            if not others:
                kept.add(frozenset(g["counties"]))
                continue
            touching = [d for d in others if any(n in d["counties"] for c in g["counties"]
                                                 for n in adjacency.get(c, ()))]
            gx, gy = centre(g)
            into = min(touching or others, key=lambda d: (
                people(d) if touching else (centre(d)[0] - gx) ** 2 + (centre(d)[1] - gy) ** 2,
                min(d["counties"])))
            into["members"] += g["members"]
            if into["split"]:
                into.setdefault("whole", set()).update(g["counties"])
            into["counties"] |= g["counties"]
            districts = [d for d in districts if d is not g]

    # A whole-county group too small for a district joins the smallest touching district; with
    # none touching, the nearest. Pieces of split counties are never merged away. Then any
    # whole-county district grown past MAX_WORTH is re-cut (by its connected parts first), and the
    # two steps repeat until neither changes anything.
    stuck: set = set()
    for _round in range(12):
        merge_small()
        changed = False
        for d in list(districts):
            if d["split"] or people(d) / spp <= MAX_WORTH or frozenset(d["counties"]) in stuck:
                continue
            if len(d["counties"]) == 1:
                continue
            comps = _components(d["counties"], adjacency)
            w = lambda g: sum(county_pops.get(c, 0) for c in g) / spp
            real = [g for g in comps if w(g) >= MIN_WORTH]
            if len(real) >= 2:
                parts = real
            else:
                main = max(comps, key=lambda g: (w(g), min(g)))
                seats = round(people(d) / spp)
                parts = split_region(main, sorted(rest_partition(seats), reverse=True),
                                     county_pops, adjacency, centroids)
            # Islands and other small detached pieces ride with the nearest part.
            for g in comps:
                if any(g <= h for h in parts):
                    continue
                for c in sorted(g):
                    cx, cy = centroids.get(c, (0.0, 0.0))
                    min(parts, key=lambda h: (min(((centroids[n][0] - cx) ** 2 + (centroids[n][1] - cy) ** 2
                                                   for n in h if n in centroids), default=1e18),
                                              min(h))).add(c)
            if len(parts) < 2 or any(w(h) < MIN_WORTH for h in parts):
                stuck.add(frozenset(d["counties"]))
                continue
            districts.remove(d)
            for g in parts:
                districts.append({"members": [(c, county_pops.get(c, 0)) for c in g],
                                  "counties": set(g), "split": None})
            changed = True
        if not changed:
            break
    merge_small()

    alloc = largest_remainder({i: people(d) for i, d in enumerate(districts)}, D)
    for i, d in enumerate(districts):
        d["seats"] = alloc[i]
    assert all(d["seats"] > 0 for d in districts), "a drawn district earned no seat"
    return districts




def draw_map(name: str, adjacency, state_counties, county_tiers, county_pops, centroids, zpieces):
    cfg = MAPS[name]
    pps, triple, reserve = cfg["pps"], cfg["triple"], cfg["reserve"]
    base_partition = (lambda t, u: partition_seats_triple(t, urban_pct=u)) if triple \
        else (lambda t, u: partition_seats(t))
    rest_partition = _partition_standard if triple else partition_seats

    apport_rows, county_rows, split_rows = [], [], []
    report = []
    for fips in sorted(STATE_POPS):
        sf = f"{fips:02d}"
        abbr = FIPS_TO_ABBR.get(fips, sf)
        T = max(1, round(STATE_POPS[fips] / pps))
        upct = STATE_URBAN_PCT.get(fips, 70.0)
        R_res = 0
        if reserve and T >= MIN_RESERVE_TOTAL:
            R_res = int(round(RESERVE_FRAC * T))
        D = T - R_res
        counties = sorted(state_counties.get(sf, set()))
        P = sum(county_pops.get(c, 0) for c in counties) or 1
        spp = P / D                                  # this state's people per district seat

        if reserve:
            # Below the reserve threshold the whole delegation is elected at large, no reserve.
            at_large = not R_res or len(base_partition(D, upct)) == 1
        else:
            at_large = len(base_partition(T, upct)) == 1
        districts = []      # dicts: members [(county, people)], seats, kind
        if at_large:
            districts.append({"members": [(c, county_pops.get(c, 0)) for c in counties],
                              "counties": set(counties), "seats": D, "split": None})
        else:
            districts = draw_state(counties, D, spp, cfg["big_max"], rest_partition, county_pops,
                                   adjacency, centroids, zpieces)

        for d in districts:
            d["pop"] = sum(p for _, p in d["members"])
            d["tier"] = dominant_tier(d["members"], county_tiers)
        districts = [d for d in districts if d["seats"] > 0 or at_large]
        districts.sort(key=lambda d: (TIER_SORT_ORDER.get(d["tier"], 9), -d["pop"]))
        for n, d in enumerate(districts, start=1):
            did = f"{sf}-{n:02d}"
            d["id"] = did
            row = {"state_fips": fips, "state_abbr": abbr, "district_id": did,
                   "seat_count": int(d["seats"]), "density_tier": d["tier"]}
            if reserve:
                row["reserve"] = R_res
            apport_rows.append(row)
            report.append((abbr, did, int(d["seats"]), d["pop"], spp, bool(d["split"])))
            if d["split"]:
                c, _, mine, scale = d["split"]
                for z, people, lon, lat in mine:
                    split_rows.append({"county_fips5": c, "zcta5": z, "district_id": did,
                                       "pop": round(people * scale), "lon": round(lon, 6),
                                       "lat": round(lat, 6)})
        whole = {}
        for d in districts:
            for c in (d["counties"] if not d["split"] else d.get("whole", set())):
                whole[c] = d["id"]
        for c in counties:
            if c not in whole:   # a split county: its row names the piece with the most people
                pieces = [d for d in districts if d["split"] and d["split"][0] == c]
                whole[c] = max(pieces, key=lambda d: (d["pop"], d["id"]))["id"]
            county_rows.append({"county_fips5": c, "state_fips": sf, "district_id": whole[c],
                                "density_tier": county_tiers.get(c, "RURAL"),
                                "split": int(any(d["split"] and d["split"][0] == c for d in districts))})
    return apport_rows, county_rows, split_rows, report


def main(maps=None):
    maps = maps or list(MAPS)
    print("Building county adjacency from TopoJSON…")
    adjacency, state_counties = build_county_adjacency(TOPO_PATH)
    with open(TIERS_PATH) as f:
        county_tiers: dict = json.load(f)
    county_pops = load_county_pops(XLSX_PATH)
    centroids = county_centroids(TOPO_PATH)
    zpieces = load_zcta_pieces()
    print(f"  {len(adjacency):,} counties, {len(county_pops):,} with population, "
          f"{sum(len(v) for v in zpieces.values()):,} ZIP-county pieces")
    for name in maps:
        cfg = MAPS[name]
        apport, crow, srow, report = draw_map(name, adjacency, state_counties, county_tiers,
                                              county_pops, centroids, zpieces)
        out_dir = OUTPUTS / cfg["outdir"]
        out_dir.mkdir(parents=True, exist_ok=True)
        fields = ["state_fips", "state_abbr", "district_id", "seat_count", "density_tier"] + \
            (["reserve"] if cfg["reserve"] else [])
        with open(out_dir / "district_apportionment.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(apport)
        with open(PROCESSED / f"county_to_district{cfg['suffix']}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["county_fips5", "state_fips", "district_id",
                                              "density_tier", "split"])
            w.writeheader(); w.writerows(sorted(crow, key=lambda r: r["county_fips5"]))
        with open(PROCESSED / f"county_split_zcta{cfg['suffix']}.csv", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["county_fips5", "zcta5", "district_id", "pop", "lon", "lat"])
            w.writeheader(); w.writerows(sorted(srow, key=lambda r: (r["county_fips5"], r["zcta5"])))
        seats = sum(r["seat_count"] for r in apport) + (
            sum({r["state_abbr"]: r["reserve"] for r in apport}.values()) if cfg["reserve"] else 0)
        ratios = [pop / s / spp for _, _, s, pop, spp, _ in report if s]
        merged = sum(1 for r in report if r[1] == "merged")
        if merged:
            print(f"  {merged} grown groups too small for a seat were merged into a neighbour")
        print(f"{name}: {len(apport)} districts, {seats} seats, "
              f"{sum(1 for r in report if r[5])} cut from split counties; people per seat vs state "
              f"average: min {min(ratios):.2f}, max {max(ratios):.2f}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    main(args or None)

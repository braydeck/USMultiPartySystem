#!/usr/bin/env python3
"""
draw_geographic_districts.py
----------------------------
Build geographically contiguous multi-member House districts by county.

Algorithm per state:
  1. Extract county adjacency from TopoJSON shared arcs
  2. For each district (urban-first), seed from the highest-population
     county matching the district's density tier
  3. Grow region by adjacency until target population is reached,
     preferring tier-matching counties at each step
  4. Flood-fill any leftover counties into the nearest assigned district

Output: data/processed/county_to_district.csv
  county_fips5  — 5-digit zero-padded county FIPS
  state_fips    — 2-digit zero-padded state FIPS
  district_id   — e.g. "17-01"
  density_tier  — URBAN | SUBURBAN | RURAL
"""

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
from run_house_canonical import run_apportionment, partition_seats_triple
from stv_config import POP_PER_SEAT, POP_PER_SEAT_TRIPLE

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


# ── Geographic district drawing ──────────────────────────────────────────────

def draw_state_districts(state_fips: str,
                          state_county_set: set,
                          adjacency: dict,
                          districts: list,
                          county_tiers: dict,
                          county_pops: dict,
                          pop_per_seat: int = 380_000) -> dict:
    """
    Assign counties to districts using seed-and-grow then flood-fill.

    districts: list of dicts {district_id, seat_count, density_tier}
               sorted URBAN-first, SUBURBAN-second, RURAL-last
    Returns: {county_fips5: district_id}
    """
    unassigned: set = set(state_county_set)
    assignment: dict = {}

    for dist in districts:
        target_pop = dist["seat_count"] * pop_per_seat
        tier       = dist["density_tier"]

        # Seed: highest-population unassigned county matching tier; fall back to any
        pool = [c for c in unassigned if county_tiers.get(c) == tier]
        if not pool:
            pool = list(unassigned)
        if not pool:
            continue

        seed = max(pool, key=lambda c: county_pops.get(c, 0))
        in_district: set = {seed}
        unassigned.discard(seed)
        frontier: set = {n for n in adjacency.get(seed, set()) if n in unassigned}
        current_pop   = county_pops.get(seed, 1)

        # Grow: prefer tier-matching counties, break ties by population
        while current_pop < target_pop and frontier:
            best = max(frontier, key=lambda c: (
                int(county_tiers.get(c, "") == tier),
                county_pops.get(c, 0),
            ))
            in_district.add(best)
            unassigned.discard(best)
            frontier.discard(best)
            frontier |= {n for n in adjacency.get(best, set()) if n in unassigned}
            current_pop += county_pops.get(best, 1)

        for c in in_district:
            assignment[c] = dist["district_id"]

    # Flood-fill leftover counties into adjacent assigned district
    changed = True
    while changed and unassigned:
        changed = False
        for c in list(unassigned):
            for nbr in adjacency.get(c, set()):
                if nbr in assignment:
                    assignment[c] = assignment[nbr]
                    unassigned.discard(c)
                    changed = True
                    break

    # Hard fallback for isolated counties (e.g., island FIPS with no adjacency)
    if unassigned and districts:
        fallback_id = districts[0]["district_id"]
        for c in unassigned:
            assignment[c] = fallback_id

    return assignment


# ── Main ─────────────────────────────────────────────────────────────────────

def main(triple=False):
    print("Building county adjacency from TopoJSON…")
    adjacency, state_counties = build_county_adjacency(TOPO_PATH)
    print(f"  {len(adjacency):,} counties with adjacency data")
    print(f"  {sum(len(v) for v in state_counties.values()):,} county-state entries")

    print("Loading county tiers…")
    with open(TIERS_PATH) as f:
        county_tiers: dict = json.load(f)
    print(f"  {len(county_tiers):,} counties with tier assignment")

    print("Loading county populations from NCHS xlsx…")
    county_pops = load_county_pops(XLSX_PATH)
    print(f"  {len(county_pops):,} counties with population")

    if triple:
        print("Running TRIPLE WYOMING apportionment…")
        apportion = run_apportionment(pop_per_seat=POP_PER_SEAT_TRIPLE,
                                      partition_fn=partition_seats_triple)
        output_path = OUTPUT_PATH_TRIPLE
        active_pop_per_seat = POP_PER_SEAT_TRIPLE
    else:
        print("Running apportionment…")
        apportion = run_apportionment()
        output_path = OUTPUT_PATH
        active_pop_per_seat = POP_PER_SEAT
    n_districts = len(apportion)
    print(f"  {n_districts} districts across {apportion['state_fips'].nunique()} states")

    # Build per-state district lists sorted URBAN-first
    state_districts: dict = defaultdict(list)
    for _, row in apportion.iterrows():
        sf = str(int(row["state_fips"])).zfill(2)
        state_districts[sf].append({
            "district_id":  row["district_id"],
            "seat_count":   int(row["seat_count"]),
            "density_tier": row["density_tier"],
        })
    for sf in state_districts:
        state_districts[sf].sort(key=lambda d: TIER_SORT_ORDER.get(d["density_tier"], 9))

    print("Drawing geographic districts…")
    rows: list = []
    total_unassigned = 0

    for sf in sorted(state_districts.keys()):
        dists      = state_districts[sf]
        county_set = state_counties.get(sf, set())
        if not county_set:
            continue

        assignment = draw_state_districts(
            sf, county_set, adjacency, dists, county_tiers, county_pops,
            pop_per_seat=active_pop_per_seat,
        )
        leftover = county_set - set(assignment.keys())
        if leftover:
            total_unassigned += len(leftover)
            sample = sorted(leftover)[:5]
            print(f"  WARNING: state {sf} — {len(leftover)} unassigned counties: {sample}")

        for fips5, dist_id in assignment.items():
            rows.append({
                "county_fips5": fips5,
                "state_fips":   sf,
                "district_id":  dist_id,
                "density_tier": county_tiers.get(fips5, "RURAL"),
            })

    print(f"  Total unassigned after flood-fill: {total_unassigned}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["county_fips5", "state_fips", "district_id", "density_tier"]
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {output_path}  ({len(rows):,} county-district mappings)")


if __name__ == "__main__":
    main(triple="--triple" in sys.argv)

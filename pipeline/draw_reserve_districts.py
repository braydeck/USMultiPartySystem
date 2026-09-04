#!/usr/bin/env python3
"""
draw_reserve_districts.py
--------------------------
Draw geographic districts for the ~20% per-state reserve scenario.

Reuses draw_geographic_districts.py's county-assignment logic but feeds it the
reserve apportionment (from build_reserve_apportionment.py) instead of calling
run_apportionment() internally.

Output:
  data/processed/county_to_district_reserve.csv
  data/processed/county_to_district_triple_reserve.csv
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from draw_geographic_districts import (  # noqa: E402
    build_county_adjacency, load_county_pops, draw_state_districts,
    TOPO_PATH, TIERS_PATH, XLSX_PATH, TIER_SORT_ORDER,
)
from stv_config import POP_PER_SEAT, POP_PER_SEAT_TRIPLE  # noqa: E402

CONFIGS = [
    {
        "label": "DOUBLE RESERVE",
        "apport": BASE_DIR / "data" / "outputs" / "No_C7_canonical_reserve" / "district_apportionment.csv",
        "output": BASE_DIR / "data" / "processed" / "county_to_district_reserve.csv",
        "pps": POP_PER_SEAT,
    },
    {
        "label": "TRIPLE RESERVE",
        "apport": BASE_DIR / "data" / "outputs" / "No_C7_triple_reserve" / "district_apportionment.csv",
        "output": BASE_DIR / "data" / "processed" / "county_to_district_triple_reserve.csv",
        "pps": POP_PER_SEAT_TRIPLE,
    },
]


def main():
    print("Building county adjacency from TopoJSON…")
    adjacency, state_counties = build_county_adjacency(TOPO_PATH)
    print(f"  {len(adjacency):,} counties")

    print("Loading county tiers…")
    with open(TIERS_PATH) as f:
        county_tiers: dict = json.load(f)

    print("Loading county populations…")
    county_pops = load_county_pops(XLSX_PATH)

    for cfg in CONFIGS:
        print(f"\n{'='*70}\n{cfg['label']}")
        apportion = pd.read_csv(cfg["apport"])
        n_districts = len(apportion)
        print(f"  {n_districts} districts, {apportion.seat_count.sum()} district seats")

        state_districts: dict = defaultdict(list)
        for _, row in apportion.iterrows():
            sf = str(int(row["state_fips"])).zfill(2)
            state_districts[sf].append({
                "district_id": row["district_id"],
                "seat_count": int(row["seat_count"]),
                "density_tier": row["density_tier"],
            })
        for sf in state_districts:
            state_districts[sf].sort(key=lambda d: TIER_SORT_ORDER.get(d["density_tier"], 9))

        print(f"  Drawing geographic districts for {len(state_districts)} states…")
        rows: list = []
        total_unassigned = 0

        for sf in sorted(state_districts.keys()):
            dists = state_districts[sf]
            county_set = state_counties.get(sf, set())
            if not county_set:
                continue

            assignment = draw_state_districts(
                sf, county_set, adjacency, dists, county_tiers, county_pops,
                pop_per_seat=cfg["pps"],
            )
            leftover = county_set - set(assignment.keys())
            if leftover:
                total_unassigned += len(leftover)

            for fips5, dist_id in assignment.items():
                rows.append({
                    "county_fips5": fips5,
                    "state_fips": sf,
                    "district_id": dist_id,
                    "density_tier": county_tiers.get(fips5, "RURAL"),
                })

        print(f"  Unassigned after flood-fill: {total_unassigned}")
        cfg["output"].parent.mkdir(parents=True, exist_ok=True)
        with open(cfg["output"], "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["county_fips5", "state_fips", "district_id", "density_tier"])
            writer.writeheader()
            writer.writerows(sorted(rows, key=lambda r: r["county_fips5"]))
        print(f"  Saved {cfg['output']}  ({len(rows):,} mappings)")


if __name__ == "__main__":
    main()

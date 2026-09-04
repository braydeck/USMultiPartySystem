#!/usr/bin/env python3
"""
build_reserve_apportionment.py
------------------------------
Generate district apportionment CSVs for the ~20% per-state reserve scenario.

Each multi-district state carves ~20% of its seats as a statewide compensatory reserve.
The remaining ~80% are partitioned into districts using the same sizing rules as the base
map (partition_seats for double, partition_seats_triple for triple). Single-district states
— those whose total fits in one district at the base map's max magnitude — are unchanged.

The chamber size stays at 873 (double) and 1726 (triple). No seats are added.

Output:
  data/outputs/No_C7_canonical_reserve/district_apportionment.csv
  data/outputs/No_C7_triple_reserve/district_apportionment.csv
"""

import inspect
import sys
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from run_house_canonical import (run_apportionment, partition_seats,
                                  partition_seats_triple, assign_density_tiers)
from stv_config import (STATE_POPS, FIPS_TO_ABBR, POP_PER_SEAT,
                         POP_PER_SEAT_TRIPLE, STATE_URBAN_PCT)

RESERVE_FRAC = 0.20

CONFIGS = [
    {
        "label": "DOUBLE",
        "pps": POP_PER_SEAT,
        "pfn": partition_seats,
        "out": BASE_DIR / "data" / "outputs" / "No_C7_canonical_reserve" / "district_apportionment.csv",
    },
    {
        "label": "TRIPLE",
        "pps": POP_PER_SEAT_TRIPLE,
        "pfn": partition_seats_triple,
        "out": BASE_DIR / "data" / "outputs" / "No_C7_triple_reserve" / "district_apportionment.csv",
    },
]


def main():
    for cfg in CONFIGS:
        pps = cfg["pps"]
        pfn = cfg["pfn"]
        has_urban = 'urban_pct' in inspect.signature(pfn).parameters

        # First get the base apportionment to find max magnitude (at-large threshold)
        base = run_apportionment(pop_per_seat=pps, partition_fn=pfn)
        cap = int(base["seat_count"].max())

        rows = []
        total_d = 0
        total_r = 0
        for fips in sorted(STATE_POPS.keys()):
            T = max(1, round(STATE_POPS[fips] / pps))
            abbr = FIPS_TO_ABBR.get(fips, str(fips))
            kw = {'urban_pct': STATE_URBAN_PCT.get(fips, 70.0)} if has_urban else {}

            orig = sorted(pfn(T, **kw), reverse=True)

            # Single-district state: no reserve needed
            if len(orig) <= 1:
                tiers = assign_density_tiers(orig, fips)
                for idx, (size, tier) in enumerate(zip(orig, tiers), start=1):
                    rows.append({
                        "state_fips": fips, "state_abbr": abbr,
                        "district_id": f"{fips:02d}-{idx:02d}",
                        "seat_count": size, "density_tier": tier,
                        "reserve": 0,
                    })
                total_d += T
                continue

            R = int(round(RESERVE_FRAC * T))
            D = T - R

            # If the reduced district total collapses to a single district under
            # partition rules, shrink the reserve until it doesn't. A multi-district
            # state with a single reserve district is pointless — the reserve has
            # nothing to compensate against. Minimum reserve is 1 seat.
            new = pfn(D, **kw)
            while len(new) <= 1 and R > 1:
                R -= 1
                D = T - R
                new = pfn(D, **kw)

            if len(new) <= 1:
                # Even R=1 doesn't split. Keep the base partition with no reserve —
                # these are small states (T=8 at double, T=11 at triple) where the
                # base map already has 2 reasonably-sized districts.
                R = 0
                D = T
                new = orig

            new = sorted(new, reverse=True)
            tiers = assign_density_tiers(new, fips)
            for idx, (size, tier) in enumerate(zip(new, tiers), start=1):
                rows.append({
                    "state_fips": fips, "state_abbr": abbr,
                    "district_id": f"{fips:02d}-{idx:02d}",
                    "seat_count": size, "density_tier": tier,
                    "reserve": R,
                })
            total_d += D
            total_r += R

        df = pd.DataFrame(rows)
        chamber = total_d + total_r
        n_reserve_states = int((df.groupby("state_abbr")["reserve"].first() > 0).sum())
        n_districts = len(df)

        cfg["out"].parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(cfg["out"], index=False)
        print(f"{cfg['label']}: {n_districts} districts, {total_d} district seats + "
              f"{total_r} reserve = {chamber}, effective {total_r/chamber*100:.1f}% "
              f"({n_reserve_states} reserve states)")
        size_dist = df["seat_count"].value_counts().sort_index()
        for sz, cnt in size_dist.items():
            print(f"    {sz}-seat: {cnt}")


if __name__ == "__main__":
    main()

"""
stv_step1.py
------------
District apportionment for the 10-party STV simulation.

Rules:
- Seats per state = max(1, round(population / 380,000))
- Preferred district size: 5 seats
- Minimize 3-seat districts (prefer 7-seat over 3-seat when not divisible by 5)
- 2 and 4-seat districts ONLY for states with exactly 2 or 4 total seats
- Label each district URBAN / SUBURBAN / RURAL based on Census urban %
"""

import pandas as pd
import numpy as np
from stv_config import (
    STATE_POPS, POP_PER_SEAT, STATE_URBAN_PCT, FIPS_TO_ABBR, OUTPUT_DIR
)


def seats_for_state(fips: int) -> int:
    """Compute seat count for a state: max(1, round(pop / 380000))."""
    return max(1, round(STATE_POPS[fips] / POP_PER_SEAT))


def partition_seats(total: int) -> list:
    """
    Partition total seats into district sizes from {7, 6, 5, 4}.

    Objective (lexicographic):
      1. Minimize 4-seat districts
      2. Maximize 7-seat districts
      3. Minimize 6-seat districts
    States with <=3 total seats get a single at-large district.
    """
    if total <= 3:
        return [total]

    best      = None
    best_key  = None  # (n4, -n7, n6) — minimize lexicographically
    for n7 in range(total // 7, -1, -1):
        rem7 = total - 7 * n7
        for n6 in range(rem7 // 6, -1, -1):
            rem76 = rem7 - 6 * n6
            for n5 in range(rem76 // 5, -1, -1):
                rem = rem76 - 5 * n5
                if rem >= 0 and rem % 4 == 0:
                    n4  = rem // 4
                    key = (n4, -n7, n6)
                    if best_key is None or key < best_key:
                        best_key = key
                        best     = [7]*n7 + [6]*n6 + [5]*n5 + [4]*n4
    return sorted(best, reverse=True) if best else [total]


def assign_density_tiers(district_sizes: list, fips: int) -> list:
    """
    Assign URBAN / SUBURBAN / RURAL labels to districts in a state.

    Strategy:
    - Derive tier fractions from Census urban % for the state.
    - True-urban fraction = max(0, (urban_pct - 30) / 100)  [above suburban baseline]
    - Suburban fraction   = 0.30 (constant baseline)
    - Rural fraction      = 1 - urban_pct / 100
    - Normalize to sum = 1, compute counts, assign to districts largest-first.
    - For a single-district state, assign the dominant tier by threshold.
    """
    urban_pct = STATE_URBAN_PCT.get(fips, 70.0)
    D = len(district_sizes)

    if D == 1:
        if urban_pct >= 75:
            return ["URBAN"]
        elif urban_pct >= 45:
            return ["SUBURBAN"]
        else:
            return ["RURAL"]

    # Three-tier fractions
    true_urban_frac = max(0.0, (urban_pct - 30.0) / 100.0)
    suburban_frac   = 0.30
    rural_frac      = max(0.0, 1.0 - urban_pct / 100.0)

    total_frac = true_urban_frac + suburban_frac + rural_frac
    if total_frac < 1e-9:
        total_frac = 1.0
    u_f = true_urban_frac / total_frac
    s_f = suburban_frac   / total_frac
    # r_f = rural_frac    / total_frac  (derived as remainder)

    n_u = round(D * u_f)
    n_s = round(D * s_f)
    n_r = D - n_u - n_s

    # Clamp to non-negative; absorb rounding surplus into rural
    if n_r < 0:
        n_s += n_r
        n_r = 0
    if n_s < 0:
        n_u += n_s
        n_s = 0
    if n_u < 0:
        n_u = 0

    # Ensure total = D
    while n_u + n_s + n_r < D:
        n_r += 1
    while n_u + n_s + n_r > D:
        if n_r > 0:
            n_r -= 1
        elif n_s > 0:
            n_s -= 1
        else:
            n_u -= 1

    # Assign: largest districts → URBAN first, then SUBURBAN, then RURAL
    # district_sizes is already sorted descending
    tiers = ["URBAN"] * n_u + ["SUBURBAN"] * n_s + ["RURAL"] * n_r
    return tiers


def run_apportionment() -> pd.DataFrame:
    """
    Run full district apportionment for all states.

    Returns DataFrame with columns:
        state_fips, state_abbr, district_id, seat_count, density_tier,
        approx_population
    """
    rows = []

    total_seats     = 0
    total_districts = 0

    for fips in sorted(STATE_POPS.keys()):
        seats = seats_for_state(fips)
        total_seats += seats
        abbr = FIPS_TO_ABBR.get(fips, str(fips))

        district_sizes = partition_seats(seats)
        tiers          = assign_density_tiers(district_sizes, fips)
        total_districts += len(district_sizes)

        for idx, (size, tier) in enumerate(zip(district_sizes, tiers), start=1):
            district_id = f"{fips:02d}-{idx:02d}"
            rows.append({
                "state_fips":        fips,
                "state_abbr":        abbr,
                "district_id":       district_id,
                "seat_count":        size,
                "density_tier":      tier,
                "approx_population": size * POP_PER_SEAT,
            })

    df = pd.DataFrame(rows)

    # Verification
    assert df["seat_count"].sum() == total_seats, "Seat count mismatch after partition"
    assert set(df["seat_count"].unique()).issubset({1, 2, 3, 4, 5, 6, 7}), \
        f"Unexpected district sizes: {set(df['seat_count'].unique())}"
    assert df["seat_count"].min() >= 1, "Seat count below 1"

    print(f"  States:     {df['state_fips'].nunique()}")
    print(f"  Districts:  {len(df)}")
    print(f"  Total seats: {total_seats}")
    print(f"  District size distribution:")
    for sz, cnt in sorted(df["seat_count"].value_counts().items()):
        print(f"    {sz}-seat: {cnt} districts")
    print(f"  Density tier distribution:")
    for tier, cnt in df["density_tier"].value_counts().items():
        print(f"    {tier}: {cnt} districts ({cnt/len(df)*100:.1f}%)")

    return df


if __name__ == "__main__":
    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("=" * 60)
    print("STEP 1: DISTRICT APPORTIONMENT")
    print("=" * 60)
    apportionment = run_apportionment()
    out_path = OUTPUT_DIR / "district_apportionment.csv"
    apportionment.to_csv(out_path, index=False)
    print(f"\n  Saved: {out_path}")
    print(apportionment.head(10).to_string(index=False))

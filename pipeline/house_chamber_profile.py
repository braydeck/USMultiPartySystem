#!/usr/bin/env python3
"""
house_chamber_profile.py
-------------------------
Produces seat-weighted policy and demographic profiles for three House of
Representatives simulation scenarios, in the same format as blend_stats.csv.

House winners are pure party clusters (0–9), so profiles come directly from
cluster_stats.csv columns c0–c9.

Sources
-------
  cluster_stats.csv                       - pure cluster profiles (c0–c9)
  baseline/stv_seat_summary.csv           - baseline seat counts (party + NATIONAL)
  no_C2/stv_seat_summary.csv              - no-C2 scenario seat counts
  No_C7_canonical/stv_seat_summary.csv    - no-C7 scenario seat counts

Output
------
  Claude/outputs/house_chamber_profile.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path

BASE        = Path(__file__).parent.parent
PROFILE_DIR = BASE / "data" / "outputs" / "profiles"
OUT_DIR     = BASE / "data" / "outputs"

# Cluster index → label mapping
CLUSTER_NAMES = {
    0: "CON", 1: "LBR",  2: "STY", 3: "NAT", 4: "LIB",
    5: "POP", 6: "CUP", 7: "OAO",  8: "DSA", 9: "PRG",
}

TYPE_COLS = [CLUSTER_NAMES[i] for i in range(10)]

META_COLS = ["variable", "domain", "type", "stat_label", "question", "overall"]

# Canonical scenario: C7 (Blue Dogs) pre-dissolved, all other parties active
SCENARIOS = [
    ("house_chamber", "No_C7_canonical"),
]


def load_seat_counts(summary_path: Path) -> dict:
    """Read stv_seat_summary.csv and return {cluster_int: seats} mapping."""
    df = pd.read_csv(summary_path)
    return dict(zip(df["party"].astype(int), df["NATIONAL"].astype(int)))


def weighted_avg(type_profiles: dict, seats: dict) -> pd.Series:
    """
    Seat-weighted average across all clusters with non-zero seats.
    type_profiles: {type_label: Series}
    seats:         {cluster_int: int}
    """
    total = sum(seats.values())
    if total == 0:
        return pd.Series(np.nan, index=next(iter(type_profiles.values())).index)
    result = sum(
        seats[i] * type_profiles[CLUSTER_NAMES[i]]
        for i in seats
        if seats[i] > 0
    )
    return (result / total).round(4)


def main():
    # ── Load cluster profiles ───────────────────────────────────────────────
    cluster = pd.read_csv(PROFILE_DIR / "cluster_stats.csv")
    print(f"cluster_stats: {len(cluster)} rows")

    # ── Build type profile DataFrame ────────────────────────────────────────
    out = cluster[META_COLS].copy()

    for i, label in CLUSTER_NAMES.items():
        out[label] = cluster[f"c{i}"].round(4)

    type_profiles = {label: out[label] for label in TYPE_COLS}

    # ── Load seat counts and compute chamber aggregates ─────────────────────
    agg_cols = []
    for col_name, subdir in SCENARIOS:
        path = OUT_DIR / subdir / "stv_seat_summary.csv"
        seats = load_seat_counts(path)
        total = sum(seats.values())
        print(f"\n{col_name}: {total} seats")
        for i in range(10):
            s = seats.get(i, 0)
            if s > 0:
                print(f"  {CLUSTER_NAMES[i]:<6} {s:>4} ({100*s/total:.1f}%)")

        out[col_name] = weighted_avg(type_profiles, seats)
        agg_cols.append(col_name)

    # ── Assemble final columns ──────────────────────────────────────────────
    out = out[META_COLS + TYPE_COLS + agg_cols]

    # ── Save ────────────────────────────────────────────────────────────────
    out_path = OUT_DIR / "house_chamber_profile.csv"
    out.to_csv(out_path, index=False)
    print(f"\nSaved {len(out)} rows × {len(out.columns)} cols → {out_path}")

    # ── Spot-check ──────────────────────────────────────────────────────────
    ideo = out[out["variable"] == "ideo5"] if "ideo5" in out["variable"].values else out.head(1)
    if not ideo.empty:
        row = ideo.iloc[0]
        c0_val = cluster.loc[cluster["variable"] == row["variable"], "c0"]
        if not c0_val.empty:
            match = "✓" if abs(row["CON"] - c0_val.iloc[0]) < 0.001 else "✗"
            print(f"\nSpot-check CON == c0 for '{row['variable']}': "
                  f"CON={row['CON']:.4f}  c0={c0_val.iloc[0]:.4f}  {match}")

        print(f"Chamber ideo5 (canonical): {row['house_chamber']:.3f}")

    print("\n✓ Done.")


if __name__ == "__main__":
    main()

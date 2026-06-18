#!/usr/bin/env python3
"""
senate_chamber_profile.py
--------------------------
Produces seat-weighted policy and demographic profiles for the simulated senate,
in the same format as blend_stats.csv.

Sources
-------
  blend_stats.csv          - existing profiles for 12 blended senate types
  cluster_stats.csv        - source for 4 pure types + 3 new senate-only blends
  senate_composition.csv   - Condorcet seat counts (senator_label)
  senate_irv_composition.csv - IRV seat counts (winner_label)
  senate_voting_blocs.csv  - 4-bloc assignments per scenario

Output
------
  Claude/outputs/senate/senate_chamber_profile.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path

BASE        = Path(__file__).parent.parent
PROFILE_DIR = BASE / "data" / "outputs" / "profiles"
SENATE_DIR  = BASE / "data" / "outputs" / "senate"

# ── Pure type columns: label → cluster_stats column ────────────────────────
PURE_TYPES = {
    "CON": "c0",
    "SD":  "c1",
    "STY": "c2",
    "POP": "c5",
    "CUP": "c6",
    "LIB": "c4",
}

# ── New senate blends not in blend_stats.csv ────────────────────────────────
# (label, primary_col, secondary_col, w_primary)
NEW_BLENDS = [
    ("CON/POP",  "c0", "c5", 0.6900),
    ("CON/NAT",  "c0", "c3", 0.5100),
    ("LIB/CUP",  "c4", "c6", 0.6000),
    ("POP/SD",   "c5", "c1", 0.5500),
    ("CUP/LIB",  "c6", "c4", 0.5000),
    ("PRG/DSA",  "c9", "c8", 0.7000),
]

# ── Existing blends to pull from blend_stats.csv ───────────────────────────
EXISTING_BLENDS = [
    "CON/CUP", "CON/SD", "CON/STY",
    "SD/STY",  "SD/CON", "SD/CUP", "SD/LIB",
    "STY/POP", "STY/SD", "STY/CON",
    "POP/STY",
]

# Column order for output
TYPE_COLS = (
    list(PURE_TYPES.keys()) +
    EXISTING_BLENDS +
    [label for label, *_ in NEW_BLENDS]
)

META_COLS = ["variable", "domain", "type", "stat_label", "question", "overall"]


def weighted_avg(profiles: dict, seats: dict) -> pd.Series:
    """
    Compute seat-weighted average across types present in both dicts.
    profiles: {type_label: Series of numeric values}
    seats:    {type_label: int}
    """
    total = sum(seats.get(t, 0) for t in profiles)
    if total == 0:
        return pd.Series(np.nan, index=next(iter(profiles.values())).index)
    result = sum(
        seats.get(t, 0) * profiles[t]
        for t in profiles
        if seats.get(t, 0) > 0
    )
    return (result / total).round(4)


def main():
    # ── Load base data ──────────────────────────────────────────────────────
    cluster = pd.read_csv(PROFILE_DIR / "cluster_stats.csv")
    blends  = pd.read_csv(PROFILE_DIR / "blend_stats.csv")

    print(f"cluster_stats: {len(cluster)} rows")
    print(f"blend_stats:   {len(blends)} rows")

    # ── Build type profiles DataFrame (same row index as cluster_stats) ─────
    out = cluster[META_COLS].copy()

    # Pure types
    for label, col in PURE_TYPES.items():
        out[label] = cluster[col].round(4)

    # Existing blends — pull directly from blend_stats
    for label in EXISTING_BLENDS:
        out[label] = blends[label]

    # New senate-only blends — compute from cluster_stats
    for label, pc, sc, wp in NEW_BLENDS:
        ws = 1.0 - wp
        out[label] = (wp * cluster[pc] + ws * cluster[sc]).round(4)

    # Dict of type → Series for weighted averaging
    type_profiles = {t: out[t] for t in TYPE_COLS}

    # ── Load seat counts ────────────────────────────────────────────────────
    cond_seats = (
        pd.read_csv(SENATE_DIR / "senate_composition.csv")["senator_label"]
        .value_counts()
        .to_dict()
    )
    irv_seats = (
        pd.read_csv(SENATE_DIR / "senate_irv_composition.csv")["winner_label"]
        .value_counts()
        .to_dict()
    )
    cond_pure_seats = (
        pd.read_csv(BASE / "data" / "outputs" / "pure_only" / "senate" / "senate_composition.csv")["senator_label"]
        .value_counts()
        .to_dict()
    )
    irv_pure_seats = (
        pd.read_csv(BASE / "data" / "outputs" / "pure_only" / "senate" / "senate_irv_composition.csv")["winner_label"]
        .value_counts()
        .to_dict()
    )

    cond_total = sum(cond_seats.values())
    irv_total  = sum(irv_seats.values())
    print(f"\nCondorcet mixed: {cond_total} senators across {len(cond_seats)} types")
    print(f"IRV mixed:       {irv_total} senators across {len(irv_seats)} types")
    print(f"Condorcet pure:  {sum(cond_pure_seats.values())} senators across {len(cond_pure_seats)} types")
    print(f"IRV pure:        {sum(irv_pure_seats.values())} senators across {len(irv_pure_seats)} types")

    # Warn on any type not covered
    for label, seats in cond_seats.items():
        if label not in TYPE_COLS:
            print(f"  ⚠ Condorcet type '{label}' ({seats} seats) not in TYPE_COLS")
    for label, seats in irv_seats.items():
        if label not in TYPE_COLS:
            print(f"  ⚠ IRV type '{label}' ({seats} seats) not in TYPE_COLS")

    # ── Chamber aggregates ──────────────────────────────────────────────────
    out["cond_chamber"]      = weighted_avg(type_profiles, cond_seats)
    out["irv_chamber"]       = weighted_avg(type_profiles, irv_seats)
    out["cond_pure_chamber"] = weighted_avg(type_profiles, cond_pure_seats)
    out["irv_pure_chamber"]  = weighted_avg(type_profiles, irv_pure_seats)

    # ── Voting bloc aggregates ──────────────────────────────────────────────
    blocs_df = pd.read_csv(SENATE_DIR / "senate_voting_blocs.csv")

    for scenario, seats_dict, prefix in [
        ("Condorcet", cond_seats, "cond"),
        ("IRV",       irv_seats,  "irv"),
    ]:
        subset = blocs_df[(blocs_df["scenario"] == scenario) &
                          (blocs_df["n_blocs"] == 4)]
        for _, row in subset.iterrows():
            b = int(row["bloc"])
            members = row["members"].split("|")
            bloc_seats = {m: seats_dict.get(m, 0) for m in members}
            bloc_profiles = {m: type_profiles[m] for m in members if m in type_profiles}
            col = f"{prefix}_bloc{b}"
            out[col] = weighted_avg(bloc_profiles, bloc_seats)

    # ── Assemble final column order ─────────────────────────────────────────
    agg_cols = (
        ["cond_chamber", "irv_chamber", "cond_pure_chamber", "irv_pure_chamber"] +
        [f"cond_bloc{b}" for b in range(1, 5)] +
        [f"irv_bloc{b}"  for b in range(1, 5)]
    )
    final_cols = META_COLS + TYPE_COLS + agg_cols
    out = out[final_cols]

    # ── Save ────────────────────────────────────────────────────────────────
    out_path = SENATE_DIR / "senate_chamber_profile.csv"
    out.to_csv(out_path, index=False)
    print(f"\nSaved {len(out)} rows × {len(out.columns)} cols → {out_path}")

    # ── Spot-checks ─────────────────────────────────────────────────────────
    # CON should equal c0
    check = out[out["variable"] == "ideo5"] if "ideo5" in out["variable"].values else out.head(1)
    if not check.empty:
        row = check.iloc[0]
        c0_val = cluster.loc[cluster["variable"] == row["variable"], "c0"]
        if not c0_val.empty:
            match = "✓" if abs(row["CON"] - c0_val.iloc[0]) < 0.001 else "✗"
            print(f"\nSpot-check CON == c0 for '{row['variable']}': "
                  f"CON={row['CON']:.4f}  c0={c0_val.iloc[0]:.4f}  {match}")

        print(f"\nChamber ideo5 (Condorcet mixed): {row['cond_chamber']:.3f}")
        print(f"Chamber ideo5 (IRV mixed):       {row['irv_chamber']:.3f}")
        print(f"Chamber ideo5 (Condorcet pure):  {row['cond_pure_chamber']:.3f}")
        print(f"Chamber ideo5 (IRV pure):         {row['irv_pure_chamber']:.3f}")

    print("\n✓ Done.")


if __name__ == "__main__":
    main()

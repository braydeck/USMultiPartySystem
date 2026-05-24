#!/usr/bin/env python3
"""
generate_fd_chamber_profile.py
--------------------------------
Produces seat-weighted policy profiles for the FD senate + house chambers.

Sources:
  factor_deviation_stats.csv          — 285-row × 71-candidate item stats
  factor_deviation/senate/senate_composition.csv      — Condorcet senate
  factor_deviation/senate/senate_irv_composition.csv  — IRV senate
  factor_deviation/house/stv_seat_summary.csv         — House seat counts

Output:
  data/outputs/factor_deviation/profiles/factor_deviation_chamber_profile.csv
  - 285 rows (same item structure as cluster_stats.csv)
  - 71 candidate columns (from factor_deviation_stats.csv)
  - 3 chamber aggregate columns: fd_senate_condorcet, fd_senate_irv, fd_house
  - 4 factor_sensitive_* flag columns
"""

import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR      = Path(__file__).parent.parent
FD_DIR        = BASE_DIR / "data" / "outputs" / "factor_deviation"
FD_STATS      = FD_DIR / "profiles" / "factor_deviation_stats.csv"
SENATE_COND   = FD_DIR / "senate" / "senate_composition.csv"
SENATE_IRV    = FD_DIR / "senate" / "senate_irv_composition.csv"
HOUSE_SUMMARY = FD_DIR / "house" / "stv_seat_summary.csv"
OUT_PATH      = FD_DIR / "profiles" / "factor_deviation_chamber_profile.csv"

META_COLS = ["variable", "domain", "type", "stat_label", "question", "overall"]
FLAG_COLS = ["factor_sensitive_so", "factor_sensitive_ae",
             "factor_sensitive_rt", "factor_sensitive_pc"]


def seat_weighted_avg(stats_df: pd.DataFrame,
                      seat_counts: dict,
                      cand_codes: list) -> pd.Series:
    """
    Seat-weighted average of candidate stat columns.

    seat_counts: {candidate_code: n_seats}
    Returns a Series aligned to stats_df's index.
    """
    elected_codes = [c for c in cand_codes if seat_counts.get(c, 0) > 0]
    total_seats   = sum(seat_counts.get(c, 0) for c in elected_codes)

    if total_seats == 0 or not elected_codes:
        return pd.Series(np.nan, index=stats_df.index)

    result = pd.Series(0.0, index=stats_df.index)
    for code in elected_codes:
        n = seat_counts[code]
        col_vals = pd.to_numeric(stats_df[code], errors="coerce")
        result = result + n * col_vals.fillna(0)

    # Restore NaN where all contributing candidates had NaN
    all_nan_mask = pd.concat(
        [pd.to_numeric(stats_df[c], errors="coerce").isna() for c in elected_codes],
        axis=1,
    ).all(axis=1)
    result[all_nan_mask] = np.nan

    return result / total_seats


def main():
    sep  = "=" * 70
    thin = "-" * 70

    print(sep)
    print("FD CHAMBER PROFILE")
    print(sep)

    # ── Load base stats ────────────────────────────────────────────────────────
    print("\nLoading factor deviation stats…")
    stats_df  = pd.read_csv(FD_STATS)
    cand_cols = [c for c in stats_df.columns
                 if c not in META_COLS + FLAG_COLS]
    print(f"  {len(stats_df)} rows × {len(cand_cols)} candidate columns")

    # ── Senate Condorcet seat counts ──────────────────────────────────────────
    print("Loading senate Condorcet composition…")
    cond_df    = pd.read_csv(SENATE_COND)
    cond_seats = cond_df["senator_code"].value_counts().to_dict()
    total_cond = sum(cond_seats.values())
    print(f"  {total_cond} seats across {len(cond_seats)} candidates:")
    for code, n in sorted(cond_seats.items(), key=lambda x: -x[1]):
        print(f"    {code:<22}  {n} seats")

    # ── Senate IRV seat counts ─────────────────────────────────────────────────
    print("Loading senate IRV composition…")
    irv_df    = pd.read_csv(SENATE_IRV)
    irv_seats = irv_df["senator_code"].value_counts().to_dict()
    total_irv = sum(irv_seats.values())
    print(f"  {total_irv} seats across {len(irv_seats)} candidates")

    # ── House seat counts ─────────────────────────────────────────────────────
    print("Loading house seat summary…")
    house_df   = pd.read_csv(HOUSE_SUMMARY)
    house_seats = dict(zip(house_df["candidate_code"], house_df["NATIONAL"]))
    total_house = sum(house_seats.values())
    print(f"  {int(total_house)} seats across {len(house_seats)} candidates")

    # ── Compute chamber aggregates ────────────────────────────────────────────
    print(f"\n{thin}")
    print("Computing seat-weighted chamber profiles…")

    cond_profile = seat_weighted_avg(stats_df, cond_seats, cand_cols)
    irv_profile  = seat_weighted_avg(stats_df, irv_seats,  cand_cols)
    house_profile = seat_weighted_avg(stats_df, house_seats, cand_cols)

    print(f"  Senate Condorcet: {total_cond} total seats")
    print(f"  Senate IRV:       {total_irv} total seats")
    print(f"  House:            {int(total_house)} total seats")

    # ── Assemble output ───────────────────────────────────────────────────────
    out_df = stats_df.copy()
    out_df["fd_senate_condorcet"] = cond_profile.values
    out_df["fd_senate_irv"]       = irv_profile.values
    out_df["fd_house"]            = house_profile.values

    out_df.to_csv(OUT_PATH, index=False)
    print(f"\nWrote {len(out_df)} rows × {len(out_df.columns)} cols → {OUT_PATH.relative_to(BASE_DIR)}")

    # ── Spot check: show a few items where chamber profile differs from pure base ──
    print(f"\n{thin}")
    print("SAMPLE: Chamber profile vs. base party candidates (border patrols, election fairness)")
    print(thin)

    sample_vars = ["CC24_323b", "CC24_421_2", "CC24_325", "CC24_341c"]
    for var in sample_vars:
        sub = out_df[out_df["variable"] == var]
        if sub.empty:
            continue
        row = sub.iloc[0]
        print(f"\n  {var} — {row['stat_label']} — {row['question'][:55]}")
        print(f"    {'Overall':>22}  {row['overall']:.2f}")
        for code in sorted(cond_seats.keys(), key=lambda c: -cond_seats[c])[:5]:
            if code in out_df.columns:
                print(f"    {code:>22}  {row[code]:.2f}  [{cond_seats[code]} seats]")
        print(f"    {'fd_senate_condorcet':>22}  {row['fd_senate_condorcet']:.2f}  [chamber avg]")
        print(f"    {'fd_house':>22}  {row['fd_house']:.2f}  [chamber avg]")

    print(f"\n{sep}")
    print("FD chamber profile complete.")
    print(sep)


if __name__ == "__main__":
    main()

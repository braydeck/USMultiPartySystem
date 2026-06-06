"""
stv_step5.py
------------
Seat count summary by cluster, nationally and by density tier.

Output: stv_seat_summary.csv
Columns: party, party_name, NATIONAL, URBAN, SUBURBAN, RURAL,
         pct_national, pct_urban, pct_suburban, pct_rural
"""

import pandas as pd
from stv_config import OUTPUT_DIR, PARTY_LABELS, N_PARTIES


def build_seat_summary(all_results: list) -> pd.DataFrame:
    """
    Tally seats won per cluster nationally and by density tier.

    Returns a pivot DataFrame with rows = party (0..9) and columns for
    each tier plus NATIONAL, with both count and % columns.
    """
    # Flatten to one row per elected seat
    records = []
    for result in all_results:
        for party_idx in result.get("elected", []):
            records.append({
                "party":        int(party_idx),
                "density_tier": result["density_tier"],
                "district_id":  result["district_id"],
                "state_fips":   result["state_fips"],
            })

    if not records:
        print("  WARNING: No elected seats found — empty summary")
        return pd.DataFrame()

    df = pd.DataFrame(records)

    # Count seats by party × tier
    by_tier = (
        df.groupby(["party", "density_tier"])
        .size()
        .reset_index(name="seats")
        .pivot(index="party", columns="density_tier", values="seats")
        .fillna(0)
        .astype(int)
    )

    # Ensure all tier columns exist
    for tier in ["URBAN", "SUBURBAN", "RURAL"]:
        if tier not in by_tier.columns:
            by_tier[tier] = 0

    by_tier = by_tier[["URBAN", "SUBURBAN", "RURAL"]]

    # National totals
    by_tier["NATIONAL"] = by_tier["URBAN"] + by_tier["SUBURBAN"] + by_tier["RURAL"]

    # Ensure all 10 parties appear (even those with 0 seats)
    by_tier = by_tier.reindex(range(N_PARTIES), fill_value=0)
    by_tier.index.name = "party"
    by_tier = by_tier.reset_index()

    # Add party names
    by_tier.insert(1, "party_name", by_tier["party"].map(PARTY_LABELS))

    # Add percentage columns
    n_national = by_tier["NATIONAL"].sum()
    n_urban    = by_tier["URBAN"].sum()
    n_suburban = by_tier["SUBURBAN"].sum()
    n_rural    = by_tier["RURAL"].sum()

    by_tier["pct_national"] = (by_tier["NATIONAL"] / n_national * 100).round(2) if n_national else 0.0
    by_tier["pct_urban"]    = (by_tier["URBAN"]    / n_urban    * 100).round(2) if n_urban    else 0.0
    by_tier["pct_suburban"] = (by_tier["SUBURBAN"] / n_suburban * 100).round(2) if n_suburban else 0.0
    by_tier["pct_rural"]    = (by_tier["RURAL"]    / n_rural    * 100).round(2) if n_rural    else 0.0

    # Sort by national seats descending
    by_tier = by_tier.sort_values("NATIONAL", ascending=False).reset_index(drop=True)

    return by_tier


def print_seat_summary(df: pd.DataFrame) -> None:
    """Print a formatted seat summary table."""
    total_nat  = df["NATIONAL"].sum()
    total_urb  = df["URBAN"].sum()
    total_sub  = df["SUBURBAN"].sum()
    total_rur  = df["RURAL"].sum()

    print(f"\n  {'Party':<28} {'Natl':>5} {'%':>6}  {'Urban':>5} {'%':>6}  "
          f"{'Suburb':>6} {'%':>6}  {'Rural':>5} {'%':>6}")
    print("  " + "-" * 85)
    for _, row in df.iterrows():
        print(
            f"  C{row['party']} {row['party_name']:<26}"
            f" {row['NATIONAL']:>5}  {row['pct_national']:>5.1f}%"
            f"  {row['URBAN']:>5}  {row['pct_urban']:>5.1f}%"
            f"  {row['SUBURBAN']:>6}  {row['pct_suburban']:>5.1f}%"
            f"  {row['RURAL']:>5}  {row['pct_rural']:>5.1f}%"
        )
    print("  " + "-" * 85)
    print(
        f"  {'TOTAL':<28}"
        f" {total_nat:>5}  {'100.0':>5}%"
        f"  {total_urb:>5}  {'100.0':>5}%"
        f"  {total_sub:>6}  {'100.0':>5}%"
        f"  {total_rur:>5}  {'100.0':>5}%"
    )


if __name__ == "__main__":
    import os
    from stv_step1 import run_apportionment
    from stv_step2 import load_and_prepare
    from stv_step3 import run_all_districts

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Running Steps 1-5 (standalone)...")

    apportionment = run_apportionment()
    df            = load_and_prepare(apportionment)
    all_results   = run_all_districts(df, apportionment)

    print("\n" + "=" * 60)
    print("STEP 5: SEAT SUMMARY")
    print("=" * 60)
    summary = build_seat_summary(all_results)
    print_seat_summary(summary)

    out_path = OUTPUT_DIR / "stv_seat_summary.csv"
    summary.to_csv(out_path, index=False)
    print(f"\n  Saved: {out_path}")

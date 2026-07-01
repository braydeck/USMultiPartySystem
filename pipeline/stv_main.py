"""
stv_main.py
-----------
Orchestrator for the 10-party STV simulation (Steps 1-5).

Usage:
    python stv_main.py              # run all steps
    python stv_main.py --steps 1    # run only Step 1
    python stv_main.py --steps 3,4,5  # resume from Step 3 (requires Step 1+2 outputs)

Outputs (all to /Users/bdecker/Documents/STV/Claude/stv_outputs/):
    district_apportionment.csv
    stv_results_by_district.csv
    transfer_matrix_10party.csv
    transfer_matrix_directed.csv
    stv_seat_summary.csv

Also saves transfer_asymmetry_report.csv as a bonus diagnostic.
"""

import argparse
import os
import sys
import time
import pandas as pd
import numpy as np

from stv_config import OUTPUT_DIR, DISSOLVED_PARTIES


def parse_args():
    parser = argparse.ArgumentParser(
        description="10-party STV simulation using CES 2024 DPGMM cluster assignments"
    )
    parser.add_argument(
        "--steps",
        default="1,2,3,4,5",
        help="Comma-separated steps to run (default: 1,2,3,4,5). "
             "Steps 3-5 require steps 1-2 to have been run first.",
    )
    return parser.parse_args()


def main():
    args   = parse_args()
    steps  = [int(s.strip()) for s in args.steps.split(",")]
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 65)
    print("10-PARTY STV SIMULATION")
    print(f"Running steps: {steps}")
    print("=" * 65)

    t_start = time.time()
    apportionment = None
    df            = None
    all_results   = None

    # ── STEP 1: District apportionment ───────────────────────────────────────
    if 1 in steps:
        from stv_step1 import run_apportionment
        t0 = time.time()
        print(f"\n{'─'*65}")
        print("STEP 1: DISTRICT APPORTIONMENT")
        print(f"{'─'*65}")
        apportionment = run_apportionment()
        out_path = OUTPUT_DIR / "district_apportionment.csv"
        apportionment.to_csv(out_path, index=False)
        print(f"\n  ✓ Saved: {out_path}  [{time.time()-t0:.1f}s]")
    else:
        ap_path = OUTPUT_DIR / "district_apportionment.csv"
        if not ap_path.exists():
            sys.exit(f"ERROR: {ap_path} not found — run Step 1 first.")
        apportionment = pd.read_csv(ap_path)
        print(f"\n  Loaded apportionment: {len(apportionment)} districts")

    # ── STEP 2: Ballot generation ─────────────────────────────────────────────
    if 2 in steps:
        from stv_step2 import load_and_prepare
        t0 = time.time()
        print(f"\n{'─'*65}")
        print("STEP 2: BALLOT GENERATION")
        print(f"{'─'*65}")
        df = load_and_prepare(apportionment)
        print(f"\n  ✓ {len(df):,} respondents with ranked ballots  [{time.time()-t0:.1f}s]")
    elif any(s in steps for s in [3, 4, 5]):
        # Steps 3+ need the ballot dataframe — must have run Step 2
        # (We reload from a parquet checkpoint if available)
        parquet_path = OUTPUT_DIR / "ballots_checkpoint.parquet"
        if parquet_path.exists():
            print(f"\n  Loading ballot checkpoint from {parquet_path}...")
            df = pd.read_parquet(parquet_path)
            # Restore ballot column from stored list-of-lists
            if "ballot" not in df.columns:
                sys.exit("ERROR: ballot column not found in checkpoint parquet.")
        else:
            sys.exit(
                f"ERROR: Ballot checkpoint not found at {parquet_path}.\n"
                f"       Run Step 2 first, or include step 2 in --steps."
            )

    # Optionally save ballot checkpoint for resumption
    if 2 in steps and df is not None:
        try:
            # Store ballots as list column — parquet handles object arrays
            parquet_path = OUTPUT_DIR / "ballots_checkpoint.parquet"
            # Convert ballot from numpy arrays to lists for parquet compat
            df_save = df.copy()
            df_save["ballot"] = df_save["ballot"].apply(
                lambda b: b.tolist() if hasattr(b, "tolist") else list(b)
            )
            df_save.to_parquet(parquet_path, index=False)
            print(f"  ✓ Ballot checkpoint saved: {parquet_path}")
        except Exception as e:
            print(f"  (Ballot checkpoint save failed: {e} — continuing)")

    # Restore ballot arrays from list if loaded from parquet
    if df is not None and 2 not in steps:
        df["ballot"] = df["ballot"].apply(
            lambda b: np.array(b, dtype=np.int8)
        )

    # ── STEP 3: STV per district ──────────────────────────────────────────────
    if 3 in steps:
        from stv_step3 import run_all_districts, results_to_dataframe
        t0 = time.time()
        print(f"\n{'─'*65}")
        print("STEP 3: STV PER DISTRICT")
        print(f"{'─'*65}")
        all_results = run_all_districts(df, apportionment, pre_dissolved=DISSOLVED_PARTIES)

        df_results = results_to_dataframe(all_results)
        out_path   = OUTPUT_DIR / "stv_results_by_district.csv"
        df_results.to_csv(out_path, index=False)

        total_filled = sum(len(r["elected"]) for r in all_results)
        total_avail  = apportionment["seat_count"].sum()
        print(f"\n  ✓ Seats filled: {total_filled} / {total_avail}  [{time.time()-t0:.1f}s]")
        print(f"  ✓ Saved: {out_path}")

    # ── STEP 4: Transfer matrices ─────────────────────────────────────────────
    if 4 in steps:
        from stv_step4 import (
            build_transfer_matrices, save_transfer_matrices,
            build_directed_asymmetry_report,
        )
        t0 = time.time()
        print(f"\n{'─'*65}")
        print("STEP 4: TRANSFER MATRICES")
        print(f"{'─'*65}")

        if all_results is None:
            sys.exit("ERROR: Step 4 requires Step 3 results. Include step 3 in --steps.")

        dir_pct, sym_pct, raw = build_transfer_matrices(all_results)
        save_transfer_matrices(dir_pct, sym_pct, raw)

        # Bonus: asymmetry report
        asym = build_directed_asymmetry_report(dir_pct)
        out_asym = OUTPUT_DIR / "transfer_asymmetry_report.csv"
        asym.to_csv(out_asym, index=False)
        print(f"  ✓ Asymmetry report: {out_asym}  [{time.time()-t0:.1f}s]")

    # ── STEP 5: Seat summary ──────────────────────────────────────────────────
    if 5 in steps:
        from stv_step5 import build_seat_summary, print_seat_summary
        t0 = time.time()
        print(f"\n{'─'*65}")
        print("STEP 5: SEAT SUMMARY")
        print(f"{'─'*65}")

        if all_results is None:
            sys.exit("ERROR: Step 5 requires Step 3 results. Include step 3 in --steps.")

        summary = build_seat_summary(all_results)
        print_seat_summary(summary)

        out_path = OUTPUT_DIR / "stv_seat_summary.csv"
        summary.to_csv(out_path, index=False)
        print(f"\n  ✓ Saved: {out_path}  [{time.time()-t0:.1f}s]")

    # ── Final summary ─────────────────────────────────────────────────────────
    elapsed = time.time() - t_start
    print(f"\n{'='*65}")
    print(f"SIMULATION COMPLETE  ({elapsed:.1f}s total)")
    print(f"Outputs in: {OUTPUT_DIR}")
    print(f"{'='*65}")

    if 1 in steps and 3 in steps and 5 in steps:
        # Final verification: seat totals should match
        total_apport = apportionment["seat_count"].sum()
        total_filled = sum(len(r["elected"]) for r in all_results)
        if total_apport != total_filled:
            print(f"\n  NOTE: Apportionment seats = {total_apport}, "
                  f"seats filled = {total_filled} "
                  f"(difference due to empty districts)")


if __name__ == "__main__":
    main()

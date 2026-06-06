"""
stv_scenarios.py
----------------
Run dissolution scenarios and compare against the baseline.

Scenarios
---------
  Baseline  : all 10 parties (already computed — loaded from outputs/)
  Scenario A : dissolve C7 (Blue Dogs) only
  Scenario B : dissolve C7 (Blue Dogs) + C2 (Solidarity)

"Dissolving" a party means pre-eliminating them at the start of every district's
STV run. Their voters' weights flow immediately to the next-ranked active party,
exactly as if that party had been the first eliminated in every race.

Outputs (each scenario gets its own subdirectory under Claude/outputs/):
  Claude/outputs/scenario_a/
    district_apportionment.csv          (copied — unchanged from baseline)
    stv_results_by_district.csv
    transfer_matrix_10party.csv
    transfer_matrix_directed.csv
    stv_seat_summary.csv
  Claude/outputs/scenario_b/
    (same set)

  Claude/outputs/scenario_comparison.csv  — side-by-side seat counts + deltas
"""

import os
import shutil
import time
import numpy as np
import pandas as pd

from stv_config import OUTPUT_DIR, SCENARIOS_ROOT, PARTY_LABELS, N_PARTIES
from stv_step3  import run_all_districts, results_to_dataframe
from stv_step4  import build_transfer_matrices, save_transfer_matrices
from stv_step5  import build_seat_summary, print_seat_summary


# ── Scenario definitions ──────────────────────────────────────────────────────

SCENARIOS = {
    "scenario_a": {
        "label":         "Scenario A — dissolve C7 (Blue Dogs)",
        "pre_dissolved": [7],
    },
    "scenario_b": {
        "label":         "Scenario B — dissolve C7 (Blue Dogs) + C2 (Solidarity)",
        "pre_dissolved": [7, 2],
    },
}


# ── Load checkpointed data ────────────────────────────────────────────────────

def load_checkpoints():
    """Load apportionment CSV and ballot parquet from baseline run."""
    ap_path  = OUTPUT_DIR / "district_apportionment.csv"
    pq_path  = OUTPUT_DIR / "ballots_checkpoint.parquet"

    if not ap_path.exists():
        raise FileNotFoundError(
            f"Apportionment not found: {ap_path}\n"
            f"Run stv_main.py first to generate baseline outputs."
        )
    if not pq_path.exists():
        raise FileNotFoundError(
            f"Ballot checkpoint not found: {pq_path}\n"
            f"Run stv_main.py first to generate baseline outputs."
        )

    print("  Loading apportionment...", end=" ")
    apportionment = pd.read_csv(ap_path)
    print(f"{len(apportionment)} districts")

    print("  Loading ballot checkpoint...", end=" ")
    df = pd.read_parquet(pq_path)
    # Restore numpy int8 ballot arrays from stored lists
    df["ballot"] = df["ballot"].apply(
        lambda b: np.array(b, dtype=np.int8)
    )
    print(f"{len(df):,} respondents")

    return apportionment, df


# ── Run one scenario ──────────────────────────────────────────────────────────

def run_scenario(
    name:          str,
    config:        dict,
    apportionment: pd.DataFrame,
    df:            pd.DataFrame,
) -> dict:
    """
    Run a full STV simulation with the specified pre_dissolved parties.
    Saves all outputs to SCENARIOS_ROOT / name /
    Returns the seat summary DataFrame for comparison.
    """
    label         = config["label"]
    pre_dissolved = config["pre_dissolved"]
    out_dir       = SCENARIOS_ROOT / name
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n{'─'*65}")
    print(label)
    print(f"  Pre-dissolved parties: {[f'C{p} {PARTY_LABELS[p]}' for p in pre_dissolved]}")
    print(f"{'─'*65}")

    t0 = time.time()

    # ── STV ──────────────────────────────────────────────────────────────────
    print("  Running STV per district...")
    all_results = run_all_districts(df, apportionment, pre_dissolved=pre_dissolved)

    df_results = results_to_dataframe(all_results)
    df_results.to_csv(out_dir / "stv_results_by_district.csv", index=False)

    seats_filled = sum(len(r["elected"]) for r in all_results)
    print(f"  Seats filled: {seats_filled}  [{time.time()-t0:.1f}s]")

    # ── Transfer matrices ─────────────────────────────────────────────────────
    dir_pct, sym_pct, raw = build_transfer_matrices(all_results)
    save_transfer_matrices(dir_pct, sym_pct, raw, output_dir=out_dir)

    # ── Seat summary ──────────────────────────────────────────────────────────
    summary = build_seat_summary(all_results)
    print_seat_summary(summary)
    summary.to_csv(out_dir / "stv_seat_summary.csv", index=False)

    # Copy apportionment (unchanged across scenarios)
    shutil.copy(OUTPUT_DIR / "district_apportionment.csv",
                out_dir / "district_apportionment.csv")

    print(f"  Saved to: {out_dir}")
    return summary


# ── Build comparison table ────────────────────────────────────────────────────

def build_comparison(baseline: pd.DataFrame,
                     summary_a: pd.DataFrame,
                     summary_b: pd.DataFrame) -> pd.DataFrame:
    """
    Produce a side-by-side comparison of national seat counts.
    Columns: party, party_name,
             base_seats, base_pct,
             scen_a_seats, scen_a_delta,
             scen_b_seats, scen_b_delta
    """
    def _extract(df):
        d = df.set_index("party")[["NATIONAL", "pct_national"]].copy()
        d.columns = ["seats", "pct"]
        return d

    b = _extract(baseline)
    a = _extract(summary_a)
    sb = _extract(summary_b)

    rows = []
    for k in range(N_PARTIES):
        b_seats  = int(b.loc[k, "seats"])  if k in b.index  else 0
        a_seats  = int(a.loc[k, "seats"])  if k in a.index  else 0
        sb_seats = int(sb.loc[k, "seats"]) if k in sb.index else 0

        b_pct    = float(b.loc[k, "pct"])   if k in b.index  else 0.0
        a_pct    = float(a.loc[k, "pct"])   if k in a.index  else 0.0
        sb_pct   = float(sb.loc[k, "pct"])  if k in sb.index else 0.0

        rows.append({
            "party":       k,
            "party_name":  PARTY_LABELS[k],
            "base_seats":  b_seats,
            "base_pct":    b_pct,
            "scen_a_seats": a_seats,
            "scen_a_delta": a_seats - b_seats,
            "scen_a_pct":   round(a_pct, 2),
            "scen_b_seats": sb_seats,
            "scen_b_delta": sb_seats - b_seats,
            "scen_b_pct":   round(sb_pct, 2),
        })

    return pd.DataFrame(rows)


def print_comparison(df: pd.DataFrame) -> None:
    total_base = df["base_seats"].sum()
    total_a    = df["scen_a_seats"].sum()
    total_b    = df["scen_b_seats"].sum()

    print(f"\n{'='*80}")
    print("SCENARIO COMPARISON — National Seat Counts")
    print(f"{'='*80}")
    print(f"  {'Party':<28}  {'Baseline':>8}  "
          f"{'Scen A':>7} {'Δ':>5}  "
          f"{'Scen B':>7} {'Δ':>5}")
    print(f"  {'':28}  {'(all 10)':>8}  "
          f"{'(−C7)':>7} {'':>5}  "
          f"{'(−C7,C2)':>8} {'':>5}")
    print("  " + "─" * 74)

    for _, row in df.iterrows():
        diss_a = " [dissolved]" if row["scen_a_seats"] == 0 and row["base_seats"] > 0 else ""
        diss_b = " [dissolved]" if row["scen_b_seats"] == 0 and row["base_seats"] > 0 else ""
        delta_a = f"{row['scen_a_delta']:+d}" if row["scen_a_delta"] != 0 else "  —"
        delta_b = f"{row['scen_b_delta']:+d}" if row["scen_b_delta"] != 0 else "  —"

        print(
            f"  C{row['party']} {row['party_name']:<26}"
            f"  {row['base_seats']:>5} ({row['base_pct']:>4.1f}%)"
            f"  {row['scen_a_seats']:>5} ({row['scen_a_pct']:>4.1f}%)"
            f"  {delta_a:>5}"
            f"  {row['scen_b_seats']:>5} ({row['scen_b_pct']:>4.1f}%)"
            f"  {delta_b:>5}"
            f"{diss_b or diss_a}"
        )

    print("  " + "─" * 74)
    print(
        f"  {'TOTAL':<28}"
        f"  {total_base:>5}          "
        f"  {total_a:>5}            "
        f"  {total_b:>5}"
    )
    print()
    print("  Scen A: Dissolve C7 (Blue Dogs) — 14 seats redistributed")
    print("  Scen B: Dissolve C7 + C2 (Solidarity) — 175 seats redistributed")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    t_start = time.time()

    print("=" * 65)
    print("STV DISSOLUTION SCENARIOS")
    print("=" * 65)

    # Load shared inputs
    print("\nLoading checkpointed baseline data...")
    apportionment, df = load_checkpoints()

    # Load baseline seat summary (already computed)
    baseline_path = OUTPUT_DIR / "stv_seat_summary.csv"
    if not baseline_path.exists():
        raise FileNotFoundError(f"Baseline seat summary not found: {baseline_path}")
    baseline = pd.read_csv(baseline_path)
    print(f"  Baseline loaded: {baseline['NATIONAL'].sum()} total seats")

    # Run scenarios
    summary_a = run_scenario("scenario_a", SCENARIOS["scenario_a"], apportionment, df)
    summary_b = run_scenario("scenario_b", SCENARIOS["scenario_b"], apportionment, df)

    # Comparison table
    comparison = build_comparison(baseline, summary_a, summary_b)
    print_comparison(comparison)

    out_path = SCENARIOS_ROOT / "scenario_comparison.csv"
    comparison.to_csv(out_path, index=False)
    print(f"\n  Comparison table saved: {out_path}")

    print(f"\n{'='*65}")
    print(f"SCENARIOS COMPLETE  ({time.time()-t_start:.1f}s total)")
    print(f"{'='*65}")


if __name__ == "__main__":
    main()

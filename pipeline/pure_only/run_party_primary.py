#!/usr/bin/env python3
"""
run_party_primary.py
--------------------
Presidential primary using 9 party slates with multi-seat STV.

Stages (each is a multi-seat STV with decreasing seat targets):
  1. Retail:  12 seats — determines initial slot allocation
  2. Pod A:    9 seats — among retail survivors
  3. Pod B:    7 seats — among Pod A survivors
  4. Pod C/D:  5 seats — final allocation (general election finalists)

At each stage, parties that win 0 seats are eliminated. Their votes
transfer to surviving parties in subsequent stages. Parties exceeding
multiple Droop quotas earn multiple "slots" (e.g., CON_1, CON_2).

Outputs to data/outputs/pure_multi/:
  primary_results_2028.csv          — stage-by-stage results
  primary_diagnostics_2028.csv      — per-stage vote shares and transfers
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR    = Path(__file__).parent.parent.parent
BALLOTS_PATH = BASE_DIR / "data" / "outputs" / "pure_multi" / "party_ballots.csv"
EFA_PATH    = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
OUTPUT_DIR  = BASE_DIR / "data" / "outputs" / "pure_multi"

sys.path.insert(0, str(Path(__file__).parent.parent))
from party_stv import run_multi_seat_stv, expand_slots, condorcet_matchups

PARTY_CODES = ["CON", "SD", "STY", "NAT", "LIB", "POP", "CUP", "DSA", "PRG"]
PARTY_IDX   = {code: i for i, code in enumerate(PARTY_CODES)}
N_PARTIES   = len(PARTY_CODES)

STAGES = [
    ("Initial_Slate", N_PARTIES),   # all 9 parties
    ("After_Retail",  12),
    ("After_Pod_A",    9),
    ("After_Pod_B",    7),
    ("After_Pod_BD",   5),
]


def load_ballots():
    """Load party ballots as (N, 9) int8 array of party indices."""
    df = pd.read_csv(BALLOTS_PATH, index_col=0)
    N = len(df)
    ballots = np.zeros((N, N_PARTIES), dtype=np.int8)
    for rank_k in range(N_PARTIES):
        col = f"rank_{rank_k + 1}"
        ballots[:, rank_k] = df[col].map(PARTY_IDX).values.astype(np.int8)
    return ballots


def main():
    print("=" * 70)
    print("PARTY PRIMARY — 9 parties, multi-seat STV")
    print("=" * 70)

    print("\nLoading ballots…")
    ballots = load_ballots()
    efa     = pd.read_csv(EFA_PATH)
    weights = efa["commonpostweight"].values.astype(np.float64)
    N = len(ballots)
    print(f"  {N:,} ballots loaded")

    surviving = set(range(N_PARTIES))
    stage_results = []
    diagnostics   = []

    for stage_idx, (stage_name, target_seats) in enumerate(STAGES):
        print(f"\n{'─'*60}")
        print(f"Stage: {stage_name}  (target: {target_seats} slots)")

        if stage_idx == 0:
            # Initial slate — just record vote shares
            totals = np.zeros(N_PARTIES)
            for i in range(N):
                for j in range(N_PARTIES):
                    p = int(ballots[i, j])
                    if p in surviving:
                        totals[p] += weights[i]
                        break

            total_w = totals.sum()
            slot_labels = list(PARTY_CODES)

            print(f"  {'Party':<6} {'Share':>7}")
            for p in sorted(surviving, key=lambda x: -totals[x]):
                code = PARTY_CODES[p]
                pct  = totals[p] / total_w * 100
                print(f"  {code:<6} {pct:>6.1f}%")

                stage_results.append({
                    "stage":        stage_name,
                    "candidate":    code,
                    "party":        code,
                    "vote_share":   round(pct, 2),
                    "status":       "surviving",
                    "n_slots":      1,
                })
                diagnostics.append({
                    "stage": stage_name, "candidate": code, "party": code,
                    "vote_pct": round(pct, 2), "status": "surviving",
                })
            continue

        # Run multi-seat STV among surviving parties
        # Filter ballots to surviving parties only (remap indices)
        surv_list = sorted(surviving)
        surv_map  = {old: new for new, old in enumerate(surv_list)}
        n_surv    = len(surv_list)

        filtered_ballots = np.full((N, n_surv), -1, dtype=np.int8)
        for i in range(N):
            rank = 0
            for j in range(N_PARTIES):
                p = int(ballots[i, j])
                if p in surv_map:
                    filtered_ballots[i, rank] = surv_map[p]
                    rank += 1

        result = run_multi_seat_stv(
            filtered_ballots, weights, n_surv,
            target_seats,
            party_codes=[PARTY_CODES[s] for s in surv_list],
        )

        seats = result["seats"]

        # Map back to global indices
        global_seats = {}
        for local_idx, n_seats in seats.items():
            global_idx = surv_list[local_idx]
            if n_seats > 0:
                global_seats[global_idx] = n_seats

        # Update surviving set
        eliminated_this = surviving - set(global_seats.keys())
        surviving = set(global_seats.keys())

        # Report
        slot_labels = expand_slots(
            {i: global_seats[i] for i in sorted(global_seats.keys())},
            PARTY_CODES
        )
        total_slots = sum(global_seats.values())

        print(f"  Quota: {result['quota']:.1f}")
        print(f"  {'Party':<6} {'Seats':>5}")
        for p in sorted(global_seats.keys(), key=lambda x: -global_seats[x]):
            code = PARTY_CODES[p]
            n    = global_seats[p]
            print(f"  {code:<6} {n:>5}")

        if eliminated_this:
            elim_codes = sorted(PARTY_CODES[p] for p in eliminated_this)
            print(f"  Eliminated: {', '.join(elim_codes)}")

        print(f"  Slots ({total_slots}): {', '.join(slot_labels)}")

        # Record results
        for p, n in global_seats.items():
            code = PARTY_CODES[p]
            if n == 1:
                stage_results.append({
                    "stage": stage_name, "candidate": code, "party": code,
                    "vote_share": 0, "status": "surviving", "n_slots": 1,
                })
            else:
                for k in range(1, n + 1):
                    stage_results.append({
                        "stage": stage_name, "candidate": f"{code}_{k}",
                        "party": code, "vote_share": 0,
                        "status": "surviving", "n_slots": n,
                    })

        for p in eliminated_this:
            code = PARTY_CODES[p]
            stage_results.append({
                "stage": stage_name, "candidate": code, "party": code,
                "vote_share": 0, "status": "eliminated_this_round", "n_slots": 0,
            })

    # ── Ranked Pairs among finalists ──────────────────────────────────────────
    print(f"\n{'─'*60}")
    finalist_list = sorted(surviving)
    finalist_codes = [PARTY_CODES[p] for p in finalist_list]
    print(f"Running Ranked Pairs among {len(finalist_list)} finalists: {', '.join(finalist_codes)}")

    # Filter ballots to finalists
    fin_map = {old: new for new, old in enumerate(finalist_list)}
    n_fin   = len(finalist_list)
    fin_ballots = np.full((N, n_fin), -1, dtype=np.int8)
    for i in range(N):
        rank = 0
        for j in range(N_PARTIES):
            p = int(ballots[i, j])
            if p in fin_map:
                fin_ballots[i, rank] = fin_map[p]
                rank += 1

    cond = condorcet_matchups(fin_ballots, weights, list(range(n_fin)), finalist_codes)

    if cond["winner"] is not None:
        winner_code = finalist_codes[cond["winner"]]
        print(f"  Ranked Pairs winner: {winner_code}")
    else:
        print("  No Condorcet winner (cycle)")
        winner_code = "none"

    # ── Save outputs ─────────────────────────────────────────────────────────
    results_df = pd.DataFrame(stage_results)
    results_df.to_csv(OUTPUT_DIR / "primary_results_2028.csv", index=False)

    diag_df = pd.DataFrame(diagnostics) if diagnostics else pd.DataFrame()
    diag_df.to_csv(OUTPUT_DIR / "primary_diagnostics_2028.csv", index=False)

    print(f"\nSaved primary_results_2028.csv  ({len(results_df)} rows)")
    print(f"Saved primary_diagnostics_2028.csv")

    # Final slots
    final_seats = {p: global_seats.get(p, 0) for p in surviving}
    final_slots = expand_slots(
        {i: final_seats[i] for i in sorted(final_seats.keys())},
        PARTY_CODES
    )
    print(f"\n{'='*70}")
    print(f"Party primary complete.")
    print(f"  Finalists:          {', '.join(final_slots)}")
    print(f"  Finalist parties:   {', '.join(finalist_codes)}")
    print(f"  Ranked Pairs winner: {winner_code}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()

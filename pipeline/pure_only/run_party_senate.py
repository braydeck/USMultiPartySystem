#!/usr/bin/env python3
"""
run_party_senate.py
-------------------
Senate election using 9 party slates per state.

Per state:
  1. Multi-seat STV (5 seats) determines finalist parties
  2. Condorcet (Ranked Pairs) among finalists → 1 senator
  3. IRV among finalists → 1 senator (alternative method)

Outputs to data/outputs/pure_multi/senate/:
  senate_composition.csv          — Condorcet winner per state
  senate_irv_composition.csv      — IRV winner per state
  senate_condorcet_results.csv    — pairwise matchup details
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict

BASE_DIR     = Path(__file__).parent.parent.parent
BALLOTS_PATH = BASE_DIR / "data" / "outputs" / "pure_multi" / "party_ballots.csv"
EFA_PATH     = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
TYPOLOGY     = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
OUTPUT_DIR   = BASE_DIR / "data" / "outputs" / "pure_multi" / "senate"

sys.path.insert(0, str(Path(__file__).parent.parent))
from party_stv import run_multi_seat_stv, run_irv, condorcet_matchups

PARTY_CODES = ["CON", "LBR", "STY", "NAT", "LIB", "POP", "CUP", "DSA", "PRG"]
PARTY_IDX   = {c: i for i, c in enumerate(PARTY_CODES)}
CLUSTER_FOR_PARTY = {"CON":0,"LBR":1,"STY":2,"NAT":3,"LIB":4,"POP":5,"CUP":6,"DSA":8,"PRG":9}
N_PARTIES   = len(PARTY_CODES)
STV_SEATS   = 5   # finalists per state

FIPS_TO_ABBR = {
     1:"AL",  2:"AK",  4:"AZ",  5:"AR",  6:"CA",  8:"CO",  9:"CT",
    10:"DE", 11:"DC", 12:"FL", 13:"GA", 15:"HI", 16:"ID", 17:"IL",
    18:"IN", 19:"IA", 20:"KS", 21:"KY", 22:"LA", 23:"ME", 24:"MD",
    25:"MA", 26:"MI", 27:"MN", 28:"MS", 29:"MO", 30:"MT", 31:"NE",
    32:"NV", 33:"NH", 34:"NJ", 35:"NM", 36:"NY", 37:"NC", 38:"ND",
    39:"OH", 40:"OK", 41:"OR", 42:"PA", 44:"RI", 45:"SC", 46:"SD",
    47:"TN", 48:"TX", 49:"UT", 50:"VT", 51:"VA", 53:"WA", 54:"WV",
    55:"WI", 56:"WY",
}


def load_ballots():
    df = pd.read_csv(BALLOTS_PATH, index_col=0)
    N  = len(df)
    ballots = np.zeros((N, N_PARTIES), dtype=np.int8)
    for k in range(N_PARTIES):
        ballots[:, k] = df[f"rank_{k+1}"].map(PARTY_IDX).values.astype(np.int8)
    return ballots


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("PARTY SENATE — 9 parties per state, STV → Condorcet/IRV")
    print("=" * 70)

    print("\nLoading data…")
    ballots    = load_ballots()
    efa        = pd.read_csv(EFA_PATH)
    weights    = efa["commonpostweight"].values.astype(np.float64)
    inputstate = efa["inputstate"].values.astype(int)
    N = len(ballots)
    print(f"  {N:,} voters")

    unique_states = sorted(set(inputstate) & set(FIPS_TO_ABBR.keys()))
    print(f"  {len(unique_states)} states")

    cond_rows    = []
    irv_rows     = []
    all_matchups = []

    print(f"\n  {'St':<4} {'N':>5}  {'Finalists':<40}  {'Cond':>6}  {'IRV':>6}")
    print(f"  {'-'*70}")

    for fips in unique_states:
        mask = inputstate == fips
        if mask.sum() < 5:
            continue

        abbr          = FIPS_TO_ABBR[fips]
        state_ballots = ballots[mask]
        state_weights = weights[mask]
        n_state       = int(mask.sum())

        # STV: 9 parties → 5 finalist slots
        stv_result = run_multi_seat_stv(
            state_ballots, state_weights, N_PARTIES, STV_SEATS, PARTY_CODES
        )
        finalist_indices = {p for p, n in stv_result["seats"].items() if n > 0}

        if len(finalist_indices) < 2:
            # Fallback: use all parties
            finalist_indices = set(range(N_PARTIES))

        fin_list  = sorted(finalist_indices)
        fin_codes = [PARTY_CODES[p] for p in fin_list]
        n_fin     = len(fin_list)

        # Filter ballots to finalists
        fin_map = {old: new for new, old in enumerate(fin_list)}
        fin_ballots = np.full((n_state, n_fin), -1, dtype=np.int8)
        for i in range(n_state):
            rank = 0
            for j in range(N_PARTIES):
                p = int(state_ballots[i, j])
                if p in fin_map:
                    fin_ballots[i, rank] = fin_map[p]
                    rank += 1

        # Condorcet
        cond = condorcet_matchups(fin_ballots, state_weights, list(range(n_fin)), fin_codes)
        cond_winner_code = fin_codes[cond["winner"]] if cond["winner"] is not None else fin_codes[0]
        cond_cluster = CLUSTER_FOR_PARTY.get(cond_winner_code, -1)

        # IRV
        irv_result = run_irv(fin_ballots, state_weights, set(range(n_fin)), fin_codes)
        irv_winner_code = fin_codes[irv_result["winner"]] if irv_result["winner"] >= 0 else fin_codes[0]
        irv_cluster = CLUSTER_FOR_PARTY.get(irv_winner_code, -1)

        # First-preference shares among finalists
        first_round = irv_result["rounds"][0] if irv_result["rounds"] else {}
        total_v = sum(first_round.values()) or 1

        # Build output rows
        base_row = {
            "state_fips": fips,
            "state_abbr": abbr,
            "total_weighted_respondents": round(state_weights.sum(), 2),
            "n_finalists": n_fin,
        }
        for code in fin_codes:
            base_row[f"finalist_{code}_pct"] = round(first_round.get(code, 0) / total_v * 100, 2)

        cond_row = {**base_row,
            "senator_code": cond_winner_code,
            "senator_party": cond_winner_code,
            "senator_label": cond_winner_code,
            "senator_type": "pure",
            "senator_axis": "base",
            "senator_dir": "base",
            "primary_cluster": str(cond_cluster),
            "secondary_cluster": "",
        }
        irv_row = {**base_row,
            "senator_code": irv_winner_code,
            "senator_party": irv_winner_code,
            "senator_label": irv_winner_code,
            "senator_type": "pure",
            "senator_axis": "base",
            "senator_dir": "base",
            "primary_cluster": str(irv_cluster),
            "secondary_cluster": "",
        }

        cond_rows.append(cond_row)
        irv_rows.append(irv_row)

        for m in cond["matchups"]:
            all_matchups.append({"state_fips": fips, "state_abbr": abbr, **m})

        fin_str = ", ".join(fin_codes)
        print(f"  {abbr:<4} {n_state:>5}  {fin_str:<40}  {cond_winner_code:>6}  {irv_winner_code:>6}")

    # ── Save ─────────────────────────────────────────────────────────────────
    cond_df = pd.DataFrame(cond_rows)
    irv_df  = pd.DataFrame(irv_rows)

    cond_df.to_csv(OUTPUT_DIR / "senate_composition.csv", index=False)
    irv_df.to_csv(OUTPUT_DIR / "senate_irv_composition.csv", index=False)

    if all_matchups:
        pd.DataFrame(all_matchups).to_csv(OUTPUT_DIR / "senate_condorcet_results.csv", index=False)

    # National summary
    for label, df in [("CONDORCET", cond_df), ("IRV", irv_df)]:
        party_counts = df["senator_party"].value_counts()
        print(f"\n  {label} Senate:")
        for party, n in party_counts.items():
            print(f"    {party:<8} {n:>3} seats")
        print(f"    TOTAL    {len(df):>3}")

    print(f"\n✓ Party senate complete.")


if __name__ == "__main__":
    main()

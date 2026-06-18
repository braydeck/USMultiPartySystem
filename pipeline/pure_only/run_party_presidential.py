#!/usr/bin/env python3
"""
run_party_presidential.py
--------------------------
Presidential general election using party-slate finalists from the primary.

Reads primary results to determine 5 finalist slots, then runs:
  1. National IRV among finalist parties
  2. Per-state IRV (determines electoral geography)
  3. Condorcet (Ranked Pairs) among finalist parties

Finalist slots with multiple candidates from the same party (e.g., CON_1, CON_2)
are displayed as separate candidates but share identical voter preferences.
In IRV, the weaker same-party slot is eliminated first and transfers 100% to
the other. In Condorcet, same-party slots have identical pairwise records.

Outputs to data/outputs/pure_multi/irv/:
  irv_presidential_national_2028.csv
  irv_presidential_states_2028.csv
  condorcet_matchups_2028.csv
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR     = Path(__file__).parent.parent.parent
BALLOTS_PATH = BASE_DIR / "data" / "outputs" / "pure_multi" / "party_ballots.csv"
PRIMARY_PATH = BASE_DIR / "data" / "outputs" / "pure_multi" / "primary_results_2028.csv"
EFA_PATH     = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
OUTPUT_DIR   = BASE_DIR / "data" / "outputs" / "pure_multi" / "irv"

sys.path.insert(0, str(Path(__file__).parent.parent))
from party_stv import run_irv, condorcet_matchups

PARTY_CODES = ["CON", "SD", "STY", "NAT", "LIB", "POP", "CUP", "DSA", "PRG"]
PARTY_IDX   = {c: i for i, c in enumerate(PARTY_CODES)}

FIPS_TO_ABBR = {
     1:"AL",  2:"AK",  4:"AZ",  5:"AR",  6:"CA",  8:"CO",  9:"CT",
    10:"DE", 11:"DC", 12:"FL", 13:"GA", 15:"HI", 16:"ID", 17:"IL",
    18:"IN", 19:"IA", 20:"KS", 21:"KY", 22:"LA", 23:"ME", 24:"MD",
    25:"MA", 26:"MI", 27:"MN", 28:"MS", 29:"MO", 30:"MT", 31:"NE",
    32:"NV", 33:"NH", 34:"NJ", 35:"NM", 36:"NY", 37:"NC", 38:"ND",
    39:"OH", 40:"OK", 41:"OR", 42:"PA", 44:"RI", 45:"SC", 46:"SD",
    47:"TN", 48:"TX", 49:"UT", 50:"VT", 51:"VA", 53:"WA", 54:"WV",
    55:"WI", 56:"WY", 72:"PR",
}


def load_ballots():
    df = pd.read_csv(BALLOTS_PATH, index_col=0)
    N  = len(df)
    ballots = np.zeros((N, len(PARTY_CODES)), dtype=np.int8)
    for k in range(len(PARTY_CODES)):
        ballots[:, k] = df[f"rank_{k+1}"].map(PARTY_IDX).values.astype(np.int8)
    return ballots


def get_finalist_parties():
    """Read primary results and return set of finalist party indices."""
    df = pd.read_csv(PRIMARY_PATH)
    final = df[df["stage"] == "After_Pod_BD"]
    surviving = final[final["status"] == "surviving"]
    parties = set()
    for _, row in surviving.iterrows():
        code = row["party"]
        if code in PARTY_IDX:
            parties.add(PARTY_IDX[code])
    return parties


def run_national_irv(ballots, weights, finalists):
    """Run national IRV among finalist parties. Returns round-by-round data."""
    result = run_irv(ballots, weights, finalists, PARTY_CODES)
    winner_code = PARTY_CODES[result["winner"]] if result["winner"] >= 0 else "none"

    rounds_data = []
    for rnd_idx, rnd in enumerate(result["rounds"], 1):
        eliminated = PARTY_CODES[result["eliminated"][rnd_idx-1]] if rnd_idx <= len(result["eliminated"]) else ""
        total = sum(rnd.values())
        for code, votes in rnd.items():
            rounds_data.append({
                "round": rnd_idx,
                "candidate": code,
                "party": code,
                "votes": round(votes, 2),
                "pct": round(votes / total * 100, 2) if total > 0 else 0,
                "status": "eliminated_this_round" if code == eliminated else
                          ("winner" if rnd_idx == len(result["rounds"]) and code == winner_code else "surviving"),
            })

    return winner_code, rounds_data


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("PARTY PRESIDENTIAL GENERAL — IRV + Condorcet")
    print("=" * 70)

    print("\nLoading data…")
    ballots   = load_ballots()
    efa       = pd.read_csv(EFA_PATH)
    weights   = efa["commonpostweight"].values.astype(np.float64)
    inputstate = efa["inputstate"].values.astype(int)
    N = len(ballots)

    finalists = get_finalist_parties()
    fin_codes = sorted([PARTY_CODES[p] for p in finalists])
    print(f"  {N:,} voters, {len(finalists)} finalist parties: {', '.join(fin_codes)}")

    # ── National IRV ─────────────────────────────────────────────────────────
    print("\nRunning national IRV…")
    winner, irv_rounds = run_national_irv(ballots, weights, finalists)
    print(f"  Winner: {winner}")

    irv_df = pd.DataFrame(irv_rounds)
    irv_df.to_csv(OUTPUT_DIR / "irv_presidential_national_2028.csv", index=False)
    print(f"  Saved irv_presidential_national_2028.csv ({len(irv_df)} rows)")

    # ── Per-state IRV ────────────────────────────────────────────────────────
    print("\nRunning per-state IRV…")
    state_rows = []
    unique_states = sorted(np.unique(inputstate))

    for fips in unique_states:
        mask = inputstate == fips
        if mask.sum() == 0:
            continue
        state_ballots = ballots[mask]
        state_weights = weights[mask]
        abbr = FIPS_TO_ABBR.get(fips, f"FIPS{fips}")

        result = run_irv(state_ballots, state_weights, set(finalists), PARTY_CODES)
        winner_p = PARTY_CODES[result["winner"]] if result["winner"] >= 0 else "none"

        # Runner-up = last eliminated
        runner_up = PARTY_CODES[result["eliminated"][-1]] if result["eliminated"] else "none"

        # First-round shares
        first_round = result["rounds"][0] if result["rounds"] else {}
        total_v = sum(first_round.values()) if first_round else 1

        row = {
            "state_fips": fips,
            "state_abbr": abbr,
            "irv_winner": winner_p,
            "irv_runner_up": runner_up,
            "n_rounds": len(result["rounds"]),
            "total_weight": round(state_weights.sum(), 1),
        }
        for code in fin_codes:
            row[f"fc_pct_{code}"] = round(first_round.get(code, 0) / total_v * 100, 1)

        state_rows.append(row)

    state_df = pd.DataFrame(state_rows)
    state_df.to_csv(OUTPUT_DIR / "irv_presidential_states_2028.csv", index=False)
    print(f"  Saved irv_presidential_states_2028.csv ({len(state_df)} rows)")

    # States won summary
    print("\n  States won:")
    for code, n in state_df["irv_winner"].value_counts().items():
        print(f"    {code:<8} {n}")

    # ── Condorcet ────────────────────────────────────────────────────────────
    print("\nRunning Condorcet (Ranked Pairs)…")
    fin_list = sorted(finalists)
    fin_map  = {old: new for new, old in enumerate(fin_list)}
    n_fin    = len(fin_list)

    fin_ballots = np.full((N, n_fin), -1, dtype=np.int8)
    for i in range(N):
        rank = 0
        for j in range(len(PARTY_CODES)):
            p = int(ballots[i, j])
            if p in fin_map:
                fin_ballots[i, rank] = fin_map[p]
                rank += 1

    fin_codes_ordered = [PARTY_CODES[p] for p in fin_list]
    cond = condorcet_matchups(fin_ballots, weights, list(range(n_fin)), fin_codes_ordered)

    cond_winner = fin_codes_ordered[cond["winner"]] if cond["winner"] is not None else "none"
    print(f"  Condorcet winner: {cond_winner}")

    matchup_df = pd.DataFrame(cond["matchups"])
    matchup_df.to_csv(OUTPUT_DIR / "condorcet_matchups_2028.csv", index=False)
    print(f"  Saved condorcet_matchups_2028.csv ({len(matchup_df)} rows)")

    print(f"\n✓ Raw multi presidential general complete.")


if __name__ == "__main__":
    main()

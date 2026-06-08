#!/usr/bin/env python3
"""
run_fd_irv_2028.py
-------------------
Presidential general election (IRV + Condorcet) for the Factor Deviation
scenario, using the 5 finalists from run_fd_primary_2028.py.

Finalists are loaded dynamically from factor_deviation/primary_results_2028.csv.

Outputs to data/outputs/factor_deviation/irv/:
  irv_presidential_national_2028.csv  — round-by-round national IRV
  irv_presidential_states_2028.csv    — winner + runner-up per state
  condorcet_matchups_2028.csv         — pairwise matchups among finalists
"""

import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR       = Path(__file__).parent.parent
BALLOTS_PATH   = BASE_DIR / "data" / "outputs" / "factor_deviation" / "ballots.csv"
PRIMARY_PATH   = BASE_DIR / "data" / "outputs" / "factor_deviation" / "primary_results_2028.csv"
EFA_PATH       = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
OUTPUT_DIR     = BASE_DIR / "data" / "outputs" / "factor_deviation" / "irv"

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

FINALISTS:       list = []
FINALIST_LABELS: dict = {}


def extract_finalist_ballots(ballots_df: pd.DataFrame) -> np.ndarray:
    finalist_set = set(FINALISTS)
    rank_cols    = [c for c in ballots_df.columns if c.startswith("rank_")]
    raw = ballots_df[rank_cols].values
    N   = len(raw)
    F   = len(FINALISTS)
    out = np.empty((N, F), dtype=object)
    for i in range(N):
        out[i] = [code for code in raw[i] if code in finalist_set]
    return out


def first_surviving_choice(ballots: np.ndarray, active: set) -> np.ndarray:
    N      = len(ballots)
    result = np.full(N, "__exhausted__", dtype=object)
    for i in range(N):
        for code in ballots[i]:
            if code in active:
                result[i] = code
                break
    return result


def run_irv(ballots: np.ndarray, weights: np.ndarray,
            candidates: list) -> list:
    active  = set(candidates)
    rounds  = []
    total_w = float(weights.sum())

    while len(active) > 1:
        fsc    = first_surviving_choice(ballots, active)
        totals = {code: float(weights[fsc == code].sum()) for code in active}

        winner_candidates = [c for c, v in totals.items() if v > total_w / 2]
        round_record = {
            "round":     len(rounds) + 1,
            "active":    sorted(active),
            "totals":    {c: round(totals[c], 4) for c in sorted(active)},
            "pcts":      {c: round(totals[c] / total_w * 100, 4) for c in sorted(active)},
            "eliminated": None,
        }

        if winner_candidates:
            rounds.append(round_record)
            break

        loser = min(active, key=lambda c: (totals[c], c))
        round_record["eliminated"] = loser
        rounds.append(round_record)
        active.discard(loser)

    return rounds


def summarise_irv(rounds: list, candidates: list) -> dict:
    elimination_order = [r["eliminated"] for r in rounds if r["eliminated"]]
    remaining         = [c for c in candidates if c not in elimination_order]
    last_pcts         = rounds[-1]["pcts"] if rounds else {}
    winner            = max(remaining, key=lambda c: last_pcts.get(c, 0)) if remaining else "none"
    runner_up         = elimination_order[-1] if elimination_order else "none"
    return {
        "winner":          winner,
        "runner_up":       runner_up,
        "winner_label":    FINALIST_LABELS.get(winner, winner),
        "runner_up_label": FINALIST_LABELS.get(runner_up, runner_up),
    }


def run_condorcet(ballots: np.ndarray, weights: np.ndarray,
                  candidates: list) -> tuple:
    n       = len(candidates)
    matchups = []
    for i in range(n):
        for j in range(i + 1, n):
            a, b = candidates[i], candidates[j]
            votes_a = votes_b = 0.0
            for k in range(len(ballots)):
                ballot = ballots[k]
                w      = weights[k]
                a_pos  = b_pos = 999
                for rank, code in enumerate(ballot):
                    if code == a:   a_pos = rank
                    elif code == b: b_pos = rank
                if a_pos < b_pos:
                    votes_a += w
                elif b_pos < a_pos:
                    votes_b += w
                # else: absent from ballot — skip (exhausted)
            total      = votes_a + votes_b
            winner     = a if votes_a > votes_b else b
            margin     = abs(votes_a - votes_b)
            margin_pct = round(margin / total * 100, 3) if total > 0 else 0.0
            matchups.append({
                "candidate_a":     a,
                "candidate_b":     b,
                "votes_a_beats_b": round(votes_a, 4),
                "votes_b_beats_a": round(votes_b, 4),
                "winner":          winner,
                "margin":          round(margin, 4),
                "margin_pct":      margin_pct,
            })

    wins = {c: 0 for c in candidates}
    for m in matchups:
        wins[m["winner"]] += 1
    condorcet_winner = next((c for c, w in wins.items() if w == n - 1), "none")
    return matchups, condorcet_winner


def main():
    global FINALISTS, FINALIST_LABELS

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Load finalists ─────────────────────────────────────────────────────────
    print(f"Loading finalists from {PRIMARY_PATH.name}…")
    primary_df    = pd.read_csv(PRIMARY_PATH)
    finalist_rows = primary_df[
        (primary_df["winnowing_point"] == "After_Pod_BD") &
        (primary_df["status"] == "surviving")
    ][["candidate_code", "candidate_name"]].drop_duplicates()
    FINALISTS       = sorted(finalist_rows["candidate_code"].tolist())
    FINALIST_LABELS = dict(zip(finalist_rows["candidate_code"], finalist_rows["candidate_name"]))
    print(f"  Finalists ({len(FINALISTS)}): {', '.join(FINALISTS)}")

    # ── Load data ──────────────────────────────────────────────────────────────
    print("Loading ballots and EFA scores…")
    ballots_df = pd.read_csv(BALLOTS_PATH)
    efa        = pd.read_csv(EFA_PATH)
    weights    = efa["commonpostweight"].values.astype(float)
    state_fips = efa["inputstate"].values.astype(int)
    print(f"  {len(efa):,} respondents")

    print("Extracting finalist sub-ballots…")
    ballots = extract_finalist_ballots(ballots_df)
    print(f"  Shape: {ballots.shape}")

    # ── National IRV ───────────────────────────────────────────────────────────
    print("\nRunning national IRV…")
    nat_rounds = run_irv(ballots, weights, FINALISTS)
    nat_result = summarise_irv(nat_rounds, FINALISTS)

    print(f"\n{'='*60}")
    print("NATIONAL IRV RESULT")
    print(f"{'='*60}")
    for rnd in nat_rounds:
        pcts = "  ".join(f"{c}={rnd['pcts'][c]:.1f}%" for c in rnd["active"])
        elim = f"  → ELIMINATE {rnd['eliminated']}" if rnd["eliminated"] else "  → WINNER"
        print(f"  Round {rnd['round']}: {pcts}{elim}")
    print(f"\n  IRV Winner:    {nat_result['winner']}")
    print(f"  IRV Runner-up: {nat_result['runner_up']}")

    nat_rows = []
    for rnd in nat_rounds:
        for code in FINALISTS:
            if code in rnd["totals"]:
                nat_rows.append({
                    "round":          rnd["round"],
                    "candidate_code": code,
                    "candidate_name": FINALIST_LABELS[code],
                    "vote_total":     rnd["totals"][code],
                    "vote_pct":       rnd["pcts"][code],
                    "eliminated":     (rnd["eliminated"] == code),
                    "winner":         (nat_result["winner"] == code and rnd["eliminated"] is None),
                })
    nat_df   = pd.DataFrame(nat_rows)
    nat_path = OUTPUT_DIR / "irv_presidential_national_2028.csv"
    nat_df.to_csv(nat_path, index=False)
    print(f"\nSaved national rounds → {nat_path.relative_to(BASE_DIR)}")

    # ── National Condorcet ─────────────────────────────────────────────────────
    print("\nRunning national Condorcet…")
    matchups, cond_winner = run_condorcet(ballots, weights, FINALISTS)
    print(f"  Condorcet winner: {cond_winner}")

    cond_rows = [{**m, "condorcet_winner": cond_winner} for m in matchups]
    cond_df   = pd.DataFrame(cond_rows)
    cond_path = OUTPUT_DIR / "condorcet_matchups_2028.csv"
    cond_df.to_csv(cond_path, index=False)
    print(f"Saved Condorcet matchups → {cond_path.relative_to(BASE_DIR)}")

    # ── Per-state IRV + Condorcet ────────────────────────────────────────────
    print("\nRunning per-state IRV + Condorcet…")
    state_rows = []
    for fips in sorted(set(state_fips)):
        mask = state_fips == fips
        if mask.sum() < 5:
            continue
        s_ballots = ballots[mask]
        s_weights = weights[mask]
        s_rounds = run_irv(s_ballots, s_weights, FINALISTS)
        s_result = summarise_irv(s_rounds, FINALISTS)
        _, s_cond_winner = run_condorcet(s_ballots, s_weights, FINALISTS)
        r1 = s_rounds[0]["pcts"] if s_rounds else {}
        row = {
            "state_fips":            fips,
            "state_abbr":            FIPS_TO_ABBR.get(fips, f"FIPS{fips}"),
            "winner_code":           s_result["winner"],
            "winner_label":          s_result["winner_label"],
            "runner_up_code":        s_result["runner_up"],
            "runner_up_label":       s_result["runner_up_label"],
            "condorcet_winner_code": s_cond_winner,
            "n_respondents":         int(mask.sum()),
            "n_irv_rounds":          len(s_rounds),
        }
        for code in FINALISTS:
            row[f"r1_pct_{code}"] = round(r1.get(code, 0.0), 2)
        state_rows.append(row)

    state_df   = pd.DataFrame(state_rows)
    state_path = OUTPUT_DIR / "irv_presidential_states_2028.csv"
    state_df.to_csv(state_path, index=False)
    print(f"Saved state results → {state_path.relative_to(BASE_DIR)}  ({len(state_df)} states)")

    win_counts = state_df["winner_code"].value_counts()
    print("\nStates won:")
    for code, cnt in win_counts.items():
        print(f"  {code:<22} {cnt:2d}")

    print("\nFD presidential IRV + Condorcet complete.")


if __name__ == "__main__":
    main()

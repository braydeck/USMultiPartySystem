#!/usr/bin/env python3
"""
run_pure_multi_presidential.py
-------------------------------
Presidential general election for the 27-candidate Raw Multi pipeline.

Reads finalists dynamically from the primary output (After_Pod_BD, surviving),
then runs national IRV, per-state IRV, and Ranked Pairs (Condorcet) using the
pre-generated Plackett-Luce ballots.

Outputs to data/outputs/pure_multi/irv/:
  irv_presidential_national_2028.csv   — round-by-round national IRV
  condorcet_matchups_2028.csv          — Ranked Pairs pairwise matchups
  irv_presidential_states_2028.csv     — IRV winner + runner-up per state
"""

import os
import numpy as np
import pandas as pd
from pathlib import Path
from itertools import combinations

INCLUDE_C7   = os.environ.get("INCLUDE_C7") == "1"
_SUB         = "pure_multi_c7" if INCLUDE_C7 else "pure_multi"

BASE_DIR     = Path(__file__).parent.parent.parent
BALLOTS_PATH = BASE_DIR / "data" / "outputs" / _SUB / "presidential_ballots.csv"
PRIMARY_PATH = BASE_DIR / "data" / "outputs" / _SUB / "primary_results_2028.csv"
EFA_PATH     = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
OUTPUT_DIR   = BASE_DIR / "data" / "outputs" / _SUB / "irv"

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

# ── Helpers ────────────────────────────────────────────────────────────────────

def extract_finalist_ballots(ballots_arr: np.ndarray, finalist_set: set,
                              n_finalists: int) -> np.ndarray:
    """Project full ballots to finalist-only ordering."""
    N = len(ballots_arr)
    out = np.empty((N, n_finalists), dtype=object)
    for i in range(N):
        filtered = [code for code in ballots_arr[i] if code in finalist_set]
        out[i] = filtered
    return out


def first_surviving_choice(ballots: np.ndarray, active: set) -> np.ndarray:
    N = len(ballots)
    result = np.full(N, "__exhausted__", dtype=object)
    for i in range(N):
        for code in ballots[i]:
            if code in active:
                result[i] = code
                break
    return result


# ── IRV ────────────────────────────────────────────────────────────────────────

def run_irv(ballots: np.ndarray, weights: np.ndarray,
            candidates: list) -> list:
    """Run IRV to completion. Returns list of round dicts."""
    active  = set(candidates)
    total_w = float(weights.sum())
    rounds  = []

    while len(active) > 1:
        fsc    = first_surviving_choice(ballots, active)
        totals = {c: float(weights[fsc == c].sum()) for c in active}

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
    remaining = [c for c in candidates if c not in elimination_order]
    last_pcts = rounds[-1]["pcts"] if rounds else {}
    winner    = max(remaining, key=lambda c: last_pcts.get(c, 0)) if remaining else "none"
    runner_up = elimination_order[-1] if elimination_order else "none"
    return {"winner": winner, "runner_up": runner_up}


# ── Condorcet (Ranked Pairs) ───────────────────────────────────────────────────

def build_matchups(ballots_arr: np.ndarray, weights: np.ndarray,
                   finalists: list) -> list:
    finalist_ranks = {}
    M = ballots_arr.shape[1]
    for code in finalists:
        ranks = np.full(len(ballots_arr), M + 1)
        for j in range(M):
            mask = ballots_arr[:, j] == code
            ranks[mask] = j
        finalist_ranks[code] = ranks

    matchups = []
    for a, b in combinations(finalists, 2):
        ra, rb = finalist_ranks[a], finalist_ranks[b]
        matchups.append({
            "candidate_a":     a,
            "candidate_b":     b,
            "votes_a_beats_b": float(weights[ra < rb].sum()),
            "votes_b_beats_a": float(weights[rb < ra].sum()),
        })
    return matchups


def ranked_pairs_winner(matchups: list, candidates: list) -> tuple:
    if not matchups or len(candidates) < 2:
        return (candidates[0] if candidates else "none"), matchups

    total_votes = max(m["votes_a_beats_b"] + m["votes_b_beats_a"] for m in matchups)

    defeats = []
    for idx, m in enumerate(matchups):
        a, b   = m["candidate_a"], m["candidate_b"]
        va, vb = m["votes_a_beats_b"], m["votes_b_beats_a"]
        winner, loser, margin = (a, b, va - vb) if va >= vb else (b, a, vb - va)
        defeats.append({"winner": winner, "loser": loser, "margin": margin,
                         "margin_pct": margin / total_votes * 100 if total_votes else 0,
                         "orig_idx": idx})
    defeats.sort(key=lambda x: (-x["margin"], x["winner"]))

    def creates_cycle(locked, new_w, new_l):
        reachable, frontier = set(), {new_l}
        while frontier:
            node = frontier.pop()
            if node == new_w: return True
            if node in reachable: continue
            reachable.add(node)
            for w, l in locked:
                if w == node and l not in reachable:
                    frontier.add(l)
        return False

    locked_edges = []
    lock_meta = {d["orig_idx"]: {"lock_order": None, "locked": False} for d in defeats}
    for order, defeat in enumerate(defeats, start=1):
        idx = defeat["orig_idx"]
        lock_meta[idx]["lock_order"] = order
        if not creates_cycle(locked_edges, defeat["winner"], defeat["loser"]):
            locked_edges.append((defeat["winner"], defeat["loser"]))
            lock_meta[idx]["locked"] = True

    losers     = {l for _, l in locked_edges}
    undefeated = [c for c in candidates if c not in losers]
    rp_winner  = undefeated[0] if undefeated else "none"

    for d in defeats:
        idx = d["orig_idx"]
        matchups[idx].update({
            "margin":            round(d["margin"], 2),
            "margin_pct":        round(d["margin_pct"], 4),
            "lock_order":        lock_meta[idx]["lock_order"],
            "locked":            lock_meta[idx]["locked"],
            "condorcet_winner":  rp_winner,
        })
    return rp_winner, matchups


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("RAW MULTI PRESIDENTIAL GENERAL  —  27-candidate pool")
    print("=" * 65)

    # Load finalists from primary output
    print(f"\nLoading finalists from {PRIMARY_PATH.name}…")
    primary_df    = pd.read_csv(PRIMARY_PATH)
    finalist_rows = primary_df[
        (primary_df["winnowing_point"] == "After_Pod_BD") &
        (primary_df["status"] == "surviving")
    ][["candidate_code", "candidate_name"]].drop_duplicates()
    FINALISTS       = sorted(finalist_rows["candidate_code"].tolist())
    FINALIST_LABELS = dict(zip(finalist_rows["candidate_code"], finalist_rows["candidate_name"]))
    print(f"  Finalists ({len(FINALISTS)}): {', '.join(FINALISTS)}")

    # Load ballots and weights
    print("Loading ballots and EFA scores…")
    ballots_df  = pd.read_csv(BALLOTS_PATH, index_col="respondent_id")
    efa         = pd.read_csv(EFA_PATH)
    N           = len(ballots_df)
    rank_cols   = [f for f in ballots_df.columns if f.startswith("rank_")]
    ballots_arr = ballots_df[rank_cols].values
    weights     = efa["commonpostweight"].values.astype(float)
    state_fips  = efa["inputstate"].values.astype(int)
    assert len(efa) == N, f"Row count mismatch: {N} vs {len(efa)}"
    print(f"  {N:,} ballots loaded")

    # Project to finalist sub-ballots
    finalist_set = set(FINALISTS)
    print("Extracting finalist sub-ballots…")
    fin_ballots = extract_finalist_ballots(ballots_arr, finalist_set, len(FINALISTS))
    print(f"  Ballot shape: {fin_ballots.shape}")

    # ── National IRV ──────────────────────────────────────────────────────────
    print("\nRunning national IRV…")
    nat_rounds = run_irv(fin_ballots, weights, FINALISTS)
    nat_result = summarise_irv(nat_rounds, FINALISTS)

    print(f"\n{'='*60}")
    print("NATIONAL IRV RESULT")
    print(f"{'='*60}")
    for rnd in nat_rounds:
        pcts = "  ".join(f"{c}={rnd['pcts'][c]:.1f}%" for c in rnd["active"])
        elim = f"  → ELIMINATE {rnd['eliminated']}" if rnd["eliminated"] else "  → WINNER DETERMINED"
        print(f"  Round {rnd['round']:1d}: {pcts}{elim}")
    print(f"\n  Winner:    {nat_result['winner']}")
    print(f"  Runner-up: {nat_result['runner_up']}")

    # Save national round-by-round
    nat_rows = []
    for rnd in nat_rounds:
        for code in FINALISTS:
            if code in rnd["totals"]:
                nat_rows.append({
                    "round":          rnd["round"],
                    "candidate_code": code,
                    "candidate_name": FINALIST_LABELS.get(code, code),
                    "vote_total":     rnd["totals"][code],
                    "vote_pct":       rnd["pcts"][code],
                    "eliminated":     (rnd["eliminated"] == code),
                    "winner":         (nat_result["winner"] == code and rnd["eliminated"] is None),
                })
    nat_df   = pd.DataFrame(nat_rows)
    nat_path = OUTPUT_DIR / "irv_presidential_national_2028.csv"
    nat_df.to_csv(nat_path, index=False)
    print(f"\nSaved national rounds → {nat_path}")

    # ── Ranked Pairs Condorcet ────────────────────────────────────────────────
    print("\nRunning Ranked Pairs Condorcet…")
    raw_matchups           = build_matchups(fin_ballots, weights, FINALISTS)
    cond_winner, matchups  = ranked_pairs_winner(raw_matchups, FINALISTS)
    print(f"  Condorcet winner: {cond_winner}")

    cond_col_order = ["candidate_a", "candidate_b", "votes_a_beats_b", "votes_b_beats_a",
                      "margin", "margin_pct", "locked", "lock_order", "condorcet_winner"]
    cond_df   = pd.DataFrame(matchups)
    cond_df   = cond_df[[c for c in cond_col_order if c in cond_df.columns]]
    cond_path = OUTPUT_DIR / "condorcet_matchups_2028.csv"
    cond_df.to_csv(cond_path, index=False)
    print(f"Saved Condorcet matchups → {cond_path}  ({len(cond_df)} rows)")

    # ── Per-state IRV + Condorcet ──────────────────────────────────────────────
    print("\nRunning per-state IRV + Condorcet…")
    unique_states = sorted(s for s in np.unique(state_fips) if s != 72)
    state_rows    = []

    for fips in unique_states:
        mask = state_fips == fips
        if mask.sum() < 5:
            continue
        s_ballots = fin_ballots[mask]
        s_weights = weights[mask]
        abbr      = FIPS_TO_ABBR.get(fips, f"FIPS{fips}")

        s_rounds = run_irv(s_ballots, s_weights, FINALISTS)
        s_result = summarise_irv(s_rounds, FINALISTS)

        # State-level Condorcet via Ranked Pairs
        s_matchups                  = build_matchups(s_ballots, s_weights, FINALISTS)
        s_cond_winner, _            = ranked_pairs_winner(s_matchups, FINALISTS)

        r1 = s_rounds[0]["pcts"] if s_rounds else {}
        row = {
            "state_fips":            fips,
            "state_abbr":            abbr,
            "winner_code":           s_result["winner"],
            "runner_up_code":        s_result["runner_up"],
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
    print(f"Saved state results → {state_path}  ({len(state_df)} states)")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("STATE RESULTS  (Raw Multi Presidential IRV)")
    print(f"{'='*60}")
    win_counts = state_df["winner_code"].value_counts()
    print("\nStates won:")
    for code, cnt in win_counts.items():
        print(f"  {code:<12} {cnt:2d}")

    print(f"\n  {'St':<4}  {'Winner':<8}  {'Runner-up':<8}  {'Rds':>3}  First-choice %")
    print("  " + "-" * 60)
    for _, row in state_df.sort_values("state_abbr").iterrows():
        r1_str = "  ".join(f"{c}={row[f'r1_pct_{c}']:.0f}%" for c in FINALISTS)
        print(f"  {row['state_abbr']:<4}  {row['winner_code']:<8}  "
              f"{row['runner_up_code']:<8}  {int(row['n_irv_rounds']):>3}   {r1_str}")

    print("\n✓ Raw multi presidential general complete.")


if __name__ == "__main__":
    main()

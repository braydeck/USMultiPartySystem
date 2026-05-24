#!/usr/bin/env python3
"""
run_pure_multi_senate.py
--------------------------
State-by-state senate simulation using the 21-candidate pure/raw multi-candidate pool.

For each state:
  1. Filter the pre-generated global ballots to state respondents
  2. Run STV (Gregory) elimination → 5 finalists
  3. Run Ranked Pairs Condorcet → 1 senator  (senate_composition.csv)
  4. Run IRV → 1 senator  (senate_irv_composition.csv)

No per-state ballot re-generation needed — the global Plackett-Luce ballots
already reflect each respondent's factor-space preferences over all 21 candidates.

Outputs to data/outputs/pure_multi/senate/:
  senate_composition.csv         — Condorcet (Ranked Pairs) winner per state
  senate_irv_composition.csv     — IRV winner per state
  senate_condorcet_results.csv   — Ranked Pairs matchup detail per state
"""

import numpy as np
import pandas as pd
from pathlib import Path
from itertools import combinations
from collections import defaultdict

BASE_DIR     = Path(__file__).parent.parent.parent
BALLOTS_PATH = BASE_DIR / "data" / "outputs" / "pure_multi" / "presidential_ballots.csv"
EFA_PATH     = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
OUTPUT_DIR   = BASE_DIR / "data" / "outputs" / "pure_multi" / "senate"

STV_SURVIVORS   = 5
MIN_RESPONDENTS = 10

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

# 21 candidates — must match generate_pure_multi_ballots.py exactly
CANDIDATES = [
    {"code": "CON_1", "party": "CON", "cluster": 0},
    {"code": "CON_2", "party": "CON", "cluster": 0},
    {"code": "CON_3", "party": "CON", "cluster": 0},
    {"code": "SD_1",  "party": "SD",  "cluster": 1},
    {"code": "SD_2",  "party": "SD",  "cluster": 1},
    {"code": "SD_3",  "party": "SD",  "cluster": 1},
    {"code": "STY_1", "party": "STY", "cluster": 2},
    {"code": "STY_2", "party": "STY", "cluster": 2},
    {"code": "STY_3", "party": "STY", "cluster": 2},
    {"code": "NAT_1", "party": "NAT", "cluster": 3},
    {"code": "NAT_2", "party": "NAT", "cluster": 3},
    {"code": "LIB_1", "party": "LIB", "cluster": 4},
    {"code": "LIB_2", "party": "LIB", "cluster": 4},
    {"code": "REF_1", "party": "REF", "cluster": 5},
    {"code": "REF_2", "party": "REF", "cluster": 5},
    {"code": "CTR_1", "party": "CTR", "cluster": 6},
    {"code": "CTR_2", "party": "CTR", "cluster": 6},
    {"code": "DSA_1", "party": "DSA", "cluster": 8},
    {"code": "DSA_2", "party": "DSA", "cluster": 8},
    {"code": "PRG_1", "party": "PRG", "cluster": 9},
    {"code": "PRG_2", "party": "PRG", "cluster": 9},
]
CAND_CODES   = [c["code"]    for c in CANDIDATES]
CAND_PARTY   = {c["code"]: c["party"]   for c in CANDIDATES}
CAND_CLUSTER = {c["code"]: c["cluster"] for c in CANDIDATES}
N_CANDIDATES = len(CANDIDATES)


def party_of(code: str) -> str:
    return CAND_PARTY.get(code, code.rsplit("_", 1)[0])


# ── STV helpers ───────────────────────────────────────────────────────────────

def first_surviving_choice(ballots_arr: np.ndarray, active_set: set) -> np.ndarray:
    N = len(ballots_arr)
    result = np.empty(N, dtype=object)
    for i in range(N):
        result[i] = "__exhausted__"
        for code in ballots_arr[i]:
            if code in active_set:
                result[i] = code
                break
    return result


def compute_vote_totals(fsc: np.ndarray, weights: np.ndarray, active_set: set) -> dict:
    totals = {c: 0.0 for c in active_set}
    for code, w in zip(fsc, weights):
        if code in totals:
            totals[code] += w
    return totals


def droop_quota(total_votes: float, n_survivors: int) -> float:
    return total_votes / (n_survivors + 1) + 1


def winnow_stv(ballots_arr: np.ndarray, weights: np.ndarray,
               active_set: set, target: int) -> set:
    """Gregory STV → returns finalist set."""
    active      = set(active_set)
    ballot_wts  = weights.astype(float).copy()
    total_votes = float(weights.sum())
    quota       = droop_quota(total_votes, target)
    elected: list = []

    while len(elected) < target and active:
        remaining = target - len(elected)
        if len(active) <= remaining:
            elected.extend(sorted(active))
            active.clear()
            break

        fsc    = first_surviving_choice(ballots_arr, active)
        totals = compute_vote_totals(fsc, ballot_wts, active)

        over_quota = sorted(
            [c for c in active if totals[c] >= quota],
            key=lambda c: (-totals[c], c),
        )
        if over_quota:
            winner         = over_quota[0]
            surplus_factor = (totals[winner] - quota) / totals[winner]
            for i in range(len(fsc)):
                if fsc[i] == winner:
                    ballot_wts[i] *= surplus_factor
            active.discard(winner)
            elected.append(winner)
        else:
            loser = min(active, key=lambda c: (totals[c], c))
            active.discard(loser)

    return set(elected)


# ── Condorcet (Ranked Pairs) ──────────────────────────────────────────────────

def build_matchups(ballots_arr: np.ndarray, weights: np.ndarray,
                   finalists: list) -> list:
    """Vectorised head-to-head matchup builder."""
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
            "rp_winner_overall": rp_winner,
        })
    return rp_winner, matchups


# ── IRV ───────────────────────────────────────────────────────────────────────

def irv_winner(ballots_arr: np.ndarray, weights: np.ndarray,
               candidates: list) -> str:
    """Plain IRV (instant runoff) among a candidate list."""
    active = set(candidates)
    bwts   = weights.astype(float).copy()
    while len(active) > 1:
        fsc    = first_surviving_choice(ballots_arr, active)
        totals = compute_vote_totals(fsc, bwts, active)
        total  = sum(totals.values())
        if total == 0:
            break
        winner_candidates = [c for c in active if totals[c] / total > 0.5]
        if winner_candidates:
            return winner_candidates[0]
        active.discard(min(active, key=lambda c: (totals[c], c)))
    return next(iter(active)) if active else "none"


# ── Composition row builder ───────────────────────────────────────────────────

def make_comp_row(state_fips: int, state_abbr: str, senator_code: str,
                  finalists: list, ballots_arr: np.ndarray,
                  weights: np.ndarray) -> dict:
    fsc    = first_surviving_choice(ballots_arr, set(finalists))
    totals = compute_vote_totals(fsc, weights, set(finalists))
    total  = weights.sum()
    party  = party_of(senator_code)
    row = {
        "state_fips":                 int(state_fips),
        "state_abbr":                 state_abbr,
        "senator_code":               senator_code,
        "senator_label":              senator_code,
        "senator_party":              party,
        "senator_type":               "pure",
        "primary_cluster":            str(CAND_CLUSTER.get(senator_code, -1)),
        "secondary_cluster":          "",
        "total_weighted_respondents": round(float(total), 2),
        "n_candidates_in_race":       N_CANDIDATES,
        "n_finalists":                len(finalists),
    }
    for code in finalists:
        row[f"finalist_{code}_pct"] = round(totals.get(code, 0.0) / total * 100, 4) if total else 0.0
    return row


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 65)
    print("PURE MULTI SENATE SIMULATION  —  21 intra-party candidates")
    print("=" * 65)

    # Load global ballots
    print("\nLoading global ballots…")
    ballot_df   = pd.read_csv(BALLOTS_PATH, index_col="respondent_id")
    N           = len(ballot_df)
    rank_cols   = [f"rank_{k+1}" for k in range(N_CANDIDATES)]
    ballots_arr = ballot_df[rank_cols].values
    print(f"  {N:,} ballots × {N_CANDIDATES} candidates")

    # Load EFA scores for state + weights
    print("Loading EFA scores…")
    efa        = pd.read_csv(EFA_PATH)
    inputstate = efa["inputstate"].values.astype(int)
    weights    = efa["commonpostweight"].values.astype(float)
    assert len(efa) == N, f"Row count mismatch: {N} vs {len(efa)}"

    all_states = sorted(s for s in np.unique(inputstate) if s != 72)

    all_condorcet:   list = []
    comp_rows_cond:  list = []
    comp_rows_irv:   list = []

    print(f"\nRunning senate elections for {len(all_states)} states/DC…\n")
    print(f"  {'St':4s}  {'N':>5s}  {'Finalists':<40s}  Cond → IRV")
    print(f"  {'-'*75}")

    for state_fips in all_states:
        mask       = inputstate == state_fips
        state_abbr = FIPS_TO_ABBR.get(int(state_fips), f"FIPS{state_fips}")
        n_resp     = mask.sum()

        if n_resp < MIN_RESPONDENTS:
            print(f"  {state_abbr:4s}  SKIPPED (N={n_resp})")
            continue

        state_ballots = ballots_arr[mask]
        state_weights = weights[mask]

        # STV → finalists
        finalists = winnow_stv(state_ballots, state_weights,
                               set(CAND_CODES), STV_SURVIVORS)
        finalist_list = sorted(finalists)

        # Ranked Pairs
        if len(finalist_list) < 2:
            cond_winner = finalist_list[0] if finalist_list else "none"
            matchups    = []
        else:
            raw_matchups              = build_matchups(state_ballots, state_weights, finalist_list)
            cond_winner, matchups     = ranked_pairs_winner(raw_matchups, finalist_list)

        # IRV
        irv_win = irv_winner(state_ballots, state_weights, finalist_list)

        # Matchups — annotate with state
        for m in matchups:
            m["state_fips"] = int(state_fips)
            m["state_abbr"] = state_abbr
        all_condorcet.extend(matchups)

        # Composition rows
        comp_rows_cond.append(
            make_comp_row(state_fips, state_abbr, cond_winner,
                          finalist_list, state_ballots, state_weights)
        )
        comp_rows_irv.append(
            make_comp_row(state_fips, state_abbr, irv_win,
                          finalist_list, state_ballots, state_weights)
        )

        finalists_str = ", ".join(finalist_list)
        if len(finalists_str) > 40:
            finalists_str = finalists_str[:37] + "…"
        print(f"  {state_abbr:4s}  {n_resp:>5d}  {finalists_str:<40s}  "
              f"{cond_winner} → {irv_win}")

    # ── Save outputs ──────────────────────────────────────────────────────────
    print(f"\nSaving to {OUTPUT_DIR} …")

    cond_df = pd.DataFrame(comp_rows_cond).sort_values("state_fips").reset_index(drop=True)
    irv_df  = pd.DataFrame(comp_rows_irv).sort_values("state_fips").reset_index(drop=True)

    cond_df.to_csv(OUTPUT_DIR / "senate_composition.csv", index=False)
    irv_df.to_csv(OUTPUT_DIR / "senate_irv_composition.csv", index=False)
    print(f"  senate_composition.csv:       {len(cond_df)} rows")
    print(f"  senate_irv_composition.csv:   {len(irv_df)} rows")

    if all_condorcet:
        cond_results_df = pd.DataFrame(all_condorcet)
        cond_col_order  = ["state_fips", "state_abbr", "candidate_a", "candidate_b",
                           "votes_a_beats_b", "votes_b_beats_a",
                           "margin", "margin_pct", "locked", "lock_order", "rp_winner_overall"]
        cond_results_df = cond_results_df[[c for c in cond_col_order if c in cond_results_df.columns]]
        cond_results_df.to_csv(OUTPUT_DIR / "senate_condorcet_results.csv", index=False)
        print(f"  senate_condorcet_results.csv: {len(cond_results_df)} rows")

    # ── National summary ──────────────────────────────────────────────────────
    for label, df in [("CONDORCET", cond_df), ("IRV", irv_df)]:
        print(f"\n{'='*55}")
        print(f"NATIONAL SENATE  ({label})  —  {len(df)} states")
        print(f"{'='*55}")

        # By individual senator code
        code_counts  = df["senator_code"].value_counts()
        party_counts = df["senator_party"].value_counts()
        total        = len(df)
        print(f"\n  {'Candidate':<14}  {'Party':<8}  {'Seats':>5}  {'%':>6}")
        print(f"  {'-'*40}")
        for code, n in code_counts.items():
            print(f"  {code:<14}  {party_of(code):<8}  {n:>5}  {n/total*100:>5.1f}%")
        print(f"\n  {'Party':<10}  {'Seats':>5}  {'%':>6}")
        print(f"  {'-'*28}")
        for party, n in party_counts.items():
            print(f"  {party:<10}  {n:>5}  {n/total*100:>5.1f}%")
        print(f"  {'TOTAL':<10}  {total:>5}")

    print("\n✓ Pure multi senate simulation complete.")


if __name__ == "__main__":
    main()

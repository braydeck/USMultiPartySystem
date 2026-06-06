#!/usr/bin/env python3
"""
run_presidential_primary_2028.py
----------------------------------
2028 Presidential Primary simulation using cumulative rolling STV.

Requires:
  Claude/outputs/presidential_ballots.csv       (from generate_presidential_ballots.py)
  Claude/outputs/state_candidate_profiles.csv   (from generate_presidential_ballots.py)
  Claude/data/efa_factor_scores.csv             (for inputstate + commonpostweight)

Voting order:
  Retail Six → Pod A → Pod C → Pod B + Pod D

Winnowing schedule:
  After Retail Six  → 12 survivors
  After Pod A       → 10 survivors
  After Pod C       →  8 survivors
  After Pod B + D   →  5 survivors

Outputs:
  Claude/outputs/primary_results_2028.csv
  Claude/outputs/primary_diagnostics_2028.csv   (trajectories, geo breakdown, straddler
                                                  analysis, transfer analysis, Condorcet)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR         = Path(__file__).parent.parent
BALLOTS_PATH     = BASE_DIR / "data" / "outputs" / "presidential_ballots.csv"
EFA_SCORES_PATH  = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
OUTPUT_DIR       = BASE_DIR / "data" / "outputs"

# ── Candidates (same order as generate_presidential_ballots.py) ────────────────
# Congressional stable: 9 pure cluster candidates
# Governor/Senate stable: 8 senate-derived blends (weights = national senate averages)
CANDIDATES = [
    # ── Congressional Stable (pure) ──
    {"code": "RH",      "name": "CON",     "primary": 0, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "MW",      "name": "SD",      "primary": 1, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "MRJ",     "name": "STY",     "primary": 2, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "BE",      "name": "NAT",     "primary": 3, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "CO",      "name": "LIB",     "primary": 4, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "DH",      "name": "REF",     "primary": 5, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "LK",      "name": "CTR",     "primary": 6, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "ZN",      "name": "DSA",     "primary": 8, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "JR",      "name": "PRG",     "primary": 9, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    # ── Governor/Senate Stable (senate-derived blends) ──
    {"code": "SD_STY",  "name": "SD/STY",  "primary": 1, "secondary": 2, "w_primary": 0.67, "w_secondary": 0.33},
    {"code": "CON_CTR", "name": "CON/CTR", "primary": 0, "secondary": 6, "w_primary": 0.62, "w_secondary": 0.38},
    {"code": "CON_SD",  "name": "CON/SD",  "primary": 0, "secondary": 1, "w_primary": 0.55, "w_secondary": 0.45},
    {"code": "CON_STY", "name": "CON/STY", "primary": 0, "secondary": 2, "w_primary": 0.58, "w_secondary": 0.42},
    {"code": "STY_REF", "name": "STY/REF", "primary": 2, "secondary": 5, "w_primary": 0.55, "w_secondary": 0.45},
    {"code": "SD_CON",  "name": "SD/CON",  "primary": 1, "secondary": 0, "w_primary": 0.52, "w_secondary": 0.48},
    {"code": "STY_SD",  "name": "STY/SD",  "primary": 2, "secondary": 1, "w_primary": 0.50, "w_secondary": 0.50},
    {"code": "REF_STY", "name": "REF/STY", "primary": 5, "secondary": 2, "w_primary": 0.63, "w_secondary": 0.37},
    # ── New senate-represented blends (senate mean weights) ──
    {"code": "CON_REF", "name": "CON/REF", "primary": 0, "secondary": 5, "w_primary": 0.69, "w_secondary": 0.31},
    {"code": "SD_LIB",  "name": "SD/LIB",  "primary": 1, "secondary": 4, "w_primary": 0.51, "w_secondary": 0.49},
    {"code": "SD_CTR",  "name": "SD/CTR",  "primary": 1, "secondary": 6, "w_primary": 0.57, "w_secondary": 0.43},
]
CAND_CODES = [c["code"] for c in CANDIDATES]
CAND_NAMES = {
    "RH":      "CON",
    "MW":      "SD",
    "MRJ":     "STY",
    "BE":      "NAT",
    "CO":      "LIB",
    "DH":      "REF",
    "LK":      "CTR",
    "ZN":      "DSA",
    "JR":      "PRG",
    "SD_STY":  "SD/STY",
    "CON_CTR": "CON/CTR",
    "CON_SD":  "CON/SD",
    "CON_STY": "CON/STY",
    "STY_REF": "STY/REF",
    "SD_CON":  "SD/CON",
    "STY_SD":  "STY/SD",
    "REF_STY": "REF/STY",
    "CON_REF": "CON/REF",
    "SD_LIB":  "SD/LIB",
    "SD_CTR":  "SD/CTR",
}
N_CANDIDATES = len(CANDIDATES)

PLATONIC_CODES  = {c["code"] for c in CANDIDATES if c["secondary"] is None}
STRADDLER_CODES = {c["code"] for c in CANDIDATES if c["secondary"] is not None}

# ── FIPS → abbreviation ────────────────────────────────────────────────────────
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

# ── Pod / state assignments ────────────────────────────────────────────────────
# 2028 cycle: Retail Six states are removed from their pod benches
RETAIL_SIX = {32, 28, 10, 19, 33, 72}   # NV, MS, DE, IA, NH, PR

POD_A_MAIN  = {48, 17, 53, 51, 49,  9}   # TX IL WA VA UT CT
POD_A_BENCH = {50, 54, 35, 15, 38, 11}   # VT WV NM HI ND DC

POD_B_MAIN  = {12, 42, 25, 47,  8, 24}   # FL PA MA TN CO MD
POD_B_BENCH = {16, 44,  5,  2, 21, 22, 40}  # ID RI AR AK + KY LA OK  (Iowa removed)

POD_C_MAIN  = {36, 13, 39,  4, 27, 18}   # NY GA OH AZ MN IN
POD_C_BENCH = {31, 30, 23}               # NE MT ME  (MS, DE removed)

POD_D_MAIN  = { 6, 37, 26, 34, 29, 45}   # CA NC MI NJ MO SC
POD_D_BENCH = {20, 46, 56,  1, 41, 55}   # KS SD WY + AL OR WI  (NH, PR, NV removed)

# Build FIPS → (pod, bench, retail) lookup
STATE_POD: dict[int, dict] = {}
for fips in RETAIL_SIX:
    STATE_POD[fips] = {"pod": "Retail", "bench": False, "retail_2028": True}
for fips in POD_A_MAIN:
    STATE_POD[fips] = {"pod": "A", "bench": False, "retail_2028": False}
for fips in POD_A_BENCH:
    STATE_POD[fips] = {"pod": "A", "bench": True,  "retail_2028": False}
for fips in POD_B_MAIN:
    STATE_POD[fips] = {"pod": "B", "bench": False, "retail_2028": False}
for fips in POD_B_BENCH:
    STATE_POD[fips] = {"pod": "B", "bench": True,  "retail_2028": False}
for fips in POD_C_MAIN:
    STATE_POD[fips] = {"pod": "C", "bench": False, "retail_2028": False}
for fips in POD_C_BENCH:
    STATE_POD[fips] = {"pod": "C", "bench": True,  "retail_2028": False}
for fips in POD_D_MAIN:
    STATE_POD[fips] = {"pod": "D", "bench": False, "retail_2028": False}
for fips in POD_D_BENCH:
    STATE_POD[fips] = {"pod": "D", "bench": True,  "retail_2028": False}


# ── Helpers ────────────────────────────────────────────────────────────────────

def first_surviving_choice(ballots_arr: np.ndarray, active_set: set[str]) -> np.ndarray:
    """
    For each ballot (row), return the index of the first candidate in active_set.
    ballots_arr: (N, 18) array of candidate codes (dtype=object or str)
    Returns (N,) array of candidate codes (the current effective first choice).
    """
    N = len(ballots_arr)
    result = np.empty(N, dtype=object)
    active_list = list(active_set)
    # build a set for fast lookup
    for i in range(N):
        for code in ballots_arr[i]:
            if code in active_set:
                result[i] = code
                break
    return result


def compute_vote_totals(
    fsc: np.ndarray,
    weights: np.ndarray,
    active_set: set[str],
) -> dict[str, float]:
    """Weighted vote total for each active candidate."""
    totals = {c: 0.0 for c in active_set}
    for code, w in zip(fsc, weights):
        if code in totals:
            totals[code] += w
    return totals


def droop_quota(total_votes: float, n_survivors: int) -> float:
    return total_votes / (n_survivors + 1) + 1


def winnow(
    ballots_arr: np.ndarray,
    weights: np.ndarray,
    active_set: set[str],
    survivors_target: int,
    label: str,
) -> tuple[set[str], list[dict], list[dict]]:
    """
    True STV primary with Gregory fractional surplus transfer.

    Candidates reaching the Droop quota are elected; their surplus votes
    transfer proportionally (Gregory method). When no candidate reaches
    quota the lowest is eliminated (alphabetical tiebreak). Continues
    until survivors_target candidates are elected or the field exhausts.

    Each phase receives the cumulative voter pool (growing across phases);
    ballot_weights start fresh from the supplied weights for this phase.

    Returns:
      finalists       — elected/surviving candidates after this phase
      results_rows    — list of dicts for primary_results_2028.csv
      transfer_rows   — list of dicts for transfer analysis
                        (transfer_type: "surplus" | "elimination")
    """
    active         = set(active_set)
    total_votes    = float(weights.sum())
    quota          = droop_quota(total_votes, survivors_target)
    ballot_weights = weights.astype(float).copy()

    elected:               list[str] = []
    elected_via_quota:     list[str] = []
    survived_default:      list[str] = []
    eliminated_this_round: list[str] = []
    results_rows:          list[dict] = []
    transfer_rows:         list[dict] = []

    while len(elected) < survivors_target and active:
        remaining_seats = survivors_target - len(elected)

        # If candidates remaining ≤ seats left, elect them all without a round
        if len(active) <= remaining_seats:
            survived_default.extend(sorted(active))
            elected.extend(sorted(active))
            active.clear()
            break

        fsc    = first_surviving_choice(ballots_arr, active)
        totals = compute_vote_totals(fsc, ballot_weights, active)

        # ── Elect highest at or above quota (alphabetical tiebreak) ──────────
        over_quota = sorted(
            [c for c in active if totals[c] >= quota],
            key=lambda c: (-totals[c], c),
        )
        if over_quota:
            winner         = over_quota[0]
            winner_votes   = totals[winner]
            surplus_factor = (winner_votes - quota) / winner_votes
            elected.append(winner)
            elected_via_quota.append(winner)

            # Gregory: scale ballot_weights for winner's supporters;
            # the retained (scaled) weight flows to next surviving choice
            temp_active = active - {winner}
            transfer_targets: dict[str, float] = defaultdict(float)
            for i in range(len(fsc)):
                if fsc[i] == winner:
                    ballot_weights[i] *= surplus_factor
                    for ranked_code in ballots_arr[i]:
                        if ranked_code in temp_active:
                            transfer_targets[ranked_code] += ballot_weights[i]
                            break

            active.discard(winner)
            for dest, votes in sorted(transfer_targets.items(), key=lambda x: -x[1]):
                transfer_rows.append({
                    "eliminated_code":         winner,
                    "eliminated_name":         CAND_NAMES[winner],
                    "winnowing_point":         label,
                    "transfer_type":           "surplus",
                    "dest_code":               dest,
                    "dest_name":               CAND_NAMES.get(dest, dest),
                    "transferred_votes":       round(votes, 4),
                    "pct_of_eliminated_total": round(votes / winner_votes * 100, 2)
                                               if winner_votes > 0 else 0.0,
                })

        # ── No quota reached → eliminate lowest ──────────────────────────────
        else:
            loser       = min(active, key=lambda c: (totals[c], c))
            loser_votes = totals[loser]
            eliminated_this_round.append(loser)
            active.discard(loser)

            transfer_targets = defaultdict(float)
            for i in range(len(fsc)):
                if fsc[i] == loser:
                    for ranked_code in ballots_arr[i]:
                        if ranked_code in active:
                            transfer_targets[ranked_code] += ballot_weights[i]
                            break
                    # exhausted ballots fall out naturally

            for dest, votes in sorted(transfer_targets.items(), key=lambda x: -x[1]):
                transfer_rows.append({
                    "eliminated_code":         loser,
                    "eliminated_name":         CAND_NAMES[loser],
                    "winnowing_point":         label,
                    "transfer_type":           "elimination",
                    "dest_code":               dest,
                    "dest_name":               CAND_NAMES.get(dest, dest),
                    "transferred_votes":       round(votes, 4),
                    "pct_of_eliminated_total": round(votes / loser_votes * 100, 2)
                                               if loser_votes > 0 else 0.0,
                })

    finalists = set(elected)

    # Final vote totals for output (ballot_weights reflect all surplus transfers)
    if finalists:
        final_fsc    = first_surviving_choice(ballots_arr, finalists)
        final_totals = compute_vote_totals(final_fsc, ballot_weights, finalists)
    else:
        final_totals = {}

    for code in CAND_CODES:
        is_finalist = code in finalists
        vote_total  = final_totals.get(code, 0.0) if is_finalist else 0.0
        if code in finalists:
            status = "surviving"
        elif code in eliminated_this_round:
            status = "eliminated_this_round"
        else:
            status = "previously_eliminated"
        results_rows.append({
            "winnowing_point":       label,
            "candidate_code":        code,
            "candidate_name":        CAND_NAMES[code],
            "vote_total":            round(vote_total, 4),
            "vote_pct":              round(vote_total / total_votes * 100, 4) if total_votes > 0 else 0.0,
            "status":                status,
            "quota_threshold":       round(quota, 4),
            "accumulated_pool_size": round(total_votes, 4),
        })

    print(f"\n  ── {label} winnowing (→ {survivors_target} survivors) ──")
    print(f"     Accumulated weighted votes: {total_votes:,.1f}")
    print(f"     Droop quota ({survivors_target}): {quota:,.2f}")
    print(f"     Elected via quota:  {', '.join(elected_via_quota) or 'none'}")
    print(f"     Survived (default): {', '.join(survived_default) or 'none'}")
    print(f"     Eliminated:         {', '.join(eliminated_this_round) or 'none'}")
    print(f"     Survivors:          {', '.join(sorted(finalists))}")

    return finalists, results_rows, transfer_rows


# ── Pod-level vote totals (for geographic breakdown) ──────────────────────────

def pod_vote_shares(
    ballots_arr: np.ndarray,
    weights: np.ndarray,
    pod_mask: np.ndarray,
    active_set: set[str],
    pod_label: str,
) -> list[dict]:
    """
    For ballots in pod_mask, compute weighted first-surviving-choice share.
    """
    fsc    = first_surviving_choice(ballots_arr[pod_mask], active_set)
    w_pod  = weights[pod_mask]
    totals = compute_vote_totals(fsc, w_pod, active_set)
    total_w = w_pod.sum()
    rows = []
    for code, votes in totals.items():
        rows.append({
            "candidate_code":         code,
            "pod":                    pod_label,
            "votes_from_pod":         round(votes, 4),
            "pod_total_votes":        round(total_w, 4),
            "pct_of_pod":             round(votes / total_w * 100, 4) if total_w > 0 else 0.0,
        })
    return rows


# ── Ranked Pairs (Tideman) ────────────────────────────────────────────────────

def ranked_pairs_winner(
    matchups: list[dict],
    candidates: list[str],
) -> tuple[str, list[dict]]:
    """
    Ranked Pairs (Tideman) algorithm.

    1. For every pair compute the directed defeat and its margin.
    2. Sort defeats by margin, largest first.
    3. Lock each defeat into the result graph unless doing so creates a cycle.
    4. The candidate with no locked defeats against them is the Ranked Pairs winner.

    Returns
    -------
    rp_winner : str  — candidate code, or 'none' if no unique winner
    annotated : list[dict] — original matchup rows augmented with:
        margin, margin_pct, lock_order, locked, rp_winner_overall
    """
    # Build directed defeats from pairwise totals
    defeats = []
    for idx, m in enumerate(matchups):
        a, b  = m["candidate_a"], m["candidate_b"]
        va, vb = m["votes_a_beats_b"], m["votes_b_beats_a"]
        if va >= vb:
            defeats.append({"winner": a, "loser": b, "margin": va - vb, "orig_idx": idx})
        else:
            defeats.append({"winner": b, "loser": a, "margin": vb - va, "orig_idx": idx})

    # Sort by margin descending; alphabetical winner as tiebreak
    defeats.sort(key=lambda x: (-x["margin"], x["winner"]))

    def creates_cycle(locked_edges: list[tuple], new_winner: str, new_loser: str) -> bool:
        """True if locking new_winner→new_loser would create a cycle."""
        reachable: set[str] = set()
        frontier = {new_loser}
        while frontier:
            node = frontier.pop()
            if node == new_winner:
                return True
            if node in reachable:
                continue
            reachable.add(node)
            for w, l in locked_edges:
                if w == node and l not in reachable:
                    frontier.add(l)
        return False

    locked_edges: list[tuple] = []
    lock_meta: dict[int, dict] = {d["orig_idx"]: {"lock_order": None, "locked": False}
                                   for d in defeats}

    for order, defeat in enumerate(defeats, start=1):
        idx = defeat["orig_idx"]
        lock_meta[idx]["lock_order"] = order
        if not creates_cycle(locked_edges, defeat["winner"], defeat["loser"]):
            locked_edges.append((defeat["winner"], defeat["loser"]))
            lock_meta[idx]["locked"] = True

    # Candidate with in-degree 0 in locked graph = Ranked Pairs winner
    losers     = {l for _, l in locked_edges}
    undefeated = [c for c in candidates if c not in losers]
    rp_winner  = undefeated[0] if len(undefeated) == 1 else "none"

    # Annotate original matchup rows
    annotated = []
    for idx, m in enumerate(matchups):
        total_v    = m["votes_a_beats_b"] + m["votes_b_beats_a"]
        raw_margin = abs(m["votes_a_beats_b"] - m["votes_b_beats_a"])
        annotated.append({
            **m,
            "margin":          round(raw_margin, 4),
            "margin_pct":      round(raw_margin / total_v * 100, 4) if total_v > 0 else 0.0,
            "lock_order":      lock_meta[idx]["lock_order"],
            "locked":          lock_meta[idx]["locked"],
            "rp_winner_overall": rp_winner,
        })

    return rp_winner, annotated


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Load ballots ───────────────────────────────────────────────────────────
    print("Loading presidential ballots…")
    ballot_df = pd.read_csv(BALLOTS_PATH, index_col="respondent_id")
    N = len(ballot_df)
    rank_cols = [f"rank_{k+1}" for k in range(N_CANDIDATES)]
    ballots_arr = ballot_df[rank_cols].values  # (N, 18) object array of codes
    print(f"  {N:,} ballots loaded")

    # ── Load EFA scores for inputstate + weights ───────────────────────────────
    print("Loading EFA scores…")
    efa = pd.read_csv(EFA_SCORES_PATH)
    assert len(efa) == N
    inputstate = efa["inputstate"].values.astype(int)
    weights    = efa["commonpostweight"].values.astype(float)

    # ── Build pod mask arrays ──────────────────────────────────────────────────
    def pod_mask(pods_and_retail: list[str]) -> np.ndarray:
        """Boolean mask for all respondents whose state is in the given pod list."""
        mask = np.zeros(N, dtype=bool)
        for i, fips in enumerate(inputstate):
            info = STATE_POD.get(fips)
            if info and info["pod"] in pods_and_retail:
                mask[i] = True
        return mask

    retail_mask = pod_mask(["Retail"])
    poda_mask   = pod_mask(["A"])
    podc_mask   = pod_mask(["C"])
    podb_mask   = pod_mask(["B"])
    podd_mask   = pod_mask(["D"])
    pod_bd_mask = podb_mask | podd_mask

    # States not assigned to any pod (not in our structure) — log them
    unassigned = {fips for fips in np.unique(inputstate) if fips not in STATE_POD}
    if unassigned:
        abbrs = [FIPS_TO_ABBR.get(f, f"FIPS{f}") for f in sorted(unassigned)]
        print(f"\n  WARNING: {len(unassigned)} states not assigned to any pod: {abbrs}")
        print("           These respondents will not participate in primary voting.")

    print(f"\n  Retail Six respondents:  {retail_mask.sum():,}  (weighted: {weights[retail_mask].sum():,.1f})")
    print(f"  Pod A respondents:       {poda_mask.sum():,}  (weighted: {weights[poda_mask].sum():,.1f})")
    print(f"  Pod C respondents:       {podc_mask.sum():,}  (weighted: {weights[podc_mask].sum():,.1f})")
    print(f"  Pod B respondents:       {podb_mask.sum():,}  (weighted: {weights[podb_mask].sum():,.1f})")
    print(f"  Pod D respondents:       {podd_mask.sum():,}  (weighted: {weights[podd_mask].sum():,.1f})")

    # ── Cumulative rolling STV ─────────────────────────────────────────────────
    all_results  = []
    all_transfers= []
    trajectory   = []  # per-phase vote totals for all 18 candidates
    geo_rows     = []  # pod-level vote shares for finalists

    active = set(CAND_CODES)

    # helper: record trajectory snapshot
    def snapshot(phase_label: str, mask: np.ndarray, current_active: set[str]):
        """Record vote totals for all candidates at this phase."""
        fsc    = first_surviving_choice(ballots_arr[mask], current_active)
        totals = compute_vote_totals(fsc, weights[mask], current_active)
        total_w = weights[mask].sum()
        for code in CAND_CODES:
            v = totals.get(code, 0.0)
            trajectory.append({
                "phase":          phase_label,
                "candidate_code": code,
                "candidate_name": CAND_NAMES[code],
                "raw_votes":      round(v, 4),
                "vote_pct":       round(v / total_w * 100, 4) if total_w > 0 else 0.0,
                "status":         "active" if code in current_active else "eliminated",
            })

    # ── PHASE 1: Retail Six ────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("PHASE 1: Retail Six")
    cum_mask = retail_mask.copy()
    print(f"  States: NV, MS, DE, IA, NH, PR")

    active, r_rows, t_rows = winnow(
        ballots_arr[cum_mask], weights[cum_mask],
        active, survivors_target=12, label="After_Retail_Six"
    )
    all_results  += r_rows
    all_transfers += t_rows
    snapshot("After_Retail_Six", cum_mask, active)

    # ── PHASE 2: Pod A ─────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("PHASE 2: Pod A")
    cum_mask = retail_mask | poda_mask
    print(f"  States: TX IL WA VA UT CT + VT WV NM HI ND DC")

    active, r_rows, t_rows = winnow(
        ballots_arr[cum_mask], weights[cum_mask],
        active, survivors_target=10, label="After_Pod_A"
    )
    all_results  += r_rows
    all_transfers += t_rows
    snapshot("After_Pod_A", cum_mask, active)

    # ── PHASE 3: Pod C ─────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("PHASE 3: Pod C")
    cum_mask = retail_mask | poda_mask | podc_mask
    print(f"  States: NY GA OH AZ MN IN + NE MT ME")

    active, r_rows, t_rows = winnow(
        ballots_arr[cum_mask], weights[cum_mask],
        active, survivors_target=8, label="After_Pod_C"
    )
    all_results  += r_rows
    all_transfers += t_rows
    snapshot("After_Pod_C", cum_mask, active)

    # ── PHASE 4: Pod B + Pod D ─────────────────────────────────────────────────
    print("\n" + "="*60)
    print("PHASE 4: Pod B + Pod D (combined)")
    cum_mask = retail_mask | poda_mask | podc_mask | pod_bd_mask
    print(f"  Pod B: FL PA MA TN CO MD + ID RI AR AK")
    print(f"  Pod D: CA NC MI NJ MO SC + KS SD WY")

    active, r_rows, t_rows = winnow(
        ballots_arr[cum_mask], weights[cum_mask],
        active, survivors_target=5, label="After_Pod_BD"
    )
    all_results  += r_rows
    all_transfers += t_rows
    snapshot("After_Pod_BD", cum_mask, active)

    finalists = sorted(active)
    print(f"\n{'='*60}")
    print(f"FINALISTS (5): {', '.join(finalists)}")
    print(f"{'='*60}")

    # ── Save primary results ───────────────────────────────────────────────────
    results_df = pd.DataFrame(all_results)
    results_out = OUTPUT_DIR / "primary_results_2028.csv"
    results_df.to_csv(results_out, index=False)
    print(f"\nSaved primary results → {results_out}  ({len(results_df)} rows)")

    # ── DIAGNOSTICS ────────────────────────────────────────────────────────────
    diag_sheets = {}

    # 1. Candidate Trajectories
    traj_df = pd.DataFrame(trajectory)
    diag_sheets["trajectories"] = traj_df

    # 2. Geographic Breakdown for finalists (by pod, full national ballots)
    full_mask = retail_mask | poda_mask | podc_mask | pod_bd_mask
    for pod_label, pmask in [
        ("Retail", retail_mask),
        ("A",      poda_mask),
        ("C",      podc_mask),
        ("B",      podb_mask),
        ("D",      podd_mask),
    ]:
        geo_rows += pod_vote_shares(
            ballots_arr, weights, pmask,
            set(finalists), pod_label
        )
    geo_df = pd.DataFrame(geo_rows)
    # add pct_of_finalist_total
    finalist_totals = (
        geo_df.groupby("candidate_code")["votes_from_pod"].sum().rename("finalist_national_total")
    )
    geo_df = geo_df.merge(finalist_totals, on="candidate_code")
    geo_df["pct_of_finalist_total"] = (
        geo_df["votes_from_pod"] / geo_df["finalist_national_total"] * 100
    ).round(2)
    diag_sheets["geo_breakdown"] = geo_df

    # 3. Straddler Analysis
    straddler_rows = []
    # for each straddler, compare to its primary-cluster platonic equivalent (if exists)
    platonic_by_cluster = {c["primary"]: c["code"]
                           for c in CANDIDATES if c["secondary"] is None}
    for cand in CANDIDATES:
        if cand["secondary"] is None:
            continue
        straddler = cand["code"]
        platonic_p = platonic_by_cluster.get(cand["primary"])  # primary platonic
        platonic_s = platonic_by_cluster.get(cand["secondary"])  # secondary platonic
        for pod_label, pmask in [
            ("Retail", retail_mask), ("A", poda_mask),
            ("C", podc_mask), ("B", podb_mask), ("D", podd_mask),
        ]:
            if pmask.sum() == 0:
                continue
            # use unweighted first-choice from full active (all 18, no eliminations)
            all_active = set(CAND_CODES)
            fsc_pod = first_surviving_choice(ballots_arr[pmask], all_active)
            w_pod   = weights[pmask]
            totals_pod = compute_vote_totals(fsc_pod, w_pod, all_active)
            total_w_pod = w_pod.sum()
            s_pct = totals_pod.get(straddler, 0.0) / total_w_pod * 100 if total_w_pod else 0
            p_pct = totals_pod.get(platonic_p, 0.0) / total_w_pod * 100 if (total_w_pod and platonic_p) else None
            ps_pct = totals_pod.get(platonic_s, 0.0) / total_w_pod * 100 if (total_w_pod and platonic_s) else None
            straddler_rows.append({
                "straddler_code":  straddler,
                "straddler_name":  CAND_NAMES[straddler],
                "platonic_code":   platonic_p or "",
                "platonic_name":   CAND_NAMES.get(platonic_p, "") if platonic_p else "",
                "platonic_secondary_code": platonic_s or "",
                "pod":             pod_label,
                "straddler_pct":   round(s_pct, 4),
                "platonic_pct":    round(p_pct, 4) if p_pct is not None else None,
                "platonic_secondary_pct": round(ps_pct, 4) if ps_pct is not None else None,
                "delta_vs_primary": round(s_pct - p_pct, 4) if p_pct is not None else None,
            })
    straddler_df = pd.DataFrame(straddler_rows)
    diag_sheets["straddler_analysis"] = straddler_df

    # 4. Transfer Analysis — top 3 destinations per eliminated candidate
    transfer_df = pd.DataFrame(all_transfers)
    if not transfer_df.empty:
        transfer_top3 = (
            transfer_df
            .sort_values(["eliminated_code", "winnowing_point", "transferred_votes"], ascending=[True, True, False])
            .groupby(["eliminated_code", "winnowing_point"])
            .head(3)
            .reset_index(drop=True)
        )
    else:
        transfer_top3 = transfer_df
    diag_sheets["transfer_analysis"] = transfer_top3

    # 5. Ranked Pairs (Tideman) among 5 finalists
    print("\nRunning Ranked Pairs (Tideman) among 5 finalists on full national ballot…")
    full_ballots  = ballots_arr  # all 45,707
    full_weights  = weights
    finalist_list = sorted(finalists)

    # ── Step 1: tally all pairwise matchups ────────────────────────────────────
    raw_matchups: list[dict] = []
    for i, ca in enumerate(finalist_list):
        for cb in finalist_list[i + 1:]:
            votes_a, votes_b = 0.0, 0.0
            for ballot, w in zip(full_ballots, full_weights):
                for code in ballot:
                    if code == ca:
                        votes_a += w
                        break
                    elif code == cb:
                        votes_b += w
                        break
            pairwise_winner = (ca if votes_a > votes_b else
                               (cb if votes_b > votes_a else "tie"))
            raw_matchups.append({
                "candidate_a":     ca,
                "candidate_b":     cb,
                "votes_a_beats_b": round(votes_a, 4),
                "votes_b_beats_a": round(votes_b, 4),
                "winner":          pairwise_winner,
            })

    # ── Step 2: Ranked Pairs resolution ────────────────────────────────────────
    rp_winner, annotated_matchups = ranked_pairs_winner(raw_matchups, finalist_list)

    condorcet_df = pd.DataFrame(annotated_matchups).sort_values("lock_order").reset_index(drop=True)

    # Print lock sequence
    print(f"\n  Ranked Pairs lock sequence (strongest margin first):")
    for _, row in condorcet_df.iterrows():
        a, b   = row["candidate_a"], row["candidate_b"]
        winner = row["winner"]
        loser  = b if winner == a else a
        lock_sym = "✓ LOCKED" if row["locked"] else "✗ skipped (cycle)"
        print(f"    [{int(row['lock_order'])}] {winner} > {loser}  "
              f"(margin {row['margin_pct']:.2f}%)  {lock_sym}")
    print(f"\n  Ranked Pairs winner: {rp_winner}")
    if rp_winner != "none":
        print(f"    → {CAND_NAMES.get(rp_winner, rp_winner)} is the Ranked Pairs winner")

    cw = rp_winner  # used in final summary below
    diag_sheets["condorcet"] = condorcet_df

    # ── Save diagnostics ───────────────────────────────────────────────────────
    diag_out = OUTPUT_DIR / "primary_diagnostics_2028.csv"
    # Save as a single CSV with a "sheet" column distinguishing sections
    combined_parts = []
    for sheet_name, df in diag_sheets.items():
        df2 = df.copy()
        df2.insert(0, "diagnostic", sheet_name)
        combined_parts.append(df2)
    diag_combined = pd.concat(combined_parts, ignore_index=True)
    diag_combined.to_csv(diag_out, index=False)
    print(f"\nSaved diagnostics → {diag_out}  ({len(diag_combined)} rows)")

    # ── Also save state pod assignments ───────────────────────────────────────
    pod_rows = []
    for fips, info in sorted(STATE_POD.items()):
        pod_rows.append({
            "state_fips":   fips,
            "state_abbr":   FIPS_TO_ABBR.get(fips, f"FIPS{fips}"),
            "pod":          info["pod"],
            "bench":        info["bench"],
            "retail_2028":  info["retail_2028"],
        })
    pod_df = pd.DataFrame(pod_rows)
    pod_out = OUTPUT_DIR / "state_pod_assignments.csv"
    pod_df.to_csv(pod_out, index=False)
    print(f"Saved pod assignments → {pod_out}  ({len(pod_df)} rows)")

    # ── Print summary ──────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)
    final_stage = results_df[results_df["winnowing_point"] == "After_Pod_BD"].copy()
    final_stage = final_stage.sort_values("vote_pct", ascending=False)
    print(final_stage[["candidate_code", "candidate_name", "vote_pct", "status"]].to_string(index=False))

    print(f"\nRanked Pairs winner among finalists: {cw}")
    if cw != "none":
        print(f"  → {CAND_NAMES.get(cw, cw)}")

    print("\n✓ Primary simulation complete.")


if __name__ == "__main__":
    main()

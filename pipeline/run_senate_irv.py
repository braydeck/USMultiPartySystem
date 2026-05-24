#!/usr/bin/env python3
"""
run_senate_irv.py
------------------
Alternative scenario: replaces the Ranked Pairs Condorcet final step with
Instant Runoff Voting (IRV).  Everything else is identical to
run_senate_simulation.py — same seed (42), same ballot generation, same STV
primary → 5 finalists.  Only the winner-selection among finalists differs.

Outputs (Claude/outputs/senate/ — irv_ prefix to avoid overwriting primaries):
  senate_irv_candidates.csv    — candidate pool per state (same as primary)
  senate_irv_primary.csv       — STV primary results (same as primary)
  senate_irv_rounds.csv        — IRV round-by-round detail per state
  senate_irv_composition.csv   — winner + runner-up per state
"""

import numpy as np
import pandas as pd
from pathlib import Path
from itertools import combinations

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent.parent
TYPOLOGY_PATH   = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
EFA_SCORES_PATH = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
OUTPUT_DIR      = BASE_DIR / "data" / "outputs" / "senate"

PARTY_ABBR      = {0:"CON", 1:"SD", 2:"STY", 3:"NAT", 4:"LIB",
                   5:"REF", 6:"CTR", 8:"DSA", 9:"PRG"}
ACTIVE_CLUSTERS = sorted(PARTY_ABBR.keys())
PROB_COLS       = [f"prob_cluster_{k}" for k in range(10)]

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

PURE_THRESHOLD       = 0.05
COOC_MIN_SHARE       = 0.04
WILDCARD_MIN_SHARE   = 0.15
WILDCARD_MIN_DIST    = 1.40
MAX_COOC_STRADDLERS  = 6
MAX_WILDCARDS        = 2
MAX_CANDIDATES       = 18
STV_SURVIVORS        = 5
MIN_RESPONDENTS      = 10

# Positional scoring: candidates have positions in 5-D factor space, voters
# score by Gaussian proximity to their own factor scores. See companion
# documentation in run_senate_simulation.py:score_candidates.
FACTOR_COLS      = ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]
POSITIONAL_SIGMA = 0.35
FACTOR_WEIGHTS   = np.array([1.000, 0.535, 0.081, 0.436, 1.050])  # η²-based: F1 F2 F3 F4 F5


# ═════════════════════════════════════════════════════════════════════════════
# 1 — Cluster centroid computation  (unchanged)
# ═════════════════════════════════════════════════════════════════════════════

def compute_cluster_centroids(efa_df, typology_df):
    factor_cols = ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]
    weights  = efa_df["commonpostweight"].values
    clusters = typology_df["cluster"].values.astype(int)
    centroids = np.zeros((10, 5), dtype=np.float64)
    for k in range(10):
        mask = clusters == k
        w_k  = weights[mask]
        if w_k.sum() > 0:
            for f, col in enumerate(factor_cols):
                centroids[k, f] = np.average(efa_df[col].values[mask], weights=w_k)
    return centroids


# ═════════════════════════════════════════════════════════════════════════════
# 2 — State candidate pool  (unchanged)
# ═════════════════════════════════════════════════════════════════════════════

def generate_state_candidates(prob_matrix, weights, cluster_centroids):
    total_weight = weights.sum()
    state_shares = {k: float(np.average(prob_matrix[:, k], weights=weights))
                    for k in ACTIVE_CLUSTERS}
    candidates = []
    seen_pairs  = set()

    for k in ACTIVE_CLUSTERS:
        if state_shares[k] >= PURE_THRESHOLD:
            code = PARTY_ABBR[k]
            candidates.append({
                "cand_code": code, "cand_label": code,
                "primary_cluster": k, "secondary_cluster": None,
                "w_primary": 1.0, "w_secondary": 0.0, "cand_type": "pure",
                "state_share_primary": round(state_shares[k], 4),
                "state_share_secondary": np.nan, "cooc_rate": np.nan,
            })
            seen_pairs.add(frozenset([k]))

    active_arr   = np.array(ACTIVE_CLUSTERS)
    active_probs = prob_matrix[:, active_arr]
    top2_local   = np.argsort(active_probs, axis=1)[:, -2:]
    top2_abs     = active_arr[top2_local]
    hi_clusters  = top2_abs[:, 1]
    lo_clusters  = top2_abs[:, 0]

    cooc_total = {}; cooc_ordered = {}
    for n in range(len(weights)):
        hi, lo, w = int(hi_clusters[n]), int(lo_clusters[n]), float(weights[n])
        cooc_total[frozenset([hi, lo])]  = cooc_total.get(frozenset([hi, lo]), 0.0) + w
        cooc_ordered[(hi, lo)]           = cooc_ordered.get((hi, lo), 0.0) + w

    cooc_list = sorted([(pair, w / total_weight) for pair, w in cooc_total.items()],
                       key=lambda x: -x[1])
    n_cooc = 0
    for pair_key, cooc_rate in cooc_list:
        if n_cooc >= MAX_COOC_STRADDLERS or pair_key in seen_pairs:
            continue
        pair_list = sorted(pair_key)
        i, j = pair_list[0], pair_list[1]
        if state_shares[i] < COOC_MIN_SHARE or state_shares[j] < COOC_MIN_SHARE:
            continue
        primary, secondary = (i, j) if state_shares[i] >= state_shares[j] else (j, i)
        p_w = cooc_ordered.get((primary, secondary), 0.0)
        s_w = cooc_ordered.get((secondary, primary), 0.0)
        denom = p_w + s_w
        w_primary = max(0.50, min(0.70, (p_w / denom) if denom > 0 else 0.55))
        label = f"{PARTY_ABBR[primary]}/{PARTY_ABBR[secondary]}"
        candidates.append({
            "cand_code": label, "cand_label": label,
            "primary_cluster": primary, "secondary_cluster": secondary,
            "w_primary": round(w_primary, 4), "w_secondary": round(1.0 - w_primary, 4),
            "cand_type": "cooc",
            "state_share_primary":   round(state_shares[primary], 4),
            "state_share_secondary": round(state_shares[secondary], 4),
            "cooc_rate": round(cooc_rate, 4),
        })
        seen_pairs.add(pair_key); n_cooc += 1

    wildcard_pool = []
    for ci, cj in combinations(ACTIVE_CLUSTERS, 2):
        if state_shares[ci] < WILDCARD_MIN_SHARE or state_shares[cj] < WILDCARD_MIN_SHARE:
            continue
        pair_key = frozenset([ci, cj])
        if pair_key in seen_pairs:
            continue
        dist = float(np.linalg.norm(cluster_centroids[ci] - cluster_centroids[cj]))
        if dist >= WILDCARD_MIN_DIST:
            primary, secondary = (ci, cj) if state_shares[ci] >= state_shares[cj] else (cj, ci)
            wildcard_pool.append({"primary": primary, "secondary": secondary,
                                  "dist": dist, "pair_key": pair_key})
    wildcard_pool.sort(key=lambda x: -x["dist"])
    n_wc = 0
    for wc in wildcard_pool:
        if n_wc >= MAX_WILDCARDS or len(candidates) >= MAX_CANDIDATES:
            break
        pair_key = wc["pair_key"]
        if pair_key in seen_pairs:
            continue
        p, s = wc["primary"], wc["secondary"]
        label = f"{PARTY_ABBR[p]}/{PARTY_ABBR[s]}"
        total_share = state_shares[p] + state_shares[s]
        w_p = max(0.55, min(0.80, (state_shares[p] / total_share) if total_share > 0 else 0.625))
        candidates.append({
            "cand_code": label, "cand_label": label,
            "primary_cluster": p, "secondary_cluster": s,
            "w_primary": round(w_p, 4), "w_secondary": round(1.0 - w_p, 4),
            "cand_type": "wildcard",
            "state_share_primary":   round(state_shares[p], 4),
            "state_share_secondary": round(state_shares[s], 4),
            "cooc_rate": np.nan,
        })
        seen_pairs.add(pair_key); n_wc += 1

    seen_labels = set(); deduped = []
    for c in candidates:
        if c["cand_label"] not in seen_labels:
            seen_labels.add(c["cand_label"]); deduped.append(c)
    return deduped[:MAX_CANDIDATES]


# ═════════════════════════════════════════════════════════════════════════════
# 3 — Ballot generation  (unchanged)
# ═════════════════════════════════════════════════════════════════════════════

def candidate_position(c, cluster_centroids):
    p = c["primary_cluster"]
    pos = c["w_primary"] * cluster_centroids[p]
    s = c["secondary_cluster"]
    if s is not None:
        pos = pos + c["w_secondary"] * cluster_centroids[int(s)]
    return pos


def score_candidates(voter_factors, candidates, cluster_centroids, sigma=POSITIONAL_SIGMA):
    """Gaussian proximity in 5-D factor space; see run_senate_simulation.py."""
    cand_positions = np.stack([candidate_position(c, cluster_centroids) for c in candidates])
    diff = voter_factors[:, None, :] - cand_positions[None, :, :]
    dist_sq = ((diff ** 2) * FACTOR_WEIGHTS).sum(axis=2)
    return np.exp(-dist_sq / (2.0 * sigma ** 2))


def generate_state_ballots(scores, cand_codes, rng):
    N, M = scores.shape
    EPSILON = 1e-10
    ballots = np.empty((N, M), dtype=object)
    cand_arr = np.array(cand_codes, dtype=object)
    for i in range(N):
        probs = scores[i] + EPSILON
        probs /= probs.sum()
        ballots[i] = cand_arr[rng.choice(M, size=M, replace=False, p=probs)]
    return ballots


# ═════════════════════════════════════════════════════════════════════════════
# 4 — STV primary  (unchanged)
# ═════════════════════════════════════════════════════════════════════════════

def first_surviving_choice(ballots_arr, active_set):
    N, M = ballots_arr.shape
    result = np.full(N, "__exhausted__", dtype=object)
    for i in range(N):
        for j in range(M):
            if ballots_arr[i, j] in active_set:
                result[i] = ballots_arr[i, j]
                break
    return result


def droop_quota(total_votes, n_seats):
    return total_votes / (n_seats + 1)


def compute_vote_totals(fsc, weights, active_set):
    return {code: float(weights[fsc == code].sum()) for code in active_set}


def winnow(ballots_arr, weights, active_set, target, label, cand_names):
    """
    True STV primary with Gregory fractional surplus transfer.

    Candidates reaching the Droop quota are elected and their surplus votes
    transfer proportionally (Gregory method).  When no candidate reaches quota
    the lowest is eliminated (alphabetical tiebreak).  Continues until
    `target` candidates are elected or the field is exhausted.
    """
    active         = set(active_set)
    total_votes    = float(weights.sum())
    quota          = droop_quota(total_votes, target)
    ballot_weights = weights.astype(float).copy()
    elected: list  = []

    while len(elected) < target and active:
        remaining_seats = target - len(elected)
        if len(active) <= remaining_seats:
            elected.extend(sorted(active))
            active.clear()
            break

        fsc    = first_surviving_choice(ballots_arr, active)
        totals = compute_vote_totals(fsc, ballot_weights, active)

        over_quota = sorted(
            [c for c in active if totals[c] >= quota],
            key=lambda c: (-totals[c], c),
        )
        if over_quota:
            winner = over_quota[0]
            elected.append(winner)
            surplus_factor = (totals[winner] - quota) / totals[winner]
            for i in range(len(fsc)):
                if fsc[i] == winner:
                    ballot_weights[i] *= surplus_factor
            active.discard(winner)
        else:
            loser = min(active, key=lambda c: (totals[c], c))
            active.discard(loser)

    finalists = set(elected)

    if finalists:
        final_fsc    = first_surviving_choice(ballots_arr, finalists)
        final_totals = compute_vote_totals(final_fsc, ballot_weights, finalists)
    else:
        final_totals = {}

    results_rows = []
    for code in sorted(active_set):
        is_finalist = code in finalists
        vote_total  = final_totals.get(code, 0.0) if is_finalist else 0.0
        results_rows.append({
            "winnowing_point": label,
            "cand_code":       code,
            "cand_label":      cand_names.get(code, code),
            "vote_total":      round(vote_total, 2),
            "vote_pct":        round(vote_total / total_votes * 100, 4) if total_votes > 0 else 0.0,
            "quota_threshold": round(quota, 2),
            "status":          "surviving" if is_finalist else "eliminated",
        })
    return finalists, results_rows


# ═════════════════════════════════════════════════════════════════════════════
# 5 — IRV winner selection  (replaces Ranked Pairs)
# ═════════════════════════════════════════════════════════════════════════════

def irv_winner(ballots_arr: np.ndarray, weights: np.ndarray,
               finalists: list[str]) -> tuple[str, str, list[dict]]:
    """
    Instant Runoff Voting among finalists.
    Uses the full ballot array — first_surviving_choice filters to finalists.
    Tiebreak: alphabetical (eliminate lowest code first).

    Returns:
        winner      — code of IRV winner
        runner_up   — last candidate eliminated before winner
        rounds      — list of round dicts for audit trail
    """
    active = set(finalists)
    total_w = float(weights.sum())
    rounds  = []
    elimination_order = []

    while len(active) > 1:
        fsc    = first_surviving_choice(ballots_arr, active)
        totals = {code: float(weights[fsc == code].sum()) for code in active}

        # Majority check
        leader = max(active, key=lambda c: totals[c])
        if totals[leader] > total_w / 2:
            rounds.append({
                "round":     len(rounds) + 1,
                "active":    sorted(active),
                "totals":    {c: round(totals[c], 4) for c in sorted(active)},
                "pcts":      {c: round(totals[c] / total_w * 100, 4) for c in sorted(active)},
                "eliminated": None,
            })
            break

        # Eliminate lowest (alphabetical tiebreak)
        loser = min(active, key=lambda c: (totals[c], c))
        rounds.append({
            "round":     len(rounds) + 1,
            "active":    sorted(active),
            "totals":    {c: round(totals[c], 4) for c in sorted(active)},
            "pcts":      {c: round(totals[c] / total_w * 100, 4) for c in sorted(active)},
            "eliminated": loser,
        })
        elimination_order.append(loser)
        active.discard(loser)

    winner    = max(active, key=lambda c: totals[c]) if active else "none"
    runner_up = elimination_order[-1] if elimination_order else "none"
    return winner, runner_up, rounds


# ═════════════════════════════════════════════════════════════════════════════
# 6 — Per-state election runner  (IRV variant)
# ═════════════════════════════════════════════════════════════════════════════

def run_state_election(state_fips, prob_matrix, voter_factors, weights, cluster_centroids, rng):
    state_abbr = FIPS_TO_ABBR.get(int(state_fips), f"FIPS{int(state_fips)}")
    N = len(prob_matrix)
    if N < MIN_RESPONDENTS:
        return None

    cands = generate_state_candidates(prob_matrix, weights, cluster_centroids)
    if len(cands) < 2:
        return None

    cand_codes = [c["cand_code"] for c in cands]
    cand_names = {c["cand_code"]: c["cand_label"] for c in cands}
    M = len(cands)

    scores  = score_candidates(voter_factors, cands, cluster_centroids)
    ballots = generate_state_ballots(scores, cand_codes, rng)

    target = min(STV_SURVIVORS, M)
    if M <= target:
        finalists    = set(cand_codes)
        total_votes  = float(weights.sum())
        fsc          = first_surviving_choice(ballots, finalists)
        totals       = compute_vote_totals(fsc, weights, finalists)
        results_rows = [{
            "winnowing_point": state_abbr,
            "cand_code":       code,
            "cand_label":      cand_names[code],
            "vote_total":      round(totals.get(code, 0.0), 2),
            "vote_pct":        round(totals.get(code, 0.0) / total_votes * 100, 4),
            "quota_threshold": round(droop_quota(total_votes, target), 2),
            "status":          "surviving",
        } for code in cand_codes]
    else:
        finalists, results_rows = winnow(
            ballots, weights, set(cand_codes), target, state_abbr, cand_names
        )

    finalist_list = sorted(finalists)

    # ── IRV (replaces Ranked Pairs) ───────────────────────────────────────
    if len(finalist_list) < 2:
        winner    = finalist_list[0] if finalist_list else "none"
        runner_up = "none"
        irv_rounds = []
    else:
        winner, runner_up, irv_rounds = irv_winner(ballots, weights, finalist_list)

    # Attach metadata to primary results
    cand_type_map    = {c["cand_code"]: c["cand_type"] for c in cands}
    cand_cluster_map = {c["cand_code"]: (c["primary_cluster"], c["secondary_cluster"])
                        for c in cands}
    for row in results_rows:
        code = row["cand_code"]
        row["cand_type"]          = cand_type_map.get(code, "unknown")
        row["primary_cluster"], row["secondary_cluster"] = cand_cluster_map.get(code, (-1, None))
        row["state_fips"]         = int(state_fips)
        row["state_abbr"]         = state_abbr

    for c in cands:
        c["state_fips"] = int(state_fips); c["state_abbr"] = state_abbr

    # Annotate IRV rounds with state info
    irv_rows = []
    for rnd in irv_rounds:
        for code in finalist_list:
            if code in rnd["totals"]:
                irv_rows.append({
                    "state_fips":     int(state_fips),
                    "state_abbr":     state_abbr,
                    "round":          rnd["round"],
                    "candidate_code": code,
                    "candidate_label": cand_names.get(code, code),
                    "vote_total":     rnd["totals"][code],
                    "vote_pct":       rnd["pcts"][code],
                    "eliminated":     (rnd["eliminated"] == code),
                    "irv_winner":     winner,
                })

    # Composition row — includes runner_up
    winner_cand = next((c for c in cands if c["cand_code"] == winner), None)
    runner_cand = next((c for c in cands if c["cand_code"] == runner_up), None)
    finalist_results = {r["cand_code"]: r for r in results_rows if r["cand_code"] in finalists}

    comp_row = {
        "state_fips":                  int(state_fips),
        "state_abbr":                  state_abbr,
        "winner_code":                 winner,
        "winner_label":                cand_names.get(winner, winner),
        "winner_type":                 winner_cand["cand_type"] if winner_cand else "unknown",
        "winner_primary_cluster":      winner_cand["primary_cluster"] if winner_cand else -1,
        "winner_secondary_cluster":    winner_cand["secondary_cluster"] if winner_cand else None,
        "runner_up_code":              runner_up,
        "runner_up_label":             cand_names.get(runner_up, runner_up),
        "runner_up_type":              runner_cand["cand_type"] if runner_cand else "unknown",
        "runner_up_primary_cluster":   runner_cand["primary_cluster"] if runner_cand else -1,
        "runner_up_secondary_cluster": runner_cand["secondary_cluster"] if runner_cand else None,
        "n_irv_rounds":                len(irv_rounds),
        "total_weighted_respondents":  round(float(weights.sum()), 2),
        "n_candidates_in_race":        M,
        "n_finalists":                 len(finalist_list),
    }
    for code in finalist_list:
        r = finalist_results.get(code)
        comp_row[f"finalist_{code}_pct"] = r["vote_pct"] if r else 0.0

    return {
        "state_fips":   int(state_fips),
        "state_abbr":   state_abbr,
        "candidates":   cands,
        "results_rows": results_rows,
        "irv_rows":     irv_rows,
        "comp_row":     comp_row,
        "winner":       winner,
        "runner_up":    runner_up,
        "finalists":    finalist_list,
        "n_candidates": M,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 7 — Main
# ═════════════════════════════════════════════════════════════════════════════

def main():
    rng = np.random.default_rng(42)   # same seed as primary simulation
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading data…")
    typology = pd.read_csv(TYPOLOGY_PATH)
    efa      = pd.read_csv(EFA_SCORES_PATH)
    assert len(typology) == len(efa)

    prob_matrix   = typology[PROB_COLS].values.astype(np.float64)
    voter_factors = efa[FACTOR_COLS].values.astype(np.float64)
    inputstate    = efa["inputstate"].values.astype(int)
    weights       = efa["commonpostweight"].values.astype(np.float64)

    print("Computing cluster centroids…")
    cluster_centroids = compute_cluster_centroids(efa, typology)

    all_states = sorted(np.unique(inputstate))
    run_states = [s for s in all_states if s != 72]
    print(f"\nRunning IRV senate elections for {len(run_states)} states/DC…\n")
    print(f"  {'St':4s}  {'N':>5s}  {'Cands':>5s}  {'Finalists':<40s}  Winner → Runner-up")
    print(f"  {'-'*90}")

    all_candidates  = []
    all_primary     = []
    all_irv         = []
    all_composition = []

    for state_fips in run_states:
        mask           = inputstate == state_fips
        state_probs    = prob_matrix[mask]
        state_factors  = voter_factors[mask]
        state_weights  = weights[mask]

        result = run_state_election(
            state_fips, state_probs, state_factors, state_weights, cluster_centroids, rng
        )

        abbr = FIPS_TO_ABBR.get(int(state_fips), f"FIPS{state_fips}")
        if result is None:
            print(f"  {abbr:4s}  SKIPPED")
            continue

        all_candidates.extend(result["candidates"])
        all_primary.extend(result["results_rows"])
        all_irv.extend(result["irv_rows"])
        all_composition.append(result["comp_row"])

        finalists_str = ", ".join(result["finalists"])
        if len(finalists_str) > 40:
            finalists_str = finalists_str[:37] + "…"
        print(f"  {result['state_abbr']:4s}  {mask.sum():>5d}  {result['n_candidates']:>5d}  "
              f"{finalists_str:<40s}  {result['winner']} → {result['runner_up']}")

    # ── Save outputs ──────────────────────────────────────────────────────────
    print(f"\nSaving to {OUTPUT_DIR} (irv_ prefix)…")

    cands_df = pd.DataFrame(all_candidates)
    col_order = ["state_fips", "state_abbr", "cand_code", "cand_label",
                 "primary_cluster", "secondary_cluster", "w_primary", "w_secondary",
                 "cand_type", "state_share_primary", "state_share_secondary", "cooc_rate"]
    cands_df = cands_df[[c for c in col_order if c in cands_df.columns]]
    cands_df.to_csv(OUTPUT_DIR / "senate_irv_candidates.csv", index=False)
    print(f"  senate_irv_candidates.csv:   {len(cands_df):,} rows")

    primary_df = pd.DataFrame(all_primary)
    pri_cols = ["state_fips", "state_abbr", "cand_code", "cand_label", "cand_type",
                "primary_cluster", "secondary_cluster",
                "vote_total", "vote_pct", "quota_threshold", "status", "winnowing_point"]
    primary_df = primary_df[[c for c in pri_cols if c in primary_df.columns]]
    primary_df.to_csv(OUTPUT_DIR / "senate_irv_primary.csv", index=False)
    print(f"  senate_irv_primary.csv:      {len(primary_df):,} rows")

    irv_df = pd.DataFrame(all_irv) if all_irv else pd.DataFrame()
    irv_df.to_csv(OUTPUT_DIR / "senate_irv_rounds.csv", index=False)
    print(f"  senate_irv_rounds.csv:       {len(irv_df):,} rows")

    comp_df = pd.DataFrame(all_composition).sort_values("state_fips")
    base_cols = ["state_fips", "state_abbr",
                 "winner_code", "winner_label", "winner_type",
                 "winner_primary_cluster", "winner_secondary_cluster",
                 "runner_up_code", "runner_up_label", "runner_up_type",
                 "runner_up_primary_cluster", "runner_up_secondary_cluster",
                 "n_irv_rounds", "total_weighted_respondents",
                 "n_candidates_in_race", "n_finalists"]
    pct_cols = sorted(c for c in comp_df.columns if c.startswith("finalist_") and c.endswith("_pct"))
    comp_df[[c for c in base_cols if c in comp_df.columns] + pct_cols]\
        .to_csv(OUTPUT_DIR / "senate_irv_composition.csv", index=False)
    print(f"  senate_irv_composition.csv:  {len(comp_df):,} rows")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("SENATE IRV COMPOSITION")
    print(f"{'='*60}")
    winner_counts = comp_df["winner_label"].value_counts()
    for lbl, cnt in winner_counts.items():
        bar = "█" * cnt
        print(f"  {lbl:<12} {cnt:2d}  {bar}")
    print(f"  {'TOTAL':<12} {winner_counts.sum():2d}")

    print(f"\n{'='*60}")
    print("STATE-BY-STATE  (Winner / Runner-up)")
    print(f"{'='*60}")
    for _, row in comp_df.sort_values("state_abbr").iterrows():
        print(f"  {row['state_abbr']:<4}  {row['winner_label']:<14} / {row['runner_up_label']}")

    print("\n✓ Senate IRV complete.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
run_senate_simulation.py
-------------------------
State-by-state senate simulation (single election, one senator per state).

For each state with CES respondents:
  1. Generate a state-specific candidate pool (pure + co-occurrence + wild card), up to 18
  2. Generate Plackett-Luce ranked ballots for every respondent in that state
  3. Run STV elimination → 5 finalists
  4. Run Ranked Pairs Condorcet among finalists → 1 senator

Outputs (Claude/outputs/senate/):
  state_senate_candidates.csv   — candidate pool per state
  senate_primary_results.csv    — STV results for all states
  senate_condorcet_results.csv  — Ranked Pairs detail for all states
  senate_composition.csv        — one row per state (senator + vote shares)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from itertools import combinations

# ── Paths ──────────────────────────────────────────────────────────────────────
# pure_only/ variant: pure-cluster candidates only (no cooc, no wildcard).
# Lives one directory deeper than the standard pipeline, so BASE_DIR goes up 3.
BASE_DIR        = Path(__file__).parent.parent.parent
TYPOLOGY_PATH   = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
EFA_SCORES_PATH = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
OUTPUT_DIR      = BASE_DIR / "data" / "outputs" / "pure_only" / "senate"

# ── Party abbreviations (C7 Blue Dogs excluded — permanently dissolved) ────────
PARTY_ABBR      = {0:"CON", 1:"SD", 2:"STY", 3:"NAT", 4:"LIB",
                   5:"REF", 6:"CTR", 8:"DSA", 9:"PRG"}
ACTIVE_CLUSTERS = sorted(PARTY_ABBR.keys())   # [0,1,2,3,4,5,6,8,9]
PROB_COLS       = [f"prob_cluster_{k}" for k in range(10)]

# ── FIPS → state abbreviation ─────────────────────────────────────────────────
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

# ── Candidate generation thresholds ───────────────────────────────────────────
PURE_THRESHOLD       = 0.05   # min weighted mean prob_cluster to qualify as pure
COOC_MIN_SHARE       = 0.04   # min cluster share for co-occurrence pair eligibility
WILDCARD_MIN_SHARE   = 0.15   # both clusters need ≥15% state share for wild card
WILDCARD_MIN_DIST    = 1.40   # min factor-space distance to qualify as cross-aisle
MAX_COOC_STRADDLERS  = 6      # max co-occurrence straddlers per state
MAX_WILDCARDS        = 2      # max wild card candidates per state
MAX_CANDIDATES       = 18     # hard cap on candidates per state
STV_SURVIVORS        = 5      # STV primary winnows to this many finalists
MIN_RESPONDENTS      = 10     # skip state if fewer than this many CES respondents

# ── Positional scoring ────────────────────────────────────────────────────────
# Candidates have positions in 5-D factor space (weighted blend of cluster
# centroids per w_primary / w_secondary). Voters score candidates by Gaussian
# proximity to their own factor scores: score = exp(-‖v - c‖² / (2 σ²)).
FACTOR_COLS    = ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]
POSITIONAL_SIGMA = 0.35
FACTOR_WEIGHTS   = np.array([1.000, 0.535, 0.081, 0.436, 1.050])  # η²-based: F1 F2 F3 F4 F5


# ═════════════════════════════════════════════════════════════════════════════
# 1 — Cluster centroid computation
# ═════════════════════════════════════════════════════════════════════════════

def compute_cluster_centroids(efa_df: pd.DataFrame,
                               typology_df: pd.DataFrame) -> np.ndarray:
    """
    Weighted mean of FS_F1–FS_F5 per cluster (0–9).
    Returns (10, 5) float64 array.
    """
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
# 2 — State candidate pool generation
# ═════════════════════════════════════════════════════════════════════════════

def generate_state_candidates(prob_matrix: np.ndarray,
                               weights: np.ndarray,
                               cluster_centroids: np.ndarray) -> list[dict]:
    """
    Build up to MAX_CANDIDATES candidates for a single state.
    Mix: pure (dominant clusters) + co-occurrence straddlers + wild card cross-aisle.
    Returns list of candidate dicts.
    """
    total_weight = weights.sum()

    # Weighted mean cluster share for each active cluster
    state_shares = {k: float(np.average(prob_matrix[:, k], weights=weights))
                    for k in ACTIVE_CLUSTERS}

    candidates: list[dict] = []
    seen_pairs: set = set()   # frozenset keys for deduplication

    # ── Step A: Pure candidates ───────────────────────────────────────────────
    # PURE-ONLY VARIANT: lower the pure threshold so every cluster with any
    # meaningful share competes. The mixed pipeline filtered pures at 5% to make
    # room for cooc/wildcard candidates; here we want the full pure bench.
    pure_threshold_pure_only = 0.02
    for k in ACTIVE_CLUSTERS:
        if state_shares[k] >= pure_threshold_pure_only:
            code = PARTY_ABBR[k]
            candidates.append({
                "cand_code":             code,
                "cand_label":            code,
                "primary_cluster":       k,
                "secondary_cluster":     None,
                "w_primary":             1.0,
                "w_secondary":           0.0,
                "cand_type":             "pure",
                "state_share_primary":   round(state_shares[k], 4),
                "state_share_secondary": np.nan,
                "cooc_rate":             np.nan,
            })
            seen_pairs.add(frozenset([k]))

    # PURE-ONLY VARIANT: skip Step B (cooc) and Step C (wildcard) entirely.
    return candidates[:MAX_CANDIDATES]

    # ── Step B: Co-occurrence straddlers ──────────────────────────────────────
    active_arr   = np.array(ACTIVE_CLUSTERS)             # shape (9,)
    active_probs = prob_matrix[:, active_arr]             # (N, 9)
    top2_local   = np.argsort(active_probs, axis=1)[:, -2:]   # col0=2nd, col1=highest
    top2_abs     = active_arr[top2_local]                # (N, 2) cluster indices

    hi_clusters = top2_abs[:, 1]   # each respondent's top cluster
    lo_clusters = top2_abs[:, 0]   # each respondent's second cluster

    cooc_total   = {}   # frozenset({i,j}) → cumulative weight
    cooc_ordered = {}   # (hi, lo)         → weight (hi = primary/highest)

    for n in range(len(weights)):
        hi = int(hi_clusters[n])
        lo = int(lo_clusters[n])
        w  = float(weights[n])
        cooc_total[frozenset([hi, lo])]  = cooc_total.get(frozenset([hi, lo]),  0.0) + w
        cooc_ordered[(hi, lo)]           = cooc_ordered.get((hi, lo), 0.0) + w

    cooc_list = sorted(
        [(pair, w / total_weight) for pair, w in cooc_total.items()],
        key=lambda x: -x[1]
    )

    n_cooc = 0
    for pair_key, cooc_rate in cooc_list:
        if n_cooc >= MAX_COOC_STRADDLERS:
            break
        if pair_key in seen_pairs:
            continue
        pair_list = sorted(pair_key)
        i, j = pair_list[0], pair_list[1]
        if state_shares[i] < COOC_MIN_SHARE or state_shares[j] < COOC_MIN_SHARE:
            continue

        # Primary = whichever has higher state share
        primary, secondary = (i, j) if state_shares[i] >= state_shares[j] else (j, i)

        # w_primary from conditional split; clamp to [0.50, 0.70]
        p_w   = cooc_ordered.get((primary, secondary), 0.0)
        s_w   = cooc_ordered.get((secondary, primary), 0.0)
        denom = p_w + s_w
        w_primary = (p_w / denom) if denom > 0 else 0.55
        w_primary = max(0.50, min(0.70, w_primary))

        label = f"{PARTY_ABBR[primary]}/{PARTY_ABBR[secondary]}"
        candidates.append({
            "cand_code":             label,
            "cand_label":            label,
            "primary_cluster":       primary,
            "secondary_cluster":     secondary,
            "w_primary":             round(w_primary, 4),
            "w_secondary":           round(1.0 - w_primary, 4),
            "cand_type":             "cooc",
            "state_share_primary":   round(state_shares[primary], 4),
            "state_share_secondary": round(state_shares[secondary], 4),
            "cooc_rate":             round(cooc_rate, 4),
        })
        seen_pairs.add(pair_key)
        n_cooc += 1

    # ── Step C: Wild card cross-aisle straddlers ──────────────────────────────
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

    wildcard_pool.sort(key=lambda x: -x["dist"])   # most cross-aisle first
    n_wc = 0
    for wc in wildcard_pool:
        if n_wc >= MAX_WILDCARDS or len(candidates) >= MAX_CANDIDATES:
            break
        pair_key = wc["pair_key"]
        if pair_key in seen_pairs:
            continue
        p, s  = wc["primary"], wc["secondary"]
        label = f"{PARTY_ABBR[p]}/{PARTY_ABBR[s]}"
        # State-proportional weight: primary party dominates, clamped to [0.55, 0.80]
        total_share = state_shares[p] + state_shares[s]
        w_p = (state_shares[p] / total_share) if total_share > 0 else 0.625
        w_p = max(0.55, min(0.80, w_p))
        candidates.append({
            "cand_code":             label,
            "cand_label":            label,
            "primary_cluster":       p,
            "secondary_cluster":     s,
            "w_primary":             round(w_p, 4),
            "w_secondary":           round(1.0 - w_p, 4),
            "cand_type":             "wildcard",
            "state_share_primary":   round(state_shares[p], 4),
            "state_share_secondary": round(state_shares[s], 4),
            "cooc_rate":             np.nan,
        })
        seen_pairs.add(pair_key)
        n_wc += 1

    # ── Step D: Deduplicate by label; cap at MAX_CANDIDATES ───────────────────
    seen_labels: set = set()
    deduped = []
    for c in candidates:
        if c["cand_label"] not in seen_labels:
            seen_labels.add(c["cand_label"])
            deduped.append(c)

    return deduped[:MAX_CANDIDATES]


# ═════════════════════════════════════════════════════════════════════════════
# 3 — Ballot generation (Plackett-Luce)
# ═════════════════════════════════════════════════════════════════════════════

def candidate_position(c: dict, cluster_centroids: np.ndarray) -> np.ndarray:
    """Candidate's location in 5-D factor space.

    Pure candidate sits on its cluster centroid; coalition candidate sits at
    w_primary * centroid_primary + w_secondary * centroid_secondary. A REF/STY
    candidate at w_primary=0.7 is 30% of the way from REF toward STY in factor
    space — a literal position, not a discount factor on cluster membership.
    """
    p = c["primary_cluster"]
    pos = c["w_primary"] * cluster_centroids[p]
    s = c["secondary_cluster"]
    if s is not None:
        pos = pos + c["w_secondary"] * cluster_centroids[int(s)]
    return pos


def score_candidates(voter_factors: np.ndarray,
                      candidates: list[dict],
                      cluster_centroids: np.ndarray,
                      sigma: float = POSITIONAL_SIGMA) -> np.ndarray:
    """Build (N, M) score matrix via Gaussian proximity in 5-D factor space.

    score[i, j] = exp(-‖voter_factors[i] - cand_position[j]‖² / (2 σ²))

    Replaces the prior cluster-membership formulation
    (score = w_p · p_primary + w_s · p_secondary), which gave pure candidates
    a 1.0 multiplier on their own cluster and made coalition candidates
    structurally unable to compete for first-preference votes. Positional
    scoring lets a voter near the STY centroid rank SD/STY and REF/STY
    symmetrically based on actual factor-space proximity, not on a label
    asymmetry hidden inside the score weights.
    """
    N = len(voter_factors)
    M = len(candidates)
    cand_positions = np.stack([candidate_position(c, cluster_centroids) for c in candidates])
    # (N, 1, 5) - (1, M, 5) -> (N, M, 5) -> (N, M)
    diff = voter_factors[:, None, :] - cand_positions[None, :, :]
    dist_sq = ((diff ** 2) * FACTOR_WEIGHTS).sum(axis=2)
    return np.exp(-dist_sq / (2.0 * sigma ** 2))


def generate_state_ballots(scores: np.ndarray,
                            cand_codes: list[str],
                            rng: np.random.Generator) -> np.ndarray:
    """
    Plackett-Luce sampling.
    Returns (N, M) object array where each row is a ranked list of candidate codes.
    """
    N, M  = scores.shape
    EPSILON = 1e-10
    ballots = np.empty((N, M), dtype=object)
    cand_arr = np.array(cand_codes, dtype=object)
    for i in range(N):
        probs = scores[i] + EPSILON
        probs /= probs.sum()
        ballots[i] = cand_arr[rng.choice(M, size=M, replace=False, p=probs)]
    return ballots


# ═════════════════════════════════════════════════════════════════════════════
# 4 — STV election engine
# ═════════════════════════════════════════════════════════════════════════════

def first_surviving_choice(ballots_arr: np.ndarray, active_set: set) -> np.ndarray:
    """Return each ballot's first active-candidate choice (or '__exhausted__')."""
    N, M = ballots_arr.shape
    result = np.empty(N, dtype=object)
    for i in range(N):
        result[i] = "__exhausted__"
        for j in range(M):
            if ballots_arr[i, j] in active_set:
                result[i] = ballots_arr[i, j]
                break
    return result


def compute_vote_totals(fsc: np.ndarray,
                         weights: np.ndarray,
                         active_set: set) -> dict:
    """Weighted tally per active candidate from first-surviving-choice array."""
    totals = {c: 0.0 for c in active_set}
    for code, w in zip(fsc, weights):
        if code in totals:
            totals[code] += w
    return totals


def droop_quota(total_votes: float, n_survivors: int) -> float:
    return total_votes / (n_survivors + 1) + 1


def winnow(ballots_arr: np.ndarray,
           weights: np.ndarray,
           active_set: set,
           survivors_target: int,
           label: str,
           cand_names: dict) -> tuple[set, list]:
    """
    True STV primary with Gregory fractional surplus transfer.

    Candidates reaching the Droop quota are elected and their surplus votes
    transfer proportionally (Gregory method).  When no candidate reaches quota
    the lowest is eliminated (alphabetical tiebreak).  Continues until
    survivors_target candidates are elected or the field is exhausted.

    Returns (finalists_set, results_rows) — same contract as before.
    """
    active         = set(active_set)
    total_votes    = float(weights.sum())
    quota          = droop_quota(total_votes, survivors_target)
    ballot_weights = weights.astype(float).copy()   # scaled down on surplus transfer
    elected: list  = []

    while len(elected) < survivors_target and active:
        # If active candidates ≤ remaining seats, elect them all without a round
        remaining_seats = survivors_target - len(elected)
        if len(active) <= remaining_seats:
            elected.extend(sorted(active))
            active.clear()
            break

        fsc    = first_surviving_choice(ballots_arr, active)
        totals = compute_vote_totals(fsc, ballot_weights, active)

        # Elect highest vote-getter at or above quota (alphabetical tiebreak)
        over_quota = sorted(
            [c for c in active if totals[c] >= quota],
            key=lambda c: (-totals[c], c),
        )
        if over_quota:
            winner = over_quota[0]
            elected.append(winner)
            # Gregory fractional transfer: scale ballots for this candidate
            surplus_factor = (totals[winner] - quota) / totals[winner]
            for i in range(len(fsc)):
                if fsc[i] == winner:
                    ballot_weights[i] *= surplus_factor
            active.discard(winner)
        else:
            # No quota reached — eliminate lowest (alphabetical tiebreak)
            loser = min(active, key=lambda c: (totals[c], c))
            active.discard(loser)

    finalists = set(elected)

    # Final vote totals for output (use ballot_weights to reflect transfers)
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
            "winnowing_point":  label,
            "cand_code":        code,
            "cand_label":       cand_names.get(code, code),
            "vote_total":       round(vote_total, 2),
            "vote_pct":         round(vote_total / total_votes * 100, 4) if total_votes > 0 else 0.0,
            "quota_threshold":  round(quota, 2),
            "status":           "surviving" if is_finalist else "eliminated",
        })

    return finalists, results_rows


# ═════════════════════════════════════════════════════════════════════════════
# 5 — Condorcet / Ranked Pairs
# ═════════════════════════════════════════════════════════════════════════════

def build_matchups(ballots_arr: np.ndarray,
                   weights: np.ndarray,
                   finalists: list[str]) -> list[dict]:
    """Build weighted head-to-head matchup dicts for every finalist pair."""
    M = ballots_arr.shape[1]

    # Vectorised rank lookup: for each finalist find their position in each ballot
    finalist_ranks = {}
    for code in finalists:
        ranks = np.full(len(ballots_arr), M + 1)   # sentinel = not found
        for j in range(M):
            mask = ballots_arr[:, j] == code
            ranks[mask] = j
        finalist_ranks[code] = ranks

    matchups = []
    for a, b in combinations(finalists, 2):
        ra = finalist_ranks[a]
        rb = finalist_ranks[b]
        matchups.append({
            "candidate_a":    a,
            "candidate_b":    b,
            "votes_a_beats_b": float(weights[ra < rb].sum()),
            "votes_b_beats_a": float(weights[rb < ra].sum()),
        })
    return matchups


def ranked_pairs_winner(matchups: list[dict],
                         candidates: list[str]) -> tuple[str, list[dict]]:
    """
    Tideman Ranked Pairs.  Locks directed defeats strongest-first, skipping
    any that would create a cycle (DFS detection).
    Returns (winner_code, annotated_matchups).
    """
    if not matchups or len(candidates) < 2:
        return (candidates[0] if candidates else "none"), matchups

    # Reference total for margin_pct (use max pairwise total)
    total_votes = max(m["votes_a_beats_b"] + m["votes_b_beats_a"] for m in matchups)

    # Build directed defeats
    defeats = []
    for idx, m in enumerate(matchups):
        a, b   = m["candidate_a"], m["candidate_b"]
        va, vb = m["votes_a_beats_b"], m["votes_b_beats_a"]
        winner, loser, margin = (a, b, va - vb) if va >= vb else (b, a, vb - va)
        defeats.append({"winner": winner, "loser": loser, "margin": margin,
                         "margin_pct": margin / total_votes * 100 if total_votes else 0,
                         "orig_idx": idx})

    defeats.sort(key=lambda x: (-x["margin"], x["winner"]))

    def creates_cycle(locked_edges, new_winner, new_loser):
        reachable, frontier = set(), {new_loser}
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

    locked_edges = []
    lock_meta = {d["orig_idx"]: {"lock_order": None, "locked": False} for d in defeats}
    for order, defeat in enumerate(defeats, start=1):
        idx = defeat["orig_idx"]
        lock_meta[idx]["lock_order"] = order
        if not creates_cycle(locked_edges, defeat["winner"], defeat["loser"]):
            locked_edges.append((defeat["winner"], defeat["loser"]))
            lock_meta[idx]["locked"] = True

    losers      = {l for _, l in locked_edges}
    undefeated  = [c for c in candidates if c not in losers]
    rp_winner   = undefeated[0] if len(undefeated) == 1 else (undefeated[0] if undefeated else "none")

    # Annotate original matchups list
    for d in defeats:
        idx = d["orig_idx"]
        matchups[idx].update({
            "margin":         round(d["margin"], 2),
            "margin_pct":     round(d["margin_pct"], 4),
            "lock_order":     lock_meta[idx]["lock_order"],
            "locked":         lock_meta[idx]["locked"],
            "rp_winner_overall": rp_winner,
        })

    return rp_winner, matchups


# ═════════════════════════════════════════════════════════════════════════════
# 6 — Per-state election runner
# ═════════════════════════════════════════════════════════════════════════════

def run_state_election(state_fips: int,
                        prob_matrix: np.ndarray,
                        voter_factors: np.ndarray,
                        weights: np.ndarray,
                        cluster_centroids: np.ndarray,
                        rng: np.random.Generator) -> dict | None:
    """
    Run the full state senate election.
    Returns a results dict or None if state should be skipped.
    """
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

    # Score and ballot generation
    scores  = score_candidates(voter_factors, cands, cluster_centroids)
    ballots = generate_state_ballots(scores, cand_codes, rng)

    # STV primary
    target = min(STV_SURVIVORS, M)

    if M <= target:
        # All candidates are finalists — no elimination needed
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

    # Condorcet / Ranked Pairs
    if len(finalist_list) < 2:
        rp_winner = finalist_list[0] if finalist_list else "none"
        matchups  = []
    else:
        raw_matchups           = build_matchups(ballots, weights, finalist_list)
        rp_winner, matchups    = ranked_pairs_winner(raw_matchups, finalist_list)

    # Attach candidate-type and cluster info to results rows
    cand_type_map    = {c["cand_code"]: c["cand_type"] for c in cands}
    cand_cluster_map = {c["cand_code"]: (c["primary_cluster"], c["secondary_cluster"])
                        for c in cands}
    for row in results_rows:
        code = row["cand_code"]
        row["cand_type"]         = cand_type_map.get(code, "unknown")
        row["primary_cluster"], row["secondary_cluster"] = cand_cluster_map.get(code, (-1, None))
        row["state_fips"]        = int(state_fips)
        row["state_abbr"]        = state_abbr

    # Attach state info to candidates and matchups
    for c in cands:
        c["state_fips"] = int(state_fips)
        c["state_abbr"] = state_abbr
    for m in matchups:
        m["state_fips"] = int(state_fips)
        m["state_abbr"] = state_abbr

    # Composition row
    winner_cand  = next((c for c in cands if c["cand_code"] == rp_winner), None)
    finalist_results = {r["cand_code"]: r for r in results_rows if r["cand_code"] in finalists}

    comp_row = {
        "state_fips":                 int(state_fips),
        "state_abbr":                 state_abbr,
        "senator_code":               rp_winner,
        "senator_label":              cand_names.get(rp_winner, rp_winner),
        "senator_type":               winner_cand["cand_type"] if winner_cand else "unknown",
        "primary_cluster":            winner_cand["primary_cluster"] if winner_cand else -1,
        "secondary_cluster":          winner_cand["secondary_cluster"] if winner_cand else None,
        "total_weighted_respondents": round(float(weights.sum()), 2),
        "n_candidates_in_race":       M,
        "n_finalists":                len(finalist_list),
    }
    for code in finalist_list:
        r = finalist_results.get(code)
        comp_row[f"finalist_{code}_pct"] = r["vote_pct"] if r else 0.0

    return {
        "state_fips":    int(state_fips),
        "state_abbr":    state_abbr,
        "candidates":    cands,
        "results_rows":  results_rows,
        "matchups":      matchups,
        "comp_row":      comp_row,
        "rp_winner":     rp_winner,
        "finalists":     finalist_list,
        "n_candidates":  M,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 7 — Main
# ═════════════════════════════════════════════════════════════════════════════

def main():
    rng = np.random.default_rng(42)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Load data ─────────────────────────────────────────────────────────────
    print("Loading data…")
    typology = pd.read_csv(TYPOLOGY_PATH)
    efa      = pd.read_csv(EFA_SCORES_PATH)
    print(f"  typology: {typology.shape}   efa: {efa.shape}")
    assert len(typology) == len(efa), "Row count mismatch between typology and efa files"

    prob_matrix   = typology[PROB_COLS].values.astype(np.float64)
    voter_factors = efa[FACTOR_COLS].values.astype(np.float64)
    inputstate    = efa["inputstate"].values.astype(int)
    weights       = efa["commonpostweight"].values.astype(np.float64)

    # ── Cluster centroids in F1-F5 factor space ───────────────────────────────
    print("Computing cluster factor centroids…")
    cluster_centroids = compute_cluster_centroids(efa, typology)
    print("  Cluster | F1_sec  F2_eskep F3_gdis  F4_rtrad F5_pcon")
    for k in ACTIVE_CLUSTERS:
        vals = "  ".join(f"{cluster_centroids[k, f]:+.3f}" for f in range(5))
        print(f"  C{k} {PARTY_ABBR[k]:<5}| {vals}")

    # ── State loop ────────────────────────────────────────────────────────────
    all_states = sorted(np.unique(inputstate))
    pr_n = int((inputstate == 72).sum())
    print(f"\n  {len(all_states)} unique FIPS codes in data | PR (FIPS 72): {pr_n} respondents — skipped")
    run_states = [s for s in all_states if s != 72]

    print(f"\nRunning senate elections for {len(run_states)} states/DC…\n")
    print(f"  {'St':4s}  {'N':>5s}  {'Cands':>5s}  {'Finalists':<40s}  Senator")
    print(f"  {'-'*80}")

    all_candidates:    list[dict] = []
    all_primary:       list[dict] = []
    all_condorcet:     list[dict] = []
    all_composition:   list[dict] = []

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
            print(f"  {abbr:4s}  SKIPPED (N={mask.sum()})")
            continue

        all_candidates.extend(result["candidates"])
        all_primary.extend(result["results_rows"])
        all_condorcet.extend(result["matchups"])
        all_composition.append(result["comp_row"])

        finalists_str = ", ".join(result["finalists"])
        if len(finalists_str) > 40:
            finalists_str = finalists_str[:37] + "…"
        print(f"  {result['state_abbr']:4s}  {mask.sum():>5d}  {result['n_candidates']:>5d}  "
              f"{finalists_str:<40s}  {result['rp_winner']}")

    # ── Save output files ─────────────────────────────────────────────────────
    print(f"\nSaving to {OUTPUT_DIR} …")

    # state_senate_candidates.csv
    cands_df = pd.DataFrame(all_candidates)
    cand_col_order = ["state_fips", "state_abbr", "cand_code", "cand_label",
                      "primary_cluster", "secondary_cluster", "w_primary", "w_secondary",
                      "cand_type", "state_share_primary", "state_share_secondary", "cooc_rate"]
    cands_df = cands_df[[c for c in cand_col_order if c in cands_df.columns]]
    cands_df.to_csv(OUTPUT_DIR / "state_senate_candidates.csv", index=False)
    print(f"  state_senate_candidates.csv:  {len(cands_df):,} rows")

    # senate_primary_results.csv
    primary_df = pd.DataFrame(all_primary)
    pri_col_order = ["state_fips", "state_abbr", "cand_code", "cand_label", "cand_type",
                     "primary_cluster", "secondary_cluster",
                     "vote_total", "vote_pct", "quota_threshold", "status", "winnowing_point"]
    primary_df = primary_df[[c for c in pri_col_order if c in primary_df.columns]]
    primary_df.to_csv(OUTPUT_DIR / "senate_primary_results.csv", index=False)
    print(f"  senate_primary_results.csv:   {len(primary_df):,} rows")

    # senate_condorcet_results.csv
    condorcet_df = pd.DataFrame(all_condorcet) if all_condorcet else pd.DataFrame()
    if not condorcet_df.empty:
        con_col_order = ["state_fips", "state_abbr", "candidate_a", "candidate_b",
                         "votes_a_beats_b", "votes_b_beats_a",
                         "margin", "margin_pct", "locked", "lock_order", "rp_winner_overall"]
        condorcet_df = condorcet_df[[c for c in con_col_order if c in condorcet_df.columns]]
    condorcet_df.to_csv(OUTPUT_DIR / "senate_condorcet_results.csv", index=False)
    print(f"  senate_condorcet_results.csv: {len(condorcet_df):,} rows")

    # senate_composition.csv
    comp_df = pd.DataFrame(all_composition)
    base_cols = ["state_fips", "state_abbr", "senator_code", "senator_label",
                 "senator_type", "primary_cluster", "secondary_cluster",
                 "total_weighted_respondents", "n_candidates_in_race", "n_finalists"]
    pct_cols  = sorted(c for c in comp_df.columns if c.startswith("finalist_") and c.endswith("_pct"))
    comp_out  = comp_df[[c for c in base_cols if c in comp_df.columns] + pct_cols]
    comp_out  = comp_out.sort_values("state_fips")
    comp_out.to_csv(OUTPUT_DIR / "senate_composition.csv", index=False)
    print(f"  senate_composition.csv:       {len(comp_out):,} rows")

    # ── Validation checks ─────────────────────────────────────────────────────
    print("\n── Validation ──")
    print(f"  Max candidates per state:  {cands_df.groupby('state_abbr').size().max()}")
    print(f"  Min candidates per state:  {cands_df.groupby('state_abbr').size().min()}")
    surviving_counts = primary_df[primary_df["status"] == "surviving"].groupby("state_abbr").size()
    print(f"  States with exactly 5 finalists: "
          f"{(surviving_counts == 5).sum()} / {len(surviving_counts)}")
    type_counts = cands_df["cand_type"].value_counts()
    print(f"  Candidate type breakdown:  " +
          "  ".join(f"{t}={n}" for t, n in type_counts.items()))

    # ── National senate summary ───────────────────────────────────────────────
    print("\n" + "═" * 65)
    print("NATIONAL SENATE COMPOSITION  (1 senator per state)")
    print("═" * 65)

    seat_counts = comp_out["senator_label"].value_counts()
    total_seats = seat_counts.sum()
    print(f"\n  {'Party / Candidate type':<22}  {'Seats':>6}  {'%':>6}")
    print(f"  {'-'*40}")
    for party, count in seat_counts.items():
        print(f"  {party:<22}  {count:>6}  {count/total_seats*100:>5.1f}%")
    print(f"  {'-'*40}")
    print(f"  {'TOTAL':<22}  {total_seats:>6}")

    # By senator type
    if "senator_type" in comp_out.columns:
        tc = comp_out["senator_type"].value_counts()
        print(f"\n  By type:  " + "   ".join(f"{t}: {n}" for t, n in tc.items()))

    # Pure-cluster party alignment
    pure_senators = comp_out[comp_out["senator_type"] == "pure"]
    if not pure_senators.empty:
        print(f"\n  Pure-cluster senators ({len(pure_senators)}):")
        pc_counts = pure_senators["senator_label"].value_counts()
        for label, n in pc_counts.items():
            print(f"    {label:<8}  {n:>2} seats")

    print("═" * 65)
    print("\n✓ Senate simulation complete.")


if __name__ == "__main__":
    main()

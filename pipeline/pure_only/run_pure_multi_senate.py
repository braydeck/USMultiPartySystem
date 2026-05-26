#!/usr/bin/env python3
"""
run_pure_multi_senate.py
--------------------------
State-by-state senate simulation with state-proportional candidate pools.

For each state:
  1. Read cluster shares from state_candidate_profiles.csv
  2. Build a state-specific candidate pool (variable count based on thresholds)
  3. Generate per-state Plackett-Luce ballots using the same proximity/prominence
     logic as generate_pure_multi_ballots.py
  4. Run STV (Gregory) elimination → 5 finalists
  5. Run Ranked Pairs Condorcet → 1 senator  (senate_composition.csv)
  6. Run IRV → 1 senator  (senate_irv_composition.csv)

Presidential primary/general are unaffected — they use the global 27-candidate pool.

Outputs to data/outputs/pure_multi/senate/:
  senate_composition.csv         — Condorcet (Ranked Pairs) winner per state
  senate_irv_composition.csv     — IRV winner per state
  senate_condorcet_results.csv   — Ranked Pairs matchup detail per state
"""

import numpy as np
import pandas as pd
from pathlib import Path
from itertools import combinations

BASE_DIR       = Path(__file__).parent.parent.parent
TYPOLOGY_PATH  = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
EFA_PATH       = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
STATE_PROFILES = BASE_DIR / "data" / "outputs" / "pure_multi" / "state_candidate_profiles.csv"
OUTPUT_DIR     = BASE_DIR / "data" / "outputs" / "pure_multi" / "senate"

# ── Ballot-generation constants (must match generate_pure_multi_ballots.py) ───
POSITIONAL_SIGMA = 0.35
FACTOR_WEIGHTS   = np.array([1.0, 1.0, 1.0, 1.0, 1.0])  # uniform — centroid geometry handles discrimination
FACTOR_COLS      = ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]
PROB_COLS        = [f"prob_cluster_{k}" for k in range(10)]

# ── State-proportional pool thresholds ────────────────────────────────────────
THRESH_3 = 0.12   # >= 12% share → 3 candidates  (0.40 / 0.35 / 0.25)
THRESH_2 = 0.05   # >=  5% share → 2 candidates  (0.60 / 0.40)
THRESH_1 = 0.01   # >=  1% share → 1 candidate   (1.00)
                  # <   1% share → 0 candidates (party doesn't run)

PROMINENCE_3 = [0.40, 0.35, 0.25]
PROMINENCE_2 = [0.60, 0.40]
PROMINENCE_1 = [1.00]

# ── Party → cluster index (C7/BLB excluded) ───────────────────────────────────
PARTY_CLUSTER = {
    "CON": 0,
    "SD":  1,
    "STY": 2,
    "NAT": 3,
    "LIB": 4,
    "REF": 5,
    "CTR": 6,
    "DSA": 8,
    "PRG": 9,
}

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


def party_of(code: str) -> str:
    return code.rsplit("_", 1)[0]


# ── Per-state candidate pool ───────────────────────────────────────────────────

def build_state_candidates(cluster_shares: dict) -> list:
    """Build state-specific candidate list based on cluster shares.

    Returns a list of dicts: {code, party, cluster, prominence}.
    Candidates are ordered by party (PARTY_CLUSTER key order), then by
    prominence descending within each party.
    """
    candidates = []
    for party, cluster_idx in PARTY_CLUSTER.items():
        share = cluster_shares.get(f"prob_cluster_{cluster_idx}", 0.0)
        if share >= THRESH_3:
            prominences = PROMINENCE_3
        elif share >= THRESH_2:
            prominences = PROMINENCE_2
        elif share >= THRESH_1:
            prominences = PROMINENCE_1
        else:
            continue  # party doesn't run in this state
        for i, prom in enumerate(prominences, start=1):
            candidates.append({
                "code":       f"{party}_{i}",
                "party":      party,
                "cluster":    cluster_idx,
                "prominence": prom,
            })
    return candidates


# ── Ballot generation (adapted from generate_pure_multi_ballots.py) ────────────

def compute_cluster_centroids(efa_df: pd.DataFrame, typology_df: pd.DataFrame) -> np.ndarray:
    """Weighted mean of FS_F1–FS_F5 per cluster (0–9). Returns (10, 5)."""
    weights   = efa_df["commonpostweight"].values
    clusters  = typology_df["cluster"].values.astype(int)
    centroids = np.zeros((10, 5), dtype=np.float64)
    for k in range(10):
        mask = clusters == k
        w_k  = weights[mask]
        if w_k.sum() > 0:
            for f, col in enumerate(FACTOR_COLS):
                centroids[k, f] = np.average(efa_df[col].values[mask], weights=w_k)
    return centroids


def compute_candidate_scores(voter_factors: np.ndarray,
                              cluster_centroids: np.ndarray,
                              candidates: list) -> np.ndarray:
    """Gaussian proximity × prominence weight.

    Returns (N, n_cands) score matrix.
    """
    positions  = np.array([cluster_centroids[c["cluster"]] for c in candidates])  # (n_cands, 5)
    prominence = np.array([c["prominence"] for c in candidates])                  # (n_cands,)
    diff       = voter_factors[:, None, :] - positions[None, :, :]                # (N, n_cands, 5)
    dist_sq    = ((diff ** 2) * FACTOR_WEIGHTS).sum(axis=2)                       # (N, n_cands)
    proximity  = np.exp(-dist_sq / (2.0 * POSITIONAL_SIGMA ** 2))                # (N, n_cands)
    return proximity * prominence[None, :]                                         # (N, n_cands)


def compute_candidate_scores_prob(prob_matrix: np.ndarray, candidates: list) -> np.ndarray:
    """Equal PL scores for same-party candidates (prob_cluster_k only).
    Prominence ordering is applied after PL sampling in generate_ballots()."""
    n_cands = len(candidates)
    scores  = np.zeros((len(prob_matrix), n_cands))
    for j, cand in enumerate(candidates):
        scores[:, j] = prob_matrix[:, cand["cluster"]]
    return scores


def generate_ballots(scores: np.ndarray, rng: np.random.Generator,
                     candidates: list) -> np.ndarray:
    """Plackett-Luce sampling with within-party prominence ordering.

    The first same-party candidate position is determined by Plackett-Luce
    (weighted by prominence × proximity). Remaining same-party candidates
    always follow in strict prominence order (_1 before _2 before _3).

    Returns (N, n_cands) object array of candidate code strings.
    """
    N       = len(scores)
    n_cands = len(candidates)
    EPSILON = 1e-10

    cand_codes = [c["code"] for c in candidates]

    # Build party groups in prominence order (candidates list is ordered high→low)
    party_groups: dict = {}
    for idx, cand in enumerate(candidates):
        party = cand["party"]
        if party not in party_groups:
            party_groups[party] = []
        party_groups[party].append(idx)
    multi_parties = [idxs for idxs in party_groups.values() if len(idxs) > 1]

    ballots = np.empty((N, n_cands), dtype=object)

    for i in range(N):
        probs = scores[i] + EPSILON
        probs /= probs.sum()
        ballot = rng.choice(n_cands, size=n_cands, replace=False, p=probs)

        # Assign prominence labels within each party's PL-determined positions.
        rank_of = {int(ballot[r]): r for r in range(n_cands)}
        for party_idxs in multi_parties:
            positions = sorted(rank_of[idx] for idx in party_idxs)
            for k, pos in enumerate(positions):
                ballot[pos] = party_idxs[k]

        ballots[i] = [cand_codes[int(idx)] for idx in ballot]

    return ballots


# ── STV helpers ───────────────────────────────────────────────────────────────

def first_surviving_choice(ballots_arr: np.ndarray, active_set: set) -> np.ndarray:
    N      = len(ballots_arr)
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
                  weights: np.ndarray, candidates: list) -> dict:
    cand_cluster = {c["code"]: c["cluster"] for c in candidates}
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
        "primary_cluster":            str(cand_cluster.get(senator_code, -1)),
        "secondary_cluster":          "",
        "total_weighted_respondents": round(float(total), 2),
        "n_candidates_in_race":       len(candidates),
        "n_finalists":                len(finalists),
    }
    for code in finalists:
        row[f"finalist_{code}_pct"] = round(totals.get(code, 0.0) / total * 100, 4) if total else 0.0
    return row


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rng      = np.random.default_rng(42)
    rng_prob = np.random.default_rng(43)

    print("=" * 65)
    print("PURE MULTI SENATE SIMULATION  —  state-proportional candidate pools")
    print("=" * 65)

    print("\nLoading EFA scores + typology…")
    efa      = pd.read_csv(EFA_PATH)
    typology = pd.read_csv(TYPOLOGY_PATH)
    assert len(efa) == len(typology), f"Row mismatch: {len(efa)} vs {len(typology)}"

    inputstate    = efa["inputstate"].values.astype(int)
    weights       = efa["commonpostweight"].values.astype(float)
    voter_factors = efa[FACTOR_COLS].values.astype(np.float64)

    print("Computing cluster centroids…")
    cluster_centroids = compute_cluster_centroids(efa, typology)
    prob_matrix       = typology[PROB_COLS].values.astype(np.float64)

    print("Loading state profiles…")
    state_profiles = pd.read_csv(STATE_PROFILES).set_index("state_fips")

    all_states = sorted(s for s in np.unique(inputstate) if s != 72)

    all_condorcet:  list = []
    comp_rows_cond: list = []
    comp_rows_irv:  list = []

    all_condorcet_prob:  list = []
    comp_rows_cond_prob: list = []
    comp_rows_irv_prob:  list = []

    print(f"\nRunning senate elections for {len(all_states)} states/DC…\n")
    print(f"  {'St':4s}  {'N':>5s}  {'Cands':>5s}  {'Finalists':<42s}  Cond → IRV")
    print(f"  {'-'*85}")

    for state_fips in all_states:
        mask       = inputstate == state_fips
        state_abbr = FIPS_TO_ABBR.get(int(state_fips), f"FIPS{state_fips}")
        n_resp     = int(mask.sum())

        if n_resp < MIN_RESPONDENTS:
            print(f"  {state_abbr:4s}  SKIPPED (N={n_resp})")
            continue

        # Build state-specific candidate pool from cluster shares
        if int(state_fips) in state_profiles.index:
            row_shares = state_profiles.loc[int(state_fips)]
            cluster_shares = {f"prob_cluster_{k}": float(row_shares.get(f"prob_cluster_{k}", 0.0))
                              for k in range(10)}
        else:
            # Fallback: give every party a token presence (1 candidate each)
            cluster_shares = {f"prob_cluster_{k}": 0.05 for k in range(10)}

        candidates = build_state_candidates(cluster_shares)
        cand_codes = [c["code"] for c in candidates]
        n_cands    = len(candidates)

        # Generate state-specific ballots
        state_voter_factors = voter_factors[mask]
        state_weights       = weights[mask]
        state_prob_matrix   = prob_matrix[mask]
        scores              = compute_candidate_scores_prob(state_prob_matrix, candidates)
        state_ballots       = generate_ballots(scores, rng, candidates)

        # STV → finalists
        n_survivors = min(STV_SURVIVORS, n_cands)
        finalists     = winnow_stv(state_ballots, state_weights, set(cand_codes), n_survivors)
        finalist_list = sorted(finalists)

        # Ranked Pairs
        if len(finalist_list) < 2:
            cond_winner = finalist_list[0] if finalist_list else "none"
            matchups    = []
        else:
            raw_matchups          = build_matchups(state_ballots, state_weights, finalist_list)
            cond_winner, matchups = ranked_pairs_winner(raw_matchups, finalist_list)

        # IRV
        irv_win = irv_winner(state_ballots, state_weights, finalist_list)

        for m in matchups:
            m["state_fips"] = int(state_fips)
            m["state_abbr"] = state_abbr
        all_condorcet.extend(matchups)

        comp_rows_cond.append(
            make_comp_row(state_fips, state_abbr, cond_winner,
                          finalist_list, state_ballots, state_weights, candidates)
        )
        comp_rows_irv.append(
            make_comp_row(state_fips, state_abbr, irv_win,
                          finalist_list, state_ballots, state_weights, candidates)
        )

        # ── Prob-cluster scoring variant ───────────────────────────────────────
        state_prob_matrix  = prob_matrix[mask]
        prob_scores        = compute_candidate_scores_prob(state_prob_matrix, candidates)
        prob_ballots       = generate_ballots(prob_scores, rng_prob, candidates)

        prob_finalists     = winnow_stv(prob_ballots, state_weights, set(cand_codes), n_survivors)
        prob_finalist_list = sorted(prob_finalists)

        if len(prob_finalist_list) < 2:
            prob_cond_winner = prob_finalist_list[0] if prob_finalist_list else "none"
            prob_matchups    = []
        else:
            prob_raw_matchups               = build_matchups(prob_ballots, state_weights, prob_finalist_list)
            prob_cond_winner, prob_matchups = ranked_pairs_winner(prob_raw_matchups, prob_finalist_list)

        prob_irv_win = irv_winner(prob_ballots, state_weights, prob_finalist_list)

        for m in prob_matchups:
            m["state_fips"] = int(state_fips)
            m["state_abbr"] = state_abbr
        all_condorcet_prob.extend(prob_matchups)

        comp_rows_cond_prob.append(
            make_comp_row(state_fips, state_abbr, prob_cond_winner,
                          prob_finalist_list, prob_ballots, state_weights, candidates)
        )
        comp_rows_irv_prob.append(
            make_comp_row(state_fips, state_abbr, prob_irv_win,
                          prob_finalist_list, prob_ballots, state_weights, candidates)
        )

        finalists_str = ", ".join(finalist_list)
        if len(finalists_str) > 42:
            finalists_str = finalists_str[:39] + "…"
        print(f"  {state_abbr:4s}  {n_resp:>5d}  {n_cands:>5d}  {finalists_str:<42s}  "
              f"Gauss: {cond_winner}→{irv_win}  Prob: {prob_cond_winner}→{prob_irv_win}")

    # ── Save outputs ──────────────────────────────────────────────────────────
    print(f"\nSaving to {OUTPUT_DIR} …")

    col_order = ["state_fips", "state_abbr", "candidate_a", "candidate_b",
                 "votes_a_beats_b", "votes_b_beats_a",
                 "margin", "margin_pct", "locked", "lock_order", "rp_winner_overall"]

    # ── Primary run: canonical outputs ──────────────────────────────────────
    cond_df_primary = pd.DataFrame(comp_rows_cond).sort_values("state_fips").reset_index(drop=True)
    irv_df_primary  = pd.DataFrame(comp_rows_irv).sort_values("state_fips").reset_index(drop=True)

    cond_df_primary.to_csv(OUTPUT_DIR / "senate_composition.csv", index=False)
    irv_df_primary.to_csv(OUTPUT_DIR / "senate_irv_composition.csv", index=False)
    print(f"  senate_composition.csv:              {len(cond_df_primary)} rows")
    print(f"  senate_irv_composition.csv:          {len(irv_df_primary)} rows")

    if all_condorcet_prob:
        cond_results_prob_df = pd.DataFrame(all_condorcet_prob)
        cond_results_prob_df = cond_results_prob_df[[c for c in col_order if c in cond_results_prob_df.columns]]
        cond_results_prob_df.to_csv(OUTPUT_DIR / "senate_condorcet_results.csv", index=False)
        print(f"  senate_condorcet_results.csv (prob): {len(cond_results_prob_df)} rows")

    # ── Gaussian: reference outputs ────────────────────────────────────────────
    cond_df = pd.DataFrame(comp_rows_cond).sort_values("state_fips").reset_index(drop=True)
    irv_df  = pd.DataFrame(comp_rows_irv).sort_values("state_fips").reset_index(drop=True)

    cond_df.to_csv(OUTPUT_DIR / "senate_composition_gauss.csv", index=False)
    irv_df.to_csv(OUTPUT_DIR / "senate_irv_composition_gauss.csv", index=False)
    print(f"  senate_composition_gauss.csv:        {len(cond_df)} rows")
    print(f"  senate_irv_composition_gauss.csv:    {len(irv_df)} rows")

    if all_condorcet:
        cond_results_df = pd.DataFrame(all_condorcet)
        cond_results_df = cond_results_df[[c for c in col_order if c in cond_results_df.columns]]
        cond_results_df.to_csv(OUTPUT_DIR / "senate_condorcet_results_gauss.csv", index=False)
        print(f"  senate_condorcet_results_gauss.csv:  {len(cond_results_df)} rows")

    # ── National summary ──────────────────────────────────────────────────────
    for label, df in [("CONDORCET (primary — canonical)", cond_df_primary),
                      ("IRV (primary — canonical)", irv_df_primary),
                      ("CONDORCET (gauss — reference)", cond_df),
                      ("IRV (gauss — reference)", irv_df)]:
        print(f"\n{'='*55}")
        print(f"NATIONAL SENATE  ({label})  —  {len(df)} states")
        print(f"{'='*55}")

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

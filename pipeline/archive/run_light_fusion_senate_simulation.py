#!/usr/bin/env python3
"""
run_light_fusion_senate_simulation.py
---------------------------------------
State-by-state senate simulation using the 25 light fusion candidates
(9 pure parties + 16 80/20 variants).

For each state with CES respondents:
  1. Use the fixed 25 LF candidate slate (no per-state candidate generation)
  2. Generate Plackett-Luce ranked ballots for every respondent in that state
  3. Run STV elimination → 5 finalists
  4. Run Ranked Pairs Condorcet among finalists → 1 senator  (senate_composition.csv)
  5. Also run IRV from full 25-candidate ballots → 1 senator  (senate_irv_composition.csv)

Outputs to data/outputs/light_fusion/senate/:
  senate_composition.csv         — Condorcet winners per state
  senate_irv_composition.csv     — IRV winners per state
  senate_condorcet_results.csv   — Ranked Pairs matchup detail
"""

import numpy as np
import pandas as pd
from pathlib import Path
from itertools import combinations

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR         = Path(__file__).parent.parent
TYPOLOGY_PATH    = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
EFA_SCORES_PATH  = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
CENTROIDS_PATH   = BASE_DIR / "data" / "outputs" / "light_fusion_centroids.csv"
OUTPUT_DIR       = BASE_DIR / "data" / "outputs" / "light_fusion" / "senate"

PARTY_ABBR   = {0:"CON", 1:"LBR", 2:"STY", 3:"NAT", 4:"LIB",
                5:"REF", 6:"CTR", 8:"DSA", 9:"PRG"}
FACTOR_COLS  = ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]
CENTROID_COLS = ["F1_security_order", "F2_electoral_skepticism",
                 "F3_government_distrust", "F4_religious_traditionalism",
                 "F5_populist_conservatism"]

# Pure party candidate_name values (to identify pure rows in centroids CSV)
PURE_NAMES = set(PARTY_ABBR.values())  # {"CON", "LBR", "STY", ...}

STV_SURVIVORS   = 5
MIN_RESPONDENTS = 10
POSITIONAL_SIGMA = 0.35
FACTOR_WEIGHTS   = np.array([1.0, 1.0, 1.0, 1.0, 1.0])  # uniform — centroid geometry handles discrimination

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

# ── Light fusion candidate definitions (primary/secondary cluster) ──────────────
# Used to annotate output metadata; same adjacency pairs as primary simulation
LF_CLUSTER_MAP = {
    "PRG_dsa": (9, 8), "DSA_prg": (8, 9), "DSA_lib": (8, 4),
    "LIB_dsa": (4, 8), "LIB_sd":  (4, 1), "LBR_lib":  (1, 4),
    "LBR_sty":  (1, 2), "STY_sd":  (2, 1), "STY_ctr": (2, 6),
    "CTR_sty": (6, 2), "CTR_con": (6, 0), "CON_ctr": (0, 6),
    "CON_ref": (0, 5), "REF_con": (5, 0), "REF_nat": (5, 3),
    "NAT_ref": (3, 5),
}
PURE_CLUSTER_MAP = {v: k for k, v in PARTY_ABBR.items()}  # "CON"→0, etc.


# ═══════════════════════════════════════════════════════════════════════════════
# Ballot generation
# ═══════════════════════════════════════════════════════════════════════════════

def score_candidates(voter_factors: np.ndarray,
                     cand_positions: np.ndarray,
                     sigma: float = POSITIONAL_SIGMA) -> np.ndarray:
    """(N, M) Gaussian proximity scores in 5-D factor space."""
    diff = voter_factors[:, None, :] - cand_positions[None, :, :]
    return np.exp(-((diff ** 2) * FACTOR_WEIGHTS).sum(axis=2) / (2.0 * sigma ** 2))


def generate_ballots(scores: np.ndarray,
                     cand_codes: list[str],
                     rng: np.random.Generator) -> np.ndarray:
    """Plackett-Luce ranked ballots. Returns (N, M) object array."""
    N, M = scores.shape
    EPSILON = 1e-10
    ballots = np.empty((N, M), dtype=object)
    cand_arr = np.array(cand_codes, dtype=object)
    for i in range(N):
        probs = scores[i] + EPSILON
        probs /= probs.sum()
        ballots[i] = cand_arr[rng.choice(M, size=M, replace=False, p=probs)]
    return ballots


# ═══════════════════════════════════════════════════════════════════════════════
# STV engine (Gregory fractional surplus)
# ═══════════════════════════════════════════════════════════════════════════════

def first_surviving_choice(ballots_arr: np.ndarray, active_set: set) -> np.ndarray:
    N, M = ballots_arr.shape
    result = np.empty(N, dtype=object)
    for i in range(N):
        result[i] = "__exhausted__"
        for j in range(M):
            if ballots_arr[i, j] in active_set:
                result[i] = ballots_arr[i, j]
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
    """STV with Gregory fractional surplus. Returns finalist set."""
    active       = set(active_set)
    ballot_wts   = weights.astype(float).copy()
    total_votes  = float(weights.sum())
    quota        = droop_quota(total_votes, target)
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
            winner = over_quota[0]
            elected.append(winner)
            surplus_factor = (totals[winner] - quota) / totals[winner]
            for i in range(len(fsc)):
                if fsc[i] == winner:
                    ballot_wts[i] *= surplus_factor
            active.discard(winner)
        else:
            loser = min(active, key=lambda c: (totals[c], c))
            active.discard(loser)

    return set(elected)


# ═══════════════════════════════════════════════════════════════════════════════
# Condorcet / Ranked Pairs
# ═══════════════════════════════════════════════════════════════════════════════

def build_matchups(ballots_arr: np.ndarray, weights: np.ndarray,
                   finalists: list[str]) -> list[dict]:
    M = ballots_arr.shape[1]
    finalist_ranks = {}
    for code in finalists:
        ranks = np.full(len(ballots_arr), M + 1)
        for j in range(M):
            ranks[ballots_arr[:, j] == code] = j
        finalist_ranks[code] = ranks

    matchups = []
    for a, b in combinations(finalists, 2):
        ra, rb = finalist_ranks[a], finalist_ranks[b]
        matchups.append({
            "candidate_a": a,
            "candidate_b": b,
            "votes_a_beats_b": float(weights[ra < rb].sum()),
            "votes_b_beats_a": float(weights[rb < ra].sum()),
        })
    return matchups


def ranked_pairs_winner(matchups: list[dict],
                        candidates: list[str]) -> tuple[str, list[dict]]:
    if not matchups or len(candidates) < 2:
        return (candidates[0] if candidates else "none"), matchups

    total_votes = max(m["votes_a_beats_b"] + m["votes_b_beats_a"] for m in matchups)
    defeats = []
    for idx, m in enumerate(matchups):
        a, b   = m["candidate_a"], m["candidate_b"]
        va, vb = m["votes_a_beats_b"], m["votes_b_beats_a"]
        w, l, margin = (a, b, va - vb) if va >= vb else (b, a, vb - va)
        defeats.append({"winner": w, "loser": l, "margin": margin,
                        "margin_pct": margin / total_votes * 100 if total_votes else 0,
                        "orig_idx": idx})
    defeats.sort(key=lambda x: (-x["margin"], x["winner"]))

    def creates_cycle(locked, new_w, new_l):
        reachable, frontier = set(), {new_l}
        while frontier:
            node = frontier.pop()
            if node == new_w:
                return True
            if node in reachable:
                continue
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
            "margin": round(d["margin"], 2),
            "margin_pct": round(d["margin_pct"], 4),
            "lock_order": lock_meta[idx]["lock_order"],
            "locked": lock_meta[idx]["locked"],
            "rp_winner_overall": rp_winner,
        })
    return rp_winner, matchups


# ═══════════════════════════════════════════════════════════════════════════════
# IRV (for alternate composition)
# ═══════════════════════════════════════════════════════════════════════════════

def run_irv(ballots_arr: np.ndarray, weights: np.ndarray,
            candidates: list[str]) -> str:
    """Run IRV to completion; return winner code."""
    active    = set(candidates)
    total_w   = float(weights.sum())
    while len(active) > 1:
        fsc    = first_surviving_choice(ballots_arr, active)
        totals = compute_vote_totals(fsc, weights, active)
        if any(v > total_w / 2 for v in totals.values()):
            break
        loser = min(active, key=lambda c: (totals[c], c))
        active.discard(loser)
    if not active:
        return "none"
    fsc    = first_surviving_choice(ballots_arr, active)
    totals = compute_vote_totals(fsc, weights, active)
    return max(active, key=lambda c: totals.get(c, 0))


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    rng = np.random.default_rng(42)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Load survey data ────────────────────────────────────────────────────
    print("Loading survey data…")
    typology = pd.read_csv(TYPOLOGY_PATH)
    efa      = pd.read_csv(EFA_SCORES_PATH)
    assert len(typology) == len(efa)
    voter_factors = efa[FACTOR_COLS].values.astype(np.float64)
    inputstate    = efa["inputstate"].values.astype(int)
    weights       = efa["commonpostweight"].values.astype(np.float64)
    print(f"  {len(efa):,} respondents")

    # ── Load 25 LF candidate centroids ─────────────────────────────────────
    print("Loading light fusion candidate centroids…")
    centroids_df = pd.read_csv(CENTROIDS_PATH)

    # Keep only pure-party rows (candidate_name in PURE_NAMES) + LF rows (code has lowercase suffix)
    def is_lf_or_pure(row) -> bool:
        code = row["candidate_code"]
        name = row["candidate_name"]
        if name in PURE_NAMES:
            return True
        if "_" in code:
            suffix = code.split("_", 1)[1]
            return suffix == suffix.lower()
        return False

    centroids_df = centroids_df[centroids_df.apply(is_lf_or_pure, axis=1)].copy()

    # Normalize pure-party codes: RH → CON, MW → SD, etc.
    name_to_abbr = {v: v for v in PURE_NAMES}  # identity for pure names
    def normalize_code(row):
        if row["candidate_name"] in PURE_NAMES:
            return row["candidate_name"]   # already clean: "CON", "LBR", etc.
        return row["candidate_code"]       # light fusion: "STY_ctr", etc.

    centroids_df["code"] = centroids_df.apply(normalize_code, axis=1)
    centroids_df = centroids_df.drop_duplicates(subset="code")

    cand_codes    = centroids_df["code"].tolist()
    cand_positions = centroids_df[CENTROID_COLS].values.astype(np.float64)  # (25, 5)
    M = len(cand_codes)
    print(f"  {M} candidates: {', '.join(cand_codes)}")

    # Cluster metadata for output annotation
    def primary_cluster(code: str) -> int:
        if code in LF_CLUSTER_MAP:
            return LF_CLUSTER_MAP[code][0]
        return PURE_CLUSTER_MAP.get(code, -1)

    def secondary_cluster(code: str):
        if code in LF_CLUSTER_MAP:
            return LF_CLUSTER_MAP[code][1]
        return None

    # ── State loop ──────────────────────────────────────────────────────────
    all_states = sorted(np.unique(inputstate))
    run_states = [s for s in all_states if s != 72]
    print(f"\nRunning senate elections for {len(run_states)} states/DC…")
    print(f"  {'St':4s}  {'N':>5s}  {'Finalists':<50s}  Cond  IRV")
    print(f"  {'-'*80}")

    all_condorcet:    list[dict] = []
    cond_composition: list[dict] = []
    irv_composition:  list[dict] = []

    for state_fips in run_states:
        mask          = inputstate == state_fips
        state_factors = voter_factors[mask]
        state_weights = weights[mask]
        abbr          = FIPS_TO_ABBR.get(int(state_fips), f"FIPS{state_fips}")

        N = int(mask.sum())
        if N < MIN_RESPONDENTS:
            print(f"  {abbr:4s}  SKIPPED (N={N})")
            continue

        # Ballots
        scores  = score_candidates(state_factors, cand_positions)
        ballots = generate_ballots(scores, cand_codes, rng)

        # STV → 5 finalists
        target    = min(STV_SURVIVORS, M)
        finalists = winnow_stv(ballots, state_weights, set(cand_codes), target)
        finalist_list = sorted(finalists)

        # Condorcet / Ranked Pairs
        if len(finalist_list) >= 2:
            raw_matchups = build_matchups(ballots, state_weights, finalist_list)
            rp_winner, matchups = ranked_pairs_winner(raw_matchups, finalist_list)
        else:
            rp_winner = finalist_list[0] if finalist_list else "none"
            matchups  = []

        # IRV from full ballots
        irv_winner = run_irv(ballots, state_weights, cand_codes)

        # Annotate and collect matchups
        for m in matchups:
            m["state_fips"] = int(state_fips)
            m["state_abbr"] = abbr
        all_condorcet.extend(matchups)

        # First-choice shares for all candidates (for viz)
        fsc_full  = first_surviving_choice(ballots, set(cand_codes))
        totals_fc = compute_vote_totals(fsc_full, state_weights, set(cand_codes))
        total_w   = state_weights.sum()

        base_row = {
            "state_fips":                 int(state_fips),
            "state_abbr":                 abbr,
            "total_weighted_respondents": round(float(total_w), 2),
            "n_finalists":                len(finalist_list),
        }
        for code in cand_codes:
            base_row[f"fc_pct_{code}"] = round(totals_fc.get(code, 0.0) / total_w * 100, 3)

        cond_row = {**base_row,
                    "senator_code":      rp_winner,
                    "senator_label":     rp_winner,
                    "primary_cluster":   primary_cluster(rp_winner),
                    "secondary_cluster": secondary_cluster(rp_winner)}
        irv_row  = {**base_row,
                    "senator_code":      irv_winner,
                    "senator_label":     irv_winner,
                    "primary_cluster":   primary_cluster(irv_winner),
                    "secondary_cluster": secondary_cluster(irv_winner)}

        cond_composition.append(cond_row)
        irv_composition.append(irv_row)

        fin_str = ", ".join(finalist_list)
        if len(fin_str) > 50:
            fin_str = fin_str[:47] + "…"
        print(f"  {abbr:4s}  {N:>5d}  {fin_str:<50s}  {rp_winner}  {irv_winner}")

    # ── Save outputs ─────────────────────────────────────────────────────────
    print(f"\nSaving to {OUTPUT_DIR} …")

    base_cols = ["state_fips", "state_abbr", "senator_code", "senator_label",
                 "primary_cluster", "secondary_cluster",
                 "total_weighted_respondents", "n_finalists"]
    fc_cols = sorted(c for c in cond_composition[0] if c.startswith("fc_pct_"))

    cond_df = pd.DataFrame(cond_composition).sort_values("state_fips")
    cond_df = cond_df[base_cols + fc_cols]
    cond_df.to_csv(OUTPUT_DIR / "senate_composition.csv", index=False)
    print(f"  senate_composition.csv:      {len(cond_df)} rows")

    irv_df = pd.DataFrame(irv_composition).sort_values("state_fips")
    irv_df = irv_df[base_cols + fc_cols]
    irv_df.to_csv(OUTPUT_DIR / "senate_irv_composition.csv", index=False)
    print(f"  senate_irv_composition.csv:  {len(irv_df)} rows")

    if all_condorcet:
        cond_res_df = pd.DataFrame(all_condorcet)
        cond_res_df.to_csv(OUTPUT_DIR / "senate_condorcet_results.csv", index=False)
        print(f"  senate_condorcet_results.csv: {len(cond_res_df)} rows")

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "═" * 60)
    print("LIGHT FUSION SENATE COMPOSITION (Condorcet)")
    print("═" * 60)
    cc = cond_df["senator_code"].value_counts()
    for code, n in cc.items():
        print(f"  {code:<12} {n:2d} seats")

    print("\nLIGHT FUSION SENATE COMPOSITION (IRV)")
    ic = irv_df["senator_code"].value_counts()
    for code, n in ic.items():
        print(f"  {code:<12} {n:2d} seats")

    print("\n✓ Light Fusion senate simulation complete.")


if __name__ == "__main__":
    main()

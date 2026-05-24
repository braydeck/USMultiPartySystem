#!/usr/bin/env python3
"""
run_house_stv.py
-----------------
State-level proportional house election: each state is a single multi-member district.

9 pure party candidates at weighted cluster centroids.
C7 (Blue Dogs) voters are included in the ballot pool but have no C7 candidate;
they vote naturally for the 9 parties via Gaussian proximity (CTR ≈76%, LIB ≈15%).

Seat formula: max(1, round(STATE_POP / 380_000)) → 873 total seats.

Method: Gaussian proximity scores → weighted expected first-choice vote shares
→ Hare quota + largest remainders (Hamilton/proportional representation).
This is equivalent to the expectation of Plackett-Luce STV with many candidates
per party — the principled limit for proportional multi-member elections.

Outputs to data/outputs/house/:
  house_results_by_state.csv  — one row per state × elected-party seat block
                                 (state_fips, state_abbr, total_seats,
                                  party, party_seats)
  house_seat_summary.csv      — one row per party (party, seats, pct_national)
"""

import numpy as np
import pandas as pd
from pathlib import Path
import sys

BASE_DIR        = Path(__file__).parent.parent
TYPOLOGY_PATH   = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
EFA_SCORES_PATH = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
OUTPUT_DIR      = BASE_DIR / "data" / "outputs" / "house"

sys.path.insert(0, str(Path(__file__).parent))
from stv_config import STATE_POPS, FIPS_TO_ABBR, POP_PER_SEAT

FACTOR_COLS      = ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]
POSITIONAL_SIGMA = 0.35
FACTOR_WEIGHTS   = np.array([1.000, 0.535, 0.081, 0.436, 1.050])  # η²-based: F1 F2 F3 F4 F5
MIN_RESPONDENTS  = 10

CANDIDATES = [
    {"name": "CON", "cluster": 0},
    {"name": "SD",  "cluster": 1},
    {"name": "STY", "cluster": 2},
    {"name": "NAT", "cluster": 3},
    {"name": "LIB", "cluster": 4},
    {"name": "REF", "cluster": 5},
    {"name": "CTR", "cluster": 6},
    {"name": "DSA", "cluster": 8},
    {"name": "PRG", "cluster": 9},
]
CAND_NAMES = [c["name"] for c in CANDIDATES]


# ── Centroid computation ─────────────────────────────────────────────────────

def compute_cluster_centroids(efa_df: pd.DataFrame, typology_df: pd.DataFrame) -> np.ndarray:
    """Weighted mean of FS_F1–FS_F5 per cluster (0–9). Returns (10, 5)."""
    weights  = efa_df["commonpostweight"].values
    clusters = typology_df["cluster"].values.astype(int)
    centroids = np.zeros((10, 5), dtype=np.float64)
    for k in range(10):
        mask = clusters == k
        w_k  = weights[mask]
        if w_k.sum() > 0:
            for f, col in enumerate(FACTOR_COLS):
                centroids[k, f] = np.average(efa_df[col].values[mask], weights=w_k)
    return centroids


# ── Scoring ──────────────────────────────────────────────────────────────────

def compute_vote_shares(voter_factors: np.ndarray,
                        cand_positions: np.ndarray,
                        weights: np.ndarray,
                        sigma: float = POSITIONAL_SIGMA) -> np.ndarray:
    """
    Weighted expected first-choice vote shares for each candidate.

    For each voter i, the probability of first-ranking party p is proportional
    to their Gaussian proximity score (Plackett-Luce limit). The weighted mean
    over all state voters gives the expected proportional vote share.

    Returns: (n_candidates,) array of vote shares summing to 1.
    """
    diff    = voter_factors[:, None, :] - cand_positions[None, :, :]       # (N, 9, 5)
    dist_sq = ((diff ** 2) * FACTOR_WEIGHTS).sum(axis=2)                    # (N, 9)
    scores  = np.exp(-dist_sq / (2.0 * sigma ** 2))                        # (N, 9)
    probs   = scores / scores.sum(axis=1, keepdims=True)                   # (N, 9)
    shares  = np.average(probs, axis=0, weights=weights)                   # (9,)
    return shares / shares.sum()                                           # normalized


# ── Seat allocation: Hare quota + largest remainders (Hamilton) ──────────────

def allocate_seats(vote_shares: np.ndarray, cand_names: list, n_seats: int) -> dict:
    """
    Hamilton (largest remainders) proportional seat allocation.

    Each party gets floor(share × n_seats) guaranteed seats;
    remaining seats go to parties with the largest fractional remainders.
    Returns {party_name: seats} dict with exactly n_seats total.
    """
    exact     = vote_shares * n_seats
    base      = np.floor(exact).astype(int)
    remainders = exact - base
    remaining = n_seats - base.sum()

    # Award remaining seats to parties with largest remainders
    order = np.argsort(-remainders)   # descending
    for i in range(int(remaining)):
        base[order[i]] += 1

    return {cand_names[k]: int(base[k]) for k in range(len(cand_names))}


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sep  = "=" * 70
    thin = "-" * 70

    print(sep)
    print("HOUSE PROPORTIONAL  —  9 pure parties, state-level districts")
    print(sep)

    # ── Load data ─────────────────────────────────────────────────────────────
    print("\nLoading EFA factor scores…")
    efa           = pd.read_csv(EFA_SCORES_PATH)
    voter_factors = efa[FACTOR_COLS].values.astype(np.float64)
    weights       = efa["commonpostweight"].values.astype(np.float64)
    inputstate    = efa["inputstate"].values.astype(int)

    print("Loading typology cluster assignments…")
    typology = pd.read_csv(TYPOLOGY_PATH)
    assert len(efa) == len(typology), "Row count mismatch between EFA and typology"

    print("\nComputing cluster centroids…")
    cluster_centroids = compute_cluster_centroids(efa, typology)
    cand_positions    = np.array([cluster_centroids[c["cluster"]] for c in CANDIDATES])  # (9, 5)
    print(f"  Candidate positions built for {len(CANDIDATES)} parties")

    # ── State loop ────────────────────────────────────────────────────────────
    all_fips = sorted(STATE_POPS.keys())
    print(f"\nAllocating seats for {len(all_fips)} states…")
    print(f"  {'State':<6}  {'Abbr':<5}  {'Seats':>5}  {'N':>5}  Top allocations")
    print(f"  {thin}")

    result_rows  = []    # one row per state × party (with party_seats count)
    seat_counts  = {c: 0 for c in CAND_NAMES}
    n_processed  = 0
    n_skipped    = 0
    total_seats  = 0

    for fips in all_fips:
        abbr    = FIPS_TO_ABBR.get(fips, f"FIPS{fips}")
        pop     = STATE_POPS[fips]
        n_seats = max(1, round(pop / POP_PER_SEAT))

        mask    = inputstate == fips
        N_state = int(mask.sum())

        if N_state < MIN_RESPONDENTS:
            n_skipped += 1
            print(f"  {fips:<6}  {abbr:<5}  {n_seats:>5}  SKIPPED (N={N_state})")
            continue

        # Compute vote shares and allocate seats
        d_factors  = voter_factors[mask]
        d_weights  = weights[mask]
        shares     = compute_vote_shares(d_factors, cand_positions, d_weights)
        allocation = allocate_seats(shares, CAND_NAMES, n_seats)

        # Record results and accumulate seat counts
        for party, s in allocation.items():
            if s > 0:
                result_rows.append({
                    "state_fips":  fips,
                    "state_abbr":  abbr,
                    "total_seats": n_seats,
                    "party":       party,
                    "party_seats": s,
                    "vote_share":  round(float(shares[CAND_NAMES.index(party)]), 4),
                })
                seat_counts[party] += s

        total_seats += n_seats
        n_processed += 1

        top = sorted(allocation.items(), key=lambda x: -x[1])[:4]
        top_str = ", ".join(f"{p}:{s}" for p, s in top if s > 0)
        print(f"  {fips:<6}  {abbr:<5}  {n_seats:>5}  {N_state:>5}  {top_str}")

    print(f"\n  Processed: {n_processed} states  |  Skipped: {n_skipped}  |  Total seats: {total_seats}")

    # ── Save state results ────────────────────────────────────────────────────
    results_df = pd.DataFrame(result_rows).sort_values(["state_fips", "party"])
    results_path = OUTPUT_DIR / "house_results_by_state.csv"
    results_df.to_csv(results_path, index=False)
    print(f"\nSaved house_results_by_state.csv  ({len(results_df)} rows)")

    # ── Seat summary ──────────────────────────────────────────────────────────
    summary_rows = [
        {
            "party":        p,
            "seats":        seat_counts[p],
            "pct_national": round(seat_counts[p] / total_seats * 100, 2) if total_seats else 0.0,
        }
        for p in CAND_NAMES
    ]
    summary_df   = pd.DataFrame(summary_rows).sort_values("seats", ascending=False)
    summary_path = OUTPUT_DIR / "house_seat_summary.csv"
    summary_df.to_csv(summary_path, index=False)
    print(f"Saved house_seat_summary.csv  ({len(summary_df)} parties)")

    # ── Print summary ─────────────────────────────────────────────────────────
    print(f"\n{sep}")
    print("HOUSE — SEAT SUMMARY BY PARTY")
    print(sep)
    print(f"\n  {'Party':<6}  {'Seats':>6}  {'%':>6}")
    print(f"  {'-'*6}  {'-'*6}  {'-'*6}")
    for _, row in summary_df.iterrows():
        print(f"  {row['party']:<6}  {int(row['seats']):>6}  {row['pct_national']:>5.1f}%")
    print(f"  {'TOTAL':<6}  {total_seats:>6}  100.0%")

    print(f"\n{sep}")
    print("House proportional allocation complete.")
    print(sep)


if __name__ == "__main__":
    main()

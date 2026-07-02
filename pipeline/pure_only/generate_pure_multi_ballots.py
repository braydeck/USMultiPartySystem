#!/usr/bin/env python3
"""
generate_pure_multi_ballots.py
-------------------------------
Generate ranked ballots for 27 intra-party multi-candidates using
Plackett-Luce sampling.

Candidate design
----------------
All 9 parties field 3 candidates each. Candidates from the same party
share the same factor-space centroid, so cross-party ordering is
identical to the 9-party pure simulation. Within-party ordering is
governed by a "prominence weight" that scales each candidate's
Plackett-Luce score:

  All parties: _1 = 0.40, _2 = 0.35, _3 = 0.25

Because all same-party candidates sit at the same centroid, their
Gaussian proximity scores (with σ=0.35) are equal. The prominence
weight determines the exact split, and Plackett-Luce sequential
sampling produces the correct proportional within-party transfers:

  e.g. STY_1 voters who had STY_1 eliminated rank STY_2 next with
  probability 0.35/(0.35+0.25) ≈ 58%, STY_3 with ≈ 42%.

Cross-party rankings follow the existing distance-based logic; with
σ=0.35 all same-party candidates rank well above any cross-party
candidate for voters near that party's centroid.

Outputs
-------
  data/outputs/pure_multi/presidential_ballots.csv
  data/outputs/pure_multi/state_candidate_profiles.csv
"""

import os
import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR        = Path(__file__).parent.parent.parent
TYPOLOGY_PATH   = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
EFA_SCORES_PATH = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
# NO_STY=1 dissolves Solidarity (cluster 2): its candidates are dropped and its voters
# rank the remaining 9 parties by next-highest posterior. Output goes to a parallel tree.
NO_STY          = os.environ.get("NO_STY") == "1"
OUTPUT_DIR      = BASE_DIR / "data" / "outputs" / ("pure_multi_nosty" if NO_STY else "pure_multi")

PROB_COLS  = [f"prob_cluster_{k}" for k in range(10)]
FACTOR_COLS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]
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

# ── 21 candidates ──────────────────────────────────────────────────────────────
# cluster: CES 2024 typology cluster index (C7/BLB excluded)
# prominence: intra-party ballot weight; ratios produce first-choice splits of
#   40/35/25 (3-candidate) or 60/40 (2-candidate) among same-party voters.
CANDIDATES = [
    # ── CON: 3 candidates ──
    {"code": "CON_1", "party": "CON", "cluster": 0, "prominence": 0.40},
    {"code": "CON_2", "party": "CON", "cluster": 0, "prominence": 0.35},
    {"code": "CON_3", "party": "CON", "cluster": 0, "prominence": 0.25},
    # ── SD: 3 candidates ──
    {"code": "LBR_1",  "party": "LBR",  "cluster": 1, "prominence": 0.40},
    {"code": "LBR_2",  "party": "LBR",  "cluster": 1, "prominence": 0.35},
    {"code": "LBR_3",  "party": "LBR",  "cluster": 1, "prominence": 0.25},
    # ── STY: 3 candidates ──
    {"code": "STY_1", "party": "STY", "cluster": 2, "prominence": 0.40},
    {"code": "STY_2", "party": "STY", "cluster": 2, "prominence": 0.35},
    {"code": "STY_3", "party": "STY", "cluster": 2, "prominence": 0.25},
    # ── NAT: 3 candidates ──
    {"code": "NAT_1", "party": "NAT", "cluster": 3, "prominence": 0.40},
    {"code": "NAT_2", "party": "NAT", "cluster": 3, "prominence": 0.35},
    {"code": "NAT_3", "party": "NAT", "cluster": 3, "prominence": 0.25},
    # ── LIB: 3 candidates ──
    {"code": "LIB_1", "party": "LIB", "cluster": 4, "prominence": 0.40},
    {"code": "LIB_2", "party": "LIB", "cluster": 4, "prominence": 0.35},
    {"code": "LIB_3", "party": "LIB", "cluster": 4, "prominence": 0.25},
    # ── POP: 3 candidates ──
    {"code": "POP_1", "party": "POP", "cluster": 5, "prominence": 0.40},
    {"code": "POP_2", "party": "POP", "cluster": 5, "prominence": 0.35},
    {"code": "POP_3", "party": "POP", "cluster": 5, "prominence": 0.25},
    # ── CUP: 3 candidates ──
    {"code": "CUP_1", "party": "CUP", "cluster": 6, "prominence": 0.40},
    {"code": "CUP_2", "party": "CUP", "cluster": 6, "prominence": 0.35},
    {"code": "CUP_3", "party": "CUP", "cluster": 6, "prominence": 0.25},
    # ── DSA: 3 candidates ──
    {"code": "DSA_1", "party": "DSA", "cluster": 8, "prominence": 0.40},
    {"code": "DSA_2", "party": "DSA", "cluster": 8, "prominence": 0.35},
    {"code": "DSA_3", "party": "DSA", "cluster": 8, "prominence": 0.25},
    # ── PRG: 3 candidates ──
    {"code": "PRG_1", "party": "PRG", "cluster": 9, "prominence": 0.40},
    {"code": "PRG_2", "party": "PRG", "cluster": 9, "prominence": 0.35},
    {"code": "PRG_3", "party": "PRG", "cluster": 9, "prominence": 0.25},
    # ── OAO (Order and Opportunity Party, cluster 7): single candidate (small party) ──
    {"code": "OAO_1", "party": "OAO", "cluster": 7, "prominence": 1.00},
]

if NO_STY:
    CANDIDATES = [c for c in CANDIDATES if c["cluster"] != 2]

N_CANDIDATES = len(CANDIDATES)
CAND_CODES   = [c["code"] for c in CANDIDATES]


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


def compute_candidate_scores_prob(prob_matrix: np.ndarray) -> np.ndarray:
    """Equal PL scores for same-party candidates (prob_cluster_k only).

    All candidates from the same party get identical scores = the voter's
    GMM posterior for that party. This ensures same-party candidates cluster
    naturally in the PL draw. Prominence ordering is applied AFTER PL sampling
    in generate_ballots(), not here.
    """
    scores = np.zeros((len(prob_matrix), N_CANDIDATES))
    for j, cand in enumerate(CANDIDATES):
        scores[:, j] = prob_matrix[:, cand["cluster"]]
    return scores


def compute_candidate_scores(voter_factors: np.ndarray,
                              cluster_centroids: np.ndarray,
                              sigma: float = POSITIONAL_SIGMA) -> np.ndarray:
    """Gaussian proximity × prominence weight. Returns (N, N_CANDIDATES).

    Kept for reference. The canonical pipeline now uses compute_candidate_scores_prob().
    """
    positions   = np.array([cluster_centroids[c["cluster"]] for c in CANDIDATES])  # (21, 5)
    prominence  = np.array([c["prominence"] for c in CANDIDATES])                  # (21,)
    diff        = voter_factors[:, None, :] - positions[None, :, :]                # (N, 21, 5)
    dist_sq     = ((diff ** 2) * FACTOR_WEIGHTS).sum(axis=2)                      # (N, 21)
    proximity   = np.exp(-dist_sq / (2.0 * sigma ** 2))                           # (N, 21)
    return proximity * prominence[None, :]                                         # (N, 21)


def generate_ballots(scores: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Deterministic ranking with within-party prominence ordering.

    Candidates are ranked by score descending. Within each party,
    candidates are ordered by prominence (_1 before _2 before _3).
    Returns (N, N_CANDIDATES) int8 array of candidate indices.
    """
    N       = len(scores)
    ballots = np.zeros((N, N_CANDIDATES), dtype=np.int8)

    party_groups: dict[str, list[int]] = {}
    for idx, cand in enumerate(CANDIDATES):
        party = cand["party"]
        if party not in party_groups:
            party_groups[party] = []
        party_groups[party].append(idx)
    multi_parties = [idxs for idxs in party_groups.values() if len(idxs) > 1]

    for i in range(N):
        ballot = np.argsort(-scores[i])

        rank_of = {int(ballot[r]): r for r in range(N_CANDIDATES)}
        for party_idxs in multi_parties:
            positions = sorted(rank_of[idx] for idx in party_idxs)
            for k, pos in enumerate(positions):
                ballot[pos] = party_idxs[k]

        ballots[i] = ballot

    return ballots


def build_ballot_df(ballots: np.ndarray) -> pd.DataFrame:
    rank_cols = [f"rank_{k+1}" for k in range(N_CANDIDATES)]
    df = pd.DataFrame(ballots, columns=rank_cols)
    for col in rank_cols:
        df[col] = df[col].map(lambda x: CAND_CODES[x])
    df.index.name = "respondent_id"
    return df


def build_state_profiles(
    ballot_df: pd.DataFrame,
    prob_matrix: np.ndarray,
    inputstate: np.ndarray,
    weights: np.ndarray,
) -> pd.DataFrame:
    states = np.unique(inputstate)
    rows   = []
    for fips in states:
        mask  = inputstate == fips
        w     = weights[mask]
        w_sum = w.sum()
        if w_sum == 0:
            continue
        row = {
            "state_fips": int(fips),
            "state_abbr": FIPS_TO_ABBR.get(int(fips), f"FIPS{int(fips)}"),
            "total_weighted_respondents": w_sum,
        }
        for k, col in enumerate(PROB_COLS):
            row[col] = float(np.average(prob_matrix[mask, k], weights=w))
        fc = ballot_df["rank_1"].values[mask]
        for code in CAND_CODES:
            row[f"first_choice_{code}"] = float(w[fc == code].sum() / w_sum)
        rows.append(row)
    return pd.DataFrame(rows).sort_values("state_fips").reset_index(drop=True)


def main():
    rng = np.random.default_rng(42)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading typology CSV…")
    typology = pd.read_csv(TYPOLOGY_PATH)

    print("Loading EFA scores CSV…")
    efa = pd.read_csv(EFA_SCORES_PATH)

    assert len(typology) == len(efa)
    N = len(typology)

    prob_matrix   = typology[PROB_COLS].values.astype(np.float64)
    voter_factors = efa[FACTOR_COLS].values.astype(np.float64)
    inputstate    = efa["inputstate"].values
    weights       = efa["commonpostweight"].values

    print("\nComputing cluster centroids…")
    cluster_centroids = compute_cluster_centroids(efa, typology)

    print("\nComputing candidate scores (prob-cluster)…")
    scores = compute_candidate_scores_prob(prob_matrix)

    print(f"\nGenerating {N:,} ranked ballots (Plackett-Luce, seed=42)…")
    ballots    = generate_ballots(scores, rng)
    ballot_df  = build_ballot_df(ballots)

    # ── Verify within-party splits ──────────────────────────────────────────────
    print("\nFirst-choice frequencies (unweighted):")
    fc_counts = ballot_df["rank_1"].value_counts().rename("n")
    fc_pct    = (fc_counts / N * 100).round(2).rename("pct")
    table     = pd.concat([fc_counts, fc_pct], axis=1).sort_values("n", ascending=False)
    print(table.to_string())

    print("\nWithin-party first-choice splits (verify 40/35/25):")
    for party in ["CON", "LBR", "STY", "NAT", "LIB", "POP", "CUP", "DSA", "PRG"]:
        codes = [f"{party}_{i}" for i in (1, 2, 3)]
        totals = {c: fc_counts.get(c, 0) for c in codes}
        party_total = sum(totals.values())
        if party_total > 0:
            splits = " / ".join(f"{v/party_total*100:.1f}%" for v in totals.values())
            print(f"  {party}: {splits}  (target: 40.0% / 35.0% / 25.0%)")

    # ── Save ───────────────────────────────────────────────────────────────────
    ballot_out = OUTPUT_DIR / "presidential_ballots.csv"
    ballot_df.to_csv(ballot_out, index=True)
    print(f"\nSaved ballots → {ballot_out}  ({len(ballot_df):,} rows × {N_CANDIDATES} ranks)")

    print("\nBuilding state-level profiles…")
    state_df  = build_state_profiles(ballot_df, prob_matrix, inputstate, weights)
    state_out = OUTPUT_DIR / "state_candidate_profiles.csv"
    state_df.to_csv(state_out, index=False)
    print(f"Saved state profiles → {state_out}  ({len(state_df)} states)")

    print("\n✓ Done.")


if __name__ == "__main__":
    main()

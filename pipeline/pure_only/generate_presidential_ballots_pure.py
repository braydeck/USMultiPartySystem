#!/usr/bin/env python3
"""
generate_presidential_ballots.py
---------------------------------
Generate ranked ballots for 18 presidential candidates using Plackett-Luce
sampling from each respondent's cluster probability vector.

Also produces:
  - state_candidate_profiles.csv   (weighted cluster shares + first-choice shares by state)

Inputs (positionally aligned, 45,707 rows each):
  Claude/data/typology_cluster_assignments.csv  → prob_cluster_0..9
  Claude/data/efa_factor_scores.csv             → inputstate, commonpostweight

Outputs:
  Claude/outputs/presidential_ballots.csv
  Claude/outputs/state_candidate_profiles.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
# pure_only/ variant: 9 pure-cluster candidates only (no senate-derived blends).
BASE_DIR        = Path(__file__).parent.parent.parent
TYPOLOGY_PATH   = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
EFA_SCORES_PATH = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
OUTPUT_DIR      = BASE_DIR / "data" / "outputs" / "pure_only"

PROB_COLS = [f"prob_cluster_{k}" for k in range(10)]

# ── FIPS → state abbreviation ──────────────────────────────────────────────────
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

# ── 20 Presidential Candidates ─────────────────────────────────────────────────
# primary / secondary = cluster index (0-9); C7 (Blue Dogs) not used
# w_primary + w_secondary = 1.0; secondary=None for platonic candidates
# Congressional stable: 9 pure cluster candidates
# Governor/Senate stable: 11 senate-derived blends (weights = national senate averages)
CANDIDATES = [
    # ── Congressional Stable (pure) — PURE-ONLY VARIANT ──
    {"code": "RH",      "name": "CON",     "primary": 0, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "MW",      "name": "SD",      "primary": 1, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "MRJ",     "name": "STY",     "primary": 2, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "BE",      "name": "NAT",     "primary": 3, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "CO",      "name": "LIB",     "primary": 4, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "DH",      "name": "REF",     "primary": 5, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "LK",      "name": "CTR",     "primary": 6, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "ZN",      "name": "DSA",     "primary": 8, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "JR",      "name": "PRG",     "primary": 9, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
]

N_CANDIDATES  = len(CANDIDATES)
CAND_CODES    = [c["code"] for c in CANDIDATES]
CAND_IDX      = {c["code"]: i for i, c in enumerate(CANDIDATES)}


FACTOR_COLS      = ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]
POSITIONAL_SIGMA = 0.35
FACTOR_WEIGHTS   = np.array([1.0, 1.0, 1.0, 1.0, 1.0])  # uniform — centroid geometry handles discrimination


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


def candidate_position(cand: dict, cluster_centroids: np.ndarray) -> np.ndarray:
    """Candidate's location in 5-D factor space (weighted blend of centroids)."""
    pos = cand["w_primary"] * cluster_centroids[cand["primary"]]
    if cand["secondary"] is not None:
        pos = pos + cand["w_secondary"] * cluster_centroids[int(cand["secondary"])]
    return pos


def compute_candidate_scores(voter_factors: np.ndarray,
                              cluster_centroids: np.ndarray,
                              sigma: float = POSITIONAL_SIGMA) -> np.ndarray:
    """Gaussian proximity in 5-D factor space.

    score[i, j] = exp(-‖voter_factors[i] - cand_position[j]‖² / (2 σ²))

    Replaces cluster-membership scoring (w_p·p_primary + w_s·p_secondary).
    See run_senate_simulation.py for design discussion — pure candidates no
    longer get a 1.0 multiplier on their own cluster, so coalition candidates
    can compete for first-preference votes on actual factor-space proximity.
    """
    cand_positions = np.stack([candidate_position(c, cluster_centroids) for c in CANDIDATES])
    diff = voter_factors[:, None, :] - cand_positions[None, :, :]
    dist_sq = ((diff ** 2) * FACTOR_WEIGHTS).sum(axis=2)
    return np.exp(-dist_sq / (2.0 * sigma ** 2))


def generate_ballots(scores: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Deterministic ranking: sort candidates by score descending.
    Returns (N, 18) int8 array where
    ballots[i][k] = index of candidate at rank k+1 for respondent i.
    """
    N = len(scores)
    ballots = np.zeros((N, N_CANDIDATES), dtype=np.int8)
    for i in range(N):
        ballots[i] = np.argsort(-scores[i])
    return ballots


def build_ballot_df(ballots: np.ndarray) -> pd.DataFrame:
    """Convert int8 ballot array to DataFrame with candidate code columns."""
    rank_cols = [f"rank_{k+1}" for k in range(N_CANDIDATES)]
    df = pd.DataFrame(ballots, columns=rank_cols)
    # replace integer indices with candidate codes
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
    """
    Produce one row per state with:
      - total_weighted_respondents
      - weighted mean prob_cluster_0..9
      - weighted first-choice share for each of the 18 candidates
    """
    states = np.unique(inputstate)
    rows = []
    for fips in states:
        mask = inputstate == fips
        w = weights[mask]
        w_sum = w.sum()
        if w_sum == 0:
            continue

        row = {
            "state_fips": int(fips),
            "state_abbr": FIPS_TO_ABBR.get(int(fips), f"FIPS{int(fips)}"),
            "total_weighted_respondents": w_sum,
        }

        # weighted mean cluster probabilities
        for k, col in enumerate(PROB_COLS):
            row[col] = float(np.average(prob_matrix[mask, k], weights=w))

        # weighted first-choice shares
        fc = ballot_df["rank_1"].values[mask]
        for code in CAND_CODES:
            row[f"first_choice_{code}"] = float(w[fc == code].sum() / w_sum)

        rows.append(row)

    return pd.DataFrame(rows).sort_values("state_fips").reset_index(drop=True)


def main():
    rng = np.random.default_rng(42)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Load data ──────────────────────────────────────────────────────────────
    print("Loading typology CSV…")
    typology = pd.read_csv(TYPOLOGY_PATH)
    print(f"  typology shape: {typology.shape}")

    print("Loading EFA scores CSV…")
    efa = pd.read_csv(EFA_SCORES_PATH)
    print(f"  efa shape:      {efa.shape}")

    assert len(typology) == len(efa), (
        f"Row count mismatch: typology={len(typology)}, efa={len(efa)}"
    )
    N = len(typology)

    prob_matrix   = typology[PROB_COLS].values.astype(np.float64)
    voter_factors = efa[FACTOR_COLS].values.astype(np.float64)
    inputstate    = efa["inputstate"].values
    weights       = efa["commonpostweight"].values

    # ── Check for Puerto Rico ──────────────────────────────────────────────────
    unique_states = sorted(np.unique(inputstate))
    pr_count = int((inputstate == 72).sum()) if 72 in unique_states else 0
    print(f"\n  States found: {len(unique_states)}  |  PR (FIPS 72) respondents: {pr_count}")

    # ── Cluster centroids in 5-D factor space ─────────────────────────────────
    print("\nComputing cluster centroids…")
    cluster_centroids = compute_cluster_centroids(efa, typology)

    # ── Candidate scores (GMM posterior — consistent with clustering) ────────
    print("\nComputing candidate scores (GMM posterior)…")
    scores = np.zeros((N, N_CANDIDATES))
    for j, cand in enumerate(CANDIDATES):
        scores[:, j] = prob_matrix[:, cand["primary"]]
    print(f"  scores matrix shape: {scores.shape}  min={scores.min():.4f}  max={scores.max():.4f}")

    # ── Plackett-Luce ballots ──────────────────────────────────────────────────
    print(f"\nGenerating {N:,} ranked ballots (Plackett-Luce, seed=42)…")
    ballots = generate_ballots(scores, rng)
    ballot_df = build_ballot_df(ballots)

    # sanity checks
    assert len(ballot_df) == N, "Ballot row count mismatch"
    for row_idx in range(N):
        assert len(set(ballot_df.iloc[row_idx])) == N_CANDIDATES, \
            f"Duplicate candidate in ballot row {row_idx}"
    print("  ✓ No duplicates in sampled ballots")

    # ── Save ballots ───────────────────────────────────────────────────────────
    ballot_out = OUTPUT_DIR / "presidential_ballots.csv"
    ballot_df.to_csv(ballot_out, index=True)
    print(f"\nSaved ballots → {ballot_out}")
    print(f"  Rows: {len(ballot_df):,}   Columns: {list(ballot_df.columns[:4])} … {list(ballot_df.columns[-2:])}")

    # ── First-choice frequency table ───────────────────────────────────────────
    fc_counts = ballot_df["rank_1"].value_counts().rename("first_choice_count")
    fc_pct    = (fc_counts / N * 100).round(2).rename("first_choice_pct")
    fc_table  = pd.concat([fc_counts, fc_pct], axis=1).sort_values("first_choice_count", ascending=False)
    print("\nFirst-choice frequencies (unweighted):")
    print(fc_table.to_string())

    # ── State profiles ─────────────────────────────────────────────────────────
    print("\nBuilding state-level profiles…")
    state_df = build_state_profiles(ballot_df, prob_matrix, inputstate, weights)
    state_out = OUTPUT_DIR / "state_candidate_profiles.csv"
    state_df.to_csv(state_out, index=False)
    print(f"Saved state profiles → {state_out}")
    print(f"  Rows: {len(state_df)}   Columns: {len(state_df.columns)}")

    # sample: top first-choice candidate per state
    fc_cols = [f"first_choice_{c}" for c in CAND_CODES]
    state_df["top_candidate"] = state_df[fc_cols].idxmax(axis=1).str.replace("first_choice_", "")
    print("\nTop first-choice candidate by state (weighted):")
    summary = state_df[["state_abbr", "total_weighted_respondents", "top_candidate"]].copy()
    summary["total_weighted_respondents"] = summary["total_weighted_respondents"].round(1)
    print(summary.to_string(index=False))

    print("\n✓ Done.")


if __name__ == "__main__":
    main()

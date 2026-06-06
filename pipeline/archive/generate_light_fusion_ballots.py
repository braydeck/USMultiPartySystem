#!/usr/bin/env python3
"""
generate_light_fusion_ballots.py
---------------------------------
Generate ranked ballots for 25 light-fusion presidential candidates using
Plackett-Luce sampling from each respondent's 5-D factor position.

The slate = 9 pure party candidates + 16 "light fusion" variants at 80/20.
Light fusion candidates (e.g. STY_sd) represent individuals who would still
caucus with their primary party but lean slightly toward an adjacent party.
Distinct from "blended" (50/50 midpoints) used in the senate-derived scenario.

Outputs:
  data/outputs/light_fusion/presidential_ballots.csv
  data/outputs/light_fusion/state_candidate_profiles.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR        = Path(__file__).parent.parent
TYPOLOGY_PATH   = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
EFA_SCORES_PATH = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
OUTPUT_DIR      = BASE_DIR / "data" / "outputs" / "light_fusion"

PROB_COLS   = [f"prob_cluster_{k}" for k in range(10)]
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

# ── 25 Light Fusion Presidential Candidates ────────────────────────────────────
# Pure parties: primary = cluster index, secondary = None, w = 1.0
# Light fusion: primary/secondary = cluster indices, w_primary = 0.80, w_secondary = 0.20
# Cluster map: CON=0, SD=1, STY=2, NAT=3, LIB=4, REF=5, CTR=6, [C7 skipped], DSA=8, PRG=9
CANDIDATES = [
    # ── Pure Party Candidates ──
    {"code": "RH",      "name": "CON",     "primary": 0, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "MW",      "name": "SD",      "primary": 1, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "MRJ",     "name": "STY",     "primary": 2, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "BE",      "name": "NAT",     "primary": 3, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "CO",      "name": "LIB",     "primary": 4, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "DH",      "name": "REF",     "primary": 5, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "LK",      "name": "CTR",     "primary": 6, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "ZN",      "name": "DSA",     "primary": 8, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "JR",      "name": "PRG",     "primary": 9, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    # ── Light Fusion Candidates (80/20) ──
    # Left flank: PRG ↔ DSA ↔ LIB
    {"code": "PRG_dsa", "name": "PRG_dsa", "primary": 9, "secondary": 8, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "DSA_prg", "name": "DSA_prg", "primary": 8, "secondary": 9, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "DSA_lib", "name": "DSA_lib", "primary": 8, "secondary": 4, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "LIB_dsa", "name": "LIB_dsa", "primary": 4, "secondary": 8, "w_primary": 0.80, "w_secondary": 0.20},
    # Center-left: LIB ↔ SD ↔ STY
    {"code": "LIB_sd",  "name": "LIB_sd",  "primary": 4, "secondary": 1, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "SD_lib",  "name": "SD_lib",  "primary": 1, "secondary": 4, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "SD_sty",  "name": "SD_sty",  "primary": 1, "secondary": 2, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "STY_sd",  "name": "STY_sd",  "primary": 2, "secondary": 1, "w_primary": 0.80, "w_secondary": 0.20},
    # Center: STY ↔ CTR
    {"code": "STY_ctr", "name": "STY_ctr", "primary": 2, "secondary": 6, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "CTR_sty", "name": "CTR_sty", "primary": 6, "secondary": 2, "w_primary": 0.80, "w_secondary": 0.20},
    # Center-right: CTR ↔ CON
    {"code": "CTR_con", "name": "CTR_con", "primary": 6, "secondary": 0, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "CON_ctr", "name": "CON_ctr", "primary": 0, "secondary": 6, "w_primary": 0.80, "w_secondary": 0.20},
    # Right flank: CON ↔ REF ↔ NAT
    {"code": "CON_ref", "name": "CON_ref", "primary": 0, "secondary": 5, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "REF_con", "name": "REF_con", "primary": 5, "secondary": 0, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "REF_nat", "name": "REF_nat", "primary": 5, "secondary": 3, "w_primary": 0.80, "w_secondary": 0.20},
    {"code": "NAT_ref", "name": "NAT_ref", "primary": 3, "secondary": 5, "w_primary": 0.80, "w_secondary": 0.20},
]

N_CANDIDATES = len(CANDIDATES)
CAND_CODES   = [c["code"] for c in CANDIDATES]
CAND_IDX     = {c["code"]: i for i, c in enumerate(CANDIDATES)}


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
    """Gaussian proximity score: exp(-||voter - cand||² / (2σ²))."""
    cand_positions = np.stack([candidate_position(c, cluster_centroids) for c in CANDIDATES])
    diff    = voter_factors[:, None, :] - cand_positions[None, :, :]
    dist_sq = ((diff ** 2) * FACTOR_WEIGHTS).sum(axis=2)
    return np.exp(-dist_sq / (2.0 * sigma ** 2))


def generate_ballots(scores: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Plackett-Luce sampling. Returns (N, N_CANDIDATES) int8 array."""
    N       = len(scores)
    EPSILON = 1e-10
    ballots = np.zeros((N, N_CANDIDATES), dtype=np.int8)
    for i in range(N):
        probs = scores[i] + EPSILON
        probs /= probs.sum()
        ballots[i] = rng.choice(N_CANDIDATES, size=N_CANDIDATES, replace=False, p=probs)
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
    rows = []
    for fips in states:
        mask  = inputstate == fips
        w     = weights[mask]
        w_sum = w.sum()
        if w_sum == 0:
            continue
        row = {
            "state_fips":                  int(fips),
            "state_abbr":                  FIPS_TO_ABBR.get(int(fips), f"FIPS{int(fips)}"),
            "total_weighted_respondents":  w_sum,
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

    print(f"\nComputing cluster centroids…")
    cluster_centroids = compute_cluster_centroids(efa, typology)

    print(f"Computing candidate scores (positional, σ={POSITIONAL_SIGMA})…")
    scores = compute_candidate_scores(voter_factors, cluster_centroids)

    print(f"Generating {N:,} ranked ballots (Plackett-Luce, seed=42)…")
    ballots   = generate_ballots(scores, rng)
    ballot_df = build_ballot_df(ballots)

    ballot_out = OUTPUT_DIR / "presidential_ballots.csv"
    ballot_df.to_csv(ballot_out, index=True)
    print(f"Saved ballots → {ballot_out}  ({N:,} rows × {N_CANDIDATES} candidates)")

    fc_counts = ballot_df["rank_1"].value_counts().rename("first_choice_count")
    fc_pct    = (fc_counts / N * 100).round(2).rename("first_choice_pct")
    fc_table  = pd.concat([fc_counts, fc_pct], axis=1).sort_values("first_choice_count", ascending=False)
    print("\nFirst-choice frequencies (unweighted):")
    print(fc_table.to_string())

    print("\nBuilding state-level profiles…")
    state_df  = build_state_profiles(ballot_df, prob_matrix, inputstate, weights)
    state_out = OUTPUT_DIR / "state_candidate_profiles.csv"
    state_df.to_csv(state_out, index=False)
    print(f"Saved state profiles → {state_out}")


if __name__ == "__main__":
    main()

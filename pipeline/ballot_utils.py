"""
ballot_utils.py
---------------
Shared utilities for ballot generation across all simulation scripts.

Uses GMM posterior probabilities for inter-party scoring (matches the
clustering that defined the parties) with Euclidean proximity for
intra-party variant differentiation.
"""

import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR      = Path(__file__).parent.parent
TYPOLOGY_PATH = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
EFA_PATH      = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
FACTOR_COLS   = ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]

POSITIONAL_SIGMA = 0.35


def load_voter_probs(typology_df: pd.DataFrame = None) -> np.ndarray:
    """Load (N, 10) GMM posterior probabilities from typology data.

    Returns array indexed by cluster: column k = prob_cluster_k.
    """
    if typology_df is None:
        typology_df = pd.read_csv(TYPOLOGY_PATH)
    probs = np.zeros((len(typology_df), 10))
    for k in range(10):
        col = f"prob_cluster_{k}"
        if col in typology_df.columns:
            probs[:, k] = typology_df[col].values
    return probs


def score_candidates(voter_probs: np.ndarray,
                     voter_factors: np.ndarray,
                     cand_positions: np.ndarray,
                     cand_cluster_indices: np.ndarray,
                     sigma: float = POSITIONAL_SIGMA) -> np.ndarray:
    """Score each voter × candidate pair.

    Inter-party ranking uses GMM posteriors (consistent with clustering).
    Intra-party differentiation uses Euclidean proximity normalized within
    each party, so the proximity term only distributes probability among
    a party's candidates without affecting inter-party rankings.

    For single-candidate parties, intra-party term = 1 (pure GMM posterior).

    Args:
        voter_probs:          (N, 10) GMM posterior per cluster
        voter_factors:        (N, 5) voter factor scores
        cand_positions:       (M, 5) candidate positions in factor space
        cand_cluster_indices: (M,) int — parent cluster for each candidate
        sigma:                bandwidth for intra-party proximity

    Returns: (N, M) combined scores (use as Plackett-Luce weights)
    """
    # Inter-party: GMM posterior for each candidate's party
    party_scores = voter_probs[:, cand_cluster_indices]               # (N, M)

    # Intra-party: Euclidean proximity, normalized within each party
    diff     = voter_factors[:, None, :] - cand_positions[None, :, :]  # (N, M, 5)
    dist_sq  = (diff ** 2).sum(axis=2)                                 # (N, M)
    raw_prox = np.exp(-dist_sq / (2.0 * sigma ** 2))                   # (N, M)

    intra = np.zeros_like(raw_prox)
    for k in np.unique(cand_cluster_indices):
        mask      = cand_cluster_indices == k
        party_sum = raw_prox[:, mask].sum(axis=1, keepdims=True)
        party_sum = np.where(party_sum > 0, party_sum, 1.0)
        intra[:, mask] = raw_prox[:, mask] / party_sum

    return party_scores * intra

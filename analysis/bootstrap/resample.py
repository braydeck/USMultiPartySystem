"""Stratified respondent resampling — the only source of randomness in the harness."""

import numpy as np


def stratified_indices(strata: np.ndarray, seed: int) -> np.ndarray:
    """Row positions resampled with replacement *within* each stratum.

    Each stratum contributes exactly its original count, so per-state N never
    changes and no pipeline can fail by dropping a state below MIN_RESPONDENTS.
    Rows come back grouped in sorted stratum order; only positional consistency
    across the row-aligned input files matters, not the original ordering.
    """
    rng = np.random.default_rng(seed)
    out = np.empty(len(strata), dtype=np.int64)
    pos = 0
    for s in np.unique(strata):
        members = np.flatnonzero(strata == s)
        out[pos:pos + len(members)] = rng.choice(members, size=len(members), replace=True)
        pos += len(members)
    assert pos == len(strata), f"covered {pos} of {len(strata)} rows"
    return out

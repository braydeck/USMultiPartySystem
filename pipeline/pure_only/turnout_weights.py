#!/usr/bin/env python3
"""
turnout_weights.py
------------------
Shared helper for the TURNOUT_WEIGHT=1 ("current participation") scenario.

When on, each respondent's ballot weight is scaled by its cluster's validated
2024 turnout rate (data/processed/turnout_propensity.csv, produced by
compute_turnout_propensity.py). This scales how much each electoral force
counts WITHOUT altering any ballot's ranking — isolating the turnout variable.

Party centroids (positions in factor space) are deliberately left un-scaled by
callers, so party positions stay fixed across the full-/current-participation
cells; only vote-counting weight and cluster shares change.

Tree convention:
  ballots are unaffected by turnout, so they are read from the base tree
  (pure_multi / pure_multi_nosty). Turnout-weighted OUTPUT goes to a parallel
  '<base>_turnout' tree via output_tree().
"""

import os
import numpy as np
import pandas as pd
from pathlib import Path

TURNOUT_WEIGHT = os.environ.get("TURNOUT_WEIGHT") == "1"
# Gap-compression parameter λ ∈ [0,1]: each force's turnout moves toward parity as
#   t_k(λ) = t_k + λ·(1 − t_k).  λ=0 = observed 2024 gaps (floor); λ=1 = full parity
# (= full participation). Intermediate λ = the 'tuning fork' sensitivity sweep.
TURNOUT_LAMBDA = float(os.environ.get("TURNOUT_LAMBDA", "0"))
_BASE        = Path(__file__).parent.parent.parent
_TURNOUT_CSV = _BASE / "data" / "processed" / "turnout_propensity.csv"

_cache = None


def turnout_multiplier(n: int) -> np.ndarray:
    """Per-row turnout multiplier aligned to the efa/ballot rows (length n).

    All-ones when TURNOUT_WEIGHT is off. When on, returns each row's per-cluster
    validated turnout rate compressed toward parity by λ. Asserts row alignment
    (same 45,707-row order as efa_factor_scores.csv) before returning.
    """
    if not TURNOUT_WEIGHT:
        return np.ones(n)
    global _cache
    if _cache is None:
        _cache = pd.read_csv(_TURNOUT_CSV)
    assert len(_cache) == n, (
        f"turnout_propensity rows ({len(_cache)}) != data rows ({n}) — "
        "alignment broken; regenerate with compute_turnout_propensity.py")
    t = _cache["turnout_cluster"].values.astype(float)
    return t + TURNOUT_LAMBDA * (1.0 - t)   # compress the inter-force gap toward parity


def output_tree(base_tree: str) -> str:
    """Append the _turnout[_lNN] suffix to the output tree when the knob is on.

    λ=0 keeps the plain '_turnout' floor tree (back-compatible); λ>0 adds '_lNN'
    (e.g. _l25) so each compression stop lands in its own parallel tree.
    """
    if not TURNOUT_WEIGHT:
        return base_tree
    suffix = "_turnout"
    if TURNOUT_LAMBDA > 0:
        suffix += f"_l{round(TURNOUT_LAMBDA * 100)}"
    return base_tree + suffix

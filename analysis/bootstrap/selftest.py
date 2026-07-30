#!/usr/bin/env python3
"""Assertion-based verification for the bootstrap harness. Run: python3 analysis/bootstrap/selftest.py

This repo has no pytest; these are plain asserts so they run with the stdlib interpreter.
"""
import sys
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from analysis.bootstrap.resample import stratified_indices


def test_preserves_stratum_sizes():
    strata = np.array([1, 1, 1, 2, 2, 3])
    idx = stratified_indices(strata, seed=42)
    assert len(idx) == len(strata), f"length {len(idx)} != {len(strata)}"
    got = Counter(strata[idx])
    assert got == Counter(strata), f"stratum sizes changed: {got} vs {Counter(strata)}"


def test_only_draws_within_stratum():
    strata = np.array([1, 1, 1, 2, 2, 3])
    idx = stratified_indices(strata, seed=7)
    # Resampled rows appear grouped by stratum, in sorted stratum order.
    assert list(strata[idx]) == sorted(strata), "rows leaked across strata"


def test_is_deterministic_and_seed_sensitive():
    strata = np.repeat(np.arange(20), 30)
    a = stratified_indices(strata, seed=42)
    b = stratified_indices(strata, seed=42)
    c = stratified_indices(strata, seed=43)
    assert np.array_equal(a, b), "same seed gave different draws"
    assert not np.array_equal(a, c), "different seeds gave identical draws"


def test_resamples_with_replacement():
    strata = np.zeros(200, dtype=int)
    idx = stratified_indices(strata, seed=1)
    assert len(set(idx.tolist())) < len(idx), "no duplicates — not sampling with replacement"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} checks passed")

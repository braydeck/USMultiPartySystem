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
    # Later tasks rely on int64 indices; a dtype regression must fail here, not downstream.
    assert idx.dtype == np.int64, f"expected int64, got {idx.dtype}"


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


def test_handles_empty_input():
    idx = stratified_indices(np.array([], dtype=int), seed=1)
    assert len(idx) == 0, f"expected empty result, got length {len(idx)}"
    assert idx.dtype == np.int64, f"expected int64, got {idx.dtype}"


def test_handles_singleton_stratum():
    strata = np.array([1, 2, 2])
    idx = stratified_indices(strata, seed=3)
    # Stratum 1 has one member (row 0); with replacement, its only possible draw is itself.
    singleton_draws = idx[strata[idx] == 1]
    assert list(singleton_draws) == [0], f"singleton stratum should draw row 0, got {singleton_draws}"


def test_injection_reindexes_targets():
    import pandas as pd
    from analysis.bootstrap.inject import PROCESSED_FILES, resampled_inputs

    target, turnout = PROCESSED_FILES[0], PROCESSED_FILES[2]
    real = pd.read_csv(target)
    idx = stratified_indices(real["inputstate"].values, seed=42)
    with resampled_inputs(idx):
        got = pd.read_csv(target)
        other = pd.read_csv(turnout)
    assert len(got) == len(real), "row count changed"
    assert len(other) == len(real), "second target not length-preserved"
    assert list(got["inputstate"]) == list(real["inputstate"].values[idx]), "wrong reindex"
    assert list(got.index) == list(range(len(got))), "index not reset"


def test_injection_leaves_non_targets_alone():
    """A file that is not per-respondent must read normally inside the block."""
    import pandas as pd
    from analysis.bootstrap.inject import resampled_inputs

    root = Path(__file__).resolve().parents[2]
    other = root / "data" / "outputs" / "pure_multi" / "state_candidate_profiles.csv"
    before = pd.read_csv(other)
    idx = stratified_indices(pd.read_csv(root / "data" / "processed" / "efa_factor_scores.csv")["inputstate"].values, seed=1)
    with resampled_inputs(idx):
        during = pd.read_csv(other)
    assert len(during) == len(before), "a non-target file was reindexed"


def test_injection_matches_relative_paths():
    """Pipelines build BASE_DIR without .resolve(), so callers may pass relative
    paths; those must match the (absolute) PROCESSED_FILES targets too, or the
    file silently reads unresampled."""
    import os

    import pandas as pd
    from analysis.bootstrap.inject import PROCESSED_FILES, resampled_inputs

    target = PROCESSED_FILES[0]
    repo_root = Path(__file__).resolve().parents[2]
    rel_target = os.path.relpath(target, repo_root)

    real = pd.read_csv(target)
    idx = stratified_indices(real["inputstate"].values, seed=42)
    with resampled_inputs(idx):
        got = pd.read_csv(rel_target)
    assert list(got["inputstate"]) == list(real["inputstate"].values[idx]), (
        "relative path was not matched against absolute PROCESSED_FILES targets"
    )


def test_injection_restores_pandas_and_asserts_on_mismatch():
    import pandas as pd
    from analysis.bootstrap.inject import PROCESSED_FILES, resampled_inputs

    target = PROCESSED_FILES[0]
    original = pd.read_csv
    try:
        with resampled_inputs(np.arange(10)):
            pd.read_csv(target)
    except AssertionError:
        pass
    else:
        raise AssertionError("no AssertionError on length mismatch")
    assert pd.read_csv is original, "pandas was not restored after the block raised"


def test_observed_draw_matches_committed_counts():
    """The observed-sample draw must reproduce the committed deterministic seat counts.
    If this fails, the harness is resampling something it shouldn't."""
    import json
    from collections import Counter
    from analysis.bootstrap.contests import run_draw

    got = run_draw(seed=0, lam=0.05, depth=7, observed=True)

    root = Path(__file__).resolve().parents[2]
    committed = json.loads((root / "viz" / "src" / "data" / "pureMultiSenateIRVTurnoutL5.json").read_text())
    want = Counter(x["senatorParty"] for x in committed)
    have = Counter(c.rsplit("_", 1)[0] for c in got["senate"]["irv"].values())
    assert have == want, f"IRV senate drifted: {dict(have)} vs {dict(want)}"

    cond_committed = json.loads((root / "viz" / "src" / "data" / "pureMultiSenateCondorcetTurnoutL5.json").read_text())
    want_c = Counter(x["senatorParty"] for x in cond_committed)
    have_c = Counter(c.rsplit("_", 1)[0] for c in got["senate"]["cond"].values())
    assert have_c == want_c, f"Condorcet senate drifted: {dict(have_c)} vs {dict(want_c)}"

    assert sum(got["house"].values()) == 873, f"house total {sum(got['house'].values())} != 873"
    assert len(got["primary"]) == 5, f"primary slate has {len(got['primary'])} candidates, expected 5"
    assert got["president"]["irv"], "no presidential IRV winner"


def test_resampled_draw_preserves_state_counts():
    from analysis.bootstrap.contests import run_draw
    got = run_draw(seed=43, lam=0.05, depth=7)
    assert len(got["senate"]["irv"]) == 51, f"{len(got['senate']['irv'])} senate races, expected 51"
    assert sum(got["house"].values()) == 873, "house total changed under resampling"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} checks passed")

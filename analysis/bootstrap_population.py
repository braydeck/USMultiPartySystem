#!/usr/bin/env python3
"""
bootstrap_population.py
-----------------------
Sampling range for each party's share of the adult population.

Seat shares already carry bootstrap intervals, but a population-vs-seat chart is only
answerable if BOTH sides do: without a population interval you cannot tell a real
mis-representation from one that sits inside sampling noise.

Population share is a soft-weighted mean of each respondent's cluster-membership
probabilities, so unlike the seat counts it needs no election run — one weighted mean per
draw. That makes 1000 draws a few seconds rather than the seat harness's ~80 minutes.

It is also **stop-invariant**: population share uses `commonpostweight` alone and is never
turnout-weighted, because it describes the population rather than the electorate. So this
writes one payload, not seven. (That asymmetry is the whole point of the chart: a
turnout-weighted seat share against an unweighted population share is where
disproportionality shows up.)

Provenance: data/processed/{efa_factor_scores,typology_cluster_assignments}.csv.
Resampling is stratified within state and seeded (42 + draw), matching the seat harness so
the two sides of the chart are the same resamples.

Usage:  python3 analysis/bootstrap_population.py [--draws 1000]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))

from analysis.bootstrap.contests import CLUSTER_TO_PARTY  # noqa: E402
from analysis.bootstrap.resample import stratified_indices  # noqa: E402

PROB_COLS = [f"prob_cluster_{k}" for k in range(10)]
OUT = BASE / "viz" / "src" / "data" / "populationShareRange.json"


def _shares(probs: np.ndarray, weights: np.ndarray, idx: np.ndarray) -> np.ndarray:
    """Soft-weighted share of the population in each cluster, as percentages summing to 100.
    Mirrors prepare_data.py's _national_pop_shares_10 so the point estimate matches the
    committed partyPopulation.json rather than being a parallel definition."""
    w = weights[idx]
    return (probs[idx] * w[:, None]).sum(axis=0) / w.sum() * 100.0


def build(n_draws: int) -> dict:
    efa = pd.read_csv(BASE / "data" / "processed" / "efa_factor_scores.csv")
    typ = pd.read_csv(BASE / "data" / "processed" / "typology_cluster_assignments.csv")
    assert len(efa) == len(typ), f"row mismatch {len(efa)} vs {len(typ)}"

    probs = typ[PROB_COLS].values.astype(np.float64)
    weights = efa["commonpostweight"].values.astype(np.float64)
    state = efa["inputstate"].values.astype(int)

    point = _shares(probs, weights, np.arange(len(weights)))
    draws = np.vstack([_shares(probs, weights, stratified_indices(state, seed=42 + d))
                       for d in range(n_draws)])

    assert abs(point.sum() - 100.0) < 1e-6, f"point shares sum to {point.sum()}"
    assert np.abs(draws.sum(axis=1) - 100.0).max() < 1e-6, "a draw did not sum to 100"

    shares = {}
    for k in range(10):
        col = draws[:, k]
        lo, hi = np.percentile(col, [2.5, 97.5])
        shares[CLUSTER_TO_PARTY[k]] = {
            "point": round(float(point[k]), 2),
            "expected": round(float(col.mean()), 2),
            # Widen so the interval always contains its own centre, matching the seat
            # payload's convention; a party pinned near its maximum can otherwise land
            # with a percentile bound on the wrong side of the mean.
            "lo": round(min(float(lo), float(col.mean())), 2),
            "hi": round(max(float(hi), float(col.mean())), 2),
        }
    return {"nDraws": n_draws, "seed": 42, "stopInvariant": True, "shares": shares}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=1000)
    a = ap.parse_args()

    payload = build(a.draws)
    OUT.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True))

    total = sum(v["point"] for v in payload["shares"].values())
    print(f"{a.draws} draws -> {OUT.name} ({OUT.stat().st_size} bytes), point shares sum {total:.2f}")
    for p, v in sorted(payload["shares"].items(), key=lambda kv: -kv[1]["point"]):
        print(f"  {p:4s} {v['point']:6.2f}  [{v['lo']:5.2f}, {v['hi']:5.2f}]  width {v['hi']-v['lo']:.2f}")


if __name__ == "__main__":
    main()

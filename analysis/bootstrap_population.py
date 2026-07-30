#!/usr/bin/env python3
"""
bootstrap_population.py
-----------------------
Sampling ranges for each party's share of the adult population and of the electorate.

Seat shares already carry bootstrap intervals, but a population-vs-seat chart is only
answerable if BOTH sides do: without a population interval you cannot tell a real
mis-representation from one that sits inside sampling noise.

Population share is a soft-weighted mean of each respondent's cluster-membership
probabilities, so unlike the seat counts it needs no election run — one weighted mean per
draw. That makes 1000 draws a few seconds rather than the seat harness's ~80 minutes.

Two quantities, and the difference between them is the whole point:

  population  weighted by `commonpostweight` alone. Describes the country, so it is
              **stop-invariant** — one set of intervals, not seven.
  votes       weighted by `commonpostweight x turnout multiplier`. Describes the
              electorate, so it moves with the participation slider and needs all seven.

Reading a chart across all three rows: population to votes is the turnout effect, and votes
to seats is what the electoral system does. Collapsing them into one population-vs-seats gap
mixes the two and cannot be separated by eye.

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
# Gap-compression stops the app exposes, matching _build_turnout_variant's suffixes.
STOPS = [(0, "Turnout"), (5, "TurnoutL5"), (10, "TurnoutL10"), (15, "TurnoutL15"),
         (20, "TurnoutL20"), (25, "TurnoutL25"), (30, "TurnoutL30")]


def _shares(probs: np.ndarray, weights: np.ndarray, idx: np.ndarray) -> np.ndarray:
    """Soft-weighted share of the population in each cluster, as percentages summing to 100.
    Mirrors prepare_data.py's _national_pop_shares_10 so the point estimate matches the
    committed partyPopulation.json rather than being a parallel definition."""
    w = weights[idx]
    return (probs[idx] * w[:, None]).sum(axis=0) / w.sum() * 100.0


def _intervals(probs, weights, state, n_draws):
    point = _shares(probs, weights, np.arange(len(weights)))
    draws = np.vstack([_shares(probs, weights, stratified_indices(state, seed=42 + d))
                       for d in range(n_draws)])
    assert abs(point.sum() - 100.0) < 1e-6, f"point shares sum to {point.sum()}"
    assert np.abs(draws.sum(axis=1) - 100.0).max() < 1e-6, "a draw did not sum to 100"

    out = {}
    for k in range(10):
        col = draws[:, k]
        lo, hi = np.percentile(col, [2.5, 97.5])
        out[CLUSTER_TO_PARTY[k]] = {
            "point": round(float(point[k]), 2),
            "expected": round(float(col.mean()), 2),
            # Widen so the interval always contains its own centre, matching the seat
            # payload's convention; a party pinned near its maximum can otherwise land
            # with a percentile bound on the wrong side of the mean.
            "lo": round(min(float(lo), float(col.mean())), 2),
            "hi": round(max(float(hi), float(col.mean())), 2),
        }
    return out


def build(n_draws: int) -> dict:
    efa = pd.read_csv(BASE / "data" / "processed" / "efa_factor_scores.csv")
    typ = pd.read_csv(BASE / "data" / "processed" / "typology_cluster_assignments.csv")
    turn = pd.read_csv(BASE / "data" / "processed" / "turnout_propensity.csv")
    assert len(efa) == len(typ) == len(turn), "row mismatch across per-respondent files"

    probs = typ[PROB_COLS].values.astype(np.float64)
    base_w = efa["commonpostweight"].values.astype(np.float64)
    state = efa["inputstate"].values.astype(int)
    t = turn["turnout_cluster"].values.astype(np.float64)

    payload = {
        "nDraws": n_draws,
        "seed": 42,
        "population": {"stopInvariant": True, "shares": _intervals(probs, base_w, state, n_draws)},
        "votes": {},
    }
    for pct, suffix in STOPS:
        lam = pct / 100.0
        # Same compression the pipelines apply: each force's turnout moves toward parity.
        w = base_w * (t + lam * (1.0 - t))
        payload["votes"][suffix] = {"shares": _intervals(probs, w, state, n_draws)}
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=1000)
    a = ap.parse_args()

    payload = build(a.draws)
    OUT.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True))

    pop = payload["population"]["shares"]
    vote = payload["votes"]["TurnoutL5"]["shares"]
    print(f"{a.draws} draws -> {OUT.name} ({OUT.stat().st_size} bytes)")
    print(f"population sums {sum(v['point'] for v in pop.values()):.2f}; "
          f"votes at L5 sums {sum(v['point'] for v in vote.values()):.2f}")
    print(f"\n{'party':6s}{'population':>22s}{'votes (L5)':>22s}{'turnout gap':>13s}")
    for p, v in sorted(pop.items(), key=lambda kv: -kv[1]["point"]):
        q = vote[p]
        print(f"  {p:4s}{v['point']:8.2f} [{v['lo']:5.2f},{v['hi']:5.2f}]"
              f"{q['point']:8.2f} [{q['lo']:5.2f},{q['hi']:5.2f}]"
              f"{q['point'] - v['point']:+13.2f}")


if __name__ == "__main__":
    main()

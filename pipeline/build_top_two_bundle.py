#!/usr/bin/env python3
"""
build_top_two_bundle.py
-----------------------
Per-state results for the Instructive Ballot's top-two reduction, for every
depth x turnout stop the presidency tab exposes.

Why this has to be precomputed: a state's presidential payload carries a first-choice share
vector and two single winners. Whether a voter ranked STY above LBR is not recoverable from
that, so the two-way split has to come from the ballots here.

Two routes, because the ballot instruction names "the two national finalists" and the site
offers two ways of finding them:
  condorcet  the Round-Robin winner, plus the winner of the same field with them removed
  irv        the last two standing once the IRV flow is run down to exactly two

For each route and state: the two-way share, and that state's electors allocated proportionally
(the ballot as written) and winner-take-all (clause 2 dropped).

Writes viz/public/data/topTwo.json = {depthKey: {partKey: {route: {...}}}}, lazily loaded the
way generalDepth.json is.

Reuses run_pure_multi_presidential's pairwise, IRV and finalist logic so the pairs and counts
are the same arithmetic the site's own Condorcet and IRV results use.
"""

import json
import os
import sys
from pathlib import Path

# Must precede the pipeline import: that module resolves its tree paths from env at import time.
os.environ["TURNOUT_WEIGHT"] = "1"
os.environ["TURNOUT_LAMBDA"] = "0.05"
os.environ["BALLOT_DEPTH"] = "7"

import numpy as np
import pandas as pd

BASE = Path(__file__).parent.parent
sys.path.insert(0, str(BASE / "pipeline" / "pure_only"))

from run_pure_multi_presidential import (  # noqa: E402
    BALLOTS_PATH, EFA_PATH, build_matchups, extract_finalist_ballots, first_surviving_choice,
    ranked_pairs_winner, run_irv,
)

TURNOUT_CSV = BASE / "data" / "processed" / "turnout_propensity.csv"
OUTPUTS = BASE / "data" / "outputs"
HOUSE_MAP_PATH = BASE / "viz" / "src" / "data" / "houseStateMapTurnoutL5.json"
OUT_PATH = BASE / "viz" / "public" / "data" / "topTwo.json"

SENATORIAL_ELECTORS = 2
PR_FIPS = 72  # no electors
DEPTHS = [3, 5, 7, 10]
STOPS = [0, 5, 10, 15, 20, 25, 30]


def tree_for(depth: int, stop: int) -> Path:
    suffix = "_turnout" + (f"_l{stop}" if stop > 0 else "")
    return OUTPUTS / f"pure_multi{suffix}_top{depth}"


def largest_remainder(shares: dict, seats: int) -> dict:
    """Hamilton, mirroring largestRemainder in viz/src/lib/ecAllocation.ts."""
    total = sum(shares.values())
    if total <= 0 or seats <= 0:
        return {k: 0 for k in shares}
    exact = {k: v / total * seats for k, v in shares.items()}
    out = {k: int(np.floor(v)) for k, v in exact.items()}
    order = sorted(shares, key=lambda k: (-(exact[k] - np.floor(exact[k])), k))
    for k in order[:seats - sum(out.values())]:
        out[k] += 1
    return out


def condorcet_pair(fin_ballots, weights, finalists) -> tuple:
    a, _ = ranked_pairs_winner(build_matchups(fin_ballots, weights, finalists), finalists)
    rest = [c for c in finalists if c != a]
    b, _ = ranked_pairs_winner(build_matchups(fin_ballots, weights, rest), rest)
    return a, b


def irv_pair(fin_ballots, weights, finalists) -> tuple:
    """run_irv stops once someone clears half, so elimination continues here to exactly two."""
    active = set(finalists)
    while len(active) > 2:
        fsc = first_surviving_choice(fin_ballots, active)
        totals = {c: float(weights[fsc == c].sum()) for c in active}
        active.discard(min(active, key=lambda c: (totals[c], c)))
    fsc = first_surviving_choice(fin_ballots, active)
    totals = {c: float(weights[fsc == c].sum()) for c in active}
    return tuple(sorted(active, key=lambda c: (-totals[c], c)))


def route_payload(fin_ballots, weights, state_fips, electors, a, b) -> dict:
    M = fin_ballots.shape[1]
    rank_a = np.full(len(fin_ballots), M + 1)
    rank_b = np.full(len(fin_ballots), M + 1)
    for j in range(M):
        rank_a[fin_ballots[:, j] == a] = j
        rank_b[fin_ballots[:, j] == b] = j
    assert (rank_a <= M).all() and (rank_b <= M).all(), \
        "a ballot ranks neither finalist; the general full-ranks all finalists"

    states = {}
    prop = {a: 0, b: 0}
    wta = {a: 0, b: 0}
    for fips in sorted(set(state_fips)):
        if fips == PR_FIPS or fips not in electors:
            continue
        m = state_fips == fips
        w = weights[m]
        wa = float(w[rank_a[m] < rank_b[m]].sum())
        wb = float(w[rank_b[m] < rank_a[m]].sum())
        if wa + wb <= 0:
            continue
        ev = electors[fips]
        split = largest_remainder({a: wa, b: wb}, ev)
        wta_to = a if wa > wb else b
        prop[a] += split[a]
        prop[b] += split[b]
        wta[wta_to] += ev
        states[f"{fips:02d}"] = {
            "ev": ev,
            "shareA": round(wa / (wa + wb), 5),
            "propA": split[a],
            "propB": split[b],
            "wtaTo": wta_to,
        }

    natl_a = float(weights[rank_a < rank_b].sum())
    natl_b = float(weights[rank_b < rank_a].sum())
    total_ev = sum(e["ev"] for e in states.values())
    majority = total_ev // 2 + 1

    def verdict(t):
        lead = max(t, key=lambda k: t[k])
        return lead if t[lead] >= majority else None

    return {
        "a": a, "b": b,
        "popA": round(natl_a / (natl_a + natl_b) * 100, 3),
        "prop": {a: prop[a], b: prop[b]},
        "wta": {a: wta[a], b: wta[b]},
        "propWinner": verdict(prop),
        "wtaWinner": verdict(wta),
        "totalEv": total_ev,
        "majority": majority,
        "states": states,
    }


def main() -> None:
    ballots_df = pd.read_csv(BALLOTS_PATH, index_col="respondent_id")
    efa = pd.read_csv(EFA_PATH)
    assert len(ballots_df) == len(efa), f"ballot rows {len(ballots_df)} != efa rows {len(efa)}"
    rank_cols = [c for c in ballots_df.columns if c.startswith("rank_")]
    ballots_arr = ballots_df[rank_cols].values
    base_w = efa["commonpostweight"].values.astype(float)
    state_fips = efa["inputstate"].values.astype(int)
    turnout = pd.read_csv(TURNOUT_CSV)["turnout_cluster"].values.astype(float)
    assert len(turnout) == len(efa), f"turnout rows {len(turnout)} != efa rows {len(efa)}"

    house = json.loads(HOUSE_MAP_PATH.read_text())
    # Apportionment is population-based and identical across every turnout stop, so one map
    # serves the whole grid. Verified against houseStateMapTurnout*.json.
    electors = {int(f): e["totalSeats"] + SENATORIAL_ELECTORS for f, e in house.items()}

    bundle = {}
    for depth in DEPTHS:
        by_part = {}
        for stop in STOPS:
            primary_path = tree_for(depth, stop) / "primary_results_2028.csv"
            if not primary_path.exists():
                print(f"  skip top{depth} @ {stop}%: no tree")
                continue
            primary = pd.read_csv(primary_path)
            finalists = sorted(primary[
                (primary["winnowing_point"] == "After_Pod_BD") & (primary["status"] == "surviving")
            ]["candidate_code"].drop_duplicates().tolist())

            weights = base_w * (turnout + stop / 100.0 * (1.0 - turnout))
            fin_ballots = extract_finalist_ballots(ballots_arr, set(finalists), len(finalists))

            ca, cb = condorcet_pair(fin_ballots, weights, finalists)
            ia, ib = irv_pair(fin_ballots, weights, finalists)
            by_part[str(stop)] = {
                "finalists": finalists,
                "condorcet": route_payload(fin_ballots, weights, state_fips, electors, ca, cb),
                "irv": route_payload(fin_ballots, weights, state_fips, electors, ia, ib),
            }
            print(f"  top{depth} @ {stop:>2}%  RR {ca}/{cb}  IRV {ia}/{ib}")
        bundle[f"top{depth}"] = by_part

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(bundle, separators=(",", ":")))
    print(f"\nWrote {OUT_PATH.relative_to(BASE)} ({OUT_PATH.stat().st_size / 1e3:.0f} KB)")


if __name__ == "__main__":
    main()

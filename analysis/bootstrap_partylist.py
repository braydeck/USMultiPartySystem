#!/usr/bin/env python3
"""
bootstrap_partylist.py
----------------------
Sampling range for each party's House seats under party-list PR.

Party list is the benchmark row on the population/votes/seats chart: what a proportional
rule gives on THESE districts. It is not near-proportional, and both it and STV penalise
small parties, because these are small multi-member districts rather than a national list.
So the row isolates the counting rule's contribution, not pure proportionality: votes to list
is the district-magnitude penalty common to both, and list to STV is what transferable voting
adds on top. Current Gallagher figures are printed by pipeline/build_house_partylist.py rather
than quoted here, so they cannot go stale in a comment.

Cheap for the same reason population share is: the allocation is deterministic given vote
shares, with no ballots, no transfers and no elimination. It is also depth-invariant (list
uses first choices only), so there is no ballot-depth axis. It IS turnout-weighted, so it
needs all seven stops.

Reuses `sainte_lague` from pipeline/build_house_partylist.py rather than reimplementing it, so
the bootstrap and the committed housePartyList.json cannot drift apart.

The one subtlety: a district with no assigned respondents falls back to its STATE's vote
vector rather than getting zero seats (the generator cites AZ 04-03). Skipping that loses
5 of 873 seats at the point estimate, and matters more under resampling, because a resample
can empty a district the original sample covered — every party's range would sit low.

Provenance: data/processed/{efa_factor_scores,typology_cluster_assignments,turnout_propensity}.csv
+ data/outputs/No_C7_canonical/{ballots_checkpoint.parquet,district_apportionment.csv}.
Double-Wyoming map only, matching the chart's gate. Seeded 42 + draw, stratified within state.

Usage:  python3 analysis/bootstrap_partylist.py [--draws 1000]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "pipeline"))

from analysis.bootstrap.contests import CLUSTER_TO_PARTY  # noqa: E402
from analysis.bootstrap.resample import stratified_indices  # noqa: E402
from build_house_partylist import sainte_lague  # noqa: E402  reuse, do not reimplement

PROB_COLS = [f"prob_cluster_{k}" for k in range(10)]
OUT = BASE / "viz" / "src" / "data" / "partyListSeatRange.json"
STOPS = [(0, "Turnout"), (5, "TurnoutL5"), (10, "TurnoutL10"), (15, "TurnoutL15"),
         (20, "TurnoutL20"), (25, "TurnoutL25"), (30, "TurnoutL30")]


def load():
    efa = pd.read_csv(BASE / "data" / "processed" / "efa_factor_scores.csv")
    typ = pd.read_csv(BASE / "data" / "processed" / "typology_cluster_assignments.csv")
    turn = pd.read_csv(BASE / "data" / "processed" / "turnout_propensity.csv")
    chk = pd.read_parquet(BASE / "data" / "outputs" / "No_C7_canonical" / "ballots_checkpoint.parquet")
    app = pd.read_csv(BASE / "data" / "outputs" / "No_C7_canonical" / "district_apportionment.csv")
    n = len(efa)
    assert len(typ) == len(turn) == len(chk) == n, "per-respondent files misaligned"

    # District list comes from the APPORTIONMENT, not the checkpoint. They differ: the
    # checkpoint has 149 districts but the apportionment has 150, because AZ 04-03 has no
    # assigned respondents at all and still holds 5 seats. Factorising the checkpoint drops
    # that district entirely, so the fallback below never fires and 5 of 873 seats vanish.
    uniq = list(app["district_id"])
    dist_ix = {d: i for i, d in enumerate(uniq)}
    codes = np.array([dist_ix[d] for d in chk["district_id"].values], dtype=int)
    seat_of = dict(zip(app["district_id"], app["seat_count"]))
    state_of = dict(zip(app["district_id"], app["state_fips"]))
    seats = np.array([seat_of[d] for d in uniq], dtype=int)
    # District -> index into the state list, for the empty-district fallback.
    states = sorted({int(v) for v in state_of.values()})
    state_ix = {s: i for i, s in enumerate(states)}
    dist_state = np.array([state_ix[int(state_of[d])] for d in uniq], dtype=int)

    # First-choice one-hot, matching build_house_partylist.py's allocation basis. The vote basis
    # is the one thing this script duplicates rather than imports (it imports `sainte_lague` to avoid
    # exactly that), so it has to be changed in lockstep with the builder or the intervals detach
    # from the point estimate they are drawn around.
    probs = typ[PROB_COLS].values.astype(np.float64)
    first_choice = np.zeros_like(probs)
    first_choice[np.arange(n), probs.argmax(axis=1)] = 1.0

    return dict(
        probs=first_choice,
        base_w=efa["commonpostweight"].values.astype(np.float64),
        turnout=turn["turnout_cluster"].values.astype(np.float64),
        inputstate=efa["inputstate"].values.astype(int),
        codes=codes, seats=seats, dist_state=dist_state,
        n_dist=len(uniq), n_state=len(states), state_ix=state_ix,
    )


def allocate(d, idx, lam):
    """Party-list seats per party for one resample at one turnout stop."""
    w = d["base_w"][idx] * (d["turnout"][idx] + lam * (1.0 - d["turnout"][idx]))
    P, c = d["probs"][idx], d["codes"][idx]

    votes = np.empty((d["n_dist"], 10))
    st_votes = np.empty((d["n_state"], 10))
    st_of_resp = np.array([d["state_ix"][s] for s in d["inputstate"][idx]])
    for k in range(10):
        wk = P[:, k] * w
        votes[:, k] = np.bincount(c, weights=wk, minlength=d["n_dist"])
        st_votes[:, k] = np.bincount(st_of_resp, weights=wk, minlength=d["n_state"])

    out = np.zeros(10, dtype=int)
    for i in range(d["n_dist"]):
        s = int(d["seats"][i])
        if s <= 0:
            continue
        # No respondents landed here in this draw: use the state's vote vector so the
        # district's seats are still allocated rather than silently dropped.
        v = votes[i] if votes[i].sum() > 0 else st_votes[d["dist_state"][i]]
        out += sainte_lague(v, s)
    return out


def build(n_draws: int) -> dict:
    d = load()
    base = np.arange(len(d["base_w"]))
    payload = {"nDraws": n_draws, "seed": 42, "stops": {}}

    for pct, suffix in STOPS:
        lam = pct / 100.0
        point = allocate(d, base, lam)
        draws = np.vstack([allocate(d, stratified_indices(d["inputstate"], seed=42 + i), lam)
                           for i in range(n_draws)])
        total = int(d["seats"].sum())
        assert total == 873, f"apportionment totals {total}, expected 873"
        assert point.sum() == total, f"{suffix}: point allocates {point.sum()} of {total}"
        assert (draws.sum(axis=1) == total).all(), f"{suffix}: a draw did not allocate {total}"

        shares = {}
        for k in range(10):
            col = draws[:, k].astype(float)
            lo, hi = np.percentile(col, [2.5, 97.5])
            exp = float(col.mean())
            shares[CLUSTER_TO_PARTY[k]] = {
                "point": int(point[k]),
                "expected": round(exp, 2),
                # Contain the centre, matching the seat payload's convention.
                "lo": int(min(np.floor(lo), np.floor(exp))),
                "hi": int(max(np.ceil(hi), np.ceil(exp))),
            }
        payload["stops"][suffix] = {"totalSeats": total, "shares": shares}
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=1000)
    a = ap.parse_args()

    payload = build(a.draws)
    OUT.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True))

    l5 = payload["stops"]["TurnoutL5"]
    print(f"{a.draws} draws -> {OUT.name} ({OUT.stat().st_size} bytes), {l5['totalSeats']} seats")
    print(f"\n{'party':6s}{'point':>7s}{'expected':>10s}{'95% range':>12s}")
    for p, v in sorted(l5["shares"].items(), key=lambda kv: -kv[1]["point"]):
        print(f"  {p:4s}{v['point']:7d}{v['expected']:10.1f}{f'{v[chr(108)+chr(111)]}-{v[chr(104)+chr(105)]}':>12s}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
instructive_ballot_wta_vs_prop.py
---------------------------------
Does the Instructive Ballot need its proportionality clause?

The ballot as proposed instructs two things:
  1. count my ballot for whichever of the two national Round-Robin finalists I ranked higher;
  2. apportion my state's electors in proportion to those counted ballots.

This asks what happens if only clause 1 binds and states keep winner-take-all. The reduction to
a two-way national race is the same either way; only the within-state allocation differs.

Provenance
  ballots  data/outputs/pure_multi/presidential_ballots.csv   (party-line pipeline, full ranking)
  weights  data/processed/efa_factor_scores.csv commonpostweight x turnout multiplier
  turnout  TURNOUT_WEIGHT=1, TURNOUT_LAMBDA=0.05  -> the app's default 5% gap-closure stop
  depth    BALLOT_DEPTH=7                          -> the app's default rank-7 finalists
  electors viz/src/data/houseStateMapTurnoutL5.json totalSeats + 2 senatorial = 975
  Matches the presidency tab's defaults, so the two-way race starts from the field the site shows.

No randomness: every number here is a weighted count over fixed ballots.

Reuses the pipeline's own pairwise and ranked-pairs code rather than reimplementing it, so the
finalists and the A-over-B counts are the same arithmetic the site's Condorcet result uses.
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
SENATORIAL_ELECTORS = 2
PR_FIPS = 72  # no electors; the pipeline excludes it from the state loop

# The grid the presidency tab actually exposes: rank-N ballot depth x turnout gap-closure stop.
DEPTHS = [3, 5, 7, 10]
STOPS = [0, 5, 10, 15, 20, 25, 30]
DEFAULT = (7, 5)


def tree_for(depth: int, stop: int) -> Path:
    """Mirror turnout_weights.output_tree + the _topN depth suffix."""
    suffix = "_turnout" + (f"_l{stop}" if stop > 0 else "")
    return OUTPUTS / f"pure_multi{suffix}_top{depth}"


def weights_for(stop: int, base: np.ndarray) -> np.ndarray:
    """commonpostweight x the cluster turnout rate compressed toward parity by lambda.

    Recomputed here rather than via turnout_weights.turnout_multiplier because that module
    reads TURNOUT_LAMBDA once at import, which cannot sweep.
    """
    t = pd.read_csv(TURNOUT_CSV)["turnout_cluster"].values.astype(float)
    assert len(t) == len(base), f"turnout rows {len(t)} != data rows {len(base)}"
    lam = stop / 100.0
    return base * (t + lam * (1.0 - t))


def largest_remainder(shares: dict, seats: int) -> dict:
    """Hamilton, mirroring largestRemainder in viz/src/lib/ecAllocation.ts.

    Ties on the fractional part break on candidate code so a rerun cannot reorder the result.
    """
    total = sum(shares.values())
    if total <= 0 or seats <= 0:
        return {k: 0 for k in shares}
    exact = {k: v / total * seats for k, v in shares.items()}
    out = {k: int(np.floor(v)) for k, v in exact.items()}
    remaining = seats - sum(out.values())
    order = sorted(shares, key=lambda k: (-(exact[k] - np.floor(exact[k])), k))
    for k in order[:remaining]:
        out[k] += 1
    return out


def condorcet_pair(fin_ballots, weights, finalists) -> tuple:
    """The pair a national Round-Robin narrows to.

    A = the Condorcet winner. B = the winner of the same field with A removed, i.e. the
    candidate the country prefers to every remaining rival.
    """
    a, _ = ranked_pairs_winner(build_matchups(fin_ballots, weights, finalists), finalists)
    rest = [c for c in finalists if c != a]
    b, _ = ranked_pairs_winner(build_matchups(fin_ballots, weights, rest), rest)
    return a, b


def irv_pair(fin_ballots, weights, finalists) -> tuple:
    """The last two standing in the IRV flow.

    run_irv stops as soon as someone clears half, which usually leaves three or more active,
    so elimination continues here to exactly two. The pair is returned in IRV-leader order.
    """
    active = set(finalists)
    while len(active) > 2:
        fsc = first_surviving_choice(fin_ballots, active)
        totals = {c: float(weights[fsc == c].sum()) for c in active}
        active.discard(min(active, key=lambda c: (totals[c], c)))
    fsc = first_surviving_choice(fin_ballots, active)
    totals = {c: float(weights[fsc == c].sum()) for c in active}
    return tuple(sorted(active, key=lambda c: (-totals[c], c)))


def allocate(fin_ballots, weights, state_fips, electors, a, b):
    """Two-way race between a and b, allocated both ways. Returns (prop, wta, per-state rows)."""
    M = fin_ballots.shape[1]
    rank_a = np.full(len(fin_ballots), M + 1)
    rank_b = np.full(len(fin_ballots), M + 1)
    for j in range(M):
        rank_a[fin_ballots[:, j] == a] = j
        rank_b[fin_ballots[:, j] == b] = j
    assert (rank_a <= M).all() and (rank_b <= M).all(), \
        "a ballot ranks neither finalist; the general full-ranks all finalists"

    wta = {a: 0, b: 0}
    prop = {a: 0, b: 0}
    rows = []
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
        wta[a if wa > wb else b] += ev
        split = largest_remainder({a: wa, b: wb}, ev)
        prop[a] += split[a]
        prop[b] += split[b]
        rows.append({"fips": fips, "ev": ev, "share_a": wa / (wa + wb),
                     "wta_a": ev if wa > wb else 0, "prop_a": split[a]})
    natl_a = float(weights[rank_a < rank_b].sum())
    natl_b = float(weights[rank_b < rank_a].sum())
    return prop, wta, pd.DataFrame(rows), natl_a / (natl_a + natl_b) * 100


def run_one(depth: int, stop: int, ballots_arr, base_w, state_fips, electors, verbose=False):
    """One (depth, turnout-stop) cell: both allocation rules on the same two-way race."""
    tree = tree_for(depth, stop)
    primary_path = tree / "primary_results_2028.csv"
    if not primary_path.exists():
        return None

    # Same selection run_pure_multi_presidential.main() uses, so the field matches the site's.
    primary = pd.read_csv(primary_path)
    finalists = sorted(primary[
        (primary["winnowing_point"] == "After_Pod_BD") & (primary["status"] == "surviving")
    ]["candidate_code"].drop_duplicates().tolist())
    if len(finalists) < 2:
        return None

    weights = weights_for(stop, base_w)
    fin_ballots = extract_finalist_ballots(ballots_arr, set(finalists), len(finalists))

    total_ev = sum(electors.values())
    majority = total_ev // 2 + 1

    def verdict(tally):
        lead = max(tally, key=lambda k: tally[k])
        return lead if tally[lead] >= majority else "HOUSE"

    # The Condorcet route the ballot names, and the IRV route as its analogue: run the flow
    # down to two, then let each voter's ballot count for whichever of those two they prefer.
    a, b = condorcet_pair(fin_ballots, weights, finalists)
    ia, ib = irv_pair(fin_ballots, weights, finalists)
    prop, wta, df, pop_a = allocate(fin_ballots, weights, state_fips, electors, a, b)
    iprop, iwta, idf, ipop_a = allocate(fin_ballots, weights, state_fips, electors, ia, ib)

    # The national single-winner result the IRV two-way race is supposed to reproduce: the
    # leader of run_irv's final round, which is where it stops once someone clears half.
    final_totals = run_irv(fin_ballots, weights, finalists)[-1]["totals"]
    nat_irv = max(final_totals, key=lambda k: final_totals[k])

    res = {
        "depth": depth, "stop": stop, "finalists": finalists,
        "a": a, "b": b, "pop_a": pop_a,
        "prop_a": prop[a], "prop_b": prop[b], "wta_a": wta[a], "wta_b": wta[b],
        "prop_winner": verdict(prop), "wta_winner": verdict(wta),
        "cond_winner": a,
        "ia": ia, "ib": ib, "ipop_a": ipop_a,
        "iprop_a": iprop[ia], "iprop_b": iprop[ib], "iwta_a": iwta[ia], "iwta_b": iwta[ib],
        "iprop_winner": verdict(iprop), "iwta_winner": verdict(iwta),
        "irv_winner": nat_irv,
        "majority": majority, "total_ev": total_ev, "df": df,
    }
    res["shifts"] = res["prop_winner"] != res["wta_winner"]
    res["same_pair"] = {a, b} == {ia, ib}
    res["prop_matches_cond"] = res["prop_winner"] == a
    res["iprop_matches_irv"] = res["iprop_winner"] == nat_irv
    return res


def main() -> None:
    ballots_df = pd.read_csv(BALLOTS_PATH, index_col="respondent_id")
    efa = pd.read_csv(EFA_PATH)
    assert len(ballots_df) == len(efa), f"ballot rows {len(ballots_df)} != efa rows {len(efa)}"
    rank_cols = [c for c in ballots_df.columns if c.startswith("rank_")]
    ballots_arr = ballots_df[rank_cols].values
    base_w = efa["commonpostweight"].values.astype(float)
    state_fips = efa["inputstate"].values.astype(int)

    house = json.loads(HOUSE_MAP_PATH.read_text())
    electors = {int(f): e["totalSeats"] + SENATORIAL_ELECTORS for f, e in house.items()}
    abbr = {int(f): e["stateAbbr"] for f, e in house.items()}

    print(f"{len(ballots_df):,} ballots · {sum(electors.values())} electors · "
          f"{sum(electors.values()) // 2 + 1} to win\n")

    # ── The default cell, in detail ───────────────────────────────────────────────
    d, s = DEFAULT
    r = run_one(d, s, ballots_arr, base_w, state_fips, electors)
    print(f"DEFAULT  rank-{d} ballots, {s}% gap closed")
    print(f"  Round-Robin finalists: {r['a']} (winner) vs {r['b']} (runner-up)")
    print(f"  Two-way popular vote:  {r['a']} {r['pop_a']:.2f}%   {r['b']} {100 - r['pop_a']:.2f}%")
    print(f"  Proportional (as proposed):  {r['a']} {r['prop_a']:4d}  {r['b']} {r['prop_b']:4d}"
          f"   -> {r['prop_winner']}")
    print(f"  Winner-take-all (clause 2 dropped): {r['a']} {r['wta_a']:4d}  {r['b']} {r['wta_b']:4d}"
          f"   -> {r['wta_winner']}")
    print(f"  Elector swing for {r['a']}: {r['prop_a'] - r['wta_a']:+d}\n")

    df = r["df"]
    df["delta_a"] = df["prop_a"] - df["wta_a"]
    worst = df.reindex(df["delta_a"].abs().sort_values(ascending=False).index).head(8)
    print(f"  Largest per-state differences (proportional minus WTA, for {r['a']}):")
    for _, x in worst.iterrows():
        print(f"    {abbr[int(x['fips'])]:3s} {int(x['ev']):3d} EV  {r['a']} {x['share_a'] * 100:5.1f}%"
              f"  WTA {int(x['wta_a']):3d} -> prop {int(x['prop_a']):3d}  ({int(x['delta_a']):+d})")
    close = df[(df["share_a"] > 0.45) & (df["share_a"] < 0.55)]
    print(f"  States inside 45-55%: {len(close)} holding {int(close['ev'].sum())} electors "
          f"({close['ev'].sum() / r['total_ev'] * 100:.1f}% of the college)\n")

    # ── The whole grid: does the answer hold anywhere the reader can steer? ───────
    print(f"{'depth':>6} {'stop':>5} | {'RR pair':>13} {'pop%':>6} {'prop':>9} {'wta':>9} "
          f"{'→':>6} | {'IRV pair':>13} {'pop%':>6} {'prop':>9} {'→':>6} | same pair")
    cells = []
    for depth in DEPTHS:
        for stop in STOPS:
            rr = run_one(depth, stop, ballots_arr, base_w, state_fips, electors)
            if rr is None:
                print(f"{depth:>6} {stop:>5}   (no tree)")
                continue
            cells.append(rr)
            print(f"{depth:>6} {stop:>5} | {rr['a'] + '/' + rr['b']:>13} {rr['pop_a']:>6.2f} "
                  f"{str(rr['prop_a']) + '-' + str(rr['prop_b']):>9} "
                  f"{str(rr['wta_a']) + '-' + str(rr['wta_b']):>9} {rr['prop_winner']:>6} | "
                  f"{rr['ia'] + '/' + rr['ib']:>13} {rr['ipop_a']:>6.2f} "
                  f"{str(rr['iprop_a']) + '-' + str(rr['iprop_b']):>9} {rr['iprop_winner']:>6} | "
                  f"{'yes' if rr['same_pair'] else 'NO'}"
                  f"{'   SHIFT' if rr['shifts'] else ''}")

    n = len(cells)
    shifts = [c for c in cells if c["shifts"]]
    print(f"\nProportional two-way reproduces the national CONDORCET winner: "
          f"{sum(c['prop_matches_cond'] for c in cells)}/{n} cells")
    print(f"Proportional two-way reproduces the national IRV winner:       "
          f"{sum(c['iprop_matches_irv'] for c in cells)}/{n} cells")
    print(f"Condorcet pair == IRV pair:                                    "
          f"{sum(c['same_pair'] for c in cells)}/{n} cells")
    pairs = {}
    for c in cells:
        pairs[f"{c['a']}/{c['b']}"] = pairs.get(f"{c['a']}/{c['b']}", 0) + 1
    print("Round-Robin pairs seen across the grid: "
          + ", ".join(f"{k} x{v}" for k, v in sorted(pairs.items(), key=lambda x: -x[1])))

    print(f"\nCells where dropping proportionality changes the outcome: {len(shifts)}")
    for rr in shifts:
        print(f"  rank-{rr['depth']} @ {rr['stop']}%: {rr['prop_winner']} -> {rr['wta_winner']}"
              f"  (popular {rr['a']} {rr['pop_a']:.2f}%)")

    # ── How close would the race have to be? ──────────────────────────────────────
    # Nothing shifting across the grid is not the same as the rules being equivalent: the
    # two-way margin is never near 50%, and winner-take-all can only invert a popular-vote
    # winner in a close race. Apply a uniform national swing to the default cell and find where
    # each rule's winner flips. The gap between the two flip points is the band in which the
    # proportionality clause is load-bearing.
    print("\nUniform-swing test on the default cell "
          f"(rank-{DEFAULT[0]}, {DEFAULT[1]}% stop, {r['a']} vs {r['b']}):")
    df = r["df"]
    ev = df["ev"].values
    share = df["share_a"].values
    total_ev, majority = r["total_ev"], r["majority"]

    def winners_at(delta):
        s = np.clip(share + delta, 0.0, 1.0)
        wta_a = int(ev[s > 0.5].sum())
        prop_a = sum(largest_remainder({"a": si, "b": 1 - si}, int(e))["a"]
                     for si, e in zip(s, ev))
        return (r["a"] if wta_a >= majority else r["b"],
                r["a"] if prop_a >= majority else r["b"], wta_a, prop_a)

    flip = {}
    prev = winners_at(-0.20)
    for delta in np.arange(-0.20, 0.2001, 0.0025):
        cur = winners_at(delta)
        for i, rule in ((0, "winner-take-all"), (1, "proportional")):
            if cur[i] != prev[i] and rule not in flip:
                flip[rule] = delta
        prev = cur
    for rule in ("proportional", "winner-take-all"):
        if rule in flip:
            print(f"  {rule:16s} flips at a uniform swing of {flip[rule] * 100:+.2f} pts "
                  f"(popular vote {r['pop_a'] + flip[rule] * 100:.2f}%)")
        else:
            print(f"  {rule:16s} never flips within +/-20 pts")
    if len(flip) == 2:
        lo, hi = sorted(flip.values())
        print(f"  The two rules disagree only in a {abs(hi - lo) * 100:.2f}-point band of "
              f"national vote share.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Per-draw House seats at the app default, so coalition majority odds can use the joint distribution.

houseSeatRanges.json and uncertainty*.json keep only per-party intervals; a coalition's chance of a
majority needs each draw's seats together. This reruns the House alone (analysis/bootstrap/contests
.run_house_draw) on the same cached re-clustering fits (data/bootstrap_cache/), at the default view:
double map, depth 7, 5% turnout gap. Draw seeds 42 + d, as bootstrap_house.py uses.
Job 0 is the observed anchor (published parties, full sample); it must equal
the published default-view anchor (viz/src/data/uncertaintyTurnoutL5.json house.seats observed)
or the run stops. (houseSeatsTurnoutL5.json is the full-ranking count, not depth 7.)
Writes analysis/coalitions/outputs/house_draw_seats_l5.csv: draw (-1 = observed), one column per party.
"""
import argparse
import json
import multiprocessing as mp
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
OUT = Path(__file__).parent / "outputs/house_draw_seats_l5.csv"
LAM = 0.05
CONFIG = [("double", "top7")]


def _work(args):
    seed, observed = args
    if str(BASE) not in sys.path:
        sys.path.insert(0, str(BASE))
    from analysis.bootstrap.contests import run_house_draw
    try:
        return run_house_draw(seed=seed, lam=LAM, configs=CONFIG, observed=observed)["house"]["double/top7"]
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=1000)
    ap.add_argument("--procs", type=int, default=max(1, (mp.cpu_count() or 2) - 2))
    a = ap.parse_args()
    import pandas as pd
    jobs = [(0, True)] + [(42 + d, False) for d in range(a.draws)]
    with mp.Pool(a.procs) as pool:
        res = pool.map(_work, jobs, chunksize=1)
    bad = [r for r in res if "error" in r]
    if bad:
        raise RuntimeError(f"{len(bad)} runs failed, first: {bad[0]}")
    unc = json.loads((BASE / "viz/src/data/uncertaintyTurnoutL5.json").read_text())
    pub = {p: v["observed"] for p, v in unc["house"]["seats"].items()}
    if {k: v for k, v in res[0].items() if v} != {k: v for k, v in pub.items() if v}:
        raise RuntimeError(f"observed anchor {res[0]} != published {pub}")
    df = pd.DataFrame(res).fillna(0).astype(int)
    df.insert(0, "draw", [-1] + list(range(a.draws)))
    assert (df.drop(columns="draw").sum(axis=1) == 873).all()
    df.to_csv(OUT, index=False)
    print(f"wrote {OUT} ({a.draws} draws)")


if __name__ == "__main__":
    main()

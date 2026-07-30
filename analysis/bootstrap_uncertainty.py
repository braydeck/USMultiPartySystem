#!/usr/bin/env python3
"""Bootstrap sampling uncertainty for every contest at every turnout stop.

Writes viz/src/data/uncertainty{Suffix}.json. Nothing canonical is written; every
pipeline run goes to a temp dir.

  python3 analysis/bootstrap_uncertainty.py                 # all 7 stops, 1000 draws
  python3 analysis/bootstrap_uncertainty.py --draws 50 --stops 5   # quick check

One Pool per stop: a worker may only ever see one lambda, because turnout_weights
reads it at import time.
"""

import argparse
import json
import multiprocessing as mp
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "viz" / "src" / "data"
STOPS = [(0, "Turnout"), (5, "TurnoutL5"), (10, "TurnoutL10"), (15, "TurnoutL15"),
         (20, "TurnoutL20"), (25, "TurnoutL25"), (30, "TurnoutL30")]


def _work(args):
    seed, lam, depth, observed = args
    import sys
    sys.path.insert(0, str(BASE))
    from analysis.bootstrap.contests import run_draw
    try:
        return run_draw(seed=seed, lam=lam, depth=depth, observed=observed)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "seed": seed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=1000)
    ap.add_argument("--depth", type=int, default=7)
    ap.add_argument("--procs", type=int, default=max(1, (mp.cpu_count() or 2) - 2))
    ap.add_argument("--stops", default="", help="comma-separated stop percentages, e.g. 0,5")
    a = ap.parse_args()

    import sys
    sys.path.insert(0, str(BASE))
    from analysis.bootstrap.aggregate import build_uncertainty

    want = {int(s) for s in a.stops.split(",") if s.strip()} if a.stops else None
    stops = [(p, s) for p, s in STOPS if want is None or p in want]

    for pct, suffix in stops:
        lam = pct / 100.0
        t0 = time.time()
        # The observed anchor runs inside the pool too, not here: contests.py pins one lambda
        # per process at import time, so importing the pipelines into this parent would make
        # every stop after the first raise. Job 0 is the anchor, the rest are the draws.
        jobs = ([(0, lam, a.depth, True)]
                + [(42 + d, lam, a.depth, False) for d in range(a.draws)])
        with mp.Pool(a.procs) as pool:
            results = pool.map(_work, jobs)
        failed = [r for r in results if "error" in r]
        assert not failed, (f"{len(failed)} of {len(jobs)} runs failed, first "
                            f"(seed {failed[0]['seed']}): {failed[0]['error']}")
        observed, draws = results[0], results[1:]
        u = build_uncertainty(draws, observed, n_draws=len(draws), seed=42)
        path = OUT / f"uncertainty{suffix}.json"
        path.write_text(json.dumps(u, separators=(",", ":"), sort_keys=True))
        irv = u["senate"]["irv"]
        print(f"{suffix:12s} {len(draws)} draws  {time.time()-t0:5.0f}s  "
              f"substituted={irv['nSubstituted']} below50={irv['nBelow50']}  "
              f"-> {path.name} ({path.stat().st_size/1024:.0f}KB)")


if __name__ == "__main__":
    main()

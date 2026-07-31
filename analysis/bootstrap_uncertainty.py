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
    if str(BASE) not in sys.path:      # a worker runs ~26 jobs; don't grow sys.path per draw
        sys.path.insert(0, str(BASE))
    from analysis.bootstrap.contests import run_draw
    try:
        return run_draw(seed=seed, lam=lam, depth=depth, observed=observed)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "seed": seed}


def _validate(u, suffix):
    """Re-check the sum invariants on the real payload before it is published.

    The 12-draw selftest asserts these, but a full run can break them in ways a smoke run
    cannot: one draw missing a senate fips leaves `expected` summing to 101.9x. Failing here
    aborts the bad stop instead of shipping it and finding out from the viz's tests.
    """
    def fail(what):
        raise RuntimeError(f"uncertainty{suffix}.json invariant violated: {what}")

    for chamber, methods, total in (("senate", ("cond", "irv"), 102), ("house", (None,), 873)):
        for method in methods:
            block = u[chamber][method] if method else u[chamber]
            label = f"{chamber}/{method}" if method else chamber
            seats = block["seats"]
            modal = sum(v["modal"] for v in seats.values())
            if modal != total:
                fail(f"{label} modal sums to {modal}, not {total}")
            exp = sum(v["expected"] for v in seats.values())
            if abs(exp - total) >= 1e-6:
                fail(f"{label} expected sums to {exp}, not {total}")

    for method in ("cond", "irv"):
        for fips, s in u["senate"][method]["states"].items():
            got = sum(s["dist"].values())
            if abs(got - 1.0) >= 1e-6:
                fail(f"senate/{method} fips {fips} dist sums to {got}, not 1.0")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=1000)
    ap.add_argument("--depth", type=int, default=7)
    # Default leaves two cores free so the machine stays usable across a multi-hour run.
    # Measured on an M4 Pro (8P+4E): 0.66 draws/s at 10 procs, 0.75 at 12 — pass --procs 12 to
    # trade responsiveness for ~14%.
    ap.add_argument("--procs", type=int, default=max(1, (mp.cpu_count() or 2) - 2))
    ap.add_argument("--stops", default="", help="comma-separated stop percentages, e.g. 0,5")
    ap.add_argument("--force", action="store_true",
                    help="overwrite payloads that already hold more draws than this run")
    a = ap.parse_args()

    import sys
    if str(BASE) not in sys.path:
        sys.path.insert(0, str(BASE))
    from analysis.bootstrap.aggregate import build_uncertainty

    want = {int(s) for s in a.stops.split(",") if s.strip()} if a.stops else None
    stops = [(p, s) for p, s in STOPS if want is None or p in want]

    # Check every stop before spending an hour on the first: a small smoke run must not
    # silently replace a full-size payload with a handful of draws.
    if not a.force:
        for _, suffix in stops:
            path = OUT / f"uncertainty{suffix}.json"
            if not path.exists():
                continue
            try:
                prev = int(json.loads(path.read_text()).get("nDraws", 0))
            except (ValueError, OSError):
                prev = 0
            if prev > a.draws:
                raise RuntimeError(f"{path.name} already holds {prev} draws; refusing to "
                                   f"overwrite it with {a.draws} (pass --force to override)")

    for pct, suffix in stops:
        lam = pct / 100.0
        t0 = time.time()
        # The observed anchor runs inside the pool too, not here: contests.py pins one lambda
        # per process at import time, so importing the pipelines into this parent would make
        # every stop after the first raise. Job 0 is the anchor, the rest are the draws.
        jobs = ([(0, lam, a.depth, True)]
                + [(42 + d, lam, a.depth, False) for d in range(a.draws)])
        with mp.Pool(a.procs) as pool:
            # chunksize=1, not pool.map's default. For 1,001 jobs over 12 workers the default is
            # 21, so the last worker can still be 21 draws (~5 min) behind when the others are
            # idle — about 34 min across the seven stops. Draws cost seconds, so per-job dispatch
            # overhead is noise against the balance it buys. Still map, not imap_unordered:
            # results[0] must stay the observed anchor.
            results = pool.map(_work, jobs, chunksize=1)
        failed = [r for r in results if "error" in r]
        if failed:
            # An assert would vanish under -O, and an error dict then reaches the aggregator
            # as a KeyError instead of naming the failing seed.
            raise RuntimeError(f"{len(failed)} of {len(jobs)} runs failed, first "
                               f"(seed {failed[0]['seed']}): {failed[0]['error']}")
        observed, draws = results[0], results[1:]
        u = build_uncertainty(draws, observed, n_draws=len(draws), seed=42)
        _validate(u, suffix)
        path = OUT / f"uncertainty{suffix}.json"
        # No sort_keys: every state's `dist` and the president's are built in descending
        # probability order, and the viz reads them positionally (modal first, then
        # runners-up). Dicts are built deterministically, so output stays reproducible.
        path.write_text(json.dumps(u, separators=(",", ":")))
        irv = u["senate"]["irv"]
        print(f"{suffix:12s} {len(draws)} draws  {time.time()-t0:5.0f}s  "
              f"substituted={irv['nSubstituted']} below50={irv['nBelow50']}  "
              f"-> {path.name} ({path.stat().st_size/1024:.0f}KB)")


if __name__ == "__main__":
    main()

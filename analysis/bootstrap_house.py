#!/usr/bin/env python3
"""House STV seat ranges for every map and ballot depth the House tab offers.

bootstrap_uncertainty.py covers the House only at its default (double map, no reserve, rank-7),
because it runs every contest per draw. This runs the House alone, on the same 1,000 cached
re-clustering fits (analysis/bootstrap/recluster.py), so each draw's parties and turnout are the
ones the main bootstrap used. Per draw and turnout stop it counts STV on four maps (double,
triple, and each with the ~20% statewide reserve top-off) at five depths (3, 5, 7, 10, full),
skipping double/top7, which the uncertainty payloads already hold.

Job 0 per stop is the observed anchor: the published parties on the full sample. It must
reproduce the committed house trees and houseReserveNational.json, and the run aborts if a
chamber total is off.

Output: viz/public/data/houseSeatRanges.json (lazy-loaded)
  {nDraws, seed, stops: {Turnout..TurnoutL30: {"<map>/<depth>": {party: SeatInterval}}}}

  python3 analysis/bootstrap_house.py                  # 1000 draws, all 7 stops (~5 h, 11 procs)
  python3 analysis/bootstrap_house.py --draws 20 --stops 5

One Pool per stop: turnout_weights reads the turnout gap at import, one per process.
Provenance: data/processed/{efa_factor_scores,typology_cluster_assignments,turnout_propensity,
voter_county_fips}.csv, data/outputs/canonical*/district_apportionment.csv; seeds 42 + draw.
"""

import argparse
import json
import multiprocessing as mp
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "viz" / "public" / "data" / "houseSeatRanges.json"
STOPS = [(0, "Turnout"), (5, "TurnoutL5"), (10, "TurnoutL10"), (15, "TurnoutL15"),
         (20, "TurnoutL20"), (25, "TurnoutL25"), (30, "TurnoutL30")]
CHAMBER = {"double": 873, "reserve": 873, "triple": 1726, "triple_reserve": 1726}


def _configs():
    import sys
    if str(BASE) not in sys.path:
        sys.path.insert(0, str(BASE))
    from analysis.bootstrap.contests import HOUSE_DEPTHS, HOUSE_MAPS
    return [(m, d) for m in HOUSE_MAPS for d in HOUSE_DEPTHS if (m, d) != ("double", "top7")]


def _work(args):
    seed, lam, observed = args
    import sys
    if str(BASE) not in sys.path:
        sys.path.insert(0, str(BASE))
    from analysis.bootstrap.contests import run_house_draw
    try:
        return run_house_draw(seed=seed, lam=lam, configs=_configs(), observed=observed)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "seed": seed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=1000)
    ap.add_argument("--procs", type=int, default=max(1, (mp.cpu_count() or 2) - 1))
    ap.add_argument("--stops", default="", help="comma-separated stop percentages, e.g. 0,5")
    a = ap.parse_args()

    import sys
    if str(BASE) not in sys.path:
        sys.path.insert(0, str(BASE))
    from analysis.bootstrap import recluster as rc
    from analysis.bootstrap.aggregate import house_seats

    rc.fit_all(a.draws, a.procs)  # a no-op when the cache already holds every fit
    want = {int(s) for s in a.stops.split(",") if s.strip()} if a.stops else None
    stops = [(p, s) for p, s in STOPS if want is None or p in want]
    configs = _configs()

    payload = json.loads(OUT.read_text()) if OUT.exists() else {}
    if payload.get("nDraws") != a.draws:
        payload = {"nDraws": a.draws, "seed": 42, "stops": {}}

    for pct, suffix in stops:
        lam = pct / 100.0
        t0 = time.time()
        jobs = [(0, lam, True)] + [(42 + d, lam, False) for d in range(a.draws)]
        with mp.Pool(a.procs) as pool:
            results = pool.map(_work, jobs, chunksize=1)  # map keeps results[0] the anchor
        failed = [r for r in results if "error" in r]
        if failed:
            raise RuntimeError(f"{len(failed)} of {len(jobs)} runs failed, first: {failed[0]}")
        observed, draws = results[0]["house"], [r["house"] for r in results[1:]]
        block = {}
        for m, d in configs:
            key = f"{m}/{d}"
            for r in [observed] + draws:
                got = sum(r[key].values())
                if got != CHAMBER[m]:
                    raise RuntimeError(f"{suffix} {key}: a run seated {got}, not {CHAMBER[m]}")
            block[key] = house_seats([r[key] for r in draws], observed[key])
        payload["stops"][suffix] = block
        OUT.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True))
        print(f"{suffix}: {a.draws} draws x {len(configs)} configs in {time.time() - t0:.0f}s", flush=True)

    print(f"wrote {OUT.relative_to(BASE)} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()

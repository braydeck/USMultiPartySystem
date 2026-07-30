#!/usr/bin/env python3
"""Adopt the deterministic district map and rebuild everything downstream of it.

WHY THIS EXISTS
---------------
draw_geographic_districts.py used to draw a different map on every run: its
seed-and-grow tie-breaks resolved through set iteration order, which varies with
PYTHONHASHSEED. That is fixed — the map is now byte-identical across runs — but
data/processed/county_to_district.csv predates the fix, so the committed map cannot
be reproduced by the current code. The two disagree on 65 of 3,142 counties.

Nothing is wrong today: every published figure was computed from the committed map and
the site is self-consistent. The cost of leaving it is that the map in the repo is not
reproducible; the cost of fixing it is this whole script.

WHAT ADOPTING IT COSTS  (measured 2026-07-30, full depth / double Wyoming)
--------------------------------------------------------------------------
  Conservative 201 -> 202   Labor 159 -> 158   Populist 106 -> 104   Nationalist 41 -> 43
  Six parties unchanged, chamber still 873, three seats reassigned.
All 65 counties stay inside their own state and their own density tier, and
apportionment is by state population, so no state's seat count changes — only which
same-tier district within a state a county sits in.

WHY IT IS ALL OR NOTHING
------------------------
The per-voter district assignment is baked into ballots_checkpoint.parquet, which every
House run reads. uncertainty*.json carries the modal seat counts the headline chamber
uses, so stopping after stage 3 would leave the modal chamber describing the old map
while the observed chamber describes the new one. Run every stage or none.

Stages 1-3 are verified: each script is deterministic and reproduces its committed
output byte for byte from the committed map. Stages 4-6 are NOT verified — they were
scoped from the code, not executed — so read their output rather than trusting it.

USAGE
-----
  python3 pipeline/resync_district_map.py            # print the plan, run nothing
  python3 pipeline/resync_district_map.py --run      # execute every stage in order
  python3 pipeline/resync_district_map.py --run --stage 3
  python3 pipeline/resync_district_map.py --run --draws 50   # cheap bootstrap smoke test

Budget hours: stages 1-4 are minutes, stage 5 is 1,000 draws x 7 turnout stops through
the whole House pipeline. Run it with --draws 50 first to confirm the chain works.
"""
import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
TREES = BASE / "data" / "outputs"


def house_runs() -> list:
    """One invocation per pure_multi* tree on disk, derived from the tree name rather than
    hardcoded: the trees that exist are the definition of what has to be rebuilt.

        pure_multi[_nosty][_triple][_turnout[_lNN]][_topN]
    """
    runs = []
    for d in sorted(p.name for p in TREES.glob("pure_multi*") if p.is_dir()):
        m = re.fullmatch(r"pure_multi(_nosty)?(_triple)?(_turnout(?:_l(\d+))?)?(?:_top(\d+))?", d)
        if not m:
            print(f"  ! tree name not understood, skipping: {d}", file=sys.stderr)
            continue
        nosty, triple, turnout, lam, depth = m.groups()
        env = {}
        if nosty:
            env["NO_STY"] = "1"
        if turnout:
            env["TURNOUT_WEIGHT"] = "1"
            if lam:
                env["TURNOUT_LAMBDA"] = str(int(lam) / 100)
        args = ["--triple"] if triple else []
        if depth:
            args.append(f"--depth={depth}")
        runs.append((d, env, args))
    return runs


def stages(draws: int) -> list:
    """(number, title, [(env, argv), ...]). Ordered: each stage consumes the one before."""
    pure = "pipeline/pure_only/run_pure_multi_house_stv.py"
    return [
        (1, "Redraw the district map (deterministic)", [
            ({}, ["python3", "pipeline/draw_geographic_districts.py"]),
        ]),
        (2, "Rebuild the canonical checkpoints — the per-voter district assignment", [
            ({}, ["python3", "pipeline/run_house_canonical.py"]),
            ({}, ["python3", "pipeline/run_house_canonical.py", "--triple"]),
        ]),
        (3, f"Re-run the House STV trees ({len(house_runs())} of them, ~4s each)", [
            (env, ["python3", pure, *args]) for _, env, args in house_runs()
        ]),
        (4, "Rebuild the party-list tree (drives its own depth x Wyoming x turnout matrix)", [
            ({}, ["python3", "pipeline/build_house_partylist.py"]),
        ]),
        (5, f"Re-run the bootstraps ({draws} draws) — THE EXPENSIVE STAGE", [
            ({}, ["python3", "analysis/bootstrap_uncertainty.py", "--draws", str(draws)]),
            ({}, ["python3", "analysis/bootstrap_partylist.py", "--draws", str(draws)]),
            ({}, ["python3", "analysis/bootstrap_population.py", "--draws", str(draws)]),
        ]),
        (6, "Rebuild the viz payloads", [
            ({}, ["python3", "viz/scripts/prepare_data.py"]),
            ({}, ["python3", "pipeline/build_house_votemodel_depth.py"]),
            ({}, ["python3", "pipeline/build_general_depth_bundle.py"]),
            ({}, ["python3", "pipeline/build_primary_depth_bundle.py"]),
        ]),
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="store_true", help="execute; otherwise print the plan only")
    ap.add_argument("--stage", type=int, help="run a single stage (1-6)")
    ap.add_argument("--draws", type=int, default=1000, help="bootstrap draws (stage 5)")
    a = ap.parse_args()

    plan = [s for s in stages(a.draws) if a.stage in (None, s[0])]

    if not a.run:
        print(__doc__)
        print("PLAN (nothing will run without --run)\n" + "=" * 72)
        for n, title, cmds in plan:
            print(f"\nStage {n}: {title}")
            for env, argv in cmds:
                prefix = " ".join(f"{k}={v}" for k, v in env.items())
                print(f"    {prefix + ' ' if prefix else ''}{' '.join(argv)}")
        print("\n" + "=" * 72)
        print(f"{sum(len(c) for _, _, c in plan)} commands. Re-run with --run to execute.")
        print("Afterwards: diff viz/src/data/houseSeats*.json and uncertainty*.json, confirm the")
        print("chamber still totals 873, and check the OG cards — they print seat counts.")
        return 0

    for n, title, cmds in plan:
        print(f"\n=== Stage {n}: {title} " + "=" * 20)
        for env, argv in cmds:
            shown = " ".join(f"{k}={v}" for k, v in env.items()) + " " + " ".join(argv)
            print(f"  -> {shown.strip()}")
            t0 = time.time()
            r = subprocess.run(argv, cwd=BASE, env={**os.environ, **env})
            if r.returncode != 0:
                print(f"  FAILED after {time.time() - t0:.0f}s — stopping. Downstream stages "
                      f"would run on half-rebuilt inputs.", file=sys.stderr)
                return r.returncode
            print(f"     ok ({time.time() - t0:.0f}s)")
    print("\nAll requested stages complete. Verify before committing: chamber totals 873, "
          "uncertainty modal seats agree with the observed chamber, OG cards regenerated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

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

PERFORMANCE  (measured on an M4 Pro, 8 performance + 4 efficiency cores, 24 GB)
------------------------------------------------------------------------------
One bootstrap draw costs ~7.0s alone and ~14s under 10-way parallelism — the work is
pure-Python STV counting, not BLAS, so capping Accelerate/OMP threads changes nothing
(measured: 0.66 vs 0.68 draws/s). RAM is not a constraint; workers are small.

  procs        4      8     10 (default)    12
  draws/s   0.49   0.64          0.66     0.75

Stage 5 is 7 stops x 1,001 jobs = 7,007 draws: ~2.9 h at the default, ~2.6 h at
--procs 12. Stages 1-4 are minutes once stage 3 runs --jobs-way parallel (79 trees,
~4s each: ~5 min serial, ~45s at 10-way). Budget ~3.5 h all in, or ~2 h tuned.

Where a draw goes: senate 3.3s, primary 3.3s, house 1.8s, CSV reads 0.6s. Note that
neither the senate nor the primary depends on the district map — senate is per-state,
primary is national — so ~74% of this particular rebuild recomputes numbers that cannot
change. A house-only draw mode reusing the other blocks from the existing payloads would
cut stage 5 to roughly 50 min; it is real work and a real correctness risk (draw indices
must stay aligned), so it is not done here. Separately, `first_surviving` is ~19% of
every draw and is the obvious vectorisation target if the bootstrap is ever run often.

Run --draws 50 first to confirm the chain works before committing hours.
"""
import argparse
import multiprocessing as mp
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
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


def stages(draws: int, procs_arg: list) -> list:
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
        # Independent of each other — one tree per process, run --jobs at a time.
        (3, f"Re-run the House STV trees ({len(house_runs())} of them, ~4s each, parallel)", [
            (env, ["python3", pure, *args]) for _, env, args in house_runs()
        ]),
        (4, "Rebuild the party-list tree (drives its own depth x Wyoming x turnout matrix)", [
            ({}, ["python3", "pipeline/build_house_partylist.py"]),
        ]),
        (5, f"Re-run the bootstraps ({draws} draws) — THE EXPENSIVE STAGE", [
            ({}, ["python3", "analysis/bootstrap_uncertainty.py", "--draws", str(draws), *procs_arg]),
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
    ap.add_argument("--jobs", type=int, default=max(1, (mp.cpu_count() or 4) - 2),
                    help="parallel House STV trees in stage 3")
    ap.add_argument("--procs", type=int, help="worker processes for the stage-5 bootstraps")
    a = ap.parse_args()

    procs_arg = ["--procs", str(a.procs)] if a.procs else []
    plan = [s for s in stages(a.draws, procs_arg) if a.stage in (None, s[0])]

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

    def run_one(job):
        env, argv = job
        t0 = time.time()
        # Quiet: 79 trees running at once would interleave into unreadable output. stderr stays.
        r = subprocess.run(argv, cwd=BASE, env={**os.environ, **env}, stdout=subprocess.DEVNULL)
        return r.returncode, time.time() - t0, " ".join(argv[-2:])

    for n, title, cmds in plan:
        print(f"\n=== Stage {n}: {title} " + "=" * 20)
        if n == 3 and len(cmds) > 1:
            # The trees do not read each other; only the checkpoints they share, already built.
            t0 = time.time()
            with ThreadPoolExecutor(max_workers=a.jobs) as ex:
                for rc, dt, label in ex.map(run_one, cmds):
                    if rc != 0:
                        print(f"  FAILED: {label} — stopping.", file=sys.stderr)
                        return rc
            print(f"  {len(cmds)} trees ok ({time.time() - t0:.0f}s, {a.jobs}-way)")
            continue
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

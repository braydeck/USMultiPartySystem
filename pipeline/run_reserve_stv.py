#!/usr/bin/env python3
"""
run_reserve_stv.py
-------------------
Run the pure-multi STV simulation on the reserve district maps, across all
turnout stops and ballot depths. Uses subprocess so environment variables
(TURNOUT_WEIGHT, TURNOUT_LAMBDA) are isolated per run.

~1s per run × 70 runs × 2 Wyoming rules = ~140s total.
"""

import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
SCRIPT = str(BASE_DIR / "pipeline" / "pure_only" / "run_pure_multi_house_stv.py")

DEPTHS = [0, 3, 5, 7, 10]
LAMBDAS = [0, 5, 10, 15, 20, 25, 30]

CONFIGS = [
    {
        "label": "reserve",
        "apport": str(BASE_DIR / "data" / "outputs" / "No_C7_canonical_reserve" / "district_apportionment.csv"),
        "checkpoint": str(BASE_DIR / "data" / "outputs" / "No_C7_canonical_reserve" / "ballots_checkpoint.parquet"),
        "county_dist": str(BASE_DIR / "data" / "processed" / "county_to_district_reserve.csv"),
        "tree_base": "pure_multi_reserve",
    },
    {
        "label": "triple_reserve",
        "apport": str(BASE_DIR / "data" / "outputs" / "No_C7_triple_reserve" / "district_apportionment.csv"),
        "checkpoint": str(BASE_DIR / "data" / "outputs" / "No_C7_triple_reserve" / "ballots_checkpoint.parquet"),
        "county_dist": str(BASE_DIR / "data" / "processed" / "county_to_district_triple_reserve.csv"),
        "tree_base": "pure_multi_triple_reserve",
    },
]


def run_one(job):
    cfg, lam, depth = job
    tree = cfg["tree_base"]
    suffix = "_turnout" + (f"_l{lam}" if lam > 0 else "")
    out_dir = str(BASE_DIR / "data" / "outputs" / (tree + suffix) / "house")

    env = {**os.environ, "TURNOUT_WEIGHT": "1"}
    if lam > 0:
        env["TURNOUT_LAMBDA"] = str(lam / 100)
    elif "TURNOUT_LAMBDA" in env:
        del env["TURNOUT_LAMBDA"]

    # run_pure_multi_house_stv.py doesn't accept CLI args for paths, so we patch
    # the module constants via a wrapper script inline.
    code = f"""
import sys; sys.path.insert(0, 'pipeline'); sys.path.insert(0, 'pipeline/pure_only')
from pathlib import Path
from run_pure_multi_house_stv import main
main(
    apportionment_path=Path({cfg['apport']!r}),
    checkpoint_path=Path({cfg['checkpoint']!r}),
    county_dist_path=Path({cfg['county_dist']!r}),
    output_dir=Path({out_dir!r}),
    label={cfg['label']!r},
    ballot_depth={depth},
)
"""
    r = subprocess.run([sys.executable, "-c", code], cwd=str(BASE_DIR), env=env,
                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    tag = f"{tree}{suffix}_top{depth}" if depth else f"{tree}{suffix}_full"
    if r.returncode != 0:
        print(f"  FAILED: {tag}\n{r.stderr.decode()[-500:]}", file=sys.stderr)
    return r.returncode, tag


def main():
    jobs = []
    for cfg in CONFIGS:
        for lam in LAMBDAS:
            for depth in DEPTHS:
                jobs.append((cfg, lam, depth))

    n = len(jobs)
    print(f"{n} STV runs, ~{n*1.1:.0f}s serial, ~{n*1.1/10:.0f}s at 10-way parallel")
    t0 = time.time()

    failed = 0
    with ThreadPoolExecutor(max_workers=10) as ex:
        for i, (rc, tag) in enumerate(ex.map(run_one, jobs)):
            if rc != 0:
                failed += 1
            if (i + 1) % 20 == 0 or i == n - 1:
                print(f"  [{i+1}/{n}] {time.time()-t0:.0f}s", flush=True)

    print(f"\nDone: {n - failed}/{n} succeeded in {time.time()-t0:.0f}s")
    if failed:
        print(f"  {failed} FAILED — check stderr above", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
build_viz_bundles.py
--------------------
Every derived viz artifact that has to be rebuilt after prepare_data.py, in order.

Why this exists: the sim scripts and prepare_data.py were documented in the README, but the
nine builders below were not, so a regeneration could leave the deployed JSON silently
disagreeing with the trees it was supposedly built from. Nothing warns you — the app just
renders stale numbers, or 404s a bundle and drops a whole section.

ORDER MATTERS, twice over:
  * five of these import prepare_data, so they cannot run before it (and prepare_data cannot
    call them, which is why this is a separate step rather than a hook inside it);
  * build_senate_rank7 and build_legislation_rank7 deliberately OVERWRITE JSON that
    prepare_data.py just wrote, replacing the plain trees with the rank-7 ones the app
    actually defaults to. Run them earlier and prepare_data would clobber them back.

A failure stops the run. These scripts overwrite deployed JSON in place, so a half-finished
sequence is worse than an obvious error: the viz would be part-old, part-new with nothing
saying which parts.

NOT included, on purpose: build_hex_ec_cartogram.py and build_hex_seat_cartogram.py. Those
generate the hex tilings, which key off apportionment rather than the per-run turnout and depth
data, so they change far less often — and the EC one needs a separate invocation per basis
(--basis electoral and --basis population), which a blanket runner would get wrong. Rebuild
them by hand when seat counts change.

Usage:
    python3 pipeline/build_viz_bundles.py              # run the sequence
    python3 pipeline/build_viz_bundles.py --list       # show the order, run nothing
    python3 pipeline/build_viz_bundles.py --dry-run    # print the commands, run nothing
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).parent.parent

# (script, what it produces / why it is here). Order is the run order.
STEPS: list[tuple[str, str]] = [
    ("pipeline/build_house_partylist.py",
     "housePartyList.json — party-list PR on the same districts as the STV run"),
    ("pipeline/build_senate_rank7.py",
     "OVERWRITES the deployed senate JSONs with the rank-7 winnow trees"),
    ("pipeline/build_legislation_rank7.py",
     "OVERWRITES house/senate vote-model families with the rank-7 + depth-7 defaults"),
    ("pipeline/build_general_depth_bundle.py",
     "generalDepth.json — presidency general, 4 depths x 7 turnout stops"),
    ("pipeline/build_primary_depth_bundle.py",
     "primaryDepth.json — primary, 4 depths x 7 turnout stops"),
    ("pipeline/build_house_votemodel_depth.py",
     "houseVoteModelDepth.json — house vote model across depths"),
    ("pipeline/build_top_two_bundle.py",
     "topTwo.json — instructive-ballot top-two splits per state"),
    ("pipeline/build_single_race_data.py",
     "singleRaceVoters.json — voter-level data for the Single Race Simulator"),
    ("pipeline/build_current_party_profiles.py",
     "currentPartySpreads.json — today's DEM/IND/REP electorates for the Parties tab"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="show the order and exit")
    ap.add_argument("--dry-run", action="store_true", help="print the commands without running")
    args = ap.parse_args()

    if args.list or args.dry_run:
        for i, (script, why) in enumerate(STEPS, 1):
            print(f"{i:>2}. {script}")
            print(f"    {why}")
            if args.dry_run:
                print(f"    $ {sys.executable} {script}")
        return 0

    missing = [s for s, _ in STEPS if not (BASE / s).exists()]
    if missing:
        print("Missing scripts, aborting before anything is overwritten:", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
        return 1

    started = time.time()
    for i, (script, why) in enumerate(STEPS, 1):
        print(f"\n{'=' * 78}\n[{i}/{len(STEPS)}] {script}\n  {why}\n{'=' * 78}", flush=True)
        t0 = time.time()
        result = subprocess.run([sys.executable, script], cwd=BASE)
        if result.returncode != 0:
            print(f"\n✗ {script} exited {result.returncode}. Stopping.\n"
                  f"  Deployed JSON is now part-regenerated. Fix the failure and rerun this\n"
                  f"  script from the top — the steps are idempotent, so a full rerun is safe.",
                  file=sys.stderr)
            return result.returncode
        print(f"  ✓ {time.time() - t0:.1f}s", flush=True)

    print(f"\nAll {len(STEPS)} bundles rebuilt in {time.time() - started:.1f}s.")
    print("Hex tilings are NOT part of this run — see the module docstring.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

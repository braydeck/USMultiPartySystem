#!/usr/bin/env python3
"""
check_stale.py
--------------
Find committed outputs that were built from inputs that have since changed.

This catches the failure mode that cost 73 of 74 house trees six weeks of drift: an input
changes, nothing re-runs, and the stale outputs keep serving the app. Nothing signals it —
the pipeline still runs clean, the app still builds, and the tests still pass.

  python3 pipeline/check_stale.py              # hash check, ~1s, no side effects
  python3 pipeline/check_stale.py --regenerate # rebuild everything and diff, ~3min

HOW IT DECIDES
The fast check hashes the declared inputs and compares them to `.verified.json`, a stamp
written by the last successful --regenerate. An input whose hash differs from the stamp means
that group has not been rebuilt since the input changed.

Two designs that do NOT work, both tried on 2026-09-12:
  - mtimes: git does not preserve them, so any clone or checkout resets everything and the
    check goes blind.
  - commit dates: a regeneration that produces byte-identical output creates no commit, so a
    file that is perfectly current keeps its old date and reads as stale forever.
The stamp avoids both because it records what the inputs *were* at the last verification,
which is the actual question.

MAINTAINING IT
GROUPS maps an output glob to the inputs that feed it, verified against each script's own path
constants on 2026-09-12. When a runner gains an input, add it here or this check silently
stops covering it. That is the one way this file rots.
"""

import argparse
import collections
import hashlib
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
STAMP = BASE / "data" / "outputs" / ".verified.json"

PROCESSED = "data/processed/"
SURVEY = [PROCESSED + "efa_factor_scores.csv", PROCESSED + "typology_cluster_assignments.csv"]
GEO = [PROCESSED + "county_to_district.csv", PROCESSED + "voter_county_fips.csv",
       "pipeline/county_split_overrides.csv"]
TURNOUT = [PROCESSED + "turnout_propensity.csv"]
CANON = ["data/outputs/canonical/district_apportionment.csv",
         "data/outputs/canonical/ballots_checkpoint.parquet",
         "data/outputs/canonical_triple/district_apportionment.csv",
         "data/outputs/canonical_triple/ballots_checkpoint.parquet"]
RUNNERS = ["pipeline/pure_only/run_pure_multi_house_stv.py",
           "pipeline/pure_only/turnout_weights.py"]

GROUPS = [
    ("house (party-line)", SURVEY + GEO + TURNOUT + CANON + RUNNERS),
    ("house (crossover)", SURVEY + GEO + TURNOUT + CANON + [
        "pipeline/run_fd_house_stv.py", "pipeline/generate_factor_deviation_ballots.py",
        "pipeline/generate_factor_deviation_candidates.py"]),
    ("house (reserve)", SURVEY + TURNOUT + RUNNERS + [
        PROCESSED + "county_to_district_reserve.csv",
        PROCESSED + "county_to_district_triple_reserve.csv",
        "data/outputs/canonical_reserve/district_apportionment.csv",
        "data/outputs/canonical_reserve/ballots_checkpoint.parquet",
        "pipeline/run_reserve_stv.py", "pipeline/build_reserve_apportionment.py",
        "pipeline/draw_reserve_districts.py", "pipeline/build_reserve_checkpoints.py"]),
    ("senate", SURVEY + TURNOUT + [
        "data/outputs/pure_multi/state_candidate_profiles.csv",
        "pipeline/pure_only/run_pure_multi_senate.py"]),
    ("primary", SURVEY + TURNOUT + [
        "data/outputs/pure_multi/presidential_ballots.csv",
        "data/outputs/pure_multi/state_pod_assignments.csv",
        "pipeline/pure_only/run_pure_multi_primary.py"]),
    ("presidential", SURVEY + TURNOUT + [
        "data/outputs/pure_multi/presidential_ballots.csv",
        "pipeline/pure_only/run_pure_multi_presidential.py"]),
    ("ballots", SURVEY + ["pipeline/pure_only/generate_pure_multi_ballots.py"]),
    ("viz payloads", SURVEY + TURNOUT + [
        "viz/scripts/prepare_data.py", "pipeline/build_house_partylist.py",
        "pipeline/build_house_reserve.py", "pipeline/build_legislation_rank7.py",
        "pipeline/build_senate_rank7.py"]),
]

# Full rebuild in dependency order. resync stage 3 covers the 74 house trees; the rest are the
# pieces it does not reach. prepare_data.py chains the two rank-7 rebuilds itself.
REGEN = [
    ("house trees (74)", ["python3", "pipeline/resync_district_map.py", "--run",
                          "--stage", "3", "--jobs", "3"]),
    ("reserve trees (70)", ["python3", "pipeline/run_reserve_stv.py"]),
    ("party list", ["python3", "pipeline/build_house_partylist.py"]),
    ("reserve payload", ["python3", "pipeline/build_house_reserve.py"]),
    ("viz payloads (+rank7)", ["python3", "viz/scripts/prepare_data.py"]),
]


def digest(rel: str) -> str | None:
    p = BASE / rel
    if not p.exists():
        return None
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def all_inputs() -> list:
    seen, out = set(), []
    for _, ins in GROUPS:
        for i in ins:
            if i not in seen:
                seen.add(i); out.append(i)
    return out


def check() -> int:
    if not STAMP.exists():
        print(f"  No stamp at {STAMP.relative_to(BASE)}.")
        print("  Run --regenerate once to record the verified state.")
        return 1
    stamp = json.loads(STAMP.read_text())
    now = {i: digest(i) for i in all_inputs()}
    stale = 0
    for name, ins in GROUPS:
        changed = [i for i in ins if now.get(i) != stamp["inputs"].get(i)]
        if changed:
            stale += 1
            print(f"  {name:22s} STALE — {len(changed)} input(s) changed since verification:")
            for c in changed[:4]:
                was = "absent" if stamp["inputs"].get(c) is None else "changed"
                print(f"      {c}  ({was})")
            if len(changed) > 4:
                print(f"      … and {len(changed) - 4} more")
        else:
            print(f"  {name:22s} ok")
    print(f"\n  verified {stamp['verified_at']} at commit {stamp['commit']}")
    return stale


def regenerate() -> int:
    for label, cmd in REGEN:
        print(f"  running {label} …", flush=True)
        r = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  FAILED: {' '.join(cmd)}\n{(r.stderr or r.stdout)[-1200:]}")
            return 1
    dirty = [c for c in subprocess.run(
        ["git", "status", "--porcelain", "data/outputs", "viz/src/data", "viz/public/data"],
        cwd=BASE, capture_output=True, text=True).stdout.splitlines() if c[:2] != "??"]
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=BASE,
                            capture_output=True, text=True).stdout.strip()
    STAMP.write_text(json.dumps({
        "verified_at": subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"],
                                      capture_output=True, text=True).stdout.strip(),
        "commit": commit,
        "note": "Written by pipeline/check_stale.py --regenerate. Records the inputs as they "
                "stood when every committed output last reproduced. Commit this with the "
                "regenerated outputs.",
        "inputs": {i: digest(i) for i in all_inputs()},
    }, indent=2, sort_keys=True) + "\n")
    if not dirty:
        print("\n  clean — every committed output reproduces from current code")
        print(f"  stamp written to {STAMP.relative_to(BASE)}")
        return 0
    by_tree = collections.Counter(
        c[3:].split("/")[2] if c[3:].startswith("data/outputs/") else "viz payloads"
        for c in dirty)
    print(f"\n  STALE — {len(dirty)} committed files differ from a fresh run:")
    for tree, n in by_tree.most_common(12):
        print(f"    {tree:52s} {n}")
    print("\n  The regenerated files are the correct ones. Review, then commit them together")
    print(f"  with {STAMP.relative_to(BASE)}.")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--regenerate", action="store_true",
                    help="rebuild every output group, diff, and rewrite the stamp")
    a = ap.parse_args()
    if a.regenerate:
        print("Rebuilding every output group (~3 min). Files are rewritten in place.\n")
        return regenerate()
    print("Comparing declared inputs against the last verified stamp.\n")
    n = check()
    print(f"  {n} group(s) stale." if n else "  all groups current.")
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())

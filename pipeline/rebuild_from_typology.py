#!/usr/bin/env python3
"""Rebuild everything downstream of a new typology (efa_factor_scores.csv +
typology_cluster_assignments.csv), in dependency order.

check_stale.py --regenerate covers only the house trees and the viz payloads. A new
typology also invalidates the per-respondent intermediates, both ballot files, every
senate / primary / presidential / crossover tree, the profile tables and the bootstraps.
This script runs all of it. Trees are enumerated from the directories on disk, so a tree
that exists is a tree that gets rebuilt. Scope and risks:
analysis/efa/exploration/church_dk/REGENERATION_SCOPE.md.

Prerequisite (not run here): analysis/efa/pipeline/efa_update.py, then
analysis/efa/pipeline/dpgmm_clustering.py, then a check that the ten party IDs landed
where expected.

USAGE
  python3 pipeline/rebuild_from_typology.py                  # print the plan
  python3 pipeline/rebuild_from_typology.py --run            # every step
  python3 pipeline/rebuild_from_typology.py --run --from 9 --to 12
  python3 pipeline/rebuild_from_typology.py --run --draws 50 # cheap bootstrap smoke test
"""
import argparse
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
TREES = BASE / "data" / "outputs"
PY = sys.executable


def tree_env(name, prefix):
    """env + depth for prefix[_triple][_turnout[_lNN]][_topN]; None if the name doesn't parse."""
    m = re.fullmatch(rf"{prefix}(_triple)?(_turnout(?:_l(\d+))?)?(?:_top(\d+))?", name)
    if not m:
        return None
    triple, turnout, lam, depth = m.groups()
    env = {}
    if turnout:
        env["TURNOUT_WEIGHT"] = "1"
        if lam:
            env["TURNOUT_LAMBDA"] = str(int(lam) / 100)
    return env, bool(triple), int(depth) if depth else 0


def trees_with(prefix, marker):
    out = []
    for p in sorted(TREES.glob(f"{prefix}*")):
        if (p / marker).exists():
            parsed = tree_env(p.name, prefix)
            if parsed is None:
                print(f"  ! tree name not understood, skipping: {p.name}", file=sys.stderr)
            else:
                out.append((p.name, *parsed))
    return out


def py(script, *args, env=None):
    return (env or {}, [PY, script, *args])


def steps(draws, procs):
    senate = [py("pipeline/pure_only/run_pure_multi_senate.py", *([f"--depth={d}"] if d else []), env=e)
              for _, e, _, d in trees_with("pure_multi", "senate")]
    office = []
    for _, e, _, d in trees_with("pure_multi", "primary_results_2028.csv"):
        e2 = {**e, **({"BALLOT_DEPTH": str(d)} if d else {})}
        chain = [py("pipeline/pure_only/run_pure_multi_primary.py", env=e2),
                 py("pipeline/pure_only/run_pure_multi_presidential.py", env=e2)]
        if e2:  # the base-tree call also computes the crossover tree's shares, so it runs after step 12
            chain.append(py("pipeline/compute_primary_state_shares.py", env=e2))
        office.append(chain)
    fd_house = [py("pipeline/run_fd_house_stv.py", *(["--triple"] if t else []), env=e)
                for _, e, t, _ in trees_with("factor_deviation", "house")]
    fd_senate = [py("pipeline/run_fd_senate_simulation.py", env=e)
                 for _, e, _, _ in trees_with("factor_deviation", "senate")]
    procs_arg = ["--procs", str(procs)] if procs else []
    return [
        (4, "per-respondent geography and turnout", [[py("pipeline/make_voter_counties.py")],
                                                    [py("pipeline/pure_only/compute_turnout_propensity.py")]]),
        (5, "party factor centroids", [[py("pipeline/archive/generate_candidate_profiles.py")]]),
        (6, "ballots", [[py("pipeline/pure_only/generate_pure_multi_ballots.py")],
                        [py("pipeline/pure_only/generate_party_ballots.py")]]),
        (7, "canonical district checkpoints", [[py("pipeline/run_house_canonical.py")],
                                               [py("pipeline/run_house_canonical.py", "--triple")]]),
        (8, "reserve checkpoints", [[py("pipeline/build_reserve_checkpoints.py")]]),
        (9, "house trees", [[py("pipeline/resync_district_map.py", "--run", "--stage", "3", "--jobs", "10")],
                            [py("pipeline/run_reserve_stv.py")]]),
        (10, f"senate trees ({len(senate)})", [[c] for c in senate]),
        (11, f"primary -> presidential -> stage shares ({len(office)} trees)", office),
        (12, "crossover chain", [[py("pipeline/generate_factor_deviation_candidates.py")],
                                 [py("pipeline/generate_factor_deviation_ballots.py")]]
            + [[c] for c in fd_house] + [[c] for c in fd_senate]
            + [[py("pipeline/run_fd_primary_2028.py"), py("pipeline/run_fd_irv_2028.py"),
                py("pipeline/compute_primary_state_shares.py")]]),
        (13, "profile tables", [[py("pipeline/archive/cluster_profile_viz.py")], [py("pipeline/add_compare_items.py")],
                                [py("pipeline/build_current_party_profiles.py")], [py("pipeline/compute_intensity.py")],
                                [py("pipeline/candidate_vote_model.py")]]),
        (14, "house payloads", [[py("pipeline/build_house_partylist.py")], [py("pipeline/build_house_reserve.py")]]),
        (15, f"bootstraps ({draws} draws)", [[py("analysis/bootstrap_uncertainty.py", "--draws", str(draws), "--force", *procs_arg)],
                                            [py("analysis/bootstrap_partylist.py", "--draws", str(draws))],
                                            [py("analysis/bootstrap_population.py", "--draws", str(draws))]]),
        (16, "viz payloads (chains the rank-7 rebuilds)", [[py("viz/scripts/prepare_data.py")]]),
        (17, "payloads downstream of prepare_data", [[py(s, *a)] for s, *a in [
            ("pipeline/build_house_mmp.py",), ("pipeline/build_house_rep_by_rank.py",),
            ("pipeline/build_house_votemodel_depth.py",), ("pipeline/build_general_depth_bundle.py",),
            ("pipeline/build_primary_depth_bundle.py",), ("pipeline/build_top_two_bundle.py",),
            ("pipeline/build_party_factor_ellipses.py",), ("pipeline/build_cross_party_affinity.py",),
            ("pipeline/build_single_race_data.py",),
            ("viz/scripts/make_quiz_questions.py",),
            ("pipeline/build_hex_seat_cartogram.py",), ("pipeline/build_hex_seat_cartogram.py", "--triple"),
            ("pipeline/build_hex_seat_cartogram.py", "--reserve"),
            ("pipeline/build_hex_seat_cartogram.py", "--reserve", "--triple"),
            ("pipeline/build_hex_mmp_cartogram.py",), ("pipeline/build_hex_mmp_cartogram.py", "--triple")]]
            # the quota payloads describe the app's default stop and refuse to run at any other
            + [[py(s, env={"TURNOUT_WEIGHT": "1", "TURNOUT_LAMBDA": "0.05"})]
               for s in ("analysis/quota_flows.py", "analysis/quota_composition.py")]),
    ]


def run(job, log):
    env, argv = job
    t0 = time.time()
    r = subprocess.run(argv, cwd=BASE, env={**os.environ, **env}, capture_output=True, text=True)
    tag = " ".join(f"{k}={v}" for k, v in env.items())
    with open(log, "a") as f:
        f.write(f"\n### {tag} {' '.join(argv[1:])}  exit={r.returncode}  {time.time() - t0:.0f}s\n{r.stdout[-4000:]}{r.stderr[-4000:]}")
    return r.returncode, f"{tag} {' '.join(argv[1:])}".strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--from", dest="first", type=int, default=4)
    ap.add_argument("--to", dest="last", type=int, default=17)
    ap.add_argument("--draws", type=int, default=1000)
    ap.add_argument("--procs", type=int, default=12)
    ap.add_argument("--jobs", type=int, default=8, help="parallel jobs within a step")
    ap.add_argument("--log", default=str(BASE / "data" / "outputs" / "rebuild_from_typology.log"))
    a = ap.parse_args()
    plan = [s for s in steps(a.draws, a.procs) if a.first <= s[0] <= a.last]
    for n, title, chains in plan:
        print(f"Step {n}: {title}  [{len(chains)} chain(s)]")
        if not a.run:
            for chain in chains[:3]:
                for env, argv in chain:
                    print("    " + " ".join([*(f"{k}={v}" for k, v in env.items()), *argv[1:]]))
            if len(chains) > 3:
                print(f"    … {len(chains) - 3} more")
            continue
        t0 = time.time()
        # independent chains of a step run in parallel; commands inside a chain run in order.
        # Steps whose chains share outputs (4-9, 13-17) are listed as ordered single chains.
        parallel = n in (10, 11) or (n == 12)
        def do_chain(chain):
            for job in chain:
                code, what = run(job, a.log)
                if code:
                    return code, what
            return 0, None
        if parallel:
            ordered_head = chains[:2] if n == 12 else []
            for chain in ordered_head:
                code, what = do_chain(chain)
                if code:
                    sys.exit(f"  FAILED: {what} (see {a.log})")
            with ThreadPoolExecutor(a.jobs) as ex:
                results = list(ex.map(do_chain, chains[len(ordered_head):]))
        else:
            results = []
            for chain in chains:
                results.append(do_chain(chain))
                if results[-1][0]:
                    break
        failed = [w for c, w in results if c]
        if failed:
            sys.exit(f"  FAILED: {failed[0]} (+{len(failed) - 1} more; see {a.log})")
        print(f"  ok in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()

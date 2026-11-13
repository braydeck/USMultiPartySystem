#!/usr/bin/env python3
"""Dissolve-a-party scenarios: rerun every election with one or more parties removed from the field.

A dissolved party fields no candidates anywhere. Each of its voters' ballots goes to their next
preference: the party's column of the DPGMM posterior is zeroed and every row renormalized, so the
ranking over the remaining parties is unchanged, and `cluster` (each voter's first choice) moves to
the voter's next party. Everything downstream is then rebuilt from those posteriors exactly as the
production pipeline builds it: ballots, state profiles, candidate counts per district and state
(a party that inherits voters fields more candidates where its share now earns them), every count.
Turnout stays per person: a dissolved party's voters keep the validated turnout of the cluster they
were scored in, because they are the same people. Bootstrap ranges are not rebuilt.

Engine: the bootstrap's in-process harness (analysis/bootstrap/inject.py) swaps the per-respondent
files for stand-ins, the production runners write their usual trees into a scratch workspace, and
the production payload builders (prepare_data, build_house_*, the depth bundles, top-two, quota
flows, representation by choice) convert those trees into the same JSON the app reads. Dropping the
parties from party_codes before any runner imports is what removes their candidates.

Output: data/dissolve_store/<KEY>/<file>.json, gzip-compressed, one folder per combination (KEY =
dissolved codes in LEFT_RIGHT order joined by '-', e.g. NAT-LP). Each file has the shape of the
baseline file of the same name; per-stop families ({name}Turnout{,L5..L30}.json) are one file keyed
by stop, and the three biggest bundles are split by ballot depth (housePartyList.top7.json).
manifest.json records the inputs' hashes so check_stale.py can flag a stale set.

USAGE
  python3 pipeline/build_dissolve_scenarios.py --check            # baseline must match every committed payload
  python3 pipeline/build_dissolve_scenarios.py --only NAT,LP     # one combination
  python3 pipeline/build_dissolve_scenarios.py --run --procs 6    # every combination; resumes, skips finished
  python3 pipeline/build_dissolve_scenarios.py --manifest         # rewrite the manifest for what is on disk
"""

import argparse
import contextlib
import gzip
import hashlib
import io
import itertools
import json
import multiprocessing as mp
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
STORE = BASE / "data" / "dissolve_store"
PROCESSED = BASE / "data" / "processed"
OUTPUTS = BASE / "data" / "outputs"
SRC_DATA = BASE / "viz" / "src" / "data"
PUB_DATA = BASE / "viz" / "public" / "data"

PARTS = [0, 5, 10, 15, 20, 25, 30]
DEPTHS = {"full": 0, "top3": 3, "top5": 5, "top7": 7, "top10": 10}
SPLIT_BY_DEPTH = ("housePartyList", "houseReserve", "primaryDepth")
DONE_MARKER = "done.json"

# Inputs whose change invalidates every scenario: the survey files and every script a run calls.
_SCRIPTS = ["pipeline/pure_only/" + f for f in (
    "run_pure_multi_house_stv.py", "run_pure_multi_senate.py", "run_pure_multi_primary.py",
    "run_pure_multi_presidential.py", "generate_pure_multi_ballots.py", "turnout_weights.py")] + [
    "pipeline/" + f for f in (
        "party_codes.py", "build_house_partylist.py", "build_house_mmp.py", "build_house_reserve.py",
        "build_house_rep_by_rank.py", "build_top_two_bundle.py", "compute_primary_state_shares.py",
        "build_dissolve_scenarios.py")] + [
    "viz/scripts/prepare_data.py", "analysis/quota_flows.py", "analysis/quota_composition.py",
    "analysis/bootstrap/inject.py"]
INPUTS = [BASE / p for p in _SCRIPTS] + [PROCESSED / f for f in (
    "typology_cluster_assignments.csv", "efa_factor_scores.csv", "turnout_propensity.csv",
    "voter_county_fips.csv", "party_order.csv", "county_to_district.csv", "county_to_district_triple.csv",
    "county_to_district_reserve.csv", "county_to_district_triple_reserve.csv",
    "county_split_zcta.csv", "county_split_zcta_triple.csv", "county_split_zcta_reserve.csv",
    "county_split_zcta_triple_reserve.csv")] + [
    BASE / "pipeline" / f for f in ("tiebreak.py", "district_assign.py")] + [
    OUTPUTS / d / f for d in ("canonical", "canonical_triple", "canonical_reserve", "canonical_triple_reserve")
    for f in ("district_apportionment.csv", "ballots_checkpoint.parquet")]


def file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def input_hashes() -> dict:
    return {str(p.relative_to(BASE)): file_hash(p) for p in INPUTS}


def live_order() -> list:
    sys.path.insert(0, str(BASE / "pipeline"))
    from party_codes import LEFT_RIGHT
    return list(LEFT_RIGHT)


def combo_key(combo) -> str:
    return "-".join(combo) if combo else "baseline"


def all_combos(order) -> list:
    # Every non-empty subset that leaves at least one party standing.
    return [c for r in range(1, len(order)) for c in itertools.combinations(order, r)]


def stop_suffix(part: int) -> str:
    return "Turnout" + (f"L{part}" if part else "")


def _quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


# ── one combination, in a fresh process ──────────────────────────────────────

def run_combo(combo: tuple, parity: bool = False) -> dict:
    """Run every election for one dissolved set. Returns {file name: payload}.

    parity=True keeps the legislation vote models on the bootstrap's modal chamber, as the committed
    baseline does, so --check can compare them; a dissolved field has no bootstrap and uses the
    observed chamber."""
    os.environ["TURNOUT_WEIGHT"] = "1"
    os.environ["TURNOUT_LAMBDA"] = "0"
    sys.path[:0] = [str(BASE / "pipeline" / "pure_only"), str(BASE / "pipeline"),
                    str(BASE / "viz" / "scripts"), str(BASE / "analysis"), str(BASE)]

    import numpy as np
    import pandas as pd

    # Drop the dissolved parties before anything that fields candidates is imported. In place, so
    # every `from party_codes import X` taken later sees the reduced set.
    import party_codes as pc
    gone = {pc.PARTY_TO_CLUSTER[p] for p in combo}
    pc.LIVE_CLUSTERS[:] = [k for k in pc.LIVE_CLUSTERS if k not in gone]
    for k in gone:
        del pc.PARTY_TO_CLUSTER[pc.CLUSTER_TO_PARTY.pop(k)]
    pc.PARTIES[:] = list(pc.CLUSTER_TO_PARTY.values())
    pc.LEFT_RIGHT[:] = [p for p in pc.LEFT_RIGHT if p not in combo]
    pc.EMPTY_PARTIES[:] = [p for k, p in pc.ALL_PARTIES.items() if k not in pc.CLUSTER_TO_PARTY]

    import turnout_weights as tw
    import generate_pure_multi_ballots as gb
    import run_pure_multi_house_stv as hou
    import run_pure_multi_senate as sen
    import run_pure_multi_primary as prim
    import run_pure_multi_presidential as pres
    import compute_primary_state_shares as css
    import build_house_partylist as bhp
    import build_house_mmp as bmm
    import build_house_reserve as bhr
    import build_house_rep_by_rank as rbr
    import build_top_two_bundle as ttb
    import quota_flows as qf
    import prepare_data as pdm
    from analysis.bootstrap.inject import resampled_inputs, ballots_path
    from analysis.bootstrap.contests import HOUSE_MAPS

    captured = {}
    capture = lambda data, name: captured.__setitem__("last", data)
    pdm.write_json = capture
    if not parity:
        pdm._modal_seats = lambda *a, **k: None

    def cap(fn, *a, **k):
        captured.pop("last", None)
        _quiet(fn, *a, **k)
        return captured["last"]

    # Inside the repo: the reused builders print their outputs relative to it.
    (STORE / "_work").mkdir(parents=True, exist_ok=True)
    ws = Path(tempfile.mkdtemp(prefix=f"{combo_key(combo)}_", dir=STORE / "_work"))
    wsviz = ws / "viz"
    wsviz.mkdir()
    out = {}
    try:
        # Stand-in inputs: dissolved posteriors, then ballots and state profiles rebuilt from them.
        typ = pd.read_csv(PROCESSED / "typology_cluster_assignments.csv")
        prob_cols = [f"prob_cluster_{k}" for k in range(10)]
        P = typ[prob_cols].values.astype(np.float64)
        if gone:
            P[:, sorted(gone)] = 0.0
            P /= P.sum(axis=1, keepdims=True)
            typ[prob_cols] = P
            typ["cluster"] = P.argmax(axis=1).astype(float)
        efa = pd.read_csv(PROCESSED / "efa_factor_scores.csv")
        ballots = gb.build_ballot_df(gb.generate_ballots(gb.compute_candidate_scores_prob(P), None))
        profiles = gb.build_state_profiles(ballots, P, efa["inputstate"].values,
                                           efa["commonpostweight"].values)
        subs = {}
        for real, df, keep_index in (
                (PROCESSED / "typology_cluster_assignments.csv", typ, False),
                (ballots_path("pure_multi"), ballots, True),
                (OUTPUTS / "pure_multi" / "state_candidate_profiles.csv", profiles, False)):
            subs[real] = ws / f"in_{real.name}"
            df.to_csv(subs[real], index=keep_index)
        typo_standin = subs[PROCESSED / "typology_cluster_assignments.csv"]

        def tree(name, part, depth=0):
            return (ws / "data" / "outputs" /
                    (name + "_turnout" + (f"_l{part}" if part else "") + (f"_top{depth}" if depth else "")))

        with resampled_inputs(np.arange(len(typ)), extra_paths=(ballots_path("pure_multi"),), substitutes=subs):
            # ── elections, every stop ────────────────────────────────────────────
            for part in PARTS:
                tw.TURNOUT_LAMBDA = part / 100.0
                tw._cache = None
                for map_key, base_tree in (("double", "pure_multi"), ("triple", "pure_multi_triple"),
                                           ("reserve", "pure_multi_reserve"),
                                           ("triple_reserve", "pure_multi_triple_reserve")):
                    cfg = HOUSE_MAPS[map_key]
                    for depth in DEPTHS.values():
                        # main() writes depth N into the <tree>_topN sibling of output_dir
                        _quiet(hou.main, apportionment_path=cfg["apport"], checkpoint_path=cfg["checkpoint"],
                               county_dist_path=cfg["county"], output_dir=tree(base_tree, part) / "house",
                               label="DISSOLVE", ballot_depth=depth)
                # Senate: the full-depth tree feeds the state round views, the rank-7 tree the seats
                # (build_senate_rank7.py), as in the baseline. main() rewrites OUTPUT_DIR per depth.
                for depth in (0, 7):
                    sen.OUTPUT_DIR = tree("pure_multi", part) / "senate"
                    _quiet(sen.main, ballot_depth=depth)
                # Primary -> general -> stage shares, every depth. main()s rewrite their paths with _topN.
                for depth in DEPTHS.values():
                    os.environ["BALLOT_DEPTH"] = str(depth)
                    prim.OUTPUT_DIR = tree("pure_multi", part)
                    _quiet(prim.main)
                    pres.OUTPUT_DIR = tree("pure_multi", part) / "irv"
                    pres.PRIMARY_PATH = tree("pure_multi", part) / "primary_results_2028.csv"
                    _quiet(pres.main)
                    d = tree("pure_multi", part, depth)
                    _quiet(css.compute_shares, ballots_path=ballots_path("pure_multi"),
                           primary_path=d / "primary_results_2028.csv",
                           pod_path=OUTPUTS / "pure_multi" / "state_pod_assignments.csv",
                           output_path=d / "primary_state_stage_shares.json", ballot_depth=depth)
                os.environ["BALLOT_DEPTH"] = "0"

            # ── per-stop families (prepare_data._build_turnout_variant + the rank-7 rebuilds) ──
            names = ["rawMultiPresidentialElection", "houseSeats", "houseStateMap", "districtStvResults",
                     "senateIrvRounds", "senateCondorcet", "senateBuckets", "pureMultiPrimary",
                     "pureMultiPrimaryBuckets", "pureMultiPrimaryStageShares", "houseSeatsTriple",
                     "districtStvResultsTriple", "pureMultiSenateCondorcet", "pureMultiSenateIRV",
                     "houseVoteModel", "senateVoteModel"]
            stops = {n: {} for n in names}
            for part in PARTS:
                k, sfx = str(part), stop_suffix(part)
                d, d7 = tree("pure_multi", part), tree("pure_multi", part, 7)
                stops["rawMultiPresidentialElection"][k] = cap(pdm.build_raw_multi_presidential_election, src_dir=d)
                stops["houseSeats"][k] = cap(pdm.build_house_seats, src_csv=d / "house" / "stv_seat_summary.csv")
                stops["houseStateMap"][k] = cap(pdm.build_house_state_map, src_dir=d)
                stops["districtStvResults"][k] = cap(pdm.build_district_stv_results,
                                                     src_csv=d / "house" / "stv_results_by_district.csv")
                stops["senateIrvRounds"][k] = cap(pdm.build_senate_irv_rounds, d)
                stops["senateCondorcet"][k] = cap(pdm.build_senate_condorcet, d)
                stops["senateBuckets"][k] = cap(pdm.build_senate_buckets, d)
                stops["pureMultiPrimary"][k] = cap(pdm.build_pure_multi_primary, d)
                stops["pureMultiPrimaryBuckets"][k] = cap(pdm.build_pure_multi_primary_buckets, d)
                stops["pureMultiPrimaryStageShares"][k] = cap(pdm.build_pure_multi_primary_state_shares, d, "x")
                stops["houseSeatsTriple"][k] = cap(pdm.build_house_seats_triple, tree("pure_multi_triple", part))
                stops["districtStvResultsTriple"][k] = cap(pdm.build_district_stv_results_triple,
                                                           tree("pure_multi_triple", part))
                senate = {}
                pdm.write_json = lambda data, name: senate.__setitem__(name, data)
                _quiet(pdm.build_pure_multi_senate, src_dir=d7, cond_name="c", irv_name="i")
                pdm.write_json = capture
                stops["pureMultiSenateCondorcet"][k], stops["pureMultiSenateIRV"][k] = senate["c"], senate["i"]
                # The out_name carries the stop suffix: the baseline reads the modal chamber by it.
                stops["houseVoteModel"][k] = cap(pdm.build_house_vote_model_wfp, d7, out_name=f"houseVoteModel{sfx}.json",
                                                 triple_src=tree("pure_multi_triple", part, 7))
                stops["senateVoteModel"][k] = cap(pdm.build_senate_vote_model_wfp, d7, out_name=f"senateVoteModel{sfx}.json")
            out.update(stops)

            # ── depth bundles (build_general_depth_bundle / build_primary_depth_bundle / votemodel depth) ──
            out["generalDepth"] = {f"top{D}": {str(p): cap(pdm.build_raw_multi_presidential_election,
                                                           tree("pure_multi", p, D), "x") for p in PARTS}
                                   for D in (3, 5, 7, 10)}
            out["primaryDepth"] = {f"top{D}": {
                "primary": {str(p): cap(pdm.build_pure_multi_primary, tree("pure_multi", p, D), "x") for p in PARTS},
                "buckets": {str(p): cap(pdm.build_pure_multi_primary_buckets, tree("pure_multi", p, D), "x") for p in PARTS},
                "stageShares": {str(p): cap(pdm.build_pure_multi_primary_state_shares, tree("pure_multi", p, D), "x")
                                for p in PARTS},
            } for D in (3, 5, 7, 10)}
            out["houseVoteModelDepth"] = {dk: {str(p): cap(pdm.build_house_vote_model_wfp, tree("pure_multi", p, D), "x",
                                                           triple_src=tree("pure_multi_triple", p, D)) for p in PARTS}
                                          for dk, D in (("top3", 3), ("top5", 5), ("top7", 7), ("top10", 10), ("full", 0))}

            # ── House payloads through the production builders, pointed at the workspace ──
            for mod, name in ((bhp, "housePartyList"), (bhr, "houseReserve")):
                mod.BASE_DIR = ws
                mod.TYPO_PATH = typo_standin
                mod.OUT_PATH = wsviz / f"{name}.json"
                mod.SUMMARY_PATH = wsviz / f"{name}_summary.json"
            bmm.TYPO_PATH = typo_standin
            bmm.OUT_PATH, bmm.SUMMARY_PATH = wsviz / "houseMmp.json", wsviz / "houseMmpNational.json"
            for mod in (bhp, bmm, bhr):
                _quiet(mod.main)
            rbr.VIZ_DATA, rbr.OUT_PATH = wsviz, wsviz / "houseRepByRank.json"
            _quiet(rbr.main)
            ttb.OUTPUTS, ttb.OUT_PATH = ws / "data" / "outputs", wsviz / "topTwo.json"
            _quiet(ttb.main)
            qf.PUBLISHED, qf.OUT_PATH = wsviz / "housePartyList.json", wsviz / "quotaFlows.json"
            _quiet(qf.main)
            # Constellation transfer lines: the default stop's full-ranking count (the baseline
            # reads the full-participation tree, which no app stop shows).
            real_pm, pdm.PURE_MULTI_DIR = pdm.PURE_MULTI_DIR, tree("pure_multi", 5)
            out["transferMatrix"] = cap(pdm.build_transfer_matrix)
            pdm.PURE_MULTI_DIR = real_pm

        for name, f in (("housePartyList", "housePartyList.json"), ("houseDepthNational", "housePartyList_summary.json"),
                        ("houseReserve", "houseReserve.json"), ("houseReserveNational", "houseReserve_summary.json"),
                        ("houseMmp", "houseMmp.json"), ("houseMmpNational", "houseMmpNational.json"),
                        ("houseRepByRank", "houseRepByRank.json"), ("topTwo", "topTwo.json"),
                        ("quotaFlows", "quotaFlows.json")):
            out[name] = json.loads((wsviz / f).read_text())
        return out
    finally:
        shutil.rmtree(ws, ignore_errors=True)


def write_combo(out: dict, out_dir: Path, combo: tuple):
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, payload in out.items():
        parts = payload.items() if name in SPLIT_BY_DEPTH else [(None, payload)]
        for dk, data in parts:
            fname = f"{name}.{dk}.json" if dk else f"{name}.json"
            with gzip.open(out_dir / fname, "wt", compresslevel=6) as f:
                json.dump(data, f, separators=(",", ":"))
    # Written last: a folder without it is an interrupted run and gets rebuilt.
    (out_dir / DONE_MARKER).write_text(json.dumps({"dissolved": list(combo),
                                                   "files": len(list(out_dir.glob("*.json"))) - 0}))


def _worker(args):
    combo, out_dir = args
    t0 = time.time()
    try:
        write_combo(run_combo(tuple(combo)), Path(out_dir), tuple(combo))
        return {"combo": combo_key(combo), "seconds": round(time.time() - t0, 1)}
    except (Exception, SystemExit) as exc:  # report and keep the pool going (a builder's sys.exit too); retried next run
        import traceback
        return {"combo": combo_key(combo), "error": f"{exc}\n{traceback.format_exc()[-1500:]}"}


def _parity_worker(_):
    return run_combo((), parity=True)


def run_isolated(fn, jobs, procs):
    """One fresh process per combination: party_codes and turnout_weights are module state."""
    ctx = mp.get_context("spawn")
    with ctx.Pool(procs, maxtasksperchild=1) as pool:
        yield from pool.imap_unordered(fn, jobs)


# ── baseline parity check ────────────────────────────────────────────────────

def check():
    """Run the harness with nothing dissolved and compare every file against the committed payloads."""
    t0 = time.time()
    got = list(run_isolated(_parity_worker, [None], 1))[0]
    print(f"baseline run: {time.time() - t0:.0f}s")
    load = lambda p: json.loads(p.read_text())
    bad, checked = [], 0
    for name, payload in got.items():
        if name == "transferMatrix":
            continue  # built from the default stop here; the baseline uses a tree no stop shows
        if isinstance(payload, dict) and set(payload) == {str(p) for p in PARTS}:
            for part, data in payload.items():
                checked += 1
                if data != load(SRC_DATA / f"{name}{stop_suffix(int(part))}.json"):
                    bad.append(f"{name}{stop_suffix(int(part))}")
        else:
            src = SRC_DATA / f"{name}.json"
            checked += 1
            if payload != load(src if src.exists() else PUB_DATA / f"{name}.json"):
                bad.append(name)
    if bad:
        print(f"{len(bad)} of {checked} files differ: {', '.join(bad)}")
        sys.exit(1)
    print(f"baseline reproduces all {checked} committed payload files")


def write_manifest(order, combos):
    STORE.mkdir(parents=True, exist_ok=True)
    done = [combo_key(c) for c in combos if (STORE / combo_key(c) / DONE_MARKER).exists()]
    (STORE / "manifest.json").write_text(json.dumps({
        "parties": order, "combinations": len(combos), "built": len(done),
        "inputs": input_hashes(), "written": time.strftime("%Y-%m-%d %H:%M:%S"),
    }, indent=1))
    return done


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--only", help="comma-separated party codes to dissolve")
    ap.add_argument("--procs", type=int, default=6)
    ap.add_argument("--force", action="store_true", help="rebuild finished combinations too")
    ap.add_argument("--manifest", action="store_true", help="rewrite manifest.json for what is on disk")
    a = ap.parse_args()
    order = live_order()
    if a.check:
        return check()
    if a.manifest:
        print(f"manifest: {len(write_manifest(order, all_combos(order)))} of {len(all_combos(order))} built")
        return
    combos = all_combos(order)
    if a.only:
        want = set(a.only.split(","))
        combos = [c for c in combos if set(c) == want]
        if not combos:
            sys.exit(f"not a valid combination: {a.only}")
    elif not a.run:
        ap.print_help()
        return
    # A stale set (new typology, order or code) is rebuilt whole rather than mixed with fresh files.
    man = STORE / "manifest.json"
    if man.exists() and a.run and not a.force and json.loads(man.read_text()).get("inputs") != input_hashes():
        sys.exit("inputs changed since the last build; rerun with --force to rebuild every combination")
    jobs = [(c, str(STORE / combo_key(c))) for c in combos
            if a.force or a.only or not (STORE / combo_key(c) / DONE_MARKER).exists()]
    print(f"{len(jobs)} of {len(combos)} combinations to build on {a.procs} processes", flush=True)
    t0, failed = time.time(), 0
    for i, res in enumerate(run_isolated(_worker, jobs, a.procs), 1):
        if "error" in res:
            failed += 1
            print(f"  FAILED {res['combo']}: {res['error']}", flush=True)
        else:
            el = time.time() - t0
            print(f"  [{i}/{len(jobs)}] {res['combo']} {res['seconds']}s  elapsed {el / 60:.0f} min, "
                  f"eta {el / i * (len(jobs) - i) / 60:.0f} min", flush=True)
        if i % 25 == 0:
            write_manifest(order, all_combos(order))
    done = write_manifest(order, all_combos(order))
    print(f"{len(done)} of {len(all_combos(order))} combinations built; {failed} failed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()

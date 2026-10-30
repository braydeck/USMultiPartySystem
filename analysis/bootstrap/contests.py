"""Run one bootstrap draw through all four real pipelines.

Env must be set before importing any pipeline module (turnout_weights reads
TURNOUT_WEIGHT/TURNOUT_LAMBDA at import time), so the imports live inside
_pipelines() and a worker process must only ever see one lambda.
"""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from .inject import BASE, PROCESSED, ballots_path, resampled_inputs
from .resample import stratified_indices

sys.path.insert(0, str(BASE / "pipeline"))
from party_codes import CLUSTER_TO_PARTY  # noqa: E402

# The app publishes the rank-7 model for the house, primary and president.
DEPTH = 7

_MODS = {}


def _pipelines(lam: float):
    """Import the pipeline modules once per process, with env already set."""
    if _MODS:
        if _MODS["lam"] != lam:
            # An assert here would vanish under -O and silently mislabel a whole stop.
            raise RuntimeError(f"a worker saw two lambdas ({_MODS['lam']} then {lam}); use one Pool per stop")
        return _MODS
    os.environ["TURNOUT_WEIGHT"] = "1"
    os.environ["TURNOUT_LAMBDA"] = str(lam)
    # The primary and the president read BALLOT_DEPTH from the environment (default 0 =
    # full ranking). The app publishes the rank-7 model, so leaving this unset would
    # bootstrap a different contest than the one on the page.
    os.environ["BALLOT_DEPTH"] = str(DEPTH)
    sys.path.insert(0, str(BASE / "pipeline" / "pure_only"))
    import run_pure_multi_house_stv as hou
    import run_pure_multi_presidential as pres
    import run_pure_multi_primary as prim
    import run_pure_multi_senate as sen
    import turnout_weights as tw
    assert tw.TURNOUT_WEIGHT and tw.TURNOUT_LAMBDA == lam, \
        f"turnout_weights imported before env was set ({tw.TURNOUT_WEIGHT}, {tw.TURNOUT_LAMBDA})"
    _MODS.update(lam=lam, sen=sen, hou=hou, prim=prim, pres=pres, tw=tw)
    return _MODS


def _quiet(fn, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **k)


def _recluster_inputs(seed: int, tmp: Path):
    """Write draw (seed - 42)'s typology, turnout, ballots and state profiles to `tmp`.

    Returns (idx, substitutes). Ballots and state profiles are rebuilt with the generator's own
    functions, because both are functions of the posteriors, which change with the parties.
    """
    from . import recluster as rc
    sys.path.insert(0, str(BASE / "pipeline" / "pure_only"))
    import generate_pure_multi_ballots as gb
    d = seed - 42
    idx = rc.draw_index(d)
    typ = rc.draw_typology(d)
    probs = typ[rc.PROB_COLS].values.astype(np.float64)
    turn = rc.draw_turnout(d, typ["cluster"].values, idx)
    ballots = gb.build_ballot_df(gb.generate_ballots(gb.compute_candidate_scores_prob(probs), None))
    efa = pd.read_csv(PROCESSED / "efa_factor_scores.csv")
    profiles = gb.build_state_profiles(ballots.iloc[idx].reset_index(drop=True), probs[idx],
                                       efa["inputstate"].values[idx], efa["commonpostweight"].values[idx])
    files = {PROCESSED / "typology_cluster_assignments.csv": (typ, False),
             PROCESSED / "turnout_propensity.csv": (turn, False),
             ballots_path("pure_multi"): (ballots, True),
             BASE / "data" / "outputs" / "pure_multi" / "state_candidate_profiles.csv": (profiles, False)}
    subs = {}
    for real, (df, keep_index) in files.items():
        stand_in = tmp / f"draw_{real.name}"
        df.to_csv(stand_in, index=keep_index)
        subs[real] = stand_in
    return idx, subs


# The House maps the app offers. Reserve maps carve ~20% of each state's seats into a statewide
# Sainte-Laguë top-off seeded with the district STV wins (pipeline/build_house_reserve.py).
OUTPUTS = BASE / "data" / "outputs"
HOUSE_MAPS = {
    "double": dict(apport=OUTPUTS / "canonical" / "district_apportionment.csv",
                   checkpoint=OUTPUTS / "canonical" / "ballots_checkpoint.parquet",
                   county=PROCESSED / "county_to_district.csv", reserve=False),
    "triple": dict(apport=OUTPUTS / "canonical_triple" / "district_apportionment.csv",
                   checkpoint=OUTPUTS / "canonical_triple" / "ballots_checkpoint.parquet",
                   county=PROCESSED / "county_to_district_triple.csv", reserve=False),
    "reserve": dict(apport=OUTPUTS / "canonical_reserve" / "district_apportionment.csv",
                    checkpoint=OUTPUTS / "canonical_reserve" / "ballots_checkpoint.parquet",
                    county=PROCESSED / "county_to_district_reserve.csv", reserve=True),
    "triple_reserve": dict(apport=OUTPUTS / "canonical_triple_reserve" / "district_apportionment.csv",
                           checkpoint=OUTPUTS / "canonical_triple_reserve" / "ballots_checkpoint.parquet",
                           county=PROCESSED / "county_to_district_triple_reserve.csv", reserve=True),
}
HOUSE_DEPTHS = {"full": 0, "top3": 3, "top5": 5, "top7": 7, "top10": 10}


def _reserve_topoff(district_csv: Path, apport: Path, fc: np.ndarray, w: np.ndarray,
                    inputstate: np.ndarray) -> dict:
    """National STV + reserve seats: district STV wins plus each state's compensatory tier."""
    sys.path.insert(0, str(BASE / "pipeline"))
    from build_house_reserve import load_stv_seats, sainte_lague
    app = pd.read_csv(apport)
    stv = load_stv_seats(district_csv)
    total = np.zeros(10, dtype=int)
    for f, g in app.groupby("state_fips"):
        won = sum((stv.get(d, np.zeros(10, int)) for d in g["district_id"]), np.zeros(10, int))
        m = inputstate == int(f)
        V = np.bincount(fc[m], weights=w[m], minlength=10)
        R = int(g["reserve"].iloc[0])
        total += won + (sainte_lague(V, R, seed=won) if R > 0 else 0)
    return {p: int(total[k]) for k, p in CLUSTER_TO_PARTY.items()}


def run_house_draw(seed: int, lam: float, configs, observed: bool = False) -> dict:
    """House STV seats per party for each (map, depth) in `configs`, for one re-clustering draw.

    Only the House runs, so the draw needs its typology and turnout stand-ins and nothing else:
    the House builds its own district ballots from the posteriors. `observed` runs the published
    parties on the full sample, which must reproduce the committed house trees.
    """
    m = _pipelines(lam)
    hou = m["hou"]
    tmp = Path(tempfile.mkdtemp(prefix=f"bh_{seed}_"))
    efa = pd.read_csv(PROCESSED / "efa_factor_scores.csv")
    if observed:
        idx = np.arange(len(efa))
        typ = pd.read_csv(PROCESSED / "typology_cluster_assignments.csv")
        turn = pd.read_csv(PROCESSED / "turnout_propensity.csv")
        subs = None
    else:
        from . import recluster as rc
        d = seed - 42
        idx = rc.draw_index(d)
        typ = rc.draw_typology(d)
        turn = rc.draw_turnout(d, typ["cluster"].values, idx)
        subs = {}
        for real, df in ((PROCESSED / "typology_cluster_assignments.csv", typ),
                         (PROCESSED / "turnout_propensity.csv", turn)):
            subs[real] = tmp / f"draw_{real.name}"
            df.to_csv(subs[real], index=False)
    # Reserve top-off inputs, on the draw's resample: first choice and turnout-weighted count weight.
    fc = typ["cluster"].values[idx].astype(int)
    t = turn["turnout_cluster"].values[idx].astype(float)
    w = efa["commonpostweight"].values[idx] * (t + lam * (1.0 - t))
    inputstate = efa["inputstate"].values[idx].astype(int)

    out = {}
    try:
        with resampled_inputs(idx, substitutes=subs):
            m["tw"]._cache = None
            for map_key, depth_key in configs:
                cfg, depth = HOUSE_MAPS[map_key], HOUSE_DEPTHS[depth_key]
                run_out = tmp / f"{map_key}_{depth_key}" / "house"
                _quiet(hou.main, apportionment_path=cfg["apport"], checkpoint_path=cfg["checkpoint"],
                       county_dist_path=cfg["county"], output_dir=run_out, label="BOOTSTRAP",
                       ballot_depth=depth)
                run_dir = (run_out.parent.parent / (run_out.parent.name + f"_top{depth}") / run_out.name
                           if depth else run_out)
                if cfg["reserve"]:
                    seats = _reserve_topoff(run_dir / "stv_results_by_district.csv", cfg["apport"],
                                            fc, w, inputstate)
                else:
                    hs = pd.read_csv(run_dir / "stv_seat_summary.csv")
                    seats = {CLUSTER_TO_PARTY[int(r.party)]: int(r.NATIONAL) for r in hs.itertuples()}
                out[f"{map_key}/{depth_key}"] = seats
        return {"seed": seed, "house": out}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        # hou.main writes a _top{depth} sibling of tmp's subfolders, all inside tmp, so the
        # rmtree above covers them.
        m["tw"]._cache = None


def run_draw(seed: int, lam: float, depth: int = DEPTH, observed: bool = False,
             recluster: bool = False) -> dict:
    # Only the house takes depth as an argument; the primary and president follow the
    # module DEPTH via BALLOT_DEPTH, frozen at import, so any other depth mixes contests.
    assert depth == DEPTH, "depth is frozen at import; one DEPTH per process"
    m = _pipelines(lam)
    sen, hou, prim, pres = m["sen"], m["hou"], m["prim"], m["pres"]

    tmp = Path(tempfile.mkdtemp(prefix=f"boot_{seed}_"))
    extra = (ballots_path("pure_multi"),)
    subs = None
    if observed:
        idx = np.arange(len(pd.read_csv(PROCESSED / "efa_factor_scores.csv")))
    elif recluster:
        idx, subs = _recluster_inputs(seed, tmp)
    else:
        state = pd.read_csv(PROCESSED / "efa_factor_scores.csv")["inputstate"].values
        idx = stratified_indices(state, seed=seed)

    try:
        with resampled_inputs(idx, extra_paths=extra, substitutes=subs):
            # turnout_weights caches turnout_propensity.csv in a module global on first
            # use and never invalidates it, so without this every draw after the first
            # would score its own respondents against draw #1's resampled turnout.
            m["tw"]._cache = None

            # ── senate ────────────────────────────────────────────────────────
            sen_dir = tmp / "senate"
            real_sen_out, sen.OUTPUT_DIR = sen.OUTPUT_DIR, sen_dir
            try:
                # Rank-7, matching build_senate_rank7.py and the deployed senate JSONs. This
                # truncates only the STV winnow that picks the 5 finalists; the final
                # IRV/Condorcet among those 5 is full-ranked either way. Was hardcoded to 0
                # (full ranking), which bootstrapped a different contest than the page shows.
                _quiet(sen.main, ballot_depth=depth)
                # main() reassigns its global OUTPUT_DIR to <parent>_top{depth}/senate for any
                # nonzero depth, so read back where it actually wrote rather than sen_dir.
                sen_out = sen.OUTPUT_DIR
            finally:
                sen.OUTPUT_DIR = real_sen_out
            cond = {f'{int(k):02d}': v for k, v in
                    pd.read_csv(sen_out / "senate_composition.csv")[["state_fips", "senator_code"]].values}
            irv = {f'{int(k):02d}': v for k, v in
                   pd.read_csv(sen_out / "senate_irv_composition.csv")[["state_fips", "senator_code"]].values}
            rounds = json.loads((sen_out / "senate_irv_rounds.json").read_text())
            paths = {}
            for fips, st in rounds.items():
                rs = st["rounds"]
                paths[fips] = {
                    "slate": sorted({c["code"] for c in rs[0]["candidates"]}),
                    "elim": [next((c["code"] for c in rd["candidates"] if c["eliminated"]), None)
                             for rd in rs[:-1]],
                    "rounds": rs,
                }

            # ── house ─────────────────────────────────────────────────────────
            hou_out = tmp / "house_run" / "house"
            _quiet(hou.main, output_dir=hou_out, ballot_depth=depth, label="BOOTSTRAP")
            hou_dir = (hou_out.parent.parent / (hou_out.parent.name + f"_top{depth}") / hou_out.name
                       if depth else hou_out)
            hs = pd.read_csv(hou_dir / "stv_seat_summary.csv")
            house = {CLUSTER_TO_PARTY[int(r.party)]: int(r.NATIONAL) for r in hs.itertuples()}

            # ── primary → president (president reads the primary's finalists) ─
            # Both modules rewrite their own paths when BALLOT_DEPTH is set, appending a
            # _top{depth} sibling. So always hand them the UNSUFFIXED path and let them do
            # the rewrite — pre-suffixing gets double-suffixed into a directory that does
            # not exist. Read the primary's location from the same formula it uses, and the
            # president's from its module global *after* main(), since main() reassigns it.
            prim_out = tmp / "prim"
            real_prim_out, prim.OUTPUT_DIR = prim.OUTPUT_DIR, prim_out
            try:
                _quiet(prim.main)
                prim_dir = (prim_out if not DEPTH
                            else prim_out.parent / (prim_out.name + f"_top{DEPTH}"))
            finally:
                prim.OUTPUT_DIR = real_prim_out
            pr = pd.read_csv(prim_dir / "primary_results_2028.csv")
            last = pr["winnowing_point"].unique()[-1]
            primary = sorted(pr[(pr.winnowing_point == last) & (pr.status == "surviving")]["candidate_code"])

            real_pres_out, pres.OUTPUT_DIR = pres.OUTPUT_DIR, tmp / "pres" / "irv"
            real_pres_prim, pres.PRIMARY_PATH = pres.PRIMARY_PATH, prim_out / "primary_results_2028.csv"
            try:
                _quiet(pres.main)
                pres_dir = pres.OUTPUT_DIR      # main() has rewritten this when DEPTH is set
            finally:
                pres.OUTPUT_DIR = real_pres_out
                pres.PRIMARY_PATH = real_pres_prim
            nat = pd.read_csv(pres_dir / "irv_presidential_national_2028.csv")
            won = nat[nat["winner"].astype(str).str.strip() == "True"]
            irv_pres = won["candidate_code"].iloc[0] if len(won) else ""
            cm = pd.read_csv(pres_dir / "condorcet_matchups_2028.csv")
            cond_pres = str(cm["condorcet_winner"].iloc[0]) if "condorcet_winner" in cm.columns and len(cm) else ""

        return {"seed": seed,
                "senate": {"cond": cond, "irv": irv, "paths": paths},
                "house": house,
                "primary": primary,
                "president": {"irv": irv_pres, "cond": cond_pres}}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        # Leave no resampled turnout behind: anything else in this process that touches
        # turnout_weights would otherwise read the last draw's table.
        m["tw"]._cache = None

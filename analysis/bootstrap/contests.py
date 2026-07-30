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

CLUSTER_TO_PARTY = {0: "CON", 1: "LBR", 2: "STY", 3: "NAT", 4: "LIB",
                    5: "POP", 6: "CUP", 7: "OAO", 8: "DSA", 9: "PRG"}

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
    # All four modules pick pure_multi_nosty vs pure_multi from NO_STY at import, but we
    # always resample ballots_path("pure_multi") — an ambient NO_STY=1 would read
    # unresampled nosty ballots with no error.
    os.environ.pop("NO_STY", None)
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


def run_draw(seed: int, lam: float, depth: int = DEPTH, observed: bool = False) -> dict:
    # Only the house takes depth as an argument; the primary and president follow the
    # module DEPTH via BALLOT_DEPTH, frozen at import, so any other depth mixes contests.
    assert depth == DEPTH, "depth is frozen at import; one DEPTH per process"
    m = _pipelines(lam)
    sen, hou, prim, pres = m["sen"], m["hou"], m["prim"], m["pres"]

    if observed:
        idx = np.arange(len(pd.read_csv(PROCESSED / "efa_factor_scores.csv")))
    else:
        state = pd.read_csv(PROCESSED / "efa_factor_scores.csv")["inputstate"].values
        idx = stratified_indices(state, seed=seed)

    tmp = Path(tempfile.mkdtemp(prefix=f"boot_{seed}_"))
    extra = (ballots_path("pure_multi"),)

    try:
        with resampled_inputs(idx, extra_paths=extra):
            # turnout_weights caches turnout_propensity.csv in a module global on first
            # use and never invalidates it, so without this every draw after the first
            # would score its own respondents against draw #1's resampled turnout.
            m["tw"]._cache = None

            # ── senate ────────────────────────────────────────────────────────
            sen_dir = tmp / "senate"
            real_sen_out, sen.OUTPUT_DIR = sen.OUTPUT_DIR, sen_dir
            try:
                _quiet(sen.main, ballot_depth=0)
            finally:
                sen.OUTPUT_DIR = real_sen_out
            cond = {f'{int(k):02d}': v for k, v in
                    pd.read_csv(sen_dir / "senate_composition.csv")[["state_fips", "senator_code"]].values}
            irv = {f'{int(k):02d}': v for k, v in
                   pd.read_csv(sen_dir / "senate_irv_composition.csv")[["state_fips", "senator_code"]].values}
            rounds = json.loads((sen_dir / "senate_irv_rounds.json").read_text())
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

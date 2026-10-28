#!/usr/bin/env python3
"""Per-state Senate winners for the nine-party bootstrap, and the split-delegation rule applied to them.

PROVENANCE
  Typologies: the 200 per-draw fits cached by run_k9_bootstrap.py (--work-dir/typologies/draw_NNN.csv.gz).
  No refits. The observed per-state winners come from that run's full-rebuild snapshot
  (--work-dir/observed_full/pure_multi_turnout_l5_top7/senate). Run 2026-10-28.

WHAT IT DOES
  Per draw: install the cached typology, rerun the steps the default Senate tree reads (geography, turnout
  propensity, candidate centroids, ballots), then run_pure_multi_senate.py --depth=7 at the 5% turnout gap.
  It records each state's IRV winner (senate_irv_composition.csv) and Ranked Pairs winner
  (senate_composition.csv). Each draw's state counts must equal the chamber totals already in per_draw.csv,
  which checks that the rerun reproduces the bootstrap. Rows are appended per draw; finished draws are skipped.

  Split rule, as viz/src/lib/senateDelegations.ts applies it: per state, the win share of each party
  across draws; a state sends its top two parties when the top-two gap is <= 12 points (with 1e-9 slack),
  otherwise two senators of the top party. Here the draws re-cluster the parties; in the app the
  shares come from respondent resampling of a fixed typology (analysis/bootstrap/contests.py).

USAGE
  caffeinate -ims python3 analysis/efa/exploration/k9_bootstrap/senate_per_state.py --work-dir <scratch>
"""
import argparse
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_k9_bootstrap import (BASE, DEFAULT_TREE, ENV5, HERE, OUT, PARTIES, PER_DRAW, PY,  # noqa: E402
                              TYPO, install, sh)

PER_STATE = HERE / "per_state_senate.csv"
SPLIT_THRESHOLD_PP = 12
EPS = 1e-9
RULES = {"irv": ("senate_irv_composition.csv", "sen_irv"), "rp": ("senate_composition.csv", "sen_rp")}


def read_winners(senate_dir):
    out = None
    for rule, (f, _) in RULES.items():
        df = pd.read_csv(senate_dir / f)[["state_fips", "state_abbr", "senator_party"]]
        df = df.rename(columns={"senator_party": f"{rule}_winner"})
        out = df if out is None else out.merge(df, on=["state_fips", "state_abbr"])
    assert len(out) == 51
    return out


def rerun_senate(log):
    for script in ("pipeline/make_voter_counties.py", "pipeline/pure_only/compute_turnout_propensity.py",
                   "pipeline/archive/generate_candidate_profiles.py",
                   "pipeline/pure_only/generate_pure_multi_ballots.py"):
        sh([PY, script], log)
    sh([PY, "pipeline/pure_only/run_pure_multi_senate.py", "--depth=7"], log, ENV5)


def delegations(win):
    """win: one row per draw x state. Returns per-state delegation table for one rule column."""
    rows = []
    for (fips, abbr), g in win.groupby(["state_fips", "state_abbr"]):
        share = g["winner"].value_counts() / len(g)  # ties keep first-seen order, as JS sort is stable
        top, top_p = share.index[0], share.iloc[0]
        runner, run_p = (share.index[1], share.iloc[1]) if len(share) > 1 else (None, 0.0)
        gap = (top_p - run_p) * 100 if runner else np.inf
        split = gap <= SPLIT_THRESHOLD_PP + EPS
        rows.append({"state_fips": fips, "state_abbr": abbr, "top": top, "top_pct": round(100 * top_p, 1),
                     "runner": runner, "runner_pct": round(100 * run_p, 1), "gap_pp": round(gap, 2),
                     "split": split, "seat_1": top, "seat_2": runner if split else top,
                     "tie_at_top_two": bool(len(share) > 2 and share.iloc[2] == run_p)})
    return pd.DataFrame(rows)


def report(per_state, clean):
    d = pd.read_csv(PER_DRAW)
    for label, draws in (("all 200 draws", set(d.draw)), (f"{len(clean)} cleanly matched draws", clean)):
        sub = per_state[per_state.draw.isin(draws)]
        print(f"\n=== {label} ===")
        for rule in RULES:
            dl = delegations(sub.rename(columns={f"{rule}_winner": "winner"}))
            seats = pd.concat([dl.seat_1, dl.seat_2]).value_counts()
            assert seats.sum() == 102
            gaps = sorted(dl.gap_pp[np.isfinite(dl.gap_pp)])
            print(f"[{rule}] {dl.split.sum()} states split: "
                  + ", ".join(f"{r.state_abbr} {r.top}/{r.runner} ({r.top_pct}-{r.runner_pct})"
                              for r in dl[dl.split].itertuples()))
            print(f"[{rule}] delegation seats: " + ", ".join(f"{p} {seats.get(p, 0)}" for p in PARTIES if seats.get(p, 0)))
            print(f"[{rule}] sorted top-two gaps (pp): {' '.join(f'{g:g}' for g in gaps)}"
                  f"  | unanimous states (no runner-up): {int((~np.isfinite(dl.gap_pp)).sum())}")
            if dl.tie_at_top_two.any():
                print(f"[{rule}] tie for runner-up in: {' '.join(dl[dl.tie_at_top_two].state_abbr)}")
            if label.startswith("all"):
                dl.to_csv(HERE / f"senate_delegations_{rule}.csv", index=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work-dir", type=Path, required=True)
    a = ap.parse_args()
    t0 = time.time()
    d = pd.read_csv(PER_DRAW).set_index("draw")
    done = set(pd.read_csv(PER_STATE)["draw"].astype(str)) if PER_STATE.exists() else set()

    if "observed" not in done:
        obs = read_winners(a.work_dir / "observed_full" / DEFAULT_TREE / "senate")
        obs.insert(0, "draw", "observed")
        obs.to_csv(PER_STATE, mode="a", header=not PER_STATE.exists(), index=False)

    saved = a.work_dir / "typology_before_senate_rerun.csv"
    shutil.copy(TYPO, saved)
    log = a.work_dir / "senate_rerun.log"
    for b in d.index:
        if str(b) in done:
            continue
        t1 = time.time()
        install(a.work_dir / "typologies" / f"draw_{b:03d}.csv.gz")
        log.unlink(missing_ok=True)
        rerun_senate(log)
        win = read_winners(OUT / DEFAULT_TREE / "senate")
        for rule, (_, tag) in RULES.items():
            counts = win[f"{rule}_winner"].value_counts()
            assert all(counts.get(p, 0) == d.loc[b, f"{tag}_{p}"] for p in PARTIES), \
                f"draw {b} {rule}: rerun does not match per_draw.csv"
        win.insert(0, "draw", b)
        win.to_csv(PER_STATE, mode="a", header=False, index=False)
        print(f"draw {b}: ok {time.time() - t1:.0f}s", flush=True)
    shutil.copy(saved, TYPO)

    per_state = pd.read_csv(PER_STATE)
    obs = per_state[per_state.draw == "observed"]
    per_state = per_state[per_state.draw != "observed"].assign(draw=lambda x: x.draw.astype(int))
    clean = {b for b, w, e in zip(d.index, d.weak_matches.fillna(""), d.empty_ids.fillna(""))
             if set(w.split()) <= set(e.split())}
    for rule in RULES:
        print(f"observed {rule}: " + ", ".join(f"{p} {n}" for p, n in obs[f'{rule}_winner'].value_counts().items()))
    report(per_state, clean)
    print(f"\ntotal {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()

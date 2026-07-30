#!/usr/bin/env python3
"""
ballot_model_diagnostic.py
--------------------------
How much do outcomes depend on which ballot model we use?

Two candidate-scoring models exist in the pipeline:

  A. posterior  — compute_candidate_scores_prob(): rank candidates by the voter's
     Bayesian-GMM posterior membership in that candidate's cluster. Canonical; every
     published number uses it.

  B. proximity  — compute_candidate_scores(): rank by Gaussian proximity between the
     voter's factor scores and the candidate's position in a SHARED factor metric.
     Defined in every pipeline script and never called by any of them.

They disagree because the GMM fits a full per-cluster covariance, so the posterior
ranks by Mahalanobis distance under each cluster's OWN covariance, minus a spread
penalty, plus a size prior. A large diffuse cluster therefore reaches further into the
tails than a tight one regardless of centroid distance. Model A answers a
classification question ("which cluster did this respondent come from?"); a ballot
needs a preference question ("who would this voter rank next?"). Those coincide near a
voter's own cluster and come apart deep in the ranking — which is where late IRV/STV
transfers live.

Method. Each pipeline's typology frame is widened to 20 affinity columns: 0-9 hold the
posterior, 10-19 hold proximity. PROB_COLS is widened to match, so a district/state
mask slices both models together. Candidate POOLS are built from columns 0-9 in both
runs (pool code reads range(10)), so pool composition never confounds the comparison.
Only the scorer's column offset changes, and both models feed the same
generate_ballots(), so within-party prominence ordering is identical too. The affinity
metric is the single variable.

Each contest's real main() then runs twice into a temp dir and the outputs are diffed.
No canonical output is written.

Provenance: data/processed/{efa_factor_scores,typology_cluster_assignments,
turnout_propensity}.csv, data/outputs/pure_multi/state_candidate_profiles.csv,
data/outputs/No_C7_canonical/{district_apportionment.csv,ballots_checkpoint.parquet}.
Seeded rng 42; generate_ballots is deterministic given scores.

Usage:  python3 analysis/ballot_model_diagnostic.py [--lam 0.05] [--depth 7]
"""

import argparse
import contextlib
import io
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path

# turnout_weights reads these at import time, so set them before importing pipelines.
# 0.05 == the app's default part=5 stop.
_LAM = os.environ.get("DIAG_LAMBDA", "0.05")
os.environ["TURNOUT_WEIGHT"] = "1"
os.environ["TURNOUT_LAMBDA"] = _LAM

import numpy as np   # noqa: E402
import pandas as pd  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "pipeline" / "pure_only"))

import run_pure_multi_senate as sen                 # noqa: E402
import run_pure_multi_house_stv as hou              # noqa: E402
import generate_presidential_ballots_pure as pres   # noqa: E402

FACTOR_COLS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]
PROB10 = [f"prob_cluster_{k}" for k in range(10)]
PROB20 = [f"prob_cluster_{k}" for k in range(20)]
SIGMA = sen.POSITIONAL_SIGMA
MODELS = (("posterior", 0), ("proximity", 10))


def party(code):
    return code.rsplit("_", 1)[0] if code and code != "none" else code


def tally_line(a: Counter, b: Counter) -> str:
    keys = sorted(set(a) | set(b), key=lambda k: (-a.get(k, 0), k))
    return "  ".join(f"{k}:{a.get(k, 0)}→{b.get(k, 0)}" for k in keys)


def build_proximity() -> np.ndarray:
    """(N,10) Gaussian proximity of each voter to each party's position in the shared
    factor metric — the same formula compute_candidate_scores() uses."""
    efa = pd.read_csv(BASE / "data" / "processed" / "efa_factor_scores.csv")
    typ = pd.read_csv(BASE / "data" / "processed" / "typology_cluster_assignments.csv")
    assert len(efa) == len(typ), f"row mismatch {len(efa)} vs {len(typ)}"
    X = efa[FACTOR_COLS].values.astype(np.float64)
    w = efa["commonpostweight"].values.astype(float)
    hard = typ[PROB10].values.argmax(axis=1)
    mu = np.vstack([np.average(X[hard == k], weights=w[hard == k], axis=0) for k in range(10)])
    d2 = ((X[:, None, :] - mu[None, :, :]) ** 2).sum(axis=2)
    prox = np.exp(-d2 / (2.0 * SIGMA ** 2))
    assert np.isfinite(prox).all(), "proximity overflow"
    # Exact ties would be broken by candidate index rather than preference.
    assert (np.diff(np.sort(prox, axis=1), axis=1) > 0).all(axis=1).mean() > 0.999
    return prox, mu


PROX, MU = build_proximity()


def make_scorer(offset: int):
    def scorer(prob_matrix, candidates):
        s = np.zeros((len(prob_matrix), len(candidates)))
        for j, c in enumerate(candidates):
            s[:, j] = prob_matrix[:, c["cluster"] + offset]
        return s
    return scorer


@contextlib.contextmanager
def widened(module, offset: int):
    """Widen a pipeline module's typology frame to 20 affinity columns and point its
    scorer at the requested half. Pool code reads range(10), so pools stay posterior."""
    real_read, real_cols, real_scorer = pd.read_csv, module.PROB_COLS, module.compute_candidate_scores_prob
    typ_path = str(module.TYPOLOGY_PATH)

    def patched_read(path, *a, **k):
        df = real_read(path, *a, **k)
        if str(path) == typ_path:
            assert len(df) == len(PROX), "typology/proximity misaligned"
            for j in range(10):
                df[f"prob_cluster_{10 + j}"] = PROX[:, j]
        return df

    pd.read_csv = patched_read
    module.pd.read_csv = patched_read
    module.PROB_COLS = PROB20
    module.compute_candidate_scores_prob = make_scorer(offset)
    try:
        yield
    finally:
        pd.read_csv = real_read
        module.pd.read_csv = real_read
        module.PROB_COLS = real_cols
        module.compute_candidate_scores_prob = real_scorer


def quiet(fn, *a, **k):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return fn(*a, **k)


# ── Senate ────────────────────────────────────────────────────────────────────

def senate_run(offset):
    out = Path(tempfile.mkdtemp(prefix="diag_sen_")) / "senate"
    real_dir = sen.OUTPUT_DIR
    sen.OUTPUT_DIR = out
    try:
        with widened(sen, offset):
            quiet(sen.main, ballot_depth=0)
    finally:
        sen.OUTPUT_DIR = real_dir
    cond = pd.read_csv(out / "senate_composition.csv")
    irv = pd.read_csv(out / "senate_irv_composition.csv")
    return (dict(zip(cond["state_abbr"], cond["senator_code"])),
            dict(zip(irv["state_abbr"], irv["senator_code"])))


def senate_report():
    res = {name: senate_run(off) for name, off in MODELS}
    print(f"\n### SENATE — 51 single-winner races (5 finalists via STV winnow)\n")
    for i, method in enumerate(("Condorcet", "IRV")):
        p, x = res["posterior"][i], res["proximity"][i]
        states = sorted(p)
        moved = [s for s in states if p[s] != x[s]]
        print(f"{method}: {len(moved)}/{len(states)} states change winner "
              f"({len(moved) / len(states) * 100:.0f}%)")
        print("   seats  " + tally_line(Counter(party(p[s]) for s in states),
                                        Counter(party(x[s]) for s in states)))
        if moved:
            print("   moved  " + ", ".join(f"{s} {party(p[s])}→{party(x[s])}" for s in moved))
        print()


# ── House ─────────────────────────────────────────────────────────────────────

def house_run(offset, depth):
    out = Path(tempfile.mkdtemp(prefix="diag_hou_")) / "house"
    with widened(hou, offset):
        quiet(hou.main, output_dir=out, ballot_depth=depth, label="DIAGNOSTIC")
    d = out.parent.parent / (out.parent.name + f"_top{depth}") / out.name if depth else out
    dist = pd.read_csv(d / "stv_results_by_district.csv")
    summ = pd.read_csv(d / "stv_seat_summary.csv")
    return dist, summ


def house_report(depth):
    print(f"\n### HOUSE — district STV, ballot depth {depth}\n")
    dist, summ = {}, {}
    for name, off in MODELS:
        dist[name], summ[name] = house_run(off, depth)

    key = "district_id"
    a, b = dist["posterior"], dist["proximity"]
    col = "elected" if "elected" in a.columns else a.columns[-1]
    am = dict(zip(a[key], a[col]))
    bm = dict(zip(b[key], b[col]))
    shared = [d for d in am if d in bm]
    moved = [d for d in shared if str(am[d]) != str(bm[d])]
    print(f"{len(moved)}/{len(shared)} districts change their elected set "
          f"({len(moved) / max(1, len(shared)) * 100:.0f}%)")

    pcol = "party" if "party" in summ["posterior"].columns else summ["posterior"].columns[0]
    ncol = next((c for c in ("NATIONAL", "national", "seats", "total", "n_seats")
                 if c in summ["posterior"].columns), None)
    if ncol:
        # The summary keys parties by cluster index; relabel so the tally reads in codes.
        cl2party = {v: k for k, v in sen.PARTY_CLUSTER.items()}
        lab = lambda v: cl2party.get(int(v), str(v)) if str(v).isdigit() else str(v)
        ca = Counter({lab(k): v for k, v in zip(summ["posterior"][pcol], summ["posterior"][ncol])})
        cb = Counter({lab(k): v for k, v in zip(summ["proximity"][pcol], summ["proximity"][ncol])})
        print("   seats  " + tally_line(ca, cb))
        print(f"   total  {sum(ca.values())} → {sum(cb.values())}")
    else:
        print(f"   (seat summary columns: {list(summ['posterior'].columns)})")


# ── President (indicative: general-election pool, not the full primary chain) ──

def president_report():
    print("\n### PRESIDENT — indicative national contest over the committed candidate pool")
    print("    (not the full primary→general chain)\n")
    efa = pd.read_csv(BASE / "data" / "processed" / "efa_factor_scores.csv")
    turn = pd.read_csv(BASE / "data" / "processed" / "turnout_propensity.csv")
    t = turn["turnout_cluster"].values.astype(float)
    w = efa["commonpostweight"].values.astype(float) * (t + float(_LAM) * (1.0 - t))
    typ = pd.read_csv(BASE / "data" / "processed" / "typology_cluster_assignments.csv")
    post = typ[PROB10].values.astype(np.float64)
    aff = np.hstack([post, PROX])

    cl2party = {v: k for k, v in sen.PARTY_CLUSTER.items()}
    cands = [{"code": c["code"], "cluster": c["primary"],
              "party": cl2party.get(c["primary"], "?"), "prominence": c.get("prominence", 1.0)}
             for c in pres.CANDIDATES]
    codes = [c["code"] for c in cands]
    # Candidate codes are personal initials; report the party they carry instead.
    to_party = {c["code"]: c["party"] for c in cands}

    res = {}
    for name, off in MODELS:
        b = sen.generate_ballots(make_scorer(off)(aff, cands), np.random.default_rng(42), cands)
        irv, rounds = sen.irv_rounds(b, w, codes)
        cond, _ = sen.ranked_pairs_winner(sen.build_matchups(b, w, codes), codes)
        r1 = sorted(((c["code"], c["pct"]) for c in rounds[0]["candidates"]), key=lambda kv: -kv[1])
        r1 = r1  # full round-1 field, aggregated by party below
        res[name] = {"irv": to_party.get(irv, irv), "cond": to_party.get(cond, cond),
                     "rounds": len(rounds)}
        print(f"  {name:9s} IRV={res[name]['irv']:4s}  Condorcet={res[name]['cond']:4s}  "
              f"rounds={len(rounds)}")
        agg = {}
        for c, v in r1:
            agg[to_party.get(c, c)] = agg.get(to_party.get(c, c), 0) + v
        top = sorted(agg.items(), key=lambda kv: -kv[1])[:5]
        print("            round-1 by party: " + ", ".join(f"{k} {v:.1f}%" for k, v in top))
    print(f"  IRV winner moves:       "
          f"{res['posterior']['irv'] != res['proximity']['irv']}")
    print(f"  Condorcet winner moves: "
          f"{res['posterior']['cond'] != res['proximity']['cond']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lam", type=float, default=float(_LAM))
    ap.add_argument("--depth", type=int, default=7)
    a = ap.parse_args()

    bar = "=" * 78
    print(bar)
    print("BALLOT MODEL DIAGNOSTIC   posterior (canonical)  →  proximity (never used)")
    print(f"turnout lambda={a.lam}   house ballot depth={a.depth}")
    print(bar)
    print("\nParty positions are identical in both runs; only voter→candidate affinity changes.")

    for fn, args in ((senate_report, ()), (house_report, (a.depth,)), (president_report, ())):
        try:
            fn(*args)
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  FAILED: {type(e).__name__}: {e}")
    print("\n" + bar)


if __name__ == "__main__":
    main()

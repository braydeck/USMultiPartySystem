#!/usr/bin/env python3
"""Nine-party typology: the observed election result, then a 200-draw re-clustering bootstrap.

PROVENANCE
  Factor scores: data/processed/efa_factor_scores.csv (label-coded rescore, 69a6eeb; N = 45,214).
  Party IDs: matched by caseid to the seed-61 ten-party typology (bd-corrected-scoring @ 7139c31),
  frozen as seed61_party_ids.csv in this folder. With nine clusters one of the ten IDs is empty;
  its prob_cluster column is all zeros and it fields only zero-vote candidates.
  Why K = 9: analysis/efa/exploration/k_stability/ (main checkout), outputs/k_summary.csv. At cap 9
  all five full-data seeds agree (ARI 0.999) and no cluster dissolves.
  CES 2024 validated-vote DTA (data/raw, untracked) feeds the turnout propensity step.
  Run 2026-10-28.

WHAT IT DOES
  Observed: dpgmm_clustering.py --n-components 9 --seeds 42-46 --select bound (n_init 5, full data),
    then the full rebuild (rebuild_from_typology.py steps 4-11 + build_house_partylist.py), then reads
    the app-default outputs: depth top7, turnout gap 5%, rawMulti, double (873) and triple (1,726).
  Validation: the lean per-draw pipeline below is re-run on the observed typology and must reproduce
    the full rebuild's default trees byte for byte, and the in-driver Sainte-Lague count must equal
    housePartyList.json. The bootstrap stops if either check fails.
  Bootstrap draw b = 0..199: resample the 45,214 respondents with replacement (rng seed 42 + b), fit
    DPGMM K = 9 (n_init 5, random_state b), predict hard labels and posteriors for all 45,214, match
    IDs to seed 61. Every draw uses the full observed electorate and weights; only the parties change.
    Lean pipeline: geography + turnout, candidate centroids, ballots, canonical checkpoints, then in
    parallel the two default House trees, the default Senate tree, and primary -> presidential.
    Party-list seats are counted here with build_house_partylist.sainte_lague, the same allocation
    that script writes, restricted to the default stop.
  A draw whose fit does not converge to 9 effective clusters is recorded with status fit_failed.

RESUMABLE: fits are cached as gzipped CSVs in --work-dir/typologies; each finished draw is appended to
per_draw.csv immediately, and draws already there are skipped. Deterministic end to end.

USAGE
  caffeinate -ims python3 analysis/efa/exploration/k9_bootstrap/run_k9_bootstrap.py --work-dir <scratch>
  ... --skip-observed      # resume: observed.csv and the lean-pipeline check are already done
  python3 analysis/efa/exploration/k9_bootstrap/summarize.py   # tables from observed.csv + per_draw.csv
"""
import argparse
import filecmp
import gzip
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[3]
PROC = BASE / "data" / "processed"
OUT = BASE / "data" / "outputs"
TYPO = PROC / "typology_cluster_assignments.csv"
REF = HERE / "seed61_party_ids.csv"
PER_DRAW = HERE / "per_draw.csv"
OBSERVED = HERE / "observed.csv"
PY = sys.executable
K = 9
N_DRAWS = 200
LAM = 0.05
PARTIES = ["CON", "LBR", "STY", "NAT", "LIB", "POP", "CUP", "OAO", "DSA", "PRG"]
DEFAULT_TREE = "pure_multi_turnout_l5_top7"
TRIPLE_TREE = "pure_multi_triple_turnout_l5_top7"
ENV5 = {"TURNOUT_WEIGHT": "1", "TURNOUT_LAMBDA": str(LAM)}

sys.path.insert(0, str(BASE / "pipeline"))
from build_house_partylist import sainte_lague  # noqa: E402


def sh(argv, log, env=None):
    with open(log, "a") as f:
        f.write(f"\n$ {' '.join(f'{k}={v}' for k, v in (env or {}).items())} {' '.join(map(str, argv))}\n")
        f.flush()
        r = subprocess.run(argv, cwd=BASE, env={**os.environ, **(env or {})}, stdout=f,
                           stderr=subprocess.STDOUT, text=True)
    if r.returncode:
        raise RuntimeError(f"FAILED ({r.returncode}): {' '.join(map(str, argv))}  see {log}")


def dpgmm(args, out, log, threads=None):
    env = {"OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"} if threads == 1 else None
    sh([PY, "analysis/efa/pipeline/dpgmm_clustering.py", "--n-components", str(K), "--reference", str(REF),
        "--out", str(out), *args], log, env)


def full_rebuild(log):
    sh([PY, "pipeline/rebuild_from_typology.py", "--run", "--from", "4", "--to", "11", "--log", str(log)], log)
    sh([PY, "pipeline/build_house_partylist.py"], log)


def lean_rebuild(log):
    """Only what the default trees need, in the order and with the env rebuild_from_typology uses."""
    for script in ("pipeline/make_voter_counties.py", "pipeline/pure_only/compute_turnout_propensity.py",
                   "pipeline/archive/generate_candidate_profiles.py",
                   "pipeline/pure_only/generate_pure_multi_ballots.py"):
        sh([PY, script], log)
    sh([PY, "pipeline/run_house_canonical.py"], log)
    sh([PY, "pipeline/run_house_canonical.py", "--triple"], log)
    house = "pipeline/pure_only/run_pure_multi_house_stv.py"
    chains = [
        [([house, "--depth=7"], ENV5)],
        [([house, "--triple", "--depth=7"], ENV5)],
        [(["pipeline/pure_only/run_pure_multi_senate.py", "--depth=7"], ENV5)],
        [(["pipeline/pure_only/run_pure_multi_primary.py"], {**ENV5, "BALLOT_DEPTH": "7"}),
         (["pipeline/pure_only/run_pure_multi_presidential.py"], {**ENV5, "BALLOT_DEPTH": "7"})],
    ]
    logs = [log.with_suffix(f".c{i}.log") for i in range(len(chains))]

    def run_chain(i):
        for argv, env in chains[i]:
            sh([PY, *argv], logs[i], env)

    with ThreadPoolExecutor(len(chains)) as ex:
        list(ex.map(run_chain, range(len(chains))))
    with open(log, "a") as f:
        for lg in logs:
            f.write(lg.read_text())
            lg.unlink()


def list_seats(typ, magnitude):
    """National Sainte-Lague seats at the default stop, as build_house_partylist.py counts them."""
    canon = "canonical" if magnitude == "double" else "canonical_triple"
    P = typ[[f"prob_cluster_{k}" for k in range(10)]].values.astype(np.float64)
    FC = np.zeros_like(P)
    FC[np.arange(len(P)), P.argmax(axis=1)] = 1.0
    t = pd.read_csv(PROC / "turnout_propensity.csv")["turnout_cluster"].values.astype(np.float64)
    w = typ["commonpostweight"].values.astype(np.float64) * (t + LAM * (1.0 - t))
    state = typ["inputstate"].astype(int).values
    district = pd.read_parquet(OUT / canon / "ballots_checkpoint.parquet")["district_id"].values
    app = pd.read_csv(OUT / canon / "district_apportionment.csv")
    state_V = {int(f): FC[state == f].T @ w[state == f] for f in np.unique(state)}
    total = np.zeros(10, dtype=int)
    for d, S, f in zip(app["district_id"], app["seat_count"], app["state_fips"]):
        idx = np.where(district == d)[0]
        V = FC[idx].T @ w[idx] if len(idx) else np.asarray(state_V[int(f)], dtype=np.float64)
        total += sainte_lague(V, int(S))
    return {p: int(total[k]) for k, p in enumerate(PARTIES)}


def seats_by_party(csv):
    s = pd.read_csv(csv).set_index("party")["NATIONAL"]
    return {PARTIES[k]: int(s.get(k, 0)) for k in range(10)}


def metrics(typ, ref_cluster):
    w = typ["commonpostweight"].values
    cl = typ["cluster"].values
    row = {"ari_vs_seed61": round(adjusted_rand_score(ref_cluster, cl), 4)}
    present = sorted(set(cl))
    row["empty_ids"] = " ".join(PARTIES[k] for k in range(10) if k not in present)
    for k, p in enumerate(PARTIES):
        row[f"share_{p}"] = round(100 * w[cl == k].sum() / w.sum(), 2)
        r = ref_cluster == k
        row[f"ret_{p}"] = round(100 * w[r & (cl == k)].sum() / w[r].sum(), 1)
    row["weak_matches"] = " ".join(p for p in PARTIES if row[f"ret_{p}"] < 50)

    for tree, tag, total in ((DEFAULT_TREE, "house", 873), (TRIPLE_TREE, "house3", 1726)):
        seats = seats_by_party(OUT / tree / "house" / "stv_seat_summary.csv")
        assert sum(seats.values()) == total, (tree, sum(seats.values()))
        row.update({f"{tag}_{p}": v for p, v in seats.items()})
    for mag, tag, total in (("double", "list", 873), ("triple", "list3", 1726)):
        seats = list_seats(typ, mag)
        assert sum(seats.values()) == total, (mag, sum(seats.values()))
        row.update({f"{tag}_{p}": v for p, v in seats.items()})

    tdir = OUT / DEFAULT_TREE
    prim = pd.read_csv(tdir / "primary_results_2028.csv")
    fin = prim[(prim.winnowing_point == "After_Pod_BD") & (prim.status == "surviving")]
    irv = pd.read_csv(tdir / "irv" / "irv_presidential_national_2028.csv")
    assert len(fin) == 5, f"{len(fin)} primary finalists"
    assert sorted(fin.party_code) == sorted(irv[irv["round"] == 1].candidate_code.str[:3]), "finalists != IRV field"
    row["finalists"] = " ".join(sorted(fin.party_code))
    row["pres_irv"] = irv.loc[irv.winner, "candidate_code"].str[:3].item()
    last = irv[irv["round"] == irv["round"].max()].sort_values("vote_pct", ascending=False)
    row["pres_irv_runner_up"] = last.candidate_code.iloc[1][:3]
    row["pres_irv_margin_pp"] = round(last.vote_pct.iloc[0] - last.vote_pct.iloc[1], 2)
    cond = pd.read_csv(tdir / "irv" / "condorcet_matchups_2028.csv")
    row["pres_rp"] = cond["condorcet_winner"].iloc[0][:3]

    # electoral college, IRV per state, winner-take-all; electors = state House seats + 2 (975). Not a headline.
    dist = pd.read_csv(tdir / "house" / "stv_results_by_district.csv")
    ev = dist.groupby("state_abbr")["seat_count"].sum() + 2
    assert ev.sum() == 975, ev.sum()
    states = pd.read_csv(tdir / "irv" / "irv_presidential_states_2028.csv").set_index("state_abbr")
    ec = ev.groupby(states["winner_code"].str[:3]).sum().sort_values(ascending=False)
    row["ec_irv_leader"] = ec.index[0]
    row["ec_irv_leader_ev"] = int(ec.iloc[0])

    for f, tag in (("senate_irv_composition.csv", "sen_irv"), ("senate_composition.csv", "sen_rp")):
        s = pd.read_csv(tdir / "senate" / f)["senator_party"].value_counts()
        assert s.sum() == 51, (f, s.sum())
        row.update({f"{tag}_{p}": int(s.get(p, 0)) for p in PARTIES})
    return row


def install(gz):
    with gzip.open(gz, "rb") as src, open(TYPO, "wb") as dst:
        shutil.copyfileobj(src, dst)


def fit_draw(b, tdir):
    gz = tdir / f"draw_{b:03d}.csv.gz"
    fail = tdir / f"draw_{b:03d}.failed"
    if gz.exists() or fail.exists():
        return
    csv, log = tdir / f"draw_{b:03d}.csv", tdir / f"draw_{b:03d}.log"
    log.unlink(missing_ok=True)
    try:
        dpgmm(["--seed", str(b), "--resample", str(b)], csv, log, threads=1)
    except RuntimeError:
        fail.write_text(log.read_text()[-2000:])
        return
    with open(csv, "rb") as src, gzip.open(gz.with_suffix(".tmp"), "wb") as dst:
        shutil.copyfileobj(src, dst)
    gz.with_suffix(".tmp").rename(gz)
    csv.unlink()


def observed(work, ref_cluster):
    log = work / "observed.log"
    log.unlink(missing_ok=True)
    t0 = time.time()
    dpgmm(["--seeds", "42", "43", "44", "45", "46", "--select", "bound"], TYPO, log)
    shutil.copy(TYPO, work / "observed_typology.csv")
    full_rebuild(work / "observed_rebuild.log")
    snap = work / "observed_full"
    shutil.rmtree(snap, ignore_errors=True)
    snap.mkdir()
    for tree in (DEFAULT_TREE, TRIPLE_TREE):
        shutil.copytree(OUT / tree, snap / tree)
    typ = pd.read_csv(TYPO)
    row = {"draw": "observed", **metrics(typ, ref_cluster)}
    pl = json.loads((BASE / "viz/public/data/housePartyList.json").read_text())
    for mag, tag in (("double", "list"), ("triple", "list3")):
        nat = pl["top7"][mag]["5"]["national"]["listSeats"]
        assert all(row[f"{tag}_{p}"] == nat.get(p, 0) for p in PARTIES), f"list seats != housePartyList ({mag})"
    row["sec"] = round(time.time() - t0)
    pd.DataFrame([row]).to_csv(OBSERVED, index=False)

    lean_rebuild(work / "observed_lean.log")  # must reproduce the full rebuild's default trees
    bad = [str(f.relative_to(snap)) for tree in (DEFAULT_TREE, TRIPLE_TREE) for f in (snap / tree).rglob("*")
           if f.is_file() and not filecmp.cmp(f, OUT / f.relative_to(snap), shallow=False)]
    (work / "lean_validation.txt").write_text(f"files differing between lean and full rebuild: {len(bad)}\n"
                                              + "\n".join(bad) + "\n")
    if bad:
        raise SystemExit(f"lean pipeline does not reproduce the full rebuild: {bad[:5]}")
    print(f"observed done in {row['sec']}s; lean pipeline reproduces the full rebuild", flush=True)


def bootstrap(work, ref_cluster, jobs):
    tdir = work / "typologies"
    tdir.mkdir(parents=True, exist_ok=True)
    done = set(pd.read_csv(PER_DRAW)["draw"].astype(int)) if PER_DRAW.exists() else set()
    cols = ["draw", "status", *[c for c in pd.read_csv(OBSERVED).columns if c not in ("draw", "sec")], "sec"]
    todo = [b for b in range(N_DRAWS) if b not in done]
    pool = ThreadPoolExecutor(jobs)
    futures = {b: pool.submit(fit_draw, b, tdir) for b in todo}
    for b in todo:
        t0 = time.time()
        futures[b].result()
        row = {"draw": b}
        if (tdir / f"draw_{b:03d}.failed").exists():
            row["status"] = "fit_failed"
        else:
            install(tdir / f"draw_{b:03d}.csv.gz")
            lean_rebuild(work / "draw.log")
            (work / "draw.log").unlink()
            typ = pd.read_csv(TYPO)
            row.update({"status": "ok", **metrics(typ, ref_cluster)})
        row["sec"] = round(time.time() - t0)
        pd.DataFrame([row]).reindex(columns=cols).to_csv(PER_DRAW, mode="a", header=not PER_DRAW.exists(),
                                                         index=False)
        print(f"draw {b}: {row['status']}  IRV {row.get('pres_irv')}  RP {row.get('pres_rp')}  "
              f"weak {row.get('weak_matches') or '-'}  {row['sec']}s", flush=True)
    pool.shutdown()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work-dir", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=6, help="parallel single-threaded bootstrap fits")
    ap.add_argument("--skip-observed", action="store_true", help="observed.csv and the lean check already done")
    a = ap.parse_args()
    a.work_dir.mkdir(parents=True, exist_ok=True)
    fs = pd.read_csv(PROC / "efa_factor_scores.csv", usecols=["caseid"])
    ref_cluster = fs.merge(pd.read_csv(REF), on="caseid", how="left")["party_id"].values
    t0 = time.time()
    if not a.skip_observed:
        observed(a.work_dir, ref_cluster)
    bootstrap(a.work_dir, ref_cluster, a.jobs)
    print(f"total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()

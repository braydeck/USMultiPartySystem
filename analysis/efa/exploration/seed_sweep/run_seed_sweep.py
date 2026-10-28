#!/usr/bin/env python3
"""How much do the headline election results depend on which DPGMM solution was kept?

PROVENANCE
  Typology inputs: data/processed/efa_factor_scores.csv (label-coded rescore, 69a6eeb; N = 45,214)
  and data/processed/party_id_reference.csv (the pre-rescore party IDs the Hungarian match pins to).
  Seed families: data/processed/dpgmm_seed_selection.csv (20 seeds, 42-61; seed 61 is the kept medoid).
  CES 2024 validated-vote DTA (data/raw, untracked) feeds step 4's turnout propensity.
  Branch base: bd-corrected-scoring @ 7139c31. Run 2026-10-28.

WHAT IT DOES, per seed
  1. analysis/efa/pipeline/dpgmm_clustering.py --seed N  (writes typology_cluster_assignments.csv)
  2. pipeline/rebuild_from_typology.py --run --from 4 --to 11  (geography/turnout, centroids, ballots,
     canonical + reserve checkpoints, every house tree, every senate tree, every primary/presidential tree)
  3. pipeline/build_house_partylist.py  (Sainte-Lague party-list seats)
  4. reads the app-default outputs: depth top7, turnout gap 5%, rawMulti field, i.e. the
     pure_multi_turnout_l5_top7 tree (double magnitude, 873 seats) and pure_multi_triple_turnout_l5_top7
     (triple, 1,726 seats). Bootstraps, crossover and viz payloads are not rebuilt, so the Senate here is
     the observed tree composition, not the bootstrap modal winner the Senate map renders (CLAUDE.md trap 8).

Seed 61 runs first as a control: its typology and every output it rebuilds must match the committed
files (git diff against HEAD, plus a file-by-file compare with --main-checkout for the untracked
transfer matrices); byte for byte, except parquet checkpoints, compared as tables because pyarrow
rewrites their file metadata on every write. The sweep stops if the control does not reproduce.
After the sweep, seed 61 is re-run so the worktree ends on the committed state.

Every step is deterministic (DPGMM random_state = the seed; STV runners are byte-identical across runs),
so a rerun reproduces results.csv exactly.

USAGE
  python3 analysis/efa/exploration/seed_sweep/run_seed_sweep.py --work-dir /path/to/scratch \
      [--main-checkout /path/to/main/STV] [--seeds 61 43 45 42 53 58]
"""
import argparse
import filecmp
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score

BASE = Path(__file__).resolve().parents[4]
PROC = BASE / "data" / "processed"
OUT = BASE / "data" / "outputs"
PY = sys.executable
CONTROL = 61
PARTIES = ["CON", "LBR", "STY", "NAT", "LIB", "POP", "CUP", "OAO", "DSA", "PRG"]
DEFAULT_TREE = "pure_multi_turnout_l5_top7"
TRIPLE_TREE = "pure_multi_triple_turnout_l5_top7"
REBUILT = ["data/processed", "data/outputs", "viz/public/data/housePartyList.json",
           "viz/src/data/houseDepthNational.json"]


def sh(argv, log):
    t0 = time.time()
    with open(log, "a") as f:
        f.write(f"\n$ {' '.join(map(str, argv))}\n")
        f.flush()
        r = subprocess.run(argv, cwd=BASE, stdout=f, stderr=subprocess.STDOUT, text=True)
    if r.returncode:
        raise SystemExit(f"FAILED ({r.returncode}): {' '.join(map(str, argv))}  see {log}")
    return time.time() - t0


def rebuild(seed, work):
    work.mkdir(parents=True, exist_ok=True)
    log = work / f"seed_{seed}.log"
    log.unlink(missing_ok=True)
    t = {"dpgmm": sh([PY, "analysis/efa/pipeline/dpgmm_clustering.py", "--seed", str(seed)], log)}
    t["steps_4_11"] = sh([PY, "pipeline/rebuild_from_typology.py", "--run", "--from", "4", "--to", "11",
                          "--log", str(work / f"seed_{seed}_rebuild.log")], log)
    t["partylist"] = sh([PY, "pipeline/build_house_partylist.py"], log)
    snap = work / f"seed_{seed}"
    shutil.rmtree(snap, ignore_errors=True)
    snap.mkdir(parents=True)
    shutil.copy(PROC / "typology_cluster_assignments.csv", snap)
    shutil.copy(BASE / "viz/public/data/housePartyList.json", snap)
    for tree in (DEFAULT_TREE, TRIPLE_TREE):
        shutil.copytree(OUT / tree, snap / tree)
    return t


def seats_by_party(csv):
    s = pd.read_csv(csv).set_index("party")["NATIONAL"]
    return {PARTIES[k]: int(s.get(k, 0)) for k in range(10)}


def metrics(seed, typ, ref_ids, control_typ, families):
    w = typ["commonpostweight"].values
    cl = typ["cluster"].values
    row = {"seed": seed, "lower_bound": families.loc[seed, "lower_bound"],
           "ari_vs_seed61": round(adjusted_rand_score(control_typ["cluster"], cl), 4)}
    for k, p in enumerate(PARTIES):
        row[f"share_{p}"] = round(100 * w[cl == k].sum() / w.sum(), 2)
        row[f"ret_ref_{p}"] = round(100 * w[(ref_ids == k) & (cl == k)].sum() / w[ref_ids == k].sum(), 1)
        c61 = control_typ["cluster"].values == k
        row[f"ret_61_{p}"] = round(100 * w[c61 & (cl == k)].sum() / w[c61].sum(), 1)

    for tree, tag, total in ((DEFAULT_TREE, "house", 873), (TRIPLE_TREE, "house3", 1726)):
        seats = seats_by_party(OUT / tree / "house" / "stv_seat_summary.csv")
        assert sum(seats.values()) == total, (tree, sum(seats.values()))
        row.update({f"{tag}_{p}": v for p, v in seats.items()})

    pl = json.loads((BASE / "viz/public/data/housePartyList.json").read_text())
    for mag, tag, total in (("double", "list", 873), ("triple", "list3", 1726)):
        nat = pl["top7"][mag]["5"]["national"]["listSeats"]
        assert sum(nat.values()) == total, (mag, sum(nat.values()))
        row.update({f"{tag}_{p}": int(nat.get(p, 0)) for p in PARTIES})

    tdir = OUT / DEFAULT_TREE
    prim = pd.read_csv(tdir / "primary_results_2028.csv")
    fin = prim[(prim.winnowing_point == "After_Pod_BD") & (prim.status == "surviving")]
    irv = pd.read_csv(tdir / "irv" / "irv_presidential_national_2028.csv")
    assert sorted(fin.party_code) == sorted(irv[irv["round"] == 1].candidate_code.str[:3]), "finalists != IRV field"
    row["finalists"] = " ".join(sorted(fin.party_code))
    row["pres_irv"] = irv.loc[irv.winner, "candidate_code"].str[:3].item()
    last = irv[irv["round"] == irv["round"].max()].sort_values("vote_pct", ascending=False)
    row["pres_irv_final"] = " v ".join(f"{c[:3]} {v:.1f}" for c, v in zip(last.candidate_code, last.vote_pct))
    cond = pd.read_csv(tdir / "irv" / "condorcet_matchups_2028.csv")
    row["pres_condorcet"] = cond["condorcet_winner"].iloc[0][:3]

    # electoral college, IRV per state, winner-take-all; electors = state House seats + 2 (975 total)
    dist = pd.read_csv(tdir / "house" / "stv_results_by_district.csv")
    ev = dist.groupby("state_abbr")["seat_count"].sum() + 2
    states = pd.read_csv(tdir / "irv" / "irv_presidential_states_2028.csv").set_index("state_abbr")
    assert ev.sum() == 975, ev.sum()
    ec = ev.groupby(states["winner_code"].str[:3]).sum().sort_values(ascending=False)
    row["ec_irv_leader"] = f"{ec.index[0]} {ec.iloc[0]}"
    row["ec_irv_majority"] = bool(ec.iloc[0] >= 488)

    for f, tag in (("senate_irv_composition.csv", "sen_irv"), ("senate_composition.csv", "sen_rp")):
        s = pd.read_csv(tdir / "senate" / f)["senator_party"].value_counts()
        assert s.sum() == 51, (f, s.sum())
        row.update({f"{tag}_{p}": int(s.get(p, 0)) for p in PARTIES})
    return row


def same_content(new, old):
    """Byte-identical, or for parquet the same table: pyarrow rewrites file metadata on every write."""
    if new.suffix == ".parquet":
        return pd.read_parquet(new).equals(pd.read_parquet(old))
    return filecmp.cmp(new, old, shallow=False)


def control_check(main_checkout, work):
    diff = subprocess.run(["git", "diff", "--name-only", "HEAD", "--", *REBUILT], cwd=BASE,
                          capture_output=True, text=True).stdout.split()
    real = []
    for f in diff:
        head = subprocess.run(["git", "show", f"HEAD:{f}"], cwd=BASE, capture_output=True).stdout
        tmp = work / ("head" + Path(f).suffix)
        tmp.write_bytes(head)
        if not same_content(BASE / f, tmp):
            real.append(f)
    report = [f"tracked files differing from HEAD in bytes: {len(diff)}, in content: {len(real)}", *real[:50]]
    differ = 0
    if main_checkout:
        same, bad = 0, []
        for sub in ("data/outputs", "data/processed"):
            for f in (BASE / sub).rglob("*"):
                g = main_checkout / f.relative_to(BASE)
                if f.is_file() and f.name != "rebuild_from_typology.log" and g.exists():
                    if same_content(f, g):
                        same += 1
                    else:
                        bad.append(str(f.relative_to(BASE)))
        differ = len(bad)
        report += [f"files compared with main checkout: {same + differ}, same content {same}, differing {differ}",
                   *bad[:50]]
    (work / "control_seed61.txt").write_text("\n".join(report) + "\n")
    print("\n".join(report[:5]))
    return not real and differ == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work-dir", type=Path, required=True)
    ap.add_argument("--main-checkout", type=Path)
    ap.add_argument("--seeds", type=int, nargs="+", default=[CONTROL, 43, 45, 42, 53, 58])
    a = ap.parse_args()
    a.work_dir.mkdir(parents=True, exist_ok=True)
    families = pd.read_csv(PROC / "dpgmm_seed_selection.csv").set_index("seed")
    ref = pd.read_csv(PROC / "party_id_reference.csv")
    fs = pd.read_csv(PROC / "efa_factor_scores.csv", usecols=["caseid"])
    ref_ids = fs.merge(ref, on="caseid", how="left")["party_id"].values
    control_typ = pd.read_csv(PROC / "typology_cluster_assignments.csv")  # committed = seed 61
    assert (control_typ["caseid"].values == fs["caseid"].values).all()

    rows, t_all = [], time.time()
    for seed in a.seeds:
        t = rebuild(seed, a.work_dir)
        if seed == CONTROL:
            ok = control_check(a.main_checkout, a.work_dir)
            print(f"seed {CONTROL} control reproduces committed outputs: {ok}")
            if not ok:
                raise SystemExit("control did not reproduce; stopping before the sweep")
        typ = pd.read_csv(PROC / "typology_cluster_assignments.csv")
        assert (typ["caseid"].values == fs["caseid"].values).all()
        row = metrics(seed, typ, ref_ids, control_typ, families)
        row.update({f"sec_{k}": round(v) for k, v in t.items()})
        rows.append(row)
        print(f"seed {seed}: done in {sum(t.values()):.0f}s  pres IRV {row['pres_irv']}  "
              f"Condorcet {row['pres_condorcet']}", flush=True)
        pd.DataFrame(rows).to_csv(Path(__file__).parent / "results.csv", index=False)

    if a.seeds[-1] != CONTROL:  # leave the worktree on the committed typology and outputs
        rebuild(CONTROL, a.work_dir / "restore")
        print(f"restored seed {CONTROL}; tracked files differing from HEAD: "
              f"{len(subprocess.run(['git', 'diff', '--name-only', 'HEAD', '--', *REBUILT], cwd=BASE, capture_output=True, text=True).stdout.split())}")
    print(f"total {time.time() - t_all:.0f}s")


if __name__ == "__main__":
    main()

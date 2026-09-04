#!/usr/bin/env python3
"""
build_house_reserve.py
-----------------------
Two reserve scenarios for the House, each with a ~20% per-state compensatory tier:

  1. Party list + reserve: Sainte-Laguë in each district, then Sainte-Laguë at the state
     level seeded with district results to fill the reserve.
  2. STV + reserve: STV in each district (from the pure_multi_reserve runs), then
     Sainte-Laguë at the state level seeded with STV's per-party district wins.

Both use the redrawn reserve district map. The chamber is 873 (double) / 1726 (triple).
Reserve seats are not added — they are carved from the state's total, with the remaining
~80% going to districts. Single-district states and states too small to split are unchanged.

Compensatory determination is per-state: a party's district wins count against its statewide
Sainte-Laguë entitlement over the full state delegation (district + reserve). Overhang is
absorbed inside the state's fixed total.

Provenance: data/processed/{typology_cluster_assignments,turnout_propensity}.csv,
data/outputs/No_C7_{canonical,triple}_reserve/{district_apportionment,ballots_checkpoint},
data/outputs/pure_multi{,_triple}_reserve_turnout*/house/stv_results_by_district.csv.

Output:
  viz/public/data/houseReserve.json  (lazy-loaded)
  viz/src/data/houseReserveNational.json  (national blocks, bundled)
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from stv_config import POP_PER_SEAT, POP_PER_SEAT_TRIPLE  # noqa: E402

TYPO_PATH = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
TURNOUT_PATH = BASE_DIR / "data" / "processed" / "turnout_propensity.csv"
OUT_PATH = BASE_DIR / "viz" / "public" / "data" / "houseReserve.json"
SUMMARY_PATH = BASE_DIR / "viz" / "src" / "data" / "houseReserveNational.json"

PROB_COLS = [f"prob_cluster_{k}" for k in range(10)]
CLUSTER_TO_PARTY = {0: "CON", 1: "LBR", 2: "STY", 3: "NAT", 4: "LIB",
                    5: "POP", 6: "CUP", 7: "OAO", 8: "DSA", 9: "PRG"}
PARTIES = [CLUSTER_TO_PARTY[k] for k in range(10)]
F5_ORDER = ["PRG", "DSA", "LIB", "LBR", "OAO", "STY", "CUP", "CON", "POP", "NAT"]
PARTS = [0, 5, 10, 15, 20, 25, 30]
DEPTHS = {"full": 0, "top3": 3, "top5": 5, "top7": 7, "top10": 10}

WYOMING = {
    "double": {
        "apport": BASE_DIR / "data" / "outputs" / "No_C7_canonical_reserve" / "district_apportionment.csv",
        "checkpoint": BASE_DIR / "data" / "outputs" / "No_C7_canonical_reserve" / "ballots_checkpoint.parquet",
        "stv_tree": "pure_multi_reserve",
    },
    "triple": {
        "apport": BASE_DIR / "data" / "outputs" / "No_C7_triple_reserve" / "district_apportionment.csv",
        "checkpoint": BASE_DIR / "data" / "outputs" / "No_C7_triple_reserve" / "ballots_checkpoint.parquet",
        "stv_tree": "pure_multi_triple_reserve",
    },
}


def sainte_lague(votes: np.ndarray, seats: int, seed: np.ndarray = None) -> np.ndarray:
    s = seed.copy() if seed is not None else np.zeros(10, dtype=int)
    added = np.zeros(10, dtype=int)
    for _ in range(int(seats)):
        q = np.where(votes > 0, votes / (2 * s + 1), -1.0)
        if q.max() <= 0:
            break
        k = int(q.argmax())
        s[k] += 1
        added[k] += 1
    return added


def gallagher(vs, ss):
    return float(np.sqrt(0.5 * np.sum((vs * 100 - ss * 100) ** 2)))


def as_party_map(vec, cast=float, rnd=None):
    out = {}
    for k in range(10):
        v = cast(vec[k])
        if rnd is not None:
            v = round(v, rnd)
        if v:
            out[CLUSTER_TO_PARTY[k]] = v
    return out


def expand_seats(vec):
    out = []
    for p in F5_ORDER:
        k = PARTIES.index(p)
        out.extend([p] * int(vec[k]))
    return out


def stv_tree_dir(tree, part, depth):
    suffix = "_turnout" + (f"_l{part}" if part > 0 else "") + (f"_top{depth}" if depth else "")
    return BASE_DIR / "data" / "outputs" / (tree + suffix) / "house"


def load_stv_seats(csv_path):
    p2k = {v: k for k, v in enumerate(PARTIES)}
    df = pd.read_csv(csv_path)
    ecols = [c for c in df.columns if c.startswith("elected_")]
    out = {}
    for _, r in df.iterrows():
        counts = np.zeros(10, dtype=int)
        for c in ecols:
            code = r[c]
            if isinstance(code, str):
                party = code.split("_")[0] if "_" in code else code
                if party in p2k:
                    counts[p2k[party]] += 1
        out[r["district_id"]] = counts
    return out


def main():
    typ = pd.read_csv(TYPO_PATH)
    N = len(typ)
    P = typ[PROB_COLS].values.astype(np.float64)
    fc = P.argmax(axis=1)
    FC = np.zeros_like(P)
    FC[np.arange(N), fc] = 1.0
    cpw = typ["commonpostweight"].values.astype(np.float64)
    inputstate = typ["inputstate"].astype(int).values
    tp = pd.read_csv(TURNOUT_PATH)
    assert len(tp) == N
    t = tp["turnout_cluster"].values.astype(np.float64)

    out: dict = {}
    summary: dict = {}

    for dkey, depth in DEPTHS.items():
        out[dkey] = {}
        for wyo, cfg in WYOMING.items():
            app = pd.read_csv(cfg["apport"])
            chk = pd.read_parquet(cfg["checkpoint"])
            assert len(chk) == N
            district = chk["district_id"].values
            seat_of = dict(zip(app["district_id"], app["seat_count"]))
            reserve_of = dict(zip(app["district_id"], app["reserve"]))
            state_of = dict(zip(app["district_id"], app["state_fips"]))
            district_ids = list(app["district_id"])
            idx_by_dist = {d: np.where(district == d)[0] for d in district_ids}

            # Per-state structure
            by_state_dists: dict = {}
            state_reserve: dict = {}
            for d in district_ids:
                f = int(state_of[d])
                by_state_dists.setdefault(f, []).append(d)
                state_reserve[f] = int(reserve_of[d])
            state_total = {f: sum(seat_of[d] for d in ds) + state_reserve[f]
                           for f, ds in by_state_dists.items()}

            out[dkey][wyo] = {}
            for part in PARTS:
                lam = part / 100.0
                w = cpw * (t + lam * (1.0 - t))
                W = w.sum()

                stv_csv = stv_tree_dir(cfg["stv_tree"], part, depth) / "stv_results_by_district.csv"
                stv_seats = load_stv_seats(stv_csv) if stv_csv.exists() else {}

                # Ballot-path unrepresented from the STV representation CSV.
                rep_csv = stv_tree_dir(cfg["stv_tree"], part, depth) / "stv_representation_by_district.csv"
                if rep_csv.exists():
                    rep = pd.read_csv(rep_csv)
                    stv_ballot_unrep = float(rep["unrep_weight"].sum() / rep["vote_weight"].sum() * 100)
                    stv_ballot_unrep = round(stv_ballot_unrep, 2)
                else:
                    stv_ballot_unrep = None

                state_V = {f: FC[inputstate == f].T @ w[inputstate == f]
                           for f in by_state_dists}

                # --- Per-district: party list (SL) allocation ---
                list_by_dist = {}
                for d in district_ids:
                    idx = idx_by_dist[d]
                    S = int(seat_of[d])
                    if len(idx) == 0:
                        V = np.array(state_V[int(state_of[d])], dtype=np.float64)
                    else:
                        V = FC[idx].T @ w[idx]
                    list_by_dist[d] = sainte_lague(V, S)

                # --- State-level compensatory allocation ---
                nat = {sys: np.zeros(10, int) for sys in ("listDist", "listRes", "stvDist", "stvRes")}
                nat_scov = {sys: 0.0 for sys in ("listDist", "listState", "stvDist", "stvState")}
                nat_shut = {sys: 0.0 for sys in ("list", "stv", "listRes", "stvRes")}
                nat_w = 0.0
                by_state_out = {}

                for f, dists in by_state_dists.items():
                    m = inputstate == f
                    V = state_V[f]
                    R = state_reserve[f]
                    T = state_total[f]
                    sw = w[m]
                    Ps = P[m]
                    fcs = fc[m]

                    # District tier results
                    list_won = np.zeros(10, int)
                    stv_won = np.zeros(10, int)
                    for d in dists:
                        list_won += list_by_dist[d]
                        stv_won += stv_seats.get(d, np.zeros(10, int))

                    # Compensatory reserve: SL seeded with district wins
                    if R > 0:
                        list_res = sainte_lague(V, R, seed=list_won)
                        stv_res = sainte_lague(V, R, seed=stv_won)
                    else:
                        list_res = np.zeros(10, int)
                        stv_res = np.zeros(10, int)

                    list_total = list_won + list_res
                    stv_total = stv_won + stv_res

                    # Accumulate nationals
                    nat["listDist"] += list_won
                    nat["listRes"] += list_res
                    nat["stvDist"] += stv_won
                    nat["stvRes"] += stv_res

                    # Shut-out: first-choice party has no seat in the state
                    nat_shut["listRes"] += float(sw[list_total[fcs] == 0].sum())
                    nat_shut["stvRes"] += float(sw[stv_total[fcs] == 0].sum())
                    # District-only shut-out for comparison
                    nat_shut["list"] += float(sw[list_won[fcs] == 0].sum())
                    nat_shut["stv"] += float(sw[stv_won[fcs] == 0].sum())

                    # Soft coverage
                    for sys_name, seats_vec in (("listDist", list_won), ("stvDist", stv_won)):
                        seated = seats_vec > 0
                        for d in dists:
                            idx = idx_by_dist[d]
                            if len(idx) == 0:
                                continue
                            d_seated = list_by_dist[d] > 0 if "list" in sys_name else stv_seats.get(d, np.zeros(10, int)) > 0
                            nat_scov[sys_name] += float((P[idx][:, d_seated].sum(1) * w[idx]).sum())
                    for sys_name, seats_vec in (("listState", list_total), ("stvState", stv_total)):
                        seated = seats_vec > 0
                        nat_scov[sys_name] += float((Ps[:, seated].sum(1) * sw).sum())

                    nat_w += float(sw.sum())

                    abbr = app.loc[app["state_fips"] == f, "state_abbr"].iloc[0]
                    by_state_out[f"{f:02d}"] = {
                        "abbr": abbr,
                        "totalSeats": T,
                        "districtSeats": int(list_won.sum()),
                        "reserveSeats": R,
                        "voteShare": as_party_map(V / V.sum() * 100, rnd=2),
                        "listSeats": as_party_map(list_total, cast=int),
                        "listDistrictSeats": as_party_map(list_won, cast=int),
                        "listReserveSeats": as_party_map(list_res, cast=int),
                        "stvSeats": as_party_map(stv_total, cast=int),
                        "stvDistrictSeats": as_party_map(stv_won, cast=int),
                        "stvReserveSeats": as_party_map(stv_res, cast=int),
                        "softCoverage": {
                            "listState": round(float((Ps[:, list_total > 0].sum(1) * sw).sum()) / float(sw.sum()) * 100, 2),
                            "stvState": round(float((Ps[:, stv_total > 0].sum(1) * sw).sum()) / float(sw.sum()) * 100, 2),
                        },
                    }

                # National aggregation
                vs_vec = sum(state_V.values())
                vs = vs_vec / vs_vec.sum()
                list_all = nat["listDist"] + nat["listRes"]
                stv_all = nat["stvDist"] + nat["stvRes"]
                total_seats = int(list_all.sum())

                national = {
                    "totalSeats": total_seats,
                    "districtSeats": int(nat["listDist"].sum()),
                    "reserveSeats": int(nat["listRes"].sum()),
                    "voteShare": as_party_map(vs * 100, rnd=2),
                    "list": {
                        "seats": as_party_map(list_all, cast=int),
                        "districtSeats": as_party_map(nat["listDist"], cast=int),
                        "reserveSeats": as_party_map(nat["listRes"], cast=int),
                        "elected": expand_seats(list_all),
                        "gallagher": round(gallagher(vs, list_all / total_seats), 2),
                        "gallagherDistrictOnly": round(gallagher(vs, nat["listDist"] / max(1, int(nat["listDist"].sum()))), 2),
                        "unrepresented": round(nat_shut["listRes"] / nat_w * 100, 2),
                        "unrepDistrictOnly": round(nat_shut["list"] / nat_w * 100, 2),
                        "softCoverage": {
                            "district": round(nat_scov["listDist"] / nat_w * 100, 2),
                            "state": round(nat_scov["listState"] / nat_w * 100, 2),
                        },
                    },
                    "stv": {
                        "seats": as_party_map(stv_all, cast=int),
                        "districtSeats": as_party_map(nat["stvDist"], cast=int),
                        "reserveSeats": as_party_map(nat["stvRes"], cast=int),
                        "elected": expand_seats(stv_all),
                        "gallagher": round(gallagher(vs, stv_all / total_seats), 2),
                        "gallagherDistrictOnly": round(gallagher(vs, nat["stvDist"] / max(1, int(nat["stvDist"].sum()))), 2),
                        "unrepresented": round(nat_shut["stvRes"] / nat_w * 100, 2),
                        "unrepDistrictOnly": round(nat_shut["stv"] / nat_w * 100, 2),
                        # Ballot-path: did any of your ranked choices win via STV transfers.
                        # This is the metric the base STV view uses ("nobody they voted for won
                        # a seat"), computed from the STV representation CSV.
                        "ballotPathUnrep": stv_ballot_unrep,
                        "softCoverage": {
                            "district": round(nat_scov["stvDist"] / nat_w * 100, 2),
                            "state": round(nat_scov["stvState"] / nat_w * 100, 2),
                        },
                    },
                }

                out[dkey][wyo][str(part)] = {
                    "national": national,
                    "byState": by_state_out,
                }
                # Strip elected[] from the summary — it's 80% of the payload and only
                # needed by the per-state view, which reads from the lazy bundle.
                summary_nat = json.loads(json.dumps(national))
                for sys_key in ("list", "stv"):
                    summary_nat[sys_key].pop("elected", None)
                summary.setdefault(dkey, {}).setdefault(wyo, {})[str(part)] = summary_nat

            print(f"  [{dkey}] {wyo}: {len(district_ids)} districts × {len(PARTS)} turnout stops")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, separators=(",", ":")))
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, separators=(",", ":"), sort_keys=True))
    mb = OUT_PATH.stat().st_size / 1e6
    kb = SUMMARY_PATH.stat().st_size / 1024
    print(f"\nWrote {OUT_PATH}  ({mb:.2f} MB)")
    print(f"Wrote {SUMMARY_PATH}  ({kb:.0f} KB)")

    # Print headline comparison
    for wyo in ("double", "triple"):
        n = summary["top7"][wyo]["5"]
        print(f"\n[{wyo} top7 λ=5%] {n['totalSeats']} seats "
              f"({n['districtSeats']} district + {n['reserveSeats']} reserve)")
        for sys in ("list", "stv"):
            s = n[sys]
            print(f"  {sys:5s}: Gallagher {s['gallagher']:5.2f} (district {s['gallagherDistrictOnly']:5.2f}) "
                  f"| unrep {s['unrepresented']:5.2f}% (district {s['unrepDistrictOnly']:5.2f}%) "
                  f"| coverage district {s['softCoverage']['district']:.1f}% state {s['softCoverage']['state']:.1f}%")


if __name__ == "__main__":
    sys.exit(main())

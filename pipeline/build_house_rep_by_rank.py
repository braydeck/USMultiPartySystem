#!/usr/bin/env python3
"""
build_house_rep_by_rank.py
--------------------------
For each voter, the highest-ranked party on their ballot that holds a seat representing them,
under STV, party list and MMP. Feeds the House tab's "Represented by choice" chart.

A seat represents a voter when it is in their district, or in their state's reserve tier (the
~20% reserve scenarios) or top-off tier (MMP). Party list and MMP count one choice, so a voter
is represented at rank 1 or not at all. STV ballots rank candidates in party slates, so a voter
can be represented by their 2nd, 3rd or later party. When the highest-ranked seated party holds
only state-tier seats in the voter's scope, the voter counts as represented by the state tier,
so the chart can show how much representation the reserve and top-off seats supply.

Ballots are rebuilt rather than stored. With every party fielding at least one candidate per
district, a voter's party order is the argsort of their cluster posterior, and each party's
slate length comes from the runner's own n_candidates_for_district() on the district's
population-weighted shares. A depth-N ballot reaches a party when that party's first slot is
inside the top N. Checked against the runner: the rebuilt ballots reproduce its per-district
nonfirst_weight and unrep_weight exactly.

Voters are attributed to districts the way each system counted them: STV by the runner's
assign_voter_districts(), party list by the checkpoint (as build_house_partylist.py and
build_house_reserve.py allocate), MMP by the real 119th district (cd119).

Seats come from the payloads the app draws, so the chart agrees with the maps:
viz/public/data/{housePartyList,houseReserve,houseMmp}.json. STV slate lengths come from
data/outputs/canonical*/district_apportionment.csv and the processed county-to-district files.
Weights are commonpostweight x the turnout multiplier at each gap stop, as in the seat builders.

Output: viz/public/data/houseRepByRank.json (lazy-loaded). Each cell is
{party: [pct by a district seat at rank 1..10, pct by a state-tier seat only, pct unrepresented]}
over that party's first-choice voters, plus "ALL" over every voter.
"""

import contextlib
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent / "pure_only"))
from run_pure_multi_house_stv import (  # noqa: E402
    MIN_RESPONDENTS, assign_voter_districts, n_candidates_for_district)

PROCESSED = BASE_DIR / "data" / "processed"
OUTPUTS = BASE_DIR / "data" / "outputs"
VIZ_DATA = BASE_DIR / "viz" / "public" / "data"
OUT_PATH = VIZ_DATA / "houseRepByRank.json"

CLUSTER_TO_PARTY = {0: "CON", 1: "LBR", 2: "STY", 3: "NAT", 4: "LIB",
                    5: "POP", 6: "CUP", 7: "OAO", 8: "DSA", 9: "PRG"}
PARTIES = [CLUSTER_TO_PARTY[k] for k in range(10)]
PARTS = [0, 5, 10, 15, 20, 25, 30]
DEPTHS = {"full": 0, "top3": 3, "top5": 5, "top7": 7, "top10": 10}

# (wyoming, reserve) -> the district map STV and party list ran on.
MAPS = {
    ("double", "off"): ("canonical", "county_to_district.csv"),
    ("triple", "off"): ("canonical_triple", "county_to_district_triple.csv"),
    ("double", "on"): ("canonical_reserve", "county_to_district_reserve.csv"),
    ("triple", "on"): ("canonical_triple_reserve", "county_to_district_triple_reserve.csv"),
}


def seat_matrix(elected_by_key: dict, keys: np.ndarray) -> np.ndarray:
    """(N, 10) seat counts each voter sees, from {district or state key: [party, ...]}."""
    lookup = {}
    for k, parties in elected_by_key.items():
        v = np.zeros(10, int)
        for p in parties:
            v[PARTIES.index(p)] += 1
        lookup[k] = v
    zero = np.zeros(10, int)
    return np.stack([lookup.get(k, zero) for k in keys])


def first_seated_rank(order: np.ndarray, reached: np.ndarray, seats: np.ndarray) -> np.ndarray:
    """1-based party rank of the first reached party holding a seat; 0 when none does."""
    seated_in_order = np.take_along_axis(seats, order, axis=1) > 0
    hit = seated_in_order & reached
    return np.where(hit.any(axis=1), hit.argmax(axis=1) + 1, 0)


def state_only(rank: np.ndarray, order: np.ndarray, district_seats: np.ndarray) -> np.ndarray:
    """True where the party at `rank` holds no seat in the voter's district, only state-tier ones."""
    idx = order[np.arange(len(rank)), np.maximum(rank, 1) - 1]
    return (rank > 0) & (district_seats[np.arange(len(rank)), idx] == 0)


def tabulate(rank: np.ndarray, via_state: np.ndarray, w: np.ndarray, fc: np.ndarray) -> dict:
    """Percent of each party's first-choice voters (and of all voters) by district-seat rank, then
    state tier only, then unrepresented."""
    def row(m):
        tot = w[m].sum()
        cells = [w[m & (rank == r) & ~via_state].sum() / tot * 100 for r in range(1, 11)]
        cells += [w[m & via_state].sum() / tot * 100, w[m & (rank == 0)].sum() / tot * 100]
        return [round(float(c), 2) for c in cells]
    out = {CLUSTER_TO_PARTY[k]: row(fc == k) for k in range(10)}
    out["ALL"] = row(np.ones_like(fc, dtype=bool))
    return out


def main():
    typ = pd.read_csv(PROCESSED / "typology_cluster_assignments.csv")
    N = len(typ)
    P = typ[[f"prob_cluster_{k}" for k in range(10)]].values.astype(np.float64)
    fc = P.argmax(axis=1)
    order = np.argsort(-P, axis=1, kind="stable")
    cpw = typ["commonpostweight"].values.astype(np.float64)
    inputstate = typ["inputstate"].astype(int).values
    state_key = np.array([f"{s:02d}" for s in inputstate])
    tp = pd.read_csv(PROCESSED / "turnout_propensity.csv")
    assert len(tp) == N
    t = tp["turnout_cluster"].values.astype(np.float64)
    cds = pd.read_csv(PROCESSED / "voter_county_fips.csv")
    assert len(cds) == N
    cd_key = np.array([f"{s:02d}-{int(d):02d}" for s, d in zip(inputstate, cds["cd119"])])

    pl = json.loads((VIZ_DATA / "housePartyList.json").read_text())
    rs = json.loads((VIZ_DATA / "houseReserve.json").read_text())
    mm = json.loads((VIZ_DATA / "houseMmp.json").read_text())

    out = {"ranks": 10, "stv": {}, "list": {}, "mmp": {}}

    for (wyo, reserve), (canon, cdist) in MAPS.items():
        app = pd.read_csv(OUTPUTS / canon / "district_apportionment.csv")
        with contextlib.redirect_stdout(io.StringIO()):
            stv_dist = assign_voter_districts(app, PROCESSED / cdist,
                                              OUTPUTS / canon / "ballots_checkpoint.parquet", N)
        list_dist = pd.read_parquet(OUTPUTS / canon / "ballots_checkpoint.parquet")["district_id"].values

        # Slate lengths per district, on the runner's pool: population-weighted shares, with the
        # whole state standing in for a district below MIN_RESPONDENTS.
        slate = {}
        for d, f, S in zip(app["district_id"], app["state_fips"], app["seat_count"]):
            m = stv_dist == d
            if m.sum() < MIN_RESPONDENTS:
                m = inputstate == int(f)
            sh = np.average(P[m], weights=cpw[m], axis=0)
            slate[d] = np.array([n_candidates_for_district(float(sh[c]), int(S)) for c in range(10)])
        k_voter = np.stack([slate.get(d, np.ones(10, int)) for d in stv_dist])
        k_in_order = np.take_along_axis(k_voter, order, axis=1)
        slot_start = np.cumsum(k_in_order, axis=1) - k_in_order
        unassigned = int((~np.isin(stv_dist, app["district_id"])).sum())
        if unassigned:
            print(f"  {wyo}/{reserve}: {unassigned} voters outside every district count as unrepresented")

        for dkey, depth in DEPTHS.items():
            reached = slot_start < depth if depth else np.ones_like(slot_start, dtype=bool)
            for part in PARTS:
                w = cpw * (t + part / 100.0 * (1.0 - t))
                if reserve == "off":
                    dists = pl[dkey][wyo][str(part)]["districts"]
                    stv_el = {r["districtId"]: r["stvElected"] for ds in dists.values() for r in ds}
                    list_el = {r["districtId"]: r["listElected"] for ds in dists.values() for r in ds}
                    stv_dseats = seat_matrix(stv_el, stv_dist)
                    list_dseats = seat_matrix(list_el, list_dist)
                    stv_seats, list_seats = stv_dseats, list_dseats
                else:
                    dists = rs[dkey][wyo][str(part)]["districts"]
                    flat = {d: r for st in dists.values() for d, r in st.items()}
                    res_stv = {d[:2]: r["stvElected"] for d, r in flat.items() if d.endswith("-RES")}
                    res_list = {d[:2]: r["listElected"] for d, r in flat.items() if d.endswith("-RES")}
                    stv_dseats = seat_matrix({d: r["stvElected"] for d, r in flat.items()}, stv_dist)
                    list_dseats = seat_matrix({d: r["listElected"] for d, r in flat.items()}, list_dist)
                    stv_seats = stv_dseats + seat_matrix(res_stv, state_key)
                    list_seats = list_dseats + seat_matrix(res_list, state_key)

                stv_rank = first_seated_rank(order, reached, stv_seats)
                out["stv"].setdefault(dkey, {}).setdefault(wyo, {}).setdefault(str(part), {})[reserve] = \
                    tabulate(stv_rank, state_only(stv_rank, order, stv_dseats), w, fc)
                if dkey == "full":
                    list_rank = np.where(list_seats[np.arange(N), fc] > 0, 1, 0)
                    out["list"].setdefault(wyo, {}).setdefault(str(part), {})[reserve] = \
                        tabulate(list_rank, state_only(list_rank, order, list_dseats), w, fc)

    for wyo in ("double", "triple"):
        for part in PARTS:
            w = cpw * (t + part / 100.0 * (1.0 - t))
            cell = mm[wyo][str(part)]
            winners = {d: [r["winner"]] for st in cell["districts"].values() for d, r in st.items()}
            topoff = {f: [p for p, n in s["topoffSeats"].items() for _ in range(n)]
                      for f, s in cell["byState"].items()}
            dseats = seat_matrix(winners, cd_key)
            seats = dseats + seat_matrix(topoff, state_key)
            mmp_rank = np.where(seats[np.arange(N), fc] > 0, 1, 0)
            out["mmp"].setdefault(wyo, {})[str(part)] = \
                tabulate(mmp_rank, state_only(mmp_rank, order, dseats), w, fc)

    OUT_PATH.write_text(json.dumps(out, separators=(",", ":")))
    print(f"wrote {OUT_PATH.relative_to(BASE_DIR)}  ({OUT_PATH.stat().st_size / 1024:.0f} KB)")
    for reserve in ("off", "on"):
        s = out["stv"]["top7"]["double"]["5"][reserve]["ALL"]
        li = out["list"]["double"]["5"][reserve]["ALL"]
        print(f"  top7 double 5% reserve {reserve}: STV 1st {s[0]}  2nd {s[1]}  3rd {s[2]}  "
              f"later {round(sum(s[3:10]), 2)}  state {s[10]}  none {s[11]}  |  "
              f"list 1st {li[0]}  state {li[10]}  none {li[11]}")
    m = out["mmp"]["double"]["5"]["ALL"]
    print(f"  MMP double 5%: 1st {m[0]}  state {m[10]}  none {m[11]}")


if __name__ == "__main__":
    main()

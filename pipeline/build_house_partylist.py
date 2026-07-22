#!/usr/bin/env python3
"""
build_house_partylist.py
------------------------
Party-list PR comparison for the House, computed on the SAME multi-member districts
as the STV run (Drutman-style district sizes). Party-list is party-centric, so there
are no factor-deviation candidates — this uses the pure-party (rawMulti) party set.

Party vote share per district = soft cluster-posterior share (identical to how
houseStateMap popShares are defined — validated below), aggregated over the voters
assigned to that district, weighted by commonpostweight × turnout multiplier.

For each district we compute:
  - Hare quota + largest-remainder seat allocation (party list).
  - STV seats (read from the matching pure_multi[_triple]_turnout[_lNN] run).
  - Wasted votes, computed the same way conceptually for both systems:
      * list = lost (votes for zero-seat parties) + surplus (votes above a party's
        seats × Hare quota) — i.e. votes that elected no one.
      * STV = one Droop quota per district (V/(S+1)); STV's transfers rescue every
        below-quota / surplus vote down to this structural floor, so it is the
        minimum any Droop-quota STV strands. (With full-ranking ballots exhaustion ≈ 0.)
  - Gallagher disproportionality index for each system.

Configs: {double, triple} × turnout-gap λ ∈ {0,.05,.10,.15,.20,.25,.30} (14 total),
matching the House tab's wyoming × part axes.

Output: viz/public/data/housePartyList.json  (lazy-loaded when the list flip is on).
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent.parent
TYPO_PATH = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
TURNOUT_PATH = BASE_DIR / "data" / "processed" / "turnout_propensity.csv"
HSM_BASE = BASE_DIR / "viz" / "src" / "data" / "houseStateMap.json"
OUT_PATH = BASE_DIR / "viz" / "public" / "data" / "housePartyList.json"

PROB_COLS = [f"prob_cluster_{k}" for k in range(10)]
CLUSTER_TO_PARTY = {0: "CON", 1: "LBR", 2: "STY", 3: "NAT", 4: "LIB",
                    5: "POP", 6: "CUP", 7: "OAO", 8: "DSA", 9: "PRG"}
PARTIES = [CLUSTER_TO_PARTY[k] for k in range(10)]
F5_ORDER = ["PRG", "DSA", "LIB", "LBR", "OAO", "STY", "CUP", "CON", "POP", "NAT"]
PARTS = [0, 5, 10, 15, 20, 25, 30]

WYOMING = {
    "double": {
        "checkpoint": BASE_DIR / "data" / "outputs" / "No_C7_canonical" / "ballots_checkpoint.parquet",
        "apport": BASE_DIR / "data" / "outputs" / "No_C7_canonical" / "district_apportionment.csv",
        "stv_tree": "pure_multi",
    },
    "triple": {
        "checkpoint": BASE_DIR / "data" / "outputs" / "No_C7_triple" / "ballots_checkpoint.parquet",
        "apport": BASE_DIR / "data" / "outputs" / "No_C7_triple" / "district_apportionment.csv",
        "stv_tree": "pure_multi_triple",
    },
}


def _tree_dir(tree: str, part: int, depth: int) -> Path:
    suffix = "_turnout" + (f"_l{part}" if part > 0 else "") + (f"_top{depth}" if depth else "")
    return BASE_DIR / "data" / "outputs" / (tree + suffix) / "house"


def stv_csv(tree: str, part: int, depth: int = 0) -> Path:
    return _tree_dir(tree, part, depth) / "stv_results_by_district.csv"


def rep_csv(tree: str, part: int, depth: int = 0) -> Path:
    return _tree_dir(tree, part, depth) / "stv_representation_by_district.csv"


def hare_lr(votes: np.ndarray, seats: int) -> np.ndarray:
    """Hare quota + largest remainder. votes: (10,) weighted party votes. Returns (10,) int seats."""
    total = votes.sum()
    if total <= 0 or seats <= 0:
        return np.zeros(10, dtype=int)
    exact = votes / total * seats
    base = np.floor(exact).astype(int)
    rem = seats - int(base.sum())
    if rem > 0:
        order = np.argsort(-(exact - base))
        for i in range(rem):
            base[order[i]] += 1
    return base


def gallagher(vote_share: np.ndarray, seat_share: np.ndarray) -> float:
    """Least-squares index, 0–100."""
    return float(np.sqrt(0.5 * np.sum((vote_share - seat_share) ** 2)) * 100)


def expand_seats(seats_by_cluster: np.ndarray) -> list:
    """Cluster seat counts -> flat party-code list, F5 order."""
    out = []
    for p in F5_ORDER:
        k = PARTIES.index(p)
        out.extend([p] * int(seats_by_cluster[k]))
    return out


def stv_seats_by_district(csv_path: Path) -> dict:
    """district_id -> (10,) cluster seat counts from a stv_results_by_district.csv."""
    df = pd.read_csv(csv_path)
    ecols = [c for c in df.columns if c.startswith("elected_")]
    p2k = {v: k for k, v in CLUSTER_TO_PARTY.items()}
    out = {}
    for _, r in df.iterrows():
        counts = np.zeros(10, dtype=int)
        for c in ecols:
            code = r[c]
            if isinstance(code, str) and code in p2k:
                counts[p2k[code]] += 1
        out[r["district_id"]] = counts
    return out


def as_party_map(vec, cast=float, rnd=None):
    out = {}
    for k in range(10):
        v = cast(vec[k])
        if rnd is not None:
            v = round(v, rnd)
        if v:
            out[CLUSTER_TO_PARTY[k]] = v
    return out


def main():
    typ = pd.read_csv(TYPO_PATH)
    N = len(typ)
    P = typ[PROB_COLS].values.astype(np.float64)
    fc = P.argmax(axis=1)   # each voter's first-choice party (cluster index) — config-independent
    cpw = typ["commonpostweight"].values.astype(np.float64)
    inputstate = typ["inputstate"].astype(int).values
    tp = pd.read_csv(TURNOUT_PATH)
    assert len(tp) == N, "turnout rows misaligned"
    t = tp["turnout_cluster"].values.astype(np.float64)

    # Ballot depth: 'full' = exhaustive ranking, 'topN' = voters rank their top N.
    # Party-list results are depth-invariant (list uses first choices only); only STV
    # seats + representation change, read from the *_topN output trees.
    DEPTHS = {"full": 0, "top3": 3, "top5": 5, "top7": 7, "top10": 10}

    out = {dk: {} for dk in DEPTHS}
    for dkey, depth in DEPTHS.items():
      for wyo, cfg in WYOMING.items():
        chk = pd.read_parquet(cfg["checkpoint"])
        assert len(chk) == N, f"{wyo} checkpoint misaligned ({len(chk)} != {N})"
        district = chk["district_id"].values
        app = pd.read_csv(cfg["apport"])
        seat_of = dict(zip(app["district_id"], app["seat_count"]))
        tier_of = dict(zip(app["district_id"], app["density_tier"]))
        state_of = dict(zip(app["district_id"], app["state_fips"]))
        district_ids = list(app["district_id"])
        idx_by_dist = {d: np.where(district == d)[0] for d in district_ids}

        out[dkey][wyo] = {}
        for part in PARTS:
            lam = part / 100.0
            w = cpw * (t + lam * (1.0 - t))
            stv_seats = stv_seats_by_district(stv_csv(cfg["stv_tree"], part, depth))
            rep = pd.read_csv(rep_csv(cfg["stv_tree"], part, depth))
            rep_by_d = {r.district_id: (r.vote_weight, r.nonfirst_weight, r.unrep_weight,
                                        r.below_quota_seats)
                        for r in rep.itertuples()}
            # State-level vote vector — fallback for districts with no assigned respondents
            # (e.g. AZ 04-03), so their seats are still allocated rather than dropped.
            state_V = {int(f): P[inputstate == f].T @ w[inputstate == f] for f in np.unique(inputstate)}

            districts_by_state: dict = {}
            for d in district_ids:
                idx = idx_by_dist[d]
                S = int(seat_of[d])
                if len(idx) == 0:                        # no respondents — use state shares
                    V = np.array(state_V[int(state_of[d])], dtype=np.float64)
                else:
                    V = P[idx].T @ w[idx]                 # (10,) weighted party votes
                totV = float(V.sum())
                listc = hare_lr(V, S)
                stvc = stv_seats.get(d, np.zeros(10, dtype=int))
                q_hare = totV / S if S else 0.0
                # list wasted: lost (0-seat parties) + surplus above seats*quota.
                # surplus_list = just the over-quota part (stranded under list; STV transfers it).
                wasted_list = 0.0
                surplus_list = 0.0
                for k in range(10):
                    if listc[k] == 0:
                        wasted_list += V[k]
                    else:
                        s_over = max(0.0, V[k] - listc[k] * q_hare)
                        wasted_list += s_over
                        surplus_list += s_over
                wasted_stv = totV / (S + 1)             # one Droop quota (structural floor)
                # Winner-take-all ("current system" analog): the district's plurality party takes
                # every seat; every non-winner vote is stranded.
                k_plur = int(np.argmax(V))
                fptpc = np.zeros(10, dtype=int); fptpc[k_plur] = S
                wasted_fptp = totV - V[k_plur]
                # "Shut out": share of real voters whose first-choice party won no seat.
                if len(idx):
                    fcd = fc[idx]
                    wsub = w[idx]
                    vw = float(wsub.sum())
                    so_list = float(wsub[(listc[fcd] == 0)].sum())
                    so_stv = float(wsub[(stvc[fcd] == 0)].sum())
                else:
                    vw = so_list = so_stv = 0.0
                fips = f"{int(state_of[d]):02d}"
                rec = {
                    "districtId": d,
                    "densityTier": tier_of[d],
                    "seatCount": S,
                    "listElected": expand_seats(listc),
                    "stvElected": expand_seats(stvc),
                    "nRespondents": int(len(idx)),
                    "_V": V, "_totV": totV, "_list": listc, "_stv": stvc, "_fptp": fptpc,
                    "_wl": wasted_list, "_ws": wasted_stv, "_wf": wasted_fptp, "_surp": surplus_list,
                    "_vw": vw, "_sol": so_list, "_sos": so_stv,
                    "_rep": rep_by_d.get(d, (0.0, 0.0, 0.0, 0)),
                }
                districts_by_state.setdefault(fips, []).append(rec)

            # ── aggregate ───────────────────────────────────────────────────
            nat_V = np.zeros(10); nat_list = np.zeros(10, int); nat_stv = np.zeros(10, int); nat_fptp = np.zeros(10, int)
            nat_totV = 0.0; nat_wl = 0.0; nat_ws = 0.0; nat_wf = 0.0; nat_surp = 0.0
            nat_vw = 0.0; nat_sol = 0.0; nat_sos = 0.0
            nat_rvw = 0.0; nat_rnfc = 0.0; nat_runrep = 0.0; nat_rbq = 0
            by_state = {}
            districts_out = {}
            for fips, recs in districts_by_state.items():
                sV = np.zeros(10); sl = np.zeros(10, int); ss = np.zeros(10, int); sf = np.zeros(10, int)
                stotV = 0.0; swl = 0.0; sws = 0.0; swf = 0.0; sSeats = 0; ssurp = 0.0
                svw = 0.0; ssol = 0.0; ssos = 0.0
                srvw = 0.0; srnfc = 0.0; srunrep = 0.0; srbq = 0
                clean = []
                for r in recs:
                    sV += r["_V"]; sl += r["_list"]; ss += r["_stv"]; sf += r["_fptp"]
                    stotV += r["_totV"]; swl += r["_wl"]; sws += r["_ws"]; swf += r["_wf"]; sSeats += r["seatCount"]
                    ssurp += r["_surp"]
                    svw += r["_vw"]; ssol += r["_sol"]; ssos += r["_sos"]
                    srvw += r["_rep"][0]; srnfc += r["_rep"][1]; srunrep += r["_rep"][2]; srbq += r["_rep"][3]
                    clean.append({k: r[k] for k in ("districtId", "densityTier", "seatCount",
                                                    "listElected", "stvElected", "nRespondents")})
                nat_V += sV; nat_list += sl; nat_stv += ss; nat_fptp += sf
                nat_totV += stotV; nat_wl += swl; nat_ws += sws; nat_wf += swf; nat_surp += ssurp
                nat_vw += svw; nat_sol += ssol; nat_sos += ssos
                nat_rvw += srvw; nat_rnfc += srnfc; nat_runrep += srunrep; nat_rbq += srbq
                by_state[fips] = {
                    "abbr": app.loc[app["state_fips"] == int(fips), "state_abbr"].iloc[0],
                    "totalSeats": int(sSeats),
                    "voteShare": as_party_map(sV / stotV * 100, rnd=2),
                    "listSeats": as_party_map(sl, cast=int),
                    "stvSeats": as_party_map(ss, cast=int),
                    # Left unrepresented: list = first-choice party won no seat (no transfers);
                    # STV = candidate-level, transfer-aware (none of top-S choices won).
                    "unrepresented": {"list": round(ssol / svw * 100, 2) if svw else 0,
                                      "stv": round(srunrep / srvw * 100, 2) if srvw else 0},
                    "nonFirstChoice": {"list": round(ssol / svw * 100, 2) if svw else 0,
                                       "stv": round(srnfc / srvw * 100, 2) if srvw else 0},
                    "wasted": {"list": round(swl / stotV * 100, 2), "stv": round(sws / stotV * 100, 2),
                               "fptp": round(swf / stotV * 100, 2)},
                    # STV seats filled below the Droop quota (field collapse from ballot exhaustion).
                    "belowQuota": {"stv": round(srbq / int(ss.sum()) * 100, 2) if ss.sum() else 0},
                }
                districts_out[fips] = clean

            total_seats = int(nat_list.sum())
            vs = nat_V / nat_totV
            out[dkey][wyo][str(part)] = {
                "national": {
                    "totalSeats": total_seats,
                    "voteShare": as_party_map(vs * 100, rnd=2),
                    "listSeats": as_party_map(nat_list, cast=int),
                    "stvSeats": as_party_map(nat_stv, cast=int),
                    "fptpSeats": as_party_map(nat_fptp, cast=int),
                    "unrepresented": {"list": round(nat_sol / nat_vw * 100, 2),
                                      "stv": round(nat_runrep / nat_rvw * 100, 2)},
                    "nonFirstChoice": {"list": round(nat_sol / nat_vw * 100, 2),
                                       "stv": round(nat_rnfc / nat_rvw * 100, 2)},
                    # Over-quota surplus stranded (list); STV transfers its surplus (~0 wasted).
                    "excess": {"list": round(nat_surp / nat_totV * 100, 2), "stv": 0.0},
                    "wasted": {"list": round(nat_wl / nat_totV * 100, 2),
                               "stv": round(nat_ws / nat_totV * 100, 2),
                               "fptp": round(nat_wf / nat_totV * 100, 2)},
                    "gallagher": {"list": round(gallagher(vs, nat_list / total_seats), 2),
                                  "stv": round(gallagher(vs, nat_stv / max(1, int(nat_stv.sum()))), 2),
                                  "fptp": round(gallagher(vs, nat_fptp / total_seats), 2)},
                    # STV seats filled below the Droop quota (field collapse from ballot exhaustion).
                    "belowQuota": {"stv": round(nat_rbq / int(nat_stv.sum()) * 100, 2) if nat_stv.sum() else 0},
                },
                "byState": by_state,
                "districts": districts_out,
            }
        print(f"  [{dkey}] {wyo}: {len(district_ids)} districts × {len(PARTS)} turnout stops")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, separators=(",", ":")))
    mb = OUT_PATH.stat().st_size / 1e6
    print(f"\nWrote {OUT_PATH}  ({mb:.2f} MB)")

    # ── validation: the soft-posterior share basis IS the app's vote share. ──
    # commonpostweight (turnout-off) soft shares must reproduce houseStateMap popShares exactly.
    hsm = json.loads(HSM_BASE.read_text())
    worst = 0.0
    for fips_i in np.unique(inputstate):
        m = inputstate == fips_i
        s = (P[m] * cpw[m, None]).sum(0); s = s / s.sum()
        pop = hsm.get(f"{int(fips_i):02d}", {}).get("popShares", {})
        for k in range(10):
            p = CLUSTER_TO_PARTY[k]
            if p in pop:
                worst = max(worst, abs(s[k] * 100 - pop[p]))
    print(f"validation — max |cpw soft-share − houseStateMap popShares| = {worst:.4f} pp (should be ~0)")
    for dk in ("full", "top3", "top5", "top7", "top10"):
        nat = out[dk]["double"]["0"]["national"]
        print(f"[{dk}] double λ=0: unrepresented list {nat['unrepresented']['list']}% "
              f"stv {nat['unrepresented']['stv']}%  |  nonFirstChoice stv {nat['nonFirstChoice']['stv']}%")


def total_seats_str(nat):
    ls = sorted(nat["listSeats"].items(), key=lambda x: -x[1])[:4]
    ss = sorted(nat["stvSeats"].items(), key=lambda x: -x[1])[:4]
    return f"list {ls} | stv {ss}"


if __name__ == "__main__":
    sys.exit(main())

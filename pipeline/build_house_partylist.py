#!/usr/bin/env python3
"""
build_house_partylist.py
------------------------
Party-list PR comparison for the House, computed on the SAME multi-member districts
as the STV run (Drutman-style district sizes). Party-list is party-centric, so there
are no factor-deviation candidates — this uses the pure-party (rawMulti) party set.

Party vote share per district = FIRST-CHOICE share, aggregated over the voters assigned to
that district, weighted by commonpostweight × turnout multiplier. Each voter contributes one
ballot, to the party of their modal cluster.

This used to sum the posterior matrix itself, so a voter at 0.40/0.35/0.25 cast 0.40 of a
ballot for one party and 0.35 for another. That is a measure of partisan affinity, not an
election: no ballot is divisible, and the STV pipeline this tab is compared against has always
counted discrete first preferences (run_pure_multi_house_stv.py ranks by `prob_cluster_k`, so
its rank-1 IS this argmax). The two House systems now count votes the same way, so a
list-versus-STV gap is the counting rule rather than the vote definition. Cost of the switch,
national vote share at λ=5%: STY 9.9 → 7.3, CON 18.8 → 20.4, PRG 6.2 → 7.5. The affinity
measure it replaced is reported for its own sake by pipeline/build_cross_party_affinity.py.

For each district we compute:
  - Sainte-Laguë (Webster) divisor seat allocation (party list).
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
# Small companion to the above. housePartyList.json is ~4 MB because per-state (1.5 MB) and
# per-district (1.8 MB) detail is replicated across all 70 depth x map x turnout configurations,
# so it has to be lazy-fetched. The national blocks are only ~0.7 KB per configuration, and the
# House tab's headline charts need nothing else — so they get bundled at build time instead of
# waiting on the big fetch. Same numbers, same loop: this is a projection, not a second source.
SUMMARY_PATH = BASE_DIR / "viz" / "src" / "data" / "houseDepthNational.json"

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
    """Hare quota + largest remainder. Kept for the bootstrap import and for any
    caller that explicitly needs quota-based allocation."""
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


def sainte_lague(votes: np.ndarray, seats: int) -> np.ndarray:
    """Sainte-Laguë (Webster) divisor method. Awards seats one at a time to the party
    with the highest quotient votes/(2*seats_held + 1). Unbiased between large and small
    parties, monotone (adding a seat never takes one away), and no Alabama paradox."""
    out = np.zeros(10, dtype=int)
    for _ in range(int(seats)):
        q = np.where(votes > 0, votes / (2 * out + 1), -1.0)
        if q.max() <= 0:
            break
        out[int(q.argmax())] += 1
    return out


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
    # One-hot of `fc`: the ballot each voter actually casts. Allocation sums THIS, not `P`.
    FC = np.zeros_like(P)
    FC[np.arange(N), fc] = 1.0
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
            state_V = {int(f): FC[inputstate == f].T @ w[inputstate == f] for f in np.unique(inputstate)}

            districts_by_state: dict = {}
            for d in district_ids:
                idx = idx_by_dist[d]
                S = int(seat_of[d])
                if len(idx) == 0:                        # no respondents — use state shares
                    V = np.array(state_V[int(state_of[d])], dtype=np.float64)
                else:
                    V = FC[idx].T @ w[idx]                # (10,) weighted party votes
                totV = float(V.sum())
                listc = sainte_lague(V, S)
                stvc = stv_seats.get(d, np.zeros(10, dtype=int))
                quota = totV / S if S else 0.0
                # list wasted: lost (0-seat parties) + surplus above seats × quota.
                # surplus_list = just the over-quota part (stranded under list; STV transfers it).
                wasted_list = 0.0
                surplus_list = 0.0
                for k in range(10):
                    if listc[k] == 0:
                        wasted_list += V[k]
                    else:
                        s_over = max(0.0, V[k] - listc[k] * quota)
                        wasted_list += s_over
                        surplus_list += s_over
                wasted_stv = totV / (S + 1)             # one Droop quota (structural floor)
                # Winner-take-all ("current system" analog): the district's plurality party takes
                # every seat; every non-winner vote is stranded.
                k_plur = int(np.argmax(V))
                fptpc = np.zeros(10, dtype=int); fptpc[k_plur] = S
                wasted_fptp = totV - V[k_plur]
                # "Shut out": share of real voters whose first-choice party won no seat.
                # Soft coverage: share of each voter's posterior mass on parties that hold a
                # seat in this district. Measures how much of the electorate's political
                # complexity the resulting delegation represents, separately from whether
                # the allocation was proportional (Gallagher) or the ballot connected to a
                # winner (unrepresented).
                if len(idx):
                    fcd = fc[idx]
                    wsub = w[idx]
                    vw = float(wsub.sum())
                    so_list = float(wsub[(listc[fcd] == 0)].sum())
                    so_stv = float(wsub[(stvc[fcd] == 0)].sum())
                    Psub = P[idx]
                    scov_list = float((Psub[:, listc > 0].sum(1) * wsub).sum())
                    scov_stv = float((Psub[:, stvc > 0].sum(1) * wsub).sum())
                else:
                    vw = so_list = so_stv = 0.0
                    scov_list = scov_stv = 0.0
                fips = f"{int(state_of[d]):02d}"
                rec = {
                    "districtId": d,
                    "densityTier": tier_of[d],
                    "seatCount": S,
                    "listElected": expand_seats(listc),
                    "stvElected": expand_seats(stvc),
                    "nRespondents": int(len(idx)),
                    # No respondents: this district's V is a borrowed copy of its state's vote
                    # vector, present only so its seats get allocated. Its votes are fictional,
                    # so every vote-based aggregate below has to skip it.
                    "_empty": len(idx) == 0,
                    "_V": V, "_totV": totV, "_list": listc, "_stv": stvc, "_fptp": fptpc,
                    "_wl": wasted_list, "_ws": wasted_stv, "_wf": wasted_fptp, "_surp": surplus_list,
                    "_vw": vw, "_sol": so_list, "_sos": so_stv,
                    "_scl": scov_list, "_scs": scov_stv,
                    "_rep": rep_by_d.get(d, (0.0, 0.0, 0.0, 0)),
                }
                districts_by_state.setdefault(fips, []).append(rec)

            # ── aggregate ───────────────────────────────────────────────────
            nat_V = np.zeros(10); nat_list = np.zeros(10, int); nat_stv = np.zeros(10, int); nat_fptp = np.zeros(10, int)
            tiers = {t: np.zeros(10, int) for t in ("urban", "suburban", "rural")}
            listTiers = {t: np.zeros(10, int) for t in ("urban", "suburban", "rural")}
            nat_totV = 0.0; nat_wl = 0.0; nat_ws = 0.0; nat_wf = 0.0; nat_surp = 0.0
            nat_vw = 0.0; nat_sol = 0.0; nat_sos = 0.0; nat_scl = 0.0; nat_scs = 0.0
            nat_scl_st = 0.0; nat_scs_st = 0.0; nat_svw_st = 0.0
            nat_rvw = 0.0; nat_rnfc = 0.0; nat_runrep = 0.0; nat_rbq = 0
            by_state = {}
            districts_out = {}
            for fips, recs in districts_by_state.items():
                sV = np.zeros(10); sl = np.zeros(10, int); ss = np.zeros(10, int); sf = np.zeros(10, int)
                stotV = 0.0; swl = 0.0; sws = 0.0; swf = 0.0; sSeats = 0; ssurp = 0.0
                svw = 0.0; ssol = 0.0; ssos = 0.0; sscl = 0.0; sscs = 0.0
                srvw = 0.0; srnfc = 0.0; srunrep = 0.0; srbq = 0
                clean = []
                for r in recs:
                    sl += r["_list"]; ss += r["_stv"]; sf += r["_fptp"]; sSeats += r["seatCount"]
                    srvw += r["_rep"][0]; srnfc += r["_rep"][1]; srunrep += r["_rep"][2]; srbq += r["_rep"][3]
                    tiers[r["densityTier"].lower()] += r["_stv"]
                    listTiers[r["densityTier"].lower()] += r["_list"]
                    clean.append({k: r[k] for k in ("districtId", "densityTier", "seatCount",
                                                    "listElected", "stvElected", "nRespondents")})
                    if r["_empty"]:
                        continue
                    swl += r["_wl"]; sws += r["_ws"]; swf += r["_wf"]; ssurp += r["_surp"]
                    svw += r["_vw"]; ssol += r["_sol"]; ssos += r["_sos"]
                    sscl += r["_scl"]; sscs += r["_scs"]
                # Vote TOTALS come from the state's voters directly rather than from summing the
                # per-district vectors. A district with no assigned respondents borrows its
                # state's vote vector so its seats still get allocated, but that borrowed copy
                # must not also be counted as votes: it adds a second copy of the whole state.
                # The triple map has 14 such districts holding 86 of 1,726 seats, six of them in
                # California, so summing districts counted CA roughly seven times and put the
                # national vote share 2.2pp out (CON read 18.25 against a true 20.45). Seat
                # allocation still uses the per-district vectors; only the reported totals change.
                sV = np.array(state_V[int(fips)], dtype=np.float64)
                stotV = float(sV.sum())
                # State-level soft coverage: posterior mass on parties seated ANYWHERE in the
                # state, not just the voter's own district. More parties are represented at the
                # state level, so this is always >= the per-district figure.
                f_int = int(fips)
                sm = inputstate == f_int
                if sm.any() and svw > 0:
                    sw_sub = w[sm]; Ps = P[sm]
                    stl_mask = sl > 0; sts_mask = ss > 0
                    sscl_st = float((Ps[:, stl_mask].sum(1) * sw_sub).sum())
                    sscs_st = float((Ps[:, sts_mask].sum(1) * sw_sub).sum())
                    ssvw_st = float(sw_sub.sum())
                else:
                    sscl_st = sscs_st = ssvw_st = 0.0
                nat_V += sV; nat_list += sl; nat_stv += ss; nat_fptp += sf
                nat_totV += stotV; nat_wl += swl; nat_ws += sws; nat_wf += swf; nat_surp += ssurp
                nat_vw += svw; nat_sol += ssol; nat_sos += ssos
                nat_scl += sscl; nat_scs += sscs
                nat_scl_st += sscl_st; nat_scs_st += sscs_st; nat_svw_st += ssvw_st
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
                    # Soft coverage: share of each voter's posterior mass on a party that holds a
                    # seat. Per-district = mass on a party seated in your district; per-state =
                    # mass on a party seated anywhere in your state.
                    "softCoverage": {
                        "listDistrict": round(sscl / svw * 100, 2) if svw else 0,
                        "stvDistrict": round(sscs / svw * 100, 2) if svw else 0,
                        "listState": round(sscl_st / ssvw_st * 100, 2) if ssvw_st else 0,
                        "stvState": round(sscs_st / ssvw_st * 100, 2) if ssvw_st else 0,
                    },
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
                    "softCoverage": {
                        "listDistrict": round(nat_scl / nat_vw * 100, 2),
                        "stvDistrict": round(nat_scs / nat_vw * 100, 2),
                        "listState": round(nat_scl_st / nat_svw_st * 100, 2) if nat_svw_st else 0,
                        "stvState": round(nat_scs_st / nat_svw_st * 100, 2) if nat_svw_st else 0,
                    },
                },
                "byState": by_state,
                "districts": districts_out,
                # Consumed only by the summary projection below, then stripped.
                "_stvTiers": {t: as_party_map(v, cast=int) for t, v in tiers.items()},
                "_listTiers": {t: as_party_map(v, cast=int) for t, v in listTiers.items()},
            }
        print(f"  [{dkey}] {wyo}: {len(district_ids)} districts × {len(PARTS)} turnout stops")

    # Project the national blocks out, and strip the scratch tier field from the big payload.
    summary: dict = {}
    for dk, dv in out.items():
        for wy, wv in dv.items():
            for pt, cfg in wv.items():
                summary.setdefault(dk, {}).setdefault(wy, {})[pt] = {
                    "national": cfg["national"],
                    "stvTiers": cfg.pop("_stvTiers"),
                    "listTiers": cfg.pop("_listTiers"),
                }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, separators=(",", ":")))
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, separators=(",", ":"), sort_keys=True))
    mb = OUT_PATH.stat().st_size / 1e6
    kb = SUMMARY_PATH.stat().st_size / 1024
    print(f"\nWrote {OUT_PATH}  ({mb:.2f} MB)")
    print(f"Wrote {SUMMARY_PATH}  ({kb:.0f} KB)")

    # ── validation: allocation basis vs the state map's population shares. ──
    # This check used to assert the two were IDENTICAL, because allocation summed the posterior
    # matrix and so did houseStateMap popShares. Allocation now counts first choices, so the two
    # legitimately differ and the gap is the quantity to watch rather than a failure: it is the
    # per-party affinity residual, bounded at ~2pp nationally. Reported, not asserted.
    hsm = json.loads(HSM_BASE.read_text())
    worst = 0.0; worst_at = ""
    for fips_i in np.unique(inputstate):
        m = inputstate == fips_i
        s = (FC[m] * cpw[m, None]).sum(0); s = s / s.sum()
        pop = hsm.get(f"{int(fips_i):02d}", {}).get("popShares", {})
        for k in range(10):
            p = CLUSTER_TO_PARTY[k]
            if p in pop and abs(s[k] * 100 - pop[p]) > worst:
                worst = abs(s[k] * 100 - pop[p]); worst_at = f"{int(fips_i):02d}/{p}"
    print(f"first-choice share vs houseStateMap popShares: max gap {worst:.2f} pp at {worst_at}")
    print("  (nonzero by design — popShares are still soft; see module docstring)")
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

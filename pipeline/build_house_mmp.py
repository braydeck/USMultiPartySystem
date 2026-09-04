#!/usr/bin/env python3
"""
build_house_mmp.py
------------------
Compensatory mixed-member proportional (MMP) House, on the CURRENT single-member congressional
map with a per-state proportional top-off.

Two tiers, one ballot:
  district tier  the 436 real current congressional districts (CES `cd119`, i.e. the 119th
                 Congress lines). Each elects one member by plurality of first choices.
  list tier      each state's delegation is topped off to its Wyoming-rule size. A party's
                 district wins count against its proportional entitlement, so the top-off is
                 compensatory rather than parallel.

Seat allocation is SAINTE-LAGUE, seeded with district wins: award the top-off pool one seat at
a time to the party with the highest quotient votes/(2*seats_already_held + 1), where
seats_already_held starts at the party's district wins. Compensation falls out of the divisors,
so no subtract-and-re-round step is needed. That matters because re-rounding is where the
quota route loses accuracy: at double Wyoming there are ~39 seats of overhang, and the Hare
route has to compute entitlements, subtract district wins, then re-round the deficit vector to
fit the pool. Two roundings compound. Sainte-Lague absorbs overhang in one pass, because a
party that already holds more seats than its votes justify simply never posts a winning
quotient again. build_house_partylist.py keeps Hare/largest-remainder, which is the more
proportional allocator when it can allocate freely; the split is on mechanism, not taste.

CHAMBER SIZE IS FIXED PER STATE. No leveling seats: a state cannot be given more members than
its population entitles it to, and there is no national at-large pool to draw them from. So
overhang is absorbed within the state's fixed total rather than corrected by growing the
chamber. Overhang is reported per state so the cost stays visible.

Vote definition: FIRST CHOICE, for both tiers. One ballot, one first preference, driving both
the district contest and the state list. Weighted by commonpostweight x turnout multiplier,
matching build_house_partylist.py. No split-ticket second vote is modelled, because the ballot
model gives each voter a single preference ordering (see build_single_race_data.py).

No ballot-depth axis: MMP has no rankings, so like party list it is depth-invariant.

Districts per state come from the map, not from apportionment: mid-decade redistricting changes
lines but not the number of districts a state holds. Every state's Wyoming-rule target exceeds
its current district count, so the top-off pool is always >= 1 and no state needs a negative
entitlement rule.

Provenance: data/processed/{typology_cluster_assignments,turnout_propensity,voter_county_fips}.csv
(row-aligned; see make_voter_counties.py) + stv_config.STATE_POPS for the Wyoming-rule targets.

Output: viz/public/data/houseMmp.json  (lazy-loaded)
        viz/src/data/houseMmpNational.json  (national blocks only, bundled for headline charts)
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from stv_config import (STATE_POPS, FIPS_TO_ABBR,  # noqa: E402
                        POP_PER_SEAT, POP_PER_SEAT_TRIPLE)
from run_house_canonical import assign_density_tiers  # noqa: E402

TYPO_PATH = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
TURNOUT_PATH = BASE_DIR / "data" / "processed" / "turnout_propensity.csv"
CD_PATH = BASE_DIR / "data" / "processed" / "voter_county_fips.csv"
OUT_PATH = BASE_DIR / "viz" / "public" / "data" / "houseMmp.json"
SUMMARY_PATH = BASE_DIR / "viz" / "src" / "data" / "houseMmpNational.json"

PROB_COLS = [f"prob_cluster_{k}" for k in range(10)]
CLUSTER_TO_PARTY = {0: "CON", 1: "LBR", 2: "STY", 3: "NAT", 4: "LIB",
                    5: "POP", 6: "CUP", 7: "OAO", 8: "DSA", 9: "PRG"}
PARTIES = [CLUSTER_TO_PARTY[k] for k in range(10)]
F5_ORDER = ["PRG", "DSA", "LIB", "LBR", "OAO", "STY", "CUP", "CON", "POP", "NAT"]
PARTS = [0, 5, 10, 15, 20, 25, 30]
WYOMING = {"double": POP_PER_SEAT, "triple": POP_PER_SEAT_TRIPLE}


def sainte_lague(votes: np.ndarray, pool: int, seeded: np.ndarray) -> np.ndarray:
    """Award `pool` seats by highest quotient votes/(2s+1), with s seeded at district wins.

    Returns the (10,) vector of TOP-OFF seats only, so callers can report the two tiers
    separately. A party with zero votes never wins a quotient.
    """
    s = seeded.astype(int).copy()
    added = np.zeros(10, dtype=int)
    for _ in range(int(pool)):
        q = votes / (2 * s + 1)
        q = np.where(votes > 0, q, -1.0)
        if q.max() <= 0:
            break
        k = int(q.argmax())
        s[k] += 1
        added[k] += 1
    return added


def hare_lr(votes: np.ndarray, seats: int) -> np.ndarray:
    """Hare quota + largest remainder. Used only to report each party's unconstrained
    entitlement, which is what overhang is measured against."""
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
    """Least-squares index, 0-100. Same definition as build_house_partylist.py."""
    return float(np.sqrt(0.5 * np.sum((vote_share - seat_share) ** 2)) * 100)


def as_party_map(vec, cast=float, rnd=None):
    out = {}
    for k in range(10):
        v = cast(vec[k])
        if rnd is not None:
            v = round(v, rnd)
        if v:
            out[CLUSTER_TO_PARTY[k]] = v
    return out


def expand_seats(seats_by_cluster: np.ndarray) -> list:
    """Cluster seat counts -> flat party-code list, F5 order."""
    out = []
    for p in F5_ORDER:
        k = PARTIES.index(p)
        out.extend([p] * int(seats_by_cluster[k]))
    return out


def main():
    typ = pd.read_csv(TYPO_PATH)
    N = len(typ)
    P = typ[PROB_COLS].values.astype(np.float64)
    fc = P.argmax(axis=1)
    cpw = typ["commonpostweight"].values.astype(np.float64)
    inputstate = typ["inputstate"].astype(int).values

    tp = pd.read_csv(TURNOUT_PATH)
    assert len(tp) == N, "turnout rows misaligned"
    t = tp["turnout_cluster"].values.astype(np.float64)

    cds = pd.read_csv(CD_PATH)
    assert len(cds) == N, "voter_county_fips rows misaligned"
    cd_num = cds["cd119"].astype(int).values
    cd_key = np.array([f"{s:02d}-{d:02d}" for s, d in zip(inputstate, cd_num)])

    states = sorted(STATE_POPS.keys())
    cds_by_state = {f: sorted(set(cd_key[inputstate == f])) for f in states}
    idx_by_cd = {k: np.where(cd_key == k)[0] for k in np.unique(cd_key)}
    n_cd = sum(len(v) for v in cds_by_state.values())
    print(f"{N:,} voters across {n_cd} districts in {len(states)} states")

    cd_resp = {key: len(idx_by_cd[key]) for key in idx_by_cd}
    tier_of_cd: dict[str, str] = {}
    for f in states:
        keys = cds_by_state[f]
        sorted_keys = sorted(keys, key=lambda k: cd_resp.get(k, 0), reverse=True)
        tiers = assign_density_tiers([1] * len(keys), f)
        for key, tier in zip(sorted_keys, tiers):
            tier_of_cd[key] = tier.lower()

    out: dict = {}
    summary: dict = {}
    for wyo, pps in WYOMING.items():
        target = {f: max(1, round(STATE_POPS[f] / pps)) for f in states}
        for f in states:
            assert target[f] > len(cds_by_state[f]), \
                f"{FIPS_TO_ABBR.get(f, f)}: target {target[f]} <= {len(cds_by_state[f])} districts"
        out[wyo] = {}
        for part in PARTS:
            lam = part / 100.0
            w = cpw * (t + lam * (1.0 - t))

            nat_V = np.zeros(10)
            nat_dist = np.zeros(10, dtype=int)
            nat_top = np.zeros(10, dtype=int)
            nat_over = 0
            nat_shut = 0.0
            nat_w = 0.0
            nat_scov = 0.0
            nat_surp = 0.0
            nat_totV = 0.0
            dist_tiers = {t: np.zeros(10, int) for t in ("urban", "suburban", "rural")}
            by_state = {}
            districts_out: dict = {}

            for f in states:
                m = inputstate == f
                keys = cds_by_state[f]
                V = np.array([w[m & (fc == k)].sum() for k in range(10)])
                dist = np.zeros(10, dtype=int)
                dwin = {}
                for key in keys:
                    i = idx_by_cd[key]
                    h = np.array([w[i][fc[i] == k].sum() for k in range(10)])
                    k_win = int(h.argmax())
                    dist[k_win] += 1
                    dist_tiers[tier_of_cd[key]][k_win] += 1
                    dwin[key] = {"winner": CLUSTER_TO_PARTY[k_win],
                                 "nRespondents": int(len(i)),
                                 "winnerShare": round(float(h[k_win] / h.sum() * 100), 2) if h.sum() else 0.0}

                pool = int(target[f]) - int(dist.sum())
                top = sainte_lague(V, pool, dist)
                seats = dist + top
                # Overhang: seats a party holds beyond the entitlement its own votes justify
                # over the state's full delegation. Absorbed inside the fixed total.
                ent = hare_lr(V, int(target[f]))
                over = int(np.maximum(dist - ent, 0).sum())

                sw = w[m]
                shut = float(sw[seats[fc[m]] == 0].sum())
                Ps = P[m]
                seated_mask = seats > 0
                scov = float((Ps[:, seated_mask].sum(1) * sw).sum())
                totV = float(V.sum())
                quota = totV / int(target[f]) if target[f] else 0.0
                surplus = sum(max(0.0, V[k] - seats[k] * quota) for k in range(10) if seats[k] > 0)
                fips = f"{f:02d}"
                nat_V += V; nat_dist += dist; nat_top += top; nat_over += over
                nat_shut += shut; nat_w += float(sw.sum()); nat_scov += scov
                nat_surp += surplus; nat_totV += totV
                by_state[fips] = {
                    "abbr": FIPS_TO_ABBR.get(f, str(f)),
                    "totalSeats": int(target[f]),
                    "districtCount": len(keys),
                    "voteShare": as_party_map(V / V.sum() * 100, rnd=2),
                    "districtSeats": as_party_map(dist, cast=int),
                    "topoffSeats": as_party_map(top, cast=int),
                    "mmpSeats": as_party_map(seats, cast=int),
                    "elected": expand_seats(seats),
                    "overhang": over,
                    "unrepresented": round(shut / float(sw.sum()) * 100, 2) if sw.sum() else 0.0,
                    "softCoverage": round(scov / float(sw.sum()) * 100, 2) if sw.sum() else 0.0,
                }
                districts_out[fips] = dwin

            total = int(nat_dist.sum() + nat_top.sum())
            vs = nat_V / nat_V.sum()
            mmp = nat_dist + nat_top
            out[wyo][str(part)] = {
                "national": {
                    "totalSeats": total,
                    "districtTotal": int(nat_dist.sum()),
                    "topoffTotal": int(nat_top.sum()),
                    "voteShare": as_party_map(vs * 100, rnd=2),
                    "districtSeats": as_party_map(nat_dist, cast=int),
                    "topoffSeats": as_party_map(nat_top, cast=int),
                    "mmpSeats": as_party_map(mmp, cast=int),
                    "overhang": nat_over,
                    # Share of voters whose first-choice party won no seat in their STATE.
                    # State-level because the list tier is statewide; the party-list and STV
                    # equivalents in build_house_partylist.py are per-district, so the two
                    # numbers are not interchangeable.
                    "unrepresented": round(nat_shut / nat_w * 100, 2),
                    "softCoverage": round(nat_scov / nat_w * 100, 2),
                    "excess": round(nat_surp / nat_totV * 100, 2) if nat_totV else 0.0,
                    "gallagher": {
                        "mmp": round(gallagher(vs, mmp / total), 2),
                        "districtOnly": round(gallagher(vs, nat_dist / int(nat_dist.sum())), 2),
                    },
                },
                "byState": by_state,
                "districts": districts_out,
                "_districtTiers": {t: as_party_map(v, cast=int) for t, v in dist_tiers.items()},
            }
            nat_block = out[wyo][str(part)]["national"]
            nat_block["districtTiers"] = out[wyo][str(part)].pop("_districtTiers")
            summary.setdefault(wyo, {})[str(part)] = nat_block
        print(f"  {wyo}: {n_cd} districts + top-off to {sum(target.values())} × {len(PARTS)} turnout stops")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, separators=(",", ":")))
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, separators=(",", ":"), sort_keys=True))
    print(f"\nWrote {OUT_PATH}  ({OUT_PATH.stat().st_size / 1e6:.2f} MB)")
    print(f"Wrote {SUMMARY_PATH}  ({SUMMARY_PATH.stat().st_size / 1024:.0f} KB)")

    for wyo in WYOMING:
        nat = out[wyo]["5"]["national"]
        print(f"\n[{wyo} λ=5%] {nat['totalSeats']} seats "
              f"({nat['districtTotal']} district + {nat['topoffTotal']} top-off), "
              f"overhang {nat['overhang']}, Gallagher {nat['gallagher']['mmp']} "
              f"(district tier alone {nat['gallagher']['districtOnly']}), "
              f"unrepresented {nat['unrepresented']}%")
        for p in sorted(nat["mmpSeats"], key=lambda x: -nat["mmpSeats"][x]):
            print(f"    {p:4s} {nat['mmpSeats'][p]:4d} = {nat['districtSeats'].get(p, 0):3d} district "
                  f"+ {nat['topoffSeats'].get(p, 0):3d} top-off   (vote {nat['voteShare'].get(p, 0):5.2f}%)")


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
quota_composition.py
--------------------
Decomposes every House seat into WHOSE ballots elected it: for each elected
candidate, the weight sitting with them at the moment they reached quota, broken
down by the first-preference party of each contributing ballot and by the rank that
ballot was resting on.

Answers "which parties are viable on their own first preferences and which need
borrowed votes", which preference depth alone cannot: ballots are party-contiguous,
so 92% of them do not leave their own party until rank 4 and depth mostly measures
slate size. See docs/METHODOLOGY.md and the About tab.

Provenance: reruns the canonical House STV path at the app default (double
apportionment, rank-7 ballots, 5% turnout-gap closure) by importing the real
engine's pool construction, scoring and ballot generation from
run_pure_multi_house_stv, so only the counting loop is re-implemented — with
instrumentation. Validates its elected sets district-by-district against the
published viz bundle before writing anything.

Run:
    TURNOUT_WEIGHT=1 TURNOUT_LAMBDA=0.05 python analysis/quota_composition.py

Not emitted, deliberately: seats won per own-base quota. Summing each party's
first-preference weight over district-specific quotas makes the measure sensitive to
district magnitude, and its party shares diverge from the published vote shares in
exactly the direction that would manufacture a conversion finding (CON +1.8pp, NAT
+1.7 score low; STY -2.5, CUP -1.2 score high). `base_quotas` is still accumulated
below for anyone who wants to reconcile it, but nothing should be published from it
until it agrees with housePartyList's voteShare.

For conversion efficiency use the published stvSeats vs listSeats comparison instead:
same ballots, proportional baseline, no denominator of ours in the way.

Output: viz/src/data/quotaComposition.json
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "pipeline" / "pure_only"))

BALLOT_DEPTH = int(os.environ.get("BALLOT_DEPTH", "7"))
# The bundle the House tab displays at the app default: rank-7 ballots, double
# apportionment, 5% gap. districtStvResults*.json is the FULL-RANKING tree and would
# validate a different chamber.
PUBLISHED = BASE / "viz" / "public" / "data" / "housePartyList.json"
PUBLISHED_PATH = ("top7", "double", "5")
# 04-01/04-03 carry the Maricopa sub-county split, which the published bundle predates
# (see county_split_overrides.csv and the "label the statewide-pool district until it
# runs" commit). This run applies the override, so these two are expected to differ.
KNOWN_STALE = {"04-01", "04-03"}
OUT_PATH = BASE / "viz" / "src" / "data" / "quotaComposition.json"

if os.environ.get("TURNOUT_WEIGHT") != "1" or os.environ.get("TURNOUT_LAMBDA") != "0.05":
    sys.exit("Set TURNOUT_WEIGHT=1 and TURNOUT_LAMBDA=0.05 to match the app default stop.")

import run_pure_multi_house_stv as H  # noqa: E402  (needs the env vars set first)


def active_choice(ballot_row, active_set):
    """(code, rank_index) of the first still-active preference, or (None, None)."""
    for r, code in enumerate(ballot_row):
        if code in active_set:
            return code, r
    return None, None


def run_stv_instrumented(ballots_arr, weights, cand_codes, n_seats, first_party, flows=None):
    """H.run_stv with per-seat composition recorded. Counting logic is line-for-line
    the same: Droop quota, weighted inclusive Gregory surplus, field-collapse branch.

    Composition is measured on the weight resting with a candidate when they cross
    quota. Under WIGM the retained quota and the transferred surplus are scaled by the
    same factor, so both have identical composition and the shares are unambiguous.

    Returns (elected, below_quota, seats) where each seat records:
      {code, party, belowQuota, order, byOrigin: {party: weight}, joint: {origin|rank: weight}}

    When `flows` is passed, records actual transfer destinations as the count runs: for every
    surplus and every elimination, the weight leaving a candidate is followed to its next
    surviving choice. Keyed by party pair, with same-party moves and exhausted weight kept
    apart, because under slate voting most of a surplus goes to the party's own next candidate.
    """
    active = set(cand_codes)
    ballot_wts = weights.astype(float).copy()
    total_votes = float(weights.sum())
    quota = total_votes / (n_seats + 1) + 1
    elected: list = []
    seats: list = []
    below_quota = 0

    def compose(winner, fsc, ranks):
        """Joint weight by (origin party, rank). Marginals are recoverable from it;
        the reverse is not, because own-party ballots cluster at ranks 1-3 and other
        parties' ballots cannot appear before their own slate is exhausted."""
        joint: dict = defaultdict(float)
        for i in range(len(fsc)):
            if fsc[i] == winner:
                joint[(first_party[i], int(ranks[i]) + 1)] += ballot_wts[i]
        by_origin: dict = defaultdict(float)
        for (origin, _r), w in joint.items():
            by_origin[origin] += w
        return dict(by_origin), {f"{o}|{r}": w for (o, r), w in joint.items()}

    def record_flow(source, movers, kind):
        """movers: list of (ballot index, weight leaving). `active` must already exclude the
        source, so the next surviving choice is the real destination."""
        if flows is None:
            return
        src_party = source.rsplit("_", 1)[0]
        for i, w in movers:
            nxt, _ = active_choice(ballots_arr[i], active)
            if nxt is None:
                flows["exhausted"][src_party] += w
            else:
                dst_party = nxt.rsplit("_", 1)[0]
                if dst_party == src_party:
                    flows["internal"][src_party] += w
                else:
                    flows["out"][src_party][dst_party] += w
            flows["moved"][(src_party, kind)] += w

    while len(elected) < n_seats and active:
        remaining = n_seats - len(elected)
        fsc = np.empty(len(ballots_arr), dtype=object)
        ranks = np.full(len(ballots_arr), -1, dtype=int)
        for i in range(len(ballots_arr)):
            code, r = active_choice(ballots_arr[i], active)
            fsc[i] = code if code is not None else "__exhausted__"
            ranks[i] = r if r is not None else -1

        totals = {c: 0.0 for c in active}
        for code, w in zip(fsc, ballot_wts):
            if code in totals:
                totals[code] += w

        if len(active) <= remaining:
            for c in sorted(active):
                by_origin, joint = compose(c, fsc, ranks)
                elected.append(c)
                is_below = totals.get(c, 0.0) < quota
                below_quota += int(is_below)
                seats.append({
                    "code": c, "party": c.rsplit("_", 1)[0], "belowQuota": is_below,
                    "order": len(elected), "byOrigin": by_origin, "joint": joint,
                })
            active.clear()
            break

        over_quota = sorted([c for c in active if totals[c] >= quota],
                            key=lambda c: (-totals[c], c))
        if over_quota:
            winner = over_quota[0]
            by_origin, joint = compose(winner, fsc, ranks)
            sf = (totals[winner] - quota) / totals[winner]
            elected.append(winner)
            seats.append({
                "code": winner, "party": winner.rsplit("_", 1)[0], "belowQuota": False,
                "order": len(elected), "byOrigin": by_origin, "joint": joint,
            })
            movers = [(i, ballot_wts[i] * (1 - sf)) for i in range(len(fsc)) if fsc[i] == winner]
            for i in range(len(fsc)):
                if fsc[i] == winner:
                    ballot_wts[i] *= sf
            active.discard(winner)
            # Surplus leaves at the transferred value, which is what (1 - sf) of the old weight is.
            record_flow(winner, [(i, ballot_wts[i]) for i, _ in movers], "surplus")
        else:
            loser = min(active, key=lambda c: (totals[c], c))
            movers = [(i, ballot_wts[i]) for i in range(len(fsc)) if fsc[i] == loser]
            active.discard(loser)
            record_flow(loser, movers, "elimination")

    return elected, below_quota, seats


def main():
    print("Loading inputs…")
    efa = pd.read_csv(H.EFA_PATH)
    typology = pd.read_csv(H.TYPOLOGY_PATH)
    voter_factors = efa[H.FACTOR_COLS].values.astype(np.float64)
    weights = efa["commonpostweight"].values.astype(np.float64)
    count_weights = weights * H.turnout_multiplier(len(efa))
    prob_matrix = typology[H.PROB_COLS].values.astype(np.float64)

    apportion_df = pd.read_csv(H.APPORTIONMENT)
    dist_seats = dict(zip(apportion_df["district_id"], apportion_df["seat_count"]))
    dist_state = dict(zip(apportion_df["district_id"], apportion_df["state_fips"]))
    dist_abbr = dict(zip(apportion_df["district_id"], apportion_df["state_abbr"]))

    district_ids = H_district_ids(efa, apportion_df)

    state_fips_of_voter = np.array([
        did[:2] if isinstance(did, str) and len(did) >= 2 else '' for did in district_ids
    ])
    state_voter_masks = {
        int(r["state_fips"]): state_fips_of_voter == str(int(r["state_fips"])).zfill(2)
        for _, r in apportion_df.drop_duplicates("state_fips").iterrows()
    }

    blk = json.loads(PUBLISHED.read_text())
    for key in PUBLISHED_PATH:
        blk = blk[key]
    pub_by_did = {}
    for rows in blk["districts"].values():
        for row in (rows if isinstance(rows, list) else [rows]):
            pub_by_did[row["districtId"]] = row["stvElected"]

    rng_prob = np.random.default_rng(43)
    flows = {
        "out": defaultdict(lambda: defaultdict(float)),
        "internal": defaultdict(float),
        "exhausted": defaultdict(float),
        "moved": defaultdict(float),
    }
    base_quotas: dict = defaultdict(float)
    seats_all: list = []
    checked = mismatched = 0

    for did in apportion_df["district_id"].tolist():
        mask = district_ids == did
        N_dist = int(mask.sum())
        n_seats = dist_seats.get(did, 5)
        fips = int(dist_state.get(did, 0))

        if N_dist < H.MIN_RESPONDENTS:
            state_mask = state_voter_masks.get(fips, np.zeros(len(district_ids), dtype=bool))
            if int(state_mask.sum()) < H.MIN_RESPONDENTS:
                continue
            mask = state_mask

        d_weights = weights[mask]
        d_count_weights = count_weights[mask]
        d_prob_matrix = prob_matrix[mask]

        d_shares = np.average(d_prob_matrix, weights=d_weights, axis=0)
        shares_dict = {f"prob_cluster_{k}": float(d_shares[k]) for k in range(10)}
        candidates = H.build_district_candidates(shares_dict, n_seats)
        if not candidates:
            continue

        cand_codes = [c["code"] for c in candidates]
        n_seats_eff = min(n_seats, len(candidates))

        scores = H.compute_candidate_scores_prob(d_prob_matrix, candidates)
        ballots = H.generate_ballots(scores, rng_prob, candidates)
        bal_stv = ballots if not BALLOT_DEPTH else ballots[:, :BALLOT_DEPTH]
        first_party = np.array([b[0].rsplit("_", 1)[0] for b in ballots], dtype=object)

        elected, _, seats = run_stv_instrumented(
            bal_stv, d_count_weights, cand_codes, n_seats_eff, first_party, flows)

        quota_d = float(d_count_weights.sum()) / (n_seats_eff + 1) + 1
        own_quotas: dict = defaultdict(float)
        for i, p_first in enumerate(first_party):
            own_quotas[p_first] += float(d_count_weights[i])
        for party, w in own_quotas.items():
            base_quotas[party] += w / quota_d

        got = [c.rsplit("_", 1)[0] for c in elected]
        want = pub_by_did.get(did)
        if want is not None and did not in KNOWN_STALE:
            checked += 1
            if sorted(got) != sorted(want):
                mismatched += 1
                if mismatched <= 5:
                    print(f"  MISMATCH {did}: got {sorted(got)} want {sorted(want)}")
        elif did in KNOWN_STALE:
            print(f"  (skipping {did}: Maricopa split, published bundle predates it)")

        for s in seats:
            s["districtId"] = did
            s["stateAbbr"] = dist_abbr.get(did, "??")
            s["seatCount"] = n_seats_eff
            seats_all.append(s)

    print(f"\nValidation: {checked - mismatched}/{checked} districts reproduce the published "
          f"rank-7 seats (multiset), {len(KNOWN_STALE)} excluded as known-stale.")
    if mismatched:
        sys.exit(f"ABORT: {mismatched} districts disagree; the decomposition would not describe "
                 "the published chamber.")

    write_bundle(seats_all, flows)


def H_district_ids(efa, apportion_df):
    """Voter→district assignment, mirroring the geo path in H.main()."""
    voter_fips_df = pd.read_csv(H.VOTER_FIPS_PATH, index_col=0)
    county_fips = pd.to_numeric(voter_fips_df["countyfips"], errors="coerce").fillna(0).astype(int)
    voter_counties = county_fips.astype(str).str.zfill(5).values

    county_dist_df = pd.read_csv(H.COUNTY_DIST_PATH)
    county_to_dist = dict(zip(
        county_dist_df["county_fips5"].astype(str).str.zfill(5), county_dist_df["district_id"]))

    state_fallback: dict = {}
    for _, row in apportion_df.iterrows():
        sfips = str(int(row["state_fips"])).zfill(2)
        state_fallback.setdefault(sfips, row["district_id"])

    split_override: dict = {}
    if H.SPLIT_OVERRIDE_PATH.exists():
        for _, row in pd.read_csv(H.SPLIT_OVERRIDE_PATH).iterrows():
            split_override[(str(row["county_fips5"]).zfill(5), int(row["cd119"]))] = row["district_id"]
    voter_cds = (pd.to_numeric(voter_fips_df["cd119"], errors="coerce").values
                 if "cd119" in voter_fips_df.columns else np.full(len(voter_counties), np.nan))

    out = np.empty(len(voter_counties), dtype=object)
    for i, county in enumerate(voter_counties):
        did = None
        cd = voter_cds[i]
        if split_override and cd == cd:
            did = split_override.get((county, int(cd)))
        if did is None:
            did = county_to_dist.get(county)
        if did is None:
            did = state_fallback.get(county[:2], "")
        out[i] = did
    return out


def write_bundle(seats_all, flows):
    """Aggregate to party level: overall composition, own-party rank depth, and the
    composition of each party's marginal (last-won) seat per district."""
    parties = sorted({s["party"] for s in seats_all})
    overall = {p: defaultdict(float) for p in parties}
    own_depth = {p: defaultdict(float) for p in parties}
    marginal = {p: defaultdict(float) for p in parties}
    seat_counts = {p: 0 for p in parties}
    below = {p: 0 for p in parties}

    last_of: dict = {}
    per_district: dict = defaultdict(lambda: defaultdict(int))
    for s in seats_all:
        key = (s["districtId"], s["party"])
        if key not in last_of or s["order"] > last_of[key]["order"]:
            last_of[key] = s
        per_district[s["party"]][s["districtId"]] += 1

    for s in seats_all:
        p = s["party"]
        seat_counts[p] += 1
        below[p] += int(s["belowQuota"])
        for origin, w in s["byOrigin"].items():
            overall[p][origin] += w
        # Own-party depth: ranks are only comparable within a party's own voters, since
        # slate size sets where other parties can appear on the ballot at all.
        for key, w in s["joint"].items():
            origin, rank = key.split("|")
            if origin == p:
                own_depth[p][int(rank)] += w

    for (_did, p), s in last_of.items():
        for origin, w in s["byOrigin"].items():
            marginal[p][origin] += w

    def shares(d):
        tot = sum(d.values()) or 1.0
        return {k: round(v / tot, 4) for k, v in sorted(d.items(), key=lambda kv: -kv[1]) if v / tot >= 0.002}

    def spread(party):
        """Distribution of seats won per district: how often a party takes more than one
        seat in the same district, which is what creates a margin to measure at all."""
        counts = sorted(per_district[party].values())
        hist: dict = defaultdict(int)
        for c in counts:
            hist[min(c, 4)] += 1
        n = len(counts)
        return {
            "districtsWon": n,
            "median": counts[n // 2] if n else 0,
            "max": counts[-1] if n else 0,
            "hist": {str(k): hist[k] for k in sorted(hist)},
            "multiSeatShare": round(sum(1 for c in counts if c > 1) / n, 4) if n else 0.0,
        }

    out = {
        "config": {"apportionment": "double", "ballotDepth": BALLOT_DEPTH, "turnoutGap": 0.05},
        "parties": [
            {
                "party": p,
                "seats": seat_counts[p],
                "belowQuota": below[p],
                "ownShare": round(sum(v for k, v in overall[p].items() if k == p)
                                  / (sum(overall[p].values()) or 1.0), 4),
                "byOrigin": shares(overall[p]),
                "ownDepth": shares(own_depth[p]),
                "marginalByOrigin": shares(marginal[p]),
                "marginalOwnShare": round(sum(v for k, v in marginal[p].items() if k == p)
                                          / (sum(marginal[p].values()) or 1.0), 4),
                "perDistrict": spread(p),
            }
            for p in parties
        ],
    }
    # Real transfer destinations, replacing the rank-2 proxy in houseTransfers.json: this
    # follows the weight that actually left each party during the count.
    transfers = []
    for p in sorted(flows["out"], key=lambda k: -sum(flows["out"][k].values())):
        cross = dict(flows["out"][p])
        cross_tot = sum(cross.values())
        internal = flows["internal"][p]
        exhausted = flows["exhausted"][p]
        moved = cross_tot + internal + exhausted
        if moved <= 0:
            continue
        transfers.append({
            "party": p,
            # Shares of cross-party outflow, so a row sums to 100% and is comparable to the
            # composition matrix; the three context shares below say how big that slice is.
            "byDest": {k: round(v / cross_tot, 4) for k, v in
                       sorted(cross.items(), key=lambda kv: -kv[1]) if v / cross_tot >= 0.002},
            "crossShare": round(cross_tot / moved, 4),
            "internalShare": round(internal / moved, 4),
            "exhaustedShare": round(exhausted / moved, 4),
            "surplusShare": round(flows["moved"][(p, "surplus")] / moved, 4),
        })
    out["transfersOut"] = transfers

    out["parties"].sort(key=lambda r: -r["ownShare"])
    OUT_PATH.write_text(json.dumps(out, indent=1))
    print(f"\nWrote {OUT_PATH.relative_to(BASE)}  ({len(seats_all)} seats decomposed)")
    print("\n  transfers out (share of weight leaving each party):")
    for t in out["transfersOut"]:
        eff = 1 / sum(v * v for v in t["byDest"].values()) if t["byDest"] else 0
        print(f"    {t['party']:4s} cross {t['crossShare']*100:5.1f}%  internal {t['internalShare']*100:5.1f}%  "
              f"exhausted {t['exhaustedShare']*100:5.1f}%  effN {eff:4.2f}  "
              f"{ {k: round(v*100) for k, v in list(t['byDest'].items())[:4]} }")
    for r in out["parties"]:
        borrowed = 1 - r["ownShare"]
        d = r["perDistrict"]
        print(f"  {r['party']:4s} {r['seats']:4d} seats  own {r['ownShare']*100:5.1f}%  "
              f"marginal {r['marginalOwnShare']*100:5.1f}%  gap {(r['ownShare']-r['marginalOwnShare'])*100:4.1f}pp  "
              f"| {d['districtsWon']:3d} districts, {d['multiSeatShare']*100:4.1f}% multi-seat")


if __name__ == "__main__":
    main()

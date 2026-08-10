#!/usr/bin/env python3
"""
quota_flows.py
--------------
Runs the two House flow matrices across every configuration the tab exposes, so the charts
follow the controls instead of being pinned to one cell:

  apportionment {double, triple} x ballot depth {3, 5, 7, 10, all} x turnout gap {0..30} = 70

Emits, per configuration:
  transfersOut  — where each party's votes go when they leave it (surplus + elimination),
                  with the internal / exhausted context shares.
  parties       — whose ballots elected each party's seats, by the voters' own first choice.

Reuses run_stv_instrumented() from quota_composition so the counting and the recording cannot
drift from the validated single-config version. Ballot generation is hoisted out of the config
loop: candidate pools and ballots depend only on the apportionment, while turnout changes the
counting weights and depth truncates the ballot, so the expensive part runs twice, not 70 times.

Validates every configuration against housePartyList's own stvElected lists before writing.

Run:  TURNOUT_WEIGHT=1 python analysis/quota_flows.py
Out:  viz/public/data/quotaFlows.json   (lazy-loaded, like housePartyList)
"""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("TURNOUT_WEIGHT", "1")
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "analysis"))
sys.path.insert(0, str(BASE / "pipeline" / "pure_only"))

import quota_composition as Q  # noqa: E402
H = Q.H

DEPTHS = {"full": 0, "top3": 3, "top5": 5, "top7": 7, "top10": 10}
GAPS = [0, 5, 10, 15, 20, 25, 30]
WYOMING = {
    "double": {"apport": H.APPORTIONMENT, "county": H.COUNTY_DIST_PATH},
    "triple": {"apport": H.APPORTIONMENT_TRIPLE, "county": H.COUNTY_DIST_PATH_TRIPLE},
}
# Optional slice for testing a few cells: QF_DEPTHS=top7 QF_GAPS=5 QF_WYO=double
if os.environ.get("QF_DEPTHS"):
    keep = os.environ["QF_DEPTHS"].split(",")
    DEPTHS = {k: v for k, v in DEPTHS.items() if k in keep}
if os.environ.get("QF_GAPS"):
    GAPS = [int(g) for g in os.environ["QF_GAPS"].split(",")]
if os.environ.get("QF_WYO"):
    keep_w = os.environ["QF_WYO"].split(",")
    WYOMING = {k: v for k, v in WYOMING.items() if k in keep_w}

PUBLISHED = BASE / "viz" / "public" / "data" / "housePartyList.json"
OUT_PATH = BASE / "viz" / "public" / "data" / "quotaFlows.json"
TURNOUT_CSV = BASE / "data" / "processed" / "turnout_propensity.csv"
# 04-01/04-03 carry the Maricopa sub-county split the published bundle predates. It applies to
# both apportionments: the override maps county+cd119 to a district id present in each.
KNOWN_STALE = {"04-01", "04-03"}


def district_assignment(apportion_df, county_path):
    """Voter→district, mirroring the geo path in H.main() for either apportionment."""
    voter_fips_df = pd.read_csv(H.VOTER_FIPS_PATH, index_col=0)
    counties = (pd.to_numeric(voter_fips_df["countyfips"], errors="coerce").fillna(0)
                .astype(int).astype(str).str.zfill(5).values)
    county_dist = pd.read_csv(county_path)
    to_dist = dict(zip(county_dist["county_fips5"].astype(str).str.zfill(5),
                       county_dist["district_id"]))
    fallback: dict = {}
    for _, row in apportion_df.iterrows():
        fallback.setdefault(str(int(row["state_fips"])).zfill(2), row["district_id"])

    split: dict = {}
    if H.SPLIT_OVERRIDE_PATH.exists():
        for _, row in pd.read_csv(H.SPLIT_OVERRIDE_PATH).iterrows():
            split[(str(row["county_fips5"]).zfill(5), int(row["cd119"]))] = row["district_id"]
    cds = (pd.to_numeric(voter_fips_df["cd119"], errors="coerce").values
           if "cd119" in voter_fips_df.columns else np.full(len(counties), np.nan))

    out = np.empty(len(counties), dtype=object)
    for i, county in enumerate(counties):
        did = None
        if split and cds[i] == cds[i]:
            did = split.get((county, int(cds[i])))
        if did is None:
            did = to_dist.get(county)
        if did is None:
            did = fallback.get(county[:2], "")
        out[i] = did
    return out


def prepare(wyo, cfg, weights, prob_matrix):
    """Per-district candidate pools, ballots and origins for one apportionment. None of it
    depends on turnout or depth, so it is built once and reused across 35 configurations."""
    apportion_df = pd.read_csv(cfg["apport"])
    district_ids = district_assignment(apportion_df, cfg["county"])
    state_of_voter = np.array([d[:2] if isinstance(d, str) and len(d) >= 2 else ''
                               for d in district_ids])
    state_masks = {int(r["state_fips"]): state_of_voter == str(int(r["state_fips"])).zfill(2)
                   for _, r in apportion_df.drop_duplicates("state_fips").iterrows()}

    rng = np.random.default_rng(43)
    prepared = []
    for did in apportion_df["district_id"].tolist():
        row = apportion_df[apportion_df["district_id"] == did].iloc[0]
        mask = district_ids == did
        if int(mask.sum()) < H.MIN_RESPONDENTS:
            mask = state_masks.get(int(row["state_fips"]), np.zeros(len(district_ids), bool))
            if int(mask.sum()) < H.MIN_RESPONDENTS:
                continue
        n_seats = int(row["seat_count"])
        shares = np.average(prob_matrix[mask], weights=weights[mask], axis=0)
        cands = H.build_district_candidates(
            {f"prob_cluster_{k}": float(shares[k]) for k in range(10)}, n_seats)
        if not cands:
            continue
        scores = H.compute_candidate_scores_prob(prob_matrix[mask], cands)
        ballots = H.generate_ballots(scores, rng, cands)
        prepared.append({
            "did": did, "mask": mask, "codes": [c["code"] for c in cands],
            "n_seats": min(n_seats, len(cands)), "ballots": ballots,
            "first": np.array([b[0].rsplit("_", 1)[0] for b in ballots], dtype=object),
        })
    print(f"  {wyo}: prepared {len(prepared)} districts")
    return prepared


def run_config(prepared, count_weights, depth, published, stale):
    """One (depth, gap) cell. Returns (payload, checked, mismatched)."""
    flows = {"out": defaultdict(lambda: defaultdict(float)), "internal": defaultdict(float),
             "exhausted": defaultdict(float), "moved": defaultdict(float),
             "exhausted_by_origin": defaultdict(float), "ballot_weight": defaultdict(float)}
    origin = {p: defaultdict(float) for p in H.PARTY_CLUSTER}
    seat_counts = {p: 0 for p in H.PARTY_CLUSTER}
    checked = mismatched = 0

    for d in prepared:
        w = count_weights[d["mask"]]
        bal = d["ballots"] if not depth else d["ballots"][:, :depth]
        elected, _, seats = Q.run_stv_instrumented(
            bal, w, d["codes"], d["n_seats"], d["first"], flows)

        got = sorted(c.rsplit("_", 1)[0] for c in elected)
        want = published.get(d["did"])
        if want is not None and d["did"] not in stale:
            checked += 1
            if got != sorted(want):
                mismatched += 1
                if os.environ.get("QF_VERBOSE"):
                    print(f"      MISMATCH {d['did']}: got {got} want {sorted(want)}")
        for s in seats:
            seat_counts[s["party"]] += 1
            for o, v in s["byOrigin"].items():
                origin[s["party"]][o] += v

    def shares(dct, floor=0.002):
        tot = sum(dct.values()) or 1.0
        return {k: round(v / tot, 4) for k, v in sorted(dct.items(), key=lambda kv: -kv[1])
                if v / tot >= floor}

    parties = []
    for p in sorted(origin, key=lambda k: -(origin[k].get(k, 0) / (sum(origin[k].values()) or 1))):
        if not sum(origin[p].values()):
            continue
        tot = sum(origin[p].values())
        parties.append({"party": p, "seats": seat_counts[p],
                        "ownShare": round(origin[p].get(p, 0.0) / tot, 4),
                        "byOrigin": shares(origin[p])})

    transfers = []
    for p in sorted(flows["out"], key=lambda k: -sum(flows["out"][k].values())):
        cross = dict(flows["out"][p])
        ct = sum(cross.values())
        moved = ct + flows["internal"][p] + flows["exhausted"][p]
        if moved <= 0:
            continue
        transfers.append({"party": p, "byDest": shares(cross),
                          "crossShare": round(ct / moved, 4),
                          "internalShare": round(flows["internal"][p] / moved, 4),
                          "exhaustedShare": round(flows["exhausted"][p] / moved, 4)})

    return {"parties": parties, "transfersOut": transfers}, checked, mismatched


def main():
    print("Loading inputs…")
    efa = pd.read_csv(H.EFA_PATH)
    typology = pd.read_csv(H.TYPOLOGY_PATH)
    weights = efa["commonpostweight"].values.astype(np.float64)
    prob_matrix = typology[H.PROB_COLS].values.astype(np.float64)
    # Same turnout construction as build_house_partylist: t + lambda*(1 - t), per respondent.
    t = pd.read_csv(TURNOUT_CSV)["turnout_cluster"].values.astype(float)
    assert len(t) == len(efa), f"turnout rows {len(t)} != data rows {len(efa)}"

    pub = json.loads(PUBLISHED.read_text())
    configs: dict = {}
    total_bad = 0

    for wyo, cfg in WYOMING.items():
        prepared = prepare(wyo, cfg, weights, prob_matrix)
        for dkey, depth in DEPTHS.items():
            for gap in GAPS:
                cw = weights * (t + gap / 100.0 * (1.0 - t))
                block = pub[dkey][wyo][str(gap)]["districts"]
                published = {r["districtId"]: r["stvElected"]
                             for rows in block.values() for r in rows}
                payload, checked, bad = run_config(
                    prepared, cw, depth, published, KNOWN_STALE)
                configs[f"{dkey}|{wyo}|{gap}"] = payload
                total_bad += bad
                flag = "" if not bad else f"  <-- {bad} MISMATCHED"
                print(f"    {dkey:6s} {wyo:6s} gap {gap:2d}: "
                      f"{checked - bad}/{checked} districts reproduce{flag}")

    if total_bad:
        sys.exit(f"ABORT: {total_bad} district mismatches across configurations.")

    OUT_PATH.write_text(json.dumps({
        "meta": {"depths": list(DEPTHS), "wyoming": list(WYOMING), "gaps": GAPS,
                 "default": "top7|double|5"},
        "configs": configs,
    }))
    kb = OUT_PATH.stat().st_size / 1024
    print(f"\nWrote {OUT_PATH.relative_to(BASE)}  ({len(configs)} configurations, {kb:.0f} KB)")


if __name__ == "__main__":
    main()

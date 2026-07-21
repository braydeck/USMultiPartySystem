#!/usr/bin/env python3
"""
build_single_race_data.py
--------------------------
Precompute voter-level data for the Single Race Simulator (viz app).

Each CES respondent (post listwise deletion, N=45,707) is placed in their
real current congressional district (cdid119) and emitted with:
  - commonpostweight
  - the 5 EFA factor scores (FS_F1..FS_F5)

The head-to-head model is the app's canonical ballot model
(generate_factor_deviation_ballots.compute_candidate_scores_hybrid — the scorer
that produced ballots.csv, which drives the House STV, Senate IRV and Presidency
IRV simulations). Each voter ranks all candidates by a hybrid score:

    base candidate:    score = prob_cluster_k                          (GMM posterior)
    variant candidate: score = prob_cluster_k * gauss(variant)/gauss(base)
                       gauss(x) = exp(-||voter - pos_x||^2 / 2σ^2), gauss(base) floored at 1e-10

In a two-way FPTP race the vote goes to whichever of the two candidates ranks
higher — exactly how a vote transfers to its next-preferred surviving candidate
in IRV/STV. No new ranking concept is invented.

To evaluate this in the browser at full precision we ship, per voter, the 10
log-posteriors and the 5 factor scores. The score comparison is done in log space
(underflow-proof, preserves exact ranking):

    logScore(base)    = logprob_k
    logScore(variant) = logprob_k - d_var^2/2σ^2 + min(d_base^2/2σ^2, -log(1e-10))

Candidate positions come from the canonical candidate_factor_centroids.csv (38
candidates incl. OAO) — the same slate ballots.csv was built from.

Row alignment: efa_factor_scores.csv, typology_cluster_assignments.csv and the
listwise-deleted CES .dta share row order (see make_voter_counties.py).

Outputs (viz/src/data/):
  singleRaceVoters.json - { sigma, byCD: { "<fips2>-<dist2>": [[w, f1..f5, lp0..lp9], ...] } }
  singleRaceMeta.json   - sigma, meNe, totalEV, partyClusters, states[], candidates[]
"""

import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from stv_config import DTA_PATH, ITEMS_24  # noqa: E402

EFA_PATH   = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
TYPO_PATH  = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
CAND_PATH  = BASE_DIR / "data" / "outputs" / "factor_deviation" / "candidate_factor_centroids.csv"
OUT_DIR    = BASE_DIR / "viz" / "src" / "data"          # small meta (imported, typed)
PUBLIC_DIR = BASE_DIR / "viz" / "public" / "data"       # large voters file (fetched at runtime)

FACTOR_COLS      = ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]
CAND_FACTOR_COLS = ["F1_security_order", "F2_electoral_skepticism", "F3_government_distrust",
                    "F4_religious_traditionalism", "F5_populist_conservatism"]
PROB_COLS        = [f"prob_cluster_{k}" for k in range(10)]
POSITIONAL_SIGMA = 0.35            # matches generate_factor_deviation_ballots.py
EXPECTED_N       = 45_707
DEC              = 4
LOGPROB_FLOOR    = -700.0          # only replaces log(0)=-inf; preserves full ranking (100% ballots.csv match)

# Party -> GMM cluster index (run_fd_house_stv.PARTY_CLUSTER)
PARTY_CLUSTER = {
    "CON": 0, "LBR": 1, "STY": 2, "NAT": 3, "LIB": 4,
    "POP": 5, "CUP": 6, "OAO": 7, "DSA": 8, "PRG": 9,
}
# Display order left->right (constants/parties.ts F5_ORDER)
PARTY_ORDER = ["PRG", "DSA", "LIB", "LBR", "OAO", "STY", "CUP", "CON", "POP", "NAT"]

# Current Electoral College (2020 census apportionment, used 2024/2028) — 538 total.
STATE_EV = {
    "AL": 9,  "AK": 3,  "AZ": 11, "AR": 6,  "CA": 54, "CO": 10, "CT": 7,  "DE": 3,
    "DC": 3,  "FL": 30, "GA": 16, "HI": 4,  "ID": 4,  "IL": 19, "IN": 11, "IA": 6,
    "KS": 6,  "KY": 8,  "LA": 8,  "ME": 4,  "MD": 10, "MA": 11, "MI": 15, "MN": 10,
    "MS": 6,  "MO": 10, "MT": 4,  "NE": 5,  "NV": 6,  "NH": 4,  "NJ": 14, "NM": 5,
    "NY": 28, "NC": 16, "ND": 3,  "OH": 17, "OK": 7,  "OR": 8,  "PA": 19, "RI": 4,
    "SC": 9,  "SD": 3,  "TN": 11, "TX": 40, "UT": 6,  "VT": 3,  "VA": 13, "WA": 12,
    "WV": 4,  "WI": 10, "WY": 3,
}

FIPS_ABBR = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO", "09": "CT",
    "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI", "16": "ID", "17": "IL",
    "18": "IN", "19": "IA", "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD",
    "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO", "30": "MT", "31": "NE",
    "32": "NV", "33": "NH", "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND",
    "39": "OH", "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA", "54": "WV",
    "55": "WI", "56": "WY",
}
STATE_NAME = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan",
    "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri", "MT": "Montana",
    "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota",
    "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}

# States that split electoral votes by congressional district.
ME_NE = {
    "23": {"statewide": 2, "districts": ["23-01", "23-02"]},           # Maine
    "31": {"statewide": 2, "districts": ["31-01", "31-02", "31-03"]},  # Nebraska
}


def build_candidates() -> list:
    """Canonical FD slate (candidate_factor_centroids.csv) — 38 candidates incl. OAO.
    Ordered by party (left->right) then base-first."""
    cdf = pd.read_csv(CAND_PATH)
    by_code = {}
    for _, r in cdf.iterrows():
        by_code[r["candidate_code"]] = {
            "code": r["candidate_code"], "party": r["party"],
            "axis": r["axis"], "direction": r["direction"],
            "pos": [round(float(r[c]), DEC) for c in CAND_FACTOR_COLS],
        }
    cands = []
    for party in PARTY_ORDER:
        rows = [c for c in by_code.values() if c["party"] == party]
        rows.sort(key=lambda c: (c["axis"] != "base", c["axis"], c["direction"]))
        cands.extend(rows)
    assert len(cands) == len(by_code), "candidate ordering dropped rows"
    return cands


def main():
    assert sum(STATE_EV.values()) == 538, f"EV total is {sum(STATE_EV.values())}, expected 538"

    print("Loading EFA factor scores + typology…")
    efa = pd.read_csv(EFA_PATH)
    typ = pd.read_csv(TYPO_PATH)
    assert len(efa) == len(typ) == EXPECTED_N, "row-count mismatch"
    assert (efa["inputstate"].astype(int).values == typ["inputstate"].astype(int).values).all(), \
        "efa/typology inputstate misalignment"

    print(f"Reading CES .dta for cdid119: {DTA_PATH.name} …")
    try:
        import pyreadstat
    except ImportError:
        print("ERROR: pyreadstat not installed. Run: pip install pyreadstat")
        sys.exit(1)
    read_cols = ["caseid", "inputstate", "cdid119", "commonpostweight"] + ITEMS_24
    dta, _ = pyreadstat.read_dta(str(DTA_PATH), usecols=read_cols)
    mask = dta[ITEMS_24 + ["commonpostweight"]].notna().all(axis=1)
    dta = dta.loc[mask].reset_index(drop=True)
    assert len(dta) == EXPECTED_N, f"post-deletion rows {len(dta)} != {EXPECTED_N}"
    assert (dta["inputstate"].astype(int).values == efa["inputstate"].astype(int).values).all(), \
        "CES/efa inputstate misalignment — row order changed"

    state_fips = efa["inputstate"].astype(int).map(lambda s: f"{s:02d}").values
    dist_num   = dta["cdid119"].astype(int).map(lambda d: f"{d:02d}").values
    cd_id      = np.char.add(np.char.add(state_fips, "-"), dist_num)

    weights = efa["commonpostweight"].astype(float).round(DEC).values
    factors = efa[FACTOR_COLS].astype(float).round(DEC).values
    with np.errstate(divide="ignore"):
        logprob = np.log(typ[PROB_COLS].values.astype(np.float64))
    logprob = np.clip(logprob, LOGPROB_FLOOR, 0.0).round(DEC)

    print("Grouping voters by real congressional district…")
    by_cd: dict[str, list] = {}
    for i in range(EXPECTED_N):
        row = ([float(weights[i])]
               + [float(x) for x in factors[i]]
               + [float(x) for x in logprob[i]])
        by_cd.setdefault(cd_id[i], []).append(row)

    cds_by_state: dict[str, list] = {}
    for cd in by_cd:
        fips = cd.split("-")[0]
        if fips in FIPS_ABBR:
            cds_by_state.setdefault(fips, []).append(cd)
    for fips in cds_by_state:
        cds_by_state[fips].sort()

    states = []
    for fips in sorted(FIPS_ABBR):
        abbr = FIPS_ABBR[fips]
        states.append({
            "fips": fips, "abbr": abbr, "name": STATE_NAME[abbr],
            "ev": STATE_EV[abbr], "cds": cds_by_state.get(fips, []),
        })

    voters_out = {"sigma": POSITIONAL_SIGMA, "byCD": by_cd}
    meta_out = {
        "sigma": POSITIONAL_SIGMA,
        "meNe": ME_NE,
        "totalEV": 538,
        "partyOrder": PARTY_ORDER,
        "partyClusters": PARTY_CLUSTER,
        "states": states,
        "candidates": build_candidates(),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    voters_path = PUBLIC_DIR / "singleRaceVoters.json"
    meta_path   = OUT_DIR / "singleRaceMeta.json"
    voters_path.write_text(json.dumps(voters_out, separators=(",", ":")))
    meta_path.write_text(json.dumps(meta_out, separators=(",", ":")))

    sizes = sorted(len(v) for v in by_cd.values())
    print(f"\nWrote {voters_path}  ({voters_path.stat().st_size/1e6:.2f} MB)")
    print(f"Wrote {meta_path}  ({len(meta_out['candidates'])} candidates)")
    print(f"  districts: {len(by_cd)} | states with CDs: {sum(1 for s in states if s['cds'])}")
    print(f"  per-CD n: min {sizes[0]} | median {sizes[len(sizes)//2]} | max {sizes[-1]}")
    print(f"  EV total: {sum(s['ev'] for s in states)}")


if __name__ == "__main__":
    main()

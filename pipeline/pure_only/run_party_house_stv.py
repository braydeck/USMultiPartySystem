#!/usr/bin/env python3
"""
run_party_house_stv.py
----------------------
House STV using 9 party slates per district.

Each geographically-drawn district runs multi-seat STV with 9 parties.
Parties can win multiple seats proportional to their district vote share.
Uses the same party ballots (GMM posterior Plackett-Luce) as senate/presidential.

Outputs to data/outputs/pure_multi/house/:
  stv_seat_summary.csv          — national seat totals by party × density tier
  stv_results_by_district.csv   — per-district elected parties
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path
from collections import defaultdict

BASE_DIR         = Path(__file__).parent.parent.parent
BALLOTS_PATH     = BASE_DIR / "data" / "outputs" / "pure_multi" / "party_ballots.csv"
EFA_PATH         = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
APPORTIONMENT    = BASE_DIR / "data" / "outputs" / "No_C7_canonical" / "district_apportionment.csv"
VOTER_FIPS_PATH  = BASE_DIR / "data" / "processed" / "voter_county_fips.csv"
COUNTY_DIST_PATH = BASE_DIR / "data" / "processed" / "county_to_district.csv"
OUTPUT_DIR       = BASE_DIR / "data" / "outputs" / "pure_multi" / "house"

sys.path.insert(0, str(Path(__file__).parent.parent))
from party_stv import run_multi_seat_stv

PARTY_CODES = ["CON", "SD", "STY", "NAT", "LIB", "POP", "CUP", "DSA", "PRG"]
PARTY_IDX   = {c: i for i, c in enumerate(PARTY_CODES)}
N_PARTIES   = len(PARTY_CODES)

PARTY_LABELS = {
    0: "Conservative", 1: "Social Democrat", 2: "Solidarity",
    3: "Nationalist",  4: "Liberal",         5: "Populist",
    6: "Civic Union Party",       8: "DSA",             9: "Progressive",
}
CODE_TO_CLUSTER = {"CON":0,"SD":1,"STY":2,"NAT":3,"LIB":4,"POP":5,"CUP":6,"DSA":8,"PRG":9}

MIN_RESPONDENTS = 5


def load_ballots():
    df = pd.read_csv(BALLOTS_PATH, index_col=0)
    N  = len(df)
    ballots = np.zeros((N, N_PARTIES), dtype=np.int8)
    for k in range(N_PARTIES):
        ballots[:, k] = df[f"rank_{k+1}"].map(PARTY_IDX).values.astype(np.int8)
    return ballots


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sep  = "=" * 70
    thin = "-" * 70

    print(sep)
    print("PARTY HOUSE STV — 9 parties per district")
    print(sep)

    # ── Load ─────────────────────────────────────────────────────────────────
    print("\nLoading data…")
    ballots = load_ballots()
    efa     = pd.read_csv(EFA_PATH)
    weights = efa["commonpostweight"].values.astype(np.float64)
    N = len(ballots)

    apportion_df = pd.read_csv(APPORTIONMENT)
    dist_seats   = dict(zip(apportion_df["district_id"], apportion_df["seat_count"]))
    dist_state   = dict(zip(apportion_df["district_id"], apportion_df["state_fips"]))
    dist_abbr    = dict(zip(apportion_df["district_id"], apportion_df["state_abbr"]))
    dist_tier    = dict(zip(apportion_df["district_id"], apportion_df["density_tier"]))

    # ── Voter → district assignment ──────────────────────────────────────────
    if VOTER_FIPS_PATH.exists() and COUNTY_DIST_PATH.exists():
        print("  Assigning voters via county FIPS…")
        voter_fips_df = pd.read_csv(VOTER_FIPS_PATH, index_col=0)
        county_fips   = pd.to_numeric(voter_fips_df["countyfips"], errors="coerce").fillna(0).astype(int)
        voter_counties = county_fips.astype(str).str.zfill(5).values

        county_dist_df = pd.read_csv(COUNTY_DIST_PATH)
        county_to_dist = dict(zip(
            county_dist_df["county_fips5"].astype(str).str.zfill(5),
            county_dist_df["district_id"]
        ))

        state_fallback = {}
        for _, row in apportion_df.iterrows():
            sfips = str(int(row["state_fips"])).zfill(2)
            if sfips not in state_fallback:
                state_fallback[sfips] = row["district_id"]

        district_ids = np.empty(N, dtype=object)
        for i, county in enumerate(voter_counties):
            did = county_to_dist.get(county)
            if did is None:
                did = state_fallback.get(county[:2], "")
            district_ids[i] = did
    else:
        print("  ERROR: geo files not found")
        return

    # ── State-level fallback masks ───────────────────────────────────────────
    state_fips_of_voter = np.array([
        did[:2] if isinstance(did, str) and len(did) >= 2 else ''
        for did in district_ids
    ])
    state_masks = {}
    for _, row in apportion_df.drop_duplicates("state_fips").iterrows():
        sf = str(int(row["state_fips"])).zfill(2)
        state_masks[int(row["state_fips"])] = state_fips_of_voter == sf

    # ── Run STV per district ─────────────────────────────────────────────────
    all_dids = apportion_df["district_id"].tolist()
    print(f"\nRunning STV for {len(all_dids)} districts…")
    print(f"  {'District':<10}  {'St':<4}  {'Tier':<10}  {'N':>5}  {'Seats':>5}  Elected")
    print(f"  {thin}")

    district_results = []
    tier_counts      = defaultdict(lambda: defaultdict(int))
    n_processed = 0
    n_skipped   = 0

    for did in all_dids:
        mask    = district_ids == did
        N_dist  = int(mask.sum())
        n_seats = dist_seats.get(did, 5)
        fips    = int(dist_state.get(did, 0))
        abbr    = dist_abbr.get(did, "??")
        tier    = dist_tier.get(did, "SUBURBAN")

        if N_dist < MIN_RESPONDENTS:
            # Fall back to state
            state_mask = state_masks.get(fips, np.zeros(N, dtype=bool))
            if state_mask.sum() < MIN_RESPONDENTS:
                n_skipped += 1
                print(f"  {did:<10}  {abbr:<4}  {tier:<10}  SKIPPED (N={N_dist})")
                continue
            mask   = state_mask
            N_dist = int(state_mask.sum())

        d_ballots = ballots[mask]
        d_weights = weights[mask]

        result = run_multi_seat_stv(d_ballots, d_weights, N_PARTIES, n_seats, PARTY_CODES)
        seats  = result["seats"]

        # Build elected list (expand multi-seat parties)
        elected = []
        for p_idx in sorted(seats.keys(), key=lambda x: -seats[x]):
            code = PARTY_CODES[p_idx]
            for _ in range(seats[p_idx]):
                elected.append(code)

        for code in elected:
            tier_counts[code][tier] += 1

        district_results.append({
            "district_id":   did,
            "state_fips":    fips,
            "state_abbr":    abbr,
            "density_tier":  tier,
            "seat_count":    n_seats,
            "n_respondents": N_dist,
            "elected":       elected,
        })

        n_processed += 1
        elected_str = ", ".join(elected[:5]) + (" +…" if len(elected) > 5 else "")
        if n_processed <= 20 or n_processed % 20 == 0:
            print(f"  {did:<10}  {abbr:<4}  {tier:<10}  {N_dist:>5}  {n_seats:>5}  {elected_str}")

    print(f"\n  Processed: {n_processed}  |  Skipped: {n_skipped}")

    # ── Save district results ────────────────────────────────────────────────
    dist_rows = []
    for dr in district_results:
        row = {
            "district_id": dr["district_id"],
            "state_fips": dr["state_fips"],
            "state_abbr": dr["state_abbr"],
            "density_tier": dr["density_tier"],
            "seat_count": dr["seat_count"],
            "n_respondents": dr["n_respondents"],
        }
        for i, code in enumerate(dr["elected"]):
            row[f"elected_{i}"] = code
        dist_rows.append(row)

    dist_df = pd.DataFrame(dist_rows)
    dist_df.to_csv(OUTPUT_DIR / "stv_results_by_district.csv", index=False)

    # ── Seat summary ─────────────────────────────────────────────────────────
    summary_rows = []
    total_seats  = 0
    for code in PARTY_CODES:
        urban = tier_counts[code].get("URBAN", 0)
        sub   = tier_counts[code].get("SUBURBAN", 0)
        rural = tier_counts[code].get("RURAL", 0)
        nat   = urban + sub + rural
        total_seats += nat
        if nat > 0:
            cluster = CODE_TO_CLUSTER[code]
            summary_rows.append({
                "party": cluster,
                "party_name": PARTY_LABELS.get(cluster, code),
                "URBAN": urban, "SUBURBAN": sub, "RURAL": rural,
                "NATIONAL": nat, "pct_national": 0,
            })

    for r in summary_rows:
        r["pct_national"] = round(r["NATIONAL"] / total_seats * 100, 2) if total_seats else 0

    summary_rows.sort(key=lambda x: -x["NATIONAL"])
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(OUTPUT_DIR / "stv_seat_summary.csv", index=False)

    # ── Print summary ────────────────────────────────────────────────────────
    print(f"\n{sep}")
    print(f"PARTY HOUSE — SEAT SUMMARY")
    print(f"{sep}\n")
    u_total = sum(r["URBAN"] for r in summary_rows)
    s_total = sum(r["SUBURBAN"] for r in summary_rows)
    r_total = sum(r["RURAL"] for r in summary_rows)

    print(f"  {'Party':<10} {'URBAN':>6} {'SUBURB':>6} {'RURAL':>6} {'TOTAL':>6} {'%':>6}")
    print(f"  {thin}")
    for r in summary_rows:
        print(f"  {r['party_name'][:10]:<10} {r['URBAN']:>6} {r['SUBURBAN']:>6} {r['RURAL']:>6} "
              f"{r['NATIONAL']:>6} {r['pct_national']:>5.1f}%")
    print(f"  {'TOTAL':<10} {u_total:>6} {s_total:>6} {r_total:>6} {total_seats:>6}")

    print(f"\n{sep}")
    print(f"Party house STV complete.")
    print(f"{sep}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
run_house_canonical.py
----------------------
Canonical house election: geographically contiguous multi-member districts,
9 pure parties, Gaussian proximity ballots, Gregory fractional STV.

District size preference:
  Urban: 7-seat preferred
  Suburban / Rural: 5-seat preferred
  3-seat: last resort only (no absorbed 6/8/9-seat single districts)
  ≤4 total seats: single at-large district

When data/processed/voter_county_fips.csv and county_to_district.csv exist,
voters are assigned to districts via their actual county FIPS.  Falls back to
the legacy tier-shuffle assignment if those files are absent.

2020 Census apportionment counts are sourced from stv_config.STATE_POPS.
Factor scores are loaded from efa_factor_scores.csv (NOT the checkpoint).

Outputs to data/outputs/No_C7_canonical/:
  stv_results_by_district.csv  — elected candidates per district
  stv_seat_summary.csv         — seat totals by party × density tier
"""

import sys
import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR        = Path(__file__).parent.parent
CHECKPOINT_PATH = BASE_DIR / "data" / "outputs" / "No_C7_canonical" / "ballots_checkpoint.parquet"
EFA_SCORES_PATH = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
TYPOLOGY_PATH   = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
OUTPUT_DIR       = BASE_DIR / "data" / "outputs" / "No_C7_canonical"
VOTER_FIPS_PATH  = BASE_DIR / "data" / "processed" / "voter_county_fips.csv"
COUNTY_DIST_PATH = BASE_DIR / "data" / "processed" / "county_to_district.csv"

sys.path.insert(0, str(Path(__file__).parent))
from stv_config import STATE_POPS, FIPS_TO_ABBR, POP_PER_SEAT, POP_PER_SEAT_TRIPLE, STATE_URBAN_PCT

FACTOR_COLS      = ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]
POSITIONAL_SIGMA = 0.35
FACTOR_WEIGHTS   = np.array([1.0, 1.0, 1.0, 1.0, 1.0])  # uniform — centroid geometry handles discrimination
MIN_RESPONDENTS  = 5

CANDIDATES = [
    {"name": "CON", "cluster": 0},
    {"name": "SD",  "cluster": 1},
    {"name": "STY", "cluster": 2},
    {"name": "NAT", "cluster": 3},
    {"name": "LIB", "cluster": 4},
    {"name": "REF", "cluster": 5},
    {"name": "CTR", "cluster": 6},
    {"name": "DSA", "cluster": 8},
    {"name": "PRG", "cluster": 9},
]
CAND_NAMES = [c["name"] for c in CANDIDATES]

PARTY_LABELS = {
    0: "Conservative", 1: "Social Democrat", 2: "Solidarity",
    3: "Nationalist",  4: "Liberal",         5: "Reform",
    6: "Center",       8: "DSA",             9: "Progressive",
}
NAME_TO_CLUSTER = {c["name"]: c["cluster"] for c in CANDIDATES}


# ── District apportionment ────────────────────────────────────────────────────

def partition_seats(total: int) -> list:
    """
    Partition total seats into district sizes from {7, 6, 5, 4}.

    Objective (lexicographic):
      1. Minimize 4-seat districts
      2. Maximize 7-seat districts
      3. Minimize 6-seat districts
    States with <=3 total seats get a single at-large district.
    """
    if total <= 3:
        return [total]

    best      = None
    best_key  = None  # (n4, -n7, n6) — minimize lexicographically
    for n7 in range(total // 7, -1, -1):
        rem7 = total - 7 * n7
        for n6 in range(rem7 // 6, -1, -1):
            rem76 = rem7 - 6 * n6
            for n5 in range(rem76 // 5, -1, -1):
                rem = rem76 - 5 * n5
                if rem >= 0 and rem % 4 == 0:
                    n4  = rem // 4
                    key = (n4, -n7, n6)
                    if best_key is None or key < best_key:
                        best_key = key
                        best     = [7]*n7 + [6]*n6 + [5]*n5 + [4]*n4
    return sorted(best, reverse=True) if best else [total]


def _partition_standard(total: int) -> list:
    """Partition seats using {7, 5, 6, 4} for non-urban districts.

    Same logic as partition_seats but produces the preferred distribution for
    standard (non-urban) districts.
    """
    if total <= 0:
        return []
    if total <= 3:
        return [total]

    best = None
    best_key = None
    for n7 in range(total // 7, -1, -1):
        rem7 = total - 7 * n7
        for n5 in range(rem7 // 5, -1, -1):
            rem75 = rem7 - 5 * n5
            for n6 in range(rem75 // 6, -1, -1):
                rem = rem75 - 6 * n6
                if rem >= 0 and rem % 4 == 0:
                    n4 = rem // 4
                    # minimize 4s, maximize 7s, minimize 6s
                    key = (n4, -n7, n6)
                    if best_key is None or key < best_key:
                        best_key = key
                        best = [7]*n7 + [6]*n6 + [5]*n5 + [4]*n4
    return sorted(best, reverse=True) if best else [total]


def _partition_urban(total: int) -> list:
    """Partition seats into urban-sized districts {8, 9, 10}, prefer 9."""
    if total <= 0:
        return []
    if total <= 10:
        return [total]

    n9 = total // 9
    rem = total % 9
    # Handle remainder by adjusting: prefer 9, then 10, then 8
    REMAINDER = {
        0: [],
        1: [10, -9],       # swap one 9 for 10
        2: [10, 10, -9, -9],  # swap two 9s for two 10s (18 → 20)
        3: [10, 10, 10, -9, -9, -9],  # swap three 9s for three 10s (27 → 30)
        4: [10, 10, 10, 10, -9, -9, -9, -9],  # (36 → 40) — only if enough 9s
        5: [10, 10, 10, 10, 10, -9, -9, -9, -9, -9],
        6: [10, 10, 10, 8, -9, -9, -9],  # swap three 9s for three 10s + 8 (27 → 38, net +11) no...
        7: [8, 8, -9],     # swap one 9 for two 8s (9 → 16, net +7)
        8: [8],
    }

    # Simpler approach: greedily fill with 9, then adjust
    if rem == 0:
        return [9] * n9
    elif rem <= 5 and n9 >= rem:
        # Swap 'rem' nines for 'rem' tens
        return [10] * rem + [9] * (n9 - rem)
    elif rem == 6:
        # 6 remaining: could do one extra 9 → swap: (n9-1)*9 + 6 = total - 3, add 9 back...
        # Actually: rem 6 with enough 9s: swap 2 nines (18) → 10+8+6 (24, net +6)
        if n9 >= 2:
            return [10] + [9] * (n9 - 2) + [8] + [6]
        else:
            return [9] * n9 + [6] if n9 > 0 else [6]
    elif rem == 7:
        if n9 >= 1:
            return [10] + [9] * (n9 - 1) + [6]  # swap one 9 → 10+6 (net +7)
        else:
            return [7]
    elif rem == 8:
        return [9] * n9 + [8]
    else:
        return [9] * n9 + [rem] if rem >= 4 else [9] * n9 + [rem]


def partition_seats_triple(total: int, urban_pct: float = 70.0) -> list:
    """
    Partition total seats into district sizes for Triple Wyoming.

    Two-pass approach:
      1. Determine how many seats go to URBAN districts (8, 9, 10)
         based on state's urban population percentage.
      2. Remaining seats go to standard districts (7, 5, 6, 4).

    3-seat districts are NEVER used as partition units.
    States with <=3 total seats → single at-large district.
    States with 4-10 total seats → single district of that size.
    """
    if total <= 3:
        return [total]
    if total <= 10:
        return [total]

    # Below 60% urban → no large districts, all standard (7/5/6/4)
    if urban_pct < 60:
        return _partition_standard(total)

    # Compute urban seat count: higher urban % → more seats in 8-10 districts
    urban_frac = max(0.0, (urban_pct - 40.0) / 100.0)  # 90% urban → 0.50
    urban_seats_target = round(total * urban_frac)

    # Snap urban_seats to a multiple of 9 (preferred urban district size)
    # This avoids awkward remainders
    n_urban_dists = max(0, round(urban_seats_target / 9))
    urban_seats = n_urban_dists * 9  # start with clean 9s

    # Ensure standard remainder is partitionable (>= 4 or == 0)
    standard_seats = total - urban_seats
    while standard_seats > 0 and standard_seats < 4 and n_urban_dists > 0:
        n_urban_dists -= 1
        urban_seats = n_urban_dists * 9
        standard_seats = total - urban_seats

    if n_urban_dists == 0:
        return _partition_standard(total)

    # Adjust: if standard partition would leave a bad remainder,
    # try shifting one 9 → (7 + extra standard seats)
    standard_part = _partition_standard(standard_seats)
    # Check for any district < 5 in the standard part (we want to minimize 4s)
    if any(s <= 4 for s in standard_part) and standard_seats > 0:
        # Try absorbing standard seats into urban: make one 9 bigger (→10)
        # or add standard as an 8, or redistribute
        combined = urban_seats + standard_seats
        # Re-partition the combined total prioritizing fewer 4s:
        # Try (n_urban_dists - 1) 9s + standard of remainder
        for try_n in range(n_urban_dists + 1, 0, -1):
            try_urban = try_n * 9
            try_std = combined - try_urban
            if try_std == 0:
                n_urban_dists = try_n
                standard_part = []
                break
            if try_std >= 5:
                try_std_part = _partition_standard(try_std)
                if all(s >= 5 for s in try_std_part):
                    n_urban_dists = try_n
                    standard_part = try_std_part
                    break
        else:
            # Fallback: try making one urban dist a 10
            if n_urban_dists >= 1 and standard_seats > 0:
                n_urban_dists -= 1
                extra = 9 + standard_seats
                if extra <= 10:
                    standard_part = []
                    n_urban_dists += 1  # restore, but as a 10 handled below
                else:
                    standard_part = _partition_standard(total - n_urban_dists * 9)

    urban_part = [9] * n_urban_dists
    result = urban_part + standard_part
    assert sum(result) == total, f"Partition error: {result} sums to {sum(result)}, expected {total}"
    return sorted(result, reverse=True)


def assign_density_tiers(district_sizes: list, fips: int) -> list:
    """
    Assign URBAN / SUBURBAN / RURAL labels to districts.
    Districts are sorted descending; largest get URBAN first, then SUBURBAN, then RURAL.
    """
    urban_pct = STATE_URBAN_PCT.get(fips, 70.0)
    D = len(district_sizes)

    if D == 1:
        if urban_pct >= 75:
            return ["URBAN"]
        elif urban_pct >= 45:
            return ["SUBURBAN"]
        else:
            return ["RURAL"]

    true_urban_frac = max(0.0, (urban_pct - 30.0) / 100.0)
    suburban_frac   = 0.30
    rural_frac      = max(0.0, 1.0 - urban_pct / 100.0)
    total_frac      = true_urban_frac + suburban_frac + rural_frac or 1.0

    n_u = round(D * true_urban_frac / total_frac)
    n_s = round(D * suburban_frac   / total_frac)
    n_r = D - n_u - n_s

    if n_r < 0: n_s += n_r; n_r = 0
    if n_s < 0: n_u += n_s; n_s = 0
    if n_u < 0: n_u = 0
    while n_u + n_s + n_r < D: n_r += 1
    while n_u + n_s + n_r > D:
        if n_r > 0:   n_r -= 1
        elif n_s > 0: n_s -= 1
        else:         n_u -= 1

    return ["URBAN"] * n_u + ["SUBURBAN"] * n_s + ["RURAL"] * n_r


def run_apportionment(pop_per_seat=POP_PER_SEAT, partition_fn=None) -> pd.DataFrame:
    """Compute district apportionment for all 51 states."""
    if partition_fn is None:
        partition_fn = partition_seats
    rows = []
    for fips in sorted(STATE_POPS.keys()):
        total  = max(1, round(STATE_POPS[fips] / pop_per_seat))
        abbr   = FIPS_TO_ABBR.get(fips, str(fips))
        urban_pct = STATE_URBAN_PCT.get(fips, 70.0)
        import inspect
        # Pass urban_pct if the partition function accepts it
        if 'urban_pct' in inspect.signature(partition_fn).parameters:
            sizes = partition_fn(total, urban_pct=urban_pct)
        else:
            sizes = partition_fn(total)
        tiers  = assign_density_tiers(sizes, fips)
        for idx, (size, tier) in enumerate(zip(sizes, tiers), start=1):
            rows.append({
                "state_fips":   fips,
                "state_abbr":   abbr,
                "district_id":  f"{fips:02d}-{idx:02d}",
                "seat_count":   size,
                "density_tier": tier,
            })
    return pd.DataFrame(rows)


# ── Voter → district assignment ───────────────────────────────────────────────

TIER_FALLBACK = {
    "URBAN":    ["URBAN", "SUBURBAN", "RURAL"],
    "SUBURBAN": ["SUBURBAN", "URBAN", "RURAL"],
    "RURAL":    ["RURAL", "SUBURBAN", "URBAN"],
}


def assign_voters_to_districts(apportion: pd.DataFrame,
                                inputstates: np.ndarray,
                                density_tiers: np.ndarray) -> np.ndarray:
    """
    Return array of district_id strings (one per voter row).
    Within each (state, tier) pool, voters are split evenly across same-tier districts.
    Voters whose tier has no district in their state fall back to SUBURBAN then URBAN.
    """
    voter_district = np.full(len(inputstates), "", dtype=object)

    for fips in sorted(STATE_POPS.keys()):
        state_app  = apportion[apportion["state_fips"] == fips]
        tier_dists = {}
        for _, row in state_app.iterrows():
            tier_dists.setdefault(row["density_tier"], []).append(row["district_id"])

        for voter_tier in ["URBAN", "SUBURBAN", "RURAL"]:
            voter_idx = np.where((inputstates == fips) & (density_tiers == voter_tier))[0]
            if len(voter_idx) == 0:
                continue

            # Find available districts for this tier (with fallback)
            dists_for_tier = None
            for candidate_tier in TIER_FALLBACK[voter_tier]:
                if candidate_tier in tier_dists:
                    dists_for_tier = tier_dists[candidate_tier]
                    break
            if dists_for_tier is None:
                dists_for_tier = [state_app.iloc[0]["district_id"]]  # guaranteed fallback

            n_dists = len(dists_for_tier)
            for rank, did in enumerate(dists_for_tier):
                chunk = len(voter_idx) // n_dists
                start = rank * chunk
                end   = start + chunk if rank < n_dists - 1 else len(voter_idx)
                voter_district[voter_idx[start:end]] = did

    return voter_district


def assign_voters_to_districts_geo(voter_counties: np.ndarray,
                                    county_to_dist: dict,
                                    inputstates: np.ndarray,
                                    apportion: pd.DataFrame) -> np.ndarray:
    """Assign each voter to a district via county FIPS lookup.
    Voters in counties not in county_to_dist fall back to the first district
    in their state.
    """
    state_fallback: dict = {}
    for _, row in apportion.iterrows():
        state_fallback.setdefault(int(row["state_fips"]), row["district_id"])

    voter_district = np.empty(len(voter_counties), dtype=object)
    for i, (county, state) in enumerate(zip(voter_counties, inputstates)):
        did = county_to_dist.get(county)
        voter_district[i] = did if did else state_fallback.get(int(state), "")
    return voter_district


# ── Centroid computation ──────────────────────────────────────────────────────

def compute_cluster_centroids(efa_df: pd.DataFrame,
                              typology_df: pd.DataFrame) -> np.ndarray:
    """Weighted mean of FS_F1–FS_F5 per cluster (0–9). Returns (10, 5)."""
    weights  = efa_df["commonpostweight"].values
    clusters = typology_df["cluster"].values.astype(int)
    centroids = np.zeros((10, 5), dtype=np.float64)
    for k in range(10):
        mask = clusters == k
        w_k  = weights[mask]
        if w_k.sum() > 0:
            for f, col in enumerate(FACTOR_COLS):
                centroids[k, f] = np.average(efa_df[col].values[mask], weights=w_k)
    return centroids


# ── Ballot generation ─────────────────────────────────────────────────────────

def score_candidates(voter_factors: np.ndarray,
                     cand_positions: np.ndarray) -> np.ndarray:
    diff = voter_factors[:, None, :] - cand_positions[None, :, :]
    return np.exp(-((diff ** 2) * FACTOR_WEIGHTS).sum(axis=2) / (2.0 * POSITIONAL_SIGMA ** 2))


def generate_ballots(scores: np.ndarray,
                     cand_arr: np.ndarray,
                     rng: np.random.Generator) -> np.ndarray:
    """Deterministic ranking: sort candidates by score descending."""
    N, M    = scores.shape
    ballots = np.empty((N, M), dtype=object)
    for i in range(N):
        order = np.argsort(-scores[i])
        ballots[i] = cand_arr[order]
    return ballots


# ── Gregory STV ──────────────────────────────────────────────────────────────

def first_surviving_choice(ballots: np.ndarray, active: set) -> np.ndarray:
    N, M   = ballots.shape
    result = np.empty(N, dtype=object)
    for i in range(N):
        result[i] = "__exhausted__"
        for j in range(M):
            if ballots[i, j] in active:
                result[i] = ballots[i, j]
                break
    return result


def run_stv(ballots: np.ndarray, weights: np.ndarray,
            cand_codes: list, n_seats: int) -> list:
    """Gregory fractional STV; returns elected candidate codes in election order."""
    active     = set(cand_codes)
    ballot_wts = weights.astype(float).copy()
    total_v    = float(weights.sum())
    quota      = total_v / (n_seats + 1) + 1
    elected: list = []

    while len(elected) < n_seats and active:
        remaining = n_seats - len(elected)
        if len(active) <= remaining:
            elected.extend(sorted(active))
            break

        fsc    = first_surviving_choice(ballots, active)
        totals = {c: 0.0 for c in active}
        for code, w in zip(fsc, ballot_wts):
            if code in totals:
                totals[code] += w

        over_quota = sorted(
            [c for c in active if totals[c] >= quota],
            key=lambda c: (-totals[c], c),
        )
        if over_quota:
            winner = over_quota[0]
            sf     = (totals[winner] - quota) / totals[winner]
            elected.append(winner)
            for i in range(len(fsc)):
                if fsc[i] == winner:
                    ballot_wts[i] *= sf
            active.discard(winner)
        else:
            active.discard(min(active, key=lambda c: (totals[c], c)))

    return elected


# ── Main ─────────────────────────────────────────────────────────────────────

def main(output_dir=None, pop_per_seat=POP_PER_SEAT, partition_fn=None, label="CANONICAL"):
    if output_dir is None:
        output_dir = OUTPUT_DIR
    else:
        output_dir = Path(output_dir)
    if partition_fn is None:
        partition_fn = partition_seats

    rng = np.random.default_rng(42)
    output_dir.mkdir(parents=True, exist_ok=True)

    sep  = "=" * 70
    thin = "-" * 70
    print(sep)
    print(f"{label} HOUSE STV  —  9 parties · Gaussian proximity · 2020 Census")
    print(sep)

    # ── Load data ──────────────────────────────────────────────────────────────
    print("\nLoading EFA factor scores…")
    efa           = pd.read_csv(EFA_SCORES_PATH)
    voter_factors = efa[FACTOR_COLS].values.astype(np.float64)
    weights       = efa["commonpostweight"].values.astype(np.float64)
    inputstates   = efa["inputstate"].values.astype(int)

    print("Loading density tiers from checkpoint…")
    checkpoint    = pd.read_parquet(CHECKPOINT_PATH, columns=["density_tier"])
    assert len(checkpoint) == len(efa), \
        f"Row count mismatch: checkpoint={len(checkpoint)}, efa={len(efa)}"
    density_tiers = checkpoint["density_tier"].values

    print("Loading typology for cluster centroids…")
    typology       = pd.read_csv(TYPOLOGY_PATH)
    centroids      = compute_cluster_centroids(efa, typology)
    cand_positions = np.array([centroids[c["cluster"]] for c in CANDIDATES])  # (9, 5)
    cand_arr       = np.array(CAND_NAMES, dtype=object)

    # ── Apportionment ──────────────────────────────────────────────────────────
    print("\nRunning apportionment…")
    apportion    = run_apportionment(pop_per_seat=pop_per_seat, partition_fn=partition_fn)
    total_seats  = int(apportion["seat_count"].sum())
    n_districts  = len(apportion)

    apportion.to_csv(output_dir / "district_apportionment.csv", index=False)
    print(f"  {apportion['state_fips'].nunique()} states  |  {n_districts} districts  |  {total_seats} seats")
    size_dist = apportion["seat_count"].value_counts().sort_index()
    for sz, cnt in size_dist.items():
        print(f"    {sz}-seat: {cnt} districts")
    tier_dist = apportion["density_tier"].value_counts()
    for tier, cnt in tier_dist.items():
        print(f"    {tier}: {cnt} districts ({cnt/n_districts*100:.1f}%)")

    # ── Voter assignment ───────────────────────────────────────────────────────
    print("\nAssigning voters to districts…")
    # Triple Wyoming uses its own county-to-district mapping if available
    county_dist_path = (BASE_DIR / "data" / "processed" / "county_to_district_triple.csv"
                        if pop_per_seat == POP_PER_SEAT_TRIPLE else COUNTY_DIST_PATH)
    if VOTER_FIPS_PATH.exists() and county_dist_path.exists():
        print(f"  Using geographic county FIPS assignment ({county_dist_path.name})…")
        voter_fips_df  = pd.read_csv(VOTER_FIPS_PATH, index_col=0)
        voter_counties = voter_fips_df["countyfips"].astype(str).str.zfill(5).values
        county_dist_df = pd.read_csv(county_dist_path)
        county_to_dist = dict(zip(
            county_dist_df["county_fips5"].astype(str).str.zfill(5),
            county_dist_df["district_id"]
        ))
        voter_district = assign_voters_to_districts_geo(
            voter_counties, county_to_dist, inputstates, apportion
        )
    else:
        print("  Warning: geo files not found — falling back to tier-shuffle assignment")
        voter_district = assign_voters_to_districts(apportion, inputstates, density_tiers)
    unassigned = (voter_district == "").sum()
    if unassigned:
        print(f"  Warning: {unassigned} voters unassigned — check state FIPS coverage")

    # ── Save checkpoint (for FD and pure_multi scripts to reuse) ──────────────
    ckpt_df = pd.DataFrame({"district_id": voter_district, "density_tier": density_tiers})
    ckpt_df.to_parquet(output_dir / "ballots_checkpoint.parquet", index=False)
    print(f"  Saved ballots_checkpoint.parquet ({len(ckpt_df):,} voters)")

    # ── District STV loop ──────────────────────────────────────────────────────
    all_dids = apportion["district_id"].tolist()
    dist_meta = {
        row["district_id"]: {
            "state_fips":   int(row["state_fips"]),
            "state_abbr":   row["state_abbr"],
            "density_tier": row["density_tier"],
            "seat_count":   int(row["seat_count"]),
        }
        for _, row in apportion.iterrows()
    }

    print(f"\nRunning STV for {len(all_dids)} districts…")
    print(f"  {'District':<10}  {'St':<4}  {'Tier':<10}  {'N':>5}  {'Seats':>5}  Elected")
    print(f"  {thin}")

    district_results = []
    n_processed = 0
    n_skipped   = 0

    for did in all_dids:
        meta    = dist_meta[did]
        mask    = voter_district == did
        N_dist  = int(mask.sum())
        n_seats = meta["seat_count"]
        abbr    = meta["state_abbr"]
        tier    = meta["density_tier"]

        if N_dist < MIN_RESPONDENTS:
            n_skipped += 1
            print(f"  {did:<10}  {abbr:<4}  {tier:<10}  SKIPPED (N={N_dist})")
            continue

        d_factors = voter_factors[mask]
        d_weights = weights[mask]
        scores    = score_candidates(d_factors, cand_positions)
        ballots   = generate_ballots(scores, cand_arr, rng)
        elected   = run_stv(ballots, d_weights, CAND_NAMES, n_seats)

        district_results.append({
            "district_id":   did,
            "state_fips":    meta["state_fips"],
            "state_abbr":    abbr,
            "density_tier":  tier,
            "seat_count":    n_seats,
            "n_respondents": N_dist,
            "elected":       elected,
        })
        n_processed += 1

        if n_processed <= 10 or n_processed % 30 == 0:
            elec_str = ", ".join(elected[:5])
            if len(elected) > 5:
                elec_str += f" +{len(elected)-5}"
            print(f"  {did:<10}  {abbr:<4}  {tier:<10}  {N_dist:>5}  {n_seats:>5}  {elec_str}")

    print(f"\n  Processed: {n_processed}  |  Skipped: {n_skipped}")

    # ── Save per-district results ──────────────────────────────────────────────
    dist_rows = []
    for r in district_results:
        row = {k: r[k] for k in
               ["district_id", "state_fips", "state_abbr", "density_tier",
                "seat_count", "n_respondents"]}
        for k, code in enumerate(r["elected"]):
            row[f"elected_{k}"] = code
        dist_rows.append(row)

    dist_df = pd.DataFrame(dist_rows).sort_values(["state_fips", "district_id"])
    dist_df.to_csv(output_dir / "stv_results_by_district.csv", index=False)
    print(f"\nSaved stv_results_by_district.csv  ({len(dist_df)} districts)")

    # ── Seat summary ───────────────────────────────────────────────────────────
    tier_counts = {name: {"URBAN": 0, "SUBURBAN": 0, "RURAL": 0} for name in CAND_NAMES}
    for r in district_results:
        for code in r["elected"]:
            if code in tier_counts:
                tier_counts[code][r["density_tier"]] += 1

    summary_rows = []
    for c in CANDIDATES:
        name    = c["name"]
        cluster = c["cluster"]
        tc      = tier_counts[name]
        total   = tc["URBAN"] + tc["SUBURBAN"] + tc["RURAL"]
        summary_rows.append({
            "party":      cluster,
            "party_name": PARTY_LABELS.get(cluster, name),
            "URBAN":      tc["URBAN"],
            "SUBURBAN":   tc["SUBURBAN"],
            "RURAL":      tc["RURAL"],
            "NATIONAL":   total,
        })

    summary_df = pd.DataFrame(summary_rows).sort_values("NATIONAL", ascending=False)
    grand_total = summary_df["NATIONAL"].sum()
    summary_df["pct_national"] = (summary_df["NATIONAL"] / grand_total * 100).round(2)
    summary_df.to_csv(output_dir / "stv_seat_summary.csv", index=False)
    print(f"Saved stv_seat_summary.csv  ({len(summary_df)} parties)")

    # ── Summary table ──────────────────────────────────────────────────────────
    print(f"\n{sep}")
    print("CANONICAL HOUSE — SEAT SUMMARY BY PARTY")
    print(sep)
    print(f"  {'Party':<6}  {'URBAN':>6}  {'SUBURBAN':>8}  {'RURAL':>6}  {'TOTAL':>6}  {'%':>6}")
    print(f"  {thin}")
    for _, row in summary_df.iterrows():
        pct = row["NATIONAL"] / grand_total * 100
        print(f"  {row['party_name'][:6]:<6}  {int(row['URBAN']):>6}  "
              f"{int(row['SUBURBAN']):>8}  {int(row['RURAL']):>6}  "
              f"{int(row['NATIONAL']):>6}  {pct:>5.1f}%")
    print(f"  {'TOTAL':<6}  {int(summary_df['URBAN'].sum()):>6}  "
          f"{int(summary_df['SUBURBAN'].sum()):>8}  "
          f"{int(summary_df['RURAL'].sum()):>6}  {int(grand_total):>6}  100.0%")

    print(f"\n{sep}")
    print(f"{label} house STV complete.")
    print(sep)


TRIPLE_OUTPUT_DIR = BASE_DIR / "data" / "outputs" / "No_C7_triple"


def main_triple():
    main(
        output_dir=TRIPLE_OUTPUT_DIR,
        pop_per_seat=POP_PER_SEAT_TRIPLE,
        partition_fn=partition_seats_triple,
        label="TRIPLE WYOMING",
    )


if __name__ == "__main__":
    if "--triple" in sys.argv:
        main_triple()
    else:
        main()

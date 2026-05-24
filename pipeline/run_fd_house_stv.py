#!/usr/bin/env python3
"""
run_fd_house_stv.py
--------------------
House general-election STV per district using 71 factor-deviation candidates.

Reuses district assignments from the canonical ballot checkpoint.
Generates new Gaussian-proximity Plackett-Luce ballots for all 71 FD candidates.
Runs STV (Gregory fractional surplus) to fill seat_count seats per district.

Outputs to data/outputs/factor_deviation/house/:
  stv_results_by_district.csv  — per-district elected candidates
  stv_seat_summary.csv         — seat counts by party/variant × density tier
"""

import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR        = Path(__file__).parent.parent
CHECKPOINT_PATH = BASE_DIR / "data" / "outputs" / "No_C7_canonical" / "ballots_checkpoint.parquet"
APPORTIONMENT   = BASE_DIR / "data" / "outputs" / "No_C7_canonical" / "district_apportionment.csv"
EFA_SCORES_PATH = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
CANDIDATES_PATH = BASE_DIR / "data" / "outputs" / "factor_deviation" / "candidate_factor_centroids.csv"
OUTPUT_DIR      = BASE_DIR / "data" / "outputs" / "factor_deviation" / "house"

VOTER_FACTOR_COLS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]
CAND_FACTOR_COLS  = [
    "F1_security_order", "F2_electoral_skepticism", "F3_government_distrust",
    "F4_religious_traditionalism", "F5_populist_conservatism",
]
POSITIONAL_SIGMA = 0.35
FACTOR_WEIGHTS   = np.array([1.000, 0.535, 0.081, 0.436, 1.050])  # η²-based: F1 F2 F3 F4 F5
MIN_RESPONDENTS  = 5


# ── Ballot generation ────────────────────────────────────────────────────────

def score_candidates(voter_factors: np.ndarray,
                     cand_positions: np.ndarray,
                     sigma: float = POSITIONAL_SIGMA) -> np.ndarray:
    diff = voter_factors[:, None, :] - cand_positions[None, :, :]
    return np.exp(-((diff ** 2) * FACTOR_WEIGHTS).sum(axis=2) / (2.0 * sigma ** 2))


def generate_ballots(scores: np.ndarray,
                     cand_arr: np.ndarray,
                     rng: np.random.Generator) -> np.ndarray:
    N, M     = scores.shape
    EPSILON  = 1e-10
    ballots  = np.empty((N, M), dtype=object)
    for i in range(N):
        probs  = scores[i] + EPSILON
        probs /= probs.sum()
        ballots[i] = cand_arr[rng.choice(M, size=M, replace=False, p=probs)]
    return ballots


# ── STV engine (Gregory fractional surplus) ──────────────────────────────────

def first_surviving_choice(ballots_arr: np.ndarray, active_set: set) -> np.ndarray:
    N, M   = ballots_arr.shape
    result = np.empty(N, dtype=object)
    for i in range(N):
        result[i] = "__exhausted__"
        for j in range(M):
            if ballots_arr[i, j] in active_set:
                result[i] = ballots_arr[i, j]
                break
    return result


def compute_vote_totals(fsc: np.ndarray, weights: np.ndarray, active_set: set) -> dict:
    totals = {c: 0.0 for c in active_set}
    for code, w in zip(fsc, weights):
        if code in totals:
            totals[code] += w
    return totals


def droop_quota(total_votes: float, n_seats: int) -> float:
    return total_votes / (n_seats + 1) + 1


def run_stv(ballots_arr: np.ndarray, weights: np.ndarray,
            cand_codes: list, n_seats: int) -> list:
    """Run STV; return list of elected candidate codes (in election order)."""
    active      = set(cand_codes)
    ballot_wts  = weights.astype(float).copy()
    total_votes = float(weights.sum())
    quota       = droop_quota(total_votes, n_seats)
    elected: list = []

    while len(elected) < n_seats and active:
        remaining = n_seats - len(elected)
        if len(active) <= remaining:
            elected.extend(sorted(active))
            active.clear()
            break

        fsc    = first_surviving_choice(ballots_arr, active)
        totals = compute_vote_totals(fsc, ballot_wts, active)

        over_quota = sorted(
            [c for c in active if totals[c] >= quota],
            key=lambda c: (-totals[c], c),
        )
        if over_quota:
            winner         = over_quota[0]
            surplus_factor = (totals[winner] - quota) / totals[winner]
            elected.append(winner)
            for i in range(len(fsc)):
                if fsc[i] == winner:
                    ballot_wts[i] *= surplus_factor
            active.discard(winner)
        else:
            loser = min(active, key=lambda c: (totals[c], c))
            active.discard(loser)

    return elected


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    rng = np.random.default_rng(42)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sep  = "=" * 70
    thin = "-" * 70

    print(sep)
    print("FD HOUSE STV  —  71 factor-deviation candidates, 180 districts")
    print(sep)

    # ── Load data ─────────────────────────────────────────────────────────────
    print("\nLoading EFA factor scores…")
    efa           = pd.read_csv(EFA_SCORES_PATH)
    voter_factors = efa[VOTER_FACTOR_COLS].values.astype(np.float64)
    weights       = efa["commonpostweight"].values.astype(np.float64)

    print("Loading district assignments from canonical checkpoint…")
    checkpoint    = pd.read_parquet(CHECKPOINT_PATH)
    assert len(checkpoint) == len(efa), "Row count mismatch between EFA scores and checkpoint"
    district_ids  = checkpoint["district_id"].values
    density_tiers = checkpoint["density_tier"].values
    print(f"  {len(efa):,} respondents assigned to {checkpoint['district_id'].nunique()} districts")

    print("Loading district apportionment…")
    apportion_df  = pd.read_csv(APPORTIONMENT)
    dist_seats    = dict(zip(apportion_df["district_id"], apportion_df["seat_count"]))
    dist_state    = dict(zip(apportion_df["district_id"], apportion_df["state_fips"]))
    dist_abbr     = dict(zip(apportion_df["district_id"], apportion_df["state_abbr"]))
    dist_tier     = dict(zip(apportion_df["district_id"], apportion_df["density_tier"]))

    print("Loading FD candidates…")
    cand_df        = pd.read_csv(CANDIDATES_PATH)
    cand_codes     = cand_df["candidate_code"].tolist()
    cand_arr       = np.array(cand_codes, dtype=object)
    cand_positions = cand_df[CAND_FACTOR_COLS].values.astype(np.float64)
    cand_meta      = {row["candidate_code"]: {"party": row["party"], "axis": row["axis"],
                                               "direction": row["direction"]}
                      for _, row in cand_df.iterrows()}
    M = len(cand_codes)
    print(f"  {M} candidates across {cand_df['party'].nunique()} parties")

    # ── District loop ─────────────────────────────────────────────────────────
    all_districts = sorted(apportion_df["district_id"].tolist())
    print(f"\nRunning STV for {len(all_districts)} districts…")
    print(f"  {'District':<10}  {'St':<4}  {'Tier':<10}  {'N':>5}  {'Seats':>5}  Elected candidates")
    print(f"  {thin}")

    district_results  = []
    n_processed       = 0
    n_skipped         = 0

    for did in all_districts:
        mask          = district_ids == did
        N_dist        = int(mask.sum())
        n_seats       = dist_seats.get(did, 5)
        state_fips    = dist_state.get(did, 0)
        state_abbr    = dist_abbr.get(did, "??")
        tier          = dist_tier.get(did, "SUBURBAN")

        if N_dist < MIN_RESPONDENTS:
            n_skipped += 1
            print(f"  {did:<10}  {state_abbr:<4}  SKIPPED (N={N_dist})")
            continue

        # Score and generate ballots
        d_factors = voter_factors[mask]
        d_weights = weights[mask]
        scores    = score_candidates(d_factors, cand_positions)
        ballots   = generate_ballots(scores, cand_arr, rng)

        # STV
        elected = run_stv(ballots, d_weights, cand_codes, n_seats)

        district_results.append({
            "district_id":  did,
            "state_fips":   int(state_fips),
            "state_abbr":   state_abbr,
            "density_tier": tier,
            "seat_count":   n_seats,
            "n_respondents": N_dist,
            "elected":      elected,
        })

        n_processed += 1
        if n_processed % 20 == 0 or n_processed <= 10:
            elec_str = ", ".join(elected[:5])
            if len(elected) > 5:
                elec_str += f" … +{len(elected)-5}"
            print(f"  {did:<10}  {state_abbr:<4}  {tier:<10}  {N_dist:>5}  {n_seats:>5}  {elec_str}")

    print(f"\n  Processed: {n_processed} districts  |  Skipped: {n_skipped}")

    # ── Save per-district results ─────────────────────────────────────────────
    dist_rows = []
    for r in district_results:
        row = {
            "district_id":   r["district_id"],
            "state_fips":    r["state_fips"],
            "state_abbr":    r["state_abbr"],
            "density_tier":  r["density_tier"],
            "seat_count":    r["seat_count"],
            "n_respondents": r["n_respondents"],
        }
        for k, code in enumerate(r["elected"]):
            row[f"elected_{k}"] = code
        dist_rows.append(row)

    dist_df = pd.DataFrame(dist_rows).sort_values(["state_fips", "district_id"])
    dist_df.to_csv(OUTPUT_DIR / "stv_results_by_district.csv", index=False)
    print(f"\nSaved stv_results_by_district.csv  ({len(dist_df)} districts)")

    # ── Seat summary ──────────────────────────────────────────────────────────
    tier_counts: dict = {code: {"URBAN": 0, "SUBURBAN": 0, "RURAL": 0} for code in cand_codes}
    for r in district_results:
        tier = r["density_tier"]
        for code in r["elected"]:
            if tier in tier_counts.get(code, {}):
                tier_counts[code][tier] += 1

    summary_rows = []
    for code in cand_codes:
        tc    = tier_counts[code]
        urban = tc["URBAN"]
        sub   = tc["SUBURBAN"]
        rural = tc["RURAL"]
        total = urban + sub + rural
        if total == 0:
            continue
        meta = cand_meta.get(code, {"party": "?", "axis": "?", "direction": "?"})
        summary_rows.append({
            "candidate_code": code,
            "party":          meta["party"],
            "axis":           meta["axis"],
            "direction":      meta["direction"],
            "URBAN":          urban,
            "SUBURBAN":       sub,
            "RURAL":          rural,
            "NATIONAL":       total,
        })

    summary_df = pd.DataFrame(summary_rows).sort_values("NATIONAL", ascending=False)
    total_seats = summary_df["NATIONAL"].sum()
    summary_df["pct_national"] = (summary_df["NATIONAL"] / total_seats * 100).round(2)
    summary_df.to_csv(OUTPUT_DIR / "stv_seat_summary.csv", index=False)
    print(f"Saved stv_seat_summary.csv  ({len(summary_df)} candidates with seats)")

    # ── Summary by party ──────────────────────────────────────────────────────
    print(f"\n{sep}")
    print("FD HOUSE — SEAT SUMMARY BY PARTY")
    print(sep)
    party_summary = (
        summary_df.groupby("party")[["URBAN", "SUBURBAN", "RURAL", "NATIONAL"]]
        .sum()
        .sort_values("NATIONAL", ascending=False)
    )
    print(f"\n  {'Party':<6}  {'URBAN':>6}  {'SUBURBAN':>8}  {'RURAL':>6}  {'TOTAL':>6}  {'%':>6}")
    print(f"  {'-'*6}  {'-'*6}  {'-'*8}  {'-'*6}  {'-'*6}  {'-'*6}")
    for party, row in party_summary.iterrows():
        pct = row["NATIONAL"] / total_seats * 100
        print(f"  {party:<6}  {int(row['URBAN']):>6}  {int(row['SUBURBAN']):>8}  "
              f"{int(row['RURAL']):>6}  {int(row['NATIONAL']):>6}  {pct:>5.1f}%")
    print(f"  {'TOTAL':<6}  {int(party_summary['URBAN'].sum()):>6}  "
          f"{int(party_summary['SUBURBAN'].sum()):>8}  "
          f"{int(party_summary['RURAL'].sum()):>6}  {int(total_seats):>6}  100.0%")

    print(f"\n  Top elected variants:")
    for _, row in summary_df.head(15).iterrows():
        print(f"    {row['candidate_code']:<20}  {row['party']:<6}  "
              f"axis={row['axis']:<5}  dir={row['direction']:<5}  "
              f"seats={int(row['NATIONAL'])}")

    print(f"\n{sep}")
    print("FD house STV complete.")
    print(sep)


if __name__ == "__main__":
    main()

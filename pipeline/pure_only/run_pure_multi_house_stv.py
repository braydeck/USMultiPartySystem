#!/usr/bin/env python3
"""
run_pure_multi_house_stv.py
----------------------------
House STV per district using state-proportional intra-party candidate pools.

Reuses district assignments and density tiers from the canonical ballot checkpoint.
For each state, builds a variable-length candidate pool based on that state's
cluster shares (same thresholds as run_pure_multi_senate.py):
  >= 12% share → 3 candidates (prominence 0.40 / 0.35 / 0.25)
  >=  5% share → 2 candidates (prominence 0.60 / 0.40)
  >=  1% share → 1 candidate  (prominence 1.00)
  <   1% share → 0 candidates (party doesn't run in that state)

All districts within a state share the same candidate pool; voters are
assigned to districts by density tier (URBAN / SUBURBAN / RURAL) as stored
in the canonical checkpoint.

Outputs to data/outputs/pure_multi/house/:
  stv_seat_summary.csv        — seat counts by party × density tier
                                (format matches No_C7_canonical/stv_seat_summary.csv)
  stv_results_by_district.csv — per-district elected party names
                                (elected_k values are base party codes, not candidate codes)
"""

import numpy as np
import pandas as pd
from pathlib import Path

import os
import sys

sys.path.insert(0, str(Path(__file__).parent))
from turnout_weights import turnout_multiplier, output_tree, TURNOUT_WEIGHT

BASE_DIR         = Path(__file__).parent.parent.parent
NO_STY           = os.environ.get("NO_STY") == "1"
_TREE            = output_tree("pure_multi_nosty" if NO_STY else "pure_multi")
CHECKPOINT_PATH  = BASE_DIR / "data" / "outputs" / "No_C7_canonical" / "ballots_checkpoint.parquet"
APPORTIONMENT    = BASE_DIR / "data" / "outputs" / "No_C7_canonical" / "district_apportionment.csv"
EFA_PATH         = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
TYPOLOGY_PATH    = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
OUTPUT_DIR       = BASE_DIR / "data" / "outputs" / _TREE / "house"
VOTER_FIPS_PATH  = BASE_DIR / "data" / "processed" / "voter_county_fips.csv"
COUNTY_DIST_PATH = BASE_DIR / "data" / "processed" / "county_to_district.csv"
SPLIT_OVERRIDE_PATH     = BASE_DIR / "pipeline" / "county_split_overrides.csv"

# Triple Wyoming variants
CHECKPOINT_PATH_TRIPLE  = BASE_DIR / "data" / "outputs" / "No_C7_triple" / "ballots_checkpoint.parquet"
APPORTIONMENT_TRIPLE    = BASE_DIR / "data" / "outputs" / "No_C7_triple" / "district_apportionment.csv"
OUTPUT_DIR_TRIPLE       = BASE_DIR / "data" / "outputs" / output_tree("pure_multi_triple") / "house"
COUNTY_DIST_PATH_TRIPLE = BASE_DIR / "data" / "processed" / "county_to_district_triple.csv"

# ── Ballot-generation constants (must match generate_pure_multi_ballots.py) ───
POSITIONAL_SIGMA = 0.35
FACTOR_WEIGHTS   = np.array([1.0, 1.0, 1.0, 1.0, 1.0])  # uniform — centroid geometry handles discrimination
FACTOR_COLS      = ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]
PROB_COLS        = [f"prob_cluster_{k}" for k in range(10)]

# ── Droop-based candidate pool ────────────────────────────────────────────────
# Prominence weights for k candidates (declining, reflecting name recognition)
PROMINENCE_BY_K: dict[int, list[float]] = {
    1: [1.00],
    2: [0.60, 0.40],
    3: [0.40, 0.35, 0.25],
    4: [0.32, 0.28, 0.22, 0.18],
    5: [0.28, 0.24, 0.20, 0.16, 0.12],
}


MIN_SHARE = 0.00   # every party fields at least 1 candidate in every district

def n_candidates_for_district(share: float, n_seats: int) -> int:
    """Droop-based candidate count for one party in one district.

    A party expecting to win k seats runs k+1 candidates (strategic overshoot),
    capped at floor(n_seats/2)+1.  Below half a Droop quota the party still
    runs 1 candidate if they have >=2% share (prevents seat shortfalls in small
    or sparse districts).
    """
    droop = 1.0 / (n_seats + 1)
    if share < droop / 2:
        return 1 if share >= MIN_SHARE else 0
    expected = int(share / droop)          # floor(share / droop)
    return min(expected + 1, n_seats // 2 + 1)

# ── Party → cluster index (C7/BLB excluded unless INCLUDE_C7) ─────────────────
PARTY_CLUSTER = {
    "CON": 0,
    "LBR":  1,
    "STY": 2,
    "NAT": 3,
    "LIB": 4,
    "POP": 5,
    "CUP": 6,
    "OAO": 7,
    "DSA": 8,
    "PRG": 9,
}
if NO_STY:
    PARTY_CLUSTER = {k: v for k, v in PARTY_CLUSTER.items() if k != "STY"}

PARTY_LABELS = {
    0: "Conservative", 1: "Labor", 2: "Solidarity",
    3: "Nationalist",  4: "Liberal",         5: "Populist",
    6: "Civic Union Party", 7: "Order and Opportunity Party", 8: "DSA", 9: "Progressive",
}

MIN_RESPONDENTS = 5


# ── Per-district candidate pool ───────────────────────────────────────────────

def build_district_candidates(cluster_shares: dict, n_seats: int) -> list:
    """Build district-specific candidate list using Droop-based quotas.

    Returns a list of dicts: {code, party, cluster, prominence}.
    """
    candidates = []
    for party, cluster_idx in PARTY_CLUSTER.items():
        share = cluster_shares.get(f"prob_cluster_{cluster_idx}", 0.0)
        k = n_candidates_for_district(share, n_seats)
        if k == 0:
            continue
        prominences = PROMINENCE_BY_K[k]
        for i, prom in enumerate(prominences, start=1):
            candidates.append({
                "code":       f"{party}_{i}",
                "party":      party,
                "cluster":    cluster_idx,
                "prominence": prom,
            })
    return candidates


# ── Ballot generation ─────────────────────────────────────────────────────────

def compute_cluster_centroids(efa_df: pd.DataFrame, typology_df: pd.DataFrame) -> np.ndarray:
    """Weighted mean of FS_F1–FS_F5 per cluster (0–9). Returns (10, 5)."""
    weights   = efa_df["commonpostweight"].values
    clusters  = typology_df["cluster"].values.astype(int)
    centroids = np.zeros((10, 5), dtype=np.float64)
    for k in range(10):
        mask = clusters == k
        w_k  = weights[mask]
        if w_k.sum() > 0:
            for f, col in enumerate(FACTOR_COLS):
                centroids[k, f] = np.average(efa_df[col].values[mask], weights=w_k)
    return centroids


def compute_candidate_scores(voter_factors: np.ndarray,
                              cluster_centroids: np.ndarray,
                              candidates: list) -> np.ndarray:
    """Gaussian proximity × prominence weight. Returns (N, n_cands) score matrix."""
    positions  = np.array([cluster_centroids[c["cluster"]] for c in candidates])
    prominence = np.array([c["prominence"] for c in candidates])
    diff       = voter_factors[:, None, :] - positions[None, :, :]
    dist_sq    = ((diff ** 2) * FACTOR_WEIGHTS).sum(axis=2)
    proximity  = np.exp(-dist_sq / (2.0 * POSITIONAL_SIGMA ** 2))
    return proximity * prominence[None, :]


def compute_candidate_scores_prob(prob_matrix: np.ndarray, candidates: list) -> np.ndarray:
    """Equal PL scores for same-party candidates (prob_cluster_k only).
    Prominence ordering is applied after PL sampling in generate_ballots()."""
    n_cands = len(candidates)
    scores  = np.zeros((len(prob_matrix), n_cands))
    for j, cand in enumerate(candidates):
        scores[:, j] = prob_matrix[:, cand["cluster"]]
    return scores


def generate_ballots(scores: np.ndarray, rng: np.random.Generator,
                     candidates: list) -> np.ndarray:
    """Deterministic ranking with within-party prominence ordering.

    Candidates are ranked by score descending. Within each party,
    candidates are ordered by prominence (_1 before _2 before _3).

    Returns (N, n_cands) object array of candidate code strings.
    """
    N       = len(scores)
    n_cands = len(candidates)

    cand_codes = [c["code"] for c in candidates]

    party_groups: dict = {}
    for idx, cand in enumerate(candidates):
        party = cand["party"]
        if party not in party_groups:
            party_groups[party] = []
        party_groups[party].append(idx)
    multi_parties = [idxs for idxs in party_groups.values() if len(idxs) > 1]

    ballots = np.empty((N, n_cands), dtype=object)

    for i in range(N):
        ballot = np.argsort(-scores[i])

        # Assign prominence labels within each party's positions.
        # _1 gets the best position, _2 next, _3 worst.
        rank_of = {int(ballot[r]): r for r in range(n_cands)}
        for party_idxs in multi_parties:
            positions = sorted(rank_of[idx] for idx in party_idxs)
            for k, pos in enumerate(positions):
                ballot[pos] = party_idxs[k]

        ballots[i] = [cand_codes[int(idx)] for idx in ballot]

    return ballots


# ── STV engine (Gregory fractional surplus) ───────────────────────────────────

def first_surviving_choice(ballots_arr: np.ndarray, active_set: set) -> np.ndarray:
    N      = len(ballots_arr)
    result = np.empty(N, dtype=object)
    for i in range(N):
        result[i] = "__exhausted__"
        for code in ballots_arr[i]:
            if code in active_set:
                result[i] = code
                break
    return result


def run_stv(ballots_arr: np.ndarray, weights: np.ndarray,
            cand_codes: list, n_seats: int) -> tuple:
    """Gregory fractional STV. Returns (elected codes in election order, n_below_quota),
    where n_below_quota counts seats filled by the field-collapse branch below the Droop
    quota — the classic 'exhausted-ballots weaken late seats' failure mode."""
    active      = set(cand_codes)
    ballot_wts  = weights.astype(float).copy()
    total_votes = float(weights.sum())
    quota       = total_votes / (n_seats + 1) + 1
    elected: list = []
    below_quota   = 0

    while len(elected) < n_seats and active:
        remaining = n_seats - len(elected)
        if len(active) <= remaining:
            # Field collapsed (too few continuing candidates): elect the rest regardless of
            # quota. Count how many are actually below quota at this point.
            fsc = first_surviving_choice(ballots_arr, active)
            totals = {c: 0.0 for c in active}
            for code, w in zip(fsc, ballot_wts):
                if code in totals:
                    totals[code] += w
            for c in sorted(active):
                elected.append(c)
                if totals.get(c, 0.0) < quota:
                    below_quota += 1
            active.clear()
            break

        fsc    = first_surviving_choice(ballots_arr, active)
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

    return elected, below_quota


# ── Main ──────────────────────────────────────────────────────────────────────

def main(apportionment_path=None, checkpoint_path=None, county_dist_path=None,
         output_dir=None, label="PURE MULTI", ballot_depth=0):
    if apportionment_path is None:
        apportionment_path = APPORTIONMENT
    if checkpoint_path is None:
        checkpoint_path = CHECKPOINT_PATH
    if county_dist_path is None:
        county_dist_path = COUNTY_DIST_PATH
    if output_dir is None:
        output_dir = OUTPUT_DIR
    else:
        output_dir = Path(output_dir)
    # Ballot depth: 0 = full ranking (exhaustive); N = voters rank only their top N candidates.
    # Truncated ballots can exhaust in STV, so this is what makes exhaustion/representation realistic.
    if ballot_depth and ballot_depth > 0:
        output_dir = output_dir.parent.parent / (output_dir.parent.name + f"_top{ballot_depth}") / output_dir.name

    rng      = np.random.default_rng(42)
    rng_prob = np.random.default_rng(43)
    output_dir.mkdir(parents=True, exist_ok=True)

    sep  = "=" * 70
    thin = "-" * 70

    print(sep)
    print(f"{label} HOUSE STV  —  state-proportional candidate pools")
    print(sep)

    # ── Load data ──────────────────────────────────────────────────────────────
    print("\nLoading EFA factor scores…")
    efa           = pd.read_csv(EFA_PATH)
    typology      = pd.read_csv(TYPOLOGY_PATH)
    assert len(efa) == len(typology), f"Row mismatch: {len(efa)} vs {len(typology)}"
    voter_factors = efa[FACTOR_COLS].values.astype(np.float64)
    weights       = efa["commonpostweight"].values.astype(np.float64)
    # Population weights build the district candidate pool (party field fixed across
    # cells); count_weights add turnout so only vote-counting reflects participation.
    count_weights = weights * turnout_multiplier(len(efa))

    print("Loading district apportionment…")
    apportion_df = pd.read_csv(apportionment_path)
    dist_seats   = dict(zip(apportion_df["district_id"], apportion_df["seat_count"]))
    dist_state   = dict(zip(apportion_df["district_id"], apportion_df["state_fips"]))
    dist_abbr    = dict(zip(apportion_df["district_id"], apportion_df["state_abbr"]))
    dist_tier    = dict(zip(apportion_df["district_id"], apportion_df["density_tier"]))

    if VOTER_FIPS_PATH.exists() and county_dist_path.exists():
        print(f"Assigning voters to districts via county FIPS ({county_dist_path.name})…")
        voter_fips_df  = pd.read_csv(VOTER_FIPS_PATH, index_col=0)
        county_fips    = pd.to_numeric(voter_fips_df["countyfips"], errors="coerce").fillna(0).astype(int)
        voter_counties = county_fips.astype(str).str.zfill(5).values

        county_dist_df = pd.read_csv(county_dist_path)
        county_to_dist = dict(zip(
            county_dist_df["county_fips5"].astype(str).str.zfill(5),
            county_dist_df["district_id"]
        ))

        state_fallback: dict = {}
        for _, row in apportion_df.iterrows():
            sfips = str(int(row["state_fips"])).zfill(2)
            if sfips not in state_fallback:
                state_fallback[sfips] = row["district_id"]

        # Sub-county override. The draw assigns whole counties, which cannot express a county whose
        # population exceeds one district: Maricopa (04013) justifies ~11.6 seats at 380k/seat but
        # lands entirely in 04-01 (7 seats), leaving 04-03 (5 seats) with no counties and no
        # respondents — it then falls back to counting Arizona statewide. This splits such counties
        # on the respondent's real 119th-Congress district. Counties absent from the file keep their
        # whole-county assignment, so this is inert for the other 3,141.
        split_override: dict = {}
        if SPLIT_OVERRIDE_PATH.exists():
            _so = pd.read_csv(SPLIT_OVERRIDE_PATH)
            for _, row in _so.iterrows():
                key = (str(row["county_fips5"]).zfill(5), int(row["cd119"]))
                split_override[key] = row["district_id"]
        voter_cds = (pd.to_numeric(voter_fips_df["cd119"], errors="coerce")
                     if "cd119" in voter_fips_df.columns else pd.Series(index=voter_fips_df.index, dtype=float))
        voter_cds = voter_cds.values

        district_ids = np.empty(len(voter_counties), dtype=object)
        n_split = 0
        for i, county in enumerate(voter_counties):
            did = None
            if split_override:
                cd = voter_cds[i]
                if cd == cd:  # not NaN
                    did = split_override.get((county, int(cd)))
                    if did is not None:
                        n_split += 1
            if did is None:
                did = county_to_dist.get(county)
            if did is None:
                did = state_fallback.get(county[:2], "")
            district_ids[i] = did
        if n_split:
            print(f"  sub-county override applied to {n_split:,} respondents")
        n_unique = len({d for d in district_ids if d})
        print(f"  {len(efa):,} respondents assigned to {n_unique} districts")
    else:
        print("Geo files not found — falling back to checkpoint…")
        checkpoint   = pd.read_parquet(checkpoint_path, columns=["district_id", "density_tier"])
        assert len(checkpoint) == len(efa), \
            f"Row count mismatch: checkpoint={len(checkpoint)}, efa={len(efa)}"
        district_ids = checkpoint["district_id"].values
        print(f"  {len(efa):,} respondents in {checkpoint['district_id'].nunique()} districts")

    print("Computing cluster centroids…")
    cluster_centroids = compute_cluster_centroids(efa, typology)
    prob_matrix       = typology[PROB_COLS].values.astype(np.float64)

    # ── Pre-compute state-level voter masks for fallback ──────────────────────
    state_fips_of_voter = np.array([
        did[:2] if isinstance(did, str) and len(did) >= 2 else ''
        for did in district_ids
    ])
    state_voter_masks: dict = {}
    for _, srow in apportion_df.drop_duplicates("state_fips").iterrows():
        sfips_int = int(srow["state_fips"])
        state_voter_masks[sfips_int] = state_fips_of_voter == str(sfips_int).zfill(2)

    # ── District STV loop ──────────────────────────────────────────────────────
    all_dids = apportion_df["district_id"].tolist()
    print(f"\nRunning STV for {len(all_dids)} districts…")
    print(f"  {'District':<10}  {'St':<4}  {'Tier':<10}  {'N':>5}  {'Seats':>5}  "
          f"{'Cands':>5}  Elected")
    print(f"  {thin}")

    district_results: list = []
    tier_counts: dict = {party: {"URBAN": 0, "SUBURBAN": 0, "RURAL": 0}
                         for party in PARTY_CLUSTER}
    tier_counts_prob: dict = {party: {"URBAN": 0, "SUBURBAN": 0, "RURAL": 0}
                              for party in PARTY_CLUSTER}
    district_results_prob: list = []
    n_processed = 0
    n_skipped   = 0

    for did in all_dids:
        mask      = district_ids == did
        N_dist    = int(mask.sum())
        n_seats   = dist_seats.get(did, 5)
        fips      = int(dist_state.get(did, 0))
        abbr      = dist_abbr.get(did, "??")
        tier      = dist_tier.get(did, "SUBURBAN")

        if N_dist < MIN_RESPONDENTS:
            # Fall back to all state respondents rather than skipping
            state_mask = state_voter_masks.get(fips, np.zeros(len(district_ids), dtype=bool))
            N_state = int(state_mask.sum())
            if N_state < MIN_RESPONDENTS:
                n_skipped += 1
                print(f"  {did:<10}  {abbr:<4}  {tier:<10}  SKIPPED (N={N_dist}, state N={N_state})")
                continue
            mask   = state_mask
            N_dist = N_state

        d_factors       = voter_factors[mask]
        d_weights       = weights[mask]          # population — district pool composition
        d_count_weights = count_weights[mask]    # turnout-scaled — STV vote counting
        d_prob_matrix   = prob_matrix[mask]

        # Build district-specific candidate pool using Droop-based thresholds
        d_shares    = np.average(d_prob_matrix, weights=d_weights, axis=0)
        shares_dict = {f"prob_cluster_{k}": float(d_shares[k]) for k in range(10)}
        candidates  = build_district_candidates(shares_dict, n_seats)
        if not candidates:
            n_skipped += 1
            print(f"  {did:<10}  {abbr:<4}  {tier:<10}  SKIPPED (no candidates at district shares)")
            continue

        cand_codes  = [c["code"] for c in candidates]
        n_seats_eff = min(n_seats, len(candidates))

        scores    = compute_candidate_scores_prob(d_prob_matrix, candidates)
        ballots   = generate_ballots(scores, rng, candidates)
        elected, _ = run_stv(ballots, d_count_weights, cand_codes, n_seats_eff)

        # Tally by base party (strip _N suffix)
        elected_parties = [code.rsplit("_", 1)[0] for code in elected]
        for party in elected_parties:
            if party in tier_counts and tier in tier_counts[party]:
                tier_counts[party][tier] += 1

        district_results.append({
            "district_id":   did,
            "state_fips":    fips,
            "state_abbr":    abbr,
            "density_tier":  tier,
            "seat_count":    n_seats_eff,
            "n_respondents": N_dist,
            "n_candidates":  len(candidates),
            "elected":       elected_parties,
        })

        # ── Prob-cluster scoring variant ───────────────────────────────────────
        prob_scores    = compute_candidate_scores_prob(d_prob_matrix, candidates)
        prob_ballots   = generate_ballots(prob_scores, rng_prob, candidates)
        # Truncate to the top-`ballot_depth` preferences for the STV count; truncated ballots
        # exhaust when all ranked candidates are eliminated (they stop transferring).
        bal_stv        = prob_ballots if not ballot_depth else prob_ballots[:, :ballot_depth]
        prob_elected, prob_below = run_stv(bal_stv, d_count_weights, cand_codes, n_seats_eff)

        # ── Representation metrics (canonical prob variant) ────────────────────
        # non-first-choice: ballot's first choice is not an election winner.
        # unrepresented:    none of the ballot's top-K ranked candidates won, where
        #                   K = min(seats, ballot_depth) — under truncation you only have `depth`.
        elset = set(prob_elected)
        dcap = ballot_depth if ballot_depth else 10 ** 9
        K = min(n_seats_eff, dcap)
        vw = nfc_w = unrep_w = 0.0
        for i in range(len(prob_ballots)):
            wt = float(d_count_weights[i]); vw += wt
            b = prob_ballots[i]
            if b[0] not in elset:
                nfc_w += wt
            if not any(code in elset for code in b[:K]):
                unrep_w += wt

        prob_elected_parties = [code.rsplit("_", 1)[0] for code in prob_elected]
        for party in prob_elected_parties:
            if party in tier_counts_prob and tier in tier_counts_prob[party]:
                tier_counts_prob[party][tier] += 1

        district_results_prob.append({
            "district_id":   did,
            "state_fips":    fips,
            "state_abbr":    abbr,
            "density_tier":  tier,
            "seat_count":    n_seats_eff,
            "n_respondents": N_dist,
            "n_candidates":  len(candidates),
            "elected":       prob_elected_parties,
            "vote_weight":   round(vw, 4),
            "nonfirst_weight": round(nfc_w, 4),
            "unrep_weight":  round(unrep_w, 4),
            "below_quota_seats": prob_below,
        })
        n_processed += 1

        if n_processed <= 10 or n_processed % 30 == 0:
            elec_str = ", ".join(elected_parties[:5])
            if len(elected_parties) > 5:
                elec_str += f" +{len(elected_parties)-5}"
            print(f"  {did:<10}  {abbr:<4}  {tier:<10}  {N_dist:>5}  "
                  f"{n_seats_eff:>5}  {len(candidates):>5}  {elec_str}")

    print(f"\n  Processed: {n_processed} districts  |  Skipped: {n_skipped}")

    # ── Save per-district results ──────────────────────────────────────────────
    def _dist_rows(results):
        rows = []
        for r in results:
            row = {
                "district_id":   r["district_id"],
                "state_fips":    r["state_fips"],
                "state_abbr":    r["state_abbr"],
                "density_tier":  r["density_tier"],
                "seat_count":    r["seat_count"],
                "n_respondents": r["n_respondents"],
                "n_candidates":  r["n_candidates"],
            }
            for k, party in enumerate(r["elected"]):
                row[f"elected_{k}"] = party
            rows.append(row)
        return rows

    # prob → canonical; gaussian → reference
    dist_df_prob = pd.DataFrame(_dist_rows(district_results_prob)).sort_values(["state_fips", "district_id"])
    dist_df_prob.to_csv(output_dir / "stv_results_by_district.csv", index=False)
    print(f"\nSaved stv_results_by_district.csv (prob — canonical)  ({len(dist_df_prob)} districts)")

    dist_df = pd.DataFrame(_dist_rows(district_results)).sort_values(["state_fips", "district_id"])
    dist_df.to_csv(output_dir / "stv_results_by_district_gauss.csv", index=False)
    print(f"Saved stv_results_by_district_gauss.csv  ({len(dist_df)} districts)")

    # ── Representation metrics (non-first-choice / unrepresented) ───────────────
    rep_df = pd.DataFrame([{
        "district_id":     r["district_id"],
        "state_fips":      r["state_fips"],
        "seat_count":      r["seat_count"],
        "vote_weight":     r["vote_weight"],
        "nonfirst_weight": r["nonfirst_weight"],
        "unrep_weight":    r["unrep_weight"],
        "below_quota_seats": r["below_quota_seats"],
    } for r in district_results_prob]).sort_values(["state_fips", "district_id"])
    rep_df.to_csv(output_dir / "stv_representation_by_district.csv", index=False)
    tvw = rep_df["vote_weight"].sum()
    print(f"Saved stv_representation_by_district.csv  |  non-first-choice "
          f"{rep_df['nonfirst_weight'].sum()/tvw*100:.1f}%  unrepresented {rep_df['unrep_weight'].sum()/tvw*100:.1f}%")

    # ── Seat summary (format matches No_C7_canonical/stv_seat_summary.csv) ────
    def _build_summary(tc_dict):
        total = sum(tc["URBAN"] + tc["SUBURBAN"] + tc["RURAL"] for tc in tc_dict.values())
        rows = []
        for party, cluster_idx in PARTY_CLUSTER.items():
            tc    = tc_dict[party]
            urban = tc["URBAN"]
            sub   = tc["SUBURBAN"]
            rural = tc["RURAL"]
            t     = urban + sub + rural
            if t == 0:
                continue
            rows.append({
                "party":        cluster_idx,
                "party_name":   PARTY_LABELS.get(cluster_idx, party),
                "URBAN":        urban,
                "SUBURBAN":     sub,
                "RURAL":        rural,
                "NATIONAL":     t,
                "pct_national": round(t / total * 100, 2) if total else 0.0,
            })
        return pd.DataFrame(rows).sort_values("NATIONAL", ascending=False), total

    # prob → canonical; gaussian → reference
    summary_df_prob, total_seats_prob = _build_summary(tier_counts_prob)
    summary_df_prob.to_csv(output_dir / "stv_seat_summary.csv", index=False)
    print(f"Saved stv_seat_summary.csv (prob — canonical)  ({len(summary_df_prob)} parties with seats)")

    summary_df, total_seats = _build_summary(tier_counts)
    summary_df.to_csv(output_dir / "stv_seat_summary_gauss.csv", index=False)
    print(f"Saved stv_seat_summary_gauss.csv  ({len(summary_df)} parties with seats)")

    # ── Summary table ──────────────────────────────────────────────────────────
    print(f"\n{sep}")
    print("PURE MULTI HOUSE — SEAT SUMMARY BY PARTY (prob-cluster, canonical)")
    print(sep)
    print(f"\n  {'Party':<6}  {'URBAN':>6}  {'SUBURBAN':>8}  {'RURAL':>6}  "
          f"{'TOTAL':>6}  {'%':>6}")
    print(f"  {thin}")
    for _, row in summary_df_prob.iterrows():
        pct = row["NATIONAL"] / total_seats_prob * 100 if total_seats_prob else 0
        print(f"  {str(row['party_name'])[:6]:<6}  {int(row['URBAN']):>6}  "
              f"{int(row['SUBURBAN']):>8}  {int(row['RURAL']):>6}  "
              f"{int(row['NATIONAL']):>6}  {pct:>5.1f}%")
    print(f"  {'TOTAL':<6}  "
          f"{sum(int(r['URBAN']) for _, r in summary_df_prob.iterrows()):>6}  "
          f"{sum(int(r['SUBURBAN']) for _, r in summary_df_prob.iterrows()):>8}  "
          f"{sum(int(r['RURAL']) for _, r in summary_df_prob.iterrows()):>6}  "
          f"{int(total_seats_prob):>6}  100.0%")

    print(f"\n{sep}")
    print(f"{label} house STV complete.")
    print(sep)


if __name__ == "__main__":
    depth = 0
    for a in sys.argv:
        if a.startswith("--depth="):
            depth = int(a.split("=", 1)[1])
    if "--triple" in sys.argv:
        main(
            apportionment_path=APPORTIONMENT_TRIPLE,
            checkpoint_path=CHECKPOINT_PATH_TRIPLE,
            county_dist_path=COUNTY_DIST_PATH_TRIPLE,
            output_dir=OUTPUT_DIR_TRIPLE,
            label="PURE MULTI TRIPLE WYOMING",
            ballot_depth=depth,
        )
    else:
        main(ballot_depth=depth)

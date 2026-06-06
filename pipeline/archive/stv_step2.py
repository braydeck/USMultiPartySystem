"""
stv_step2.py
------------
Data loading, DTA join, density-tier assignment, ballot generation.

Outputs:
  - Returns merged DataFrame with columns including:
      district_id, commonpostweight, ballot (ranked list of 0..9)
  - Optionally saves intermediate parquet for checkpoint resumption
"""

import numpy as np
import pandas as pd
import pyreadstat

from stv_config import (
    TYPOLOGY_PATH, DTA_PATH, OUTPUT_DIR,
    ITEMS_24, DTA_AUX_COLS, DTA_READ_COLS,
    PROB_COLS, N_PARTIES,
    STATE_URBAN_PCT, URBANCITY_TO_TIER,
)

EXPECTED_N = 45_707
RNG_SEED   = 42


# ── 1. Load typology cluster assignments ──────────────────────────────────────

def load_typology() -> pd.DataFrame:
    df = pd.read_csv(TYPOLOGY_PATH)
    assert len(df) == EXPECTED_N, \
        f"typology_cluster_assignments.csv has {len(df)} rows, expected {EXPECTED_N}"
    assert all(c in df.columns for c in PROB_COLS), \
        f"Missing prob_cluster columns in typology CSV"
    assert "commonpostweight" in df.columns and "inputstate" in df.columns
    return df


# ── 2. Load supplemental columns from DTA and positional-align ───────────────

def load_dta_aux() -> pd.DataFrame:
    """
    Read only the 29 needed columns from the 947 MB DTA.
    Apply the same listwise deletion as efa_update.py lines 291-293 to
    recover the exact 45,707-row subset in the same row order.
    """
    print("  Reading DTA (29 columns)... ", end="", flush=True)
    df_dta, _ = pyreadstat.read_dta(
        str(DTA_PATH),
        usecols=DTA_READ_COLS,
        apply_value_formats=False,
    )
    print(f"done. Raw rows: {len(df_dta):,}")

    # Replicate exact listwise deletion from efa_update.py
    deletion_cols = ITEMS_24 + ["commonpostweight"]
    mask = df_dta[deletion_cols].notna().all(axis=1)
    df_aux = df_dta.loc[mask, ["caseid", "faminc_new", "region", "urbancity"]].reset_index(drop=True)

    assert len(df_aux) == EXPECTED_N, (
        f"DTA listwise deletion yielded {len(df_aux)} rows, expected {EXPECTED_N}. "
        f"Row alignment broken — check ITEMS_24 list matches efa_update.py exactly."
    )
    print(f"  DTA rows after listwise deletion: {len(df_aux):,}  ✓")
    return df_aux


# ── 3. Assign density tier to each respondent ────────────────────────────────

def assign_density_tiers_respondents(
    df: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Assign each respondent a density tier (URBAN / SUBURBAN / RURAL).

    Primary signal: CES `urbancity` variable
      1 = City     → URBAN
      2 = Suburb   → SUBURBAN
      3 = Town     → SUBURBAN  (treated as suburban)
      4 = Rural    → RURAL
      5 = Other/NA → probabilistic assignment from state Census urban %

    Missing / unknown urbancity: probabilistic assignment calibrated to
    each state's Census urban percentage.
    """
    df = df.copy()

    # Direct mapping for known urbancity values
    df["density_tier"] = df["urbancity"].map(URBANCITY_TO_TIER)

    # Probabilistic assignment for urbancity == 5 or NaN
    unknown_mask = df["density_tier"].isna()
    n_unknown = unknown_mask.sum()
    if n_unknown > 0:
        unknown_idx = df.index[unknown_mask]
        for idx in unknown_idx:
            state = int(df.at[idx, "inputstate"])
            urban_pct = STATE_URBAN_PCT.get(state, 70.0) / 100.0

            # Three-tier probabilities matching assign_density_tiers in step1
            true_urban = max(0.0, (urban_pct * 100 - 30) / 100.0)
            suburban   = 0.30
            rural      = max(0.0, 1.0 - urban_pct)
            total      = true_urban + suburban + rural
            if total < 1e-9:
                total = 1.0
            probs = np.array([true_urban, suburban, rural]) / total
            tier  = rng.choice(["URBAN", "SUBURBAN", "RURAL"], p=probs)
            df.at[idx, "density_tier"] = tier

        print(f"  Probabilistic tier assignment for {n_unknown} respondents "
              f"with unknown urbancity")

    return df


# ── 4. Assign respondents to specific districts ───────────────────────────────

def assign_to_districts(
    df: pd.DataFrame,
    apportionment: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    """
    Assign each respondent to a specific district_id.

    For each state + density_tier combination, collect the list of matching
    district_ids from the apportionment table, then randomly assign respondents
    (uniform draw with replacement) to those districts.

    Fallback: if no district of the respondent's tier exists in their state,
    use any district in the state.
    """
    df = df.copy()

    # Build lookup: (state_fips, density_tier) → list of district_ids
    tier_map = (
        apportionment
        .groupby(["state_fips", "density_tier"])["district_id"]
        .apply(list)
        .to_dict()
    )
    # Fallback: state_fips → all districts
    state_map = (
        apportionment
        .groupby("state_fips")["district_id"]
        .apply(list)
        .to_dict()
    )

    assignments = []
    fallback_count = 0

    for _, row in df.iterrows():
        state = int(row["inputstate"])
        tier  = row["density_tier"]
        key   = (state, tier)

        if key in tier_map and tier_map[key]:
            options = tier_map[key]
        else:
            # Fallback: any district in the state
            options = state_map.get(state, [])
            fallback_count += 1
            if not options:
                # State not in apportionment (should not happen)
                assignments.append(None)
                continue

        assignments.append(rng.choice(options))

    df["district_id"] = assignments

    if fallback_count:
        print(f"  WARNING: {fallback_count} respondents used state-level fallback "
              f"(no matching density tier district in state)")

    n_null = df["district_id"].isna().sum()
    if n_null:
        print(f"  WARNING: {n_null} respondents could not be assigned a district")

    return df


# ── 5. Generate Plackett-Luce ranked ballots ──────────────────────────────────

def generate_ballots(
    df: pd.DataFrame,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Generate a ranked ballot for every respondent using Plackett-Luce sampling.

    At each stage, the next rank is drawn proportional to the remaining
    probability mass. numpy's rng.choice(replace=False) implements this exactly:
    it performs successive weighted sampling without replacement (Plackett-Luce).

    Returns:
        ndarray of shape (N, 10), dtype int8
        Row i: ranked list of party indices, position 0 = most preferred
    """
    prob_matrix = df[PROB_COLS].values.astype(np.float64)   # (N, 10)
    N           = len(df)
    EPSILON     = 1e-10   # floor to prevent np.random.choice from choking on ~0

    ballots = np.zeros((N, N_PARTIES), dtype=np.int8)

    for i in range(N):
        probs    = prob_matrix[i] + EPSILON
        probs   /= probs.sum()
        ballots[i] = rng.choice(N_PARTIES, size=N_PARTIES, replace=False, p=probs)

    return ballots


# ── Main entry point ──────────────────────────────────────────────────────────

def load_and_prepare(apportionment: pd.DataFrame) -> pd.DataFrame:
    """
    Full Step 2 pipeline. Returns the working DataFrame with:
        - All typology columns
        - caseid, faminc_new, region, urbancity (from DTA)
        - density_tier
        - district_id
        - ballot  (object column: list of 10 party indices)
    """
    rng = np.random.default_rng(seed=RNG_SEED)

    # 1. Load typology CSV
    print("  Loading typology cluster assignments...")
    df_typo = load_typology()

    # 2. Load and join DTA aux columns
    print("  Loading DTA supplemental columns...")
    df_aux = load_dta_aux()
    df = pd.concat([df_typo.reset_index(drop=True), df_aux], axis=1)

    # Quick sanity: caseid should be unique
    if df["caseid"].duplicated().any():
        n_dup = df["caseid"].duplicated().sum()
        print(f"  WARNING: {n_dup} duplicate caseids after join — check alignment")

    # 3. Assign density tiers
    print("  Assigning density tiers...")
    df = assign_density_tiers_respondents(df, rng)

    # 4. Assign to districts
    print("  Assigning respondents to districts...")
    df = assign_to_districts(df, apportionment, rng)

    # 5. Generate ranked ballots
    print("  Generating Plackett-Luce ranked ballots...")
    ballots = generate_ballots(df, rng)
    df["ballot"] = list(ballots)

    # Verification
    valid_districts = set(apportionment["district_id"])
    assigned = df["district_id"].dropna()
    unknown_districts = set(assigned) - valid_districts
    if unknown_districts:
        print(f"  WARNING: {len(unknown_districts)} unknown district_ids assigned")

    tier_counts = df["density_tier"].value_counts()
    print(f"\n  Tier distribution (respondents):")
    for t, n in tier_counts.items():
        print(f"    {t}: {n:,} ({n/len(df)*100:.1f}%)")

    dist_counts = df["district_id"].value_counts()
    print(f"\n  Districts with respondents: {dist_counts.count()} / {len(apportionment)}")
    print(f"  Respondents per district — min: {dist_counts.min()}, "
          f"median: {dist_counts.median():.0f}, max: {dist_counts.max()}")

    return df


if __name__ == "__main__":
    import os
    from stv_step1 import run_apportionment

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("=" * 60)
    print("STEP 2: BALLOT GENERATION")
    print("=" * 60)

    apportionment = run_apportionment()
    df = load_and_prepare(apportionment)
    print(f"\n  Total respondents with ballots: {len(df):,}")
    print(f"  Sample ballot[0]: {df['ballot'].iloc[0]}")

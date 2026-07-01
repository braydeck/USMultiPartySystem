#!/usr/bin/env python3
"""
generate_factor_deviation_ballots.py
--------------------------------------
Generate ranked ballots for 71 factor-deviation (FD) candidates using
Plackett-Luce sampling from each respondent's 5-D factor position.

The slate = 9 base party candidates + 62 factor-deviation variants:
  - 4 axes: SO (F1), AE (F2), RT (F4; STY/CUP/POP/CON only), PC (F5)
  - Deviation = ±25% of inter-party SD per factor
  - F3 fixed at party centroid for all candidates (excluded deviation axis)

Candidate positions are loaded directly from:
  data/outputs/factor_deviation/candidate_factor_centroids.csv

Outputs:
  data/outputs/factor_deviation/ballots.csv
  data/outputs/factor_deviation/state_candidate_profiles.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR        = Path(__file__).parent.parent
CANDIDATES_PATH = BASE_DIR / "data" / "outputs" / "factor_deviation" / "candidate_factor_centroids.csv"
EFA_SCORES_PATH = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
TYPOLOGY_PATH   = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
OUTPUT_DIR      = BASE_DIR / "data" / "outputs" / "factor_deviation"

# Voter factor score columns — raw (not residualized); same space as candidate centroids
VOTER_FACTOR_COLS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]
PROB_COLS         = [f"prob_cluster_{k}" for k in range(10)]

# Party → cluster index (C7/BLB excluded)
PARTY_CLUSTER = {
    "CON": 0, "LBR": 1, "STY": 2, "NAT": 3, "LIB": 4,
    "POP": 5, "CUP": 6, "OAO": 7, "DSA": 8, "PRG": 9,
}

# Corresponding columns in the candidate CSV
CAND_FACTOR_COLS = [
    "F1_security_order",
    "F2_electoral_skepticism",
    "F3_government_distrust",
    "F4_religious_traditionalism",
    "F5_populist_conservatism",
]

POSITIONAL_SIGMA = 0.35
FACTOR_WEIGHTS   = np.array([1.0, 1.0, 1.0, 1.0, 1.0])  # uniform — centroid geometry handles discrimination

FIPS_TO_ABBR = {
     1:"AL",  2:"AK",  4:"AZ",  5:"AR",  6:"CA",  8:"CO",  9:"CT",
    10:"DE", 11:"DC", 12:"FL", 13:"GA", 15:"HI", 16:"ID", 17:"IL",
    18:"IN", 19:"IA", 20:"KS", 21:"KY", 22:"LA", 23:"ME", 24:"MD",
    25:"MA", 26:"MI", 27:"MN", 28:"MS", 29:"MO", 30:"MT", 31:"NE",
    32:"NV", 33:"NH", 34:"NJ", 35:"NM", 36:"NY", 37:"NC", 38:"ND",
    39:"OH", 40:"OK", 41:"OR", 42:"PA", 44:"RI", 45:"SC", 46:"SD",
    47:"TN", 48:"TX", 49:"UT", 50:"VT", 51:"VA", 53:"WA", 54:"WV",
    55:"WI", 56:"WY", 72:"PR",
}


def compute_candidate_scores_hybrid(voter_factors: np.ndarray,
                                    prob_matrix:   np.ndarray,
                                    cand_positions: np.ndarray,
                                    cand_clusters:  np.ndarray,
                                    is_base:        np.ndarray,
                                    sigma: float = POSITIONAL_SIGMA) -> np.ndarray:
    """Base catches core voters, variants capture loose voters.

    Base candidates:   score = prob_cluster_k (pure GMM posterior)
    Variant candidates: score = prob_cluster_k × Gaussian(variant) / Gaussian(base)

    The ratio Gaussian(variant)/Gaussian(base) measures whether the variant
    is closer or farther than base for each voter:
      ratio > 1 → variant closer → marginal/loose voter picks variant
      ratio < 1 → base closer → core voter stays with base

    Cross-party: prob is tiny, so neither base nor variant can be first-preference.
    Base never steals cross-party votes. Variants attract transfers when parties
    are eliminated in STV — the real FD signal.

    voter_factors:  (N, 5)
    prob_matrix:    (N, 10)
    cand_positions: (C, 5)
    cand_clusters:  (C,)     — base party cluster index per candidate
    is_base:        (C,) bool — True for base candidates
    Returns:        (N, C)
    """
    N, C = len(voter_factors), len(cand_positions)
    prob = prob_matrix[:, cand_clusters]                               # (N, C)

    # Gaussian proximity for all candidates
    diff    = voter_factors[:, None, :] - cand_positions[None, :, :]   # (N, C, 5)
    dist_sq = ((diff ** 2) * FACTOR_WEIGHTS).sum(axis=2)               # (N, C)
    gauss   = np.exp(-dist_sq / (2.0 * sigma ** 2))                    # (N, C)

    # Find each party's base candidate index
    base_idx = {}  # cluster_k → candidate index
    for j in range(C):
        if is_base[j]:
            base_idx[cand_clusters[j]] = j

    scores = np.empty((N, C), dtype=np.float64)
    for j in range(C):
        k = cand_clusters[j]
        if is_base[j]:
            # Base: pure GMM posterior
            scores[:, j] = prob[:, j]
        else:
            # Variant: prob × (Gaussian_variant / Gaussian_base)
            bi = base_idx.get(k, j)
            gauss_base = gauss[:, bi]
            gauss_base = np.where(gauss_base > 1e-10, gauss_base, 1e-10)
            scores[:, j] = prob[:, j] * gauss[:, j] / gauss_base

    return scores


def compute_candidate_scores(voter_factors: np.ndarray,
                              cand_positions: np.ndarray,
                              sigma: float = POSITIONAL_SIGMA) -> np.ndarray:
    """Gaussian-only scorer. Kept for reference; canonical pipeline uses hybrid."""
    diff    = voter_factors[:, None, :] - cand_positions[None, :, :]
    dist_sq = ((diff ** 2) * FACTOR_WEIGHTS).sum(axis=2)
    return np.exp(-dist_sq / (2.0 * sigma ** 2))


def generate_ballots(scores: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Deterministic ranking: sort candidates by score descending.
    Returns (N, C) int16 array of candidate indices."""
    N, C    = scores.shape
    ballots = np.zeros((N, C), dtype=np.int16)
    for i in range(N):
        ballots[i] = np.argsort(-scores[i])
    return ballots


def build_ballot_df(ballots: np.ndarray, cand_codes: list) -> pd.DataFrame:
    C         = len(cand_codes)
    rank_cols = [f"rank_{k + 1}" for k in range(C)]
    df        = pd.DataFrame(ballots, columns=rank_cols)
    for col in rank_cols:
        df[col] = df[col].map(lambda x: cand_codes[x])
    df.index.name = "respondent_id"
    return df


def build_state_profiles(
    ballot_df:  pd.DataFrame,
    inputstate: np.ndarray,
    weights:    np.ndarray,
    cand_codes: list,
) -> pd.DataFrame:
    states = np.unique(inputstate)
    rows   = []
    for fips in states:
        mask  = inputstate == fips
        w     = weights[mask]
        w_sum = w.sum()
        if w_sum == 0:
            continue
        row = {
            "state_fips":                 int(fips),
            "state_abbr":                 FIPS_TO_ABBR.get(int(fips), f"FIPS{int(fips)}"),
            "total_weighted_respondents": w_sum,
        }
        fc = ballot_df["rank_1"].values[mask]
        for code in cand_codes:
            row[f"first_choice_{code}"] = float(w[fc == code].sum() / w_sum)
        rows.append(row)
    return pd.DataFrame(rows).sort_values("state_fips").reset_index(drop=True)


def main():
    rng = np.random.default_rng(42)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sep  = "=" * 70
    thin = "-" * 70

    print(sep)
    print("FACTOR DEVIATION BALLOT GENERATION")
    print(sep)

    # ── Load candidate positions ──────────────────────────────────────────────
    print("\nLoading FD candidate positions…")
    cand_df = pd.read_csv(CANDIDATES_PATH)
    print(f"  {len(cand_df)} candidates × {len(CAND_FACTOR_COLS)} factor dimensions")

    cand_codes    = cand_df["candidate_code"].tolist()
    N_CANDIDATES  = len(cand_codes)
    cand_positions = cand_df[CAND_FACTOR_COLS].values.astype(np.float64)

    print(f"\n  Candidate range summary:")
    for i, col in enumerate(CAND_FACTOR_COLS):
        vals = cand_positions[:, i]
        print(f"    {col:<35}  min={vals.min():+.4f}  max={vals.max():+.4f}")

    # ── Load voter factor scores + typology ──────────────────────────────────
    print(f"\n{thin}")
    print("Loading EFA factor scores…")
    efa           = pd.read_csv(EFA_SCORES_PATH)
    voter_factors = efa[VOTER_FACTOR_COLS].values.astype(np.float64)
    weights       = efa["commonpostweight"].values.astype(np.float64)
    inputstate    = efa["inputstate"].values
    N             = len(efa)
    print(f"  {N:,} respondents  |  total weight: {weights.sum():,.1f}")

    print("Loading typology cluster probabilities…")
    typology    = pd.read_csv(TYPOLOGY_PATH)
    assert len(typology) == N, f"Row mismatch: typology={len(typology)}, efa={N}"
    prob_matrix = typology[PROB_COLS].values.astype(np.float64)

    # Map each FD candidate to its base party cluster index
    cand_clusters = cand_df["party"].map(PARTY_CLUSTER).values.astype(int)
    is_base       = (cand_df["axis"] == "base").values

    # ── Compute hybrid scores ─────────────────────────────────────────────────
    print(f"\n{thin}")
    print(f"Computing candidate scores (base=GMM posterior, variants=prob×Gaussian, σ={POSITIONAL_SIGMA})…")
    n_base = int(is_base.sum())
    print(f"  {n_base} base candidates (pure GMM), {len(is_base) - n_base} variants (hybrid)")
    scores = compute_candidate_scores_hybrid(voter_factors, prob_matrix, cand_positions, cand_clusters, is_base)
    print(f"  Scores shape: {scores.shape}")
    print(f"  Score range:  min={scores.min():.6f}  max={scores.max():.6f}  mean={scores.mean():.6f}")

    # Verify no degenerate rows
    zero_rows = (scores.sum(axis=1) == 0).sum()
    if zero_rows:
        print(f"  WARNING: {zero_rows} respondents have all-zero scores")

    # ── Generate ranked ballots ───────────────────────────────────────────────
    print(f"\n{thin}")
    print(f"Generating {N:,} ranked ballots (Plackett-Luce, seed=42)…")
    ballots   = generate_ballots(scores, rng)
    ballot_df = build_ballot_df(ballots, cand_codes)

    ballot_out = OUTPUT_DIR / "ballots.csv"
    ballot_df.to_csv(ballot_out, index=True)
    print(f"Saved → {ballot_out.relative_to(BASE_DIR)}  ({N:,} rows × {N_CANDIDATES} candidates)")

    # ── First-choice summary ──────────────────────────────────────────────────
    print(f"\n{thin}")
    print("FIRST-CHOICE FREQUENCIES (unweighted)")
    print(thin)

    fc_counts = ballot_df["rank_1"].value_counts().rename("fc_count")
    fc_pct    = (fc_counts / N * 100).round(2).rename("fc_pct")
    fc_table  = pd.concat([fc_counts, fc_pct], axis=1)
    meta      = cand_df.set_index("candidate_code")[["party", "axis", "direction"]]
    fc_table  = fc_table.join(meta).sort_values("fc_count", ascending=False)

    print(f"\n  {'Candidate':<20}  {'Party':<6}  {'Axis':<5}  {'Dir':<5}  {'Count':>7}  {'Pct':>6}")
    print(f"  {'-'*20}  {'-'*6}  {'-'*5}  {'-'*5}  {'-'*7}  {'-'*6}")
    for code, row in fc_table.iterrows():
        print(f"  {code:<20}  {row['party']:<6}  {row['axis']:<5}  {row['direction']:<5}  "
              f"{int(row['fc_count']):>7,}  {row['fc_pct']:>5.2f}%")

    # ── Party-level first-choice totals ───────────────────────────────────────
    print(f"\n{thin}")
    print("PARTY TOTALS (all variants combined, unweighted first choices)")
    print(thin)

    fc_table["party"] = fc_table["party"].fillna(
        cand_df.set_index("candidate_code")["party"]
    )
    party_totals = fc_table.groupby("party")["fc_count"].sum().sort_values(ascending=False)
    for party, count in party_totals.items():
        print(f"  {party:<6}  {count:>7,}  {100 * count / N:>5.2f}%")

    # ── State-level profiles ──────────────────────────────────────────────────
    print(f"\n{thin}")
    print("Building state-level profiles…")
    state_df  = build_state_profiles(ballot_df, inputstate, weights, cand_codes)
    state_out = OUTPUT_DIR / "state_candidate_profiles.csv"
    state_df.to_csv(state_out, index=False)
    print(f"Saved → {state_out.relative_to(BASE_DIR)}")
    print(f"  {len(state_df)} states × {len(state_df.columns)} columns")

    print(f"\n{'=' * 70}")
    print("DONE")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()

"""
stv_affinity.py
---------------
Three complementary inter-cluster affinity measures, all with C7 (Blue Dogs) dissolved.

1. Second-choice matrix (9×9)
   - Global %: flow from i→j as % of all (matching STV matrix format)
   - Row %: "of C3 voters, X% rank C5 second" — row-stochastic

2. Mean rank proximity matrix (9×9, symmetrized, 0-1)
   - Uses the FULL ballot, not just position 2
   - prox(A,B) = 1 − (mean_rank_of_B_on_A_first_ballots − 1) / 7
   - Symmetrized: average of A→B and B→A proximity
   - 1 = always ranked directly after 1st choice; 0 = always ranked last

3. Mahalanobis distance matrix (9×9)
   - Pairwise distance between cluster centroids in 5D factor space
   - Ideological/attitudinal proximity (independent of ballot preferences)

Why mean rank > second choice alone:
  Second-choice only uses position 2 of each ballot. Mean rank uses all 9
  remaining positions after removing C7, giving a much richer picture of
  the full preference gradient between every pair of clusters.

Outputs → Claude/stv_outputs/affinity/
  second_choice_global_pct.csv   — 9×9, global % (same format as STV directed matrix)
  second_choice_row_pct.csv      — 9×9, row-normalized % (% of A's voters ranking B 2nd)
  mean_rank_proximity.csv        — 9×9, symmetrized proximity 0-1
  mean_rank_raw.csv              — 9×9, raw asymmetric mean rank (1=closest slot)
  factor_mahalanobis.csv         — 9×9, Mahalanobis distances in 5D factor space
"""

import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.spatial.distance import mahalanobis as scipy_maha
from numpy.linalg import inv

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).parent.parent
CHECKPOINT_PATH = BASE_DIR / "data" / "outputs" / "baseline" / "ballots_checkpoint.parquet"
AFFINITY_DIR    = BASE_DIR / "data" / "outputs" / "affinity"
SCENARIO_A_DIR  = BASE_DIR / "data" / "outputs" / "scenario_a"

PARTIES_9 = [0, 1, 2, 3, 4, 5, 6, 8, 9]   # C7 excluded
PARTY_LABELS = {
    0: "Conservative",
    1: "Social Democrat",
    2: "Solidarity",
    3: "Nationalist",
    4: "Liberal",
    5: "Populist",
    6: "Civic Union Party",
    8: "DSA",
    9: "Progressive",
}
SHORT = {k: f"C{k}:{v[:12]}" for k, v in PARTY_LABELS.items()}
COL_LABELS = [f"C{k}" for k in PARTIES_9]
FACTOR_COLS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4_resid", "FS_F5_resid"]


# ── Load checkpoint ───────────────────────────────────────────────────────────

def load_checkpoint():
    print(f"Loading ballot checkpoint from {CHECKPOINT_PATH} ...")
    df = pd.read_parquet(CHECKPOINT_PATH)
    print(f"  Shape: {df.shape}")

    # Reconstruct ballot array: each row is a 10-element ranking
    raw_ballots = np.array(list(df["ballot"]), dtype=np.int8)   # (N, 10)
    assert raw_ballots.shape == (len(df), 10), "Unexpected ballot shape"

    weights = df["commonpostweight"].values

    # Remove C7 from every ballot → 9-element effective ranked list
    effective = np.array(
        [[p for p in row if p != 7] for row in raw_ballots],
        dtype=np.int8
    )
    assert effective.shape == (len(df), 9), f"Expected (N,9), got {effective.shape}"
    assert 7 not in effective, "C7 found in effective ballots!"
    print(f"  Effective ballots (C7 removed): {effective.shape}")

    return df, effective, weights


# ── Matrix 1: Second-choice matrix ───────────────────────────────────────────

def compute_second_choice(effective, weights):
    """
    For each ballot:
      first_choice = effective[:, 0]
      second_choice = effective[:, 1]
    Returns:
      sc_global (9×9): flow i→j as % of total weight
      sc_row (9×9): flow i→j as % of i-first-choice weight (row-stochastic)
    """
    print("\nComputing second-choice matrices...")
    n9 = len(PARTIES_9)
    idx = {p: i for i, p in enumerate(PARTIES_9)}

    sc_raw = np.zeros((n9, n9))   # raw weighted counts

    first_choice  = effective[:, 0]
    second_choice = effective[:, 1]

    for ai, a in enumerate(PARTIES_9):
        mask_a = (first_choice == a)
        w_a = weights[mask_a]
        sc2 = second_choice[mask_a]
        for b in PARTIES_9:
            if a == b:
                continue
            bi = idx[b]
            sc_raw[ai, bi] = w_a[sc2 == b].sum()

    total_w = weights.sum()
    sc_global = sc_raw / total_w * 100          # % of all weights
    row_sums = sc_raw.sum(axis=1, keepdims=True)
    row_sums[row_sums < 1e-9] = 1.0
    sc_row = sc_raw / row_sums * 100            # % of each cluster's weight

    # Sanity: row sums of sc_row should be ~100
    tol = sc_row.sum(axis=1)
    assert np.allclose(tol, 100.0, atol=0.5), f"Row sums off: {tol}"

    return sc_global, sc_row


# ── Matrix 2: Mean rank proximity ─────────────────────────────────────────────

def compute_mean_rank_proximity(effective, weights):
    """
    For each ordered pair (A, B), A≠B, A≠C7, B≠C7:
      On all ballots where effective[0]==A, find the rank position of B
      in effective[1:] (1=immediately after A, 8=last remaining party).
      Compute weighted mean.

    Then normalize: prox_raw[A,B] = (8 - mean_rank[A,B]) / 7
      → 1 = B always immediately after A (closest)
      → 0 = B always last among remaining 8 (furthest)

    Symmetrize: proximity[A,B] = (prox_raw[A,B] + prox_raw[B,A]) / 2
    """
    print("\nComputing mean rank proximity matrix...")
    n9 = len(PARTIES_9)
    idx = {p: i for i, p in enumerate(PARTIES_9)}

    mean_rank  = np.full((n9, n9), np.nan)
    first_choice = effective[:, 0]
    # Positions [1:] = remaining 8 parties after first choice
    remaining  = effective[:, 1:]    # shape (N, 8)

    for ai, a in enumerate(PARTIES_9):
        mask_a = (first_choice == a)
        if mask_a.sum() == 0:
            continue
        sub = remaining[mask_a, :]        # (n_a, 8) — ranked preferences after A
        w_a = weights[mask_a]

        for b in PARTIES_9:
            if a == b:
                continue
            bi = idx[b]
            # Find column index of b in sub for each row (vectorized)
            positions = np.where(sub == b)
            # positions[0] = row indices, positions[1] = column indices (0-based → rank 1..8)
            if len(positions[1]) == 0:
                continue
            row_w = w_a[positions[0]]
            ranks = positions[1] + 1      # 1-indexed rank
            mean_rank[ai, bi] = np.average(ranks, weights=row_w)

    # Normalize: 1=closest (rank 1 of remaining 8), 0=furthest (rank 8)
    prox_raw = (8 - mean_rank) / 7
    np.fill_diagonal(prox_raw, np.nan)

    # Symmetrize
    proximity = (prox_raw + prox_raw.T) / 2
    np.fill_diagonal(proximity, np.nan)

    return mean_rank, proximity


# ── Matrix 3: Mahalanobis distances ──────────────────────────────────────────

def compute_mahalanobis(df):
    """
    Pairwise Mahalanobis distance between cluster centroids in 5D factor space.
    Uses overall sample covariance (all 10 clusters including C7).
    C7 excluded from output matrix.
    """
    print("\nComputing Mahalanobis distance matrix (5D factor space)...")
    present = [c for c in FACTOR_COLS if c in df.columns]
    if len(present) < 5:
        print(f"  WARNING: Only found {len(present)}/5 factor columns: {present}")
        return None

    X = df[present].values.astype(float)
    cluster_ids = df["cluster"].values

    # Check for NaN
    nan_mask = np.isnan(X).any(axis=1)
    if nan_mask.any():
        print(f"  Dropping {nan_mask.sum()} rows with NaN factor scores")
        X = X[~nan_mask]
        cluster_ids = cluster_ids[~nan_mask]

    # Inverse covariance using all available data (not just C7-excluded)
    Sigma = np.cov(X.T)
    try:
        Sigma_inv = inv(Sigma)
    except np.linalg.LinAlgError:
        print("  WARNING: Covariance matrix singular, using pseudoinverse")
        Sigma_inv = np.linalg.pinv(Sigma)

    means = {}
    for k in PARTIES_9 + [7]:          # compute C7 mean too (needed for baseline check)
        mask = (cluster_ids == k)
        if mask.sum() > 0:
            means[k] = X[mask].mean(axis=0)

    n9 = len(PARTIES_9)
    maha = np.zeros((n9, n9))
    for ai, a in enumerate(PARTIES_9):
        for bi, b in enumerate(PARTIES_9):
            if a == b:
                continue
            maha[ai, bi] = scipy_maha(means[a], means[b], Sigma_inv)

    return maha


# ── Formatting helpers ────────────────────────────────────────────────────────

def to_df(mat, parties=PARTIES_9, fmt=None):
    """Convert numpy matrix to labeled DataFrame."""
    labels = [f"C{p}" for p in parties]
    df = pd.DataFrame(mat, index=labels, columns=labels)
    if fmt:
        df = df.round(fmt)
    return df


def print_matrix(title, mat, parties=PARTIES_9, fmt=".3f"):
    """Pretty-print a 9×9 matrix with cluster labels."""
    labels = [f"C{p}" for p in parties]
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    header = f"{'':>6}" + "".join(f"  {l:>6}" for l in labels)
    print(header)
    for i, p in enumerate(parties):
        row_str = f"C{p:>2}  {PARTY_LABELS[p][:17]:<17}"
        for j in range(len(parties)):
            v = mat[i, j]
            if np.isnan(v) or i == j:
                row_str += f"  {'---':>6}"
            else:
                row_str += f"  {v:{fmt}}"
        print(row_str)


def print_top_partners(title, mat, parties=PARTIES_9, top_n=3, high_is_close=True):
    """For each cluster, print its closest N partners."""
    print(f"\n── {title} ──")
    for ai, a in enumerate(parties):
        row = mat[ai].copy()
        row[ai] = np.nan
        valid = [(row[bi], b) for bi, b in enumerate(parties) if not np.isnan(row[bi]) and b != a]
        if high_is_close:
            ranked = sorted(valid, reverse=True)
        else:
            ranked = sorted(valid)
        top = ranked[:top_n]
        partner_str = ", ".join([f"C{b}({v:.3f})" for v, b in top])
        print(f"  C{a} {PARTY_LABELS[a][:22]:<22} → {partner_str}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import time
    t0 = time.time()

    print("=" * 70)
    print("INTER-CLUSTER AFFINITY ANALYSIS (C7 dissolved)")
    print("=" * 70)

    os.makedirs(AFFINITY_DIR, exist_ok=True)

    # Load
    df, effective, weights = load_checkpoint()

    # ── Matrix 1: Second choice ──────────────────────────────────────────────
    sc_global, sc_row = compute_second_choice(effective, weights)

    df_sc_global = to_df(sc_global, fmt=4)
    df_sc_row    = to_df(sc_row,    fmt=2)
    df_sc_global.to_csv(AFFINITY_DIR / "second_choice_global_pct.csv")
    df_sc_row.to_csv(   AFFINITY_DIR / "second_choice_row_pct.csv")

    print_matrix("SECOND-CHOICE MATRIX (row % — of A voters, % ranking B 2nd)",
                 sc_row, fmt=".1f")
    print_top_partners("Top 2nd-choice partners (row %)", sc_row, high_is_close=True)

    # ── Matrix 2: Mean rank proximity ────────────────────────────────────────
    mean_rank, proximity = compute_mean_rank_proximity(effective, weights)

    df_prox     = to_df(proximity,  fmt=4)
    df_meanrank = to_df(mean_rank,  fmt=3)
    df_prox.to_csv(    AFFINITY_DIR / "mean_rank_proximity.csv")
    df_meanrank.to_csv(AFFINITY_DIR / "mean_rank_raw.csv")

    print_matrix("MEAN RANK PROXIMITY (symmetrized, 1=closest, 0=furthest)",
                 proximity, fmt=".3f")
    print_top_partners("Closest partners by mean rank proximity", proximity, high_is_close=True)

    # ── Matrix 3: Mahalanobis ────────────────────────────────────────────────
    maha = compute_mahalanobis(df)
    if maha is not None:
        df_maha = to_df(maha, fmt=4)
        df_maha.to_csv(AFFINITY_DIR / "factor_mahalanobis.csv")

        print_matrix("MAHALANOBIS DISTANCE (5D factor space, lower=more similar)",
                     maha, fmt=".3f")
        print_top_partners("Closest partners by ideological distance (Mahalanobis)",
                           maha, high_is_close=False)    # low distance = close

    # ── Reference: STV transfer matrix (scenario_a) ─────────────────────────
    stv_path = SCENARIO_A_DIR / "transfer_matrix_directed.csv"
    if stv_path.exists():
        print(f"\n── Reference: STV transfer matrix (C7 dissolved) ──")
        print(f"   {stv_path}")
        df_stv = pd.read_csv(stv_path, index_col=0)
        # Index labels are like "C0 Mainstream Conserv" — keep non-C7 rows/cols
        keep_idx = [c for c in df_stv.index  if not c.startswith("C7")]
        keep_col = [c for c in df_stv.columns if not c.startswith("C7")]
        stv_sub = df_stv.loc[keep_idx, keep_col]
        if stv_sub.shape[0] == 9:
            print_top_partners(
                "Top transfer recipients under STV (C7 dissolved, row %)",
                stv_sub.values, high_is_close=True
            )
        else:
            print(f"  (Could not subset STV matrix to 10 parties — shape: {stv_sub.shape})")
    else:
        print(f"\n  NOTE: Scenario A STV matrix not found at {stv_path}")

    # ── Comparison summary ───────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  CROSS-MEASURE SUMMARY: TOP AFFINITY PAIRS (excl. C7)")
    print("=" * 70)
    print("\n  Measure          | Top 3 closest pairs")
    print("  ─────────────────|───────────────────────────────────────────")

    if maha is not None:
        flat_maha = [(maha[ai, bi], PARTIES_9[ai], PARTIES_9[bi])
                     for ai in range(9) for bi in range(9)
                     if ai < bi and not np.isnan(maha[ai, bi])]
        flat_maha.sort()
        pairs_maha = [f"C{a}-C{b}({d:.3f})" for d, a, b in flat_maha[:3]]
        print(f"  Mahalanobis      | {', '.join(pairs_maha)}")

    flat_prox = [(proximity[ai, bi], PARTIES_9[ai], PARTIES_9[bi])
                 for ai in range(9) for bi in range(9)
                 if ai < bi and not np.isnan(proximity[ai, bi])]
    flat_prox.sort(reverse=True)
    pairs_prox = [f"C{a}-C{b}({v:.3f})" for v, a, b in flat_prox[:3]]
    print(f"  Mean rank prox.  | {', '.join(pairs_prox)}")

    # Second-choice: top global flows
    flat_sc = [(sc_row[ai, bi], PARTIES_9[ai], PARTIES_9[bi])
               for ai in range(9) for bi in range(9)
               if ai != bi]
    flat_sc.sort(reverse=True)
    pairs_sc = [f"C{a}→C{b}({v:.1f}%)" for v, a, b in flat_sc[:3]]
    print(f"  Second choice    | {', '.join(pairs_sc)}")

    print(f"\n  Outputs saved to: {AFFINITY_DIR}")
    print(f"  Runtime: {time.time()-t0:.1f}s")
    print()


if __name__ == "__main__":
    main()

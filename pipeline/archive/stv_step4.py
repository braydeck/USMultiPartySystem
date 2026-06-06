"""
stv_step4.py
------------
Aggregate transfer data from all STV elections into 10×10 transfer matrices.

Outputs:
  transfer_matrix_10party.csv    — symmetric matrix (% of total bidirectional flow)
  transfer_matrix_directed.csv   — directed matrix  (% of all transfers from i to j)

Matrix interpretation:
  Directed[i, j] = X% means X% of ALL transfer events came from party i → party j
  Symmetric[i, j] = total flow between i and j as % of all bidirectional flow
  Diagonal is always 0 (no self-transfers).

Row label = source party (eliminated or surplus)
Col label = destination party (receiving votes)
"""

import numpy as np
import pandas as pd
from stv_config import OUTPUT_DIR, PARTY_LABELS, N_PARTIES


def build_transfer_matrices(all_results: list) -> tuple:
    """
    Aggregate transfer events across all districts into directed and symmetric
    10×10 matrices.

    Returns:
        directed_pct  : ndarray (10, 10) — % of all transfer weight from i to j
        symmetric_pct : ndarray (10, 10) — % of total bidirectional weight between i,j
        raw_directed  : ndarray (10, 10) — raw transfer weights (unscaled)
    """
    directed = np.zeros((N_PARTIES, N_PARTIES), dtype=np.float64)

    for result in all_results:
        for t in result.get("transfers", []):
            i = int(t["from_party"])
            j = int(t["to_party"])
            w = float(t["weight"])
            if 0 <= i < N_PARTIES and 0 <= j < N_PARTIES and i != j:
                directed[i, j] += w

    raw_directed = directed.copy()

    # Normalize to percentages
    total = directed.sum()
    if total > 0:
        directed_pct = directed / total * 100.0
    else:
        directed_pct = directed.copy()
        print("  WARNING: No transfer events found — matrices will be all zeros")

    # Symmetric: element-wise sum of directed and its transpose
    symmetric = directed + directed.T
    sym_total = symmetric.sum()
    if sym_total > 0:
        symmetric_pct = symmetric / sym_total * 100.0
    else:
        symmetric_pct = symmetric.copy()

    # Diagonal must be 0 (no self-transfers; assert for sanity)
    assert np.diag(directed_pct).sum() < 1e-9, "Non-zero diagonal in directed matrix"

    return directed_pct, symmetric_pct, raw_directed


def build_party_labels_short() -> list:
    """Short labels for matrix rows/columns: 'C0 Mainstream Con.'"""
    labels = []
    for k in range(N_PARTIES):
        name = PARTY_LABELS[k]
        # Truncate to 18 chars for readability
        short = name[:18] if len(name) > 18 else name
        labels.append(f"C{k} {short}")
    return labels


def save_transfer_matrices(
    directed_pct:  np.ndarray,
    symmetric_pct: np.ndarray,
    raw_directed:  np.ndarray,
    output_dir=None,             # override OUTPUT_DIR if provided
) -> None:
    out = output_dir if output_dir is not None else OUTPUT_DIR
    labels = build_party_labels_short()

    # Directed matrix
    df_dir = pd.DataFrame(directed_pct, index=labels, columns=labels)
    df_dir.index.name   = "from_party"
    df_dir.columns.name = "to_party"
    out_dir = out / "transfer_matrix_directed.csv"
    df_dir.round(4).to_csv(out_dir)
    print(f"  Saved: {out_dir}")

    # Symmetric matrix
    df_sym = pd.DataFrame(symmetric_pct, index=labels, columns=labels)
    df_sym.index.name   = "party_a"
    df_sym.columns.name = "party_b"
    out_sym = out / "transfer_matrix_10party.csv"
    df_sym.round(4).to_csv(out_sym)
    print(f"  Saved: {out_sym}")

    # Diagnostics
    print(f"\n  Transfer matrix diagnostics:")
    print(f"  Total raw transfer weight: {raw_directed.sum():,.1f}")
    print(f"  Directed matrix row sums (% each party's transfers sent):")
    row_sums = directed_pct.sum(axis=1)
    for k in range(N_PARTIES):
        print(f"    C{k} {PARTY_LABELS[k][:22]:<22}: {row_sums[k]:.2f}%")
    print(f"  Directed matrix col sums (% each party's transfers received):")
    col_sums = directed_pct.sum(axis=0)
    for k in range(N_PARTIES):
        print(f"    C{k} {PARTY_LABELS[k][:22]:<22}: {col_sums[k]:.2f}%")


def build_directed_asymmetry_report(directed_pct: np.ndarray) -> pd.DataFrame:
    """
    Build a human-readable asymmetry report.
    For each pair (i, j) where i < j, shows:
        C_i → C_j %,  C_j → C_i %,  asymmetry = (i→j) - (j→i)
    Sorted by abs(asymmetry) descending.
    """
    rows = []
    for i in range(N_PARTIES):
        for j in range(i + 1, N_PARTIES):
            i_to_j = directed_pct[i, j]
            j_to_i = directed_pct[j, i]
            rows.append({
                "party_i":    f"C{i} {PARTY_LABELS[i]}",
                "party_j":    f"C{j} {PARTY_LABELS[j]}",
                "i_to_j_pct": round(i_to_j, 4),
                "j_to_i_pct": round(j_to_i, 4),
                "asymmetry":  round(i_to_j - j_to_i, 4),
                "total_flow": round(i_to_j + j_to_i, 4),
            })
    df = pd.DataFrame(rows)
    df = df.sort_values("total_flow", ascending=False).reset_index(drop=True)
    return df


if __name__ == "__main__":
    import os
    from stv_step1 import run_apportionment
    from stv_step2 import load_and_prepare
    from stv_step3 import run_all_districts

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("Running Steps 1-4 (standalone)...")

    apportionment = run_apportionment()
    df            = load_and_prepare(apportionment)
    all_results   = run_all_districts(df, apportionment)

    print("\n" + "=" * 60)
    print("STEP 4: TRANSFER MATRICES")
    print("=" * 60)
    dir_pct, sym_pct, raw = build_transfer_matrices(all_results)
    save_transfer_matrices(dir_pct, sym_pct, raw)

    # Save asymmetry report as bonus
    asym = build_directed_asymmetry_report(dir_pct)
    out_asym = OUTPUT_DIR / "transfer_asymmetry_report.csv"
    asym.to_csv(out_asym, index=False)
    print(f"  Saved: {out_asym}")
    print("\n  Top 10 transfer pairs by total flow:")
    print(asym.head(10).to_string(index=False))

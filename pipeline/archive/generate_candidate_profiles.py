#!/usr/bin/env python3
"""
generate_candidate_profiles.py
--------------------------------
Produce two output files describing the 18 presidential candidates' estimated
positions on policy items and EFA factors.

Inputs:
  Claude/analysis/clustering/cluster_item_means.csv
      - variable, label, scale, domain, overall, c0–c9, range
  Claude/data/efa_factor_scores.csv
      - FS_F1–FS_F5 per respondent + commonpostweight (positionally aligned)
  Claude/data/typology_cluster_assignments.csv
      - cluster (hard assignment 0–9) + prob_cluster_0–9 (positionally aligned)

Outputs:
  Claude/outputs/candidate_stance_profiles.csv   (468 rows: 18 × 26 items)
  Claude/outputs/candidate_factor_centroids.csv  (18 rows)
"""

import numpy as np
import pandas as pd
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR          = Path(__file__).parent.parent
ITEM_MEANS_PATH   = BASE_DIR / "analysis" / "clustering_old" / "cluster_item_means.csv"
EFA_SCORES_PATH   = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
TYPOLOGY_PATH     = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
OUTPUT_DIR        = BASE_DIR / "data" / "outputs"

# ── 17 Presidential Candidates (same definition as generate_presidential_ballots.py) ──
# Congressional stable: 9 pure cluster candidates
# Governor/Senate stable: 8 senate-derived blends (weights = national senate averages)
CANDIDATES = [
    # ── Congressional Stable (pure) ──
    {"code": "RH",      "primary": 0, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "MW",      "primary": 1, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "MRJ",     "primary": 2, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "BE",      "primary": 3, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "CO",      "primary": 4, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "DH",      "primary": 5, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "LK",      "primary": 6, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "ZN",      "primary": 8, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    {"code": "JR",      "primary": 9, "secondary": None, "w_primary": 1.00, "w_secondary": 0.00},
    # ── Governor/Senate Stable (senate-derived blends) ──
    {"code": "SD_STY",  "primary": 1, "secondary": 2, "w_primary": 0.67, "w_secondary": 0.33},
    {"code": "CON_CTR", "primary": 0, "secondary": 6, "w_primary": 0.62, "w_secondary": 0.38},
    {"code": "CON_SD",  "primary": 0, "secondary": 1, "w_primary": 0.55, "w_secondary": 0.45},
    {"code": "CON_STY", "primary": 0, "secondary": 2, "w_primary": 0.58, "w_secondary": 0.42},
    {"code": "STY_REF", "primary": 2, "secondary": 5, "w_primary": 0.55, "w_secondary": 0.45},
    {"code": "SD_CON",  "primary": 1, "secondary": 0, "w_primary": 0.52, "w_secondary": 0.48},
    {"code": "STY_SD",  "primary": 2, "secondary": 1, "w_primary": 0.50, "w_secondary": 0.50},
    {"code": "REF_STY", "primary": 5, "secondary": 2, "w_primary": 0.63, "w_secondary": 0.37},
]

CAND_NAMES = {
    "RH":      "CON",     "MW":      "SD",      "MRJ":     "STY",
    "BE":      "NAT",     "CO":      "LIB",     "DH":      "REF",
    "LK":      "CTR",     "ZN":      "DSA",     "JR":      "PRG",
    "SD_STY":  "SD/STY",  "CON_CTR": "CON/CTR", "CON_SD":  "CON/SD",
    "CON_STY": "CON/STY", "STY_REF": "STY/REF", "SD_CON":  "SD/CON",
    "STY_SD":  "STY/SD",  "REF_STY": "REF/STY",
}

# ── 24 EFA items + 2 supplementary = 26 profile items ─────────────────────────
ITEMS_25 = [
    "pew_churatd", "CC24_302",   "CC24_303",   "CC24_341a",  "CC24_341c",
    "CC24_341d",   "CC24_323a",  "CC24_323b",  "CC24_323d",  "CC24_321b",
    "CC24_321d",   "CC24_321e",  "CC24_325",   "CC24_324b",  "CC24_340a",
    "CC24_340b",   "CC24_340c",  "CC24_340e",  "CC24_340f",  "CC24_440b",
    "CC24_440c",   "CC24_421_1", "CC24_421_2", "CC24_423",   "CC24_424",
]
ITEMS_24      = [it for it in ITEMS_25 if it != "CC24_340a"]
SUPPLEMENTARY = ["ideo5", "pew_religimp"]
PROFILE_ITEMS = ITEMS_24 + SUPPLEMENTARY   # 26 items

# ── EFA factor labels ──────────────────────────────────────────────────────────
FACTOR_COLS = {
    "F1_security_order":           "FS_F1",
    "F2_electoral_skepticism":     "FS_F2",
    "F3_government_distrust":      "FS_F3",
    "F4_religious_traditionalism": "FS_F4",
    "F5_populist_conservatism":    "FS_F5",
}

# Finalists to highlight in console output
FINALISTS = ["CON_SD", "SD_CON", "SD_STY", "CON_STY", "REF_STY"]


# ─────────────────────────────────────────────────────────────────────────────
def build_stance_profiles(item_means_df: pd.DataFrame) -> pd.DataFrame:
    """
    For each candidate × item compute:
      candidate_mean    = w_primary * c{primary}[item] + w_secondary * c{secondary}[item]
      delta             = candidate_mean - overall
      delta_pct_range   = delta / range * 100
    Returns long-format DataFrame (468 rows: 18 × 26).
    """
    # Filter to the 26 profile items (preserving order)
    df = item_means_df[item_means_df["variable"].isin(PROFILE_ITEMS)].copy()

    # Re-order to match PROFILE_ITEMS order
    df["_sort"] = df["variable"].map({v: i for i, v in enumerate(PROFILE_ITEMS)})
    df = df.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)

    assert len(df) == len(PROFILE_ITEMS), (
        f"Expected {len(PROFILE_ITEMS)} profile items, found {len(df)}.\n"
        f"Missing: {set(PROFILE_ITEMS) - set(df['variable'].values)}"
    )

    rows = []
    for cand in CANDIDATES:
        code   = cand["code"]
        wp     = cand["w_primary"]
        ws     = cand["w_secondary"]
        p_col  = f"c{cand['primary']}"
        s_col  = f"c{cand['secondary']}" if cand["secondary"] is not None else None

        for _, item_row in df.iterrows():
            cand_mean = wp * item_row[p_col]
            if s_col is not None:
                cand_mean += ws * item_row[s_col]

            overall    = item_row["overall"]
            item_range = item_row["range"]
            delta      = cand_mean - overall
            delta_pct  = (delta / item_range * 100) if item_range != 0 else np.nan

            rows.append({
                "candidate_code":   code,
                "candidate_name":   CAND_NAMES[code],
                "variable":         item_row["variable"],
                "label":            item_row["label"],
                "scale":            item_row["scale"],
                "domain":           item_row["domain"],
                "overall_mean":     round(overall,    4),
                "candidate_mean":   round(cand_mean,  4),
                "delta":            round(delta,       4),
                "delta_pct_range":  round(delta_pct,   2),
            })

    return pd.DataFrame(rows)


def compute_cluster_centroids(
    efa_df: pd.DataFrame, typology_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Compute weighted mean of FS_F1–FS_F5 for each cluster (0–9).
    Returns DataFrame indexed by cluster with factor columns.
    """
    factor_raw_cols = list(FACTOR_COLS.values())   # FS_F1 … FS_F5
    weights = efa_df["commonpostweight"].values
    clusters = typology_df["cluster"].values

    centroids = {}
    for k in range(10):
        mask  = clusters == k
        w_k   = weights[mask]
        w_sum = w_k.sum()
        if w_sum == 0:
            centroids[k] = {col: np.nan for col in factor_raw_cols}
        else:
            centroids[k] = {
                col: float(np.average(efa_df[col].values[mask], weights=w_k))
                for col in factor_raw_cols
            }

    return pd.DataFrame(centroids).T   # shape (10, 5), indexed by cluster int


def build_factor_centroids(cluster_centroids: pd.DataFrame) -> pd.DataFrame:
    """
    For each candidate compute:
      candidate_factor[f] = w_primary * centroid[primary, f]
                          + w_secondary * centroid[secondary, f]
    Returns wide-format DataFrame (18 rows).
    """
    rows = []
    for cand in CANDIDATES:
        code  = cand["code"]
        wp    = cand["w_primary"]
        ws    = cand["w_secondary"]
        p     = cand["primary"]
        s     = cand["secondary"]

        row = {"candidate_code": code, "candidate_name": CAND_NAMES[code]}
        for label, raw_col in FACTOR_COLS.items():
            val = wp * cluster_centroids.loc[p, raw_col]
            if s is not None:
                val += ws * cluster_centroids.loc[s, raw_col]
            row[label] = round(float(val), 4)

        rows.append(row)

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Load inputs ────────────────────────────────────────────────────────────
    print("Loading cluster item means…")
    item_means_df = pd.read_csv(ITEM_MEANS_PATH)
    print(f"  shape: {item_means_df.shape}  |  variables: {len(item_means_df)}")

    print("Loading EFA factor scores…")
    efa_df = pd.read_csv(EFA_SCORES_PATH)
    print(f"  shape: {efa_df.shape}")

    print("Loading typology cluster assignments…")
    typology_df = pd.read_csv(TYPOLOGY_PATH)
    print(f"  shape: {typology_df.shape}")

    assert len(efa_df) == len(typology_df), (
        f"Row count mismatch: efa={len(efa_df)}, typology={len(typology_df)}"
    )

    # ── Stance profiles ────────────────────────────────────────────────────────
    print("\nBuilding candidate stance profiles…")
    stance_df = build_stance_profiles(item_means_df)

    assert len(stance_df) == len(CANDIDATES) * len(PROFILE_ITEMS), (
        f"Expected {len(CANDIDATES) * len(PROFILE_ITEMS)} rows, got {len(stance_df)}"
    )
    assert stance_df["delta_pct_range"].between(-100, 100).all(), \
        "delta_pct_range out of [-100, 100] bounds!"

    stance_out = OUTPUT_DIR / "candidate_stance_profiles.csv"
    stance_df.to_csv(stance_out, index=False)
    print(f"  ✓ Saved {len(stance_df)} rows → {stance_out}")

    # ── Factor centroids ───────────────────────────────────────────────────────
    print("\nComputing cluster factor centroids…")
    cluster_centroids = compute_cluster_centroids(efa_df, typology_df)
    print("  Cluster centroids (weighted means):")
    print(cluster_centroids.round(3).to_string())

    print("\nBuilding candidate factor centroids…")
    factor_df = build_factor_centroids(cluster_centroids)

    factor_out = OUTPUT_DIR / "candidate_factor_centroids.csv"
    factor_df.to_csv(factor_out, index=False)
    print(f"  ✓ Saved {len(factor_df)} rows → {factor_out}")

    # ── Console: finalist factor positions ────────────────────────────────────
    factor_labels = list(FACTOR_COLS.keys())
    print("\n" + "═" * 80)
    print("FINALIST FACTOR POSITIONS  (5 final candidates)")
    print("Factors: F1=Law&Order/Security  F2=Election Distrust  F3=Govt Distrust")
    print("         F4=Religious/Social Con  F5=Cultural Traditionalism")
    print("─" * 80)
    header = f"{'Candidate':<18}" + "".join(f"{lbl.split('_',1)[0]:>8}" for lbl in factor_labels)
    print(header)
    print("─" * 80)
    finalist_rows = factor_df[factor_df["candidate_code"].isin(FINALISTS)].copy()
    finalist_rows["_sort"] = finalist_rows["candidate_code"].map(
        {c: i for i, c in enumerate(FINALISTS)}
    )
    finalist_rows = finalist_rows.sort_values("_sort")
    for _, row in finalist_rows.iterrows():
        vals = "".join(f"{row[lbl]:>8.3f}" for lbl in factor_labels)
        print(f"{row['candidate_name']:<18}{vals}")
    print("═" * 80)

    # ── Console: full candidate factor table ──────────────────────────────────
    print("\nFull candidate factor centroids:")
    for _, row in factor_df.iterrows():
        vals = "  ".join(f"{lbl.split('_',1)[0]}={row[lbl]:+.3f}" for lbl in factor_labels)
        print(f"  {row['candidate_name']:<18}  {vals}")

    # ── Spot-check CON_SD ─────────────────────────────────────────────────────
    cand_check = next(c for c in CANDIDATES if c["code"] == "CON_SD")
    check_row = factor_df[factor_df["candidate_code"] == "CON_SD"].iloc[0]
    wp, ws = cand_check["w_primary"], cand_check["w_secondary"]
    p, s   = cand_check["primary"], cand_check["secondary"]
    print(f"\nSpot-check CON_SD | CON/SD ({wp:.0%}/{ws:.0%}):")
    for lbl, raw_col in FACTOR_COLS.items():
        cp_val = cluster_centroids.loc[p, raw_col]
        cs_val = cluster_centroids.loc[s, raw_col]
        expected = round(wp * cp_val + ws * cs_val, 4)
        actual   = check_row[lbl]
        match_str = "✓" if abs(expected - actual) < 1e-4 else "✗"
        print(f"  {lbl}: {wp}×{cp_val:.4f} + {ws}×{cs_val:.4f} = {expected:.4f}  →  file={actual:.4f}  {match_str}")

    print("\n✓ Done.")


if __name__ == "__main__":
    main()

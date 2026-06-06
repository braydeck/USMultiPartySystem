"""
generate_blend_stats.py

Generates a blend_stats.csv in the same format as cluster_stats.csv, but with
columns for each requested blend archetype instead of c0–c9.

For every stat row (binary %, ordinal mean, distribution %, continuous median,
likert mean), the blend value is computed as:
    blend = w_primary * cluster_primary + w_secondary * cluster_secondary

Weights sourced from senate simulation nationals where available; 50/50 for
blends with no simulation data.

Output: data/outputs/profiles/blend_stats.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

# ── Cluster index mapping ──────────────────────────────────────────────────
CLUSTER_NAMES = {
    0: "CON", 1: "SD", 2: "STY", 3: "NAT", 4: "LIB",
    5: "REF", 6: "CTR", 7: "C7",  8: "DSA", 9: "PRG",
}

# ── Blend definitions: (label, primary_cluster, secondary_cluster, w_primary) ──
# Weights = mean w_primary across all winning senators of that blend type
# in the senate simulation (cooc + wildcard winners).
BLENDS = [
    ("CON/CTR",  0, 6, 0.6231),  # n=8,  range 0.50–0.70
    ("CON/SD",   0, 1, 0.5545),  # n=7,  range 0.55–0.57
    ("CON/STY",  0, 2, 0.5800),  # n=5,  range 0.55–0.70
    ("SD/STY",   1, 2, 0.6684),  # n=11, range 0.57–0.70
    ("SD/CON",   1, 0, 0.5208),  # n=3,  range 0.50–0.56
    ("SD/DSA",   1, 8, 0.5000),  # n=1,  equal cluster shares
    ("SD/CTR",   1, 6, 0.5000),  # n=1,  equal cluster shares
    ("SD/LIB",   1, 4, 0.5000),  # n=1,  equal cluster shares
    ("STY/REF",  2, 5, 0.5500),  # n=4,  range 0.50–0.70
    ("STY/SD",   2, 1, 0.5000),  # n=3,  equal cluster shares
    ("STY/CON",  2, 0, 0.5923),  # n=1,  wildcard weight
    ("REF/STY",  5, 2, 0.6311),  # n=2,  range 0.56–0.70
]

# ── Paths ──────────────────────────────────────────────────────────────────
_BASE         = Path(__file__).parent.parent
CLUSTER_STATS = _BASE / "data" / "outputs" / "profiles" / "cluster_stats.csv"
OUT_PATH      = _BASE / "data" / "outputs" / "profiles" / "blend_stats.csv"

def main():
    df = pd.read_csv(CLUSTER_STATS)
    print(f"Loaded cluster_stats.csv  ({len(df)} rows, {len(df.columns)} cols)")

    cluster_cols = [f"c{i}" for i in range(10)]

    # Build output rows
    out_rows = []
    for _, row in df.iterrows():
        new_row = {
            "variable":   row["variable"],
            "domain":     row["domain"],
            "type":       row["type"],
            "stat_label": row["stat_label"],
            "question":   row["question"],
            "overall":    row["overall"],
        }
        for label, p, s, wp in BLENDS:
            ws = 1.0 - wp
            cp_val = row[f"c{p}"]
            cs_val = row[f"c{s}"]
            new_row[label] = round(wp * cp_val + ws * cs_val, 4)
        out_rows.append(new_row)

    out_df = pd.DataFrame(out_rows)

    # Column order: metadata + overall + blend labels
    blend_labels = [b[0] for b in BLENDS]
    out_df = out_df[["variable", "domain", "type", "stat_label", "question", "overall"] + blend_labels]

    out_df.to_csv(OUT_PATH, index=False)
    print(f"Saved {len(out_df)} rows → {OUT_PATH}")
    print(f"Blend columns: {blend_labels}")

    # ── Spot-check: CON/SD row for CC24_341a (extend 2017 tax cuts) ──
    con_sd = next(b for b in BLENDS if b[0] == "CON/SD")
    _, cp, cs, wp = con_sd
    ws = 1.0 - wp
    check = out_df[(out_df["variable"] == "CC24_341a") & (out_df["stat_label"] == "% Supporting")]
    if not check.empty:
        val = check["CON/SD"].iloc[0]
        src = df[(df["variable"] == "CC24_341a") & (df["stat_label"] == "% Supporting")]
        c0  = src[f"c{cp}"].iloc[0]
        c1  = src[f"c{cs}"].iloc[0]
        exp = round(wp * c0 + ws * c1, 4)
        match = "✓" if abs(val - exp) < 0.01 else "✗"
        print(f"\nSpot-check CON/SD | CC24_341a (extend tax cuts):")
        print(f"  {wp}×{c0:.2f} + {ws:.4f}×{c1:.2f} = {exp:.2f}  →  file={val:.4f}  {match}")

    print("\n✓ Done.")


if __name__ == "__main__":
    main()

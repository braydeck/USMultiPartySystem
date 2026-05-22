#!/usr/bin/env python3
"""
generate_light_fusion_stats.py
---------------------------------
Generates a light_fusion_stats.csv with position/viewpoint data for the
16 light fusion (80/20) candidates, using the same format as blend_stats.csv
and cluster_stats.csv.

For each stat row, the light fusion value is:
    value = 0.80 * cluster_primary + 0.20 * cluster_secondary

Output: data/outputs/profiles/light_fusion_stats.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

_BASE         = Path(__file__).parent.parent
CLUSTER_STATS = _BASE / "data" / "outputs" / "profiles" / "cluster_stats.csv"
OUT_PATH      = _BASE / "data" / "outputs" / "profiles" / "light_fusion_stats.csv"

# Light fusion definitions: (display_code, primary_cluster, secondary_cluster)
# Same 80/20 weights throughout
LIGHT_FUSION = [
    ("PRG_dsa", 9, 8),
    ("DSA_prg", 8, 9),
    ("DSA_lib", 8, 4),
    ("LIB_dsa", 4, 8),
    ("LIB_sd",  4, 1),
    ("SD_lib",  1, 4),
    ("SD_sty",  1, 2),
    ("STY_sd",  2, 1),
    ("STY_ctr", 2, 6),
    ("CTR_sty", 6, 2),
    ("CTR_con", 6, 0),
    ("CON_ctr", 0, 6),
    ("CON_ref", 0, 5),
    ("REF_con", 5, 0),
    ("REF_nat", 5, 3),
    ("NAT_ref", 3, 5),
]

W_PRIMARY   = 0.80
W_SECONDARY = 0.20


def main():
    df = pd.read_csv(CLUSTER_STATS)
    print(f"Loaded cluster_stats.csv  ({len(df)} rows, {len(df.columns)} cols)")

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
        for code, p, s in LIGHT_FUSION:
            cp_val = row[f"c{p}"]
            cs_val = row[f"c{s}"]
            new_row[code] = round(W_PRIMARY * float(cp_val) + W_SECONDARY * float(cs_val), 4)
        out_rows.append(new_row)

    lf_labels = [lf[0] for lf in LIGHT_FUSION]
    out_df = pd.DataFrame(out_rows)
    out_df = out_df[["variable", "domain", "type", "stat_label", "question", "overall"] + lf_labels]

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(OUT_PATH, index=False)
    print(f"Saved {len(out_df)} rows → {OUT_PATH}")
    print(f"Light fusion columns ({len(lf_labels)}): {lf_labels}")
    print("\n✓ Done.")


if __name__ == "__main__":
    main()

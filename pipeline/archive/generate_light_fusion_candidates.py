#!/usr/bin/env python3
"""
generate_light_fusion_candidates.py
-------------------------------------
Computes factor-score centroids for 16 "light fusion" (80/20) candidates
and appends them to a new light_fusion_centroids.csv.

Light fusion candidates represent individuals who would still caucus with
their primary party but have slightly deviant beliefs toward an adjacent
party — as opposed to true "blended" midpoint candidates used in the
senate-derived scenario.

Naming convention: STY_sd (uppercase base, lowercase lean suffix).
This is distinct from STY/SD blended (true midpoint, ~50/50).

Factor scores: 0.80 * primary_centroid + 0.20 * secondary_centroid

Outputs:
  data/outputs/light_fusion_centroids.csv
"""

import csv
from pathlib import Path

BASE_DIR  = Path(__file__).parent.parent
CENTROIDS = BASE_DIR / "data" / "outputs" / "candidate_factor_centroids.csv"
OUT_PATH  = BASE_DIR / "data" / "outputs" / "light_fusion_centroids.csv"

FACTOR_COLS = [
    "F1_security_order",
    "F2_electoral_skepticism",
    "F3_government_distrust",
    "F4_religious_traditionalism",
    "F5_populist_conservatism",
]

# Pure party cluster index → candidate_code (from generate_presidential_ballots.py)
PURE_CODES = {0: "RH", 1: "MW", 2: "MRJ", 3: "BE", 4: "CO", 5: "DH", 6: "LK", 8: "ZN", 9: "JR"}
# Cluster index → party abbreviation
CLUSTER_PARTY = {0: "CON", 1: "LBR", 2: "STY", 3: "NAT", 4: "LIB", 5: "REF", 6: "CTR", 8: "DSA", 9: "PRG"}

# Light fusion definitions: (code, primary_cluster, secondary_cluster)
# F5 adjacency order: PRG(-0.99), LIB(-0.95), DSA(-0.87), SD(-0.56), STY(-0.06),
#                     CTR(0.04),  CON(0.44),  REF(0.99),  NAT(1.51)
LIGHT_FUSION = [
    ("PRG_dsa", 9, 8),   # PRG leaning DSA
    ("DSA_prg", 8, 9),   # DSA leaning PRG
    ("DSA_lib", 8, 4),   # DSA leaning LIB
    ("LIB_dsa", 4, 8),   # LIB leaning DSA
    ("LIB_sd",  4, 1),   # LIB leaning SD
    ("LBR_lib",  1, 4),   # SD leaning LIB
    ("LBR_sty",  1, 2),   # SD leaning STY
    ("STY_sd",  2, 1),   # STY leaning SD
    ("STY_ctr", 2, 6),   # STY leaning CTR
    ("CTR_sty", 6, 2),   # CTR leaning STY
    ("CTR_con", 6, 0),   # CTR leaning CON
    ("CON_ctr", 0, 6),   # CON leaning CTR
    ("CON_ref", 0, 5),   # CON leaning REF
    ("REF_con", 5, 0),   # REF leaning CON
    ("REF_nat", 5, 3),   # REF leaning NAT
    ("NAT_ref", 3, 5),   # NAT leaning REF
]


def main():
    # Load existing centroids (pure + blended)
    raw_centroids = {}
    with open(CENTROIDS, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_centroids[row["candidate_code"]] = {
                col: float(row[col]) for col in FACTOR_COLS
            }

    # Build lookup: cluster_index → factor scores (from pure party codes)
    cluster_factors = {}
    for cluster_idx, code in PURE_CODES.items():
        if code in raw_centroids:
            cluster_factors[cluster_idx] = raw_centroids[code]

    # Compute 80/20 blends
    out_rows = []

    # Include all existing rows first
    with open(CENTROIDS, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            out_rows.append(row)

    # Append light fusion rows
    for code, primary_c, secondary_c in LIGHT_FUSION:
        p = cluster_factors[primary_c]
        s = cluster_factors[secondary_c]
        primary_party  = CLUSTER_PARTY[primary_c]
        secondary_party = CLUSTER_PARTY[secondary_c]
        display_name = code  # e.g. "STY_sd"
        row = {
            "candidate_code": code,
            "candidate_name": display_name,
        }
        for col in FACTOR_COLS:
            row[col] = round(0.80 * p[col] + 0.20 * s[col], 4)
        print(f"  {code:12s}  ({primary_party} 80% + {secondary_party} 20%)  "
              f"F5={row['F5_populist_conservatism']:+.4f}")
        out_rows.append(row)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        fieldnames = ["candidate_code", "candidate_name"] + FACTOR_COLS
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"\nWrote {len(out_rows)} candidates → {OUT_PATH}")
    print(f"  ({len(LIGHT_FUSION)} light fusion + {len(out_rows) - len(LIGHT_FUSION)} existing)")


if __name__ == "__main__":
    main()

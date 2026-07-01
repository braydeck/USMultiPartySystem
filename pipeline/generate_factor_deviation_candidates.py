#!/usr/bin/env python3
"""
generate_factor_deviation_candidates.py
----------------------------------------
Defines 37 factor-deviation (FD) candidates for the FD pipeline.

Each party gets hi/lo variants only on axes where its within-party SD
is >= 70% of the inter-party SD — i.e., axes where real internal
ideological variation exists.  F3 (Government Distrust) and F4
(Religious Traditionalism) are excluded: F3's inter-party SD is near-
zero; F4's inter-party SD is also very small (0.19 vs 0.76 for F1),
making the ±0.048 deviation negligible.

Active axes and qualifying parties (within/inter SD ratio >= 0.70):
  so  — Security & Order (F1)      → SD (0.72), STY (0.75)
  es  — Electoral Skepticism (F2)  → DSA (1.16), SD (0.88), STY (1.47),
                                      CON (0.91), POP (1.39), NAT (1.39)
  pc  — Populist Conservatism (F5) → LIB (0.72), SD (0.86), STY (1.21),
                                      CUP (0.99), CON (0.86), POP (1.09)

Deviation = 25% of the inter-party SD on each factor.

Candidate count:
  PRG  — base only                   =  1
  LIB  — base + PC×2                 =  3
  DSA  — base + ES×2                 =  3
  SD   — base + SO×2 + ES×2 + PC×2  =  7
  STY  — base + SO×2 + ES×2 + PC×2  =  7
  CUP  — base + PC×2                 =  3
  CON  — base + ES×2 + PC×2         =  5
  POP  — base + ES×2 + PC×2         =  5
  NAT  — base + ES×2                 =  3
  Total                               = 37

Outputs:
  data/outputs/factor_deviation/candidate_factor_centroids.csv
"""

import csv
import math
from pathlib import Path

BASE_DIR     = Path(__file__).parent.parent
CENTROIDS_IN = BASE_DIR / "data" / "outputs" / "candidate_factor_centroids.csv"
OUT_DIR      = BASE_DIR / "data" / "outputs" / "factor_deviation"
OUT_PATH     = OUT_DIR / "candidate_factor_centroids.csv"

FACTOR_COLS = [
    "F1_security_order",
    "F2_electoral_skepticism",
    "F3_government_distrust",
    "F4_religious_traditionalism",
    "F5_populist_conservatism",
]

# Pure-party candidate codes in the existing centroids file
PURE_CODES = {
    "CON": "RH",
    "LBR":  "MW",
    "STY": "MRJ",
    "NAT": "BE",
    "LIB": "CO",
    "POP": "DH",
    "CUP": "LK",
    "DSA": "ZN",
    "PRG": "JR",
}
PARTIES = list(PURE_CODES.keys())

# Parties that qualify for each axis (within-party SD / inter-party SD >= 0.70)
SO_PARTIES = {"LBR", "STY"}
ES_PARTIES = {"DSA", "LBR", "STY", "CON", "POP", "NAT"}
PC_PARTIES = {"LIB", "LBR", "STY", "CUP", "CON", "POP"}

AXIS_PARTIES = {"so": SO_PARTIES, "es": ES_PARTIES, "pc": PC_PARTIES}

# OAO (cluster 7) is a small party: base candidate only, no crossover variants.
# Centroid = weighted FS_F1..F5 mean of cluster 7 (matches clusterSpreads).
OAO_CENTROID = {
    "F1_security_order":          0.7235,
    "F2_electoral_skepticism":   -0.6288,
    "F3_government_distrust":      0.2912,
    "F4_religious_traditionalism": -0.1322,
    "F5_populist_conservatism":   -0.6845,
}

# Factor axis → column name (F3 and F4 excluded — inter-party SD too small)
AXIS_FACTOR_IDX = {"so": 0, "es": 1, "pc": 4}
AXIS_FACTOR_COL = {"so": "F1_security_order",
                   "es": "F2_electoral_skepticism",
                   "pc": "F5_populist_conservatism"}

DEVIATION_PCT = 0.25   # fraction of inter-party SD


def load_pure_centroids() -> dict[str, dict[str, float]]:
    """Return {party_abbr: {factor_col: value}} for the 9 base parties."""
    raw = {}
    with open(CENTROIDS_IN, newline="") as f:
        for row in csv.DictReader(f):
            raw[row["candidate_code"]] = {c: float(row[c]) for c in FACTOR_COLS}

    centroids = {}
    for party, code in PURE_CODES.items():
        centroids[party] = raw[code]
    return centroids


def compute_inter_party_sd(centroids: dict[str, dict[str, float]]) -> dict[str, float]:
    """Population SD of each factor across the 9 base party centroids."""
    sds = {}
    for col in FACTOR_COLS:
        vals = [centroids[p][col] for p in PARTIES]
        mean = sum(vals) / len(vals)
        var  = sum((v - mean) ** 2 for v in vals) / len(vals)
        sds[col] = math.sqrt(var)
    return sds


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    centroids = load_pure_centroids()

    print("Base party centroids:")
    print(f"  {'Party':5}  {'F1':>7}  {'F2':>7}  {'F3':>7}  {'F4':>7}  {'F5':>7}")
    for p in PARTIES:
        c = centroids[p]
        print(f"  {p:5}  "
              + "  ".join(f"{c[col]:>7.4f}" for col in FACTOR_COLS))

    sds = compute_inter_party_sd(centroids)
    print("\nInter-party SDs:")
    for col, sd in sds.items():
        print(f"  {col:<32}  SD={sd:.4f}  Δ(25%)=±{DEVIATION_PCT * sd:.4f}")

    # Build candidate list
    rows = []
    total = 0

    for party in PARTIES:
        base = centroids[party]
        axes = [a for a in AXIS_FACTOR_COL if party in AXIS_PARTIES[a]]

        # Base candidate
        rows.append({
            "candidate_code": party,
            "candidate_name": party,
            "party":          party,
            "axis":           "base",
            "direction":      "base",
            **{col: round(base[col], 4) for col in FACTOR_COLS},
        })
        total += 1

        # Deviation variants
        for axis in axes:
            col    = AXIS_FACTOR_COL[axis]
            delta  = DEVIATION_PCT * sds[col]

            for direction in ("hi", "lo"):
                sign  = +1 if direction == "hi" else -1
                code  = f"{party}_{direction}_{axis}"
                factors = {c: round(base[c], 4) for c in FACTOR_COLS}
                factors[col] = round(base[col] + sign * delta, 4)
                rows.append({
                    "candidate_code": code,
                    "candidate_name": code,
                    "party":          party,
                    "axis":           axis,
                    "direction":      direction,
                    **factors,
                })
                total += 1

    # OAO (cluster 7): base candidate only, no variants (small party)
    rows.append({
        "candidate_code": "OAO",
        "candidate_name": "OAO",
        "party":          "OAO",
        "axis":           "base",
        "direction":      "base",
        **{col: round(OAO_CENTROID[col], 4) for col in FACTOR_COLS},
    })
    total += 1

    print(f"\nGenerated {total} candidates:")
    for p in PARTIES:
        n = sum(1 for r in rows if r["party"] == p)
        active = [a for a in AXIS_FACTOR_COL if p in AXIS_PARTIES[a]]
        axes_str = f" ({'+'.join(active)})" if active else " (base only)"
        print(f"  {p}: {n} variants{axes_str}")

    # Verify no variant crosses nearest neighbor's centroid on its deviated axis
    print("\nNeighbor boundary check (warning if variant exceeds nearest neighbor on axis):")
    all_base = {p: centroids[p] for p in PARTIES}
    for row in rows:
        if row["axis"] == "base":
            continue
        col  = AXIS_FACTOR_COL[row["axis"]]
        val  = row[col]
        base_val = centroids[row["party"]][col]
        sign = +1 if row["direction"] == "hi" else -1
        # Find nearest neighbor in the direction of deviation
        neighbors = [(p, centroids[p][col]) for p in PARTIES if p != row["party"]]
        same_dir  = [(p, v) for p, v in neighbors if sign * (v - base_val) > 0]
        if same_dir:
            nearest_p, nearest_v = min(same_dir, key=lambda x: abs(x[1] - base_val))
            if sign * (val - nearest_v) > 0:
                print(f"  ⚠  {row['candidate_code']:18}  val={val:+.4f} crosses "
                      f"{nearest_p} ({nearest_v:+.4f}) on {col}")

    fieldnames = ["candidate_code", "candidate_name", "party", "axis", "direction"] + FACTOR_COLS
    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {total} candidates → {OUT_PATH.relative_to(BASE_DIR)}")
    print("\nSample rows (base + first SO variant per party):")
    shown = set()
    for r in rows:
        if r["party"] not in shown:
            print(f"  {r['candidate_code']:18}  "
                  + "  ".join(f"{r[c]:>7.4f}" for c in FACTOR_COLS))
        if r["axis"] == "hi" and r["direction"] in ("hi",):
            print(f"  {r['candidate_code']:18}  "
                  + "  ".join(f"{r[c]:>7.4f}" for c in FACTOR_COLS))
            shown.add(r["party"])


if __name__ == "__main__":
    main()

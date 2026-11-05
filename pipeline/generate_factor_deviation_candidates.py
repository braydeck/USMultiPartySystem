#!/usr/bin/env python3
"""
generate_factor_deviation_candidates.py
----------------------------------------
Defines the factor-deviation (FD, "crossover") candidates for the FD pipeline.

Each party gets hi/lo variants only on axes where its within-party SD is >= 70% of the
inter-party SD, i.e. axes where real internal ideological variation exists. The qualifying
parties are computed from the typology each run (the five-factor version froze them by hand).
Axes are the four app factor keys (pipeline/factor_keys.py): so = F1 Security & Order,
id = F2 Government Distrust (the code kept from the five-factor elections-distrust axis),
rt = F4 Cultural Conservatism, pc = F5 Economic Conservatism.

Deviation = 25% of the inter-party SD on each factor. Within-party SD is weighted
(commonpostweight) over the party's hard-cluster members; inter-party SD is the population SD
of the live parties' centroids.

Inputs:
  data/outputs/candidate_factor_centroids.csv   (archive/generate_candidate_profiles.py)
  data/processed/efa_factor_scores.csv, typology_cluster_assignments.csv (joined by caseid)
Outputs:
  data/outputs/factor_deviation/candidate_factor_centroids.csv
"""


import csv
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR     = Path(__file__).parent.parent
CENTROIDS_IN = BASE_DIR / "data" / "outputs" / "candidate_factor_centroids.csv"
OUT_DIR      = BASE_DIR / "data" / "outputs" / "factor_deviation"
OUT_PATH     = OUT_DIR / "candidate_factor_centroids.csv"

sys.path.insert(0, str(BASE_DIR / "pipeline"))
from factor_keys import CENTROID_COLS  # noqa: E402
from party_codes import LEFT_RIGHT, PARTY_TO_CLUSTER  # noqa: E402

FACTOR_COLS = list(CENTROID_COLS.values())
PARTIES = list(LEFT_RIGHT)
PURE_CODES = {p: p for p in PARTIES}   # base rows in candidate_factor_centroids.csv are keyed by party

AXIS_KEY = {"so": "F1", "id": "F2", "rt": "F4", "pc": "F5"}
AXIS_FACTOR_COL = {a: CENTROID_COLS[k] for a, k in AXIS_KEY.items()}
QUALIFY_RATIO = 0.70


def qualifying_parties(centroids):
    """{axis: set of parties whose weighted within-party SD >= QUALIFY_RATIO x inter-party SD}."""
    efa = pd.read_csv(BASE_DIR / "data" / "processed" / "efa_factor_scores.csv")
    typ = pd.read_csv(BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv", usecols=["caseid", "cluster"])
    df = efa.merge(typ, on="caseid", validate="one_to_one")
    inter = compute_inter_party_sd(centroids)
    out = {}
    for axis, key in AXIS_KEY.items():
        col = AXIS_FACTOR_COL[axis]
        out[axis] = set()
        for p in PARTIES:
            g = df[df["cluster"] == PARTY_TO_CLUSTER[p]]
            x, w = g[f"FS_{key}"].values, g["commonpostweight"].values
            sd = math.sqrt(np.average((x - np.average(x, weights=w)) ** 2, weights=w))
            if sd >= QUALIFY_RATIO * inter[col]:
                out[axis].add(p)
        print(f"  {axis}: {sorted(out[axis], key=PARTIES.index)}")
    return out


DEVIATION_PCT = 0.25   # fraction of inter-party SD


def load_pure_centroids() -> dict[str, dict[str, float]]:
    """Return {party_abbr: {factor_col: value}} for the live base parties."""
    raw = {}
    with open(CENTROIDS_IN, newline="") as f:
        for row in csv.DictReader(f):
            raw[row["candidate_code"]] = {c: float(row[c]) for c in FACTOR_COLS}

    centroids = {}
    for party, code in PURE_CODES.items():
        centroids[party] = raw[code]
    return centroids


def compute_inter_party_sd(centroids: dict[str, dict[str, float]]) -> dict[str, float]:
    """Population SD of each factor across the live base party centroids."""
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
    print(f"  {'Party':5}  " + "  ".join(f"{k:>7}" for k in AXIS_KEY.values()))
    for p in PARTIES:
        c = centroids[p]
        print(f"  {p:5}  "
              + "  ".join(f"{c[col]:>7.4f}" for col in FACTOR_COLS))

    sds = compute_inter_party_sd(centroids)
    print("\nQualifying parties per axis (within/inter SD >= 0.70):")
    AXIS_PARTIES = qualifying_parties(centroids)
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

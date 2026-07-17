#!/usr/bin/env python3
"""
generate_factor_deviation_stats.py
------------------------------------
Computes item-level survey statistics for all 71 FD candidates.

For each survey item and FD candidate:
  - Base value = pure party cluster statistic (from cluster_stats.csv)
  - Variant candidates: adjusted = base + slope(item, axis) × Δ_factor
    where slope(item, axis) = cov(item_values, factor_positions) / var(factor_positions)
    computed via OLS across 9 base party clusters.

Factor-sensitive flags (per row, per axis): True if the typical deviation
on that axis produces a shift > 3pp (binary/ordinal_dist) or > 5% of
the cross-cluster range (ordinal/continuous).

Outputs:
  data/outputs/factor_deviation/profiles/factor_deviation_stats.csv
    - 285 rows (same structure as cluster_stats.csv)
    - 71 candidate columns (base + all variants)
    - 4 factor_sensitive_* flag columns (so, ae, rt, pc)
"""

import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR      = Path(__file__).parent.parent
CLUSTER_STATS = BASE_DIR / "data" / "outputs" / "profiles" / "cluster_stats.csv"
FD_CANDIDATES = BASE_DIR / "data" / "outputs" / "factor_deviation" / "candidate_factor_centroids.csv"
OUT_DIR       = BASE_DIR / "data" / "outputs" / "factor_deviation" / "profiles"
OUT_PATH      = OUT_DIR / "factor_deviation_stats.csv"

# 10 active parties in cluster order
PARTY_ORDER      = ["CON", "LBR", "STY", "NAT", "LIB", "POP", "CUP", "OAO", "DSA", "PRG"]
PARTY_TO_CLUSTER = {"CON": 0, "LBR": 1, "STY": 2, "NAT": 3, "LIB": 4,
                     "POP": 5, "CUP": 6, "OAO": 7, "DSA": 8, "PRG": 9}

# Axis → column in the FD candidate CSV
AXIS_CAND_COL = {
    "so": "F1_security_order",
    "id": "F2_institutional_distrust",
    "rt": "F4_religious_traditionalism",
    "pc": "F5_populist_conservatism",
}
AXES = list(AXIS_CAND_COL.keys())

# Factor-sensitivity thresholds
BINARY_PP_THRESHOLD   = 3.0   # percentage-point shift for binary / ordinal_dist rows
ORDINAL_RANGE_FRAC    = 0.05  # fraction of cross-cluster range for ordinal rows
CONTINUOUS_THRESHOLD  = 1.0   # absolute shift for continuous rows (e.g., weeks)


def ols_slope(x_vals: list, y_vals: list) -> float:
    """Population OLS slope: cov(x, y) / var(x). Returns 0 for degenerate cases."""
    x = np.array(x_vals, dtype=float)
    y = np.array(y_vals, dtype=float)
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    if len(x) < 3:
        return 0.0
    vx = np.var(x)
    if vx < 1e-10:
        return 0.0
    return float(np.cov(x, y, ddof=0)[0, 1] / vx)


def clamp_value(val: float, row_type: str) -> float:
    if row_type in ("binary", "ordinal_dist"):
        return max(0.0, min(100.0, val))
    return val


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    sep  = "=" * 70
    thin = "-" * 70

    print(sep)
    print("FACTOR DEVIATION STATS")
    print(sep)

    # ── Load inputs ───────────────────────────────────────────────────────────
    print("\nLoading cluster stats…")
    stats_df = pd.read_csv(CLUSTER_STATS)
    print(f"  {len(stats_df)} rows × {len(stats_df.columns)} cols")

    print("Loading FD candidates…")
    fd_df = pd.read_csv(FD_CANDIDATES)
    cand_codes = fd_df["candidate_code"].tolist()
    print(f"  {len(fd_df)} candidates")

    # ── Build candidate lookup tables ─────────────────────────────────────────
    # base_factor: {party: {axis_col: value}} — factor position for each base party
    base_rows_df = fd_df[fd_df["axis"] == "base"].set_index("party")
    base_factor  = {
        p: {col: float(base_rows_df.loc[p, col]) for col in AXIS_CAND_COL.values()}
        for p in PARTY_ORDER
    }

    # cand_info: {code: {party, axis, direction, AXIS_CAND_COL values}}
    cand_info = {}
    for _, row in fd_df.iterrows():
        code = row["candidate_code"]
        cand_info[code] = {
            "party":     row["party"],
            "axis":      row["axis"],
            "direction": row["direction"],
            **{col: float(row[col]) for col in AXIS_CAND_COL.values()},
        }

    # ── x-axis values for OLS per axis (9 base party factor positions) ─────────
    x_by_axis = {
        axis: [base_factor[p][col] for p in PARTY_ORDER]
        for axis, col in AXIS_CAND_COL.items()
    }

    print(f"\nBase party factor positions used for OLS x-axis:")
    print(f"  {'Party':<6}  {'so(F1)':>8}  {'id(F2)':>8}  {'rt(F4)':>8}  {'pc(F5)':>8}")
    for p in PARTY_ORDER:
        print(f"  {p:<6}  " + "  ".join(f"{x_by_axis[ax][PARTY_ORDER.index(p)]:>8.4f}" for ax in AXES))

    # ── Pre-compute OLS slopes for all rows × axes ────────────────────────────
    print(f"\n{thin}")
    print("Computing OLS slopes (285 rows × 4 axes)…")

    slopes = {}  # {(row_idx, axis): slope}
    for idx, row in stats_df.iterrows():
        y_vals = []
        for p in PARTY_ORDER:
            col = f"c{PARTY_TO_CLUSTER[p]}"
            try:
                val = float(row[col]) if pd.notna(row[col]) else np.nan
            except (ValueError, KeyError):
                val = np.nan
            y_vals.append(val)

        for axis in AXES:
            slopes[(idx, axis)] = ols_slope(x_by_axis[axis], y_vals)

    # Spot-check
    SPOT_VARS = {"CC24_323b", "CC24_421_2", "CC24_340f", "CC24_325", "CC24_321d"}
    print(f"\n  Slope spot-check (high-loading items):")
    print(f"  {'Variable':<14}  {'stat_label':<22}  {'so(F1)':>8}  {'id(F2)':>8}  "
          f"{'rt(F4)':>8}  {'pc(F5)':>8}")
    for idx, row in stats_df.iterrows():
        if row["variable"] in SPOT_VARS and row["type"] in ("binary", "ordinal"):
            print(f"  {row['variable']:<14}  {row['stat_label']:<22}  "
                  + "  ".join(f"{slopes.get((idx, a), 0.0):>8.3f}" for a in AXES))

    # ── Build output rows ─────────────────────────────────────────────────────
    print(f"\n{thin}")
    print("Building candidate predictions for all rows…")

    out_rows = []
    flags_by_axis = {axis: [] for axis in AXES}

    for idx, row in stats_df.iterrows():
        out_row = {
            "variable":   row["variable"],
            "domain":     row["domain"],
            "type":       row["type"],
            "stat_label": row["stat_label"],
            "question":   row["question"],
            "overall":    row["overall"],
        }
        row_type = str(row["type"])

        # ── Candidate values ──────────────────────────────────────────────────
        for code in cand_codes:
            info        = cand_info[code]
            party       = info["party"]
            cluster_idx = PARTY_TO_CLUSTER[party]
            base_col    = f"c{cluster_idx}"

            try:
                base_val = float(row[base_col]) if pd.notna(row[base_col]) else np.nan
            except (ValueError, KeyError):
                base_val = np.nan

            if pd.isna(base_val) or info["axis"] == "base":
                out_row[code] = round(base_val, 4) if not pd.isna(base_val) else None
                continue

            axis      = info["axis"]
            axis_col  = AXIS_CAND_COL[axis]
            delta     = info[axis_col] - base_factor[party][axis_col]
            slope     = slopes.get((idx, axis), 0.0)
            adjusted  = clamp_value(base_val + slope * delta, row_type)
            out_row[code] = round(adjusted, 4)

        # ── Factor sensitivity flags ──────────────────────────────────────────
        for axis in AXES:
            axis_col = AXIS_CAND_COL[axis]
            slope    = slopes.get((idx, axis), 0.0)

            # Use delta from any "hi" variant of any party for this axis
            hi_codes = [c for c in cand_codes
                        if cand_info[c]["axis"] == axis and cand_info[c]["direction"] == "hi"]
            if not hi_codes:
                flags_by_axis[axis].append(False)
                continue

            max_shift = max(
                abs(slope * (cand_info[c][axis_col] - base_factor[cand_info[c]["party"]][axis_col]))
                for c in hi_codes
            )

            if row_type in ("binary", "ordinal_dist"):
                flags_by_axis[axis].append(max_shift > BINARY_PP_THRESHOLD)
            elif row_type == "ordinal":
                cluster_vals = [v for v in
                                [float(row.get(f"c{PARTY_TO_CLUSTER[p]}", np.nan)) for p in PARTY_ORDER]
                                if not np.isnan(v)]
                val_range    = (max(cluster_vals) - min(cluster_vals)) if len(cluster_vals) >= 2 else 1.0
                threshold    = ORDINAL_RANGE_FRAC * val_range if val_range > 0 else 0.05
                flags_by_axis[axis].append(max_shift > threshold)
            elif row_type == "continuous":
                flags_by_axis[axis].append(max_shift > CONTINUOUS_THRESHOLD)
            else:
                flags_by_axis[axis].append(False)

        out_rows.append(out_row)

    # ── Assemble DataFrame ────────────────────────────────────────────────────
    out_df = pd.DataFrame(out_rows)
    for axis in AXES:
        out_df[f"factor_sensitive_{axis}"] = flags_by_axis[axis]

    out_df.to_csv(OUT_PATH, index=False)
    print(f"\nWrote {len(out_df)} rows × {len(out_df.columns)} cols → {OUT_PATH.relative_to(BASE_DIR)}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{thin}")
    print("FACTOR SENSITIVITY SUMMARY")
    print(thin)
    axis_labels = {"so": "F1 Security/Order", "id": "F2 Inst. Distrust", "rt": "F4 Relig/Trad", "pc": "F5 Pop/Con"}
    for axis in AXES:
        col  = f"factor_sensitive_{axis}"
        n    = int(out_df[col].sum())
        vars_ = out_df[out_df[col]]["variable"].unique().tolist()
        print(f"\n  {axis.upper()} ({axis_labels[axis]}): {n}/{len(out_df)} rows sensitive")
        print(f"    Items: {', '.join(vars_[:10])}" + (" …" if len(vars_) > 10 else ""))

    # ── Sample output: show a few rows for CON variants ───────────────────────
    print(f"\n{thin}")
    print("SAMPLE: CON variants on key items (CC24_323b = border patrols, CC24_321d = police +10%)")
    print(thin)
    con_codes = [c for c in cand_codes if cand_info[c]["party"] == "CON"]
    sample_vars = ["CC24_323b", "CC24_321d", "CC24_325", "CC24_421_2"]
    for var in sample_vars:
        sub = out_df[out_df["variable"] == var]
        if sub.empty:
            continue
        row = sub.iloc[0]
        print(f"\n  {var} — {row['stat_label']} — {row['question'][:60]}")
        for code in con_codes:
            if code in row.index:
                val = row[code]
                axis = cand_info[code]["axis"]
                dirn = cand_info[code]["direction"]
                print(f"    {code:<18}  ({axis:>4} {dirn:<4})  {val}")

    print(f"\n{'=' * 70}")
    print("DONE")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()

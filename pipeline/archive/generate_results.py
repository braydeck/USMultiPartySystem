#!/usr/bin/env python3
"""
generate_results.py
--------------------
Produces all summary outputs in results/:

  house_seats_<factor>_categorical.png          — house STV seat semicircle (5 factors)
  senate_seats_<scenario>_<factor>_categorical.png  — senate semicircle (4 scenarios × 5 factors)
  chamber_profiles.csv                          — joint house + senate policy profiles
  vote_model.csv                                — combined house + senate vote model with
                                                  presidential ratification (mixed and pure)

Reads from data/outputs/. Requires senate_chamber_profile.csv to be current
(senate_chamber_profile.csv is now inert — its generator moved to pipeline/archive/ with the rest
of the retired blended-senator-type layer, so the senate charts here describe that old model).
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb, to_hex
from pathlib import Path
from scipy.stats import norm

BASE    = Path(__file__).parent.parent
DATA    = BASE / "data" / "outputs"
RESULTS = BASE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

CLUSTER_NAMES = {
    0: "CON", 1: "LBR", 2: "STY", 3: "NAT", 4: "LIB",
    5: "POP", 6: "CUP", 7: "OAO", 8: "DSA", 9: "PRG",
}

PARTY_COLORS = {
    "DSA": "#E6194B", "PRG": "#F032E6", "LIB": "#911EB4",
    "LBR":  "#4363D8", "CUP": "#A9A9A9", "STY": "#3CB44B",
    "POP": "#F58231", "CON": "#9A6324", "NAT": "#000000",
    "OAO":  "#000000",
}

# ── Factor scores for all senate/house-relevant party types ───────────────────
# Source: senate_candidate_factor_centroids.csv + main candidate_factor_centroids.csv
# Computed types (POP/SD, CUP/LIB, PRG/DSA) derived from weighted cluster centroids.
# Format: [F1, F2, F3, F4, F5]
TYPE_SCORES = {
    # Pure clusters (all scenarios)
    "CON":     [ 0.7674, -0.0235,  0.1108,  0.2186,  0.4424],
    "LBR":      [-0.4143, -0.0321,  0.0915, -0.3447, -0.5640],
    "STY":     [-0.4460,  0.6579,  0.1333,  0.1645, -0.0623],
    "NAT":     [ 0.7366,  0.4278, -0.2078,  0.4573,  1.5101],
    "LIB":     [-0.4623, -0.7437, -0.0862, -0.3230, -0.9496],
    "POP":     [ 0.2023,  0.7593, -0.2061,  0.1470,  0.9903],
    "CUP":     [ 0.2658, -0.8166, -0.1744,  0.1296,  0.0387],
    "DSA":     [-1.3034,  0.5040,  0.0761, -0.3869, -0.8740],
    "PRG":     [-1.2600, -0.6338, -0.2057, -0.3869, -0.9900],
    "OAO":     [ 0.7235, -0.6288,  0.2912, -0.1322, -0.6845],
    # Co-occurrence blends from senate centroids (w_primary = 0.70)
    "CON/CUP": [ 0.5768, -0.3248,  0.0024,  0.1848,  0.2890],
    "CON/NAT": [ 0.7523,  0.1976, -0.0453,  0.3356,  0.9656],
    "CON/POP": [ 0.5922,  0.2192,  0.0126,  0.1964,  0.6122],
    "CON/LBR":  [ 0.2357, -0.0274,  0.1021, -0.0349, -0.0105],
    "CON/STY": [ 0.2577,  0.2627,  0.1202,  0.1959,  0.2304],
    "LBR/CON":  [ 0.1529, -0.0280,  0.1007, -0.0743, -0.0809],
    "LBR/CUP":  [-0.1219, -0.3694, -0.0228, -0.1408, -0.3048],
    "LBR/LIB":  [-0.4378, -0.3808,  0.0044, -0.3341, -0.7529],
    "LBR/STY":  [-0.4247,  0.1956,  0.1053, -0.1767, -0.3984],
    "STY/CON": [ 0.0758,  0.3649,  0.1236,  0.1878,  0.1547],
    "STY/POP": [-0.1543,  0.7035, -0.0194,  0.1566,  0.4114],
    "STY/LBR":  [-0.4301,  0.3129,  0.1124, -0.0901, -0.3132],
    "POP/STY": [-0.0376,  0.7218, -0.0805,  0.1535,  0.6008],
    "LIB/CUP": [-0.1711, -0.7729, -0.1215, -0.1420, -0.5543],
    # Computed: POP/SD wildcard (w = 0.55)
    "POP/LBR":  [
        0.55 * 0.2023 + 0.45 * (-0.4143),   # F1 = -0.075
        0.55 * 0.7593 + 0.45 * (-0.0321),   # F2 =  0.403
        0.55 * (-0.2061) + 0.45 * 0.0915,   # F3 = -0.072
        0.55 * 0.1470 + 0.45 * (-0.3447),   # F4 = -0.074
        0.55 * 0.9903 + 0.45 * (-0.5640),   # F5 =  0.291
    ],
    # Computed: CUP/LIB wildcard (w = 0.50)
    "CUP/LIB": [
        0.50 * 0.2658 + 0.50 * (-0.4623),   # F1 = -0.098
        0.50 * (-0.8166) + 0.50 * (-0.7437),# F2 = -0.780
        0.50 * (-0.1744) + 0.50 * (-0.0862),# F3 = -0.130
        0.50 * 0.1296 + 0.50 * (-0.3230),   # F4 = -0.097
        0.50 * 0.0387 + 0.50 * (-0.9496),   # F5 = -0.455
    ],
    # Computed: PRG/DSA cooc (w = 0.70)
    "PRG/DSA": [
        0.70 * (-1.2600) + 0.30 * (-1.3034),# F1 = -1.273
        0.70 * (-0.6338) + 0.30 * 0.5040,   # F2 = -0.292
        0.70 * (-0.2057) + 0.30 * 0.0761,   # F3 = -0.121
        0.70 * (-0.3869) + 0.30 * (-0.3869),# F4 = -0.387
        0.70 * (-0.9900) + 0.30 * (-0.8740),# F5 = -0.955
    ],
}

# Factor index in TYPE_SCORES list
FACTOR_IDX = {"F1": 0, "F2": 1, "F3": 2, "F4": 3, "F5": 4}

# Per-factor tier thresholds (VeryLow|Low|Medium|High|VeryHigh boundaries)
# Derived from FanCharts.py tier assignments for existing types.
# Tuple: (vl_l, l_m, m_h, h_vh)  — four cut-points for five tiers.
FACTOR_INFO = {
    "F1": {
        "label":      "Security Order",
        "thresholds": (-1.00, -0.20,  0.25, 0.74),
    },
    "F2": {
        "label":      "Electoral Skepticism",
        "thresholds": (-0.76, -0.28,  0.25, 0.73),
    },
    "F3": {
        "label":      "Government Distrust",
        # All types cluster in Medium; wide outer bounds leave VL/VH empty.
        "thresholds": (-1.00, -0.50,  0.20, 0.50),
    },
    "F4": {
        "label":      "Religious Traditionalism",
        # Only Low / Medium / High populated; VL and VH left empty.
        "thresholds": (-1.00, -0.31,  0.32, 1.00),
    },
    "F5": {
        "label":      "Populist Conservatism",
        "thresholds": (-0.63, -0.27,  0.27, 0.85),
    },
}


# ═══════════════════════════════════════════════════════════════════════
# SEAT LAYOUT PNGs
# ═══════════════════════════════════════════════════════════════════════

def type_color(t: str) -> str:
    if "/" in t:
        parts = t.split("/")
        rgbs = [np.array(to_rgb(PARTY_COLORS.get(p, "#888888"))) for p in parts]
        return to_hex(np.mean(rgbs, axis=0))
    return PARTY_COLORS.get(t, "#888888")


def factor_tier(score: float, thresholds: tuple) -> tuple:
    vl_l, l_m, m_h, h_vh = thresholds
    if score < vl_l:  return 0, "Very Low"
    if score < l_m:   return 1, "Low"
    if score < m_h:   return 2, "Medium"
    if score < h_vh:  return 3, "High"
    return 4, "Very High"


def hemicycle_coords(n_seats: int):
    if n_seats == 0:
        return np.array([]), np.array([])
    nrows = max(1, int(np.sqrt(n_seats) * 0.4))
    radii = np.linspace(1, 2, nrows)
    ideal = (n_seats * radii) / radii.sum()
    spr   = ideal.round().astype(int)
    diff  = n_seats - spr.sum()
    while diff != 0:
        idx  = len(spr) - 1
        adj  = 1 if diff > 0 else -1
        spr[idx] += adj
        diff -= adj
        idx   = (idx - 1) % len(spr)
    xx, yy, aa = [], [], []
    for r, n in zip(radii, spr):
        if n == 0:
            continue
        theta = np.linspace(np.pi, 0, n)
        xx.extend(r * np.cos(theta))
        yy.extend(r * np.sin(theta))
        aa.extend(theta)
    coords = np.column_stack((xx, yy, aa))
    s = coords[np.argsort(coords[:, 2])[::-1]]
    return s[:, 0], s[:, 1]


def plot_hemicycle(seats_dict: dict, title: str, out_path: Path,
                   factor_key: str):
    """Build and save a parliament semicircle chart ordered by the given factor."""
    info        = FACTOR_INFO[factor_key]
    thresholds  = info["thresholds"]
    tier_order  = ["Very Low", "Low", "Medium", "High", "Very High"]
    bg          = "#f5f5f5"

    records = []
    skipped = {}
    for t, count in seats_dict.items():
        if count == 0:
            continue
        scores = TYPE_SCORES.get(t)
        if scores is None:
            skipped[t] = count
            continue
        score    = scores[FACTOR_IDX[factor_key]]
        tier_id, tier_label = factor_tier(score, thresholds)
        for _ in range(count):
            records.append({"type": t, "tier_id": tier_id,
                            "tier_label": tier_label, "score": score})
    if skipped:
        print(f"    ⚠ Missing scores for: {skipped} — omitted")
    records.sort(key=lambda r: (r["tier_id"], r["score"]))

    colors_list = [type_color(r["type"]) for r in records]
    legend_dict = {r["type"]: type_color(r["type"]) for r in records}
    tier_counts = {}
    for r in records:
        tier_counts[r["tier_label"]] = tier_counts.get(r["tier_label"], 0) + 1

    n = len(records)
    if n == 0:
        return

    fig, ax = plt.subplots(figsize=(10, 6), facecolor=bg)
    ax.set_facecolor(bg)
    plt.subplots_adjust(top=0.85, bottom=0.2)

    x, y = hemicycle_coords(n)
    ms   = 40 if n < 200 else 10
    ax.scatter(x, y, c=colors_list, s=ms, marker="s",
               edgecolors="#555555", linewidths=0.5)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-2.5, 2.5)
    ax.set_ylim(-0.1, 2.8)

    R_inner, R_outer, label_R = 0.9, 2.1, 2.3
    cum = 0
    for tier in tier_order:
        cnt = tier_counts.get(tier, 0)
        if cnt == 0:
            continue
        start_idx = cum
        end_idx   = cum + cnt
        start_a   = np.arctan2(y[start_idx], x[start_idx])
        last_a    = np.arctan2(y[end_idx - 1], x[end_idx - 1])
        if tier != "Very High" and end_idx < n:
            next_a = np.arctan2(y[end_idx], x[end_idx])
            div_a  = np.mean([last_a, next_a])
            ax.plot(
                [R_inner * np.cos(div_a), R_outer * np.cos(div_a)],
                [R_inner * np.sin(div_a), R_outer * np.sin(div_a)],
                color="black", lw=1.5, alpha=0.5,
            )
        mid_a = np.mean([start_a, last_a])
        rot   = np.degrees(mid_a) - 90
        ax.text(
            label_R * np.cos(mid_a), label_R * np.sin(mid_a), tier,
            ha="center", va="center", rotation=rot,
            fontweight="bold", fontsize=12,
        )
        cum += cnt

    ax.set_title(title, fontsize=16, fontweight="bold", pad=15)
    ax.axis("off")

    sorted_legend = sorted(legend_dict.items())
    elems = [
        plt.Line2D([0], [0], marker="s", color=bg, label=k,
                   markerfacecolor=v, markeredgecolor="#555555", markersize=10)
        for k, v in sorted_legend
    ]
    fig.legend(
        handles=elems, loc="lower center", ncol=min(len(sorted_legend), 5),
        title="Party Types", facecolor=bg, frameon=False,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, bbox_inches="tight", dpi=150)
    plt.close()


def generate_seat_charts():
    print("\n── SEAT LAYOUT CHARTS ────────────────────────────────────────")

    # House seat counts
    # The canonical 873-seat chamber, not No_C7_canonical's 850-seat older run.
    house_summary = pd.read_csv(DATA / "pure_multi" / "house" / "stv_seat_summary.csv")
    house_seats   = {
        CLUSTER_NAMES[int(r["party"])]: int(r["NATIONAL"])
        for _, r in house_summary.iterrows()
    }
    total_house = sum(v for v in house_seats.values() if v > 0)

    # Senate seat counts (4 scenarios)
    senate_scenarios = [
        ("mixed_condorcet", DATA / "senate" / "senate_composition.csv",
         "senator_code", "Mixed Senate — Condorcet"),
        ("mixed_irv",       DATA / "senate" / "senate_irv_composition.csv",
         "winner_code",  "Mixed Senate — IRV"),
        ("pure_condorcet",  DATA / "pure_only" / "senate" / "senate_composition.csv",
         "senator_code", "Pure Senate — Condorcet"),
        ("pure_irv",        DATA / "pure_only" / "senate" / "senate_irv_composition.csv",
         "winner_code",  "Pure Senate — IRV"),
    ]
    senate_seat_dicts = []
    for name, path, col, label in senate_scenarios:
        df    = pd.read_csv(path)
        seats = df[col].value_counts().to_dict()
        senate_seat_dicts.append((name, seats, label))

    # Generate one chart per factor × scenario
    for fkey, finfo in FACTOR_INFO.items():
        flabel = finfo["label"]
        fid    = fkey.lower()  # "f1" … "f5"

        # House
        fname = f"house_seats_{fid}_categorical.png"
        plot_hemicycle(
            house_seats,
            f"House Seats: {flabel}\n(Total Seats: {total_house})",
            RESULTS / fname,
            fkey,
        )
        print(f"  → {fname}")

        # Senate scenarios
        for name, seats, label in senate_seat_dicts:
            total = sum(seats.values())
            fname = f"senate_seats_{name}_{fid}_categorical.png"
            plot_hemicycle(
                seats,
                f"{label}: {flabel}\n(Total Seats: {total})",
                RESULTS / fname,
                fkey,
            )
            print(f"  → {fname}")


# ═══════════════════════════════════════════════════════════════════════
# JOINT CHAMBER PROFILES
# ═══════════════════════════════════════════════════════════════════════

def create_joint_profile():
    print("\n── JOINT CHAMBER PROFILES ────────────────────────────────────")

    senate_prof = pd.read_csv(DATA / "senate" / "senate_chamber_profile.csv")
    house_prof  = pd.read_csv(DATA / "house_chamber_profile.csv")

    meta_cols     = ["variable", "domain", "type", "stat_label", "question", "overall"]
    agg_cols      = [c for c in senate_prof.columns if "chamber" in c or "bloc" in c]
    sen_type_cols = [c for c in senate_prof.columns if c not in meta_cols and c not in agg_cols]
    house_only    = ["NAT", "OAO", "DSA", "PRG"]

    joint = senate_prof[meta_cols].copy()

    for col in sen_type_cols:
        joint[col] = senate_prof[col].values

    for col in house_only:
        if col in house_prof.columns:
            joint[col] = house_prof[col].values

    joint["house_chamber"] = house_prof["house_chamber"].values

    for col in agg_cols:
        joint[col] = senate_prof[col].values

    out_path = RESULTS / "chamber_profiles.csv"
    joint.to_csv(out_path, index=False)
    print(f"  → chamber_profiles.csv  ({len(joint)} rows × {len(joint.columns)} cols)")
    return joint


# ═══════════════════════════════════════════════════════════════════════
# COMBINED VOTE MODEL
# ═══════════════════════════════════════════════════════════════════════

VERDICT_PASS   = "PASS"
VERDICT_FAIL   = "FAIL"
VERDICT_TOSSUP = "TOSS-UP"


def verdict(prob: float) -> str:
    if prob >= 0.67:
        return VERDICT_PASS
    if prob <= 0.33:
        return VERDICT_FAIL
    return VERDICT_TOSSUP


def compute_vote_model(variables, type_cols, type_profiles_df, seats, majority, label):
    """
    Compute expected-yes / sigma / prob-pass for each variable.
    type_profiles_df: DataFrame indexed by variable, columns = type names (values 0–100).
    seats: {type_label: seat_count}
    """
    exp_yes, sigmas, probs, verdicts = [], [], [], []
    for var in variables:
        mu, sig2 = 0.0, 0.0
        for t in type_cols:
            n_t = seats.get(t, 0)
            if n_t == 0:
                continue
            if t not in type_profiles_df.columns or var not in type_profiles_df.index:
                continue
            val = type_profiles_df.loc[var, t]
            if pd.isna(val):
                continue
            p_t   = float(np.clip(val / 100.0, 0.0, 1.0))
            mu   += n_t * p_t
            sig2 += n_t * p_t * (1.0 - p_t)
        sigma = float(np.sqrt(sig2)) if sig2 > 0 else 1e-9
        z     = (majority - 0.5 - mu) / sigma
        prob  = float(1.0 - norm.cdf(z))
        exp_yes.append(round(mu, 2))
        sigmas.append(round(sigma, 2))
        probs.append(round(prob, 4))
        verdicts.append(verdict(prob))

    total  = sum(seats.get(t, 0) for t in type_cols)
    n_pass = sum(1 for v in verdicts if v == VERDICT_PASS)
    n_tu   = sum(1 for v in verdicts if v == VERDICT_TOSSUP)
    n_fail = sum(1 for v in verdicts if v == VERDICT_FAIL)
    print(f"  {label}: {total} seats — {n_pass} PASS / {n_tu} TOSS-UP / {n_fail} FAIL")
    return {"expected_yes": exp_yes, "sigma": sigmas, "prob_pass": probs, "verdict": verdicts}


def create_vote_model():
    print("\n── COMBINED VOTE MODEL ───────────────────────────────────────")

    senate_vm = pd.read_csv(DATA / "senate" / "senate_vote_model.csv")
    house_vm  = pd.read_csv(DATA / "house_vote_model.csv")

    senate_binary = senate_vm[senate_vm["variable"].str.startswith("CC24_")].reset_index(drop=True)
    house_binary  = house_vm[house_vm["variable"].str.startswith("CC24_")].reset_index(drop=True)
    variables     = senate_binary["variable"].tolist()

    out = senate_binary[["variable", "domain", "question", "overall_pct"]].copy()

    # House
    hb = house_binary.set_index("variable")
    for col in ["house_expected_yes", "house_sigma", "house_prob_pass", "house_verdict"]:
        out[col] = [hb.loc[v, col] if v in hb.index else np.nan for v in variables]

    # Mixed senate (rename existing columns for clarity)
    for old, new in [
        ("cond_expected_yes", "senate_cond_expected_yes"),
        ("cond_sigma",        "senate_cond_sigma"),
        ("cond_prob_pass",    "senate_cond_prob_pass"),
        ("cond_verdict",      "senate_cond_verdict"),
        ("irv_expected_yes",  "senate_irv_expected_yes"),
        ("irv_sigma",         "senate_irv_sigma"),
        ("irv_prob_pass",     "senate_irv_prob_pass"),
        ("irv_verdict",       "senate_irv_verdict"),
    ]:
        out[new] = senate_binary[old].values

    # Pure senate vote model — use house_chamber_profile for pure type stances
    house_prof = pd.read_csv(DATA / "house_chamber_profile.csv")
    pure_binary_prof = house_prof[
        (house_prof["stat_label"] == "% Supporting") &
        (house_prof["variable"].str.startswith("CC24_"))
    ].set_index("variable")

    PURE_TYPES      = ["CON", "LBR", "STY", "CUP", "POP", "LIB", "OAO", "DSA", "PRG"]
    SENATE_MAJORITY = 26

    cond_pure_seats = (
        pd.read_csv(DATA / "pure_only" / "senate" / "senate_composition.csv")["senator_code"]
        .value_counts().to_dict()
    )
    irv_pure_seats = (
        pd.read_csv(DATA / "pure_only" / "senate" / "senate_irv_composition.csv")["winner_code"]
        .value_counts().to_dict()
    )

    cond_pure_res = compute_vote_model(
        variables, PURE_TYPES, pure_binary_prof, cond_pure_seats,
        SENATE_MAJORITY, "Pure Condorcet Senate",
    )
    irv_pure_res = compute_vote_model(
        variables, PURE_TYPES, pure_binary_prof, irv_pure_seats,
        SENATE_MAJORITY, "Pure IRV Senate",
    )
    for suffix, vals in cond_pure_res.items():
        out[f"senate_cond_pure_{suffix}"] = vals
    for suffix, vals in irv_pure_res.items():
        out[f"senate_irv_pure_{suffix}"]  = vals

    # Presidential ratification
    # Mixed president: CON/SD (IRV general winner = Ranked-Pairs primary winner)
    # Pure  president: STY   (same for both methods in the pure pipeline)
    senate_prof = pd.read_csv(DATA / "senate" / "senate_chamber_profile.csv")
    senate_binary_prof = senate_prof[
        (senate_prof["stat_label"] == "% Supporting") &
        (senate_prof["variable"].str.startswith("CC24_"))
    ].set_index("variable")

    pres_mixed_pct = np.array([
        senate_binary_prof.loc[v, "CON/LBR"] if v in senate_binary_prof.index else np.nan
        for v in variables
    ])
    pres_pure_pct = np.array([
        senate_binary_prof.loc[v, "STY"] if v in senate_binary_prof.index else np.nan
        for v in variables
    ])

    out["pres_mixed_support_pct"] = np.round(pres_mixed_pct, 2)
    out["pres_mixed_signs"]       = np.where(pres_mixed_pct > 50, "SIGN", "VETO")
    out["pres_pure_support_pct"]  = np.round(pres_pure_pct, 2)
    out["pres_pure_signs"]        = np.where(pres_pure_pct > 50, "SIGN", "VETO")

    # Becomes-law: house PASS AND senate PASS AND president SIGN
    def is_law(hv, sv, ps):
        return (
            pd.Series(hv == VERDICT_PASS) &
            pd.Series(sv == VERDICT_PASS) &
            pd.Series(ps == "SIGN")
        )

    out["law_cond_mixed"] = is_law(
        out["house_verdict"].values, out["senate_cond_verdict"].values, out["pres_mixed_signs"].values)
    out["law_irv_mixed"]  = is_law(
        out["house_verdict"].values, out["senate_irv_verdict"].values,  out["pres_mixed_signs"].values)
    out["law_cond_pure"]  = is_law(
        out["house_verdict"].values, out["senate_cond_pure_verdict"].values, out["pres_pure_signs"].values)
    out["law_irv_pure"]   = is_law(
        out["house_verdict"].values, out["senate_irv_pure_verdict"].values,  out["pres_pure_signs"].values)

    out.to_csv(RESULTS / "vote_model.csv", index=False)
    print(f"\n  → vote_model.csv  ({len(out)} items)")
    for col in ["law_cond_mixed", "law_irv_mixed", "law_cond_pure", "law_irv_pure"]:
        print(f"    {col}: {out[col].sum()}/{len(out)} bills become law")


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    print("=== generate_results.py ===")
    print(f"Output directory: {RESULTS}\n")
    generate_seat_charts()
    create_joint_profile()
    create_vote_model()
    print("\n✓ Done.")


if __name__ == "__main__":
    main()

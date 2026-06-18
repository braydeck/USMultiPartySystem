#!/usr/bin/env python3
"""
cross_chamber_coalitions.py
---------------------------
Identifies cross-chamber legislative coalitions by analyzing where senate and
house party types align *within* each of the 5 ideological factor dimensions.

Unlike senate_voting_blocs.py (which clusters in 5D simultaneously), this
script shows per-factor alignment — revealing which types form natural partners
on each specific ideological axis (security, electoralism, govt distrust, etc.).

The "within the five factor space" framing means:
  • k=2 (poles): relative split via 1D k-means on the 23 winner types —
    shows which side of the winner set each type falls on per factor.
  • k=5 (tiers): absolute thresholds against the full EFA scale (mean≈0,
    SD≈1), so labels reflect position relative to the whole electorate:
      Very High > +0.75 | High +0.25–+0.75 | Medium -0.25–+0.25
      Low -0.75–-0.25   | Very Low < -0.75
    A factor where all winners land in "Medium" is informative — it means
    that dimension does not differentiate winning coalitions.
  • Pairwise factor alignment is computed as 1 - (per-factor distance / max)
    so 1.0 = perfect alignment, 0.0 = maximally opposed on that factor.
  • An overall coalition affinity score is also computed from 5D Euclidean
    proximity (inverted and normalised).

Types included
--------------
  Senate (20): all types from senate_candidate_factor_centroids.csv
  House-only (3): NAT, DSA, PRG — pure house parties absent from senate
  C7 (Blue Dogs) excluded: always pre-dissolved, 0 seats.

Inputs
------
  Claude/outputs/senate/senate_candidate_factor_centroids.csv
  Claude/outputs/candidate_factor_centroids.csv
  Claude/outputs/senate/senate_composition.csv
  Claude/outputs/senate/senate_irv_composition.csv
  Claude/outputs/No_C7_canonical/stv_seat_summary.csv

Outputs
-------
  Claude/outputs/coalitions/coalition_type_profiles.csv
      One row per type: factor positions, chamber tag, seat counts.

  Claude/outputs/coalitions/coalition_factor_alignment.csv
      Per-factor ranking of all types with k=2 (pole) and k=3 (tier)
      cluster assignments.  One row per (factor × type).

  Claude/outputs/coalitions/coalition_pairwise.csv
      All type pairs: per-factor absolute distance, 5D Euclidean distance,
      and per-factor alignment score (0–1, higher = more aligned).
"""

import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.cluster import KMeans

BASE    = Path(__file__).parent.parent
SEN_DIR = BASE / "data" / "outputs" / "senate"
OUT_DIR = BASE / "data" / "outputs" / "coalitions"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FACTOR_COLS = [
    "F1_security_order",
    "F2_electoral_skepticism",
    "F3_government_distrust",
    "F4_religious_traditionalism",
    "F5_populist_conservatism",
]
FACTOR_SHORT = {
    "F1_security_order":           "F1_SecOrd",
    "F2_electoral_skepticism":     "F2_ElecSkep",
    "F3_government_distrust":      "F3_GovtDis",
    "F4_religious_traditionalism": "F4_ReligTrad",
    "F5_populist_conservatism":    "F5_PopCons",
}

# Human-readable pole labels per factor (high score direction → low score direction)
FACTOR_POLES = {
    "F1_security_order":           ("High Security/Order",    "Low Security (Liberty)"),
    "F2_electoral_skepticism":     ("High Elec. Skepticism",  "Low Skepticism (Pro-Sys)"),
    "F3_government_distrust":      ("High Govt Distrust",     "Low Govt Distrust"),
    "F4_religious_traditionalism": ("High Relig. Trad.",      "Low Relig. Trad. (Secular)"),
    "F5_populist_conservatism":    ("High Populist-Right",    "Low Populist (Progressive)"),
}

# House-only pure parties to add (must not already appear in senate centroids)
HOUSE_ONLY_NAMES = {"NAT", "DSA", "PRG"}

# Pure party names that appear in BOTH chambers (senate + house seats)
BOTH_CHAMBERS = {"CON", "SD", "STY", "POP", "LIB", "CUP"}


# ── Helpers ──────────────────────────────────────────────────────────────────

# Absolute tier thresholds (EFA factors are standardised, mean≈0 SD≈1)
TIER_BREAKS = [(-np.inf, -0.75), (-0.75, -0.25), (-0.25, 0.25), (0.25, 0.75), (0.75, np.inf)]
TIER_LABELS = ["Very Low", "Low", "Medium", "High", "Very High"]


def kmeans_1d(values: np.ndarray, k: int = 2, random_state: int = 42) -> np.ndarray:
    """Run k-means on a 1D array; return labels sorted by centroid (0=lowest)."""
    km = KMeans(n_clusters=k, n_init=20, random_state=random_state)
    raw = km.fit_predict(values.reshape(-1, 1))
    order = np.argsort(km.cluster_centers_.ravel())
    remap = {old: new for new, old in enumerate(order)}
    return np.array([remap[r] for r in raw])


def absolute_tier(score: float) -> tuple[int, str]:
    """Map a factor score to (tier_id 0–4, label) using absolute thresholds."""
    for i, (lo, hi) in enumerate(TIER_BREAKS):
        if lo <= score < hi:
            return i, TIER_LABELS[i]
    return 4, TIER_LABELS[4]  # score == +inf edge case


def pole_label(cluster_id: int, factor: str) -> str:
    """Human-readable label for a k=2 pole cluster."""
    high_label, low_label = FACTOR_POLES[factor]
    return high_label if cluster_id == 1 else low_label


# ── Load data ─────────────────────────────────────────────────────────────────

# Senate type centroids (20 types)
senate_cents = pd.read_csv(
    SEN_DIR / "senate_candidate_factor_centroids.csv"
)[["candidate_label"] + FACTOR_COLS].rename(columns={"candidate_label": "type"})

# All pure-party centroids (for NAT, DSA, PRG)
pure_cents = pd.read_csv(
    BASE / "data" / "outputs" / "candidate_factor_centroids.csv"
)[["candidate_name"] + FACTOR_COLS].rename(columns={"candidate_name": "type"})
house_only = pure_cents[pure_cents["type"].isin(HOUSE_ONLY_NAMES)].copy()

# Combine and tag chambers
senate_cents["chamber"] = senate_cents["type"].map(
    lambda t: "both" if t in BOTH_CHAMBERS else "senate"
)
house_only["chamber"] = "house"

types_df = pd.concat([senate_cents, house_only], ignore_index=True)

print(f"  Total types: {len(types_df)}  "
      f"(senate={len(senate_cents)}, house_only={len(house_only)})")

# ── Senate seat counts ────────────────────────────────────────────────────────
cond_comp = pd.read_csv(SEN_DIR / "senate_composition.csv")
irv_comp  = pd.read_csv(SEN_DIR / "senate_irv_composition.csv")

cond_seats = (cond_comp["senator_label"]
              .value_counts()
              .rename("seats_senate_cond")
              .rename_axis("type"))
irv_seats  = (irv_comp["winner_label"]
              .value_counts()
              .rename("seats_senate_irv")
              .rename_axis("type"))

# ── House seat counts ─────────────────────────────────────────────────────────
house_seats_raw = pd.read_csv(
    BASE / "data" / "outputs" / "No_C7_canonical" / "stv_seat_summary.csv"
)[["party_name", "NATIONAL"]].rename(
    columns={"party_name": "type", "NATIONAL": "seats_house"}
)
# Normalise names: stv_seat_summary uses full names, we need short names
NAME_MAP = {
    "Conservative":   "CON",
    "Social Democrat":"SD",
    "Solidarity":     "STY",
    "Nationalist":    "NAT",
    "Liberal":        "LIB",
    "Populist":         "POP",
    "Civic Union Party":         "CUP",
    "DSA":            "DSA",
    "Progressive":    "PRG",
    "Blue Dogs":      "C7",   # excluded (0 seats)
}
house_seats_raw["type"] = house_seats_raw["type"].map(NAME_MAP)
house_seats = (house_seats_raw
               .dropna(subset=["type"])
               .query("type != 'C7'")
               .set_index("type")["seats_house"])

# ── Merge seat counts ─────────────────────────────────────────────────────────
types_df = (types_df
            .set_index("type")
            .join(cond_seats, how="left")
            .join(irv_seats,  how="left")
            .join(house_seats, how="left")
            .fillna({"seats_senate_cond": 0, "seats_senate_irv": 0, "seats_house": 0})
            .reset_index())

# Round seat counts to int
for col in ["seats_senate_cond", "seats_senate_irv", "seats_house"]:
    types_df[col] = types_df[col].astype(int)

# Total seats (IRV senate + house as baseline cross-chamber view)
types_df["seats_total_irv_house"] = types_df["seats_senate_irv"] + types_df["seats_house"]


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  OUTPUT 1 — coalition_type_profiles.csv                                  ║
# ╚══════════════════════════════════════════════════════════════════════════╝

profiles_out = types_df[[
    "type", "chamber",
    *FACTOR_COLS,
    "seats_senate_cond", "seats_senate_irv", "seats_house", "seats_total_irv_house",
]]
profiles_out = profiles_out.sort_values(["chamber", "seats_senate_irv"],
                                         ascending=[True, False])

profiles_path = OUT_DIR / "coalition_type_profiles.csv"
profiles_out.to_csv(profiles_path, index=False, float_format="%.4f")
print(f"\n  Saved → {profiles_path}  ({len(profiles_out)} rows)")

# ── Console summary ─────────────────────────────────────────────────────────
print("\n  Type profiles:")
print(f"  {'Type':<14} {'Chamber':<8} {'SenC':>5} {'SenI':>5} {'House':>6} "
      f"  {'F1':>7} {'F2':>7} {'F3':>7} {'F4':>7} {'F5':>7}")
print("  " + "─" * 80)
for _, row in profiles_out.iterrows():
    print(f"  {row['type']:<14} {row['chamber']:<8} "
          f"{int(row['seats_senate_cond']):>5} {int(row['seats_senate_irv']):>5} "
          f"{int(row['seats_house']):>6}  "
          f"  {row['F1_security_order']:>+7.3f} {row['F2_electoral_skepticism']:>+7.3f} "
          f"{row['F3_government_distrust']:>+7.3f} {row['F4_religious_traditionalism']:>+7.3f} "
          f"{row['F5_populist_conservatism']:>+7.3f}")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  OUTPUT 2 — coalition_factor_alignment.csv                               ║
# ╚══════════════════════════════════════════════════════════════════════════╝

alignment_rows = []

for factor in FACTOR_COLS:
    scores = types_df[factor].values
    labels_k2 = kmeans_1d(scores, k=2)

    # Rank by score (1 = highest)
    rank = pd.Series(scores).rank(ascending=False).astype(int).values

    for i, row in types_df.iterrows():
        tier_id, tier_label = absolute_tier(float(row[factor]))
        alignment_rows.append({
            "factor":        factor,
            "factor_short":  FACTOR_SHORT[factor],
            "type":          row["type"],
            "chamber":       row["chamber"],
            "score":         round(float(row[factor]), 4),
            "rank":          int(rank[i]),
            "k2_cluster":    int(labels_k2[i]),
            "k2_label":      pole_label(int(labels_k2[i]), factor),
            "tier_id":       tier_id,
            "tier_label":    tier_label,
            "seats_senate_cond": int(row["seats_senate_cond"]),
            "seats_senate_irv":  int(row["seats_senate_irv"]),
            "seats_house":       int(row["seats_house"]),
        })

alignment_df = pd.DataFrame(alignment_rows)
alignment_df = alignment_df.sort_values(["factor", "score"], ascending=[True, False])

alignment_path = OUT_DIR / "coalition_factor_alignment.csv"
alignment_df.to_csv(alignment_path, index=False)
print(f"\n  Saved → {alignment_path}  ({len(alignment_df)} rows)")

# ── Console summary ─────────────────────────────────────────────────────────
print()
for factor in FACTOR_COLS:
    sub = alignment_df[alignment_df["factor"] == factor].copy()
    high_label, low_label = FACTOR_POLES[factor]
    print(f"\n  {'─'*62}")
    print(f"  {FACTOR_SHORT[factor]}  ({factor})")

    # k=2 poles
    for k2_val, grp_label in [(1, high_label), (0, low_label)]:
        members = sub[sub["k2_cluster"] == k2_val]
        sen_seats = int(members["seats_senate_irv"].sum())
        h_seats   = int(members["seats_house"].sum())
        types_str = ", ".join(
            f"{r['type']}({r['score']:+.2f})"
            for _, r in members.sort_values("score", ascending=(k2_val == 0)).iterrows()
        )
        print(f"  [{grp_label}]  Sen={sen_seats} House={h_seats}")
        print(f"    {types_str}")

    # Absolute tiers (k=5)
    print(f"  Absolute tiers:")
    for tier_id in reversed(range(5)):
        tier_name = TIER_LABELS[tier_id]
        members = sub[sub["tier_id"] == tier_id]
        if members.empty:
            print(f"    {tier_name:<12}  (none)")
        else:
            sen_seats = int(members["seats_senate_irv"].sum())
            h_seats   = int(members["seats_house"].sum())
            types_str = ", ".join(
                f"{r['type']}({r['score']:+.2f})"
                for _, r in members.sort_values("score", ascending=False).iterrows()
            )
            print(f"    {tier_name:<12}  Sen={sen_seats:>3} House={h_seats:>4}  {types_str}")


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  OUTPUT 3 — coalition_pairwise.csv                                       ║
# ╚══════════════════════════════════════════════════════════════════════════╝

pairwise_rows = []
n = len(types_df)
idx_list = types_df.reset_index(drop=True)

for i in range(n):
    for j in range(i + 1, n):
        a = idx_list.iloc[i]
        b = idx_list.iloc[j]

        row = {
            "type_a":   a["type"],
            "chamber_a": a["chamber"],
            "type_b":   b["type"],
            "chamber_b": b["chamber"],
        }

        # Per-factor absolute distance
        factor_dists = {}
        sq_sum = 0.0
        for f in FACTOR_COLS:
            d = abs(float(a[f]) - float(b[f]))
            short = FACTOR_SHORT[f]
            factor_dists[f"{short}_dist"] = round(d, 4)
            sq_sum += d ** 2

        row.update(factor_dists)
        row["euclidean_5d"] = round(np.sqrt(sq_sum), 4)

        pairwise_rows.append(row)

pairwise_df = pd.DataFrame(pairwise_rows)

# Add per-factor normalised alignment (0 = max distance, 1 = identical)
dist_cols = [f"{FACTOR_SHORT[f]}_dist" for f in FACTOR_COLS]
for col in dist_cols:
    max_d = pairwise_df[col].max()
    pairwise_df[col.replace("_dist", "_align")] = round(
        1.0 - pairwise_df[col] / max_d if max_d > 0 else 1.0, 4
    )

# Overall alignment from 5D distance
max_euc = pairwise_df["euclidean_5d"].max()
pairwise_df["overall_align"] = round(1.0 - pairwise_df["euclidean_5d"] / max_euc, 4)

pairwise_df = pairwise_df.sort_values("overall_align", ascending=False)

pairwise_path = OUT_DIR / "coalition_pairwise.csv"
pairwise_df.to_csv(pairwise_path, index=False)
print(f"\n  Saved → {pairwise_path}  ({len(pairwise_df)} pairs)")

# ── Top 10 most-aligned pairs ────────────────────────────────────────────────
print("\n  Top 15 most-aligned cross-type pairs (overall 5D):")
print(f"  {'Type A':<14} {'Type B':<14} {'Dist':>6} {'Align':>6}  "
      f"{'F1':>5} {'F2':>5} {'F3':>5} {'F4':>5} {'F5':>5}")
print("  " + "─" * 80)
for _, r in pairwise_df.head(15).iterrows():
    print(f"  {r['type_a']:<14} {r['type_b']:<14} "
          f"{r['euclidean_5d']:>6.3f} {r['overall_align']:>6.3f}  "
          f"{r['F1_SecOrd_dist']:>5.3f} {r['F2_ElecSkep_dist']:>5.3f} "
          f"{r['F3_GovtDis_dist']:>5.3f} {r['F4_ReligTrad_dist']:>5.3f} "
          f"{r['F5_PopCons_dist']:>5.3f}")

print(f"\n  ── All outputs written to {OUT_DIR} ──\n")


if __name__ == "__main__":
    pass

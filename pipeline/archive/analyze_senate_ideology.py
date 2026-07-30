#!/usr/bin/env python3
"""
analyze_senate_ideology.py
---------------------------
1. Builds factor-space centroids for every candidate type that wins senate seats.
2. Computes a full pairwise Euclidean distance matrix (proximity map).
3. Aggregates the actual senate seat results into coalition and chamber-wide
   factor balance for both Condorcet and IRV scenarios.

Outputs
-------
  Claude/outputs/senate/candidate_proximity.csv
  Claude/outputs/senate/senate_ideology_balance.csv
  Claude/outputs/senate/senate_factor_coalitions.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path
from itertools import combinations

BASE    = Path(__file__).parent.parent
OUT_DIR = BASE / "data" / "outputs" / "senate"

# ── Factor names (short labels for display) ───────────────────────────────────
FACTOR_COLS   = ["F1_security_order","F2_electoral_skepticism","F3_government_distrust",
                 "F4_religious_traditionalism","F5_populist_conservatism"]
FACTOR_LABELS = {
    "F1_security_order":           "F1 Security & Order",
    "F2_electoral_skepticism":     "F2 Electoral Skepticism",
    "F3_government_distrust":      "F3 Government Distrust",
    "F4_religious_traditionalism": "F4 Religious Traditionalism",
    "F5_populist_conservatism":    "F5 Populist Conservatism",
}
FACTOR_SHORT = {
    "F1_security_order":           "SecOrd",
    "F2_electoral_skepticism":     "ElecSkep",
    "F3_government_distrust":      "GovtDis",
    "F4_religious_traditionalism": "ReligTrad",
    "F5_populist_conservatism":    "PopCons",
}

# ── Load existing factor centroids ────────────────────────────────────────────
existing = pd.read_csv(BASE / "data" / "outputs" / "candidate_factor_centroids.csv")
# Index by candidate_name for easy lookup
cent_by_name = existing.set_index("candidate_name")[FACTOR_COLS].to_dict("index")
# Pure cluster centroid look-up by name
PURE_CENTROIDS = {
    "CON": cent_by_name["CON"],
    "LBR":  cent_by_name["LBR"],
    "STY": cent_by_name["STY"],
    "NAT": cent_by_name["NAT"],
    "LIB": cent_by_name["LIB"],
    "POP": cent_by_name["POP"],
    "CUP": cent_by_name["CUP"],
    "DSA": cent_by_name["DSA"],
    "PRG": cent_by_name["PRG"],
}

def blend_centroid(primary_name: str, secondary_name: str,
                   w_primary: float, w_secondary: float) -> dict:
    """Weighted blend of two pure-cluster factor centroids."""
    p = PURE_CENTROIDS[primary_name]
    s = PURE_CENTROIDS[secondary_name]
    return {f: w_primary * p[f] + w_secondary * s[f] for f in FACTOR_COLS}

# ── Missing blend definitions (from senate simulation mean weights) ────────────
MISSING_BLENDS = {
    # name         primary  secondary  w_pri   w_sec
    "CON/POP": ("CON", "POP", 0.69, 0.31),
    "LBR/LIB":  ("LBR",  "LIB", 0.51, 0.49),
    "LBR/CUP":  ("LBR",  "CUP", 0.57, 0.43),
    "CON/NAT": ("CON", "NAT", 0.51, 0.49),
    "LIB/CUP": ("LIB", "CUP", 0.60, 0.40),
    "STY/CON": ("STY", "CON", 0.57, 0.43),
}

# ── Build full centroid table ─────────────────────────────────────────────────
rows = []
for name, vals in cent_by_name.items():
    rows.append({"label": name, **vals})
for name, (pri, sec, wp, ws) in MISSING_BLENDS.items():
    c = blend_centroid(pri, sec, wp, ws)
    rows.append({"label": name, **c})

centroids_df = pd.DataFrame(rows).set_index("label")

# ── Pairwise Euclidean distance matrix ───────────────────────────────────────
labels = centroids_df.index.tolist()
X      = centroids_df[FACTOR_COLS].values
n      = len(labels)
dist_rows = []
for i in range(n):
    for j in range(n):
        d = float(np.linalg.norm(X[i] - X[j]))
        dist_rows.append({"candidate_a": labels[i], "candidate_b": labels[j], "euclidean_dist": round(d, 4)})

dist_df = pd.DataFrame(dist_rows)
dist_df.to_csv(OUT_DIR / "candidate_proximity.csv", index=False)

# ── Nearest-neighbour table (top 5 closest for each candidate type) ───────────
print("=" * 70)
print("CANDIDATE PROXIMITY — nearest neighbours in 5-factor ideology space")
print("=" * 70)

# Only show senate-relevant types (pure + blends that win seats)
SENATE_TYPES = [
    "CON","CON/CUP","CON/NAT","CON/POP","CON/LBR","CON/STY",
    "LBR","LBR/CON","LBR/CUP","LBR/LIB","LBR/STY",
    "STY","STY/CON","STY/POP","STY/LBR",
    "POP","POP/STY",
    "LIB","LIB/CUP",
    "CUP",
]
# build square distance matrix for just these
sub_labels = [l for l in SENATE_TYPES if l in centroids_df.index]
sub_X = centroids_df.loc[sub_labels, FACTOR_COLS].values
n_sub = len(sub_labels)
sub_dist = np.zeros((n_sub, n_sub))
for i in range(n_sub):
    for j in range(n_sub):
        sub_dist[i, j] = np.linalg.norm(sub_X[i] - sub_X[j])

print(f"\n{'Candidate':<14}  Nearest → (distance)")
print("-" * 65)
for i, lab in enumerate(sub_labels):
    dists = [(sub_labels[j], sub_dist[i, j]) for j in range(n_sub) if j != i]
    dists.sort(key=lambda x: x[1])
    top4 = ", ".join(f"{d[0]} ({d[1]:.2f})" for d in dists[:4])
    print(f"  {lab:<13}  {top4}")

# ── Load senate outcomes ──────────────────────────────────────────────────────
cond_df = pd.read_csv(OUT_DIR / "senate_condorcet_results.csv")
irv_df  = pd.read_csv(OUT_DIR / "senate_irv_composition.csv")

cond_winners = cond_df.drop_duplicates("state_abbr")[["state_abbr","rp_winner_overall"]]
cond_winners.columns = ["state","label"]
irv_winners  = irv_df[["state_abbr","winner_label"]].copy()
irv_winners.columns = ["state","label"]

def coalition_of(label: str) -> str:
    """Map a candidate label to its top-level coalition."""
    if label.startswith("CON"):   return "CON"
    if label.startswith("LBR"):    return "LBR"
    if label.startswith("STY"):   return "STY"
    if label.startswith("POP"):   return "POP"
    if label.startswith("LIB"):   return "LIB"
    if label.startswith("CUP"):   return "CUP"
    if label in ("NAT","DSA","PRG"): return label
    return "OTHER"

# ── Factor balance function ───────────────────────────────────────────────────
def compute_balance(winners_df: pd.DataFrame) -> pd.DataFrame:
    """
    Given a dataframe with columns [state, label], compute:
    - Per-coalition weighted (seat-count) mean of each factor
    - Overall chamber mean
    Returns a tidy DataFrame.
    """
    winners_df = winners_df.copy()
    winners_df["coalition"] = winners_df["label"].apply(coalition_of)

    # attach factor scores
    winners_df["found_in_centroids"] = winners_df["label"].isin(centroids_df.index)
    missing = winners_df[~winners_df["found_in_centroids"]]["label"].unique()
    if len(missing):
        print(f"  WARNING: no centroid for {missing} — skipping those states")
    winners_df = winners_df[winners_df["found_in_centroids"]]

    for f in FACTOR_COLS:
        winners_df[f] = winners_df["label"].map(centroids_df[f])

    rows = []
    # Coalition rows
    for coal, grp in winners_df.groupby("coalition"):
        seats = len(grp)
        row = {"group": coal, "seats": seats}
        for f in FACTOR_COLS:
            row[FACTOR_SHORT[f]] = round(float(grp[f].mean()), 3)
        rows.append(row)
    # Overall
    row = {"group": "CHAMBER", "seats": len(winners_df)}
    for f in FACTOR_COLS:
        row[FACTOR_SHORT[f]] = round(float(winners_df[f].mean()), 3)
    rows.append(row)

    return pd.DataFrame(rows).sort_values("seats", ascending=False)

cond_balance = compute_balance(cond_winners)
irv_balance  = compute_balance(irv_winners)

# ── Print balance tables ──────────────────────────────────────────────────────
factor_shorts = list(FACTOR_SHORT.values())

def print_balance(df: pd.DataFrame, title: str):
    print(f"\n{'=' * 70}")
    print(title)
    print(f"{'=' * 70}")
    print(f"  {'Coalition':<12} {'Seats':>5}   " + "   ".join(f"{s:>8}" for s in factor_shorts))
    print("  " + "-" * 65)
    for _, row in df.iterrows():
        vals = "   ".join(f"{row[s]:>+8.3f}" for s in factor_shorts)
        star = " ◀" if row["group"] == "CHAMBER" else ""
        print(f"  {row['group']:<12} {int(row['seats']):>5}   {vals}{star}")
    print()
    print("  Factors: F1=Law&Order, F2=ElectionDistrust, F3=GovtDistrust,")
    print("           F4=Religious/SocCon, F5=CulturalTrad")
    print("  (+) = high on dimension   (−) = low on dimension")
    print()
    # Show which coalition is most extreme on each factor
    data_rows = df[df["group"] != "CHAMBER"]
    print(f"  {'Factor':<22}  Most conservative (+)   Most progressive (−)")
    print("  " + "-" * 65)
    for f, short in FACTOR_SHORT.items():
        top = data_rows.loc[data_rows[short].idxmax(), "group"]
        bot = data_rows.loc[data_rows[short].idxmin(), "group"]
        print(f"  {FACTOR_LABELS[f]:<22}  {top:<22}  {bot}")

print_balance(cond_balance, "CONDORCET SENATE — Factor Balance by Coalition")
print_balance(irv_balance,  "IRV SENATE — Factor Balance by Coalition")

# ── Majority direction on each factor (chamber > 0 means + coalition has majority) ──
print("=" * 70)
print("CHAMBER MAJORITY DIRECTION (both scenarios)")
print("=" * 70)
cond_chamber = cond_balance[cond_balance["group"] == "CHAMBER"].iloc[0]
irv_chamber  = irv_balance[irv_balance["group"]  == "CHAMBER"].iloc[0]

print(f"\n  {'Factor':<22}  {'Condorcet':>12}  {'IRV':>12}  Consensus?")
print("  " + "-" * 60)
for f, short in FACTOR_SHORT.items():
    cv = cond_chamber[short]
    iv = irv_chamber[short]
    c_dir = "+" if cv >= 0 else "−"
    i_dir = "+" if iv >= 0 else "−"
    agree = "✓" if c_dir == i_dir else "✗"
    print(f"  {FACTOR_LABELS[f]:<22}  {cv:>+12.3f}  {iv:>+12.3f}  {agree} ({c_dir}/{i_dir})")

# ── Save outputs ──────────────────────────────────────────────────────────────
cond_balance["scenario"] = "Condorcet"
irv_balance["scenario"]  = "IRV"
combined = pd.concat([cond_balance, irv_balance], ignore_index=True)
combined.to_csv(OUT_DIR / "senate_ideology_balance.csv", index=False)
print(f"\nSaved → senate_ideology_balance.csv")
print(f"Saved → candidate_proximity.csv")

# ── Also save full factor centroid table including all senate types ────────────
full_cent = centroids_df.loc[
    [l for l in sub_labels if l in centroids_df.index]
].reset_index().rename(columns={"label":"candidate_label"})
for f, short in FACTOR_SHORT.items():
    full_cent[short] = full_cent[f].round(3)
full_cent.to_csv(OUT_DIR / "senate_candidate_factor_centroids.csv", index=False)
print(f"Saved → senate_candidate_factor_centroids.csv")

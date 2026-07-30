#!/usr/bin/env python3
"""
chamber_vote_model.py
----------------------
For each binary policy item, models the probability of a bill passing a
floor vote in the Senate and House under each electoral scenario.

Method: Sum-of-Independent-Binomials, approximated by Normal distribution.
  - Each seat in a type bloc is a Bernoulli trial with p = group % support / 100
  - E[Y] = Σ nᵢ · pᵢ                           (expected yes votes)
  - σ[Y] = √(Σ nᵢ · pᵢ · (1−pᵢ))              (uncertainty from near-50% blocs)
  - P(pass) = P(Y ≥ majority) ≈ 1 − Φ((majority − 0.5 − μ) / σ)

Outputs
-------
  Claude/outputs/senate/senate_vote_model.csv
  Claude/outputs/house_vote_model.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import norm

BASE        = Path(__file__).parent.parent
PROFILE_DIR = BASE / "data" / "outputs" / "profiles"
SENATE_DIR  = BASE / "data" / "outputs" / "senate"
OUT_DIR     = BASE / "data" / "outputs"

# ── Senate type columns (from senate_chamber_profile.csv) ──────────────────
SENATE_TYPES = [
    "CON", "LBR", "STY", "POP",
    "CON/CUP", "CON/LBR", "CON/STY",
    "LBR/STY", "LBR/CON", "LBR/CUP", "LBR/LIB",
    "STY/POP", "STY/LBR", "STY/CON",
    "POP/STY",
    "CON/POP", "CON/NAT", "LIB/CUP",
]

# ── House type columns (from house_chamber_profile.csv) ────────────────────
HOUSE_CLUSTER_NAMES = {
    0: "CON", 1: "LBR", 2: "STY", 3: "NAT", 4: "LIB",
    5: "POP", 6: "CUP", 7: "OAO", 8: "DSA", 9: "PRG",
}
HOUSE_TYPES = [HOUSE_CLUSTER_NAMES[i] for i in range(10)]

VERDICT_PASS   = "PASS"
VERDICT_FAIL   = "FAIL"
VERDICT_TOSSUP = "TOSS-UP"


def verdict(prob: float) -> str:
    if prob >= 0.67:
        return VERDICT_PASS
    if prob <= 0.33:
        return VERDICT_FAIL
    return VERDICT_TOSSUP


def vote_model(
    policy_rows: pd.DataFrame,
    type_cols: list,
    seats: dict,
    majority: int,
    label: str,
) -> dict:
    """
    Compute expected yes, sigma, and probability of passage for each policy row.

    Parameters
    ----------
    policy_rows : DataFrame with one row per binary policy item;
                  columns include all type_cols with values in 0–100 scale
    type_cols   : list of type labels matching column names in policy_rows
    seats       : dict {type_label: int} — seat counts per type
    majority    : int — minimum yes votes to pass (e.g. 26 for Senate)
    label       : prefix string for diagnostic output

    Returns
    -------
    dict of column_name -> list of values (parallel to policy_rows index)
    """
    total_seats = sum(seats.get(t, 0) for t in type_cols)
    missing = [t for t in type_cols if seats.get(t, 0) > 0
               and t not in policy_rows.columns]
    if missing:
        print(f"  ⚠ {label}: type(s) with seats but missing from profile: {missing}")

    exp_yes = []
    sigmas  = []
    probs   = []
    verdicts = []

    for _, row in policy_rows.iterrows():
        mu     = 0.0
        sigma2 = 0.0
        for t in type_cols:
            n_t = seats.get(t, 0)
            if n_t == 0:
                continue
            p_t = row[t] / 100.0
            p_t = np.clip(p_t, 0.0, 1.0)
            mu     += n_t * p_t
            sigma2 += n_t * p_t * (1.0 - p_t)

        sigma = np.sqrt(sigma2) if sigma2 > 0 else 1e-9
        # Continuity correction: P(Y >= majority) ≈ P(Z >= majority - 0.5)
        z    = (majority - 0.5 - mu) / sigma
        prob = float(1.0 - norm.cdf(z))

        exp_yes.append(round(mu, 2))
        sigmas.append(round(sigma, 2))
        probs.append(round(prob, 4))
        verdicts.append(verdict(prob))

    print(f"  {label}: {total_seats} seats, {len(policy_rows)} items  "
          f"({sum(1 for v in verdicts if v == VERDICT_PASS)} PASS / "
          f"{sum(1 for v in verdicts if v == VERDICT_TOSSUP)} TOSS-UP / "
          f"{sum(1 for v in verdicts if v == VERDICT_FAIL)} FAIL)")

    return {
        "expected_yes": exp_yes,
        "sigma":        sigmas,
        "prob_pass":    probs,
        "verdict":      verdicts,
    }


def load_senate_seats(csv_path: Path, label_col: str) -> dict:
    return (
        pd.read_csv(csv_path)[label_col]
        .value_counts()
        .to_dict()
    )


def load_house_seats(csv_path: Path) -> dict:
    df = pd.read_csv(csv_path)
    return {
        HOUSE_CLUSTER_NAMES[int(row["party"])]: int(row["NATIONAL"])
        for _, row in df.iterrows()
    }


def main():
    # ── Load chamber profiles ───────────────────────────────────────────────
    senate_profile = pd.read_csv(SENATE_DIR / "senate_chamber_profile.csv")
    house_profile  = pd.read_csv(OUT_DIR    / "house_chamber_profile.csv")

    # Filter to binary "% Supporting" rows that are CES policy questions (CC24_)
    # Excludes demographic/employment binary items (pew_bornagain, milstat, etc.)
    senate_binary = senate_profile[
        (senate_profile["stat_label"] == "% Supporting") &
        (senate_profile["variable"].str.startswith("CC24_"))
    ].copy()
    house_binary = house_profile[
        (house_profile["stat_label"] == "% Supporting") &
        (house_profile["variable"].str.startswith("CC24_"))
    ].copy()

    print(f"Senate binary policy rows: {len(senate_binary)}")
    print(f"House  binary policy rows: {len(house_binary)}")

    # ── Senate: Condorcet and IRV ───────────────────────────────────────────
    print("\n── SENATE ────────────────────────────────────────────────────")
    SENATE_MAJORITY = 26

    cond_seats = load_senate_seats(
        SENATE_DIR / "senate_composition.csv", "senator_label")
    irv_seats  = load_senate_seats(
        SENATE_DIR / "senate_irv_composition.csv", "winner_label")

    cond_results = vote_model(senate_binary, SENATE_TYPES, cond_seats,
                              SENATE_MAJORITY, "Condorcet")
    irv_results  = vote_model(senate_binary, SENATE_TYPES, irv_seats,
                              SENATE_MAJORITY, "IRV")

    senate_out = senate_binary[["variable", "domain", "question", "overall"]].copy()
    senate_out = senate_out.rename(columns={"overall": "overall_pct"})

    for prefix, results in [("cond", cond_results), ("irv", irv_results)]:
        for suffix, vals in results.items():
            senate_out[f"{prefix}_{suffix}"] = vals

    senate_path = SENATE_DIR / "senate_vote_model.csv"
    senate_out.to_csv(senate_path, index=False)
    print(f"\nSaved {len(senate_out)} rows → {senate_path}")

    # ── House: baseline, no_C2, no_C7 ──────────────────────────────────────
    print("\n── HOUSE ─────────────────────────────────────────────────────")
    HOUSE_MAJORITY = 437

    # The canonical 873-seat chamber, not No_C7_canonical's 850-seat older run.
    scenarios = [
        ("house", OUT_DIR / "pure_multi" / "house" / "stv_seat_summary.csv"),
    ]

    house_out = house_binary[["variable", "domain", "question", "overall"]].copy()
    house_out = house_out.rename(columns={"overall": "overall_pct"})

    for prefix, path in scenarios:
        seats   = load_house_seats(path)
        results = vote_model(house_binary, HOUSE_TYPES, seats,
                             HOUSE_MAJORITY, prefix)
        for suffix, vals in results.items():
            house_out[f"{prefix}_{suffix}"] = vals

    house_path = OUT_DIR / "house_vote_model.csv"
    house_out.to_csv(house_path, index=False)
    print(f"\nSaved {len(house_out)} rows → {house_path}")

    # ── Spot-checks ─────────────────────────────────────────────────────────
    print("\n── SPOT CHECKS ───────────────────────────────────────────────")

    for label, df in [("Senate", senate_out), ("House", house_out)]:
        # Background checks — should be near-certain pass everywhere
        bc = df[df["variable"] == "CC24_321c"]
        if not bc.empty:
            row = bc.iloc[0]
            cols = [c for c in df.columns if "prob_pass" in c]
            probs = {c: row[c] for c in cols}
            print(f"\n{label} | CC24_321c 'Background checks on all gun sales':")
            print(f"  Overall support: {row['overall_pct']:.1f}%")
            for c, p in probs.items():
                print(f"  {c}: {p:.4f}")

        # Tax cuts — should vary by chamber composition
        tax = df[df["variable"] == "CC24_341a"]
        if not tax.empty:
            row = tax.iloc[0]
            cols = [c for c in df.columns if "prob_pass" in c]
            print(f"\n{label} | CC24_341a 'Extend 2017 tax cuts':")
            print(f"  Overall support: {row['overall_pct']:.1f}%")
            for c, p in probs.items():
                print(f"  {c}: {p:.4f}")

    # Sigma sanity: all sigmas should be > 0
    all_sigma_cols = [c for c in senate_out.columns if "sigma" in c]
    all_positive = all((senate_out[c] > 0).all() for c in all_sigma_cols)
    print(f"\nAll Senate sigmas > 0: {'✓' if all_positive else '✗'}")

    print("\n✓ Done.")


if __name__ == "__main__":
    main()

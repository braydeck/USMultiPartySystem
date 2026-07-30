#!/usr/bin/env python3
"""
chamber_vote_model.py
----------------------
For each bill in stv_config.BILL_VARS, models the probability of it passing a floor vote in the
House. The senate half was dropped: it scored the retired mixed-senate model's blended senator
types (CON/CUP, STY/LBR and the like) against a profile that can no longer be regenerated, and its
output had no consumer — the live senate probabilities are computed by viz/scripts/prepare_data.py
from pure party types.

Method: Sum-of-Independent-Binomials, approximated by Normal distribution.
  - Each seat in a type bloc is a Bernoulli trial with p = group % support / 100
  - E[Y] = Σ nᵢ · pᵢ                           (expected yes votes)
  - σ[Y] = √(Σ nᵢ · pᵢ · (1−pᵢ))              (uncertainty from near-50% blocs)
  - P(pass) = P(Y ≥ majority) ≈ 1 − Φ((majority − 0.5 − μ) / σ)

Outputs
-------
  Claude/outputs/house_vote_model.csv
"""

import numpy as np
import pandas as pd
from pathlib import Path
from scipy.stats import norm

from stv_config import BILL_VARS

BASE    = Path(__file__).parent.parent
OUT_DIR = BASE / "data" / "outputs"

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
    # A seated type contributes only if the profile has a column of support values for it. Both
    # ways of failing that used to be quiet — a type in type_cols but absent from the profile raised
    # a KeyError below, and a seated type absent from type_cols entirely was dropped without a word.
    # Report the seats each case costs, since the model is a seat-weighted sum and an unnoticed
    # exclusion just lowers every probability.
    usable = [t for t in type_cols if t in policy_rows.columns]
    dropped = {t: n for t, n in seats.items() if n > 0 and t not in usable}
    if dropped:
        print(f"  ⚠ {label}: {sum(dropped.values())} seat(s) excluded — no profile column for "
              f"{', '.join(f'{t} ({n})' for t, n in sorted(dropped.items()))}")
    total_seats = sum(seats.get(t, 0) for t in usable)

    exp_yes = []
    sigmas  = []
    probs   = []
    verdicts = []

    for _, row in policy_rows.iterrows():
        mu     = 0.0
        sigma2 = 0.0
        for t in usable:
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


def load_house_seats(csv_path: Path) -> dict:
    df = pd.read_csv(csv_path)
    return {
        HOUSE_CLUSTER_NAMES[int(row["party"])]: int(row["NATIONAL"])
        for _, row in df.iterrows()
    }


def main():
    # ── Load chamber profiles ───────────────────────────────────────────────
    house_profile = pd.read_csv(OUT_DIR / "house_chamber_profile.csv")

    # BILL_VARS, not every "% Supporting" CC24_ row: the profile also carries attitude and
    # behaviour items that belong in the policy comparison, not in a chamber vote.
    house_binary = house_profile[
        (house_profile["stat_label"] == "% Supporting") &
        (house_profile["variable"].isin(BILL_VARS))
    ].copy()
    absent = [v for v in BILL_VARS if v not in set(house_binary["variable"])]
    if absent:
        print(f"  ⚠ bill(s) with no house profile row: {absent}")

    print(f"House  binary policy rows: {len(house_binary)}")

    # ── House ──────────────────────────────────────────────────────────────
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

    for label, df in [("House", house_out)]:
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
    all_sigma_cols = [c for c in house_out.columns if "sigma" in c]
    all_positive = all((house_out[c] > 0).all() for c in all_sigma_cols)
    print(f"\nAll House sigmas > 0: {'✓' if all_positive else '✗'}")

    print("\n✓ Done.")


if __name__ == "__main__":
    main()

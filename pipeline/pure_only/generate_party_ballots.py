#!/usr/bin/env python3
"""
generate_party_ballots.py
-------------------------
Generate ranked-choice ballots for 9 parties using GMM posteriors.

Each voter ranks 9 parties via Plackett-Luce sampling weighted by their
personal GMM cluster probabilities. No intra-party candidate distinction —
the party IS the candidate. Multiple "slots" for strong parties are
determined downstream by Droop quota allocation.

Outputs to data/outputs/pure_multi/:
  party_ballots.csv           — (N, 9) rankings of party codes
  party_state_profiles.csv    — per-state vote shares
"""

import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR    = Path(__file__).parent.parent.parent
EFA_PATH    = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
TYPOLOGY    = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
OUTPUT_DIR  = BASE_DIR / "data" / "outputs" / "pure_multi"

PARTIES = [
    {"code": "CON", "cluster": 0},
    {"code": "SD",  "cluster": 1},
    {"code": "STY", "cluster": 2},
    {"code": "NAT", "cluster": 3},
    {"code": "LIB", "cluster": 4},
    {"code": "REF", "cluster": 5},
    {"code": "CTR", "cluster": 6},
    {"code": "DSA", "cluster": 8},
    {"code": "PRG", "cluster": 9},
]
N_PARTIES   = len(PARTIES)
PARTY_CODES = [p["code"] for p in PARTIES]
CLUSTER_IDS = [p["cluster"] for p in PARTIES]

PROB_COLS = [f"prob_cluster_{k}" for k in range(10)]

FIPS_TO_ABBR = {
     1:"AL",  2:"AK",  4:"AZ",  5:"AR",  6:"CA",  8:"CO",  9:"CT",
    10:"DE", 11:"DC", 12:"FL", 13:"GA", 15:"HI", 16:"ID", 17:"IL",
    18:"IN", 19:"IA", 20:"KS", 21:"KY", 22:"LA", 23:"ME", 24:"MD",
    25:"MA", 26:"MI", 27:"MN", 28:"MS", 29:"MO", 30:"MT", 31:"NE",
    32:"NV", 33:"NH", 34:"NJ", 35:"NM", 36:"NY", 37:"NC", 38:"ND",
    39:"OH", 40:"OK", 41:"OR", 42:"PA", 44:"RI", 45:"SC", 46:"SD",
    47:"TN", 48:"TX", 49:"UT", 50:"VT", 51:"VA", 53:"WA", 54:"WV",
    55:"WI", 56:"WY", 72:"PR",
}


def generate_ballots(scores: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Deterministic ranking: sort parties by score descending. Returns (N, 9) int array."""
    N = len(scores)
    ballots = np.zeros((N, N_PARTIES), dtype=np.int8)
    for i in range(N):
        ballots[i] = np.argsort(-scores[i])
    return ballots


def main():
    rng = np.random.default_rng(42)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("PARTY BALLOT GENERATION — 9 parties, GMM posteriors")
    print("=" * 60)

    print("\nLoading data…")
    efa      = pd.read_csv(EFA_PATH)
    typology = pd.read_csv(TYPOLOGY)
    N = len(efa)
    assert len(typology) == N

    weights    = efa["commonpostweight"].values
    inputstate = efa["inputstate"].values

    # GMM posteriors for the 9 active parties
    scores = np.zeros((N, N_PARTIES), dtype=np.float64)
    for j, p in enumerate(PARTIES):
        col = f"prob_cluster_{p['cluster']}"
        scores[:, j] = typology[col].values

    print(f"  {N:,} respondents, {N_PARTIES} parties")

    # Generate ballots
    print("\nGenerating Plackett-Luce ballots…")
    ballots = generate_ballots(scores, rng)

    # Convert to party codes
    rank_cols = [f"rank_{k+1}" for k in range(N_PARTIES)]
    ballot_df = pd.DataFrame(ballots, columns=rank_cols)
    for col in rank_cols:
        ballot_df[col] = ballot_df[col].map(lambda x: PARTY_CODES[x])
    ballot_df.index.name = "respondent_id"

    # Sanity checks
    for i in range(min(1000, N)):
        assert len(set(ballot_df.iloc[i])) == N_PARTIES, f"Duplicate in ballot {i}"
    print("  ✓ No duplicates in sampled ballots")

    # Save ballots
    ballot_out = OUTPUT_DIR / "party_ballots.csv"
    ballot_df.to_csv(ballot_out, index=True)
    print(f"\nSaved → {ballot_out}  ({N:,} rows × {N_PARTIES} ranks)")

    # First-preference distribution
    first_prefs = ballot_df["rank_1"].value_counts()
    print("\n  First-preference shares:")
    for code in PARTY_CODES:
        n = first_prefs.get(code, 0)
        print(f"    {code:<6} {n:>6}  ({n/N*100:.1f}%)")

    # State profiles
    print("\nBuilding state profiles…")
    rows = []
    for fips in sorted(np.unique(inputstate)):
        mask = inputstate == fips
        w = weights[mask]
        if w.sum() == 0:
            continue
        row = {
            "state_fips": int(fips),
            "state_abbr": FIPS_TO_ABBR.get(int(fips), f"FIPS{int(fips)}"),
            "total_weight": float(w.sum()),
        }
        state_scores = scores[mask]
        for j, code in enumerate(PARTY_CODES):
            row[f"share_{code}"] = float(np.average(state_scores[:, j], weights=w))
        rows.append(row)

    profiles_df = pd.DataFrame(rows)
    profiles_out = OUTPUT_DIR / "party_state_profiles.csv"
    profiles_df.to_csv(profiles_out, index=False)
    print(f"  Saved → {profiles_out}  ({len(profiles_df)} states)")

    print("\n✓ Done.")


if __name__ == "__main__":
    main()

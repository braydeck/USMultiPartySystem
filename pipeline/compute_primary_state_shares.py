#!/usr/bin/env python3
"""
compute_primary_state_shares.py
-------------------------------
Compute per-stage, per-state first-choice vote shares for the primary.

For each primary stage's survivor set, projects every voter's ballot to
those survivors, takes their first surviving choice, and tallies by state.
Tracks exhausted ballots (voters with no surviving choice).

Outputs a JSON per pipeline:
  data/outputs/pure_multi/primary_state_stage_shares.json
  data/outputs/factor_deviation/primary_state_stage_shares.json
"""

import json
import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
EFA_PATH = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
sys.path.insert(0, str(BASE_DIR / "pipeline" / "pure_only"))
from turnout_weights import turnout_multiplier, TURNOUT_WEIGHT, TURNOUT_LAMBDA, output_tree  # noqa: E402

FIPS_TO_ABBR = {
     1:"AL",  2:"AK",  4:"AZ",  5:"AR",  6:"CA",  8:"CO",  9:"CT",
    10:"DE", 11:"DC", 12:"FL", 13:"GA", 15:"HI", 16:"ID", 17:"IL",
    18:"IN", 19:"IA", 20:"KS", 21:"KY", 22:"LA", 23:"ME", 24:"MD",
    25:"MA", 26:"MI", 27:"MN", 28:"MS", 29:"MO", 30:"MT", 31:"NE",
    32:"NV", 33:"NH", 34:"NJ", 35:"NM", 36:"NY", 37:"NC", 38:"ND",
    39:"OH", 40:"OK", 41:"OR", 42:"PA", 44:"RI", 45:"SC", 46:"SD",
    47:"TN", 48:"TX", 49:"UT", 50:"VT", 51:"VA", 53:"WA", 54:"WV",
    55:"WI", 56:"WY",
}

STAGES = ["After_Retail", "After_Pod_A", "After_Pod_C", "After_Pod_BD"]


def compute_shares(ballots_path, primary_path, pod_path, output_path):
    print(f"\n{'='*60}")
    print(f"Computing state shares: {output_path.name}")
    print(f"{'='*60}")

    # Load primary results to get survivors per stage
    primary_df = pd.read_csv(primary_path)
    survivors_by_stage = {}
    for stage in STAGES:
        rows = primary_df[
            (primary_df["winnowing_point"] == stage) &
            (primary_df["status"].isin(["surviving", "elected"]))
        ]
        survivors_by_stage[stage] = set(rows["candidate_code"].unique())
        print(f"  {stage}: {len(survivors_by_stage[stage])} survivors")

    # Load ballots
    print("Loading ballots…")
    ballots_df = pd.read_csv(ballots_path, index_col="respondent_id")
    rank_cols = [c for c in ballots_df.columns if c.startswith("rank_")]
    ballots_arr = ballots_df[rank_cols].values
    N = len(ballots_arr)

    # Load respondent metadata
    efa = pd.read_csv(EFA_PATH)
    weights = efa["commonpostweight"].values.astype(float) * turnout_multiplier(len(efa))
    state_fips = efa["inputstate"].values.astype(int)
    assert len(efa) == N, f"Row mismatch: {N} vs {len(efa)}"

    # Load pod assignments
    pod_df = pd.read_csv(pod_path)
    pod_by_fips = {}
    abbr_by_fips = {}
    for _, row in pod_df.iterrows():
        fips = int(row["state_fips"])
        pod_by_fips[fips] = row["pod"]
        abbr_by_fips[fips] = row["state_abbr"]

    # For each stage, compute per-state first-choice shares
    unique_fips = sorted(f for f in np.unique(state_fips) if f in FIPS_TO_ABBR)
    result = {}  # fips_str -> { stateAbbr, pod, nRespondents, stages: { stage -> { shares, exhausted } } }

    for fips in unique_fips:
        fips_str = str(fips).zfill(2)
        mask = state_fips == fips
        if mask.sum() < 5:
            continue
        s_ballots = ballots_arr[mask]
        s_weights = weights[mask]
        total_weight = float(s_weights.sum())
        abbr = FIPS_TO_ABBR.get(fips, f"FIPS{fips}")
        pod = pod_by_fips.get(fips, "D")

        stage_data = {}
        for stage in STAGES:
            survivors = survivors_by_stage[stage]
            # First surviving choice per voter
            shares = {}
            exhausted_w = 0.0
            for i in range(len(s_ballots)):
                w = s_weights[i]
                found = False
                for code in s_ballots[i]:
                    if code in survivors:
                        shares[code] = shares.get(code, 0.0) + w
                        found = True
                        break
                if not found:
                    exhausted_w += w

            # Normalize to fractions
            share_frac = {}
            for code in sorted(shares.keys()):
                share_frac[code] = round(shares[code] / total_weight, 4)
            exhausted_frac = round(exhausted_w / total_weight, 4)

            stage_data[stage] = {
                "shares": share_frac,
                "exhausted": exhausted_frac,
            }

        result[fips_str] = {
            "stateAbbr": abbr,
            "pod": pod,
            "nRespondents": int(mask.sum()),
            "stages": stage_data,
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, separators=(",", ":"))
    print(f"Wrote {output_path.name} ({len(result)} states)")


def main():
    pm = BASE_DIR / "data" / "outputs" / "pure_multi"
    if TURNOUT_WEIGHT:
        # Turnout-weighted per-stage shares: ballots + pod structure are turnout-independent
        # (reuse the base tree); only the primary_results and the vote weights change.
        out_tree = BASE_DIR / "data" / "outputs" / output_tree("pure_multi")
        print(f"TURNOUT_WEIGHT=1 λ={TURNOUT_LAMBDA} → {out_tree.name}")
        compute_shares(
            ballots_path=pm / "presidential_ballots.csv",
            primary_path=out_tree / "primary_results_2028.csv",
            pod_path=pm / "state_pod_assignments.csv",
            output_path=out_tree / "primary_state_stage_shares.json",
        )
        return

    # Raw Multi
    compute_shares(
        ballots_path=pm / "presidential_ballots.csv",
        primary_path=pm / "primary_results_2028.csv",
        pod_path=pm / "state_pod_assignments.csv",
        output_path=pm / "primary_state_stage_shares.json",
    )

    # Factor Deviation
    compute_shares(
        ballots_path=BASE_DIR / "data" / "outputs" / "factor_deviation" / "ballots.csv",
        primary_path=BASE_DIR / "data" / "outputs" / "factor_deviation" / "primary_results_2028.csv",
        pod_path=BASE_DIR / "data" / "outputs" / "factor_deviation" / "state_pod_assignments.csv",
        output_path=BASE_DIR / "data" / "outputs" / "factor_deviation" / "primary_state_stage_shares.json",
    )


if __name__ == "__main__":
    main()

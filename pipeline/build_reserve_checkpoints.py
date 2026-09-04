#!/usr/bin/env python3
"""
build_reserve_checkpoints.py
-----------------------------
Assign voters to reserve-scenario districts and save ballots_checkpoint.parquet.

Reads the reserve apportionment and county-to-district maps, runs the same geo-based
voter assignment as run_house_canonical.py, and saves the checkpoint that
run_pure_multi_house_stv.py reads.

Output:
  data/outputs/No_C7_canonical_reserve/ballots_checkpoint.parquet
  data/outputs/No_C7_triple_reserve/ballots_checkpoint.parquet
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from run_house_canonical import assign_voters_to_districts_geo, SPLIT_OVERRIDE_PATH  # noqa: E402
from stv_config import EFA_SCORES_PATH, TYPOLOGY_PATH  # noqa: E402

VOTER_FIPS_PATH = BASE_DIR / "data" / "processed" / "voter_county_fips.csv"

CONFIGS = [
    {
        "label": "DOUBLE RESERVE",
        "apport": BASE_DIR / "data" / "outputs" / "No_C7_canonical_reserve" / "district_apportionment.csv",
        "county_dist": BASE_DIR / "data" / "processed" / "county_to_district_reserve.csv",
        "out": BASE_DIR / "data" / "outputs" / "No_C7_canonical_reserve" / "ballots_checkpoint.parquet",
    },
    {
        "label": "TRIPLE RESERVE",
        "apport": BASE_DIR / "data" / "outputs" / "No_C7_triple_reserve" / "district_apportionment.csv",
        "county_dist": BASE_DIR / "data" / "processed" / "county_to_district_triple_reserve.csv",
        "out": BASE_DIR / "data" / "outputs" / "No_C7_triple_reserve" / "ballots_checkpoint.parquet",
    },
]


def main():
    efa = pd.read_csv(EFA_SCORES_PATH)
    inputstates = efa["inputstate"].values.astype(int)
    N = len(efa)
    print(f"{N:,} voters loaded")

    voter_fips_df = pd.read_csv(VOTER_FIPS_PATH, index_col=0)
    voter_counties = voter_fips_df["countyfips"].astype(str).str.zfill(5).values
    voter_cds = (pd.to_numeric(voter_fips_df["cd119"], errors="coerce").values
                 if "cd119" in voter_fips_df.columns else None)

    # Need density_tier from the base checkpoint for fallback assignment
    base_ckpt = pd.read_parquet(
        BASE_DIR / "data" / "outputs" / "No_C7_canonical" / "ballots_checkpoint.parquet",
        columns=["density_tier"])
    density_tiers = base_ckpt["density_tier"].values

    for cfg in CONFIGS:
        print(f"\n{'='*60}\n{cfg['label']}")
        apportion = pd.read_csv(cfg["apport"])
        county_dist_df = pd.read_csv(cfg["county_dist"])
        county_to_dist = dict(zip(
            county_dist_df["county_fips5"].astype(str).str.zfill(5),
            county_dist_df["district_id"]
        ))

        voter_district = assign_voters_to_districts_geo(
            voter_counties, county_to_dist, inputstates, apportion, voter_cds)

        unassigned = (voter_district == "").sum()
        if unassigned:
            print(f"  WARNING: {unassigned} voters unassigned")

        ckpt = pd.DataFrame({"district_id": voter_district, "density_tier": density_tiers})
        cfg["out"].parent.mkdir(parents=True, exist_ok=True)
        ckpt.to_parquet(cfg["out"], index=False)
        n_dists = len(set(voter_district) - {""})
        print(f"  Saved {cfg['out'].name} ({N:,} voters, {n_dists} districts covered)")


if __name__ == "__main__":
    main()

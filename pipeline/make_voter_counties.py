#!/usr/bin/env python3
"""
make_voter_counties.py
----------------------
Extract county FIPS for the 45,707 CES rows that survive listwise deletion,
aligned positionally with efa_factor_scores.csv.

Output: data/processed/voter_county_fips.csv
  index   = row position (0-based, matches efa row order)
  caseid  = CES respondent ID
  countyfips = 5-digit zero-padded county FIPS string
"""

import sys
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from stv_config import DTA_PATH, ITEMS_24

EXPECTED_N    = 45_707
OUTPUT_PATH   = BASE_DIR / "data" / "processed" / "voter_county_fips.csv"
DELETION_COLS = ITEMS_24 + ["commonpostweight"]
READ_COLS     = ["caseid", "countyfips", "cdid119"] + DELETION_COLS


def main():
    try:
        import pyreadstat
    except ImportError:
        print("ERROR: pyreadstat not installed.  Run: pip install pyreadstat")
        sys.exit(1)

    print(f"Reading DTA: {DTA_PATH.name} …")
    df, _ = pyreadstat.read_dta(str(DTA_PATH), usecols=READ_COLS)
    print(f"  Raw rows: {len(df):,}")

    mask = df[DELETION_COLS].notna().all(axis=1)
    out  = df.loc[mask, ["caseid", "countyfips", "cdid119"]].reset_index(drop=True)
    print(f"  After listwise deletion: {len(out):,} rows")
    assert len(out) == EXPECTED_N, \
        f"Expected {EXPECTED_N} rows after deletion, got {len(out)}"

    # Zero-pad to 5-digit string; coerce NaN/empty to 0 then "00000"
    out["countyfips"] = (
        pd.to_numeric(out["countyfips"], errors="coerce")
        .fillna(0)
        .astype(int)
        .astype(str)
        .str.zfill(5)
    )

    # cd119: the respondent's real 119th-Congress district. Carried so a county that spans more
    # districts than the whole-county draw can express — Maricopa is the only one — can be split on
    # actual congressional geography instead of arbitrarily. See county_split_overrides.csv.
    out["cd119"] = pd.to_numeric(out.pop("cdid119"), errors="coerce").astype("Int64")

    null_count = (out["countyfips"] == "00000").sum()
    if null_count:
        print(f"  Warning: {null_count} rows with null/zero countyfips")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_PATH, index=True)
    print(f"Saved {OUTPUT_PATH}  ({len(out):,} rows)")


if __name__ == "__main__":
    main()

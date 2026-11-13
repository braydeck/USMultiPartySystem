#!/usr/bin/env python3
"""
make_voter_counties.py
----------------------
Extract county FIPS, real 119th-Congress district, and ZIP for every typology respondent,
aligned by caseid with efa_factor_scores.csv and typology_cluster_assignments.csv.

Output: data/processed/voter_county_fips.csv
  index   = row position (0-based, matches efa row order)
  caseid  = CES respondent ID
  countyfips = 5-digit zero-padded county FIPS string
  cd119   = real 119th-Congress district number within the state
  zip     = 5-digit ZIP (CES lookupzip)
"""

import sys
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))
from stv_config import DTA_PATH, TYPOLOGY_PATH as BASE_TYPO

EXPECTED_N    = len(pd.read_csv(BASE_TYPO, usecols=["caseid"]))
OUTPUT_PATH   = BASE_DIR / "data" / "processed" / "voter_county_fips.csv"

READ_COLS     = ["caseid", "countyfips", "cdid119", "lookupzip"]


def main():
    try:
        import pyreadstat
    except ImportError:
        print("ERROR: pyreadstat not installed.  Run: pip install pyreadstat")
        sys.exit(1)

    print(f"Reading DTA: {DTA_PATH.name} …")
    df, _ = pyreadstat.read_dta(str(DTA_PATH), usecols=READ_COLS)
    print(f"  Raw rows: {len(df):,}")

    ids = pd.read_csv(BASE_TYPO, usecols=["caseid"]).caseid.values
    out = df.set_index("caseid").loc[ids, ["countyfips", "cdid119", "lookupzip"]].reset_index()  # CLAUDE.md trap 4: rows join the typology by caseid, in typology order
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

    # cd119: the respondent's real 119th-Congress district, for MMP and Single Race, which use the
    # real districts.
    out["cd119"] = pd.to_numeric(out.pop("cdid119"), errors="coerce").astype("Int64")
    # zip: the respondent's 5-digit ZIP. A county too big for one drawn district is split on Census
    # ZIP areas (draw_geographic_districts.py), and the ZIP places the respondent in a piece.
    out["zip"] = out.pop("lookupzip").astype(str).str.extract(r"(\d+)")[0].str.zfill(5)

    null_count = (out["countyfips"] == "00000").sum()
    if null_count:
        print(f"  Warning: {null_count} rows with null/zero countyfips")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_PATH, index=True)
    print(f"Saved {OUTPUT_PATH}  ({len(out):,} rows)")


if __name__ == "__main__":
    main()

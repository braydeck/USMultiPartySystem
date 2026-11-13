"""Which drawn House district each respondent votes in. One copy, used by every House runner.

A respondent votes in the district that holds their county (data/processed/county_to_district*.csv).
A county too big for one district is cut into ZIP-area pieces by draw_geographic_districts.py
(county_split_zcta*.csv); a respondent there is placed by their ZIP (voter_county_fips.csv `zip`,
CES lookupzip). A ZIP that is not a 2010 ZIP area of that county (0.6% of respondents in split
counties, mostly PO-box ZIPs) takes the piece holding the numerically nearest ZIP area, since ZIP
numbers run in geographic blocks. A respondent with no county on file votes in their state's
first district.
"""
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
VOTER_FIPS_PATH = BASE_DIR / "data" / "processed" / "voter_county_fips.csv"


def split_table_path(county_dist_path) -> Path:
    p = Path(county_dist_path)
    return p.with_name(p.name.replace("county_to_district", "county_split_zcta"))


def load_map(county_dist_path):
    """(county -> district for whole counties, {county: [(zcta int, district)]} for split ones)."""
    cdf = pd.read_csv(county_dist_path, dtype={"county_fips5": str})
    county_to_dist = dict(zip(cdf["county_fips5"].str.zfill(5), cdf["district_id"]))
    splits: dict = {}
    sp = split_table_path(county_dist_path)
    if sp.exists():
        sdf = pd.read_csv(sp, dtype={"county_fips5": str, "zcta5": str})
        for county, zcta, did in zip(sdf["county_fips5"].str.zfill(5), sdf["zcta5"], sdf["district_id"]):
            splits.setdefault(county, []).append((int(zcta), did))
        for county in splits:
            splits[county].sort()
    return county_to_dist, splits


def assign(county_dist_path, apportion_df, voter_fips_path=VOTER_FIPS_PATH,
           inputstates=None, verbose=True) -> np.ndarray:
    """District id for every respondent, in typology row order."""
    voters = pd.read_csv(voter_fips_path, index_col=0, dtype={"countyfips": str, "zip": str})
    counties = voters["countyfips"].fillna("0").str.zfill(5).values
    zips = voters["zip"].fillna("").values if "zip" in voters.columns else np.full(len(voters), "")
    county_to_dist, splits = load_map(county_dist_path)

    state_first: dict = {}
    for _, row in apportion_df.iterrows():
        state_first.setdefault(int(row["state_fips"]), row["district_id"])

    out = np.empty(len(voters), dtype=object)
    n_zip = n_near = n_state = 0
    for i, (county, z) in enumerate(zip(counties, zips)):
        did = None
        pieces = splits.get(county)
        if pieces:
            zi = int(z) if z.isdigit() else -1
            exact = [d for zc, d in pieces if zc == zi]
            if exact:
                did = exact[0]
                n_zip += 1
            else:
                did = min(pieces, key=lambda p: (abs(p[0] - zi), p[0]))[1]
                n_near += 1
        if did is None:
            did = county_to_dist.get(county)
        if did is None:
            st = int(inputstates[i]) if inputstates is not None else int(county[:2] or 0)
            did = state_first.get(st, "")
            n_state += 1
        out[i] = did
    if verbose:
        print(f"  {len(out):,} respondents: {n_zip:,} placed by ZIP inside a split county, "
              f"{n_near:,} by nearest ZIP there, {n_state:,} on their state's first district")
    return out

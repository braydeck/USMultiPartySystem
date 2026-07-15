"""Compute affective polarization from the CSES Integrated Module Dataset (IMD) microdata.

CSES IMD is the primary source: respondent-level party like/dislike thermometers (0-10). We
compute the standard vote-share-weighted spread measure (Wagner 2021; the basis of Reiljan's
API): for each respondent, the weighted standard deviation of their party ratings, with parties
weighted by lower-house vote share so tiny parties don't dominate; then averaged (survey-
weighted) to a country-election estimate.

    spread_i = sqrt( sum_p w_p (like_ip - mbar_i)^2 ),   mbar_i = sum_p w_p like_ip
    AP(country, election) = weighted mean of spread_i over respondents

Outputs:
  data/affective_polarization_election.csv  one row per country-election (ISO3, year, AP, n)
  data/affective_polarization.csv           one row per country (mean/latest AP across waves)

The raw .dat is fixed-width; column positions come from the Stata dictionary (.dct).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
CSES = BASE / "cses" / "cses_imd_syntax"
DAT = CSES / "cses_imd.dat"
DCT = CSES / "cses_imd.dct"
DATA = BASE / "data"

PARTIES = list("ABCDEFGHI")
NEEDED = (["IMD1006_UNALPHA3", "IMD1004", "IMD1008_YEAR", "IMD1010_2", "IMD3005_3"]
          + [f"IMD3008_{p}" for p in PARTIES]      # party like/dislike 0-10
          + [f"IMD5000_{p}" for p in PARTIES]      # party numeric identifier (to find in-party)
          + [f"IMD5001_{p}" for p in PARTIES])     # lower-house vote share (%)
MIN_PARTIES = 2      # >=2 parties: valid for two-party systems (US), where AP is the like gap
MIN_RESP = 100       # spread: election must have >=100 usable respondents
MIN_API_RESP = 50    # in/out API: >=50 party identifiers (partisans only)
CODE_SENTINEL = 9_000_000  # numeric party codes >= this are missing/refused/none sentinels


def parse_dct(path: Path) -> dict[str, tuple[int, int]]:
    """Return {varname: (start0, end0)} half-open, 0-based, from the Stata dictionary.
    Width is inferred from the gap to the next _column (robust to format quirks)."""
    entries = []
    for line in path.read_text().splitlines():
        m = re.search(r"_column\((\d+)\)\s+\S+\s+(\S+)\s+%", line)
        if m:
            entries.append((int(m.group(1)), m.group(2)))
    entries.sort()
    spans = {}
    for i, (start, name) in enumerate(entries):
        end = entries[i + 1][0] if i + 1 < len(entries) else start + 20
        spans[name] = (start - 1, end - 1)  # to 0-based half-open
    return spans


def load_microdata() -> pd.DataFrame:
    spans = parse_dct(DCT)
    cols = [c for c in NEEDED if c in spans]
    missing = [c for c in NEEDED if c not in spans]
    if missing:
        raise SystemExit(f"Missing from dictionary: {missing}")
    colspecs = [spans[c] for c in cols]
    print(f"[read] {DAT.name} fixed-width, {len(cols)} columns ...")
    df = pd.read_fwf(DAT, colspecs=colspecs, names=cols, dtype=str)
    print(f"[read] {len(df):,} respondents")
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={"IMD1006_UNALPHA3": "code", "IMD1008_YEAR": "year",
                            "IMD1004": "election", "IMD1010_2": "weight"})
    df["code"] = df["code"].str.strip()
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    df.loc[(df["weight"] <= 0) | (df["weight"] > 100) | df["weight"].isna(), "weight"] = 1.0
    inp = pd.to_numeric(df["IMD3005_3"], errors="coerce")           # respondent's closest party code
    df["inparty_code"] = inp.where((inp > 0) & (inp < CODE_SENTINEL))
    for p in PARTIES:
        like = pd.to_numeric(df[f"IMD3008_{p}"], errors="coerce")
        df[f"like_{p}"] = like.where(like.between(0, 10))          # 0-10 valid; codes >10 = missing
        vs = pd.to_numeric(df[f"IMD5001_{p}"], errors="coerce")
        df[f"vs_{p}"] = vs.where(vs.between(0, 100))               # 0-100 valid; else missing
        pid = pd.to_numeric(df[f"IMD5000_{p}"], errors="coerce")
        df[f"pid_{p}"] = pid.where((pid > 0) & (pid < CODE_SENTINEL))  # party A..I numeric id
    return df


def respondent_measures(df: pd.DataFrame) -> pd.DataFrame:
    """Compute two per-respondent affective-polarization measures:
       spread  = vote-share-weighted SD of party ratings (Wagner 2021)
       api     = in-party rating minus vote-share-weighted mean of out-party ratings
                 (Reiljan 2020 / Gidron-Adams-Horne in-vs-out affect; 'do I dislike the
                 other side because they're the other side') -- partisans only."""
    like = df[[f"like_{p}" for p in PARTIES]].to_numpy(float)
    vs = df[[f"vs_{p}" for p in PARTIES]].to_numpy(float)
    pid = df[[f"pid_{p}" for p in PARTIES]].to_numpy(float)
    incode = df["inparty_code"].to_numpy(float)[:, None]
    valid = ~np.isnan(like)
    n_rated = valid.sum(axis=1)

    # ---- spread (all respondents rating >=2 parties) ----
    w = np.where(valid & ~np.isnan(vs), np.nan_to_num(vs), 0.0)
    no_share = w.sum(axis=1) == 0
    w[no_share] = valid[no_share].astype(float)         # equal weights if no shares
    wn = _normalize(w)
    like0 = np.nan_to_num(like)
    mbar = (wn * like0).sum(axis=1, keepdims=True)
    spread = np.sqrt((wn * (like0 - mbar) ** 2).sum(axis=1))

    # ---- in/out API (respondents with an identified in-party) ----
    inmask = valid & ~np.isnan(pid) & (pid == incode) & ~np.isnan(incode)
    has_in = inmask.sum(axis=1) == 1                    # exactly one in-party, rated
    in_like = np.where(inmask, like0, 0.0).sum(axis=1)
    outmask = valid & ~inmask
    ow = np.where(outmask & ~np.isnan(vs), np.nan_to_num(vs), 0.0)
    no_oshare = (ow.sum(axis=1) == 0) & outmask.any(axis=1)
    ow[no_oshare] = outmask[no_oshare].astype(float)
    own = _normalize(ow)
    out_mean = (own * like0).sum(axis=1)
    has_out = ow.sum(axis=1) > 0
    api = in_like - out_mean
    df = df.copy()
    df["spread"] = spread
    df["n_rated"] = n_rated
    df["api"] = np.where(has_in & has_out, api, np.nan)
    return df[df["n_rated"] >= MIN_PARTIES]


def _normalize(w):
    s = w.sum(axis=1, keepdims=True)
    return np.divide(w, s, out=np.zeros_like(w), where=s > 0)


def wmean(v, wt):
    m = ~np.isnan(v)
    return np.average(v[m], weights=wt[m]) if m.any() else np.nan


def aggregate(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    def agg_elec(g):
        api_ok = g["api"].notna()
        return pd.Series({
            "affpol_api": wmean(g["api"].to_numpy(), g["weight"].to_numpy()),
            "n_api": int(api_ok.sum()),
            "affpol_spread": np.average(g["spread"], weights=g["weight"]),
            "n_parties": np.average(g["n_rated"], weights=g["weight"]),
            "n": len(g)})
    elec = (df.groupby(["code", "year", "election"])
            .apply(agg_elec, include_groups=False).reset_index())
    elec = elec[elec["n"] >= MIN_RESP].copy()
    # API estimate only trustworthy with enough partisans
    elec.loc[elec["n_api"] < MIN_API_RESP, "affpol_api"] = np.nan
    for c in ["affpol_api", "affpol_spread", "n_parties"]:
        elec[c] = elec[c].round(3)
    country = (elec.sort_values("year").groupby("code")
               .agg(api_mean=("affpol_api", "mean"), api_latest=("affpol_api", "last"),
                    spread_mean=("affpol_spread", "mean"), spread_latest=("affpol_spread", "last"),
                    latest_year=("year", "last"), n_parties=("n_parties", "mean"),
                    n_elections=("affpol_spread", "size"))
               .reset_index())
    for c in ["api_mean", "api_latest", "spread_mean", "spread_latest", "n_parties"]:
        country[c] = country[c].round(3)
    return elec, country


def main():
    df = clean(load_microdata())
    df = df[df["code"].str.fullmatch(r"[A-Z]{3}", na=False)]
    df = respondent_measures(df)
    in_rate = df["api"].notna().mean()
    print(f"[in-party] {in_rate:.0%} of rating respondents have an identified in-party")
    elec, country = aggregate(df)
    elec.to_csv(DATA / "affective_polarization_election.csv", index=False)
    country.to_csv(DATA / "affective_polarization.csv", index=False)
    print(f"\n[saved] {len(elec)} country-elections, {len(country)} countries; "
          f"{country['api_latest'].notna().sum()} countries have a usable in/out API")
    print("Elections coverage:", int(elec["year"].min()), "-", int(elec["year"].max()))
    print("\nSample latest wave (api = in/out affect gap, spread = Wagner SD):")
    show = country[country.code.isin(["USA", "GBR", "CAN", "AUS", "NZL", "IRL", "ZAF",
                                      "DEU", "SWE", "FRA", "CHE"])]
    print(show[["code", "api_latest", "spread_latest", "latest_year", "n_parties",
                "n_elections"]].to_string(index=False))


if __name__ == "__main__":
    main()

"""Build the merged country-year analysis panel.

Takes the user's polarization CSV as the outcome source of truth and appends
institutional attributes from the acquired authoritative datasets:

  outcome        polarization            <- political-polarization-score.csv (V-Dem v2cacamps)
  institutions   elec_system_lower       <- V-Dem v2elparlel (forward-filled; coded only in
                                             election years), plus a hand-coded elec_family for
                                             the anglophone core (FPTP vs AV vs STV vs MMP vs PR)
                 gov_system              <- Cheibub chga_hinst (QoG TS; time-invariant fill)
                 bicameral               <- V-Dem v2lgbicam
                 house_incongruent       <- hand-coded (upper vs lower chamber apportionment)
  context        democracy_score         <- V-Dem v2x_polyarchy
                 regime                  <- V-Dem v2x_regime (Regimes of the World)
                 legal_origin            <- La Porta lp_legor (QoG CS jan22; time-invariant)
                 colonial_origin         <- Hadenius-Teorell ht_colonial (QoG TS)
                 anglophone, language_family <- hand-coded reference
  tiers          tier_anglo / tier_established / tier_all_democracies

Validation: the V-Dem v2cacamps merged in by (ISO3, year) must correlate ~1.0 with the
polarization score in the user's CSV, confirming the institutional join is on the right rows.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw"
DATA = BASE / "data"

CORE = ["USA", "GBR", "CAN", "IRL", "AUS", "NZL", "IND", "MLT", "ZAF"]

# Fine-grained electoral family for the anglophone core. V-Dem's v2elparlel collapses
# single-member systems (FPTP and Australia's preferential AV) into one "majoritarian"
# category, so the descriptive tier needs this hand annotation. AV is majoritarian, not PR.
ELEC_FAMILY_CORE = {
    "USA": "FPTP", "GBR": "FPTP", "CAN": "FPTP", "IND": "FPTP",
    "AUS": "AV",                      # preferential, majoritarian single-member
    "NZL": "MMP",                     # mixed-member proportional since 1996 (FPTP before)
    "IRL": "STV", "MLT": "STV",       # proportional
    "ZAF": "PR-list",                 # closed-list PR
}

ELEC_SYSTEM_MAP = {0: "majoritarian", 1: "proportional", 2: "mixed", 3: "other"}
# Cheibub chga_hinst regime labels. Codes 3/4/5 (dictatorship types) are set to NaN: for the
# democracies we analyse they are either not applicable or, as with South Africa (coded a
# civilian dictatorship throughout the series, an error for the post-1994 democracy), wrong.
GOV_SYSTEM_MAP = {0: "parliamentary", 1: "semi-presidential", 2: "presidential",
                  3: None, 4: None, 5: None}
# Documented corrections where chga_hinst is clearly wrong/missing for a current democracy.
GOV_OVERRIDE = {"ZAF": "parliamentary"}  # president elected by & accountable to the Assembly
LEGAL_ORIGIN_MAP = {1: "common_law", 2: "french", 3: "socialist",
                    4: "german", 5: "scandinavian"}
REGIME_MAP = {0: "closed_autocracy", 1: "electoral_autocracy",
              2: "electoral_democracy", 3: "liberal_democracy"}


def load_polarization() -> pd.DataFrame:
    df = pd.read_csv(BASE / "political-polarization-score.csv")
    df = df.rename(columns={"Code": "code", "Year": "year", "Entity": "entity",
                            "Political polarization score": "polarization"})
    # keep genuine ISO-3 country codes; drop OWID regional aggregates
    iso3 = df["code"].astype(str).str.fullmatch(r"[A-Z]{3}")
    dropped = sorted(df.loc[~iso3, "entity"].unique())
    df = df[iso3].copy()
    print(f"[polarization] {df.shape[0]} country-year rows, "
          f"{df['code'].nunique()} countries; dropped aggregates: {dropped}")
    return df[["code", "entity", "year", "polarization"]]


def load_vdem() -> pd.DataFrame:
    v = pd.read_parquet(RAW / "vdem_slim.parquet")
    v = v.rename(columns={"country_text_id": "code"})
    v["year"] = v["year"].astype(int)
    v = v.sort_values(["code", "year"])
    # v2elparlel is coded only in election years -> carry the electoral system forward
    # (and backward for the pre-first-election tail) within each country.
    v["v2elparlel_filled"] = (v.groupby("code")["v2elparlel"]
                              .ffill().bfill())
    return v


HT_REGION_MAP = {1: "E_Europe_postSoviet", 2: "Latin_America", 3: "MENA",
                 4: "Sub_Saharan_Africa", 5: "West_Europe_N_America", 6: "East_Asia",
                 7: "SE_Asia", 8: "South_Asia", 9: "Pacific_Oceania", 10: "Caribbean"}


def load_gov_system() -> pd.DataFrame:
    ts = pd.read_csv(RAW / "qog_std_ts_jan25.csv",
                     usecols=["ccodealp", "year", "chga_hinst", "ht_colonial",
                              "ht_region", "wdi_pop"])
    ts = ts.rename(columns={"ccodealp": "code", "wdi_pop": "population"})
    ts = ts.sort_values(["code", "year"])
    # chga_hinst (Cheibub) ends ~2008; government system is near time-invariant, so fill
    # within country to extend coverage to the present. Population is genuinely annual -> no fill.
    ts["chga_hinst"] = ts.groupby("code")["chga_hinst"].ffill().bfill()
    ts["ht_region"] = ts.groupby("code")["ht_region"].ffill().bfill()
    ts["region"] = ts["ht_region"].map(HT_REGION_MAP)
    return ts[["code", "year", "chga_hinst", "ht_colonial", "region", "population"]]


def load_legal_origin() -> pd.DataFrame:
    cs = pd.read_csv(RAW / "qog_std_cs_jan22.csv", usecols=["ccodealp", "lp_legor"])
    cs = cs.rename(columns={"ccodealp": "code", "lp_legor": "legal_origin_code"})
    # La Porta leaves the reference German-origin country (Germany) blank; patch it.
    cs.loc[cs["code"] == "DEU", "legal_origin_code"] = 4.0
    return cs.dropna(subset=["legal_origin_code"])


def main() -> None:
    pol = load_polarization()
    vdem = load_vdem()
    gov = load_gov_system()
    legal = load_legal_origin()
    ref = pd.read_csv(DATA / "country_reference.csv")

    df = pol.merge(
        vdem[["code", "year", "v2cacamps", "v2x_polyarchy", "v2x_regime",
              "v2elparlel_filled", "v2lgbicam", "v2ex_elechos", "v2exhoshog"]],
        on=["code", "year"], how="left")

    # --- merge validation: our polarization score IS V-Dem v2cacamps ---
    both = df.dropna(subset=["v2cacamps"])
    corr = both["polarization"].corr(both["v2cacamps"])
    print(f"[validate] corr(CSV polarization, merged V-Dem v2cacamps) = {corr:.4f} "
          f"on {len(both)} overlapping rows")
    assert corr > 0.99, f"merge validation failed: correlation {corr:.3f} < 0.99"

    df = df.merge(gov, on=["code", "year"], how="left")
    df = df.merge(legal, on="code", how="left")
    df = df.merge(ref, on="code", how="left")

    # --- derived analysis columns ---
    df["elec_system_lower"] = df["v2elparlel_filled"].map(ELEC_SYSTEM_MAP)
    df["majoritarian_fptp"] = np.where(
        df["v2elparlel_filled"].isin([1, 2, 3]), 0,
        np.where(df["v2elparlel_filled"] == 0, 1, np.nan))
    df["elec_family"] = df["code"].map(ELEC_FAMILY_CORE)  # core only; NaN elsewhere
    df["gov_system"] = df["chga_hinst"].map(GOV_SYSTEM_MAP)
    for c, val in GOV_OVERRIDE.items():
        df.loc[df["code"] == c, "gov_system"] = val
    # `presidential` (regression control) comes from V-Dem, not chga_hinst: a popularly
    # elected head of state who is ALSO head of government. This has coverage to 2025 and
    # correctly treats directly-elected-but-ceremonial presidencies (Ireland, Germany) and
    # assembly-elected executives (South Africa) as non-presidential.
    both_exec = df["v2ex_elechos"].notna() & df["v2exhoshog"].notna()
    df["presidential"] = np.where(
        (df["v2ex_elechos"] == 1) & (df["v2exhoshog"] == 1), 1,
        np.where(both_exec, 0, np.nan))
    df["bicameral"] = np.where(df["v2lgbicam"] == 2, 1,
                               np.where(df["v2lgbicam"].isin([0, 1]), 0, np.nan))
    df["democracy_score"] = df["v2x_polyarchy"]
    # Taiwan is absent from the World Bank population series (a known data gap); patch it so it
    # is not dropped as "missing" and mis-flagged. ~23.5M -> clearly not a micro-state.
    df.loc[df["code"] == "TWN", "population"] = df.loc[df["code"] == "TWN", "population"].fillna(23_500_000)
    df["log_pop"] = np.log10(df["population"])
    # Micro-state status is a country trait, not year-varying: classify from each country's most
    # recent available population so missing-year rows can't flip the flag (NaN < 1e6 is False,
    # which previously leaked small states like Barbados/Seychelles into the non-micro set).
    pop_ref = (df.dropna(subset=["population"]).sort_values("year")
               .groupby("code")["population"].last())
    micro = df["code"].map(pop_ref) < 1_000_000
    df["microstate"] = micro.where(df["code"].map(pop_ref).notna()).astype("Int64")
    df["regime"] = df["v2x_regime"].map(REGIME_MAP)
    df["legal_origin"] = df["legal_origin_code"].map(LEGAL_ORIGIN_MAP)
    df["common_law"] = (df["legal_origin"] == "common_law").astype("Int64")
    df["anglophone"] = df["anglophone"].fillna(0).astype(int)
    df["language_family"] = df["language_family"].fillna("Other")

    # --- tiers ---
    df["tier_anglo"] = df["code"].isin(CORE)
    df["tier_established"] = df["v2x_regime"] == 3          # liberal democracies
    df["tier_all_democracies"] = df["v2x_regime"] >= 2      # electoral + liberal democracies

    out_cols = ["code", "entity", "year", "polarization",
                "elec_system_lower", "majoritarian_fptp", "elec_family",
                "gov_system", "presidential", "bicameral", "house_incongruent",
                "upper_house_system", "democracy_score", "regime",
                "population", "log_pop", "microstate", "region",
                "legal_origin", "common_law", "colonial_origin_ht",
                "anglophone", "language_family",
                "tier_anglo", "tier_established", "tier_all_democracies"]
    df = df.rename(columns={"ht_colonial": "colonial_origin_ht"})
    df = df[out_cols].sort_values(["code", "year"]).reset_index(drop=True)

    df.to_parquet(DATA / "analysis_panel.parquet", index=False)
    df.to_csv(DATA / "analysis_panel.csv", index=False)
    print(f"[saved] analysis_panel {df.shape} -> data/analysis_panel.parquet/.csv")

    # --- spot checks ---
    print("\n[spot check] anglophone core, 2020:")
    cols = ["code", "polarization", "elec_family", "majoritarian_fptp",
            "gov_system", "bicameral", "legal_origin", "democracy_score"]
    print(df[(df.code.isin(CORE)) & (df.year == 2020)][cols].to_string(index=False))
    print("\n[spot check] contrast cases, 2020:")
    print(df[(df.code.isin(["FRA", "DEU", "SWE", "BRA"])) & (df.year == 2020)][cols]
          .to_string(index=False))
    print("\n[coverage] rows per tier (year>=1990):")
    r = df[df.year >= 1990]
    for t in ["tier_anglo", "tier_established", "tier_all_democracies"]:
        sub = r[r[t]]
        print(f"  {t}: {len(sub)} rows, {sub['code'].nunique()} countries, "
              f"FPTP-coded rows={sub['majoritarian_fptp'].notna().sum()}")


if __name__ == "__main__":
    main()

"""Wave-specific item inventories for independent per-wave clustering.

Each wave gets its own full policy-item universe — broader than the crosswalk, which
only tracks items shared across waves. Items reuse crosswalk.RECODE_MAPS for label→number
recoding. Split-sample items (441e/f/g) are excluded to keep N~48k.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common.crosswalk import RECODE_MAPS, _norm
import numpy as np


def _item(variable, construct_id, recode, domain):
    return {"variable": variable, "construct_id": construct_id, "recode": recode, "domain": domain}


ITEMS_2022 = [
    # Religion
    _item("pew_churatd",  "relig_church",        "CHURCH6",          "Religion"),
    # Economic
    _item("CC22_303",     "econ_income",          "INCOME5",          "Economic"),
    _item("CC22_304",     "econ_price",           "PRICE5",           "Economic"),
    # Immigration
    _item("CC22_331a",    "imm_legalstatus",      "SO_hi_oppose",     "Immigration"),
    _item("CC22_331b",    "imm_border",           "SO_hi_support",    "Immigration"),
    _item("CC22_331c",    "imm_reducelegal",      "SO_hi_support",    "Immigration"),
    _item("CC22_331d",    "imm_border25b",        "SO_hi_support",    "Immigration"),
    # Guns
    _item("CC22_330a",    "gun_registry",         "SO_hi_oppose",     "Guns"),
    _item("CC22_330b",    "gun_assaultban",       "SO_hi_oppose",     "Guns"),
    _item("CC22_330c",    "gun_concealcarry",     "SO_hi_support",    "Guns"),
    _item("CC22_330d",    "gun_redflag",          "SO_hi_oppose",     "Guns"),
    _item("CC22_330e",    "gun_bgchecks",         "SO_hi_oppose",     "Guns"),
    _item("CC22_330f",    "gun_teacherscarry",    "SO_hi_support",    "Guns"),
    # Abortion
    _item("CC22_332a",    "abortion_alwaysallow", "SO_hi_oppose",     "Abortion"),
    _item("CC22_332b",    "abortion_rapeincest",  "SO_hi_support",    "Abortion"),
    _item("CC22_332c",    "abortion_20wk",        "SO_hi_support",    "Abortion"),
    _item("CC22_332d",    "abortion_employer",    "SO_hi_support",    "Abortion"),
    _item("CC22_332e",    "abortion_funding",     "SO_hi_support",    "Abortion"),
    _item("CC22_332f",    "abortion_illegalall",  "SO_hi_support",    "Abortion"),
    # Racial / Gender attitudes (full-sample only)
    _item("CC22_440a",    "race_whiteadv",        "AGREE5_hi_disagree", "Racial"),
    _item("CC22_440b",    "race_problemsrare",    "AGREE5_hi_agree",   "Racial"),
    _item("CC22_440c",    "gender_womenpower",    "AGREE5_hi_agree",   "Racial"),
    _item("CC22_440d",    "gender_womenoffended", "AGREE5_hi_agree",   "Racial"),
    _item("CC22_441a",    "race_workedup",        "AGREE5_hi_agree",   "Racial"),
    _item("CC22_441b",    "race_slavery",         "AGREE5_hi_disagree", "Racial"),
    # Spending
    _item("CC22_443_1",   "spend_welfare",        "SPEND5_cut",       "Spending"),
    _item("CC22_443_2",   "spend_health",         "SPEND5_cut",       "Spending"),
    _item("CC22_443_3",   "spend_education",      "SPEND5_cut",       "Spending"),
    _item("CC22_443_4",   "spend_lawenforce",     "SPEND5_raise",     "Spending"),
    _item("CC22_443_5",   "spend_transport",      "SPEND5_cut",       "Spending"),
    # Health
    _item("CC22_327a",    "health_singlepayer",   "SO_hi_oppose",     "Health"),
    _item("CC22_327b",    "health_drugnegotiate", "SO_hi_oppose",     "Health"),
    _item("CC22_327c",    "health_acarepeal",     "SO_hi_support",    "Health"),
    _item("CC22_327d",    "health_drugimport",    "SO_hi_oppose",     "Health"),
    # Environment
    _item("CC22_333a",    "env_eparegulate",      "SO_hi_oppose",     "Environment"),
    _item("CC22_333b",    "env_renewables",       "SO_hi_oppose",     "Environment"),
    _item("CC22_333c",    "env_epaenforce",       "SO_hi_oppose",     "Environment"),
    _item("CC22_333d",    "env_fuelefficiency",   "SO_hi_oppose",     "Environment"),
    _item("CC22_333e",    "env_fossilfuel",       "SO_hi_support",    "Environment"),
    # Policing (exact match to 2024 CC24_321d/e — missed in original crosswalk)
    _item("CC22_334c",    "police_increase",      "SO_hi_support",    "Policing"),
    _item("CC22_334d",    "police_decrease",      "SO_hi_oppose",     "Policing"),
    # Government trust
    _item("CC22_423",     "trust_fed",            "GOVT4",            "GovtTrust"),
    _item("CC22_424",     "trust_state",          "GOVT4",            "GovtTrust"),
]


ITEMS_2020 = [
    # Religion
    _item("pew_churatd",  "relig_church",        "CHURCH6",          "Religion"),
    # Economic
    _item("CC20_303",     "econ_income",          "INCOME5",          "Economic"),
    # Immigration
    _item("CC20_331a",    "imm_legalstatus",      "SO_hi_oppose",     "Immigration"),
    _item("CC20_331b",    "imm_border",           "SO_hi_support",    "Immigration"),
    _item("CC20_331c",    "imm_sanctuary",        "SO_hi_oppose",     "Immigration"),
    _item("CC20_331d",    "imm_reducelegal",      "SO_hi_support",    "Immigration"),
    _item("CC20_331e",    "imm_border25b",        "SO_hi_support",    "Immigration"),
    # Guns
    _item("CC20_330a",    "gun_registry",         "SO_hi_oppose",     "Guns"),
    _item("CC20_330b",    "gun_assaultban",       "SO_hi_oppose",     "Guns"),
    _item("CC20_330c",    "gun_concealcarry",     "SO_hi_support",    "Guns"),
    # Policing (post-Floyd, 2020-only)
    _item("CC20_334a",    "police_mandatorymin",  "SO_hi_oppose",     "Policing"),
    _item("CC20_334b",    "police_bodycams",      "SO_hi_oppose",     "Policing"),
    _item("CC20_334c",    "police_increase",      "SO_hi_support",    "Policing"),
    _item("CC20_334d",    "police_decrease",      "SO_hi_oppose",     "Policing"),
    _item("CC20_334e",    "police_chokeholds",    "SO_hi_oppose",     "Policing"),
    _item("CC20_334f",    "police_registry",      "SO_hi_oppose",     "Policing"),
    _item("CC20_334g",    "police_enddod",        "SO_hi_oppose",     "Policing"),
    _item("CC20_334h",    "police_civilsuits",    "SO_hi_oppose",     "Policing"),
    # Abortion
    _item("CC20_332a",    "abortion_alwaysallow", "SO_hi_oppose",     "Abortion"),
    _item("CC20_332b",    "abortion_rapeincest",  "SO_hi_support",    "Abortion"),
    _item("CC20_332c",    "abortion_20wk",        "SO_hi_support",    "Abortion"),
    _item("CC20_332d",    "abortion_employer",    "SO_hi_support",    "Abortion"),
    _item("CC20_332e",    "abortion_funding",     "SO_hi_support",    "Abortion"),
    _item("CC20_332f",    "abortion_illegalall",  "SO_hi_support",    "Abortion"),
    _item("CC20_332g",    "abortion_statereqs",   "SO_hi_oppose",     "Abortion"),
    # Racial / Gender (full-sample only)
    _item("CC20_440a",    "race_whiteadv",        "AGREE5_hi_disagree", "Racial"),
    _item("CC20_440b",    "race_problemsrare",    "AGREE5_hi_agree",   "Racial"),
    _item("CC20_440c",    "gender_womenpower",    "AGREE5_hi_agree",   "Racial"),
    _item("CC20_440d",    "gender_womenoffended", "AGREE5_hi_agree",   "Racial"),
    _item("CC20_441a",    "race_workedup",        "AGREE5_hi_agree",   "Racial"),
    _item("CC20_441b",    "race_slavery",         "AGREE5_hi_disagree", "Racial"),
    # Spending
    _item("CC20_443_1",   "spend_welfare",        "SPEND5_cut",       "Spending"),
    _item("CC20_443_2",   "spend_health",         "SPEND5_cut",       "Spending"),
    _item("CC20_443_3",   "spend_education",      "SPEND5_cut",       "Spending"),
    _item("CC20_443_4",   "spend_lawenforce",     "SPEND5_raise",     "Spending"),
    _item("CC20_443_5",   "spend_transport",      "SPEND5_cut",       "Spending"),
    # Executive orders
    _item("CC20_355a",    "exec_paris",           "SO_hi_support",    "Executive"),
    _item("CC20_355c",    "exec_cleanpower",      "SO_hi_support",    "Executive"),
    _item("CC20_355d",    "exec_transban",        "SO_hi_support",    "Executive"),
    _item("CC20_355e",    "exec_workreqs",        "SO_hi_support",    "Executive"),
]


ITEMS_2018 = [
    # Religion
    _item("pew_churatd",  "relig_church",         "CHURCH6",          "Religion"),
    # Economic
    _item("CC18_302",     "econ_income",          "INCOME5",          "Economic"),
    # Immigration
    _item("CC18_322a",    "imm_border25b",        "SO_hi_support",    "Immigration"),
    _item("CC18_322b",    "imm_legalstatus",      "SO_hi_oppose",     "Immigration"),
    _item("CC18_322c",    "imm_sanctuary",        "SO_hi_oppose",     "Immigration"),
    _item("CC18_322c_new","imm_reducelegal",      "SO_hi_support",    "Immigration"),
    _item("CC18_322d_new","imm_dacawall",         "SO_hi_support",    "Immigration"),
    _item("CC18_322f",    "imm_deportprison",     "SO_hi_support",    "Immigration"),
    # Guns (2018 uses For/Against labels — handled by SO_hi_support/oppose)
    _item("CC18_320a",    "gun_bgchecks",         "SO_hi_oppose",     "Guns"),
    _item("CC18_320c",    "gun_assaultban",       "SO_hi_oppose",     "Guns"),
    _item("CC18_320d",    "gun_concealcarry",     "SO_hi_support",    "Guns"),
    # Abortion
    _item("CC18_321a",    "abortion_alwaysallow", "SO_hi_oppose",     "Abortion"),
    _item("CC18_321b",    "abortion_rapeincest",  "SO_hi_support",    "Abortion"),
    _item("CC18_321c",    "abortion_20wk",        "SO_hi_support",    "Abortion"),
    _item("CC18_321d",    "abortion_employer",    "SO_hi_support",    "Abortion"),
    _item("CC18_321e",    "abortion_funding",     "SO_hi_support",    "Abortion"),
    _item("CC18_321f",    "abortion_illegalall",  "SO_hi_support",    "Abortion"),
    # Racial / Gender
    _item("CC18_422a",    "race_whiteadv",        "AGREE5_hi_disagree", "Racial"),
    _item("CC18_422b",    "race_problemsrare",    "AGREE5_hi_agree",   "Racial"),
    _item("CC18_422c",    "gender_sexismcomp",    "AGREE5_hi_agree",   "Racial"),
    _item("CC18_422d",    "gender_feministsreasonable", "AGREE5_hi_disagree", "Racial"),
    _item("CC18_422e",    "race_workedup",        "AGREE5_hi_agree",   "Racial"),
    _item("CC18_422f",    "race_slavery",         "AGREE5_hi_disagree", "Racial"),
    _item("CC18_422g",    "race_lessdeserve",     "AGREE5_hi_disagree", "Racial"),
    _item("CC18_422h",    "race_tryharder",       "AGREE5_hi_agree",   "Racial"),
    # Spending
    _item("CC18_426_1",   "spend_welfare",        "SPEND5_cut",       "Spending"),
    _item("CC18_426_2",   "spend_health",         "SPEND5_cut",       "Spending"),
    _item("CC18_426_3",   "spend_education",      "SPEND5_cut",       "Spending"),
    _item("CC18_426_4",   "spend_lawenforce",     "SPEND5_raise",     "Spending"),
    _item("CC18_426_5",   "spend_transport",      "SPEND5_cut",       "Spending"),
    # Tax (TCJA battery)
    _item("CC18_325a",    "tax_corprate",         "SO_hi_support",    "Tax"),
    _item("CC18_325f_new","tax_richcut",          "SO_hi_support",    "Tax"),
    # Executive orders
    _item("CC18_417_a",   "exec_cleanpower",      "SO_hi_support",    "Executive"),
    _item("CC18_417_b",   "exec_iran",            "SO_hi_support",    "Executive"),
    _item("CC18_417_c",   "exec_travelban",       "SO_hi_support",    "Executive"),
    _item("CC18_417_d",   "exec_transban",        "SO_hi_support",    "Executive"),
    _item("CC18_417_e",   "exec_twoforone",       "SO_hi_support",    "Executive"),
]


WAVE_CONFIGS = {
    "2022": ITEMS_2022,
    "2020": ITEMS_2020,
    "2018": ITEMS_2018,
}


def get_items(wave):
    """Return the item inventory for a wave."""
    if wave not in WAVE_CONFIGS:
        raise ValueError(f"No independent item config for wave {wave}. Available: {list(WAVE_CONFIGS)}")
    return WAVE_CONFIGS[wave]


def recode_items(df_labeled, items):
    """Recode a label-decoded DataFrame into numeric values for the given item list.

    Returns a DataFrame keyed by construct_id with numeric columns."""
    out = {}
    for it in items:
        var = it["variable"]
        cid = it["construct_id"]
        token = it["recode"]
        if var not in df_labeled.columns:
            raise KeyError(f"Variable {var} for construct {cid} not in dataframe")
        rmap = {_norm(k): v for k, v in RECODE_MAPS[token].items()}
        s = df_labeled[var].astype("object")
        vals = [rmap.get(_norm(v), np.nan) for v in s]
        out[cid] = vals
    import pandas as pd
    return pd.DataFrame(out, index=df_labeled.index).astype(float)

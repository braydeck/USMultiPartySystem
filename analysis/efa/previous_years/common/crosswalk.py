"""Item crosswalk: load config/item_crosswalk.csv, apply per-construct recodes,
and expose the per-wave / common-across-waves item sets.

Recode is label-based (convert_categoricals=True): every substantive response
label maps to a number oriented so HIGHER = more conservative/right (or, for
econ/trust/distrust items, the documented direction). Any label not in the map
(skipped / not asked / don't know / Not sure*) becomes NaN.
  * exception: govt-trust "Not sure" → 2 (midpoint), matching the 2024 pipeline.

This reproduces the direction conventions in efa_pipeline_v4.py /
cluster_survival_k4_k5.py (validated against efa_loadings_k5_final.csv).
"""
import numpy as np
import pandas as pd
from . import io_paths

USABLE = {"exact", "equivalent", "weak"}   # coverage levels admitted to a native fit
STRICT = {"exact", "equivalent"}           # coverage levels admitted to the common subset

# The state-spending battery is all-wave, but its five same-format "increase/decrease
# spending on X" items form a method/format factor that is NOT part of the 2024
# typology (whose fiscal content loads on Populist Conservatism, not a separate axis).
# Keep it in native "on its own terms" fits, exclude it from the cross-wave common
# comparison so the common factors map to the five named 2024 factors.
EXCLUDE_FROM_COMMON = {"spend_welfare", "spend_health", "spend_education",
                       "spend_lawenforce", "spend_transport"}

# ── Recode label maps (by construct-level recode token) ──────────────────────
_SO_SUPPORT = {"Support": 1, "Oppose": 0, "For": 1, "Against": 0, "Favor": 1}
_SO_OPPOSE = {"Support": 0, "Oppose": 1, "For": 0, "Against": 1, "Favor": 0}
_AGREE_HI = {"Strongly agree": 5, "Somewhat agree": 4, "Neither agree nor disagree": 3,
             "Somewhat disagree": 2, "Strongly disagree": 1}
_AGREE_LO = {"Strongly agree": 1, "Somewhat agree": 2, "Neither agree nor disagree": 3,
             "Somewhat disagree": 4, "Strongly disagree": 5}
_CHURCH = {"Never": 1, "Seldom": 2, "A few times a year": 3, "Once or twice a month": 4,
           "Once a week": 5, "More than once a week": 6, "Don't know": np.nan}
_INCOME = {"Increased a lot": 1, "Increased somewhat": 2, "Stayed about the same": 3,
           "Decreased somewhat": 4, "Decreased a lot": 5}
_PRICE = {"Decreased a lot": 1, "Decreased somewhat": 2, "Stayed about the same": 3,
          "Increased somewhat": 4, "Increased a lot": 5}
_GOVT = {"A great deal": 1, "A fair amount": 2, "Not very much": 3, "None at all": 4,
         "Not sure": 2}
_ELEC = {"Strongly agree": 1, "Somewhat agree": 2, "Neither agree nor disagree": 3,
         "Somewhat disagree": 4, "Strongly disagree": 5}
# State-spending battery: 5-pt greatly-increase..greatly-decrease.
# _cut: higher = cut spending = conservative (welfare/health/education/transport).
# _raise: higher = increase spending = conservative/order (law enforcement).
_SPEND_CUT = {"Greatly increase": 1, "Slightly increase": 2, "Maintain": 3,
              "Slightly decrease": 4, "Greatly decrease": 5}
_SPEND_RAISE = {"Greatly increase": 5, "Slightly increase": 4, "Maintain": 3,
                "Slightly decrease": 2, "Greatly decrease": 1}

RECODE_MAPS = {
    "SO_hi_support": _SO_SUPPORT, "SO_hi_oppose": _SO_OPPOSE,
    "AGREE5_hi_agree": _AGREE_HI, "AGREE5_hi_disagree": _AGREE_LO,
    "CHURCH6": _CHURCH, "INCOME5": _INCOME, "PRICE5": _PRICE,
    "GOVT4": _GOVT, "ELEC5": _ELEC,
    "SPEND5_cut": _SPEND_CUT, "SPEND5_raise": _SPEND_RAISE,
}


def load():
    return pd.read_csv(io_paths.CONFIG / "item_crosswalk.csv")


def _var_col(wave):
    return f"var_{wave}"


def _cov_col(wave):
    return f"cov_{wave}"


def constructs_for_wave(wave, levels=USABLE, cw=None):
    """Construct rows usable in a native fit for this wave (coverage in `levels`)."""
    cw = load() if cw is None else cw
    m = cw[_cov_col(wave)].isin(levels) & cw[_var_col(wave)].notna()
    return cw[m].copy()


def common_constructs(levels=STRICT, cw=None):
    """Constructs present at `levels` in ALL waves (the apples-to-apples subset)."""
    cw = load() if cw is None else cw
    mask = np.ones(len(cw), dtype=bool)
    for wv in io_paths.WAVES:
        mask &= cw[_cov_col(wv)].isin(levels) & cw[_var_col(wv)].notna()
    mask &= ~cw["construct_id"].isin(EXCLUDE_FROM_COMMON)
    return cw[mask].copy()


def _norm(s):
    """Normalize a response label: collapse internal whitespace and strip.
    CES label strings vary in spacing across waves (e.g. 2018 'Strongly  agree')."""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None
    return " ".join(str(s).split())


def recode_wave(df_labeled, wave, levels=USABLE, cw=None):
    """Given a label-decoded DataFrame (convert_categoricals=True) for `wave`,
    return a DataFrame of recoded numeric items keyed by construct_id.

    Whitespace in both the response labels and the recode-map keys is normalized
    before matching, so single/double-space variants across waves map identically."""
    cw = load() if cw is None else cw
    rows = constructs_for_wave(wave, levels=levels, cw=cw)
    out = {}
    for _, r in rows.iterrows():
        var = r[_var_col(wave)]
        cid = r["construct_id"]
        token = r["recode"]
        if var not in df_labeled.columns:
            raise KeyError(f"{wave}: variable {var} for construct {cid} not in dataframe")
        rmap = {_norm(k): v for k, v in RECODE_MAPS[token].items()}
        s = df_labeled[var].astype("object")
        vals = pd.Series([rmap.get(_norm(v), np.nan) for v in s], index=df_labeled.index, dtype=float)
        if vals.notna().sum() == 0:
            uniq = list(pd.unique(s.astype("object")))[:8]
            raise ValueError(f"{wave}/{cid} ({var}) recoded to all-NaN via {token}; "
                             f"sample labels seen: {uniq}")
        out[cid] = vals
    return pd.DataFrame(out)

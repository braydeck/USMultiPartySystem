"""Wave → data-path / weight-column / output-dir resolution (repo-relative)."""
from pathlib import Path

# repo root = three levels up from this file (.../analysis/efa/previous_years/common/)
ROOT = Path(__file__).resolve().parents[4]
CES = ROOT / "UNTRACKED" / "CES Data"
PY_DIR = ROOT / "analysis" / "efa" / "previous_years"
OUT = PY_DIR / "outputs"
CONFIG = PY_DIR / "config"

WAVES = ["2018", "2020", "2022", "2024"]
KIND = {"2018": "midterm", "2020": "presidential", "2022": "midterm", "2024": "presidential"}

_DTA = {
    "2018": CES / "2018" / "CCES18_Common_OUTPUT_vv_topost.dta",
    "2020": CES / "2020" / "CES20_Common_OUTPUT_vv.dta",
    "2022": CES / "2022" / "CCES22_Common_OUTPUT_vv_topost.dta",
    "2024": CES / "2024" / "CCES24_Common_OUTPUT_vv_topost_final (2).dta",
}

# All waves carry commonpostweight; the racial/gender items are post-survey, so
# listwise completion restricts to post-completers → commonpostweight is correct.
WEIGHT_COL = "commonpostweight"

# Validated-turnout scheme differs by wave (documented; not used in this deliverable).
TURNOUT = {
    "2018": "CL_2018gvm", "2020": "CL_2020gvm",
    "2022": "TS_g2022", "2024": "TS_g2024",
}


def dta_path(wave):
    return _DTA[wave]


def out_dir(wave):
    d = OUT / wave
    d.mkdir(parents=True, exist_ok=True)
    return d


def compare_dir():
    OUT.mkdir(parents=True, exist_ok=True)
    return OUT

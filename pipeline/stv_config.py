"""
stv_config.py
-------------
Shared constants for the 10-party STV simulation.
"""

from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).parent.parent
DTA_PATH       = BASE_DIR / "data" / "raw" / "2024 CES Base" / "CCES24_Common_OUTPUT_vv_topost_final.dta"
TYPOLOGY_PATH  = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
EFA_SCORES_PATH = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
OUTPUT_DIR     = BASE_DIR / "data" / "outputs" / "baseline"     # baseline STV run
SCENARIOS_ROOT = BASE_DIR / "data" / "outputs"                  # parent for all scenarios

# ── Party labels ───────────────────────────────────────────────────────────────
PARTY_LABELS = {
    0: "Conservative",
    1: "Labor",
    2: "Solidarity",
    3: "Nationalist",
    4: "Liberal",
    5: "Populist",
    6: "Civic Union Party",
    7: "Order and Opportunity Party",
    8: "DSA",
    9: "Progressive",
}
N_PARTIES  = 10
PROB_COLS  = [f"prob_cluster_{k}" for k in range(N_PARTIES)]

# All 10 clusters are active parties (C7 reintroduced as Order and Opportunity Party).
DISSOLVED_PARTIES = []

# ── The bill set ───────────────────────────────────────────────────────────────
# Every CES item the legislative model treats as a bill: something a chamber could hold a vote on.
# This list is the definition. It used to be whatever survived the "% Supporting CC24_*" filter,
# which meant the set was decided by whichever chamber profile happened to be oldest, and it
# silently widened whenever add_compare_items appended to cluster_stats.
#
# Deliberately excluded, because they measure a disposition rather than a proposition, and belong
# in the Parties policy comparison instead: the CC24_430a_* past-year behaviours, the CC24_420_*
# "would you use troops for…" hypotheticals, the CC24_443_* state-spending items (these chambers
# are federal), and the CC24_308a/b_* Ukraine and Israel/Gaza check-all batteries, whose options
# are mutually exclusive and so cannot all be live bills at once.
BILL_VARS = (
    # Taxes & economy
    "CC24_341a", "CC24_341b", "CC24_341c", "CC24_341d", "CC24_323f",
    # Immigration
    "CC24_323a", "CC24_323b", "CC24_323c", "CC24_323d", "CC24_340f",
    # Police & guns
    "CC24_321a", "CC24_321b", "CC24_321c", "CC24_321d", "CC24_321e", "CC24_321f",
    # Abortion & contraception
    "CC24_324b", "CC24_340a", "CC24_340b", "CC24_444c", "CC24_444d",
    # Civil liberties
    "CC24_340c", "CC24_340d", "CC24_340e",
    "CC24_444a", "CC24_444b", "CC24_444e", "CC24_444f",
    # Environment & climate
    "CC24_326a", "CC24_326b", "CC24_326c", "CC24_326d", "CC24_326e", "CC24_326f",
    # Healthcare & housing
    "CC24_328a", "CC24_328b", "CC24_328c", "CC24_328d", "CC24_328e",
)

# ── Items used for listwise deletion (replicates efa_update.py) ───────────────
ITEMS_25 = [
    "pew_churatd", "CC24_302",   "CC24_303",   "CC24_341a",  "CC24_341c",
    "CC24_341d",   "CC24_323a",  "CC24_323b",  "CC24_323d",  "CC24_321b",
    "CC24_321d",   "CC24_321e",  "CC24_325",   "CC24_324b",  "CC24_340a",
    "CC24_340b",   "CC24_340c",  "CC24_340e",  "CC24_340f",  "CC24_440b",
    "CC24_440c",   "CC24_421_1", "CC24_421_2", "CC24_423",   "CC24_424",
]
ITEMS_24 = [it for it in ITEMS_25 if it != "CC24_340a"]   # 24 items post-drop

# Columns to read from DTA (beyond ITEMS_24 which drive the deletion mask)
DTA_AUX_COLS = ["caseid", "faminc_new", "region", "urbancity", "commonpostweight"]
DTA_READ_COLS = DTA_AUX_COLS + ITEMS_24     # 29 columns total

# ── 2020 Census state populations (key = inputstate integer, FIPS-aligned) ────
# Source: 2020 Decennial Census apportionment counts
STATE_POPS = {
     1: 5024279,   # Alabama
     2:  733391,   # Alaska
     4: 7151502,   # Arizona
     5: 3011524,   # Arkansas
     6: 39538223,  # California
     8: 5773714,   # Colorado
     9: 3605944,   # Connecticut
    10:  989948,   # Delaware
    11:  689545,   # District of Columbia
    12: 21538187,  # Florida
    13: 10711908,  # Georgia
    15: 1455271,   # Hawaii
    16: 1839106,   # Idaho
    17: 12812508,  # Illinois
    18: 6785528,   # Indiana
    19: 3190369,   # Iowa
    20: 2937880,   # Kansas
    21: 4505836,   # Kentucky
    22: 4657757,   # Louisiana
    23: 1362359,   # Maine
    24: 6177224,   # Maryland
    25: 7029917,   # Massachusetts
    26: 10077331,  # Michigan
    27: 5706494,   # Minnesota
    28: 2961279,   # Mississippi
    29: 6154913,   # Missouri
    30: 1084225,   # Montana
    31: 1961504,   # Nebraska
    32: 3104614,   # Nevada
    33: 1377529,   # New Hampshire
    34: 9288994,   # New Jersey
    35: 2117522,   # New Mexico
    36: 20201249,  # New York
    37: 10439388,  # North Carolina
    38:  779094,   # North Dakota
    39: 11799448,  # Ohio
    40: 3959353,   # Oklahoma
    41: 4237256,   # Oregon
    42: 13002700,  # Pennsylvania
    44: 1097379,   # Rhode Island
    45: 5118425,   # South Carolina
    46:  886667,   # South Dakota
    47: 6910840,   # Tennessee
    48: 29145505,  # Texas
    49: 3271616,   # Utah
    50:  643077,   # Vermont
    51: 8631393,   # Virginia
    53: 7705281,   # Washington
    54: 1793716,   # West Virginia
    55: 5893718,   # Wisconsin
    56:  576851,   # Wyoming
}

POP_PER_SEAT = 380_000
POP_PER_SEAT_TRIPLE = 192_284   # Triple Wyoming: 576,851 / 3

# ── Census 2020 urban % by state FIPS ─────────────────────────────────────────
# Approximated from 2020 Census Urban and Rural Classification
# Represents % of state population in urbanized areas + urban clusters
STATE_URBAN_PCT = {
     1: 59.0,   # Alabama
     2: 66.0,   # Alaska
     4: 89.8,   # Arizona
     5: 56.2,   # Arkansas
     6: 95.0,   # California
     8: 86.2,   # Colorado
     9: 88.0,   # Connecticut
    10: 83.3,   # Delaware
    11: 100.0,  # District of Columbia
    12: 91.2,   # Florida
    13: 75.1,   # Georgia
    15: 91.9,   # Hawaii
    16: 70.6,   # Idaho
    17: 88.5,   # Illinois
    18: 72.4,   # Indiana
    19: 64.0,   # Iowa
    20: 61.1,   # Kansas
    21: 58.4,   # Kentucky
    22: 73.2,   # Louisiana
    23: 38.7,   # Maine
    24: 87.2,   # Maryland
    25: 92.0,   # Massachusetts
    26: 74.6,   # Michigan
    27: 73.3,   # Minnesota
    28: 50.2,   # Mississippi
    29: 70.4,   # Missouri
    30: 55.9,   # Montana
    31: 73.1,   # Nebraska
    32: 94.2,   # Nevada
    33: 60.3,   # New Hampshire
    34: 94.7,   # New Jersey
    35: 77.3,   # New Mexico
    36: 87.9,   # New York
    37: 66.1,   # North Carolina
    38: 59.9,   # North Dakota
    39: 77.9,   # Ohio
    40: 68.1,   # Oklahoma
    41: 81.1,   # Oregon
    42: 78.7,   # Pennsylvania
    44: 90.7,   # Rhode Island
    45: 66.3,   # South Carolina
    46: 56.5,   # South Dakota
    47: 66.4,   # Tennessee
    48: 84.7,   # Texas
    49: 90.6,   # Utah
    50: 38.9,   # Vermont
    51: 75.5,   # Virginia
    53: 84.0,   # Washington
    54: 48.7,   # West Virginia
    55: 70.2,   # Wisconsin
    56: 62.8,   # Wyoming
}

# ── CES urbancity → density tier ──────────────────────────────────────────────
# 1=City, 2=Suburb, 3=Town, 4=Rural, 5=Other/NA
URBANCITY_TO_TIER = {1: "URBAN", 2: "SUBURBAN", 3: "SUBURBAN", 4: "RURAL"}

# ── State FIPS → abbreviation (for readable output) ───────────────────────────
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

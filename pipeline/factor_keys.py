"""
factor_keys.py
--------------
The app's factor keys for the four-factor typology (ruled 2026-11-04).

  F1 Security & Order       = -FS_SO
  F2 Government Distrust    =  FS_TR
  F4 Cultural Conservatism  =  FS_RT
  F5 Economic Conservatism  = -FS_PC
  F3 retired (the app already hid it).

The raw SO and PC scores run high = liberal (each correlates -0.58 with ideo5), so the app keys
flip them so that high means the factor's name, as the five-factor keys did. Clustering and
ballots use the raw FS_RT/TR/SO/PC columns and are sign-invariant; anything that shows or
describes a factor position uses these keys.

efa_factor_scores.csv carries the keyed columns (FS_F1, FS_F2, FS_F4, FS_F5) next to the raw
ones; add_app_keys() writes them and check_orientation() guards the signs.
"""

import numpy as np

SOURCE = {"F1": ("FS_SO", -1), "F2": ("FS_TR", 1), "F4": ("FS_RT", 1), "F5": ("FS_PC", -1)}
KEYS = list(SOURCE)
SCORE_COLS = [f"FS_{k}" for k in KEYS]
CENTROID_COLS = {
    "F1": "F1_security_order",
    "F2": "F2_government_distrust",
    "F4": "F4_cultural_conservatism",
    "F5": "F5_economic_conservatism",
}
RAW_COLS = ["FS_RT", "FS_TR", "FS_SO", "FS_PC"]


def add_app_keys(df):
    """Return df with FS_F1/F2/F4/F5 derived from the raw columns."""
    out = df.copy()
    for k, (raw, sign) in SOURCE.items():
        out[f"FS_{k}"] = sign * out[raw]
    return out


def check_orientation(df):
    """Security & Order, cultural and economic conservatism must rise with self-placed conservatism."""
    d = df[df["ideo5"].between(1, 5)]
    for k in ("F1", "F4", "F5"):
        r = np.corrcoef(d[f"FS_{k}"], d["ideo5"])[0, 1]
        assert r > 0.3, f"FS_{k} runs the wrong way: r = {r:+.2f} with ideo5"

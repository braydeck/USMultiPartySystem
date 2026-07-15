#!/usr/bin/env python3
"""
compute_turnout_propensity.py
-----------------------------
Attach CES 2024 *validated* turnout (TS_g2024) to the EFA/cluster rows so the
simulation can weight each respondent by whether they actually voted.

Turnout definition (CES Specification 1, validated vote):
  voted := TS_g2024 in 1..6 (absentee/early/mail/polling/provisional/unknown-method).
  TS_g2024 == 7 means "matched but did not vote" (a registered non-voter), and a
  missing value means "not matched to the voter file"; both count as non-voters
  under Spec 1. (Per the CES vv guide: "any non-missing value below 7 = validated
  vote record.") Yields ~59% weighted national turnout.

Alignment is SELF-VERIFYING: we replicate efa_update.py's listwise-deletion
filter (notna on the 24 items + commonpostweight, original .dta order), then
assert pid3/inputstate/commonpostweight match efa_factor_scores.csv row-by-row
before trusting the join. No factor scores or clusters are recomputed.

Output: data/processed/turnout_propensity.csv
  caseid, voted (0/1), cluster, turnout_cluster (weighted cluster rate)
aligned 1:1 with efa_factor_scores.csv / typology_cluster_assignments.csv.
"""

import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR  = Path(__file__).parent.parent.parent
CES_PATH  = BASE_DIR / "data" / "raw" / "2024 CES Base" / "CCES24_Common_OUTPUT_vv_topost_final.dta"
PROC_DIR  = BASE_DIR / "data" / "processed"
FS_PATH   = PROC_DIR / "efa_factor_scores.csv"
CL_PATH   = PROC_DIR / "typology_cluster_assignments.csv"
OUT_PATH  = PROC_DIR / "turnout_propensity.csv"

# 24 EFA items (ITEMS_25 minus the dropped anchor CC24_340a) — must match efa_update.py
ITEMS_25 = [
    "pew_churatd", "CC24_302",   "CC24_303",   "CC24_341a",  "CC24_341c",
    "CC24_341d",   "CC24_323a",  "CC24_323b",  "CC24_323d",  "CC24_321b",
    "CC24_321d",   "CC24_321e",  "CC24_325",   "CC24_324b",  "CC24_340a",
    "CC24_340b",   "CC24_340c",  "CC24_340e",  "CC24_340f",  "CC24_440b",
    "CC24_440c",   "CC24_421_1", "CC24_421_2", "CC24_423",   "CC24_424",
]
ITEMS_24 = [it for it in ITEMS_25 if it != "CC24_340a"]


def main():
    print("Reading validated-vote + join keys from the CES .dta …")
    cols = ITEMS_24 + ["caseid", "pid3", "inputstate", "commonpostweight", "TS_g2024"]
    df = pd.read_stata(CES_PATH, columns=cols, convert_categoricals=False)
    print(f"  raw rows: {len(df):,}")

    # Replicate efa_update.py listwise deletion (24 items + weight), preserve order
    mask = df[ITEMS_24 + ["commonpostweight"]].notna().all(axis=1)
    dfc = df[mask].copy().reset_index(drop=True)
    print(f"  after listwise deletion: {len(dfc):,}")

    fs = pd.read_csv(FS_PATH)
    cl = pd.read_csv(CL_PATH)
    assert len(dfc) == len(fs) == len(cl), (
        f"row-count mismatch: dta={len(dfc)} fs={len(fs)} cl={len(cl)}")

    # ── VERIFY alignment before trusting the join ──────────────────────────
    assert (dfc["pid3"].values == fs["pid3"].values).all(), "pid3 mismatch — alignment broken"
    assert (dfc["inputstate"].values == fs["inputstate"].values).all(), "inputstate mismatch"
    assert np.allclose(dfc["commonpostweight"].values, fs["commonpostweight"].values), "weight mismatch"
    print("  ✓ alignment verified (pid3, inputstate, commonpostweight match row-by-row)")

    # ── Validated turnout (Spec 1) ────────────────────────────────────────
    # TS_g2024 codebook: 1 absentee, 2 early, 3 mail, 4 polling place, 5 provisional,
    # 6 voted-by-unknown-method, 7 DID NOT VOTE; missing = not matched to voter file.
    # "Any non-missing value below 7 = validated vote." So voted iff 1 <= TS_g2024 <= 6;
    # code 7 (matched non-voter) and missing (unmatched) are both non-voters under Spec 1.
    g = dfc["TS_g2024"].values
    voted = ((~np.isnan(g)) & (g <= 6)).astype(int)
    w = dfc["commonpostweight"].values
    print(f"\n  weighted national validated turnout: {np.average(voted, weights=w)*100:.1f}%")

    cluster = cl["cluster"].values.astype(int)
    rows = []
    print("\n  per-cluster validated turnout (weighted):")
    turnout_cluster = np.zeros(len(dfc))
    for k in sorted(set(cluster)):
        m = cluster == k
        rate = np.average(voted[m], weights=w[m])
        turnout_cluster[m] = rate
        rows.append((k, m.sum(), rate))
        print(f"    cluster {k}: n={m.sum():6d}  turnout={rate*100:5.1f}%")

    out = pd.DataFrame({
        "caseid": dfc["caseid"].values,
        "cluster": cluster,
        "voted": voted,
        "turnout_cluster": turnout_cluster,
    })
    out.to_csv(OUT_PATH, index=False)
    print(f"\n  ✓ wrote {OUT_PATH.relative_to(BASE_DIR)}  (N={len(out):,})")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
generate_candidate_profiles.py
--------------------------------
Party factor centroids: the weighted mean of each app factor key (pipeline/factor_keys.py:
F1 Security & Order, F2 Government Distrust, F4 Cultural Conservatism, F5 Economic
Conservatism) within each live party's hard cluster.

Inputs:
  data/processed/efa_factor_scores.csv           FS_F1/F2/F4/F5 + commonpostweight + caseid
  data/processed/typology_cluster_assignments.csv cluster + caseid (joined by caseid)

Output:
  data/outputs/candidate_factor_centroids.csv    one row per live party; candidate_code and
                                                 candidate_name are both the party code

The five-factor version also wrote candidate_stance_profiles.csv and eight senate-blend rows.
The stance table read item means of a retired clustering and nothing read either, so both
went with the nine-party rebuild (2026-11-04).
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE_DIR / "pipeline"))
from factor_keys import CENTROID_COLS  # noqa: E402
from party_codes import LEFT_RIGHT, PARTY_TO_CLUSTER  # noqa: E402

EFA_SCORES_PATH = BASE_DIR / "data" / "processed" / "efa_factor_scores.csv"
TYPOLOGY_PATH = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
OUT_PATH = BASE_DIR / "data" / "outputs" / "candidate_factor_centroids.csv"


def main():
    efa = pd.read_csv(EFA_SCORES_PATH)
    typ = pd.read_csv(TYPOLOGY_PATH, usecols=["caseid", "cluster"])
    df = efa.merge(typ, on="caseid", how="inner", validate="one_to_one")
    assert len(df) == len(efa) == len(typ), "typology and scores do not cover the same respondents"

    rows = []
    for party in LEFT_RIGHT:
        d = df[df["cluster"] == PARTY_TO_CLUSTER[party]]
        row = {"candidate_code": party, "candidate_name": party}
        for key, col in CENTROID_COLS.items():
            row[col] = round(float(np.average(d[f"FS_{key}"], weights=d["commonpostweight"])), 4)
        rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(OUT_PATH, index=False)
    print(out.to_string(index=False))
    print(f"wrote {OUT_PATH.relative_to(BASE_DIR)} ({len(out)} parties)")


if __name__ == "__main__":
    main()

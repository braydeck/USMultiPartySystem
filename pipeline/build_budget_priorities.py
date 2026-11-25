#!/usr/bin/env python3
"""
build_budget_priorities.py
--------------------------
The CES state-spending battery as Legislation-tab rows: viz/src/data/budgetPriorities.json.

CC24_443_1..5 ask whether the respondent's state legislature should increase or decrease spending
on welfare, health care, education, law enforcement, and transportation and infrastructure
(1 greatly increase, 2 slightly increase, 3 maintain, 4 slightly decrease, 5 greatly decrease).
A row's observedPct is the weighted share choosing 1 or 2, so "maintain" counts against, the
coding add_compare_items.py uses for the Parties tab. pYes is the candidate vote model's
prediction (candidate_vote_model.py): a weighted logit of the same 0/1 item on the four factor
scores, read at each party's centroid.

These are state spending preferences, not federal bills, so they stay out of stv_config.BILL_VARS,
candidateVoteModel.json and the 37-bill set that vote_agreement.py orders the parties on.
Rows carry the candidateVoteModel.json shape (variable, domain, question, parties[p].pYes /
observedPct / delta / diverges) plus category and overallPct, so CoalitionMap and passProbability
take them unchanged. House and Senate pass probabilities are computed client-side with
passProbability, as the tab does for MMP and reserve; nothing is baked.

Inputs   data/raw/2024 CES Base/CCES24_Common_OUTPUT_vv_topost_final.dta
         data/processed/typology_cluster_assignments.csv, efa_factor_scores.csv
         data/outputs/profiles/cluster_stats.csv   (gate: shares must match the Parties tab's)
Output   viz/src/data/budgetPriorities.json
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from party_codes import PARTY_TO_CLUSTER  # noqa: E402
from candidate_vote_model import (  # noqa: E402
    DIVERGENCE_THRESHOLD, DTA, EFA, FACTORS, TYPO, CLUSTER_STATS,
    fit_factor_logit, party_centroids, score_profile, wpct,
)

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "viz" / "src" / "data" / "budgetPriorities.json"
DOMAIN = "Budget"
ITEMS = [
    ("CC24_443_1", "Welfare", "Increase state spending on welfare"),
    ("CC24_443_2", "Health care", "Increase state spending on health care"),
    ("CC24_443_3", "Education", "Increase state spending on education"),
    ("CC24_443_4", "Law enforcement", "Increase state spending on law enforcement"),
    ("CC24_443_5", "Transportation & infrastructure", "Increase state spending on transportation & infrastructure"),
]
GATE_PP = 0.01


def main():
    vars_ = [v for v, _, _ in ITEMS]
    df = pd.read_stata(DTA, columns=["caseid", "commonpostweight"] + vars_, convert_categoricals=False)
    typo = pd.read_csv(TYPO)
    efa = pd.read_csv(EFA)
    dc = df.set_index("caseid").loc[typo.caseid.values].reset_index()  # CLAUDE.md trap 4
    assert len(dc) == len(typo) == len(efa) and (efa.caseid.values == typo.caseid.values).all()

    cl = typo["cluster"].values
    w = dc["commonpostweight"].values.astype(float)
    F = {f: efa[f].values.astype(float) for f in FACTORS}
    Fmat = np.column_stack([F[f] for f in FACTORS])
    centroids = party_centroids(F, w, cl)

    stats = pd.read_csv(CLUSTER_STATS).drop_duplicates("variable").set_index("variable")
    everyone = np.ones(len(dc), bool)
    rows = []
    for var, category, question in ITEMS:
        raw = dc[var].values.astype(float)
        y = np.where(np.isin(raw, [1, 2]), 1.0, np.where(np.isin(raw, [3, 4, 5]), 0.0, np.nan))
        beta, n_fit, pr2 = fit_factor_logit(y, w, Fmat)
        overall = wpct(y, w, everyone)
        assert abs(overall - stats.loc[var, "overall"]) <= GATE_PP, f"{var} overall drifted from cluster_stats"
        parties = {}
        for party, cluster in PARTY_TO_CLUSTER.items():
            obs = wpct(y, w, cl == cluster)
            assert abs(obs - stats.loc[var, f"c{cluster}"]) <= GATE_PP, f"{var} {party} drifted from cluster_stats"
            p_yes = score_profile(beta, centroids[party])
            delta = obs - p_yes * 100
            parties[party] = {"pYes": round(p_yes, 4), "observedPct": round(obs, 2),
                              "delta": round(delta, 2), "diverges": bool(abs(delta) >= DIVERGENCE_THRESHOLD)}
        rows.append({"variable": var, "domain": DOMAIN, "category": category, "question": question,
                     "overallPct": round(overall, 2), "n": n_fit, "pseudoR2": round(pr2, 4), "parties": parties})
        print(f"{var} {category:<32} overall {overall:5.1f}%  n {n_fit}  pseudo-R² {pr2:.3f}")

    OUT.write_text(json.dumps(rows, indent=2, allow_nan=False) + "\n")
    print(f"wrote {OUT.relative_to(BASE)} ({len(rows)} rows)")


if __name__ == "__main__":
    sys.exit(main())

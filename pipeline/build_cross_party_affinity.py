#!/usr/bin/env python3
"""
build_cross_party_affinity.py
-----------------------------
Cross-party acceptability, from the GMM cluster posterior in
data/processed/typology_cluster_assignments.csv (prob_cluster_0..9 + commonpostweight).

Each voter carries a full posterior over the ten parties. The argmax of that row is the
voter's first choice; the rest of the row is regard the voter holds for parties other than
the one they would rank first. Two directions of that regard, both in percentage points of
the electorate:

  received_k = Σ_{i: fc(i) != k}  P(k|i) · w_i / W · 100
  leaked_k   = Σ_{i: fc(i) == k}  (1 − P(k|i)) · w_i / W · 100
  net_k      = received_k − leaked_k

net_k is exactly the gap between party k's soft posterior share and its first-choice
(hard) share, asserted below:

  soft_share_k = Σ_i P(k|i) · w_i / W · 100
  hard_share_k = Σ_{i: fc(i) == k} w_i / W · 100
  net_k        = soft_share_k − hard_share_k

The 10×10 matrix `matrix[j][k]` gives the share of the electorate's posterior mass on
party k held by voters whose first choice is party j, so the card can name who finds each
party acceptable. Diagonal cells are the retained mass (j == k) and are reported
separately from the off-diagonal flows.

Weighting is commonpostweight only: this is a property of the typology, not of any single
turnout / ballot-depth configuration, so no turnout multiplier is applied.

Output: viz/src/data/crossPartyAffinity.json  (~6 KB, bundled at build time).
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).parent.parent
TYPO_PATH = BASE_DIR / "data" / "processed" / "typology_cluster_assignments.csv"
OUT_PATH = BASE_DIR / "viz" / "src" / "data" / "crossPartyAffinity.json"

PROB_COLS = [f"prob_cluster_{k}" for k in range(10)]
CLUSTER_TO_PARTY = {0: "CON", 1: "LBR", 2: "STY", 3: "NAT", 4: "LIB",
                    5: "POP", 6: "CUP", 7: "OAO", 8: "DSA", 9: "PRG"}
PARTIES = [CLUSTER_TO_PARTY[k] for k in range(10)]
F5_ORDER = ["PRG", "DSA", "LIB", "LBR", "OAO", "STY", "CUP", "CON", "POP", "NAT"]


def main():
    typ = pd.read_csv(TYPO_PATH)
    P = typ[PROB_COLS].values.astype(np.float64)
    w = typ["commonpostweight"].values.astype(np.float64)
    W = w.sum()
    fc = P.argmax(axis=1)

    # Rows are normalized posteriors by construction; hold the pipeline to it, since both
    # `leaked` and the row-sum identity below depend on Σ_k P(k|i) = 1.
    row_max_err = float(np.abs(P.sum(axis=1) - 1.0).max())
    assert row_max_err < 1e-6, f"posterior rows do not sum to 1 (max err {row_max_err:.2e})"

    soft = (P.T @ w) / W * 100.0                      # (10,) soft posterior share
    hard = np.array([w[fc == k].sum() for k in range(10)]) / W * 100.0

    received = np.zeros(10)
    leaked = np.zeros(10)
    for k in range(10):
        own = fc == k
        received[k] = (P[~own, k] * w[~own]).sum() / W * 100.0
        leaked[k] = ((1.0 - P[own, k]) * w[own]).sum() / W * 100.0
    net = received - leaked

    ident = float(np.abs(net - (soft - hard)).max())
    assert ident < 1e-9, f"net != soft − hard (max err {ident:.2e} pp)"

    # matrix[j][k] — electorate mass on party k held by first-choice-j voters.
    mass = np.zeros((10, 10))
    for j in range(10):
        own = fc == j
        mass[j] = (P[own].T @ w[own]) / W * 100.0
    col_err = float(np.abs(mass.sum(axis=0) - soft).max())
    assert col_err < 1e-9, f"matrix columns do not reproduce soft share (max err {col_err:.2e} pp)"
    row_err = float(np.abs(mass.sum(axis=1) - hard).max())
    assert row_err < 1e-9, f"matrix rows do not reproduce hard share (max err {row_err:.2e} pp)"

    idx = {p: PARTIES.index(p) for p in F5_ORDER}
    payload = {
        "order": F5_ORDER,
        "nVoters": int(len(typ)),
        "parties": {
            p: {
                "received": round(float(received[idx[p]]), 3),
                "leaked": round(float(leaked[idx[p]]), 3),
                "net": round(float(net[idx[p]]), 3),
                "softShare": round(float(soft[idx[p]]), 3),
                "hardShare": round(float(hard[idx[p]]), 3),
                "retained": round(float(mass[idx[p], idx[p]]), 3),
            }
            for p in F5_ORDER
        },
        # matrix[from][to] in F5 order; diagonal = retained mass.
        "matrix": {
            src: {dst: round(float(mass[idx[src], idx[dst]]), 4) for dst in F5_ORDER}
            for src in F5_ORDER
        },
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True))
    print(f"Wrote {OUT_PATH}  ({OUT_PATH.stat().st_size / 1024:.1f} KB)")
    print(f"n = {len(typ):,} voters · Σ commonpostweight = {W:,.1f}")
    print(f"validation — max |row sum − 1| = {row_max_err:.2e}; "
          f"max |net − (soft − hard)| = {ident:.2e} pp")

    print(f"\n{'party':<6}{'recv':>7}{'leak':>7}{'net':>7}{'soft':>8}{'hard':>8}")
    for p in sorted(F5_ORDER, key=lambda q: -net[idx[q]]):
        k = idx[p]
        print(f"{p:<6}{received[k]:>7.1f}{leaked[k]:>7.1f}{net[k]:>+7.1f}"
              f"{soft[k]:>8.2f}{hard[k]:>8.2f}")

    print("\nlargest off-diagonal flows (from -> to, pp of electorate):")
    flows = [(mass[idx[a], idx[b]], a, b) for a in F5_ORDER for b in F5_ORDER if a != b]
    for v, a, b in sorted(flows, reverse=True)[:10]:
        print(f"  {a} -> {b}  {v:.2f}")


if __name__ == "__main__":
    sys.exit(main())

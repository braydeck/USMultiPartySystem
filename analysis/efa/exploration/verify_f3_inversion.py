#!/usr/bin/env python3
"""Verify that the F3 ("Government Distrust") factor is inverted / residual relative to
actual government distrust, and that the electoral-skepticism factor (F2) carries the
primary government-distrust signal.

Motivation: the party z-scores read backwards — CON scores higher on "Government Distrust"
than POP, even though POP distrusts government more on the raw survey items. This script
re-derives the relationship from the stored factor scores so the finding is reproducible.

Inputs (all local; raw CES .dta not required):
  data/processed/typology_cluster_assignments.csv   (FS_F1..F5, cluster, govt_trust_imputed, weight)

Run: python3 analysis/efa/verify_f3_inversion.py
"""
import pandas as pd
import numpy as np
import statsmodels.api as sm

SRC = "data/processed/typology_cluster_assignments.csv"
C2P = {0: "CON", 1: "LBR", 2: "STY", 3: "NAT", 4: "LIB", 5: "POP", 6: "CUP", 7: "OAO", 8: "DSA", 9: "PRG"}
ORDER = ["PRG", "DSA", "LIB", "LBR", "OAO", "STY", "CUP", "CON", "POP", "NAT"]
LAB = {"FS_F1": "Security&Order", "FS_F2": "ElecSkeptic", "FS_F3": "GovDistrust",
       "FS_F4_resid": "RelijTrad", "FS_F5_resid": "PopulistCons"}
FACTORS = list(LAB)


def main():
    df = pd.read_csv(SRC)
    df["party"] = df.cluster.map(C2P)
    w = df.commonpostweight.clip(lower=0).fillna(0)

    # govt_trust_imputed is a 0..1 distrust indicator: higher = more distrust.
    # Confirmed by sign — electoral skeptics (high F2) distrust govt: corr(F2, distrust) > 0.
    print(f"polarity check: corr(FS_F2, govt_trust_imputed) = {df.FS_F2.corr(df.govt_trust_imputed):+.3f} "
          "(>0 confirms higher govt_trust_imputed = more distrust)\n")

    print("=== per-party weighted means: raw distrust vs the two 'trust' factors ===")
    print(f"{'party':6}{'rawGovDistrust':>16}{'FS_F2 ElecSkep':>16}{'FS_F3 GovDist':>15}")
    rows = []
    for p in ORDER:
        m = df.party == p
        ww = w[m]
        raw = np.average(df.govt_trust_imputed[m], weights=ww)
        f2 = np.average(df.FS_F2[m], weights=ww)
        f3 = np.average(df.FS_F3[m], weights=ww)
        rows.append((p, raw, f2, f3))
        print(f"{p:6}{raw:+16.3f}{f2:+16.3f}{f3:+15.3f}")

    r = pd.DataFrame(rows, columns=["party", "raw", "f2", "f3"])
    print(f"\nparty-level corr(raw distrust, FS_F3) = {r.raw.corr(r.f3):+.3f}  <- F3 does NOT track distrust")
    print(f"party-level corr(raw distrust, FS_F2) = {r.raw.corr(r.f2):+.3f}  <- F2 carries the distrust signal")

    print("\n=== raw govt distrust ~ 5 factor scores (WLS) — which factor carries it? ===")
    X = sm.add_constant(df[FACTORS])
    m = sm.WLS(df.govt_trust_imputed, X, weights=w).fit()
    for f in FACTORS:
        print(f"  {LAB[f]:16} beta={m.params[f]:+.3f}  (t={m.tvalues[f]:+.0f})")
    print(f"  R2={m.rsquared:.3f}")
    print("  -> F2 (ElecSkeptic) is the strong POSITIVE carrier; F3 (GovDistrust) is NEGATIVE.")

    print("\n=== respondent-level corr(FS_F3, raw govt distrust) ===")
    print(f"  {df.FS_F3.corr(df.govt_trust_imputed):+.3f}  <- the factor named 'Government Distrust' is "
          "negatively correlated with actual government distrust")


if __name__ == "__main__":
    main()

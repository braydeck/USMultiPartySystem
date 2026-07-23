#!/usr/bin/env python3
"""Adjacent-wave comparison of a prior wave against 2024 on the items they share
(more than the all-wave common set): factor congruence, where key items load, and
cluster comparison INCLUDING partisan makeup of matched clusters.

Usage:  python compare_pair.py 2020    # adds the police battery (shared 2020&2024)
        python compare_pair.py 2022    # adds government trust (shared 2022&2024)
"""
import sys, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import wave_pipeline as wp, crosswalk as cwmod, clustering as cl, congruence as cg, io_paths as io

BASE = ["relig_church", "econ_income", "imm_legalstatus", "imm_border", "gun_concealcarry",
        "abortion_rapeincest", "race_problemsrare", "race_whiteadv", "race_workedup",
        "race_slavery", "gender_womenpower"]
EXTRA = {"2020": ["police_increase", "police_decrease", "imm_dreamers"],  # security battery
         "2022": ["econ_price", "trust_fed", "trust_state"]}              # distrust battery
K = 4


def fit(wave, items):
    df, w, pid3, _ = wp.load_wave_items(wave, levels=cwmod.USABLE)
    return wp.fit_efa(df, w, pid3, items, K, wave, "pair", save=False)


def pid_mix(cluster, pid3, w, k):
    """Weighted Dem/Rep/Ind % within each cluster 0..k-1."""
    out = {}
    for c in range(k):
        m = cluster == c
        tot = w[m].sum()
        out[c] = {lab: 100 * w[m & (pid3 == v)].sum() / tot for lab, v in [("Dem", 1), ("Rep", 2), ("Ind", 3)]}
    return out


def main(prior):
    items = BASE + EXTRA[prior]
    print(f"=== {prior} vs 2024  ({len(items)} shared items, k={K}) ===")
    print("  " + ", ".join(items) + "\n")
    fa, f24 = fit(prior, items), fit("2024", items)
    print(f"  parallel analysis: {prior} k={fa['k_pa']}   2024 k={f24['k_pa']}\n")

    Sp, S24 = cg.structure_loadings(fa["L"], fa["Phi"]), cg.structure_loadings(f24["L"], f24["Phi"])
    print(f"2024 factor anchors:")
    for j in range(K):
        top = np.argsort(np.abs(S24[:, j]))[::-1][:3]
        print(f"  F{j+1}: " + ", ".join(f"{items[i]}({S24[i,j]:+.2f})" for i in top))
    print(f"\nTucker phi ({prior} matched to 2024):")
    for m in cg.match_factors(S24, Sp):
        print(f"  2024 F{m['factor_1']+1} <- {prior} F{m['factor_2']+1}  phi={m['phi']:+.3f}  {m['replication']}")

    # key-item location per wave
    keys = [x for x in ("police_increase", "police_decrease", "trust_fed", "trust_state") if x in items]
    if keys:
        print("\nkey-item primary factor:")
        for tag, S in [(prior, Sp), ("2024", S24)]:
            for it in keys:
                i = items.index(it); j = int(np.argmax(np.abs(S[i])))
                print(f"  {tag} {it}: F{j+1} ({S[i,j]:+.2f})")

    # ── cluster makeup comparison: match prior clusters to 2024 by centroid ──
    mapping, dists = cl.hungarian_match(fa["centroids"], f24["centroids"])
    pm_p = pid_mix(fa["cluster"], fa["pid3"], fa["w"], fa["n_eff"])
    pm_24 = pid_mix(f24["cluster"], f24["pid3"], f24["w"], f24["n_eff"])
    shp = [fa["w"][fa["cluster"] == c].sum() / fa["w"].sum() * 100 for c in range(fa["n_eff"])]
    sh24 = [f24["w"][f24["cluster"] == c].sum() / f24["w"].sum() * 100 for c in range(f24["n_eff"])]
    print(f"\nmatched clusters — share% and partisan makeup ({prior} vs its 2024 match):")
    print(f"  {'pri':>3} {'sh%':>5} {'D/R/I':>14}   ->  {'24':>3} {'sh%':>5} {'D/R/I':>14}   dist")
    for pc in sorted(range(fa["n_eff"]), key=lambda c: -shp[c]):
        rc = mapping.get(pc)
        if rc is None:
            continue
        pp, p24 = pm_p[pc], pm_24[rc]
        print(f"  c{pc:>2} {shp[pc]:>5.1f} {pp['Dem']:>4.0f}/{pp['Rep']:>3.0f}/{pp['Ind']:>3.0f}"
              f"   ->  c{rc:>2} {sh24[rc]:>5.1f} {p24['Dem']:>4.0f}/{p24['Rep']:>3.0f}/{p24['Ind']:>3.0f}"
              f"   {dists[pc]:.2f}")
    md = np.mean([dists[c] for c in range(fa["n_eff"]) if c in dists])
    print(f"  mean matched-centroid distance: {md:.2f} (z-scored factor space)")


if __name__ == "__main__":
    main(sys.argv[1])

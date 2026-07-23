#!/usr/bin/env python3
"""Dedicated 2022-vs-2024 comparison — the two waves share the most items, including
government trust (absent 2018/2020), so a distrust factor CAN be tested here.

Uses the full-sample shared set (excludes the split-sample white-privilege items and
the out-of-typology spending battery). Reports per-factor Tucker congruence and a
cluster comparison (2022 projected into 2024's space vs clustered independently).
"""
import sys, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import wave_pipeline as wp, crosswalk as cwmod, efa_math as em, clustering as cl, congruence as cg, io_paths as io

K = 4
# full-sample shared 2022&2024 constructs (excl. spending battery + split-sample 441e/f/g)
SHARED = ["relig_church", "econ_income", "econ_price", "imm_legalstatus", "imm_border",
          "gun_concealcarry", "abortion_rapeincest", "race_problemsrare", "race_whiteadv",
          "race_workedup", "race_slavery", "gender_womenpower", "trust_fed", "trust_state"]


def fit(wave):
    items_df, w, pid3, _ = wp.load_wave_items(wave, levels=cwmod.USABLE)
    return wp.fit_efa(items_df, w, pid3, SHARED, K, wave, "cmp2224", save=False)


def main():
    print(f"2022-vs-2024 shared full-sample items ({len(SHARED)}, incl. govt trust):")
    print("  " + ", ".join(SHARED) + "\n")
    f22, f24 = fit("2022"), fit("2024")

    # ── structural congruence, factor-matched ──
    S22 = cg.structure_loadings(f22["L"], f22["Phi"])
    S24 = cg.structure_loadings(f24["L"], f24["Phi"])
    print(f"2024 factor anchors (k={K}):")
    for j in range(K):
        top = np.argsort(np.abs(S24[:, j]))[::-1][:3]
        print(f"  F{j+1}: " + ", ".join(f"{SHARED[i]}({S24[i,j]:+.2f})" for i in top))
    print("\nTucker phi, 2022 factors matched to 2024:")
    for m in cg.match_factors(S24, S22):
        print(f"  2024 F{m['factor_1']+1} <- 2022 F{m['factor_2']+1}  phi={m['phi']:+.3f}  {m['replication']}")

    # is there a distrust factor? report where trust items load in each wave
    print("\ngovt-trust loading (primary factor) per wave:")
    for tag, f, S in [("2022", f22, S22), ("2024", f24, S24)]:
        for it in ("trust_fed", "trust_state"):
            i = SHARED.index(it); j = int(np.argmax(np.abs(S[i])))
            print(f"  {tag} {it}: F{j+1} ({S[i,j]:+.2f})")

    # ── cluster comparison: project 2022 into 2024 space, ARI vs independent ──
    enf, rel, val = f24["ident"]["enf"], f24["ident"]["rel"], f24["ident"]["val"]
    targets = [j for j in (rel, val) if j is not None and j != enf]
    ref_model, ref_raw, _ = cl.dpgmm_fit(f24["Xc"])
    ref_cluster, ref_size = cl.remap_by_weighted_n(ref_raw, f24["w"], ref_model.weights_)
    comp_to_id = {orig: new for new, orig in enumerate(ref_size)}
    Zref = (f24["_Xitems"] - f24["mu"]) / f24["sig"]
    net_sign = np.sign((f24["F"] * (Zref @ f24["B"])).sum(0)); net_sign[net_sign == 0] = 1
    W = f24["w"] / f24["w"].mean(); Xd = np.column_stack([np.ones_like(f24["F"][:, enf]), f24["F"][:, enf]])
    betas = {j: np.linalg.solve((Xd.T * W) @ Xd, (Xd.T * W) @ f24["F"][:, j]) for j in targets}

    Z = (f22["_Xitems"] - f24["mu"]) / f24["sig"]
    F = (Z @ f24["B"]) * net_sign
    Xc = F.copy()
    for j in targets:
        a, b = betas[j]; Xc[:, j] = F[:, j] - (a + b * F[:, enf])
    proj = np.array([comp_to_id.get(c, -1) for c in ref_model.predict_proba(Xc).argmax(1)])
    ari = cl.ari(f22["cluster"], proj)
    neff24 = int((ref_model.weights_ > 0.01).sum())
    sh_ind = np.sort([f22["w"][f22["cluster"] == k].sum() / f22["w"].sum() * 100 for k in range(f22["n_eff"])])[::-1]
    sh_prj = np.sort([f22["w"][proj == k].sum() / f22["w"][proj >= 0].sum() * 100 for k in range(neff24)])[::-1]
    print(f"\ncluster comparison (2022 vs 2024, {SHARED and len(SHARED)}-item shared space):")
    print(f"  effective clusters: 2022={f22['n_eff']}  2024={neff24}")
    print(f"  ARI(2022 independent vs 2022-projected-into-2024): {ari:.3f}")
    print(f"  2022 independent sorted shares: {np.round(sh_ind,1)}")
    print(f"  2022 projected  sorted shares: {np.round(sh_prj,1)}")


if __name__ == "__main__":
    main()

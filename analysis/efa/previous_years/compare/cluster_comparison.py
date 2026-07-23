#!/usr/bin/env python3
"""Cross-wave cluster comparison on the common (F1/F4/F5) space.

Two views:
  (A) Independent — each wave's own common-fit DPGMM; clusters matched to 2024's
      common clusters by Hungarian nearest-centroid; report effective-k, share
      drift, and centroid drift.
  (B) 2024 prior-lens — project each prior wave's common items into 2024's factor
      space (2024 mu/sig/B + 2024 residualization betas), assign via the 2024
      reference DPGMM (refit seed=42); report projected shares and ARI vs (A).

Emits outputs/cluster_drift.csv and outputs/priorlens_shares.csv.
"""
import sys, pickle, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import io_paths as io, clustering as cl, efa_math as em


def load_common(wave):
    with open(io.out_dir(wave) / "fit_results.pkl", "rb") as f:
        return pickle.load(f)["common"]


def shares(cluster, w, n):
    return np.array([w[cluster == k].sum() / w[cluster >= 0].sum() * 100 for k in range(n)])


def resid_betas(F, enf, targets, w):
    """Weighted-OLS betas (a,b) regressing each target factor on the enf factor."""
    betas = {}
    W = w / w.mean()
    Xd = np.column_stack([np.ones_like(F[:, enf]), F[:, enf]])
    XtW = Xd.T * W
    for j in targets:
        a, b = np.linalg.solve(XtW @ Xd, XtW @ F[:, j])
        betas[j] = (a, b)
    return betas


def main():
    fits = {w: load_common(w) for w in io.WAVES}
    ref = fits["2024"]
    ref_cent = ref["centroids"]
    ref_neff = ref["n_eff"]

    # -------- (A) independent: match each wave's clusters to 2024 --------
    print("=== (A) INDEPENDENT common-space DPGMM, matched to 2024 ===")
    drift_rows = []
    ref_self = {k: v for k, v in zip(range(ref_neff), shares(ref["cluster"], ref["w"], ref_neff))}
    for w in io.WAVES:
        f = fits[w]
        mapping, dists = cl.hungarian_match(f["centroids"], ref_cent)  # wave cl -> 2024 cl
        sh = shares(f["cluster"], f["w"], f["n_eff"])
        print(f"\n-- {w} ({io.KIND[w]}): effective clusters={f['n_eff']} (2024={ref_neff}) --")
        for wc in range(f["n_eff"]):
            rc = mapping.get(wc)
            drift_rows.append({"wave": w, "kind": io.KIND[w], "wave_cluster": wc,
                               "matched_2024_cluster": rc,
                               "match_dist": round(dists.get(wc, np.nan), 3),
                               "wave_share_pct": round(sh[wc], 2),
                               "ref2024_share_pct": round(ref_self.get(rc, np.nan), 2)})
            print(f"   wave cl{wc} ({sh[wc]:4.1f}%) -> 2024 cl{rc} "
                  f"({ref_self.get(rc, float('nan')):4.1f}%)  dist={dists.get(wc, np.nan):.2f}")
    pd.DataFrame(drift_rows).to_csv(io.compare_dir() / "cluster_drift.csv", index=False)
    print("\nsaved outputs/cluster_drift.csv")

    # -------- (B) 2024 prior-lens projection --------
    print("\n=== (B) 2024 PRIOR-LENS projection ===")
    # 2024 reference model refit (deterministic seed=42) on 2024 common residualized space
    ref_model, ref_raw, _ = cl.dpgmm_fit(ref["Xc"])
    ref_cluster, ref_size = cl.remap_by_weighted_n(ref_raw, ref["w"], ref_model.weights_)
    ref_neff_b = int((ref_model.weights_ > 0.01).sum())
    # map raw component -> remapped id for predict_proba columns
    comp_to_id = {orig: new for new, orig in enumerate(ref_size)}

    enf = ref["ident"]["enf"]; rel = ref["ident"]["rel"]; val = ref["ident"]["val"]
    targets = [j for j in (rel, val) if j is not None and j != enf]
    betas = resid_betas(ref["F"], enf, targets, ref["w"])
    # reconstruct the net per-factor sign flips the 2024 fit applied (base + partisan),
    # so projected scores land in the same oriented space the ref model was trained on.
    Zref = (ref["_Xitems"] - ref["mu"]) / ref["sig"]
    net_sign = np.sign((ref["F"] * (Zref @ ref["B"])).sum(0))
    net_sign[net_sign == 0] = 1.0

    def project(wave_fit):
        # raw (recoded) common items for this wave, listwise-complete rows used in its fit
        X = wave_fit["_Xitems"]
        w = wave_fit["w"]
        Z = (X - ref["mu"]) / ref["sig"]  # standardize into 2024 metric
        F = (Z @ ref["B"]) * net_sign     # 2024 scoring coefficients + 2024 sign flips
        Xc = F.copy()
        for j in targets:
            a, b = betas[j]
            Xc[:, j] = F[:, j] - (a + b * F[:, enf])
        proba = ref_model.predict_proba(Xc)
        raw = proba.argmax(1)
        # remap to id space, keep only effective
        lab = np.array([comp_to_id.get(c, -1) for c in raw])
        return lab, w

    pl_rows = []
    ref_shares_b = shares(ref_cluster, ref["w"], ref_neff_b)
    for w in io.WAVES:
        f = fits[w]
        lab, ww = project(f)
        sh = np.array([ww[lab == k].sum() / ww[lab >= 0].sum() * 100 for k in range(ref_neff_b)])
        a = cl.ari(f["cluster"], lab)  # independent vs projected (same respondents)
        print(f"-- {w}: projected shares vs 2024 ref; ARI(indep,proj)={a:.3f}")
        for k in range(ref_neff_b):
            pl_rows.append({"wave": w, "kind": io.KIND[w], "ref2024_cluster": k,
                            "projected_share_pct": round(sh[k], 2),
                            "ref2024_share_pct": round(ref_shares_b[k], 2),
                            "ari_indep_vs_proj": round(a, 3)})
    pd.DataFrame(pl_rows).to_csv(io.compare_dir() / "priorlens_shares.csv", index=False)
    print("saved outputs/priorlens_shares.csv")


if __name__ == "__main__":
    main()

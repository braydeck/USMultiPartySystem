#!/usr/bin/env python3
"""Cross-wave structural congruence (Tucker's phi) on the common-subset EFA.

Compares each wave's common-fit structure loadings (S = L @ Phi) against 2024's,
factor-matched via Hungarian on 1-|phi|. Emits outputs/congruence_matrix.csv.
"""
import sys, pickle, warnings
warnings.filterwarnings("ignore")
from pathlib import Path
import numpy as np, pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import io_paths as io, congruence as cg, efa_math as em


def load_common(wave):
    with open(io.out_dir(wave) / "fit_results.pkl", "rb") as f:
        return pickle.load(f)["common"]


def sign_first(L):
    """Orient a single-factor loading vector so its largest |loading| is positive."""
    return L * (1 if L[np.argmax(np.abs(L))] >= 0 else -1)


def main():
    fits = {w: load_common(w) for w in io.WAVES}
    base_items = fits["2024"]["item_ids"]
    for w in io.WAVES:
        assert fits[w]["item_ids"] == base_items, f"{w} item order differs"
    print(f"common-subset items ({len(base_items)}): {base_items}")
    labelmap = {i: it for i, it in enumerate(base_items)}

    # ── headline: rotation-free k=1 dominant-factor congruence (from stored R) ──
    print("\n=== [A] k=1 DOMINANT-DIMENSION congruence (rotation-free) ===")
    domL = {}
    for w in io.WAVES:
        L1, _, _ = em.paf(em.regularize_corr(fits[w]["R"].copy()), 1)
        domL[w] = sign_first(L1[:, 0])
    print("2024 dominant dimension (conservatism) item loadings:")
    for i in np.argsort(-np.abs(domL["2024"])):
        print(f"    {base_items[i]:20} {domL['2024'][i]:+.2f}")
    head_rows = []
    print("\n  wave    Tucker phi vs 2024   replication")
    for w in io.WAVES:
        phi = cg.tucker_phi(domL["2024"], domL[w])
        lab = ("identical" if abs(phi) >= cg.IDENTICAL else "fair" if abs(phi) >= cg.FAIR else "did-not-replicate")
        print(f"  {w} ({io.KIND[w][:4]})   {phi:+.3f}              {lab}")
        head_rows.append({"comparison": "k1_dominant", "wave": w, "kind": io.KIND[w],
                          "ref_factor": "dom", "matched_factor": "dom",
                          "tucker_phi": round(phi, 4), "replication": lab})

    # ── rotated multi-factor structure congruence (factor-matched) ──
    kc = fits["2024"]["k"]
    print(f"\n=== [B] ROTATED structure-loading congruence, k={kc} (Hungarian-matched) ===")
    S = {w: cg.structure_loadings(fits[w]["L"], fits[w]["Phi"]) for w in io.WAVES}
    ref = S["2024"]
    print(f"2024 k={kc} common-factor anchors:")
    for j in range(ref.shape[1]):
        top = np.argsort(np.abs(ref[:, j]))[::-1][:3]
        print(f"  F{j+1}: " + ", ".join(f"{labelmap[i]}({ref[i,j]:+.2f})" for i in top))
    k2_rows = []
    for w in io.WAVES:
        for m in cg.match_factors(ref, S[w]):
            k2_rows.append({"comparison": "k2_rotated", "wave": w, "kind": io.KIND[w],
                            "ref_factor": f"F{m['factor_1']+1}",
                            "matched_factor": f"F{m['factor_2']+1}",
                            "tucker_phi": m["phi"], "replication": m["replication"]})
        row = [x for x in k2_rows if x["wave"] == w]
        print(f"  {w}: " + "  ".join(f"{r['ref_factor']}<-{r['matched_factor']} phi={r['tucker_phi']:+.2f}({r['replication'][:4]})" for r in row))

    pd.DataFrame(head_rows + k2_rows).to_csv(io.compare_dir() / "congruence_matrix.csv", index=False)
    print("\nsaved outputs/congruence_matrix.csv")


if __name__ == "__main__":
    main()

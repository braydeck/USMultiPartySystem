"""How strong is each dimension? Production's 24 items vs the rule-screened pools (item_pool.py).

Data: CES 2024, pairwise polychoric matrices on the 49,432 post-weighted respondents (outputs/polychoric_pairwise.csv
for the 24; outputs/item_pool/polychoric_pairwise_all.csv for the pools); item sets and factor names from
outputs/item_pool/<arm>_loadings.csv and <arm>_bridge.csv. PAF + oblimin refit at each arm's k (deterministic).

Two measures per factor:
  share of explained variance  SS of pattern loadings / sum over factors (production's efa_variance_summary.csv
                               measure, normalized so pools with different item counts compare)
  determinacy                  correlation between the factor and its best score estimate, sqrt(diag(S' R^-1 S)),
                               S = L Phi. Near 1 = sharply pinned down by its items; below ~0.8 = loosely defined.
Writes outputs/factor_strength.csv.
"""
import numpy as np
import pandas as pd

import reestimate_loadings as rl

OUT = rl.OUT
NEW = {"main": {}, "fpmain": {}}


def measures(R, L, Phi):
    ss = (L ** 2).sum(axis=0)
    S = L @ Phi
    det = np.sqrt(np.clip(np.diag(S.T @ np.linalg.solve(R, S)), 0, 1))
    primary = np.abs(L).argmax(axis=1)
    return ss / ss.sum(), det, np.bincount(primary, minlength=L.shape[1])


def main():
    rows = []
    L_final = pd.read_csv(rl.ROOT / "analysis/efa/efa_loadings_k5_final.csv", index_col=0).loc[rl.ITEMS, ["F1", "F2", "F3", "F4", "F5"]].values
    R = rl.em.regularize_corr(rl.poly(None, None, OUT / "polychoric_pairwise.csv"))
    L, Phi, _ = rl.align(L_final, *rl.fit(R))
    share, det, n = measures(R, L, Phi)
    for j, nm in enumerate(rl.NAMES):
        rows.append({"arm": "production 24", "factor": nm, "items": n[j], "share": share[j], "determinacy": det[j]})

    Rall = pd.read_csv(OUT / "item_pool/polychoric_pairwise_all.csv", index_col=0)
    for arm in ("main", "fpmain", "fp24"):
        ld = pd.read_csv(OUT / f"item_pool/{arm}_loadings.csv", index_col=0)
        fn = [c for c in ld.columns if c.startswith("N")]
        names = [c.split("(")[1].rstrip(")") for c in pd.read_csv(OUT / f"item_pool/{arm}_bridge.csv", index_col=0).columns]
        items = list(ld.index)
        Ra = rl.em.regularize_corr(Rall.loc[items, items].values.copy())
        L_un, _, _ = rl.em.paf(Ra, len(fn))
        La, Pa = rl.em.oblimin(L_un)
        # same solution as item_pool.py up to sign; match columns by |loading| correlation to the saved ones
        Ls = ld[fn].values
        order = [int(np.argmax([abs(np.corrcoef(Ls[:, j], La[:, b])[0, 1]) for b in range(len(fn))])) for j in range(len(fn))]
        assert len(set(order)) == len(fn)
        La, Pa = La[:, order], Pa[np.ix_(order, order)]
        share, det, n = measures(Ra, La, Pa)
        top = [", ".join(ld[fn[j]].abs().sort_values(ascending=False).index[:3]) for j in range(len(fn))]
        for j in range(len(fn)):
            rows.append({"arm": arm, "factor": names[j], "items": n[j], "share": share[j], "determinacy": det[j], "top_items": top[j]})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "factor_strength.csv", index=False)
    pd.set_option("display.width", 200)
    for arm, g in out.groupby("arm", sort=False):
        print(f"\n{arm}\n", g.drop(columns="arm").sort_values("share", ascending=False).round(3).to_string(index=False))


if __name__ == "__main__":
    main()

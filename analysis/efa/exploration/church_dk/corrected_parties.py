"""What do the ten parties look like when respondents are scored with correct item coding?

Data: CES 2024 Common Content DTA, label-based canonical recode
(analysis/efa/previous_years/wave_2024/reproduce_gate.py), 45,214 respondents (production's
45,707 minus the 493 church "Don't know"); production parties joined by position
(data/processed/typology_cluster_assignments.csv). Factor model held at production: frozen
polychoric matrix and k=5 loadings/Phi (analysis/efa/efa_loadings_k5_final.csv,
efa_phi_k5_final.csv), which were always label-coded. Only the scoring changes.

Chain after scoring is production's: sign-align, Republican-higher flip on the enforcement /
religion / values factors, religion and values residualized on enforcement, 10-component DPGMM.
Seeds 42-46, because the agent's refits found an alternate DPGMM solution at some seeds.
Each corrected cluster is labeled with a production party by Hungarian match on the weighted
crosstab.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "analysis" / "validation" / "anes"))
import matched_clustering as mc  # noqa: E402
from common import clustering as cl  # noqa: E402
from common import efa_math as em  # noqa: E402

OUT = Path(__file__).parent / "outputs"
FACTORS = ["Security & Order", "Institutional Distrust", "Government Distrust",
           "Religious Traditionalism", "Populist Conservatism"]
PARTIES = cl.PARTY_CODES
SEEDS = (42, 43, 44, 45, 46)


def corrected_space(ces):
    I = mc.rg.ITEMS
    R = pd.read_csv(ROOT / "data/processed/polychoric_matrix.csv", index_col=0).loc[I, I].values
    R = (R + R.T) / 2
    L = pd.read_csv(ROOT / "analysis/efa/efa_loadings_k5_final.csv", index_col=0).loc[I, ["F1", "F2", "F3", "F4", "F5"]].values
    Phi = pd.read_csv(ROOT / "analysis/efa/efa_phi_k5_final.csv", index_col=0).values
    w, pid3 = ces.w.values, ces.pid3.values
    Z, _, _ = em.weighted_standardize(ces[I].values.astype(float), w)
    F, _ = em.thomson_scores(Z, R, L, Phi)
    F, L = em.sign_align_by_loading(F, L)
    enf, rel, val = (int(np.argmax(np.abs(L[I.index(a)]))) for a in mc.ANCHORS)
    dem, rep = pid3 == 1, pid3 == 2
    for j in (enf, rel, val):
        if np.average(F[rep, j], weights=w[rep]) < np.average(F[dem, j], weights=w[dem]):
            F[:, j] *= -1
    X = F.copy()
    for j in (rel, val):
        X[:, j] = em.wresid(F[:, j], F[:, enf], w)
    return F, X


def label_by_crosstab(cluster, party, w):
    ct = pd.crosstab(cluster, party, values=w, aggfunc="sum").fillna(0)
    ri, ci = linear_sum_assignment(-ct.values / ct.values.sum(axis=0, keepdims=True))
    return {int(ct.index[r]): int(ct.columns[c]) for r, c in zip(ri, ci)}, ct


def main():
    ces = mc.load_ces()
    w, pid3, party = ces.w.values, ces.pid3.values, ces.party.values
    F, X = corrected_space(ces)
    print(f"n = {len(ces):,}")

    runs = {}
    for seed in SEEDS:
        model, raw, _ = cl.dpgmm_fit(X, seed=seed)
        runs[seed], _ = cl.remap_by_weighted_n(raw, w, model.weights_)
    seed_ari = pd.DataFrame([[cl.ari(runs[a], runs[b]) for b in SEEDS] for a in SEEDS], index=SEEDS, columns=SEEDS).round(3)
    print("\nARI between seeds:\n", seed_ari)
    seed_ari.to_csv(OUT / "corrected_seed_ari.csv")

    rows = []
    for seed, clu in runs.items():
        lab, ct = label_by_crosstab(clu, party, w)
        for c, p in lab.items():
            m_new, m_old = clu == c, party == p
            rows.append({
                "seed": seed, "party": PARTIES[p],
                "old_share": w[m_old].sum() / w.sum(), "new_share": w[m_new].sum() / w.sum(),
                "retained": w[m_old & m_new].sum() / w[m_old].sum(),
                "new_cluster_from_party": w[m_old & m_new].sum() / w[m_new].sum(),
                "old_dem": np.average(pid3[m_old] == 1, weights=w[m_old]), "new_dem": np.average(pid3[m_new] == 1, weights=w[m_new]),
                "old_rep": np.average(pid3[m_old] == 2, weights=w[m_old]), "new_rep": np.average(pid3[m_new] == 2, weights=w[m_new]),
                **{f"new_{f}": np.average(X[m_new, j], weights=w[m_new]) for j, f in enumerate(FACTORS)},
            })
        print(f"seed {seed}: ARI vs production {cl.ari(clu, party):.3f}")
    res = pd.DataFrame(rows).round(3)
    res.to_csv(OUT / "corrected_parties_by_seed.csv", index=False)

    main_seed = 42
    r = res[res.seed == main_seed].set_index("party").loc[PARTIES]
    pd.set_option("display.width", 220)
    print(f"\nSeed {main_seed}, each production party vs its matched corrected cluster:")
    print(r[["old_share", "new_share", "retained", "new_cluster_from_party", "old_dem", "new_dem", "old_rep", "new_rep"]].to_string())
    print("\nCorrected-cluster factor means (residualized space; religion and populism net of security):")
    print(r[[f"new_{f}" for f in FACTORS]].rename(columns=lambda c: c[4:]).to_string())
    spread = res.groupby("party")[["new_share", "retained"]].agg(["min", "max"]).round(3).loc[PARTIES]
    print("\nRange across seeds 42-46:\n", spread.to_string())
    spread.to_csv(OUT / "corrected_parties_seed_range.csv")


if __name__ == "__main__":
    main()

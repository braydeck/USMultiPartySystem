"""Design-based bootstrap intervals for the matched-EFA Tucker phi values.

Data: as in matched_efa.py (ANES 2024 matched set, n = 3,796; CES 2024 polychoric subset).
Rao-Wu rescaling bootstrap: within each stratum (V240108d) with n_h PSUs (V240108c), draw
n_h - 1 PSUs with replacement and rescale weights by n_h / (n_h - 1) x times drawn. Each
replicate refits the ANES polychoric -> PAF -> oblimin and re-matches factors by Hungarian,
so the interval includes factor-matching instability. CES is held fixed (n = 45,707, its
sampling error is small next to ANES's). 500 replicates, seed 42.
"""
import sys

import numpy as np
import pandas as pd

import matched_efa as me
from common import congruence as cg
from common import efa_math as em

N_REP, SEED, KS = 500, 42, (3, 5)


def rao_wu_weights(psu, stratum, w, rng):
    out = np.zeros_like(w)
    for h in np.unique(stratum):
        in_h = stratum == h
        psus = np.unique(psu[in_h])
        n_h = len(psus)
        if n_h < 2:
            out[in_h] = w[in_h]
            continue
        draws = rng.choice(psus, size=n_h - 1, replace=True)
        counts = pd.Series(draws).value_counts()
        mult = np.array([counts.get(p, 0) for p in psu[in_h]])
        out[in_h] = w[in_h] * (n_h / (n_h - 1)) * mult
    return out


def phi_by_ces_factor(L_ref, L_new, names):
    return {names[m["factor_1"]]: abs(m["phi"]) for m in cg.match_factors(L_ref, L_new)}


def main():
    raw, items, cw = me.rm.load_matched()
    ids = list(items.columns)
    w = raw[me.rm.WEIGHT].values.astype(float)
    mask = items.notna().all(axis=1).values & ~np.isnan(w) & (w > 0)
    D = items[mask].reset_index(drop=True)
    w0 = w[mask]
    psu = raw[me.rm.PSU].values[mask]
    stratum = raw[me.rm.STRATUM].values[mask]

    R_ces = em.regularize_corr(pd.read_csv(me.CES_R, index_col=0).loc[ids, ids].values)
    L_can = pd.read_csv(me.CES_L, index_col=0).loc[ids, list(me.CES_NAMES)].values
    refs = {}
    for k in KS:
        L_c, _, _ = me.fit(R_ces, k)
        canon = cg.match_factors(L_can, L_c)
        nm = {m["factor_2"]: list(me.CES_NAMES.values())[m["factor_1"]] for m in canon}
        refs[k] = (L_c, [nm.get(j, f"C{j + 1}") for j in range(k)])

    rng = np.random.default_rng(SEED)
    rows = []
    for rep in range(N_REP):
        wr = rao_wu_weights(psu, stratum, w0, rng)
        keep = wr > 0
        R = em.regularize_corr(em.polychoric_matrix(D[keep].reset_index(drop=True), ids, wr[keep], progress=False))
        for k in KS:
            L_a, _, _ = me.fit(R, k)
            L_c, names = refs[k]
            for f, phi in phi_by_ces_factor(L_c, L_a, names).items():
                rows.append({"rep": rep, "k": k, "reference": "ces18", "factor": f, "phi": phi})
            if k == 5:
                for f, phi in phi_by_ces_factor(L_can, L_a, list(me.CES_NAMES.values())).items():
                    rows.append({"rep": rep, "k": k, "reference": "canonical", "factor": f, "phi": phi})
        if (rep + 1) % 50 == 0:
            print(f"  {rep + 1}/{N_REP}", flush=True)

    reps = pd.DataFrame(rows)
    reps.to_csv(me.OUT / "bootstrap_phi_reps.csv", index=False)
    summ = (reps.groupby(["k", "reference", "factor"]).phi
            .agg(median="median", lo=lambda s: s.quantile(0.025), hi=lambda s: s.quantile(0.975),
                 p_fair=lambda s: (s >= cg.FAIR).mean(), p_identical=lambda s: (s >= cg.IDENTICAL).mean())
            .round(3).reset_index())
    summ.to_csv(me.OUT / "bootstrap_phi_summary.csv", index=False)
    print(summ.to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())

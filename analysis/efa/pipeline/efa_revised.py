"""Production factor scores under the revised §3c rule (the nine-party typology, ruled 2026-11-04).

Replaces efa_update.py (24 items, five factors) as the writer of data/processed/efa_factor_scores.csv. The rule and
its full run live in analysis/efa/exploration/listwise_check/stage_c_v2.py; this script applies that run's fixed
result, it does not re-select items or factors:
  items     the 41 retained items (listwise_check/outputs/stage_c_v2/loadings.csv)
  loadings  PAF k = 5 + oblimin on the weighted pairwise polychoric over all post-weighted respondents, aligned by
            Tucker phi to the listwise fit in loadings.csv
  factors   the four that pass the entry test (factors.csv `enters`): RT cultural conservatism, TR distrust of
            government, SO security & order, PC economic right
  scoring   available-item scores (eligible = answered at least half of each entering factor's primary items);
            no residualization (dropped 2026-11-04); §3c step 7 in-power adjustment (opposed and split contrasts
            of state-government alignment removed, nonpartisan difference kept)
Data: CES 2024 Common Content (efa_update.CES_PATH), weight commonpostweight.
Check: the scores must match listwise_check/outputs/stage_c_v2/scores.csv (r = 1 on every factor); the script stops
otherwise.
Writes data/processed/efa_factor_scores.csv: pid3, ideo5, inputstate, commonpostweight, FS_RT, FS_TR, FS_SO, FS_PC,
the app keys FS_F1, FS_F2, FS_F4, FS_F5 (pipeline/factor_keys.py), caseid (49,431 rows, one per eligible respondent).
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
ROOT = Path(__file__).resolve().parents[3]
LW = ROOT / "analysis/efa/exploration/listwise_check"
sys.path.insert(0, str(LW))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import item_pool as ip  # noqa: E402
import reestimate_loadings as rl  # noqa: E402
import rescore_refit as rr  # noqa: E402
import stage_c_v2 as v2  # noqa: E402
import state_control as stc  # noqa: E402

sys.path.insert(0, str(ROOT / "pipeline"))
import factor_keys as fk  # noqa: E402

em = rl.em
V2 = LW / "outputs/stage_c_v2"
OUT = ROOT / "data/processed/efa_factor_scores.csv"
ORDER = ["RT", "TR", "SO", "PC"]


def main():
    X, w, pid, caseid = ip.load()
    fac = pd.read_csv(V2 / "factors.csv")
    enter = [int(j) for j in fac.factor[fac.enters]]
    sn = v2.roles(dict(zip(fac.factor, fac.name)), enter)
    lw = pd.read_csv(V2 / "loadings.csv", index_col=0)
    items = list(lw.index)
    Rp = v2.reg(ip.poly_all(X, w).loc[items, items].values, items)
    Lp, Pp = em.oblimin(em.paf(Rp.values.copy(), len(fac))[0])
    Lp, Pp, phi = rl.align(lw[[f"F{j}" for j in range(len(fac))]].values, Lp, Pp)
    primary = np.abs(Lp).argmax(axis=1)
    Xv = X[items].values.astype(float)
    answered = np.column_stack([(~np.isnan(Xv[:, primary == j])).mean(axis=1) for j in enter])
    elig = (answered >= rr.MIN_SHARE_PER_FACTOR).all(axis=1)
    F, _ = rr.available_scores(Xv[elig], w[elig], Rp.values, Lp, Pp)
    we = w[elig]
    S = pd.DataFrame({sn[j]: F[:, j] for j in enter})
    strata = stc.strata(caseid, pid)[0][elig]
    Xd = np.column_stack([np.ones(len(S))] + [(strata == g).astype(float) for g in ("nonpartisan", "opposed", "split")])
    sw = np.sqrt(we / we.mean())
    for c in S.columns:
        y = S[c].values
        beta = np.linalg.lstsq(Xd * sw[:, None], y * sw, rcond=None)[0]
        S[c] = y - Xd[:, 2:] @ beta[2:]

    ref = pd.read_csv(V2 / "scores.csv")
    assert np.array_equal(ref.caseid.values, caseid[elig]), "eligible respondents differ from the stage_c_v2 run"
    r = {c: float(np.corrcoef(S[c], ref[c])[0, 1]) for c in ORDER}
    print(f"{elig.sum():,} eligible; phi vs listwise {np.round(phi, 3).tolist()}; r vs stage_c_v2 {r}")
    assert min(r.values()) > 0.9999, "scores do not reproduce the stage_c_v2 run"

    meta = pd.read_stata(rl.eu.CES_PATH, columns=["caseid", "pid3", "ideo5", "inputstate"], convert_categoricals=False).set_index("caseid")
    out = meta.loc[caseid[elig]].reset_index()
    out = out[["pid3", "ideo5", "inputstate"]].assign(commonpostweight=we)
    for c in ORDER:
        out[f"FS_{c}"] = S[c].values
    out = fk.add_app_keys(out)
    fk.check_orientation(out)
    out["caseid"] = caseid[elig]
    out.to_csv(OUT, index=False)
    print(f"wrote {OUT} ({len(out):,} rows): {list(out.columns)}")


if __name__ == "__main__":
    main()

"""Which items best explain the four factors? Ranking for the short and long quiz (researcher, 2026-11-04).

Simulates the quiz as viz/src/utils/quizScoring.ts runs it: answers on a 0-1 scale, a linear key (intercept + one
weight per item, weighted least squares on the full-model factor scores) predicts the four factors, and a flat-prior
full-covariance Gaussian per party (each party's weighted mean and covariance of the full-model scores) picks the
party.

Data: CES 2024; the 41 clustering items (listwise_check/outputs/stage_c_v2/loadings.csv), recoded by
listwise_check/item_pool.recode and rescaled to 0-1 (lowest code 0, highest 1); the four factor scores and the nine
parties in data/processed/ (efa_revised.py, dpgmm_clustering.py). Weight commonpostweight. An item a respondent
skipped is filled with its weighted mean, as a quiz-taker who skips gets the neutral answer.
Selection: greedy forward, each step adds the item that most raises the mean R-squared across the four factors. Keys
are fit on a random half of respondents (seed 42) and every reported number is on the other half.
Writes analysis/efa/rebuild_nine_parties/quiz_items.csv (step, item, label, factor R2s, party agreement).
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "4")
ROOT = Path(__file__).resolve().parents[3]
LW = ROOT / "analysis/efa/exploration/listwise_check"
sys.path.insert(0, str(LW))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import compare_typologies as ct  # noqa: E402
import item_pool as ip  # noqa: E402

OUT = Path(__file__).with_name("quiz_items.csv")
F = ["FS_RT", "FS_TR", "FS_SO", "FS_PC"]


def main():
    X, w_all, _, caseid = ip.load()
    items = list(pd.read_csv(LW / "outputs/stage_c_v2/loadings.csv", index_col=0).index)
    fs = pd.read_csv(ROOT / "data/processed/efa_factor_scores.csv")
    typ = pd.read_csv(ROOT / "data/processed/typology_cluster_assignments.csv", usecols=["caseid", "cluster"])
    assert (fs.caseid.values == typ.caseid.values).all()
    pos = pd.Series(np.arange(len(caseid)), index=caseid).loc[fs.caseid.values].values
    A = X[items].values.astype(float)[pos]
    w = fs.commonpostweight.values
    lo, hi = np.nanmin(A, axis=0), np.nanmax(A, axis=0)
    A = (A - lo) / (hi - lo)
    mu = np.array([np.average(A[~np.isnan(A[:, j]), j], weights=w[~np.isnan(A[:, j])]) for j in range(len(items))])
    A = np.where(np.isnan(A), mu, A)
    Y = fs[F].values
    party = typ.cluster.values

    rng = np.random.default_rng(42)
    tr = rng.random(len(w)) < 0.5
    te = ~tr
    sw = np.sqrt(w / w.mean())

    def fit(cols):
        M = np.column_stack([np.ones(len(w)), A[:, cols]])
        B = np.linalg.lstsq(M[tr] * sw[tr, None], Y[tr] * sw[tr, None], rcond=None)[0]
        return M @ B

    def r2(P):
        out = []
        for j in range(len(F)):
            res = Y[te, j] - P[te, j]
            dev = Y[te, j] - np.average(Y[te, j], weights=w[te])
            out.append(1 - np.average(res ** 2, weights=w[te]) / np.average(dev ** 2, weights=w[te]))
        return np.array(out)

    # party Gaussians from the training half's full-model scores (the quiz's classify block)
    ks = np.unique(party)
    gauss = []
    for k in ks:
        m = tr & (party == k)
        mean = np.average(Y[m], axis=0, weights=w[m])
        cov = np.cov(Y[m].T, aweights=w[m])
        gauss.append((mean, np.linalg.inv(cov), np.linalg.slogdet(cov)[1]))

    def agree(P):
        ll = np.column_stack([-0.5 * np.einsum("ij,jk,ik->i", P[te] - m, ic, P[te] - m) - 0.5 * ld for m, ic, ld in gauss])
        return float(np.average(ks[ll.argmax(1)] == party[te], weights=w[te]))

    labels = {it: lab for _, rows in ct.TOPICS for it, lab, _ in rows}
    chosen, left, rows = [], list(range(len(items))), []
    while left:
        best = max(left, key=lambda j: r2(fit(chosen + [j])).mean())
        chosen.append(best)
        left.remove(best)
        P = fit(chosen)
        r = r2(P)
        rows.append({"step": len(chosen), "item": items[best], "label": labels.get(items[best], ""),
                     **{f"r2_{c[3:]}": round(float(v), 3) for c, v in zip(F, r)}, "r2_mean": round(float(r.mean()), 3),
                     "party_agreement": round(agree(P), 3)})
        print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

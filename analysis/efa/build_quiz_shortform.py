#!/usr/bin/env python3
"""Scoring keys and party classifier for the short (25-item) and long (41-item) quiz.

Ruled 2026-11-04 (analysis/efa/exploration/listwise_check/DECISIONS.md, "Quiz: short = 25 items, model
components"); method from analysis/efa/rebuild_nine_parties/quiz_classifier.py.

Key, per version: weighted least squares of each app factor key (FS_F1, FS_F2, FS_F4, FS_F5;
pipeline/factor_keys.py) on an intercept and the version's items, answers on the 0-1 scale of
viz/src/data/quizQuestions.json (item_pool coding, min-max scaled; a skipped item sits at its weighted
mean, which the key also carries so the app can do the same).

Classifier, per version: the DPGMM's own nine components (dpgmm_clustering.py settings, seed 52 = the
production run's seed, refit here; its labels must reproduce typology_cluster_assignments.csv), with
their mixing weights, means and covariances carried into app-key space, and each covariance widened by
the key's weighted residual covariance so a short quiz's estimation error enters the match. A party's
probability is its component's posterior (no temperature).

Ships viz/src/data/quizShortform.json:
  popSd     per factor: population SD, to put the respondent on the FactorBar z scale
  versions  {short, long}: variables, itemMean, weights (factor -> intercept + item coefficients),
            classify {factors, clusters: {id: {party, mean, invCov, logDet, logWeight}}}, placement
Run from repo root: python3 analysis/efa/build_quiz_shortform.py (after viz/scripts/make_quiz_questions.py)
"""
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "4")
ROOT = Path(__file__).resolve().parents[2]
LW = ROOT / "analysis" / "efa" / "exploration" / "listwise_check"
sys.path.insert(0, str(LW))
sys.path.insert(0, str(ROOT / "pipeline"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy.special import logsumexp  # noqa: E402
from sklearn.metrics import adjusted_rand_score as ari  # noqa: E402
from sklearn.mixture import BayesianGaussianMixture  # noqa: E402

import item_pool as ip  # noqa: E402
import factor_keys as fk  # noqa: E402
from party_codes import CLUSTER_TO_PARTY  # noqa: E402

PROC = ROOT / "data" / "processed"
VIZDATA = ROOT / "viz" / "src" / "data"
OUT = VIZDATA / "quizShortform.json"
KEYS = fk.KEYS                                   # F1, F2, F4, F5
SEED = 52
# raw clustering space -> app keys: x_app = T @ x_raw
T = np.zeros((len(KEYS), len(fk.RAW_COLS)))
for i, k in enumerate(KEYS):
    raw, sign = fk.SOURCE[k]
    T[i, fk.RAW_COLS.index(raw)] = sign


def gauss_ll(P, means, covs, logw):
    out = []
    for m, c, lw in zip(means, covs, logw):
        d = P - m
        out.append(lw - 0.5 * np.einsum("ij,jk,ik->i", d, np.linalg.inv(c), d) - 0.5 * np.linalg.slogdet(c)[1])
    return np.column_stack(out)


def main():
    qs = json.loads((VIZDATA / "quizQuestions.json").read_text())
    versions = {"short": [q["variable"] for q in qs if q["short"]], "long": [q["variable"] for q in qs]}

    X, _, _, caseid = ip.load()
    fs = pd.read_csv(PROC / "efa_factor_scores.csv")
    typ = pd.read_csv(PROC / "typology_cluster_assignments.csv", usecols=["caseid", "cluster"])
    assert (fs.caseid.values == typ.caseid.values).all()
    party = typ.cluster.values
    w = fs.commonpostweight.values
    pos = pd.Series(np.arange(len(caseid)), index=caseid).loc[fs.caseid.values].values
    items = versions["long"]
    A = X[items].values.astype(float)[pos]
    lo, hi = np.nanmin(A, axis=0), np.nanmax(A, axis=0)
    A = (A - lo) / (hi - lo)
    mu = np.array([np.average(A[~np.isnan(A[:, j]), j], weights=w[~np.isnan(A[:, j])]) for j in range(A.shape[1])])
    A = np.where(np.isnan(A), mu, A)
    Y = fs[[f"FS_{k}" for k in KEYS]].values

    model = BayesianGaussianMixture(n_components=9, covariance_type="full",
                                    weight_concentration_prior_type="dirichlet_process",
                                    n_init=5, random_state=SEED, max_iter=2000).fit(fs[fk.RAW_COLS].values)
    comp = model.predict(fs[fk.RAW_COLS].values)
    print(f"refit seed {SEED}: ARI vs production {ari(comp, party):.4f}")
    assert ari(comp, party) > 0.999
    keep = [k for k in range(9) if model.weights_[k] > 1e-3]
    to_party = {k: int(pd.Series(party[comp == k]).mode()[0]) for k in keep}
    assert sorted(to_party.values()) == sorted(CLUSTER_TO_PARTY), to_party
    cm = [T @ model.means_[k] for k in keep]
    cc = [T @ model.covariances_[k] @ T.T for k in keep]
    cw = [float(np.log(model.weights_[k])) for k in keep]
    ids = np.array([to_party[k] for k in keep])

    out = {"popSd": {k: round(float(np.sqrt(np.average((Y[:, i] - np.average(Y[:, i], weights=w)) ** 2, weights=w))), 6)
                     for i, k in enumerate(KEYS)},
           "versions": {}}
    sw = np.sqrt(w / w.mean())
    for name, vars_ in versions.items():
        idx = [items.index(v) for v in vars_]
        M = np.column_stack([np.ones(len(w)), A[:, idx]])
        B = np.linalg.lstsq(M * sw[:, None], Y * sw[:, None], rcond=None)[0]
        P = M @ B
        E = np.cov((Y - P).T, aweights=w)
        r2 = 1 - np.average((Y - P) ** 2, axis=0, weights=w) / np.average((Y - np.average(Y, axis=0, weights=w)) ** 2, axis=0, weights=w)
        covs = [c + E for c in cc]
        ll = gauss_ll(P, cm, covs, cw)
        place = float(np.average(ids[ll.argmax(1)] == party, weights=w))
        post = np.exp(ll - logsumexp(ll, axis=1, keepdims=True))
        conf = float(np.average(post.max(1), weights=w))
        print(f"[{name}] {len(vars_)} items  R2 " + " ".join(f"{k}={r:.3f}" for k, r in zip(KEYS, r2))
              + f"  placement {place:.3f}  mean top prob {conf:.3f}")
        clusters = {}
        for j, cid in enumerate(ids):
            clusters[str(cid)] = {"party": CLUSTER_TO_PARTY[int(cid)],
                                  "mean": [round(float(x), 6) for x in cm[j]],
                                  "invCov": [[round(float(x), 6) for x in row] for row in np.linalg.inv(covs[j])],
                                  "logDet": round(float(np.linalg.slogdet(covs[j])[1]), 6),
                                  "logWeight": round(cw[j], 6)}
        out["versions"][name] = {
            "variables": vars_,
            "itemMean": {v: round(float(mu[items.index(v)]), 6) for v in vars_},
            "weights": {k: {"intercept": round(float(B[0, i]), 6),
                            **{v: round(float(B[1 + n, i]), 6) for n, v in enumerate(vars_)}}
                        for i, k in enumerate(KEYS)},
            "classify": {"factors": KEYS, "clusters": clusters},
            "placement": round(place, 4),
        }
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

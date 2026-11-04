"""Quiz party placement with the clustering model's own components vs the current per-party Gaussians (2026-11-04).

Same simulation as quiz_items.py (0-1 answers, skipped items at the weighted mean, linear key fit on a random half,
seed 42, everything reported on the other half), at the short-quiz candidates and the full 41 items in the
quiz_items.csv order. Classifiers, all on the key's predicted factor scores:
  party gaussians, flat   current quiz: each party's weighted mean and covariance of its members' scores, equal priors
  components, flat        the fitted DPGMM's nine components (means, covariances), equal priors
  components, weighted    the same with the components' mixing weights: the model's own predict_proba
  components + key error  weighted, each covariance widened by the key's residual covariance (training half), so a
                          short quiz's estimation error enters the classification
Also reported: mean top-party probability among held-out respondents (calibration: should track agreement).
Model: dpgmm_clustering.py settings, seed 52 (the production run's chosen seed), refit here on
data/processed/efa_factor_scores.csv; its labels must reproduce typology_cluster_assignments.csv (ARI 1).
Writes analysis/efa/rebuild_nine_parties/quiz_classifier.csv.
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
from scipy.special import logsumexp  # noqa: E402
from sklearn.metrics import adjusted_rand_score as ari  # noqa: E402
from sklearn.mixture import BayesianGaussianMixture  # noqa: E402

import item_pool as ip  # noqa: E402

HERE = Path(__file__).parent
F = ["FS_RT", "FS_TR", "FS_SO", "FS_PC"]
SIZES = [10, 15, 20, 25, 41]


def gauss_ll(P, means, covs, logw):
    out = []
    for m, c, lw in zip(means, covs, logw):
        ic, ld = np.linalg.inv(c), np.linalg.slogdet(c)[1]
        d = P - m
        out.append(lw - 0.5 * np.einsum("ij,jk,ik->i", d, ic, d) - 0.5 * ld)
    return np.column_stack(out)


def main():
    X, _, _, caseid = ip.load()
    fs = pd.read_csv(ROOT / "data/processed/efa_factor_scores.csv")
    party = pd.read_csv(ROOT / "data/processed/typology_cluster_assignments.csv", usecols=["caseid", "cluster"])
    assert (fs.caseid.values == party.caseid.values).all()
    party = party.cluster.values
    order = pd.read_csv(HERE / "quiz_items.csv").item.tolist()
    pos = pd.Series(np.arange(len(caseid)), index=caseid).loc[fs.caseid.values].values
    A = X[order].values.astype(float)[pos]
    w = fs.commonpostweight.values
    lo, hi = np.nanmin(A, axis=0), np.nanmax(A, axis=0)
    A = (A - lo) / (hi - lo)
    mu = np.array([np.average(A[~np.isnan(A[:, j]), j], weights=w[~np.isnan(A[:, j])]) for j in range(A.shape[1])])
    A = np.where(np.isnan(A), mu, A)
    Y = fs[F].values

    model = BayesianGaussianMixture(n_components=9, covariance_type="full", weight_concentration_prior_type="dirichlet_process",
                                    n_init=5, random_state=52, max_iter=2000).fit(Y)
    comp = model.predict(Y)
    print(f"refit seed 52: ARI vs production {ari(comp, party):.4f}")
    assert ari(comp, party) > 0.999
    to_party = {k: int(pd.Series(party[comp == k]).mode()[0]) for k in np.unique(comp)}
    keep = [k for k in range(9) if model.weights_[k] > 1e-3]
    cm, cc, cw = model.means_[keep], model.covariances_[keep], np.log(model.weights_[keep])
    cp = np.array([to_party[k] for k in keep])

    rng = np.random.default_rng(42)
    tr = rng.random(len(w)) < 0.5
    te = ~tr
    sw = np.sqrt(w / w.mean())
    ks = np.unique(party)
    pm = [np.average(Y[tr & (party == k)], axis=0, weights=w[tr & (party == k)]) for k in ks]
    pc = [np.cov(Y[tr & (party == k)].T, aweights=w[tr & (party == k)]) for k in ks]

    rows = []
    for n in SIZES:
        M = np.column_stack([np.ones(len(w)), A[:, :n]])
        B = np.linalg.lstsq(M[tr] * sw[tr, None], Y[tr] * sw[tr, None], rcond=None)[0]
        P = M @ B
        E = np.cov((Y[tr] - P[tr]).T, aweights=w[tr])
        for name, ll, lab in [
            ("party gaussians, flat", gauss_ll(P[te], pm, pc, np.zeros(len(ks))), ks),
            ("components, flat", gauss_ll(P[te], cm, cc, np.zeros(len(keep))), cp),
            ("components, weighted", gauss_ll(P[te], cm, cc, cw), cp),
            ("components + key error", gauss_ll(P[te], cm, [c + E for c in cc], cw), cp),
        ]:
            post = np.exp(ll - logsumexp(ll, axis=1, keepdims=True))
            agree = float(np.average(lab[ll.argmax(1)] == party[te], weights=w[te]))
            conf = float(np.average(post.max(1), weights=w[te]))
            rows.append({"items": n, "classifier": name, "party_agreement": round(agree, 3), "mean_top_prob": round(conf, 3)})
            print(rows[-1], flush=True)
    pd.DataFrame(rows).to_csv(HERE / "quiz_classifier.csv", index=False)


if __name__ == "__main__":
    main()

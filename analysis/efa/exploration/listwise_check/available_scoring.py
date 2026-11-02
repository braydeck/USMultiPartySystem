"""Does listwise deletion skew the nine parties? Score the CES respondents it drops on the items they answered.

Data: CES 2024 Common Content (efa_update.CES_PATH), production recode (efa_update.recode_items), production
scores data/processed/efa_factor_scores.csv (n = 45,214), parties data/processed/typology_cluster_assignments.csv
(same row order), codes from pipeline/party_codes.py.

Population: the 49,432 respondents with the post-election weight. 45,214 answered all 24 items; the other
4,218 are dropped by listwise deletion today. (The 10,568 without a post-election interview have no
post-election items and no post weight; they stay out.)

Method, holding production fixed:
  1. Items standardized with production's weighted means and SDs (complete cases), as in efa_update.py.
  2. Production's scoring coefficients B recovered from its own scores (least squares of FS_F1..F5 on Z,
     asserted exact), so the structure matrix is S = R B with R = polychoric_matrix.csv.
  3. Each dropped respondent gets Thomson regression scores on the items they answered:
     F = z_s R_ss^-1 S_s. For a complete respondent this equals production's score exactly.
  4. FS_F4_resid and FS_F5_resid from production's own weighted-OLS line on FS_F1 (recovered, asserted exact).
  5. Parties: the production DPGMM (cap 9, seed 59, n_init 5, max_iter 2000), refit on the production
     inputs and asserted to reproduce the typology, predicts each dropped respondent's party.
Shares use commonpostweight. Intervals: 1,000-draw respondent bootstrap of the dropped group (seed 42).
Writes outputs/ (party_shares.csv, dropped_respondents.csv).
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score
from sklearn.mixture import BayesianGaussianMixture

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "analysis" / "efa" / "pipeline"))
sys.path.insert(0, str(ROOT / "pipeline"))
import efa_update as eu  # noqa: E402
import party_codes as pc  # noqa: E402

OUT = Path(__file__).parent / "outputs"
FS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]
CLUSTER_COLS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4_resid", "FS_F5_resid"]


def wols(y, x, w):
    X = np.column_stack([np.ones_like(x), x])
    W = w / w.mean()
    return np.linalg.solve((X.T * W) @ X, (X.T * W) @ y)


def score():
    """Frozen-production scores for complete and dropped respondents (clustering inputs, weights, masks)."""
    lab = pd.read_stata(eu.CES_PATH, columns=eu.ITEMS_24, convert_categoricals=True, convert_missing=False, convert_dates=False)
    meta = pd.read_stata(eu.CES_PATH, columns=["caseid", "commonpostweight", "pid3"], convert_categoricals=False)
    X = eu.recode_items(lab)
    w_all = pd.to_numeric(meta.commonpostweight, errors="coerce")
    post = (w_all > 0).values
    complete = (X.notna().all(axis=1) & post).values
    dropped = post & ~complete

    fs = pd.read_csv(ROOT / "data/processed/efa_factor_scores.csv")
    typ = pd.read_csv(ROOT / "data/processed/typology_cluster_assignments.csv", usecols=["cluster", "commonpostweight"])
    assert complete.sum() == len(fs) and np.allclose(meta.caseid[complete].values, fs.caseid.values), "production rows not reproduced"
    assert np.allclose(fs.commonpostweight.values, typ.commonpostweight.values)

    Xc = X[complete].values.astype(float)
    wc = w_all[complete].values
    wn = wc / wc.sum()
    mu = (wn[:, None] * Xc).sum(0)
    sig = np.sqrt((wn[:, None] * (Xc - mu) ** 2).sum(0))
    B, *_ = np.linalg.lstsq((Xc - mu) / sig, fs[FS].values, rcond=None)
    fit_err = np.abs(((Xc - mu) / sig) @ B - fs[FS].values).max()
    assert fit_err < 1e-6, f"scoring coefficients not recovered (max error {fit_err:.2e})"
    R = pd.read_csv(ROOT / "data/processed/polychoric_matrix.csv", index_col=0).loc[eu.ITEMS_24, eu.ITEMS_24].values
    S = R @ B

    Xd = X[dropped].values.astype(float)
    ok = ~np.isnan(Xd)
    Zd = (Xd - mu) / sig
    Fd = np.zeros((len(Xd), 5))
    for pattern in np.unique(ok, axis=0):
        rows = (ok == pattern).all(axis=1)
        Fd[rows] = Zd[np.ix_(rows, pattern)] @ np.linalg.solve(R[np.ix_(pattern, pattern)], S[pattern])

    lines = {}
    for j in (3, 4):
        a, b = wols(fs[FS[j]].values, fs.FS_F1.values, fs.commonpostweight.values)
        assert np.abs(fs[FS[j]].values - (a + b * fs.FS_F1.values) - fs[f"{FS[j]}_resid"].values).max() < 1e-6
        lines[j] = (a, b)
    Xd_cl = np.column_stack([Fd[:, 0], Fd[:, 1], Fd[:, 2]] + [Fd[:, j] - (lines[j][0] + lines[j][1] * Fd[:, 0]) for j in (3, 4)])
    return dict(meta=meta, w_all=w_all, complete=complete, dropped=dropped, ok=ok, fs=fs, typ=typ, wc=wc,
                Fd=Fd, Xd_cl=Xd_cl)


def main():
    OUT.mkdir(exist_ok=True)
    d = score()
    meta, w_all, complete, dropped, ok, fs, typ, wc, Xd_cl = (d[k] for k in
        ("meta", "w_all", "complete", "dropped", "ok", "fs", "typ", "wc", "Xd_cl"))
    post = (w_all > 0).values

    m = BayesianGaussianMixture(n_components=9, covariance_type="full", weight_concentration_prior_type="dirichlet_process",
                                n_init=5, random_state=59, max_iter=2000).fit(fs[CLUSTER_COLS].values)
    raw = m.predict(fs[CLUSTER_COLS].values)
    assert adjusted_rand_score(raw, typ.cluster.values) > 0.999, "production DPGMM not reproduced"
    to_prod = pd.crosstab(raw, typ.cluster.values).idxmax(axis=1).to_dict()
    party_d = pd.Series(m.predict(Xd_cl)).map(to_prod).map(pc.CLUSTER_TO_PARTY).values
    post_max = m.predict_proba(Xd_cl).max(axis=1)
    post_max_c = m.predict_proba(fs[CLUSTER_COLS].values).max(axis=1)

    wd = w_all[dropped].values
    party_c = typ.cluster.map(pc.CLUSTER_TO_PARTY).values
    rng = np.random.default_rng(42)
    boot = []
    for _ in range(1000):
        i = rng.integers(0, len(wd), len(wd))
        boot.append(pd.Series(wd[i]).groupby(party_d[i]).sum() / wd[i].sum())
    boot = pd.DataFrame(boot).fillna(0)
    rows = []
    for p in pc.PARTIES:
        prod = wc[party_c == p].sum() / wc.sum()
        drop = wd[party_d == p].sum() / wd.sum()
        comb = (wc[party_c == p].sum() + wd[party_d == p].sum()) / (wc.sum() + wd.sum())
        rows.append({"party": p, "production_share": prod, "dropped_share": drop,
                     "dropped_lo": boot[p].quantile(0.025) if p in boot else 0.0, "dropped_hi": boot[p].quantile(0.975) if p in boot else 0.0,
                     "p_dropped_higher": float((boot[p] > prod).mean()) if p in boot else 0.0,
                     "combined_share": comb, "shift_pp": (comb - prod) * 100})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "party_shares.csv", index=False)
    pd.DataFrame({"caseid": meta.caseid[dropped].values, "items_answered": ok.sum(axis=1), "party": party_d,
                  "max_posterior": post_max, **{c: Xd_cl[:, j] for j, c in enumerate(CLUSTER_COLS)}}).to_csv(OUT / "dropped_respondents.csv", index=False)

    print(f"post-weight respondents {post.sum():,}; complete {complete.sum():,}; dropped {dropped.sum():,}")
    print("items answered by the dropped:", pd.Series(ok.sum(axis=1)).value_counts().sort_index(ascending=False).head(5).to_dict())
    print("most-skipped items among the dropped:", pd.Series((~ok).mean(axis=0), index=eu.ITEMS_24).sort_values(ascending=False).head(5).round(3).to_dict())
    print(f"party ID among the dropped: Dem {np.average(meta.pid3[dropped] == 1, weights=wd):.0%}, Rep {np.average(meta.pid3[dropped] == 2, weights=wd):.0%}, "
          f"Ind {np.average(meta.pid3[dropped] == 3, weights=wd):.0%} | complete: Dem {np.average(meta.pid3[complete] == 1, weights=wc):.0%}, "
          f"Rep {np.average(meta.pid3[complete] == 2, weights=wc):.0%}, Ind {np.average(meta.pid3[complete] == 3, weights=wc):.0%}")
    print(f"assignment confidence (weighted mean top posterior): dropped {np.average(post_max, weights=wd):.2f}, complete {np.average(post_max_c, weights=wc):.2f}")
    print(out.round(4).to_string(index=False))


if __name__ == "__main__":
    main()

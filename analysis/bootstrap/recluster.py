"""Re-clustering draws: each bootstrap draw refits the parties on its own resample.

The fixed-party harness resampled respondents under one set of parties, which measures vote
noise only. The parties are themselves an estimate, and at the old ten-party cap a different
DPGMM seed elected a different president. A draw here reruns the whole procedure on the
resample: fit the DPGMM on the resampled respondents, assign every respondent from that fit,
then hold the elections on the same resample.

Draw d uses stratified_indices(state, seed=42 + d), the index vector the seat, party-list and
population bootstraps already share, so all three describe the same resamples. The fitted
model is cached per draw (a few KB), and posteriors are recomputed on demand.

Fit settings match analysis/efa/pipeline/dpgmm_clustering.py: cap 9 (the stable cap,
analysis/efa/exploration/k_stability/), full covariance, Dirichlet process prior, n_init 5,
max_iter 2000, random_state 42 + d. Party IDs come from a Hungarian match of the draw's hard
labels against the published typology, over every respondent, weighted. With nine clusters
over ten ID slots, the slot the published typology leaves empty stays empty in every draw.
"""

import pickle
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from sklearn.mixture import BayesianGaussianMixture

from .inject import BASE, PROCESSED
from .resample import stratified_indices

CACHE = BASE / "data" / "bootstrap_cache" / "recluster_k9"
COLS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4_resid", "FS_F5_resid"]
K = 9
N_IDS = 10
PROB_COLS = [f"prob_cluster_{k}" for k in range(N_IDS)]


@lru_cache(maxsize=1)
def _inputs():
    fs = pd.read_csv(PROCESSED / "efa_factor_scores.csv")
    typ = pd.read_csv(PROCESSED / "typology_cluster_assignments.csv")
    assert (fs.caseid.values == typ.caseid.values).all(), "typology is not row-aligned with the factor scores"
    return fs, typ


def draw_index(d: int) -> np.ndarray:
    fs, _ = _inputs()
    return stratified_indices(fs["inputstate"].values, seed=42 + d)


def fit_draw(d: int) -> dict:
    """Fit draw d and cache {model, component -> party id, fit diagnostics}. Idempotent."""
    path = CACHE / f"draw_{d:04d}.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    fs, typ = _inputs()
    X, w = fs[COLS].values, fs["commonpostweight"].values
    m = BayesianGaussianMixture(n_components=K, covariance_type="full",
                                weight_concentration_prior_type="dirichlet_process",
                                n_init=5, random_state=42 + d, max_iter=2000).fit(X[draw_index(d)])
    labels = m.predict(X)
    published = typ["cluster"].values
    ids = sorted(np.unique(published))
    ct = pd.crosstab(labels, published, values=w, aggfunc="sum").reindex(index=range(K), columns=ids).fillna(0)
    ri, ci = linear_sum_assignment(-ct.values / np.maximum(ct.values.sum(axis=0, keepdims=True), 1e-12))
    comp_to_id = {int(r): int(ids[c]) for r, c in zip(ri, ci)}
    retention = {int(ids[c]): float(ct.values[r, c] / ct.values[:, c].sum()) for r, c in zip(ri, ci)}
    out = {"model": m, "comp_to_id": comp_to_id, "retention": retention,
           "converged": bool(m.converged_), "n_eff": int((m.weights_ > 0.01).sum()),
           "lower_bound": float(m.lower_bound_)}
    CACHE.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(pickle.dumps(out))
    tmp.replace(path)
    return out


def draw_typology(d: int) -> pd.DataFrame:
    """Draw d's assignments for all 45,214 respondents, in the published typology's schema."""
    fs, typ = _inputs()
    f = fit_draw(d)
    p = f["model"].predict_proba(fs[COLS].values)
    probs = np.zeros((len(fs), N_IDS))
    for comp, pid in f["comp_to_id"].items():
        probs[:, pid] = p[:, comp]
    out = typ.copy()
    out[PROB_COLS] = probs
    out["cluster"] = probs.argmax(axis=1)
    return out


def draw_turnout(d: int, cluster: np.ndarray, idx: np.ndarray) -> pd.DataFrame:
    """turnout_propensity.csv for draw d: each respondent gets their draw cluster's validated
    turnout, measured on the draw's own resample (compute_turnout_propensity.py, Spec 1)."""
    fs, _ = _inputs()
    real = pd.read_csv(PROCESSED / "turnout_propensity.csv")
    voted, w = real["voted"].values, fs["commonpostweight"].values
    rate = np.zeros(len(real))
    for k in np.unique(cluster):
        in_k = cluster[idx] == k
        rate[cluster == k] = np.average(voted[idx][in_k], weights=w[idx][in_k]) if in_k.any() else 0.0
    return pd.DataFrame({"caseid": real["caseid"].values, "cluster": cluster,
                         "voted": voted, "turnout_cluster": rate})


def fit_all(n_draws: int, procs: int) -> None:
    """Fit every uncached draw in parallel; DPGMM fits are the slow part of a draw."""
    import os
    from concurrent.futures import ProcessPoolExecutor
    todo = [d for d in range(n_draws) if not (CACHE / f"draw_{d:04d}.pkl").exists()]
    if not todo:
        return
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    with ProcessPoolExecutor(procs) as ex:
        for i, _ in enumerate(ex.map(fit_draw, todo, chunksize=1), 1):
            if i % 50 == 0 or i == len(todo):
                print(f"  fitted {i}/{len(todo)} draws", flush=True)


def fit_summary(n_draws: int) -> pd.DataFrame:
    rows = []
    for d in range(n_draws):
        f = fit_draw(d)
        rows.append({"draw": d, "converged": f["converged"], "n_eff": f["n_eff"],
                     "lower_bound": f["lower_bound"], **{f"ret_{k}": v for k, v in f["retention"].items()}})
    return pd.DataFrame(rows)


def draw_first_choice(d: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(one-hot first choice, per-respondent cluster turnout, resample index) for draw d.

    What the party-list and population bootstraps need: both count first choices, weighted by
    the draw cluster's validated turnout."""
    typ = draw_typology(d)
    idx = draw_index(d)
    cluster = typ["cluster"].values
    # uint8 / float32: the callers hold a thousand of these at once
    fc = np.zeros((len(typ), N_IDS), dtype=np.uint8)
    fc[np.arange(len(typ)), cluster] = 1
    return fc, draw_turnout(d, cluster, idx)["turnout_cluster"].values.astype(np.float32), idx

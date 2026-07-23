"""Shared EFA math — extracted verbatim from the frozen 2024 pipeline.

Source of each function (byte-identical logic, only parameterized):
  - compute_smc, paf, oblimin, parallel_analysis  ← analysis/efa/pipeline/run_efa.py
  - weighted_mean, weighted_std                    ← analysis/efa/pipeline/efa_update.py
  - weighted_polychoric                            ← analysis/efa/pipeline/efa_pipeline_v4.py
  - thomson_scores, sign_flip, wresid              ← efa_update.py / cluster_survival_k4_k5.py

Do NOT change the algorithm here without re-running the 2024 reproduction gate
(wave_2024/run_wave.py), which asserts these reproduce efa_loadings_k5_final.csv.
"""
import warnings
warnings.filterwarnings("ignore")
import numpy as np
from scipy.optimize import minimize_scalar
from scipy.stats import norm
from scipy.stats import multivariate_normal as mvn

BIG = 6.5


# ── PAF ───────────────────────────────────────────────────────────────────────
def compute_smc(R):
    """Squared multiple correlations as initial communality estimates."""
    try:
        R_inv = np.linalg.inv(R)
        smc = 1.0 - 1.0 / np.diag(R_inv)
    except np.linalg.LinAlgError:
        smc = np.full(R.shape[0], 0.5)
    return np.clip(smc, 0.005, 0.999)


def paf(R, n_factors, n_iter=1000, tol=1e-7):
    """Principal Axis Factoring from a correlation matrix.

    Returns (L unrotated [p×k], h2 communalities, eigs [k])."""
    h2 = compute_smc(R)
    evals = None
    for _ in range(n_iter):
        R_red = R.copy()
        np.fill_diagonal(R_red, h2)
        evals, evecs = np.linalg.eigh(R_red)
        idx = np.argsort(evals)[::-1]
        evals, evecs = evals[idx], evecs[:, idx]
        pos = np.maximum(evals[:n_factors], 0.0)
        L = evecs[:, :n_factors] * np.sqrt(pos)
        h2_new = np.clip(np.sum(L ** 2, axis=1), 0.0, 0.999)
        if np.max(np.abs(h2_new - h2)) < tol:
            h2 = h2_new
            break
        h2 = h2_new
    return L, h2, evals[:n_factors]


# ── Oblimin (factor_analyzer backend, matches production) ──────────────────────
def oblimin(A, gamma=0):
    """Direct oblimin rotation via factor_analyzer. Returns (L pattern, Phi)."""
    from factor_analyzer.rotator import Rotator
    rot = Rotator(method="oblimin", power=gamma)
    L = rot.fit_transform(A)
    Phi = rot.phi_ if rot.phi_ is not None else np.eye(A.shape[1])
    return L, Phi


# ── Parallel analysis ─────────────────────────────────────────────────────────
def parallel_analysis(R, n_obs, n_max=10, n_sim=200, pct=95, seed=2024):
    """Compare observed eigenvalues of R to random-data eigenvalues (95th pct).

    n_obs is the effective (listwise) sample size for the simulated matrices."""
    rng = np.random.RandomState(seed)
    p = R.shape[0]
    obs_evals = np.linalg.eigvalsh(R)[::-1]
    n_max = min(n_max, p)
    sim_evals = np.zeros((n_sim, p))
    for i in range(n_sim):
        X = rng.randn(n_obs, p)
        Rc = np.corrcoef(X.T)
        sim_evals[i] = np.linalg.eigvalsh(Rc)[::-1]
    threshold = np.percentile(sim_evals, pct, axis=0)
    n_factors = int(np.sum(obs_evals[:n_max] > threshold[:n_max]))
    return n_factors, obs_evals, threshold


# ── Weighted statistics ─────────────────────────────────────────────────────
def weighted_mean(x, w):
    mask = ~np.isnan(x)
    return np.sum(x[mask] * w[mask]) / np.sum(w[mask])


def weighted_std(x, w):
    mask = ~np.isnan(x)
    mu = weighted_mean(x, w)
    var = np.sum(w[mask] * (x[mask] - mu) ** 2) / np.sum(w[mask])
    return np.sqrt(var)


def weighted_standardize(X, w):
    """Weighted column standardization. Returns (Z, mu, sig)."""
    wn = w / w.sum()
    mu = (wn[:, None] * X).sum(0)
    sig = np.sqrt((wn[:, None] * (X - mu) ** 2).sum(0))
    sig[sig < 1e-10] = 1.0
    return (X - mu) / sig, mu, sig


# ── Regularize a (polychoric) correlation matrix to PSD ──────────────────────
def regularize_corr(R):
    """Enforce symmetry, unit diagonal, and positive-definiteness (matches
    run_efa.py / efa_update.py regularization)."""
    R = (R + R.T) / 2.0
    np.fill_diagonal(R, 1.0)
    min_eig = np.linalg.eigvalsh(R).min()
    if min_eig < 1e-6:
        bump = abs(min_eig) + 1e-4
        R = R + np.eye(R.shape[0]) * bump
        d = np.sqrt(np.diag(R))
        R = R / np.outer(d, d)
    return R


# ── Thomson (regression) factor scores for oblique rotation ──────────────────
def thomson_scores(Z, R, L_rot, Phi):
    """Bartlett/Thomson regression factor scores.
      S = L_rot @ Phi            (structure matrix)
      B = R_inv @ S              (scoring coefficients)
      F = Z @ B                  (factor scores)
    """
    S = L_rot @ Phi
    R_inv = np.linalg.inv(R)
    B = R_inv @ S
    return Z @ B, B


def sign_align_by_loading(F, L):
    """Flip each factor so its strongest-loading item is positive (matches the
    compact convention in cluster_survival_k4_k5.build)."""
    k = L.shape[1]
    F = F.copy(); L = L.copy()
    for j in range(k):
        if L[np.argmax(np.abs(L[:, j])), j] < 0:
            F[:, j] *= -1
            L[:, j] *= -1
    return F, L


# ── Weighted-OLS residualization (F4/F5 on F1) ───────────────────────────────
def wresid(y, x, w):
    """Residual of y on x under weighted OLS (production residualization)."""
    Xd = np.column_stack([np.ones_like(x), x])
    W = w / w.mean()
    XtW = Xd.T * W
    return y - Xd @ np.linalg.solve(XtW @ Xd, XtW @ y)


# ── Weighted polychoric correlation (single pair) ────────────────────────────
def weighted_polychoric(x, y, wts):
    mask = ~(np.isnan(x) | np.isnan(y))
    x_, y_, w_ = x[mask], y[mask], wts[mask]
    if len(x_) < 30:
        return np.nan
    x_cats = np.sort(np.unique(x_))
    y_cats = np.sort(np.unique(y_))
    nx, ny = len(x_cats), len(y_cats)
    if nx < 2 or ny < 2:
        return np.nan
    xi = np.searchsorted(x_cats, x_)
    yi = np.searchsorted(y_cats, y_)
    w_ = w_ / w_.sum()
    ct = np.zeros((nx, ny))
    for ii, jj, ww in zip(xi, yi, w_):
        ct[ii, jj] += ww
    x_marg = ct.sum(axis=1)
    y_marg = ct.sum(axis=0)
    tau_x = np.concatenate([[-BIG], norm.ppf(np.clip(np.cumsum(x_marg)[:-1], 1e-7, 1 - 1e-7)), [BIG]])
    tau_y = np.concatenate([[-BIG], norm.ppf(np.clip(np.cumsum(y_marg)[:-1], 1e-7, 1 - 1e-7)), [BIG]])

    def neg_log_lik(rho):
        cov = [[1.0, rho], [rho, 1.0]]
        H, K = np.meshgrid(tau_x, tau_y, indexing="ij")
        pts = np.column_stack([H.ravel(), K.ravel()])
        cdf = mvn(mean=[0, 0], cov=cov).cdf(pts).reshape(nx + 1, ny + 1)
        P = np.diff(np.diff(cdf, axis=0), axis=1)
        P = np.maximum(P, 1e-12)
        return -np.sum(ct * np.log(P))

    res = minimize_scalar(neg_log_lik, bounds=(-0.9999, 0.9999),
                          method="bounded", options={"xatol": 1e-5})
    return float(res.x)


def polychoric_matrix(D, items, w, progress=True):
    """Full weighted polychoric matrix over `items` columns of DataFrame D."""
    import time
    p = len(items)
    M = np.eye(p)
    pairs = [(i, j) for i in range(p) for j in range(i + 1, p)]
    t0 = time.time()
    for k, (i, j) in enumerate(pairs):
        r = weighted_polychoric(D[items[i]].values, D[items[j]].values, w)
        M[i, j] = M[j, i] = r
        if progress and (k + 1) % 25 == 0:
            el = time.time() - t0
            eta = el / (k + 1) * (len(pairs) - k - 1)
            print(f"    polychoric {k+1}/{len(pairs)}  ({el:.0f}s, ~{eta:.0f}s left)", flush=True)
    return M

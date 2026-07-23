"""Tucker's congruence coefficient + factor matching across EFA solutions.

Tucker's phi is the standard metric for comparing factor loadings across samples:
  phi(x,y) = sum(x*y) / sqrt(sum(x^2) * sum(y^2))
Reporting thresholds (Lorenzo-Seva & ten Berge 2006):
  |phi| > 0.95  -> factors are essentially identical
  |phi| > 0.85  -> fair correspondence
  |phi| < 0.85  -> the factor did not replicate
"""
import numpy as np
from scipy.optimize import linear_sum_assignment

FAIR, IDENTICAL = 0.85, 0.95


def tucker_phi(x, y):
    """Tucker's congruence between two loading vectors."""
    denom = np.sqrt(np.sum(x ** 2) * np.sum(y ** 2))
    if denom == 0:
        return 0.0
    return float(np.sum(x * y) / denom)


def phi_matrix(L1, L2):
    """All pairwise Tucker phi between columns of L1 (k1) and L2 (k2)."""
    k1, k2 = L1.shape[1], L2.shape[1]
    M = np.zeros((k1, k2))
    for a in range(k1):
        for b in range(k2):
            M[a, b] = tucker_phi(L1[:, a], L2[:, b])
    return M


def match_factors(L1, L2):
    """Align L2 factors to L1 factors via Hungarian on 1-|phi|.

    Returns list of dicts: for each L1 factor index, the best-matching L2 factor,
    the signed phi, and a replication label. L1/L2 must share row order (same items).
    """
    M = phi_matrix(L1, L2)
    ri, ci = linear_sum_assignment(1 - np.abs(M))
    out = []
    for a, b in zip(ri, ci):
        phi = M[a, b]
        label = ("identical" if abs(phi) >= IDENTICAL
                 else "fair" if abs(phi) >= FAIR else "did-not-replicate")
        out.append({"factor_1": int(a), "factor_2": int(b),
                    "phi": round(float(phi), 4),
                    "sign": "+" if phi >= 0 else "-",
                    "replication": label})
    return out


def structure_loadings(L_pattern, Phi):
    """Structure matrix S = L @ Phi — the stable comparison target for oblique
    solutions (pattern loadings are rotation-frame dependent)."""
    return L_pattern @ Phi

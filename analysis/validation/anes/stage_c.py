"""ANES independent segmentation under the shared Stage C rule (docs/EFA_ITEM_SELECTION_ROBUSTNESS.md §3c as revised
2026-11-03).

Data: ANES 2024 Time Series CSV and codebook (2025-08-08 release), post weight V240108a.
Pool: config/anes_independent_pool.csv (162 items; battery_id tagged by tag_batteries.py before this ran). Changes
since the k = 17 run (archived): V241451 (personal finances, economic sentiment) out at Stage A; the federal spending
battery (V241263x-V241284x, one battery) back in (analysis/validation/DECISIONS.md 2026-11-03).

Choices fixed before running (§3c):
  Stage B  on the full sample: missing > 30% out; weighted modal share > 85% out. Redundancy: pairs with weighted
           polychoric |r| > 0.70, strongest first, keep the member with the LOWER mean |r| with the rest of the
           current pool (the pair excluded). Party-blind. (§3c corrected 2026-11-03: keeping the higher-mean member
           let one central item absorb distinct topics in a chain.)
  Matrix   one pairwise weighted polychoric per sample on every post-weighted respondent, regularized, subset as
           items leave. Parallel analysis takes n = the median pairwise-complete count across item pairs.
  k        lower of parallel analysis (95th percentile, every eigenvalue) and Velicer's MAP on the full-sample Stage B
           pool, bounded to 3-7. Unbounded counts reported.
  Screen   50 bootstrap resamples of respondents (rng = default_rng(42), resample b = its b-th draw). In each: the
           redundancy screen, then PAF + oblimin at k with every weak item (max |l| < 0.30, h^2 < 0.20 or
           h^2 >= 0.995) dropped together and refit until none is weak. Cross-loaders stay. An item is retained if
           it survives in more than 25 of 50. The retained items are fit once on the full sample at k; parallel
           analysis and MAP rerun on that pool and are reported, not looped.
  Entry    a factor clusters if it has >= 2 clean items (|l| >= 0.40 on it, < 0.30 on every other) from >= 2
           batteries in the full-sample fit AND in more than 25 of the 50 resamples, each resample refit at k on
           the retained items and its factors matched one-to-one to the full-sample factors (Hungarian on |phi|);
           a match under phi 0.85 counts as a fail.
  Step 7   state in-power adjustment: the pool has no item about the respondent's state government, so nothing to
           adjust.
  Cluster  available-item Thomson scores from the full-sample fit; respondents answering >= half of each passing
           factor's items (items assigned by primary loading); the anchor residualization rule; the stability sweep
           and cap rule (n_check.sweep); the modal solution across 20 seeds, best lower bound within it. Compared with
           the production four segments (outputs/clustering/independent_available/) by ARI and crosswalk.

Sensitivity: --no-foreign-policy drops the foreign_policy_nation domain (14 items: threat ratings, Israel/Ukraine/
Palestinian aid, Gaza protests, "better off if we stayed home", force, US vs other countries) after the missing/modal
screen and reruns everything else unchanged, writing to outputs/stage_c_nofp/ and comparing with the main run. Defense
spending and terrorism worry stay (other domains). Resample matrices are the main run's, subset (a pairwise matrix's
submatrix is the subset's matrix).

Writes outputs/stage_c/{screen_log.csv, retention.csv, loadings_k<k>.csv, entry_test.csv, caps.csv, clusters.csv,
crosswalk.csv}; log via tee. Resample matrices are cached in outputs/stage_c/cache/ (not committed).
"""
import hashlib
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.optimize import linear_sum_assignment
from scipy.sparse.csgraph import connected_components

import describe_clusters as dc
import dims_check as dk
import independent_clustering as ic
import independent_efa as ie
import matched_efa as me
import n_check as nc
from common import clustering as cl
from common import efa_math as em

NOFP = "--no-foreign-policy" in sys.argv
OUT = me.OUT / ("stage_c_nofp" if NOFP else "stage_c")
CACHE = me.OUT / "stage_c" / "cache"
MIN_LOAD, MIN_H2, HEYWOOD = 0.30, 0.20, 0.995
CLEAN, CROSS, MIN_CLEAN, MIN_BATTERIES = 0.40, 0.30, 2, 2
K_MIN, K_MAX = 3, 7
N_RESAMPLES, PHI = 50, 0.85
SEGMENTS = {0: "center-left moderates", 1: "religious conservatives", 2: "secular progressives", 3: "young disaffected"}


def stage_b_univariate(items, w, log):
    alive = list(items.columns)
    for c in list(alive):
        x = items[c].values
        ok = ~np.isnan(x)
        miss = 1 - np.average(ok, weights=w)
        modal = (pd.Series(w[ok]).groupby(x[ok]).sum() / w[ok].sum()).max()
        if miss > ie.MAX_MISSING:
            log.append((c, "B1 missing", miss)); alive.remove(c)
        elif modal > ie.MAX_MODAL:
            log.append((c, "B2 modal share", modal)); alive.remove(c)
    return alive


def redundancy(R, ids, log=None):
    """Party-blind: of each pair over |r| 0.70, strongest first, keep the member less correlated with the rest."""
    A = np.abs(R)
    np.fill_diagonal(A, 0)
    alive = set(range(len(ids)))
    pairs = sorted(((A[i, j], i, j) for i in range(len(ids)) for j in range(i + 1, len(ids)) if A[i, j] > ie.MAX_R),
                   reverse=True)
    for r, i, j in pairs:
        if i in alive and j in alive:
            rest = [m for m in alive if m not in (i, j)]
            mi, mj = A[i, rest].mean(), A[j, rest].mean()
            loser, other = (i, j) if mi >= mj else (j, i)
            alive.remove(loser)
            if log is not None:
                log.append((ids[loser], f"B4 redundant with {ids[other]} (mean |r| {A[loser, rest].mean():.3f} vs "
                                        f"{A[other, rest].mean():.3f})", r))
    return [ids[m] for m in sorted(alive)]


def weak_screen(R_all, ids_all, pool, k, log=None):
    alive = list(pool)
    while True:
        idx = [ids_all.index(c) for c in alive]
        L, Phi, h2 = me.fit(R_all[np.ix_(idx, idx)], k)
        A = np.abs(L)
        weak = [(c, A[i].max(), h2[i]) for i, c in enumerate(alive)
                if A[i].max() < MIN_LOAD or h2[i] < MIN_H2 or h2[i] >= HEYWOOD]
        if not weak:
            return alive
        for c, lmax, h in weak:
            if log is not None:
                log.append((c, f"C weak (max |l| {lmax:.2f}, h2 {h:.2f})", lmax))
            alive.remove(c)


def entry(L, alive, cw):
    A = np.abs(L)
    rows = []
    for j in range(L.shape[1]):
        others = np.delete(A, j, axis=1).max(axis=1)
        clean = [c for i, c in enumerate(alive) if A[i, j] >= CLEAN and others[i] < CROSS]
        bats = sorted({cw.battery_id[c] for c in clean})
        rows.append({"factor": j, "n_clean": len(clean), "n_batteries": len(bats),
                     "passes": len(clean) >= MIN_CLEAN and len(bats) >= MIN_BATTERIES,
                     "clean_items": "; ".join(clean), "batteries": "; ".join(bats)})
    return pd.DataFrame(rows)


def cache_path(b, ids):
    return CACHE / f"R_b{b}_{hashlib.md5(','.join(ids).encode()).hexdigest()[:8]}.npy"


def resample_matrix(b, idx, items, w, ids):
    path = cache_path(b, ids)
    if path.exists():
        return np.load(path)
    D = items.iloc[idx].reset_index(drop=True)
    R = em.regularize_corr(em.polychoric_matrix(D[ids], ids, w[idx], progress=False))
    np.save(path, R)
    return R


def subset(R, ids_full, ids):
    i = [ids_full.index(c) for c in ids]
    return R[np.ix_(i, i)]


def one_resample(b, idx, items, w, ids_full, ids, k):
    R = subset(resample_matrix(b, idx, items, w, ids_full), ids_full, ids)
    pool = redundancy(R, ids)
    return b, weak_screen(R, ids, pool, k)


def resample_entry(b, ids_full, retained, k, L_full, cw):
    L, _, _ = me.fit(subset(np.load(cache_path(b, ids_full)), ids_full, retained), k)
    P = (L_full.T @ L) / np.sqrt(np.outer((L_full ** 2).sum(0), (L ** 2).sum(0)))
    ri, ci = linear_sum_assignment(-np.abs(P))
    et = entry(L, retained, cw)
    out = {}
    for a, c in zip(ri, ci):
        out[a] = (abs(P[a, c]), bool(abs(P[a, c]) >= PHI and et.passes[c]))
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(exist_ok=True)
    items, w, _, cw = ie.load_pool()
    log = []
    ids_full = stage_b_univariate(items, w, log)
    R_full = em.regularize_corr(em.polychoric_matrix(items[ids_full], ids_full, w, progress=False))
    excluded = [c for c in ids_full if NOFP and cw.domain[c] == "foreign_policy_nation"]
    for c in excluded:
        log.append((c, "A excluded (foreign-policy sensitivity)", np.nan))
    ids = [c for c in ids_full if c not in excluded]
    R_all = subset(R_full, ids_full, ids)
    if excluded:
        print(f"foreign-policy sensitivity: {len(excluded)} items excluded", flush=True)
    pool = redundancy(R_all, ids, log)
    print(f"Stage B: {len(ids)} of {items.shape[1]} pass missing/modal; {len(pool)} after redundancy", flush=True)
    idx = [ids.index(c) for c in pool]
    ok = (~items[pool].isna()).values.astype(float)
    n_obs = int(np.median((ok.T @ ok)[np.triu_indices(len(pool), 1)]))
    k_pa, _, _ = em.parallel_analysis(R_all[np.ix_(idx, idx)], n_obs=n_obs, n_max=len(pool))
    k_map, _ = em.velicer_map(R_all[np.ix_(idx, idx)])
    k = int(np.clip(min(k_pa, k_map), K_MIN, K_MAX))
    print(f"k: parallel analysis {k_pa}, MAP {k_map} (n = {n_obs:,}); lower bounded to {K_MIN}-{K_MAX}: k = {k}", flush=True)

    rng = np.random.default_rng(42)
    draws = [rng.integers(0, len(items), len(items)) for _ in range(N_RESAMPLES)]
    res = Parallel(n_jobs=5)(delayed(one_resample)(b, draws[b], items, w, ids_full, ids, k) for b in range(N_RESAMPLES))
    surv = pd.Series(0, index=ids)
    for _, alive_b in res:
        surv[alive_b] += 1
    retained = [c for c in ids if surv[c] > N_RESAMPLES / 2]
    ret = pd.DataFrame({"item_id": ids, "survived_of_50": surv.values, "retained": [c in retained for c in ids],
                        "in_full_stage_b": [c in pool for c in ids], "label": [cw.label[c] for c in ids]})
    ret.to_csv(OUT / "retention.csv", index=False)
    full_weak = weak_screen(R_all, ids, pool, k)
    print(f"retained in > 25 of 50 resamples: {len(retained)} items (full-sample screens alone would keep "
          f"{len(full_weak)}; {len(set(retained) ^ set(full_weak))} differ)", flush=True)

    idx = [ids.index(c) for c in retained]
    R = R_all[np.ix_(idx, idx)]
    L, Phi, h2 = me.fit(R, k)
    k_pa2, _, _ = em.parallel_analysis(R, n_obs=n_obs, n_max=len(retained))
    k_map2, _ = em.velicer_map(R)
    print(f"full-sample fit at k = {k} on {len(retained)} items; recheck: parallel analysis {k_pa2}, MAP {k_map2}"
          f"{'' if min(k_pa2, k_map2) == k else ' (differs from the fitted k; disclosed, not looped)'}", flush=True)
    n_weak = int(((np.abs(L).max(1) < MIN_LOAD) | (h2 < MIN_H2) | (h2 >= HEYWOOD)).sum())
    print(f"weak items in the full-sample fit of the retained pool: {n_weak}; cross-loaders "
          f"(|l| >= 0.30 on 2+): {int(((np.abs(L) >= CROSS).sum(1) >= 2).sum())}", flush=True)
    ld = pd.DataFrame(L, index=retained, columns=[f"N{j + 1}" for j in range(k)]).round(3)
    ld.insert(0, "label", [cw.label[c][:70] for c in retained])
    ld.insert(1, "battery_id", [cw.battery_id[c] for c in retained])
    ld["h2"] = h2.round(3)
    ld.to_csv(OUT / f"loadings_k{k}.csv")

    et = entry(L, retained, cw)
    rs = Parallel(n_jobs=5)(delayed(resample_entry)(b, ids_full, retained, k, L, cw) for b in range(N_RESAMPLES))
    et["resample_pass"] = [sum(r[j][1] for r in rs) for j in range(k)]
    et["resample_matched"] = [sum(r[j][0] >= PHI for r in rs) for j in range(k)]
    et["median_phi"] = [round(float(np.median([r[j][0] for r in rs])), 3) for j in range(k)]
    et["clusters"] = et.passes & (et.resample_pass > N_RESAMPLES / 2)
    et["two_item_factor"] = et.n_clean == 2
    et["top_items"] = ["; ".join(f"{cw.label[c][:45]} ({L[retained.index(c), j]:+.2f})"
                                 for c in [retained[i] for i in np.argsort(-np.abs(L[:, j]))[:5]]) for j in range(k)]
    et.to_csv(OUT / "entry_test.csv", index=False)
    pd.DataFrame(log, columns=["item_id", "dropped_at", "value"]).assign(
        label=lambda d: d.item_id.map(cw.label)).to_csv(OUT / "screen_log.csv", index=False)
    with pd.option_context("display.width", 260, "display.max_colwidth", 150):
        print("\n" + et[["factor", "n_clean", "n_batteries", "passes", "resample_pass", "resample_matched", "median_phi",
                         "clusters", "top_items"]].to_string(index=False), flush=True)
    print(f"\nfactor correlations:\n{pd.DataFrame(Phi).round(2).to_string()}")
    passing = sorted(et.factor[et.clusters])
    print(f"\nclustering factors: {passing} of {k}")
    print("step 7 (state in-power): no state-government items in the pool; no adjustment", flush=True)
    if len(passing) < 2:
        print("fewer than two factors pass; no clustering")
        return

    D = items[retained]
    primary = np.abs(L).argmax(axis=1)
    answered = pd.DataFrame({j: D[[c for i, c in enumerate(retained) if primary[i] == j]].notna().mean(axis=1)
                             for j in passing})
    keep = (answered >= ic.MIN_SHARE_PER_FACTOR).all(axis=1).values
    F, _ = ic.available_scores(D[keep], w[keep], R, L, Phi)
    X = dk.residualize(F[:, passing], w[keep])
    print(f"respondents scored: {int(keep.sum()):,} of {len(D):,}", flush=True)

    s = nc.sweep(X)
    s.to_csv(OUT / "caps.csv", index=False)
    K = dk.kept(s)
    print(f"\nkept cap {K}\n{s.to_string(index=False)}", flush=True)
    seeds = [ic.job(X, K, "seed", i) for i in ic.SEEDS]
    S = ic.pairwise([f[3] for f in seeds])
    _, comp = connected_components(S >= 0.9, directed=False)
    modal = np.bincount(comp).argmax()
    lab = max((f for f, c in zip(seeds, comp) if c == modal), key=lambda f: f[4])[3]
    desc_all, keep_w = dc.descriptors()
    caseid = desc_all.caseid[keep_w].values[keep]
    out = pd.DataFrame({"caseid": caseid, "cluster": lab, **{f"F{j}": F[:, j] for j in range(k)}})
    out.to_csv(OUT / "clusters.csv", index=False)
    shares = pd.Series(w[keep]).groupby(lab).sum() / w[keep].sum()
    print(f"cluster shares (weighted): {shares.round(3).to_dict()}")

    prod = pd.read_csv(me.OUT / "clustering" / "independent_available" / "independent_clusters.csv")[["caseid", "cluster"]]
    m = out[["caseid", "cluster"]].merge(prod, on="caseid", suffixes=("_new", "_prod"))
    wm = pd.Series(w[keep], index=caseid).loc[m.caseid].values
    print(f"\noverlap with production segments: n = {len(m):,}, ARI {cl.ari(m.cluster_prod.values, m.cluster_new.values):.2f}")
    ct = pd.crosstab(m.cluster_prod.map(SEGMENTS), m.cluster_new, values=wm, aggfunc="sum", normalize="index").round(2)
    ct.to_csv(OUT / "crosswalk.csv")
    print(ct.to_string())
    if NOFP:
        main_run = pd.read_csv(me.OUT / "stage_c" / "clusters.csv")[["caseid", "cluster"]]
        m2 = out[["caseid", "cluster"]].merge(main_run, on="caseid", suffixes=("_nofp", "_main"))
        wm2 = pd.Series(w[keep], index=caseid).loc[m2.caseid].values
        print(f"\noverlap with the main Stage C run: n = {len(m2):,}, ARI {cl.ari(m2.cluster_main.values, m2.cluster_nofp.values):.2f}")
        ct2 = pd.crosstab(m2.cluster_main, m2.cluster_nofp, values=wm2, aggfunc="sum", normalize="index").round(2)
        ct2.to_csv(OUT / "crosswalk_main.csv")
        print(ct2.to_string())


if __name__ == "__main__":
    sys.exit(main())

"""ANES independent segmentation under the shared Stage C rule (docs/EFA_ITEM_SELECTION_ROBUSTNESS.md §3c).

Data: ANES 2024 Time Series CSV and codebook (2025-08-08 release), post weight V240108a, party ID V241227x.
Pool: config/anes_independent_pool.csv (155 items, battery_id tagged in c0e525c before this ran).

Choices fixed before running:
  Stage B  missing > 30% out; weighted modal share > 85% out; pairs with weighted polychoric |r| > 0.70 drop the
           higher party-ID R^2 member, strongest pair first. No party-ID cap.
  Matrix   one pairwise weighted polychoric over the post-Stage-B pool on every post-weighted respondent
           (available-item ruling, analysis/validation/DECISIONS.md 2026-11-02), regularized, subset as items leave.
           Parallel analysis takes n = the median pairwise-complete count across item pairs.
  k        parallel analysis (95th percentile) and Velicer's MAP (efa_math.velicer_map, shared with CES). If they
           disagree both are fit; a factor enters clustering only if it passes in both fits, matched at Tucker phi
           >= 0.85 on the items common to both final pools. Scores then come from the parallel-analysis fit.
  Reduce   PAF + oblimin at fixed k. Each pass: items with max |loading| < 0.30, h^2 < 0.20 or h^2 >= 0.995 drop
           together and the model refits; once none are weak, the cross-loader (|loading| >= 0.30 on 2+ factors)
           with the largest second-highest |loading| is removed and the model refits. Stop when neither remains.
           Parallel analysis and MAP rerun once on the final pool and are reported, not looped.
  Entry    a factor clusters if it has >= MIN_CLEAN clean items (|loading| >= 0.40 on it, < 0.30 on every other)
           from >= 2 batteries. MIN_CLEAN = 3 for ANES (researcher, 2026-11-02; the shared doc's 2 was set for
           CES's trust items). Factors that fail stay in the fit and are profiled, not clustered.
  Cluster  available-item Thomson scores from the full final fit; respondents answering >= half of each passing
           factor's items (items assigned by primary loading); the anchor residualization rule; the stability sweep
           and cap rule of independent_clustering.py (n_check.sweep); the modal solution across 20 seeds, best lower
           bound within it. Compared with the production four segments by ARI and crosswalk.

Writes outputs/stage_c/{screen_log.csv, loadings_k<k>.csv, entry_test.csv, caps.csv, clusters.csv, crosswalk.csv,
run.log}.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import sys

import numpy as np
import pandas as pd
from scipy.sparse.csgraph import connected_components

import describe_clusters as dc
import dims_check as dk
import independent_clustering as ic
import independent_efa as ie
import matched_efa as me
import n_check as nc
from common import clustering as cl
from common import efa_math as em

OUT = me.OUT / "stage_c"
MIN_LOAD, MIN_H2, HEYWOOD = 0.30, 0.20, 0.995
CLEAN, CROSS, MIN_CLEAN, MIN_BATTERIES, MATCH_PHI = 0.40, 0.30, 3, 2, 0.85
SEGMENTS = {0: "center-left moderates", 1: "religious conservatives", 2: "secular progressives", 3: "young disaffected"}


def stage_b(items, w, pid, cw, log):
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
    r2 = {c: ie.weighted_r2(items[c].values, pid, w) for c in alive}
    R = em.polychoric_matrix(items[alive], alive, w, progress=False)
    pairs = sorted(((abs(R[i, j]), alive[i], alive[j]) for i in range(len(alive)) for j in range(i + 1, len(alive))
                    if abs(R[i, j]) > ie.MAX_R), reverse=True)
    for r, a, b in pairs:
        if a in alive and b in alive:
            loser, other = (a, b) if r2[a] >= r2[b] else (b, a)
            log.append((loser, f"B4 redundant with {other}", r)); alive.remove(loser)
    return alive


def reduce(R_all, ids_all, k, log, tag):
    alive = list(ids_all)
    while True:
        idx = [ids_all.index(c) for c in alive]
        L, Phi, h2 = me.fit(R_all[np.ix_(idx, idx)], k)
        A = np.abs(L)
        weak = [(c, A[i].max(), h2[i]) for i, c in enumerate(alive)
                if A[i].max() < MIN_LOAD or h2[i] < MIN_H2 or h2[i] >= HEYWOOD]
        if weak:
            for c, lmax, h in weak:
                log.append((c, f"C{tag} weak (max |l| {lmax:.2f}, h2 {h:.2f})", lmax))
                alive.remove(c)
            continue
        second = np.sort(A, axis=1)[:, -2]
        cross = [(second[i], c) for i, c in enumerate(alive) if (A[i] >= CROSS).sum() >= 2]
        if not cross:
            return alive, L, Phi, h2
        s, c = max(cross)
        log.append((c, f"C{tag} cross-loader (second |l| {s:.2f})", s))
        alive.remove(c)


def entry(L, alive, cw):
    A = np.abs(L)
    rows = []
    for j in range(L.shape[1]):
        others = np.delete(A, j, axis=1).max(axis=1)
        clean = [c for i, c in enumerate(alive) if A[i, j] >= CLEAN and others[i] < CROSS]
        bats = sorted({cw.battery_id[c] for c in clean})
        top = [alive[i] for i in np.argsort(-A[:, j])[:4]]
        rows.append({"factor": j, "n_clean": len(clean), "n_batteries": len(bats),
                     "passes": len(clean) >= MIN_CLEAN and len(bats) >= MIN_BATTERIES,
                     "clean_items": "; ".join(clean), "batteries": "; ".join(bats),
                     "top_items": "; ".join(f"{cw.label[c][:45]} ({L[alive.index(c), j]:+.2f})" for c in top)})
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    items, w, pid, cw = ie.load_pool()
    log = []
    pool = stage_b(items, w, pid, cw, log)
    print(f"Stage B: {len(pool)} of {items.shape[1]} items remain", flush=True)
    R_all = em.regularize_corr(em.polychoric_matrix(items[pool], pool, w, progress=False))
    ok = (~items[pool].isna()).values.astype(float)
    pair_n = ok.T @ ok
    n_obs = int(np.median(pair_n[np.triu_indices(len(pool), 1)]))
    k_pa, _, _ = em.parallel_analysis(R_all, n_obs=n_obs)
    k_map, _ = em.velicer_map(R_all)
    print(f"k: parallel analysis {k_pa}, MAP {k_map} (n for parallel analysis = {n_obs:,})", flush=True)

    fits = {}
    for k in sorted({k_pa, k_map}):
        alive, L, Phi, h2 = reduce(R_all, pool, k, log, k)
        idx = [pool.index(c) for c in alive]
        R = R_all[np.ix_(idx, idx)]
        k_pa2, _, _ = em.parallel_analysis(R, n_obs=n_obs)
        k_map2, _ = em.velicer_map(R)
        et = entry(L, alive, cw)
        fits[k] = (alive, L, Phi, et)
        ld = pd.DataFrame(L, index=alive, columns=[f"N{j + 1}" for j in range(k)]).round(3)
        ld.insert(0, "label", [cw.label[c][:70] for c in alive])
        ld.insert(1, "battery_id", [cw.battery_id[c] for c in alive])
        ld["h2"] = h2.round(3)
        ld.to_csv(OUT / f"loadings_k{k}.csv")
        print(f"\nk = {k}: {len(alive)} items after reduction; recheck on final pool: parallel analysis {k_pa2}, "
              f"MAP {k_map2}", flush=True)
        with pd.option_context("display.width", 250, "display.max_colwidth", 120):
            print(et[["factor", "n_clean", "n_batteries", "passes", "top_items"]].to_string(index=False), flush=True)

    alive, L, Phi, et = fits[k_pa]
    passing = set(et.factor[et.passes])
    if k_map != k_pa:
        a2, L2, _, et2 = fits[k_map]
        common = [c for c in alive if c in a2]
        Lc = L[[alive.index(c) for c in common]]
        L2c = L2[[a2.index(c) for c in common]]
        both = set()
        for m in me.cg.match_factors(Lc, L2c):
            if abs(m["phi"]) >= MATCH_PHI and m["factor_1"] in passing and et2.passes[m["factor_2"]]:
                both.add(m["factor_1"])
        print(f"\nfactors passing in both fits (phi >= {MATCH_PHI}): {sorted(both)} of {sorted(passing)}")
        passing = both
    et["clusters"] = et.factor.isin(passing)
    et.to_csv(OUT / "entry_test.csv", index=False)
    pd.DataFrame(log, columns=["item_id", "dropped_at", "value"]).assign(
        label=lambda d: d.item_id.map(cw.label)).to_csv(OUT / "screen_log.csv", index=False)
    print(f"\nclustering factors: {sorted(passing)} of {L.shape[1]}")
    if len(passing) < 2:
        print("fewer than two factors pass; no clustering")
        return

    D = items[alive]
    primary = np.abs(L).argmax(axis=1)
    answered = pd.DataFrame({j: D[[c for i, c in enumerate(alive) if primary[i] == j]].notna().mean(axis=1)
                             for j in passing})
    keep = (answered >= ic.MIN_SHARE_PER_FACTOR).all(axis=1).values
    idx = [pool.index(c) for c in alive]
    F, _ = ic.available_scores(D[keep], w[keep], R_all[np.ix_(idx, idx)], L, Phi)
    cols = sorted(passing)
    X = dk.residualize(F[:, cols], w[keep])
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
    out = pd.DataFrame({"caseid": caseid, "cluster": lab, **{f"F{j}": F[:, j] for j in range(L.shape[1])}})
    out.to_csv(OUT / "clusters.csv", index=False)

    prod = pd.read_csv(me.OUT / "clustering" / "independent_available" / "independent_clusters.csv")[["caseid", "cluster"]]
    m = out[["caseid", "cluster"]].merge(prod, on="caseid", suffixes=("_new", "_prod"))
    wm = pd.Series(w[keep], index=caseid).loc[m.caseid].values
    print(f"\noverlap with production segments: n = {len(m):,}, ARI {cl.ari(m.cluster_prod.values, m.cluster_new.values):.2f}")
    ct = pd.crosstab(m.cluster_prod.map(SEGMENTS), m.cluster_new, values=wm, aggfunc="sum", normalize="index").round(2)
    ct.to_csv(OUT / "crosswalk.csv")
    print(ct.to_string())


if __name__ == "__main__":
    sys.exit(main())

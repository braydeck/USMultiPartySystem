"""Stage C (docs/EFA_ITEM_SELECTION_ROBUSTNESS.md §3c): which factors may define the CES clustering?

Data: CES 2024 Common Content, the 49,432 respondents with commonpostweight > 0 (item_pool.load: recodes, pid7).
Battery tags: analysis/efa/ces_item_pool.csv (committed 41a392f before this ran).
Production names: outputs/rescore_scores.csv (rescored five factors) for score-correlation naming.

Pools (--pool):
  p24     the 24 production items as ruled ("same 24 items", DECISIONS.md 2026-11-02), no re-screen
  p24b    the 24 after Stage B as written in §3c (pairs with |r| > 0.70: drop the higher party-ID R^2 member).
          Production kept four such pairs as multiple indicators; this shows what the written rule does to them.
  pool69  the 69-item Stage A pool after Stage B (item_pool.py stages 1-4: missingness, modal share, redundancy)
  fp24    the 24 as ruled plus the foreign-policy binaries (item_pool.FP); Stage B screens only the binaries
  fpmain  the 69-item pool plus the foreign-policy binaries, all through Stage B
  pool69nat  the 69-item pool minus state-government trust and state election fairness (sensitivity check)
          (checkbox items in the clustering are an open ruling, §3c; these two pools are the evidence for it)
Matrix: weighted polychoric, listwise on respondents complete on the screened pool, computed once and subset as items
leave (so every fit in one pool uses one sample). Parallel analysis n capped at 20,000 (CES convention).

§3c as implemented:
  2. k from parallel analysis (efa_math.parallel_analysis, 95th pct) and Velicer's MAP (efa_math.velicer_map). Tie rule
     (researcher 2026-11-02): if they differ, the lower k is the fit used. The script still fits both and prints the
     original both-fits comparison (one-to-one Tucker phi >= 0.85 on shared items), which is reported alongside.
  3. At fixed k: PAF + oblimin; drop weak items (max |l| < 0.30, h2 < 0.20, or h2 >= 0.995) together and refit; when
     none are weak, drop the cross-loader (|l| >= 0.30 on two or more factors) with the largest second-highest |l|
     and refit; repeat until neither remains. Then parallel analysis and MAP once more on the final items, reported.
  4. Entry test (minimum lowered from 3 to 2 by the researcher 2026-11-02): >= 2 clean items (|l| >= 0.40 on the factor, < 0.30 on every other) from >= 2 batteries.
Names: a factor takes a production name when its scores correlate |r| >= 0.7 with that rescored factor
(Hungarian one-to-one); otherwise it is named by its top items. Naming is after the test and plays no part in it.
Writes outputs/stage_c/<pool>_{factors,loadings,removed}.csv; log outputs/stage_c_<pool>_run.log via tee.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import argparse

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.optimize import linear_sum_assignment

import item_pool as ip
import reestimate_loadings as rl

em, cg, eu = rl.em, rl.cg, rl.eu
OUT = rl.OUT / "stage_c"
TAGS = rl.ROOT / "analysis/efa/ces_item_pool.csv"
# pool69nat: sensitivity check (2026-11-03, after results were seen): the two items about the respondent's own
# state, whose answers flip with which party carried the state, removed from the 69-item pool
STATE_TRUST = ("CC24_424", "CC24_421_2")
MIN_LOAD, MIN_H2, HEYWOOD, CROSS, CLEAN, MIN_CLEAN, MIN_BATT, PHI_SAME, NAME_R = 0.30, 0.20, 0.995, 0.30, 0.40, 2, 2, 0.85, 0.7


def stage_b(X, w, pid, items, Rpw, log, fixed=()):
    alive = list(items)
    for c in [c for c in alive if c not in fixed]:
        x = X[c].values
        ok = ~np.isnan(x)
        miss = 1 - w[ok].sum() / w.sum()
        modal = (pd.Series(w[ok]).groupby(x[ok]).sum() / w[ok].sum()).max()
        if miss > ip.MAX_MISSING or modal > ip.MAX_MODAL:
            log.append({"item": c, "stage": "B missing" if miss > ip.MAX_MISSING else "B modal share",
                        "value": round(float(max(miss, modal) if miss > ip.MAX_MISSING else modal), 3)})
            alive.remove(c)
    r2 = {c: ip.rr_weighted_r2(X[c].values, pid, w) for c in alive}
    pairs = sorted(((abs(Rpw.loc[a, b]), a, b) for i, a in enumerate(alive) for b in alive[i + 1:]
                    if abs(Rpw.loc[a, b]) > ip.MAX_R), reverse=True)
    for r, a, b in pairs:
        if a in alive and b in alive:
            cand = [c for c in (a, b) if c not in fixed]
            if not cand:
                continue
            loser = max(cand, key=lambda c: r2[c])
            log.append({"item": loser, "stage": f"B redundant with {b if loser == a else a}", "value": round(r, 3)})
            alive.remove(loser)
    return alive


def listwise_matrix(X, w, items):
    D = X[items].dropna()
    wD = w[D.index.values]
    pairs = [(i, j) for i in range(len(items)) for j in range(i + 1, len(items))]
    vals = Parallel(n_jobs=11)(delayed(em.weighted_polychoric)(D[items[i]].values, D[items[j]].values, wD) for i, j in pairs)
    M = np.eye(len(items))
    for (i, j), r in zip(pairs, vals):
        M[i, j] = M[j, i] = r
    return pd.DataFrame(em.regularize_corr(M), index=items, columns=items), D.index.values


def fit(R, k):
    L_un, _, _ = em.paf(R.values.copy(), k)
    L, Phi = em.oblimin(L_un)
    return L, Phi, np.clip(np.diag(L @ Phi @ L.T), 0, None)


def pick_k(R, n):
    k_pa, ev, thr = em.parallel_analysis(R.values, min(n, ip.PA_CAP))
    k_map, curve = em.velicer_map(R.values)
    return k_pa, k_map


def remove_at_k(R, items, k, removed, tag):
    items = list(items)
    while True:
        L, Phi, h2 = fit(R.loc[items, items], k)
        A = np.abs(L)
        weak = [c for c, row, h in zip(items, A, h2) if row.max() < MIN_LOAD or h < MIN_H2 or h >= HEYWOOD]
        if weak:
            for c in weak:
                i = items.index(c)
                why = "Heywood (h2 >= 0.995)" if h2[i] >= HEYWOOD else "weak"
                removed.append({"fit": tag, "item": c, "reason": why, "max_loading": A[i].max(), "h2": h2[i]})
            items = [c for c in items if c not in weak]
            continue
        second = np.sort(A, axis=1)[:, -2] if k > 1 else np.zeros(len(items))
        cross = second >= CROSS
        if not cross.any():
            return items, L, Phi, h2
        i = int(np.argmax(np.where(cross, second, -1)))
        removed.append({"fit": tag, "item": items[i], "reason": "cross-loader", "max_loading": A[i].max(),
                        "second_loading": second[i], "h2": h2[i]})
        items.pop(i)


def entry_test(items, L, battery):
    A = np.abs(L)
    rows = []
    for j in range(L.shape[1]):
        others = np.delete(A, j, axis=1).max(axis=1) if L.shape[1] > 1 else np.zeros(len(items))
        clean = [c for c, a, o in zip(items, A[:, j], others) if a >= CLEAN and o < CROSS]
        bats = sorted({battery[c] for c in clean})
        rows.append({"factor": j, "clean_items": len(clean), "batteries": len(bats),
                     "two_item_factor": len(clean) == 2,
                     "passes": len(clean) >= MIN_CLEAN and len(bats) >= MIN_BATT,
                     "clean": " ".join(clean), "battery_ids": " | ".join(bats)})
    return pd.DataFrame(rows)


def name_factors(D, w_D, caseid_D, items, R, L, Phi):
    s = pd.read_csv(rl.OUT / "rescore_scores.csv").set_index("caseid")
    Z, _, _ = em.weighted_standardize(D[items].values.astype(float), w_D)
    F, _ = em.thomson_scores(Z, R.loc[items, items].values, L, Phi)
    keep = np.isin(caseid_D, s.index.values)
    P = s.loc[caseid_D[keep], ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]].values
    C = np.array([[np.corrcoef(P[:, a], F[keep, b])[0, 1] for b in range(L.shape[1])] for a in range(5)])
    ri, ci = linear_sum_assignment(-np.abs(C))
    names = {}
    for a, b in zip(ri, ci):
        if abs(C[a, b]) >= NAME_R:
            names[b] = f"{rl.NAMES[a]} (r {abs(C[a, b]):.2f})"
    for b in range(L.shape[1]):
        if b not in names:
            top = np.argsort(-np.abs(L[:, b]))[:3]
            best = int(np.abs(C[:, b]).argmax())
            names[b] = f"new: {', '.join(items[t] for t in top)} (closest {rl.NAMES[best]} r {abs(C[best, b]):.2f})"
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", choices=["p24", "p24b", "pool69", "pool69nat", "fp24", "fpmain"], required=True)
    pool = ap.parse_args().pool
    OUT.mkdir(parents=True, exist_ok=True)
    tags = pd.read_csv(TAGS)
    battery = dict(zip(tags.item_id, tags.battery_id))
    X, w, pid, caseid = ip.load()
    Rpw = ip.poly_all(X, w)
    log = []
    if pool == "p24":
        items = list(eu.ITEMS_24)
    elif pool == "fp24":
        items = stage_b(X, w, pid, eu.ITEMS_24 + ip.FP, Rpw, log, fixed=set(eu.ITEMS_24))
    else:
        items = stage_b(X, w, pid, {"p24b": eu.ITEMS_24, "pool69": ip.POOL, "fpmain": ip.POOL + ip.FP,
                                   "pool69nat": [c for c in ip.POOL if c not in STATE_TRUST]}[pool], Rpw, log)
    print(f"{pool}: {len(items)} items after Stages A/B; dropped {[(d['item'], d['stage']) for d in log]}", flush=True)

    R, rows = listwise_matrix(X, w, items)
    D, w_D, caseid_D = X.loc[rows], w[rows], caseid[rows]
    k_pa, k_map = pick_k(R, len(rows))
    print(f"listwise n {len(rows):,}; parallel analysis k = {k_pa}, MAP k = {k_map}", flush=True)

    removed, fits = [], {}
    for k in sorted({k_pa, k_map}):
        tag = f"k{k}"
        final, L, Phi, h2 = remove_at_k(R, items, k, removed, tag)
        k2_pa, k2_map = pick_k(R.loc[final, final], len(rows))
        test = entry_test(final, L, battery)
        names = name_factors(D, w_D, caseid_D, final, R, L, Phi)
        test.insert(1, "name", test.factor.map(names))
        test.insert(0, "fit", tag)
        fits[k] = (final, L, test)
        n_rm = sum(r["fit"] == tag for r in removed)
        print(f"\n[{tag}] {len(final)} items after removing {n_rm} "
              f"({sum(r['fit'] == tag and r['reason'] == 'cross-loader' for r in removed)} cross-loaders); "
              f"rerun on the final items: parallel analysis k = {k2_pa}, MAP k = {k2_map}"
              f"{'' if (k2_pa == k and k2_map == k) else '  (differs from the fitted k; disclosed, not looped)'}")
        print(test.drop(columns=["fit", "factor"]).to_string(index=False))
        pd.DataFrame(L, index=final, columns=[f"{tag}_F{j}" for j in range(k)]).assign(h2=h2,
            battery=[battery[c] for c in final]).to_csv(OUT / f"{pool}_loadings_{tag}.csv")

    if len(fits) == 2:
        (ka, (ia, La, ta)), (kb, (ib, Lb, tb)) = sorted(fits.items())
        shared = [c for c in ia if c in ib]
        A_, B_ = La[[ia.index(c) for c in shared]], Lb[[ib.index(c) for c in shared]]
        P = np.array([[abs(cg.tucker_phi(A_[:, a], B_[:, b])) for b in range(kb)] for a in range(ka)])
        ri, ci = linear_sum_assignment(-P)
        both = []
        for a, b in zip(ri, ci):
            ok = P[a, b] >= PHI_SAME and ta.passes[a] and tb.passes[b]
            both.append({"factor_k%d" % ka: ta.name[a], "factor_k%d" % kb: tb.name[b], "phi": round(P[a, b], 3),
                         f"passes_k{ka}": ta.passes[a], f"passes_k{kb}": tb.passes[b], "enters_clustering": ok})
        both = pd.DataFrame(both)
        print(f"\nPA and MAP disagree: factors matched across k{ka} and k{kb} on {len(shared)} shared items")
        print(both.to_string(index=False))
        both.to_csv(OUT / f"{pool}_both_fits.csv", index=False)
    factors = pd.concat([t for _, _, t in fits.values()])
    factors.to_csv(OUT / f"{pool}_factors.csv", index=False)
    pd.DataFrame(log + removed).to_csv(OUT / f"{pool}_removed.csv", index=False)


if __name__ == "__main__":
    main()

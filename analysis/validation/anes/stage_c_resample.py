"""How often does each ANES Stage C factor form? The full §3c factor selection rerun on 20 bootstrap resamples.

Data: ANES 2024 Time Series (2025-08-08 release), post weight V240108a, pool config/anes_independent_pool.csv
(corrected 2026-11-03: V242253x). Rule and code: stage_c.py (Stage B, pairwise polychoric, parallel analysis and
MAP, k = the lower, reduce, entry test), with parallel analysis counted over every eigenvalue (n_max = number of
items; efa_math's default stops counting at 10).

Each resample draws 5,276 respondents with replacement (rng 42 + b), keeping their weights, and runs the whole
selection. Polychoric correlations are pairwise, so the Stage B matrix is subset rather than recomputed for the pool.

Matching: each resample factor is compared with every reference factor by Tucker phi over the items both fits kept
(at least 2 items loading |l| >= 0.30 on each side). A reference "forms" in a resample when some factor there has
|phi| >= 0.85 with it, and "clusters" when such a factor also passes the entry test. Matching is per reference, not
exclusive, so two references that describe the same factor can both form. References: the full-data fit
(outputs/stage_c/loadings_k*.csv) plus any extra loadings files passed with --ref NAME=PATH:COLUMN.

Writes outputs/stage_c_resample/{per_resample.csv, factors_b<b>.csv, formation.csv, unmatched.csv, run.log}.
Run with --match-only to redo the matching on saved fits.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import sys

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

import independent_efa as ie
import matched_efa as me
import stage_c as sc
from common import efa_math as em

OUT = me.OUT / "stage_c_resample"
N_RESAMPLES = 20
PHI = 0.85


def stage_b_with_R(items, w, pid):
    alive = list(items.columns)
    for c in list(alive):
        x = items[c].values
        ok = ~np.isnan(x)
        miss = 1 - np.average(ok, weights=w)
        modal = (pd.Series(w[ok]).groupby(x[ok]).sum() / w[ok].sum()).max()
        if miss > ie.MAX_MISSING or modal > ie.MAX_MODAL:
            alive.remove(c)
    r2 = {c: ie.weighted_r2(items[c].values, pid, w) for c in alive}
    R = em.polychoric_matrix(items[alive], alive, w, progress=False)
    pairs = sorted(((abs(R[i, j]), alive[i], alive[j]) for i in range(len(alive)) for j in range(i + 1, len(alive))
                    if abs(R[i, j]) > ie.MAX_R), reverse=True)
    pool = list(alive)
    for r, a, b in pairs:
        if a in pool and b in pool:
            pool.remove(a if r2[a] >= r2[b] else b)
    idx = [alive.index(c) for c in pool]
    return pool, em.regularize_corr(R[np.ix_(idx, idx)])


def one(b, items, w, pid, cw):
    idx = np.random.default_rng(42 + b).integers(0, len(items), len(items))
    D = items.iloc[idx].reset_index(drop=True)
    pool, R = stage_b_with_R(D, w[idx], pid[idx])
    ok = (~D[pool].isna()).values.astype(float)
    n_obs = int(np.median((ok.T @ ok)[np.triu_indices(len(pool), 1)]))
    k_pa, _, _ = em.parallel_analysis(R, n_obs=n_obs, n_max=len(pool))
    k_map, _ = em.velicer_map(R)
    k = min(k_pa, k_map)
    alive, L, _, _ = sc.reduce(R, pool, k, [], k)
    et = sc.entry(L, alive, cw)
    fac = pd.DataFrame(L, index=alive, columns=[f"N{j + 1}" for j in range(k)])
    fac.to_csv(OUT / f"factors_b{b}.csv")
    et.to_csv(OUT / f"entry_b{b}.csv", index=False)
    return {"resample": b, "n_stage_b": len(pool), "k_pa": k_pa, "k_map": k_map, "k": k, "n_items": len(alive),
            "n_passing": int(et.passes.sum())}


def phi(a, b):
    items = a.index.intersection(b.index)
    x, y = a[items].values, b[items].values
    if (np.abs(x) >= 0.30).sum() < 2 or (np.abs(y) >= 0.30).sum() < 2:
        return 0.0
    return float(x @ y / np.sqrt((x @ x) * (y @ y)))


def references(cw):
    full = sorted((me.OUT / "stage_c").glob("loadings_k*.csv"))[-1]
    ld = pd.read_csv(full, index_col=0)
    et = pd.read_csv(me.OUT / "stage_c" / "entry_test.csv")
    refs = {}
    for j, row in et.iterrows():
        top = ld[f"N{j + 1}"].abs().sort_values(ascending=False).index[:2]
        refs[f"full F{j}: " + " / ".join(cw.label[t][:28] for t in top)] = ld[f"N{j + 1}"]
    for arg in sys.argv[1:]:
        if arg.startswith("--ref="):
            name, spec = arg[6:].split("=", 1)
            path, col = spec.rsplit(":", 1)
            refs[name] = pd.read_csv(path, index_col=0)[col]
    return refs


def match(cw):
    per = pd.read_csv(OUT / "per_resample.csv")
    refs = references(cw)
    form = {r: [0, 0] for r in refs}
    unmatched = []
    for b in per["resample"]:
        F = pd.read_csv(OUT / f"factors_b{b}.csv", index_col=0)
        et = pd.read_csv(OUT / f"entry_b{b}.csv")
        P = np.array([[abs(phi(F[col], ref)) for ref in refs.values()] for col in F.columns])
        for i, name in enumerate(refs):
            hit = P[:, i] >= PHI
            form[name][0] += bool(hit.any())
            form[name][1] += bool((hit & et.passes.values).any())
        for j, col in enumerate(F.columns):
            best = (P[j].max(), list(refs)[P[j].argmax()])
            if best[0] < PHI and et.passes[j]:
                top = F[col].abs().sort_values(ascending=False).index[:3]
                unmatched.append({"resample": b, "best_phi": round(best[0], 2), "best_ref": best[1],
                                  "top_items": "; ".join(f"{cw.label[t][:40]} ({F[col][t]:+.2f})" for t in top)})
    fm = pd.DataFrame([{"reference": r, "forms": v[0], "clusters": v[1], "of": len(per)} for r, v in form.items()])
    fm.to_csv(OUT / "formation.csv", index=False)
    pd.DataFrame(unmatched).to_csv(OUT / "unmatched.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_colwidth", 140):
        print(per.to_string(index=False))
        print(f"\nk across resamples: {per.k.value_counts().sort_index().to_dict()}")
        print(f"\nhow often each reference factor forms (|phi| >= {PHI}) and passes the entry test:")
        print(fm.to_string(index=False))
        print(f"\npassing factors that match no reference: {len(unmatched)}")
        if unmatched:
            print(pd.DataFrame(unmatched).to_string(index=False))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    items, w, pid, cw = ie.load_pool()
    if "--match-only" not in sys.argv:
        rows = Parallel(n_jobs=10)(delayed(one)(b, items, w, pid, cw) for b in range(N_RESAMPLES))
        pd.DataFrame(rows).to_csv(OUT / "per_resample.csv", index=False)
    match(cw)


if __name__ == "__main__":
    main()

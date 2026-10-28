"""Independent EFA: what factor structure does ANES 2024 produce on its own attitude pool?

Data: ANES 2024 Time Series CSV (2025-08-08 release). Stage A pool:
config/anes_independent_pool.csv (155 policy/attitude items, including the trust and
election-fairness items; spending battery, thermometers, approvals, ideology placements,
issue-importance ratings and multi-selects excluded). Weight V240108a; party ID V241227x.

Stage B screen, the CES rules from docs/EFA_ITEM_SELECTION_ROBUSTNESS.md applied in order:
  1. drop items missing for > 30% of post-weighted respondents
  2. drop items whose weighted modal category share > 85%
  3. drop partisan proxies: weighted linear R^2 on 7-pt party ID > 0.34 (cross-wave convention)
  4. for pairs with weighted polychoric |r| > 0.70, drop the higher-party-ID-R^2 member
     (greedy, strongest pair first)
  5. listwise, parallel analysis picks k; PAF + oblimin; drop items with max |loading| < 0.30
     or h^2 < 0.20 (or Heywood h^2 >= 0.995); refit until stable
Bridge to the matched solution: Thomson scores for both solutions on the respondents
complete on both item sets, correlated and Hungarian-matched.
"""
import sys

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

import matched_efa as me
import recode_matched as rm
from common import efa_math as em

POOL = me.HERE / "config" / "anes_independent_pool.csv"
PID = "V241227x"
# Sensitivity run (--keep-election): the four election-fairness items are exempt from stages 4-5,
# to see whether they form their own factor when not screened out. Not the primary fit.
ELECTION = ["V241314", "V241315", "V242207", "V242430"]
KEEP_ELECTION = "--keep-election" in sys.argv
SUFFIX = "_keep_election" if KEEP_ELECTION else ""
MAX_MISSING, MAX_MODAL, MAX_PID_R2, MAX_R, MIN_LOAD, MIN_H2 = 0.30, 0.85, 0.34, 0.70, 0.30, 0.20


def weighted_r2(y, x, w):
    ok = ~(np.isnan(y) | np.isnan(x))
    y, x, w = y[ok], x[ok], w[ok] / w[ok].mean()
    X = np.column_stack([np.ones_like(x), x])
    beta = np.linalg.solve(X.T @ (X * w[:, None]), X.T @ (w * y))
    resid = y - X @ beta
    ybar = np.average(y, weights=w)
    return 1 - np.sum(w * resid ** 2) / np.sum(w * (y - ybar) ** 2)


def load_pool():
    cw = pd.read_csv(POOL)
    cols = sorted({s for src in cw.anes_sources for s in src.split("|")} | {rm.WEIGHT, PID})
    raw = pd.read_csv(rm.ANES_CSV, usecols=cols, low_memory=False)
    w = pd.to_numeric(raw[rm.WEIGHT], errors="coerce").values
    pid = pd.to_numeric(raw[PID], errors="coerce").where(lambda s: s.between(1, 7)).values
    items = pd.DataFrame({r.item_id: rm.recode_row(raw, r.anes_sources, r.anes_map) for r in cw.itertuples()})
    keep = ~np.isnan(w) & (w > 0)
    return items[keep].reset_index(drop=True), w[keep], pid[keep], cw.set_index("item_id")


def fit_scores(D, w, k):
    ids = list(D.columns)
    R = em.regularize_corr(em.polychoric_matrix(D, ids, w, progress=False))
    L, Phi, h2 = me.fit(R, k)
    Z, _, _ = em.weighted_standardize(D.values.astype(float), w)
    F, _ = em.thomson_scores(Z, R, L, Phi)
    return R, L, Phi, h2, F


def main():
    items, w, pid, cw = load_pool()
    log = []

    def drop(item, stage, value):
        log.append({"item_id": item, "label": cw.label[item], "dropped_at": stage, "value": round(float(value), 3)})

    alive = list(items.columns)
    for c in list(alive):
        x = items[c].values
        miss = 1 - np.average(~np.isnan(x), weights=w)
        ok = ~np.isnan(x)
        modal = (pd.Series(w[ok]).groupby(x[ok]).sum() / w[ok].sum()).max()
        if miss > MAX_MISSING:
            drop(c, "1 missing", miss); alive.remove(c)
        elif modal > MAX_MODAL:
            drop(c, "2 modal share", modal); alive.remove(c)
    r2 = {c: weighted_r2(items[c].values, pid, w) for c in alive}
    for c in list(alive):
        if r2[c] > MAX_PID_R2:
            drop(c, "3 party-ID R2", r2[c]); alive.remove(c)

    print(f"Stage B 1-3: {len(alive)} of {items.shape[1]} items remain; pairwise polychoric for redundancy...", flush=True)
    R_pw = em.polychoric_matrix(items[alive], alive, w, progress=False)
    pairs = sorted(((abs(R_pw[i, j]), alive[i], alive[j]) for i in range(len(alive)) for j in range(i + 1, len(alive))
                    if abs(R_pw[i, j]) > MAX_R), reverse=True)
    for r, a, b in pairs:
        if a in alive and b in alive:
            loser = a if r2[a] >= r2[b] else b
            if KEEP_ELECTION and loser in ELECTION:
                other = b if loser == a else a
                if other in ELECTION:
                    continue
                loser = other
            drop(loser, f"4 redundant with {b if loser == a else a}", r); alive.remove(loser)

    while True:
        D = items[alive].dropna()
        wD = w[D.index.values]
        R = em.regularize_corr(em.polychoric_matrix(D.reset_index(drop=True), alive, wD, progress=False))
        k, ev, thr = em.parallel_analysis(R, n_obs=len(D))
        L, Phi, h2 = me.fit(R, k)
        weak = [c for c, row, h in zip(alive, L, h2) if (np.abs(row).max() < MIN_LOAD or h < MIN_H2 or h >= 0.995)
                and not (KEEP_ELECTION and c in ELECTION)]
        print(f"  listwise n = {len(D):,}, items = {len(alive)}, parallel-analysis k = {k}, weak = {len(weak)}", flush=True)
        if not weak:
            break
        for c in weak:
            i = alive.index(c)
            drop(c, "5 weak loading/communality", max(np.abs(L[i]).max(), h2[i])); alive.remove(c)

    log = pd.DataFrame(log)
    log.to_csv(me.OUT / f"independent_screen_log{SUFFIX}.csv", index=False)
    print("\nDropped by stage:", log.dropped_at.str[0].value_counts().sort_index().to_dict())

    fn = [f"N{j + 1}" for j in range(k)]
    load = pd.DataFrame(L, index=alive, columns=fn).round(3)
    load["h2"] = h2.round(3)
    load.insert(0, "label", [cw.label[c][:60] for c in alive])
    load.insert(1, "domain", [cw.domain[c] for c in alive])
    load["primary"] = load[fn].abs().idxmax(axis=1)
    load = load.sort_values(["primary", "h2"], ascending=[True, False])
    load.to_csv(me.OUT / f"independent_loadings{SUFFIX}.csv")
    pd.DataFrame(Phi, index=fn, columns=fn).round(3).to_csv(me.OUT / f"independent_factor_corr{SUFFIX}.csv")
    pd.DataFrame({"factor": range(1, 13), "eigen": ev[:12].round(3), "threshold": np.asarray(thr)[:12].round(3)}).to_csv(
        me.OUT / f"independent_parallel{SUFFIX}.csv", index=False)
    pd.set_option("display.width", 250, "display.max_rows", 200)
    print(f"\nFinal: {len(alive)} items, listwise n = {len(D):,}, k = {k}")
    for f in fn:
        sub = load[load.primary == f]
        print(f"\n--- {f} ({len(sub)} items) ---")
        print(sub[["label", "domain", f, "h2"]].to_string())
    print("\nFactor correlations:\n", pd.DataFrame(Phi, index=fn, columns=fn).round(2))

    # bridge: both solutions scored on respondents complete on both item sets
    raw_m, items_m, _ = rm.load_matched()
    wm = pd.to_numeric(raw_m[rm.WEIGHT], errors="coerce").values
    keep_m = ~np.isnan(wm) & (wm > 0)
    M = items_m[keep_m].reset_index(drop=True)
    both = M.notna().all(axis=1) & items[alive].notna().all(axis=1)
    wb = w[both.values]
    _, Lm, _, _, Fm = fit_scores(M[both].reset_index(drop=True), wb, 5)
    _, _, _, _, Fn = fit_scores(items[alive][both].reset_index(drop=True), wb, k)
    C = np.array([[np.corrcoef(Fm[:, a], Fn[:, b])[0, 1] for b in range(k)] for a in range(5)])
    # name the refit matched factors by Tucker match to the full-sample matched loadings
    ces_like = pd.read_csv(me.OUT / "matched_phi_vs_canonical_k5.csv").set_index("anes_factor").ces_factor
    L_full = pd.read_csv(me.OUT / "matched_loadings_anes_k5.csv", index_col=0)[[f"A{j + 1}" for j in range(5)]].values
    name_of = {m["factor_2"]: ces_like[f"A{m['factor_1'] + 1}"] for m in me.cg.match_factors(L_full, Lm)}
    rows_lab = [name_of[a] for a in range(5)]
    bridge = pd.DataFrame(C, index=rows_lab, columns=fn).round(2)
    bridge.to_csv(me.OUT / f"independent_bridge_corr{SUFFIX}.csv")
    ri, ci = linear_sum_assignment(-np.abs(C))
    print(f"\nBridge (n = {int(both.sum()):,}): matched-set factors x independent factors, score correlations")
    print(bridge.to_string())
    print("Hungarian pairs:", [(rows_lab[a], fn[b], round(C[a, b], 2)) for a, b in zip(ri, ci)])


if __name__ == "__main__":
    main()

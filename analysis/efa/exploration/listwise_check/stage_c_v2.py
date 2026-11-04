"""Stage C under the revised §3c (docs/EFA_ITEM_SELECTION_ROBUSTNESS.md, revised 2026-11-03), CES 2024, end to end.

Data: CES 2024 Common Content, the 49,432 respondents with commonpostweight > 0 (item_pool.load: recodes, pid7).
Battery tags: analysis/efa/ces_item_pool.csv. State control: analysis/efa/state_control_2024.csv.
Pool: the 69-item Stage A pool minus economic sentiment (CC24_302 household income, CC24_303 prices): 67 items.
Checkbox items stay out (Stage A as written; open ruling).

Steps, as §3c now reads:
  B   full sample: drop items > 30% missing or modal share > 85%; redundancy |r| > 0.70 from the highest |r| down,
      keep the member with the lower mean |r| with the other surviving items (pair excluded): more information
      not already in the pool. (Higher-mean, as first written, chained: the wall absorbed 11 items; reversed 2026-11-03.) Weighted pairwise
      polychoric (item_pool cache).
  2   k = min(parallel analysis, MAP) on the Stage B pool's listwise polychoric, bounded to 3-7. Parallel analysis
      counts every eigenvalue (n_max = items) with the simulated n capped at 20,000 (CES convention).
  3   50 respondent bootstrap draws (seed 42), each with its own weighted pairwise polychoric on the items passing the
      missing/modal screen: redundancy screen, then the weak-item loop at k (PAF + oblimin; drop max |l| < 0.30,
      h2 < 0.20 or h2 >= 0.995 together, refit, repeat). Cross-loaders stay. Retained = survives in > 25 of 50 draws.
      Retained items fit at k on their listwise polychoric; parallel analysis and MAP rerun once and reported.
  4   entry test (>= 2 clean items, |l| >= 0.40 here and < 0.30 elsewhere, from >= 2 batteries) in the full-sample fit
      and in > 25 of the 50 draws (draw refit on the retained items, matched to the full-sample factor at Tucker
      phi >= 0.85; unmatched = fail).
  scoring   pairwise loadings on all respondents aligned to the listwise fit; available-item scores (eligible =
      answered at least half of each passing factor's primary items). No anchor residualization (dropped
      2026-11-04: it is an affine map of the clustering columns, so it changes only the DPGMM's k-means starts;
      the residualized run is kept in outputs/stage_c_v2_residualized/).
  7   in-power adjustment of every clustering score: weighted OLS on alignment groups (aligned base), subtract the
      opposed and split contrasts, keep the nonpartisan difference (state_control.strata).
  cap scan 2-10 (DPGMM, 20 seeds 42-61, 30 resample fits; Jaccard >= 0.75 stable, < 0.5 dissolved; cap rule = largest
      cap with no dissolved cluster), compared with the reference ten (outputs/four_dim) and production's nine.
Names (after the test, no part in it): score correlation |r| >= 0.7 with a rescored production factor.
Writes outputs/stage_c_v2/; log outputs/stage_c_v2_run.log via tee.
"""
import os
import re
os.environ.setdefault("OMP_NUM_THREADS", "1")

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from sklearn.metrics import adjusted_rand_score as ari

import four_dim_space as fd
import item_pool as ip
import loading_draws as ld
import reestimate_loadings as rl
import rescore_refit as rr
import stage_c as sc
import state_control as stc

em, fc = rl.em, fd.fc
OUT = rl.OUT / "stage_c_v2"
SENTIMENT = ("CC24_302", "CC24_303")
N_DRAWS, SEED, K_MIN, K_MAX = 50, 42, 3, 7
CAPS = range(2, 11)


def basic_screen(X, w, items, log):
    keep = []
    for c in items:
        x = X[c].values
        ok = ~np.isnan(x)
        miss = 1 - w[ok].sum() / w.sum()
        modal = (pd.Series(w[ok]).groupby(x[ok]).sum() / w[ok].sum()).max()
        if miss > ip.MAX_MISSING:
            log.append({"item": c, "stage": "B missing", "value": round(float(miss), 3)})
        elif modal > ip.MAX_MODAL:
            log.append({"item": c, "stage": "B modal share", "value": round(float(modal), 3)})
        else:
            keep.append(c)
    return keep


def redundancy(R, items, log=None):
    alive = list(items)
    A = R.loc[alive, alive].abs()
    pairs = sorted(((A.loc[a, b], a, b) for i, a in enumerate(alive) for b in alive[i + 1:] if A.loc[a, b] > ip.MAX_R),
                   reverse=True)
    for r, a, b in pairs:
        if a in alive and b in alive:
            rest = [c for c in alive if c not in (a, b)]
            ma, mb = A.loc[a, rest].mean(), A.loc[b, rest].mean()
            loser = a if ma >= mb else b
            if log is not None:
                log.append({"item": loser, "stage": f"B redundant with {a if loser == b else b}", "value": round(float(r), 3),
                            "mean_r_kept": round(float(min(ma, mb)), 3), "mean_r_dropped": round(float(max(ma, mb)), 3)})
            alive.remove(loser)
    return alive


def weak_loop(R, items, k, log=None):
    items = list(items)
    while True:
        L, Phi, h2 = sc.fit(R.loc[items, items], k)
        A = np.abs(L)
        weak = [c for c, row, h in zip(items, A, h2) if row.max() < sc.MIN_LOAD or h < sc.MIN_H2 or h >= sc.HEYWOOD]
        if not weak:
            return items, L, Phi, h2
        if log is not None:
            for c in weak:
                i = items.index(c)
                log.append({"item": c, "stage": "weak" if h2[i] < sc.HEYWOOD else "Heywood", "value": round(float(A[i].max()), 3),
                            "h2": round(float(h2[i]), 3)})
        items = [c for c in items if c not in weak]


def pairwise(X, w, items):
    pairs = [(i, j) for i in range(len(items)) for j in range(i + 1, len(items))]
    V = X[items].values.astype(float)
    vals = Parallel(n_jobs=11)(delayed(em.weighted_polychoric)(V[:, i], V[:, j], w) for i, j in pairs)
    M = np.eye(len(items))
    for (i, j), r in zip(pairs, vals):
        M[i, j] = M[j, i] = r
    return M


def reg(M, items):
    return pd.DataFrame(em.regularize_corr(np.asarray(M, dtype=float).copy()), index=items, columns=items)


def pick_k(R, n):
    k_pa = em.parallel_analysis(R.values, min(n, ip.PA_CAP), n_max=R.shape[0])[0]
    k_map = em.velicer_map(R.values)[0]
    return int(k_pa), int(k_map)


ROLES = {**fd.NAMES, "Government Distrust": "TR"}


def roles(names, enter):
    """Short role names for the entering factors: the one-to-one production name when it has a role, else the closest
    production factor when |r| >= 0.7 and that role is still free (naming only, never which factors enter)."""
    out, used = {}, set()
    for j in enter:
        base = names[j].split(" (")[0]
        if base in ROLES and ROLES[base] not in used:
            out[j] = ROLES[base]
            used.add(out[j])
    for j in enter:
        if j in out:
            continue
        m = re.search(r"closest (.+) r ([0-9.]+)\)", names[j])
        if m and float(m.group(2)) >= sc.NAME_R and ROLES.get(m.group(1)) not in used and m.group(1) in ROLES:
            out[j] = ROLES[m.group(1)]
            used.add(out[j])
        else:
            out[j] = f"N{j}"
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tags = pd.read_csv(sc.TAGS)
    battery = dict(zip(tags.item_id, tags.battery_id))
    X, w, pid, caseid = ip.load()
    pool = [c for c in ip.POOL if c not in SENTIMENT]
    Rpw = ip.poly_all(X, w)
    log = []
    b1 = basic_screen(X, w, pool, log)
    items_b = redundancy(Rpw, b1, log)
    print(f"pool {len(pool)}; after missing/modal {len(b1)}; Stage B pool {len(items_b)}", flush=True)
    print("Stage B drops:", [(d["item"], d["stage"]) for d in log], flush=True)

    R_lw, rows = sc.listwise_matrix(X, w, items_b)
    k_pa, k_map = pick_k(R_lw, len(rows))
    k = int(np.clip(min(k_pa, k_map), K_MIN, K_MAX))
    print(f"step 2: listwise n {len(rows):,}; parallel analysis {k_pa}, MAP {k_map}; fit k = {k}", flush=True)

    # step 3: resampled redundancy + weak-item loop
    cache = OUT / "draw_poly.npz"
    store = dict(np.load(cache)) if cache.exists() else {}
    rng = np.random.default_rng(SEED)
    draws_idx = [rng.integers(0, len(w), len(w)) for _ in range(N_DRAWS)]
    surv = {c: 0 for c in b1}
    why = {c: {} for c in b1}
    for b, i in enumerate(draws_idx):
        key = f"d{b}"
        if key not in store:
            store[key] = pairwise(X.iloc[i].reset_index(drop=True), w[i], b1)
            np.savez_compressed(cache, **store)
        Rb = reg(store[key], b1)
        dl = []
        it = redundancy(Rb, b1, dl)
        it, *_ = weak_loop(Rb, it, k, dl)
        for c in it:
            surv[c] += 1
        for d in dl:
            st = d["stage"].split(" with")[0]
            why[d["item"]][st] = why[d["item"]].get(st, 0) + 1
        print(f"draw {b + 1}/{N_DRAWS}: {len(it)} items survive", flush=True)
    ret = pd.DataFrame({"item": b1, "survived": [surv[c] for c in b1],
                        "dropped_as": [", ".join(f"{s} {n}" for s, n in why[c].items()) for c in b1],
                        "in_stage_b_full_sample": [c in items_b for c in b1]})
    ret["retained"] = ret.survived > N_DRAWS / 2
    ret.sort_values("survived").to_csv(OUT / "retention.csv", index=False)
    print("\nitem retention across draws:\n", ret.sort_values("survived").to_string(index=False), flush=True)
    retained = [c for c in b1 if surv[c] > N_DRAWS / 2]

    R, rows = sc.listwise_matrix(X, w, retained)
    D, w_D, caseid_D = X.loc[rows], w[rows], caseid[rows]
    full_log = []
    _, _, _, _ = weak_loop(R, retained, k, full_log)
    L, Phi, h2 = sc.fit(R.loc[retained, retained], k)
    k2_pa, k2_map = pick_k(R, len(rows))
    print(f"\n{len(retained)} retained items; full-sample fit k = {k}; rerun: parallel analysis {k2_pa}, MAP {k2_map}"
          f"{'' if min(k2_pa, k2_map) == k else ' (differs; disclosed, not looped)'}; "
          f"weak in the full-sample fit (kept, retention is by draws): {[d['item'] for d in full_log]}", flush=True)
    test = sc.entry_test(retained, L, battery)
    names = sc.name_factors(D, w_D, caseid_D, retained, R, L, Phi)
    test.insert(1, "name", test.factor.map(names))

    # step 4: resampled entry test
    passes = np.zeros(k, int)
    phis = []
    for b in range(N_DRAWS):
        Rb = reg(pd.DataFrame(store[f"d{b}"], index=b1, columns=b1).loc[retained, retained].values, retained)
        Lb, Pb, _ = sc.fit(Rb, k)
        Lb, Pb, phi = rl.align(L, Lb, Pb)
        tb = sc.entry_test(retained, Lb, battery)
        passes += ((phi >= sc.PHI_SAME) & tb.passes.values).astype(int)
        phis.append(phi)
    test["draw_pass_rate"] = passes / N_DRAWS
    test["median_phi"] = np.median(np.array(phis), axis=0).round(3)
    test["enters"] = test.passes & (test.draw_pass_rate > 0.5)
    test.to_csv(OUT / "factors.csv", index=False)
    pd.DataFrame(L, index=retained, columns=[f"F{j}" for j in range(k)]).assign(
        h2=h2, battery=[battery[c] for c in retained]).round(3).to_csv(OUT / "loadings.csv")
    pd.DataFrame(log).to_csv(OUT / "stage_b_log.csv", index=False)
    print("\nfactors:\n", test.drop(columns=["factor"]).to_string(index=False), flush=True)

    # scoring
    enter = [j for j in range(k) if test.enters[j]]
    sn = roles(names, enter)
    Rp = reg(Rpw.loc[retained, retained].values, retained)
    Lp, Pp = em.oblimin(em.paf(Rp.values.copy(), k)[0])
    Lp, Pp, phi = rl.align(L, Lp, Pp)
    print(f"\nclustering factors: {sn}; pairwise vs listwise phi {np.round(phi, 3).tolist()}", flush=True)
    primary = np.abs(Lp).argmax(axis=1)
    Xv = X[retained].values.astype(float)
    answered = np.column_stack([(~np.isnan(Xv[:, primary == j])).mean(axis=1) for j in enter])
    elig = (answered >= rr.MIN_SHARE_PER_FACTOR).all(axis=1)
    F, _ = rr.available_scores(Xv[elig], w[elig], Rp.values, Lp, Pp)
    we = w[elig]
    S = pd.DataFrame({sn[j]: F[:, j] for j in enter})
    cols = list(S.columns)
    # step 7: in-power adjustment
    s_all, st_all = stc.strata(caseid, pid)
    se, st = s_all[elig], st_all[elig]
    Xd = np.column_stack([np.ones(len(S))] + [(se == g).astype(float) for g in ("nonpartisan", "opposed", "split")])
    sw = np.sqrt(we / we.mean())
    adj = []
    for c in cols:
        y = S[c].values
        beta = np.linalg.lstsq(Xd * sw[:, None], y * sw, rcond=None)[0]
        rem = Xd[:, 2:] @ beta[2:]
        adj.append({"factor": c, "share_removed": round(float(np.cov(rem, aweights=we) / np.cov(y, aweights=we)), 4),
                    "opposed": round(float(beta[2]), 3), "split": round(float(beta[3]), 3), "nonpartisan_kept": round(float(beta[1]), 3)})
        S[c] = y - rem
    adj = pd.DataFrame(adj)
    adj.to_csv(OUT / "in_power.csv", index=False)
    print("in-power adjustment:\n", adj.to_string(index=False), flush=True)
    S.insert(0, "caseid", caseid[elig])
    S.insert(1, "commonpostweight", we)
    S.to_csv(OUT / "scores.csv", index=False)
    print(f"eligible {elig.sum():,}; clustering on {cols}", flush=True)

    Xc = S[cols].values
    lab_path = OUT / "labels.npz"
    if lab_path.exists():
        lab_store = dict(np.load(lab_path))
    else:
        jobs = [delayed(fc.job)(Xc, "dpgmm", K, kind, i) for K in CAPS
                for kind, rr_ in (("seed", fc.SEEDS), ("boot", range(fc.N_BOOT))) for i in rr_]
        res = Parallel(n_jobs=11, verbose=1)(jobs)
        acc = {}
        for _, K, kind, i, labels, bound in res:
            acc.setdefault((K, kind), []).append((i, labels, bound))
        lab_store = {}
        for (K, kind), v in acc.items():
            v = sorted(v, key=lambda t: t[0])
            lab_store[f"{K}_{kind}"] = np.stack([l for _, l, _ in v])
            lab_store[f"{K}_{kind}_bounds"] = np.array([b for *_, b in v])
        np.savez_compressed(lab_path, **lab_store)
    summary, clusters = [], []
    for K in CAPS:
        seeds = list(zip(fc.SEEDS, lab_store[f"{K}_seed"], lab_store[f"{K}_seed_bounds"]))
        sm, cl = fd.summarize(Xc, we, np.array(["x"] * len(S)), seeds, list(lab_store[f"{K}_boot"]), K, cols)
        summary.append(sm)
        clusters += cl
    summ = pd.DataFrame(summary)
    summ.to_csv(OUT / "summary.csv", index=False)
    pd.DataFrame(clusters).to_csv(OUT / "clusters.csv", index=False)
    ok = summ[summ.n_dissolved == 0]
    kept = int(ok.K.max()) if not ok.empty else None
    print("\ncap scan:\n", summ.to_string(index=False))
    print(f"cap rule: {kept}", flush=True)

    S0 = pd.read_csv(fd.OUT / "scores.csv", usecols=["caseid"])
    z = np.load(fd.OUT / "labels.npz")
    ref10 = pd.Series(ld.modal_solution(list(zip(range(42, 62), z["10_seed"], z["10_seed_bounds"])))[0], index=S0.caseid.values)
    fs = pd.read_csv(rl.ROOT / "data/processed/efa_factor_scores.csv", usecols=["caseid"])
    typ = pd.read_csv(rl.ROOT / "data/processed/typology_cluster_assignments.csv", usecols=["cluster"])
    prod = pd.Series(typ.cluster.values, index=fs.caseid.values)
    out = []
    for K in sorted({kept, 9, 10} - {None}):
        lab, n_sol, share = ld.modal_solution(list(zip(fc.SEEDS, lab_store[f"{K}_seed"], lab_store[f"{K}_seed_bounds"])))
        L_ = pd.Series(lab, index=S.caseid.values)
        row = {"cap": K, "n_solutions": n_sol, "modal_share": share}
        for nm, ref in (("reference_ten", ref10), ("production", prod)):
            common = np.intersect1d(L_.index.values, ref.index.values)
            row[f"ari_vs_{nm}"] = round(ari(ref.loc[common].values, L_.loc[common].values), 3)
        stc_ = pd.Series(st, index=S.caseid.values)
        row["max_state_index"] = round(max(
            0.5 * (pd.Series(we * (lab == c)).groupby(st).sum() / we[lab == c].sum()
                   - pd.Series(we).groupby(st).sum() / we.sum()).abs().sum() for c in np.unique(lab)), 3)
        out.append(row)
    out = pd.DataFrame(out)
    out.to_csv(OUT / "compare.csv", index=False)
    print("\n", out.to_string(index=False))


if __name__ == "__main__":
    main()

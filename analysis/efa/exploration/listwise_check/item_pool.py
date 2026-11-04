"""Does a larger, rule-screened CES item pool change the factors or the parties? NEXT.md steps 2 and 3.

Data: CES 2024 Common Content (efa_update.CES_PATH), the 49,432 respondents with commonpostweight > 0.
Party ID: pid7 (1-7, "Not sure" missing). Reference parties: the rescored cap-8 typology (loading_draws.py).

Arms (--arm):
  main    Stage A pool: every policy/attitude item on a common ordinal or binary scale (69 items, POOL below).
          Out by category (DECISIONS.md 2026-11-02): approvals CC24_312*, ideology placements CC24_330*,
          economy retrospective CC24_301, multi-selects CC24_309d*, CC24_420*, CC24_308*, and non-attitudinal items
          (media, vote choice, participation, knowledge, life events, health). The hand drops CC24_440a, 441a,
          441b and pew_bornagain re-enter here and face the rule like everything else.
  fp24    the 24 production items, held fixed, plus the foreign-policy binaries (FP below). Only FP items face the screen.
  fpmain  the main pool plus FP, all screened.
FP: military intervention CC24_420_1-6, Ukraine CC24_308a_2-8, Israel/Gaza CC24_308b_2-9, each a selected / not
selected binary. The exclusive "none" box of each battery (420_7, 308a_1, 308b_1) is dropped.

Rule, fixed before running (NEXT.md step 2):
  (a) Stage B, as analysis/validation/anes/independent_efa.py applies it:
      1. drop items missing for > 30% of post-weighted respondents
      2. drop items whose weighted modal category share > 85%
      3. no party-ID cap on policy items (analysis/validation/DECISIONS.md 2026-10-31)
      4. pairs with weighted pairwise polychoric |r| > 0.70: drop the higher party-ID R^2 member, strongest pair first
      5. listwise polychoric; parallel analysis (n capped at 20,000, as production) picks k; PAF + oblimin; drop
         items with max |loading| < 0.30, h^2 < 0.20 or h^2 >= 0.995; repeat until nothing drops
  (b) numerical check on the final set: no Heywood case (h^2 >= 0.995), the unregularized listwise polychoric
      positive definite, and parallel analysis on the final set giving the k that was fitted
  (c) if (b) fails: from the dominating battery (the question battery with the most surviving items, ties
      broken by summed h^2) drop the item with the highest party-ID R^2, re-run step 5 and (b); repeat
Party layer, the production procedure on the final set: loadings from the pairwise polychoric on all post-weighted
respondents; available-item scoring (rescore_refit.available_scores; eligible = answered half of each factor's
primary items); the factors that score-correlate one-to-one (Hungarian) with production's Religious
Traditionalism and Populist Conservatism residualized on the one matching Security & Order, as production does,
when the match is a same-factor match (score |r| >= 0.7; otherwise the factor is left raw);
DPGMM cap 8, the procedure in loading_draws.py. Clusters matched one-to-one to the reference parties; kept share and
Jaccard judged against the loading-draw spread (outputs/loading_draws/summary.csv).
Writes outputs/item_pool/<arm>_{screen_log,loadings,bridge,parties}.csv, <arm>_labels.npz; matrix cache
outputs/item_pool/polychoric_pairwise_all.csv (all pool + FP items). Log: outputs/item_pool_<arm>_run.log via tee.
"""
import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
import argparse
import re

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score as ari

import loading_draws as ld
import reestimate_loadings as rl
import rescore_refit as rr

eu, em, cg = rl.eu, rl.em, rl.cg
OUT = rl.OUT / "item_pool"
MAX_MISSING, MAX_MODAL, MAX_R, MIN_LOAD, MIN_H2, HEYWOOD, PA_CAP = 0.30, 0.85, 0.70, 0.30, 0.20, 0.995, 20000
SAME_FACTOR_R = 0.7  # a new factor stands in for a production factor only when their scores correlate this well

POOL = (["pew_churatd", "pew_religimp", "pew_prayer", "pew_bornagain", "CC24_302", "CC24_303"]
        + [f"CC24_321{c}" for c in "abcdef"] + [f"CC24_323{c}" for c in "abcdf"] + [f"CC24_324{c}" for c in "abcd"]
        + ["CC24_325"] + [f"CC24_326{c}" for c in "abcdef"] + [f"CC24_328{c}" for c in "abcde"]
        + [f"CC24_340{c}" for c in "abcdef"] + [f"CC24_341{c}" for c in "abcd"]
        + ["CC24_421_1", "CC24_421_2", "CC24_423", "CC24_424"]
        + [f"CC24_440{c}" for c in "abcd"] + [f"CC24_441{c}" for c in "abefg"] + [f"CC24_443_{i}" for i in range(1, 6)]
        + [f"CC24_444{c}" for c in "abcdef"] + ["CC24_445a", "CC24_445b"])
FP = ([f"CC24_420_{i}" for i in range(1, 7)] + [f"CC24_308a_{i}" for i in range(2, 9)]
      + [f"CC24_308b_{i}" for i in range(2, 10)])
PID7 = {"Strong Democrat": 1, "Not very strong Democrat": 2, "Lean Democrat": 3, "Independent": 4,
        "Lean Republican": 5, "Not very strong Republican": 6, "Strong Republican": 7}
MAPS = {
    "pew_religimp": {"Not at all important": 1, "Not too important": 2, "Somewhat important": 3, "Very important": 4},
    "pew_prayer": {"Never": 1, "Seldom": 2, "A few times a month": 3, "Once a week": 4, "A few times a week": 5,
                   "Once a day": 6, "Several times a day": 7},
    "pew_bornagain": {"Yes": 1, "No": 0},
}
SPEND = {"Greatly decrease": 1, "Slightly decrease": 2, "Maintain": 3, "Slightly increase": 4, "Greatly increase": 5}


def battery(item):
    if item.startswith("pew_"):
        return "pew"
    m = re.match(r"^(CC24_\d{3}[a-z]?)_\d+$", item) or re.match(r"^(CC24_\d{3})[a-z]$", item)
    return m.group(1) if m else item


def recode(lab):
    out = eu.recode_items(lab[eu.ITEMS_24]).to_dict("series")
    for c in lab.columns:
        if c in out:
            continue
        s = lab[c]
        if c in MAPS:
            m = MAPS[c]
        elif c in eu.LABEL_MAPS:
            m = eu.LABEL_MAPS[c]
        elif c.startswith("CC24_443"):
            m = SPEND
        elif c.startswith(("CC24_420", "CC24_308")):
            m = {"selected": 1, "not selected": 0}
        else:
            cats = set(s.cat.categories)
            m = {"Support": 1, "Oppose": 0} if "Support" in cats else (
                {"Agree": 1, "Disagree": 0} if cats == {"Agree", "Disagree"} else eu.AGREE_HI)
            assert set(m) >= cats - {"Don't know"}, (c, cats)
        out[c] = s.map(m).astype(float)
    if "CC24_340a" in lab:
        out["CC24_340a"] = lab["CC24_340a"].map(eu.OPPOSE_HI).astype(float)
    return pd.DataFrame(out)


def load():
    cols = POOL + FP
    lab = pd.read_stata(eu.CES_PATH, columns=cols + ["pid7"], convert_categoricals=True, convert_missing=False)
    meta = pd.read_stata(eu.CES_PATH, columns=["caseid", "commonpostweight"], convert_categoricals=False)
    w = pd.to_numeric(meta.commonpostweight, errors="coerce").values
    post = w > 0
    X = recode(lab[cols])[cols]
    pid = lab.pid7.map(PID7).astype(float).values
    return X[post].reset_index(drop=True), w[post], pid[post], meta.caseid.values[post]


def poly_all(X, w):
    path = OUT / "polychoric_pairwise_all.csv"
    if path.exists():
        return pd.read_csv(path, index_col=0)
    items = list(X.columns)
    pairs = [(i, j) for i in range(len(items)) for j in range(i + 1, len(items))]
    vals = Parallel(n_jobs=11, verbose=1)(delayed(em.weighted_polychoric)(X[items[i]].values, X[items[j]].values, w)
                                          for i, j in pairs)
    M = np.eye(len(items))
    for (i, j), r in zip(pairs, vals):
        M[i, j] = M[j, i] = r
    M = pd.DataFrame(M, index=items, columns=items)
    M.to_csv(path)
    return M


def listwise_fit(X, w, items):
    D = X[items].dropna()
    wD = w[D.index.values]
    pairs = [(i, j) for i in range(len(items)) for j in range(i + 1, len(items))]
    vals = Parallel(n_jobs=11)(delayed(em.weighted_polychoric)(D[items[i]].values, D[items[j]].values, wD) for i, j in pairs)
    Rraw = np.eye(len(items))
    for (i, j), r in zip(pairs, vals):
        Rraw[i, j] = Rraw[j, i] = r
    R = em.regularize_corr(Rraw.copy())
    k, ev, thr = em.parallel_analysis(R, min(len(D), PA_CAP))
    L_un, _, _ = em.paf(R, k)
    L, Phi = em.oblimin(L_un)
    h2 = np.clip(np.diag(L @ Phi @ L.T), 0, None)
    return {"n": len(D), "Rraw": Rraw, "k": k, "ev": ev, "L": L, "Phi": Phi, "h2": h2}


def screen(X, w, pid, items, fixed, log, Rpw):
    def drop(c, stage, v, h2=np.nan):
        log.append({"item": c, "battery": battery(c), "stage": stage, "value": round(float(v), 3), "h2": round(float(h2), 3)})
        alive.remove(c)

    alive = list(items)
    for c in list(alive):
        if c in fixed:
            continue
        x = X[c].values
        ok = ~np.isnan(x)
        miss = 1 - w[ok].sum() / w.sum()
        modal = (pd.Series(w[ok]).groupby(x[ok]).sum() / w[ok].sum()).max()
        if miss > MAX_MISSING:
            drop(c, "1 missing", miss)
        elif modal > MAX_MODAL:
            drop(c, "2 modal share", modal)
    r2 = {c: rr_weighted_r2(X[c].values, pid, w) for c in X.columns}
    pairs = sorted(((abs(Rpw.loc[a, b]), a, b) for i, a in enumerate(alive) for b in alive[i + 1:]
                    if abs(Rpw.loc[a, b]) > MAX_R), reverse=True)
    for r, a, b in pairs:
        if a in alive and b in alive:
            cand = [c for c in (a, b) if c not in fixed]
            if not cand:
                continue
            loser = max(cand, key=lambda c: r2[c])
            drop(loser, f"4 redundant with {b if loser == a else a}", r)
    print(f"after stages 1-4: {len(alive)} items", flush=True)

    def step5():
        while True:
            f = listwise_fit(X, w, alive)
            weak = [c for c, row, h in zip(alive, f["L"], f["h2"])
                    if c not in fixed and (np.abs(row).max() < MIN_LOAD or h < MIN_H2 or h >= HEYWOOD)]
            print(f"  step 5: listwise n {f['n']:,}, {len(alive)} items, PA k {f['k']}, weak {len(weak)}", flush=True)
            if not weak:
                return f
            vals = {c: (np.abs(f["L"][alive.index(c)]).max(), f["h2"][alive.index(c)]) for c in weak}
            for c in weak:
                drop(c, "5 weak loading/communality", *vals[c])

    f = step5()
    while True:
        min_eig = np.linalg.eigvalsh(f["Rraw"]).min()
        heywood = [c for c, h in zip(alive, f["h2"]) if h >= HEYWOOD]
        k_final, _, _ = em.parallel_analysis(em.regularize_corr(f["Rraw"].copy()), min(f["n"], PA_CAP))
        ok = (not heywood) and min_eig > 0 and k_final == f["k"]
        print(f"(b) check: Heywood {heywood or 'none'}, min eigenvalue {min_eig:.4f}, PA k {k_final} vs fitted {f['k']}: "
              f"{'PASS' if ok else 'FAIL'}", flush=True)
        if ok:
            return alive, f, r2, Rpw
        h2 = dict(zip(alive, f["h2"]))
        bats = pd.Series({c: battery(c) for c in alive if c not in fixed})
        size = bats.value_counts()
        hsum = pd.Series({b: sum(h2[c] for c in bats.index[bats == b]) for b in size.index})
        dom = sorted(size.index, key=lambda b: (-size[b], -hsum[b]))[0]
        loser = max(bats.index[bats == dom], key=lambda c: r2[c])
        drop(loser, f"c dominating battery {dom}", r2[loser])
        f = step5()


def rr_weighted_r2(y, x, w):
    ok = ~(np.isnan(y) | np.isnan(x))
    y, x, w = y[ok], x[ok], w[ok] / w[ok].mean()
    A = np.column_stack([np.ones_like(x), x])
    beta = np.linalg.solve(A.T @ (A * w[:, None]), A.T @ (w * y))
    return 1 - np.sum(w * (y - A @ beta) ** 2) / np.sum(w * (y - np.average(y, weights=w)) ** 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["main", "fp24", "fpmain"], required=True)
    arm = ap.parse_args().arm
    OUT.mkdir(parents=True, exist_ok=True)
    X, w, pid, caseid = load()
    print(f"post-weighted respondents: {len(X):,}; pool {len(POOL)} items, FP {len(FP)} binaries")
    items = {"main": POOL, "fp24": eu.ITEMS_24 + FP, "fpmain": POOL + FP}[arm]
    fixed = set(eu.ITEMS_24) if arm == "fp24" else set()
    Rpw = poly_all(X, w)
    Xa = X[items]
    log = []
    alive, f, r2, Rpw = screen(Xa, w, pid, items, fixed, log, Rpw)
    pd.DataFrame(log).to_csv(OUT / f"{arm}_screen_log.csv", index=False)
    print(f"\nscreen drops by stage: {pd.DataFrame(log).stage.str[0].value_counts().sort_index().to_dict() if log else {}}")
    print(f"final: {len(alive)} items, k = {f['k']}; first eigenvalues {np.round(f['ev'][:f['k'] + 2], 3).tolist()}")
    print("production items surviving:", sorted(set(alive) & set(eu.ITEMS_24)), f"({len(set(alive) & set(eu.ITEMS_24))} of 24)")
    print("re-entered hand drops surviving:", sorted(set(alive) & {"CC24_440a", "CC24_441a", "CC24_441b", "pew_bornagain"}))

    # party layer: pairwise loadings, available-item scores, production clustering at cap 8
    k = f["k"]
    R = em.regularize_corr(Rpw.loc[alive, alive].values.copy())
    L_un, _, _ = em.paf(R, k)
    L, Phi = em.oblimin(L_un)
    h2 = np.clip(np.diag(L @ Phi @ L.T), 0, None)
    primary = np.abs(L).argmax(axis=1)
    Xv = Xa[alive].values.astype(float)
    answered = np.column_stack([(~np.isnan(Xv[:, primary == j])).mean(axis=1) for j in range(k)])
    elig = (answered >= rr.MIN_SHARE_PER_FACTOR).all(axis=1)
    F, n_pat = rr.available_scores(Xv[elig], w[elig], R, L, Phi)

    s, ref, names = ld.reference()
    ref_s = pd.Series(ref, index=s.caseid.values)
    cid = caseid[elig]
    both = np.isin(cid, s.caseid.values)
    P = s.set_index("caseid").loc[cid[both], rr.FS].values
    C = np.array([[np.corrcoef(P[:, a], F[both, b])[0, 1] for b in range(k)] for a in range(5)])
    ri, ci = linear_sum_assignment(-np.abs(C))
    sign = np.sign(C[ri, ci])
    F[:, ci] *= sign
    L[:, ci] *= sign
    C[:, ci] *= sign
    fn = [f"N{j + 1}" for j in range(k)]
    tag = {ci[i]: rl.NAMES[ri[i]] for i in range(len(ri))}
    bridge = pd.DataFrame(C, index=rl.NAMES, columns=[f"{fn[j]} ({tag.get(j, 'new')})" for j in range(k)])
    bridge.to_csv(OUT / f"{arm}_bridge.csv")
    print(f"\nscore correlations with the rescored production factors (n {both.sum():,}):\n{bridge.round(2).to_string()}")

    load_df = pd.DataFrame(L, index=alive, columns=fn).assign(h2=h2, primary=[fn[j] for j in primary],
                                                              pid_r2=[r2[c] for c in alive])
    load_df.to_csv(OUT / f"{arm}_loadings.csv")
    for j in range(k):
        sub = load_df[load_df.primary == fn[j]].sort_values(fn[j], key=np.abs, ascending=False)
        print(f"\n{fn[j]} ({tag.get(j, 'new')}): " + ", ".join(f"{c} {v:+.2f}" for c, v in sub[fn[j]].items()))
    shared = [c for c in alive if c in eu.ITEMS_24]
    if shared:
        Lp = pd.read_csv(rl.OUT / "loadings_pairwise.csv", index_col=0).loc[shared, rl.NAMES].values
        Ln = load_df.loc[shared, fn].values
        phis = {rl.NAMES[a]: round(cg.tucker_phi(Lp[:, a], Ln[:, b]), 3) for a, b in zip(ri, ci)}
        print(f"\nTucker phi with the rescored loadings on the {len(shared)} shared items:", phis)

    col = {name: j for j, name in tag.items() if abs(C[rl.NAMES.index(name), j]) >= SAME_FACTOR_R}
    print(f"residualized on Security & Order (matched |r| >= {SAME_FACTOR_R}):",
          [nm for nm in ("Religious Traditionalism", "Populist Conservatism") if nm in col and "Security & Order" in col])
    Fc = F.copy()
    w_e = w[elig]
    if "Security & Order" in col:
        for nm in ("Religious Traditionalism", "Populist Conservatism"):
            if nm in col:
                Fc[:, col[nm]] = em.wresid(F[:, col[nm]], F[:, col["Security & Order"]], w_e)
    res = sorted(Parallel(n_jobs=11)(delayed(ld.fit)(Fc, sd) for sd in ld.SEEDS))
    lab, n_sol, share = ld.modal_solution(res)
    np.savez_compressed(OUT / f"{arm}_labels.npz", labels=lab, caseid=cid)
    print(f"\ncap-{ld.CAP} DPGMM on {elig.sum():,} eligible ({n_pat} missing-data patterns): {n_sol} solutions, "
          f"modal share {share:.2f}")

    refb = ref_s.loc[cid[both]].values
    rows = ld.match(refb, lab[both], w_e[both], names)
    floor = pd.read_csv(rl.OUT / "loading_draws" / "summary.csv", index_col=0) if (rl.OUT / "loading_draws" / "summary.csv").exists() else None
    pa = pd.DataFrame(rows).set_index("party")
    if floor is not None:
        pa = pa.join(floor[["kept_q05", "kept_median", "jaccard_q05"]])
        pa["below_noise_floor"] = pa.kept < pa.kept_q05
    pa.to_csv(OUT / f"{arm}_parties.csv")
    print(f"ARI vs the reference cap-8 parties on {both.sum():,}: {ari(refb, lab[both]):.3f}")
    print(pa.round(3).to_string())


if __name__ == "__main__":
    main()

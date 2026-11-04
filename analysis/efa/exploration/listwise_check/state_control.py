"""Sensitivity check (2026-11-03, researcher-requested after results were seen): the full factor-to-cluster chain with
alignment with one's state government held out. Does distrust still form a factor, and how many factors and clusters
does the space then support? Not a rule change; disclosed in DECISIONS.md.

Data: CES 2024 Common Content, 49,432 post-weighted respondents (item_pool.load), the 69-item pool.
State control: analysis/efa/state_control_2024.csv, the 2024 configuration (before the 2024 election took effect;
the CES post-election wave was fielded under it). 23 Republican trifectas, 17 Democratic (plus DC), 10 divided,
matching Ballotpedia's pre-election count; governors match CES CurrentGovParty in every state.
Alignment: partisans by pid7 (leaners counted with their party, pure independents and "not sure" nonpartisan). A
partisan's share of the three power centers (governor, upper and lower chamber) held by their party; a chamber run
by a bipartisan coalition (Alaska) counts half. Strata: aligned (all three), opposed (none), split (some),
nonpartisan.
Control, two places:
  1. factor structure: every polychoric (pairwise for Stage B, listwise for Stage C) is the pooled within-stratum
     matrix, sum_s W_s R_s / sum_s W_s with W_s the stratum's weight, so differences between strata do not count as
     shared variance. Party ID itself is not a stratum: each stratum mixes Democrats and Republicans, so the
     left-right covariance the factors are built on stays.
  2. clustering scores: from each clustering factor, after the production anchor residualization (Religious
     Traditionalism and Populist Conservatism on Security & Order), the opposed and split contrasts against aligned
     are removed (weighted OLS with a nonpartisan control that stays in the score).
Then §3c Stage C as written (lower-k rule, cross-loader removal, entry test of 2 clean items from 2 batteries), the
available-item scoring and the cap scan 2-10 of four_dim_space.py (20 seeds, 30 resample fits, cap rule = largest
cap with no dissolved cluster). The kept cap's modal solution is compared to the reference ten clusters.
Writes outputs/state_control/{poly_pairwise_pooled.csv, poly_listwise_pooled.csv, factors.csv, loadings_k*.csv,
removed.csv, strata_r2.csv, scores.csv, summary.csv, clusters.csv, labels.npz, compare.csv}; log via tee.
"""
import os
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

em, fc = rl.em, fd.fc
OUT = rl.OUT / "state_control"
CONTROL = rl.ROOT / "analysis/efa/state_control_2024.csv"
STRATA = ["aligned", "opposed", "split", "nonpartisan"]
CAPS = range(2, 11)
SHORT = {"Security & Order": "SO", "Religious Traditionalism": "RT", "Populist Conservatism": "PC",
         "Institutional Distrust": "TR", "Government Distrust": "GD"}


def strata(caseid, pid):
    st = pd.read_stata(rl.eu.CES_PATH, columns=["caseid", "inputstate"], convert_categoricals=True).set_index("caseid")
    st = st.inputstate.astype(str).loc[caseid].values
    c = pd.read_csv(CONTROL).set_index("state")
    val = {"D": (1.0, 0.0), "R": (0.0, 1.0), "coalition": (0.5, 0.5)}
    held = {s: [sum(val[r[k]][p] for k in ("governor", "upper", "lower")) / 3 for p in (0, 1)] for s, r in c.iterrows()}
    dem, rep = pid <= 3, pid >= 5
    share = np.full(len(pid), np.nan)
    share[dem] = [held[s][0] for s in st[dem]]
    share[rep] = [held[s][1] for s in st[rep]]
    lab = np.where(np.isnan(share), "nonpartisan", np.where(share == 1, "aligned", np.where(share == 0, "opposed", "split")))
    return lab, st


def pooled(X, w, items, s, path):
    if path.exists():
        return pd.read_csv(path, index_col=0).loc[items, items]
    pairs = [(i, j) for i in range(len(items)) for j in range(i + 1, len(items))]
    M = np.zeros((len(items), len(items)))
    tot = 0.0
    for g in STRATA:
        m = s == g
        Xg, wg = X.loc[m, items].values.astype(float), w[m]
        vals = Parallel(n_jobs=11)(delayed(em.weighted_polychoric)(Xg[:, i], Xg[:, j], wg) for i, j in pairs)
        Mg = np.eye(len(items))
        for (i, j), r in zip(pairs, vals):
            Mg[i, j] = Mg[j, i] = r
        M += wg.sum() * Mg
        tot += wg.sum()
        print(f"  {path.name}: stratum {g} done (n {m.sum():,})", flush=True)
    M = pd.DataFrame(M / tot, index=items, columns=items)
    M.to_csv(path)
    return M


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    X, w, pid, caseid = ip.load()
    s, st = strata(caseid, pid)
    print("strata (weighted %):", {g: round(w[s == g].sum() / w.sum() * 100, 1) for g in STRATA}, flush=True)
    tags = pd.read_csv(sc.TAGS)
    battery = dict(zip(tags.item_id, tags.battery_id))

    # Stages A/B on the pooled pairwise matrix
    Rpw = pooled(X, w, list(ip.POOL), s, OUT / "poly_pairwise_pooled.csv")
    log = []
    items = sc.stage_b(X, w, pid, ip.POOL, Rpw, log)
    print(f"{len(items)} items after Stages A/B; dropped {[(d['item'], d['stage']) for d in log]}", flush=True)

    # Stage C on the pooled listwise matrix
    rows = X[items].dropna().index.values
    Rl = pooled(X.loc[rows].reset_index(drop=True), w[rows], items, s[rows], OUT / "poly_listwise_pooled.csv")
    R = pd.DataFrame(em.regularize_corr(Rl.values.copy()), index=items, columns=items)
    D, w_D, caseid_D = X.loc[rows], w[rows], caseid[rows]
    k_pa, k_map = sc.pick_k(R, len(rows))
    print(f"listwise n {len(rows):,}; parallel analysis k = {k_pa}, MAP k = {k_map}", flush=True)
    removed, fits = [], {}
    for k in sorted({k_pa, k_map}):
        tag = f"k{k}"
        final, L, Phi, h2 = sc.remove_at_k(R, items, k, removed, tag)
        k2_pa, k2_map = sc.pick_k(R.loc[final, final], len(rows))
        test = sc.entry_test(final, L, battery)
        names = sc.name_factors(D, w_D, caseid_D, final, R, L, Phi)
        test.insert(1, "name", test.factor.map(names))
        test.insert(0, "fit", tag)
        fits[k] = (final, L, Phi, test)
        print(f"\n[{tag}{' (fitted, lower-k rule)' if k == min(k_pa, k_map) else ' (higher k, for reference)'}] "
              f"{len(final)} items; rerun on the final items: PA {k2_pa}, MAP {k2_map}")
        print(test.drop(columns=["fit", "factor"]).to_string(index=False), flush=True)
        pd.DataFrame(L, index=final, columns=[f"{tag}_F{j}" for j in range(k)]).assign(h2=h2).to_csv(OUT / f"loadings_{tag}.csv")
    pd.concat([t for *_, t in fits.values()]).to_csv(OUT / "factors.csv", index=False)
    pd.DataFrame(log + removed).to_csv(OUT / "removed.csv", index=False)

    # clustering space at the fitted (lower) k
    k = min(k_pa, k_map)
    final, L_lw, _, test = fits[k]
    names = {}
    for j, r in test.iterrows():
        if r.passes:
            base = str(r["name"]).split(" (")[0]
            names[j] = SHORT.get(base, f"F{j}")
    print(f"\nclustering factors at k = {k}: {names}", flush=True)
    Rp = em.regularize_corr(Rpw.loc[final, final].values.copy())
    L, Phi = em.oblimin(em.paf(Rp, k)[0])
    L, Phi, phi = rl.align(L_lw, L, Phi)
    print(f"pairwise vs listwise loadings, Tucker phi per factor: {np.round(phi, 3).tolist()}")
    keep = sorted(names)
    primary = np.abs(L).argmax(axis=1)
    Xv = X[final].values.astype(float)
    elig = (np.column_stack([(~np.isnan(Xv[:, primary == j])).mean(axis=1) for j in keep]) >= rr.MIN_SHARE_PER_FACTOR).all(axis=1)
    F, _ = rr.available_scores(Xv[elig], w[elig], Rp, L, Phi)
    we, se = w[elig], s[elig]
    S = pd.DataFrame({names[j]: F[:, j] for j in keep})
    cols = list(S.columns)
    if {"SO", "RT", "PC"} <= set(cols):
        for c in ("RT", "PC"):
            S[c] = em.wresid(S[c].values, S["SO"].values, we)
    # only the alignment contrasts among partisans are removed (opposed and split vs aligned); the nonpartisan term
    # is a control, so nonpartisans' own difference from partisans stays in the score
    Xd = np.column_stack([np.ones(len(S))] + [(se == g).astype(float) for g in ("nonpartisan", "opposed", "split")])
    sw = np.sqrt(we / we.mean())
    r2 = []
    for c in cols:
        y = S[c].values
        beta = np.linalg.lstsq(Xd * sw[:, None], y * sw, rcond=None)[0]
        removed_part = Xd[:, 2:] @ beta[2:]
        r2.append({"factor": c, "alignment_r2": round(float(np.cov(removed_part, aweights=we) / np.cov(y, aweights=we)), 4),
                   "beta_opposed": round(float(beta[2]), 3), "beta_split": round(float(beta[3]), 3),
                   "beta_nonpartisan_kept": round(float(beta[1]), 3)})
        S[c] = y - removed_part
    r2 = pd.DataFrame(r2)
    r2.to_csv(OUT / "strata_r2.csv", index=False)
    print("alignment effect removed from each clustering score (nonpartisan difference kept):\n", r2.to_string(index=False))
    S.insert(0, "caseid", caseid[elig])
    S.insert(1, "commonpostweight", we)
    S.to_csv(OUT / "scores.csv", index=False)
    print(f"eligible {elig.sum():,}; clustering on {cols}", flush=True)

    Xc = S[cols].values
    lab_path = OUT / "labels.npz"
    if lab_path.exists():
        store = dict(np.load(lab_path))
    else:
        jobs = [delayed(fc.job)(Xc, "dpgmm", K, kind, i) for K in CAPS
                for kind, rng in (("seed", fc.SEEDS), ("boot", range(fc.N_BOOT))) for i in rng]
        res = Parallel(n_jobs=11, verbose=1)(jobs)
        acc = {}
        for _, K, kind, i, labels, bound in res:
            acc.setdefault((K, kind), []).append((i, labels, bound))
        store = {}
        for (K, kind), v in acc.items():
            v = sorted(v, key=lambda t: t[0])
            store[f"{K}_{kind}"] = np.stack([l for _, l, _ in v])
            store[f"{K}_{kind}_bounds"] = np.array([b for *_, b in v])
        np.savez_compressed(lab_path, **store)
    summary, clusters = [], []
    for K in CAPS:
        seeds = list(zip(fc.SEEDS, store[f"{K}_seed"], store[f"{K}_seed_bounds"]))
        sm, cl = fd.summarize(Xc, we, np.array(["x"] * len(S)), seeds, list(store[f"{K}_boot"]), K, cols)
        summary.append(sm)
        clusters += cl
    summ = pd.DataFrame(summary)
    summ.to_csv(OUT / "summary.csv", index=False)
    pd.DataFrame(clusters).to_csv(OUT / "clusters.csv", index=False)
    ok = summ[summ.n_dissolved == 0]
    kept = int(ok.K.max()) if not ok.empty else None
    print("\ncap scan:\n", summ.to_string(index=False))
    print(f"cap rule (largest cap with no dissolved cluster): {kept}", flush=True)

    # compare the kept cap's modal solution to the reference ten
    S0 = pd.read_csv(fd.OUT / "scores.csv", usecols=["caseid"])
    z = np.load(fd.OUT / "labels.npz")
    ref = pd.Series(ld.modal_solution(list(zip(range(42, 62), z["10_seed"], z["10_seed_bounds"])))[0], index=S0.caseid.values)
    out = []
    for K in sorted({kept, 10} - {None}):
        lab, n_sol, share = ld.modal_solution(list(zip(fc.SEEDS, store[f"{K}_seed"], store[f"{K}_seed_bounds"])))
        common = np.intersect1d(S.caseid.values, ref.index.values)
        r_, l_ = ref.loc[common].values, pd.Series(lab, index=S.caseid.values).loc[common].values
        w_ = S.set_index("caseid").commonpostweight.loc[common].values
        rows_ = pd.DataFrame(ld.match(r_, l_, w_, {k_: f"C{k_}" for k_ in np.unique(r_)}))
        stc = pd.Series(st[elig], index=S.caseid.values).loc[common].values
        c9 = pd.Series(w_[r_ == 9]).groupby(l_[r_ == 9]).sum().idxmax()
        a = pd.Series(w_ * (l_ == c9)).groupby(stc).sum()
        b = pd.Series(w_).groupby(stc).sum()
        idx = 0.5 * (a / a.sum() - b / b.sum()).abs().sum()
        print(f"\ncap {K}: {n_sol} seed solutions (modal {share:.2f}); ARI vs reference ten {ari(r_, l_):.3f}; "
              f"C9's best match {w_[l_ == c9].sum() / w_.sum() * 100:.1f}% of respondents, state index {idx:.3f}")
        print(rows_.set_index("party").round(3).T.to_string())
        out += [{"cap": K, **r} for r in rows_.to_dict(orient="records")]
    pd.DataFrame(out).to_csv(OUT / "compare.csv", index=False)


if __name__ == "__main__":
    main()

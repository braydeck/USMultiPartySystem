"""The four-dimension clustering with only the state-alignment part of distrust removed (2026-11-03, after results
were seen; a sensitivity check, not a rule change; disclosed in DECISIONS.md).

Data: CES 2024 Common Content. Scores: outputs/four_dim/scores.csv (the reference space, unchanged: SO, TR, RT_resid,
PC_resid; 49,431 eligible respondents). Alignment: state_control.strata, pid7 leaners as partisans, 2024 governor +
both chambers from analysis/efa/state_control_2024.csv -> aligned / opposed / split / nonpartisan.
Adjustment: weighted OLS of TR on stratum indicators (aligned is the base); only the opposed and split contrasts are
subtracted, so the nonpartisan difference stays in the score. The other three dimensions are untouched, which isolates
the alignment adjustment from the factor reshaping in state_control.py.
Cap scan 2-10 with the four_dim_space procedure (DPGMM, 20 seeds 42-61, 30 resample fits, Jaccard >= 0.75 stable,
< 0.5 dissolved; cap rule = largest cap with no dissolved cluster). Kept cap and cap 10 compared to the reference ten
(cap-10 modal seed solution of outputs/four_dim/), with each cluster's state concentration (dissimilarity index of the
cluster's state distribution vs everyone's).
Writes outputs/four_dim_aligned/{summary.csv, clusters.csv, compare.csv, state_index.csv, labels.npz}.
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
import state_control as sc_

fc = fd.fc
OUT = rl.OUT / "four_dim_aligned"
CAPS = range(2, 11)
COLS = ["SO", "TR_aligned", "RT_resid", "PC_resid"]


def state_index(mask, st, w):
    a = pd.Series(w * mask).groupby(st).sum()
    b = pd.Series(w).groupby(st).sum()
    return 0.5 * (a / a.sum() - b / b.sum()).abs().sum()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    S = pd.read_csv(fd.OUT / "scores.csv")
    _, _, pid, caseid = ip.load()
    s_all, st_all = sc_.strata(caseid, pid)
    s = pd.Series(s_all, index=caseid).loc[S.caseid].values
    st = pd.Series(st_all, index=caseid).loc[S.caseid].values
    w = S.commonpostweight.values
    Xd = np.column_stack([np.ones(len(S))] + [(s == g).astype(float) for g in ("nonpartisan", "opposed", "split")])
    sw = np.sqrt(w / w.mean())
    y = S.TR.values
    beta = np.linalg.lstsq(Xd * sw[:, None], y * sw, rcond=None)[0]
    removed = Xd[:, 2:] @ beta[2:]
    S["TR_aligned"] = y - removed
    r2 = float(np.cov(removed, aweights=w) / np.cov(y, aweights=w))
    print(f"n {len(S):,}; strata (weighted %): " + ", ".join(f"{g} {w[s == g].sum() / w.sum() * 100:.1f}" for g in sc_.STRATA))
    print(f"distrust on alignment: opposed {beta[2]:+.3f}, split {beta[3]:+.3f}, nonpartisan {beta[1]:+.3f} (kept); "
          f"share of distrust variance removed {r2:.4f}; r(TR, TR_aligned) {np.corrcoef(y, S.TR_aligned)[0, 1]:.3f}", flush=True)
    X = S[COLS].values

    lab_path = OUT / "labels.npz"
    if lab_path.exists():
        store = dict(np.load(lab_path))
    else:
        jobs = [delayed(fc.job)(X, "dpgmm", K, kind, i) for K in CAPS
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
        sm, cl = fd.summarize(X, w, np.array(["x"] * len(S)), seeds, list(store[f"{K}_boot"]), K, COLS)
        summary.append(sm)
        clusters += cl
    summ = pd.DataFrame(summary)
    summ.to_csv(OUT / "summary.csv", index=False)
    pd.DataFrame(clusters).to_csv(OUT / "clusters.csv", index=False)
    ok = summ[summ.n_dissolved == 0]
    kept = int(ok.K.max()) if not ok.empty else None
    ref_summ = pd.read_csv(fd.OUT / "summary.csv")
    print("\ncap scan, alignment-adjusted distrust:\n", summ.to_string(index=False))
    print("\ncap scan, reference (unadjusted):\n", ref_summ.to_string(index=False))
    print(f"\ncap rule: {kept}", flush=True)

    z = np.load(fd.OUT / "labels.npz")
    ref = ld.modal_solution(list(zip(range(42, 62), z["10_seed"], z["10_seed_bounds"])))[0]
    out, sidx = [], []
    for c in np.unique(ref):
        sidx.append({"solution": "reference 10", "cluster": int(c), "share": round(w[ref == c].sum() / w.sum() * 100, 1),
                     "state_index": round(state_index(ref == c, st, w), 3)})
    for K in sorted({kept, 10} - {None}):
        lab, n_sol, share = ld.modal_solution(list(zip(fc.SEEDS, store[f"{K}_seed"], store[f"{K}_seed_bounds"])))
        rows = pd.DataFrame(ld.match(ref, lab, w, {k: f"C{k}" for k in np.unique(ref)}))
        out += [{"cap": K, **r} for r in rows.to_dict(orient="records")]
        c9 = pd.Series(w[ref == 9]).groupby(lab[ref == 9]).sum().idxmax()
        for c in np.unique(lab):
            m = lab == c
            ov = pd.Series(w[m]).groupby(ref[m]).sum().sort_values(ascending=False) / w[m].sum()
            sidx.append({"solution": f"adjusted {K}", "cluster": int(c), "share": round(w[m].sum() / w.sum() * 100, 1),
                         "state_index": round(state_index(m, st, w), 3),
                         "from_reference": ", ".join(f"C{k} {v * 100:.0f}" for k, v in ov.items() if v >= 0.08),
                         **{col: round(float(np.average(X[m, j], weights=w[m])), 2) for j, col in enumerate(COLS)}})
        print(f"\ncap {K}: {n_sol} seed solutions (modal {share:.2f}); ARI vs reference ten {ari(ref, lab):.3f}; "
              f"C9's best match is {w[lab == c9].sum() / w.sum() * 100:.1f}% of respondents, state index "
              f"{state_index(lab == c9, st, w):.3f} (C9 {state_index(ref == 9, st, w):.3f})")
        print(rows.set_index("party").round(3).T.to_string())
    pd.DataFrame(out).to_csv(OUT / "compare.csv", index=False)
    si = pd.DataFrame(sidx)
    si.to_csv(OUT / "state_index.csv", index=False)
    rng = np.random.default_rng(42)
    chance = np.mean([state_index(rng.random(len(w)) < 0.05, st, w) for _ in range(50)])
    print(f"\nstate concentration by cluster (chance for a 5% random group ~{chance:.3f}):\n", si.to_string(index=False))


if __name__ == "__main__":
    main()

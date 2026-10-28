"""Cluster ANES 2024 on the matched factors, with a CES subsample benchmark at ANES's n.

Data: CES 2024 Common Content (UNTRACKED/CES Data/2024, canonical recode from
analysis/efa/previous_years/wave_2024/reproduce_gate.py, listwise n = 45,707, production
parties from data/processed/typology_cluster_assignments.csv joined by position); ANES 2024
matched set (config/anes_matched_crosswalk.csv, n = 3,796).

Every fit runs the production chain from reproduce_gate.py: weighted polychoric -> PAF k=5 +
oblimin -> Thomson scores -> partisan sign-align -> religion/values factors residualized on the
enforcement factor (anchors CC24_323b, pew_churatd, CC24_440b) -> 10-component DPGMM, seed 42.

  1. CES full sample on the 18 matched items: party survival from dropping 6 items alone.
  2. Benchmark: 100 simple random CES subsamples of n = 3,796 (seed 42), on the 18 items and on
     the full 24. Survival per production party, criterion from
     analysis/efa/exploration/cluster_survival_k4_k5.py: SURVIVES if >= 60% of the party's weight
     sits in one cluster and the party is >= 50% of that cluster; "splits" if under 60%;
     otherwise "merges-in".
  3. ANES on the 18 items. ANES has no party labels, so each ANES cluster is labeled by its
     nearest production-party centroid in the CES-full 18-item factor space (factors aligned by
     Tucker match on loadings, scores standardized per respondent). The same labeling is
     applied to the CES-18 subsamples, where the truth is known, to measure how often it
     names the right party.
"""
import sys

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

import matched_efa as me
import recode_matched as rm
from common import clustering as cl
from common import congruence as cg
from common import efa_math as em

sys.path.insert(0, str(me.ROOT / "analysis" / "efa" / "previous_years" / "wave_2024"))
import reproduce_gate as rg  # noqa: E402

OUT = me.OUT / "clustering"
N_SUB, N_REP, SEED = 3796, 100, 42
PARTIES = cl.PARTY_CODES
ANCHORS = ("CC24_323b", "pew_churatd", "CC24_440b")


def run_chain(D, w, pid3, ids):
    R = em.regularize_corr(em.polychoric_matrix(D, ids, w, progress=False))
    L_un, _, _ = em.paf(R, 5)
    L, Phi = em.oblimin(L_un)
    Z, _, _ = em.weighted_standardize(D[ids].values.astype(float), w)
    F, _ = em.thomson_scores(Z, R, L, Phi)
    F, L = em.sign_align_by_loading(F, L)
    enf, rel, val = (int(np.argmax(np.abs(L[ids.index(a)]))) for a in ANCHORS)
    dem, rep = pid3 == 1, pid3 == 2
    for j in {enf, rel, val}:
        if np.average(F[rep, j], weights=w[rep]) < np.average(F[dem, j], weights=w[dem]):
            F[:, j] *= -1
            L[:, j] *= -1
    X = F.copy()
    for j in {rel, val} - {enf}:
        X[:, j] = em.wresid(F[:, j], F[:, enf], w)
    model, raw, _ = cl.dpgmm_fit(X)
    cluster, _ = cl.remap_by_weighted_n(raw, w, model.weights_)
    X = (X - np.average(X, axis=0, weights=w)) / np.sqrt(np.average((X - np.average(X, axis=0, weights=w)) ** 2, axis=0, weights=w))
    return L, X, cluster


def survival(cluster, party, w):
    rows = []
    ok = cluster >= 0
    ct = pd.crosstab(party[ok], cluster[ok], values=w[ok], aggfunc="sum").fillna(0)
    for p in range(len(PARTIES)):
        if p not in ct.index:
            continue
        row = ct.loc[p]
        bc = row.idxmax()
        pur, share = row[bc] / row.sum(), row[bc] / ct[bc].sum()
        verdict = "SURVIVES" if pur >= 0.6 and share >= 0.5 else ("splits" if pur < 0.6 else "merges-in")
        rows.append({"party": PARTIES[p], "best_cluster": int(bc), "purity": round(pur, 3),
                     "cluster_share": round(share, 3), "verdict": verdict})
    return pd.DataFrame(rows)


def align_to(L_ref, L, X):
    """Permute/flip a fit's factor columns to the reference fit's order by Tucker match."""
    Xa = np.zeros_like(X)
    for m in cg.match_factors(L_ref, L):
        Xa[:, m["factor_1"]] = X[:, m["factor_2"]] * (1 if m["sign"] == "+" else -1)
    return Xa


def label_clusters(Xa, cluster, w, party_centroids):
    n = cluster.max() + 1
    C = cl.weighted_centroids(Xa, cluster, w, n)
    dist = np.linalg.norm(C[:, None, :] - party_centroids[None, :, :], axis=2)
    nearest = dist.argmin(axis=1)
    ri, ci = linear_sum_assignment(dist)
    hung = dict(zip(ri, ci))
    return C, dist, nearest, hung


def load_ces():
    """Production labels attach by position on production's own mask (efa_update.py reads raw
    numeric codes, ITEMS_24 + commonpostweight notna -> 45,707). Item values come from the
    label-based canonical recode, which also sets Don't-know codes to missing, so rows that
    production kept as numeric codes are then dropped."""
    num = pd.read_stata(str(rg.DTA), columns=rg.ITEMS + ["commonpostweight"], convert_categoricals=False)
    prod_mask = num[rg.ITEMS + ["commonpostweight"]].notna().all(axis=1).values
    df = pd.read_stata(str(rg.DTA), columns=rg.ITEMS + ["commonpostweight", "pid3"],
                       convert_categoricals=True, convert_missing=False, convert_dates=False)
    R = rg.canonical_recode(df)
    R["w"] = pd.to_numeric(df["commonpostweight"], errors="coerce").values
    R["pid3"] = df["pid3"].map({"Democrat": 1, "Republican": 2, "Independent": 3, "Other": 4, "Not sure": 5}).values
    prod = pd.read_csv(me.ROOT / "data" / "processed" / "typology_cluster_assignments.csv", usecols=["cluster", "commonpostweight"])
    assert prod_mask.sum() == len(prod), "production mask does not reproduce 45,707"
    R = R[prod_mask].reset_index(drop=True)
    assert np.allclose(prod.commonpostweight.values, R.w.values), "positional join broken"
    R["party"] = prod.cluster.values
    clean = R[rg.ITEMS].notna().all(axis=1)
    print(f"production rows {len(R):,}; dropped {int((~clean).sum()):,} whose items are non-substantive codes", flush=True)
    return R[clean].reset_index(drop=True)


def main():
    OUT.mkdir(exist_ok=True)
    ces = load_ces()
    ids18 = list(pd.read_csv(rm.CROSSWALK).query("fidelity != 'none'").ces_var)
    w, pid3, party = ces.w.values, ces.pid3.values, ces.party.values
    print(f"CES listwise n = {len(ces):,}; matched items = {len(ids18)}", flush=True)

    # Ceiling: a fresh fit on all 24 items at full n. Anything below it in the rows that
    # follow is the cost of fewer items or smaller n, not of refitting from scratch.
    _, _, clu24 = run_chain(ces, w, pid3, rg.ITEMS)
    surv24 = survival(clu24, party, w)
    surv24.to_csv(OUT / "ces24_fullsample_survival.csv", index=False)
    print(f"\n[0] CES full sample, 24 items (ARI vs production {cl.ari(clu24, party):.2f}):\n", surv24.to_string(index=False))

    L_ref, X_ref, clu_ref = run_chain(ces, w, pid3, ids18)
    surv_full = survival(clu_ref, party, w)
    surv_full.to_csv(OUT / "ces18_fullsample_survival.csv", index=False)
    print("\n[1] CES full sample, 18 items:\n", surv_full.to_string(index=False))
    party_centroids = cl.weighted_centroids(X_ref, party, w, len(PARTIES))

    rng = np.random.default_rng(SEED)
    reps, calib = [], []
    for rep in range(N_REP):
        idx = np.sort(rng.choice(len(ces), size=N_SUB, replace=False))
        S = ces.iloc[idx].reset_index(drop=True)
        ws, ps, pt = S.w.values, S.pid3.values, S.party.values
        for label, ids in (("18 items", ids18), ("24 items", rg.ITEMS)):
            L, X, clu = run_chain(S, ws, ps, ids)
            sv = survival(clu, pt, ws).assign(rep=rep, items=label, n_clusters=int(clu.max() + 1))
            reps.append(sv)
            if label == "18 items":
                Xa = align_to(L_ref, L, X)
                _, _, nearest, hung = label_clusters(Xa, clu, ws, party_centroids)
                for k in range(clu.max() + 1):
                    m = clu == k
                    truth = pd.Series(ws[m]).groupby(pt[m]).sum().idxmax()
                    calib.append({"rep": rep, "cluster": k, "share": ws[m].sum() / ws.sum(), "truth": PARTIES[truth],
                                  "nearest": PARTIES[nearest[k]], "hungarian": PARTIES[hung[k]] if k in hung else None})
        if (rep + 1) % 10 == 0:
            print(f"  benchmark {rep + 1}/{N_REP}", flush=True)
    reps = pd.concat(reps)
    reps.to_csv(OUT / "benchmark_reps.csv", index=False)
    summ = (reps.groupby(["items", "party"]).verdict.value_counts(normalize=True).unstack(fill_value=0)
            .reindex(columns=["SURVIVES", "splits", "merges-in"], fill_value=0).round(2).reset_index())
    summ.to_csv(OUT / "benchmark_summary.csv", index=False)
    print("\n[2] Benchmark, share of 100 CES subsamples (n = 3,796):\n", summ.to_string(index=False))
    print("clusters per subsample:", reps.groupby("items").n_clusters.describe()[["mean", "min", "max"]].round(1).to_dict())
    calib = pd.DataFrame(calib)
    calib.to_csv(OUT / "label_calibration.csv", index=False)
    for col in ("nearest", "hungarian"):
        acc = np.average(calib[col] == calib.truth, weights=calib.share)
        print(f"label method '{col}' names the cluster's plurality party for {acc:.0%} of subsample weight")
    by_truth = calib.assign(hit=calib.hungarian == calib.truth).groupby("truth").apply(
        lambda g: np.average(g.hit, weights=g.share)).round(2)
    by_truth.to_csv(OUT / "label_calibration_by_party.csv", header=["hungarian_hit_rate"])
    print("Hungarian hit rate by true party:", by_truth.to_dict())

    raw, items, _ = rm.load_matched()
    wa = raw[rm.WEIGHT].values.astype(float)
    pid_raw = pd.read_csv(rm.ANES_CSV, usecols=["V241221"]).V241221.values
    pa = np.where(pid_raw == 1, 1, np.where(pid_raw == 2, 2, 3))
    keep = items.notna().all(axis=1).values & ~np.isnan(wa) & (wa > 0)
    A = items[keep].reset_index(drop=True)
    wa, pa = wa[keep], pa[keep]
    L_a, X_a, clu_a = run_chain(A, wa, pa, ids18)
    Xa = align_to(L_ref, L_a, X_a)
    C, dist, nearest, hung = label_clusters(Xa, clu_a, wa, party_centroids)
    ces_pid = pd.DataFrame({"p": party, "w": w, "d": pid3 == 1, "r": pid3 == 2})
    ces_mix = ces_pid.groupby("p").apply(lambda g: pd.Series({
        "ces_share": g.w.sum() / w.sum(), "ces_dem": np.average(g.d, weights=g.w), "ces_rep": np.average(g.r, weights=g.w)}))
    rows = []
    for k in range(clu_a.max() + 1):
        m = clu_a == k
        h = hung.get(k)
        rows.append({"anes_cluster": k, "share": wa[m].sum() / wa.sum(), "dem": np.average(pa[m] == 1, weights=wa[m]),
                     "rep": np.average(pa[m] == 2, weights=wa[m]), "nearest_party": PARTIES[nearest[k]],
                     "nearest_dist": dist[k, nearest[k]], "hungarian_party": PARTIES[h] if h is not None else None,
                     "hungarian_dist": dist[k, h] if h is not None else np.nan,
                     "party_ces_share": ces_mix.ces_share[h] if h is not None else np.nan,
                     "party_ces_dem": ces_mix.ces_dem[h] if h is not None else np.nan,
                     "party_ces_rep": ces_mix.ces_rep[h] if h is not None else np.nan})
    anes = pd.DataFrame(rows).round(3)
    anes.to_csv(OUT / "anes_clusters.csv", index=False)
    pd.DataFrame(C, columns=[f"F{j + 1}" for j in range(5)]).round(3).to_csv(OUT / "anes_cluster_centroids.csv")
    pd.DataFrame(party_centroids, index=PARTIES, columns=[f"F{j + 1}" for j in range(5)]).round(3).to_csv(
        OUT / "ces18_party_centroids.csv")
    print(f"\n[3] ANES clusters (n = {len(A):,}):\n", anes.to_string(index=False))


if __name__ == "__main__":
    main()

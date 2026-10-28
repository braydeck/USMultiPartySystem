"""How much does the church-attendance "Don't know" leak move the production party assignments?

Data provenance
  - CES 2024 Common Content, UNTRACKED/CES Data/2024/CCES24_Common_OUTPUT_vv_topost_final (2).dta,
    24 typology items + commonpostweight + pid3. Production mask (efa_update.py: raw numeric codes,
    ITEMS_24 + commonpostweight notna) gives n = 45,707; 493 of them have pew_churatd raw code 7
    ("Don't know").
  - Production parties: data/processed/typology_cluster_assignments.csv (no caseid; joined by
    position, weights asserted equal). Saved production factor scores are in the same file.
  - Frozen correlation matrix: data/processed/polychoric_matrix.csv (built by efa_pipeline_v4.py
    with "Don't know" missing), CC24_340a dropped.
  - Chain: analysis/efa/previous_years/wave_2024/reproduce_gate.py (canonical_recode) and
    analysis/efa/previous_years/common/ (polychoric, PAF k=5 + oblimin, Thomson, DPGMM seed 42).

Runs (all fresh fits, DPGMM seed 42)
  Canonical coding (label-based recode; the brief's runs):
    A        45,707, church = 7 for the 493 DK, frozen matrix
    B        45,214 (DK dropped), polychoric recomputed on that sample
    B_frozen 45,214 (DK dropped), frozen matrix (isolates the drop from the matrix recompute)
    N42-N46  A's setup with 493 random non-DK rows dropped (seeds 42-46)
  Production coding (raw numeric codes recoded exactly as efa_update.py does):
    P        45,707, frozen matrix: checks that this reproduces the saved production scores/parties
    P_noDK   45,214, frozen matrix
    PN42-46  P's setup with 493 random non-DK rows dropped
  S0       DPGMM refit on the saved production scores (determinism check)

Run: .venv/bin/python analysis/efa/exploration/church_dk/church_dk_impact.py
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "analysis" / "efa" / "previous_years"))
sys.path.insert(0, str(ROOT / "analysis" / "efa" / "previous_years" / "wave_2024"))
import reproduce_gate as rg  # noqa: E402
from common import clustering as cl  # noqa: E402
from common import efa_math as em  # noqa: E402

OUT = HERE / "outputs"
ITEMS = rg.ITEMS
PARTIES = cl.PARTY_CODES
ANCHORS = ("CC24_323b", "pew_churatd", "CC24_440b")
NOISE_SEEDS = [42, 43, 44, 45, 46]
REV_BINARY = {"CC24_341c", "CC24_341d", "CC24_323a", "CC24_323d", "CC24_321e", "CC24_340b", "CC24_340c"}


def production_coding(num):
    """efa_update.py's recode of the raw numeric codes, step for step."""
    P = num[ITEMS].copy()
    for c in ("CC24_423", "CC24_424"):
        P[c] = P[c].where(P[c] != 8, 2)
    chk = num[["CC24_303", "CC24_341a", "commonpostweight"]].notna().all(axis=1)
    if np.corrcoef(num.loc[chk, "CC24_303"], num.loc[chk, "CC24_341a"])[0, 1] < 0:
        P["CC24_303"] = 6 - P["CC24_303"]
    for c in REV_BINARY:
        P[c] = 3 - P[c]
    P["CC24_325"] = 40 - P["CC24_325"]
    return P


def load():
    num = pd.read_stata(str(rg.DTA), columns=ITEMS + ["commonpostweight", "pid3"], convert_categoricals=False)
    lab = pd.read_stata(str(rg.DTA), columns=ITEMS + ["commonpostweight", "pid3"],
                        convert_categoricals=True, convert_missing=False, convert_dates=False)
    mask = num[ITEMS + ["commonpostweight"]].notna().all(axis=1).values
    prod = pd.read_csv(ROOT / "data" / "processed" / "typology_cluster_assignments.csv")
    assert mask.sum() == len(prod) == 45707
    w = num.commonpostweight.values[mask]
    assert np.allclose(prod.commonpostweight.values, w), "positional join broken"
    canon = rg.canonical_recode(lab)[mask].reset_index(drop=True)
    dk = (num.pew_churatd.values[mask] == 7)
    assert dk.sum() == 493
    assert (canon[ITEMS].isna().any(axis=1).values == dk).all(), "a non-church item also leaks"
    canon.loc[dk, "pew_churatd"] = 7.0
    pcode = production_coding(num)[mask].reset_index(drop=True)
    pid3 = num.pid3.values[mask]
    return dict(canon=canon[ITEMS].values.astype(float), pcode=pcode.values.astype(float), w=w, pid3=pid3,
                dk=dk, party=prod.cluster.values,
                FS=prod[["FS_F1", "FS_F2", "FS_F3", "FS_F4_resid", "FS_F5_resid"]].values)


def frozen_R():
    return em.regularize_corr(pd.read_csv(ROOT / "data/processed/polychoric_matrix.csv", index_col=0)
                              .loc[ITEMS, ITEMS].values.astype(float))


def chain(X, w, pid3, R, loading_align=True):
    """Production chain from reproduce_gate.py. loading_align=False mirrors efa_update.py, which
    applies only the partisan flip (needed to compare scores to production's saved FS columns)."""
    L_un, _, _ = em.paf(R, 5)
    L, Phi = em.oblimin(L_un)
    Z, _, _ = em.weighted_standardize(X, w)
    F, _ = em.thomson_scores(Z, R, L, Phi)
    if loading_align:
        F, L = em.sign_align_by_loading(F, L)
    enf, rel, val = (int(np.argmax(np.abs(L[ITEMS.index(a)]))) for a in ANCHORS)
    dem, rep = pid3 == 1, pid3 == 2
    for j in {enf, rel, val}:
        if np.average(F[rep, j], weights=w[rep]) < np.average(F[dem, j], weights=w[dem]):
            F[:, j] *= -1
    Xc = F.copy()
    for j in {rel, val} - {enf}:
        Xc[:, j] = em.wresid(F[:, j], F[:, enf], w)
    model, raw, _ = cl.dpgmm_fit(Xc)
    cluster, _ = cl.remap_by_weighted_n(raw, w, model.weights_)
    return cluster, Xc


def shares(cluster, w):
    k = cluster.max() + 1
    return np.array([w[cluster == j].sum() for j in range(k)]) / w.sum() * 100


def wct(a, b, w):
    return pd.crosstab(a, b, values=w, aggfunc="sum").fillna(0)


def majority_labels(cluster, party, w):
    ct = wct(cluster, party, w)
    lab = {k: PARTIES[int(ct.loc[k].idxmax())] for k in ct.index}
    seen = {}
    for k in sorted(lab):  # disambiguate duplicate majorities by cluster size order
        seen[lab[k]] = seen.get(lab[k], 0) + 1
        if seen[lab[k]] > 1:
            lab[k] = f"{lab[k]}#{seen[lab[k]]}"
    purity = {k: float(ct.loc[k].max() / ct.loc[k].sum()) for k in ct.index}
    return lab, purity


def compare(ref, ref_w, ref_lab, new, new_w, ref_idx_shared):
    """ref: reference clusters on its full sample; new: clusters on a subsample whose rows are
    ref rows ref_idx_shared. Match new->ref by Hungarian on the weighted crosstab of shared rows."""
    r_sh = ref[ref_idx_shared]
    ct = wct(new, r_sh, new_w)
    ri, ci = linear_sum_assignment(-ct.values)
    mapping = {int(ct.index[i]): int(ct.columns[j]) for i, j in zip(ri, ci)}
    mapped = np.array([mapping.get(int(k), 1000 + int(k)) for k in new])
    changed = mapped != r_sh
    s_ref, s_new = shares(ref, ref_w), shares(new, new_w)
    s_ref_sh = shares(r_sh, new_w)
    rows = []
    for k in range(ref.max() + 1):
        inv = [n for n, r in mapping.items() if r == k]
        rows.append({"party": ref_lab[k], "ref_share": s_ref[k], "ref_share_on_shared": s_ref_sh[k] if k < len(s_ref_sh) else 0.0,
                     "new_share": s_new[inv[0]] if inv else 0.0,
                     "retained": float(new_w[(r_sh == k) & (mapped == k)].sum() / new_w[r_sh == k].sum())})
    for n in sorted(set(np.unique(new)) - set(mapping)):
        rows.append({"party": f"unmatched new cluster {n}", "ref_share": 0.0, "ref_share_on_shared": 0.0,
                     "new_share": s_new[n], "retained": np.nan})
    tab = pd.DataFrame(rows)
    tab["delta_pp"] = tab.new_share - tab.ref_share_on_shared
    return {"ari": cl.ari(r_sh, new), "pct_changed_w": float(new_w[changed].sum() / new_w.sum() * 100),
            "pct_changed_n": float(changed.mean() * 100), "n_clusters_new": int(new.max() + 1),
            "n_clusters_ref": int(ref.max() + 1)}, tab


def main():
    OUT.mkdir(exist_ok=True)
    d = load()
    w, pid3, dk, party = d["w"], d["pid3"], d["dk"], d["party"]
    keep = ~dk
    Rf = frozen_R()
    log = {}
    print(f"n = {len(w):,}; DK = {dk.sum()} ({w[dk].sum() / w.sum() * 100:.2f}% weighted)", flush=True)

    # Which coding reproduces production's saved scores? (|r| per matched column)
    for name, X in (("canonical+DK7", d["canon"]), ("production coding", d["pcode"])):
        L_un, _, _ = em.paf(Rf, 5); L, Phi = em.oblimin(L_un)
        F, _ = em.thomson_scores(em.weighted_standardize(X, w)[0], Rf, L, Phi)
        M = np.abs(np.corrcoef(np.column_stack([F, d["FS"][:, :3]]).T)[:5, 5:])
        log[f"score_r_{name}"] = [round(float(M[:, j].max()), 4) for j in range(3)]
        print(f"max |r| of {name} scores with saved FS_F1..F3: {log[f'score_r_{name}']}", flush=True)

    # S0: DPGMM refit on the saved production scores
    m, raw, _ = cl.dpgmm_fit(d["FS"])
    s0, _ = cl.remap_by_weighted_n(raw, w, m.weights_)
    log["S0_ari_vs_production"] = cl.ari(s0, party)
    print(f"S0 DPGMM refit on saved FS: ARI vs production {log['S0_ari_vs_production']:.3f}", flush=True)

    prod_shares = np.sort(shares(party, w))[::-1]
    results, tables = {}, {}

    def run_set(tag, X, R_full, make_B):
        A, _ = chain(X, w, pid3, R_full)
        A_lab, A_pur = majority_labels(A, party, w)
        a_sh = np.sort(shares(A, w))[::-1]
        results[f"{tag}_vs_production"] = {"ari": cl.ari(A, party), "n_clusters": int(A.max() + 1),
                                           "labels": A_lab, "purity": A_pur}
        pd.DataFrame({"production_sorted": pd.Series(prod_shares), f"{tag}_sorted": pd.Series(a_sh)}).round(2).to_csv(
            OUT / f"{tag}_sorted_shares_vs_production.csv", index=False)
        print(f"\n[{tag}] ARI vs production {results[f'{tag}_vs_production']['ari']:.3f}; labels {A_lab}", flush=True)
        dk_where = (pd.Series(w[dk]).groupby([A_lab[k] for k in A[dk]]).sum() / w[dk].sum() * 100).round(1)
        dk_prod = (pd.Series(w[dk]).groupby([PARTIES[k] for k in party[dk]]).sum() / w[dk].sum() * 100).round(1)
        pd.DataFrame({f"{tag}_cluster_pct": dk_where, "production_party_pct": dk_prod}).fillna(0).to_csv(
            OUT / f"{tag}_where_dk_sat.csv")
        for name, (Xs, Rs, idx) in make_B(X).items():
            clu, _ = chain(Xs, w[idx], pid3[idx], Rs)
            stats, tab = compare(A, w, A_lab, clu, w[idx], idx)
            results[f"{tag}_vs_{name}"] = stats
            tables[f"{tag}_vs_{name}"] = tab
            tab.round(3).to_csv(OUT / f"{tag}_vs_{name}_shares.csv", index=False)
            print(f"  {name}: ARI {stats['ari']:.3f}, changed {stats['pct_changed_w']:.2f}% (w), "
                  f"k {stats['n_clusters_new']}", flush=True)
        return A

    def noise(X, R):
        out = {}
        for s in NOISE_SEEDS:
            rng = np.random.default_rng(s)
            drop = rng.choice(np.flatnonzero(keep), size=int(dk.sum()), replace=False)
            idx = np.setdiff1d(np.arange(len(w)), drop)
            out[f"noise{s}"] = (X[idx], R, idx)
        return out

    idx_keep = np.flatnonzero(keep)

    poly_cache = OUT / "polychoric_B_45214.csv"
    if poly_cache.exists():
        R_B = pd.read_csv(poly_cache, index_col=0).values
    else:
        print("computing polychoric on 45,214 ...", flush=True)
        R_B = em.polychoric_matrix(pd.DataFrame(d["canon"][keep], columns=ITEMS), ITEMS, w[keep], progress=True)
        pd.DataFrame(R_B, index=ITEMS, columns=ITEMS).to_csv(poly_cache)
    R_B = em.regularize_corr(R_B)
    log["B_polychoric_maxdiff_vs_frozen"] = float(np.abs(R_B - Rf).max())

    run_set("A", d["canon"], Rf, lambda X: {"B": (X[keep], R_B, idx_keep), "B_frozen": (X[keep], Rf, idx_keep),
                                            **noise(X, Rf)})
    run_set("P", d["pcode"], Rf, lambda X: {"P_noDK": (X[keep], Rf, idx_keep), **noise(X, Rf)})

    for k, v in results.items():
        if "labels" in v:
            v["labels"] = {str(a): b for a, b in v["labels"].items()}
            v["purity"] = {str(a): round(b, 3) for a, b in v["purity"].items()}
    json.dump({"log": log, "results": results}, open(OUT / "summary.json", "w"), indent=2, default=float)

    for tag, main_runs in (("A", ["B", "B_frozen"]), ("P", ["P_noDK"])):
        noise_tabs = [tables[f"{tag}_vs_noise{s}"] for s in NOISE_SEEDS]
        nd = pd.concat([t.set_index("party").delta_pp.rename(f"n{s}") for t, s in zip(noise_tabs, NOISE_SEEDS)], axis=1)
        side = pd.concat([tables[f"{tag}_vs_{r}"].set_index("party")[["ref_share", "new_share", "delta_pp"]]
                          .add_prefix(f"{r}_") for r in main_runs], axis=1)
        side["noise_min_pp"], side["noise_max_pp"] = nd.min(axis=1), nd.max(axis=1)
        side["noise_max_abs_pp"] = nd.abs().max(axis=1)
        side.round(2).to_csv(OUT / f"{tag}_verdict_table.csv")
        print(f"\n[{tag}] party share deltas vs noise floor:\n{side.round(2).to_string()}")
        ns = pd.DataFrame([results[f"{tag}_vs_noise{s}"] for s in NOISE_SEEDS], index=NOISE_SEEDS)
        print(f"noise ARI {ns.ari.min():.3f}-{ns.ari.max():.3f}; changed {ns.pct_changed_w.min():.2f}-"
              f"{ns.pct_changed_w.max():.2f}%; k {ns.n_clusters_new.min()}-{ns.n_clusters_new.max()}")


if __name__ == "__main__":
    main()

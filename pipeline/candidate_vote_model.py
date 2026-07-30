#!/usr/bin/env python3
"""
candidate_vote_model.py
-----------------------
Models how a representative candidate of each party would vote on each binary
policy bill, from a per-bill logistic regression on the 5 EFA factor scores.

Unlike the chamber vote model (which aggregates observed per-party support over
seats), this predicts a candidate's stance from the party's *ideological
centroid* projected through a fitted factor logit. The prediction discards each
bill's item-specific residual, so it can — and does — disagree with observed
support. That gap ("divergence") is the point: it flags bills where a party
votes against what its own latent ideology predicts.

Method
------
  For each bill P:
    fit  logit(P(yes)) = b0 + Σ b_k · F_k     (weighted GLM over all respondents)
    then P(yes | party) = logistic(b0 + Σ b_k · centroid_k[party])
  Divergence: observed party support − factor-predicted, flagged at |Δ| ≥ 15pp.

  A p10..p90 "spread band" per party used to be emitted alongside pYes, drawn by a 500-sample
  Monte Carlo off the within-party factor SD. Nothing ever rendered it, and because all the draws
  came from one sequentially-consumed RNG the bill set was effectively part of the seed — adding or
  removing a bill re-rolled every band after it. Removed rather than reseeded.

Two validation gates guard correctness:
  A) recoded binary → weighted per-cluster mean must reproduce cluster_stats c0..c9
  B) weighted per-cluster mean of FS_F1..F5 must reproduce candidate centroids

Outputs
-------
  data/outputs/candidate_vote_model.csv   (long: one row per bill × party)
  data/outputs/candidate_vote_params.csv  (per-bill fitted coefficients)
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from pathlib import Path

BASE = Path(__file__).parent.parent
OUT_DIR = BASE / "data" / "outputs"
DTA = BASE / "data" / "raw" / "2024 CES Base" / "CCES24_Common_OUTPUT_vv_topost_final.dta"
TYPO = BASE / "data" / "processed" / "typology_cluster_assignments.csv"
EFA = BASE / "data" / "processed" / "efa_factor_scores.csv"
CLUSTER_STATS = OUT_DIR / "profiles" / "cluster_stats.csv"
CENTROIDS = OUT_DIR / "candidate_factor_centroids.csv"
VOTE_MODEL = OUT_DIR / "house_vote_model.csv"

FACTORS = ["FS_F1", "FS_F2", "FS_F3", "FS_F4", "FS_F5"]
CENTROID_COLS = [
    "F1_security_order", "F2_electoral_skepticism", "F3_government_distrust",
    "F4_religious_traditionalism", "F5_populist_conservatism",
]
CLUSTER_TO_PARTY = {0: "CON", 1: "LBR", 2: "STY", 3: "NAT", 4: "LIB",
                    5: "POP", 6: "CUP", 7: "OAO", 8: "DSA", 9: "PRG"}
PARTY_TO_CLUSTER = {v: k for k, v in CLUSTER_TO_PARTY.items()}

# 24 EFA-anchor items — the listwise mask that defines the typology row set.
ANCHORS = ['pew_churatd', 'CC24_302', 'CC24_303', 'CC24_341a', 'CC24_341c',
           'CC24_341d', 'CC24_323a', 'CC24_323b', 'CC24_323d', 'CC24_321b',
           'CC24_321d', 'CC24_321e', 'CC24_325', 'CC24_324b', 'CC24_340b',
           'CC24_340c', 'CC24_340e', 'CC24_340f', 'CC24_440b', 'CC24_440c',
           'CC24_421_1', 'CC24_421_2', 'CC24_423', 'CC24_424']

DIVERGENCE_THRESHOLD = 15.0   # |observed − predicted| in pp to flag a divergence


def wpct(binvals, w, m):
    """Weighted % of 1s among non-NaN binary values under mask m."""
    v = binvals[m]
    ww = w[m]
    ok = ~np.isnan(v)
    if not ok.any() or ww[ok].sum() == 0:
        return np.nan
    return float((ww[ok] * v[ok]).sum() / ww[ok].sum() * 100.0)


def wmean(vals, w, m):
    v = vals[m]
    ww = w[m]
    ok = ~np.isnan(v)
    return float((ww[ok] * v[ok]).sum() / ww[ok].sum()) if ok.any() else np.nan


def wstd(vals, w, m):
    v = vals[m]
    ww = w[m]
    ok = ~np.isnan(v)
    v, ww = v[ok], ww[ok]
    if ww.sum() == 0:
        return 0.0
    mu = (ww * v).sum() / ww.sum()
    return float(np.sqrt((ww * (v - mu) ** 2).sum() / ww.sum()))


def logistic(x):
    return 1.0 / (1.0 + np.exp(-x))


def main():

    bills = pd.read_csv(VOTE_MODEL)[["variable", "domain", "question"]]
    bill_vars = bills["variable"].tolist()
    print(f"Bills: {len(bill_vars)}")

    # ── Aligned respondent frame ─────────────────────────────────────────────
    load = list(dict.fromkeys(ANCHORS + bill_vars + ["commonpostweight"]))
    df = pd.read_stata(DTA, columns=load, convert_categoricals=False)
    mask = df[ANCHORS + ["commonpostweight"]].notna().all(axis=1)
    dc = df[mask].reset_index(drop=True)

    typo = pd.read_csv(TYPO)
    efa = pd.read_csv(EFA)
    assert len(dc) == len(typo) == len(efa), \
        f"row mismatch dc={len(dc)} typo={len(typo)} efa={len(efa)}"

    cl = typo["cluster"].values
    w = dc["commonpostweight"].values.astype(float)
    F = {f: efa[f].values.astype(float) for f in FACTORS}
    Fmat = np.column_stack([F[f] for f in FACTORS])

    stats = pd.read_csv(CLUSTER_STATS)
    stats = stats[stats["stat_label"] == "% Supporting"].drop_duplicates("variable")
    stats = stats.set_index("variable")

    # Centroid = weighted mean of FS_F1..F5 within each cluster (the definition).
    # We reconstruct all 10 directly from the aligned factor scores rather than
    # read candidate_factor_centroids.csv, which carries stale cluster labels
    # (REF/CTR for POP/CUP) and no OAO row. The file is used only as a cross-check
    # where its labels still match the current taxonomy.
    pure = {}
    for party, cluster in PARTY_TO_CLUSTER.items():
        pure[party] = np.array([wmean(F[f], w, cl == cluster) for f in FACTORS])

    # ── Validation gate B: cross-check against centroids file where labels match ─
    print("\n── Validation B: centroid cross-check vs candidate_factor_centroids ──")
    centroids = pd.read_csv(CENTROIDS)
    maxdev_b = 0.0
    checked = 0
    for party in PARTY_TO_CLUSTER:
        row = centroids[centroids["candidate_name"] == party]
        if row.empty:
            continue
        filevals = row.iloc[0][CENTROID_COLS].values.astype(float)
        dev = np.abs(pure[party] - filevals).max()
        maxdev_b = max(maxdev_b, dev)
        checked += 1
        if dev > 0.02:
            print(f"  ⚠ {party}: max dev {dev:.4f}  recon={pure[party].round(3)} file={filevals.round(3)}")
    print(f"  cross-checked {checked}/10 parties, max deviation: {maxdev_b:.4f}  "
          f"({'OK' if maxdev_b <= 0.02 else 'FAIL'})")
    assert maxdev_b <= 0.05, "centroid reconstruction off — wrong factor-score columns or join"

    # ── Per-bill: recode, validate, fit, predict ─────────────────────────────
    print("\n── Fitting per-bill logits ──")
    out_rows = []
    param_rows = []
    maxdev_a = 0.0
    const = sm.add_constant(Fmat, has_constant="add")  # [1, F1..F5]

    for _, brow in bills.iterrows():
        var, domain, question = brow["variable"], brow["domain"], brow["question"]
        raw = dc[var].values.astype(float)
        y = np.where(raw == 1, 1.0, np.where(raw == 2, 0.0, np.nan))

        # Gate A: recoded → per-cluster weighted mean matches cluster_stats c0..c9
        if var in stats.index:
            for cluster in range(10):
                obs = stats.loc[var, f"c{cluster}"]
                rec = wpct(y, w, cl == cluster)
                if not np.isnan(obs) and not np.isnan(rec):
                    dev = abs(obs - rec)
                    maxdev_a = max(maxdev_a, dev)
                    if dev > 0.6:
                        print(f"  ⚠ {var} c{cluster}: observed {obs:.2f} vs recode {rec:.2f} (Δ{dev:.2f})")

        # Fit weighted logit on non-NaN rows
        fit_mask = ~np.isnan(y)
        model = sm.GLM(y[fit_mask], const[fit_mask],
                       family=sm.families.Binomial(),
                       freq_weights=w[fit_mask])
        res = model.fit()
        beta = res.params  # [b0, b_F1..b_F5]
        # McFadden pseudo-R²
        pr2 = float(1.0 - res.llf / res.llnull) if res.llnull != 0 else np.nan
        param_rows.append({
            "variable": var, "intercept": round(float(beta[0]), 5),
            **{f"b_{FACTORS[k]}": round(float(beta[k + 1]), 5) for k in range(5)},
            "n": int(fit_mask.sum()), "pseudo_r2": round(pr2, 4),
        })

        for party, cluster in PARTY_TO_CLUSTER.items():
            if party not in pure:
                continue
            c = pure[party]
            lin = beta[0] + float(np.dot(beta[1:], c))
            p_yes = logistic(lin)
            observed = stats.loc[var, f"c{cluster}"] if var in stats.index else np.nan
            delta = (observed - p_yes * 100.0) if not np.isnan(observed) else np.nan
            out_rows.append({
                "variable": var, "domain": domain, "question": question,
                "party": party,
                "pYes": round(float(p_yes), 4),
                "observedPct": round(float(observed), 2) if not np.isnan(observed) else "",
                "delta": round(float(delta), 2) if not np.isnan(delta) else "",
                "diverges": bool(abs(delta) >= DIVERGENCE_THRESHOLD) if not np.isnan(delta) else False,
            })

    print(f"\n── Validation A: recode vs observed ── max cluster deviation: "
          f"{maxdev_a:.3f}pp  ({'OK' if maxdev_a <= 0.6 else 'CHECK'})")

    pd.DataFrame(out_rows).to_csv(OUT_DIR / "candidate_vote_model.csv", index=False)
    pd.DataFrame(param_rows).to_csv(OUT_DIR / "candidate_vote_params.csv", index=False)
    print(f"\nSaved {len(out_rows)} rows → candidate_vote_model.csv")
    print(f"Saved {len(param_rows)} rows → candidate_vote_params.csv")

    # ── Spot checks ──────────────────────────────────────────────────────────
    print("\n── SPOT CHECKS ──")
    dfo = pd.DataFrame(out_rows)
    for var, label in [("CC24_341a", "Extend 2017 tax cuts"),
                       ("CC24_321c", "Background checks (near-universal)")]:
        sub = dfo[dfo["variable"] == var]
        if sub.empty:
            continue
        print(f"\n{var} — {label}:")
        for _, r in sub.iterrows():
            flag = " ⚠DIVERGE" if r["diverges"] else ""
            print(f"  {r['party']:>4}  pred {r['pYes']*100:5.1f}%   "
                  f"obs {r['observedPct']}%   Δ {r['delta']}{flag}")

    n_div = int(dfo["diverges"].sum())
    print(f"\nTotal divergences flagged (|Δ|≥{DIVERGENCE_THRESHOLD}pp): {n_div} "
          f"of {len(dfo)} bill×party cells")
    print("\n✓ Done.")


if __name__ == "__main__":
    main()

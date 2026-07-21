#!/usr/bin/env python3
"""Build a validated 21-item short-form scoring key for the quiz.

Predicts the full-model EFA factor scores (raw F1/F2/F4/F5) from the 21 quiz
items, recoded to the quiz's 0-1 answer scale, then classifies with a
FULL-COVARIANCE Gaussian per cluster. Full covariance makes the classifier
invariant to the F1-residualization of F4/F5 (raw space == resid space under an
invertible linear map), so the residualized cluster definition is honored without
having to score in resid space -- and it reproduces the DPGMM assignments better
than a diagonal classifier in either space.

Ships viz/src/data/quizShortform.json:
  variables  - the 21 items in order
  weights    - per factor: intercept + item coefficients (raw 0-1 answer scale)
  popSd      - per factor: population sd (to z-scale the display dots)
  classify   - per cluster: 4-vector mean, 4x4 inverse covariance, logDet; + temp

Run from repo root:  python3 analysis/efa/build_quiz_shortform.py
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
CES = ROOT / "CCES24_Common_OUTPUT_vv_topost_final.csv"
PROC = ROOT / "data" / "processed"
VIZDATA = ROOT / "viz" / "src" / "data"
OUT = VIZDATA / "quizShortform.json"

# Predict + classify in the DPGMM's 5-D space (F3 is a hidden classification
# dimension: fed to the match, never shown). DISPLAY is the subset with FactorBars.
FACTORS = ["F1", "F2", "F3", "F4", "F5"]
DISPLAY = ["F1", "F2", "F4", "F5"]
TEMP = 3
C2P = {0: "CON", 1: "LBR", 2: "STY", 3: "NAT", 4: "LIB", 5: "POP", 6: "CUP", 7: "OAO", 8: "DSA", 9: "PRG"}
WING = {"CON": "R", "NAT": "R", "POP": "R", "LBR": "L", "STY": "L", "LIB": "L", "PRG": "L", "DSA": "L", "CUP": "C", "OAO": "C"}

RAW = {"CC24_421_1_agree": "CC24_421_1", "CC24_421_2_agree": "CC24_421_2",
       "CC24_440b_agree": "CC24_440b", "CC24_440c_agree": "CC24_440c", "CC24_325_median": "CC24_325"}
AGREE = {1: 1.0, 2: 0.75, 3: 0.5, 4: 0.25, 5: 0.0}
TRUST = {1: 0.0, 2: 0.33, 3: 0.67, 4: 1.0, 8: 1.0}          # "None at all" is code 8
CHURCH = {1: 1.0, 2: 0.8, 3: 0.5, 4: 0.25, 5: 0.1, 6: 0.0}  # 7 = Don't know -> nan


def recode(v, s):
    if v in ("CC24_421_1_agree", "CC24_421_2_agree", "CC24_440b_agree", "CC24_440c_agree"):
        return s.map(AGREE)
    if v in ("CC24_423", "CC24_424"):
        return s.map(TRUST)
    if v == "pew_churatd":
        return s.map(CHURCH)
    if v == "CC24_325_median":
        w = pd.to_numeric(s, errors="coerce"); return w.where((w >= 0) & (w <= 40)) / 40.0
    return s.map({1: 1.0, 2: 0.0})


def wstd(x, w):
    mu = np.average(x, weights=w); return float(np.sqrt(np.average((x - mu) ** 2, weights=w)))


def main():
    qs = json.load(open(VIZDATA / "quizQuestions.json"))
    variables = [q["variable"] for q in qs]

    tp = pd.read_csv(PROC / "turnout_propensity.csv")
    fs = pd.read_csv(PROC / "efa_factor_scores.csv")
    assert len(tp) == len(fs)
    key = pd.DataFrame({"caseid": tp["caseid"].astype("int64"), "cluster": tp["cluster"].values,
                        "w": fs["commonpostweight"].values,
                        **{f: fs[f"FS_{f}"].values for f in FACTORS}})
    ces = pd.read_csv(CES, low_memory=False); ces["caseid"] = ces["caseid"].astype("int64")
    m = key.merge(ces[["caseid"] + [RAW.get(v, v) for v in variables]], on="caseid", how="inner")
    w = m["w"].values
    print(f"merged respondents: {len(m):,}")

    X = pd.DataFrame({v: recode(v, m[RAW.get(v, v)]) for v in variables})
    for v in variables:
        c = X[v].values.astype(float)
        c[np.isnan(c)] = np.average(c[~np.isnan(c)], weights=w[~np.isnan(c)])
        X[v] = c
    Xv = X[variables].values

    # WLS: each raw factor on the 21 items (0-1) + intercept
    A = np.column_stack([np.ones(len(m)), Xv]); sw = np.sqrt(w)
    coefs, r2 = {}, {}
    for f in FACTORS:
        y = m[f].values
        beta, *_ = np.linalg.lstsq(A * sw[:, None], y * sw, rcond=None)
        pred = A @ beta
        r2[f] = 1 - np.average((y - pred) ** 2, weights=w) / np.average((y - np.average(y, weights=w)) ** 2, weights=w)
        coefs[f] = beta
    print("[fit] R2:  " + "  ".join(f"{f}={r2[f]:.3f}" for f in FACTORS))

    popsd = {f: wstd(m[f].values, w) for f in DISPLAY}
    SF = {f: coefs[f][0] + Xv @ coefs[f][1:] for f in FACTORS}  # short-form scores for everyone

    # full-covariance cluster params (weighted) in raw {F1,F2,F4,F5}
    clusters = {}
    for k in range(10):
        sub = m[m.cluster == k]; wk = sub["w"].values
        Xk = np.column_stack([sub[f].values for f in FACTORS])
        mu = np.average(Xk, axis=0, weights=wk)
        d = Xk - mu; cov = (d * wk[:, None]).T @ d / wk.sum()
        ic = np.linalg.inv(cov); _, logdet = np.linalg.slogdet(cov)
        clusters[str(k)] = {"party": C2P[k], "mean": [round(float(x), 6) for x in mu],
                            "invCov": [[round(float(x), 6) for x in row] for row in ic],
                            "logDet": round(float(logdet), 6)}

    # validate: reproduce DPGMM cluster (full-cov, flat prior)
    P = np.column_stack([SF[f] for f in FACTORS]); saved = m["cluster"].values
    ll = np.zeros((len(m), 10))
    for k in range(10):
        c = clusters[str(k)]; mu = np.array(c["mean"]); ic = np.array(c["invCov"])
        dd = P - mu; ll[:, k] = -0.5 * np.einsum("ni,ij,nj->n", dd, ic, dd) - 0.5 * c["logDet"]
    pred = ll.argmax(1)
    ex = np.average(pred == saved, weights=w)
    wg = np.average([WING[C2P[a]] == WING[C2P[b]] for a, b in zip(pred, saved)], weights=w)
    print(f"[validate] full-cov reproduction of DPGMM: exact={ex:.3f}  same-wing={wg:.3f}")

    out = {
        "variables": variables,
        "weights": {f: {"intercept": round(float(coefs[f][0]), 6),
                        **{variables[i]: round(float(coefs[f][i + 1]), 6) for i in range(len(variables))}} for f in FACTORS},
        "popSd": {f: round(popsd[f], 6) for f in DISPLAY},
        "classify": {"factors": FACTORS, "temp": TEMP, "clusters": clusters},
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")

    # the dad, through the new scorer
    dad = {"CC24_321d": 1, "CC24_321e": 0, "CC24_321b": 0.75, "CC24_323b": 1, "CC24_340f": 1, "CC24_323a": 0.25,
           "CC24_323d": 0.75, "CC24_340e": 0, "CC24_341a": 0.75, "CC24_341c": 0, "CC24_341d": 0.25, "CC24_340c": 1,
           "CC24_340b": 0.25, "CC24_421_1_agree": 0.25, "CC24_421_2_agree": 0.25, "CC24_440b_agree": 0.75,
           "CC24_440c_agree": 0.75, "CC24_423": 0.67, "CC24_424": 0.67, "pew_churatd": 0.5, "CC24_325_median": 0.15}
    xd = np.array([dad[v] for v in variables])
    fd = {f: float(coefs[f][0] + xd @ coefs[f][1:]) for f in FACTORS}
    pv = np.array([fd[f] for f in FACTORS])
    lg = {}
    for k in range(10):
        c = clusters[str(k)]; d = pv - np.array(c["mean"])
        lg[C2P[k]] = (-0.5 * d @ np.array(c["invCov"]) @ d - 0.5 * c["logDet"]) / TEMP
    mx = max(lg.values()); e = {p: np.exp(v - mx) for p, v in lg.items()}; Z = sum(e.values())
    top = sorted(((p, e[p] / Z) for p in e), key=lambda x: -x[1])[:5]
    print("[dad] raw F1={F1:+.2f} F2={F2:+.2f} F4={F4:+.2f} F5={F5:+.2f}  ->  ".format(**fd)
          + "  ".join(f"{p}:{pr:.3f}" for p, pr in top))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate the factor reference for the four-factor typology.

Writes:
  viz/src/data/factorLoadings.json  per factor (strongest sorter first): label, poles, eta (the weighted
                                    eta-squared of the factor score by party), bw (between-party SD over
                                    within-party SD), and every item loading |lambda| > 0.20 with its
                                    survey question
  viz/src/data/factorItems.json     {factor: [{key, loading}]} and {key: primary factor}, keyed by the
                                    app's variable names (clusterProfiles), which constants/parties.ts
                                    imports as FACTOR_ITEMS and VAR_FACTOR

Loadings: analysis/efa/exploration/listwise_check/outputs/stage_c_v2/loadings.csv (the four entering
factors), carried to the app keys of pipeline/factor_keys.py (F1 = -SO, F5 = -PC) and signed by each
item's keyed answer (support, agree, increase, low trust, attends more, a later abortion limit), so a
positive loading means that answer goes with a high score on the factor.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import factor_keys as fk  # noqa: E402

LW = ROOT / "analysis" / "efa" / "exploration" / "listwise_check" / "outputs" / "stage_c_v2"
QUIZ = ROOT / "viz" / "src" / "data" / "quizQuestions.json"
PROFILES = ROOT / "viz" / "src" / "data" / "clusterProfiles.json"
OUT_LOADINGS = ROOT / "viz" / "src" / "data" / "factorLoadings.json"
OUT_ITEMS = ROOT / "viz" / "src" / "data" / "factorItems.json"

ROLE_COL = {"RT": "F4", "TR": "F2", "SO": "F1", "PC": "F5"}
META = {
    "F1": {"short": "SO", "label": "Security & Order", "color": "#1d4ed8",
           "hi": "More police and border patrols, more law-enforcement spending",
           "lo": "Fewer police, more spending on other services"},
    "F2": {"short": "GD", "label": "Government Distrust", "color": "#7c3aed",
           "hi": "Little or no trust in federal and state government; doubts elections are fair",
           "lo": "Trusts federal and state government and elections"},
    "F4": {"short": "CC", "label": "Cultural Conservatism", "color": "#dc2626",
           "hi": "Restricts abortion and gender transition for minors; backs school vouchers; born-again",
           "lo": "Protects abortion access, same-sex marriage and contraception"},
    "F5": {"short": "EC", "label": "Economic Conservatism", "color": "#92400e",
           "hi": "Cuts state spending on health care, education and welfare; opposes Medicaid expansion",
           "lo": "Raises state social spending, expands Medicaid, taxes high earners"},
}
QUESTION_OVERRIDE = {
    "CC24_325": "Later week limit for a legal abortion",
    "CC24_423": "Low trust in the federal government",
    "CC24_424": "Low trust in state government",
    "pew_churatd": "Frequency of religious service attendance",
}


def app_key(item, profile_vars):
    for k in (item, item + "_agree", item + "_median"):
        if k in profile_vars:
            return k
    return item


def keyed_direction(q):
    """+1 when the item's keyed answer (support, agree, increase, low trust, ...) is coded high."""
    v = q["variable"]
    if v == "CC24_325":
        return -1.0           # coded 40 - weeks; keyed = a later limit
    if v in ("CC24_423", "CC24_424"):
        return 1.0 if q["options"][-1]["value"] >= 0.5 else -1.0   # keyed = "None at all", the last option
    first = q["options"][0]   # Strongly support / Strongly agree / Greatly increase / attends most / Yes
    return 1.0 if first["value"] >= 0.5 else -1.0


def main():
    qs = {q["variable"]: q for q in json.loads(QUIZ.read_text())}
    profile_vars = json.loads(PROFILES.read_text())[0]["variables"]
    L = pd.read_csv(LW / "loadings.csv", index_col=0)
    fac = pd.read_csv(LW / "factors.csv")
    cols = {}
    for _, r in fac[fac.enters].iterrows():
        n = r["name"]
        role = "RT" if ("Religious" in n or "new:" in n) else "TR" if "Distrust" in n else "SO" if "Security" in n else "PC"
        cols[ROLE_COL[role]] = f"F{r.factor}"
    sign = {k: fk.SOURCE[k][1] for k in fk.KEYS}

    efa = pd.read_csv(ROOT / "data" / "processed" / "efa_factor_scores.csv")
    typ = pd.read_csv(ROOT / "data" / "processed" / "typology_cluster_assignments.csv", usecols=["caseid", "cluster"])
    d = efa.merge(typ, on="caseid", validate="one_to_one")
    w = d.commonpostweight.values
    eta = {}
    for k in fk.KEYS:
        x = d[f"FS_{k}"].values
        m = np.average(x, weights=w)
        between = sum(w[d.cluster == c].sum() * (np.average(x[d.cluster == c], weights=w[d.cluster == c]) - m) ** 2
                      for c in d.cluster.unique()) / w.sum()
        eta[k] = between / np.average((x - m) ** 2, weights=w)

    items, primary, loadings = {k: [] for k in fk.KEYS}, {}, []
    for item in L.index:
        q = qs.get(item)
        dirn = keyed_direction(q) if q else 1.0
        key = app_key(item, profile_vars)
        best = None
        for k in fk.KEYS:
            lam = float(L.loc[item, cols[k]]) * sign[k] * dirn
            if abs(lam) > 0.20:
                items[k].append({"key": key, "loading": round(lam, 3)})
            if best is None or abs(lam) > abs(best[1]):
                best = (k, lam)
        primary[key] = best[0]
    for k in items:
        items[k].sort(key=lambda it: -abs(it["loading"]))

    order = sorted(fk.KEYS, key=lambda k: -eta[k])
    for k in order:
        bw = float(np.sqrt(eta[k] / (1 - eta[k])))
        qtext = {}
        for it in items[k]:
            base = it["key"].removesuffix("_agree").removesuffix("_median")
            qtext[it["key"]] = QUESTION_OVERRIDE.get(base) or profile_vars.get(it["key"], {}).get("question") \
                or (qs[base]["question"] if base in qs else base)
        loadings.append({**META[k], "factor": k, "eta": round(float(eta[k]), 3), "bw": round(bw, 2),
                         "strength": f"Parties sit about {bw:.1f}x farther apart on this factor than the spread within each one.",
                         "items": [{"loading": it["loading"], "question": qtext[it["key"]]} for it in items[k]]})

    OUT_LOADINGS.write_text(json.dumps(loadings, indent=2) + "\n")
    OUT_ITEMS.write_text(json.dumps({"order": order, "items": items, "primary": primary}, indent=2) + "\n")
    print(f"wrote {OUT_LOADINGS.relative_to(ROOT)} and {OUT_ITEMS.relative_to(ROOT)}")
    for f in loadings:
        print(f"  {f['factor']} {f['label']}: eta2 {f['eta']}, {len(f['items'])} items")


if __name__ == "__main__":
    main()

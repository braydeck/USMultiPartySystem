#!/usr/bin/env python3
"""Generate viz/src/data/factorLoadings.json for the methodology display.

Authoritative sources: analysis/efa/efa_loadings_k5_final.csv (loadings) and
clusterProfiles.json (the REAL survey-question text). This replaces hand-transcribed
descriptions, which had errors (e.g. CC24_321b is concealed-carry, not 'community
policing'; CC24_440c is 'women seek power over men', not 'progressive racial attitudes').

Per factor: η²/strength metadata (from the discriminating-power analysis) plus every item
loading |λ|>0.20 on that factor, sorted by |loading|, with its real question.
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
LOADINGS = ROOT / "analysis" / "efa" / "efa_loadings_k5_final.csv"
PROFILES = json.loads((ROOT / "viz" / "src" / "data" / "clusterProfiles.json").read_text())
OUT = ROOT / "viz" / "src" / "data" / "factorLoadings.json"

vars0 = PROFILES[0]["variables"]

# Cleaner display text for a few clunky/median items; otherwise use the clusterProfiles question.
QUESTION_OVERRIDE = {
    "CC24_325": "Stricter limits on how many weeks abortion is legal",
    "CC24_423": "Low trust in the federal government",
    "CC24_424": "Low trust in state government",
    "pew_churatd": "Frequency of church attendance",
    "CC24_302": "Household finances got worse over the past year",
    "CC24_303": "Perceive consumer prices as higher",
}

def question_for(code: str) -> str:
    if code in QUESTION_OVERRIDE:
        return QUESTION_OVERRIDE[code]
    for k in (code, code + "_agree", code + "_median"):
        if k in vars0:
            return vars0[k]["question"]
    return code

# Factor metadata (η², B/W, interpretation) from the discriminating-power analysis.
META = {
    "F5": {"short": "PC", "label": "Populist Conservatism", "color": "#92400e", "eta": 0.736, "bw": 1.67,
           "strength": "Strongest sorter. Parties sit about 1.7x farther apart than the spread within each one.",
           "hi": "Anti-elite, nationalist, culturally conservative", "lo": "Cosmopolitan, progressive on culture and economics",
           "note": "Most items load negatively: the survey coded progressive answers as higher numbers, so a negative loading means a high factor score predicts the conservative answer."},
    "F1": {"short": "SO", "label": "Security & Order", "color": "#1d4ed8", "eta": 0.701, "bw": 1.53,
           "strength": "Nearly as strong. The main law-and-order axis.",
           "hi": "Pro-police, tougher sentencing, strong military", "lo": "Reform policing, de-escalation, diplomacy-first"},
    "F2": {"short": "ES", "label": "Electoral Skepticism", "color": "#7c3aed", "eta": 0.375, "bw": 0.775,
           "strength": "Cross-cutting. Within-party noise is larger than the gap between parties, and it cuts across left and right.",
           "hi": "Questions election integrity, anti-establishment media", "lo": "Trusts institutions, accepts electoral outcomes"},
    "F4": {"short": "RT", "label": "Religious Traditionalism", "color": "#dc2626", "eta": 0.305, "bw": 0.663,
           "strength": "Moderate. Sorts parties mainly on abortion and marriage, with substantial within-party noise.",
           "hi": "Faith-informed policy, traditional family structures", "lo": "Secular policy, pluralist social norms"},
    "F3": {"short": "GD", "label": "Government Distrust", "color": "#b45309", "eta": 0.057, "bw": 0.246,
           "strength": "Essentially non-differentiating: every party scores Medium, so it is not used to place you in the quiz.",
           "hi": "Government is inefficient and overreaches", "lo": "Government can solve problems, trusts agencies"},
}

rows = list(csv.DictReader(open(LOADINGS)))
out = []
for f in ["F5", "F1", "F2", "F4", "F3"]:  # sorted by η² descending
    items = []
    for r in rows:
        load = float(r[f])
        if abs(load) > 0.20:
            items.append({"loading": round(load, 3), "question": question_for(r[""])})
    items.sort(key=lambda it: -abs(it["loading"]))
    out.append({**META[f], "factor": f, "items": items})

OUT.write_text(json.dumps(out, indent=2) + "\n")
print(f"wrote {len(out)} factors to {OUT.relative_to(ROOT)}")
for fac in out:
    print(f"  {fac['short']} {fac['label']}: {len(fac['items'])} items")

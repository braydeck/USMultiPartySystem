#!/usr/bin/env python3
"""Generate viz/src/data/quizQuestions.json from clusterProfiles.json.

Picks the highest-discrimination items across the 9 parties, covering F1/F4/F5
heavily plus two cross-cutting F2 items. Drops F3 (non-differentiating: all
parties score Medium). clusterSupport = each party's policy support, 0-1.
Retune by editing QUESTIONS below and re-running.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROFILES = ROOT / "viz" / "src" / "data" / "clusterProfiles.json"
OUT = ROOT / "viz" / "src" / "data" / "quizQuestions.json"
ACTIVE = ["0", "1", "2", "3", "4", "5", "6", "8", "9"]  # cluster 7 dissolved

# (variable, factor, optional question override for awkward Likert phrasing)
QUESTIONS = [
    ("CC24_340f", "F1", None),
    ("CC24_321d", "F1", None),
    ("CC24_323b", "F1", None),
    ("CC24_323a", "F5", None),
    ("CC24_323d", "F5", None),
    ("CC24_341c", "F5", None),
    ("CC24_341b", "F5", None),
    ("CC24_321b", "F5", None),
    ("pew_churatd", "F4", "I attend religious services regularly"),
    ("CC24_340c", "F4", None),
    ("CC24_325_median", "F4", "Abortion should be legal:"),  # weeks scale (see WEEKS_OPTIONS)
    ("CC24_421_1_agree", "F2", None),
    ("CC24_421_2_agree", "F2", None),
]

# Abortion-by-weeks is more intuitive than the "rape/incest/life only" binary.
# Answer values and cluster support are on a 0-1 permissiveness scale = weeks / 40.
WEEKS_OPTIONS = [
    {"value": 1.0, "label": "A woman's choice, without limits"},
    {"value": 0.6, "label": "Up to about 24 weeks (viability)"},
    {"value": 0.375, "label": "Up to about 15 weeks"},
    {"value": 0.15, "label": "Up to about 6 weeks"},
    {"value": 0.0, "label": "Only for rape, incest, or the mother's life"},
]

profiles = json.loads(PROFILES.read_text())
by_id = {p["id"]: p for p in profiles}

out = []
for code, factor, override in QUESTIONS:
    meta = by_id["2"]["variables"].get(code) or next(
        (by_id[a]["variables"][code] for a in ACTIVE if code in by_id[a]["variables"]), None)
    if meta is None:
        raise SystemExit(f"missing variable: {code}")
    denom = 40.0 if code == "CC24_325_median" else 100.0  # weeks/40 vs pct/100
    support = {a: round(min(by_id[a]["variables"][code]["pct"] / denom, 1.0), 6) for a in ACTIVE
               if code in by_id[a]["variables"]}
    if len(support) != len(ACTIVE):
        raise SystemExit(f"{code} missing in some clusters")
    entry = {
        "variable": code,
        "factor": factor,
        "question": override or meta["question"],
        "domain": meta["domain"],
        "clusterSupport": support,
    }
    if code == "CC24_325_median":
        entry["options"] = WEEKS_OPTIONS
    out.append(entry)

OUT.write_text(json.dumps(out, indent=2) + "\n")
print(f"wrote {len(out)} questions to {OUT.relative_to(ROOT)}")
print("factor coverage:", {f: sum(1 for _, ff, _ in QUESTIONS if ff == f) for f in ["F1", "F2", "F4", "F5"]})

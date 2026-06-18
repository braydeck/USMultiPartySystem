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
    ("CC24_324b", "F4", None),
    ("CC24_421_1_agree", "F2", None),
    ("CC24_421_2_agree", "F2", None),
]

profiles = json.loads(PROFILES.read_text())
by_id = {p["id"]: p for p in profiles}

out = []
for code, factor, override in QUESTIONS:
    meta = by_id["2"]["variables"].get(code) or next(
        (by_id[a]["variables"][code] for a in ACTIVE if code in by_id[a]["variables"]), None)
    if meta is None:
        raise SystemExit(f"missing variable: {code}")
    support = {a: round(by_id[a]["variables"][code]["pct"] / 100, 6) for a in ACTIVE
               if code in by_id[a]["variables"]}
    if len(support) != len(ACTIVE):
        raise SystemExit(f"{code} missing in some clusters")
    out.append({
        "variable": code,
        "factor": factor,
        "question": override or meta["question"],
        "domain": meta["domain"],
        "clusterSupport": support,
    })

OUT.write_text(json.dumps(out, indent=2) + "\n")
print(f"wrote {len(out)} questions to {OUT.relative_to(ROOT)}")
print("factor coverage:", {f: sum(1 for _, ff, _ in QUESTIONS if ff == f) for f in ["F1", "F2", "F4", "F5"]})

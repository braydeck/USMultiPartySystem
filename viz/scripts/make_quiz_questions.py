#!/usr/bin/env python3
"""Generate viz/src/data/quizQuestions.json from clusterProfiles.json.

The set is the top-loading items for each differentiating factor (F1, F2, F4, F5);
F3 is dropped (non-differentiating). Each item carries its EFA loading magnitude,
used as a weight when estimating the respondent's factor-space position (Method A
probabilistic scoring). clusterSupport = each party's value for the item, 0-1; the
classifier learns each item's orientation to the factor from the cluster data, so
phrasing/sign conventions don't have to be reconciled by hand.

Retune by editing QUESTIONS and re-running.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROFILES = ROOT / "viz" / "src" / "data" / "clusterProfiles.json"
OUT = ROOT / "viz" / "src" / "data" / "quizQuestions.json"
ACTIVE = ["0", "1", "2", "3", "4", "5", "6", "8", "9"]  # cluster 7 dissolved

# Abortion-by-weeks is more intuitive than a binary. Values + cluster support are on a
# 0-1 permissiveness scale = weeks / 40.
WEEKS_OPTIONS = [
    {"value": 1.0, "label": "A woman's choice, without limits"},
    {"value": 0.6, "label": "Up to about 24 weeks (viability)"},
    {"value": 0.375, "label": "Up to about 15 weeks"},
    {"value": 0.15, "label": "Up to about 6 weeks"},
    {"value": 0.0, "label": "Only for rape, incest, or the mother's life"},
]

# Full set: every answerable item that loads |λ|>0.2, assigned to its top differentiating
# factor (F1/F2/F4/F5; F3 dropped). (variable, factor, loading magnitude, question override)
QUESTIONS = [
    # F1 — Security & Order
    ("CC24_321d", "F1", 0.734, "Increase the number of police by 10%"),
    ("CC24_323b", "F1", 0.705, "Increase border patrols on the US-Mexico border"),
    ("CC24_340f", "F1", 0.664, "Deny asylum to people crossing the border illegally"),
    ("CC24_321e", "F1", 0.653, "Cut the number of police by 10% and shift the funding elsewhere"),
    ("CC24_340e", "F1", 0.493, "Renew the post-9/11 government surveillance programs"),
    ("CC24_341a", "F1", 0.260, "Extend the 2017 tax cuts"),
    # F2 — Electoral Skepticism
    ("CC24_421_2_agree", "F2", 0.901, "Your 2024 state and local elections were run fairly"),
    ("CC24_421_1_agree", "F2", 0.726, "U.S. elections are run fairly"),
    ("CC24_424", "F2", 0.380, "I have little trust in my state government"),
    ("CC24_423", "F2", 0.240, "I have little trust in the federal government"),
    # F4 — Religious Traditionalism
    ("pew_churatd", "F4", 0.688, "I attend religious services regularly"),
    ("CC24_325_median", "F4", 0.688, "Abortion should be legal:"),
    ("CC24_340c", "F4", 0.651, "Require states to recognize same-sex and interracial marriages"),
    ("CC24_340b", "F4", 0.489, "Pass a federal law protecting access to abortion"),
    # CC24_324b ("abortion only in rape/incest/life") dropped: lowest F4 loading and redundant
    # with the abortion-by-weeks item, whose most-restrictive option says the same thing.
    # F5 — Populist Conservatism
    ("CC24_440b_agree", "F5", 0.616, "Racial problems in the U.S. are rare, isolated situations"),
    ("CC24_321b", "F5", 0.557, "Make it easier to get a concealed-carry permit"),
    ("CC24_323d", "F5", 0.540, "A permanent pathway to citizenship for Dreamers"),
    ("CC24_341c", "F5", 0.534, "Let tax rates on income over $400k rise to 35%"),
    ("CC24_323a", "F5", 0.520, "Grant legal status to long-term undocumented immigrants"),
    ("CC24_440c_agree", "F5", 0.437, "Women seek to gain power by getting control over men"),
    ("CC24_341d", "F5", 0.365, "Spend $150 billion a year on infrastructure"),
]

profiles = json.loads(PROFILES.read_text())
by_id = {p["id"]: p for p in profiles}

out = []
for code, factor, loading, override in QUESTIONS:
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
        "loading": loading,
        "question": override or meta["question"],
        "domain": meta["domain"],
        "clusterSupport": support,
    }
    if code == "CC24_325_median":
        entry["options"] = WEEKS_OPTIONS
    out.append(entry)

OUT.write_text(json.dumps(out, indent=2) + "\n")
print(f"wrote {len(out)} questions")
cov = {}
for _, f, *_ in QUESTIONS:
    cov[f] = cov.get(f, 0) + 1
print("factor coverage:", cov)

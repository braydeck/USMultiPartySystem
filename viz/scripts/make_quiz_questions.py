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

# Response scales: exact CES wording on the surface, each option's `value` keyed to the
# clusterSupport axis (clusterSupport = pct/100 = fraction giving the keyed response, so
# value 1 = behaves like a cluster at 100% on that axis). Orientation to the factor is then
# learned from the cluster data, so only the value→clusterSupport mapping must be right here.

# Policy batteries (CC24_321/323/340/341): original is binary Support/Oppose. We add an
# intensity gradient (no neutral) so an individual's answer lands on the same continuous
# support axis the model was calibrated on (cluster fractions); pure 0/1 over-extremizes.
# clusterSupport = % who Support the statement → Strongly support 1, Strongly oppose 0.
INTENSITY = [
    {"value": 1.0,  "label": "Strongly support"},
    {"value": 0.75, "label": "Support"},
    {"value": 0.25, "label": "Oppose"},
    {"value": 0.0,  "label": "Strongly oppose"},
]

# Agree/disagree statements (CC24_421_*, CC24_440*): clusterSupport = % who agree.
AGREE_5 = [
    {"value": 1.0,  "label": "Strongly agree"},
    {"value": 0.75, "label": "Somewhat agree"},
    {"value": 0.5,  "label": "Neither agree nor disagree"},
    {"value": 0.25, "label": "Somewhat disagree"},
    {"value": 0.0,  "label": "Strongly disagree"},
]

# Trust in government (CC24_423/424): clusterSupport keys to % with LOW trust, so the
# value rises with distrust (None at all = 1) even though the prompt asks how much trust.
TRUST_4 = [
    {"value": 0.0,  "label": "A great deal"},
    {"value": 0.33, "label": "A fair amount"},
    {"value": 0.67, "label": "Not very much"},
    {"value": 1.0,  "label": "None at all"},
]

# Religious attendance (pew_churatd): clusterSupport keys to % attending regularly, so the
# value rises with frequency.
CHURCH_6 = [
    {"value": 1.0,  "label": "More than once a week"},
    {"value": 0.8,  "label": "Once a week"},
    {"value": 0.5,  "label": "Once or twice a month"},
    {"value": 0.25, "label": "A few times a year"},
    {"value": 0.1,  "label": "Seldom"},
    {"value": 0.0,  "label": "Never"},
]

# Abortion is a 0-40 week slider in CES; discretized here. Values + clusterSupport are on a
# 0-1 permissiveness scale = weeks / 40.
WEEKS_OPTIONS = [
    {"value": 1.0,   "label": "A woman's choice, without limits"},
    {"value": 0.6,   "label": "Up to about 24 weeks (viability)"},
    {"value": 0.375, "label": "Up to about 15 weeks"},
    {"value": 0.15,  "label": "Up to about 6 weeks"},
    {"value": 0.0,   "label": "Never legal, or only for rape, incest, or the mother's life"},
]

# Conceptual sections — group items by response type, each with an answering instruction.
SECTION_INFO = {
    "policy":   {"section": "Policy Proposals",    "instruction": "Do you support or oppose each proposal — and how strongly?"},
    "agree":    {"section": "Statements",          "instruction": "Rate your level of agreement."},
    "trust":    {"section": "Trust in Government",  "instruction": "Rate your level of trust."},
    "religion": {"section": "Religion & Abortion",  "instruction": "Choose the answer that fits you best."},
}

# Full set: every answerable item that loads |λ|>0.2, assigned to its top differentiating
# factor (F1/F2/F4/F5; F3 dropped). Question text is the exact CES wording. Items are ordered
# and grouped by section. (variable, factor, loading, exact question, options, section)
QUESTIONS = [
    # ── Policy Proposals (Support/Oppose intensity) ──────────────────────────
    ("CC24_321d", "F1", 0.734, "Increase the number of police on the street by 10 percent, even if it means fewer funds for other public services", INTENSITY, "policy"),
    ("CC24_321e", "F1", 0.653, "Decrease the number of police on the street by 10 percent, and increase funding for other public services", INTENSITY, "policy"),
    ("CC24_321b", "F5", 0.557, "Make it easier for people to obtain concealed-carry permit", INTENSITY, "policy"),
    ("CC24_323b", "F1", 0.705, "Increase the number of border patrols on the US-Mexican border", INTENSITY, "policy"),
    ("CC24_340f", "F1", 0.664, "Deny access to asylum for immigrants who cross the US-Mexico border illegally", INTENSITY, "policy"),
    ("CC24_323a", "F5", 0.520, "Grant legal status to all illegal immigrants who have held jobs and paid taxes for at least 3 years, and not been convicted of any felony crimes", INTENSITY, "policy"),
    ("CC24_323d", "F5", 0.540, "Provide permanent resident status to children of immigrants who were brought to the United States by their parents (also known as Dreamers). Provide these immigrants a pathway to citizenship if they meet the citizenship requirements and have committed no crimes", INTENSITY, "policy"),
    ("CC24_340e", "F1", 0.493, "Renew the federal surveillance programs that were adopted after 9/11 and that allow the government to search private electronic data without a search warrant", INTENSITY, "policy"),
    ("CC24_341a", "F1", 0.260, "Extend the tax cuts enacted in 2017, which reduced individual and corporate income tax rates and limited deductions on mortgage interest and state and local taxes", INTENSITY, "policy"),
    ("CC24_341c", "F5", 0.534, "Allow tax rates on those earning $400,000 or more a year to rise to 35 percent", INTENSITY, "policy"),
    ("CC24_341d", "F5", 0.365, "Spend $150 billion a year for 8 years on construction and repair of roads and bridges, rail, public transit, airports, water systems, broadband internet, and electric grid", INTENSITY, "policy"),
    ("CC24_340c", "F4", 0.651, "Require that all federal agencies recognize same-sex marriages and interracial marriages", INTENSITY, "policy"),
    ("CC24_340b", "F4", 0.489, "Prohibit government restrictions on the provision of, and access to, abortion services", INTENSITY, "policy"),
    # ── Statements (agree/disagree) ──────────────────────────────────────────
    ("CC24_421_1_agree", "F2", 0.726, "Elections in the U.S. are fair", AGREE_5, "agree"),
    ("CC24_421_2_agree", "F2", 0.901, "Your state or local government conducted a fair and accurate election in 2024", AGREE_5, "agree"),
    ("CC24_440b_agree", "F5", 0.616, "Racial problems in the U.S. are rare, isolated situations", AGREE_5, "agree"),
    ("CC24_440c_agree", "F5", 0.437, "Women seek to gain power by getting control over men", AGREE_5, "agree"),
    # ── Trust in Government ──────────────────────────────────────────────────
    ("CC24_423", "F2", 0.240, "How much trust do you have in the federal government in Washington when it comes to handling the nation's problems?", TRUST_4, "trust"),
    ("CC24_424", "F2", 0.380, "How much trust do you have in the government of the state where you live when it comes to handling the state's problems?", TRUST_4, "trust"),
    # ── Religion & Abortion ──────────────────────────────────────────────────
    ("pew_churatd", "F4", 0.688, "Aside from weddings and funerals, how often do you attend religious services?", CHURCH_6, "religion"),
    ("CC24_325_median", "F4", 0.688, "Until what point in a pregnancy do you think a woman should be legally allowed to obtain an abortion? (A normal pregnancy runs up to about 40 weeks.)", WEEKS_OPTIONS, "religion"),
    # CC24_324b ("abortion only in rape/incest/life") dropped: lowest F4 loading and redundant
    # with the abortion-by-weeks item, whose most-restrictive option says the same thing.
    # CC24_302 (household income change) and CC24_303 (perceived price change / inflation) are
    # also in the 24-item EFA but omitted here: both are near-zero-communality retrospective
    # *perceptions* (|loadings| <= 0.22 on every factor), not policy stances, so they make poor
    # party-match questions and add negligible discriminating signal. This makes the quiz 21
    # items = 24 EFA items - 324b - 302 - 303; F3 is dropped only as a scoring axis (its two
    # trust items, 423/424, are retained above under F2).
]

profiles = json.loads(PROFILES.read_text())
by_id = {p["id"]: p for p in profiles}

out = []
for code, factor, loading, question, options, section_key in QUESTIONS:
    meta = by_id["2"]["variables"].get(code) or next(
        (by_id[a]["variables"][code] for a in ACTIVE if code in by_id[a]["variables"]), None)
    if meta is None:
        raise SystemExit(f"missing variable: {code}")
    denom = 40.0 if code == "CC24_325_median" else 100.0  # weeks/40 vs pct/100
    support = {a: round(min(by_id[a]["variables"][code]["pct"] / denom, 1.0), 6) for a in ACTIVE
               if code in by_id[a]["variables"]}
    if len(support) != len(ACTIVE):
        raise SystemExit(f"{code} missing in some clusters")
    info = SECTION_INFO[section_key]
    out.append({
        "variable": code,
        "factor": factor,
        "loading": loading,
        "question": question,
        "domain": meta["domain"],
        "section": info["section"],
        "instruction": info["instruction"],
        "clusterSupport": support,
        "options": options,
    })

OUT.write_text(json.dumps(out, indent=2) + "\n")
print(f"wrote {len(out)} questions")
cov = {}
for _, f, *_ in QUESTIONS:
    cov[f] = cov.get(f, 0) + 1
print("factor coverage:", cov)

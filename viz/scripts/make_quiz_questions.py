#!/usr/bin/env python3
"""Generate viz/src/data/quizQuestions.json: the quiz items of the nine-party typology (the 41 factor items less
QUIZ_EXCLUDE).

Items and their order come from analysis/efa/rebuild_nine_parties/quiz_items.csv (greedy by held-out
factor R2). The short quiz is the first 25 of that order, the long quiz all of them (ruled 2026-11-04,
analysis/efa/exploration/listwise_check/DECISIONS.md). Each question carries `short` (true when it is
in the short quiz); the app shows the items of the chosen version in this file's order, which groups
them by section.

Question wording is the CES item text (the variable label after the battery prefix, or the
questionnaire stem where the label is a bare area name). Answer values sit on the scale the scoring
key is fit on (analysis/efa/build_quiz_shortform.py): each item's coding in
analysis/efa/exploration/listwise_check/item_pool.py, min-max scaled to 0-1. Those values are read off
the data here, label by label, so an item coded high = oppose gets reversed values automatically.
Binary support/oppose and agree/disagree items get a four-step intensity scale (the strong answers at
the item's 0 and 1, the mild ones at 0.25 / 0.75), as the five-factor quiz did.

`factor` is the item's primary app factor key (largest |loading| among the four entering factors of
outputs/stage_c_v2/loadings.csv), `loading` that |loading|. clusterSupport is each live party's
weighted mean answer on the 0-1 scale.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

ROOT = Path(__file__).resolve().parent.parent.parent
LW = ROOT / "analysis" / "efa" / "exploration" / "listwise_check"
sys.path.insert(0, str(LW))
sys.path.insert(0, str(ROOT / "pipeline"))
import item_pool as ip  # noqa: E402
from party_codes import LIVE_CLUSTERS  # noqa: E402

ITEMS_CSV = ROOT / "analysis" / "efa" / "rebuild_nine_parties" / "quiz_items.csv"
LOADINGS = LW / "outputs" / "stage_c_v2" / "loadings.csv"
FACTORS = LW / "outputs" / "stage_c_v2" / "factors.csv"
STATS = ROOT / "data" / "outputs" / "profiles" / "cluster_stats.csv"
TYPO = ROOT / "data" / "processed" / "typology_cluster_assignments.csv"
PROFILES = ROOT / "viz" / "src" / "data" / "clusterProfiles.json"
OUT = ROOT / "viz" / "src" / "data" / "quizQuestions.json"
N_SHORT = 25
# Items that stay in the factor model and on the rest of the site but are not asked in the quiz.
QUIZ_EXCLUDE = {
    "CC24_340d": "TikTok ban: the forced-sale deadline has passed, so the question is out of date (ruled 2026-11-05)",
}

ROLE_TO_KEY = {"RT": "F4", "TR": "F2", "SO": "F1", "PC": "F5"}

SECTIONS = {
    "policy":   ("Policy Proposals", "Do you support or oppose each proposal, and how strongly?"),
    "court":    ("Supreme Court Decisions", "Do you agree or disagree with each decision of the Supreme Court, and how strongly?"),
    "spending": ("State Spending", "State legislatures must make choices when making spending decisions on important state programs. How would you like your legislature to spend money on each area?"),
    "agree":    ("Statements", "How much do you agree or disagree with each statement?"),
    "trust":    ("Trust in Government", "Rate your level of trust."),
    "religion": ("Religion & Abortion", "Choose the answer that fits you best."),
}
SECTION_ORDER = list(SECTIONS)

# Items whose variable label is not the question a respondent reads.
QUESTION_TEXT = {
    "CC24_423": "How much trust do you have in the federal government in Washington when it comes to handling the nation's problems?",
    "CC24_424": "How much trust do you have in the government of the state where you live when it comes to handling the state's problems?",
    "pew_churatd": "Aside from weddings and funerals, how often do you attend religious services?",
    "pew_bornagain": 'Would you describe yourself as a "born-again" or evangelical Christian, or not?',
    "CC24_325": "Until what point in a pregnancy do you think a woman should be legally allowed to obtain an abortion? (A normal pregnancy runs up to about 40 weeks.)",
    "CC24_421_1": "Elections in the U.S. are fair",
}

# Abortion week limit: CES asks for a week (0-40); the quiz offers five stops.
WEEKS = [(40, "A woman's choice, without limits"), (24, "Up to about 24 weeks (viability)"),
         (15, "Up to about 15 weeks"), (6, "Up to about 6 weeks"),
         (0, "Never legal, or only for rape, incest, or the mother's life")]


def section_of(item):
    if item in ("CC24_423", "CC24_424"):
        return "trust"
    if item.startswith("pew_") or item == "CC24_325":
        return "religion"
    if item.startswith("CC24_445"):
        return "court"
    if item.startswith("CC24_443"):
        return "spending"
    if item.startswith(("CC24_421", "CC24_440", "CC24_441")):
        return "agree"
    return "policy"


def intensity(v_yes, yes, no):
    """Four-step scale for a binary item whose `yes` answer codes to v_yes (0 or 1)."""
    mild = 0.75 * v_yes + 0.25 * (1 - v_yes)
    return [{"value": round(v_yes, 4), "label": f"Strongly {yes.lower()}"},
            {"value": round(mild, 4), "label": yes},
            {"value": round(1 - mild, 4), "label": no},
            {"value": round(1 - v_yes, 4), "label": f"Strongly {no.lower()}"}]


def main():
    order = [i for i in pd.read_csv(ITEMS_CSV).item.tolist() if i not in QUIZ_EXCLUDE]
    short = set(order[:N_SHORT])

    X, w, _, caseid = ip.load()
    _, meta = pyreadstat.read_dta(ip.eu.CES_PATH, metadataonly=True)
    lab = pd.read_stata(ip.eu.CES_PATH, columns=[c for c in order if c != "CC24_325"], convert_categoricals=True)
    post = pd.to_numeric(pd.read_stata(ip.eu.CES_PATH, columns=["commonpostweight"],
                                       convert_categoricals=False).commonpostweight, errors="coerce").values > 0
    lab = lab[post].reset_index(drop=True)

    L = pd.read_csv(LOADINGS, index_col=0)
    fac = pd.read_csv(FACTORS)
    roles = {}
    for _, r in fac[fac.enters].iterrows():
        name = r["name"]
        roles[f"F{r.factor}"] = ("RT" if "Religious" in name or "new:" in name else
                                 "TR" if "Distrust" in name else "SO" if "Security" in name else "PC")
    assert sorted(roles.values()) == ["PC", "RT", "SO", "TR"], roles

    typ = pd.read_csv(TYPO, usecols=["caseid", "cluster", "commonpostweight"])
    pos = pd.Series(np.arange(len(caseid)), index=caseid).loc[typ.caseid.values].values
    cl, wt = typ.cluster.values, typ.commonpostweight.values
    domains = pd.read_csv(STATS).drop_duplicates("variable").set_index("variable")["domain"].to_dict()
    # cluster_stats files an item under its CES battery (CC24_323f, student debt, sits in the immigration battery);
    # the Parties tab's clusterProfiles.json carries the topic, so prefer it
    prof = json.loads(PROFILES.read_text())[0]["variables"]
    for k, v in prof.items():
        base = k.removesuffix("_agree").removesuffix("_median")
        if v.get("domain"):
            domains[base] = v["domain"]

    out = []
    for item in order:
        x = X[item].values.astype(float)
        lo, hi = np.nanmin(x), np.nanmax(x)
        scaled = (x - lo) / (hi - lo)
        sec = section_of(item)
        if item == "CC24_325":
            assert lo == 0 and hi == 40  # item_pool codes 40 - weeks (restrictiveness)
            options = [{"value": round((40 - wk) / 40, 4), "label": txt} for wk, txt in WEEKS]
        else:
            df = pd.DataFrame({"l": lab[item].astype(str), "v": scaled}).dropna()
            val = df.groupby("l").v.agg(["min", "max"])
            assert (val["min"] == val["max"]).all(), f"{item}: a label maps to several codes"
            val = val["min"].to_dict()
            cats = [c for c in lab[item].cat.categories if c in val]
            if set(cats) == {"Support", "Oppose"}:
                options = intensity(val["Support"], "Support", "Oppose")
            elif set(cats) == {"Agree", "Disagree"}:
                options = intensity(val["Agree"], "Agree", "Disagree")
            else:
                options = [{"value": round(val[c], 4), "label": c} for c in cats]
        label = meta.column_names_to_labels[item]
        question = QUESTION_TEXT.get(item, label.split(" -- ", 1)[-1].strip())
        ld = L.loc[item, list(roles)].abs()
        key = ROLE_TO_KEY[roles[ld.idxmax()]]
        s = scaled[pos]
        support = {}
        for k in LIVE_CLUSTERS:
            m = (cl == k) & ~np.isnan(s)
            support[str(k)] = round(float(np.average(s[m], weights=wt[m])), 6)
        name, instruction = SECTIONS[sec]
        out.append({"variable": item, "factor": key, "loading": round(float(ld.max()), 3),
                    "question": question, "domain": str(domains.get(item, "")), "section": name,
                    "instruction": instruction, "short": item in short,
                    "clusterSupport": support, "options": options})

    out.sort(key=lambda q: (SECTION_ORDER.index(next(k for k, v in SECTIONS.items() if v[0] == q["section"])),
                            order.index(q["variable"])))
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    n_short = sum(q["short"] for q in out)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(out)} questions, {n_short} in the short quiz")
    cov = pd.Series([q["factor"] for q in out]).value_counts().to_dict()
    print("primary factor per item:", cov)


if __name__ == "__main__":
    main()
